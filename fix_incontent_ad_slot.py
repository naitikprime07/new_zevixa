#!/usr/bin/env python3
"""
Restore the in-content GPT ad slot `div-gpt-ad-1769536797735-0` on article
pages where LiteSpeed's optimizer stripped the inline define/display scripts,
leaving only an orphan empty <div>.

Idempotent: pages that already define the slot (e.g. rewarding-government,
top-public-sector) are skipped, as are pages without the slot at all.
"""

import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, "site")
ASSETS = os.path.join(SITE, "_assets")

SLOT = "div-gpt-ad-1769536797735-0"

DEFINE = (
    "<script>window.googletag = window.googletag || { cmd: [] }; googletag.cmd.push(function () { "
    "googletag.defineSlot('/21775744923/example/banner', "
    "[[320, 480], [300, 250], [336, 280], [300, 100], [300, 75], [300, 50], [250, 250], 'fluid'], "
    "'" + SLOT + "').addService(googletag.pubads()); googletag.pubads().enableSingleRequest(); "
    "googletag.pubads().collapseEmptyDivs(); googletag.enableServices() })</script>"
)
DISPLAY = (
    "<script>googletag.cmd.push(function () { googletag.display('" + SLOT + "') })</script>"
)

# Matches the empty slot div: <div ...id="SLOT"...>  (only whitespace)  </div>
EMPTY_DIV = re.compile(
    r'(<div\b[^>]*id=["\']' + re.escape(SLOT) + r'["\'][^>]*>)(\s*)(</div>)',
    re.IGNORECASE,
)
ALREADY_DEFINED = re.compile(r'defineSlot\([^)]*' + re.escape(SLOT))


def iter_html():
    for dp, _, fns in os.walk(SITE):
        if os.path.abspath(dp).startswith(os.path.abspath(ASSETS)):
            continue
        for fn in fns:
            if fn.lower().endswith(".html"):
                yield os.path.join(dp, fn)


def main():
    fixed = []
    for path in iter_html():
        with open(path, "r", encoding="utf-8") as f:
            t = f.read()
        if SLOT not in t:
            continue
        if ALREADY_DEFINED.search(t):
            continue  # working page, leave as-is

        # Rebuild: keep original opening tag, inject DEFINE before it and
        # DISPLAY inside it.
        new = EMPTY_DIV.sub(
            lambda m: DEFINE + "\n" + m.group(1) + "\n" + DISPLAY + "\n" + m.group(3),
            t,
            count=1,
        )
        if new != t:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new)
            fixed.append(os.path.relpath(path, ROOT))

    print("Restored in-content ad slot on %d file(s):" % len(fixed))
    for rel in fixed:
        print("  -", rel)


if __name__ == "__main__":
    main()
