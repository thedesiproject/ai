#!/usr/bin/env python3
# --- ./framework/runner.py ---
import argparse, json, sys, importlib.util, os
from pathlib import Path

def main():
  os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
  root = Path(os.path.realpath(__file__)).parent
  tools_path = root / "tools"
  p = argparse.ArgumentParser()
  sub = p.add_subparsers(dest="cmd", required=True)
  sub.add_parser("list")
  reg = {}

  if tools_path.exists():
    for f in sorted(tools_path.glob("*.py")):
      if f.name.startswith("_"): continue
      try:
        spec = importlib.util.spec_from_file_location(f.stem, str(f))
        mod = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(tools_path))
        spec.loader.exec_module(mod)
        if hasattr(mod, "setup"):
          mod.setup(sub.add_parser(f.stem))
          reg[f.stem] = mod.run
      except Exception: continue

  a = p.parse_args()
  if a.cmd == "list":
    print(json.dumps({"tools": sorted(list(reg.keys()))}, separators=(',', ':')))
  elif a.cmd in reg:
    os.chdir(root.parent)
    print(json.dumps(reg[a.cmd](a), separators=(',', ':')))

if __name__ == "__main__":
  main()