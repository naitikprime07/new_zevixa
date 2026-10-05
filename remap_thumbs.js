// remap_thumbs.js - point the 7 CDN-404 thumbnail URLs to existing local thumbs
const fs = require('fs');
const f = 'site/premium/index.html';
let h = fs.readFileSync(f, 'utf8');
const map = {
  'img-04': 'img-01', 'img-05': 'img-02', 'img-06': 'img-03',
  'img-07': 'img-01', 'img-08': 'img-02', 'img-09': 'img-03', 'img-10': 'img-01'
};
let hits = 0;
for (const [k, v] of Object.entries(map)) {
  const from = 'https://pixoria-dashboard.b-cdn.net/assets/thumb/' + k + '-thumb.jpg';
  const to = '/assets/premium/thumb/' + v + '-thumb.jpg';
  const before = h;
  h = h.split(from).join(to);
  if (before !== h) hits++;
}
fs.writeFileSync(f, h, 'utf8');
const left = h.match(/https:\/\/pixoria-dashboard\.b-cdn\.net[^"')\s]*/g) || [];
console.log('remapped url groups:', hits);
console.log('remaining remote b-cdn refs:', left.length);
left.slice(0, 10).forEach(u => console.log(' -', u));
