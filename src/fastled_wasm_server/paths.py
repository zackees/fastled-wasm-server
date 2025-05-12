import os
from pathlib import Path

UPLOAD_DIR = Path(os.environ.get("FWS_UPLOAD_DIR", "/uploads"))
TEMP_DIR = Path(os.environ.get("FWS_TEMP_DIR", "/tmp"))
OUTPUT_DIR = Path(os.environ.get("FWS_OUTPUT_DIR", "/output"))
COMPILER_ROOT = Path(os.environ.get("FWS_COMPILER_ROOT", "/js"))
VOLUME_MAPPED_SRC = Path(os.environ.get("FWS_VOLUME_MAPPED_SRC", "/host/fastled/src"))
LIVE_GIT_FASTLED_DIR = Path(os.environ.get("FWS_GIT_FASTLED_DIR", "/git/fastled"))


FASTLED_SRC = COMPILER_ROOT / "fastled" / "src"
SKETCH_SRC = COMPILER_ROOT / "src"
SKETCH_CACHE_FILE = OUTPUT_DIR / "compile_cache.db"
COMPIER_DIR = COMPILER_ROOT / "compiler"
FASTLED_COMPILER_DIR = COMPILER_ROOT / "fastled/src/platforms/wasm/compiler"
PIO_BUILD_DIR = COMPILER_ROOT / ".pio/build"
