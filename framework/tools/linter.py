#!/usr/bin/env python3
# --- framework/tools/linter.py | checksum: auto ---
import argparse
from pathlib import Path

config = {
  "skip": ["node_modules", "dist", ".git", "__pycache__"],
  "keep": ["#!", "# ---", "# [start", "# [end"],
  "indent": 2
}

def setup(p):
  p.add_argument("t", nargs="*", default=["."], metavar="path")
  p.add_argument("--fix", action="store_true")

def run(a):
  res = {"processed": 0, "fixed": 0, "errors": []}
  root = Path.cwd()
  for t in a.t:
    tp = Path(t).resolve()
    if not tp.exists(): continue
    for f in (tp.rglob("*.py") if tp.is_dir() else [tp]):
      if not f.is_file() or any(x in f.parts for x in config["skip"]): continue
      f_abs = f.resolve()
      try:
        f_rel = str(f_abs.relative_to(root)).lower()
      except ValueError:
        f_rel = str(f_abs).lower()
      res["processed"] += 1
      src_raw = f.read_text()
      src = src_raw.splitlines()
      valid, prev_blank = [], False
      for i, l in enumerate(src):
        s = l.strip()
        if not s:
          if i + 1 < len(src) and src[i+1].strip().startswith(("def ", "class ", "import ", "from ", "@")) and not prev_blank:
            valid.append("")
            prev_blank = True
          continue
        if s.startswith("#") and not any(s.lower().startswith(z) for z in config["keep"]): continue
        is_imp = s.startswith(("import ", "from "))
        if not is_imp and valid and valid[-1].strip().startswith(("import ", "from ")) and not prev_blank:
          valid.append("")
          prev_blank = True
        indent = len(l) - len(l.lstrip())
        if indent % config["indent"] != 0:
          l = (" " * (round(indent / config["indent"]) * config["indent"])) + l.lstrip()
        valid.append(l.rstrip())
        prev_blank = False
      while valid and not valid[-1]: valid.pop()
      final = "\n".join(valid).rstrip() + "\n"
      if final != src_raw:
        res["errors"].append(f_rel)
        if a.fix:
          f.write_text(final)
          res["fixed"] += 1
  return {"status": "success", "data": res}
