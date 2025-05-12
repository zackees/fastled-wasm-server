# UPLOAD_DIR = path_or_default("/uploads", "ENV_UPLOAD_DIR")
# TEMP_DIR = path_or_default("/tmp", "ENV_TEMP_DIR")
# OUTPUT_DIR = path_or_default("/output", "ENV_OUTPUT_DIR")
# COMPILER_ROOT = path_or_default("/js", "ENV_COMPILER_ROOT")
# VOLUME_MAPPED_SRC = path_or_default("/host/fastled/src", "ENV_VOLUME_MAPPED_SRC")
# LIVE_GIT_FASTLED_DIR = path_or_default("/git/fastled", "ENV_GIT_FASTLED_DIR")

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Args:
    compiler_root: Path

    def __post__init__(self):
        if not isinstance(self.compiler_root, Path):
            raise TypeError("Compiler root must be a Path object.")
        if not self.compiler_root.exists():
            raise ValueError(f"Compiler root path does not exist: {self.compiler_root}")


def parse_args() -> Args:
    """Parse command line arguments."""

    parser = argparse.ArgumentParser(description="Compile INO file to WASM.")
    parser.add_argument(
        "--compiler-root",
        type=Path,
        default=Path("/js"),
        help="Path to the compiler root directory.",
    )

    args = parser.parse_args()
    return Args(**vars(args))


def main() -> int:
    return 0


if __name__ == "__main__":
    main()
