"""
Unit test file.
"""

import unittest
from pathlib import Path

from fastled_wasm_server.server_serve_src_files import SourceFileFetcher

_PREFIX_FASTLED = "/fastled/src"
_PREFIX_SKETCH = "/js/src"

"drawfsource/js/drawfsource/headers/FastLED.h"
_FASTLED_TEST_DATA: dict[str, str] = {
    "drawfsource/js/drawfsource/headers/FastLED.h": f"{_PREFIX_FASTLED}/FastLED.h",
    "drawfsource/js/src/drawfsource/git/fastled/src/FastLED.h": f"{_PREFIX_FASTLED}/FastLED.h",
}

_SKETCH_TEST_DATA: dict[str, str] = {
    "drawfsource/js/src/XYPath.ino.cpp": f"{_PREFIX_SKETCH}/XYPath.ino.cpp",
    "drawfsource/js/src/direct.h": f"{_PREFIX_SKETCH}/direct.h",
}


_SOURCE_FILE_FETCHER: SourceFileFetcher = SourceFileFetcher(
    fastled_src=Path(_PREFIX_FASTLED),
    sketch_src=Path(_PREFIX_SKETCH),
)


class SourceFileResolver(unittest.TestCase):
    """Main tester class."""

    def test_fastled_patterns(self) -> None:
        """Test command line interface (CLI)."""

        for url_browser, backend_path in _FASTLED_TEST_DATA.items():
            resolved: Path | None = _SOURCE_FILE_FETCHER.resolve_drawfsource(
                path=url_browser
            )
            self.assertIsNotNone(resolved)
            self.assertEqual(
                resolved,
                Path(backend_path),
            )

        print("done")

    def test_sketch_patterns(self) -> None:
        """Test command line interface (CLI)."""
        for url_browser, backend_path in _SKETCH_TEST_DATA.items():
            resolved: Path | None = _SOURCE_FILE_FETCHER.resolve_drawfsource(
                path=url_browser
            )
            self.assertIsNotNone(resolved)
            self.assertEqual(
                resolved,
                Path(backend_path),
            )

        print("done")


if __name__ == "__main__":
    unittest.main()
