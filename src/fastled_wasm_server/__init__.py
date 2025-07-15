"""FastLED WASM Server package."""

from pathlib import Path
from typing import AsyncGenerator, Awaitable, Dict, Optional, Union

from .api_client import (
    Client,
    ClientAsync,
    CompilerInUseResponse,
    DwarfSourceRequest,
    HealthResponse,
    ServerInfo,
    ServerSettings,
)


class FastLEDWasmAPI:
    """
    Unified API interface for FastLED WASM server operations.

    This class dynamically loads the appropriate client implementation (async or sync)
    and forwards all method calls through an interface pointer.
    """

    def __init__(
        self,
        base_url: str,
        auth_token: str = "oBOT5jbsO4ztgrpNsQwlmFLIKB",
        timeout: float = 30.0,
        use_async: bool = True,
        **httpx_kwargs,
    ):
        """
        Initialize the FastLED WASM API.

        Args:
            base_url: Base URL of the FastLED WASM server
            auth_token: Authorization token for protected endpoints
            timeout: Request timeout in seconds
            use_async: If True, uses async client; if False, uses sync client
            **httpx_kwargs: Additional arguments passed to httpx.AsyncClient
        """
        self.base_url = base_url
        self.auth_token = auth_token
        self.timeout = timeout
        self.use_async = use_async
        self.httpx_kwargs = httpx_kwargs

        # Dynamically load the appropriate client implementation
        if use_async:
            self._client = ClientAsync(
                base_url=base_url,
                auth_token=auth_token,
                timeout=timeout,
                **httpx_kwargs,
            )
        else:
            self._client = Client(
                base_url, auth_token=auth_token, timeout=timeout, **httpx_kwargs
            )

    # Context manager support for async client
    async def __aenter__(self):
        """Async context manager entry."""
        if self.use_async and hasattr(self._client, "__aenter__"):
            return await self._client.__aenter__()  # type: ignore
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.use_async and hasattr(self._client, "__aexit__"):
            await self._client.__aexit__(exc_type, exc_val, exc_tb)  # type: ignore

    async def close(self):
        """Close the HTTP client (async only)."""
        if self.use_async and hasattr(self._client, "close"):
            await self._client.close()  # type: ignore

    def health_check(self) -> Union[HealthResponse, Awaitable[HealthResponse]]:
        """
        Perform a health check on the server.

        Returns:
            HealthResponse or Awaitable[HealthResponse]: Server health status
        """
        return self._client.health_check()

    def get_settings(self) -> Union[ServerSettings, Awaitable[ServerSettings]]:
        """
        Get server settings.

        Returns:
            ServerSettings or Awaitable[ServerSettings]: Current server settings
        """
        return self._client.get_settings()

    def get_info(self) -> Union[ServerInfo, Awaitable[ServerInfo]]:
        """
        Get server information including available examples and statistics.

        Returns:
            ServerInfo or Awaitable[ServerInfo]: Server information and statistics
        """
        return self._client.get_info()

    def is_compiler_in_use(
        self,
    ) -> Union[CompilerInUseResponse, Awaitable[CompilerInUseResponse]]:
        """
        Check if the compiler is currently in use.

        Returns:
            CompilerInUseResponse or Awaitable[CompilerInUseResponse]: Compiler usage status
        """
        return self._client.is_compiler_in_use()

    def shutdown_server(self) -> Union[Dict[str, str], Awaitable[Dict[str, str]]]:
        """
        Shutdown the server (if allowed by server configuration).

        Returns:
            Dict[str, str] or Awaitable[Dict[str, str]]: Shutdown status
        """
        return self._client.shutdown_server()

    def init_project(
        self, example: Optional[str] = None
    ) -> Union[bytes, Awaitable[bytes]]:
        """
        Initialize a new project with default or specified example.

        Args:
            example: Optional example name. If None, uses default example.

        Returns:
            bytes or Awaitable[bytes]: ZIP file content of the initialized project
        """
        return self._client.init_project(example)

    def get_dwarf_source(self, path: str) -> Union[str, Awaitable[str]]:
        """
        Get source file content for debugging.

        Args:
            path: Path to the source file

        Returns:
            str or Awaitable[str]: Source file content
        """
        return self._client.get_dwarf_source(path)

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
    ) -> Union[bytes, Awaitable[bytes]]:
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
            bytes or Awaitable[bytes]: Compiled WASM file content
        """
        return self._client.compile_wasm(
            file_path,
            build,
            profile,
            strict,
            no_platformio,
            native,
            session_id,
            allow_libcompile=allow_libcompile,
        )

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
    ) -> Union[bytes, Awaitable[bytes]]:
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
            bytes or Awaitable[bytes]: Compiled WASM file content
        """
        return self._client.compile_wasm_with_file_content(
            file_content,
            filename,
            build,
            profile,
            strict,
            no_platformio,
            native,
            session_id,
        )

    def compile_libfastled(
        self, build: Optional[str] = None, dry_run: bool = False
    ) -> Optional[AsyncGenerator[str, None]]:
        """
        Compile libfastled library and stream the compilation output.
        Only available for async client.

        Args:
            build: Build type (quick, debug, release)
            dry_run: If True, performs a dry run without actual compilation

        Returns:
            AsyncGenerator[str, None] or None: Compilation output lines (async only)
        """
        if self.use_async and hasattr(self._client, "compile_libfastled"):
            return self._client.compile_libfastled(build, dry_run)  # type: ignore
        else:
            raise NotImplementedError(
                "compile_libfastled is only available for async client"
            )

    @property
    def client(self):
        """Access to the underlying client implementation."""
        return self._client


__all__ = [
    "FastLEDWasmAPI",
    "Client",
    "ClientAsync",
    "ServerSettings",
    "ServerInfo",
    "CompilerInUseResponse",
    "HealthResponse",
    "DwarfSourceRequest",
]
