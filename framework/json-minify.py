#!/usr/bin/env python3
# --- framework/json-minify.py | checksum: auto ---
import argparse
import contextlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

CFG = {"encoding": "utf-8", "compact_threshold": 80}

def find_files(paths: List[str]) -> List[Path]:
  """High-performance recursive file discovery."""
  results = []
  for p in paths:
    path = Path(p)
    if path.is_file() and path.suffix.lower() in {".json", ".csv"}:
      results.append(path)
    elif path.is_dir():
      results.extend(path.rglob("*.json"))
      results.extend(path.rglob("*.csv"))
  return sorted(set(results))

def extract_keys(data: Any, keys: Optional[Set[str]] = None) -> Set[str]:
  """Recursively extract all keys from nested structures."""
  if keys is None:
    keys = set()
  if isinstance(data, dict):
    for k, v in data.items():
      if not k.startswith("_"):
        keys.add(k)
      extract_keys(v, keys)
  elif isinstance(data, list):
    for item in data:
      extract_keys(item, keys)
  return keys

def generate_keymap_optimized(all_keys: Set[str]) -> Dict[str, str]:
  """Generate optimal abbreviation keymap from full key set."""
  sorted_keys = sorted(all_keys, key=len)
  keymap, used = {}, set()
  for key in sorted_keys:
    assigned = False
    if key and key[0] not in used:
      keymap[key[0]] = key
      used.add(key[0])
      assigned = True
    if not assigned:
      for i in range(1, 1000):
        cand = f"{key[0]}{i}"
        if cand not in used:
          keymap[cand] = key
          used.add(cand)
          assigned = True
          break
    if not assigned:
      for length in range(2, len(key) + 1):
        prefix = key[:length]
        if prefix not in used:
          keymap[prefix] = key
          used.add(prefix)
          assigned = True
          break
    if not assigned and key not in used:
      keymap[key] = key
      used.add(key)
  return keymap

class SmartFormatter:
  """Intelligent JSON formatter balancing readability and density."""

  @staticmethod
  def smart_format(
    obj: Any, indent: int = 0, threshold: int = CFG["compact_threshold"]
  ) -> str:
    """Format JSON with smart line breaking based on compact threshold."""
    if obj is None:
      return "null"
    elif isinstance(obj, bool):
      return "true" if obj else "false"
    elif isinstance(obj, (int, float, str)):
      return json.dumps(obj)
    elif isinstance(obj, list):
      compact = json.dumps(obj, separators=(",", ":"))
      if len(compact) <= threshold:
        return compact
      items = [SmartFormatter.smart_format(i, indent + 2, threshold) for i in obj]
      inner = ",\n" + " " * (indent + 2)
      return f"[\n{' ' * (indent + 2)}{inner.join(items)}\n{' ' * indent}]"
    elif isinstance(obj, dict):
      compact = json.dumps(obj, separators=(",", ":"))
      if len(compact) <= threshold:
        return compact
      items = [
        f'"{k}": {SmartFormatter.smart_format(v, indent + 2, threshold)}'
        for k, v in obj.items()
      ]
      inner = ",\n" + " " * (indent + 2)
      return f"{{\n{' ' * (indent + 2)}{inner.join(items)}\n{' ' * indent}}}"
    return json.dumps(obj)

class MinimalKeyAbbreviator:
  """Manages bidirectional key mapping for minification/expansion."""

  def __init__(self, keymap: Optional[Dict[str, str]] = None):
    self.short_to_long = keymap or {}
    self.long_to_short = {v: k for k, v in self.short_to_long.items()}
    self.used_shorts = set(self.short_to_long.keys())
    self.new_mappings = {}

  def _candidates(self, key: str) -> List[str]:
    """Generate candidate abbreviations for a key."""
    return [key[:i] for i in range(1, len(key) + 1)] + [
      f"{key[0]}{i}" for i in range(1, 101)
    ]

  def abbreviate(self, long_key: str) -> str:
    """Generate abbreviation for a long key."""
    if long_key in self.long_to_short:
      return self.long_to_short[long_key]
    for c in self._candidates(long_key):
      if c not in self.used_shorts:
        self.used_shorts.add(c)
        self.short_to_long[c] = long_key
        self.long_to_short[long_key] = c
        self.new_mappings[c] = long_key
        return c
    return long_key

  def apply(self, obj: Any, reverse: bool = False) -> Any:
    """Apply key mapping in forward or reverse direction."""
    if reverse:
      mapping = self.short_to_long
      if isinstance(obj, dict):
        return {mapping.get(k, k): self.apply(v, reverse=True) for k, v in obj.items()}
      elif isinstance(obj, list):
        return [self.apply(i, reverse=True) for i in obj]
      return obj
    else:
      if isinstance(obj, dict):
        return {self.abbreviate(k): self.apply(v, reverse=False) for k, v in obj.items()}
      elif isinstance(obj, list):
        return [self.apply(i, reverse=False) for i in obj]
      return obj

  def get_file_format(self) -> Dict[str, str]:
    """Get complete short→long mapping."""
    return self.short_to_long

  def get_new_mappings(self) -> Dict[str, str]:
    """Get only newly generated mappings."""
    return self.new_mappings

