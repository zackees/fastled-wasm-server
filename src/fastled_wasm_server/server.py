import json
import os
import time
import warnings
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Optional

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
from fastled_wasm_compiler.compiler import UpdateSrcResult
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
from fastled_wasm_server.session_manager import SessionManager
from fastled_wasm_server.types import CompilerStats
from fastled_wasm_server.upload_size_middleware import UploadSizeMiddleware

_COMPILER_STATS = CompilerStats()
_SESSION_MANAGER = SessionManager()

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


async def update_src_async(
    compiler: Compiler, builds: list[str], src_to_merge_from: Path
) -> AsyncGenerator[str, None]:
    """
    Async generator for compiler.update_src() that yields progress updates.

    Args:
        compiler: The compiler instance
        builds: List of build types
        src_to_merge_from: Source directory to merge from

    Yields:
        str: Progress update messages

    Returns:
        None: On successful completion

    Raises:
        Exception: If the source update fails
    """
    import asyncio

    yield "Starting source update check..."

    loop = asyncio.get_event_loop()
    try:
        yield f"Checking for FastLED source file changes from {src_to_merge_from}..."

        # Run the potentially blocking update_src call in a thread executor
        update_src_result: UpdateSrcResult | Exception = await loop.run_in_executor(
            None,
            lambda: compiler.update_src(
                builds=builds, src_to_merge_from=src_to_merge_from
            ),
        )

        if isinstance(update_src_result, Exception):
            yield f"Error during source update: {update_src_result}"
            raise update_src_result

        files_changed = update_src_result.files_changed
        if files_changed:
            yield f"Source update result: {update_src_result.stdout}"
            yield f"Found {len(files_changed)} changed files:"
            for file_path in files_changed:
                yield f"  Changed: {file_path}"
            yield "Source files updated successfully"
        else:
            yield "No source file changes detected"

        yield "Source update completed"
        # Note: files_changed info was already yielded in the progress messages above

    except Exception as e:
        yield f"Source update failed: {str(e)}"
        raise e


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
    build: str = Header(None),
    profile: str = Header(None),
    strict: bool = Header(False),
    allow_libcompile: bool = Header(True),
    no_platformio: Optional[bool] = Header(None),
    native: Optional[bool] = Header(None),
    session_id: Optional[int] = Header(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> FileResponse:
    """Upload a file into a temporary directory."""

    # Handle session management
    session_info = _SESSION_MANAGER.get_session_info(session_id)
    if session_id is None:
        session_id = _SESSION_MANAGER.generate_session_id()

    # Handle native parameter with environment variable fallback
    if native is None:
        native = os.environ.get("NATIVE", "0") == "1"

    # Handle no_platformio parameter with environment variable fallback
    if no_platformio is None:
        no_platformio = os.environ.get("NO_PLATFORMIO", "0") == "1"

    # If native is True, automatically set no_platformio to True
    if native:
        no_platformio = True

    print(
        f"Endpoint accessed: /compile/wasm with file: {file.filename}, build: {build}, profile: {profile}, no_platformio: {no_platformio}, native: {native}, session: {session_info}"
    )

    file_response = _COMPILER.compile(
        file=file,
        build=build,
        profile=profile,
        output_dir=OUTPUT_DIR,
        use_sketch_cache=not _NO_SKETCH_CACHE,
        background_tasks=background_tasks,
        strict=strict,
        no_platformio=no_platformio,
        native=native,
        allow_libcompile=allow_libcompile,
    )

    # Add session information to response headers
    file_response.headers["X-Session-Id"] = str(session_id)
    file_response.headers["X-Session-Info"] = session_info
    return file_response


@app.post("/compile/libfastled")
async def compile_libfastled(
    authorization: str = Header(None),
    build: str = Header(None),
    dry_run: str = Header("false"),
) -> StreamingResponse:
    """Compile libfastled library and stream the compilation output."""

    if not _TEST and authorization != _AUTH_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Parse dry_run string to boolean
    dry_run_bool = dry_run.lower() in ["true", "1", "yes"]

    print(
        f"Endpoint accessed: /compile/libfastled with build: {build}, dry_run: {dry_run_bool}"
    )

    # EARLY VALIDATION - Check preconditions before streaming starts
    if not dry_run_bool and not VOLUME_MAPPED_SRC.exists():
        raise HTTPException(
            status_code=400,
            detail="Volume mapped source directory does not exist. This endpoint requires a properly configured environment.",
        )

    # Validate build mode early
    if build:
        build_mode_str = build.upper()
        if build_mode_str not in ["QUICK", "DEBUG", "RELEASE"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid build mode: {build}. Must be one of: quick, debug, release",
            )
    else:
        build_mode_str = "QUICK"  # Default

    async def stream_compilation() -> AsyncGenerator[bytes, None]:
        """Stream the compilation output line by line."""
        exit_code = 0
        status = "SUCCESS"

        try:
            yield f"data: Using BUILD_MODE: {build_mode_str}\n".encode()

            if dry_run_bool:
                yield "data: DRY RUN MODE: Will skip actual compilation\n".encode()
                yield f"data: Would compile libfastled with BUILD_MODE={build_mode_str}\n".encode()
                # Dry run always succeeds
            else:
                # Actual compilation logic here
                builds = [build]
                yield "data: Checking for source file changes...\n".encode()

                start_time = time.time()
                try:
                    # Stream source file changes check with progress updates
                    async for progress_msg in update_src_async(
                        _NEW_COMPILER,
                        builds=builds,
                        src_to_merge_from=VOLUME_MAPPED_SRC,
                    ):
                        yield f"data: {progress_msg}\n".encode()

                    # The generator completed successfully, get the final result
                    # Note: files_changed is returned by the generator's return statement
                    # but since we're using async for, we need to handle this differently

                    duration = time.time() - start_time
                    yield f"data: Source update completed in {duration:.2f} seconds\n".encode()

                    # Clear cache if there were changes (we'll know from the progress messages)
                    # For now, we'll always clear the cache to be safe
                    yield "data: Clearing sketch cache as a precaution\n".encode()
                    SKETCH_CACHE.clear()
                    yield "data: Cache cleared successfully\n".encode()

                    yield "data: LibFastLED compilation completed successfully!\n".encode()

                except Exception as e:
                    yield f"data: ERROR: Source update or compilation failed: {str(e)}\n".encode()
                    exit_code = 1
                    status = "FAIL"

        except Exception as e:
            yield f"data: ERROR: {str(e)}\n".encode()
            exit_code = -1
            status = "FAIL"

        finally:
            # Always send completion markers
            yield "data: COMPILATION_COMPLETE\n".encode()
            yield f"data: EXIT_CODE: {exit_code}\n".encode()
            yield f"data: STATUS: {status}\n".encode()

            # Append the logical HTTP status code that would have been used if this wasn't streaming
            if exit_code == 0:
                http_status = 200
            elif exit_code == 1:
                http_status = 400  # Bad Request - compilation failed
            else:
                http_status = 500  # Internal Server Error - unexpected failure
            yield f"data: HTTP_STATUS: {http_status}\n".encode()

    # Create the streaming response - at this point we're confident it will start successfully
    response = StreamingResponse(
        stream_compilation(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )

    return response
