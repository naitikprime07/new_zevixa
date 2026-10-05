// de_localize.js - revert premium page back to REMOTE CDN assets (no local images).
// Broken CDN thumbs (img-04..10 = 404 on CDN) stay mapped to existing remote thumbs.
const fs = require('fs');
const f = 'site/premium/index.html';
let h = fs.readFileSync(f, 'utf8');

const CDN = 'https://pixoria-dashboard.b-cdn.net/assets/';
const TENOR = 'https://media.tenor.com/WX_LDjYUrMsAAAAj/loading.gif';

// 1) loading gif -> remote tenor
h = h.split('/assets/premium/loading/tenor-loading.gif').join(TENOR);

// 2) all other local assets -> back to remote CDN paths
h = h.split('/assets/premium/').join(CDN);

// 3) fix any leftover 404 CDN thumbs -> existing remote thumbs
const map = {
  'img-04': 'img-01', 'img-05': 'img-02', 'img-06': 'img-03',
  'img-07': 'img-01', 'img-08': 'img-02', 'img-09': 'img-03', 'img-10': 'img-01'
};
for (const [k, v] of Object.entries(map)) {
  h = h.split(CDN + 'thumb/' + k + '-thumb.jpg').join(CDN + 'thumb/' + v + '-thumb.jpg');
}

fs.writeFileSync(f, h, 'utf8');
const localRefs = (h.match(/\/assets\/premium\//g) || []).length;
console.log('local /assets/premium refs left:', localRefs);
console.log('remote CDN refs now:', (h.match(/pixoria-dashboard\.b-cdn\.net/g) || []).length);
