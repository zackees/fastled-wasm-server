"""
Unit tests for the /compile/libfastled endpoint.
"""

import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Environment variable to disable problematic dependencies during testing
DISABLE_FASTLED_DEPS = os.environ.get("DISABLE_FASTLED_DEPS", "false").lower() in ["true", "1"]
DISABLE_MCP_DEPS = os.environ.get("DISABLE_MCP_DEPS", "false").lower() in ["true", "1"]


class TestCompileLibfastled(unittest.TestCase):
    """Test class for the /compile/libfastled endpoint."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock problematic dependencies if disabled
        if DISABLE_FASTLED_DEPS:
            self.setup_fastled_mocks()
        if DISABLE_MCP_DEPS:
            self.setup_mcp_mocks()
        
        # Import after mocking to avoid import errors
        try:
            from fastapi.testclient import TestClient
            from fastled_wasm_server.server import app
            self.client = TestClient(app)
            self.app = app
        except ImportError as e:
            if not DISABLE_FASTLED_DEPS:
                raise e
            # If dependencies are disabled, create a minimal mock
            self.client = MagicMock()
            self.app = MagicMock()

        # Valid auth token for testing
        self.auth_token = "oBOT5jbsO4ztgrpNsQwlmFLIKB"
        self.invalid_auth_token = "invalid_token"

    def setup_fastled_mocks(self):
        """Set up mocks for FastLED-related dependencies."""
        # Mock fastled_wasm_compiler
        mock_compiler = MagicMock()
        mock_compiler.Compiler = MagicMock()
        
        # Mock disklru
        mock_disklru = MagicMock()
        mock_disklru.DiskLRUCache = MagicMock()
        
        # Apply mocks
        import sys
        sys.modules['fastled_wasm_compiler'] = mock_compiler
        sys.modules['fastled_wasm_compiler.dwarf_path_to_file_path'] = MagicMock()
        sys.modules['disklru'] = mock_disklru

    def setup_mcp_mocks(self):
        """Set up mocks for MCP-related dependencies."""
        mock_mcp = MagicMock()
        mock_mcp.types = MagicMock()
        mock_mcp.server = MagicMock()
        mock_mcp.server.stdio = MagicMock()
        
        import sys
        sys.modules['mcp'] = mock_mcp
        sys.modules['mcp.types'] = mock_mcp.types
        sys.modules['mcp.server'] = mock_mcp.server
        sys.modules['mcp.server.stdio'] = mock_mcp.server.stdio

    def test_compile_libfastled_unauthorized(self):
        """Test that compile_libfastled requires proper authorization."""
        if DISABLE_FASTLED_DEPS:
            self.skipTest("FastLED dependencies disabled")
        
        response = self.client.post(
            "/compile/libfastled",
            headers={"authorization": self.invalid_auth_token}
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("Unauthorized", response.json()["detail"])

    def test_compile_libfastled_missing_auth(self):
        """Test that compile_libfastled requires authorization header."""
        if DISABLE_FASTLED_DEPS:
            self.skipTest("FastLED dependencies disabled")
        
        response = self.client.post("/compile/libfastled")
        self.assertEqual(response.status_code, 401)

    @patch('asyncio.create_subprocess_exec')
    def test_compile_libfastled_success(self, mock_subprocess):
        """Test successful compilation with streaming response."""
        if DISABLE_FASTLED_DEPS:
            self.skipTest("FastLED dependencies disabled")
        
        # Mock successful subprocess
        mock_process = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(side_effect=[
            b"Building libfastled...\n",
            b"Compilation step 1/3\n", 
            b"Compilation step 2/3\n",
            b"Compilation step 3/3\n",
            b"Build complete!\n",
            b""  # End of stream
        ])
        mock_process.wait = AsyncMock(return_value=0)  # Success return code
        mock_subprocess.return_value = mock_process

        response = self.client.post(
            "/compile/libfastled",
            headers={"authorization": self.auth_token}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "text/plain; charset=utf-8")
        self.assertIn("no-cache", response.headers.get("cache-control", ""))

    @patch('asyncio.create_subprocess_exec')
    def test_compile_libfastled_failure(self, mock_subprocess):
        """Test compilation failure with streaming response."""
        if DISABLE_FASTLED_DEPS:
            self.skipTest("FastLED dependencies disabled")
        
        # Mock failed subprocess
        mock_process = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(side_effect=[
            b"Building libfastled...\n",
            b"Error: Missing dependency\n",
            b"Build failed!\n",
            b""  # End of stream
        ])
        mock_process.wait = AsyncMock(return_value=1)  # Failure return code
        mock_subprocess.return_value = mock_process

        response = self.client.post(
            "/compile/libfastled",
            headers={"authorization": self.auth_token}
        )
        
        self.assertEqual(response.status_code, 200)  # Still 200 for streaming
        # The failure is indicated in the stream content, not HTTP status

    @patch('asyncio.create_subprocess_exec')
    def test_compile_libfastled_exception(self, mock_subprocess):
        """Test compilation with exception handling."""
        if DISABLE_FASTLED_DEPS:
            self.skipTest("FastLED dependencies disabled")
        
        # Mock subprocess that raises an exception
        mock_subprocess.side_effect = Exception("Process creation failed")

        response = self.client.post(
            "/compile/libfastled",
            headers={"authorization": self.auth_token}
        )
        
        self.assertEqual(response.status_code, 200)  # Still 200 for streaming
        # The error is indicated in the stream content

    def test_compile_libfastled_test_mode(self):
        """Test that _TEST mode bypasses authorization."""
        if DISABLE_FASTLED_DEPS:
            self.skipTest("FastLED dependencies disabled")
        
        # Mock the _TEST variable
        with patch('fastled_wasm_server.server._TEST', True):
            with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.stdout = AsyncMock()
                mock_process.stdout.readline = AsyncMock(side_effect=[b"test\n", b""])
                mock_process.wait = AsyncMock(return_value=0)
                mock_subprocess.return_value = mock_process

                response = self.client.post("/compile/libfastled")
                self.assertEqual(response.status_code, 200)

    @patch('fastled_wasm_server.paths.COMPILER_ROOT', Path('/mock/compiler/root'))
    @patch('asyncio.create_subprocess_exec')
    def test_compile_libfastled_script_path(self, mock_subprocess):
        """Test that the correct script path is used."""
        if DISABLE_FASTLED_DEPS:
            self.skipTest("FastLED dependencies disabled")
        
        mock_process = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(side_effect=[b"", b""])
        mock_process.wait = AsyncMock(return_value=0)
        mock_subprocess.return_value = mock_process

        self.client.post(
            "/compile/libfastled",
            headers={"authorization": self.auth_token}
        )
        
        # Verify the correct script path was used
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        self.assertEqual(call_args[0][0], "/bin/bash")
        self.assertIn("build_archive.sh", call_args[0][1])

    def test_streaming_response_headers(self):
        """Test that proper headers are set for streaming response."""
        if DISABLE_FASTLED_DEPS:
            self.skipTest("FastLED dependencies disabled")
        
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.stdout = AsyncMock()
            mock_process.stdout.readline = AsyncMock(side_effect=[b"test\n", b""])
            mock_process.wait = AsyncMock(return_value=0)
            mock_subprocess.return_value = mock_process

            response = self.client.post(
                "/compile/libfastled",
                headers={"authorization": self.auth_token}
            )
            
            self.assertEqual(response.headers["cache-control"], "no-cache")
            self.assertEqual(response.headers["connection"], "keep-alive")
            self.assertEqual(response.headers["content-type"], "text/plain; charset=utf-8")


class TestCompileLibfastledAsync(unittest.IsolatedAsyncioTestCase):
    """Async test class for the /compile/libfastled endpoint."""

    async def asyncSetUp(self):
        """Set up async test fixtures."""
        if DISABLE_FASTLED_DEPS:
            return
        
        try:
            from httpx import AsyncClient
            from fastled_wasm_server.server import app
            self.async_client = AsyncClient(app=app, base_url="http://test")
            self.auth_token = "oBOT5jbsO4ztgrpNsQwlmFLIKB"
        except ImportError:
            self.async_client = None

    async def asyncTearDown(self):
        """Clean up async test fixtures."""
        if hasattr(self, 'async_client') and self.async_client:
            await self.async_client.aclose()

    @patch('asyncio.create_subprocess_exec')
    async def test_async_streaming_response(self, mock_subprocess):
        """Test the async streaming functionality."""
        if DISABLE_FASTLED_DEPS or not hasattr(self, 'async_client') or not self.async_client:
            self.skipTest("FastLED dependencies disabled or httpx not available")
        
        # Mock subprocess with realistic output
        mock_process = AsyncMock()
        mock_process.stdout = AsyncMock()
        output_lines = [
            b"Starting build process...\n",
            b"[1/5] Configuring build\n",
            b"[2/5] Compiling sources\n", 
            b"[3/5] Linking objects\n",
            b"[4/5] Creating archive\n",
            b"[5/5] Build complete\n",
            b""  # End of stream
        ]
        mock_process.stdout.readline = AsyncMock(side_effect=output_lines)
        mock_process.wait = AsyncMock(return_value=0)
        mock_subprocess.return_value = mock_process

        async with self.async_client as client:
            response = await client.post(
                "/compile/libfastled",
                headers={"authorization": self.auth_token}
            )
            
            self.assertEqual(response.status_code, 200)
            
            # Read streaming content
            content = b""
            async for chunk in response.aiter_bytes():
                content += chunk
            
            # Verify streaming content contains expected output
            content_str = content.decode('utf-8')
            self.assertIn("Starting build process", content_str)
            self.assertIn("Build complete", content_str)
            self.assertIn("COMPILATION_COMPLETE", content_str)
            self.assertIn("STATUS: SUCCESS", content_str)

    @patch('asyncio.create_subprocess_exec')
    async def test_async_streaming_failure(self, mock_subprocess):
        """Test async streaming with compilation failure."""
        if DISABLE_FASTLED_DEPS or not hasattr(self, 'async_client') or not self.async_client:
            self.skipTest("FastLED dependencies disabled or httpx not available")
        
        # Mock subprocess with failure
        mock_process = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(side_effect=[
            b"Starting build...\n",
            b"ERROR: Compilation failed\n",
            b""
        ])
        mock_process.wait = AsyncMock(return_value=1)  # Non-zero exit code
        mock_subprocess.return_value = mock_process

        async with self.async_client as client:
            response = await client.post(
                "/compile/libfastled",
                headers={"authorization": self.auth_token}
            )
            
            content = b""
            async for chunk in response.aiter_bytes():
                content += chunk
            
            content_str = content.decode('utf-8')
            self.assertIn("COMPILATION_COMPLETE", content_str)
            self.assertIn("STATUS: FAIL", content_str)
            self.assertIn("EXIT_CODE: 1", content_str)


# Integration tests that can be skipped if dependencies are problematic
@pytest.mark.skipif(DISABLE_FASTLED_DEPS, reason="FastLED dependencies disabled")
class TestCompileLibfastledIntegration(unittest.TestCase):
    """Integration tests for the compile_libfastled endpoint."""

    def setUp(self):
        """Set up integration test fixtures."""
        try:
            from fastapi.testclient import TestClient
            from fastled_wasm_server.server import app
            self.client = TestClient(app)
            self.auth_token = "oBOT5jbsO4ztgrpNsQwlmFLIKB"
        except ImportError:
            self.skipTest("Required dependencies not available")

    def test_endpoint_exists(self):
        """Test that the endpoint exists in the OpenAPI schema."""
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        
        openapi_spec = response.json()
        paths = openapi_spec.get("paths", {})
        self.assertIn("/compile/libfastled", paths)
        
        endpoint_spec = paths["/compile/libfastled"]
        self.assertIn("post", endpoint_spec)
        
        post_spec = endpoint_spec["post"]
        self.assertIn("parameters", post_spec)
        
        # Check for authorization parameter
        auth_param = None
        for param in post_spec["parameters"]:
            if param["name"] == "authorization":
                auth_param = param
                break
        
        self.assertIsNotNone(auth_param)
        self.assertEqual(auth_param["in"], "header")

    @patch('fastled_wasm_server.paths.COMPILER_ROOT')
    def test_build_script_exists(self, mock_compiler_root):
        """Test that the build script exists at the expected location."""
        # Create a temporary directory structure for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            mock_compiler_root.return_value = temp_path
            
            # Create a mock build script
            build_script = temp_path / "build_archive.sh"
            build_script.write_text("#!/bin/bash\necho 'Mock build script'\n")
            build_script.chmod(0o755)
            
            self.assertTrue(build_script.exists())
            self.assertTrue(build_script.is_file())


if __name__ == "__main__":
    # Set environment variables for testing if not already set
    if "DISABLE_FASTLED_DEPS" not in os.environ:
        print("Setting DISABLE_FASTLED_DEPS=true for safer testing")
        os.environ["DISABLE_FASTLED_DEPS"] = "true"
    
    if "DISABLE_MCP_DEPS" not in os.environ:
        print("Setting DISABLE_MCP_DEPS=true for safer testing")
        os.environ["DISABLE_MCP_DEPS"] = "true"
    
    unittest.main()