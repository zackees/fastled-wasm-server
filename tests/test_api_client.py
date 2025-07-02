"""Tests for the FastLED WASM Server API Client."""

from unittest.mock import Mock, patch

import pytest

from fastled_wasm_server.api_client import (
    CompilerInUseResponse,
    FastLEDWasmClient,
    FastLEDWasmSyncClient,
    HealthResponse,
    ServerInfo,
    ServerSettings,
)


class TestFastLEDWasmClient:
    """Test cases for the async FastLED WASM client."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return FastLEDWasmClient("http://localhost:8080")

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check endpoint."""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "ok"}
        mock_response.raise_for_status = Mock()

        with patch.object(
            client._client, "get", return_value=mock_response
        ) as mock_get:
            result = await client.health_check()

            mock_get.assert_called_once_with("/healthz")
            assert isinstance(result, HealthResponse)
            assert result.status == "ok"

    @pytest.mark.asyncio
    async def test_get_settings(self, client):
        """Test get settings endpoint."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "ALLOW_SHUTDOWN": True,
            "NO_AUTO_UPDATE": "0",
            "NO_SKETCH_CACHE": False,
            "LIVE_GIT_UPDATES_ENABLED": False,
            "LIVE_GIT_UPDATES_INTERVAL": 86400,
            "UPLOAD_LIMIT": 10485760,
            "VOLUME_MAPPED_SRC": "/path/to/src",
            "VOLUME_MAPPED_SRC_EXISTS": True,
        }
        mock_response.raise_for_status = Mock()

        with patch.object(
            client._client, "get", return_value=mock_response
        ) as mock_get:
            result = await client.get_settings()

            mock_get.assert_called_once_with("/settings")
            assert isinstance(result, ServerSettings)
            assert result.ALLOW_SHUTDOWN is True
            assert result.UPLOAD_LIMIT == 10485760

    @pytest.mark.asyncio
    async def test_get_info(self, client):
        """Test get info endpoint."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "examples": ["example1", "example2"],
            "compile_count": 42,
            "compile_failures": 2,
            "compile_successes": 40,
            "uptime": "01:23:45",
            "build_timestamp": "2024-01-01T00:00:00Z",
            "fastled_version": "3.6.0",
            "available_builds": ["quick", "release", "debug"],
        }
        mock_response.raise_for_status = Mock()

        with patch.object(
            client._client, "get", return_value=mock_response
        ) as mock_get:
            result = await client.get_info()

            mock_get.assert_called_once_with("/info")
            assert isinstance(result, ServerInfo)
            assert result.examples == ["example1", "example2"]
            assert result.compile_count == 42
            assert result.fastled_version == "3.6.0"

    @pytest.mark.asyncio
    async def test_is_compiler_in_use(self, client):
        """Test compiler in use check endpoint."""
        mock_response = Mock()
        mock_response.json.return_value = {"in_use": False}
        mock_response.raise_for_status = Mock()

        with patch.object(
            client._client, "get", return_value=mock_response
        ) as mock_get:
            result = await client.is_compiler_in_use()

            mock_get.assert_called_once_with("/compile/wasm/inuse")
            assert isinstance(result, CompilerInUseResponse)
            assert result.in_use is False

    @pytest.mark.asyncio
    async def test_init_project_default(self, client):
        """Test project initialization with default example."""
        mock_response = Mock()
        mock_response.content = b"fake_zip_content"
        mock_response.raise_for_status = Mock()

        with patch.object(
            client._client, "get", return_value=mock_response
        ) as mock_get:
            result = await client.init_project()

            mock_get.assert_called_once_with("/project/init")
            assert result == b"fake_zip_content"

    @pytest.mark.asyncio
    async def test_init_project_with_example(self, client):
        """Test project initialization with specific example."""
        mock_response = Mock()
        mock_response.content = b"fake_zip_content"
        mock_response.raise_for_status = Mock()

        with patch.object(
            client._client, "post", return_value=mock_response
        ) as mock_post:
            result = await client.init_project("test_example")

            mock_post.assert_called_once_with("/project/init", content="test_example")
            assert result == b"fake_zip_content"

    @pytest.mark.asyncio
    async def test_get_dwarf_source(self, client):
        """Test dwarf source retrieval."""
        mock_response = Mock()
        mock_response.text = "source code content"
        mock_response.raise_for_status = Mock()

        with patch.object(
            client._client, "post", return_value=mock_response
        ) as mock_post:
            result = await client.get_dwarf_source("/path/to/source.cpp")

            mock_post.assert_called_once_with(
                "/dwarfsource", json={"path": "/path/to/source.cpp"}
            )
            assert result == "source code content"

    @pytest.mark.asyncio
    async def test_compile_wasm_with_file_content(self, client):
        """Test WASM compilation with file content."""
        mock_response = Mock()
        mock_response.content = b"fake_wasm_content"
        mock_response.raise_for_status = Mock()

        file_content = b"test sketch content"
        filename = "test.ino"

        with patch.object(
            client._client, "post", return_value=mock_response
        ) as mock_post:
            result = await client.compile_wasm_with_file_content(
                file_content=file_content, filename=filename, build="quick", strict=True
            )

            # Verify the call was made with correct parameters
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "/compile/wasm"

            # Check headers
            headers = call_args[1]["headers"]
            assert headers["Authorization"] == client.auth_token
            assert headers["build"] == "quick"
            assert headers["strict"] == "true"

            # Check files
            files = call_args[1]["files"]
            assert files["file"][0] == filename
            assert files["file"][1] == file_content

            assert result == b"fake_wasm_content"

    @pytest.mark.asyncio
    async def test_auth_headers(self, client):
        """Test that auth headers are properly set."""
        headers = client._get_auth_headers()
        assert headers["Authorization"] == client.auth_token

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality."""
        async with FastLEDWasmClient("http://localhost:8080") as client:
            assert client is not None
            assert isinstance(client, FastLEDWasmClient)


class TestFastLEDWasmSyncClient:
    """Test cases for the sync FastLED WASM client."""

    def test_init(self):
        """Test synchronous client initialization."""
        client = FastLEDWasmSyncClient("http://localhost:8080", auth_token="test_token")
        assert client._client_args == ("http://localhost:8080",)
        assert client._client_kwargs["auth_token"] == "test_token"

    @patch("asyncio.run")
    def test_health_check_sync(self, mock_asyncio_run):
        """Test synchronous health check."""
        mock_health_response = HealthResponse(status="ok")
        mock_asyncio_run.return_value = mock_health_response

        client = FastLEDWasmSyncClient("http://localhost:8080")
        result = client.health_check()

        assert result == mock_health_response
        mock_asyncio_run.assert_called_once()


class TestAPIClientIntegration:
    """Integration-style tests for API client."""

    def test_client_initialization_with_different_options(self):
        """Test client initialization with various options."""
        # Test with minimal options
        client1 = FastLEDWasmClient("http://localhost:8080")
        assert client1.base_url == "http://localhost:8080"
        assert client1.auth_token == "oBOT5jbsO4ztgrpNsQwlmFLIKB"
        assert client1.timeout == 30.0

        # Test with custom options
        client2 = FastLEDWasmClient(
            "http://example.com:9000/", auth_token="custom_token", timeout=60.0
        )
        assert client2.base_url == "http://example.com:9000"
        assert client2.auth_token == "custom_token"
        assert client2.timeout == 60.0

        # Test sync client
        sync_client = FastLEDWasmSyncClient("http://localhost:8080", timeout=45.0)
        assert sync_client._client_kwargs["timeout"] == 45.0

    def test_response_models_creation(self):
        """Test that response models can be created correctly."""
        # Test HealthResponse
        health = HealthResponse(status="ok")
        assert health.status == "ok"

        # Test ServerSettings
        settings = ServerSettings(
            ALLOW_SHUTDOWN=True,
            NO_AUTO_UPDATE="0",
            NO_SKETCH_CACHE=False,
            LIVE_GIT_UPDATES_ENABLED=False,
            LIVE_GIT_UPDATES_INTERVAL=86400,
            UPLOAD_LIMIT=10485760,
            VOLUME_MAPPED_SRC="/path/to/src",
            VOLUME_MAPPED_SRC_EXISTS=True,
        )
        assert settings.ALLOW_SHUTDOWN is True
        assert settings.UPLOAD_LIMIT == 10485760

        # Test ServerInfo
        info = ServerInfo(
            examples=["example1"],
            compile_count=10,
            compile_failures=1,
            compile_successes=9,
            uptime="01:00:00",
            build_timestamp="2024-01-01T00:00:00Z",
            fastled_version="3.6.0",
            available_builds=["quick"],
        )
        assert info.examples == ["example1"]
        assert info.compile_count == 10
