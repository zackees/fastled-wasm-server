import json
import os
import threading
import time
import warnings
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Timer

import psutil  # type: ignore
from disklru import DiskLRUCache  # type: ignore
from fastapi import (  # type: ignore
    BackgroundTasks,
    Body,
    FastAPI,
    File,
    Header,
    HTTPException,
    UploadFile,
)
from fastapi.responses import FileResponse, RedirectResponse, Response  # type: ignore
from starlette.middleware.base import BaseHTTPMiddleware  # type: ignore
from starlette.requests import Request  # type: ignore

from fastled_wasm_server import server_compile
from fastled_wasm_server.code_sync import CodeSync
from fastled_wasm_server.compile_lock import COMPILE_LOCK  # type: ignore
from fastled_wasm_server.paths import (  # The folder where the actual source code is located.
    FASTLED_SRC,
    LIVE_GIT_FASTLED_DIR,
    OUTPUT_DIR,
    SKETCH_CACHE_FILE,
    UPLOAD_DIR,
    VOLUME_MAPPED_SRC,
)
from fastled_wasm_server.server_fetch_example import (
    fetch_example,
)
from fastled_wasm_server.server_serve_src_files import (
    fetch_drawfsource,
    fetch_source_file,
)
from fastled_wasm_server.server_update_live_git_repo import update_live_git_repo
from fastled_wasm_server.types import CompilerStats

_EXAMPLES: list[str] = [
    "Chromancer",
    "LuminescentGrand",
    "wasm",
    "FxAnimartrix",
    "FxCylon",
    "FxDemoReel100",
    "FxFire2012",
    "FxEngine",
    "FxGfx2Video",
    "FxNoisePlusPalette",
    "FxNoiseRing",
    "FxSdCard",
    "FxWater",
    "Wave2d",
    "FxWave2d",
    "FireCylinder",
]

_COMPILER_STATS = CompilerStats()

_TEST = False
_UPLOAD_LIMIT = 10 * 1024 * 1024
_MEMORY_LIMIT_MB = int(os.environ.get("MEMORY_LIMIT_MB", "0"))  # 0 means disabled
_MEMORY_CHECK_INTERVAL = 0.1  # Check every 100ms
_MEMORY_EXCEEDED_EXIT_CODE = 137  # Standard OOM kill code
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


# TODO - cleanup
_NO_AUTO_UPDATE = (
    os.environ.get("NO_AUTO_UPDATE", "0") in ["1", "true"] or VOLUME_MAPPED_SRC.exists()
)
# This feature is broken. To fix, issue a git update, THEN invoke the compiler command to re-warm the cache.
# otherwise you get worst case scenario on a new compile.
# _LIVE_GIT_UPDATES_ENABLED = (not _NO_AUTO_UPDATE) or (
#     os.environ.get("LIVE_GIT_UPDATES", "0") in ["1", "true"]
# )
_LIVE_GIT_UPDATES_ENABLED = False


if _NO_SKETCH_CACHE:
    print("Sketch caching disabled")


UPLOAD_DIR.mkdir(exist_ok=True)
START_TIME = time.time()


OUTPUT_DIR.mkdir(exist_ok=True)

# Initialize disk cache
SKETCH_CACHE_MAX_ENTRIES = 50
SKETCH_CACHE = DiskLRUCache(str(SKETCH_CACHE_FILE), SKETCH_CACHE_MAX_ENTRIES)


class UploadSizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_upload_size: int):
        super().__init__(app)
        self.max_upload_size = max_upload_size

    async def dispatch(self, request: Request, call_next):
        if request.method == "POST" and "/compile/wasm" in request.url.path:
            print(
                f"Upload request with content-length: {request.headers.get('content-length')}"
            )
            content_length = request.headers.get("content-length")
            if content_length:
                content_length = int(content_length)  # type: ignore
                if content_length > self.max_upload_size:  # type: ignore
                    return Response(
                        status_code=413,
                        content=f"File size exceeds {self.max_upload_size} byte limit, for large assets please put them in data/ directory to avoid uploading them to the server.",
                    )
        return await call_next(request)


_CODE_SYNC = CodeSync(
    volume_mapped_src=VOLUME_MAPPED_SRC,
    rsync_dest=FASTLED_SRC,
)