class KeyedJSONConverter:
  """Converts between array-of-objects and keyed JSON format."""

  @staticmethod
  def is_keyed_json(data: Any) -> bool:
    """Check if data is in keyed JSON format."""
    return isinstance(data, dict) and "_schema" in data

  @staticmethod
  def to_keyed(records: List[Dict], key_field: str) -> Dict:
    """Convert array of objects to keyed JSON format."""
    if not records:
      return {
        "_schema": {
          "format": f"keyed_json:{key_field}",
          "key_field": key_field,
          "fields": [],
        }
      }
    field_order, seen = [], set()
    for rec in records:
      for k in rec:
        if k != key_field and k not in seen:
          field_order.append(k)
          seen.add(k)
    res = {
      "_schema": {
        "format": f"keyed_json:{key_field}",
        "key_field": key_field,
        "fields": field_order,
      }
    }
    for rec in records:
      k = str(rec[key_field])
      res[k] = [rec.get(f) for f in field_order]
    return res

  @staticmethod
  def from_keyed(obj: Dict) -> List[Dict]:
    """Convert keyed JSON format back to array of objects."""
    schema = obj.get("_schema", {})
    kf = schema.get("key_field", "id")
    fields = schema.get("fields", [])
    records = []
    for k, v in obj.items():
      if k.startswith("_"):
        continue
      rec = {kf: k}
      for f, val in zip(fields, v):
        rec[f] = val
      records.append(rec)
    return records

class OptimizationEngine:
  """Unified transformation engine for all optimization modes."""

  def __init__(self, data: Any, abbrev: Optional[MinimalKeyAbbreviator] = None):
    self.data = data
    self.abbrev = abbrev
    self.optimizations: List[str] = []

  def remove_nulls(self) -> "OptimizationEngine":
    """Remove null values from data structures."""

    def proc(o):
      if isinstance(o, dict):
        return {
          k: v for k, v in ((kk, proc(vv)) for kk, vv in o.items()) if v is not None
        }
      elif isinstance(o, list):
        return [x for x in (proc(i) for i in o) if x is not None]
      return o
    self.data = proc(self.data)
    self.optimizations.append("null-removal")
    return self

  def compress_booleans(self) -> "OptimizationEngine":
    """Convert booleans to 1/0."""

    def proc(o):
      if isinstance(o, dict):
        return {k: proc(v) for k, v in o.items()}
      elif isinstance(o, list):
        return [proc(i) for i in o]
      elif isinstance(o, bool):
        return 1 if o else 0
      return o
    self.data = proc(self.data)
    self.optimizations.append("bool-compress")
    return self

  def abbreviate_keys(self) -> "OptimizationEngine":
    """Apply key abbreviation using abbreviator."""
    if self.abbrev is None:
      self.abbrev = MinimalKeyAbbreviator()
    self.data = self.abbrev.apply(self.data, reverse=False)
    self.optimizations.append("abbrev-keys")
    return self

  def expand_keys(self, short_to_long: Dict[str, str]) -> "OptimizationEngine":
    """Expand abbreviated keys back to original names."""

    def proc(o):
      if isinstance(o, dict):
        return {short_to_long.get(k, k): proc(v) for k, v in o.items()}
      elif isinstance(o, list):
        return [proc(i) for i in o]
      return o
    self.data = proc(self.data)
    self.optimizations.append("expand-keys")
    return self

  def convert_keyed_to_array(self) -> "OptimizationEngine":
    """Convert keyed JSON to array of objects."""
    if KeyedJSONConverter.is_keyed_json(self.data):
      self.data = KeyedJSONConverter.from_keyed(self.data)
      self.optimizations.append("from-keyed")
    return self

  def convert_array_to_keyed(
    self, key_field: Optional[str] = None
  ) -> "OptimizationEngine":
    """Convert array of objects to keyed JSON."""
    if isinstance(self.data, list):
      if key_field is None:
        key_field = list(self.data[0].keys())[0] if self.data and self.data[0] else "id"
      self.data = KeyedJSONConverter.to_keyed(self.data, key_field)
      self.optimizations.append("to-keyed")
    return self

  def flatten_structure(self) -> "OptimizationEngine":
    """Flatten nested structures into dot-notation keys."""

    def flat(obj, p=""):
      if isinstance(obj, dict):
        res = {}
        for k, v in obj.items():
          nk = f"{p}_{k}" if p else k
          if isinstance(v, (dict, list)):
            res.update(flat(v, nk))
          else:
            res[nk] = v
        return res
      elif isinstance(obj, list):
        res = {}
        for i, v in enumerate(obj):
          nk = f"{p}_{i}" if p else str(i)
          if isinstance(v, (dict, list)):
            res.update(flat(v, nk))
          else:
            res[nk] = v
        return res
      return {p: obj}
    self.data = flat(self.data)
    self.optimizations.append("flatten")
    return self

  def compact(self) -> "OptimizationEngine":
    """Mark for compact output."""
    self.optimizations.append("compact")
    return self

  def result(self) -> Any:
    """Get optimized data."""
    return self.data

  def get_optimizations_summary(self) -> str:
    """Get summary of applied optimizations."""
    return ", ".join(self.optimizations) if self.optimizations else "null"

