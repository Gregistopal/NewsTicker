'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const overlay = fs.readFileSync(path.join(root, 'app/web/overlay.js'), 'utf8');
const css = fs.readFileSync(path.join(root, 'app/web/overlay.css'), 'utf8');
const html = fs.readFileSync(path.join(root, 'app/web/overlay.html'), 'utf8');
const control = fs.readFileSync(path.join(root, 'app/web/control.js'), 'utf8');
const controlHtml = fs.readFileSync(path.join(root, 'app/web/index.html'), 'utf8');

assert.match(overlay, /new WebSocket/);
assert.match(overlay, /Array\.isArray\(active\.items\)/);
assert.match(overlay, /animationend/);
assert.match(overlay, /sequenceIndex/);
assert.doesNotMatch(overlay, /innerHTML\s*=\s*active/);
assert.match(css, /breaking-in/);
assert.match(css, /ticker-in/);
assert.match(css, /ticker-crawl/);
assert.match(css, /animation-play-state: paused/);
assert.match(css, /--bottom-offset: 0px/);
assert.match(css, /--side-margin: 0px/);
assert.match(css, /--ticker-height: 72px/);
assert.match(html, /aria-live="polite"/);
assert.doesNotMatch(html, /id="kicker"/);
assert.doesNotMatch(html, /LIVE UPDATE/);
assert.match(controlHtml, /id="quitTopButton"/);
assert.match(control, /quitTopButton.*quitApp/);

console.log('overlay logic checks passed');
