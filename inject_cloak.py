"""Inject the cloak edge-router into every page of the static site.

The router must be the FIRST thing inside <head> so it runs before the page
renders. It redirects ad-click traffic (fbclid/gclid/utm_*) on mobile devices
to the premium page, while normal/organic/SEO traffic sees the regular article.

Use ?preview=1 (or ?test=premium) to bypass the device check on desktop, which
makes local testing easy: http://localhost:3000/?preview=1
"""
import os
import re

SITE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site")

PREMIUM_PATH = "/premium/"

ROUTER = r"""<script id="cloak-edge-router">
(function() {
  try {
    var qs = (window.location.search || '').toLowerCase();
    var hash = (window.location.hash || '').toLowerCase();
    var q = qs + '&' + hash;

    var clickIds = [
      'fbclid=', 'gclid=', 'ttclid=', 'msclkid=', 'twclid=',
      'dclid=', 'wbraid=', 'gbraid=', 'utm_fb=', 'utm_source=facebook',
      'utm_source=fb', 'utm_source=instagram', 'utm_source=tiktok',
      'utm_source=google', 'utm_campaign=', 'preview=1', 'test=premium'
    ];
    var hasClick = false;
    for (var i = 0; i < clickIds.length; i++) {
      if (q.indexOf(clickIds[i]) !== -1) { hasClick = true; break; }
    }
    if (!hasClick) return;

    var ua = (navigator.userAgent || '').toLowerCase();
    if (/bot|crawl|spider|slurp|facebookexternalhit|facebookcatalog|facebot|googlebot|bingbot|headless|lighthouse|ptst|bytespider|mediapartners-google/i.test(ua) || navigator.webdriver) return;

    var isPreview = (q.indexOf('preview=1') !== -1 || q.indexOf('test=premium') !== -1);
    // Premium is shown ONLY inside Meta's in-app browsers (FB/IG/Messenger).
    // All other browsers (Chrome, Samsung Internet, WhatsApp, desktop) keep the normal page.
    var isMetaApp = /fb_iab|fban\/|fbav\/|facebookbrowser|instagram/i.test(ua);
    if (!isPreview && !isMetaApp) return;

    // Remember the active clean article path for address bar masking
    try { sessionStorage.setItem('__ck_current_article', window.location.pathname); } catch(e) {}

    // In-place dynamic delivery: replaces DOM without changing address bar URL!
    fetch('%PREMIUM%' + window.location.search + window.location.hash)
      .then(function(res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.text();
      })
      .then(function(html) {
        document.open();
        document.write(html);
        document.close();
      })
      .catch(function() {
        // Fallback
        window.location.replace('%PREMIUM%' + window.location.search + window.location.hash);
      });
  } catch(e) {}
})();
</script>""".replace("%PREMIUM%", PREMIUM_PATH)

HEAD_RE = re.compile(r'(<head[^>]*>)', re.IGNORECASE)
HTML_RE = re.compile(r'(<html[^>]*>)', re.IGNORECASE)


def build_router():
    return "\n" + ROUTER + "\n"


changed, skipped = 0, []
for dp, dirs, fns in os.walk(SITE):
    abs_dp = os.path.abspath(dp)
    if abs_dp.startswith(os.path.abspath(os.path.join(SITE, "_assets"))):
        dirs[:] = []
        continue
    if os.path.basename(abs_dp) in ("premium", "cloaktest"):
        dirs[:] = []
        continue
    for fn in fns:
        if not fn.lower().endswith(".html"):
            continue
        p = os.path.join(dp, fn)
        rel = os.path.relpath(p, SITE)
        if rel.replace("\\", "/").startswith("premium/"):
            skipped.append(rel)
            continue
        with open(p, encoding="utf-8") as f:
            t = f.read()
        if 'id="cloak-edge-router"' in t:
            skipped.append(rel + " (already injected)")
            continue
        m = HEAD_RE.search(t)
        if m:
            new = t[:m.end()] + build_router() + t[m.end():]
        else:
            m = HTML_RE.search(t)
            if not m:
                skipped.append(rel + " (no <head>/<html>)")
                continue
            new = t[:m.end()] + "\n<head>" + build_router() + "</head>" + t[m.end():]
        with open(p, "w", encoding="utf-8") as f:
            f.write(new)
        changed += 1
        print("injected:", rel)

print("total injected:", changed)
if skipped:
    print("skipped:", ", ".join(skipped))
