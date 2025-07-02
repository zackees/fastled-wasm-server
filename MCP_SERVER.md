# FastLED WASM MCP Server

This document describes the Model Context Protocol (MCP) server for the FastLED WASM compilation service.

## Overview

The MCP server provides AI assistants with tools to interact with the FastLED WASM compilation service, allowing them to:

- Compile Arduino/FastLED sketches to WASM
- Fetch and list available FastLED examples
- Get compiler status and statistics
- Access server configuration information

## Setup

### 1. Install Dependencies

First, ensure you have the FastLED WASM server dependencies installed:

```bash
./install  # Sets up uv venv and installs dependencies
source activate  # Activate the virtual environment
```

### 2. Install MCP Package

Add the MCP dependency to the project:

```bash
uv add mcp
```

### 3. Run the MCP Server

Start the MCP server using any of these methods:

**Option 1 - Using the project script:**
```bash
uv run fastled-wasm-mcp-server
```

**Option 2 - Run directly from the project root:**
```bash
uv run python mcp_server.py
```

**Option 3 - Via the CLI module:**
```bash
uv run python -m fastled_wasm_server.cli_mcp
```

**Note:** All methods require running with `uv run` to ensure proper dependency resolution and module path handling.

## Tools Provided

### compile_sketch

Compiles an Arduino/FastLED sketch to WASM.

**Parameters:**
- `sketch_content` (required): The Arduino sketch code to compile
- `build_mode` (optional): Build mode - "quick" (default), "release", or "debug"
- `filename` (optional): Name for the sketch file (default: "sketch.ino")

**Example:**
```json
{
  "sketch_content": "#include <FastLED.h>\n\nvoid setup() {\n  // Your setup code\n}\n\nvoid loop() {\n  // Your loop code\n}",
  "build_mode": "quick",
  "filename": "my_sketch.ino"
}
```

### get_example

Fetches information about a specific FastLED example.

**Parameters:**
- `example_name` (required): Name of the example to fetch

### list_examples

Lists all available FastLED examples.

**Parameters:** None

### get_compiler_status

Gets current compiler status and statistics.

**Parameters:** None

## Resources Provided

### fastled://examples

Returns a JSON list of available FastLED example sketches.

### fastled://compiler/stats

Returns compiler usage statistics including:
- Total compilation count
- Success/failure counts
- Current compiler status

### fastled://server/settings

Returns server configuration information including:
- Source directory paths
- Output directory
- Server settings

## Development

### Project Structure

- `mcp_server.py` - Main MCP server implementation (in project root)
- `src/fastled_wasm_server/cli_mcp.py` - CLI entry point
- The MCP server reuses the existing FastLED WASM compiler infrastructure

### Testing

You can test the MCP server by running:

```bash
# Run tests
./test

# Or run specific tests if available
uv run pytest tests/ -v
```

### Integration with AI Assistants

The MCP server communicates via stdio and follows the Model Context Protocol specification. AI assistants that support MCP can connect to this server to access FastLED compilation capabilities.

## Troubleshooting

### MCP Package Not Found

If you see "MCP package not installed" errors:

```bash
uv add mcp
```

### Compilation Errors

- Ensure you're running in the `niteris/fastled-wasm` container environment
- Check that all dependencies are installed with `./install`
- Verify the sketch code is valid Arduino/FastLED syntax

### Server Issues

- Check that the FastLED WASM compiler is properly installed
- Ensure proper permissions for temporary file creation
- Verify network connectivity if using remote resources

## Environment Variables

The MCP server respects the same environment variables as the main FastLED WASM server:

- `DISABLE_AUTO_CLEAN`: Disable automatic cleanup
- `NO_SKETCH_CACHE`: Disable sketch caching
- `MEMORY_LIMIT_MB`: Set memory limit

## Notes

- The MCP server currently uses a simplified configuration without full caching support
- Background tasks are handled synchronously in the MCP context
- The server is designed to work within the existing FastLED WASM server architecture