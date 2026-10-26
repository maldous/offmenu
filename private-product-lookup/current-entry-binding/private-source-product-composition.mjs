// Existing05 worker entry composition, SAME actual identityApp and verifiedUser.
import {createPrivateSourceProductRoutes} from '../private-source-product-route.mjs';
export function createPrivateSourceProductComposition({identityApp,options}={}){
  if(typeof identityApp?.fetch!=='function')throw Error('EXISTING_IDENTITY_APP_REQUIRED');
  const routes=createPrivateSourceProductRoutes(options);
  return Object.freeze({async handle(request,env,ctx){
    const runtime={mode:'netlify',async verifiedUser(originalRequest){
      // This exact existing endpoint delegates to identityApp's real auth runtime.
      // Same request subject; no extraction, persistence, forwarding to reader,
      // credential submission or new identity/ACL implementation.
      const url=new URL('/api/auth-page/session',originalRequest.url);
      const result=await identityApp.fetch(new Request(url,{method:'GET',headers:originalRequest.headers,
        signal:originalRequest.signal}),env,ctx);
      if(result.status===401)return null;
      if(!result.ok||!result.headers.get('Content-Type')?.includes('application/json'))throw Error('AUTH_SESSION_UNAVAILABLE');
      // Existing selected endpoint emits a tiny fixed DTO, never a source body.
      const text=await result.text();if(text.length>4096)throw Error('AUTH_SESSION_UNAVAILABLE');
      const proof=JSON.parse(text);
      if(proof.authenticated!==true||proof.mode!=='netlify'||typeof proof.userId!=='string'||!proof.userId||proof.userId.length>=200)
        throw Error('AUTH_SESSION_UNAVAILABLE');
      return {id:proof.userId};
    }};
    return routes(request,env,{runtime});
  }});
}
