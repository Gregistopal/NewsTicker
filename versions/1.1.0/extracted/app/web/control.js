(() => {
  'use strict';

  const form = document.getElementById('settingsForm');
  const messageList = document.getElementById('messageList');
  const emptyMessages = document.getElementById('emptyMessages');
  const previewFrame = document.getElementById('previewFrame');
  const saveButton = document.getElementById('saveButton');
  const saveDock = document.querySelector('.save-dock');
  const saveState = document.getElementById('saveState');
  const dockTitle = document.getElementById('dockTitle');
  const toast = document.getElementById('toast');
  let csrfToken = '';
  let state = null;
  let dirty = false;
  let messages = [];
  let toastTimer = null;

  const fields = [
    'autoEnabled', 'intervalSeconds', 'visibleSeconds', 'itemsPerAppearance',
    'counterFlipSeconds', 'daysLiveStartDate', 'commandEnabled', 'command',
    'allowCustomCommandText', 'streamerUrl', 'breakingLabel',
    'showClock', 'clock24Hour', 'fontFamily', 'fontSize', 'fontWeight', 'messageMode',
    'crawlSpeed', 'uppercaseMessage', 'tickerHeight', 'labelWidth', 'bottomOffset',
    'sideMargin', 'cornerRadius', 'tickerOpacity', 'shadowStrength', 'enterMs', 'exitMs',
    'shineEnabled', 'breakingBackground', 'breakingText', 'tickerBackground', 'tickerText',
    'accentColor', 'mutedText',
    'mirrorSource1', 'mirrorSource2', 'mirrorSource3', 'mirrorSource4',
    'mirrorSource1Output', 'mirrorSource2Output', 'mirrorSource3Output', 'mirrorSource4Output',
    'localApiEnabled', 'localApiUrl', 'localApiMessage'
  ];
  const booleans = new Set(['autoEnabled', 'commandEnabled', 'allowCustomCommandText', 'showClock', 'clock24Hour', 'uppercaseMessage', 'shineEnabled', 'localApiEnabled']);
  const numbers = new Set(['intervalSeconds', 'visibleSeconds', 'itemsPerAppearance', 'counterFlipSeconds', 'fontSize', 'fontWeight', 'crawlSpeed', 'tickerHeight', 'labelWidth', 'bottomOffset', 'sideMargin', 'cornerRadius', 'tickerOpacity', 'shadowStrength', 'enterMs', 'exitMs']);
  const sliderUnits = {
    fontSize: 'px', crawlSpeed: ' px/s', tickerHeight: 'px', labelWidth: 'px',
    bottomOffset: 'px', sideMargin: 'px', cornerRadius: 'px',
    tickerOpacity: '%', shadowStrength: '%'
  };
  const appearanceDefaults = {
    breakingLabel: 'BREAKING NEWS',
    showClock: true, clock24Hour: false, fontFamily: 'Segoe UI', fontSize: 38,
    fontWeight: 700, messageMode: 'crawl', crawlSpeed: 150, uppercaseMessage: false,
    tickerHeight: 72, labelWidth: 292, bottomOffset: 0, sideMargin: 0,
    cornerRadius: 0, tickerOpacity: .97, shadowStrength: .42, enterMs: 850,
    exitMs: 500, shineEnabled: true, breakingBackground: '#d71920',
    breakingText: '#ffffff', tickerBackground: '#091421', tickerText: '#f8fbff',
    accentColor: '#ffd447', mutedText: '#afbac8'
  };

  const byId = id => document.getElementById(id);

  function flash(text, error = false) {
    clearTimeout(toastTimer);
    toast.textContent = text;
    toast.className = `toast show${error ? ' error' : ''}`;
    toastTimer = setTimeout(() => { toast.className = 'toast'; }, 2600);
  }

  function markDirty() {
    if (dirty) return;
    dirty = true;
    saveDock.classList.add('dirty');
    saveState.classList.add('dirty');
    saveState.textContent = 'Unsaved changes';
    dockTitle.textContent = 'You have unsaved changes';
  }

  function markSaved() {
    dirty = false;
    saveDock.classList.remove('dirty');
    saveState.classList.remove('dirty');
    saveState.textContent = 'All changes saved';
    dockTitle.textContent = 'Configuration is up to date';
  }

  async function api(path, body) {
    const response = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-NewsTicker-Token': csrfToken },
      body: JSON.stringify(body || {})
    });
    if (!response.ok) throw new Error((await response.text()) || `Request failed (${response.status})`);
    return response.json();
  }

  function renderMessages() {
    messageList.textContent = '';
    emptyMessages.hidden = messages.length !== 0;
    messages.forEach((item, index) => {
      const row = document.createElement('div');
      row.className = 'message-row';
      row.dataset.id = item.id;

      const enabledLabel = document.createElement('label');
      enabledLabel.className = 'message-enabled';
      enabledLabel.title = 'Include in rotation';
      const enabled = document.createElement('input');
      enabled.type = 'checkbox';
      enabled.checked = item.enabled;
      enabled.addEventListener('change', () => { item.enabled = enabled.checked; markDirty(); });
      enabledLabel.append(enabled);

      const text = document.createElement('textarea');
      text.rows = 2;
      text.maxLength = 320;
      text.value = item.text;
      text.setAttribute('aria-label', `Headline ${index + 1}`);
      text.addEventListener('input', () => { item.text = text.value; markDirty(); });

      const tools = document.createElement('div');
      tools.className = 'row-tools';
      const up = toolButton('↑', 'Move up', () => moveMessage(index, -1));
      const down = toolButton('↓', 'Move down', () => moveMessage(index, 1));
      up.disabled = index === 0;
      down.disabled = index === messages.length - 1;
      const show = toolButton('SHOW', 'Show this headline now', () => showMessage(item.id), 'show-row');
      const remove = toolButton('×', 'Delete headline', () => {
        messages.splice(index, 1);
        renderMessages();
        markDirty();
      }, 'delete-row');
      tools.append(up, down, remove, show);
      row.append(enabledLabel, text, tools);
      messageList.append(row);
    });
  }

  function toolButton(label, title, handler, className = '') {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = label;
    button.title = title;
    button.className = className;
    button.addEventListener('click', handler);
    return button;
  }

  function moveMessage(index, offset) {
    const target = index + offset;
    if (target < 0 || target >= messages.length) return;
    [messages[index], messages[target]] = [messages[target], messages[index]];
    renderMessages();
    markDirty();
  }

  function newId() {
    return globalThis.crypto?.randomUUID?.() || `message-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }

  function setField(id, value) {
    const element = byId(id);
    if (!element) return;
    if (booleans.has(id)) element.checked = Boolean(value);
    else element.value = value;
    updateAdornment(element);
  }

  function updateAdornment(element) {
    const output = document.querySelector(`output[data-for='${element.id}']`);
    if (output) {
      let value = Number(element.value);
      if (element.id === 'tickerOpacity' || element.id === 'shadowStrength') value = Math.round(value * 100);
      output.textContent = `${value}${sliderUnits[element.id] || ''}`;
    }
    const color = document.querySelector(`[data-color='${element.id}']`);
    if (color) color.textContent = element.value.toUpperCase();
    if (element.id === 'messageMode') {
      document.querySelector('.crawl-only')?.classList.toggle('is-disabled', element.value !== 'crawl');
    }
  }

  function renderSettings(settings) {
    fields.forEach(id => setField(id, settings[id]));
    messages = (settings.messages || []).map(item => ({ ...item }));
    renderMessages();
    byId('passwordHint').textContent = settings.hasStreamerPassword ? 'A password is saved locally' : 'No password saved';
    byId('clearPasswordRow').hidden = !settings.hasStreamerPassword;
    byId('streamerPassword').value = '';
    byId('clearStreamerPassword').checked = false;
    markSaved();
  }

  function collectSettings() {
    const result = {};
    fields.forEach(id => {
      const element = byId(id);
      if (booleans.has(id)) result[id] = element.checked;
      else if (numbers.has(id)) result[id] = Number(element.value);
      else result[id] = element.value;
    });
    result.messages = messages.map(item => ({ id: item.id, text: item.text.trim(), enabled: item.enabled })).filter(item => item.text);
    const password = byId('streamerPassword').value;
    if (password) result.streamerPassword = password;
    result.clearStreamerPassword = byId('clearStreamerPassword').checked;
    return result;
  }

  function updateStatus(next) {
    state = next;
    byId('versionBadge').textContent = `v${next.version}`;
    byId('overlayUrl').textContent = next.overlayUrl;
    byId('secondaryOverlayUrl').textContent = next.secondaryOverlayUrl;
    byId('localApiStatus').textContent = next.status.localApiDetail || 'Waiting for status';
    const streamer = next.status.streamer;
    const dot = byId('streamerDot');
    dot.className = `dot ${streamer === 'connected' ? 'online' : streamer === 'connecting' ? 'connecting' : streamer === 'disabled' ? '' : 'error'}`;
    const replyDetail = streamer === 'connected' && next.status.chatReplyDetail
      ? ` • ${next.status.chatReplyDetail}` : '';
    byId('streamerStatus').textContent = next.status.streamerDetail + replyDetail;
    byId('onAirBadge').textContent = next.active ? 'ON AIR' : 'STANDBY';
    byId('onAirBadge').classList.toggle('live', Boolean(next.active));
    byId('currentHeadline').textContent = next.active?.text || 'Nothing — overlay is standing by';
    byId('lastTriggered').textContent = next.status.lastTriggerBy || 'Not yet triggered';
    updateCountdown();
  }

  function updateCountdown() {
    if (!state) return;
    let text;
    if (!state.settings.autoEnabled) text = 'Automatic rotation is off';
    else if (state.active) text = 'Showing complete ticker messages';
    else if (!state.nextAutoAt) text = 'Waiting for an enabled headline';
    else {
      const remaining = Math.max(0, Math.ceil((state.nextAutoAt - state.serverTime - (Date.now() - state.receivedAt)) / 1000));
      const minutes = Math.floor(remaining / 60);
      const seconds = remaining % 60;
      text = minutes ? `${minutes}m ${String(seconds).padStart(2, '0')}s` : `${seconds}s`;
    }
    byId('nextStatus').textContent = text;
  }

  async function showMessage(messageId) {
    try {
      const next = await api('/api/show', { messageId });
      next.receivedAt = Date.now();
      updateStatus(next);
      flash('Headline sent to the overlay');
    } catch (error) { flash(error.message, true); }
  }

  async function load() {
    try {
      const response = await fetch('/api/state', { cache: 'no-store' });
      const next = await response.json();
      csrfToken = next.csrfToken;
      next.receivedAt = Date.now();
      updateStatus(next);
      renderSettings(next.settings);
      connect();
      sizePreview();
    } catch (error) {
      flash(`Could not load the controller: ${error.message}`, true);
      byId('appStatus').textContent = 'Disconnected';
      byId('appDot').className = 'dot error';
    }
  }

  function connect() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const socket = new WebSocket(`${protocol}//${location.host}/ws`);
    socket.addEventListener('message', event => {
      try {
        const next = JSON.parse(event.data);
        next.receivedAt = Date.now();
        updateStatus(next);
        if (!dirty) renderSettings(next.settings);
      } catch (_) { /* ignore malformed state */ }
    });
    socket.addEventListener('close', () => {
      byId('appStatus').textContent = 'Reconnecting…';
      byId('appDot').className = 'dot connecting';
      setTimeout(connect, 1200);
    });
    socket.addEventListener('open', () => {
      byId('appStatus').textContent = 'Running';
      byId('appDot').className = 'dot online';
    });
  }

  function sizePreview() {
    const frame = previewFrame.parentElement;
    frame.style.setProperty('--preview-scale', frame.clientWidth / 1920);
  }

  document.querySelectorAll('.tab').forEach(button => {
    button.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(item => item.classList.toggle('active', item === button));
      document.querySelectorAll('.tab-page').forEach(page => page.classList.toggle('active', page.id === `tab-${button.dataset.tab}`));
    });
  });

  fields.forEach(id => {
    const element = byId(id);
    const eventName = element.matches('select, input[type=checkbox], input[type=color]') ? 'change' : 'input';
    element.addEventListener(eventName, () => { updateAdornment(element); markDirty(); });
    if (element.type === 'range') element.addEventListener('input', () => { updateAdornment(element); markDirty(); });
  });
  byId('streamerPassword').addEventListener('input', markDirty);
  byId('clearStreamerPassword').addEventListener('change', markDirty);

  byId('addMessage').addEventListener('click', () => {
    messages.push({ id: newId(), text: 'New headline', enabled: true });
    renderMessages();
    markDirty();
    const last = messageList.querySelector('.message-row:last-child textarea');
    last?.focus(); last?.select();
  });

  form.addEventListener('submit', async event => {
    event.preventDefault();
    saveButton.disabled = true;
    saveButton.textContent = 'Saving…';
    try {
      const next = await api('/api/settings', collectSettings());
      csrfToken = next.csrfToken || csrfToken;
      next.receivedAt = Date.now();
      updateStatus(next);
      renderSettings(next.settings);
      previewFrame.contentWindow.location.reload();
      flash('Configuration saved and applied');
    } catch (error) { flash(error.message, true); }
    finally { saveButton.disabled = false; saveButton.textContent = 'Save & apply'; }
  });

  byId('showNextButton').addEventListener('click', async () => {
    try { const next = await api('/api/show', {}); next.receivedAt = Date.now(); updateStatus(next); flash('Next headline is on air'); }
    catch (error) { flash(error.message, true); }
  });
  byId('hideButton').addEventListener('click', async () => {
    try { const next = await api('/api/hide', {}); next.receivedAt = Date.now(); updateStatus(next); flash('Ticker hidden'); }
    catch (error) { flash(error.message, true); }
  });
  byId('showCustom').addEventListener('click', async () => {
    const text = byId('customHeadline').value.trim();
    if (!text) return flash('Enter a custom headline first', true);
    try { const next = await api('/api/show', { text }); next.receivedAt = Date.now(); updateStatus(next); flash('Custom headline is on air'); }
    catch (error) { flash(error.message, true); }
  });
  byId('customHeadline').addEventListener('input', event => { byId('customCount').textContent = event.target.value.length; });
  byId('copyUrl').addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(byId('overlayUrl').textContent); flash('OBS URL copied'); }
    catch (_) { flash('Select and copy the URL manually', true); }
  });
  byId('copySecondaryUrl').addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(byId('secondaryOverlayUrl').textContent); flash('Secondary OBS URL copied'); }
    catch (_) { flash('Select and copy the URL manually', true); }
  });
  byId('resetAppearance').addEventListener('click', () => {
    Object.entries(appearanceDefaults).forEach(([id, value]) => setField(id, value));
    markDirty();
    flash('Default style loaded — save to apply it');
  });
  async function quitApp() {
    if (!confirm('Quit NewsTicker? The OBS source will go offline until you launch NewsTicker.exe again.')) return;
    try { await api('/api/quit', {}); document.body.innerHTML = '<main style="display:grid;place-items:center;height:100vh;text-align:center"><div><h1>NewsTicker stopped</h1><p style="color:#8f9dad">You can close this tab.</p></div></main>'; }
    catch (error) { flash(error.message, true); }
  }
  byId('quitButton').addEventListener('click', quitApp);
  byId('quitTopButton').addEventListener('click', quitApp);

  window.addEventListener('resize', sizePreview);
  window.addEventListener('beforeunload', event => { if (dirty) { event.preventDefault(); event.returnValue = ''; } });
  setInterval(updateCountdown, 1000);
  load();
})();
