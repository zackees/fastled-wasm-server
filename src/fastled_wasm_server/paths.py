import os
import warnings
from pathlib import Path


def path_or_default(default: str, env_var: str) -> Path:
    """Return the path from the environment variable or the default."""
    return Path(os.environ.get(env_var, default))


FASTLED_EXAMPLES_DIR = Path("/git/fastled/examples")

UPLOAD_DIR = path_or_default("/uploads", "ENV_UPLOAD_DIR")
TEMP_DIR = path_or_default("/tmp", "ENV_TEMP_DIR")
OUTPUT_DIR = path_or_default("/output", "ENV_OUTPUT_DIR")
COMPILER_ROOT = path_or_default("/js", "ENV_COMPILER_ROOT")
VOLUME_MAPPED_SRC = path_or_default("/host/fastled/src", "ENV_VOLUME_MAPPED_SRC")

# This will have to be changed when we get live updates working again.
LIVE_GIT_FASTLED_DIR = path_or_default("/git/fastled/src", "ENV_GIT_FASTLED_DIR")

# FASTLED_ROOT = COMPILER_ROOT / "fastled"
# FASTLED_SRC = FASTLED_ROOT / "src"
# FASTLED_EXAMPLES_DIR = FASTLED_ROOT / "examples"
SKETCH_SRC = COMPILER_ROOT / "src"
COMPIER_DIR = COMPILER_ROOT / "compiler"
# FASTLED_COMPILER_DIR = COMPILER_ROOT / "fastled/src/platforms/wasm/compiler"
PIO_BUILD_DIR = COMPILER_ROOT / ".pio/build"

_CHECK_PATHS = [
    TEMP_DIR,
    COMPILER_ROOT,
]


for path in _CHECK_PATHS:
    if not path.exists():
        warnings.warn(
            f"Path {path} does not exist. Please check your environment variables."
        )
