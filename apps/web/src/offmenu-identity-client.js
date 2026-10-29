// Browser adapter candidate. A deployment-owned, fixed mode must select Better Auth;
// the default is the unchanged Netlify Identity client. This file does not mount auth.
export function createOffMenuIdentityClient({mode = 'netlify', netlify, request = globalThis.fetch} = {}) {
  if (mode === 'netlify') {
    if (!netlify || typeof netlify.getUser !== 'function' || typeof netlify.refreshSession !== 'function')
      throw new TypeError('The existing Netlify Identity client is required.');
    return netlify;
  }
  if (mode !== 'better-auth') throw new TypeError('Unsupported authentication mode.');
  if (typeof request !== 'function') throw new TypeError('A same-origin request function is required.');

  const unsupported = () => { throw Object.assign(new Error('This account action is not available in the selected authentication mode.'),
    {code: 'AUTH_FLOW_NOT_CONFIGURED'}); };
  async function call(endpoint, body) {
    const response = await request('/api/auth/' + endpoint, {
      method: body === undefined ? 'GET' : 'POST',
      cache: 'no-store', credentials: 'same-origin', redirect: 'manual',
      headers: body === undefined ? {Accept: 'application/json'} :
        {Accept: 'application/json', 'Content-Type': 'application/json'},
      ...(body === undefined ? {} : {body: JSON.stringify(body)}),
      signal: AbortSignal.timeout(15000),
    });
    if (!response || response.redirected || response.status >= 300 && response.status < 400 ||
        !response.headers?.get('content-type')?.includes('application/json'))
      throw Error('Authentication response unavailable.');
    let data;
    try { data = await response.json(); } catch { throw Error('Authentication response unavailable.'); }
    if (!response.ok || data?.error) throw Error('Authentication request failed. Your local kitchen is unchanged.');
    return data;
  }
  async function getUser() {
    const data = await call('get-session');
    if (data === null) return null;
    const id = data?.user?.id;
    if (typeof id !== 'string' || !id.trim() || id.length >= 200 ||
        data?.session?.userId !== id) throw Error('Authentication session unavailable.');
    // The ID is opaque and unchanged. Browser role claims never grant authorization.
    return Object.freeze({id,
      name: typeof data.user.name === 'string' ? data.user.name : null,
      email: typeof data.user.email === 'string' ? data.user.email : null,
      emailVerified: data.user.emailVerified === true});
  }
  async function login(email, password) {
    if (typeof email !== 'string' || !email || typeof password !== 'string' || !password)
      throw TypeError('Email and password are required.');
    await call('sign-in/email', {email, password});
    const user = await getUser();
    if (!user) throw Error('Authentication session unavailable.');
    return user;
  }
  async function logout() {
    await call('sign-out', {});
    if (await getUser()) throw Error('Authentication session remains active.');
  }
  return Object.freeze({
    // Conservative client capabilities; a provider/configuration contract is still pending.
    getSettings: async () => ({disableSignup: true, providers: {}}),
    getUser, login, logout,
    // Session expiry and renewal are server policy. No bearer token or cookie is read.
    refreshSession: async () => { await getUser(); },
    handleAuthCallback: async () => null,
    signup: unsupported, oauthLogin: unsupported,
    requestPasswordRecovery: unsupported, updateUser: unsupported,
    acceptInvite: unsupported,
  });
}
