import {guardGoogleReturn} from './google-return-guard.js';
// Explicit selected capability, not a generic multi-provider OAuth adapter.
// Realm settings can describe other providers without qualifying this app path.
export function withGoogleReturnGuard(netlify){
  return Object.freeze({...netlify,supportedOAuthProviders:Object.freeze(['google']),
    oauthLogin(provider){
      if(provider!=='google')throw Object.assign(new Error('This provider is not available in the selected app.'),{code:'AUTH_PROVIDER_NOT_CONFIGURED'});
      return netlify.oauthLogin(provider);
    },
    async handleAuthCallback(){
      // Ambiguous/missing Google correlation ALWAYS fails closed. No provider
      // query/fragment claim can choose an unguarded fallback to the SDK.
      await guardGoogleReturn();
      return netlify.handleAuthCallback();
    }});
}
