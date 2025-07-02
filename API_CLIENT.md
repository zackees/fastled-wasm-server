# FastLED WASM Server API Client

This document describes the HTTP API client for the FastLED WASM Server. The client provides both asynchronous and synchronous interfaces for interacting with all server endpoints.

## Installation

The API client is included with the `fastled-wasm-server` package:

```bash
pip install fastled-wasm-server
```

## Quick Start

### Async Client (Recommended)

```python
import asyncio
from fastled_wasm_server import FastLEDWasmClient

async def main():
    async with FastLEDWasmClient("http://localhost:8080") as client:
        # Health check
        health = await client.health_check()
        print(f"Server status: {health.status}")
        
        # Get server info
        info = await client.get_info()
        print(f"Available examples: {info.examples}")
        
        # Compile WASM from file content
        sketch_content = """
        #include <FastLED.h>
        
        #define NUM_LEDS 60
        #define DATA_PIN 6
        
        CRGB leds[NUM_LEDS];
        
        void setup() {
            FastLED.addLeds<WS2812, DATA_PIN, GRB>(leds, NUM_LEDS);
        }
        
        void loop() {
            fill_rainbow(leds, NUM_LEDS, 0, 7);
            FastLED.show();
            delay(100);
        }
        """.encode('utf-8')
        
        wasm_result = await client.compile_wasm_with_file_content(
            file_content=sketch_content,
            filename="rainbow.ino",
            build="quick"
        )
        
        print(f"Compiled WASM size: {len(wasm_result)} bytes")

# Run the async function
asyncio.run(main())
```

### Sync Client

```python
from fastled_wasm_server import FastLEDWasmSyncClient

# Create sync client
client = FastLEDWasmSyncClient("http://localhost:8080")

# Health check
health = client.health_check()
print(f"Server status: {health.status}")

# Get server info
info = client.get_info()
print(f"Available examples: {info.examples}")
```

## API Reference

### Client Initialization

#### FastLEDWasmClient (Async)

```python
client = FastLEDWasmClient(
    base_url="http://localhost:8080",           # Server URL
    auth_token="oBOT5jbsO4ztgrpNsQwlmFLIKB",   # Auth token (default provided)
    timeout=30.0,                               # Request timeout in seconds
    **httpx_kwargs                              # Additional httpx.AsyncClient options
)
```

#### FastLEDWasmSyncClient (Sync)

```python
client = FastLEDWasmSyncClient(
    base_url="http://localhost:8080",           # Server URL
    auth_token="oBOT5jbsO4ztgrpNsQwlmFLIKB",   # Auth token (default provided)
    timeout=30.0,                               # Request timeout in seconds
    **httpx_kwargs                              # Additional httpx.AsyncClient options
)
```

### Server Status and Information

#### Health Check

```python
# Async
health = await client.health_check()
print(f"Status: {health.status}")

# Sync
health = client.health_check()
print(f"Status: {health.status}")
```

#### Get Server Settings

```python
# Async
settings = await client.get_settings()
print(f"Upload limit: {settings.UPLOAD_LIMIT}")
print(f"Cache enabled: {not settings.NO_SKETCH_CACHE}")

# Sync
settings = client.get_settings()
```

#### Get Server Information

```python
# Async
info = await client.get_info()
print(f"Examples: {info.examples}")
print(f"Available builds: {info.available_builds}")
print(f"Uptime: {info.uptime}")
print(f"FastLED version: {info.fastled_version}")

# Sync
info = client.get_info()
```

#### Check Compiler Status

```python
# Async
status = await client.is_compiler_in_use()
print(f"Compiler in use: {status.in_use}")

# Sync
status = client.is_compiler_in_use()
```

### Project Management

#### Initialize Project

```python
# Initialize with default example
# Async
project_zip = await client.init_project()
# Sync
project_zip = client.init_project()

# Initialize with specific example
# Async
project_zip = await client.init_project(example="DemoReel100")
# Sync
project_zip = client.init_project(example="DemoReel100")

# Save the project
with open("fastled_project.zip", "wb") as f:
    f.write(project_zip)
```

### WASM Compilation

#### Compile from File

```python
# Async
wasm_bytes = await client.compile_wasm(
    file_path="path/to/sketch.ino",
    build="quick",                    # "quick", "debug", or "release"
    profile=None,                     # Optional profile setting
    strict=False,                     # Enable strict compilation
    no_platformio=None,               # Disable PlatformIO (None = auto)
    native=None,                      # Enable native compilation (None = auto)
    session_id=None                   # Optional session tracking
)

# Sync
wasm_bytes = client.compile_wasm(
    file_path="path/to/sketch.ino",
    build="quick"
)
```

