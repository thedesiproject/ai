import json
from pathlib import Path

def setup_arguments(subparser):
    subparser.add_argument("input")
    subparser.add_argument("-o", "--output-dir", required=True)
    subparser.add_argument("--instruction", default="Load master.json. Execute s0-ingest. Acknowledge only.")

def run_task(args, context=None):
    try:
        dist = Path(args.output_dir)
        dist.mkdir(parents=True, exist_ok=True)
        
        with open(args.input, 'r') as f:
            data = json.load(f)
        
        xml_output = dist / "session-init.xml"
        
        with open(xml_output, 'w') as f:
            f.write(f'<data_context info="{args.instruction}">\n')
            f.write(json.dumps(data, separators=(',', ':')))
            f.write("\n</data_context>")
        
        # return {"status": "success", "output": str(xml_output)}
        return {}

    except Exception as e:
        return {"status": "error", "message": str(e)}
