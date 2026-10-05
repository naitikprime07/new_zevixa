#!/usr/bin/env python3
"""
Switch cloaking to UA-only routing (no URL parameter required).

- cloak-edge-router (index + article pages): drop the `clickIds`/`hasClick`
  gate so premium is shown to any Meta in-app browser (or the preview bypass),
  while bots are still blocked.
- cloak-guard (premium page): reveal to Meta in-app browser or preview,
  instead of requiring a paid-click param + device check.

Idempotent: only rewrites files that still contain the old `hasClick` logic.
"""

import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, "site")
ASSETS = os.path.join(SITE, "_assets")

# Router: remove the whole block from `var clickIds = [` through `if (!hasClick) return;`
ROUTER_RE = re.compile(
    r'[ \t]*var clickIds = \[.*?if \(!hasClick\) return;[ \t]*\n',
    re.DOTALL,
)

# Premium guard: replace clickIds/hasClick/device block + gate with an isMetaApp check
PREMIUM_RE = re.compile(
    r'var clickIds = \[.*?if \(!\(isPreview \|\| \(hasClick && deviceOk\)\)\) \{',
    re.DOTALL,
)
PREMIUM_NEW = (
    "var isPreview = (q.indexOf('preview=1') !== -1 || q.indexOf('test=premium') !== -1);\n"
    "                // Reveal to Meta in-app browsers (FB/IG/Messenger) or the preview bypass.\n"
    "                var isMetaApp = /fb_iab|fban\\/|fbav\\/|facebookbrowser|instagram/i.test(ua);\n"
    "                if (!(isPreview || isMetaApp)) {"
)


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

        if "if (!hasClick) return;" in t:
            t = ROUTER_RE.sub("", t)
        if "hasClick && deviceOk" in t:
            t = PREMIUM_RE.sub(PREMIUM_NEW, t, count=1)

        if t != orig:
            with open(path, "w", encoding="utf-8") as f:
                f.write(t)
            changed.append(os.path.relpath(path, ROOT))

    print("Switched to UA-only cloaking in %d file(s):" % len(changed))
    for rel in changed:
        print("  -", rel)


if __name__ == "__main__":
    main()
