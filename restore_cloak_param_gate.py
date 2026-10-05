#!/usr/bin/env python3
"""
Restore the AD-CLICK PARAM gate to cloaking (undo UA-only).

Desired behavior (matches pixoria.fyi):
  - Direct open (no tracking param)        -> NORMAL page (even in Meta browser)
  - Arrive via ad click (has fbclid/etc.)  -> PREMIUM page (in Meta in-app browser)
  - ?preview=1 / ?test=premium             -> PREMIUM (desktop test backdoor)

- cloak-edge-router (index + article pages): re-insert `clickIds`/`hasClick`
  and `if (!hasClick) return;` right after the `q` line.
- cloak-guard (premium page): require the ad-click param again,
  revealing only on `isPreview || (hasClick && isMetaApp)`.

Idempotent: skips files already carrying the param gate.
"""

import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, "site")
ASSETS = os.path.join(SITE, "_assets")

ROUTER_CLICKS = (
    "var clickIds = ['fbclid=', 'gclid=', 'ttclid=', 'msclkid=', 'twclid=', "
    "'dclid=', 'wbraid=', 'gbraid=', 'utm_fb=', 'utm_source=facebook', "
    "'utm_source=fb', 'utm_source=instagram', 'utm_source=tiktok', "
    "'utm_source=google', 'utm_campaign=', 'preview=1', 'test=premium'];\n"
    "var hasClick = false;\n"
    "for (var i = 0; i < clickIds.length; i++) { if (q.indexOf(clickIds[i]) !== -1) { hasClick = true; break; } }\n"
    "if (!hasClick) return;"
)

PREMIUM_CLICKS = (
    "var clickIds = ['fbclid=', 'gclid=', 'ttclid=', 'msclkid=', 'twclid=', "
    "'dclid=', 'wbraid=', 'gbraid=', 'utm_fb=', 'utm_source=facebook', "
    "'utm_source=fb', 'utm_source=instagram', 'utm_source=tiktok', "
    "'utm_source=google', 'utm_campaign='];\n"
    "var hasClick = false;\n"
    "for (var i = 0; i < clickIds.length; i++) { if (q.indexOf(clickIds[i]) !== -1) { hasClick = true; break; } }"
)

# q line in router: `<indent>var q = qs + '&' + hash;` + newline + optional blank lines
Q_RE = re.compile(r"([ \t]*)(var q = qs \+ '&' \+ hash;)[ \t]*\n((?:[ \t]*\n)*)")

# premium UA-only gate we now re-gate
P_RE = re.compile(r"([ \t]*)if \(!\(isPreview \|\| isMetaApp\)\) \{")


def indented(indent, block):
    return block.replace("\n", "\n" + indent)


def restore_router(t):
    if 'id="cloak-edge-router"' not in t:
        return t, False
    if "var clickIds" in t:
        return t, False  # already param-gated
    m = Q_RE.search(t)
    if not m:
        return t, False
    indent, qline = m.group(1), m.group(2)
    repl = indent + qline + "\n\n" + indented(indent, ROUTER_CLICKS) + "\n\n"
    return t[:m.start()] + repl + t[m.end():], True


def restore_premium(t):
    if 'id="cloak-guard"' not in t:
        return t, False
    if "hasClick && isMetaApp" in t or "hasClick && deviceOk" in t:
        return t, False  # already param-gated
    m = P_RE.search(t)
    if not m:
        return t, False
    indent = m.group(1)
    repl = indent + indented(indent, PREMIUM_CLICKS) + "\n" + \
        indent + "if (!(isPreview || (hasClick && isMetaApp))) {"
    return t[:m.start()] + repl + t[m.end():], True


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
        t, r1 = restore_router(t)
        t, r2 = restore_premium(t)
        if t != orig:
            with open(path, "w", encoding="utf-8") as f:
                f.write(t)
            changed.append((os.path.relpath(path, ROOT), "premium-guard" if r2 else "router"))
    print("Restored param gate in %d file(s):" % len(changed))
    for rel, kind in changed:
        print("  - [%s] %s" % (kind, rel))


if __name__ == "__main__":
    main()
