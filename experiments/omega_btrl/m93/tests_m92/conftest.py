from __future__ import annotations
from pathlib import Path
import importlib.util
import sys

ROOT=Path(__file__).resolve().parents[1]
SNAP=ROOT.parent
for p in (str(ROOT),str(SNAP)):
    if p not in sys.path:sys.path.insert(0,p)
spec=importlib.util.spec_from_file_location('m92_original_factory', SNAP/'tests'/'conftest.py')
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
Factory=mod.Factory
STAMP=mod.STAMP
