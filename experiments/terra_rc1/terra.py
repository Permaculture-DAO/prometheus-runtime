"""Compatibility entrypoint for the original RC1 experiment; core lives in app."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services" / "api"))
from app.terra_property_core import *  # compatibility for historical RC1 tests
if __name__ == "__main__":
    sys.exit(main())
