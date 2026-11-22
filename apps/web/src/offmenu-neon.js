// Controller for the retained, source-derived OffMenu neon SVG. No page gate.
export function createNeonController(sign, {
  pauseButton, replayButton, status, materialTimeout = 5000, translate = text => text,
  document: doc = sign.ownerDocument, window: win = doc.defaultView,
} = {}) {
  if (sign.dataset.neonMounted) throw new Error('Neon already mounted');
  const circuits = [...sign.querySelectorAll('.circuit')];
  const description = sign.querySelector('desc');
  const movingDescription = description?.textContent;
  if (!circuits.length) throw new Error('Neon circuits are missing');
  sign.dataset.neonMounted = 'true';
  const motion = win.matchMedia('(prefers-reduced-motion: reduce)');
  let lastReducedMotion = motion.matches;
  const cleanups = [];
  let disposed = false, ready = false, manualPause = false, visible = true;
  let generation = 0, builtGeneration = -1, cycles = 0, frame = 0, assetTimer;
  let resolveReady;
  const whenReady = new Promise(resolve => { resolveReady = resolve; });
  const emit = (name, detail = {}) => sign.dispatchEvent(new win.CustomEvent('offmenu:' + name, {
    bubbles: true, composed: true, detail: {...detail, generation},
  }));
  function listen(target, event, callback) {
    target?.addEventListener(event, callback);
    cleanups.push(() => target?.removeEventListener(event, callback));
  }
  function describe(text) { if (status) status.textContent = translate(text); }
  function syncDescription() {
    if (description) description.textContent = sign.dataset.neonPhase === 'still'
      ? translate('OffMenu neon sign, shown without movement.') : movingDescription;
  }
  function syncControls() {
    if (pauseButton) pauseButton.disabled = motion.matches || !ready || sign.dataset.neonMaterial === 'failed';
    if (replayButton) replayButton.disabled = motion.matches || !ready
      || sign.dataset.neonMaterial === 'failed' || ['ready', 'starting'].includes(sign.dataset.neonPhase);
  }
  function syncRun() {
    const paused = manualPause || !visible || doc.hidden;
    sign.dataset.neonRun = paused ? 'paused' : 'running';
    if (pauseButton) {
      pauseButton.setAttribute('aria-pressed', String(manualPause));
      pauseButton.setAttribute('aria-label', translate('Pause neon animation'));
    }
  }
  function complete() {
    if (disposed || builtGeneration === generation) return;
    builtGeneration = generation;
    sign.dataset.neonPhase = motion.matches ? 'still' : 'steaming';
    syncDescription();
    syncControls();
    emit('built', {reducedMotion: motion.matches, material: sign.dataset.neonMaterial});
  }
  function start() {
    if (disposed || !ready) return;
    generation++; cycles = 0; builtGeneration = -1;
    win.cancelAnimationFrame(frame);
    sign.dataset.neonPhase = 'ready';
    circuits.forEach(circuit => circuit.classList.remove('ready'));
    syncRun();
    if (motion.matches || sign.dataset.neonMaterial === 'failed') {
      sign.dataset.neonPhase = 'still';
      syncDescription();
      builtGeneration = generation;
      syncControls();
      emit('built', {reducedMotion: motion.matches, material: sign.dataset.neonMaterial});
      return;
    }
    const token = generation;
    // Separate cancellation and restart into rendered states; never queue replays.
    frame = win.requestAnimationFrame(() => {
      frame = win.requestAnimationFrame(() => {
        if (!disposed && token === generation) sign.dataset.neonPhase = 'starting';
        if (!disposed && token === generation
          && !win.getComputedStyle(circuits[0]).animationName.split(',').some(name => name.trim() === 'offmenu-neon-energize')) {
          sign.dataset.neonPhase = 'still'; syncDescription(); builtGeneration = generation; syncControls();
          emit('built', {reducedMotion: false, material: sign.dataset.neonMaterial, motion: 'unsupported'});
        }
      });
    });
    syncControls();
  }
  function setPaused(value) {
    manualPause = Boolean(value); syncRun();
    describe(manualPause ? 'Neon animation paused.' : 'Neon animation resumed.');
  }
  function setVisible(value) { visible = Boolean(value); syncRun(); }
  function replay() {
    if (disposed || !ready || motion.matches || sign.dataset.neonMaterial === 'failed'
      || ['ready', 'starting'].includes(sign.dataset.neonPhase)) return false;
    // Replay is not permission to undo a deliberate quiet/pause choice.
    start(); emit('interaction', {action: 'replay'});
    describe('Neon animation restarted.');
    return true;
  }
  listen(pauseButton, 'click', () => { setPaused(!manualPause); emit('interaction', {action: manualPause ? 'pause' : 'resume'}); });
  listen(replayButton, 'click', replay);
  listen(sign, 'animationend', event => {
    if (disposed || motion.matches || sign.dataset.neonPhase !== 'starting'
      || event.animationName !== 'offmenu-neon-energize' || !circuits.includes(event.target)) return;
    event.target.classList.add('ready');
    if (circuits.every(circuit => circuit.classList.contains('ready'))) complete();
  });
  listen(sign, 'animationiteration', event => {
    if (event.animationName === 'offmenu-neon-rise' && event.target.dataset.master === 'true'
      && sign.dataset.neonRun === 'running' && sign.dataset.neonPhase === 'steaming') {
      emit('cycle', {cycle: ++cycles});
    }
  });
  listen(doc, 'visibilitychange', () => { refreshPreference(); syncRun(); });
  const preferenceChanged = () => {
    lastReducedMotion = motion.matches;
    if (motion.matches) describe('Reduced motion: the neon sign is still.');
    else if (sign.dataset.neonMaterial !== 'failed') describe('');
    start(); // Manual pause remains independent of system preference changes.
  };
  function refreshPreference() {
    if (motion.matches !== lastReducedMotion) preferenceChanged();
  }
  // Reconcile a missed/coalesced media notification when the user returns or
  // interacts. No polling loop, stored preference rewrite, or forced resume.
  listen(win, 'focus', refreshPreference);
  listen(win, 'pageshow', refreshPreference);
  listen(doc, 'pointerover', refreshPreference);
  listen(doc, 'keydown', refreshPreference);
  // CSS reduced-motion takes effect immediately even when a browser coalesces
  // its MediaQueryList notification. Reconcile semantic state on cancellation.
  listen(sign, 'animationcancel', refreshPreference);
  if (motion.addEventListener) listen(motion, 'change', preferenceChanged);
  else {
    motion.addListener(preferenceChanged);
    cleanups.push(() => motion.removeListener(preferenceChanged));
  }
  if (win.IntersectionObserver) {
    const observer = new win.IntersectionObserver(entries => {
      for (const entry of entries) if (entry.target === sign) setVisible(entry.isIntersecting);
    });
    observer.observe(sign); cleanups.push(() => observer.disconnect());
  }
  sign.dataset.neonPhase = 'loading'; syncRun();
  syncControls();
  const material = sign.querySelector('image[id$="glass-atlas"]');
  const image = new win.Image();
  let settled = false;
  function assetSettled(ok) {
    if (disposed || settled) return;
    settled = true; win.clearTimeout(assetTimer); image.onload = image.onerror = null;
    sign.dataset.neonMaterial = ok ? 'ready' : 'failed'; ready = true;
    if (!ok) {
      describe('The neon sign is shown without animation.');
      emit('error', {code: 'NEON_MATERIAL_UNAVAILABLE', fallback: 'retained-vector'});
    }
    // A failed or bounded-out material gets the actual retained vector shapes.
    preferenceChanged(); resolveReady({material: sign.dataset.neonMaterial});
  }
  assetTimer = win.setTimeout(() => assetSettled(false), materialTimeout);
  image.onload = () => {
    if (image.decode) image.decode().then(() => assetSettled(true), () => assetSettled(false));
    else assetSettled(true);
  };
  image.onerror = () => assetSettled(false);
  const materialHref = material?.getAttribute('href');
  if (materialHref) image.src = materialHref;
  else assetSettled(false);
  return {
    ready: whenReady, replay, setPaused, setVisible,
    getState: () => ({phase: sign.dataset.neonPhase, material: sign.dataset.neonMaterial,
      paused: sign.dataset.neonRun === 'paused', manualPause, visible,
      reducedMotion: motion.matches, generation, cycles, disposed}),
    dispose() {
      if (disposed) return;
      disposed = true; generation++; win.cancelAnimationFrame(frame); win.clearTimeout(assetTimer);
      image.onload = image.onerror = null;
      cleanups.splice(0).forEach(cleanup => cleanup());
      sign.dataset.neonPhase = 'still'; sign.dataset.neonRun = 'paused';
      syncDescription();
      delete sign.dataset.neonMounted;
      if (pauseButton) pauseButton.disabled = true;
      if (replayButton) replayButton.disabled = true;
      resolveReady({material: sign.dataset.neonMaterial || 'cancelled'});
    },
  };
}

