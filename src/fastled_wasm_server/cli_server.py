import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_PORT = os.environ.get("PORT", 80)
HERE = Path(__file__).parent


@dataclass
class Args:
    cwd: Path
    disable_auto_clean: bool
    allow_shutdown: bool
    no_auto_update: bool
    no_sketch_cache: bool

    def __post_init__(self):
        if not isinstance(self.cwd, Path):
            raise TypeError("CWD must be a Path object.")
        if not self.cwd.exists():
            raise ValueError(f"CWD path does not exist: {self.cwd}")
        if not self.cwd.is_dir():
            raise ValueError(f"CWD path is not a directory: {self.cwd}")

    @staticmethod
    def parse_args() -> "Args":
        parser = argparse.ArgumentParser(description="Compile INO file to WASM.")
        parser.add_argument(
            "--cwd",
            type=Path,
            default=Path(os.getcwd()),
            help="Path to the current working directory.",
        )
        parser.add_argument(
            "--disable-auto-clean",
            action="store_true",
            help="Disable auto clean.",
        )
        parser.add_argument(
            "--allow-shutdown",
            action="store_true",
            help="Allow shutdown.",
        )
        parser.add_argument(
            "--no-auto-update",
            action="store_true",
            help="Disable auto update.",
        )
        parser.add_argument(
            "--no-sketch-cache",
            action="store_true",
            help="Disable sketch cache.",
        )
        args = parser.parse_args()
        return Args(
            cwd=args.cwd,
            disable_auto_clean=args.disable_auto_clean,
            allow_shutdown=args.allow_shutdown,
            no_auto_update=args.no_auto_update,
            no_sketch_cache=args.no_sketch_cache,
        )


def run_server(args: Args) -> int:
    env = os.environ.copy()
    if args.disable_auto_clean:
        env["DISABLE_AUTO_CLEAN"] = "1"
    if args.allow_shutdown:
        env["ALLOW_SHUTDOWN"] = "1"
    if args.no_auto_update:
        env["NO_AUTO_UPDATE"] = "1"
    if args.no_sketch_cache:
        env["NO_SKETCH_CACHE"] = "1"
    cmd_list = [
        "uvicorn",
        "fastled_wasm_server.server:app",
        "--host",
        "0.0.0.0",
        "--workers",
        "1",
        "--port",
        f"{_PORT}",
    ]
    cwd = args.cwd
    cp: subprocess.CompletedProcess = subprocess.run(
        cmd_list, cwd=cwd.as_posix(), env=env
    )
    return cp.returncode


def main() -> int:
    print("Running...")
    args: Args = Args.parse_args()
    try:
        rtn = run_server(args)
        return rtn
    except KeyboardInterrupt:
        print("Exiting...")
        return 1


if __name__ == "__main__":
    sys.exit(main())
