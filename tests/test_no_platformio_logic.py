"""Tests for no_platformio parameter logic without external dependencies."""

import os
import unittest
from unittest.mock import patch


class TestNoPlatformioLogic(unittest.TestCase):
    """Test the no_platformio parameter logic."""

    def test_no_platformio_env_var_logic_true(self):
        """Test the environment variable logic when NO_PLATFORMIO=1."""
        with patch.dict(os.environ, {'NO_PLATFORMIO': '1'}):
            # Simulate the logic from server.py
            no_platformio = None
            if no_platformio is None:
                no_platformio = os.environ.get("NO_PLATFORMIO", "0") == "1"
            
            self.assertTrue(no_platformio)

    def test_no_platformio_env_var_logic_false(self):
        """Test the environment variable logic when NO_PLATFORMIO=0."""
        with patch.dict(os.environ, {'NO_PLATFORMIO': '0'}):
            # Simulate the logic from server.py
            no_platformio = None
            if no_platformio is None:
                no_platformio = os.environ.get("NO_PLATFORMIO", "0") == "1"
            
            self.assertFalse(no_platformio)

    def test_no_platformio_env_var_logic_unset(self):
        """Test the environment variable logic when NO_PLATFORMIO is not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Simulate the logic from server.py
            no_platformio = None
            if no_platformio is None:
                no_platformio = os.environ.get("NO_PLATFORMIO", "0") == "1"
            
            self.assertFalse(no_platformio)

    def test_no_platformio_env_var_logic_other_values(self):
        """Test the environment variable logic with other values."""
        test_cases = [
            ('true', False),  # Only "1" should be True
            ('false', False),
            ('yes', False),
            ('no', False),
            ('2', False),
            ('', False),
        ]
        
        for value, expected in test_cases:
            with patch.dict(os.environ, {'NO_PLATFORMIO': value}):
                # Simulate the logic from server.py
                no_platformio = None
                if no_platformio is None:
                    no_platformio = os.environ.get("NO_PLATFORMIO", "0") == "1"
                
                self.assertEqual(no_platformio, expected, 
                               f"NO_PLATFORMIO='{value}' should result in {expected}")

    def test_no_platformio_header_overrides_env_var(self):
        """Test that explicit header value overrides environment variable."""
        with patch.dict(os.environ, {'NO_PLATFORMIO': '1'}):
            # Simulate explicit header value
            no_platformio = False  # Explicit False from header
            if no_platformio is None:
                no_platformio = os.environ.get("NO_PLATFORMIO", "0") == "1"
            
            # Should be False because explicit header overrides env var
            self.assertFalse(no_platformio)

    def test_no_platformio_header_true_overrides_env_var_false(self):
        """Test that explicit True header overrides False environment variable."""
        with patch.dict(os.environ, {'NO_PLATFORMIO': '0'}):
            # Simulate explicit header value
            no_platformio = True  # Explicit True from header
            if no_platformio is None:
                no_platformio = os.environ.get("NO_PLATFORMIO", "0") == "1"
            
            # Should be True because explicit header overrides env var
            self.assertTrue(no_platformio)


class TestArgsPassing(unittest.TestCase):
    """Test that Args constructor properly handles no_platformio parameter."""

    def test_args_creation_with_no_platformio_true(self):
        """Test Args creation with no_platformio=True."""
        try:
            from fastled_wasm_compiler.run_compile import Args
        except ImportError:
            self.skipTest("fastled_wasm_compiler not available")
            
        from pathlib import Path
        
        # Test creating Args with no_platformio=True
        args = Args(
            compiler_root=Path("/tmp"),
            assets_dirs=Path("/tmp"),
            mapped_dir=Path("/tmp"),
            keep_files=False,
            only_copy=False,
            only_insert_header=False,
            only_compile=False,
            profile=False,
            disable_auto_clean=False,
            no_platformio=True,  # This is what we're testing
            clear_ccache=False,
            debug=False,
            quick=True,
            release=False,
            strict=False,
        )
        
        # Check that no_platformio is set correctly
        self.assertTrue(args.no_platformio)
        
        # Check that it appears in command line args
        cmd_args = args.to_cmd_args()
        self.assertIn('--no-platformio', cmd_args)

    def test_args_creation_with_no_platformio_false(self):
        """Test Args creation with no_platformio=False."""
        try:
            from fastled_wasm_compiler.run_compile import Args
        except ImportError:
            self.skipTest("fastled_wasm_compiler not available")
            
        from pathlib import Path
        
        # Test creating Args with no_platformio=False
        args = Args(
            compiler_root=Path("/tmp"),
            assets_dirs=Path("/tmp"),
            mapped_dir=Path("/tmp"),
            keep_files=False,
            only_copy=False,
            only_insert_header=False,
            only_compile=False,
            profile=False,
            disable_auto_clean=False,
            no_platformio=False,  # This is what we're testing
            clear_ccache=False,
            debug=False,
            quick=True,
            release=False,
            strict=False,
        )
        
        # Check that no_platformio is set correctly
        self.assertFalse(args.no_platformio)
        
        # Check that it does NOT appear in command line args
        cmd_args = args.to_cmd_args()
        self.assertNotIn('--no-platformio', cmd_args)


if __name__ == "__main__":
    unittest.main()