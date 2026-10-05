#!/usr/bin/env python3
"""
Make the pixoria clone fully offline.

- Scans every HTML file under site/
- Downloads all asset subresources (css/js/images/fonts/json) into site/_assets/<host>/<path>
- Recursively follows url(...) and @import inside CSS files
- Rewrites all remote asset references to local root-relative paths
- Skips ad / analytics / tracker hosts (not needed offline)

Safe to re-run (idempotent).
"""

import os
import re
import ssl
import sys
import hashlib
import mimetypes
import urllib.request
import urllib.parse as up

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, "site")
ASSETS = os.path.join(SITE, "_assets")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# hosts we deliberately do NOT download (ads / trackers) -> left as-is
SKIP_HOST_SUBSTR = (
    "doubleclick.net", "googletagservices", "google-analytics",
    "analytics", "admgr", "adservice", "rtbid", "prebid", "criteo",
    "taboola", "outbrain", "facebook.net", "connect.facebook",
    "googletagmanager", "amazon-adsystem", "adnxs", "rubiconproject",
    "pubmatic", "openx", "casalemedia", "didn", "sovrn", "indexwx",
)

ASSET_EXT = (
    ".css", ".js", ".mjs",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".avif", ".bmp",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".json",
)

URL_RE = re.compile(r'https?:\/\/[^\s"\'<>()\\]+', re.IGNORECASE)

_ctx = ssl.create_default_context()
_ctx.check_hostname = False
_ctx.verify_mode = ssl.CERT_NONE

# url -> local root-relative path (e.g. /_assets/host/a/b.css) or None if skipped/failed
MAP = {}
DOWNLOADED = set()
FAILED = set()


def is_likely_asset(url):
    p = up.urlparse(url)
    host = p.netloc.lower()
    if any(s in host for s in SKIP_HOST_SUBSTR):
        return False
    path = p.path.lower()
    if path.endswith(ASSET_EXT):
        return True
    if "/assets/" in path or "/wp-content/" in path or "/wp-includes/" in path:
        # strip query, check base ext
        base = os.path.basename(path)
        if "." in base and base.rsplit(".", 1)[1] in (
            "css js mjs png jpg jpeg gif webp svg ico avif bmp woff woff2 ttf otf eot json".split()
        ):
            return True
    return False


def local_path_for(url):
    p = up.urlparse(url)
    host = p.netloc
    path = p.path
    if not path or path.endswith("/"):
        path = path + "index"
    ext = os.path.splitext(path)[1].lower()
    if ext not in ASSET_EXT:
        ext = ""
    key = hashlib.md5(url.encode("utf-8")).hexdigest()[:16]
    # mirror host/path but flatten into a unique filename to avoid collisions
    rel = host + path
    rel = re.sub(r"[^a-zA-Z0-9._/-]", "_", rel)
    fname = os.path.basename(rel.rstrip("/")) or "asset"
    if len(fname) > 80:
        fname = fname[:80]
    subdir = os.path.dirname(rel) or "."
    store_dir = os.path.join(ASSETS, subdir)
    os.makedirs(store_dir, exist_ok=True)
    out = os.path.join(store_dir, key + "_" + fname + ext)
    root_rel = "/" + os.path.relpath(out, SITE).replace(os.sep, "/")
    return out, root_rel


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=45, context=_ctx) as r:
        data = r.read()
        ct = r.headers.get("Content-Type", "")
    return data, ct


def process_css_bytes(data, css_url):
    """Rewrite url(...) and @import inside a CSS file; download nested assets."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data, 0
    count = 0

    def repl(m):
        nonlocal count
        inner = m.group(1).strip().strip('"\'')
        if inner.startswith("data:") or inner == "":
            return m.group(0)
        absu = up.urljoin(css_url, inner)
        if not absu.startswith("http"):
            return m.group(0)
        if not is_likely_asset(absu):
            # still download css-referenced things (fonts etc.) even if generic
            if any(s in up.urlparse(absu).netloc.lower() for s in SKIP_HOST_SUBSTR):
                return m.group(0)
        localp = ensure(absu)
        if localp:
            count += 1
            return m.group(0).replace(m.group(1), localp)
        return m.group(0)

    def repl_imp(m):
        nonlocal count
        inner = m.group(1).strip()
        if inner.startswith("data:"):
            return m.group(0)
        absu = up.urljoin(css_url, inner)
        localp = ensure(absu)
        if localp:
            count += 1
            return m.group(0).replace(m.group(1), localp)
        return m.group(0)

    # url( ... )
    text2 = re.sub(r'url\(\s*([^\s)]+?)\s*\)', repl, text)
    # @import "url" or @import 'url'
    text2 = re.sub(r'@import\s+["\']([^"\']+)["\']', repl_imp, text2)

    return text2.encode("utf-8"), count


def ensure(url):
    """Download url (and nested css assets) and return its local root-relative path."""
    if url in MAP:
        return MAP[url]
    if url in FAILED:
        return None
    if not url.startswith("http"):
        return None
    if any(s in up.urlparse(url).netloc.lower() for s in SKIP_HOST_SUBSTR):
        MAP[url] = None
        FAILED.add(url)
        return None
    out, root_rel = local_path_for(url)
    if url in DOWNLOADED and os.path.exists(out):
        MAP[url] = root_rel
        return root_rel
    try:
        data, ct = fetch(url)
    except Exception as e:
        print("  FAIL", url, "->", repr(e)[:120])
        MAP[url] = None
        FAILED.add(url)
        return None
    DOWNLOADED.add(url)
    low = url.lower().split("?")[0]
    looks_css = low.endswith(".css") or ("text/css" in ct.lower())
    if looks_css:
        data, _ = process_css_bytes(data, url)
    with open(out, "wb") as f:
        f.write(data)
    MAP[url] = root_rel
    return root_rel


def iter_html_files():
    for dp, _, fns in os.walk(SITE):
        if os.path.abspath(dp).startswith(os.path.abspath(ASSETS)):
            continue
        for fn in fns:
            if fn.lower().endswith(".html"):
                yield os.path.join(dp, fn)


def main():
    os.makedirs(ASSETS, exist_ok=True)

    # 1st pass: collect all asset URLs found in HTML
    html_files = list(iter_html_files())
    all_urls = set()
    for hf in html_files:
        with open(hf, "r", encoding="utf-8", errors="strict") as f:
            txt = f.read()
        for m in URL_RE.finditer(txt):
            u = m.group(0).rstrip(".,;")
            if is_likely_asset(u):
                all_urls.add(u)

    print("HTML files:", len(html_files))
    print("Distinct asset URLs referenced in HTML:", len(all_urls))

    # download (this also recursively pulls nested css assets)
    for u in sorted(all_urls):
        ensure(u)

    # 2nd pass: rewrite HTML references
    replaced = 0
    for hf in html_files:
        with open(hf, "r", encoding="utf-8") as f:
            txt = f.read()
        orig = txt
        # longest URLs first to avoid partial-substring collisions
        for u in sorted(all_urls, key=len, reverse=True):
            lp = MAP.get(u)
            if lp:
                if u in txt:
                    txt = txt.replace(u, lp)
        if txt != orig:
            with open(hf, "w", encoding="utf-8") as f:
                f.write(txt)
            replaced += 1

    ok = sum(1 for v in MAP.values() if v)
    print("Assets downloaded:", ok)
    print("Assets failed/skipped:", len(FAILED))
    print("HTML files rewritten:", replaced)
    print("Asset folder:", os.path.relpath(ASSETS, ROOT))


if __name__ == "__main__":
    main()
