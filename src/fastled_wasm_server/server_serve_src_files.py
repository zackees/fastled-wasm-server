from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import Response

from fastled_wasm_server.paths import FASTLED_SRC


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
def fetch_file(full_path: Path) -> SourceFileBytes | HTTPException:
    """Fetch the file from the server."""
    print(f"Fetching file: {full_path}")
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    if not full_path.is_file():
        raise HTTPException(status_code=400, detail="Not a file.")
    if not full_path.is_relative_to(FASTLED_SRC) and not full_path.is_relative_to(
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


def fetch_source_file(filepath: str) -> Response:
    """Get the source file from the server."""
    print(f"Endpoint accessed: /sourcefiles/{filepath}")
    if ".." in filepath:
        # return HTTPException(status_code=400, detail="Invalid file path.")
        return Response(
            content="Invalid file path.", media_type="text/plain", status_code=400
        )
    full_path = Path(FASTLED_SRC / filepath)
    result: SourceFileBytes | HTTPException = fetch_file(full_path=full_path)
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


def fetch_drawfsource(file_path: str) -> Response:
    """Serve static files."""
    # Check if path matches the pattern js/fastled/src/...
    if file_path.startswith("js/fastled/src/"):
        # Extract the path after "js/fastled/src/"
        relative_path = file_path[len("js/fastled/src/") :]
        full_path = FASTLED_SRC / relative_path
        result: SourceFileBytes | HTTPException = fetch_file(full_path=full_path)

        # return Response(content=content, media_type=media_type)
        if isinstance(result, HTTPException):
            return Response(
                content=result.detail,  # type: ignore
                media_type="text/plain",
                status_code=result.status_code,  # type: ignore
            )
        content, media_type = result.content, result.media_type
        return Response(content=content, media_type=media_type)
    elif file_path.startswith("js/drawfsource/emsdk/"):
        relative_path = file_path[len("js/drawfsource/emsdk/") :]
        full_path = Path("/") / "emsdk" / relative_path
        result: SourceFileBytes | HTTPException = fetch_file(full_path=full_path)
        if isinstance(result, HTTPException):
            return Response(
                content=result.detail,  # type: ignore
                media_type="text/plain",
                status_code=result.status_code,  # type: ignore
            )
        content, media_type = result.content, result.media_type
        return Response(content=content, media_type=media_type)

    # If file not found or path doesn't match expected format
    return Response(
        content=f"File not found: {file_path}", media_type="text/plain", status_code=404
    )
