"""
Unit tests for the libfastled compiler module.

Tests the isolated LibfastledCompiler class without FastAPI dependencies.
"""

import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, AsyncMock

# Environment variable to control subprocess execution during testing
DISABLE_SUBPROCESS = os.environ.get("DISABLE_SUBPROCESS", "true").lower() in ["true", "1"]


class TestLibfastledCompiler(unittest.IsolatedAsyncioTestCase):
    """Test the LibfastledCompiler class."""

    async def asyncSetUp(self):
        """Set up test fixtures."""
        # Always enable mocking for unit tests to avoid subprocess execution
        os.environ["DISABLE_SUBPROCESS"] = "true"
        
        from fastled_wasm_server.libfastled_compiler import LibfastledCompiler, MockLibfastledCompiler
        self.LibfastledCompiler = LibfastledCompiler
        self.MockLibfastledCompiler = MockLibfastledCompiler

    async def asyncTearDown(self):
        """Clean up after tests."""
        # Reset environment variable
        if "DISABLE_SUBPROCESS" in os.environ:
            del os.environ["DISABLE_SUBPROCESS"]

    def test_compiler_initialization(self):
        """Test compiler initialization with different parameters."""
        compiler_root = Path("/tmp/test")
        
        # Test default initialization
        compiler = self.LibfastledCompiler(compiler_root)
        self.assertEqual(compiler.compiler_root, compiler_root)
        self.assertEqual(compiler.shell_executable, "/bin/bash")
        self.assertEqual(compiler.build_script_name, "build_archive.sh")
        
        # Test custom shell
        compiler = self.LibfastledCompiler(compiler_root, shell_executable="/bin/sh")
        self.assertEqual(compiler.shell_executable, "/bin/sh")

    def test_build_script_path(self):
        """Test build script path property."""
        compiler_root = Path("/tmp/test")
        compiler = self.LibfastledCompiler(compiler_root)
        
        expected_path = compiler_root / "build_archive.sh"
        self.assertEqual(compiler.build_script_path, expected_path)

    def test_validate_setup_missing_root(self):
        """Test validation when compiler root doesn't exist."""
        compiler_root = Path("/nonexistent/path")
        compiler = self.LibfastledCompiler(compiler_root)
        
        validation = compiler.validate_setup()
        
        self.assertFalse(validation["is_valid"])
        self.assertFalse(validation["compiler_root_exists"])
        self.assertFalse(validation["compiler_root_is_dir"])
        self.assertFalse(validation["build_script_exists"])
        self.assertIn("Compiler root does not exist", str(validation["errors"]))

    def test_validate_setup_valid(self):
        """Test validation with valid setup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            compiler_root = Path(temp_dir)
            build_script = compiler_root / "build_archive.sh"
            build_script.write_text("#!/bin/bash\necho 'test'\n")
            build_script.chmod(0o755)
            
            compiler = self.LibfastledCompiler(compiler_root)
            validation = compiler.validate_setup()
            
            self.assertTrue(validation["is_valid"])
            self.assertTrue(validation["compiler_root_exists"])
            self.assertTrue(validation["compiler_root_is_dir"])
            self.assertTrue(validation["build_script_exists"])
            self.assertTrue(validation["build_script_is_file"])
            self.assertTrue(validation["build_script_executable"])
            self.assertEqual(len(validation["errors"]), 0)

    def test_validate_setup_script_not_executable(self):
        """Test validation when build script is not executable."""
        with tempfile.TemporaryDirectory() as temp_dir:
            compiler_root = Path(temp_dir)
            build_script = compiler_root / "build_archive.sh"
            build_script.write_text("#!/bin/bash\necho 'test'\n")
            # Don't make it executable
            
            compiler = self.LibfastledCompiler(compiler_root)
            validation = compiler.validate_setup()
            
            self.assertFalse(validation["is_valid"])
            self.assertFalse(validation["build_script_executable"])
            self.assertIn("Build script is not executable", str(validation["errors"]))

    async def test_mock_compiler_success(self):
        """Test MockLibfastledCompiler with successful compilation."""
        compiler_root = Path("/fake/path")
        mock_output = ["Starting build...\n", "Build successful!\n"]
        compiler = self.MockLibfastledCompiler(
            compiler_root, 
            mock_output=mock_output, 
            mock_exit_code=0
        )
        
        output_chunks = []
        async for chunk in compiler.compile_stream():
            output_chunks.append(chunk.decode('utf-8'))
        
        output_text = ''.join(output_chunks)
        self.assertIn("Starting build...", output_text)
        self.assertIn("Build successful!", output_text)
        self.assertIn("COMPILATION_COMPLETE", output_text)
        self.assertIn("EXIT_CODE: 0", output_text)
        self.assertIn("STATUS: SUCCESS", output_text)

    async def test_mock_compiler_failure(self):
        """Test MockLibfastledCompiler with failed compilation."""
        compiler_root = Path("/fake/path")
        mock_output = ["Starting build...\n", "ERROR: Build failed!\n"]
        compiler = self.MockLibfastledCompiler(
            compiler_root, 
            mock_output=mock_output, 
            mock_exit_code=1
        )
        
        output_chunks = []
        async for chunk in compiler.compile_stream():
            output_chunks.append(chunk.decode('utf-8'))
        
        output_text = ''.join(output_chunks)
        self.assertIn("Starting build...", output_text)
        self.assertIn("ERROR: Build failed!", output_text)
        self.assertIn("COMPILATION_COMPLETE", output_text)
        self.assertIn("EXIT_CODE: 1", output_text)
        self.assertIn("STATUS: FAIL", output_text)

    async def test_compile_to_list_success(self):
        """Test compile_to_list method with successful compilation."""
        compiler_root = Path("/fake/path")
        mock_output = ["Building...\n", "Success!\n"]
        compiler = self.MockLibfastledCompiler(
            compiler_root,
            mock_output=mock_output,
            mock_exit_code=0
        )
        
        result = await compiler.compile_to_list()
        
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["status"], "SUCCESS")
        self.assertTrue(result["success"])
        self.assertIsNone(result["error"])
        self.assertGreater(len(result["output_lines"]), 0)

    async def test_compile_to_list_failure(self):
        """Test compile_to_list method with failed compilation."""
        compiler_root = Path("/fake/path")
        mock_output = ["Building...\n", "Failed!\n"]
        compiler = self.MockLibfastledCompiler(
            compiler_root,
            mock_output=mock_output,
            mock_exit_code=1
        )
        
        result = await compiler.compile_to_list()
        
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["success"])
        self.assertGreater(len(result["output_lines"]), 0)

    async def test_compile_stream_validation_failure(self):
        """Test compile_stream when validation fails."""
        # Use a non-existent path to trigger validation failure
        compiler_root = Path("/nonexistent/path")
        compiler = self.LibfastledCompiler(compiler_root)
        
        output_chunks = []
        async for chunk in compiler.compile_stream():
            output_chunks.append(chunk.decode('utf-8'))
        
        output_text = ''.join(output_chunks)
        self.assertIn("ERROR: Setup validation failed", output_text)
        self.assertIn("COMPILATION_COMPLETE", output_text)
        self.assertIn("EXIT_CODE: -1", output_text)
        self.assertIn("STATUS: FAIL", output_text)

    @patch('asyncio.create_subprocess_exec')
    async def test_real_compiler_with_subprocess_mock(self, mock_subprocess):
        """Test real compiler with mocked subprocess (for when subprocess is enabled)."""
        # Temporarily disable subprocess mocking
        os.environ["DISABLE_SUBPROCESS"] = "false"
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                compiler_root = Path(temp_dir)
                build_script = compiler_root / "build_archive.sh"
                build_script.write_text("#!/bin/bash\necho 'test build'\n")
                build_script.chmod(0o755)
                
                # Mock the subprocess
                mock_process = AsyncMock()
                mock_process.stdout = AsyncMock()
                mock_process.stdout.readline = AsyncMock(side_effect=[
                    b"Building libfastled...\n",
                    b"Compilation complete!\n",
                    b""  # End of stream
                ])
                mock_process.wait = AsyncMock(return_value=0)
                mock_subprocess.return_value = mock_process
                
                compiler = self.LibfastledCompiler(compiler_root)
                
                output_chunks = []
                async for chunk in compiler.compile_stream():
                    output_chunks.append(chunk.decode('utf-8'))
                
                output_text = ''.join(output_chunks)
                self.assertIn("Building libfastled", output_text)
                self.assertIn("Compilation complete", output_text)
                self.assertIn("STATUS: SUCCESS", output_text)
                
                # Verify subprocess was called correctly
                mock_subprocess.assert_called_once_with(
                    "/bin/bash",
                    str(build_script),
                    cwd=compiler_root,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT
                )
        
        finally:
            # Re-enable subprocess mocking
            os.environ["DISABLE_SUBPROCESS"] = "true"

    def test_factory_function(self):
        """Test the create_compiler factory function."""
        from fastled_wasm_server.libfastled_compiler import create_compiler
        
        compiler_root = Path("/tmp/test")
        
        # Test with mocking enabled (default)
        compiler = create_compiler(compiler_root, use_mock=True)
        self.assertIsInstance(compiler, self.MockLibfastledCompiler)
        
        # Test with mocking disabled
        compiler = create_compiler(compiler_root, use_mock=False)
        self.assertIsInstance(compiler, self.LibfastledCompiler)
        self.assertNotIsInstance(compiler, self.MockLibfastledCompiler)

    def test_should_disable_subprocess(self):
        """Test the should_disable_subprocess function."""
        from fastled_wasm_server.libfastled_compiler import should_disable_subprocess
        
        # Test with environment variable set to true
        os.environ["DISABLE_SUBPROCESS"] = "true"
        self.assertTrue(should_disable_subprocess())
        
        os.environ["DISABLE_SUBPROCESS"] = "1"
        self.assertTrue(should_disable_subprocess())
        
        os.environ["DISABLE_SUBPROCESS"] = "false"
        self.assertFalse(should_disable_subprocess())
        
        os.environ["DISABLE_SUBPROCESS"] = "0"
        self.assertFalse(should_disable_subprocess())
        
        # Test with environment variable not set
        if "DISABLE_SUBPROCESS" in os.environ:
            del os.environ["DISABLE_SUBPROCESS"]
        self.assertFalse(should_disable_subprocess())

    async def test_convenience_function(self):
        """Test the convenience function compile_libfastled_stream."""
        from fastled_wasm_server.libfastled_compiler import compile_libfastled_stream
        
        compiler_root = Path("/fake/path")
        
        output_chunks = []
        async for chunk in compile_libfastled_stream(compiler_root):
            output_chunks.append(chunk.decode('utf-8'))
        
        output_text = ''.join(output_chunks)
        self.assertIn("Mock build output", output_text)
        self.assertIn("COMPILATION_COMPLETE", output_text)


if __name__ == "__main__":
    # Ensure subprocess is disabled for testing
    os.environ["DISABLE_SUBPROCESS"] = "true"
    unittest.main()