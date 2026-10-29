import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {readFileSync} from 'node:fs';
import {ACTORS,publicActor,identityToken,RESPONSES,EMPTY,BROWSER_SCRIPTS} from './fixtures.mjs';
export const CONTRACTS=JSON.parse(readFileSync(new URL('./contracts.json',import.meta.url),'utf8'));
const stableId=value=>{const s=createHash('sha256').update(value).digest('hex');return `${s.slice(0,8)}-${s.slice(8,12)}-4${s.slice(13,16)}-8${s.slice(17,20)}-${s.slice(20,32)}`;};
const json=(body,status=200)=>({status,jsonBody:body,headers:{'Content-Type':'application/json','X-OffMenu-Dev-Mock':'wiremock'}});
const scenarioResponse=(normal,id,scenario)=>scenario==='error'?json({error:'Synthetic provider failure'},503):scenario==='rate-limit'?{...json({error:'Synthetic rate limit'},429),headers:{'Content-Type':'application/json','Retry-After':'1'}}:scenario==='auth'?json({error:'Synthetic rejected credentials'},401):scenario==='timeout'?{...normal,fixedDelayMilliseconds:5000}:scenario==='empty'?json(EMPTY[id]||{}):scenario==='unknown-barcode'&&id==='off'?json(EMPTY.off):normal;
function request(contract,path,method,scenario){return {method,urlPathPattern:path,headers:{'X-OffMenu-Upstream-Host':contract.hostPattern?{matches:contract.hostPattern}:{equalTo:contract.hosts[0]},'X-OffMenu-Scenario':{equalTo:scenario}}};}
export function createMappings(){
 const mappings=[{id:stableId('health'),metadata:{offmenuDevelopment:true},request:{method:'GET',urlPath:'/__offmenu_fixture_health'},response:json({kind:'offmenu-local-wiremock',schemaVersion:1})}];
 const add=(name,req,response,priority=10)=>mappings.push({id:stableId(name),name,priority,metadata:{offmenuDevelopment:true},request:req,response});
 for(const c of CONTRACTS.http){
  if(c.id==='corpus')continue;
  if(c.id==='identity'){
   for(const s of CONTRACTS.scenarios){
    const settings=json({external:{email:true,google:true},disable_signup:false,autoconfirm:false});
    add('identity-settings-'+s,request(c,'/\\.netlify/identity/settings','GET',s),scenarioResponse(settings,c.id,s));
    for(const [id,actor] of Object.entries(ACTORS)){
     const req=request(c,'/\\.netlify/identity/user','GET',s);req.headers.Authorization={equalTo:'Bearer '+actor.token};
     add('identity-user-'+id+'-'+s,req,scenarioResponse(json(publicActor(actor)),c.id,s),5);
     for(const kind of ['password','refresh_token']){
      const login=request(c,'/\\.netlify/identity/token','POST',s);
      login.bodyPatterns=[{contains:kind==='password'?'username='+encodeURIComponent(actor.email):'refresh_token='+actor.refreshToken}];
      add('identity-token-'+id+'-'+kind+'-'+s,login,scenarioResponse(json(identityToken(id)),c.id,s),5);
     }
    }
    add('identity-no-user-'+s,request(c,'/\\.netlify/identity/user','GET',s),json({error:'Unknown synthetic token'},401),20);
    add('identity-no-token-'+s,request(c,'/\\.netlify/identity/token','POST',s),json({error:'Unknown synthetic actor'},401),20);
    for(const path of ['logout','recover','verify'])add('identity-'+path+'-'+s,request(c,'/\\.netlify/identity/'+path,'POST',s),scenarioResponse(json({}),c.id,s));
    add('identity-signup-'+s,request(c,'/\\.netlify/identity/signup','POST',s),scenarioResponse(json(publicActor(ACTORS.alice),201),c.id,s));
    add('identity-update-'+s,request(c,'/\\.netlify/identity/user','PUT',s),json({error:'Synthetic profile update not yet agreed with Google IDP owner'},501));
    for(const path of ['authorize','callback'])add('identity-'+path+'-'+s,request(c,'/\\.netlify/identity/'+path,'GET',s),json({error:'Google browser OAuth is owned by IDP; this is not a Google login mock'},501));
   }
   continue;
  }
  for(const s of CONTRACTS.scenarios)for(const path of c.paths)for(const method of c.methods){
   const normal=BROWSER_SCRIPTS[c.id]?{status:200,body:BROWSER_SCRIPTS[c.id],headers:{'Content-Type':'application/javascript','X-OffMenu-Dev-Mock':'wiremock'}}:json(RESPONSES[c.id]||{});
   add(c.id+'-'+path+'-'+method+'-'+s,request(c,path,method,s),scenarioResponse(normal,c.id,s));
  }
  if(c.id==='off'){
   const req=request(c,'/api/v2/product/9999999999999\\.json','GET','success');
   add('off-unknown-barcode',req,json(EMPTY.off),1);
  }
 }
 // A small valid, checksummed corpus is authored here, not copied from a public dataset.
 const corpus=CONTRACTS.http.find(c=>c.id==='corpus'),blobs=new Map(),key='off:product:fixture-oats',shard=createHash('sha256').update(key).digest('hex').slice(0,3);
 const entry={id:0,source:'off',key,shard,countries:['AU'],kinds:['product']};
 const record={schemaVersion:'1.0',id:key,kind:'product',countries:['AU'],provenance:{sourceId:'off',visibility:'public',license:'ODbL',attribution:'Synthetic development fixture, not an OFF observation'},curation:{schema:'offmenu-curation/1',rawSourcePayloadPublished:false},data:{name:'Fixture oats'}};
 const blob=(name,value)=>blobs.set(name,gzipSync(Buffer.from(value)));
 blob('entries-0.json.gz',JSON.stringify([entry]));blob('records/off/'+shard+'.jsonl.gz',JSON.stringify([key,[record]])+'\n');blob('countries/off/AU-all.json.gz',JSON.stringify([0]));
 for(const [namespace,term] of [['terms','fixture'],['barcodes','0000000000001']])blob(namespace+'/'+createHash('sha256').update(term).digest('hex').slice(0,3)+'.jsonl.gz',JSON.stringify([term,{off:[0]}])+'\n');
 const manifest={format:'offmenu-curated/1',status:'curated-release-ready',privateProviderData:false,acquisitionAtRuntime:false,releaseId:'fixture-wiremock',manifestSha256:'fixture-wiremock',entryPageSize:100,shardLength:3,curatedAcceptance:{status:'all-curated-records-exercised'},sources:{off:{sourceId:'off',entryRange:[0,1],records:1,license:'ODbL',countryIndex:true}},files:[...blobs].map(([key,bytes])=>({key,bytes:bytes.length,sha256:createHash('sha256').update(bytes).digest('hex')}))};
 const empty={...manifest,sources:{},files:[]};
 for(const s of CONTRACTS.scenarios){
  for(const p of ['/manifest\\.json','/recipes/manifest\\.json'])add('corpus-'+p+'-'+s,request(corpus,p,'GET',s),scenarioResponse(json(s==='empty'?empty:manifest),'corpus',s));
  for(const [name,bytes] of blobs)add('corpus-'+name+'-'+s,request(corpus,'/releases/fixture-wiremock/'+name.replaceAll('.','\\.'),'GET',s),scenarioResponse({status:200,base64Body:bytes.toString('base64'),headers:{'Content-Type':'application/octet-stream'}},'corpus',s));
 }
 return mappings;
}
