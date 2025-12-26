import argparse
import sys
import os
import importlib.util
import json
def load_plugins(d="plugins"):
    plugins = {}
    if os.path.exists(d):
        for f in sorted([f for f in os.listdir(d) if f.endswith(".py") and not f.startswith("_")]):
            try:
                name = f[:-3].replace('-', '_')
                path = os.path.join(d, f)
                spec = importlib.util.spec_from_file_location(name, path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if all(hasattr(mod, a) for a in ["setup_arguments", "run_task"]):
                    plugins[name] = mod
            except Exception as e:
                print(f"Err:{f}|{e}", file=sys.stderr)
    return plugins
def main():
    plugins = load_plugins()
    if not plugins:
        print("ERROR: No plugins loaded", file=sys.stderr)
        sys.exit(1)
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--silent", action="store_true")
    parser.add_argument("cmd", choices=[k.replace('_', '-') for k in plugins.keys()])
    parser.add_argument("subargs", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    plugin = plugins[args.cmd.replace('-', '_')]
    plugin_parser = argparse.ArgumentParser()
    plugin.setup_arguments(plugin_parser)
    plugin_args = plugin_parser.parse_args(args.subargs)
    try:
        result = plugin.run_task(plugin_args, {})
        if isinstance(result, dict):
            result.update({"plugin": args.cmd, "status": "success"})
            if not args.silent:
                print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        err_dict = {"status": "error", "err": str(e), "plugin": args.cmd}
        print(json.dumps(err_dict, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
if __name__ == "__main__":
    main()