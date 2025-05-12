import os
from pathlib import Path


def path_or_default(env_var: str, default: str) -> Path:
    """Return the path from the environment variable or the default."""
    return Path(os.environ.get(env_var, default))


UPLOAD_DIR = path_or_default("ENV_UPLOAD_DIR", "/uploads")
TEMP_DIR = path_or_default("ENV_TEMP_DIR", "/tmp")
OUTPUT_DIR = path_or_default("ENV_OUTPUT_DIR", "/output")
COMPILER_ROOT = path_or_default("ENV_COMPILER_ROOT", "/js")
VOLUME_MAPPED_SRC = path_or_default("ENV_VOLUME_MAPPED_SRC", "/host/fastled/src")
LIVE_GIT_FASTLED_DIR = path_or_default("ENV_GIT_FASTLED_DIR", "/git/fastled")


FASTLED_SRC = COMPILER_ROOT / "fastled" / "src"
SKETCH_SRC = COMPILER_ROOT / "src"
SKETCH_CACHE_FILE = OUTPUT_DIR / "compile_cache.db"
COMPIER_DIR = COMPILER_ROOT / "compiler"
FASTLED_COMPILER_DIR = COMPILER_ROOT / "fastled/src/platforms/wasm/compiler"
PIO_BUILD_DIR = COMPILER_ROOT / ".pio/build"
