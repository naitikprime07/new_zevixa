"""Build a client-side search for the offline static clone.

Generates site/assets/search.js containing an index of all local pages
(title + keywords + url) and wires the theme's search modal (.ct-search-form)
to filter that index live and navigate to the best match on submit.

Also injects a <script src="/assets/search.js"> tag before </body> on every
page (idempotent via a marker).
"""
import glob
import os
import re
import json

ROOT = r"d:\pixoria_output\site"
ASSETS_DIR = os.path.join(ROOT, "assets")
JS_PATH = os.path.join(ASSETS_DIR, "search.js")
MARKER = "assets/search.js"

SKIP = {"cloaktest", "premium"}  # internal test + cloaked pages, exclude from index


def clean_text(s):
    s = re.sub(r"<script[\s\S]*?</script>", " ", s, flags=re.I)
    s = re.sub(r"<style[\s\S]*?</style>", " ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = (s.replace("&nbsp;", " ").replace("&amp;", "&")
          .replace("&#8217;", "'").replace("&rsquo;", "'")
          .replace("&hellip;", "...").replace("â€™", "'"))
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def page_title(html):
    m = re.search(r'<h1 class="page-title"[^>]*>([\s\S]*?)</h1>', html)
    if m:
        return clean_text(m.group(1))
    m = re.search(r"<title>([\s\S]*?)</title>", html)
    if m:
        t = clean_text(m.group(1))
        return re.sub(r"\s*[-–]\s*Pixoria\s*$", "", t)
    return ""


def page_keywords(html):
    m = re.search(
        r'<div class="entry-content is-layout-constrained">([\s\S]*?)</article>', html)
    text = clean_text(m.group(1)) if m else ""
    if not text:
        m2 = re.search(r"<body[\s\S]*?</body>", html)
        text = clean_text(m2.group(0)) if m2 else ""
    return text[:1200]


def url_for(path):
    rel = os.path.relpath(path, ROOT).replace(
        "\\", "/")  # e.g. "amazon.../index.html"
    folder = rel.rsplit("/", 1)[0] if rel != "index.html" else ""
    return "/" + folder + "/" if folder else "/"


def build_index():
    pages = []
    for p in glob.glob(os.path.join(ROOT, "**", "index.html"), recursive=True):
        rel = os.path.relpath(p, ROOT).replace("\\", "/")
        folder = rel.rsplit("/", 1)[0] if rel != "index.html" else ""
        if folder in SKIP:
            continue
        with open(p, encoding="utf-8") as f:
            html = f.read()
        title = page_title(html)
        if not title:
            continue
        pages.append({"t": title, "u": url_for(p), "k": page_keywords(html)})
    return pages


