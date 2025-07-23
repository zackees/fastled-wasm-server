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
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

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

                # Mock update_src_async to be an async generator that simulates compilation
                async def mock_update_src_gen(*args, **kwargs):
                    yield "Starting source update check..."
                    yield "Checking for FastLED source file changes..."
                    yield "Found 5 changed files:"
                    yield "  Changed: src/FastLED.h"
                    yield "  Changed: src/lib8tion.h"
                    yield "  Changed: src/colorutils.h"
                    yield "  Changed: src/platforms/wasm/compiler/lib/fastled.cpp"
                    yield "  Changed: src/platforms/wasm/compiler/lib/CMakeLists.txt"
                    yield "Source files updated successfully"
                    yield "Compiling libfastled with mode: QUICK"
                    yield "Configuring cmake..."
                    yield "Building with emmake..."
                    yield "LibFastLED compilation completed successfully"
                    yield "Source update completed"

                mock_update_src.side_effect = mock_update_src_gen

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
                        line for line in content.split("\n") if line.startswith("data:")
                    ]
                    assert (
                        len(data_lines) > 5
                    ), f"Should receive multiple data lines for streaming, got {len(data_lines)}"

                    # Check for expected streaming content
                    assert "Using BUILD_MODE: QUICK" in content
                    assert (
                        "Starting source update check..." in content
                    )  # From update_src_async
                    assert (
                        "Checking for FastLED source file changes..." in content
                    )  # From update_src_async
                    assert (
                        "Found 5 changed files:" in content
                    )  # From our mock generator
                    assert (
                        "Source files updated successfully" in content
                    )  # From our mock generator
                    assert (
                        "Compiling libfastled with mode: QUICK" in content
                    )  # From our mock generator (simulating compile_all_libs output)
                    assert "Configuring cmake..." in content  # From our mock generator
                    assert (
                        "Building with emmake..." in content
                    )  # From our mock generator
                    assert "Source update completed" in content  # From update_src_async
                    assert (
                        "LibFastLED compilation completed successfully!" in content
                    )  # Final success message
                    assert "STATUS: SUCCESS" in content
                    assert "HTTP_STATUS: 200" in content

    def test_compile_libfastled_error_handling_with_detailed_output(self):
        """Test that compilation errors include detailed error information including stdout/stderr."""
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

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

                # Mock update_src_async to simulate a compilation failure with detailed error info
                async def mock_update_src_gen_with_error(*args, **kwargs):
                    yield "Starting source update check..."
                    yield "Checking for FastLED source file changes..."

                    # Create a mock exception with captured output
                    error = RuntimeError("Compilation failed")
                    error.stdout = "make: *** [all] Error 1\nCompilation terminated."  # type: ignore
                    error.stderr = "fatal error: FastLED.h: No such file or directory"  # type: ignore
                    error.returncode = 1  # type: ignore

                    # Yield error message before raising
                    yield "Source update failed: Compilation failed\nreturn code: 1\nstdout: make: *** [all] Error 1\nCompilation terminated.\nstderr: fatal error: FastLED.h: No such file or directory"

                    raise error

                mock_update_src.side_effect = mock_update_src_gen_with_error

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
                    for chunk in response.iter_text():
                        content += chunk

                    # Verify error handling includes detailed information
                    assert "Using BUILD_MODE: QUICK" in content
                    assert "Starting source update check..." in content
                    assert "Checking for FastLED source file changes..." in content

                    # Check that detailed error information is captured
                    assert (
                        "ERROR: Source update or compilation failed: Compilation failed"
                        in content
                    )
                    assert "Compilation stdout: make: *** [all] Error 1" in content
                    assert (
                        "Compilation stderr: fatal error: FastLED.h: No such file or directory"
                        in content
                    )
                    assert "Exit code: 1" in content

                    # Verify the response indicates failure
                    assert "STATUS: FAIL" in content
                    assert "HTTP_STATUS: 400" in content
                    assert "COMPILATION_COMPLETE" in content
