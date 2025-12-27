#!/usr/bin/env python3
# --- framework/runner.py | checksum: auto ---
import argparse, json, sys, importlib.util, os, traceback, re
from pathlib import Path

tools_dir = "tools"
max_line = 320
def low(o):
  if isinstance(o, str): return o.lower()
  if isinstance(o, list): return [low(i) for i in o]
  if isinstance(o, dict): return {k.lower(): low(v) for k, v in o.items()}
  return o
def smart_format(obj, indent=0):
  flat = json.dumps(obj, separators=(",", ": "))
  if len(" " * indent + flat) <= max_line:
    return flat
  space = " " * indent
  sub = indent + 2
  if isinstance(obj, dict):
    items = [f'"{k}": {smart_format(v, sub)}' for k, v in obj.items()]
    return "{\n" + " " * sub + (",\n" + " " * sub).join(items) + "\n" + space + "}"
  if isinstance(obj, list):
    items = [smart_format(v, sub) for v in obj]
    return "[\n" + " " * sub + (",\n" + " " * sub).join(items) + "\n" + space + "]"
  return flat
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
    if isinstance(res, dict) and "data" in res and len(res) == 2:
      res = {"status": res.get("status", "success"), **res["data"]}
    formatted = smart_format(low(res))
    sys.stdout.write(formatted + "\n")
  except Exception as e:
    err = {"status": "error", "msg": str(e).lower()}
    if args.debug: err["trace"] = traceback.format_exc().lower()
    sys.stdout.write(json.dumps(low(err), indent=2) + "\n")
if __name__ == "__main__":
  main()
