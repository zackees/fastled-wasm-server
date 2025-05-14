from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import Response


@dataclass
class SourceFileBytes:
    """A class to represent a source file."""

    content: bytes
    media_type: str

    def __post_init__(self):
        if not isinstance(self.content, bytes):
            raise TypeError("Content must be of type bytes.")
        if not isinstance(self.media_type, str):
            raise TypeError("Media type must be of type str.")


# Return content and media type
def fetch_file(
    fastled_src_dir: Path, full_path: Path
) -> SourceFileBytes | HTTPException:
    """Fetch the file from the server."""
    print(f"Fetching file: {full_path}")
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    if not full_path.is_file():
        raise HTTPException(status_code=400, detail="Not a file.")
    if not full_path.is_relative_to(fastled_src_dir) and not full_path.is_relative_to(
        "/emsdk"
    ):
        raise HTTPException(status_code=400, detail="Invalid file path.")

    content = full_path.read_bytes()
    # Determine media type based on file extension
    media_type = "text/plain"
    if full_path.suffix in [".h", ".cpp"]:
        media_type = "text/plain"
    elif full_path.suffix == ".html":
        media_type = "text/html"
    elif full_path.suffix == ".js":
        media_type = "application/javascript"
    elif full_path.suffix == ".css":
        media_type = "text/css"

    # return content, media_type
    out = SourceFileBytes(content=content, media_type=media_type)
    return out


def fetch_source_file(fastled_src_dir: Path, filepath: str) -> Response:
    """Get the source file from the server."""
    print(f"Endpoint accessed: /sourcefiles/{filepath}")
    if ".." in filepath:
        # return HTTPException(status_code=400, detail="Invalid file path.")
        return Response(
            content="Invalid file path.", media_type="text/plain", status_code=400
        )
    full_path = Path(fastled_src_dir / filepath)
    result: SourceFileBytes | HTTPException = fetch_file(
        fastled_src_dir=fastled_src_dir, full_path=full_path
    )
    if isinstance(result, HTTPException):
        assert isinstance(result, HTTPException)
        return Response(
            content=result.detail,  # type: ignore
            media_type="text/plain",
            status_code=result.status_code,  # type: ignore
        )
    # content, media_type = result
    # assert isinstance(result, SourceFileBytes)
    content = result.content
    media_type = result.media_type
    return Response(content=content, media_type=media_type)


_PATTERNS_FASTLED_SRC = [
    "drawfsource/js/src/drawfsource/git/fastled/src/",
    "drawfsource/js/drawfsource/headers/",
]

_PATTERNS_SKETCH = ["drawfsources/js/src/"]


def _fetch_drawfsource(fastled_src_dir: Path, file_path: str) -> Response:
    """Serve static files."""
    # Check if path matches the pattern js/fastled/src/...

    resolved_path: Path | None = None
    is_fastled_src = False
    is_sketch_src = False

    for pattern in _PATTERNS_FASTLED_SRC:
        if file_path.startswith(pattern):
            # Extract the path after "js/fastled/src/"
            relative_path = file_path[len(pattern) :]
            resolved_path = fastled_src_dir / relative_path
            is_fastled_src = True
            break

    if resolved_path is None:
        for pattern in _PATTERNS_SKETCH:
            if file_path.startswith(pattern):
                # Extract the path after "drawfsources/js/src/"
                relative_path = file_path[len(pattern) :]
                resolved_path = fastled_src_dir / relative_path
                is_fastled_src = True
                break

    if is_fastled_src:
        assert resolved_path is not None
        result: SourceFileBytes | HTTPException = fetch_file(
            fastled_src_dir=fastled_src_dir, full_path=Path(resolved_path)
        )

        # return Response(content=content, media_type=media_type)
        if isinstance(result, HTTPException):
            return Response(
                content=result.detail,  # type: ignore
                media_type="text/plain",
                status_code=result.status_code,  # type: ignore
            )
        content, media_type = result.content, result.media_type
        return Response(content=content, media_type=media_type)

    if is_sketch_src:
        assert isinstance(resolved_path, str)
        result: SourceFileBytes | HTTPException = fetch_file(
            fastled_src_dir=fastled_src_dir, full_path=Path(resolved_path)
        )
        if isinstance(result, HTTPException):
            return Response(
                content=result.detail,  # type: ignore
                media_type="text/plain",
                status_code=result.status_code,  # type: ignore
            )
    # 404
    return Response(content="File not found.", media_type="text/plain", status_code=404)


class SourceFileFetcher:
    """A class to fetch source files."""

    def __init__(self, fastled_src: Path):
        self.fastled_src = fastled_src

    def fetch_fastled(self, path: str) -> Response:
        """Fetch the source file."""
        return fetch_source_file(fastled_src_dir=self.fastled_src, filepath=path)

    def fetch_drawfsource(self, path: str) -> Response:
        """Fetch the source file."""
        return _fetch_drawfsource(fastled_src_dir=self.fastled_src, file_path=path)
