#!/usr/bin/env python3
# --- framework/tools/bundler.py | checksum: auto ---
import argparse
import contextlib
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

config = {
  "ignore_patterns": {".git", "__pycache__", "node_modules", ".env", ".venv", "dist"},
  "default_extensions": {".py", ".json"},
  "hash_length": 16,
  "encoding": "utf-8",
  "encoding_errors": "ignore",
}

def get_hash(s, algo="sha256"):
  """Generate a stable hash for content comparison."""
  return hashlib.new(algo, s.encode(config["encoding"])).hexdigest()[
    : config["hash_length"]
  ]

def surgical_clean(txt):
  """Minify Python code specifically. Returns content with exactly one trailing newline."""
  preserve = {"#!", "# ---", "# [start", "# [end"}
  lines = txt.splitlines()
  valid, prev_b = [], False
  for i, line in enumerate(lines):
    s = line.strip()
    if s.startswith("#") and not any(s.lower().startswith(k) for k in preserve):
      continue
    if not s:
      if (
        i + 1 < len(lines)
        and lines[i + 1].strip().startswith(("def ", "class ", "import ", "from ", "@"))
        and not prev_b
      ):
        valid.append("")
        prev_b = True
      continue
    valid.append(line.rstrip())
    prev_b = False
  return "\n".join(valid).rstrip() + "\n"

def setup(p):
  """Standard dispatcher setup."""
  p.add_argument("paths", nargs="+", help="Paths to bundle (mandatory)")
  p.add_argument("-o", "--out-dir", default="build", help="Output directory")
  p.add_argument(
    "-m",
    "--mode",
    choices=["git", "changed", "all"],
    default="git",
    help="Selection mode",
  )
  p.add_argument(
    "-a", "--algo", choices=["md5", "sha256"], default="sha256", help="Hash algorithm"
  )
  p.add_argument("--manifest", action="store_true", help="Save manifest.json")
  p.add_argument("--diff", action="store_true", help="Only bundle changed files")
  p.add_argument(
    "--clean", action="store_true", help="Apply surgical cleaning to .py files"
  )

def atomic_write(path, content, is_json=False):
  """Helper to write files safely using a temporary file to prevent corruption."""
  with tempfile.NamedTemporaryFile(
    "w", dir=path.parent, delete=False, encoding=config["encoding"]
  ) as tf:
    if is_json:
      json.dump(content, tf, indent=2)
    else:
      tf.write(content)
    temp_name = tf.name
  os.replace(temp_name, path)

def run(a):
  """Main execution logic."""
  out_dir = Path(a.out_dir)
  out_dir.mkdir(parents=True, exist_ok=True)
  out_file = out_dir / "bundle.py"
  mf_p = out_dir / "manifest.json"
  root = Path.cwd()
  mf = {}
  if mf_p.exists():
    with contextlib.suppress(json.JSONDecodeError, OSError):
      mf = json.loads(mf_p.read_text(encoding=config["encoding"]))
  fs, warnings = [], []
  for path in a.paths:
    if a.mode in ("git", "changed"):
      cmd = (
        ["git", "ls-files"]
        if a.mode == "git"
        else ["git", "ls-files", "-o", "--exclude-standard"]
      )
      try:
        files = subprocess.check_output(
          cmd + [path], encoding=config["encoding"]
        ).splitlines()
        fs.extend(
          [
            Path(f).resolve()
            for f in files
            if Path(f).suffix in config["default_extensions"]
          ]
        )
      except subprocess.CalledProcessError:
        warnings.append(f"Git command failed for {path}")
    else:
      target = Path(path).resolve()
      if target.is_file():
        fs.append(target)
      else:
        fs.extend(
          [
            f.resolve()
            for f in target.rglob("*")
            if f.is_file() and f.suffix in config["default_extensions"]
          ]
        )
  if not fs:
    return {"status": "error", "msg": "No files found", "exit_code": 1}
  items, state = [], {}
  for f in sorted(set(fs)):
    if any(p in f.parts for p in config["ignore_patterns"]):
      continue
    try:
      rel = str(f.relative_to(root)).replace("\\", "/")
    except ValueError:
      rel = str(f).replace("\\", "/")
    txt_raw = f.read_text(encoding=config["encoding"], errors=config["encoding_errors"])
    txt = (
      surgical_clean(txt_raw) if a.clean and f.suffix == ".py" else txt_raw.strip() + "\n"
    )
    h = get_hash(txt, a.algo)
    state[rel] = h
    if not a.diff or mf.get(rel) != h:
      items.append(f"# [start: {rel} | {h}]\n{txt}# [end: {rel}]")
  if not items:
    if a.diff:
      if a.manifest:
        atomic_write(mf_p, state, is_json=True)
      return {"status": "success", "msg": "No changes to bundle", "exit_code": 0}
    else:
      return {"status": "error", "msg": "No files matching criteria", "exit_code": 1}
  if a.manifest:
    atomic_write(mf_p, state, is_json=True)
  body = "\n\n".join(items)
  bundle_header = (
    f"#!/usr/bin/env python3\n# --- bundle | {get_hash(body, a.algo)} ---\n\n"
  )
  atomic_write(out_file, bundle_header + body + "\n")
  return {
    "status": "success",
    "bundle": str(out_file),
    "total": len(fs),
    "bundled": len(items),
    "warnings": warnings,
    "exit_code": 0,
  }

def main():
  parser = argparse.ArgumentParser(prog="bundler")
  setup(parser)
  args = parser.parse_args()
  result = run(args)
  print(json.dumps(result, indent=2))
  sys.exit(result.get("exit_code", 0))
if __name__ == "__main__":
  main()
