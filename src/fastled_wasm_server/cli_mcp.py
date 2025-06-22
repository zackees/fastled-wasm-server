#!/usr/bin/env python3
"""
CLI entry point for the FastLED WASM MCP Server.

This provides a command-line interface to start the MCP server that allows
AI assistants to interact with the FastLED WASM compilation service.
"""

import sys

from fastled_wasm_server.print_banner import _print_banner


def main() -> None:
    """Main entry point for the MCP server CLI."""
    _print_banner("FastLED WASM MCP Server")
    print("=" * 50)

    try:
        from fastled_wasm_server.mcp_server import MCP_AVAILABLE
        from fastled_wasm_server.mcp_server import main as mcp_main

        if not MCP_AVAILABLE:
            print("ERROR: MCP package not installed.")
            print()
            print("To install the required dependencies:")
            print("  uv add mcp")
            print()
            print("Then run the server with:")
            print("  uv run fastled-wasm-mcp-server")
            sys.exit(1)

        print("Starting MCP server...")
        print("This server provides AI assistants with tools to:")
        print("  - Compile Arduino/FastLED sketches to WASM")
        print("  - Fetch and list FastLED examples")
        print("  - Get compiler status and statistics")
        print()
        print("Server will communicate via stdio...")

        # Import asyncio here to avoid issues if not needed
        import asyncio

        asyncio.run(mcp_main())

    except KeyboardInterrupt:
        print("\nShutting down MCP server...")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting MCP server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