@asynccontextmanager  # type: ignore
async def lifespan(app: FastAPI):  # type: ignore
    print("Starting FastLED wasm compiler server...")
    try:
        print(f"Settings: {json.dumps(get_settings(), indent=2)}")
    except Exception as e:
        print(f"Error getting settings: {e}")

    if _MEMORY_LIMIT_MB > 0:
        print(f"Starting memory watchdog (limit: {_MEMORY_LIMIT_MB}MB)")
        memory_watchdog()

    _CODE_SYNC.sync_source_directory_if_volume_is_mapped()

    if _LIVE_GIT_UPDATES_ENABLED:
        Timer(
            _LIVE_GIT_UPDATES_INTERVAL, sync_live_git_to_target
        ).start()  # Start the periodic git update
    else:
        print("Auto updates disabled")
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


def sync_live_git_to_target() -> None:
    if not _LIVE_GIT_UPDATES_ENABLED:
        return
    update_live_git_repo()  # no lock

    def on_files_changed() -> None:
        print("FastLED source changed from github repo, clearing disk cache.")
        SKETCH_CACHE.clear()

    _CODE_SYNC.sync_src_to_target(
        volume_mapped_src=LIVE_GIT_FASTLED_DIR / "src",
        rsync_dest=FASTLED_SRC,
        callback=on_files_changed,
    )
    _CODE_SYNC.sync_src_to_target(
        volume_mapped_src=LIVE_GIT_FASTLED_DIR / "examples",
        rsync_dest=FASTLED_SRC.parent / "examples",
        callback=on_files_changed,
    )
    # Basically a setTimeout() in JS.
    Timer(
        _LIVE_GIT_UPDATES_INTERVAL, sync_live_git_to_target
    ).start()  # Start the periodic git update


def memory_watchdog() -> None:
    """Monitor memory usage and kill process if it exceeds limit."""
    if _MEMORY_LIMIT_MB <= 0:
        return

    def check_memory() -> None:
        while True:
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            if memory_mb > _MEMORY_LIMIT_MB:
                print(
                    f"Memory limit exceeded! Using {memory_mb:.1f}MB > {_MEMORY_LIMIT_MB}MB limit"
                )
                os._exit(_MEMORY_EXCEEDED_EXIT_CODE)
            time.sleep(_MEMORY_CHECK_INTERVAL)

    watchdog_thread = threading.Thread(target=check_memory, daemon=True)
    watchdog_thread.start()


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
    """Archive /js/fastled/examples/wasm into a zip file and return it."""
    print("Endpoint accessed: /project/init")
    response: FileResponse = fetch_example(background_tasks=background_tasks)
    return response


@app.post("/project/init")
def project_init_example(
    background_tasks: BackgroundTasks, example: str = Body(...)
) -> FileResponse:
    """Archive /js/fastled/examples/{example} into a zip file and return it."""
    print(f"Endpoint accessed: /project/init/example with example: {example}")
    out: FileResponse = fetch_example(
        background_tasks=background_tasks, example=example
    )
    return out


@app.get("/sourcefiles/{filepath:path}")
def source_file(filepath: str) -> Response:
    """Get the source file from the server."""
    out: Response = fetch_source_file(filepath=filepath)
    return out


@app.get("/drawfsource/{file_path:path}")
def drawfsource(file_path: str) -> Response:
    """Serve static files."""
    out: Response = fetch_drawfsource(file_path=file_path)
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
    out = {
        "examples": _EXAMPLES,
        "compile_count": _COMPILER_STATS.compile_count,
        "compile_failures": _COMPILER_STATS.compile_failures,
        "compile_successes": _COMPILER_STATS.compile_successes,
        "uptime": uptime_fmtd,
        "build_timestamp": build_timestamp,
        "fastled_version": fastled_version,
    }
    return out


# THIS MUST NOT BE ASYNC!!!!
@app.post("/compile/wasm")
def compile_wasm(
    file: UploadFile = File(...),
    authorization: str = Header(None),
    build: str = Header(None),
    profile: str = Header(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> FileResponse:
    """Upload a file into a temporary directory."""

    if not _TEST and authorization != _AUTH_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    print(f"Endpoint accessed: /compile/wasm with file: {file.filename}")

    file_response = server_compile.server_compile(
        file=file,
        build=build,
        profile=profile,
        sketch_cache=SKETCH_CACHE,
        use_sketch_cache=not _NO_SKETCH_CACHE,
        code_sync=_CODE_SYNC,
        only_quick_builds=_ONLY_QUICK_BUILDS,
        compiler_lock=COMPILE_LOCK,
        output_dir=OUTPUT_DIR,
        stats=_COMPILER_STATS,
        background_tasks=background_tasks,
    )

    return file_response
