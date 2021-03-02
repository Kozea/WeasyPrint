"""This file contains the DLL location for Windows Wheels.
"""
from pathlib import Path
import os

__all__ = [
    "gobject_dll",
    "pango_dll",
    "harfbuzz_dll",
    "fontconfig_dll",
    "pangoft2_dll",
]

LIBS_ROOT = Path(__file__).parent / ".libs"

# add `.libs` to PATH so that peer DLL's load sucessfully.
os.environ["PATH"] = (
    f"{LIBS_ROOT.absolute()}"
    f"{os.pathsep}"
    f"{os.environ['PATH']}"
)


gobject_dll = str(Path(LIBS_ROOT, "CORE_MANIM_gobject-2.0-0.dll").absolute())
pango_dll = str(Path(LIBS_ROOT, "CORE_MANIM_pango-1.0-0.dll").absolute())
harfbuzz_dll = str(Path(LIBS_ROOT, "CORE_MANIM_harfbuzz.dll").absolute())
fontconfig_dll = str(Path(LIBS_ROOT, "CORE_MANIM_fontconfig-1.dll").absolute())
pangoft2_dll = str(Path(LIBS_ROOT, "CORE_MANIM_pangoft2-1.0-0.dll").absolute())
