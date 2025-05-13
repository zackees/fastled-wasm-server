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
    compiler_args: list[str] | None

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

    # parser.parse_known_args()
    args, unknown_args = parser.parse_known_args()
    out: Args = Args(
        compiler_root=args.compiler_root,
        compiler_args=unknown_args,
    )
    return out


def main() -> int:
    # Work in progress. Setup the environment plus call the compile function.
    args = parse_args()
    _ = args.compiler_args
    # os.environ["COMPILER_ROOT"] = str(args.compiler_root)

    # from fastled_wasm_server.compile import Args as CompileArgs
    # from fastled_wasm_server.compile import run as run_compile

    # compile_args = CompileArgs(
    #     ino_file=Path("/tmp/ino_file.ino"),
    #     output_dir=Path("/output"),
    #     compiler_root=args.compiler_root,
    #     fastled_src=Path("/fastled/src"),
    #     sketch_src=Path("/src"),
    #     sketch_cache_file=Path("/output/compile_cache.db"),
    # )

    # run_compile(compile_args)

    return 0


if __name__ == "__main__":
    main()
