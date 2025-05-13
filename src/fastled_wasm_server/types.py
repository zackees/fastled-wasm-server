from dataclasses import dataclass


@dataclass
class CompilerStats:
    compile_count: int = 0
    compile_failures: int = 0
    compile_successes: int = 0
