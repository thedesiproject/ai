import subprocess
import sys


def setup_arguments(parser):
  parser.add_argument("--fix", action="store_true")


def run_task(args, config):
  c_p = "config/pyproject.toml"
  if getattr(args, "fix", False):
    subprocess.run(["ruff", "format", ".", "--config", c_p])
  res = subprocess.run(
    ["ruff", "check", ".", "--config", c_p], capture_output=True, text=True
  )
  sys.stdout.write(res.stdout if res.stdout else "Linting passed.\n")
