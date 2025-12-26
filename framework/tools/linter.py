#!/usr/bin/env python3
# --- framework/tools/linter.py | checksum: auto ---
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