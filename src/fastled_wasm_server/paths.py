import os
from pathlib import Path


def path_or_default(default: str, env_var: str) -> Path:
    """Return the path from the environment variable or the default."""
    return Path(os.environ.get(env_var, default))


UPLOAD_DIR = path_or_default("/uploads", "ENV_UPLOAD_DIR")
TEMP_DIR = path_or_default("/tmp", "ENV_TEMP_DIR")
OUTPUT_DIR = path_or_default("/output", "ENV_OUTPUT_DIR")
COMPILER_ROOT = path_or_default("/js", "ENV_COMPILER_ROOT")
VOLUME_MAPPED_SRC = path_or_default("/host/fastled/src", "ENV_VOLUME_MAPPED_SRC")
LIVE_GIT_FASTLED_DIR = path_or_default("/git/fastled", "ENV_GIT_FASTLED_DIR")


FASTLED_SRC = COMPILER_ROOT / "fastled" / "src"
SKETCH_SRC = COMPILER_ROOT / "src"
SKETCH_CACHE_FILE = OUTPUT_DIR / "compile_cache.db"
COMPIER_DIR = COMPILER_ROOT / "compiler"
FASTLED_COMPILER_DIR = COMPILER_ROOT / "fastled/src/platforms/wasm/compiler"
PIO_BUILD_DIR = COMPILER_ROOT / ".pio/build"
