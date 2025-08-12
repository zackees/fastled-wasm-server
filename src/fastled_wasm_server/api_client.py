"""
FastLED WASM Server API Client

This module provides both synchronous and asynchronous HTTP clients for interacting
with the FastLED WASM server. The clients handle all available endpoints with proper
typing and error handling.
"""

from pathlib import Path
from typing import AsyncGenerator, Dict, Generator, List, Optional, Union

import httpx
from pydantic import BaseModel


class DwarfSourceRequest(BaseModel):
    """Request model for dwarf source file retrieval."""

    path: str


class CompileResponse(BaseModel):
    """Response model for compilation results."""

    status: str
    session_id: Optional[str] = None
    session_info: Optional[str] = None


class ServerSettings(BaseModel):
    """Server settings response model."""

    ALLOW_SHUTDOWN: bool
    NO_AUTO_UPDATE: str
    LIVE_GIT_UPDATES_ENABLED: bool
    LIVE_GIT_UPDATES_INTERVAL: int
    UPLOAD_LIMIT: int
    VOLUME_MAPPED_SRC: str
    VOLUME_MAPPED_SRC_EXISTS: bool
    ONLY_QUICK_BUILDS: Optional[bool] = None


class ServerInfo(BaseModel):
    """Server info response model."""

    examples: List[str]
    compile_count: int
    compile_failures: int
    compile_successes: int
    uptime: str
    build_timestamp: str
    fastled_version: str
    available_builds: List[str]


class CompilerInUseResponse(BaseModel):
    """Compiler in use response model."""

    in_use: bool


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str


