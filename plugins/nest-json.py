import json
import sys
import argparse
import re
from pathlib import Path
from typing import List, Dict, Any

def recursive_sum(data):
    if not isinstance(data, dict): return 0
    total = 0
    for k, v in data.items():
        if k == "__LENGTH__" or k == "manifest": continue
        if isinstance(v, dict):
            if "__LENGTH__" in v:
                total += v["__LENGTH__"]
            else:
                total += recursive_sum(v)
    return total

def apply_anchors(key, data, l_list, s_list):
    if not isinstance(data, dict): return data, 0
    actual_count = len([k for k in data.keys() if k not in ("__LENGTH__", "manifest")])
    count_val = None
    if key in l_list:
        count_val = actual_count
    elif key in s_list:
        count_val = recursive_sum(data)
    if count_val is not None:
        data["__LENGTH__"] = count_val
        return data, count_val
    return data, actual_count

def extract_and_merge_json(raw_content: str) -> Dict[str, Any]:
    text = raw_content.lstrip("\ufeff")
    text = re.sub(r"//.*?\n|/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    text = re.sub(r"'([^'\"\\]*)'", r'"\1"', text)
    text = re.sub(r'([}\]"\d])\s*\n(\s*["{\[\d])', r"\1,\n\2", text).strip()
    decoder = json.JSONDecoder()
    objects, index = [], 0
    while index < len(text):
        chunk = text[index:].lstrip()
        if not chunk: break
        if not chunk.startswith(("{", "[")):
            index += 1
            continue
        try:
            obj, end_pos = decoder.raw_decode(chunk)
            objects.append(obj)
            index += len(text[index:]) - len(chunk) + end_pos
        except json.JSONDecodeError: index += 1
    if not objects: return {}
    if len(objects) == 1: return objects[0]
    merged = {}
    for obj in objects:
        if isinstance(obj, dict): merged.update(obj)
    return merged

def collect_json_files(paths: List[str]) -> List[Path]:
    files = []
    for p in paths:
        path_obj = Path(p)
        if path_obj.is_file():
            if path_obj.name != "protocol-schema.json": files.append(path_obj)
        elif path_obj.is_dir():
            files.extend([f for f in sorted(path_obj.glob("**/*.json")) if f.name != "protocol-schema.json"])
    return sorted(set(files))

def unnest(d: Any, pk: str = "") -> Dict[str, Any]:
    res = {}
    if isinstance(d, dict):
        for k, v in d.items():
            if k.startswith("_") or k == "manifest":
                continue
            nk = f"{pk}_{k}" if pk else k
            if isinstance(v, dict) and any(not x.startswith("_") for x in v.keys()):
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

def setup_arguments(subparser):
    subparser.add_argument(
        "mode",
        nargs="?",
        default="nest",
        choices=["nest", "unnest"],
    )
    subparser.add_argument("paths", nargs="+")
    subparser.add_argument("-o", "--output", required=True, type=Path)
    subparser.add_argument("--length", nargs="*", default=[])
    subparser.add_argument("--sum", nargs="*", default=[])
    subparser.add_argument("--wrap")
    subparser.add_argument("--flat", action="store_true")
    subparser.add_argument("--auto-sum-prefix", default="protocols-", help="Prefix for auto-sum keys")

def run_task(args, context=None):
    try:
        if args.mode == "nest":
            files = collect_json_files(args.paths)
            if not files:
                return {"error": "No JSON files found"}
            nested_data, manifest = {}, {}
            identity = Path(args.paths[0]).name if Path(args.paths[0]).is_dir() else Path(args.output).stem
            
            for target in files:
                try:
                    content = extract_and_merge_json(target.read_text(encoding="utf-8"))
                    if not content: continue
                    key = content.pop("key") if isinstance(content, dict) and "key" in content else target.stem
                    if isinstance(content, dict) and len(content) == 1 and key in content: content = content[key]
                    if args.flat and isinstance(content, dict):
                        nested_data.update(content)
                    else:
                        nested_data[key] = content
                except Exception as e:
                    sys.stderr.write(f"SKIP: {target.name} | {str(e)}\n")
            
            if not args.flat:
                if identity.startswith(args.auto_sum_prefix):
                    args.sum.append(identity)
                for key in list(nested_data.keys()):
                    content, count = apply_anchors(key, nested_data[key], args.length, args.sum)
                    if key in args.sum:
                        manifest[f"{key}_total"] = count
                    nested_data[key] = content
                nested_data, root_count = apply_anchors(identity, nested_data, args.length, args.sum)
                if identity in args.sum:
                    manifest[f"{identity}_total"] = root_count
            
            wrapper = json.loads(args.wrap) if args.wrap else {}
            final_output = {**wrapper, "manifest": manifest, **nested_data} if not args.flat else {**wrapper, **nested_data}
            if not manifest: final_output.pop("manifest", None)
            if isinstance(final_output, dict) and not args.flat:
                if args.sum:
                    final_output["__LENGTH__"] = sum(v.get("__LENGTH__", 0) for k, v in final_output.items() if isinstance(v, dict) and k != "manifest")
                else:
                    final_output["__LENGTH__"] = len([k for k in final_output.keys() if k not in ("__LENGTH__", "manifest")])
            
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(final_output, indent=2, ensure_ascii=False), encoding="utf-8")
            return {"mode": "nest", "files_merged": len(files), "output_file": str(args.output)}

        elif args.mode == "unnest":
            if not args.paths or not Path(args.paths[0]).exists():
                return {"error": "Input file required for unnest mode"}
            d = json.loads(Path(args.paths[0]).read_text(encoding="utf-8"))
            flat = unnest(d)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(flat, indent=2, ensure_ascii=False), encoding="utf-8")
            return {"mode": "unnest", "keys_flattened": len(flat), "output_file": str(args.output)}

    except Exception as e:
        return {"error": str(e), "error_type": type(e).__name__}

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    setup_arguments(p)
    print(json.dumps(run_task(p.parse_args()), indent=2))
