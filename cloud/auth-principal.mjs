/** Translate only a server-verified Better Auth user. Never call on browser input. */
export function toOffMenuPrincipal(user) {
  if (!user || typeof user.id !== 'string' || !user.id.trim() || user.id.length >= 200) return null;
  let roles = [];
  try {
    const parsed = JSON.parse(user.appRoles ?? '[]');
    if (Array.isArray(parsed) && parsed.every(role => typeof role === 'string')) roles = [...new Set(parsed)];
  } catch { /* Invalid trusted-role storage denies roles; it never grants one. */ }
  return Object.freeze({
    // Exact opaque ID preserves ownership, local keys, vault AAD and audit history.
    id: user.id,
    name: typeof user.name === 'string' ? user.name : null,
    email: typeof user.email === 'string' ? user.email : null,
    emailVerified: user.emailVerified === true,
    app_metadata: Object.freeze({roles: Object.freeze(roles)}),
  });
}

/**
 * Adapter for existing route dependency injection. Storage/auth errors propagate
 * so the dispatcher can report an outage rather than pretend the user signed out.
 * No bearer bridge, caller-supplied ID, Netlify fallback or session-token exposure.
 */
export async function getOffMenuPrincipal(auth, request) {
  const result = await auth.api.getSession({
    headers: request.headers,
    query: {disableCookieCache: true, disableRefresh: true},
  });
  if (!result || result.session?.userId !== result.user?.id) return null;
  return toOffMenuPrincipal(result.user);
}
