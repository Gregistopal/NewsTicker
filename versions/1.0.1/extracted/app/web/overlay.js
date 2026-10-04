(() => {
  'use strict';

  const stage = document.getElementById('stage');
  const breakingLabel = document.getElementById('breakingLabel');
  const kicker = document.getElementById('kicker');
  const clock = document.getElementById('clock');
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
  let activeHideAt = 0;

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
    kicker.textContent = next.kickerText;
    kicker.classList.toggle('is-hidden', !next.showKicker);
    clock.classList.toggle('is-hidden', !next.showClock);
    stage.classList.toggle('uppercase-message', next.uppercaseMessage);
    stage.classList.toggle('shine', next.shineEnabled);
    stage.classList.remove('mode-headline');
    stage.classList.add('mode-crawl');
    if (preview && !activeId) showPreview();
    updateClock();
  }

  function resetCrawl() {
    message.style.animation = 'none';
    void message.offsetWidth;
    message.style.animation = '';
    if (!settings) return;
    const width = messageWindow.clientWidth;
    const textWidth = Math.ceil(message.scrollWidth);
    const distance = width + textWidth + 50;
    const duration = Math.max(3, distance / settings.crawlSpeed);
    message.style.setProperty('--crawl-start', `${width + 24}px`);
    message.style.setProperty('--crawl-end', `${-textWidth - 24}px`);
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
    activeHideAt = active.hideAt || 0;
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
    activeHideAt = 0;
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
    const socket = new WebSocket(`${protocol}//${location.host}/ws`);
    socket.addEventListener('message', event => {
      try { receive(JSON.parse(event.data)); } catch (_) { /* ignore malformed packets */ }
    });
    socket.addEventListener('close', () => setTimeout(connect, 1200));
  }

  message.addEventListener('animationend', event => {
    if (event.animationName !== 'ticker-crawl' || !activeId || sequence.length < 2) return;
    if (activeHideAt && Date.now() + serverOffset >= activeHideAt - 250) return;
    sequenceIndex = (sequenceIndex + 1) % sequence.length;
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

  setInterval(updateClock, 1000);
  connect();
})();
