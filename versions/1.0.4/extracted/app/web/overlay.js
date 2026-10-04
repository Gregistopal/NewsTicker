(() => {
  'use strict';

  const stage = document.getElementById('stage');
  const breakingLabel = document.getElementById('breakingLabel');
  const counterShell = document.getElementById('counterShell');
  const counterCube = document.getElementById('counterCube');
  const clock = document.getElementById('clock');
  const daysLive = document.getElementById('daysLive');
  const message = document.getElementById('message');
  const messageWindow = document.getElementById('messageWindow');
  const preview = new URLSearchParams(location.search).get('preview') === '1';
  let settings = null;
  let activeId = null;
  let serverOffset = 0;
  let enterTimer = null;
  let exitTimer = null;
  let sequence = [];
  let sequenceIndex = 0;
  let sequenceLoopStart = 0;
  let completedItems = 0;
  let activeMinimumItems = 1;
  let activeMinimumHideAt = 0;
  let completionPending = false;
  let completionSent = false;
  let socket = null;
  let counterTimer = null;
  let counterSignature = '';

  function css(name, value) {
    document.documentElement.style.setProperty(name, value);
  }

  function rgb(hex) {
    const value = String(hex).replace('#', '');
    return `${parseInt(value.slice(0, 2), 16)} ${parseInt(value.slice(2, 4), 16)} ${parseInt(value.slice(4, 6), 16)}`;
  }

  function applySettings(next) {
    settings = next;
    css('--breaking-bg', next.breakingBackground);
    css('--breaking-text', next.breakingText);
    css('--ticker-bg', next.tickerBackground);
    css('--ticker-rgb', rgb(next.tickerBackground));
    css('--ticker-text', next.tickerText);
    css('--accent', next.accentColor);
    css('--muted', next.mutedText);
    css('--font-stack', next.fontStack);
    css('--font-size', `${next.fontSize}px`);
    css('--font-weight', next.fontWeight);
    css('--ticker-height', `${next.tickerHeight}px`);
    css('--label-width', `${next.labelWidth}px`);
    css('--bottom-offset', `${next.bottomOffset}px`);
    css('--side-margin', `${next.sideMargin}px`);
    css('--radius', `${next.cornerRadius}px`);
    css('--ticker-opacity', next.tickerOpacity);
    css('--shadow-alpha', next.shadowStrength);
    css('--enter-ms', `${next.enterMs}ms`);
    css('--exit-ms', `${next.exitMs}ms`);
    css('--breaking-in', `${Math.round(next.enterMs * .60)}ms`);
    css('--ticker-in', `${Math.round(next.enterMs * .67)}ms`);
    css('--ticker-delay', `${Math.round(next.enterMs * .28)}ms`);
    css('--content-in', `${Math.round(next.enterMs * .42)}ms`);
    css('--content-delay', `${Math.round(next.enterMs * .63)}ms`);
    css('--sheen-duration', `${Math.round(next.enterMs * 1.2)}ms`);
    css('--sheen-delay', `${Math.round(next.enterMs * .54)}ms`);
    css('--breaking-out', `${Math.round(next.exitMs * .82)}ms`);
    css('--breaking-out-delay', `${Math.round(next.exitMs * .13)}ms`);
    css('--content-out', `${Math.round(next.exitMs * .42)}ms`);
    breakingLabel.textContent = next.breakingLabel;
    counterShell.classList.toggle('is-hidden', !next.showClock);
    stage.classList.toggle('uppercase-message', next.uppercaseMessage);
    stage.classList.toggle('shine', next.shineEnabled);
    stage.classList.remove('mode-headline');
    stage.classList.add('mode-crawl');
    if (preview && !activeId) showPreview();
    updateClock();
    updateDaysLive();
    configureCounterCube();
  }

  function resetCrawl() {
    message.style.animation = 'none';
    void message.offsetWidth;
    message.style.animation = '';
    if (!settings) return;
    const width = messageWindow.clientWidth;
    const textWidth = Math.ceil(message.scrollWidth);
    const distance = width + textWidth + 24;
    const duration = Math.max(3, distance / settings.crawlSpeed);
    message.style.setProperty('--crawl-start', `${width + 24}px`);
    // End exactly when the trailing edge leaves the message window. The old
    // extra off-screen travel left the empty ticker sitting on screen.
    message.style.setProperty('--crawl-end', `${-textWidth}px`);
    message.style.setProperty('--crawl-duration', `${duration}s`);
  }

  function showPreview() {
    if (!settings) return;
    clearTimeout(enterTimer);
    clearTimeout(exitTimer);
    activeId = null;
    message.textContent = settings.messages.find(item => item.enabled)?.text || 'Your next headline will appear here.';
    stage.className = 'stage preview';
    stage.classList.toggle('uppercase-message', settings.uppercaseMessage);
    stage.classList.toggle('shine', settings.shineEnabled);
    stage.classList.add('mode-crawl');
    requestAnimationFrame(resetCrawl);
  }

  function begin(active) {
    clearTimeout(enterTimer);
    clearTimeout(exitTimer);
    activeId = active.id;
    sequence = Array.isArray(active.items) && active.items.length
      ? active.items.filter(item => item && item.text)
      : [{ text: active.text }];
    sequenceIndex = 0;
    sequenceLoopStart = Math.max(0, Math.min(sequence.length - 1, Number(active.loopStart) || 0));
    completedItems = 0;
    activeMinimumItems = Math.max(1, Number(active.minimumItems) || 1);
    activeMinimumHideAt = Number(active.minimumHideAt) || 0;
    completionPending = false;
    completionSent = false;
    message.textContent = sequence[0]?.text || active.text;
    stage.classList.remove('preview', 'visible', 'hiding', 'showing');
    void stage.offsetWidth;
    const wait = Math.max(0, active.startAt - (Date.now() + serverOffset));
    enterTimer = setTimeout(() => {
      stage.classList.add('showing');
      requestAnimationFrame(resetCrawl);
      enterTimer = setTimeout(() => {
        if (activeId === active.id) {
          stage.classList.remove('showing');
          stage.classList.add('visible');
        }
      }, settings.enterMs + 60);
    }, wait);
  }

  function hide() {
    if (!activeId) {
      if (preview) showPreview();
      return;
    }
    activeId = null;
    sequence = [];
    sequenceIndex = 0;
    sequenceLoopStart = 0;
    completedItems = 0;
    activeMinimumItems = 1;
    activeMinimumHideAt = 0;
    completionPending = false;
    completionSent = false;
    clearTimeout(enterTimer);
    clearTimeout(exitTimer);
    stage.classList.remove('showing', 'visible', 'preview');
    stage.classList.add('hiding');
    exitTimer = setTimeout(() => {
      stage.classList.remove('hiding');
      if (preview) showPreview();
    }, (settings?.exitMs || 500) + 80);
  }

  function receive(state) {
    if (!state || state.type !== 'state') return;
    serverOffset = state.serverTime - Date.now();
    applySettings(state.settings);
    if (state.active) {
      if (state.active.id !== activeId) begin(state.active);
    } else if (activeId) {
      hide();
    } else if (preview) {
      showPreview();
    }
  }

  function connect() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const nextSocket = new WebSocket(`${protocol}//${location.host}/ws`);
    socket = nextSocket;
    nextSocket.addEventListener('open', notifySequenceComplete);
    nextSocket.addEventListener('message', event => {
      try { receive(JSON.parse(event.data)); } catch (_) { /* ignore malformed packets */ }
    });
    nextSocket.addEventListener('close', () => {
      if (socket === nextSocket) socket = null;
      setTimeout(connect, 1200);
    });
  }

  function notifySequenceComplete() {
    if (preview || !activeId || !completionPending || completionSent) return;
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    const completedActiveId = activeId;
    socket.send(JSON.stringify({ type: 'sequenceComplete', activeId: completedActiveId, completedItems }));
    completionSent = true;
    // Begin the visual exit immediately. The server still receives the exact
    // completion boundary and synchronizes every other open overlay instance.
    requestAnimationFrame(() => {
      if (activeId === completedActiveId) hide();
    });
  }

  message.addEventListener('animationend', event => {
    if (event.animationName !== 'ticker-crawl' || !activeId || !sequence.length) return;
    completedItems += 1;
    const minimumTimeReached = !activeMinimumHideAt
      || Date.now() + serverOffset >= activeMinimumHideAt;
    if (!preview && completedItems >= activeMinimumItems && minimumTimeReached) {
      completionPending = true;
      notifySequenceComplete();
      return;
    }
    sequenceIndex += 1;
    if (sequenceIndex >= sequence.length) sequenceIndex = sequenceLoopStart;
    message.textContent = sequence[sequenceIndex].text;
    requestAnimationFrame(resetCrawl);
  });

  function updateClock() {
    if (!settings?.showClock) return;
    clock.textContent = new Intl.DateTimeFormat(undefined, {
      hour: 'numeric',
      minute: '2-digit',
      hour12: !settings.clock24Hour,
    }).format(new Date());
  }

  function updateDaysLive() {
    if (!settings?.daysLiveStartDate) return;
    const parts = settings.daysLiveStartDate.split('-').map(Number);
    if (parts.length !== 3 || parts.some(value => !Number.isFinite(value))) return;
    const today = new Date();
    const currentDate = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
    const startDate = Date.UTC(parts[0], parts[1] - 1, parts[2]);
    const days = Math.max(0, Math.round((currentDate - startDate) / 86400000) + 1);
    daysLive.textContent = String(days);
  }

  function configureCounterCube() {
    if (!settings) return;
    const signature = `${settings.showClock}|${settings.counterFlipSeconds}|${settings.daysLiveStartDate}`;
    if (signature === counterSignature) return;
    counterSignature = signature;
    clearInterval(counterTimer);
    counterCube.classList.remove('show-days');
    if (!settings.showClock) return;
    counterTimer = setInterval(() => {
      counterCube.classList.toggle('show-days');
    }, Math.max(2, Number(settings.counterFlipSeconds) || 4) * 1000);
  }

  setInterval(() => {
    updateClock();
    updateDaysLive();
  }, 1000);
  connect();
})();
