"""
FastLED WASM Server API Client

This module provides a comprehensive HTTP client for interacting with the FastLED WASM server.
The client handles all available endpoints with proper typing and error handling.
"""

import asyncio
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

import httpx
from pydantic import BaseModel

from .types import BuildMode


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
    NO_SKETCH_CACHE: bool
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


class FastLEDWasmClient:
    """
    HTTP client for FastLED WASM server.
    
    This client provides methods for all available server endpoints including:
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
        **httpx_kwargs
    ):
        """
        Initialize the FastLED WASM client.
        
        Args:
            base_url: Base URL of the FastLED WASM server
            auth_token: Authorization token for protected endpoints
            timeout: Request timeout in seconds
            **httpx_kwargs: Additional arguments passed to httpx.AsyncClient
        """
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            **httpx_kwargs
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
        response = await self._client.post(
            "/dwarfsource",
            json=request.dict()
        )
        response.raise_for_status()
        return response.text
    
    async def compile_wasm(
        self,
        file_path: Union[str, Path],
        build: Optional[str] = None,
        profile: Optional[str] = None,
        strict: bool = False,
        no_platformio: Optional[bool] = None,
        native: Optional[bool] = None,
        session_id: Optional[int] = None,
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
        
        # Prepare file upload
        file_path = Path(file_path)
        
        with open(file_path, 'rb') as f:
            files = {"file": (file_path.name, f, "application/octet-stream")}
            
            response = await self._client.post(
                "/compile/wasm",
                headers=headers,
                files=files
            )
        
        response.raise_for_status()
        return response.content
    
    async def compile_libfastled(
        self,
        build: Optional[str] = None,
        dry_run: bool = False
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
            "POST",
            "/compile/libfastled",
            headers=headers
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
        
        # Prepare file upload
        files = {"file": (filename, file_content, "application/octet-stream")}
        
        response = await self._client.post(
            "/compile/wasm",
            headers=headers,
            files=files
        )
        
        response.raise_for_status()
        return response.content


# Synchronous wrapper class for convenience
class FastLEDWasmSyncClient:
    """
    Synchronous wrapper for FastLEDWasmClient.
    
    This class provides synchronous methods that internally use asyncio
    to run the async operations.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize with same arguments as FastLEDWasmClient."""
        self._client_args = args
        self._client_kwargs = kwargs
    
    def _run_async(self, coro):
        """Run an async coroutine synchronously."""
        try:
            loop = asyncio.get_running_loop()
            # If we're already in an event loop, we need to run in a thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        except RuntimeError:
            # No event loop running, we can use asyncio.run
            return asyncio.run(coro)
    
    async def _get_client(self):
        """Get async client instance."""
        return FastLEDWasmClient(*self._client_args, **self._client_kwargs)
    
    def health_check(self) -> HealthResponse:
        """Synchronous health check."""
        async def _health_check():
            async with await self._get_client() as client:
                return await client.health_check()
        return self._run_async(_health_check())
    
    def get_settings(self) -> ServerSettings:
        """Synchronous get settings."""
        async def _get_settings():
            async with await self._get_client() as client:
                return await client.get_settings()
        return self._run_async(_get_settings())
    
    def get_info(self) -> ServerInfo:
        """Synchronous get info."""
        async def _get_info():
            async with await self._get_client() as client:
                return await client.get_info()
        return self._run_async(_get_info())
    
    def is_compiler_in_use(self) -> CompilerInUseResponse:
        """Synchronous compiler in use check."""
        async def _is_compiler_in_use():
            async with await self._get_client() as client:
                return await client.is_compiler_in_use()
        return self._run_async(_is_compiler_in_use())
    
    def shutdown_server(self) -> Dict[str, str]:
        """Synchronous server shutdown."""
        async def _shutdown_server():
            async with await self._get_client() as client:
                return await client.shutdown_server()
        return self._run_async(_shutdown_server())
    
    def init_project(self, example: Optional[str] = None) -> bytes:
        """Synchronous project initialization."""
        async def _init_project():
            async with await self._get_client() as client:
                return await client.init_project(example)
        return self._run_async(_init_project())
    
    def get_dwarf_source(self, path: str) -> str:
        """Synchronous dwarf source retrieval."""
        async def _get_dwarf_source():
            async with await self._get_client() as client:
                return await client.get_dwarf_source(path)
        return self._run_async(_get_dwarf_source())
    
    def compile_wasm(
        self,
        file_path: Union[str, Path],
        build: Optional[str] = None,
        profile: Optional[str] = None,
        strict: bool = False,
        no_platformio: Optional[bool] = None,
        native: Optional[bool] = None,
        session_id: Optional[int] = None,
    ) -> bytes:
        """Synchronous WASM compilation."""
        async def _compile_wasm():
            async with await self._get_client() as client:
                return await client.compile_wasm(
                    file_path, build, profile, strict, no_platformio, native, session_id
                )
        return self._run_async(_compile_wasm())
    
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
    ) -> bytes:
        """Synchronous WASM compilation from content."""
        async def _compile_wasm_content():
            async with await self._get_client() as client:
                return await client.compile_wasm_with_file_content(
                    file_content, filename, build, profile, strict, no_platformio, native, session_id
                )
        return self._run_async(_compile_wasm_content())