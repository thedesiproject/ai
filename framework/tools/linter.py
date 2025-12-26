#!/usr/bin/env python3
# --- framework/tools/linter.py | d4c5b6a7f8e9 ---
import sys, argparse, json
from pathlib import Path

config = {
  "skip": ["node_modules", "dist", ".git", "__pycache__"],
  "keep": ["#!", "# ---", "# [start", "# [end"]
}

def setup(p):
  p.add_argument("t", nargs="*", default=["."], metavar="path")
  p.add_argument("--fix", action="store_true")

def run(a):
  res = {"processed": 0, "fixed": 0, "errors": [], "files": []}
  root = Path.cwd()
  for t in a.t:
    tp = Path(t).resolve()
    if not tp.exists(): continue
    for f in (tp.rglob("*.py") if tp.is_dir() else [tp]):
      if not f.is_file() or any(x in f.parts for x in config["skip"]): continue
      f_abs = f.resolve()
      f_rel = str(f_abs.relative_to(root)).lower() if root in f_abs.parents or root == f_abs else str(f_abs).lower()
      res["processed"] += 1
      res["files"].append(f_rel)
      src = f.read_text().splitlines()
      valid = [l for l in src if not (l.strip().startswith("#") and not any(l.strip().lower().startswith(z) for z in config["keep"]))]
      if len(valid) != len(src):
        res["errors"].append(f_rel)
        if a.fix:
          f.write_text("\n".join(valid).rstrip() + "\n")
          res["fixed"] += 1
  return {"status": "success", "data": res}

if __name__ == "__main__":
  def low(o):
    if isinstance(o, str): return o.lower()
    if isinstance(o, list): return [low(i) for i in o]
    if isinstance(o, dict): return {k.lower(): low(v) for k, v in o.items()}
    return o
  p = argparse.ArgumentParser()
  p.add_argument("--debug", action="store_true")
  setup(p)
  args = p.parse_args()
  try:
    sys.stdout.write(json.dumps(low(run(args)), indent=2))
  except Exception as e:
    err = {"status": "error", "msg": str(e).lower()}
    if args.debug:
      import traceback
      err["trace"] = traceback.format_exc().lower()
    sys.stdout.write(json.dumps(low(err), indent=2))