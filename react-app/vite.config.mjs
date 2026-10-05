import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const root = dirname(fileURLToPath(import.meta.url));

// The generator (tools/generate.mjs) writes mpa-entries.json listing every route
// entry HTML file (paths are relative to this project root and mirror the exact
// original URL paths, e.g. "index.html", "category/news/index.html").
function loadEntries() {
  const manifest = resolve(root, 'mpa-entries.json');
  if (!existsSync(manifest)) {
    // Fall back to the home entry so `vite` can at least start before first generate.
    return ['index.html'];
  }
  return JSON.parse(readFileSync(manifest, 'utf8'));
}

const entries = loadEntries();

export default defineConfig({
  root,
  plugins: [react()],
  // Keep absolute public paths (/_assets, /assets) resolving to the copied site assets.
  publicDir: resolve(root, 'public'),
  build: {
    // Faithful multi-page build: one output HTML per original route, preserving
    // the directory/index.html layout so URLs stay identical to the static site.
    rollupOptions: {
      input: entries.map((e) => resolve(root, e)),
    },
  },
});
