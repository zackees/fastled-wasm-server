import json
import shutil
import subprocess
import tempfile
import threading
import time
import traceback
import warnings
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import Path

from fastapi import (  # type: ignore
    BackgroundTasks,
    HTTPException,
    UploadFile,
)
from fastapi.responses import FileResponse  # type: ignore
from fastled_wasm_compiler import Compiler
from fastled_wasm_compiler.compiler import UpdateSrcResult
from fastled_wasm_compiler.run_compile import Args

from fastled_wasm_server.paths import VOLUME_MAPPED_SRC
from fastled_wasm_server.types import CompilerStats

# from fastled_wasm_server.paths import FASTLED_COMPILER_DIR


# TODO Fix.
FASTLED_COMPILER_DIR = Path("/git/fastled/src/platforms/wasm/compiler")


@dataclass
class CompileResult:
    """A class to represent the result of a compile operation."""

    output_zip_path: Path
    filename: str
    cleanup_list: list[Path]


def _cleanup_files(paths: list[Path]) -> None:
    for path in paths:
        if path.exists():
            if path.is_file():
                try:
                    path.unlink(missing_ok=True)
                except OSError as e:
                    warnings.warn(f"Error deleting file {path}: {e}")
            elif path.is_dir():
                shutil.rmtree(path, ignore_errors=True)


