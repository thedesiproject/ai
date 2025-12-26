#!/usr/bin/env python3
# --- ./framework/tools/lint.py ---
import subprocess, os, sys, re
from pathlib import Path

def setup(p):
  p.add_argument("targets", nargs="*", default=["."], help="Targets")
  p.add_argument("--fix", action="store_true")

def run(a):
  root = Path(os.path.realpath(__file__)).parent.parent
  conf = root / "config/pyproject.toml"
  cmd = ["ruff", "check"]
  if conf.exists(): cmd.extend(["--config", str(conf)])
  if a.fix: cmd.append("--fix")
  cmd.extend(a.targets)
  res = subprocess.run(cmd, capture_output=True, text=True)
  out, c_errs = res.stdout if res.stdout else res.stderr, []
  for t in a.targets:
    p = Path(t)
    for f in (p.rglob("*.py") if p.is_dir() else [p]):
      if not f.exists() or f.is_dir(): continue
      lines = f.read_text().splitlines()
      new_lines = []
      for i, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith("#") and not (s.startswith("#!") or s.startswith("# ---")):
          c_errs.append(f"{f}:{i} \033[1;31m[COMMENT]\033[0m Human content detected")
          continue
        new_lines.append(line)
      if a.fix and len(new_lines) != len(lines):
        f.write_text("\n".join(new_lines) + "\n")
  if a.fix: c_errs = []
  if c_errs: out = (out + "\n" + "\n".join(c_errs)).strip()
  if sys.stdout.isatty():
    print(f"\033[1m➤ Linting {', '.join(a.targets)}\033[0m")
    print(out if out.strip() else "\033[1;32m✓ All clear\033[0m")
    sys.exit(1 if c_errs or res.returncode != 0 else 0)
  return {"status": "complete", "output": out}