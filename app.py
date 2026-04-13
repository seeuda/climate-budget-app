"""Streamlit entrypoint for the climate budget self-assessment system.

This repository keeps the main application implementation in
`update_manifest.py`. The deployment entrypoint must execute that module,
otherwise users will only see the temporary health-check page.
"""

from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).with_name("update_manifest.py")), run_name="__main__")
