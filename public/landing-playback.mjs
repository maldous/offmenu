// Navigation waits for an actual clip completion. The three-second dwell starts
// only after the matching clip finishes, never when a chapter is selected.
export function createLandingPlayback({stageCount, onStage, onAdvance, setTimer = setTimeout, clearTimer = clearTimeout}) {
  let index = 0;
  let token = 0;
  let timer = null;
  let completed = false;
  let interrupted = false;
  let paused = false;
  let reducedMotion = false;

  function cancelPending() {
    if (timer !== null) clearTimer(timer);
    timer = null;
  }

  function queueNext() {
    cancelPending();
    if (!completed || interrupted || paused || reducedMotion || index >= stageCount - 1) return;
    const expectedIndex = index;
    const expectedToken = token;
    timer = setTimer(() => {
      timer = null;
      if (index === expectedIndex && token === expectedToken && !interrupted && !paused && !reducedMotion) {
        onAdvance(index + 1, expectedToken);
      }
    }, 3000);
  }

  function select(nextIndex, {force = false} = {}) {
    if (!Number.isInteger(nextIndex) || nextIndex < 0 || nextIndex >= stageCount) return null;
    if (nextIndex === index && token && !force) return token;
    cancelPending();
    index = nextIndex;
    token += 1;
    completed = false;
    interrupted = false;
    onStage(index, token);
    return token;
  }

  function finish(finishedIndex, finishedToken) {
    if (finishedIndex !== index || finishedToken !== token || completed) return false;
    completed = true;
    queueNext();
    return true;
  }

  return {
    select,
    finish,
    interrupt() { interrupted = true; cancelPending(); },
    setPaused(value) { paused = Boolean(value); if (paused) cancelPending(); else queueNext(); },
    setReducedMotion(value) { reducedMotion = Boolean(value); if (reducedMotion) cancelPending(); else queueNext(); },
    dispose() { cancelPending(); },
    get state() { return {index, token, completed, paused, reducedMotion, pending: timer !== null}; }
  };
}
