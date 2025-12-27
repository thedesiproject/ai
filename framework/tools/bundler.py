#!/usr/bin/env python3

import hashlib
import argparse
import json
import subprocess
from pathlib import Path
from datetime import datetime

config = {
    "ignore_patterns": ['.git', '__pycache__', '.pyc', 'node_modules', '.env', '.venv'],
    "default_extensions": ['.py', '.json'],
    "hash_length": 16,
    "encoding": 'utf-8',
    "encoding_errors": 'ignore'
}

def get_hash(s, algo):
  return hashlib.new(algo, s.encode()).hexdigest()[:config["hash_length"]]

def setup(p):
  p.add_argument("paths", nargs="*", help="Paths to bundle (optional)")
  p.add_argument("-o", "--out-dir", default="dist", help="Output directory (default: dist)")
  p.add_argument("-m", "--mode", choices=["git", "changed", "all"], default="git", help="File selection mode (default: git)")
  p.add_argument("-a", "--algo", choices=["md5", "sha256"], default="sha256", help="Hash algorithm (default: sha256)")
  p.add_argument("--manifest", action="store_true", help="Save manifest.json with file hashes (default: False)")
  p.add_argument("--diff", action="store_true", help="Only bundle changed files (requires previous manifest.json)")

def run(a):
  out_dir = Path(a.out_dir)
  out_dir.mkdir(parents=True, exist_ok=True)
  out_file = out_dir / "bundle.py"
  mf_p = out_dir / "manifest.json"
  root = Path.cwd()
  mf = json.loads(mf_p.read_text()) if mf_p.exists() else {}
  if not a.paths:
    if a.manifest:
      mf_p.write_text(json.dumps(mf, indent=2))
      return {"status": "success", "msg": "manifest only", "manifest": str(mf_p), "outputs": [str(mf_p)]}
    else:
      return {"status": "error", "msg": "no paths specified and --manifest not set"}
  if a.mode == "git":
    cmd = ["git", "ls-files"]
  elif a.mode == "changed":
    cmd = ["git", "ls-files", "-o", "--exclude-standard"]
  else:
    cmd = None
  fs = []
  for path in a.paths:
    if cmd:
      try:
        files = subprocess.check_output(cmd + [path]).decode().splitlines()
        fs.extend([Path(f).resolve() for f in files if f.endswith(".py")])
      except:
        pass
    else:
      fs.extend([f.resolve() for f in Path(path).rglob("*.py") if f.is_file()])
  items, state = [], {}
  for f in sorted(set(fs)):
    try:
      rel = str(f.relative_to(root.resolve())).lower()
    except ValueError:
      rel = str(f).lower()
    txt = f.read_text().strip()
    h = get_hash(txt, a.algo)
    state[rel] = h
    if not a.diff or mf.get(rel) != h:
      items.append(f"# [start: {rel} | {h}]\n{txt}\n# [end: {rel}]")
  if a.manifest:
    mf_p.write_text(json.dumps(state, indent=2))
  body = "\n\n".join(items)
  out_file.write_text(f"#!/usr/bin/env python3\n# --- bundle | {get_hash(body, a.algo)} ---\n\n{body}\n")
  outputs = [str(out_file)]
  if a.manifest:
    outputs.append(str(mf_p))
  return {
    "status": "success",
    "bundle": str(out_file),
    "manifest": str(mf_p) if a.manifest else None,
    "total": len(fs),
    "delta": len(items),
    "outputs": outputs
  }
if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Bundle Python files with optional manifest")
  setup(parser)
  args = parser.parse_args()
  result = run(args)
  print(json.dumps(result, indent=2))
