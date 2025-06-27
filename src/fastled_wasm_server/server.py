import json
import os
import time
import warnings
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from disklru import DiskLRUCache
from fastapi import (
    BackgroundTasks,
    Body,
    FastAPI,
    File,
    Header,
    HTTPException,
    UploadFile,
)
from fastapi.responses import (
    FileResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from fastled_wasm_compiler import Compiler
from fastled_wasm_compiler.dwarf_path_to_file_path import (
    dwarf_path_to_file_path,
)
from pydantic import BaseModel

from fastled_wasm_server.compile_lock import COMPILE_LOCK
from fastled_wasm_server.examples import EXAMPLES
from fastled_wasm_server.paths import (  # The folder where the actual source code is located.; FASTLED_SRC,
    COMPILER_ROOT,
    OUTPUT_DIR,
    SKETCH_CACHE_FILE,
    UPLOAD_DIR,
    VOLUME_MAPPED_SRC,
)
from fastled_wasm_server.server_compile import ServerWasmCompiler
from fastled_wasm_server.server_fetch_example import (
    fetch_example,
)
from fastled_wasm_server.server_misc import start_memory_watchdog
from fastled_wasm_server.types import CompilerStats
from fastled_wasm_server.upload_size_middleware import UploadSizeMiddleware

_COMPILER_STATS = CompilerStats()

_TEST = False
_UPLOAD_LIMIT = 10 * 1024 * 1024
_MEMORY_LIMIT_MB = int(os.environ.get("MEMORY_LIMIT_MB", "0"))  # 0 means disabled

# Protect the endpoints from random bots.
# Note that that the wasm_compiler.py greps for this string to get the URL of the server.
# Changing the name could break the compiler.
_AUTH_TOKEN = "oBOT5jbsO4ztgrpNsQwlmFLIKB"

_LIVE_GIT_UPDATES_INTERVAL = int(
    os.environ.get("LIVE_GIT_UPDATE_INTERVAL", 60 * 60 * 24)
)  # Update every 24 hours
_ALLOW_SHUTDOWN = os.environ.get("ALLOW_SHUTDOWN", "false").lower() in ["true", "1"]
_NO_SKETCH_CACHE = os.environ.get("NO_SKETCH_CACHE", "false").lower() in ["true", "1"]

# debug is a 20mb payload for the symbol information.
_ONLY_QUICK_BUILDS = os.environ.get("ONLY_QUICK_BUILDS", "false").lower() in [
    "true",
    "1",
]

_ALLOW_CODE_SYNC = False

# _FASTLED_SRC = Path("/git/fastled/src")

_LIVE_GIT_UPDATES_ENABLED = False


if _NO_SKETCH_CACHE:
    print("Sketch caching disabled")


UPLOAD_DIR.mkdir(exist_ok=True)
START_TIME = time.time()


OUTPUT_DIR.mkdir(exist_ok=True)

# Initialize disk cache
SKETCH_CACHE_MAX_ENTRIES = 50
SKETCH_CACHE = DiskLRUCache(str(SKETCH_CACHE_FILE), SKETCH_CACHE_MAX_ENTRIES)

# New compiler type that will replace the legacy ones.
_NEW_COMPILER = Compiler(
    volume_mapped_src=VOLUME_MAPPED_SRC,
)

_COMPILER = ServerWasmCompiler(
    compiler_root=COMPILER_ROOT,
    sketch_cache=SKETCH_CACHE,
    compiler=_NEW_COMPILER,
    only_quick_builds=_ONLY_QUICK_BUILDS,
    compiler_lock=COMPILE_LOCK,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting FastLED wasm compiler server...")
    try:
        print(f"Settings: {json.dumps(get_settings(), indent=2)}")
    except Exception as e:
        print(f"Error getting settings: {e}")

    if _MEMORY_LIMIT_MB > 0:
        print(f"Starting memory watchdog (limit: {_MEMORY_LIMIT_MB}MB)")
        start_memory_watchdog(_MEMORY_LIMIT_MB)

    if _ALLOW_CODE_SYNC:
        # if VOLUME_MAPPED_SRC.exists():
        #     _NEW_COMPILER.update_src(src_to_merge_from=VOLUME_MAPPED_SRC)
        print("Code sync disabled, skipping code sync")
    else:
        print("Code sync disabled")

    yield  # end startup
    return  # end shutdown


app = FastAPI(lifespan=lifespan)

app.add_middleware(UploadSizeMiddleware, max_upload_size=_UPLOAD_LIMIT)


def try_get_cached_zip(hash: str) -> bytes | None:
    if _NO_SKETCH_CACHE:
        print("Sketch caching disabled, skipping cache get")
        return None
    return SKETCH_CACHE.get_bytes(hash)


def cache_put(hash: str, data: bytes) -> None:
    if _NO_SKETCH_CACHE:
        print("Sketch caching disabled, skipping cache put")
        return
    SKETCH_CACHE.put_bytes(hash, data)


def get_settings() -> dict:
    settings = {
        "ALLOW_SHUTDOWN": _ALLOW_SHUTDOWN,
        "NO_AUTO_UPDATE": os.environ.get("NO_AUTO_UPDATE", "0"),
        "NO_SKETCH_CACHE": _NO_SKETCH_CACHE,
        "LIVE_GIT_UPDATES_ENABLED": _LIVE_GIT_UPDATES_ENABLED,
        "LIVE_GIT_UPDATES_INTERVAL": _LIVE_GIT_UPDATES_INTERVAL,
        "UPLOAD_LIMIT": _UPLOAD_LIMIT,
        "VOLUME_MAPPED_SRC": str(VOLUME_MAPPED_SRC),
        "VOLUME_MAPPED_SRC_EXISTS": VOLUME_MAPPED_SRC.exists(),
        "ONLY_QUICK_BUILDS": _ONLY_QUICK_BUILDS,
    }
    return settings


@app.get("/", include_in_schema=False)
async def read_root() -> RedirectResponse:
    """Redirect to the /docs endpoint."""

    print("Endpoint accessed: / (root redirect to docs)")
    return RedirectResponse(url="/docs")


@app.get("/healthz")
async def healthz() -> dict:
    """Health check endpoint."""
    print("Endpoint accessed: /healthz")
    return {"status": "ok"}


if _ALLOW_SHUTDOWN:

    @app.get("/shutdown")
    async def shutdown() -> dict:
        """Shutdown the server."""
        print("Endpoint accessed: /shutdown")
        print("Shutting down server...")
        SKETCH_CACHE.close()
        os._exit(0)
        return {"status": "ok"}


@app.get("/settings")
async def settings() -> dict:
    """Get the current settings."""
    print("Endpoint accessed: /settings")
    settings = {
        "ALLOW_SHUTDOWN": _ALLOW_SHUTDOWN,
        "NO_AUTO_UPDATE": os.environ.get("NO_AUTO_UPDATE", "0"),
        "NO_SKETCH_CACHE": _NO_SKETCH_CACHE,
        "LIVE_GIT_UPDATES_ENABLED": _LIVE_GIT_UPDATES_ENABLED,
        "LIVE_GIT_UPDATES_INTERVAL": _LIVE_GIT_UPDATES_INTERVAL,
        "UPLOAD_LIMIT": _UPLOAD_LIMIT,
        "VOLUME_MAPPED_SRC": str(VOLUME_MAPPED_SRC),
        "VOLUME_MAPPED_SRC_EXISTS": VOLUME_MAPPED_SRC.exists(),
    }
    return settings


@app.get("/compile/wasm/inuse")
async def compiler_in_use() -> dict:
    """Check if the compiler is in use."""
    print("Endpoint accessed: /compile/wasm/inuse")
    return {"in_use": COMPILE_LOCK.locked()}


@app.get("/project/init")
def project_init(background_tasks: BackgroundTasks) -> FileResponse:
    """Archive /git/fastled/examples/wasm into a zip file and return it."""
    print("Endpoint accessed: /project/init")
    response: FileResponse = fetch_example(background_tasks=background_tasks)
    return response


@app.post("/project/init")
def project_init_example(
    background_tasks: BackgroundTasks, example: str = Body(...)
) -> FileResponse:
    """Archive /git/fastled/examples/{example} into a zip file and return it."""
    print(f"Endpoint accessed: /project/init/example with example: {example}")
    out: FileResponse = fetch_example(
        background_tasks=background_tasks, example=example
    )
    return out


class DwarfSourceRequest(BaseModel):
    """Request model for dwarf source file retrieval."""

    path: str


@app.post("/dwarfsource")
def dwarfsource(request: DwarfSourceRequest) -> Response:
    """File serving for step through debugging."""
    path_or_err: Path | Exception = dwarf_path_to_file_path(
        f"{request.path}",
    )
    if isinstance(path_or_err, Exception):
        return Response(
            content=f"Could not resolve {request.path}: {path_or_err}",
            media_type="text/plain",
            status_code=400,
        )
    if not path_or_err.exists():
        return Response(
            content="File not found.",
            media_type="text/plain",
            status_code=404,
        )
    out: FileResponse = FileResponse(
        path_or_err,
        media_type="text/plain",
        filename=path_or_err.name,
        headers={"Cache-Control": "no-cache"},
    )
    return out


@app.get("/info")
def info_examples() -> dict:
    """Get a list of examples."""
    print("Endpoint accessed: /info")
    uptime = time.time() - START_TIME
    uptime_fmtd = time.strftime("%H:%M:%S", time.gmtime(uptime))
    try:
        build_timestamp = (
            Path("/image_timestamp.txt").read_text(encoding="utf-8").strip()
        )
    except Exception as e:
        warnings.warn(f"Error reading build timestamp: {e}")
        build_timestamp = "unknown"
    fastled_version = os.environ.get("FASTLED_VERSION", "unknown")
    available_builds: list[str] = [
        "quick",
    ]
    if not _ONLY_QUICK_BUILDS:
        available_builds += ["release", "debug"]
    out = {
        "examples": EXAMPLES,
        "compile_count": _COMPILER_STATS.compile_count,
        "compile_failures": _COMPILER_STATS.compile_failures,
        "compile_successes": _COMPILER_STATS.compile_successes,
        "uptime": uptime_fmtd,
        "build_timestamp": build_timestamp,
        "fastled_version": fastled_version,
        "available_builds": available_builds,
    }
    return out


# THIS MUST NOT BE ASYNC!!!!
@app.post("/compile/wasm")
def compile_wasm(
    file: UploadFile = File(...),
    authorization: str = Header(None),
    build: str = Header(None),
    profile: str = Header(None),
    strict: bool = Header(False),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> FileResponse:
    """Upload a file into a temporary directory."""

    if not _TEST and authorization != _AUTH_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    print(
        f"Endpoint accessed: /compile/wasm with file: {file.filename}, and build: {build}, profile: {profile}"
    )

    file_response = _COMPILER.compile(
        file=file,
        build=build,
        profile=profile,
        output_dir=OUTPUT_DIR,
        use_sketch_cache=not _NO_SKETCH_CACHE,
        background_tasks=background_tasks,
        strict=strict,
    )
    return file_response


@app.post("/compile/libfastled")
async def compile_libfastled(
    authorization: str = Header(None),
    build: str = Header(None),
    dry_run: bool = Header(False),
) -> StreamingResponse:
    """Compile libfastled library and stream the compilation output."""

    if not _TEST and authorization != _AUTH_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    print(
        f"Endpoint accessed: /compile/libfastled with build: {build}, dry_run: {dry_run}"
    )

    async def stream_compilation() -> AsyncGenerator[bytes, None]:
        """Stream the compilation output line by line."""
        try:
            # Import the compile function from our internal module
            from fastled_wasm_server.compile import compile_libfastled
            from fastled_wasm_server.types import BuildMode

            # Convert build mode
            if build:
                build_mode_str = build.upper()
                if build_mode_str not in ["QUICK", "DEBUG", "RELEASE"]:
                    build_mode_str = "QUICK"  # Default fallback
            else:
                build_mode_str = "QUICK"  # Default

            # Convert to BuildMode enum
            if build_mode_str == "DEBUG":
                build_mode = BuildMode.DEBUG
            elif build_mode_str == "RELEASE":
                build_mode = BuildMode.RELEASE
            else:
                build_mode = BuildMode.QUICK

            yield f"data: Using BUILD_MODE: {build_mode.name}\n".encode()
            if dry_run:
                yield "data: DRY RUN MODE: Will skip actual compilation\n".encode()

            # Use the dedicated compile_libfastled function
            yield "data: Starting libfastled compilation...\n".encode()

            # Run the compilation in a thread to avoid blocking
            import asyncio
            import threading
            from queue import Queue

            output_queue = Queue()
            exception_queue = Queue()

            def run_compile():
                try:
                    # Capture stdout to stream it
                    import sys

                    # Create a custom stdout capture
                    old_stdout = sys.stdout

                    class TeeOutput:
                        def write(self, text):
                            old_stdout.write(text)
                            old_stdout.flush()
                            output_queue.put(text)

                        def flush(self):
                            old_stdout.flush()

                    sys.stdout = TeeOutput()

                    try:
                        # Call the dedicated libfastled compile function
                        result = compile_libfastled(
                            compiler_root=COMPILER_ROOT,
                            build_mode=build_mode,
                            dry_run=dry_run,
                        )
                        output_queue.put(f"COMPILATION_RESULT:{result}")
                    finally:
                        sys.stdout = old_stdout

                except Exception as e:
                    exception_queue.put(e)
                finally:
                    output_queue.put("COMPILATION_FINISHED")

            # Start compilation in background thread
            compile_thread = threading.Thread(target=run_compile)
            compile_thread.start()

            # Stream output as it comes in
            while True:
                try:
                    # Check for exceptions
                    if not exception_queue.empty():
                        exc = exception_queue.get_nowait()
                        yield f"data: ERROR: {str(exc)}\n".encode()
                        break

                    # Get output with timeout
                    try:
                        output = output_queue.get(timeout=0.1)

                        if output == "COMPILATION_FINISHED":
                            break
                        elif output.startswith("COMPILATION_RESULT:"):
                            result = output.split(":", 1)[1]
                            if result == "0":
                                yield "data: COMPILATION_COMPLETE\ndata: EXIT_CODE: 0\ndata: STATUS: SUCCESS\n".encode()
                            else:
                                yield f"data: COMPILATION_COMPLETE\ndata: EXIT_CODE: {result}\ndata: STATUS: FAIL\n".encode()
                        else:
                            # Stream the output line
                            yield f"data: {output}".encode()

                    except Exception:
                        # Timeout - yield a heartbeat and continue
                        await asyncio.sleep(0.1)
                        continue

                except Exception as e:
                    yield f"data: ERROR: {str(e)}\n".encode()
                    break

            # Wait for thread to complete
            compile_thread.join(timeout=5)

        except Exception as e:
            error_message = f"data: ERROR: {str(e)}\ndata: COMPILATION_COMPLETE\ndata: EXIT_CODE: -1\ndata: STATUS: FAIL\n"
            yield error_message.encode()

    return StreamingResponse(
        stream_compilation(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
