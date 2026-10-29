// One module instance belongs to this guest document only. No browser storage,
// cookies, account, identity, backend state or cross-tab handoff is accessed.
const encoder=new TextEncoder(),MAX_BYTES=262144;
const size=(key,value)=>encoder.encode(key).length+encoder.encode(value).length;
export function createGuestStorage(){
const values=new Map();let used=0;
return Object.freeze({
  get length(){return values.size;},
  key(index){return Number.isInteger(index)&&index>=0?[...values.keys()][index]??null:null;},
  getItem(key){key=String(key);return values.has(key)?values.get(key):null;},
  setItem(key,value){
    key=String(key);value=String(value);
    const previous=values.has(key)?size(key,values.get(key)):0,next=used-previous+size(key,value);
    if(next>MAX_BYTES){const error=Error('Demo memory limit reached.');error.name='QuotaExceededError';throw error;}
    values.set(key,value);used=next;
  },
  removeItem(key){key=String(key);if(values.has(key)){used-=size(key,values.get(key));values.delete(key);}},
  clear(){values.clear();used=0;}
});
}
export const guestStorage=createGuestStorage();
export function readGuestPrefill(){return null;}
export function finishGuestSession(queue){
  if(!Array.isArray(queue))throw Error('DEMO_QUEUE_REQUIRED');
  return {message:'Demo session finished. Your list stays in this tab until you reload.',
    captureCount:queue.length,persisted:false,scope:'guest-demo'};
}
