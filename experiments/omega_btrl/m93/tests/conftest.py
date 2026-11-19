from pathlib import Path
import importlib.util
import sys

ROOT=Path(__file__).resolve().parents[1]
OMEGA=ROOT.parent
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(OMEGA))
factory_path=OMEGA/'tests/conftest.py'
spec=importlib.util.spec_from_file_location('m9_original_test_factory',factory_path)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
Factory=mod.Factory
STAMP=mod.STAMP