#### Compile from File Content

```python
# Read your sketch
with open("sketch.ino", "rb") as f:
    sketch_content = f.read()

# Async
wasm_bytes = await client.compile_wasm_with_file_content(
    file_content=sketch_content,
    filename="sketch.ino",
    build="quick"
)

# Sync
wasm_bytes = client.compile_wasm_with_file_content(
    file_content=sketch_content,
    filename="sketch.ino",
    build="quick"
)

# Save compiled WASM
with open("output.wasm", "wb") as f:
    f.write(wasm_bytes)
```

### Library Compilation

#### Compile libfastled (Streaming)

```python
# This method streams compilation output in real-time
# Only available for async client
async for output_line in client.compile_libfastled(build="quick", dry_run=False):
    print(f"Compilation: {output_line.strip()}")
```

### Debugging Support

#### Get Source File for Debugging

```python
# Async
source_content = await client.get_dwarf_source("/path/in/dwarf/symbols")
print(source_content)

# Sync
source_content = client.get_dwarf_source("/path/in/dwarf/symbols")
```

### Server Management

#### Shutdown Server (if allowed)

```python
# Async
result = await client.shutdown_server()
print(f"Shutdown result: {result}")

# Sync
result = client.shutdown_server()
```

## Response Models

The client uses Pydantic models for type-safe responses:

### HealthResponse
```python
class HealthResponse(BaseModel):
    status: str
```

### ServerSettings
```python
class ServerSettings(BaseModel):
    ALLOW_SHUTDOWN: bool
    NO_AUTO_UPDATE: str
    NO_SKETCH_CACHE: bool
    LIVE_GIT_UPDATES_ENABLED: bool
    LIVE_GIT_UPDATES_INTERVAL: int
    UPLOAD_LIMIT: int
    VOLUME_MAPPED_SRC: str
    VOLUME_MAPPED_SRC_EXISTS: bool
    ONLY_QUICK_BUILDS: Optional[bool] = None
```

### ServerInfo
```python
class ServerInfo(BaseModel):
    examples: List[str]
    compile_count: int
    compile_failures: int
    compile_successes: int
    uptime: str
    build_timestamp: str
    fastled_version: str
    available_builds: List[str]
```

### CompilerInUseResponse
```python
class CompilerInUseResponse(BaseModel):
    in_use: bool
```

## Error Handling

The client raises `httpx.HTTPStatusError` for HTTP errors:

```python
import httpx

try:
    async with FastLEDWasmClient("http://localhost:8080") as client:
        result = await client.compile_wasm("nonexistent.ino")
except httpx.HTTPStatusError as e:
    print(f"HTTP error: {e.response.status_code}")
    print(f"Response: {e.response.text}")
except Exception as e:
    print(f"Other error: {e}")
```

## Build Types

The server supports different build types:

- **`"quick"`**: Fast compilation with minimal optimizations
- **`"debug"`**: Debug build with symbols (may not be available on all servers)
- **`"release"`**: Optimized release build (may not be available on all servers)

Check `info.available_builds` to see what build types are supported by your server.

## Advanced Usage

### Custom HTTP Client Options

```python
import httpx

# Custom httpx client configuration
client = FastLEDWasmClient(
    "http://localhost:8080",
    timeout=60.0,
    # Custom httpx options
    limits=httpx.Limits(max_connections=10),
    verify=False  # Disable SSL verification (not recommended for production)
)
```

### Session Management

Some endpoints support session tracking:

```python
session_id = 12345
wasm_bytes = await client.compile_wasm(
    file_path="sketch.ino",
    session_id=session_id
)
# The response will include session information in headers
```

### Concurrent Requests

The async client supports concurrent requests:

```python
import asyncio

async def compile_multiple():
    async with FastLEDWasmClient("http://localhost:8080") as client:
        tasks = [
            client.compile_wasm_with_file_content(sketch1, "sketch1.ino"),
            client.compile_wasm_with_file_content(sketch2, "sketch2.ino"),
            client.compile_wasm_with_file_content(sketch3, "sketch3.ino"),
        ]
        results = await asyncio.gather(*tasks)
        return results
```

## Complete Example

See `examples/api_client_example.py` for a complete working example that demonstrates all client features.

## Testing

The API client includes comprehensive tests. Run them with:

```bash
pytest tests/test_api_client.py
```

## Dependencies

The API client requires:

- `httpx>=0.25.0` - Modern HTTP client
- `pydantic` - Data validation (included with FastAPI)
- `asyncio` - Async support (built into Python 3.7+)