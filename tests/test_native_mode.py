"""Test the native compiler mode functionality."""

import tempfile
import unittest
from pathlib import Path

from fastled_wasm_server.compile import Args, parse_args


class TestNativeMode(unittest.TestCase):
    """Test native compiler mode functionality."""

    def test_args_native_implies_no_platformio(self) -> None:
        """Test that native=True automatically sets no_platformio=True in Args dataclass."""
        args = Args(
            mapped_dir=Path(tempfile.gettempdir()),
            keep_files=False,
            only_copy=False,
            only_insert_header=False,
            only_compile=False,
            profile=False,
            disable_auto_clean=False,
            no_platformio=False,  # Start with False
            native=True,  # Set native to True
            debug=False,
            quick=True,
            release=False,
        )

        # After __post_init__, no_platformio should be True because native is True
        self.assertTrue(args.native)
        self.assertTrue(args.no_platformio)

    def test_args_native_false_preserves_no_platformio(self) -> None:
        """Test that native=False doesn't affect no_platformio setting."""
        args = Args(
            mapped_dir=Path(tempfile.gettempdir()),
            keep_files=False,
            only_copy=False,
            only_insert_header=False,
            only_compile=False,
            profile=False,
            disable_auto_clean=False,
            no_platformio=False,  # Start with False
            native=False,  # Set native to False
            debug=False,
            quick=True,
            release=False,
        )

        # With native=False, no_platformio should remain False
        self.assertFalse(args.native)
        self.assertFalse(args.no_platformio)

    def test_args_native_true_with_no_platformio_true(self) -> None:
        """Test that native=True works when no_platformio is already True."""
        args = Args(
            mapped_dir=Path(tempfile.gettempdir()),
            keep_files=False,
            only_copy=False,
            only_insert_header=False,
            only_compile=False,
            profile=False,
            disable_auto_clean=False,
            no_platformio=True,  # Start with True
            native=True,  # Set native to True
            debug=False,
            quick=True,
            release=False,
        )

        # Both should be True
        self.assertTrue(args.native)
        self.assertTrue(args.no_platformio)

    def test_cli_native_flag_parsing(self) -> None:
        """Test that the --native CLI flag is properly parsed."""
        # Mock sys.argv for argument parsing
        import sys

        original_argv = sys.argv
        try:
            # Test with --native flag
            sys.argv = ["compile.py", "--native"]
            args = parse_args()

            self.assertTrue(args.native)
            self.assertTrue(args.no_platformio)  # Should be automatically set

            # Test without --native flag
            sys.argv = ["compile.py"]
            args = parse_args()

            self.assertFalse(args.native)
            # no_platformio should follow environment variable or default

        finally:
            sys.argv = original_argv

    def test_cli_native_and_no_platformio_flags(self) -> None:
        """Test combining --native with --no-platformio flags."""
        import sys

        original_argv = sys.argv
        try:
            # Test with both flags
            sys.argv = ["compile.py", "--native", "--no-platformio"]
            args = parse_args()

            self.assertTrue(args.native)
            self.assertTrue(args.no_platformio)

        finally:
            sys.argv = original_argv

    def test_cli_help_includes_native_flag(self) -> None:
        """Test that the --native flag appears in help output."""
        import sys
        from io import StringIO

        original_argv = sys.argv
        original_stdout = sys.stdout
        try:
            sys.argv = ["compile.py", "--help"]
            sys.stdout = StringIO()

            # This should raise SystemExit due to --help
            with self.assertRaises(SystemExit):
                parse_args()

            help_output = sys.stdout.getvalue()
            self.assertIn("--native", help_output)
            self.assertIn("Use native build system", help_output)
            self.assertIn("automatically implies", help_output)
            self.assertIn(
                "--no-", help_output
            )  # The line breaks, so check for partial text

        finally:
            sys.argv = original_argv
            sys.stdout = original_stdout


if __name__ == "__main__":
    unittest.main()
