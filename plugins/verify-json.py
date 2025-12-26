#!/usr/bin/env python3

import json
import argparse
import sys
import re
from pathlib import Path
from jsonschema import validate, ValidationError, SchemaError

def locate_json_files(target_paths):
    json_list = []
    for raw_path in target_paths:
        p = Path(raw_path)
        if p.is_file() and p.suffix.lower() == '.json':
            json_list.append(p)
        elif p.is_dir():
            json_list.extend(p.rglob('*.json'))
    return sorted(set(json_list))

def perform_repair(content):
    changes = []
    if content.startswith('\ufeff'):
        content = content.lstrip('\ufeff')
        changes.append("bom")
    sanitized = re.sub(r'//.*?\n|/\*.*?\*/', '', content, flags=re.DOTALL)
    if sanitized != content:
        content = sanitized
        changes.append("comments")
    content, count = re.subn(r',(\s*[}\]])', r'\1', content)
    if count > 0: changes.append("trailing-commas")
    content, count = re.subn(r"'([^'\"\\]*)'", r'"\1"', content)
    if count > 0: changes.append("quotes")
    content, count = re.subn(r'([}\]"\d])\s*\n(\s*["{[\d])', r'\1,\n\2', content)
    if count > 0: changes.append("delimiters")
    return content, changes

def audit_file(file_path, schema, auto_fix):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw = f.read()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as err:
            if auto_fix:
                fixed, log = perform_repair(raw)
                try:
                    data = json.loads(fixed)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(fixed)
                    return "FIXED", f"REPAIRED: {', '.join(log)}"
                except json.JSONDecodeError:
                    return "FAIL", f"SYNTAX: L{err.lineno}"
            return "FAIL", f"SYNTAX: L{err.lineno}"
        if schema:
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, dict):
                        v.setdefault('key', k)
                    validate(instance=v, schema=schema)
            else:
                validate(instance=data, schema=schema)
        return "PASS", ""
    except ValidationError as e:
        return "FAIL", f"SCHEMA: {e.message}"
    except Exception as e:
        return "FAIL", f"SYSTEM: {str(e)}"

def setup_arguments(subparser):
    subparser.add_argument('inputs', nargs='+')
    subparser.add_argument('-s', '--schema', default=None)
    subparser.add_argument('-a', '--auto-fix', action='store_true')

def run_task(args, context=None):
    schema_data = None
    if args.schema:
        try:
            with open(args.schema, 'r', encoding='utf-8') as f:
                schema_data = json.load(f)
        except Exception as e:
            return {"error": f"SCHEMA_ERR: {e}", "stats": {}}
    
    files = locate_json_files(args.inputs)
    if args.schema:
        s_abs = Path(args.schema).resolve()
        files = [f for f in files if f.resolve() != s_abs]
    
    if not files:
        return {"error": "NO_TARGETS", "stats": {}}
    
    stats = {'PASS': 0, 'FIXED': 0, 'FAIL': 0}
    results = []
    for f in files:
        res, msg = audit_file(f, schema_data, args.auto_fix)
        stats[res] += 1
        sym = {"PASS": "✓", "FIXED": "⚙", "FAIL": "✗"}[res]
        results.append({"file": f.name, "status": res, "message": msg, "symbol": sym})
    
    return {"stats": stats, "results": results, "error": None}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='validate-json')
    setup_arguments(parser)
    args = parser.parse_args()
    result = run_task(args)
    
    if result.get("error"):
        sys.stderr.write(f"{result['error']}\n")
        sys.exit(1)
    
    for r in result["results"]:
        print(f"{r['symbol']} {r['file']}" + (f" | {r['message']}" if r['message'] else ""))
    
    stats = result["stats"]
    print(f"\nAUDIT: {stats['PASS']}P {stats['FIXED']}F {stats['FAIL']}E")
    sys.exit(0 if stats['FAIL'] == 0 else 1)
