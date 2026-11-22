// Describes the existing personal GET routes only. This document grants no
// access and does not add validation to their runtime query or response paths.
const kinds=['inventory','plans','history','directory','data','health','baskets','evidence'];
const array={type:'array',items:{}};
const cursor={type:['string','null'],description:'Opaque last scanned ID, or null when no later page remains. Continue even when a rights-filtered page contains no records.'};
const scope={type:'string',const:'private account'};

function responseSchema(kind){
  if(kind==='data')return {
    type:'object',required:['schemaVersion','records','nextCursor','withheld','scope'],
    properties:{schemaVersion:{type:'string',const:'1.0'},records:array,nextCursor:cursor,
      withheld:{type:'integer',minimum:0,description:'Rows withheld from this scanned page by export rights or country filtering.'},scope}
  };
  if(['health','baskets','evidence'].includes(kind))return {
    type:'object',required:['documents','nextCursor','scope'],
    properties:{documents:{type:'array',items:{type:'object',required:['id','revision','updatedAt','data'],
      properties:{id:{type:'string'},revision:{type:'integer'},updatedAt:{type:'string'},data:{}}}},nextCursor:cursor,scope}
  };
  const data=kind==='history'?{type:'object',required:['food','cleanup'],properties:{food:array,cleanup:array}}
    :kind==='directory'?{type:'object',required:['locations','recipes'],properties:{locations:array,recipes:array}}:array;
  return {type:'object',required:['version','revision','updatedAt','data'],
    properties:{version:{type:'integer',const:1},revision:{type:'integer'},updatedAt:{type:['string','null']},data}};
}

function parameters(kind){
  if(kind==='plans'||kind==='history')return ['from','to'].map(name=>({name,in:'query',
    description:'Inclusive date boundary. Send YYYY-MM-DD; the REST implementation compares strings without calendar validation.',
    schema:{type:'string',format:'date'}}));
  if(!['data','health','baskets','evidence'].includes(kind))return [];
  const page=[{name:'cursor',in:'query',description:'Opaque cursor returned by the preceding page. Omit for the first page.',schema:{type:'string'}},
    {name:'limit',in:'query',description:'Requested scanned page size. Omitted, non-numeric and zero values default to 100; other numeric values are clamped to 1–1000. Send an integer.',schema:{type:'integer',minimum:1,maximum:1000,default:100}}];
  if(kind==='data')page.push(
    {name:'kind',in:'query',description:'Exact normalized record-kind filter.',schema:{type:'string'}},
    {name:'source',in:'query',description:'Exact provenance source ID filter.',schema:{type:'string'}},
    {name:'country',in:'query',description:'Country/market used for export rights and record-country filtering. Filtering may leave an empty page with a non-null cursor.',schema:{type:'string'}});
  return page;
}

export function personalOpenAPI(origin){
  return {openapi:'3.1.0',info:{title:'offmenu personal kitchen API',version:'1.0.0'},servers:[{url:origin}],
    components:{securitySchemes:{personalToken:{type:'http',scheme:'bearer'}}},security:[{personalToken:[]}],
    paths:Object.fromEntries(kinds.map(kind=>['/api/v1/'+kind,{get:{summary:'Read your '+kind,
      description:'Requires '+kind+':read. Token audience must be /api/v1. Responses contain saved account data, not unsaved browser edits. Record content and nested document data remain source-specific; missing values are not zero.',
      parameters:parameters(kind),responses:{200:{description:kind==='data'?'Rights-filtered normalized records from the scanned page':
        ['health','baskets','evidence'].includes(kind)?'Owner-scoped document page':'Versioned personal records',
        content:{'application/json':{schema:responseSchema(kind)}}},
      401:{description:'Invalid, expired, revoked or wrong-audience token'},403:{description:'Required scope missing'},
      405:{description:'Only GET is supported for personal API resources'},503:{description:'Integration storage unavailable'}}}}]))};
}
