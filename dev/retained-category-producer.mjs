// Trusted server constructor only. Receipt bytes/pins, reader, current-runtime
// binding and verifier are never request/admin/browser supplied. No route here.
const clone=x=>structuredClone(x);
const sha=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x);
const pin=x=>x&&typeof x.path==='string'&&x.path.length>0&&sha(x.sha256);
const stable=x=>Array.isArray(x)?'['+x.map(stable).join(',')+']':x&&typeof x==='object'?
  '{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+stable(x[k])).join(',')+'}':JSON.stringify(x);
const same=(a,b)=>stable(a)===stable(b);
const fail=code=>{throw new Error(code);};
const requireThat=(value,code)=>{if(!value)fail(code);};
const digest=async bytes=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))]
  .map(x=>x.toString(16).padStart(2,'0')).join('');
async function pinnedJSON(input){
  requireThat(pin(input?.receipt)&&input.bytes instanceof Uint8Array&&input.bytes.length<=262144,'PINNED_INPUT_REQUIRED');
  const bytes=new Uint8Array(input.bytes);
  requireThat(await digest(bytes)===input.receipt.sha256,'PINNED_INPUT_SHA_MISMATCH');
  return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
}

export async function createRetainedCategoryProducer({selection,sourceScope,selectedProduct,
  categoryReader,adoption,createAdapter}={}){
  const policy=await pinnedJSON(selection),scope=await pinnedJSON(sourceScope);
  // Version 2 is the selected isolated consumer contract. Its explicit kind and
  // receipt pin cannot be inferred from an observed or normal runtime revision.
  const supportedPolicy=policy.schema==='offmenu-private-retained-category-output-selection/1'||
    (policy.schema==='offmenu-private-retained-category-output-selection/2'&&
      policy.target?.adoptedConsumerKind==='isolated-in-process-accepted-consumer'&&
      pin(policy.target.adoptedNewConsumerRuntimePin))||
    (policy.schema==='offmenu-private-retained-category-output-selection/3'&&
      policy.target?.adoptedConsumerKind==='isolated-local-application'&&
      policy.target.existingVerifierMode==='local-dev'&&
      policy.target.origin==='http://127.0.0.1:17645'&&
      pin(policy.target.adoptedNewConsumerRuntimePin));
  requireThat(supportedPolicy&&
    policy.operation==='selected-source-category-type-presentation'&&policy.outputScope==='private-local-app',
    'EXACT_PRIVATE_OPERATION_SELECTION_REQUIRED');
  requireThat(same(sourceScope.receipt,policy.sourceScope)&&
    scope.state==='SOURCE_USE_ELIGIBLE_FOR_EXACT_BOUNDED_PRIVATE_LOCAL_SOURCE_CATEGORY_PRESENTATION;NOT_RUNTIME_OR_PRODUCT_ADMISSION',
    'EXACT_SOURCE_USE_SCOPE_REQUIRED');
  requireThat(same(selectedProduct?.receipt,policy.projectionEvidence?.selectedArtifact),'SELECTED_ARTIFACT_MISMATCH');
  const product=await pinnedJSON(selectedProduct),p=product.provenance;
  const reference={productId:product.id,sourceId:p?.sourceId,releaseId:p?.releaseId,
    archiveSha256:p?.archiveSha256,sourceRow:p?.sourceRow,auditObservationSha256:p?.auditObservationSha256,
    sourceReference:clone(p?.sourceReference)};
  requireThat(product.kind==='product'&&same(reference,policy.sourceProductReference),'EXACT_SOURCE_PRODUCT_REQUIRED');
  const scoped=scope.provenance;
  requireThat(scope.product?.id===reference.productId&&scope.product.sha256===selectedProduct.receipt.sha256&&
    scope.source?.lineSHA256===policy.projectionEvidence.projectedLineSha256&&
    same(scope.categoryField?.encodingEvidence,policy.categories)&&
    scoped?.sourceId===reference.sourceId&&scoped.releaseId===reference.releaseId&&
    scoped.archiveSha256===reference.archiveSha256&&scoped.sourceRow===reference.sourceRow&&
    scoped.auditObservationSha256===reference.auditObservationSha256&&same(scoped.sourceReference,reference.sourceReference)&&
    scope.sourceSnapshotSHA256===policy.taxonomySnapshotSHA256,'SOURCE_SCOPE_RECORD_FIELD_MISMATCH');
  const keys=['nativeReference','storeSha256','ordinal','sourcePointer','rawStoredDocumentSha256','sourceQualificationSha256','role'];
  requireThat(reference.sourceReference&&Object.keys(reference.sourceReference).sort().join(',')===keys.sort().join(','),
    'GENUINE_RETAINED_REFERENCE_REQUIRED');
  const categories=product.data?.fieldEvidence?.categories?.categories;
  requireThat(categories?.state==='present'&&categories.pointer==='/data/categories'&&
    Array.isArray(categories.sourceValue)&&categories.sourceValue.length>0&&categories.sourceValue.length<=100&&
    categories.sourceValue.every(x=>typeof x==='string'&&x.length>0)&&
    same(product.data.categories,categories.sourceValue)&&same(categories,policy.categories),
    'EXACT_RETAINED_CATEGORY_FIELD_REQUIRED');
  const valueBytes=new TextEncoder().encode(JSON.stringify(categories.sourceValue));
  requireThat(categories.evidenceEncoding==='typed-exact-decimal-json/1; not an original byte-span hash'&&
    valueBytes.length===categories.evidenceBytes&&await digest(valueBytes)===categories.parsedValueEvidenceSha256,
    'PARSED_CATEGORY_VALUE_EVIDENCE_MISMATCH');
  requireThat(typeof categoryReader?.resolve==='function'&&policy.categoryNamespace==='off'&&
    sha(policy.taxonomySnapshotSHA256),'EXACT_CURRENT_CATEGORY_READER_REQUIRED');
  const envelope={schema:'offmenu-retained-product-source-categories/1',sourceProductReference:reference,
    projectionEvidence:clone(policy.projectionEvidence),categories:clone(categories),categoryNamespace:policy.categoryNamespace,
    taxonomySnapshotSHA256:policy.taxonomySnapshotSHA256,sourceScope:clone(policy.sourceScope),
    outputScope:policy.outputScope,currentOutputUse:null};
  const notice={attribution:p.attribution,license:p.license,rights:p.rights,
    sourceVisibility:p.visibility,originalSourceVisibility:p.sourceVisibility,
    originalPublisherByteSpan:'unknown',historicalTaxonomyEquivalence:false,productIdentityEquivalence:false};
  const views=categories.sourceValue.map(id=>{
    const v=categoryReader.resolve('off',id,{language:'en'});
    requireThat(v.category?.sourceNamespace==='off'&&v.category.exactCategoryID===id&&
      v.category.provenance?.sourceSnapshot?.sha256===policy.taxonomySnapshotSHA256,'CURRENT_CATEGORY_SNAPSHOT_MISMATCH');
    return {id,categoryStatus:v.category.status,sourceTypeCandidate:clone(v.sourceTypeIconCandidate)};
  });
  const policyReceipt=clone(selection.receipt),selectedAdoption=clone(adoption);
  async function beginRequest(request,{runtime,readCurrentBinding}={}){
    const url=new URL(request.url),target=policy.target;
    // A lexical query can reject a DIFFERENT selected source request; it never
    // establishes identity/equivalence. The full pinned source reference binds.
    if(url.searchParams.has('barcode'))requireThat(url.searchParams.getAll('barcode').length===1&&
      url.searchParams.get('barcode')===p.recordId,'DIFFERENT_SELECTED_SOURCE_REQUEST');
    requireThat(url.origin===target.origin&&target.environment==='local-development'&&
      target.authenticatedRequestOnly===true&&target.sameOriginalRequestSubject===true&&
      (!request.headers.has('Origin')||request.headers.get('Origin')===url.origin)&&
      request.headers.get('Sec-Fetch-Site')!=='cross-site','EXACT_PRIVATE_TARGET_REQUIRED');
    const adopted=target.adoptedNewConsumerRuntimePin;
    requireThat(sha(adopted)||pin(adopted),'ADOPTED_CONSUMER_RUNTIME_REQUIRED');
    const verifierMode=policy.schema==='offmenu-private-retained-category-output-selection/3'?'local-dev':'netlify';
    requireThat(runtime?.mode===verifierMode&&typeof runtime.verifiedUser==='function'&&
      typeof readCurrentBinding==='function','EXISTING_VERIFIER_AND_CURRENT_BINDING_REQUIRED');
    const read=async()=>{
      const binding=clone(await readCurrentBinding(request));
      requireThat(binding?.origin===target.origin&&binding.environment===target.environment&&
        same(binding.operationSelection,policyReceipt)&&same(binding.runtimePin,adopted),'CURRENT_OPERATION_RUNTIME_MISMATCH');
      const user=await runtime.verifiedUser(request);
      requireThat(typeof user?.id==='string'&&user.id.length>0&&user.id.length<200,'SIGN_IN_REQUIRED');
      return {binding,id:user.id};
    };
    const initial=await read();
    const currentOutputUse={operationSelection:clone(policyReceipt),runtimePin:clone(initial.binding.runtimePin),
      origin:target.origin,environment:target.environment};
    const expectedBase={operation:policy.operation,referenceKind:'retained-source-product',
      sourceProductReference:reference,projectionEvidence:policy.projectionEvidence,categories,
      categoryNamespace:policy.categoryNamespace,taxonomySnapshotSHA256:policy.taxonomySnapshotSHA256,
      sourceScope:policy.sourceScope,outputScope:policy.outputScope,currentOutputUse,
      categoryAdoption:policy.categoryAdoption};
    return {currentOutputUse:clone(currentOutputUse),async authorizeOutput(originalRequest,expected){
      requireThat(originalRequest===request,'ORIGINAL_REQUEST_REQUIRED');
      requireThat(same(expected,expectedBase),'EXACT_CATEGORY_OPERATION_BINDING_REQUIRED');
      const fresh=await read();requireThat(fresh.id===initial.id&&same(fresh.binding,initial.binding),'REQUEST_CONTEXT_CHANGED');
      return {permitted:true,current:true,binding:clone(expected),receipt:clone(policyReceipt)};
    }};
  }
  return Object.freeze({
    enrichSelected(){return {retainedSourceProduct:clone(envelope),sourceNotice:clone(notice),
      currentCategoryReadback:clone(views),qualification:'source-use-eligible retained field/current source-category candidates only; current output not admitted'};},
    beginRequest,
    async presentRetained(request,context,view={}){
      requireThat(typeof createAdapter==='function','RETAINED_ADAPTER_FACTORY_REQUIRED');
      const bound=await beginRequest(request,context),candidate=clone(envelope);
      candidate.currentOutputUse=clone(bound.currentOutputUse);let expected;
      const make=qualifySourceCategory=>createAdapter({categoryReader,adoption:selectedAdoption,qualifySourceCategory});
      const first=make(binding=>{expected=clone(binding);return null;});
      requireThat(typeof first.resolveRetainedSourceProduct==='function','RETAINED_ADAPTER_METHOD_REQUIRED');
      const fallback=first.resolveRetainedSourceProduct(clone(view),{retainedSourceProduct:candidate});
      if(!expected)return {result:fallback,sourceNotice:clone(notice),decision:'not-requested'};
      const decision=await bound.authorizeOutput(request,expected);
      const result=make(binding=>same(binding,expected)?clone(decision):null)
        .resolveRetainedSourceProduct(clone(view),{retainedSourceProduct:candidate});
      return {result,sourceNotice:clone(notice),decision:'current exact server decision checked'};
    }
  });
}
