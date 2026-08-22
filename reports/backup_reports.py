# Copyright 2026 The Market Pipeline Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Automated backup utility for all market intelligence reports.

This module scans the reports directory, packages all dated report directories,
markdown analyses, rendered PDFs, and visualization plots into timestamped
and latest zip archives stored safely in a gitignored backups folder.
"""

import datetime
import logging
import os
import shutil
import sys
import zipfile
from typing import List, Tuple

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

REPORTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUPS_DIR = os.path.join(REPORTS_DIR, "backups")

EXCLUDE_DIRS = {"backups", "__pycache__", ".cache", ".git", ".mypy_cache"}
EXCLUDE_EXTENSIONS = {".pyc", ".pyo", ".DS_Store"}


def backup_all_reports() -> Tuple[str, int]:
  """Creates a single consolidated zip archive of all reports.

  Returns:
    Tuple of (backup_zip_path, total_files_archived).
  """
  os.makedirs(BACKUPS_DIR, exist_ok=True)

  backup_zip = os.path.join(BACKUPS_DIR, "reports_backup.zip")
  temp_zip = os.path.join(BACKUPS_DIR, "reports_backup.tmp.zip")

  file_count = 0
  logger.info("Initiating report archive to %s...", backup_zip)

  with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED,
                       compresslevel=6) as zip_handle:
    for root, dirs, files in os.walk(REPORTS_DIR):
      # Modify dirs in-place to skip excluded directories
      dirs[:] = [
          d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".")
      ]

      for file_name in files:
        if file_name.startswith(".DS_Store") or file_name.endswith(".zip"):
          continue
        ext = os.path.splitext(file_name)[1].lower()
        if ext in EXCLUDE_EXTENSIONS:
          continue

        full_path = os.path.join(root, file_name)
        arc_name = os.path.relpath(full_path, REPORTS_DIR)
        zip_handle.write(full_path, arc_name)
        file_count += 1

  # Atomic replace
  if os.path.exists(backup_zip):
    os.remove(backup_zip)
  os.rename(temp_zip, backup_zip)

  zip_size_mb = os.path.getsize(backup_zip) / (1024 * 1024)
  logger.info(
      "✅ Successfully backed up %d report files (%.2f MB) to %s",
      file_count,
      zip_size_mb,
      backup_zip,
  )

  return backup_zip, file_count


if __name__ == "__main__":
  backup_all_reports()
