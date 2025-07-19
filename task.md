# Remove Sketch Cache Feature

## Overview

Remove the sketch cache functionality from the FastLED WASM server. The build process is now fast enough that caching is no longer needed, and this feature adds unnecessary complexity.

## Background

The sketch cache is a disk-based LRU cache that stores compiled sketch results to avoid recompilation of identical sketches. It uses the `disklru` package and includes:

- `DiskLRUCache` instance with cache file at `OUTPUT_DIR / "compile_cache.db"`
- Environment variable `NO_SKETCH_CACHE` to disable caching
- Cache get/put functions and integration throughout the compilation pipeline
- CLI options and API settings related to caching

## Task List

### 1. Remove Dependencies
- [ ] Remove `disklru>=2.0.4` from `pyproject.toml`
- [ ] Remove `from disklru import DiskLRUCache` imports

### 2. Remove Path Configuration  
- [ ] Remove `SKETCH_CACHE_FILE = OUTPUT_DIR / "compile_cache.db"` from `paths.py`
- [ ] Remove `SKETCH_CACHE_FILE` from imports in other files

### 3. Clean Server Logic (`server.py`)
- [ ] Remove `DiskLRUCache` import
- [ ] Remove `_NO_SKETCH_CACHE` environment variable handling
- [ ] Remove `SKETCH_CACHE_MAX_ENTRIES` and `SKETCH_CACHE` instance
- [ ] Remove `try_get_cached_zip()` function
- [ ] Remove `cache_put()` function  
- [ ] Remove cache-related code in `get_settings()`
- [ ] Remove `SKETCH_CACHE.close()` in shutdown endpoint
- [ ] Remove `use_sketch_cache=not _NO_SKETCH_CACHE` parameter in `compile_wasm()`
- [ ] Remove cache clearing code in `compile_libfastled()` endpoint

### 4. Simplify Compilation (`server_compile.py`)
- [ ] Remove `DiskLRUCache` import
- [ ] Remove `try_get_cached_zip()` function
- [ ] Remove `cache_put()` function
- [ ] Remove `sketch_cache: DiskLRUCache` parameter from `_compile_source()`
- [ ] Remove `use_sketch_cache: bool` parameter from `_compile_source()`
- [ ] Remove cache checking logic in `_compile_source()`
- [ ] Remove cache storage logic in `_compile_source()`
- [ ] Remove `sketch_cache` from `ServerWasmCompiler` class
- [ ] Remove cache-related parameters from `compile()` method

### 5. Update MCP Server (`mcp_server.py`)
- [ ] Remove `DiskLRUCache` import
- [ ] Remove `_SKETCH_CACHE` instance creation
- [ ] Update `ServerWasmCompiler` initialization to not use cache
- [ ] Remove `use_sketch_cache=False` parameter in compilation

### 6. Remove CLI Options (`cli_server.py`)
- [ ] Remove `no_sketch_cache: bool` field from `Args` dataclass
- [ ] Remove `--no-sketch-cache` argument from argument parser
- [ ] Remove `NO_SKETCH_CACHE` environment variable handling in `run_server()`

### 7. Update API Client (`api_client.py`)
- [ ] Remove `NO_SKETCH_CACHE: bool` field from settings models
- [ ] Update any client code that references this field

### 8. Update Tests
- [ ] Remove cache-related assertions from `test_compile_libfastled.py`
- [ ] Update any other tests that reference sketch cache functionality
- [ ] Remove `NO_SKETCH_CACHE=False` from test configurations

### 9. Update Documentation
- [ ] Remove cache-related sections from `MCP_SERVER.md`
- [ ] Remove cache references from `.curserrules` file
- [ ] Update any other documentation that mentions caching

### 10. Clean Examples
- [ ] Remove cache-related code from `api_client_example.py`
- [ ] Update any other example files that reference caching

## Implementation Notes

### Files to Modify
- `pyproject.toml` - Remove disklru dependency
- `src/fastled_wasm_server/paths.py` - Remove SKETCH_CACHE_FILE
- `src/fastled_wasm_server/server.py` - Major cache removal
- `src/fastled_wasm_server/server_compile.py` - Remove cache logic
- `src/fastled_wasm_server/mcp_server.py` - Remove cache instance
- `src/fastled_wasm_server/cli_server.py` - Remove CLI options
- `src/fastled_wasm_server/api_client.py` - Remove cache fields
- `tests/test_compile_libfastled.py` - Update test assertions
- `tests/test_api_client.py` - Remove cache references
- `MCP_SERVER.md` - Update documentation
- `examples/api_client_example.py` - Remove cache code

### Key Principles
1. **Minimal Changes**: Remove only caching functionality, preserve all other features
2. **Clean Removal**: Don't leave any dead code or unused imports
3. **Maintain Compatibility**: Ensure the API still works without cache parameters
4. **Update Tests**: Make sure all tests pass after cache removal
5. **Documentation**: Keep docs up to date with the changes

### Verification Steps
- [ ] Run `bash test` to ensure all tests pass
- [ ] Verify server starts without errors
- [ ] Test compilation endpoints work correctly
- [ ] Confirm no dead imports or unused variables remain
- [ ] Check that API clients can still interact with the server

## Success Criteria

- All sketch cache functionality removed
- No `disklru` dependency in the project
- All tests passing
- Server compiles sketches without any caching logic
- Clean, maintainable codebase with no cache-related complexity


