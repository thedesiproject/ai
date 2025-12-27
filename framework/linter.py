#!/usr/bin/env python3
# --- framework/linter.py | checksum: auto ---
import argparse
import os
import subprocess
import sys
from pathlib import Path

os.environ["RUFF_NO_CACHE"] = "true"
config = {
  "skip": {".git", "node_modules", "__pycache__", "venv", ".venv", "build", "dist"},
  "preserve": {"#!", "# ---", "# [start", "# [end"},
  "indent": 2,
  "encoding": "utf-8",
}

def setup(parser):
  """Configuration for both standalone and dispatcher use."""
  parser.add_argument("paths", nargs="*", default=["."], help="Paths to lint/format")
  parser.add_argument(
    "--fix", action="store_true", help="Apply fixes and formatting in-place"
  )
  parser.add_argument(
    "--unsafe-fixes", action="store_true", help="Allow ruff to apply unsafe fixes"
  )

def legacy_surgical_clean(fp):
  """
  [RESTORED] Your original logic for whitespace and comment stripping.
  Runs LAST to ensure it has final authority over Ruff.
  """
  try:
    raw = fp.read_text(encoding=config["encoding"])
    lines, valid, prev_b = raw.splitlines(), [], False
    for i, line in enumerate(lines):
      s = line.strip()
      if s.startswith("#") and not any(
        s.lower().startswith(k) for k in config["preserve"]
      ):
        continue
      if not s:
        if (
          i + 1 < len(lines)
          and lines[i + 1]
          .strip()
          .startswith(("def ", "class ", "import ", "from ", "@", "if __name__"))
          and not prev_b
        ):
          valid.append("")
          prev_b = True
        continue
      if (
        not s.startswith(("import ", "from "))
        and valid
        and valid[-1].strip().startswith(("import ", "from "))
        and not prev_b
      ):
        valid.append("")
        prev_b = True
      valid.append(line.rstrip())
      prev_b = False
    while valid and not valid[-1]:
      valid.pop()
    final = "\n".join(valid).rstrip() + "\n"
    if final != raw:
      fp.write_text(final, encoding=config["encoding"])
  except Exception as e:
    print(f"Surgical clean error on {fp.name}: {e}", file=sys.stderr)

def run(args):
  """Hybrid Flow: Ruff Check -> Ruff Format -> Legacy Surgical Clean."""
  base_dir = Path(__file__).parent.parent.resolve()
  config_path = base_dir / "pyproject.toml"
  config_args = ["--config", str(config_path)] if config_path.exists() else []
  targets = args.paths if args.paths else ["."]
  skip_norm = {s.lower() for s in config["skip"]}
  try:
    lint_cmd = [sys.executable, "-m", "ruff", "check"]
    if args.fix:
      lint_cmd.append("--fix")
    if args.unsafe_fixes:
      lint_cmd.append("--unsafe-fixes")
    lint_cmd.extend(config_args + targets)
    lint_result = subprocess.run(lint_cmd, check=False)
    if args.fix:
      fmt_cmd = [sys.executable, "-m", "ruff", "format"] + config_args + targets
      subprocess.run(
        fmt_cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
      )
      for t in targets:
        tp = Path(t).resolve()
        file_list = tp.rglob("*.py") if tp.is_dir() else [tp]
        for f in file_list:
          if not f.is_file() or any(p.lower() in skip_norm for p in f.parts):
            continue
          legacy_surgical_clean(f)
    return {"status": "success", "exit_code": lint_result.returncode}
  except Exception as e:
    print(f"System Error: {e}", file=sys.stderr)
    return {"status": "error", "exit_code": 1}

def main():
  parser = argparse.ArgumentParser(prog="linter")
  setup(parser)
  args = parser.parse_args()
  outcome = run(args)
  sys.exit(outcome["exit_code"])

if __name__ == "__main__":
  main()
