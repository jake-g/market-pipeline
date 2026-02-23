#!/usr/bin/env python3
"""Run a lightweight local server to automatically serve market-pipeline dashboard."""

import argparse
import json
import logging
import os
import socketserver
import webbrowser
from http.server import SimpleHTTPRequestHandler

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
EXCLUDE_DIRS = {
    '.git', 'venv', '__pycache__', 'node_modules', '.vscode', 'logs', '.cache',
    'old', 'LSTM_AI_Stock_Predictor-main', 'alpha_vantage_api'
}
INCLUDE_EXTS = {'.tsv', '.csv', '.md', '.txt', '.json'}
EXCLUDE_FILES = {'requirements.txt', 'TODO.md', 'index.json'}


def build_tree(root_dir, path=""):
  """Recursively builds a tree of allowed files and directories."""
  items = []
  try:
    entries = os.listdir(os.path.join(root_dir, path))
  except PermissionError:
    return items

  for entry in entries:
    if entry.startswith('.') or entry in EXCLUDE_FILES:
      continue

    full_disk_path = os.path.join(root_dir, path, entry)
    rel_path = os.path.join(path, entry).replace('\\', '/')

    if os.path.isdir(full_disk_path):
      if entry in EXCLUDE_DIRS:
        continue
      children = build_tree(root_dir, rel_path)
      if children:  # Only add folders that contain valid files
        items.append({
            "type": "folder",
            "name": entry,
            "path": rel_path,
            "children": children
        })
    else:
      _, ext = os.path.splitext(entry)
      if ext.lower() in INCLUDE_EXTS:
        stat = os.stat(full_disk_path)

        # Calculate lines
        lines = 0
        try:
          with open(full_disk_path, 'r', encoding='utf-8') as f:
            lines = sum(1 for _ in f)
        except Exception:
          pass # Fallback to 0 if encoding fails

        items.append({
            "type": "file",
            "name": entry,
            "path": rel_path,
            "size": stat.st_size,
            "lines": lines,
            "lastModified": int(stat.st_mtime * 1000)
        })

  # Sort: Important files at top (for root only), then folders, then alphabetically
  def sort_key(item):
    is_folder = 0 if item['type'] == 'folder' else 1
    name = item['name'].lower()
    top_tier = 0 if name in ['readme.md', 'changelog.md', 'todo.md'
                            ] and path == "" else 1
    return (top_tier, is_folder, name)

  items.sort(key=sort_key)
  return items


class DashboardHandler(SimpleHTTPRequestHandler):
  """Custom handler to serve /index.json endpoint dynamically and static files."""

  def __init__(self, *args, **kwargs):
    self.path = ""
    super().__init__(*args, **kwargs)

  def do_GET(self):
    # We intercept requests for market_data/index.json to generate it dynamically
    # for local development. But to avoid browser caching issues,
    # there might be query params (e.g. ?t=123)
    if self.path == '/market_data/index.json' or self.path.startswith('/market_data/index.json?'):
      self.send_response(200)
      self.send_header('Content-Type', 'application/json')
      self.end_headers()

      tree = build_tree(ROOT_DIR)
      response_json = json.dumps(tree, separators=(',', ':'))
      self.wfile.write(response_json.encode('utf-8'))
    elif self.path == '/' or self.path.startswith('/?'):
      self.path = '/index.html'
      super().do_GET()
    else:
      super().do_GET()


def main():
  parser = argparse.ArgumentParser(
      description="Run the minimalist Market Pipeline Dashboard")
  parser.add_argument('--port',
                      type=int,
                      default=8008,
                      help='Port to run the server on')
  parser.add_argument('--build',
                      action='store_true',
                      help='Generate static index.json and exit')
  args = parser.parse_args()

  # Change to root dir so SimpleHTTPRequestHandler serves files correctly from here
  os.chdir(ROOT_DIR)

  if args.build:
    output_path = os.path.join(ROOT_DIR, 'market_data', 'index.json')
    logger.info("Building static file tree to %s", output_path)
    tree = build_tree(ROOT_DIR)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
      # We indent with 2 spaces for readability and smaller git diffs,
      # while filesize remains small enough (~200kb).
      json.dump(tree, f, indent=2)
    logger.info("Successfully generated index.json")
    return

  class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

  try:
    with ReusableTCPServer(("", args.port), DashboardHandler) as httpd:
      url = f"http://localhost:{args.port}"
      logger.info("Dashboard serving at %s", url)
      logger.info("Opening browser...")
      webbrowser.open_new(url)
      logger.info("Press Ctrl+C to stop.")
      httpd.serve_forever()
  except KeyboardInterrupt:
    logger.info("\nShutting down dashboard server.")
  except Exception as e:
    logger.error("Failed to start server: %s", e)


if __name__ == "__main__":
  main()
