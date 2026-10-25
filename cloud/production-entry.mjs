import {createOffMenuHandler} from './generated.mjs';

// The existing deployment owns these choices. Requests and admin settings do not.
const application = createOffMenuHandler({
  authPageOptions: {identityTransport: 'real', oauthCallbackReady: false},
});
// Bind only a verified OffMenu publication. A client cannot select live fallback.
const selectedPublicRelease = null;

export default {
  async fetch(request, env, ctx) {
    if ((env.OFFMENU_AUTH_MODE !== undefined && env.OFFMENU_AUTH_MODE !== 'netlify') ||
        env.DEV_COMPOSITION || env.OFFMENU_LOCAL_LAB) {
      return Response.json({error: 'Authentication is unavailable.'},
        {status: 503, headers: {'Cache-Control': 'no-store'}});
    }
    const url = new URL(request.url);
    if (url.pathname === '/api/product' || url.pathname === '/api/prices') {
      return Response.json({error: 'Product information is unavailable.'},
        {status: 503, headers: {'Cache-Control': 'no-store'}});
    }
    if (url.pathname === '/api/data/public' &&
        (!selectedPublicRelease ||
         url.searchParams.get('releaseId') !== selectedPublicRelease.releaseId ||
         url.searchParams.get('manifestSha256') !== selectedPublicRelease.manifestSha256)) {
      return Response.json({error: 'Product information is unavailable.'},
        {status: 503, headers: {'Cache-Control': 'no-store'}});
    }
    if (url.pathname.startsWith('/__dev/') || url.pathname.startsWith('/api/dev-auth')) {
      return new Response('Not found', {status: 404, headers: {'Cache-Control': 'no-store'}});
    }
    if (['GET', 'HEAD'].includes(request.method)) {
      if (url.pathname === '/' || url.pathname === '/index.html') {
        url.pathname = '/landing.html';
        return application.fetch(new Request(url, request), env, ctx);
      }
      if (url.pathname === '/kitchen.html') {
        url.pathname = '/';
        return application.fetch(new Request(url, request), env, ctx);
      }
    }
    return application.fetch(request, env, ctx);
  },
  scheduled(event, env, ctx) {
    return application.scheduled(event, env, ctx);
  },
};
