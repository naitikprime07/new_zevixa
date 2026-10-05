import os
import re

SITE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site")
TAG = '<script async src="https://securepubads.g.doubleclick.net/tag/js/gpt.js" crossorigin="anonymous"></script>'
REPL = '<!-- ad tag removed for offline clone -->'
# match any <script ... src="...doubleclick.../gpt.js" ...></script> regardless of attribute order
GPT_RE = re.compile(r'<script[^>]*src="[^"]*doubleclick\.net/tag/js/gpt\.js"[^>]*>\s*</script>', re.IGNORECASE)

changed = 0
for dp, _, fns in os.walk(SITE):
    if os.path.abspath(dp).startswith(os.path.abspath(os.path.join(SITE, "_assets"))):
        continue
    for fn in fns:
        if fn.lower().endswith(".html"):
            p = os.path.join(dp, fn)
            with open(p, encoding="utf-8") as f:
                t = f.read()
            new = t
            if TAG in new:
                new = new.replace(TAG, REPL)
            new = GPT_RE.sub(REPL, new)
            if new != t:
                with open(p, "w", encoding="utf-8") as f:
                    f.write(new)
                changed += 1
print("files changed:", changed)
