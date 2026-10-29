/** Pure request-local timing wrappers: caller owns all work, I/O, protocol and headers. */
export const VERSION='offmenu-rpc-attribution-timing/1';
export const STAGES=Object.freeze(['hydration','parse','query','response_limit_serialization','serialization','total']);
const headers=Object.freeze({hydration:'attr_hydrate',parse:'attr_parse',query:'attr_query',response_limit_serialization:'attr_limit_serialize',serialization:'attr_serialize',total:'attr_total'});
const domains=new Set(['local-workerd','browser','node-test','scripted-test','unqualified']);
/** Create once per request. Never pass request/response/profile bodies to this adapter. */
export function createTimingAdapter({enabled=false,now,clockDomain='unqualified',resolutionMs=null}={}){
 const active=enabled===true,clock=typeof now==='function'?now:null,domain=domains.has(clockDomain)?clockDomain:'unqualified';
 const resolution=Number.isFinite(resolutionMs)&&resolutionMs>0?resolutionMs:null;
 const spans=[];let dropped=0,unsupported=0;
 function read(){try{const n=clock?.();return typeof n==='number'&&Number.isFinite(n)?n:null;}catch{return null;}}
 function start(stage){
  if(!STAGES.includes(stage)){unsupported++;return null;}
  if(spans.length>=16){dropped++;return null;}
  const span={stage,index:spans.length,state:'pending',durationMs:null,observedDeltaMs:null,operationOutcome:'pending'};spans.push(span);return {span,start:read()};
 }
 function finish(token,outcome){
  if(!token)return;const end=read(),s=token.span;s.operationOutcome=outcome;
  if(token.start===null||end===null){s.state='clock-unavailable';return;}
  const delta=end-token.start;s.observedDeltaMs=Number.isFinite(delta)?delta:null;
  if(!Number.isFinite(delta)||delta<0||delta>60000){s.state='clock-invalid-or-regressed';return;}
  if(delta===0||resolution!==null&&delta<resolution){s.state='non-advancing-or-below-resolution';return;}
  s.state='observed-positive';s.durationMs=delta;
 }
 function runSync(stage,work){
  if(!active)return work();const token=start(stage);
  try{const value=work();finish(token,'returned');return value;}catch(error){finish(token,'threw');throw error;}
 }
 function runAsync(stage,work){
  if(!active)return work();const token=start(stage);let promise;
  try{promise=work();}catch(error){finish(token,'threw');throw error;}
  return Promise.resolve(promise).then(value=>{finish(token,'returned');return value;},error=>{finish(token,'rejected');throw error;});
 }
 function snapshot(){return {version:VERSION,enabled:active,clockDomain:domain,clockDomainQualification:'Caller supplied; not independently verified by module',resolutionMs:resolution,stageLimit:16,droppedSpans:dropped,unsupportedStages:unsupported,spans:spans.map(s=>({...s})),meaning:'Observed inclusive wall intervals, not CPU or exclusive costs. total nests stages; do not sum it with them. Disabled path does not read clock or wrap promises.'};}
 function serverTiming(){
  if(!active)return '';const parts=[];
  for(const stage of STAGES){const rows=spans.filter(s=>s.stage===stage);if(!rows.length)continue;const valid=rows.every(s=>s.state==='observed-positive');const duration=valid?rows.reduce((sum,s)=>sum+s.durationMs,0):null;
   // Unavailable metrics have no fabricated zero duration. Repeated spans aggregate only if every span qualifies.
   parts.push(duration===null||!Number.isFinite(duration)?headers[stage]+';desc="unavailable"':headers[stage]+';dur='+duration.toFixed(3));
  }
  return parts.join(', ');
 }
 return Object.freeze({runSync,runAsync,snapshot,serverTiming});
}
