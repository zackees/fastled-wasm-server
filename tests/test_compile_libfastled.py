"""Tests for libfastled compilation functionality."""

from fastapi.testclient import TestClient

# Import the FastAPI app
from fastled_wasm_server.server import app


class TestCompileLibfastledEndpoint:
    """Test the /compile/libfastled endpoint."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_compile_libfastled_dry_run_quick(self):
        """Test /compile/libfastled endpoint with dry_run=True and QUICK mode."""
        with self.client.stream(
            "POST",
            "/compile/libfastled",
            headers={
                "authorization": "oBOT5jbsO4ztgrpNsQwlmFLIKB",  # Use the actual auth token
                "build": "quick",
                "dry-run": "true",  # Use hyphen instead of underscore
            },
        ) as response:
            # Check response status
            assert response.status_code == 200

            # Read the streaming content
            content = ""
            for chunk in response.iter_text():
                content += chunk

            # Check response content
            assert "Using BUILD_MODE: QUICK" in content
            assert "DRY RUN MODE: Will skip actual compilation" in content
            assert "Would compile libfastled with BUILD_MODE=QUICK" in content
            assert "STATUS: SUCCESS" in content

    def test_compile_libfastled_dry_run_debug(self):
        """Test /compile/libfastled endpoint with dry_run=True and DEBUG mode."""
        with self.client.stream(
            "POST",
            "/compile/libfastled",
            headers={
                "authorization": "oBOT5jbsO4ztgrpNsQwlmFLIKB",
                "build": "debug",
                "dry-run": "true",  # Use hyphen instead of underscore
            },
        ) as response:
            assert response.status_code == 200

            content = ""
            for chunk in response.iter_text():
                content += chunk

            assert "Using BUILD_MODE: DEBUG" in content
            assert "Would compile libfastled with BUILD_MODE=DEBUG" in content

    def test_compile_libfastled_dry_run_release(self):
        """Test /compile/libfastled endpoint with dry_run=True and RELEASE mode."""
        with self.client.stream(
            "POST",
            "/compile/libfastled",
            headers={
                "authorization": "oBOT5jbsO4ztgrpNsQwlmFLIKB",
                "build": "release",
                "dry-run": "true",  # Use hyphen instead of underscore
            },
        ) as response:
            assert response.status_code == 200

            content = ""
            for chunk in response.iter_text():
                content += chunk

            assert "Using BUILD_MODE: RELEASE" in content
            assert "Would compile libfastled with BUILD_MODE=RELEASE" in content

    def test_compile_libfastled_without_dry_run(self):
        """Test /compile/libfastled endpoint without dry_run (shows environment error)."""
        with self.client.stream(
            "POST",
            "/compile/libfastled",
            headers={
                "authorization": "oBOT5jbsO4ztgrpNsQwlmFLIKB",
                "build": "quick",
                "dry-run": "false",  # Use hyphen instead of underscore
            },
        ) as response:
            assert response.status_code == 200

            content = ""
            for chunk in response.iter_text():
                content += chunk

            assert "Starting libfastled compilation..." in content
            assert (
                "ERROR: libfastled compilation requires a properly configured environment"
                in content
            )
            assert "STATUS: FAIL" in content

    def test_compile_libfastled_default_dry_run_false(self):
        """Test that /compile/libfastled defaults to dry_run=False."""
        with self.client.stream(
            "POST",
            "/compile/libfastled",
            headers={
                "authorization": "oBOT5jbsO4ztgrpNsQwlmFLIKB",
                "build": "quick",
                # No dry-run header - should default to False
            },
        ) as response:
            assert response.status_code == 200

            content = ""
            for chunk in response.iter_text():
                content += chunk

            assert "Starting libfastled compilation..." in content
            assert (
                "ERROR: libfastled compilation requires a properly configured environment"
                in content
            )
            assert "STATUS: FAIL" in content

    def test_compile_libfastled_unauthorized(self):
        """Test /compile/libfastled endpoint without proper authorization."""
        response = self.client.post(
            "/compile/libfastled",
            headers={
                "authorization": "wrong_token",
                "build": "quick",
                "dry-run": "true",  # Use hyphen instead of underscore
            },
        )

        assert response.status_code == 401
        assert "Unauthorized" in response.json()["detail"]
