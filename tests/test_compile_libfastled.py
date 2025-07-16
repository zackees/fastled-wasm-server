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
            assert "HTTP_STATUS: 200" in content

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
            assert "DRY RUN MODE: Will skip actual compilation" in content
            assert "Would compile libfastled with BUILD_MODE=DEBUG" in content
            assert "STATUS: SUCCESS" in content
            assert "HTTP_STATUS: 200" in content

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
            assert "DRY RUN MODE: Will skip actual compilation" in content
            assert "Would compile libfastled with BUILD_MODE=RELEASE" in content
            assert "STATUS: SUCCESS" in content
            assert "HTTP_STATUS: 200" in content

    def test_compile_libfastled_without_dry_run(self):
        """Test /compile/libfastled endpoint without dry_run (returns immediate 400 error)."""
        response = self.client.post(
            "/compile/libfastled",
            headers={
                "authorization": "oBOT5jbsO4ztgrpNsQwlmFLIKB",
                "build": "quick",
                "dry-run": "false",  # Use hyphen instead of underscore
            },
        )
        # Now correctly returns 400 immediately due to missing environment
        assert response.status_code == 400
        assert "Volume mapped source directory does not exist" in response.text
        assert "properly configured environment" in response.text

    def test_compile_libfastled_default_dry_run_false(self):
        """Test that /compile/libfastled defaults to dry_run=False (returns immediate 400 error)."""
        response = self.client.post(
            "/compile/libfastled",
            headers={
                "authorization": "oBOT5jbsO4ztgrpNsQwlmFLIKB",
                "build": "quick",
                # No dry-run header - should default to False
            },
        )
        # Now correctly returns 400 immediately due to missing environment
        assert response.status_code == 400
        assert "Volume mapped source directory does not exist" in response.text
        assert "properly configured environment" in response.text

    def test_compile_libfastled_unauthorized(self):
        """Test /compile/libfastled endpoint without authorization."""
        response = self.client.post(
            "/compile/libfastled",
            headers={
                "build": "quick",
                "dry-run": "true",
            },
        )
        assert response.status_code == 401
        assert "Unauthorized" in response.text

    def test_compile_libfastled_invalid_build_mode(self):
        """Test /compile/libfastled endpoint with invalid build mode."""
        response = self.client.post(
            "/compile/libfastled",
            headers={
                "authorization": "oBOT5jbsO4ztgrpNsQwlmFLIKB",
                "build": "invalid_mode",
                "dry-run": "true",
            },
        )
        assert response.status_code == 400
        assert "Invalid build mode" in response.text
        assert "Must be one of: quick, debug, release" in response.text

    def test_compile_libfastled_streaming_output_simulation(self):
        """Test that streaming output includes real-time compilation messages."""
        import sys
        import tempfile
        from pathlib import Path
        from unittest.mock import AsyncMock, patch

        # Create a temporary directory to simulate VOLUME_MAPPED_SRC
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create minimal FastLED structure that update_src expects
            fastled_h = temp_path / "FastLED.h"
            fastled_h.write_text("// Mock FastLED.h file\n#pragma once\n")

            # Mock both the VOLUME_MAPPED_SRC and the update_src_async function
            with (
                patch("fastled_wasm_server.server.VOLUME_MAPPED_SRC", temp_path),
                patch("fastled_wasm_server.server.update_src_async") as mock_update_src,
            ):

                # Mock update_src_async to be an async generator
                async def mock_update_src_gen(*args, **kwargs):
                    yield "Starting source update check..."
                    yield "Checking for FastLED source file changes..."
                    yield "No source file changes detected"
                    yield "Source update completed"
                    # Note: async generators cannot return values, only yield them

                mock_update_src.side_effect = mock_update_src_gen

                # Create a mock script that works on Windows
                if sys.platform == "win32":
                    build_script = temp_path.parent / "build_archive.bat"
                    build_script.write_text(
                        """@echo off
echo Starting libfastled compilation...
echo Configuring cmake...
ping -n 1 127.0.0.1 >nul
echo Building with emmake...
ping -n 1 127.0.0.1 >nul
echo Compilation completed successfully
exit /b 0
"""
                    )
                else:
                    build_script = temp_path.parent / "build_archive.sh"
                    build_script.write_text(
                        """#!/bin/bash
echo "Starting libfastled compilation..."
echo "Configuring cmake..."
sleep 0.1
echo "Building with emmake..."
sleep 0.1
echo "Compilation completed successfully"
exit 0
"""
                    )
                    build_script.chmod(0o755)

                # Mock asyncio.create_subprocess_exec to simulate subprocess output
                async def mock_subprocess(*args, **kwargs):
                    mock_process = AsyncMock()
                    mock_process.returncode = 0

                    # Simulate streaming output
                    async def mock_stdout():
                        lines = [
                            b"Starting libfastled compilation...\n",
                            b"Configuring cmake...\n",
                            b"Building with emmake...\n",
                            b"Compilation completed successfully\n",
                        ]
                        for line in lines:
                            yield line

                    mock_process.stdout = mock_stdout()
                    mock_process.wait = AsyncMock(return_value=None)
                    return mock_process

                with patch(
                    "asyncio.create_subprocess_exec", side_effect=mock_subprocess
                ):
                    with self.client.stream(
                        "POST",
                        "/compile/libfastled",
                        headers={
                            "authorization": "oBOT5jbsO4ztgrpNsQwlmFLIKB",
                            "build": "quick",
                            "dry-run": "false",
                        },
                    ) as response:
                        assert response.status_code == 200

                        content = ""
                        chunks = []
                        for chunk in response.iter_text():
                            content += chunk
                            chunks.append(chunk)

                        # Verify that we get streaming output (should be multiple data: lines)
                        data_lines = [
                            line
                            for line in content.split("\n")
                            if line.startswith("data:")
                        ]
                        assert (
                            len(data_lines) > 5
                        ), f"Should receive multiple data lines for streaming, got {len(data_lines)}"

                        # Check for expected streaming content
                        assert "Using BUILD_MODE: QUICK" in content
                        assert (
                            "Starting source update check..." in content
                        )  # New progress message
                        assert (
                            "Checking for FastLED source file changes..." in content
                        )  # New progress message
                        assert (
                            "No source file changes detected" in content
                        )  # From our mock generator
                        assert (
                            "Source update completed" in content
                        )  # New progress message
                        assert "Starting libfastled compilation" in content
                        assert "Running build script" in content
                        assert (
                            "Starting libfastled compilation..." in content
                        )  # From our mock script
                        assert "Configuring cmake..." in content  # From our mock script
                        assert (
                            "Building with emmake..." in content
                        )  # From our mock script
                        assert (
                            "LibFastLED compilation completed successfully!" in content
                        )
                        assert "STATUS: SUCCESS" in content
                        assert "HTTP_STATUS: 200" in content