JS_TEMPLATE = """(function () {
  "use strict";
  var PAGES = __DATA__;

  function norm(s) { return (s || "").toLowerCase(); }
  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function search(q) {
    q = norm(q).trim();
    if (!q) return [];
    var terms = q.split(/\\s+/);
    var out = [];
    for (var i = 0; i < PAGES.length; i++) {
      var p = PAGES[i];
      var hay = norm(p.t) + " " + norm(p.k);
      var score = 0;
      for (var j = 0; j < terms.length; j++) {
        var term = terms[j];
        if (!term) continue;
        if (hay.indexOf(term) === -1) { score = 0; break; }
        score += (norm(p.t).indexOf(term) !== -1) ? 5 : 1;
      }
      if (score > 0) out.push([score, i]);
    }
    out.sort(function (a, b) { return b[0] - a[0]; });
    return out.map(function (x) { return PAGES[x[1]]; });
  }

  function injectStyles() {
    if (document.getElementById("pix-search-style")) return;
    var css = ".pix-search-results{position:absolute;z-index:100000;left:0;right:0;top:100%;"
      + "margin-top:6px;max-height:60vh;overflow:auto;background:#fff;border:1px solid #e1e8ed;"
      + "border-radius:6px;box-shadow:0 10px 30px rgba(0,0,0,.18);text-align:left;display:none}"
      + ".pix-search-item{display:block;padding:12px 16px;border-bottom:1px solid #f0f2f4;"
      + "color:#192a3d;text-decoration:none;font-size:15px;line-height:1.4}"
      + ".pix-search-item:hover,.pix-search-item:focus{background:#f5f8ff}"
      + ".pix-search-empty{padding:14px 16px;color:#5b6b7b;font-size:14px}"
      // Belt-and-suspenders: make sure an .active panel is actually visible and
      // interactive even though the theme's lazy chunk (which normally sets
      // body[data-panel="in"]) fails to load offline.
      + ".ct-panel.active{opacity:1 !important;pointer-events:auto !important}"
      + ".ct-panel[data-behaviour='modal'].active{display:flex !important}"
      + ".ct-panel[inert]{}";
    var el = document.createElement("style");
    el.id = "pix-search-style";
    el.textContent = css;
    document.head.appendChild(el);
  }

  function render(inner, results, q) {
    var box = inner.querySelector(".pix-search-results");
    if (!box) {
      box = document.createElement("div");
      box.className = "pix-search-results";
      inner.appendChild(box);
    }
    if (!q) { box.style.display = "none"; box.innerHTML = ""; return; }
    if (!results.length) {
      box.innerHTML = '<div class="pix-search-empty">No results for \\u201C' + esc(q) + '\\u201D</div>';
      box.style.display = "block";
      return;
    }
    var html = "";
    for (var i = 0; i < results.length && i < 8; i++) {
      html += '<a class="pix-search-item" href="' + esc(results[i].u) + '">'
        + esc(results[i].t) + "</a>";
    }
    box.innerHTML = html;
    box.style.display = "block";
  }

  // ---- Panel (search modal / offcanvas) controller -----------------------
  // The Blocksy theme lazy-loads the code that removes [inert] and sets
  // body[data-panel="in"] when a toggle is clicked. Offline that chunk is
  // fetched from the remote CDN and fails, so the panel opens invisible and
  // non-interactive. We reproduce just that behaviour here and stop the
  // theme's own half-broken handler from fighting us.
  function openPanel(panel) {
    if (!panel) return;
    panel.removeAttribute("inert");
    panel.classList.add("active");
    document.body.setAttribute("data-panel", "in");
    var field = panel.querySelector('input[name="s"]');
    if (field) { try { field.focus(); } catch (e) {} }
  }
  function closePanel(panel) {
    if (!panel) return;
    panel.classList.remove("active");
    document.body.setAttribute("data-panel", "");
    panel.setAttribute("inert", "");
  }
  function panelFromButton(btn) {
    var sel = btn.getAttribute("data-toggle-panel") || btn.getAttribute("href") || "";
    if (sel.charAt(0) !== "#") return null;
    return document.querySelector(sel);
  }
  function setupPanels() {
    document.addEventListener("click", function (e) {
      var t = e.target;
      var toggle = t.closest ? t.closest("[data-toggle-panel]") : null;
      if (toggle) {
        e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation();
        var p = panelFromButton(toggle);
        if (p) { p.classList.contains("active") ? closePanel(p) : openPanel(p); }
        return;
      }
      var close = t.closest ? t.closest(".ct-toggle-close") : null;
      if (close) {
        e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation();
        closePanel(close.closest(".ct-panel"));
        return;
      }
      // Click on the dimmed backdrop (outside an open modal) closes it.
      if (document.body.getAttribute("data-panel") === "in") {
        var open = document.querySelector(".ct-panel.active");
        if (open && open.getAttribute("data-behaviour") === "modal" &&
            t.closest && !t.closest(".ct-panel")) {
          closePanel(open);
        }
      }
    }, true);
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && document.body.getAttribute("data-panel") === "in") {
        var open = document.querySelector(".ct-panel.active");
        if (open) closePanel(open);
      }
    });
    // Panels start inert in the saved HTML; drop inert so focus works the
    // moment the modal is opened.
    var panels = document.querySelectorAll(".ct-panel[inert]");
    for (var i = 0; i < panels.length; i++) panels[i].removeAttribute("inert");
  }

  function init() {
    injectStyles();
    setupPanels();
    var forms = document.querySelectorAll(".ct-search-form");
    for (var i = 0; i < forms.length; i++) {
      (function (form) {
        var input = form.querySelector('input[name="s"]');
        if (!input) return;
        var inner = form.querySelector(".ct-search-form-inner") || form;
        inner.style.position = "relative";
        form.removeAttribute("data-live-results");
        input.setAttribute("autocomplete", "off");
        input.addEventListener("input", function () {
          render(inner, search(input.value), input.value.trim());
        });
        form.addEventListener("submit", function (e) {
          e.preventDefault();
          e.stopPropagation();
          var res = search(input.value);
          if (res.length) { window.location.href = res[0].u; }
          else { render(inner, res, input.value.trim()); }
        });
      })(forms[i]);
    }
  }

  if (document.readyState !== "loading") init();
  else document.addEventListener("DOMContentLoaded", init);
})();
"""


def write_js(pages):
    os.makedirs(ASSETS_DIR, exist_ok=True)
    data = json.dumps(pages, ensure_ascii=True)
    js = JS_TEMPLATE.replace("__DATA__", data)
    with open(JS_PATH, "w", encoding="utf-8") as f:
        f.write(js)
    print("Wrote", os.path.relpath(JS_PATH, ROOT), "with", len(pages), "pages")


def inject_script():
    tag = '<script src="/assets/search.js" defer></script>'
    changed = 0
    for p in glob.glob(os.path.join(ROOT, "**", "index.html"), recursive=True):
        with open(p, encoding="utf-8") as f:
            html = f.read()
        if MARKER in html:
            continue
        if "</body>" in html:
            html = html.replace("</body>", "  " + tag + "\n</body>", 1)
        else:
            html += "\n" + tag
        with open(p, "w", encoding="utf-8") as f:
            f.write(html)
        changed += 1
    print("Injected script tag into", changed, "pages")


def main():
    pages = build_index()
    for pg in pages:
        print("  indexed:", pg["u"], "->", pg["t"][:60])
    write_js(pages)
    inject_script()


if __name__ == "__main__":
    main()
