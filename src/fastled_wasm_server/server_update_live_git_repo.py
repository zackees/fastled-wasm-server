import subprocess
import threading
import warnings
from pathlib import Path
from threading import Timer

from disklru import DiskLRUCache  # type: ignore

from fastled_wasm_server.code_sync import CodeSync


def update_live_git_repo(live_git_fastled_root_dir: Path) -> None:
    try:
        if not live_git_fastled_root_dir.exists():
            subprocess.run(
                [
                    "git",
                    "clone",
                    "https://github.com/fastled/fastled.git",
                    str(live_git_fastled_root_dir),
                    "--depth=1",
                ],
                check=True,
            )
            print("Cloned live FastLED repository")
        else:
            print("Updating live FastLED repository")
            subprocess.run(
                ["git", "fetch", "origin"],
                check=True,
                capture_output=True,
                cwd=live_git_fastled_root_dir,
            )
            subprocess.run(
                ["git", "reset", "--hard", "origin/master"],
                check=True,
                capture_output=True,
                cwd=live_git_fastled_root_dir,
            )
            print("Live FastLED repository updated successfully")
    except subprocess.CalledProcessError as e:
        warnings.warn(
            f"Error updating live FastLED repository: {e.stdout}\n\n{e.stderr}"
        )


def start_sync_live_git_to_target(
    live_git_fastled_root_dir: Path,
    compiler_lock: threading.Lock,
    code_sync: CodeSync,
    sketch_cache: DiskLRUCache,
    fastled_src: Path,
    update_interval: int,
) -> None:
    update_live_git_repo(live_git_fastled_root_dir)  # no lock

    def on_files_changed() -> None:
        print("FastLED source changed from github repo, clearing disk cache.")
        sketch_cache.clear()

    with compiler_lock:
        code_sync.sync_src_to_target(
            volume_mapped_src=live_git_fastled_root_dir / "src",
            rsync_dest=fastled_src,
            callback=on_files_changed,
        )
    code_sync.sync_src_to_target(
        volume_mapped_src=live_git_fastled_root_dir / "examples",
        rsync_dest=fastled_src.parent / "examples",
        callback=on_files_changed,
    )
    # Basically a setTimeout() in JS.
    Timer(
        update_interval, start_sync_live_git_to_target
    ).start()  # Start the periodic git update
