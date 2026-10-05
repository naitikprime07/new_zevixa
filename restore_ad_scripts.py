#!/usr/bin/env python3
"""
Restore the Google ad loader scripts that `strip_ads.py` removed.

For every HTML file under site/ (excluding _assets):
  1. Revert `<!-- ad tag removed for offline clone -->` back to the real
     Google Publisher Tag loader (`gpt.js`) -- this is an exact undo of strip_ads.py.
  2. If a page uses `googletag` but still has no `gpt.js` loader anywhere,
     inject the loader into <head>.
  3. If a page uses `google.ima.*` (outstream/preroll) but has no `ima3.js`,
     inject the IMA SDK right after the gpt.js loader.

Idempotent: premium/ (which already loads both) is left untouched.
"""

import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, "site")
ASSETS = os.path.join(SITE, "_assets")

GPT = '<script async src="https://securepubads.g.doubleclick.net/tag/js/gpt.js" crossorigin="anonymous"></script>'
IMA = '<script src="https://imasdk.googleapis.com/js/sdkloader/ima3.js"></script>'
REPL = "<!-- ad tag removed for offline clone -->"


def iter_html():
    for dp, _, fns in os.walk(SITE):
        if os.path.abspath(dp).startswith(os.path.abspath(ASSETS)):
            continue
        for fn in fns:
            if fn.lower().endswith(".html"):
                yield os.path.join(dp, fn)


def main():
    changed = []
    for path in iter_html():
        with open(path, "r", encoding="utf-8") as f:
            t = f.read()
        orig = t

        uses_googletag = re.search(r"window\.googletag|googletag\.cmd", t) is not None
        uses_ima = re.search(r"google\.ima\.", t) is not None

        # 1) undo strip_ads.py
        if REPL in t:
            t = t.replace(REPL, GPT)

        # 2) ensure a gpt.js loader exists when the page uses GPT
        has_gpt = "doubleclick.net/tag/js/gpt.js" in t
        if uses_googletag and not has_gpt:
            if "</head>" in t:
                t = t.replace("</head>", "  " + GPT + "\n</head>", 1)
            else:
                t = GPT + "\n" + t
            has_gpt = True

        # 3) ensure IMA SDK exists when the page uses google.ima
        has_ima = "sdkloader/ima3.js" in t
        if uses_ima and not has_ima:
            if GPT in t:
                t = t.replace(GPT, GPT + "\n  " + IMA, 1)
            elif "</head>" in t:
                t = t.replace("</head>", "  " + IMA + "\n</head>", 1)
            else:
                t = IMA + "\n" + t

        if t != orig:
            with open(path, "w", encoding="utf-8") as f:
                f.write(t)
            rel = os.path.relpath(path, ROOT)
            tags = []
            if uses_googletag:
                tags.append("gpt.js")
            if uses_ima:
                tags.append("ima3.js")
            changed.append((rel, ", ".join(tags) or "comment revert"))

    print("Restored ad loaders in %d file(s):" % len(changed))
    for rel, what in changed:
        print("  -", rel, "->", what)


if __name__ == "__main__":
    main()