class Client:
    """
    Synchronous HTTP client for FastLED WASM server.

    This client provides synchronous methods for all available server endpoints including:
    - Health checks and server info
    - Project initialization
    - WASM compilation
    - Library compilation
    - Debugging support
    """

    def __init__(
        self,
        base_url: str,
        auth_token: str = "oBOT5jbsO4ztgrpNsQwlmFLIKB",
        timeout: float = 30.0,
        **httpx_kwargs,
    ):
        """
        Initialize the FastLED WASM client.

        Args:
            base_url: Base URL of the FastLED WASM server
            auth_token: Authorization token for protected endpoints
            timeout: Request timeout in seconds
            **httpx_kwargs: Additional arguments passed to httpx.Client
        """
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self.timeout = timeout
        self._client = httpx.Client(
            base_url=self.base_url, timeout=timeout, **httpx_kwargs
        )

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authorization headers."""
        return {"Authorization": self.auth_token}

    def health_check(self) -> HealthResponse:
        """
        Perform a health check on the server.

        Returns:
            HealthResponse: Server health status
        """
        response = self._client.get("/healthz")
        response.raise_for_status()
        return HealthResponse(**response.json())

    def get_settings(self) -> ServerSettings:
        """
        Get server settings.

        Returns:
            ServerSettings: Current server settings
        """
        response = self._client.get("/settings")
        response.raise_for_status()
        return ServerSettings(**response.json())

    def get_info(self) -> ServerInfo:
        """
        Get server information including available examples and statistics.

        Returns:
            ServerInfo: Server information and statistics
        """
        response = self._client.get("/info")
        response.raise_for_status()
        return ServerInfo(**response.json())

    def is_compiler_in_use(self) -> CompilerInUseResponse:
        """
        Check if the compiler is currently in use.

        Returns:
            CompilerInUseResponse: Compiler usage status
        """
        response = self._client.get("/compile/wasm/inuse")
        response.raise_for_status()
        return CompilerInUseResponse(**response.json())

    def shutdown_server(self) -> Dict[str, str]:
        """
        Shutdown the server (if allowed by server configuration).

        Returns:
            Dict[str, str]: Shutdown status

        Raises:
            httpx.HTTPStatusError: If shutdown is not allowed or fails
        """
        headers = self._get_auth_headers()
        response = self._client.get("/shutdown", headers=headers)
        response.raise_for_status()
        return response.json()

    def init_project(self, example: Optional[str] = None) -> bytes:
        """
        Initialize a new project with default or specified example.

        Args:
            example: Optional example name. If None, uses default example.

        Returns:
            bytes: ZIP file content of the initialized project
        """
        if example is None:
            response = self._client.get("/project/init")
        else:
            response = self._client.post("/project/init", content=example)

        response.raise_for_status()
        return response.content

    def get_dwarf_source(self, path: str) -> str:
        """
        Get source file content for debugging.

        Args:
            path: Path to the source file

        Returns:
            str: Source file content
        """
        request = DwarfSourceRequest(path=path)
        response = self._client.post("/dwarfsource", json=request.model_dump())
        response.raise_for_status()
        return response.text

    def export_emsdk_headers(self) -> bytes:
        """
        Export EMSDK headers zip from the server.

        Returns:
            bytes: EMSDK headers zip file content.
        """
        response = self._client.get("/headers/emsdk")
        response.raise_for_status()
        return response.content

    def compile_wasm(
        self,
        file_path: Union[str, Path],
        build: Optional[str] = None,
        profile: Optional[str] = None,
        strict: bool = False,
        no_platformio: Optional[bool] = None,
        native: Optional[bool] = None,
        session_id: Optional[int] = None,
        allow_libcompile: bool = True,
    ) -> bytes:
        """
        Compile a WASM file.

        Args:
            file_path: Path to the file to compile
            build: Build type (quick, debug, release)
            profile: Profile setting
            strict: Enable strict compilation
            no_platformio: Disable PlatformIO usage
            native: Enable native compilation
            session_id: Session ID for tracking

        Returns:
            bytes: Compiled WASM file content
        """
        # Prepare headers
        headers = self._get_auth_headers()

        if build is not None:
            headers["build"] = build
        if profile is not None:
            headers["profile"] = profile
        if strict:
            headers["strict"] = "true"
        if no_platformio is not None:
            headers["no_platformio"] = "true" if no_platformio else "false"
        if native is not None:
            headers["native"] = "true" if native else "false"
        if session_id is not None:
            headers["session_id"] = str(session_id)
        if allow_libcompile:
            headers["allow_libcompile"] = "true"
        else:
            headers["allow_libcompile"] = "false"

        # Prepare file upload
        file_path = Path(file_path)

        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "application/octet-stream")}

            response = self._client.post("/compile/wasm", headers=headers, files=files)

        response.raise_for_status()
        return response.content

    def compile_libfastled(
        self, build: Optional[str] = None, dry_run: bool = False
    ) -> Generator[str, None, None]:
        """
        Compile libfastled library and stream the compilation output.

        Args:
            build: Build type (quick, debug, release)
            dry_run: If True, performs a dry run without actual compilation

        Yields:
            str: Compilation output lines
        """
        headers = self._get_auth_headers()

        if build is not None:
            headers["build"] = build
        if dry_run:
            headers["dry_run"] = "true"

        with self._client.stream(
            "POST", "/compile/libfastled", headers=headers
        ) as response:
            response.raise_for_status()

            for chunk in response.iter_text():
                if chunk:
                    yield chunk

    def compile_wasm_with_file_content(
        self,
        file_content: bytes,
        filename: str,
        build: Optional[str] = None,
        profile: Optional[str] = None,
        strict: bool = False,
        no_platformio: Optional[bool] = None,
        native: Optional[bool] = None,
        session_id: Optional[int] = None,
        allow_libcompile: bool = True,
    ) -> bytes:
        """
        Compile WASM from file content (without saving to disk).

        Args:
            file_content: Content of the file to compile
            filename: Name of the file (for server reference)
            build: Build type (quick, debug, release)
            profile: Profile setting
            strict: Enable strict compilation
            no_platformio: Disable PlatformIO usage
            native: Enable native compilation
            session_id: Session ID for tracking

        Returns:
            bytes: Compiled WASM file content
        """
        # Prepare headers
        headers = self._get_auth_headers()

        if build is not None:
            headers["build"] = build
        if profile is not None:
            headers["profile"] = profile
        if strict:
            headers["strict"] = "true"
        if no_platformio is not None:
            headers["no_platformio"] = "true" if no_platformio else "false"
        if native is not None:
            headers["native"] = "true" if native else "false"
        if session_id is not None:
            headers["session_id"] = str(session_id)
        if allow_libcompile:
            headers["allow_libcompile"] = "true"
        else:
            headers["allow_libcompile"] = "false"

        # Prepare file upload
        files = {"file": (filename, file_content, "application/octet-stream")}

        response = self._client.post("/compile/wasm", headers=headers, files=files)

        response.raise_for_status()
        return response.content


class ClientAsync:
    """
    Asynchronous HTTP client for FastLED WASM server.

    This client provides async methods for all available server endpoints including:
    - Health checks and server info
    - Project initialization
    - WASM compilation
    - Library compilation
    - Debugging support
    """

    def __init__(
        self,
        base_url: str,
        auth_token: str = "oBOT5jbsO4ztgrpNsQwlmFLIKB",
        timeout: float = 30.0,
        **httpx_kwargs,
    ):
        """
        Initialize the FastLED WASM async client.

        Args:
            base_url: Base URL of the FastLED WASM server
            auth_token: Authorization token for protected endpoints
            timeout: Request timeout in seconds
            **httpx_kwargs: Additional arguments passed to httpx.AsyncClient
        """
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self.timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=self.base_url, timeout=timeout, **httpx_kwargs
        )

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authorization headers."""
        return {"Authorization": self.auth_token}

    async def health_check(self) -> HealthResponse:
        """
        Perform a health check on the server.

        Returns:
            HealthResponse: Server health status
        """
        response = await self._client.get("/healthz")
        response.raise_for_status()
        return HealthResponse(**response.json())

    async def get_settings(self) -> ServerSettings:
        """
        Get server settings.

        Returns:
            ServerSettings: Current server settings
        """
        response = await self._client.get("/settings")
        response.raise_for_status()
        return ServerSettings(**response.json())

    async def get_info(self) -> ServerInfo:
        """
        Get server information including available examples and statistics.

        Returns:
            ServerInfo: Server information and statistics
        """
        response = await self._client.get("/info")
        response.raise_for_status()
        return ServerInfo(**response.json())

    async def is_compiler_in_use(self) -> CompilerInUseResponse:
        """
        Check if the compiler is currently in use.

        Returns:
            CompilerInUseResponse: Compiler usage status
        """
        response = await self._client.get("/compile/wasm/inuse")
        response.raise_for_status()
        return CompilerInUseResponse(**response.json())

    async def shutdown_server(self) -> Dict[str, str]:
        """
        Shutdown the server (if allowed by server configuration).

        Returns:
            Dict[str, str]: Shutdown status

        Raises:
            httpx.HTTPStatusError: If shutdown is not allowed or fails
        """
        headers = self._get_auth_headers()
        response = await self._client.get("/shutdown", headers=headers)
        response.raise_for_status()
        return response.json()

    async def init_project(self, example: Optional[str] = None) -> bytes:
        """
        Initialize a new project with default or specified example.

        Args:
            example: Optional example name. If None, uses default example.

        Returns:
            bytes: ZIP file content of the initialized project
        """
        if example is None:
            response = await self._client.get("/project/init")
        else:
            response = await self._client.post("/project/init", content=example)

        response.raise_for_status()
        return response.content

    async def get_dwarf_source(self, path: str) -> str:
        """
        Get source file content for debugging.

        Args:
            path: Path to the source file

        Returns:
            str: Source file content
        """
        request = DwarfSourceRequest(path=path)
        response = await self._client.post("/dwarfsource", json=request.model_dump())
        response.raise_for_status()
        return response.text

    async def export_emsdk_headers(self) -> bytes:
        """
        Export EMSDK headers zip from the server asynchronously.

        Returns:
            bytes: EMSDK headers zip file content.
        """
        response = await self._client.get("/headers/emsdk")
        response.raise_for_status()
        return response.content

    async def compile_wasm(
        self,
        file_path: Union[str, Path],
        build: Optional[str] = None,
        profile: Optional[str] = None,
        strict: bool = False,
        no_platformio: Optional[bool] = None,
        native: Optional[bool] = None,
        session_id: Optional[int] = None,
        allow_libcompile: bool = True,
    ) -> bytes:
        """
        Compile a WASM file.

        Args:
            file_path: Path to the file to compile
            build: Build type (quick, debug, release)
            profile: Profile setting
            strict: Enable strict compilation
            no_platformio: Disable PlatformIO usage
            native: Enable native compilation
            session_id: Session ID for tracking

        Returns:
            bytes: Compiled WASM file content
        """
        # Prepare headers
        headers = self._get_auth_headers()

        if build is not None:
            headers["build"] = build
        if profile is not None:
            headers["profile"] = profile
        if strict:
            headers["strict"] = "true"
        if no_platformio is not None:
            headers["no_platformio"] = "true" if no_platformio else "false"
        if native is not None:
            headers["native"] = "true" if native else "false"
        if session_id is not None:
            headers["session_id"] = str(session_id)
        if allow_libcompile:
            headers["allow_libcompile"] = "true"
        else:
            headers["allow_libcompile"] = "false"

        # Prepare file upload
        file_path = Path(file_path)

        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "application/octet-stream")}

            response = await self._client.post(
                "/compile/wasm", headers=headers, files=files
            )

        response.raise_for_status()
        return response.content

    async def compile_libfastled(
        self, build: Optional[str] = None, dry_run: bool = False
    ) -> AsyncGenerator[str, None]:
        """
        Compile libfastled library and stream the compilation output.

        Args:
            build: Build type (quick, debug, release)
            dry_run: If True, performs a dry run without actual compilation

        Yields:
            str: Compilation output lines
        """
        headers = self._get_auth_headers()

        if build is not None:
            headers["build"] = build
        if dry_run:
            headers["dry_run"] = "true"

        async with self._client.stream(
            "POST", "/compile/libfastled", headers=headers
        ) as response:
            response.raise_for_status()

            async for chunk in response.aiter_text():
                if chunk:
                    yield chunk

    async def compile_wasm_with_file_content(
        self,
        file_content: bytes,
        filename: str,
        build: Optional[str] = None,
        profile: Optional[str] = None,
        strict: bool = False,
        no_platformio: Optional[bool] = None,
        native: Optional[bool] = None,
        session_id: Optional[int] = None,
        allow_libcompile: bool = True,
    ) -> bytes:
        """
        Compile WASM from file content (without saving to disk).

        Args:
            file_content: Content of the file to compile
            filename: Name of the file (for server reference)
            build: Build type (quick, debug, release)
            profile: Profile setting
            strict: Enable strict compilation
            no_platformio: Disable PlatformIO usage
            native: Enable native compilation
            session_id: Session ID for tracking

        Returns:
            bytes: Compiled WASM file content
        """
        # Prepare headers
        headers = self._get_auth_headers()

        if build is not None:
            headers["build"] = build
        if profile is not None:
            headers["profile"] = profile
        if strict:
            headers["strict"] = "true"
        if no_platformio is not None:
            headers["no_platformio"] = "true" if no_platformio else "false"
        if native is not None:
            headers["native"] = "true" if native else "false"
        if session_id is not None:
            headers["session_id"] = str(session_id)
        if allow_libcompile:
            headers["allow_libcompile"] = "true"
        else:
            headers["allow_libcompile"] = "false"

        # Prepare file upload
        files = {"file": (filename, file_content, "application/octet-stream")}

        response = await self._client.post(
            "/compile/wasm", headers=headers, files=files
        )

        response.raise_for_status()
        return response.content
