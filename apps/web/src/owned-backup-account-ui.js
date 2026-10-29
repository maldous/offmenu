import {t,setLocalizedText} from './i18n.js';

const ROUTE='/api/private-portability/owned-backup/export';
const MAX_BYTES=2_000_000;
const atom=value=>typeof value==='string'&&value.length>0&&value.length<=200&&!/[\u0000-\u001f\u007f]/u.test(value);
const exact=(value,keys)=>value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).length===keys.length&&keys.every(key=>Object.hasOwn(value,key));
// Deployment code alone supplies already-qualified, nonsecret selection metadata.
// No page attributes, forms, storage, URL parameters or account claims are inputs.
function selectedMetadata(value){
 if(!exact(value,['packageId','recoveryRef','keyReference'])||!atom(value.packageId)||!atom(value.recoveryRef)||
  !exact(value.keyReference,['keyRef','keyVersion'])||!atom(value.keyReference.keyRef)||
  !Number.isSafeInteger(value.keyReference.keyVersion)||value.keyReference.keyVersion<1)return null;
 return {packageId:value.packageId,recoveryRef:value.recoveryRef,keyReference:{keyRef:value.keyReference.keyRef,keyVersion:value.keyReference.keyVersion}};
}
const unavailable=()=>Object.assign(new Error('Invalid encrypted backup response.'),{uiMessage:t('The encrypted backup could not be downloaded. Try again.')});
function attachmentFilename(response){
 const match=/^attachment\s*;\s*filename="([^"]+)"\s*$/i.exec(response.headers.get('Content-Disposition')||'');
 const name=match?.[1];
 if(!name||name.length>96||!(/^[A-Za-z0-9][A-Za-z0-9._-]*\.json$/).test(name)||name.includes('..'))throw unavailable();
 return name;
}
function sealedPackage(value,selection){
 const fields=['schemaVersion','packageId','kind','source','identity','recipient','createdAt','scope','consent','protection','manifestDigest','envelope','checksum'];
 const e=value?.envelope;
 return exact(value,fields)&&value.schemaVersion==='offmenu-private-portable-package/1'&&value.kind==='owned-backup'&&value.packageId===selection.packageId&&
  /^[a-f0-9]{64}$/.test(value.checksum)&&/^[a-f0-9]{64}$/.test(value.manifestDigest)&&
  exact(e,['version','algorithm','custody','keyRef','keyVersion','nonce','ciphertext'])&&e.version===1&&e.algorithm==='AES-256-GCM'&&
  ['server-envelope','client'].includes(e.custody)&&e.keyRef===selection.keyReference.keyRef&&e.keyVersion===selection.keyReference.keyVersion&&
  typeof e.nonce==='string'&&/^[A-Za-z0-9+/]{16}$/.test(e.nonce)&&typeof e.ciphertext==='string'&&
  e.ciphertext.length>=24&&e.ciphertext.length<=1398124&&e.ciphertext.length%4===0&&/^[A-Za-z0-9+/]*={0,2}$/.test(e.ciphertext);
}
async function sealedResponse(response,selection,signal){
 if(response.status!==200){
  void response.body?.cancel().catch(()=>{});
  const uiMessage=response.status===401?t('Sign in again before downloading an encrypted account backup.'):
   response.status===403?t('This account backup was not authorized. Check your account and backup selection, then try again.'):
   response.status===503?t('Encrypted account backup is unavailable. Try again later.'):
   t('The encrypted backup could not be downloaded. Try again.');
  throw Object.assign(new Error('Backup request refused.'),{uiMessage});
 }
 if(response.redirected||response.headers.get('Content-Type')?.split(';')[0].trim().toLowerCase()!=='application/json')throw unavailable();
 const filename=attachmentFilename(response),reader=response.body?.getReader();if(!reader)throw unavailable();
 const chunks=[];let size=0;
 try{for(;;){if(signal.aborted)throw unavailable();const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>MAX_BYTES){await reader.cancel();throw unavailable();}chunks.push(value);}}
 finally{reader.releaseLock();}
 const bytes=new Uint8Array(size);let offset=0;for(const part of chunks){bytes.set(part,offset);offset+=part.byteLength;}
 let value;try{value=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));}catch{throw unavailable();}
 // A shallow sealed-package gate, not cryptographic verification or restore acceptance.
 if(!sealedPackage(value,selection))throw unavailable();return {bytes,filename};
}
function downloadEncryptedBackup(blob,filename,{document=globalThis.document}={}){
 const view=document.defaultView||globalThis,urls=view.URL,anchor=document.createElement('a');
 const url=urls.createObjectURL(blob);let clicked=false;
 try{anchor.href=url;anchor.download=filename;anchor.hidden=true;document.body.append(anchor);anchor.click();clicked=true;}
 finally{anchor.remove();if(clicked)view.setTimeout(()=>urls.revokeObjectURL(url),1000);else urls.revokeObjectURL(url);}
}
export function setupOwnedBackupAccount({root,dialog,getUser=()=>null,getMetadata=()=>null,fetchImpl=globalThis.fetch}={}){
 if(!root||!dialog)return Object.freeze({refresh:async()=>false,reset(){},destroy(){}});
 const button=root.querySelector('#owned-backup-download'),status=root.querySelector('#owned-backup-status');
 if(!button||!status)throw Error('Account backup controls are missing.');
 const document=root.ownerDocument,timers=document.defaultView||globalThis;
 let revision=0,busy=false,selection=null,controller=null,destroyed=false;
 const owner=()=>{const user=getUser();return atom(user?.id)?user.id:null;};
 const current=(stamp,id)=>!destroyed&&revision===stamp&&dialog.open&&owner()===id;
 const idle=()=>{root.setAttribute('aria-busy','false');setLocalizedText(button,'Download encrypted account backup');};
 const reset=()=>{revision++;controller?.abort();controller=null;busy=false;selection=null;button.disabled=true;idle();setLocalizedText(status,'Encrypted account backup is unavailable.');};
 const refresh=async()=>{
  if(destroyed||busy)return false;const stamp=++revision,id=owner();selection=null;button.disabled=true;idle();
  if(!dialog.open){setLocalizedText(status,'Open your account panel to download an encrypted backup.');return false;}
  if(!id){setLocalizedText(status,'Sign in to download an encrypted account backup.');return false;}
  setLocalizedText(status,'Checking encrypted backup availability…');
  let next;try{next=selectedMetadata(await getMetadata());}catch{next=null;}
  if(!current(stamp,id))return false;
  selection=next;button.disabled=!next;if(next)setLocalizedText(status,'Ready to download your encrypted account backup.');else setLocalizedText(status,'Encrypted account backup is unavailable.');return !!next;
 };
 const click=async event=>{
  event?.preventDefault();if(destroyed||busy)return;
  const id=owner();if(!dialog.open||!id){reset();return;}
  const stamp=++revision;busy=true;button.disabled=true;root.setAttribute('aria-busy','true');setLocalizedText(button,'Preparing encrypted account backup…');setLocalizedText(status,'Preparing your encrypted account backup…');
  const abort=new AbortController();controller=abort;const timeout=timers.setTimeout(()=>abort.abort(),30000);
  try{
   let next;try{next=selectedMetadata(await getMetadata());}catch{next=null;}
   if(!current(stamp,id))return;selection=next;
   if(!next){setLocalizedText(status,'Encrypted account backup is unavailable.');return;}
   if(abort.signal.aborted)throw unavailable();
   const response=await fetchImpl(ROUTE,{method:'POST',credentials:'same-origin',mode:'same-origin',cache:'no-store',redirect:'error',
    headers:{'Content-Type':'application/json',Accept:'application/json'},body:JSON.stringify(next),signal:abort.signal});
   if(!current(stamp,id)){void response.body?.cancel().catch(()=>{});return;}
   const {bytes,filename}=await sealedResponse(response,next,abort.signal);
   if(!current(stamp,id)||abort.signal.aborted)return;
   downloadEncryptedBackup(new Blob([bytes],{type:'application/json'}),filename,{document});
   setLocalizedText(status,'Encrypted account backup download started.');
  }catch(error){if(current(stamp,id))setLocalizedText(status,error.uiMessage||t('The encrypted backup could not be downloaded. Try again.'));}
  finally{timers.clearTimeout(timeout);if(revision===stamp&&!destroyed){controller=null;busy=false;idle();button.disabled=!selection||!dialog.open||owner()!==id;}}
 };
 button.addEventListener('click',click);dialog.addEventListener('close',reset);dialog.addEventListener('cancel',reset);reset();
 return Object.freeze({refresh,reset,destroy(){reset();destroyed=true;button.removeEventListener('click',click);dialog.removeEventListener('close',reset);dialog.removeEventListener('cancel',reset);}});
}
