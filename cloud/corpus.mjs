import {decodeStoredRecord} from './provider-data.mjs';

export const CORPUS_SOURCES=new Set(['off','prices','wikibooks','usda-files']);
export function corpusDatabase(env,source){return source==='off'?env.PRODUCT_CORPUS:source==='usda-files'?env.NUTRIENT_CORPUS:env.CORPUS;}
export async function corpusCoverage(env){
 const result=[];
 for(const database of new Set([env.CORPUS,env.PRODUCT_CORPUS,env.NUTRIENT_CORPUS].filter(Boolean))){
  const rows=await database.prepare('SELECT r.source_id,r.release_id,r.document FROM corpus_releases r JOIN corpus_active a ON a.source_id=r.source_id AND a.release_id=r.release_id').all();
  for(const row of rows.results){const m=JSON.parse(row.document);result.push({source_id:row.source_id,releaseId:row.release_id,records:m.publishedRecords,scope:m.scope,status:'published normalized release',independentAcceptance:false,rawCounts:m.counts||{raw:m.rawRows},license:m.license});}
 }
 return result;
}
export async function corpusLookup(env,{source,query='',barcode='',kind='',country='',cursor='',limit=20}){
 const database=corpusDatabase(env,source);
 if(!CORPUS_SOURCES.has(source)||!database)return null;
 if(query.length>100||new TextEncoder().encode(query).length>48||cursor.length>300||kind&&!/^[A-Za-z]+$/.test(kind)||country&&!/^[A-Z]{2}$/.test(country))throw Error('Invalid collection filter');
 if(barcode&&!/^\d{4,32}$/.test(barcode))throw Error('Invalid barcode');
 const release=await database.prepare('SELECT r.release_id,r.document FROM corpus_active a JOIN corpus_releases r ON r.source_id=a.source_id AND r.release_id=a.release_id WHERE a.source_id=?').bind(source).first();
 if(!release)return null;
 const manifest=JSON.parse(release.document),size=Math.max(1,Math.min(100,Number(limit)||20));
 const search=query.normalize('NFKD').toLowerCase().replace(/\p{M}/gu,'');
 // Parameters always bind; literal wildcard characters cannot broaden searches.
 const pattern='%'+search.replace(/[\\%_]/g,c=>'\\'+c)+'%';
 const clauses=['source_id=?','release_id=?','id>?'],params=[source,release.release_id,cursor];
 if(barcode){clauses.push('barcode=?');params.push(barcode);}
 if(kind){clauses.push('kind=?');params.push(kind);}
 if(search){clauses.push("search_text LIKE ? ESCAPE '\\'");params.push(pattern);}
 const rows=await database.prepare('SELECT id,document FROM corpus_records WHERE '+clauses.join(' AND ')+' ORDER BY id LIMIT ?').bind(...params,size+1).all();
 const selected=rows.results.slice(0,size),decoded=await Promise.all(selected.map(r=>decodeStoredRecord(r.document)));
 const records=decoded.filter(r=>!country||!r.countries.length||r.countries.includes(country));
 return {schemaVersion:'1.0',source,records,nextCursor:rows.results.length>size?selected.at(-1).id:null,withheld:selected.length-records.length,
  releaseId:release.release_id,sourceTerms:manifest.license,countryFilter:country||null,
  coverage:{scope:manifest.scope,publishedRecords:manifest.publishedRecords,returned:records.length,
   notice:'Complete named release ingestion; a filtered page does not establish complete country coverage. Source assertions and recipes still require review.'}};
}