let neonInstance = 0;
// Returns immediately. Only this component's ready promise waits for its asset;
// callers must not use it as a page/navigation/scroll readiness barrier.
export function mountNeonHost(host, options = {}) {
  if (host.dataset.neonHostMounted) throw new Error('Neon host already mounted');
  host.dataset.neonHostMounted = 'true';
  const doc = host.ownerDocument, win = doc.defaultView, abort = new win.AbortController();
  const fallback = doc.createElement('span');
  fallback.textContent = 'OffMenu'; host.append(fallback);
  let controller = null, imported = null, disposed = false;
  if (options.pauseButton) options.pauseButton.disabled = true;
  if (options.replayButton) options.replayButton.disabled = true;
  const ready = (async () => {
    try {
      const response = await win.fetch('/offmenu-neon.svg', {signal: abort.signal, credentials: 'same-origin'});
      if (!response.ok) throw new Error('Neon asset unavailable');
      const text = await response.text();
      if (disposed) return {material: 'cancelled'};
      const svg = new win.DOMParser().parseFromString(text, 'image/svg+xml').documentElement;
      // This is a curated same-origin brand asset, never user-supplied HTML.
      if (svg.localName !== 'svg' || svg.querySelector('parsererror,script,foreignObject')
        || !svg.hasAttribute('data-offmenu-neon')) throw new Error('Invalid neon asset');
      for (const node of [svg, ...svg.querySelectorAll('*')]) for (const attribute of node.attributes) {
        if (/^on/i.test(attribute.name)) throw new Error('Unexpected neon event attribute');
        if (attribute.localName === 'href' && !attribute.value.startsWith('#')
          && attribute.value !== '/offmenu-neon-material.jpg') throw new Error('Unexpected neon asset reference');
      }
      const prefix = 'offmenu-neon-' + (++neonInstance) + '-';
      const ids = new Map([...svg.querySelectorAll('[id]'), svg].filter(n => n.id).map(n => [n.id, prefix + n.id]));
      for (const node of [svg, ...svg.querySelectorAll('*')]) {
        if (node.getAttribute('href') === '#glass-atlas') node.classList.add('neon-material');
        for (const attribute of [...node.attributes]) {
          let value = attribute.value;
          if (attribute.name === 'id') value = ids.get(value) || value;
          else if (attribute.name === 'aria-labelledby') value = value.split(' ').map(id => ids.get(id) || id).join(' ');
          else if (value.startsWith('#')) value = '#' + (ids.get(value.slice(1)) || value.slice(1));
          else value = value.replace(/url\(#([^)]*)\)/g, (all, id) => ids.has(id) ? 'url(#' + ids.get(id) + ')' : all);
          node.setAttribute(attribute.name, value);
        }
      }
      imported = doc.importNode(svg, true); fallback.replaceWith(imported);
      controller = createNeonController(imported, options);
      return controller.ready;
    } catch (error) {
      if (disposed || error.name === 'AbortError') return {material: 'cancelled'};
      host.dataset.neonFallback = 'true';
      host.dispatchEvent(new win.CustomEvent('offmenu:error', {bubbles: true, composed: true,
        detail: {code: 'NEON_ASSET_UNAVAILABLE', fallback: 'brand-text'}}));
      return {material: 'unavailable'};
    }
  })();
  return {
    ready,
    getState: () => controller?.getState() || {phase: disposed ? 'disposed' : host.dataset.neonFallback ? 'still' : 'loading'},
    setPaused: value => controller?.setPaused(value),
    replay: () => controller?.replay() || false,
    dispose() { disposed = true; abort.abort(); controller?.dispose(); imported?.remove(); fallback.remove(); delete host.dataset.neonHostMounted; },
  };
}
