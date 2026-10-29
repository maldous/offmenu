import {strictJSON} from './strict-json.mjs';
// No whole-shard JSON string/array/object is assembled. Retain only one entry token,
// one parsed entry and the consumer's selected match while validating to EOF.
export async function scanShard(stream,{expectedBytes,expectedPrefix,expectedEntries,maxEntries,maxEntryBytes=262144,
  maxEntryNodes=8192,life,onEntry}) {
  const fail=()=>{throw Error('invalid-streamed-shard');};
  const reader=stream.getReader(),decoder=new TextDecoder('utf-8',{fatal:true}),encoder=new TextEncoder();
  let totalBytes=0,done=false,state='root',key='',token='',escaped=false,inString=false,depth=0,count=0;
  const keys=new Set();const isSpace=c=>c===' '||c==='\n'||c==='\r'||c==='\t';
  async function consume(chunk) {
    for(let i=0;i<chunk.length;i++) {
      const c=chunk[i];
      if(state==='entry') {
        token+=c;if(token.length>maxEntryBytes)fail();
        if(inString){if(escaped)escaped=false;else if(c==='\\')escaped=true;else if(c==='"')inString=false;}
        else if(c==='"')inString=true;else if(c==='{'||c==='[')depth++;else if(c==='}'||c===']')depth--;
        if(depth===0) {
          if(encoder.encode(token).length>maxEntryBytes||++count>maxEntries)fail();
          const entry=strictJSON(token,life.check,maxEntryNodes);token='';
          await onEntry(entry);state='after-entry';life.check();
        }
        continue;
      }
      if(state==='key-token'||state==='meta-token') {
        token+=c;if(token.length>256)fail();
        if(escaped){escaped=false;continue;}if(c==='\\'){escaped=true;continue;}
        if(c==='"') {
          const value=strictJSON(token,life.check,4);token='';
          if(state==='key-token') {
            if(!['entries','prefix','schemaVersion'].includes(value)||keys.has(value))fail();
            keys.add(value);key=value;state='colon';
          } else {
            if(key==='prefix'?value!==expectedPrefix:value!=='offmenu-source-barcode-index-shard/1')fail();
            state='after-value';
          }
        }
        continue;
      }
      if(isSpace(c))continue;
      switch(state) {
        case 'root':if(c!=='{')fail();state='key';break;
        case 'key':if(c!=='"')fail();token='"';escaped=false;state='key-token';break;
        case 'colon':if(c!==':')fail();state='value';break;
        case 'value':
          if(key==='entries'){if(c!=='[')fail();state='first-entry';}
          else {if(c!=='"')fail();token='"';escaped=false;state='meta-token';}break;
        case 'first-entry':case 'next-entry':
          if(c===']'&&state==='first-entry'){state='after-value';break;}
          if(c!=='{')fail();token='{';depth=1;escaped=false;inString=false;state='entry';break;
        case 'after-entry':if(c===',')state='next-entry';else if(c===']')state='after-value';else fail();break;
        case 'after-value':if(c===',')state='key';else if(c==='}')state='done';else fail();break;
        default:fail(); // non-whitespace after root; no concatenated JSON accepted
      }
    }
  }
  try {
    while(true) {
      const part=await life.run(()=>reader.read());if(part.done){done=true;break;}
      if(!(part.value instanceof Uint8Array))fail();totalBytes+=part.value.byteLength;
      if(totalBytes>expectedBytes)fail();
      // A runtime decompressor can return a large native byte chunk; never turn that
      // whole chunk into a UTF-16 string. Decode/process at most64KiB at a time.
      for(let offset=0;offset<part.value.byteLength;offset+=65536) {
        await consume(decoder.decode(part.value.subarray(offset,offset+65536),{stream:true}));life.check();
      }
    }
    await consume(decoder.decode());
    if(totalBytes!==expectedBytes||state!=='done'||keys.size!==3||count!==expectedEntries)fail();
    life.check();return {entries:count,decodedBytes:totalBytes};
  } finally {if(!done)void reader.cancel().catch(()=>{});reader.releaseLock();}
}
