import { DurableObject } from 'cloudflare:workers';
import { z } from 'zod';
import { config,type Env } from './config';
import { QueueStore } from './store';
import { BridgeError,enqueueSchema,reportSchema,snapshotSchema,hashPayload,uuid } from './protocol';
export class BridgeQueue extends DurableObject<Env>{
  private store:QueueStore;
  constructor(ctx:DurableObjectState,env:Env){super(ctx,env);this.store=new QueueStore(ctx.storage.sql);ctx.storage.sql.exec('CREATE TABLE IF NOT EXISTS registration_budget(day TEXT PRIMARY KEY,count INTEGER NOT NULL)');}
  private async schedule(){const next=this.store.nextExpiry();const old=await this.ctx.storage.getAlarm();if(next!==null&&old!==next)await this.ctx.storage.setAlarm(Math.max(Date.now()+1000,next));else if(next===null&&old!==null)await this.ctx.storage.deleteAlarm();}
  async alarm(){this.store.purge(Date.now());await this.schedule();}
  async call(operation:string,input:unknown){
    try{return {ok:true as const,data:await this.run(operation,input)};}
    catch(error){return {ok:false as const,error:{code:error instanceof BridgeError?error.code:'INVALID_REQUEST',status:error instanceof BridgeError?error.status:400}};}
  }
  private async run(operation:string,input:unknown){
    const c=config(this.env),now=Date.now();let result:unknown;
    if(operation==='enqueue_message'){
      const value=enqueueSchema.parse(input),hash=await hashPayload(value.sessionId,value.text);
      result=this.ctx.storage.transactionSync(()=>this.store.enqueue(value,hash,c.sessions,now));
    }else result=this.ctx.storage.transactionSync(()=>{
      switch(operation){
        case 'bridge_status':return this.store.status(c.sessions,now);
        case 'list_sessions':return {sessions:this.store.sessions(c.sessions,now)};
        case 'read_messages':return this.store.messages(z.object({sessionId:uuid}).strict().parse(input).sessionId,c.sessions,now);
        case 'get_receipt':return this.store.getReceipt(z.object({requestId:uuid}).strict().parse(input).requestId,c.sessions,now);
        case 'poll':return this.store.poll(c.sessions,now,crypto.randomUUID());
        case 'report':return this.store.report(reportSchema.parse(input),c.sessions,now);
        case 'snapshot':return this.store.snapshot(snapshotSchema.parse(input),c.sessions,now);
        case 'registration_budget':{
          const day=new Date(now).toISOString().slice(0,10);
          this.ctx.storage.sql.exec('DELETE FROM registration_budget WHERE day<>?',day);
          const row=this.ctx.storage.sql.exec<{count:number}>('SELECT count FROM registration_budget WHERE day=?',day).toArray()[0];
          if((row?.count??0)>=100)throw new BridgeError('REGISTRATION_LIMIT',429);
          this.ctx.storage.sql.exec('INSERT INTO registration_budget(day,count) VALUES(?,1) ON CONFLICT(day) DO UPDATE SET count=count+1',day);return {ok:true};
        }
        default:throw new BridgeError('UNKNOWN_OPERATION',404);
      }
    });
    await this.schedule();return result;
  }
}