def _compile_source(
    compiler_root: Path,
    temp_src_dir: Path,
    file_path: Path,
    build_mode: str,
    only_quick_builds: bool,
    profile: bool,
    compiler_lock: threading.Lock,
    output_dir: Path,
    stats: CompilerStats,
    strict: bool = False,
    hash_value: str | None = None,
    no_platformio: bool = False,
    native: bool = False,
) -> CompileResult | HTTPException:
    """Compile source code and return compiled artifacts as a zip file."""
    epoch = time.time()

    def _print(msg) -> None:
        diff = time.time() - epoch
        print(f" = SERVER {diff:.2f}s = {msg}")

    if build_mode.lower() != "quick" and only_quick_builds:
        raise HTTPException(
            status_code=400,
            detail="Only quick builds are allowed in this version.",
        )

    _print("Starting compile_source")
    stats.compile_count += 1
    try:
        # Find the first directory in temp_src_dir
        src_dir = next(Path(temp_src_dir).iterdir())
        _print(f"\nFound source directory: {src_dir}")
    except StopIteration:
        return HTTPException(
            status_code=500,
            detail=f"No files found in extracted directory: {temp_src_dir}",
        )

    _print("Files are ready, waiting for compile lock...")
    compile_lock_start = time.time()
    keep_files = (
        build_mode.lower() == "debug"
    )  # Keep files so they can be source mapped during debug.

    # If native is True, automatically set no_platformio to True
    if native:
        no_platformio = True

    args: Args = Args(
        compiler_root=compiler_root,
        assets_dirs=FASTLED_COMPILER_DIR,
        mapped_dir=temp_src_dir,
        keep_files=keep_files,
        only_copy=False,
        only_insert_header=False,
        only_compile=False,
        profile=profile,
        disable_auto_clean=False,
        no_platformio=no_platformio,
        clear_ccache=False,
        debug=build_mode.lower() == "debug",
        quick=build_mode.lower() == "quick",
        release=build_mode.lower() == "release",
        fast_debug=build_mode.lower() == "fast-debug",
        strict=strict,
    )
    cmd = ["fastled-wasm-compiler"] + args.to_cmd_args()

    with compiler_lock:
        compiled_lock_end = time.time()
        _print("\nRunning compiler...")
        proc = subprocess.Popen(
            cmd,
            cwd=compiler_root.as_posix(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        assert proc.stdout is not None
        stdout_lines: list[str] = []

        for line in iter(proc.stdout.readline, ""):
            line = line.replace("/git/src", "src").replace("/git/fastled/src", "src")
            print(line, end="")
            stdout_lines.append(line)
        _print("Compiler finished.")
        stdout = "".join(stdout_lines)
        proc.stdout.close()
        return_code = proc.wait()
        if return_code != 0:
            # COMPILE_FAILURES += 1
            stats.compile_failures += 1
            print(f"Compilation failed with return code {return_code}:\n{stdout}")
            return HTTPException(
                status_code=400,
                detail=f"Compilation failed with return code {return_code}:\n{stdout}",
            )
        # COMPILE_SUCCESSES += 1
        stats.compile_successes += 1
    compile_time = time.time() - compiled_lock_end
    COMPILE_LOCK_time = compiled_lock_end - compile_lock_start

    print(f"Compile lock time: {COMPILE_LOCK_time:.2f}s")
    print(f"Compile time: {compile_time:.2f}s")

    # Find the fastled_js directory
    fastled_js_dir = src_dir / "fastled_js"
    print(f"\nLooking for fastled_js directory at: {fastled_js_dir}")

    _print("Looking for fastled_js directory...")
    if not fastled_js_dir.exists():
        print(f"Directory contents of {src_dir}:")
        for path in src_dir.rglob("*"):
            print(f"  {path}")
        return HTTPException(
            status_code=500,
            detail=f"Compilation artifacts not found at {fastled_js_dir}",
        )
    _print("Found fastled_js directory, zipping...")

    # Replace separate stdout/stderr files with single out.txt
    out_txt = fastled_js_dir / "out.txt"
    perf_txt = fastled_js_dir / "perf.txt"
    hash_txt = fastled_js_dir / "hash.txt"
    print(f"\nSaving combined output to: {out_txt}")
    out_txt.write_text(stdout)
    perf_txt.write_text(
        f"Compile lock time: {COMPILE_LOCK_time:.2f}s\nCompile time: {compile_time:.2f}s"
    )
    if hash_value is not None:
        hash_txt.write_text(hash_value)

    output_dir.mkdir(exist_ok=True)  # Ensure output directory exists
    output_zip_path = output_dir / "fastled_output.zip"
    _print(f"\nCreating output zip at: {output_zip_path}")

    start_zip = time.time()
    try:
        with zipfile.ZipFile(
            output_zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=1
        ) as zip_out:
            _print("\nAdding files to output zip:")
            for file_path in fastled_js_dir.rglob("*"):
                if file_path.is_file():
                    arc_path = file_path.relative_to(fastled_js_dir)
                    _print(f"  Adding: {arc_path}")
                    zip_out.write(file_path, arc_path)
    except zipfile.BadZipFile as e:
        _print(f"Error creating zip file: {e}")
        return HTTPException(status_code=500, detail=f"Failed to create zip file: {e}")
    except zlib.error as e:
        _print(f"Compression error: {e}")
        return HTTPException(
            status_code=500, detail=f"Zip compression failed - zlib error: {e}"
        )
    except Exception as e:
        _print(f"Unexpected error creating zip: {e}")
        return HTTPException(status_code=500, detail=f"Failed to create zip file: {e}")
    zip_time = time.time() - start_zip
    print(f"Zip file created in {zip_time:.2f}s")

    # background_tasks.add_task(cleanup_files)

    cleanup_files: list[Path] = [
        output_zip_path,
    ]
    if temp_src_dir is not None:
        cleanup_files.append(temp_src_dir)

    _print(f"\nReturning output zip: {output_zip_path}")
    out: CompileResult = CompileResult(
        output_zip_path=output_zip_path,
        filename="fastled_output.zip",
        cleanup_list=cleanup_files,
    )
    return out


def server_compile(
    compiler_root: Path,
    file: UploadFile,
    build: str,
    profile: str,
    compiler: Compiler,
    only_quick_builds: bool,
    strict: bool,
    output_dir: Path,
    stats: CompilerStats,
    compiler_lock: threading.Lock,
    background_tasks: BackgroundTasks,
    no_platformio: bool,
    native: bool,
    allow_libcompile: bool,
) -> FileResponse:
    """Upload a file into a temporary directory."""
    if build is not None:
        build = build.lower()

    if build not in ["quick", "release", "debug", None]:
        raise HTTPException(
            status_code=400,
            detail="Invalid build mode. Must be one of 'quick', 'release', or 'debug' or omitted",
        )
    do_profile: bool = False
    if profile is not None:
        do_profile = profile.lower() == "true" or profile.lower() == "1"
    print(f"Build mode is {build}")
    build = build or "quick"
    print(f"Starting upload process for file: {file.filename}")

    # if not _TEST and authorization != _AUTH_TOKEN:
    #     raise HTTPException(status_code=401, detail="Unauthorized")

    if file is None:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    if file.filename is None:
        raise HTTPException(status_code=400, detail="No filename provided.")

    if not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=400, detail="Uploaded file must be a zip archive."
        )

    temp_zip_dir = None
    temp_src_dir = None

    try:
        # Create temporary directories - one for zip, one for source
        temp_zip_dir = tempfile.mkdtemp()
        temp_src_dir = tempfile.mkdtemp()
        print(
            f"Created temporary directories:\nzip_dir: {temp_zip_dir}\nsrc_dir: {temp_src_dir}"
        )

        file_path = Path(temp_zip_dir) / file.filename
        print(f"Saving uploaded file to: {file_path}")

        # Simple file save since size is already checked by middleware
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        print("extracting zip file...")
        hash_value: str | None = None
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            # Extract everything first
            zip_ref.extractall(temp_src_dir)

            # Use deprecated timestamp as hash value
        hash_value = f"deprecated-{time.time()}"

        if allow_libcompile and VOLUME_MAPPED_SRC.exists():
            builds = [build]
            update_result: UpdateSrcResult = compiler.update_src(
                builds=builds, src_to_merge_from=VOLUME_MAPPED_SRC
            )
            # Check if the result contains an exception
            if (
                hasattr(update_result, "exception")
                and getattr(update_result, "exception", None) is not None
            ):
                warnings.warn(
                    f"Error checking for source file changes: {getattr(update_result, 'exception')}"
                )
            elif update_result.files_changed:
                print(f"Source files changed: {len(update_result.files_changed)}")

        print("\nContents of source directory:")
        for path in Path(temp_src_dir).rglob("*"):
            print(f"  {path}")
        out: HTTPException | CompileResult = _compile_source(
            compiler_root=compiler_root,
            temp_src_dir=Path(temp_src_dir),
            file_path=file_path,
            build_mode=build,
            only_quick_builds=only_quick_builds,
            profile=do_profile,
            output_dir=output_dir,
            compiler_lock=compiler_lock,
            stats=stats,
            strict=strict,
            hash_value=hash_value,
            no_platformio=no_platformio,
            native=native,
        )
        if isinstance(out, HTTPException):
            print("Raising HTTPException")
            txt = out.detail
            json_str = json.dumps(txt)
            warnings.warn(f"Error compiling source: {json_str}")
            raise out
        compiled_out: CompileResult = out  # compiled_out is now a known type.

        def _cleanup_task(paths=compiled_out.cleanup_list) -> None:
            _cleanup_files(paths)

        background_tasks.add_task(_cleanup_task)
        # Convert to a FileResponse
        return FileResponse(
            path=compiled_out.output_zip_path,
            media_type="application/zip",
            filename=compiled_out.filename,
            background=background_tasks,
        )
    except HTTPException as e:
        stacktrace = traceback.format_exc()
        print(f"HTTPException in upload process: {str(e)}\n{stacktrace}")
        raise e

    except Exception as e:
        stack_trace = traceback.format_exc()
        print(f"Error in upload process: {stack_trace}")
        raise HTTPException(
            status_code=500,
            detail=f"Upload process failed: {str(e)}\nTrace: {e.__traceback__}",
        )
    finally:
        # Clean up in case of error
        if temp_zip_dir:
            shutil.rmtree(temp_zip_dir, ignore_errors=True)
        if temp_src_dir:
            shutil.rmtree(temp_src_dir, ignore_errors=True)


class ServerWasmCompiler:

    def __init__(
        self,
        compiler_root: Path,
        compiler: Compiler,
        compiler_lock: threading.Lock,
        only_quick_builds: bool,
    ):
        self.compiler_root = compiler_root
        self.compiler = compiler
        self.compiler_lock = compiler_lock
        self.only_quick_builds = only_quick_builds
        self.stats = CompilerStats()

    def compile(
        self,
        file: UploadFile,
        build: str,
        profile: str,
        output_dir: Path,
        background_tasks: BackgroundTasks,
        strict: bool,
        no_platformio: bool,
        native: bool,
        allow_libcompile: bool,
    ) -> FileResponse:
        return server_compile(
            compiler_root=self.compiler_root,
            file=file,
            build=build,
            profile=profile,
            strict=strict,
            compiler=self.compiler,
            only_quick_builds=self.only_quick_builds,
            output_dir=output_dir,
            stats=self.stats,
            compiler_lock=self.compiler_lock,
            background_tasks=background_tasks,
            no_platformio=no_platformio,
            native=native,
            allow_libcompile=allow_libcompile,
        )
