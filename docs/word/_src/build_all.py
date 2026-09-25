"""Regenerates every figure and Word document in docs/word.

    python docs/word/_src/build_all.py
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

STEPS = [
    "wireframes.py",
    "diagrams.py",
    "build_srs.py",
    "build_sdd.py",
    "build_screen_design.py",
    "build_test_spec.py",
    "build_dissertation.py",
]

if __name__ == "__main__":
    for step in STEPS:
        path = HERE / step
        if not path.exists():
            print(f"skip {step} (not present)")
            continue
        print(f"== {step}")
        runpy.run_path(str(path), run_name="__main__")
