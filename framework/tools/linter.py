#!/usr/bin/env python3
# --- framework/tools/linter.py | checksum: auto ---
import argparse
import subprocess
import sys
from pathlib import Path


def setup(parser):
  """Configuration for both standalone and dispatcher use."""
  parser.add_argument("paths", nargs="*", default=["."], help="Paths to lint/format")
  parser.add_argument("--fix", action="store_true", help="Apply fixes and formatting in-place")
  parser.add_argument("--check", action="store_true", help="Linting check only (exit code 1 if issues found)")
  parser.add_argument("--unsafe-fixes", action="store_true", help="Allow ruff to apply unsafe fixes (e.g. ERA001)")


def run(args):
  """Core logic using ruff with 2-pass (check + format) execution."""
  # 1. Resolve paths once
  base_dir = Path(__file__).parent.parent.resolve()
  config_path = base_dir / "config" / "pyproject.toml"
  config_args = ["--config", str(config_path)] if config_path.exists() else []
  targets = args.paths if args.paths else ["."]

  try:
    # 2. Execution Pass 1: Linting (ruff check)
    # Using sys.executable -m ruff ensures we use the environment's specific ruff version
    lint_cmd = [sys.executable, "-m", "ruff", "check"]
    if args.fix:
      lint_cmd.append("--fix")
    if args.unsafe_fixes:
      lint_cmd.append("--unsafe-fixes")
    lint_cmd.extend(config_args + targets)

    lint_result = subprocess.run(lint_cmd, check=False)

    # 3. Execution Pass 2: Formatting (ruff format)
    # This is required to enforce the 'indent-width = 2' from pyproject.toml
    if args.fix:
      fmt_cmd = [sys.executable, "-m", "ruff", "format"] + config_args + targets
      subprocess.run(fmt_cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return {"status": "success", "exit_code": lint_result.returncode}

  except FileNotFoundError:
    print("Error: ruff not found. Install with: pip install ruff", file=sys.stderr)
    return {"status": "error", "exit_code": 1}
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
