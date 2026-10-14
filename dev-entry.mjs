import app from './dist/worker.mjs';
export default {
  async fetch(request, env, ctx) {
    if (new URL(request.url).pathname === '/__dev/status') {
      return Response.json({mode:'isolated-development', interactive:!!env.DEV_INTERACTIVE, qualifiedContext:env.DEV_QUALIFIED_CONTEXT||null, blockedFeatures:JSON.parse(env.DEV_BLOCKED_FEATURES||'null'), owner:'worker-05', freshState:true, ownerThread:env.DEV_OWNER_THREAD, runId:env.DEV_RUN_ID, sourceCommit:env.DEV_SOURCE_COMMIT, stateId:env.DEV_STATE_ID, developmentCompatibilityDate:'2026-08-06', productionCompatibilityDate:'2026-10-12', database:'local synthetic D1', composition:env.DEV_COMPOSITION||'deny-all', compositionSha256:env.DEV_COMPOSITION_SHA256||null, applicationCommit:env.DEV_APP_COMMIT, applicationArtifact:JSON.parse(env.DEV_APPLICATION_ARTIFACT||'null'), applicationArtifactSha256:env.DEV_APPLICATION_ARTIFACT_SHA256||null, authorPins:JSON.parse(env.DEV_AUTHOR_PINS||'null'), pins:JSON.parse(env.DEV_AUTHOR_PINS||'null'), outbound:env.DEV_COMPOSITION==='pinned-synthetic'?'qualified synthetic WireMock; no live fallback':'deny-all pending owner WireMock artifacts', authentication:env.DEV_COMPOSITION==='pinned-synthetic'?'contracted synthetic Identity; Google OAuth blocked':'unavailable pending Google IDP and WireMock contracts', productionCredentials:false});
    }
    const response = await app.fetch(request, env, ctx);
    const headers = new Headers(response.headers);
    headers.set('Cache-Control', 'no-store');
    headers.set('Content-Security-Policy', "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; media-src 'self' blob:; connect-src 'self'; worker-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'");
    headers.set('X-OffMenu-Development', 'isolated-no-live-outbound');
    if (headers.get('Content-Type')?.includes('text/html')) {
      let html = await response.text();
      const banner=env.DEV_INTERACTIVE?'Private development preview · shared synthetic fixtures only · sign in as alice@example.test, bob@example.test or admin@example.test with fixture-password. Real Google/provider/device/corpus flows remain blocked; independent acceptance pending.':'Development preview · synthetic local data · live services blocked · sign-in and external lookups awaiting mock integration.';
      html = html.replace(/<body([^>]*)>/i, '<body$1><aside role="status" style="padding:10px;background:#fff3cd;color:#332701;font:16px system-ui">'+banner+' <a href="/__dev/status">Environment details</a></aside>');
      return new Response(html, {status:response.status, headers});
    }
    return new Response(response.body, {status:response.status, headers});
  }
};
