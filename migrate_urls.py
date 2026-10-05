"""Copy-based fallback migration for renamed article folders.

os.rename fails on Windows while a directory/file handle is open (editor, file
watchers, AV). This creates the new folder and copies the page into it (needs
only read access to the old folder), then best-effort removes the old folder.
Idempotent: skips mappings whose new folder already exists.
"""
import os
import shutil
import time

from rename_urls import build_map, ROOT


def migrate():
    mapping = build_map()
    for old, new in mapping.items():
        old_dir = os.path.join(ROOT, old)
        new_dir = os.path.join(ROOT, new)
        if not os.path.isdir(old_dir):
            print("done:", new) if os.path.isdir(new_dir) else print("MISSING:", old)
            continue
        if not os.path.exists(new_dir):
            shutil.copytree(old_dir, new_dir)
            print("COPIED:", old, "->", new)
        # best-effort cleanup of the old folder
        for attempt in range(1, 6):
            try:
                shutil.rmtree(old_dir)
                print("  removed old:", old)
                break
            except PermissionError:
                time.sleep(0.5 * attempt)
        else:
            print("  OLD FOLDER STILL LOCKED (delete later):", old)


if __name__ == "__main__":
    migrate()
