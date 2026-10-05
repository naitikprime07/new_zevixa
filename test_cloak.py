import re
import urllib.request

BASE = "http://localhost:3000/"
IOS = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
       "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
PC = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def get(url, ua):
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status, r.read().decode("utf-8", "ignore")


def title(html):
    ms = re.findall(r"<title>(.*?)</title>", html, re.S | re.I)
    return ms[-1].strip() if ms else "(no title)"


for label, url, ua in [
    ("1. NORMAL user (no ad params)", BASE, PC),
    ("2. ORGANIC desktop + utm_campaign", BASE + "?utm_campaign=x", PC),
    ("3. AD CLICK mobile (fbclid)", BASE + "?fbclid=IwAR1abc", IOS),
    ("4. AD CLICK mobile (gclid)", BASE + "?gclid=C_test", IOS),
    ("5. PREVIEW backdoor desktop", BASE + "?preview=1", PC),
    ("6. PREMIUM page directly", BASE + "premium/", PC),
    ("7. ARTICLE ad-click mobile",
     BASE + "top-government-jobs-in-the-usa-high-paying-public-sector-careers/?fbclid=1", IOS),
]:
    st, html = get(url, ua)
    router = 'id="cloak-edge-router"' in html
    target = re.search(r"fetch\('([^']+)'", html)
    print(f"{label}\n   url={url}\n   status={st} title={title(html)[:70]!r}")
    print(f"   router_present={router} premium_target={target.group(1) if target else '-'}\n")
