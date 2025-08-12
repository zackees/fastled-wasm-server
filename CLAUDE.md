# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Setup
```bash
./install  # Sets up uv venv with Python 3.11 and installs dependencies
source activate  # Activates the virtual environment
```

### Linting
```bash
./lint  # Runs ruff, black, isort, and pyright on src and tests
```

### Testing
```bash
./test  # Runs pytest with -n auto for parallel execution
```

### Cleanup
```bash
./clean  # Removes build artifacts, caches, and virtual environments
```

### Package Commands
```bash
fastled-wasm-server      # Main CLI entry point (compile server)
fastled-wasm-mcp-server  # MCP server entry point
```

## Architecture Overview

### Core Components

**FastLED WASM Server**: A FastAPI-based compilation server that compiles Arduino/FastLED sketches to WebAssembly. The server runs in the `niteris/fastled-wasm` container environment and provides both REST API and MCP (Model Context Protocol) interfaces.

**Compilation Pipeline**: 
- Uses `fastled-wasm-compiler` library for the actual compilation
- Supports multiple build modes: `quick` (default), `debug`, `release`
- Handles both file uploads and direct content compilation
- Implements session management and compile locking for concurrent safety

**Server Structure**:
- `server.py`: Main FastAPI application with endpoints for compilation, project initialization, and server management
- `server_compile.py`: Core compilation logic and file handling
- `api_client.py`: Async and sync client implementations for interacting with the server
- `session_manager.py`: Manages compilation sessions and tracking

**MCP Integration**: 
- `mcp_server.py`: Model Context Protocol server for AI assistant integration
- `cli_mcp.py`: CLI entry point for MCP server
- Provides tools for sketch compilation, example fetching, and server status

### Key Paths and Configuration

**Environment Requirements**: Must run in `niteris/fastled-wasm` container with proper FastLED source mapping.

**Volume Mapping**: 
- `VOLUME_MAPPED_SRC`: Points to FastLED source directory for library compilation
- `OUTPUT_DIR`: Temporary directory for compilation outputs
- `UPLOAD_DIR`: Directory for uploaded sketch files

**Build Configuration**:
- Uses `uv` for Python dependency management with Python 3.11
- Supports Windows development through git-bash
- Configurable memory limits and upload size restrictions

### Testing and Quality

- Uses `pytest` with async support and parallel execution
- Type checking with `pyright`
- Code formatting with `black` and `isort`
- Linting with `ruff`
- All linting tools configured in `pyproject.toml`

### Security and Authentication

- Protected endpoints use `_AUTH_TOKEN` for bot protection
- File upload size limits configurable via `_UPLOAD_LIMIT`
- Optional server shutdown endpoint controlled by `ALLOW_SHUTDOWN` environment variable