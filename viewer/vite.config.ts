import { defineConfig } from 'vite';
import { viteSingleFile } from 'vite-plugin-singlefile';

// Emits to docs/map/ (a subfolder of the repo's docs/, which report.py's
// generate_html_report also writes into) so GitHub Pages can serve this
// directly alongside the report -- see hfu/faceless-cartographer's
// vite.config.ts, which established the same base:'./'/singlefile/docs
// pattern this was copied from.
export default defineConfig({
  base: './',
  publicDir: 'public',
  plugins: [viteSingleFile()],
  build: {
    outDir: '../docs/map',
    emptyOutDir: true
  }
});
