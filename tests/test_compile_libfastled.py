"""Tests for libfastled compilation functionality."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from fastled_wasm_server.compile import compile_libfastled
from fastled_wasm_server.types import BuildMode


class TestCompileLibfastled:
    """Test the compile_libfastled function."""

    def test_compile_libfastled_dry_run_quick(self, capsys):
        """Test compile_libfastled with dry_run=True and QUICK mode."""
        compiler_root = Path("/fake/compiler/root")
        build_mode = BuildMode.QUICK

        result = compile_libfastled(compiler_root, build_mode, dry_run=True)

        # Check return code
        assert result == 0

        # Check output
        captured = capsys.readouterr()
        assert "Starting libfastled archive compilation..." in captured.out
        assert "libfastled is building in mode: QUICK" in captured.out
        assert "DRY RUN MODE: Skipping actual compilation" in captured.out
        assert "Would execute build_archive.sh with BUILD_MODE=QUICK" in captured.out
        assert (
            "libfastled archive compilation (dry run) completed successfully."
            in captured.out
        )

    def test_compile_libfastled_dry_run_debug(self, capsys):
        """Test compile_libfastled with dry_run=True and DEBUG mode."""
        compiler_root = Path("/fake/compiler/root")
        build_mode = BuildMode.DEBUG

        result = compile_libfastled(compiler_root, build_mode, dry_run=True)

        # Check return code
        assert result == 0

        # Check output
        captured = capsys.readouterr()
        assert "libfastled is building in mode: DEBUG" in captured.out
        assert "Would execute build_archive.sh with BUILD_MODE=DEBUG" in captured.out

    def test_compile_libfastled_dry_run_release(self, capsys):
        """Test compile_libfastled with dry_run=True and RELEASE mode."""
        compiler_root = Path("/fake/compiler/root")
        build_mode = BuildMode.RELEASE

        result = compile_libfastled(compiler_root, build_mode, dry_run=True)

        # Check return code
        assert result == 0

        # Check output
        captured = capsys.readouterr()
        assert "libfastled is building in mode: RELEASE" in captured.out
        assert "Would execute build_archive.sh with BUILD_MODE=RELEASE" in captured.out

    @patch("subprocess.Popen")
    def test_compile_libfastled_without_dry_run(self, mock_popen, capsys):
        """Test that compile_libfastled without dry_run attempts to run subprocess."""
        # Mock the subprocess
        mock_process = MagicMock()
        mock_process.stdout = iter(["test output line\n"])
        mock_process.returncode = 0
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        compiler_root = Path("/fake/compiler/root")
        build_mode = BuildMode.QUICK

        result = compile_libfastled(compiler_root, build_mode, dry_run=False)

        # Check that subprocess was called
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args
        assert "/bin/bash" in call_args[0][0]
        assert "build_archive.sh" in str(call_args[0][0])

        # Check return code
        assert result == 0

    def test_compile_libfastled_default_dry_run_false(self, capsys):
        """Test that compile_libfastled defaults to dry_run=False."""
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.stdout = iter(["test output\n"])
            mock_process.returncode = 0
            mock_process.wait.return_value = None
            mock_popen.return_value = mock_process

            compiler_root = Path("/fake/compiler/root")
            build_mode = BuildMode.QUICK

            # Call without dry_run parameter (should default to False)
            result = compile_libfastled(compiler_root, build_mode, dry_run=False)

            # Should call subprocess (not dry run)
            mock_popen.assert_called_once()
            assert result == 0
