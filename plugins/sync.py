import os
import json
import time
from playwright.sync_api import sync_playwright

GEMINI_URL_TEMPLATE = "https://gemini.google.com/app/{}"
MESSAGE_SELECTOR = ".message-content"
DEFAULT_TIMEOUT = 10000
WAIT_BUFFER_SECONDS = 2


def setup_arguments(parser):
  parser.add_argument("--thread-id", required=True)
  parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)


def run_task(args, config):
  vault_path = config["vault_directory"]
  debugging_port = config["browser_config"]["debugging_port"]
  thread_id = args.thread_id
  timeout = args.timeout

  os.makedirs(vault_path, exist_ok=True)

  try:
    with sync_playwright() as playwright:
      browser = playwright.chromium.connect_over_cdp(
        f"http://localhost:{debugging_port}"
      )
      context = browser.contexts[0] if browser.contexts else browser.new_context()
      page = context.new_page()

      try:
        page.goto(
          GEMINI_URL_TEMPLATE.format(thread_id),
          wait_until="domcontentloaded",
          timeout=timeout,
        )
        page.wait_for_selector(MESSAGE_SELECTOR, timeout=timeout)
        time.sleep(WAIT_BUFFER_SECONDS)

        message_elements = page.query_selector_all(MESSAGE_SELECTOR)
        message_texts = [
          element.inner_text() for element in message_elements if element.inner_text()
        ]

        output_file = os.path.join(vault_path, f"{thread_id}.json")
        with open(output_file, "w") as f:
          json.dump({"id": thread_id, "data": message_texts}, f, indent=2)

        print(f"✓ Updated: {output_file} ({len(message_texts)} messages)")

      except Exception as error:
        print(f"Error processing thread {thread_id}: {error}")
      finally:
        page.close()

  except Exception as error:
    print(f"Error connecting to browser on port {debugging_port}: {error}")
