import os


def setup_arguments(subparser):
  subparser.add_argument("-o", "--output", default="build/bundle.py")

def run_task(args, context):
  plugins_dir = "plugins"
  output_path = args.output
  os.makedirs(os.path.dirname(output_path), exist_ok=True)
  try:
    with open(output_path, "w", newline="\n") as target_file:
      target_file.write("#!/usr/bin/env python3\n")
      plugin_list = sorted(
        [
          item
          for item in os.listdir(plugins_dir)
          if item.endswith(".py") and not item.startswith("_")
        ]
      )
      for filename in plugin_list:
        with open(os.path.join(plugins_dir, filename), "r") as source_file:
          target_file.write(f"# --- {filename} ---\n{source_file.read()}\n")
    return {"status": "success", "path": output_path, "count": len(plugin_list)}
  except Exception as error:
    return {"status": "error", "message": str(error)}
