#!/usr/bin/env python3
# --- framework/json-nest.py | checksum: auto ---
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ------------------- Configuration -------------------
config = {
  "exclude": ["protocol-schema.json"],
  "auto_sum_prefix": "protocols-",
  "indent": 2,
  "encoding": "utf-8",
  "length_marker": "__LENGTH__",
  "manifest_key": "manifest"
}
# ------------------- Core Utilities -------------------

def recursive_sum(data: Any) -> int:
  """Recursively sum __LENGTH__ markers in nested structures."""
  if isinstance(data, list):
    return sum(recursive_sum(item) for item in data)
  if not isinstance(data, dict):
    return 0
  total = 0
  for k, v in data.items():
    if k in (config["length_marker"], config["manifest_key"]):
      continue
    if isinstance(v, (dict, list)):
      if isinstance(v, dict) and config["length_marker"] in v:
        total += v[config["length_marker"]]
      else:
        total += recursive_sum(v)
  return total

def apply_anchors(
  key: str, data: Any, l_list: List[str], s_list: List[str]
) -> Tuple[Any, int]:
  """Apply __LENGTH__ markers based on provided anchor lists."""
  actual_count = 0
  if isinstance(data, (dict, list)):
    actual_count = len(data)
    if isinstance(data, dict):
      actual_count = len(
        [k for k in data if k not in (config["length_marker"], config["manifest_key"])]
      )
  count_val: Optional[int] = None
  if key in l_list:
    count_val = actual_count
  elif key in s_list:
    count_val = recursive_sum(data)
  if count_val is not None and isinstance(data, dict):
    data[config["length_marker"]] = count_val
  return data, count_val if count_val is not None else actual_count

def extract_and_merge_json(raw_content: str) -> Dict[str, Any]:
  """Clean 'dirty' JSON and merge multiple objects discovered in raw text."""
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

def unnest(d: Any, pk: str = "") -> Dict[str, Any]:
  """Flatten nested JSON structure into underscore-delimited root keys."""
  res = {}
  if isinstance(d, dict):
    for k, v in d.items():
      if k.startswith("_") or k == config["manifest_key"]:
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
# ------------------- Operation Handlers -------------------

def do_nest(args: argparse.Namespace) -> Dict[str, Any]:
  """Logic for merging multiple JSON files into a nested structure."""
  l_keys, s_keys = list(args.length or []), list(args.sum or [])
  paths = [
    f
    for p in args.paths
    for f in ([Path(p)] if Path(p).is_file() else sorted(Path(p).glob("**/*.json")))
  ]
  files = sorted(set([f for f in paths if f.name not in config["exclude"]]))
  if not files:
    return {"status": "error", "msg": "no json files found", "exit_code": 1}
  nested_data, manifest = {}, {}
  identity = (
    Path(args.paths[0]).name if Path(args.paths[0]).is_dir() else Path(args.output).stem
  )
  for target in files:
    try:
      content = extract_and_merge_json(target.read_text(encoding=config["encoding"]))
      if not content:
        continue
      key = (
        content.pop("key")
        if isinstance(content, dict) and "key" in content
        else target.stem
      )
      if isinstance(content, dict) and len(content) == 1 and key in content:
        content = content[key]
      if args.flat and isinstance(content, dict):
        nested_data.update(content)
      else:
        nested_data[key] = content
    except Exception as e:
      sys.stderr.write(f"SKIP NEST: {target.name} | {str(e)}\n")
  if not args.flat:
    if identity.startswith(args.auto_sum_prefix) and identity not in s_keys:
      s_keys.append(identity)
    for key in list(nested_data.keys()):
      content, count = apply_anchors(key, nested_data[key], l_keys, s_keys)
      if key in s_keys:
        manifest[f"{key}_total"] = count
      nested_data[key] = content
    nested_data, root_count = apply_anchors(identity, nested_data, l_keys, s_keys)
    if identity in s_keys:
      manifest[f"{identity}_total"] = root_count
  try:
    wrapper = json.loads(args.wrap) if args.wrap else {}
  except json.JSONDecodeError:
    return {"status": "error", "msg": "Invalid JSON in --wrap", "exit_code": 1}
  final_output = (
    {**wrapper, config["manifest_key"]: manifest, **nested_data}
    if not args.flat
    else {**wrapper, **nested_data}
  )
  if not manifest:
    final_output.pop(config["manifest_key"], None)
  if isinstance(final_output, dict) and not args.flat:
    final_output[config["length_marker"]] = (
      recursive_sum(final_output)
      if s_keys
      else len(
        [
          k
          for k in final_output
          if k not in (config["length_marker"], config["manifest_key"])
        ]
      )
    )
  args.output.parent.mkdir(parents=True, exist_ok=True)
  args.output.write_text(
    json.dumps(final_output, indent=config["indent"], ensure_ascii=False),
    encoding=config["encoding"],
  )
  return {
    "status": "success",
    "mode": "nest",
    "files_merged": len(files),
    "output_file": str(args.output),
    "exit_code": 0
  }

def do_unnest(args: argparse.Namespace) -> Dict[str, Any]:
  """Logic for merging and flattening multiple input files."""
  merged_flat = {}
  for p in args.paths:
    path_obj = Path(p)
    if not path_obj.exists():
      continue
    try:
      data = json.loads(path_obj.read_text(encoding=config["encoding"]))
      merged_flat.update(unnest(data))
    except Exception as e:
      sys.stderr.write(f"SKIP UNNEST: {path_obj.name} | {str(e)}\n")
  args.output.parent.mkdir(parents=True, exist_ok=True)
  args.output.write_text(
    json.dumps(merged_flat, indent=config["indent"], ensure_ascii=False),
    encoding=config["encoding"],
  )
  return {
    "status": "success",
    "mode": "unnest",
    "keys_flattened": len(merged_flat),
    "output_file": str(args.output),
    "exit_code": 0
  }
# ------------------- Entry Points -------------------

def setup(parser: argparse.ArgumentParser) -> None:
  parser.add_argument("mode", nargs="?", default="nest", choices=["nest", "unnest"])
  parser.add_argument("paths", nargs="+")
  parser.add_argument("-o", "--output", required=True, type=Path)
  parser.add_argument("--length", nargs="*", default=[])
  parser.add_argument("--sum", nargs="*", default=[])
  parser.add_argument("--wrap")
  parser.add_argument("--flat", action="store_true")
  parser.add_argument("--auto-sum-prefix", default=config["auto_sum_prefix"])

def run(args: argparse.Namespace, context: Optional[Dict] = None) -> Dict[str, Any]:
  try:
    return do_nest(args) if args.mode == "nest" else do_unnest(args)
  except Exception as e:
    return {
      "status": "error",
      "msg": str(e),
      "error_type": type(e).__name__,
      "exit_code": 1
    }

def main():
  parser = argparse.ArgumentParser(prog="json-nest")
  setup(parser)
  result = run(parser.parse_args())
  print(json.dumps(result, indent=config["indent"]))
  sys.exit(result.get("exit_code", 1))

if __name__ == "__main__":
  main()
