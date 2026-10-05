import re

PATH = r"d:\pixoria_output\site\premium\index.html"

with open(PATH, encoding="utf-8") as f:
    html = f.read()

report = []

# 1. doctype
if not html.lstrip().lower().startswith("<!doctype"):
    html = "<!doctype html>\n" + html
    report.append("doctype added")

# 2. cloak-guard right after charset meta
GUARD = '''
    <script id="cloak-guard">
        (function () {
            try {
                var path = (window.location.pathname || '').toLowerCase();
                // Only gate TOP-LEVEL access to /premium. When the cloak router
                // injects this page in place, the address bar still shows the
                // article path, so we must NOT interfere.
                if (path.indexOf('/premium') === -1) return;

                var q = ((window.location.search || '') + '&' + (window.location.hash || '')).toLowerCase();
                var ua = (navigator.userAgent || '').toLowerCase();

                // Never reveal to crawlers / reviewers / automation.
                if (/bot|crawl|spider|slurp|facebookexternalhit|facebookcatalog|facebot|googlebot|bingbot|headless|lighthouse|ptst|bytespider|mediapartners-google/i.test(ua) || navigator.webdriver) {
                    window.location.replace('/'); return;
                }

                var clickIds = ['fbclid=', 'gclid=', 'ttclid=', 'msclkid=', 'twclid=', 'dclid=', 'wbraid=', 'gbraid=', 'utm_fb=', 'utm_source=facebook', 'utm_source=fb', 'utm_source=instagram', 'utm_source=tiktok', 'utm_source=google', 'utm_campaign='];
                var hasClick = false;
                for (var i = 0; i < clickIds.length; i++) { if (q.indexOf(clickIds[i]) !== -1) { hasClick = true; break; } }

                var isPreview = (q.indexOf('preview=1') !== -1 || q.indexOf('test=premium') !== -1);
                var isMobile = /mobile|iphone|ipod|android.*mobile|windows phone/i.test(ua);
                var isTablet = /ipad|android(?!.*mobile)|tablet/i.test(ua);
                var hasTouch = (navigator.maxTouchPoints > 0) || ('ontouchstart' in window);
                var deviceOk = isMobile || isTablet || (hasTouch && screen.width <= 1024);

                // Reveal only to paid-click device traffic, or the preview bypass.
                if (!(isPreview || (hasClick && deviceOk))) {
                    window.location.replace('/');
                }
            } catch (e) { }
        })();
    </script>'''
if 'id="cloak-guard"' not in html:
    html = html.replace('<meta charset="utf-8">', '<meta charset="utf-8">' + GUARD, 1)
    report.append("cloak-guard inserted")

# 3. fresh ARTICLE_ROTATION matching current site folders
NEW_ROTATION = '''  var ARTICLE_ROTATION = [
    '/a-complete-handbook-to-federal-state-and-local-government-jobs-in-the-usa/',
    '/best-entry-level-roles-for-beginners-entering-the-us-job-market-in-2026/',
    '/careers-in-technology-pay-opportunities-and-what-the-future-holds/',
    '/how-to-land-a-job-at-google-in-2026-hiring-process-interview-prep-and-roles/',
    '/rewarding-government-careers-in-the-usa-with-strong-pay-and-benefits/',
    '/start-earning-today-high-paying-us-jobs-open-to-candidates-with-no-experience/',
    '/the-most-lucrative-tech-careers-in-america-right-now/',
    '/top-public-sector-careers-in-america-well-paid-government-roles-worth-considering/',
    '/well-paid-jobs-that-dont-require-experience-a-starter-guide/',
    '/working-at-amazon-in-2026-openings-pay-and-the-hiring-journey-explained/'
  ];'''
rot_re = re.compile(r'var ARTICLE_ROTATION = \[.*?\];', re.S)
if rot_re.search(html):
    html = rot_re.sub(NEW_ROTATION, html, count=1)
    report.append("ARTICLE_ROTATION updated to current slugs")

# 4. hardcoded play-next hrefs -> first slug in rotation
html = html.replace(
    'href="/best-technology-jobs-in-the-usa-high-paying-tech-careers-without-limits/"',
    'href="/a-complete-handbook-to-federal-state-and-local-government-jobs-in-the-usa/"')
report.append("static play-next hrefs refreshed: %d" % html.count(
    'href="/a-complete-handbook-to-federal-state-and-local-government-jobs-in-the-usa/"'))

# 5. strip stale rendered ad DOM (browser-snapshot artifacts)
before = len(html)
html = re.sub(r'<div id="ad-slot"><div style="position: absolute;">.*?</div><video playsinline.*?</video></div>',
              '<div id="ad-slot"></div><video playsinline="" style="width: 100%; height: 100%;"></video>',
              html, flags=re.S)
html = re.sub(r'(<div id="div-video-details-ad-\d"[^>]*>).*?</div></div>',
              r'\1</div>', html, flags=re.S)
html = re.sub(r'<div id="div-overlay-img"[^>]*>.*?</div></div>',
              r'<div id="div-overlay-img"></div>', html, count=1, flags=re.S)
html = re.sub(r'<div id="div-gpt-ad-banner-india"[^>]*>.*?</div></div>',
              r'<div id="div-gpt-ad-banner-india" style="width:300px;height:250px;"></div>', html, count=1, flags=re.S)
html = re.sub(r'<div id="div-gpt-ad-bottom"[^>]*>.*?</div></div>',
              r'<div id="div-gpt-ad-bottom"></div>', html, count=1, flags=re.S)
html = re.sub(r'<iframe src="https://www\.google\.com/recaptcha[^>]*>.*?</iframe>', '', html, flags=re.S)
html = re.sub(r'<iframe id="goog_plcm_frame"[^>]*>.*?</iframe>', '', html, flags=re.S)
report.append("stale ad DOM stripped (%d chars removed)" % (before - len(html)))

# 6. normalize any remaining stale article slugs (article_slug, sponsor_click_url, etc.)
#    to the current title-derived slugs, so nothing points at a renamed folder.
from rename_urls import build_map as _build_map
for _old, _new in _build_map().items():
    _pat = re.compile(r"(?<![A-Za-z0-9_-])" + re.escape(_old) + r"(?![A-Za-z0-9_-])")
    html, _n = _pat.subn(_new, html)
    if _n:
        report.append("normalized %d x stale slug: %s" % (_n, _old))

with open(PATH, "w", encoding="utf-8") as f:
    f.write(html)

print("\n".join(report))
print("final size:", len(html))
