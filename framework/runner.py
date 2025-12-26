#!/usr/bin/env python3
# --- framework/runner.py | checksum: auto ---
import argparse, json, sys, importlib.util, os, traceback, re
from pathlib import Path

tools_dir = "tools"

def low(o):
  if isinstance(o, str): return o.lower()
  if isinstance(o, list): return [low(i) for i in o]
  if isinstance(o, dict): return {k.lower(): low(v) for k, v in o.items()}
  return o

def compact(j):
  j = re.sub(r'\{\n\s+"file": "(.*?)",\n\s+"hash": "(.*?)"\n\s+\}', r'{ "file": "\1", "hash": "\2" }', j)
  j = re.sub(r'\[\n\s+("(.*?)")\n\s+\]', r'[\1]', j)
  return j

def main():
  os.environ["pythondontwritebytecode"] = "1"
  root = Path(__file__).parent.resolve()
  t_path, reg = root / tools_dir, {}
  t_path.mkdir(parents=True, exist_ok=True)
  p = argparse.ArgumentParser(prog="run")
  p.add_argument("--debug", action="store_true")
  sub = p.add_subparsers(dest="cmd", required=True)
  sub.add_parser("list")
  sys.path.extend([str(root), str(t_path)])
  for f in sorted(t_path.rglob("*.py")):
    if f.name.startswith("_") or f.suffix != ".py": continue
    try:
      m_id = f.stem.replace("_", "-")
      spec = importlib.util.spec_from_file_location(m_id, f)
      mod = importlib.util.module_from_spec(spec)
      spec.loader.exec_module(mod)
      if hasattr(mod, "setup") and hasattr(mod, "run"):
        mod.setup(sub.add_parser(m_id))
        reg[m_id] = mod.run
    except Exception: continue
  args = p.parse_args()
  os.chdir(root.parent)
  try:
    res = {"tools": sorted(list(reg.keys()))} if args.cmd == "list" else reg[args.cmd](args)
    raw = json.dumps(low(res), indent=2, separators=(',', ': '))
    sys.stdout.write(compact(raw) + "\n")
  except Exception as e:
    err = {"status": "error", "msg": str(e).lower()}
    if args.debug: err["trace"] = traceback.format_exc().lower()
    sys.stdout.write(json.dumps(low(err), indent=2) + "\n")

if __name__ == "__main__":
  main()