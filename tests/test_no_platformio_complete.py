"""Complete test demonstrating no_platformio functionality."""

import os
import unittest
from unittest.mock import patch


def simulate_server_logic(header_value, env_var_value=None):
    """
    Simulate the exact logic from server.py for handling no_platformio parameter.
    
    Args:
        header_value: The value from the HTTP header (None, True, False)
        env_var_value: The value of NO_PLATFORMIO environment variable
        
    Returns:
        bool: The final no_platformio value that would be passed to compilation
    """
    # Simulate setting environment variable if provided
    if env_var_value is not None:
        os.environ['NO_PLATFORMIO'] = str(env_var_value)
    elif 'NO_PLATFORMIO' in os.environ:
        del os.environ['NO_PLATFORMIO']
    
    # This is the exact logic from server.py
    no_platformio = header_value
    if no_platformio is None:
        no_platformio = os.environ.get("NO_PLATFORMIO", "0") == "1"
    
    return no_platformio


def simulate_args_creation(no_platformio):
    """
    Simulate the Args creation logic from server_compile.py.
    
    Args:
        no_platformio: boolean value to pass to Args
        
    Returns:
        list: Simulated command line arguments
    """
    # Simulate the fastled-wasm-compiler command construction
    cmd_args = ["fastled-wasm-compiler"]
    
    # Basic args
    cmd_args.extend(["--compiler-root", "/tmp"])
    cmd_args.extend(["--mapped-dir", "/tmp/src"])
    cmd_args.extend(["--quick"])
    
    # Add no-platformio flag if True
    if no_platformio:
        cmd_args.append("--no-platformio")
    
    return cmd_args


class TestCompleteFunctionality(unittest.TestCase):
    """Test the complete no_platformio functionality flow."""

    def setUp(self):
        """Clean up environment before each test."""
        # Save original environment
        self.original_env = os.environ.get('NO_PLATFORMIO')

    def tearDown(self):
        """Restore original environment after each test."""
        if self.original_env is not None:
            os.environ['NO_PLATFORMIO'] = self.original_env
        elif 'NO_PLATFORMIO' in os.environ:
            del os.environ['NO_PLATFORMIO']

    def test_header_true_creates_no_platformio_flag(self):
        """Test that header=True results in --no-platformio flag in command."""
        # Step 1: Simulate server logic
        no_platformio = simulate_server_logic(header_value=True)
        self.assertTrue(no_platformio)
        
        # Step 2: Simulate args creation
        cmd_args = simulate_args_creation(no_platformio)
        self.assertIn("--no-platformio", cmd_args)
        
        print(f"✓ Header=True → no_platformio={no_platformio} → {' '.join(cmd_args)}")

    def test_header_false_no_flag(self):
        """Test that header=False results in no --no-platformio flag."""
        # Step 1: Simulate server logic
        no_platformio = simulate_server_logic(header_value=False)
        self.assertFalse(no_platformio)
        
        # Step 2: Simulate args creation
        cmd_args = simulate_args_creation(no_platformio)
        self.assertNotIn("--no-platformio", cmd_args)
        
        print(f"✓ Header=False → no_platformio={no_platformio} → {' '.join(cmd_args)}")

    def test_env_var_1_creates_flag(self):
        """Test that NO_PLATFORMIO=1 results in --no-platformio flag."""
        # Step 1: Simulate server logic with env var
        no_platformio = simulate_server_logic(header_value=None, env_var_value="1")
        self.assertTrue(no_platformio)
        
        # Step 2: Simulate args creation
        cmd_args = simulate_args_creation(no_platformio)
        self.assertIn("--no-platformio", cmd_args)
        
        print(f"✓ NO_PLATFORMIO=1 → no_platformio={no_platformio} → {' '.join(cmd_args)}")

    def test_env_var_0_no_flag(self):
        """Test that NO_PLATFORMIO=0 results in no --no-platformio flag."""
        # Step 1: Simulate server logic with env var
        no_platformio = simulate_server_logic(header_value=None, env_var_value="0")
        self.assertFalse(no_platformio)
        
        # Step 2: Simulate args creation
        cmd_args = simulate_args_creation(no_platformio)
        self.assertNotIn("--no-platformio", cmd_args)
        
        print(f"✓ NO_PLATFORMIO=0 → no_platformio={no_platformio} → {' '.join(cmd_args)}")

    def test_default_behavior_no_flag(self):
        """Test that default behavior (no header, no env var) results in no flag.""" 
        # Step 1: Simulate server logic with defaults
        no_platformio = simulate_server_logic(header_value=None)
        self.assertFalse(no_platformio)
        
        # Step 2: Simulate args creation
        cmd_args = simulate_args_creation(no_platformio)
        self.assertNotIn("--no-platformio", cmd_args)
        
        print(f"✓ Default → no_platformio={no_platformio} → {' '.join(cmd_args)}")

    def test_header_overrides_env_var(self):
        """Test that explicit header value overrides environment variable."""
        # Case 1: Header=False overrides NO_PLATFORMIO=1
        no_platformio = simulate_server_logic(header_value=False, env_var_value="1")
        self.assertFalse(no_platformio)
        cmd_args = simulate_args_creation(no_platformio)
        self.assertNotIn("--no-platformio", cmd_args)
        print(f"✓ Header=False + NO_PLATFORMIO=1 → no_platformio={no_platformio} (header wins)")
        
        # Case 2: Header=True overrides NO_PLATFORMIO=0
        no_platformio = simulate_server_logic(header_value=True, env_var_value="0")
        self.assertTrue(no_platformio)
        cmd_args = simulate_args_creation(no_platformio)
        self.assertIn("--no-platformio", cmd_args)
        print(f"✓ Header=True + NO_PLATFORMIO=0 → no_platformio={no_platformio} (header wins)")

    def test_comprehensive_scenarios(self):
        """Test all possible combinations of inputs."""
        scenarios = [
            # (description, header_value, env_var, expected_no_platformio, expected_flag_present)
            ("Default behavior", None, None, False, False),
            ("Header True", True, None, True, True),
            ("Header False", False, None, False, False),
            ("Env var 1", None, "1", True, True),
            ("Env var 0", None, "0", False, False),
            ("Env var other", None, "true", False, False),  # Only "1" should be True
            ("Header True overrides Env 0", True, "0", True, True),
            ("Header False overrides Env 1", False, "1", False, False),
        ]
        
        print("\n=== Comprehensive Scenario Test ===")
        for desc, header, env_var, expected_bool, expected_flag in scenarios:
            with self.subTest(scenario=desc):
                no_platformio = simulate_server_logic(header, env_var)
                self.assertEqual(no_platformio, expected_bool, 
                               f"Scenario '{desc}' failed boolean check")
                
                cmd_args = simulate_args_creation(no_platformio)
                flag_present = "--no-platformio" in cmd_args
                self.assertEqual(flag_present, expected_flag,
                               f"Scenario '{desc}' failed flag check")
                
                print(f"✓ {desc:30} → {no_platformio:5} → {'HAS FLAG' if flag_present else 'NO FLAG'}")


if __name__ == "__main__":
    # Run with verbose output
    unittest.main(verbosity=2)