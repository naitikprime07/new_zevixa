// Faithful converter: reads every page under ../site and emits a Vite multi-page
// React app. It never rewrites markup/CSS/JS content - it only splits each page
// into verbatim fragments (head, bodyTop, header, main, footer, bodyBottom or a
// whole body) and wires them to React that mounts the exact original DOM and
// re-executes the original scripts. Run with: node tools/generate.mjs
import { readFileSync, writeFileSync, mkdirSync, rmSync, existsSync } from 'node:fs';
import { readdirSync, statSync } from 'node:fs';
import { dirname, join, relative, sep, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(__dirname, '..');
const siteRoot = resolve(projectRoot, '..', 'site');

// ---------- discover pages ----------
function findIndexHtml(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (name === 'node_modules' || name === '_assets' || name === 'assets') continue;
    const st = statSync(p);
    if (st.isDirectory()) {
      out.push(...findIndexHtml(p));
    } else if (name === 'index.html') {
      out.push(p);
    }
  }
  return out;
}

const pages = findIndexHtml(siteRoot);

// slug (filesystem-safe) + url dir + entry html path
function describe(file) {
  const relDir = relative(siteRoot, dirname(file)).split(sep).join('/'); // '', 'category/news', 'author/admin', slug-folder
  const urlDir = relDir === '' ? '' : relDir; // original URL directory (no trailing slash)
  const flatSlug = urlDir === '' ? 'index' : urlDir.replace(/\//g, '__');
  const entryPath = urlDir === '' ? 'index.html' : `${urlDir}/index.html`;
  return { file, urlDir, flatSlug, entryPath };
}

// ---------- parsing ----------
const MC_OPEN = '<div id="main-container">';

// The premium page's hero/background/thumbnail/GIF assets are referenced from
// the remote BunnyCDN (zevixa.b-cdn.net), which blocks hotlinked
// image requests from other origins -> the page renders solid black. Local
// copies of every one of those files ship with the site, so we localize the
// base URL to the self-hosted /assets/ path (public/assets mirrors this layout).
const CDN_BASE = 'https://pixoria-dashboard.b-cdn.net/assets/';
const LOCAL_BASE = '/assets/';
// The offline-mirrored chrome-page assets live under a folder literally named
// after the original BunnyCDN host. That host string is invisible infra (not
// branding), but the owner rebranded Pixoria -> Zevixa and wants the word
// "pixoria" gone from asset URLs too. We rename the local mirror segment
// pixoria-dashboard.b-cdn.net -> zevixa.b-cdn.net at generation time so every
// chrome entry / raw fragment references the new path. The physical folder in
// public/_assets is renamed to match. (Rebrand-safe: only the path segment
// changes; bytes/CSS/JS are identical.)
const MIRROR_BASE = '/_assets/pixoria-dashboard.b-cdn.net/';
const MIRROR_NEW = '/_assets/zevixa.b-cdn.net/';
// The premium loading spinner also points at an external host; a local copy is
// shipped, so point it same-origin too (fully offline).
const REMOTE_LOADING = 'https://media.tenor.com/WX_LDjYUrMsAAAAj/loading.gif';
const LOCAL_LOADING = '/assets/loading/tenor-loading.gif';
// The cloak edge-router replaces the whole document via fetch('/premium/') +
// document.write. We tag that decision with a synchronous flag so the React
// entry (main.jsx) knows NOT to mount on a page that is about to be swapped.
// Without this, React's async body-mutation races the document.write and can
// leave the premium <head> with no #videoOverlay -> solid black.
const CLOAK_FETCH = "fetch('/premium/' + window.location.search + window.location.hash)";
const CLOAK_SWAP_FLAG = "window.__CLOAK_SWAP__ = true; ";

// ---------- live GAM ad-unit remap (network 23378750337 / zevixa_*) ----------
// site/ (the source of truth) still carries Google's DEMO units (/21775744923/
// example + /external). The owner wants them swapped to the live Zevixa units
// ONLY in the generated react-app, leaving site/ untouched. We do it at
// generation time - same place as the Pixoria->Zevixa rebrand - so every
// `node tools/generate.mjs` / dev / build reproduces the live tags exactly.
// The demo string '/example/banner' is shared by many slots, so it is mapped
// per-slot by each defineSlot element id / cfgAds key / variable fallback.
const GAM_DEMO_NET = '/21775744923';
const GAM_LIVE_NET = '/23378750337';
const LIVE_OUTSTREAM_URL =
  'https://pubads.g.doubleclick.net/gampad/ads?iu=' + GAM_LIVE_NET +
  '/zevixa_video_outstream&description_url=http%3A%2F%2Fzevixa.site&tfcd=0&npa=0' +
  '&sz=640x480&gdfp_req=1&unviewed_position_start=1&output=vast&env=vp&impl=s&correlator=';

function remapAds(text) {
  // 1. premium outstream_vast_url: whole value -> the live tag.
  text = text.replace(/"outstream_vast_url":\s*"[^"]*"/g, '"outstream_vast_url": "' + LIVE_OUTSTREAM_URL + '"');

  // 2. per-slot banner inside defineSlot(), keyed by the slot's element id.
  text = text.replace(/googletag\.defineSlot\(([^()]*)\)/g, (m, args) => {
    if (args.indexOf(GAM_DEMO_NET + '/example/banner') === -1) return m;
    const ids = args.match(/['"]([^'"]+)['"]/g) || [];
    const last = (ids[ids.length - 1] || '').replace(/['"]/g, '');
    let unit = null;
    if (last.indexOf('banner-india') !== -1) unit = GAM_LIVE_NET + '/zevixa_floating';
    else if (last.indexOf('ad-bottom') !== -1) unit = GAM_LIVE_NET + '/zevixa_bottom';
    else if (last.indexOf('1769536797735') !== -1) unit = GAM_LIVE_NET + '/zevixa_incontent';
    if (!unit) return m;
    return 'googletag.defineSlot(' + args.split(GAM_DEMO_NET + '/example/banner').join(unit) + ')';
  });

  // 3. premium cfgAds keys -> their dedicated live unit.
  const KEY_UNIT = {
    hero_slot_1: 'zevixa_hero_1', hero_slot_2: 'zevixa_hero_2', hero_slot_3: 'zevixa_hero_3',
    floating_slot: 'zevixa_floating', center_slot: 'zevixa_center', bottom_slot: 'zevixa_bottom',
    interstitial_slot: 'zevixa_interstitial',
  };
  for (const k in KEY_UNIT) {
    text = text.split(k + '": "' + GAM_DEMO_NET + '/example/banner"').join(k + '": "' + GAM_LIVE_NET + '/' + KEY_UNIT[k] + '"');
    text = text.split(k + '": "' + GAM_DEMO_NET + '/example/interstitial"').join(k + '": "' + GAM_LIVE_NET + '/' + KEY_UNIT[k] + '"');
  }

  // 4. premium JS fallback literals (used only if cfgAds is missing).
  const FB = {
    ['cfgAds.center_slot || "' + GAM_DEMO_NET + '/example/banner"']: GAM_LIVE_NET + '/zevixa_center',
    ['cfgAds.hero_slot_1 || cfgAds.floating_slot || "' + GAM_DEMO_NET + '/example/banner"']: GAM_LIVE_NET + '/zevixa_hero_1',
    ['cfgAds.hero_slot_2 || cfgAds.bottom_slot || "' + GAM_DEMO_NET + '/example/banner"']: GAM_LIVE_NET + '/zevixa_hero_2',
    ['cfgAds.hero_slot_3 || cfgAds.center_slot || "' + GAM_DEMO_NET + '/example/banner"']: GAM_LIVE_NET + '/zevixa_hero_3',
    ['cfgAds.floating_slot || "' + GAM_DEMO_NET + '/example/banner"']: GAM_LIVE_NET + '/zevixa_floating',
    ['cfgAds.bottom_slot || "' + GAM_DEMO_NET + '/example/banner"']: GAM_LIVE_NET + '/zevixa_bottom',
  };
  for (const frag in FB) {
    if (text.indexOf(frag) !== -1) {
      text = text.split(frag).join(frag.split('"' + GAM_DEMO_NET + '/example/banner"').join('"' + FB[frag] + '"'));
    }
  }

  // 5. preroll VAST fragment -> live outstream unit (+ live targeting params).
  text = text.split('iu=' + GAM_DEMO_NET + '/external/single_preroll_skippable').join('iu=' + GAM_LIVE_NET + '/zevixa_video_outstream&description_url=http%3A%2F%2Fzevixa.site&tfcd=0&npa=0');

  // 6. interstitial (constant + any remaining fallback) global.
  text = text.split(GAM_DEMO_NET + '/example/interstitial').join(GAM_LIVE_NET + '/zevixa_interstitial');

  // 7. premium outstream fallback iu -> live, drop the sample cust_params.
  text = text.split('iu=' + GAM_DEMO_NET + '/external/single_ad_samples&cust_params=sample_ct%3Dlinear').join('iu=' + GAM_LIVE_NET + '/zevixa_video_outstream&tfcd=0&npa=0');
  text = text.split(GAM_DEMO_NET + '/external/single_ad_samples').join(GAM_LIVE_NET + '/zevixa_video_outstream');

  return text;
}

function parse(rawText) {
  let text = rawText
    .split(CDN_BASE).join(LOCAL_BASE)
    .split(MIRROR_BASE).join(MIRROR_NEW)
    .split(REMOTE_LOADING).join(LOCAL_LOADING)
    .split(CLOAK_FETCH).join(CLOAK_SWAP_FLAG + CLOAK_FETCH);
  // Rebrand the stale source-of-truth (site/ still says "Pixoria") to Zevixa at
  // generation time, so `npm run dev`/`build` (which run this generator) can
  // NEVER revert react-app back to Pixoria. Domain pixoria.fyi -> zevixa.site.
  // Case-sensitive on purpose: capital "Pixoria" = the visible brand word; the
  // lowercase CDN segment "pixoria-dashboard" is handled by MIRROR above and is
  // left untouched. This mirrors exactly how the working react-app was branded.
  text = text.split('pixoria.fyi').join('zevixa.site');
  text = text.split('Pixoria').join('Zevixa');
  // Swap Google's demo GAM units (still present in site/) for the live Zevixa
  // ad units - react-app only; site/ is intentionally left on the demo tags.
  text = remapAds(text);
  // Premium fix #1: remove the hardcoded #dynamic-random-assets-css override
  // that pins .hero to one image and defeats the randomized hero ("stuck hero").
  text = text.replace(/<style id="dynamic-random-assets-css">[\s\S]*?hero_thumb_3\.png[\s\S]*?<\/style>\s*/i, '');
  // Premium fix #2: advance to the next clip + sync the preview thumbnail on
  // each play (mediaIndex was frozen at 0 -> same gif every time).
  text = text.replace(
    /if \(gc\) gc\.style\.display = "none";(\s*)var tc = document\.getElementById\("thumbContainer"\);/,
    'if (gc) gc.style.display = "none";$1mediaIndex = (mediaIndex + 1) % MEDIA_SET.length;$1var thumb = document.querySelector("#thumbContainer .thumbnail");$1if (thumb && MEDIA_SET[mediaIndex]) {$1    thumb.style.setProperty("background", \'url("\' + MEDIA_SET[mediaIndex].thumb + \'") center/cover no-repeat\', "important");$1}$1var tc = document.getElementById("thumbContainer");'
  );
  const htmlOpen = (text.match(/<html\b[^>]*>/i) || ['<html lang="en-US">'])[0];
  const doctype = (text.match(/<!doctype html>/i) || ['<!doctype html>'])[0];

  const headStart = text.indexOf('<head');
  const headOpenEnd = text.indexOf('>', headStart);
  const headClose = text.indexOf('</head>', headOpenEnd);
  const headInner = text.slice(headOpenEnd + 1, headClose);

  const bodyOpenMatch = text.match(/<body\b[^>]*>/i);
  const bodyOpenTag = bodyOpenMatch[0];
  const bodyInnerStart = text.indexOf(bodyOpenTag) + bodyOpenTag.length;
  const bodyClose = text.indexOf('</body>', bodyInnerStart);
  const bodyInner = text.slice(bodyInnerStart, bodyClose);

  return { doctype, htmlOpen, headInner, bodyOpenTag, bodyInner };
}

// Extract chrome + main from a body that contains the WP layout.
function extractChrome(bodyInner) {
  const header = (bodyInner.match(/<header\b[^>]*\bid="header"[\s\S]*?<\/header>/) || [])[0];
  const footer = (bodyInner.match(/<footer\b[^>]*\bid="footer"[\s\S]*?<\/footer>/) || [])[0];
  const main = (bodyInner.match(/<main[\s>][\s\S]*?<\/main>/) || [])[0];
  const mcOpenIndex = bodyInner.indexOf(MC_OPEN);

  // Bail out early if this is not a well-formed chrome page.
  if (!header || !footer || !main || mcOpenIndex === -1) return null;

  const bodyTop = bodyInner.slice(0, mcOpenIndex);
  const footerEnd = bodyInner.indexOf(footer) + footer.length;
  const mcCloseIndex = bodyInner.indexOf('</div>', footerEnd);
  if (mcCloseIndex === -1) return null;
  const bodyBottom = bodyInner.slice(mcCloseIndex + '</div>'.length);

  return { header, footer, main, bodyTop, bodyBottom };
}

// ---------- write helpers ----------
function writeFile(absolutePath, content) {
  mkdirSync(dirname(absolutePath), { recursive: true });
  writeFileSync(absolutePath, content, 'utf8');
}

// clean previous generated output
for (const dir of ['src/raw', 'src/shared']) {
  const p = resolve(projectRoot, dir);
  if (existsSync(p)) rmSync(p, { recursive: true, force: true });
}

// Parse all pages first (need home chrome as shared baseline).
const parsed = pages.map(describe).map((info) => {
  const text = readFileSync(info.file, 'utf8');
  const parts = parse(text);
  const chrome = parts.bodyInner.includes(MC_OPEN) ? extractChrome(parts.bodyInner) : null;
  return { ...info, text, parts, chrome };
});

const home = parsed.find((p) => p.flatSlug === 'index') || parsed[0];
const sharedHeader = home.chrome?.header;
const sharedFooter = home.chrome?.footer;

const entries = [];
let chromeCount = 0;
let wholeCount = 0;
let headerOverrides = 0;
let footerOverrides = 0;

for (const p of parsed) {
  const rawDir = resolve(projectRoot, 'src/raw', p.flatSlug);

  if (p.chrome) {
    chromeCount++;
    writeFile(join(rawDir, 'bodyTop.html'), p.chrome.bodyTop);
    writeFile(join(rawDir, 'main.html'), p.chrome.main);
    writeFile(join(rawDir, 'bodyBottom.html'), p.chrome.bodyBottom);
    // Chrome is now fully reusable: EVERY page renders the ONE shared header +
    // footer (src/shared). main.jsx always uses the shared baseline, so per-page
    // header.html / footer.html overrides are intentionally NOT emitted anymore.
    // (bodyTop / main / bodyBottom stay per-page - they carry page-specific content.)
  } else {
    wholeCount++;
    writeFile(join(rawDir, 'body.html'), p.parts.bodyInner);
  }

  // Emit the route entry HTML at the project root, mirroring the original URL path.
  const entryAbs = resolve(projectRoot, p.entryPath);
  let entryHtml;
  if (p.chrome) {
    // React-mounted page: verbatim head + a #root anchor + the module that
    // injects the original body and re-runs its scripts.
    const moduleScript = `<script type="module" src="/src/main.jsx"></script>`;
    entryHtml =
      `${p.parts.doctype}\n${p.parts.htmlOpen}\n<head>${p.parts.headInner}</head>\n` +
      `${p.parts.bodyOpenTag}<div id="root" data-slug="${p.flatSlug}"></div>${moduleScript}</body>\n</html>\n`;
  } else {
    // Whole-body pages (premium, cloaktest) are emitted as fully STATIC pages,
    // byte-for-byte like the source of truth. They have no shared chrome and no
    // React interactivity, and premium is the cloak swap target: document.write
    // of a static body renders reliably, whereas a JS-injected body races the
    // swap (ES modules are evaluated once per realm) and can leave a black page.
    entryHtml =
      `${p.parts.doctype}\n${p.parts.htmlOpen}\n<head>${p.parts.headInner}</head>\n` +
      `${p.parts.bodyOpenTag}${p.parts.bodyInner}</body>\n</html>\n`;
  }
  writeFile(entryAbs, entryHtml);
  entries.push(p.entryPath);
}

// Shared chrome baseline (from home) used by pages that match it.
mkdirSync(resolve(projectRoot, 'src/shared'), { recursive: true });
if (sharedHeader) writeFile(resolve(projectRoot, 'src/shared/header.html'), sharedHeader);
if (sharedFooter) writeFile(resolve(projectRoot, 'src/shared/footer.html'), sharedFooter);

writeFile(resolve(projectRoot, 'mpa-entries.json'), JSON.stringify(entries.sort(), null, 2) + '\n');

console.log(`Generated ${entries.length} entries: ${chromeCount} chrome pages, ${wholeCount} whole-body pages.`);
console.log(`Chrome overrides -> header: ${headerOverrides}, footer: ${footerOverrides} (0 means shared chrome is identical everywhere).`);
