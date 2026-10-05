import os
import re

SITE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site")
# remove the whole cloak router script block (id="cloak-edge-router")
CLOAK_RE = re.compile(
    r'\s*<script\s+id="cloak-edge-router">.*?</script>',
    re.IGNORECASE | re.DOTALL,
)

changed = 0
for dp, _, fns in os.walk(SITE):
    if os.path.abspath(dp).startswith(os.path.abspath(os.path.join(SITE, "_assets"))):
        continue
    for fn in fns:
        if fn.lower().endswith(".html"):
            p = os.path.join(dp, fn)
            with open(p, encoding="utf-8") as f:
                t = f.read()
            new = CLOAK_RE.sub("", t)
            if new != t:
                with open(p, "w", encoding="utf-8") as f:
                    f.write(new)
                changed += 1
                print("cleaned:", os.path.relpath(p, SITE))
print("total files cleaned:", changed)
