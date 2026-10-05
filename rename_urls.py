"""Rename article URLs so each slug matches its (current) title.

Steps:
  1. Derive a new slug from each article's title (from rewrite_content.ARTICLES).
  2. Replace every bounded reference to the old slug with the new one across all
     HTML files under site/ (links, canonical, og:url, JSON-LD, prev/next, related).
  3. Rename the article folders on disk.

Run build_search.py afterwards to refresh the client-side search index.
Operates on site/ only.
"""
import os
import re
import glob

from rewrite_content import ARTICLES, ROOT


def slugify(title):
    s = title.lower().replace("&", " and ")
    s = re.sub(r"['\u2019`.]", "", s)          # drop apostrophes/periods
    s = re.sub(r"[^a-z0-9]+", "-", s)          # everything else -> hyphen
    return s.strip("-")


def build_map():
    mapping = {}
    for old_slug, info in ARTICLES.items():
        new_slug = slugify(info["title"])
        if new_slug == old_slug:
            continue
        mapping[old_slug] = new_slug
    # sanity: no two olds map to same new, and no new collides with an untouched folder
    news = list(mapping.values())
    assert len(news) == len(set(news)), "slug collision detected"
    return mapping


def update_references(mapping):
    patterns = {
        old: re.compile(r"(?<![A-Za-z0-9_-])" + re.escape(old) + r"(?![A-Za-z0-9_-])")
        for old in mapping
    }
    totals = {old: 0 for old in mapping}
    for path in glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True):
        with open(path, encoding="utf-8") as f:
            html = f.read()
        orig = html
        for old, pat in patterns.items():
            html, n = pat.subn(mapping[old], html)
            totals[old] += n
        if html != orig:
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
    return totals


def rename_folders(mapping):
    import time
    for old, new in mapping.items():
        old_dir = os.path.join(ROOT, old)
        new_dir = os.path.join(ROOT, new)
        if not os.path.isdir(old_dir):
            if os.path.isdir(new_dir):
                print("ALREADY RENAMED:", new)
            else:
                print("MISSING folder:", old)
            continue
        if os.path.exists(new_dir):
            print("SKIP (target exists):", new)
            continue
        for attempt in range(1, 8):
            try:
                os.rename(old_dir, new_dir)
                print("RENAMED:", old, "->", new)
                break
            except PermissionError:
                time.sleep(0.6 * attempt)
        else:
            print("FAILED (locked):", old)


def main():
    mapping = build_map()
    print("=== slug map ===")
    for old, new in mapping.items():
        print("  %s\n    -> %s" % (old, new))
    print("\n=== reference replacements ===")
    totals = update_references(mapping)
    for old, n in totals.items():
        print("  %-70s %d" % (old, n))
    print("\n=== folder renames ===")
    rename_folders(mapping)
    print("\nDone. Now run: python build_search.py")


if __name__ == "__main__":
    main()
