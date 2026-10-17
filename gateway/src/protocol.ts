import { z } from 'zod';
export const RETENTION_MS = 7 * 24 * 60 * 60 * 1000;
export const LEASE_MS = 90_000;
export const FRESH_MS = 60_000;
export const BODY_MAX = 256 * 1024;
export const uuid = z.uuidv4();
export const state = z.enum(['accepted', 'delivered', 'started', 'completed', 'failed', 'uncertain']);
export type State = z.infer<typeof state>;
export const enqueueSchema = z.object({requestId: uuid, sessionId: uuid, text: z.string().min(1).max(16384).refine(t=>t.trim().length>0&&!t.includes('[freebuff-relay'), 'Text must be nonblank and exclude relay markers').refine(t => new TextEncoder().encode(t).length <= 16384, 'Text exceeds 16 KiB')}).strict();
export const reportSchema = z.object({requestId: uuid, leaseId: uuid, state: state.exclude(['accepted']), evidence: z.string().max(512).optional(), reason: z.string().regex(/^[A-Z0-9_:.-]{1,128}$/).optional()}).strict();
export const messageSchema = z.object({id:z.string().min(1).max(128),role:z.enum(['user','assistant','system']),text:z.string().max(4096),timestamp:z.iso.datetime({offset:true})}).strict();
export const snapshotSchema = z.object({sessionId:uuid,paused:z.boolean().nullable(),observedAt:z.number().int().nonnegative(),messages:z.array(messageSchema).max(40)}).strict();
export type Snapshot = z.infer<typeof snapshotSchema>;
export type Enqueue = z.infer<typeof enqueueSchema>;
export type Report = z.infer<typeof reportSchema>;
export async function hashPayload(sessionId:string,text:string):Promise<string> {
  const bytes = await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify({sessionId,text})));
  return Array.from(new Uint8Array(bytes), b=>b.toString(16).padStart(2,'0')).join('');
}
export class BridgeError extends Error {constructor(public code:string,public status=400){super(code);}}
export function parseAllowlist(raw:string):string[]{
  const ids=z.array(uuid).max(3).parse(JSON.parse(raw));
  if(ids.includes('8d8caabd-881d-4fda-bb90-7c7c3f10e178'))throw new BridgeError('HISTORICAL_SESSION_EXCLUDED');
  if(new Set(ids).size!==ids.length)throw new BridgeError('INVALID_ALLOWLIST');
  return ids;
}
export function mayTransition(from:State,to:State,hasEvidence:boolean):boolean{
  if(from===to)return true;
  if(from==='completed'||from==='failed')return false;
  if(to==='accepted')return false;
  if(to==='uncertain')return from==='accepted';
  if(to==='failed')return true;
  if(!hasEvidence)return false;
  const rank={accepted:0,uncertain:0,delivered:1,started:2,completed:3,failed:4};
  return rank[to]>rank[from];
}
export async function readBounded(request:Request,max=BODY_MAX):Promise<string>{
  if(Number(request.headers.get('content-length')??0)>max)throw new BridgeError('BODY_TOO_LARGE',413);
  const reader=request.body?.getReader();if(!reader)return '';
  let total=0;const chunks:Uint8Array[]=[];
  try{while(true){const {done,value}=await reader.read();if(done)break;total+=value.length;if(total>max){await reader.cancel();throw new BridgeError('BODY_TOO_LARGE',413);}chunks.push(value);}}finally{reader.releaseLock();}
  const out=new Uint8Array(total);let offset=0;for(const c of chunks){out.set(c,offset);offset+=c.length;}return new TextDecoder('utf-8',{fatal:true,ignoreBOM:false}).decode(out);
}
