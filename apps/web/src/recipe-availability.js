// Availability of these two local application reads, not proof of unified
// Gold coverage or an authoritative no-match beyond what was loaded.
export async function readRecipeAvailability(read,validateRow=row=>row){
 const paths=['/recipes.json?v=i18n-1','/api/recipes'];
 const reads=await Promise.allSettled(paths.map(async path=>{
  const rows=await read(path);
  if(!Array.isArray(rows))throw Error('Invalid recipe collection');
  const accepted=[];
  for(const row of rows){
   try{
    const valid=validateRow(row);
    if(typeof valid?.id!=='string'||!valid.id)throw Error('Invalid recipe identity');
    accepted.push(valid);
   }catch{}
  }
  return {rows:accepted,complete:accepted.length===rows.length};
 }));
 const usable=reads.flatMap(result=>result.status==='fulfilled'?[result.value]:[]);
 const recipes=[...new Map(usable.flatMap(result=>result.rows).map(row=>[row.id,row])).values()];
 const loaded=usable.length===paths.length&&usable.every(result=>result.complete);
 const showable=usable.some(result=>result.complete||result.rows.length>0);
 return {recipes,status:loaded?'loaded':showable?'partial':'unavailable'};
}
