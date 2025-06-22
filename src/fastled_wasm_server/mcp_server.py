#!/usr/bin/env python3
"""
FastLED WASM Server MCP (Model Context Protocol) Server

This MCP server provides AI assistants with tools to interact with the FastLED WASM
compilation service, allowing them to compile Arduino/FastLED sketches to WASM,
fetch examples, and manage server settings.

SETUP INSTRUCTIONS:
1. Install MCP dependency: uv add mcp
2. Run the server: uv run python -m fastled_wasm_server.mcp_server

TOOLS PROVIDED:
- compile_sketch: Compile Arduino/FastLED sketches to WASM
- get_example: Fetch FastLED example sketches  
- list_examples: List all available examples
- get_compiler_status: Get compiler statistics and status

RESOURCES PROVIDED:
- fastled://examples: Available FastLED example sketches
- fastled://compiler/stats: Compiler usage statistics
- fastled://server/settings: Server configuration
"""

import asyncio
import json
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

# MCP imports - install with: uv add mcp
try:
    from mcp import types
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    MCP_AVAILABLE = True
except ImportError:
    print("MCP package not installed. Run 'uv add mcp' to install it.")
    MCP_AVAILABLE = False

# Pydantic should be available via fastapi
try:
    from pydantic import AnyUrl
    PYDANTIC_AVAILABLE = True
except ImportError:
    print("Pydantic not available - check fastapi installation")
    PYDANTIC_AVAILABLE = False

from fastled_wasm_server.compile_lock import COMPILE_LOCK
from fastled_wasm_server.examples import EXAMPLES
from fastled_wasm_server.paths import OUTPUT_DIR, VOLUME_MAPPED_SRC
from fastled_wasm_server.server_compile import ServerWasmCompiler
from fastled_wasm_server.types import CompilerStats
from fastled_wasm_compiler import Compiler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize compiler components (similar to main server.py)
_COMPILER_STATS = CompilerStats()
_NEW_COMPILER = Compiler(volume_mapped_src=VOLUME_MAPPED_SRC)
_COMPILER = ServerWasmCompiler(
    compiler_root=Path("/tmp/compiler"),  # Default compiler root
    sketch_cache=None,  # Simplified for MCP - could add caching later
    compiler=_NEW_COMPILER,
    only_quick_builds=False,
    compiler_lock=COMPILE_LOCK,
)

# Ensure output directory exists
OUTPUT_DIR.mkdir(exist_ok=True)


