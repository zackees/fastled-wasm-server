"""
Libfastled compilation module.

This module handles the compilation of the libfastled library by executing 
the build_archive.sh script and streaming the output.

Extracted from the FastAPI endpoint for easier testing and modularity.
"""

import asyncio
import os
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, Optional


class LibfastledCompiler:
    """Handles compilation of the libfastled library."""

    def __init__(self, compiler_root: Path, shell_executable: str = "/bin/bash"):
        """
        Initialize the compiler.
        
        Args:
            compiler_root: Path to the compiler root directory
            shell_executable: Shell executable to use (default: /bin/bash)
        """
        self.compiler_root = Path(compiler_root)
        self.shell_executable = shell_executable
        self.build_script_name = "build_archive.sh"

    @property
    def build_script_path(self) -> Path:
        """Get the full path to the build script."""
        return self.compiler_root / self.build_script_name

    def validate_setup(self) -> Dict[str, Any]:
        """
        Validate that the compiler setup is correct.
        
        Returns:
            Dict with validation results
        """
        results = {
            "compiler_root_exists": self.compiler_root.exists(),
            "compiler_root_is_dir": self.compiler_root.is_dir(),
            "build_script_exists": self.build_script_path.exists(),
            "build_script_is_file": self.build_script_path.is_file(),
            "build_script_executable": False,
            "shell_executable": self.shell_executable,
            "errors": []
        }

        if not results["compiler_root_exists"]:
            results["errors"].append(f"Compiler root does not exist: {self.compiler_root}")
        
        if results["compiler_root_exists"] and not results["compiler_root_is_dir"]:
            results["errors"].append(f"Compiler root is not a directory: {self.compiler_root}")

        if not results["build_script_exists"]:
            results["errors"].append(f"Build script does not exist: {self.build_script_path}")
        
        if results["build_script_exists"]:
            results["build_script_executable"] = os.access(self.build_script_path, os.X_OK)
            if not results["build_script_executable"]:
                results["errors"].append(f"Build script is not executable: {self.build_script_path}")

        results["is_valid"] = len(results["errors"]) == 0
        return results

    async def compile_stream(self) -> AsyncGenerator[bytes, None]:
        """
        Compile libfastled and stream the output.
        
        Yields:
            bytes: Compilation output lines prefixed with 'data: '
        
        Raises:
            FileNotFoundError: If build script doesn't exist
            PermissionError: If build script is not executable
        """
        # Validate setup first
        validation = self.validate_setup()
        if not validation["is_valid"]:
            error_msg = f"data: ERROR: Setup validation failed: {'; '.join(validation['errors'])}\n"
            yield error_msg.encode()
            yield b"data: COMPILATION_COMPLETE\ndata: EXIT_CODE: -1\ndata: STATUS: FAIL\n"
            return

        try:
            # Run the build_archive.sh script to compile libfastled
            process = await asyncio.create_subprocess_exec(
                self.shell_executable,
                str(self.build_script_path),
                cwd=self.compiler_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,  # Combine stderr with stdout
            )

            # Stream output line by line
            assert process.stdout is not None
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                decoded_line = line.decode("utf-8", errors="replace")
                yield f"data: {decoded_line}".encode()

            # Wait for process to complete and get return code
            return_code = await process.wait()

            # Send final status
            if return_code == 0:
                status_message = f"data: COMPILATION_COMPLETE\ndata: EXIT_CODE: {return_code}\ndata: STATUS: SUCCESS\n"
            else:
                status_message = f"data: COMPILATION_COMPLETE\ndata: EXIT_CODE: {return_code}\ndata: STATUS: FAIL\n"

            yield status_message.encode()

        except Exception as e:
            error_message = f"data: ERROR: {str(e)}\ndata: COMPILATION_COMPLETE\ndata: EXIT_CODE: -1\ndata: STATUS: FAIL\n"
            yield error_message.encode()

    async def compile_to_list(self) -> Dict[str, Any]:
        """
        Compile libfastled and return all output as a list.
        
        Useful for testing and non-streaming use cases.
        
        Returns:
            Dict containing output lines, exit code, and status
        """
        output_lines = []
        exit_code = -1
        status = "FAIL"
        error = None

        async for chunk in self.compile_stream():
            line = chunk.decode('utf-8')
            output_lines.append(line)
            
            # Extract status information from the stream
            if "EXIT_CODE:" in line:
                try:
                    exit_code = int(line.split("EXIT_CODE:")[1].strip().split()[0])
                except (ValueError, IndexError):
                    pass
            
            if "STATUS:" in line:
                try:
                    status = line.split("STATUS:")[1].strip().split()[0]
                except IndexError:
                    pass
            
            if line.startswith("data: ERROR:"):
                error = line.replace("data: ERROR:", "").strip()

        return {
            "output_lines": output_lines,
            "exit_code": exit_code,
            "status": status,
            "success": status == "SUCCESS",
            "error": error
        }