def setup(parser: argparse.ArgumentParser) -> None:
  """Configure argument parser with all subcommands."""
  subparsers = parser.add_subparsers(dest="mode", help="Operation mode")
  scan_p = subparsers.add_parser("scan", help="Scan and generate keymap")
  scan_p.add_argument("input", nargs="+", help="Files or directories to scan")
  scan_p.add_argument("-o", "--output", type=Path, help="Output directory")
  scan_p.add_argument("--key-map", type=Path, help="Keymap file path")
  minify_p = subparsers.add_parser("minify", help="Minify JSON/CSV files")
  minify_p.add_argument("input", nargs="+", help="Files or directories to minify")
  minify_p.add_argument("-o", "--output", type=Path, help="Output directory")
  minify_p.add_argument("--key-map", type=Path, help="Keymap file path")
  minify_p.add_argument("--compact", action="store_true", help="Compact JSON output")
  minify_p.add_argument("--pretty", action="store_true", help="Pretty print JSON output")
  minify_p.add_argument("--null-removal", action="store_true", help="Remove null values")
  minify_p.add_argument(
    "--bool-compress", action="store_true", help="Compress booleans to 0/1"
  )
  minify_p.add_argument(
    "--flatten", action="store_true", help="Flatten nested structures"
  )
  minify_p.add_argument(
    "--keyed", type=str, nargs="?", const="__first__", help="Convert to keyed JSON"
  )
  expand_p = subparsers.add_parser("expand", help="Expand minified JSON")
  expand_p.add_argument("input", nargs="+", help="Files or directories to expand")
  expand_p.add_argument("-o", "--output", type=Path, help="Output directory")
  expand_p.add_argument("--key-map", type=Path, required=True, help="Keymap file path")
  expand_p.add_argument("--compact", action="store_true", help="Compact JSON output")
  expand_p.add_argument("--pretty", action="store_true", help="Pretty print JSON output")

