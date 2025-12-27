#!/usr/bin/env python3
# --- run.py | checksum: auto ---
import sys
import subprocess
import json
import argparse
from pathlib import Path

config = {
    "tools_dir": "framework/tools",
    "ignore_patterns": {".git", "__pycache__", ".pyc", "node_modules", ".env", ".venv"},
    "default_extensions": {".py", ".json"},
    "hash_length": 16,
    "encoding": "utf-8",
}

def get_tools():
    """Scan and normalize tool names using the central config."""
    base_dir = Path(__file__).parent.resolve()
    tools_path = base_dir / config["tools_dir"]
    if not tools_path.exists():
        return {}
    tools = {}
    for f in tools_path.glob("*.py"):
        if f.name == "__init__.py" or f.name in config["ignore_patterns"]:
            continue
        tools[f.stem.replace("_", "-")] = f
    return tools

def main():
    tools = get_tools()
    parser = argparse.ArgumentParser(
        prog="./run.py",
        description="Project tool dispatcher.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "tool",
        nargs="?",
        choices=sorted(tools.keys()),
        help="The tool to execute"
    )
    parser.add_argument(
        "subargs",
        nargs=argparse.REMAINDER,
        help="Arguments passed directly to the tool"
    )
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
        print(json.dumps(err, separators=(',', ':')), file=sys.stderr)
        sys.exit(1)
if __name__ == "__main__":
    main()
