"""Tests for libfastled compilation functionality."""

from unittest.mock import patch

from fastapi.testclient import TestClient

# Import the FastAPI app
from fastled_wasm_server.server import app


class TestCompileLibfastledEndpoint:
    """Test the /compile/libfastled endpoint."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    @patch("fastled_wasm_server.server._NEW_COMPILER")
    def test_compile_libfastled_dry_run_quick(self, mock_compiler):
        """Test /compile/libfastled endpoint with dry_run=True and QUICK mode."""
        # Mock the update_src method
        mock_compiler.update_src.return_value = []

        response = self.client.post(
            "/compile/libfastled",
            headers={
                "authorization": "oBOT5jbsO4ztgrpNsQwlmFLIKB",  # Use the actual auth token
                "build": "quick",
                "dry-run": "true",
            },
        )

        # Check response status
        assert response.status_code == 200

        # Check response content
        content = response.text
        assert "Using BUILD_MODE: QUICK" in content
        assert "DRY RUN MODE: Will skip actual compilation" in content
        assert "Would call _NEW_COMPILER.update_src(builds=['quick'])" in content
        assert "STATUS: SUCCESS" in content

        # Verify update_src was not called for dry run
        mock_compiler.update_src.assert_not_called()

    @patch("fastled_wasm_server.server._NEW_COMPILER")
    def test_compile_libfastled_dry_run_debug(self, mock_compiler):
        """Test /compile/libfastled endpoint with dry_run=True and DEBUG mode."""
        response = self.client.post(
            "/compile/libfastled",
            headers={
                "authorization": "oBOT5jbsO4ztgrpNsQwlmFLIKB",
                "build": "debug",
                "dry-run": "true",
            },
        )

        assert response.status_code == 200
        content = response.text
        assert "Using BUILD_MODE: DEBUG" in content
        assert "Would call _NEW_COMPILER.update_src(builds=['debug'])" in content

    @patch("fastled_wasm_server.server._NEW_COMPILER")
    def test_compile_libfastled_dry_run_release(self, mock_compiler):
        """Test /compile/libfastled endpoint with dry_run=True and RELEASE mode."""
        response = self.client.post(
            "/compile/libfastled",
            headers={
                "authorization": "oBOT5jbsO4ztgrpNsQwlmFLIKB",
                "build": "release",
                "dry-run": "true",
            },
        )

        assert response.status_code == 200
        content = response.text
        assert "Using BUILD_MODE: RELEASE" in content
        assert "Would call _NEW_COMPILER.update_src(builds=['release'])" in content

    @patch("fastled_wasm_server.server._NEW_COMPILER")
    def test_compile_libfastled_without_dry_run(self, mock_compiler):
        """Test /compile/libfastled endpoint without dry_run (actual compilation)."""
        # Mock successful compilation
        mock_compiler.update_src.return_value = ["file1.cpp", "file2.h"]

        response = self.client.post(
            "/compile/libfastled",
            headers={
                "authorization": "oBOT5jbsO4ztgrpNsQwlmFLIKB",
                "build": "quick",
                "dry-run": "false",
            },
        )

        assert response.status_code == 200
        content = response.text
        assert "Starting libfastled compilation..." in content
        assert "Successfully compiled libfastled. Files changed: 2" in content
        assert "STATUS: SUCCESS" in content

        # Verify update_src was called
        mock_compiler.update_src.assert_called_once()

    @patch("fastled_wasm_server.server._NEW_COMPILER")
    def test_compile_libfastled_default_dry_run_false(self, mock_compiler):
        """Test that /compile/libfastled defaults to dry_run=False."""
        mock_compiler.update_src.return_value = []

        response = self.client.post(
            "/compile/libfastled",
            headers={
                "authorization": "oBOT5jbsO4ztgrpNsQwlmFLIKB",
                "build": "quick",
                # No dry-run header - should default to False
            },
        )

        assert response.status_code == 200
        content = response.text
        assert "Starting libfastled compilation..." in content
        assert "libfastled compilation completed (no files changed)" in content

        # Should call update_src (not dry run)
        mock_compiler.update_src.assert_called_once()

    def test_compile_libfastled_unauthorized(self):
        """Test /compile/libfastled endpoint without proper authorization."""
        response = self.client.post(
            "/compile/libfastled",
            headers={
                "authorization": "wrong_token",
                "build": "quick",
                "dry-run": "true",
            },
        )

        assert response.status_code == 401
        assert "Unauthorized" in response.json()["detail"]
