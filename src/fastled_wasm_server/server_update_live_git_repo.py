import subprocess
import warnings

from fastled_wasm_server.paths import LIVE_GIT_FASTLED_DIR


def update_live_git_repo() -> None:
    try:
        if not LIVE_GIT_FASTLED_DIR.exists():
            subprocess.run(
                [
                    "git",
                    "clone",
                    "https://github.com/fastled/fastled.git",
                    str(LIVE_GIT_FASTLED_DIR),
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
                cwd=LIVE_GIT_FASTLED_DIR,
            )
            subprocess.run(
                ["git", "reset", "--hard", "origin/master"],
                check=True,
                capture_output=True,
                cwd=LIVE_GIT_FASTLED_DIR,
            )
            print("Live FastLED repository updated successfully")
    except subprocess.CalledProcessError as e:
        warnings.warn(
            f"Error updating live FastLED repository: {e.stdout}\n\n{e.stderr}"
        )
