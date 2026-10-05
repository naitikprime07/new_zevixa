// Simulates cloak-edge-router gates for known in-app / real-world User-Agents.
// Usage: node test_useragents.js
const fs = require("fs");

// --- gate logic copied 1:1 from the router script ---
function gate(qs, ua, opts = {}) {
  const q = (qs + "&").toLowerCase();
  const u = (ua || "").toLowerCase();

  const clickIds = [
    "fbclid=", "gclid=", "ttclid=", "msclkid=", "twclid=",
    "dclid=", "wbraid=", "gbraid=", "utm_fb=", "utm_source=facebook",
    "utm_source=fb", "utm_source=instagram", "utm_source=tiktok",
    "utm_source=google", "utm_campaign=", "preview=1", "test=premium",
  ];
  const hasClick = clickIds.some((c) => q.indexOf(c) !== -1);
  if (!hasClick) return "NORMAL (no ad marker)";

  const botRe = /bot|crawl|spider|slurp|facebookexternalhit|facebookcatalog|facebot|googlebot|bingbot|headless|lighthouse|ptst|bytespider|mediapartners-google/i;
  if (botRe.test(u) || opts.webdriver) return "NORMAL (bot gate)";

  const isPreview = q.indexOf("preview=1") !== -1 || q.indexOf("test=premium") !== -1;
  const isMobile = /mobile|iphone|ipod|android.*mobile|windows phone/i.test(u);
  const isTablet = /ipad|android(?!.*mobile)|tablet/i.test(u);
  const hasTouch = opts.maxTouchPoints > 0 || opts.ontouchstart;
  if (!isPreview && !isMobile && !isTablet && !(hasTouch && (opts.width || 1920) <= 1024))
    return "NORMAL (device gate)";

  return "PREMIUM";
}

// --- real-world UA strings ---
const cases = [
  ["FB in-app browser iOS (iPhone, FBAN/FBIOS)",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 [FBAN/FBIOS;FBAV/430.0.0.41.113;FBBV/58000810;FBDV/iPhone13,2;FBMD/iPhone;FBSN/iOS;FBSV/16.6;FBSS/3;FBID/phone;FBLC/en_US;FBOP/5]",
    { maxTouchPoints: 5 }],
  ["FB in-app browser Android (FB_IAB/FB4A)",
    "Mozilla/5.0 (Linux; Android 13; SM-A525F Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/116.0.0.0 Mobile Safari/537.36 [FB_IAB/FB4A;FBAV/431.0.0.50.114;]",
    { maxTouchPoints: 5 }],
  ["Instagram in-app Android (FB_IAB/Instagram)",
    "Mozilla/5.0 (Linux; Android 12; Redmi Note 10 Pro Build/SP1A.210812.016; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/114.0.0.0 Mobile Safari/537.36 [FB_IAB/Instagram;FBAV/310.1.0.37.113;]",
    { maxTouchPoints: 5 }],
  ["Instagram in-app iOS",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 [FBAN/FBIOS;FBAV/430.0.0.41.113;FBDV/iPhone15,2;FBMD/iPhone;FBSN/iOS;FBSV/17.1;FBSS/3;FBID/phone;FBLC/en_US]",
    { maxTouchPoints: 5 }],
  ["Messenger in-app iOS",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 [FBAN/MESSENGERIOS;FBAV/490.0;FBDV/iPhone12,1]",
    { maxTouchPoints: 5 }],
  ["Chrome custom tab Android (ad link default opener)",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
    { maxTouchPoints: 5 }],
  ["Samsung Internet mobile",
    "Mozilla/5.0 (Linux; Android 13; SAMSUNG SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/23.0 Chrome/115.0.0.0 Mobile Safari/537.36",
    { maxTouchPoints: 5 }],
  ["Googlebot (review crawler)",
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)", {}],
  ["facebookexternalhit (FB link preview scraper)",
    "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)", {}],
  ["Desktop Chrome (no touch)",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", { maxTouchPoints: 0 }],
];

const qs = "?fbclid=IwAR2d4Rtest99";
console.log("Query:", qs, "\n");
for (const [name, ua, opts] of cases) {
  console.log(gate(qs, ua, opts).padEnd(28), "=>", name);
}
