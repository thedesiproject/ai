#!/usr/bin/env python3
# --- run.py | checksum: auto ---
import argparse
import json
import subprocess
import sys
from pathlib import Path

config = {
  "framework_dir": "framework",
  "ignore_patterns": {".git", "__pycache__", ".pyc", "node_modules", ".env", ".venv"},
  "default_extensions": {".py", ".json"},
  "hash_length": 16,
  "encoding": "utf-8",
}


def get_tools():
  """Scan and normalize tool names using the central config."""
  base_dir = Path(__file__).parent.resolve()
  framework_path = base_dir / config["framework_dir"]
  if not framework_path.exists():
    return {}
  tools = {}
  for f in framework_path.rglob("*.py"):
    if f.name == "__init__.py" or f.name in config["ignore_patterns"] or f.name == "run.py":
      continue
    tool_name = f.stem.replace("_", "-")
    if tool_name not in tools:
      tools[tool_name] = f
  return tools


def main():
  tools = get_tools()
  parser = argparse.ArgumentParser(prog="./run.py", description="Project tool dispatcher.", formatter_class=argparse.RawTextHelpFormatter)
  parser.add_argument("tool", nargs="?", choices=sorted(tools.keys()), help="The tool to execute")
  parser.add_argument("subargs", nargs=argparse.REMAINDER, help="Arguments passed directly to the tool")
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(0)
  args = parser.parse_args()
  tool_path = tools[args.tool]
  cmd = [sys.executable, str(tool_path)] + args.subargs
  try:
    result = subprocess.run(cmd, check=False)
    sys.exit(result.returncode)
  except KeyboardInterrupt:
    sys.exit(130)
  except Exception as e:
    err = {"status": "error", "msg": f"Dispatcher error: {str(e)}"}
    print(json.dumps(err, separators=(",", ":")), file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
  main()
