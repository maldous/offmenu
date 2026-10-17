import {BridgeError,FRESH_MS,LEASE_MS,RETENTION_MS,mayTransition,type State,type Enqueue,type Report,type Snapshot} from './protocol';
export interface Sql {exec<T extends Record<string,SqlStorageValue>>(query:string,...args:(string|number|null)[]):Iterable<T>}
type Row=Record<string,SqlStorageValue> & {request_id:string;session_id:string;text:string;payload_hash:string;state:State;lease_id:string|null;lease_expires:number|null;created_at:number;expires_at:number;updated_at:number;evidence:string|null;reason:string|null};
export class QueueStore {
  constructor(private sql:Sql){
    sql.exec(`CREATE TABLE IF NOT EXISTS requests (request_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, text TEXT NOT NULL, payload_hash TEXT NOT NULL, state TEXT NOT NULL, lease_id TEXT, lease_expires INTEGER, created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL, updated_at INTEGER NOT NULL, evidence TEXT, reason TEXT)`);
    sql.exec(`CREATE INDEX IF NOT EXISTS req_exp ON requests(expires_at)`);
    sql.exec(`CREATE INDEX IF NOT EXISTS req_lease ON requests(state,lease_id,lease_expires,created_at)`);
    sql.exec(`CREATE TABLE IF NOT EXISTS snapshots (session_id TEXT PRIMARY KEY, paused INTEGER, observed_at INTEGER NOT NULL, expires_at INTEGER NOT NULL)`);
    sql.exec(`CREATE TABLE IF NOT EXISTS messages (session_id TEXT NOT NULL,id TEXT NOT NULL,role TEXT NOT NULL,text TEXT NOT NULL,timestamp TEXT NOT NULL,expires_at INTEGER NOT NULL,PRIMARY KEY(session_id,id))`);
    sql.exec(`CREATE INDEX IF NOT EXISTS msg_exp ON messages(expires_at)`);
  }
  private one<T extends Record<string,SqlStorageValue>>(q:string,...args:(string|number|null)[]):T|undefined{return Array.from(this.sql.exec<T>(q,...args))[0];}
  private allowed(id:string,ids:string[]){if(!ids.includes(id))throw new BridgeError('SESSION_NOT_ALLOWED',403);}
  purge(now:number){this.sql.exec('DELETE FROM requests WHERE expires_at<=?',now);this.sql.exec('DELETE FROM snapshots WHERE expires_at<=?',now);this.sql.exec('DELETE FROM messages WHERE expires_at<=?',now);this.sql.exec("UPDATE requests SET state='uncertain',reason='LEASE_EXPIRED',updated_at=? WHERE state='accepted' AND lease_id IS NOT NULL AND lease_expires<=?",now,now);}
  nextExpiry():number|null{const r=this.one<{expiry:number|null}>(`SELECT MIN(expiry) AS expiry FROM (SELECT MIN(expires_at) AS expiry FROM requests UNION ALL SELECT MIN(expires_at) FROM snapshots UNION ALL SELECT MIN(expires_at) FROM messages UNION ALL SELECT MIN(lease_expires) FROM requests WHERE state='accepted' AND lease_id IS NOT NULL)`);return r?.expiry??null;}
  private receipt(r:Row){return {requestId:r.request_id,sessionId:r.session_id,payloadHash:r.payload_hash,state:r.state,acceptedAt:r.created_at,updatedAt:r.updated_at,expiresAt:r.expires_at,evidence:r.evidence,reason:r.reason};}
  enqueue(input:Enqueue,payloadHash:string,ids:string[],now:number){
    this.purge(now);this.allowed(input.sessionId,ids);
    const old=this.one<Row>('SELECT * FROM requests WHERE request_id=?',input.requestId);
    if(old){if(old.payload_hash!==payloadHash||old.session_id!==input.sessionId)throw new BridgeError('REQUEST_ID_CONFLICT',409);return this.receipt(old);}
    this.assertDispatchable(input.sessionId,now);
    const count=this.one<{n:number}>("SELECT COUNT(*) AS n FROM requests WHERE state IN ('accepted','uncertain')")!.n;
    if(count>=32)throw new BridgeError('QUEUE_FULL',429);
    const total=this.one<{n:number}>('SELECT COUNT(*) AS n FROM requests')!.n;
    if(total>=10000)throw new BridgeError('RETENTION_CAPACITY',429);
    this.sql.exec('INSERT INTO requests(request_id,session_id,text,payload_hash,state,created_at,expires_at,updated_at) VALUES(?,?,?,?,?,?,?,?)',input.requestId,input.sessionId,input.text,payloadHash,'accepted',now,now+RETENTION_MS,now);
    return this.receipt(this.one<Row>('SELECT * FROM requests WHERE request_id=?',input.requestId)!);
  }
  private assertDispatchable(sessionId:string,now:number){const s=this.one<{paused:number|null;observed_at:number}>('SELECT paused,observed_at FROM snapshots WHERE session_id=?',sessionId);if(!s||s.observed_at<now-FRESH_MS)throw new BridgeError('SNAPSHOT_STALE',409);if(s.paused!==0)throw new BridgeError(s.paused===1?'SESSION_PAUSED':'PAUSE_UNKNOWN',409);}
  poll(ids:string[],now:number,leaseId:string){
    this.purge(now);
    const rows=Array.from(this.sql.exec<Row>("SELECT * FROM requests WHERE state='accepted' AND lease_id IS NULL ORDER BY created_at,request_id LIMIT 32"));
    for(const r of rows){if(!ids.includes(r.session_id))continue;try{this.assertDispatchable(r.session_id,now);}catch{continue;}
      this.sql.exec('UPDATE requests SET lease_id=?,lease_expires=?,updated_at=? WHERE request_id=? AND lease_id IS NULL',leaseId,Math.min(now+LEASE_MS,r.expires_at),now,r.request_id);
      return {lease:{requestId:r.request_id,sessionId:r.session_id,text:r.text,payloadHash:r.payload_hash,leaseId,leaseExpiresAt:Math.min(now+LEASE_MS,r.expires_at),acceptedAt:r.created_at,expiresAt:r.expires_at},commands:[]};
    }return {lease:null,commands:[]};
  }
  report(input:Report,ids:string[],now:number){
    this.purge(now);const r=this.one<Row>('SELECT * FROM requests WHERE request_id=?',input.requestId);if(!r)throw new BridgeError('REQUEST_NOT_FOUND',404);this.allowed(r.session_id,ids);
    if(r.lease_id!==input.leaseId)throw new BridgeError('LEASE_MISMATCH',409);
    if(!mayTransition(r.state,input.state,!!input.evidence))throw new BridgeError('INVALID_TRANSITION',409);
    if(r.state!==input.state)this.sql.exec('UPDATE requests SET state=?,evidence=?,reason=?,updated_at=? WHERE request_id=?',input.state,input.evidence??null,input.reason??null,now,input.requestId);
    return this.receipt(this.one<Row>('SELECT * FROM requests WHERE request_id=?',input.requestId)!);
  }
  snapshot(input:Snapshot,ids:string[],now:number){
    this.allowed(input.sessionId,ids);if(input.observedAt>now+5000||input.observedAt<now-FRESH_MS)throw new BridgeError('INVALID_SNAPSHOT_TIME');
    this.purge(now);const old=this.one<{observed_at:number}>('SELECT observed_at FROM snapshots WHERE session_id=?',input.sessionId);if(old&&old.observed_at>input.observedAt)throw new BridgeError('SNAPSHOT_REGRESSION',409);
    this.sql.exec('INSERT INTO snapshots(session_id,paused,observed_at,expires_at) VALUES(?,?,?,?) ON CONFLICT(session_id) DO UPDATE SET paused=excluded.paused,observed_at=excluded.observed_at,expires_at=excluded.expires_at',input.sessionId,input.paused===null?null:Number(input.paused),input.observedAt,input.observedAt+RETENTION_MS);
    const oldMessages=Array.from(this.sql.exec<{id:string;role:string;text:string;timestamp:string}>('SELECT id,role,text,timestamp FROM messages WHERE session_id=?',input.sessionId));
    const keep=new Set<string>();
    for(const m of input.messages){const timestamp=Date.parse(m.timestamp);if(timestamp>now+5000||timestamp+RETENTION_MS<=now)continue;keep.add(m.id);const old=oldMessages.find(x=>x.id===m.id);if(!old||old.role!==m.role||old.text!==m.text||old.timestamp!==m.timestamp)this.sql.exec('INSERT OR REPLACE INTO messages(session_id,id,role,text,timestamp,expires_at) VALUES(?,?,?,?,?,?)',input.sessionId,m.id,m.role,m.text,m.timestamp,timestamp+RETENTION_MS);}
    for(const old of oldMessages)if(!keep.has(old.id))this.sql.exec('DELETE FROM messages WHERE session_id=? AND id=?',input.sessionId,old.id);
    return {ok:true};
  }
  sessions(ids:string[],now:number){this.purge(now);return ids.map(sessionId=>{const row=this.one<{paused:number|null;observed_at:number}>('SELECT paused,observed_at FROM snapshots WHERE session_id=?',sessionId);return {sessionId,paused:row?.paused===undefined||row?.paused===null?null:!!row.paused,observedAt:row?.observed_at??null,stale:!row||row.observed_at<now-FRESH_MS,source:'configured_allowlist'};});}
  messages(sessionId:string,ids:string[],now:number){this.allowed(sessionId,ids);this.purge(now);return {session:this.sessions(ids,now).find(s=>s.sessionId===sessionId),messages:Array.from(this.sql.exec('SELECT id,role,text,timestamp FROM messages WHERE session_id=? ORDER BY timestamp,id LIMIT 40',sessionId)),boundedSnapshot:true};}
  getReceipt(requestId:string,ids:string[],now:number){this.purge(now);const r=this.one<Row>('SELECT * FROM requests WHERE request_id=?',requestId);if(!r)throw new BridgeError('REQUEST_NOT_FOUND',404);this.allowed(r.session_id,ids);return this.receipt(r);}
  status(ids:string[],now:number){this.purge(now);const counts=Array.from(this.sql.exec("SELECT state,COUNT(*) AS count FROM requests GROUP BY state"));return {transportOnly:true,maxSessions:3,retentionDays:7,sessions:this.sessions(ids,now),receipts:counts};}
}
