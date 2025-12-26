import json
import os
import argparse
from pathlib import Path
from typing import List, Dict, Any, Set

COMPACT_THRESHOLD = 80

def extract_keys(data, keys: Set[str] = None):
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
  sorted_keys = sorted(all_keys, key=len)
  keymap, used = {}, set()
  for key in sorted_keys:
    assigned = False
    if len(key) >= 1:
      prefix = key[0]
      if prefix not in used:
        keymap[prefix] = key
        used.add(prefix)
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

def find_files(paths: List[str]) -> List[Path]:
  results = []
  for path_str in paths:
    path = Path(path_str)
    if path.is_file() and path.suffix.lower() in [".json", ".csv"]:
      results.append(path)
    elif path.is_dir():
      results.extend(path.rglob("*.json"))
      results.extend(path.rglob("*.csv"))
  return sorted(set(results))

class MinimalKeyAbbreviator:
  def __init__(self, key_map: Dict[str, str] = None):
    self.short_to_long = key_map if key_map else {}
    self.long_to_short = {v: k for k, v in self.short_to_long.items()}
    self.used_shorts = set(self.short_to_long.keys())
    self.new_mappings = {}

  def _candidates(self, key: str):
    result = [key[:i] for i in range(1, len(key) + 1)]
    result.extend(f"{key[0]}{i}" for i in range(1, 101))
    return result

  def abbreviate(self, long_key: str) -> str:
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

  def apply(self, obj: Any) -> Any:
    if isinstance(obj, dict):
      return {self.abbreviate(k): self.apply(v) for k, v in obj.items()}
    elif isinstance(obj, list):
      return [self.apply(item) for item in obj]
    return obj

  def get_file_format(self) -> Dict[str, str]:
    return self.short_to_long

  def get_new_mappings(self) -> Dict[str, str]:
    return self.new_mappings

class SmartFormatter:
  @staticmethod
  def smart_format(obj: Any, indent=0, threshold=COMPACT_THRESHOLD):
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
      items = [SmartFormatter.smart_format(it, indent + 2, threshold) for it in obj]
      inner = (",\n" + " " * (indent + 2)).join(items)
      return f"[\n{' ' * (indent + 2)}{inner}\n{' ' * indent}]"
    elif isinstance(obj, dict):
      compact = json.dumps(obj, separators=(",", ":"))
      if len(compact) <= threshold:
        return compact
      items = [
        f'"{k}": {SmartFormatter.smart_format(v, indent + 2, threshold)}'
        for k, v in obj.items()
      ]
      inner = (",\n" + " " * (indent + 2)).join(items)
      return f"{{\n{' ' * (indent + 2)}{inner}\n{' ' * indent}}}"
    return json.dumps(obj)

class KeyedJSONConverter:
  @staticmethod
  def is_keyed_json(data):
    return isinstance(data, dict) and "_schema" in data

  @staticmethod
  def to_keyed(records: List[Dict], key_field: str) -> Dict:
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
      for k in rec.keys():
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
  def __init__(self, data: Any, abbrev: MinimalKeyAbbreviator = None):
    self.data = data
    self.abbrev = abbrev
    self.optimizations = []

  def remove_nulls(self):
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

  def compress_booleans(self):
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

  def abbreviate_keys(self):
    if self.abbrev is None:
      self.abbrev = MinimalKeyAbbreviator()
    self.data = self.abbrev.apply(self.data)
    self.optimizations.append("abbrev-keys")
    return self

  def expand_keys(self, short_to_long: Dict[str, str]):
    def proc(o):
      if isinstance(o, dict):
        return {short_to_long.get(k, k): proc(v) for k, v in o.items()}
      elif isinstance(o, list):
        return [proc(i) for i in o]
      return o

    self.data = proc(self.data)
    self.optimizations.append("expand-keys")
    return self

  def convert_keyed_to_array(self):
    if KeyedJSONConverter.is_keyed_json(self.data):
      self.data = KeyedJSONConverter.from_keyed(self.data)
      self.optimizations.append("from-keyed")
    return self

  def convert_array_to_keyed(self, key_field: str = None):
    if isinstance(self.data, list):
      if key_field is None:
        key_field = list(self.data[0].keys())[0] if self.data and self.data[0] else "id"
      self.data = KeyedJSONConverter.to_keyed(self.data, key_field)
      self.optimizations.append("to-keyed")
    return self

  def compact(self):
    self.optimizations.append("compact")
    return self

  def flatten_structure(self):
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

  def result(self):
    return self.data

  def get_optimizations_summary(self):
    return ", ".join(self.optimizations) if self.optimizations else "null"

