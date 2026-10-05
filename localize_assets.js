// localize_assets.js
// Downloads all remote premium assets (pixoria-dashboard.b-cdn.net + tenor loading gif)
// into site/assets/premium/ and rewrites premium/index.html to use local paths.
// Keeps the rest of the code identical to the working reference.
const fs = require('fs');
const path = require('path');
const https = require('https');

const FILE = path.join(__dirname, 'site', 'premium', 'index.html');
const DEST_ROOT = path.join(__dirname, 'site', 'assets', 'premium');
const TIMEOUT = 30000;

let html = fs.readFileSync(FILE, 'utf8');

// Collect unique remote URLs
const urls = new Set();
const reCdn = /https:\/\/pixoria-dashboard\.b-cdn\.net\/assets\/[A-Za-z0-9_\-\/\.]+\.(?:jpg|jpeg|png|gif|webp)/g;
const reTenor = /https:\/\/media\.tenor\.com\/[A-Za-z0-_\-]+\/loading\.gif/g;
(html.match(reCdn) || []).forEach(u => urls.add(u));
(html.match(reTenor) || []).forEach(u => urls.add(u));

function localPathFor(u) {
    if (u.includes('b-cdn.net')) {
        const rel = u.replace('https://pixoria-dashboard.b-cdn.net/assets/', '');
        return { rel: rel, url: u };
    }
    return { rel: 'loading/tenor-loading.gif', url: u };
}

function download(url, dest) {
    return new Promise(resolve => {
        const dir = path.dirname(dest);
        fs.mkdirSync(dir, { recursive: true });
        const f = fs.createWriteStream(dest);
        const req = https.get(url, { headers: { 'User-Agent': 'Mozilla/5.0' }, timeout: TIMEOUT }, res => {
            if (res.statusCode !== 200) {
                res.destroy();
                f.close();
                fs.unlink(dest, () => { });
                return resolve({ url, ok: false, why: 'HTTP ' + res.statusCode });
            }
            res.pipe(f);
            f.on('finish', () => f.close(() => resolve({ url, ok: true, size: fs.statSync(dest).size })));
        });
        req.on('error', e => { f.close(); fs.unlink(dest, () => { }); resolve({ url, ok: false, why: e.message }); });
        req.on('timeout', () => { req.destroy(); f.close(); fs.unlink(dest, () => { }); resolve({ url, ok: false, why: 'timeout' }); });
    });
}

(async () => {
    const jobs = [...urls].map(u => {
        const { rel, url } = localPathFor(u);
        return { url: url, dest: path.join(DEST_ROOT, rel), rel: rel };
    });
    console.log('Downloading ' + jobs.length + ' assets...');
    let okCount = 0;
    for (const j of jobs) {
        const r = await download(j.url, j.dest);
        if (r.ok) {
            okCount++;
            // rewrite this URL everywhere in the file
            html = html.split(j.url).join('/assets/premium/' + j.rel.replace(/\\/g, '/'));
        } else {
            console.log('FAIL: ' + j.url + ' (' + r.why + ')');
        }
    }
    fs.writeFileSync(FILE, html, 'utf8');
    console.log('Localized ' + okCount + '/' + jobs.length + ' assets; file updated.');
})();
