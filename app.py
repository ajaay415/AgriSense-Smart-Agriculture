"""Root launcher for AgriSense Smart Agriculture Simulator.

Allows running `streamlit run app.py` directly from the root workspace directory.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure AgriSense_Complete_Project is in sys.path
BASE_DIR = Path(__file__).resolve().parent
AGRI_DIR = BASE_DIR / "AgriSense_Complete_Project"
if str(AGRI_DIR) not in sys.path:
    sys.path.insert(0, str(AGRI_DIR))

# Execute the main application
app_path = AGRI_DIR / "app.py"
with open(app_path, "r", encoding="utf-8") as f:
    code = f.read()

# Execute within the context of AgriSense_Complete_Project
globals_dict = {
    "__file__": str(app_path),
    "__name__": "__main__",
}
exec(compile(code, str(app_path), "exec"), globals_dict)
