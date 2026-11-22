// Availability of these two local application reads, not proof of unified
// Gold coverage or an authoritative no-match beyond what was loaded.
export async function readRecipeAvailability(read){
 const paths=['/recipes.json?v=i18n-1','/api/recipes'];
 const reads=await Promise.allSettled(paths.map(async path=>{
  const rows=await read(path);
  if(!Array.isArray(rows))throw Error('Invalid recipe collection');
  return rows;
 }));
 const success=reads.filter(result=>result.status==='fulfilled');
 const recipes=[...new Map(success.flatMap(result=>result.value).map(row=>[row?.id,row])).values()];
 return {recipes,status:success.length===paths.length?'loaded':success.length?'partial':'unavailable'};
}
