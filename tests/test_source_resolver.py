"""
Unit test file.
"""

import unittest
from pathlib import Path

from fastled_wasm_server.server_serve_src_files import SourceFileFetcher

_PREFIX_FASTLED = "/fastled/src"
_PREFIX_SKETCH = "/js/src"

_EXAMPLES_SRC_FASTLED: list[str] = [
    "drawfsource/js/drawfsource/headers/FastLED.h",
    "drawfsource/js/src/drawfsource/git/fastled/src/FastLED.h",
]

_EXAMPLES_SRC_SKETCH: list[str] = ["drawfsource/js/src/XYPath.ino.cpp"]


class SourceFileResolver(unittest.TestCase):
    """Main tester class."""

    def test_fastled_patterns(self) -> None:
        """Test command line interface (CLI)."""
        sfr: SourceFileFetcher = SourceFileFetcher(
            fastled_src=Path(_PREFIX_FASTLED),
            sketch_src=Path(_PREFIX_SKETCH),
        )

        for examples in _EXAMPLES_SRC_FASTLED:
            resolved: Path | None = sfr.resolve_drawfsource(path=examples)
            self.assertIsNotNone(resolved)
            self.assertEqual(
                resolved,
                Path(f"{_PREFIX_FASTLED}/FastLED.h"),
            )

        print("done")

    def test_sketch_patterns(self) -> None:
        """Test command line interface (CLI)."""
        sfr: SourceFileFetcher = SourceFileFetcher(
            fastled_src=Path(_PREFIX_FASTLED),
            sketch_src=Path(_PREFIX_SKETCH),
        )

        for examples in _EXAMPLES_SRC_SKETCH:
            resolved: Path | None = sfr.resolve_drawfsource(path=examples)
            self.assertIsNotNone(resolved)
            self.assertEqual(
                resolved,
                Path(f"{_PREFIX_SKETCH}/XYPath.ino.cpp"),
            )

        print("done")


if __name__ == "__main__":
    unittest.main()
