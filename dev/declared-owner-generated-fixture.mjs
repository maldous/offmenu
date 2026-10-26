import {SOURCE_IDS, createOwnedSnapshotExtractor} from '../cloud/owned-snapshot-extractor.mjs';
import {validatePrivatePayload, digest} from '../cloud/private-portability-v1.mjs';
export const now = 1800000000000, at = new Date(now).toISOString();
const copy = v => structuredClone(v);
// Two code-owned GENERATED declarations, selected before any records exist.
// A verified principal is never rewritten or inferred from email/other lab IDs.
const DECLARATIONS=Object.freeze({
  'legacy-generated-owner':Object.freeze({ownerUserId:'synthetic-owner',namespace:'synthetic-instance',
    issuer:'https://synthetic.invalid/issuer',subject:'opaque-subject'}),
  'isolated-local-testuser':Object.freeze({ownerUserId:'local-dev:testuser',namespace:'synthetic-local-testuser-instance',
    issuer:'https://synthetic.invalid/local-lab-fixture',subject:'declared-local-testuser-fixture-subject'})
});
export function fixture({documents = 2,ownerDeclaration='legacy-generated-owner'} = {}) {
  if(!Object.hasOwn(DECLARATIONS,ownerDeclaration))throw Error('EXPLICIT_GENERATED_OWNER_DECLARATION_REQUIRED');
  const declared=DECLARATIONS[ownerDeclaration],owner=declared.ownerUserId,namespace=declared.namespace;
  const provenance = {sourceId:'generated-fixture',version:'1',recordId:'generated',recordedAt:at};
  const rec = (type,id,data,kitchen=null) => ({type,id,data,ownerRef:owner,householdRef:kitchen,
    revision:1,provenance:copy(provenance),extensions:[],lifecycle:'active'});
  const native = [rec('space','kitchen-a',{label:'Synthetic kitchen'},'kitchen-a'),
    rec('profile','profile-a',{displayName:'Synthetic profile',dietary:null,allergies:[],preferences:null,diagnoses:null}),
    rec('connection_metadata','native-connection',{providerId:'synthetic-provider',authentication:'unknown',
      toolProtocol:'unknown',capabilities:[],scopes:[],sourceStatus:'revoked',requiresReauthorization:true})];
  const fields = ['inventory','profile.full','settings','content','auth_metadata','history',
    'derived_provenance','attachments','relationships','extensions'];
  const identity = {ownerUserId:owner,issuer:declared.issuer,subject:declared.subject};
  const a = {namespace,principal:{id:owner},identity,revision:3,
    auth:{reauthenticatedAt:now-1,expiresAt:now+100000,revokedAt:null},
    consent:{id:'synthetic-current-consent',revision:2,ownerUserId:owner,recipient:copy(identity),
      purpose:'owned-backup',choice:'granted',revokedAt:null,validFrom:now-10,expiresAt:now+100000,fields},
    kitchens:['kitchen-a'],allowedRecords:native.map(r=>JSON.stringify([r.type,r.id])),tombstones:[]};
  const rows = Object.fromEntries(SOURCE_IDS.map(id=>[id,[]])); rows.nativeRecords=native;
  rows.legacyUserState=[{user_id:owner,revision:7,updated_at:at,state_json:JSON.stringify({profile:{servings:2,
    unknownFuture:{exactDecimal:'0.000001',unknown:null}},inventory:[{id:'legacy-lot',quantity:null,unit:'package'}]})}];
  rows.ownedKitchenState=[{id:'kitchen-a',owner_user_id:owner,revision:8,updated_at:at,
    state_json:JSON.stringify({inventory:[],profile:{members:[]}})}];
  rows.privateDocuments=Array.from({length:documents},(_,i)=>({owner,kind:['health','settings','evidence','baskets'][i%4],
    id:'document-'+String(i).padStart(5,'0'),revision:4,updated_at:at,
    document:JSON.stringify({records:[{id:'synthetic-measurement-'+i,value:null,unit:'unknown'}],
      consent:{version:'offmenu-health/1',acceptedAt:at,purpose:'private measurement history'},futureField:'preserved'})}));
  rows.privateRecords=[{owner,id:'synthetic-private-source-record',kind:'product',source_id:'synthetic-source',countries:'[]',
    updated_at:at,document:JSON.stringify({provenance:{sourceId:'synthetic-source',sourceLanguage:'en',license:'synthetic-only'},data:{name:'Synthetic record',quantity:null}})}];
  rows.safeConnections=[{user_id:owner,source_id:'synthetic-provider',label:'Synthetic connection',updated_at:at}];
  const sources = SOURCE_IDS.map(id=>({id,status:rows[id].length?'present':'absent',revision:'source-1',count:rows[id].length}));
  const state={authority:a,rows,sources,revision:'snapshot-1',closed:0,pages:[],reads:0,
    onPage:null,onAuthority:null,onClose:null,onRevision:null,onAuthorize:null};
  const snapshot={ownerUserId:owner,namespace,revision:state.revision,sources,
    async readPage(q) {
      state.pages.push(copy(q));
      const offset=q.cursor===null?0:Number(q.cursor), source=state.sources.find(s=>s.id===q.sourceId);
      const selected=state.rows[q.sourceId].slice(offset,offset+q.limit);
      const out={ownerUserId:owner,namespace,snapshotRevision:'snapshot-1',sourceRevision:source.revision,
        rows:copy(selected),nextCursor:offset+q.limit<state.rows[q.sourceId].length?String(offset+q.limit):null,withheld:0};
      if(state.onPage)await state.onPage(q,out);return out;
    },
    async readRevision(){if(state.onRevision)await state.onRevision();return {revision:state.revision,sources:copy(state.sources)};},
    async close(){state.closed++;if(state.onClose)await state.onClose();}
  };
  const api=createOwnedSnapshotExtractor({readAuthority:async q=>{state.reads++;if(state.onAuthority)await state.onAuthority(q);return copy(state.authority);},
    openSnapshot:async()=>snapshot,authorizeSourceRecord:async q=>state.onAuthorize?await state.onAuthorize(q):true,
    validatePayload:validatePrivatePayload,digest,clock:()=>now});
  return {state,snapshot,run:()=>api.extractOwnedSnapshot({packageId:'synthetic-package'})};
}
