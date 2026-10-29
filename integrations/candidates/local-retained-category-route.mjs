// Code-owned LOCAL composition only. The caller supplies the existing runtime
// and a producer bound to a separately qualified local-application selection.
const clone=structuredClone;
const stable=x=>Array.isArray(x)?'['+x.map(stable).join(',')+']':x&&typeof x==='object'?
  '{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+stable(x[k])).join(',')+'}':JSON.stringify(x);
const same=(a,b)=>stable(a)===stable(b);
const headers={'Cache-Control':'no-store','Vary':'Cookie, Authorization','X-Content-Type-Options':'nosniff'};
const reply=(value,status=200)=>Response.json(value,{status,headers});
export function createLocalRetainedCategoryRoutes({producer,readCurrentBinding,iconAsset=null}={}){
  // Bytes are supplied from the separately accepted original SVG asset. No
  // publisher image, filesystem path, URL or new image acquisition is accepted.
  const asset=iconAsset?{...iconAsset,bytes:new Uint8Array(iconAsset.bytes)}:null;
  return async function localRetainedCategoryRoutes(request,env,{runtime}={}){
    const url=new URL(request.url);
    const icon=asset&&url.pathname===asset.publicPath;
    if(url.pathname!=='/api/local/retained-category-product'&&!icon)return null;
    if(url.origin!=='http://127.0.0.1:17645'||runtime?.mode!=='local-dev'||
      typeof runtime.assertEnvironment!=='function'||typeof runtime.verifiedUser!=='function'||
      typeof producer?.presentRetained!=='function'||typeof producer?.enrichSelected!=='function'||
      typeof readCurrentBinding!=='function')return reply({error:'LOCAL_CATEGORY_UNAVAILABLE'},503);
    if(request.method!=='GET')return reply({error:'METHOD_NOT_ALLOWED'},405);
    if(request.headers.has('Origin')&&request.headers.get('Origin')!==url.origin||
      request.headers.get('Sec-Fetch-Site')==='cross-site')return reply({error:'ORIGIN_REJECTED'},403);
    if(icon){
      try{
        runtime.assertEnvironment(env);
        const user=await runtime.verifiedUser(request);
        if(!user?.id)return reply({error:'SIGN_IN_REQUIRED'},401);
        if(url.search||!/^\/source-categories\/icons\/[a-z0-9-]+\.svg$/.test(asset.publicPath)||
          !/^[a-f0-9]{64}$/.test(asset.sha256)||!asset.rightsID||asset.bytes.length>16384)throw Error('ASSET_REQUIRED');
        const actual=[...new Uint8Array(await crypto.subtle.digest('SHA-256',asset.bytes))]
          .map(x=>x.toString(16).padStart(2,'0')).join('');
        if(actual!==asset.sha256)throw Error('ASSET_CHANGED');
        // Recheck the same original request after the asynchronous digest.
        if((await runtime.verifiedUser(request))?.id!==user.id)return reply({error:'SIGN_IN_REQUIRED'},401);
        return new Response(asset.bytes,{headers:{...headers,'Content-Type':'image/svg+xml',
          'X-OffMenu-Source-SHA256':actual,'Content-Security-Policy':"default-src 'none'; sandbox"}});
      }catch{return reply({error:'LOCAL_CATEGORY_UNAVAILABLE'},503);}
    }
    if(url.searchParams.size!==1||url.searchParams.getAll('barcode').length!==1||
      !/^[0-9]{1,64}$/.test(url.searchParams.get('barcode')||''))return reply({error:'EXACT_BARCODE_REQUIRED'},400);
    try{
      runtime.assertEnvironment(env);
      // No synthetic identity is created here. The exact existing runtime is
      // awaited by the producer on this same original Request, twice.
      const presented=await producer.presentRetained(request,{runtime,readCurrentBinding});
      const enriched=producer.enrichSelected(),retained=enriched.retainedSourceProduct;
      const association=presented.result,ref=retained.sourceProductReference;
      if(!same(association.sourceProductReference,ref)||
        association.sourceCategoryBinding?.state!=='qualified-source-type'||
        association.sourceTypePresentation?.identityEquivalence!==false||
        association.sourceTypePresentation?.productDefinitionEquivalence!==false||
        association.sourceTypePresentation?.recipeEligibility!=='unresolved')throw Error('RETAINED_DESCRIPTOR_REQUIRED');
      const presentation={schema:'offmenu-local-retained-category-presentation/1',
        sourceProductReference:clone(ref),projectionEvidence:clone(retained.projectionEvidence),
        categories:clone(retained.categories),sourceScope:clone(retained.sourceScope),
        taxonomySnapshotSHA256:retained.taxonomySnapshotSHA256,
        sourceNotice:clone(presented.sourceNotice),association:clone(association)};
      // This is a separate selected source DTO, never a public-feed record or
      // an identifier-observation/2. Unselected fields remain explicitly unknown.
      const dto={schema:'offmenu-local-retained-category-product/1',
        id:ref.productId,sourceProductReference:clone(ref),name:null,brand:null,
        detail:{fields:{categories:{state:'present',value:clone(retained.categories.sourceValue),
          fieldPointer:retained.categories.pointer,valueOrigin:'retained-source-projection',
          sourceFieldState:'original-field-presence-unknown',
          evidenceEncoding:retained.categories.evidenceEncoding,
          parsedValueEvidenceSha256:retained.categories.parsedValueEvidenceSha256}},
          retainedSourceCategoryPresentation:presentation,
          sourceBinding:clone(ref),
          canonicalCategory:null,canonicalIngredient:null,
          projectionLimitations:['Only selected source categories supplied; name, brand, nutrition, package and ingredient eligibility remain unknown.'],
          assurance:'Source category ancestry presentation only; no product identity, ingredient, recipe, Gold or country admission.'},
        provenance:{sourceId:ref.sourceId,releaseId:ref.releaseId},
        lexicalRequestGuard:{value:url.searchParams.get('barcode'),meaning:'reject-only; full source reference establishes selected record'}};
      const text=JSON.stringify(dto);
      if(new TextEncoder().encode(text).length>65536)throw Error('DTO_LIMIT');
      return new Response(text,{headers:{...headers,'Content-Type':'application/json'}});
    }catch(error){
      const code=error?.message;
      if(code==='SIGN_IN_REQUIRED')return reply({error:code},401);
      if(['DIFFERENT_SELECTED_SOURCE_REQUEST','REQUEST_CONTEXT_CHANGED','CURRENT_OPERATION_RUNTIME_MISMATCH',
        'EXACT_PRIVATE_TARGET_REQUIRED'].includes(code))return reply({error:code},403);
      return reply({error:'LOCAL_CATEGORY_UNAVAILABLE'},503);
    }
  };
}
