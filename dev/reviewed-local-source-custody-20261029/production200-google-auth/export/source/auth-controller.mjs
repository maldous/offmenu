// Existing auth-page controller with bounded operations and strict callback qualification.
// No credentials, token values, provider endpoints or account roles are stored here.
export function readAuthCallbackFlags(location = globalThis.location) {
  const fragment = new URLSearchParams(location?.hash?.slice(1) || '');
  return {oauth: fragment.has('access_token'), error: fragment.has('error') || fragment.has('error_description')};
}
export function createAuthPageController({configuration, identityFor, verifySession, navigate, onState = () => {},
  callbackState = readAuthCallbackFlags, expectedOrigin = globalThis.location?.origin, timeoutMs = 15000}) {
  let identity, config, state = 'initial', busy = false, providers = [], signupAvailable = false;
  const emit = (next, message = '') => {
    state = next;
    onState({state, message, synthetic: config?.synthetic === true, providers: [...providers],
      oauthReady: config?.identityTransport === 'real' && config?.oauthAvailable === true, signupAvailable});
  };
  const failed = () => emit('ready', 'Sign-in could not be confirmed. Your kitchen has not changed.');
  function operation() {
    const deadline = Date.now() + timeoutMs;
    return async (call) => {
      const remaining = deadline - Date.now();
      if (remaining <= 0) throw Error('Authentication operation timed out.');
      let timer;
      try {
        return await Promise.race([Promise.resolve().then(call), new Promise((_, reject) => {
          timer = setTimeout(() => reject(Error('Authentication operation timed out.')), remaining);
        })]);
      } finally { clearTimeout(timer); }
    };
  }
  async function verified(user, run) {
    if (!user || typeof user.id !== 'string' || !user.id.trim()) return false;
    const session = await run(verifySession);
    return session?.authenticated === true && session.userId === user.id && session.mode === config.mode;
  }
  async function start() {
    if (state !== 'initial') return;
    emit('loading');
    const run = operation();
    try {
      config = await run(configuration);
      if (config?.schema !== 'offmenu-auth-page/1' || !['netlify', 'better-auth'].includes(config.mode) ||
          config.nextPath !== '/shelf-scanner.html' || (expectedOrigin && config.origin !== expectedOrigin)) throw Error('configuration');
      identity = await run(() => identityFor(config.mode));
      const flags = callbackState();
      if (flags.error) throw Error('Provider refused callback.');
      if (flags.oauth && (config.mode !== 'netlify' || config.identityTransport !== 'real' || config.oauthAvailable !== true))
        throw Error('OAuth callback is not configured.');
      const callback = await run(() => identity.handleAuthCallback());
      if (callback?.type && !['oauth', 'confirmation', 'email_change'].includes(callback.type)) {
        emit('unavailable', 'Use the existing account page for this account action.'); return;
      }
      const settings = await run(() => identity.getSettings());
      signupAvailable = config.mode === 'netlify' && settings?.disableSignup === false &&
        settings?.providers?.email === true && typeof identity.signup === 'function';
      providers = config.mode === 'netlify' ? ['google', 'github', 'gitlab', 'bitbucket', 'facebook']
        .filter(provider => settings?.providers?.[provider] === true) : [];
      const user = await run(() => identity.getUser());
      // An OAuth callback cannot silently become a different recovered account.
      if (flags.oauth || callback?.type === 'oauth') {
        if (callback?.type !== 'oauth' || !callback.user?.id || callback.user.id !== user?.id ||
            config.identityTransport !== 'real' || config.oauthAvailable !== true || !(await verified(user, run)))
          throw Error('OAuth callback could not be confirmed.');
        emit('signed-in', 'Signed in.'); return;
      }
      if (await verified(user, run)) { emit('signed-in', 'Signed in.'); return; }
      if (config.emailSignIn === 'not-configured') {
        emit('unavailable', 'Email sign-in is not configured for this environment.'); return;
      }
      emit('ready');
    } catch { emit('unavailable', 'Sign-in setup or provider return could not be confirmed. Please reload sign-in to try again.'); }
  }
  async function providerSignIn(provider) {
    if (busy || state !== 'ready' || config.identityTransport !== 'real' || config.oauthAvailable !== true ||
        !providers.includes(provider)) return false;
    busy = true; emit('redirecting', 'Opening your sign-in provider…');
    try { await operation()(() => identity.oauthLogin(provider)); failed(); return false; }
    catch (error) {
      // The unchanged official SDK throws this sentinel after assigning the existing provider URL.
      if (error?.name === 'AuthError' && error.message === 'Redirecting to OAuth provider') return true;
      failed(); return false;
    } finally { busy = false; }
  }
  async function signIn(email, password) {
    if (busy || state !== 'ready') return false;
    if (typeof email !== 'string' || !email.trim() || typeof password !== 'string' || !password) {
      emit('ready', 'Enter your email and password.'); return false;
    }
    busy = true; emit('signing-in'); const run = operation();
    try {
      const user = await run(() => identity.login(email.trim(), password));
      if (await verified(user, run)) { emit('signed-in', 'Signed in.'); return true; }
      failed(); return false;
    } catch { failed(); return false; } finally { busy = false; password = ''; }
  }
  async function continueTo(path) {
    if (busy || state !== 'signed-in') return false;
    busy = true; const run = operation();
    try {
      if (await verified(await run(() => identity.getUser()), run)) { navigate(path); return true; }
      failed(); return false;
    } catch { failed(); return false; } finally { busy = false; }
  }
  async function signUp(email, password) {
    if (busy || state !== 'ready' || !signupAvailable) return false;
    if (typeof email !== 'string' || !email.trim() || typeof password !== 'string' || !password) {
      emit('ready', 'Enter your email and password.'); return false;
    }
    busy = true; emit('creating-account'); const run = operation();
    try {
      const created = await run(() => identity.signup(email.trim(), password));
      const user = await run(() => identity.getUser());
      if (created?.id && user?.id === created.id && await verified(user, run)) emit('signed-in', 'Signed in.');
      else emit('ready', 'Check your email to confirm your account, then sign in.');
      return true;
    } catch { emit('ready', 'Account creation could not be confirmed. Check your details or sign in to your existing account.'); return false; }
    finally { busy = false; password = ''; }
  }
  async function signOut() {
    if (busy || !identity) return false;
    busy = true; const run = operation();
    try {
      await run(() => identity.logout());
      if ((await run(verifySession))?.authenticated === true) throw Error('session-remains');
      emit('ready', 'Signed out.'); return true;
    } catch { emit('unavailable', 'Sign-out could not be confirmed.'); return false; } finally { busy = false; }
  }
  return Object.freeze({start, signIn, signUp, providerSignIn,
    continueToScanner: () => continueTo('/shelf-scanner.html'), continueToKitchen: () => continueTo('/kitchen.html'),
    signOut, getState: () => state});
}
