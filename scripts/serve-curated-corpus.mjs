import {readFile} from 'node:fs/promises';
import {resolve,sep} from 'node:path';
import {createServer} from 'node:http';
import {createEngine} from '../corpus/engine.mjs';
const [release,port='8891']=process.argv.slice(2);if(!release)throw Error('Usage: node scripts/serve-curated-corpus.mjs release-directory [port]');
const root=resolve(release,'blobs');
const engine=await createEngine(async key=>{const file=resolve(root,key);if(!file.startsWith(root+sep))throw Error('Invalid blob path');try{return await readFile(file);}catch(e){if(e.code==='ENOENT')return null;throw e;}});
createServer(async(req,res)=>{try{const url=new URL(req.url,'http://localhost');if(req.method!=='GET'||!['/v1/corpus/manifest','/v1/corpus/records'].includes(url.pathname)){res.writeHead(404);res.end();return;}
 const body=url.pathname.endsWith('/manifest')?engine.manifest:await engine.lookup(Object.fromEntries(url.searchParams));res.writeHead(200,{'Content-Type':'application/json'});res.end(JSON.stringify(body));
}catch(e){res.writeHead(400,{'Content-Type':'application/json'});res.end(JSON.stringify({error:e.message}));}}).listen(Number(port),'127.0.0.1',()=>console.log('Local OffMenu curation engine: http://127.0.0.1:'+port));
