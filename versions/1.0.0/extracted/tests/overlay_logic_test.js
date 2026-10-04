'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const overlay = fs.readFileSync(path.join(root, 'app/web/overlay.js'), 'utf8');
const css = fs.readFileSync(path.join(root, 'app/web/overlay.css'), 'utf8');
const html = fs.readFileSync(path.join(root, 'app/web/overlay.html'), 'utf8');

assert.match(overlay, /new WebSocket/);
assert.match(overlay, /textContent = active\.text/);
assert.match(overlay, /messageMode !== 'crawl'/);
assert.doesNotMatch(overlay, /innerHTML\s*=\s*active/);
assert.match(css, /breaking-in/);
assert.match(css, /ticker-in/);
assert.match(css, /ticker-crawl/);
assert.match(html, /aria-live="polite"/);

console.log('overlay logic checks passed');
