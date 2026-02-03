from __future__ import annotations

import json
import os
import sys

CURRENT_DIR = os.path.dirname(__file__)
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.main import app


def main() -> None:
    spec = app.openapi()
    json.dump(spec, sys.stdout, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()