import {createOffMenuAuth, OFFMENU_AUTH_BASE_PATH} from './auth.mjs';
import {getOffMenuPrincipal} from './auth-principal.mjs';

/** Deployment-owned selection only. Missing setting preserves Netlify. */
export function offMenuAuthMode(env) {
  const mode = env?.OFFMENU_AUTH_MODE;
  if (mode === undefined || mode === 'netlify') return 'netlify';
  if (mode === 'better-auth') return mode;
  throw new TypeError('Unsupported OffMenu authentication mode.');
}

const within = (path, base) => path === base || path.startsWith(base + '/');

/**
 * Dispatcher adapter. Do not pass request-derived
 * options or mutable administrative settings. Legacy verification is provided
 * by the dispatcher, and is never attempted after a Better Auth failure.
 */
export function createOffMenuAuthRuntime(env, {legacyVerifiedUser, authOptions} = {}) {
  const mode = offMenuAuthMode(env);
  if (mode === 'netlify') {
    if (typeof legacyVerifiedUser !== 'function') throw new TypeError('Legacy authentication verifier is required.');
    return Object.freeze({mode, verifiedUser: legacyVerifiedUser, handleAuthRequest: async () => null});
  }
  const auth = createOffMenuAuth(env, authOptions);
  return Object.freeze({
    mode,
    verifiedUser: request => getOffMenuPrincipal(auth, request),
    async handleAuthRequest(request) {
      const path = new URL(request.url).pathname;
      if (within(path, '/.netlify/identity')) {
        // The dispatcher mounts this guard before the legacy proxy: no mixed identity mode.
        return Response.json({error: 'Legacy authentication is not available in this authentication mode.'},
          {status: 410, headers: {'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'}});
      }
      if (!within(path, OFFMENU_AUTH_BASE_PATH)) return null;
      let response;
      try {response = await auth.handler(request);}
      catch {
        return Response.json({error: 'Authentication is temporarily unavailable.'},
          {status: 503, headers: {'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'}});
      }
      // Clone the response without flattening Set-Cookie or rewriting redirects.
      const result = new Response(response.body, response);
      result.headers.set('Cache-Control', 'no-store');
      result.headers.set('X-Content-Type-Options', 'nosniff');
      return result;
    },
  });
}
