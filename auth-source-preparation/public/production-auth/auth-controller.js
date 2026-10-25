// Pure flow controller. Existing SDK owns tokens; existing server verifies subject.
export function createAuthController({configuration,identityFor,verifySession,navigate,
  callbackContext=()=>({kind:'none'}),onState=()=>{}}) {
  let identity,config,state='initial',busy=false,providers=[],signupAvailable=false,recoveryAvailable=false,recoverySubject=null;
  const emit=(next,message='')=>{state=next;onState({state,message,synthetic:config?.synthetic===true,
    providers:[...providers],oauthReady:config?.oauthAvailable===true,signupAvailable,recoveryAvailable});};
  const validEmail=value=>typeof value==='string'&&value.trim().length>0&&value.length<=512;
  const validPassword=value=>typeof value==='string'&&value.length>0&&value.length<=1024;
  const fail=()=>emit('ready','Sign-in could not be confirmed. Your kitchen has not changed.');
  async function confirmed(user){
    if(!user||typeof user.id!=='string'||!user.id||user.id.length>=200)return false;
    const proof=await verifySession();
    return proof?.authenticated===true&&proof.userId===user.id&&proof.mode===config.mode;
  }
  const emailMode=()=>config.mode==='netlify'&&config.identityTransport==='real';
  function callbackAllowed(intent){
    if(intent.kind==='none')return true;
    if(intent.origin!==config.origin||intent.path!=='/auth.html')return false;
    if(intent.kind==='oauth')return config.oauthAvailable===true&&
      Array.isArray(config.oauthProviders)&&config.oauthProviders.length===1&&config.oauthProviders[0]==='google';
    if(!emailMode()||config.emailCallbackPath!=='/auth.html')return false;
    if(intent.kind==='confirmation')return config.confirmationAvailable===true;
    return intent.kind==='recovery'&&config.recoveryCallbackAvailable===true&&config.passwordUpdateAvailable===true;
  }
  async function start(){
    if(state!=='initial')return;emit('loading');
    try{
      config=await configuration();
      if(config?.schema!=='offmenu-auth-page/1'||!['netlify','better-auth'].includes(config.mode)||
        config.nextPath!=='/shelf-scanner.html')throw Error('configuration');
      const intent=callbackContext();
      // Reject unsupported/unqualified actions BEFORE the SDK can consume tokens.
      if(!intent||!callbackAllowed(intent)){
        emit('unavailable','This account link cannot be completed at this address yet. Your account has not been changed.');return;
      }
      identity=await identityFor(config.mode);
      const settings=await identity.getSettings();
      const email=emailMode()&&settings?.providers?.email===true;
      signupAvailable=email&&config.signupAvailable===true&&settings?.disableSignup===false&&typeof identity.signup==='function';
      recoveryAvailable=email&&config.recoveryAvailable===true&&typeof identity.requestPasswordRecovery==='function';
      providers=config.mode==='netlify'&&config.oauthAvailable===true&&Array.isArray(config.oauthProviders)?
        ['google'].filter(provider=>config.oauthProviders.includes(provider)&&settings?.providers?.[provider]===true):[];
      if(intent.kind!=='none'){
        if((intent.kind==='confirmation'||intent.kind==='recovery')&&!email)throw Error('email unavailable');
        if(intent.kind==='recovery'&&typeof identity.updateUser!=='function')throw Error('reset unavailable');
        const callback=await identity.handleAuthCallback();
        if(callback?.type!==intent.kind||!await confirmed(callback.user))throw Error('callback verification');
        if(intent.kind==='recovery'){
          recoverySubject=callback.user.id;emit('recovery-password','Choose a new password to finish recovering your account.');return;
        }
        emit('signed-in',intent.kind==='confirmation'?'Email confirmed. You are signed in.':'Signed in.');return;
      }
      if(await confirmed(await identity.getUser())){emit('signed-in','Signed in.');return;}
      if(config.emailSignIn==='not-configured'){
        emit('unavailable','Email sign-in is not configured for this environment.');return;
      }
      emit('ready');
    }catch{emit('unavailable','This sign-in or account link could not be confirmed. Sign in again or request a new link.');}
  }
  async function providerSignIn(provider){
    if(busy||state!=='ready'||config.identityTransport!=='real'||config.oauthAvailable!==true||!providers.includes(provider))return false;
    busy=true;emit('redirecting','Opening your sign-in provider…');
    try{await identity.oauthLogin(provider);fail();return false;}
    catch(error){if(error?.name==='AuthError'&&error.message==='Redirecting to OAuth provider')return true;fail();return false;}
    finally{busy=false;}
  }
  async function signIn(email,password){
    if(busy||state!=='ready')return false;
    if(!validEmail(email)||!validPassword(password)){emit('ready','Enter your email and password.');return false;}
    busy=true;emit('signing-in');
    try{const user=await identity.login(email.trim(),password);if(!await confirmed(user)){fail();return false;}
      emit('signed-in','Signed in.');return true;
    }catch{fail();return false;}finally{busy=false;password='';}
  }
  function showSignUp(){if(busy||state!=='ready'||!signupAvailable)return false;emit('sign-up');return true;}
  function backToSignIn(){
    if(busy||!['sign-up','confirmation-pending','ready'].includes(state))return false;
    emit('ready');return true;
  }
  async function signUp(email,password,passwordConfirmation){
    if(busy||state!=='sign-up'||!signupAvailable)return false;
    if(!validEmail(email)||!validPassword(password)||password!==passwordConfirmation){
      emit('sign-up','Enter your email and matching passwords.');return false;
    }
    busy=true;emit('creating-account');
    try{
      const created=await identity.signup(email.trim(),password),user=await identity.getUser();
      if(created?.id&&user?.id===created.id&&await confirmed(user)){emit('signed-in','Account created. You are signed in.');return true;}
      emit('confirmation-pending','Account creation was accepted. If confirmation is required, check your email, then sign in.');return true;
    }catch{emit('sign-up','Account creation could not be confirmed. Check your details or sign in to your existing account.');return false;}
    finally{busy=false;password='';passwordConfirmation='';}
  }
  async function requestRecovery(email){
    if(busy||state!=='ready'||!recoveryAvailable)return false;
    if(!validEmail(email)){emit('ready','Enter your email address.');return false;}
    busy=true;emit('requesting-recovery','Requesting a password reset…');let accepted=false;
    try{await identity.requestPasswordRecovery(email.trim());accepted=true;}catch{}
    finally{
      busy=false;emit('ready','If this address has an account, check its email for a reset link. You can try again if it does not arrive.');
    }
    return accepted;
  }
  async function resetPassword(password,passwordConfirmation){
    if(busy||state!=='recovery-password'||!recoverySubject||config.passwordUpdateAvailable!==true)return false;
    if(!validPassword(password)||password!==passwordConfirmation){emit('recovery-password','Enter matching new passwords.');return false;}
    busy=true;emit('resetting-password','Updating your password…');
    try{
      const current=await identity.getUser();
      if(current?.id!==recoverySubject||!await confirmed(current))throw Error('subject changed');
      const updated=await identity.updateUser({password});
      if(updated?.id!==recoverySubject||!await confirmed(updated))throw Error('reset verification');
      recoverySubject=null;emit('signed-in','Password updated. You are signed in.');return true;
    }catch{emit('unavailable','The password update could not be confirmed. Sign in again or request a new reset link.');return false;}
    finally{busy=false;password='';passwordConfirmation='';}
  }
  async function continueToScanner(){
    if(busy||state!=='signed-in')return false;busy=true;
    try{if(!await confirmed(await identity.getUser())){fail();return false;}navigate('/shelf-scanner.html');return true;}
    catch{fail();return false;}finally{busy=false;}
  }
  async function signOut(){
    if(busy||!identity)return false;busy=true;
    try{await identity.logout();if((await verifySession())?.authenticated===true)throw Error('session remains');
      recoverySubject=null;emit('ready','Signed out.');return true;
    }catch{emit('unavailable','Sign-out could not be confirmed.');return false;}finally{busy=false;}
  }
  return Object.freeze({start,signIn,showSignUp,backToSignIn,signUp,requestRecovery,resetPassword,
    providerSignIn,continueToScanner,signOut,getState:()=>state});
}