def create_mcp_server():
    """Create and configure the MCP server with all tools and resources."""
    if not MCP_AVAILABLE:
        raise ImportError("MCP package not available. Install with: uv add mcp")
    
    # Initialize the server
    server = Server("fastled-wasm-server")

    @server.list_resources()
    async def list_resources() -> List[types.Resource]:
        """List available resources."""
        return [
            types.Resource(
                uri=AnyUrl("fastled://examples"),
                name="FastLED Examples",
                description="Available FastLED example sketches",
                mimeType="application/json",
            ),
            types.Resource(
                uri=AnyUrl("fastled://compiler/stats"),
                name="Compiler Statistics", 
                description="Current compiler usage statistics",
                mimeType="application/json",
            ),
            types.Resource(
                uri=AnyUrl("fastled://server/settings"),
                name="Server Settings",
                description="Current server configuration",
                mimeType="application/json",
            ),
        ]

    @server.read_resource()
    async def read_resource(uri: AnyUrl) -> str:
        """Read a resource by URI."""
        if uri.scheme != "fastled":
            raise ValueError(f"Unsupported URI scheme: {uri.scheme}")

        path = str(uri).replace("fastled://", "")
        
        if path == "examples":
            return json.dumps({"examples": EXAMPLES}, indent=2)
        
        elif path == "compiler/stats":
            stats = {
                "compile_count": _COMPILER_STATS.compile_count,
                "compile_failures": _COMPILER_STATS.compile_failures,
                "compile_successes": _COMPILER_STATS.compile_successes,
                "compiler_in_use": COMPILE_LOCK.locked(),
            }
            return json.dumps(stats, indent=2)
        
        elif path == "server/settings":
            settings = {
                "volume_mapped_src": str(VOLUME_MAPPED_SRC),
                "volume_mapped_src_exists": VOLUME_MAPPED_SRC.exists(),
                "output_dir": str(OUTPUT_DIR),
            }
            return json.dumps(settings, indent=2)
        
        else:
            raise ValueError(f"Unknown resource path: {path}")

    @server.list_tools()
    async def list_tools() -> List[types.Tool]:
        """List available tools."""
        return [
            types.Tool(
                name="compile_sketch",
                description="Compile an Arduino/FastLED sketch to WASM",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "sketch_content": {
                            "type": "string",
                            "description": "The Arduino sketch code to compile"
                        },
                        "build_mode": {
                            "type": "string",
                            "enum": ["quick", "release", "debug"],
                            "description": "Build mode for compilation",
                            "default": "quick"
                        },
                        "filename": {
                            "type": "string",
                            "description": "Name for the sketch file",
                            "default": "sketch.ino"
                        }
                    },
                    "required": ["sketch_content"]
                }
            ),
            types.Tool(
                name="get_example",
                description="Fetch a FastLED example sketch",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "example_name": {
                            "type": "string",
                            "description": "Name of the example to fetch"
                        }
                    },
                    "required": ["example_name"]
                }
            ),
            types.Tool(
                name="list_examples",
                description="List all available FastLED examples",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            types.Tool(
                name="get_compiler_status", 
                description="Get current compiler status and statistics",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle tool calls."""
        
        if name == "compile_sketch":
            return await handle_compile_sketch(arguments)
        elif name == "get_example":
            return await handle_get_example(arguments)
        elif name == "list_examples":
            return await handle_list_examples(arguments)
        elif name == "get_compiler_status":
            return await handle_get_compiler_status(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")

    return server


async def handle_compile_sketch(arguments: Dict[str, Any]) -> List:
    """Handle sketch compilation."""
    sketch_content = arguments["sketch_content"]
    build_mode = arguments.get("build_mode", "quick")
    filename = arguments.get("filename", "sketch.ino")
    
    # Create a temporary file with the sketch content
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ino', delete=False) as temp_file:
        temp_file.write(sketch_content)
        temp_path = Path(temp_file.name)
    
    try:
        # Create a mock UploadFile-like object
        class MockUploadFile:
            def __init__(self, path: Path):
                self.filename = path.name
                self.content_type = "application/octet-stream"
                self._path = path
            
            def read(self) -> bytes:
                return self._path.read_bytes()
            
            async def aread(self) -> bytes:
                return self.read()
        
        mock_file = MockUploadFile(temp_path)
        
        # Use the compiler to compile the sketch
        try:
            file_response = _COMPILER.compile(
                file=mock_file,
                build=build_mode,
                profile="false",
                output_dir=OUTPUT_DIR,
                use_sketch_cache=False,
                background_tasks=None,
            )
            
            result = {
                "status": "success",
                "message": f"Successfully compiled {filename}",
                "build_mode": build_mode,
                "output_file": file_response.path if hasattr(file_response, 'path') else "Generated WASM file"
            }
            
            _COMPILER_STATS.compile_count += 1
            _COMPILER_STATS.compile_successes += 1
            
        except Exception as e:
            _COMPILER_STATS.compile_count += 1
            _COMPILER_STATS.compile_failures += 1
            result = {
                "status": "error",
                "message": f"Compilation failed: {str(e)}",
                "build_mode": build_mode,
            }
    
    finally:
        # Clean up temporary file
        temp_path.unlink(missing_ok=True)
    
    if MCP_AVAILABLE:
        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
    else:
        return [{"type": "text", "text": json.dumps(result, indent=2)}]


async def handle_get_example(arguments: Dict[str, Any]) -> List:
    """Handle example retrieval."""
    example_name = arguments["example_name"]
    
    if example_name not in EXAMPLES:
        result = {
            "status": "error",
            "message": f"Example '{example_name}' not found",
            "available_examples": EXAMPLES
        }
    else:
        result = {
            "status": "success",
            "example_name": example_name,
            "message": f"Example '{example_name}' is available",
            "note": "Use the FastLED server's /project/init endpoint to download the actual files"
        }
    
    if MCP_AVAILABLE:
        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
    else:
        return [{"type": "text", "text": json.dumps(result, indent=2)}]


async def handle_list_examples(arguments: Dict[str, Any]) -> List:
    """Handle listing examples."""
    result = {
        "status": "success",
        "examples": EXAMPLES,
        "count": len(EXAMPLES)
    }
    
    if MCP_AVAILABLE:
        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
    else:
        return [{"type": "text", "text": json.dumps(result, indent=2)}]


async def handle_get_compiler_status(arguments: Dict[str, Any]) -> List:
    """Handle compiler status retrieval."""
    result = {
        "status": "success",
        "compiler_stats": {
            "compile_count": _COMPILER_STATS.compile_count,
            "compile_failures": _COMPILER_STATS.compile_failures,
            "compile_successes": _COMPILER_STATS.compile_successes,
            "success_rate": (
                _COMPILER_STATS.compile_successes / _COMPILER_STATS.compile_count
                if _COMPILER_STATS.compile_count > 0 else 0
            )
        },
        "compiler_in_use": COMPILE_LOCK.locked(),
        "settings": {
            "volume_mapped_src": str(VOLUME_MAPPED_SRC),
            "volume_mapped_src_exists": VOLUME_MAPPED_SRC.exists(),
            "output_dir": str(OUTPUT_DIR),
        }
    }
    
    if MCP_AVAILABLE:
        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
    else:
        return [{"type": "text", "text": json.dumps(result, indent=2)}]


async def main():
    """Main entry point for the MCP server."""
    if not MCP_AVAILABLE:
        print("ERROR: MCP package not available.")
        print("Install it with: uv add mcp")
        return
    
    logger.info("Starting FastLED WASM MCP Server...")
    
    server = create_mcp_server()
    
    # Run the server using stdio transport
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())