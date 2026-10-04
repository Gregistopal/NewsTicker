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
const updateHtml = fs.readFileSync(path.join(root, 'app/web/update-required.html'), 'utf8');
const fieldBlock = control.match(/const fields = \[([\s\S]*?)\];/)[1];
const configuredFields = [...fieldBlock.matchAll(/'([^']+)'/g)].map(match => match[1]);
for (const field of configuredFields) {
  assert.match(controlHtml, new RegExp(`id=["']${field}["']`), `missing controller field ${field}`);
}

assert.match(overlay, /new WebSocket/);
assert.match(overlay, /Array\.isArray\(active\.items\)/);
assert.match(overlay, /animationend/);
assert.match(overlay, /sequenceIndex/);
assert.match(overlay, /sequenceComplete/);
assert.match(overlay, /completedActiveId/);
assert.match(overlay, /completionRetryTimer/);
assert.match(overlay, /secondaryOutput/);
assert.match(overlay, /state\.animationHideAt/);
assert.match(overlay, /mirrorSource\$\{number\}Output/);
assert.match(overlay, /entranceComplete/);
assert.match(overlay, /event\.animationName === 'ticker-in'/);
assert.match(overlay, /event\.animationName === 'mirror-lift'/);
assert.match(overlay, /--mirror-lift/);
assert.match(overlay, /!preview && assignedHere/);
assert.doesNotMatch(overlay, /if \(activeId === completedActiveId\) hide\(\)/);
assert.match(overlay, /activeMinimumItems/);
assert.match(overlay, /activeMinimumHideAt/);
assert.doesNotMatch(overlay, /activeHideAt/);
assert.match(overlay, /configureCounterCube/);
assert.doesNotMatch(overlay, /innerHTML\s*=\s*active/);
assert.match(css, /breaking-in/);
assert.match(css, /ticker-in/);
assert.match(css, /ticker-crawl/);
assert.match(css, /animation-play-state: paused/);
assert.match(css, /--bottom-offset: 0px/);
assert.match(css, /--side-margin: 0px/);
assert.match(css, /--ticker-height: 72px/);
assert.match(css, /mirror-lift/);
assert.match(css, /secondary-output \.stage/);
assert.match(html, /aria-live="polite"/);
assert.match(html, /id="mirrorLayer"/);
assert.match(html, /id="counterCube"/);
assert.match(html, /DAYS LIVE:/);
assert.doesNotMatch(html, /id="kicker"/);
assert.doesNotMatch(html, /LIVE UPDATE/);
assert.match(controlHtml, /id="quitTopButton"/);
assert.match(controlHtml, /id="itemsPerAppearance"/);
assert.match(controlHtml, /id="daysLiveStartDate"/);
assert.match(controlHtml, /id="counterFlipSeconds"/);
assert.match(controlHtml, /id="mirrorSource4"/);
assert.match(controlHtml, /id="copySecondaryUrl"/);
assert.match(controlHtml, /id="localApiMessage"/);
assert.match(controlHtml, /control\.js\?v=1\.1\.0/);
assert.match(html, /overlay\.js\?v=1\.1\.0/);
assert.match(control, /quitTopButton.*quitApp/);
assert.match(updateHtml, /NewsTicker update ready/);
assert.match(updateHtml, /Open running dashboard/);

console.log('overlay logic checks passed');