def setup_arguments(subparser):
  subparser.add_argument(
    "mode",
    nargs="?",
    default="minify",
    choices=["scan", "minify", "expand"],
  )
  subparser.add_argument("input", nargs="+")
  subparser.add_argument("-o", "--output", type=Path)
  subparser.add_argument("--key-map", type=Path)
  subparser.add_argument("--compact", action="store_true")
  subparser.add_argument("--pretty", action="store_true")
  subparser.add_argument("--null-removal", action="store_true")
  subparser.add_argument("--bool-compress", action="store_true")
  subparser.add_argument("--flatten", action="store_true")
  subparser.add_argument("--keyed", type=str, nargs="?", const="__first__")

def run_task(args, context=None):
  try:
    if args.mode == "scan":
      files = find_files(args.input)
      if not files:
        return {"error": "No JSON/CSV files found"}
      all_keys = set()
      for f in files:
        try:
          data = json.loads(f.read_text(encoding="utf-8"))
          all_keys.update(extract_keys(data))
        except Exception as e:
          pass
      km = generate_keymap_optimized(all_keys)
      total_original = sum(len(k) for k in km.values())
      total_compressed = sum(len(a) for a in km.keys())
      savings = 100 * (1 - total_compressed / total_original) if total_original else 0
      if args.key_map:
        args.key_map.parent.mkdir(parents=True, exist_ok=True)
        args.key_map.write_text(json.dumps(km, indent=2), encoding="utf-8")
      return {
        "mode": "scan",
        "keys_found": len(all_keys),
        "keymap_entries": len(km),
        "savings_pct": round(savings, 1),
        "keymap_file": str(args.key_map) if args.key_map else None,
      }

    elif args.mode == "minify":
      files = find_files(args.input)
      if not files:
        return {"error": "No JSON/CSV files found"}
      km = {}
      if args.key_map and args.key_map.exists():
        km = json.loads(args.key_map.read_text(encoding="utf-8"))
      abbrev = MinimalKeyAbbreviator(km)
      if args.output:
        args.output.mkdir(parents=True, exist_ok=True)

      results = []
      total_savings = 0
      for fp in files:
        try:
          original_size = fp.stat().st_size
          original_content = fp.read_text(encoding="utf-8")
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
            oj = (
              SmartFormatter.smart_format(d)
              if len(opt.optimizations) > 0
              else original_content
            )
          if args.output:
            of = args.output / f"{fp.stem}-out.json"
            of.write_text(oj, encoding="utf-8")
            os_new = len(oj.encode("utf-8"))
            sav = 100 * (1 - os_new / original_size) if original_size else 0
            results.append(
              {"file": fp.name, "output": of.name, "savings_pct": round(sav, 1)}
            )
            total_savings += sav
        except Exception as e:
          results.append({"file": fp.name, "error": str(e)})
      if args.key_map and abbrev:
        args.key_map.write_text(
          json.dumps(abbrev.get_file_format(), indent=2), encoding="utf-8"
        )
      return {
        "mode": "minify",
        "files_processed": len(files),
        "avg_savings_pct": round(total_savings / len(files) if files else 0, 1),
        "results": results,
      }

    elif args.mode == "expand":
      if not args.key_map or not args.key_map.exists():
        return {"error": "--key-map required for expand mode"}
      km = json.loads(args.key_map.read_text(encoding="utf-8"))
      rev_km = {v: k for k, v in km.items()}
      files = find_files(args.input)
      if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
      results = []
      for fp in files:
        try:
          d = json.loads(fp.read_text(encoding="utf-8"))
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
            of.write_text(oj, encoding="utf-8")
            results.append({"file": fp.name, "output": of.name})
        except Exception as e:
          results.append({"file": fp.name, "error": str(e)})
      return {"mode": "expand", "files_processed": len(files), "results": results}

  except Exception as e:
    return {"error": str(e), "error_type": type(e).__name__}
