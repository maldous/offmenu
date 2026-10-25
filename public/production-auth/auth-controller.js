// Pure flow controller; dependencies own IO. No profile/cookie/token persistence.
export function createAuthController({configuration,identityFor,verifySession,navigate,onState=()=>{}}) {
  let identity,config,state='initial',busy=false,providers=[],signupAvailable=false;
  const emit=(next,message='')=>{state=next;onState({state,message,synthetic:config?.synthetic===true,
    providers:[...providers],oauthReady:config?.oauthAvailable===true,signupAvailable});};
  const fail=()=>emit('ready','Sign-in could not be confirmed. Your kitchen has not changed.');
  async function confirmed(user){
    if(!user||typeof user.id!=='string')return false;
    const proof=await verifySession();
    return proof?.authenticated===true&&proof.userId===user.id&&proof.mode===config.mode;
  }
  async function start(){
    if(state!=='initial')return;
    emit('loading');
    try{
      config=await configuration();
      if(config?.schema!=='offmenu-auth-page/1'||!['netlify','better-auth'].includes(config.mode)||
        config.nextPath!=='/shelf-scanner.html')throw Error('configuration');
      identity=await identityFor(config.mode);
      const callback=await identity.handleAuthCallback();
      if(callback?.type&&!['oauth','confirmation','email_change'].includes(callback.type)){
        emit('unavailable','Use the existing account page for this account action.');return;
      }
      const settings=await identity.getSettings();
      signupAvailable=config.mode==='netlify'&&settings?.disableSignup===false&&
        settings?.providers?.email===true&&typeof identity.signup==='function';
      // Enabled providers come from the selected SDK transport, never a public
      // discovery snapshot or browser query flag. Email uses the existing form.
      providers=config.mode==='netlify'?['google','github','gitlab','bitbucket','facebook']
        .filter(provider=>settings?.providers?.[provider]===true):[];
      if(await confirmed(await identity.getUser())){emit('signed-in','Signed in.');return;}
      if(config.emailSignIn==='not-configured'){
        emit('unavailable','Email sign-in is not configured for this environment.');return;
      }
      emit('ready');
    }catch{emit('unavailable','Sign-in setup is unavailable in this environment.');}
  }
  async function providerSignIn(provider){
    if(busy||state!=='ready'||config.identityTransport!=='real'||
      config.oauthAvailable!==true||!providers.includes(provider))return false;
    busy=true;emit('redirecting','Opening your sign-in provider…');
    try{await identity.oauthLogin(provider);fail();return false;}
    catch(error){
      // @netlify/identity 2.0.0 redirects and deliberately throws this error.
      if(error?.name==='AuthError'&&error.message==='Redirecting to OAuth provider')return true;
      fail();return false;
    }finally{busy=false;}
  }
  async function signIn(email,password){
    if(busy||state!=='ready')return false;
    if(typeof email!=='string'||!email.trim()||typeof password!=='string'||!password){
      emit('ready','Enter your email and password.');return false;
    }
    busy=true;emit('signing-in');
    try{
      const user=await identity.login(email.trim(),password);
      if(!await confirmed(user)){fail();return false;}
      emit('signed-in','Signed in.');return true;
    }catch{fail();return false;}finally{busy=false;password='';}
  }
  async function continueToScanner(){
    if(busy||state!=='signed-in')return false;
    busy=true;
    try{
      if(!await confirmed(await identity.getUser())){fail();return false;}
      navigate('/shelf-scanner.html');return true;
    }catch{fail();return false;}finally{busy=false;}
  }
  async function signUp(email,password){
    if(busy||state!=='ready'||!signupAvailable)return false;
    if(typeof email!=='string'||!email.trim()||typeof password!=='string'||!password){
      emit('ready','Enter your email and password.');return false;
    }
    busy=true;emit('creating-account');
    try{
      // Existing SDK/realm only; the provider controls registration and email confirmation.
      const created=await identity.signup(email.trim(),password);
      const user=await identity.getUser();
      if(created?.id&&user?.id===created.id&&await confirmed(user)){emit('signed-in','Signed in.');return true;}
      emit('ready','Check your email to confirm your account, then sign in.');return true;
    }catch{emit('ready','Account creation could not be confirmed. Check your details or sign in to your existing account.');return false;}
    finally{busy=false;password='';}
  }
  async function signOut(){
    if(busy||!identity)return false;
    busy=true;
    try{
      await identity.logout();
      if((await verifySession())?.authenticated===true)throw Error('session-remains');
      emit('ready','Signed out.');return true;
    }
    catch{emit('unavailable','Sign-out could not be confirmed.');return false;}
    finally{busy=false;}
  }
  return Object.freeze({start,signIn,signUp,providerSignIn,continueToScanner,signOut,getState:()=>state});
}
