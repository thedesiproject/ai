import os
import json


def setup_arguments(parser):
  parser.add_argument("-s", "--src", default=".", help="Source directory")
  parser.add_argument("-t", "--target", default="master-schema.json")
  parser.add_argument("-p", "--pattern", default="-schema.json")


def run_task(args, config):
  manifest = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {},
    "$defs": {},
  }
  try:
    files = sorted(
      f for f in os.listdir(args.src) if f.endswith(args.pattern) and f != args.target
    )
    for f in files:
      key = f.replace(args.pattern, "")
      with open(os.path.join(args.src, f), "r") as s:
        manifest["$defs"][key] = json.load(s)
      manifest["properties"][key] = {"$ref": f"#/$defs/{key}"}
    with open(args.target, "w") as out:
      json.dump(manifest, out, indent=2)
    return {"status": "success", "injected": list(manifest["$defs"].keys())}
  except Exception as e:
    return {"status": "error", "trace": str(e)}
