"""Fix author avatar images so they display offline.

Root cause: the offline clone left the lazy-load placeholder as a broken
src="../data:image..." (a data: URI wrongly given a ../ prefix), and the real
image only lives in data-src. If the theme's lazy-load JS does not run, the
avatar shows as a broken image.

Fix: for every <img> that references litespeed/avatar, set its src directly to
the local avatar file (taken from data-src). Also repair any remaining
src="../data:" corruption across the page.
"""
import glob
import os
import re

ROOT = r"d:\pixoria_output\site"


def local_avatar_from(data_src):
    """Map a data-src URL to an existing local path under site/, or None."""
    if not data_src:
        return None
    if data_src.startswith("data:"):
        return None
    # strip query string
    base = data_src.split("?", 1)[0]
    if base.startswith("/"):
        cand = os.path.join(ROOT, base.lstrip("/").replace("/", os.sep))
    else:
        # external URL like https://host/assets/... -> match on the /assets part
        idx = base.find("/assets/")
        if idx == -1:
            return None
        cand = os.path.join(ROOT, "_assets",
                            base[idx:].lstrip("/").replace("/", os.sep))
        # our saved assets live under _assets/pixoria-dashboard.b-cdn.net/assets...
        alt = os.path.join(ROOT, "_assets", "pixoria-dashboard.b-cdn.net",
                           base[idx:].lstrip("/").replace("/", os.sep))
        if os.path.exists(cand):
            return base
        if os.path.exists(alt):
            return "/_assets/pixoria-dashboard.b-cdn.net" + base[idx:]
        return None
    return base if os.path.exists(cand) else None


def fix_img_tag(tag):
    if "litespeed/avatar" not in tag:
        return tag, False
    ds = re.search(r'data-src="([^"]+)"', tag)
    local = local_avatar_from(ds.group(1)) if ds else None
    if not local:
        return tag, False
    # Replace the real src="..." attribute (NOT the data-src one) with the local path
    new_tag = re.sub(r'(?<![-\w])src="[^"]*"', 'src="%s"' % local, tag, count=1)
    return new_tag, new_tag != tag


def process(path):
    with open(path, encoding="utf-8") as f:
        html = f.read()
    orig = html
    # 1) point avatar <img> src at the real local file
    html = re.sub(r'<img[^>]*>', lambda m: fix_img_tag(m.group(0))[0],
                  html, flags=re.S)
    # 2) repair any remaining broken data: URI placeholders elsewhere (any ../ depth)
    html = re.sub(r'src="(?:\.\./)+data:', 'src="data:', html)
    if html != orig:
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return True
    return False


def main():
    changed = 0
    for p in glob.glob(os.path.join(ROOT, "**", "index.html"), recursive=True):
        if process(p):
            changed += 1
            print("FIXED:", os.path.relpath(p, ROOT))
    print("Total files changed:", changed)


if __name__ == "__main__":
    main()
