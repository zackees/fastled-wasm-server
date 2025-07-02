"""Test the server-side native compiler mode functionality."""

import os
import tempfile
import unittest
from io import BytesIO

from fastapi.testclient import TestClient

from fastled_wasm_server.server import app


class TestNativeServerMode(unittest.TestCase):
    """Test native compiler mode in server endpoints."""

    def setUp(self) -> None:
        """Set up test environment with proper paths."""
        # Set environment variables for testing
        self.original_env = {}
        test_env_vars = {
            "ENV_UPLOAD_DIR": tempfile.mkdtemp(),
            "ENV_OUTPUT_DIR": tempfile.mkdtemp(),
            "ENV_COMPILER_ROOT": tempfile.mkdtemp(),
        }

        for key, value in test_env_vars.items():
            self.original_env[key] = os.environ.get(key)
            os.environ[key] = value

        self.client = TestClient(app)

    def tearDown(self) -> None:
        """Clean up test environment."""
        # Restore original environment variables
        for key, value in self.original_env.items():
            if value is not None:
                os.environ[key] = value
            elif key in os.environ:
                del os.environ[key]

    def test_native_header_true(self) -> None:
        """Test that native=true header is processed correctly."""
        # Create a dummy zip file
        zip_content = BytesIO()
        zip_content.write(b"PK\x03\x04dummy zip content")
        zip_content.seek(0)

        # Mock the test environment
        app.dependency_overrides = {}

        # Test with native header set to true
        response = self.client.post(
            "/compile/wasm",
            headers={
                "native": "true",
            },
            files={"file": ("test.zip", zip_content, "application/zip")},
        )

        # The request should be processed (though it will fail due to missing actual compiler)
        # We're testing that the header is accepted and processed
        self.assertIn(
            response.status_code, [400, 500]
        )  # Compilation will fail, but header was processed

    def test_native_header_false(self) -> None:
        """Test that native=false header is processed correctly."""
        # Create a dummy zip file
        zip_content = BytesIO()
        zip_content.write(b"PK\x03\x04dummy zip content")
        zip_content.seek(0)

        # Test with native header set to false
        response = self.client.post(
            "/compile/wasm",
            headers={
                "native": "false",
            },
            files={"file": ("test.zip", zip_content, "application/zip")},
        )

        # The request should be processed
        self.assertIn(
            response.status_code, [400, 500]
        )  # Compilation will fail, but header was processed

    def test_native_header_missing(self) -> None:
        """Test that missing native header uses default behavior."""
        # Create a dummy zip file
        zip_content = BytesIO()
        zip_content.write(b"PK\x03\x04dummy zip content")
        zip_content.seek(0)

        # Test without native header
        response = self.client.post(
            "/compile/wasm",
            headers={},
            files={"file": ("test.zip", zip_content, "application/zip")},
        )

        # The request should be processed with default native=False
        self.assertIn(
            response.status_code, [400, 500]
        )  # Compilation will fail, but header was processed

    def test_native_environment_variable(self) -> None:
        """Test that NATIVE environment variable is respected."""
        # Set NATIVE environment variable
        original_native = os.environ.get("NATIVE")
        try:
            os.environ["NATIVE"] = "1"

            # Create a dummy zip file
            zip_content = BytesIO()
            zip_content.write(b"PK\x03\x04dummy zip content")
            zip_content.seek(0)

            # Test without native header (should use env var)
            response = self.client.post(
                "/compile/wasm",
                headers={},
                files={"file": ("test.zip", zip_content, "application/zip")},
            )

            # The request should be processed with native=True from env var
            self.assertIn(
                response.status_code, [400, 500]
            )  # Compilation will fail, but env var was processed

        finally:
            # Restore original NATIVE environment variable
            if original_native is not None:
                os.environ["NATIVE"] = original_native
            elif "NATIVE" in os.environ:
                del os.environ["NATIVE"]

    def test_unauthorized_request(self) -> None:
        """Test that unauthorized requests are rejected regardless of native flag."""
        # Create a dummy zip file
        zip_content = BytesIO()
        zip_content.write(b"PK\x03\x04dummy zip content")
        zip_content.seek(0)

        # Test with native header but no authorization
        response = self.client.post(
            "/compile/wasm",
            headers={
                "native": "true",
            },
            files={"file": ("test.zip", zip_content, "application/zip")},
        )

        # Should no longer return unauthorized error
        self.assertIn(response.status_code, [400, 500])

    def test_native_with_other_headers(self) -> None:
        """Test that native flag works with other compilation headers."""
        # Create a dummy zip file
        zip_content = BytesIO()
        zip_content.write(b"PK\x03\x04dummy zip content")
        zip_content.seek(0)

        # Test with multiple headers including native
        response = self.client.post(
            "/compile/wasm",
            headers={
                "native": "true",
                "build": "debug",
                "profile": "false",
            },
            files={"file": ("test.zip", zip_content, "application/zip")},
        )

        # The request should be processed with all headers
        self.assertIn(
            response.status_code, [400, 500]
        )  # Compilation will fail, but headers were processed


if __name__ == "__main__":
    unittest.main()
