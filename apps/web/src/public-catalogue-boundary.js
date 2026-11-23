// Public catalogues require one admitted unified Gold release. No release is
// bound here. Do not use an environment flag, caller identity, or provider
// selector to open these legacy public paths. Private, owned paths are separate.
export const PUBLIC_CATALOGUE_UNAVAILABLE='catalogue_unavailable';

const held=new Set([
 '/api/product','/api/prices','/api/recipes',
 '/api/data/public','/api/data/coverage','/api/data/sources',
 '/api/catalogue/coverage','/api/catalogue/records','/api/catalogue/country',
 '/api/catalogue/calculate','/api/catalogue/compare','/api/catalogue/enrich',
 '/afcd-nutrient-details.json','/recipes.json'
]);
const heldFamilies=['/recipes','/__dev/identifiers','/api/off-photos'];

export function isPublicCatalogueHeld(pathname){
 return held.has(pathname)||heldFamilies.some(prefix=>pathname===prefix||pathname.startsWith(prefix+'/'));
}

// The public shelf retains lexical and receipt behavior. Its normal mounted
// transport cannot open the retired adapters used by detached private tests.
export async function heldPublicIdentifier(raw,generation,cursor,symbology,namespace){
 return {original:raw,generation,requestCursor:cursor,symbology,namespace,
  status:'unavailable',matches:[],hasMore:false,error:PUBLIC_CATALOGUE_UNAVAILABLE};
}

export async function heldPublicDetails(){
 return {status:'unavailable',availability:'unavailable',variants:[],reasonCode:PUBLIC_CATALOGUE_UNAVAILABLE};
}
