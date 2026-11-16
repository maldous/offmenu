// Keep provider results in the fragment, never in a query string or outgoing request.
export function routeIdentityReturn(location = globalThis.location) {
  if (!location) return false;
  const url = new URL(location.href);
  if (url.pathname === '/auth.html' || !url.hash) return false;
  const fragment = new URLSearchParams(url.hash.slice(1));
  if (!['access_token', 'confirmation_token', 'email_change_token', 'error', 'error_description']
      .some(key => fragment.has(key))) return false;
  location.replace('/auth.html' + url.hash);
  return true;
}
if (typeof window !== 'undefined') routeIdentityReturn();