# Convenience function for backward compatibility
async def compile_libfastled_stream(
    compiler_root: Path, 
    shell_executable: str = "/bin/bash"
) -> AsyncGenerator[bytes, None]:
    """
    Convenience function to compile libfastled and stream output.
    
    Args:
        compiler_root: Path to the compiler root directory
        shell_executable: Shell executable to use
        
    Yields:
        bytes: Compilation output
    """
    compiler = create_compiler(compiler_root, shell_executable)
    async for chunk in compiler.compile_stream():
        yield chunk


# Environment variable to disable subprocess execution during testing
def should_disable_subprocess() -> bool:
    """Check if subprocess execution should be disabled for testing."""
    return os.environ.get("DISABLE_SUBPROCESS", "false").lower() in ["true", "1"]


class MockLibfastledCompiler(LibfastledCompiler):
    """Mock version of LibfastledCompiler for testing."""

    def __init__(self, compiler_root: Path, shell_executable: str = "/bin/bash", 
                 mock_output: Optional[list] = None, mock_exit_code: int = 0):
        """
        Initialize mock compiler.
        
        Args:
            compiler_root: Path to compiler root (can be fake for testing)
            shell_executable: Shell executable (ignored in mock)
            mock_output: List of output lines to return
            mock_exit_code: Exit code to return
        """
        super().__init__(compiler_root, shell_executable)
        self.mock_output = mock_output or ["Mock build output\n", "Build complete!\n"]
        self.mock_exit_code = mock_exit_code

    async def compile_stream(self) -> AsyncGenerator[bytes, None]:
        """Mock implementation that returns predefined output."""
        # Yield mock output lines
        for line in self.mock_output:
            yield f"data: {line}".encode()
        
        # Yield final status
        if self.mock_exit_code == 0:
            status_message = f"data: COMPILATION_COMPLETE\ndata: EXIT_CODE: {self.mock_exit_code}\ndata: STATUS: SUCCESS\n"
        else:
            status_message = f"data: COMPILATION_COMPLETE\ndata: EXIT_CODE: {self.mock_exit_code}\ndata: STATUS: FAIL\n"
        
        yield status_message.encode()


def create_compiler(
    compiler_root: Path, 
    shell_executable: str = "/bin/bash",
    use_mock: Optional[bool] = None
) -> LibfastledCompiler:
    """
    Factory function to create appropriate compiler instance.
    
    Args:
        compiler_root: Path to compiler root
        shell_executable: Shell executable to use
        use_mock: Whether to use mock compiler (None = auto-detect from env)
        
    Returns:
        LibfastledCompiler instance (real or mock)
    """
    if use_mock is None:
        use_mock = should_disable_subprocess()
    
    if use_mock:
        return MockLibfastledCompiler(compiler_root, shell_executable)
    else:
        return LibfastledCompiler(compiler_root, shell_executable)