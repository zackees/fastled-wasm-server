import os
import warnings
import zipfile
from pathlib import Path

from fastapi import BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

from fastled_wasm_server.paths import (
    FASTLED_EXAMPLES_DIR,
    TEMP_DIR,
)
from fastled_wasm_server.util import make_random_path_string


def zip_example_to_file(example: str, dst_zip_file: Path) -> None:
    examples_base_dir = FASTLED_EXAMPLES_DIR
    example_dir = examples_base_dir / example
    if not example_dir.exists():
        raise HTTPException(
            status_code=404, detail=f"Example {example} not found at {example_dir}"
        )

    try:
        print(f"Creating zip file at: {dst_zip_file}")
        with zipfile.ZipFile(str(dst_zip_file), "w", zipfile.ZIP_DEFLATED) as zip_out:
            for file_path in example_dir.rglob("*"):
                if file_path.is_file():
                    if "fastled_js" in file_path.parts:
                        continue
                    arc_path = file_path.relative_to(examples_base_dir)
                    zip_out.write(file_path, arc_path)
        print(f"Zip file created at: {dst_zip_file}")
    except Exception as e:
        warnings.warn(f"Error: {e}")
        raise


def fetch_example(
    background_tasks: BackgroundTasks, example: str | None = None
) -> FileResponse:
    """Archive /git/fastled/examples/wasm into a zip file and return it."""

    # tmp_zip_file = NamedTemporaryFile(delete=False)
    # tmp_zip_path = Path(tmp_zip_file.name)
    example = example or "wasm"

    if ".." in example:
        raise HTTPException(status_code=400, detail="Invalid example name.")

    tmp_zip_path = TEMP_DIR / f"{example}-{make_random_path_string(16)}.zip"
    zip_example_to_file(example, tmp_zip_path)

    # assert tmp_zip_path.exists()
    if not tmp_zip_path.exists():
        warnings.warn("Failed to create zip file for wasm example.")
        raise HTTPException(
            status_code=500, detail="Failed to create zip file for wasm example."
        )

    def cleanup() -> None:
        try:
            os.unlink(tmp_zip_path)
        except Exception as e:
            warnings.warn(f"Error cleaning up: {e}")

    background_tasks.add_task(cleanup)
    return FileResponse(
        path=tmp_zip_path,
        media_type="application/zip",
        filename="fastled_example.zip",
        background=background_tasks,
    )