def run(args: argparse.Namespace, context: Optional[Dict] = None) -> Dict[str, Any]:
  """Core execution logic. Supports dispatcher integration with optional context."""
  try:
    if not hasattr(args, "mode") or not args.mode:
      return {"status": "error", "message": "No mode specified", "exit_code": 1}
    files = find_files(args.input)
    if not files:
      return {"status": "error", "message": "No JSON/CSV files found", "exit_code": 1}
    enc = CFG["encoding"]
    if args.mode == "scan":
      all_keys = set()
      for f in files:
        with contextlib.suppress(Exception):
          all_keys.update(extract_keys(json.loads(f.read_text(encoding=enc))))
      km = generate_keymap_optimized(all_keys)
      if args.key_map:
        args.key_map.parent.mkdir(parents=True, exist_ok=True)
        args.key_map.write_text(json.dumps(km, indent=2), encoding=enc)
      total_original = sum(len(k) for k in km.values())
      total_compressed = sum(len(a) for a in km)
      savings = 100 * (1 - total_compressed / total_original) if total_original else 0
      return {
        "status": "success",
        "mode": "scan",
        "keys_found": len(all_keys),
        "keymap_entries": len(km),
        "savings_pct": round(savings, 1),
        "keymap_file": str(args.key_map) if args.key_map else None,
        "exit_code": 0,
      }
    elif args.mode == "minify":
      km = {}
      if args.key_map and args.key_map.exists():
        km = json.loads(args.key_map.read_text(encoding=enc))
      abbrev = MinimalKeyAbbreviator(km)
      if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
      results = []
      total_savings = 0
      for fp in files:
        try:
          original_size = fp.stat().st_size
          original_content = fp.read_text(encoding=enc)
          d = json.loads(original_content)
          opt = OptimizationEngine(d, abbrev)
          if args.null_removal:
            opt.remove_nulls()
          if args.bool_compress:
            opt.compress_booleans()
          if args.key_map:
            opt.abbreviate_keys()
          if args.keyed:
            kf = args.keyed if args.keyed != "__first__" else None
            opt.convert_array_to_keyed(kf)
          if args.flatten:
            opt.flatten_structure()
          d = opt.result()
          if args.compact:
            oj = json.dumps(d, separators=(",", ":"))
          elif args.pretty:
            oj = json.dumps(d, indent=2)
          else:
            oj = SmartFormatter.smart_format(d) if opt.optimizations else original_content
          if args.output:
            of = args.output / f"{fp.stem}-out.json"
            of.write_text(oj, encoding=enc)
            os_new = len(oj.encode(enc))
            sav = 100 * (1 - os_new / original_size) if original_size else 0
            results.append(
              {"file": fp.name, "output": of.name, "savings_pct": round(sav, 1)}
            )
            total_savings += sav
        except Exception as e:
          results.append({"file": fp.name, "error": str(e)})
      if args.key_map:
        args.key_map.write_text(
          json.dumps(abbrev.get_file_format(), indent=2), encoding=enc
        )
      return {
        "status": "success",
        "mode": "minify",
        "files_processed": len(files),
        "avg_savings_pct": round(total_savings / len(files) if files else 0, 1),
        "results": results,
        "exit_code": 0,
      }
    elif args.mode == "expand":
      if not args.key_map or not args.key_map.exists():
        return {
          "status": "error",
          "message": "--key-map required for expand mode",
          "exit_code": 1,
        }
      km = json.loads(args.key_map.read_text(encoding=enc))
      rev_km = {v: k for k, v in km.items()}
      if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
      results = []
      for fp in files:
        try:
          d = json.loads(fp.read_text(encoding=enc))
          opt = OptimizationEngine(d)
          opt.expand_keys(rev_km)
          d = opt.result()
          if args.pretty:
            oj = json.dumps(d, indent=2)
          elif args.compact:
            oj = json.dumps(d, separators=(",", ":"))
          else:
            oj = json.dumps(d)
          if args.output:
            of = args.output / f"{fp.stem}-expanded.json"
            of.write_text(oj, encoding=enc)
            results.append({"file": fp.name, "output": of.name})
        except Exception as e:
          results.append({"file": fp.name, "error": str(e)})
      return {
        "status": "success",
        "mode": "expand",
        "files_processed": len(files),
        "results": results,
        "exit_code": 0,
      }
  except Exception as e:
    print(f"System Error: {e}", file=sys.stderr)
    return {"status": "error", "exit_code": 1}

def main() -> None:
  """Standalone CLI entry point."""
  parser = argparse.ArgumentParser(
    prog="json-minify", description="JSON/CSV optimization framework"
  )
  setup(parser)
  args = parser.parse_args()
  outcome = run(args, context=None)
  sys.exit(outcome.get("exit_code", 1))

if __name__ == "__main__":
  main()
