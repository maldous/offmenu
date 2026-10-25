export function createProviderConsentController({loadTerms,recordChoice,onState=()=>{}}){
  let terms,busy=false;
  async function load(){
    try{terms=await loadTerms();if(typeof terms?.termsUrl!=='string'||typeof terms?.termsVersion!=='string')throw Error('terms');
      onState({state:'ready',terms});return terms;
    }catch{onState({state:'unavailable',message:'Terms for this connection are not configured.'});return null;}
  }
  async function choose({checked,purpose,scopes,choice='granted'}){
    if(busy)return false;
    if(choice==='withdrawn'){
      busy=true;
      try{const result=await recordChoice({choice:'withdrawn'});if(result?.recorded!==true)throw Error('record');
        terms=null;onState({state:'withdrawn',revision:result.revision});return true;
      }catch{onState({state:'unavailable',message:'Your withdrawal could not be confirmed.'});return false;}
      finally{busy=false;}
    }
    if(!terms||checked!==true)return false;
    if(!['granted','withdrawn'].includes(choice)||!terms.purposes.includes(purpose)||
      !Array.isArray(scopes)||scopes.some(s=>!terms.scopes.includes(s)))return false;
    busy=true;
    try{const result=await recordChoice({termsVersion:terms.termsVersion,purpose,scopes,choice});
      if(result?.recorded!==true)throw Error('not-recorded');
      onState({state:choice==='granted'?'recorded':'withdrawn',revision:result.revision});return true;
    }catch{terms=null;onState({state:'unavailable',message:'The connection terms changed or could not be recorded. Review them again.'});return false;}
    finally{busy=false;}
  }
  return Object.freeze({load,choose});
}
