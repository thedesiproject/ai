#!/usr/bin/env python3
# --- framework/nest-json.py | checksum: auto ---
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

def extract_and_merge_json(raw_content: str) -> Dict[str, Any]:
  """Extract JSON from string, strip comments, fix minor syntax."""
  text = raw_content.lstrip("\ufeff")
  text = re.sub(r"//.*?\n|/\*.*?\*/", "", text, flags=re.DOTALL)
  text = re.sub(r",(\s*[}\]])", r"\1", text)
  text = re.sub(r"'([^'\"\\]*)'", r'"\1"', text)
  text = re.sub(r'([}\]"\d])\s*\n(\s*["{\[\d])', r"\1,\n\2", text).strip()
  decoder = json.JSONDecoder()
  objects, index = [], 0
  while index < len(text):
    chunk = text[index:].lstrip()
    if not chunk:
      break
    if not chunk.startswith(("{", "[")):
      index += 1
      continue
    try:
      obj, end_pos = decoder.raw_decode(chunk)
      objects.append(obj)
      index += len(text[index:]) - len(chunk) + end_pos
    except json.JSONDecodeError:
      index += 1
  if not objects:
    return {}
  if len(objects) == 1:
    return objects[0]
  merged = {}
  for obj in objects:
    if isinstance(obj, dict):
      merged.update(obj)
  return merged

def collect_json_files(paths: List[str]) -> List[Path]:
  """Collect JSON files from paths, exclude schema and pycache."""
  files = []
  for p in paths:
    path_obj = Path(p)
    if path_obj.is_file() and path_obj.name != "protocol-schema.json":
      files.append(path_obj)
    elif path_obj.is_dir():
      files.extend(
        [
          f
          for f in sorted(path_obj.glob("**/*.json"))
          if f.name != "protocol-schema.json"
        ]
      )
  return sorted(set(files))

def unnest(d: Any, pk: str = "") -> Dict[str, Any]:
  """Flatten nested JSON to root-level keys."""
  res = {}
  if isinstance(d, dict):
    for k, v in d.items():
      if k.startswith("_") or k == "manifest":
        continue
      nk = f"{pk}_{k}" if pk else k
      if isinstance(v, dict) and any(not x.startswith("_") for x in v):
        res.update(unnest(v, nk))
      else:
        res[nk] = v
  elif isinstance(d, list):
    for i, item in enumerate(d):
      nk = f"{pk}_{i}" if pk else str(i)
      if isinstance(item, (dict, list)):
        res.update(unnest(item, nk))
      else:
        res[nk] = item
  else:
    res[pk] = d
  return res

def _do_nest(args) -> Dict[str, Any]:
  """
  Nest JSON files into a single structure.
  Key behaviors:
    - Don't force __LENGTH__ at root
    - Respect --wrap without overriding nodes
    - Only add manifest if content exists
    - Apply --length markers only to specified keys
    - Clean output suitable for kernel.json
  """
  files = collect_json_files(args.paths)
  if not files:
    return {"status": "error", "msg": "no json files found"}
  nested_data = {}
  manifest = {}
  Path(args.paths[0]).name if Path(args.paths[0]).is_dir() else Path(args.output).stem
  for f in files:
    try:
      content = extract_and_merge_json(f.read_text(encoding="utf-8"))
      if not content:
        continue
      key = (
        content.pop("key") if isinstance(content, dict) and "key" in content else f.stem
      )
      if isinstance(content, dict) and len(content) == 1 and key in content:
        content = content[key]
      if args.flat and isinstance(content, dict):
        nested_data.update(content)
      else:
        nested_data[key] = content
      manifest[f.stem] = "ok"
    except Exception as e:
      sys.stderr.write(f"SKIP: {f.name} | {str(e)}\n")
  wrapper = json.loads(args.wrap) if args.wrap else {}
  final_output = {**wrapper, **nested_data} if wrapper else nested_data
  if manifest and not args.flat:
    final_output["manifest"] = manifest
  if not args.flat and args.length:
    for key in args.length:
      if key in final_output and isinstance(final_output[key], dict):
        final_output[key]["__LENGTH__"] = len(
          [k for k in final_output[key] if k != "manifest"]
        )
  if args.flat:
    final_output.pop("__LENGTH__", None)
  args.output.parent.mkdir(parents=True, exist_ok=True)
  args.output.write_text(
    json.dumps(final_output, indent=2, ensure_ascii=False), encoding="utf-8"
  )
  return {
    "status": "success",
    "files_merged": len(files),
    "output_file": str(args.output),
  }

def _do_unnest(args) -> Dict[str, Any]:
  """Flatten nested JSON structure to root-level keys."""
  if not args.paths or not Path(args.paths[0]).exists():
    return {"status": "error", "msg": "input file required for unnest"}
  d = json.loads(Path(args.paths[0]).read_text(encoding="utf-8"))
  flat = unnest(d)
  args.output.parent.mkdir(parents=True, exist_ok=True)
  args.output.write_text(json.dumps(flat, indent=2, ensure_ascii=False), encoding="utf-8")
  return {"status": "success", "keys_flattened": len(flat), "file": str(args.output)}

def setup(p):
  """Configure argument parser."""
  p.add_argument("mode", nargs="?", default="nest", choices=["nest", "unnest"])
  p.add_argument("paths", nargs="+")
  p.add_argument("-o", "--output", required=True, type=Path)
  p.add_argument("--flat", action="store_true", help="flatten to root (no nesting)")
  p.add_argument("--wrap", help="optional JSON wrapper object")
  p.add_argument("--length", nargs="*", default=[], help="keys to mark with __LENGTH__")
  p.add_argument("--sum", nargs="*", default=[], help="[deprecated] use --length instead")
  p.add_argument(
    "--auto-sum-prefix", default="protocols-", help="prefix for auto-sum keys"
  )

def run(a):
  """Route to appropriate operation."""
  try:
    if a.mode == "nest":
      return _do_nest(a)
    elif a.mode == "unnest":
      return _do_unnest(a)
    else:
      return {"status": "error", "msg": f"unknown mode: {a.mode}"}
  except Exception as e:
    return {"status": "error", "msg": str(e), "error_type": type(e).__name__}
if __name__ == "__main__":
  p = argparse.ArgumentParser(prog="nest-json")
  setup(p)
  result = run(p.parse_args())
  print(json.dumps(result, indent=2))
