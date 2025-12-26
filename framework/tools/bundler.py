#!/usr/bin/env python3
# --- ./framework/tools/bundler.py ---
import re
from pathlib import Path

def setup(p):
    p.add_argument("-o", "--out", default="dist/bundle.py")

def run(a):
    root = Path.cwd() / "framework" / "tools"
    output = Path(a.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    
    bundled = []
    for f in root.glob("*.py"):
        content = f.read_text()
        clean = re.sub(r'#.*', '', content)
        clean = re.sub(r'\n\s*\n', '\n', clean).strip()
        bundled.append(f"# {f.name}\n{clean}")
        
    output.write_text("\n".join(bundled))
    return {"status": "bundled", "file": str(output), "size": output.stat().st_size}
