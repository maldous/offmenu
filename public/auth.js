import {createOffMenuIdentityClient} from './offmenu-identity-client.js';
import {createAuthController} from './auth-controller.js';
import {createProviderConsentController} from './provider-consent-controller.js';
const $=id=>document.getElementById(id);
const providerId=new URL(location.href).searchParams.get('provider');
let consent,terms;
async function loadConsent(){
  if(!/^[a-z0-9_-]{1,60}$/.test(providerId||''))return;
  $('provider-consent').hidden=false;
  const path='/api/provider-consent/'+providerId;
  consent=createProviderConsentController({loadTerms:()=>read(path),
    recordChoice:async body=>{
      const response=await fetch(path,{method:'POST',credentials:'same-origin',cache:'no-store',redirect:'error',
        headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:AbortSignal.timeout(15000)});
      if(!response.ok)throw Error('consent');return response.json();
    },onState:state=>{
      $('provider-consent-form').hidden=state.state!=='ready';
      $('provider-consent-status').textContent=state.message||({recorded:'Your choice was recorded. Provider access remains separate.',withdrawn:'Your choice was withdrawn.'}[state.state]||'');
    }});
  terms=await consent.load();if(!terms)return;
  const link=new URL(terms.termsUrl);if(link.protocol!=='https:')throw Error('terms');
  $('provider-terms-link').href=link.href;$('provider-terms-version').textContent=terms.termsVersion;
  $('provider-purpose').replaceChildren();
  for(const purpose of terms.purposes){const option=document.createElement('option');option.value=purpose;option.textContent=purpose==='private_use'?'Use this connection privately':'Refresh this connection in the background';$('provider-purpose').append(option);}
  $('provider-scopes').querySelectorAll('label').forEach(element=>element.remove());
  for(const scope of terms.scopes){const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.value=scope;label.append(input,document.createTextNode(scope));$('provider-scopes').append(label);}
}
async function read(path){
  const response=await fetch(path,{credentials:'same-origin',cache:'no-store',redirect:'error',
    headers:{Accept:'application/json'},signal:AbortSignal.timeout(15000)});
  if(!response.headers.get('Content-Type')?.includes('application/json'))throw Error('response');
  if(path.endsWith('/session')&&response.status===401)return {authenticated:false};
  if(!response.ok)throw Error('response');return response.json();
}
const controller=createAuthController({configuration:()=>read('/api/auth-page/config'),
  identityFor:async mode=>createOffMenuIdentityClient({mode,
    ...(mode==='netlify'?{netlify:await import('@netlify/identity')}:{})}),
  verifySession:()=>read('/api/auth-page/session'),navigate:path=>location.assign(path),
  onState:({state,message,synthetic})=>{
    $('auth-status').textContent=message||({loading:'Checking sign-in…','signing-in':'Signing in…'}[state]||'');
    $('synthetic-notice').hidden=!synthetic;
    $('signin-form').hidden=!['ready','signing-in'].includes(state);
    $('signin-submit').disabled=state!=='ready';
    $('continue-scanner').hidden=state!=='signed-in';$('signout').hidden=state!=='signed-in';
    if(state==='signed-in')void loadConsent().catch(()=>{$('provider-consent-status').textContent='Terms for this connection are unavailable.';});
    else $('provider-consent').hidden=true;
  }});
$('signin-form').addEventListener('submit',async event=>{event.preventDefault();
  const password=$('auth-password').value;$('auth-password').value='';
  await controller.signIn($('auth-email').value,password);
});
$('continue-scanner').onclick=()=>controller.continueToScanner();
$('signout').onclick=()=>controller.signOut();
$('provider-consent-form').onsubmit=async event=>{event.preventDefault();
  if(consent)await consent.choose({checked:$('provider-accept').checked,purpose:$('provider-purpose').value,
    scopes:[...$('provider-scopes').querySelectorAll('input:checked')].map(input=>input.value)});
};
$('provider-withdraw').onclick=()=>consent?.choose({choice:'withdrawn',purpose:$('provider-purpose').value,
  scopes:[...$('provider-scopes').querySelectorAll('input:checked')].map(input=>input.value)});
void controller.start();
