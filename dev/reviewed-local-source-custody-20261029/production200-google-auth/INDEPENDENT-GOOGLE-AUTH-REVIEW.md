# Independent existing-provider auth source review — 2026-10-28 22:31 UTC

Approved candidate asset pins:
- auth.js `e17aecb376d5483fe7afc8f3c505ebb19bf6f41b03415b521b6d0ca2efd9583f`
- auth.html `0f4af61bea945c8945c34f055bdfde8d878dbe75bee397ee4ba47e1317fd787a`
- auth-return-bridge.js `24256faa5f5c5b527bd15fedcb28fd4c5195b7c19c879a43d1332eaa0d9e42c7`

Twelve focused tests independently pass, including actual supplied bundled SDK with synthetic callback/settings/session responses. First26167 SDK bytes independently match baseline exactly. Existing synchronous SDK provider route remains loginExternalUrl(provider); no new scope/client/credential introduced.

Controller checks configuration schema/origin, callback/current/server user identity equality and mode before OAuth acceptance; every continuation re-verifies and uses fixed local scanner/kitchen paths. Error callback fails closed. Bridge moves only supported fragments to fixed /auth.html without moving fragment contents into query or network request. Email/signup/signout and provider consent gates remain separate. Total operation deadline refuses controller acceptance after timeout; SDK-internal work is not canceled. Tests are synthetic, not evidence of real Google login or provider-side configuration acceptance.

This review covers source assets and exact intended single oauthCallbackReady false→true initializer change under existing real Netlify mode. Sole integrator must reconcile actual current wrapper, preserve session/tenant verification and unrelated assets, and verify existing CSP supports the image/styles without relaxation. No full Worker source approval inferred before that exact splice. Branding asset provenance is recorded by author; no new external provider calls or private account access by reviewer. No production mutation performed.
