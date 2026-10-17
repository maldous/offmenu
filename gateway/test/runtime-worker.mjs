// Miniflare dispatchFetch rewrites the URL but retains its loopback Host header.
// Cloudflare custom-domain requests carry the public Host. Model that at the test ingress.
import worker from '../dist/index.js';
export { BridgeQueue } from '../dist/index.js';
export default {fetch(request,env,ctx){const headers=new Headers(request.headers);headers.set('Host',new URL(request.url).host);return worker.fetch(new Request(request,{headers}),env,ctx);}};
