// Source facts remain separate assertions. This module performs no I/O,
// canonical mapping, physical-product resolution, image loading or publication.
import {validGTIN,validSourceObservationReference} from '../scanner-identity-v2.js';
import {validateClassificationProjection,unresolvedProjection} from '../source-classification-contract.mjs';

export const SOURCE_ASSERTIONS_SCHEMA='offmenu-local-source-assertions/1';
const hex=value=>typeof value==='string'&&/^[a-f0-9]{64}$/.test(value);
const object=value=>value!==null&&typeof value==='object'&&!Array.isArray(value);
const encode=new TextEncoder();
const nativeKeys=['run_id','input_id','record_ordinal','assertion_id'];
const bindingKeys=['observationKey','sourceObservation','sourceBinding','referenceRecordId','exactObservationBridge'];
const sourceKeys=['sourceId','releaseId','identifierInputId','identifierAssetSha256',
  'identifierRecordOrdinal','identifierSourceRecordId','identifierNativeRecordId',
  'originalSha256','inputAssetSha256','recordPointer','recordPointers','recordSha256',
  'rightsReceiptSha256','operationReceiptSha256','custodyReceiptSha256',
  'productReference','componentDigests','backingRole'];
const fieldsMap={name:'name',names:'names',brand:'brand',packageQuantity:'pack',
  servingQuantity:'serving',dataType:'dataType',ingredientDeclaration:'ingredientsText',
  categories:'categories',sourceAllergenClaims:'allergens',sourceTraceClaims:'traces',
  sourceDietaryLabelClaims:'labels',origins:'origins',manufacturingPlaces:'manufacturingPlaces',
  rawNutriments:'rawNutriments',nutritionSourceBasis:'nutritionSourceBasis',
  nutrientProfile:'nutrientProfile',imageUrlReferences:'imageUrlReferences'};
const publicFields=[...Object.keys(fieldsMap),'markets','sourceProvenance'];
function requireThat(value,code){if(!value)throw Error(code);}
function stable(value){
  if(Array.isArray(value))return '['+value.map(stable).join(',')+']';
  if(object(value))return '{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+stable(value[k])).join(',')+'}';
  return JSON.stringify(value);
}
function copy(value,depth=0,budget={nodes:0}){
  requireThat(++budget.nodes<=20000&&depth<=24,'LOCAL_ASSERTION_STRUCTURE_BOUND');
  if(value===null||typeof value==='boolean'||typeof value==='number'&&Number.isFinite(value))return value;
  if(typeof value==='string'){requireThat(encode.encode(value).length<=131072,'LOCAL_ASSERTION_STRING_BOUND');return value;}
  if(Array.isArray(value)){requireThat(value.length<=4096,'LOCAL_ASSERTION_ARRAY_BOUND');return value.map(v=>copy(v,depth+1,budget));}
  requireThat(object(value)&&[Object.prototype,null].includes(Object.getPrototypeOf(value)),'LOCAL_ASSERTION_JSON_REQUIRED');
  return Object.fromEntries(Object.entries(value).map(([k,v])=>{
    requireThat(encode.encode(k).length<=4096,'LOCAL_ASSERTION_KEY_BOUND');return [k,copy(v,depth+1,budget)];
  }));
}
function bounded(value){requireThat(encode.encode(JSON.stringify(value)).length<=262144,'LOCAL_ASSERTION_OUTPUT_BOUND');return value;}

// The current owner supplies an already eligible representation and its exact
// expected native binding. Structural equality is not a source-use grant.
export function createSourceAssertion(input,{expectedReference,expectedBinding,expectedClassificationProjection}={}){
  const ref=input?.sourceObservationReference,binding=input?.binding,source=binding?.sourceBinding;
  requireThat(validSourceObservationReference(ref,ref?.originalLexicalValue)&&ref.namespace==='barcode'&&
    validGTIN(ref.originalLexicalValue),'LOCAL_ASSERTION_REFERENCE_INVALID');
  requireThat(stable(ref)===stable(expectedReference),'LOCAL_ASSERTION_EXPECTED_REFERENCE_MISMATCH');
  requireThat(object(source)&&object(expectedBinding),'LOCAL_ASSERTION_EXPECTED_BINDING_REQUIRED');
  for(const key of sourceKeys)requireThat(Object.hasOwn(expectedBinding,key)&&
    stable(source[key])===stable(expectedBinding[key]),'LOCAL_ASSERTION_BINDING_'+key);
  for(const key of ['profileReference','subsetCertificateSha256','backingStoreSha256'])
    if(Object.hasOwn(expectedBinding,key)&&!expectedBinding[key]?.captureState)
      requireThat(stable(source[key])===stable(expectedBinding[key]),'LOCAL_ASSERTION_BINDING_'+key);
  requireThat(source.sourceId===ref.sourceId&&source.releaseId===ref.releaseId&&
    source.identifierInputId===ref.observationKey.input_id&&
    source.identifierRecordOrdinal===ref.observationKey.record_ordinal&&
    source.identifierSourceRecordId===ref.sourceRecordId,'LOCAL_ASSERTION_SOURCE_IDENTITY');
  requireThat(binding.observationKey?.databaseSha256===ref.databaseSha256,'LOCAL_ASSERTION_DATABASE_BINDING');
  for(const key of nativeKeys)requireThat(binding.observationKey[key]===ref.observationKey[key],
    'LOCAL_ASSERTION_OBSERVATION_'+key);
  requireThat(binding.sourceObservation?.source_id===ref.sourceId&&
    binding.sourceObservation?.release_id===ref.releaseId&&
    binding.sourceObservation?.namespace===ref.namespace&&
    binding.sourceObservation?.lexical_value===ref.sourceLexicalValue,'LOCAL_ASSERTION_SOURCE_OBSERVATION');
  requireThat(binding.sourceObservation?.artifact_sha256===source.identifierAssetSha256&&
    binding.sourceObservation?.native_record_id===source.identifierNativeRecordId&&
    binding.sourceObservation?.record_ordinal===source.identifierRecordOrdinal&&
    binding.sourceObservation?.source_record_id===ref.sourceRecordId,'LOCAL_ASSERTION_RECORD_LINEAGE');
  for(const key of ['originalSha256','inputAssetSha256','recordSha256','rightsReceiptSha256',
    'operationReceiptSha256','custodyReceiptSha256'])requireThat(hex(source[key]),'LOCAL_ASSERTION_DIGEST_'+key);
  requireThat(object(source.componentDigests)&&Object.keys(source.componentDigests).length>0&&
    Object.values(source.componentDigests).every(hex),'LOCAL_ASSERTION_COMPONENT_DIGESTS');
  const provenance=input.fields?.sourceProvenance;
  requireThat(provenance?.state==='present'&&provenance.value?.visibility==='public'&&
    provenance.value.sourceId===source.sourceId,'LOCAL_ASSERTION_PUBLIC_PROVENANCE_REQUIRED');
  for(const [key,expected]of [['archiveSha256',source.originalSha256],['releaseId',source.releaseId],
    ['sourceRow',source.identifierRecordOrdinal]])if(Object.hasOwn(provenance.value,key))
      requireThat(provenance.value[key]===expected,'LOCAL_ASSERTION_PROVENANCE_'+key);
  requireThat(object(input.fields),'LOCAL_ASSERTION_FIELDS_REQUIRED');
  const fields={};
  for(const name of publicFields)if(Object.hasOwn(input.fields,name)){
    const field=input.fields[name];requireThat(object(field)&&typeof field.state==='string','LOCAL_ASSERTION_FIELD_ENVELOPE');
    // A held value must not enter this public representation. Keep the normal
    // reader available; the caller can report this local assertion's refusal.
    requireThat(!['restricted','rights-held'].includes(field.state)||field.value==null,'LOCAL_ASSERTION_RESTRICTED_VALUE');
    fields[name]=copy(field);
  }
  const classificationBinding={sourceRecordId:source.identifierNativeRecordId,snapshotSha256:source.originalSha256,
    sourceObservationReference:copy(ref),inputAssetSha256:source.inputAssetSha256,recordSha256:source.recordSha256,
    componentDigests:copy(source.componentDigests)};
  let classificationProjection=unresolvedProjection(classificationBinding);
  if(input.classificationProjection){
    validateClassificationProjection(input.classificationProjection);
    requireThat(stable(input.classificationProjection)===stable(expectedClassificationProjection),
      'LOCAL_ASSERTION_CLASSIFICATION_EXPECTED_INPUT');
    requireThat(input.classificationProjection.sourceBinding.sourceRecordId===classificationBinding.sourceRecordId&&
      input.classificationProjection.sourceBinding.snapshotSha256===classificationBinding.snapshotSha256&&
      stable(input.classificationProjection.sourceBinding.sourceObservationReference)===stable(ref),
      'LOCAL_ASSERTION_CLASSIFICATION_SOURCE_BINDING');
    // Shared structural validation/equality is not semantic admission. The
    // owning producer must have verified the existing backing/admission pins.
    classificationProjection=copy(input.classificationProjection);
  }
  return bounded({schema:'offmenu-local-source-assertion/1',sourceObservationReference:copy(ref),
    binding:Object.fromEntries(bindingKeys.filter(k=>Object.hasOwn(binding,k)).map(k=>[k,copy(binding[k])])),fields,classificationProjection,
    identity:{namespace:'barcode',lexicalValue:ref.originalLexicalValue,identifierValidation:'valid-exact-GTIN',
      relationship:'separate-attributed-source-assertion',productVariantEquivalence:'unresolved'},
    sourceState:'upstream-projection; original field presence and numeric lexemes may be unknown',
    nutritionBasisRelationship:'raw source basis and projected profile basis remain separate; applicability unverified',
    imageReferenceMeaning:'Metadata only; no display grant or external image request',
    imageReferenceCapture:Object.hasOwn(fields,'imageUrlReferences')?'supplied-envelope':'not-captured-in-selected-input'});
}

// Decorate an already completed LOCAL producer response. Never change a curated
// record, its manifest, or the meaning of the published release's payload.
export function decoratePublicPayload(payload,{assertions=[],selection,lexicalValue}={}){
  requireThat(object(selection)&&hex(selection.manifestSha256)&&typeof selection.releaseId==='string',
    'LOCAL_ASSERTION_PUBLIC_SELECTION_REQUIRED');
  requireThat(payload?.releaseId===selection.releaseId&&payload.manifestSha256===selection.manifestSha256&&
    Array.isArray(payload.records),'LOCAL_ASSERTION_PUBLIC_RESPONSE_MISMATCH');
  requireThat(validGTIN(lexicalValue),'LOCAL_ASSERTION_QUERY_INVALID');
  requireThat(Array.isArray(assertions)&&assertions.length<=25,'LOCAL_ASSERTION_COUNT_BOUND');
  const chosen=[],seen=new Set();
  for(const assertion of assertions){
    requireThat(assertion?.schema==='offmenu-local-source-assertion/1','LOCAL_ASSERTION_SCHEMA');
    if(assertion.sourceObservationReference?.originalLexicalValue!==lexicalValue)continue;
    const key=stable(assertion.sourceObservationReference);
    requireThat(!seen.has(key),'LOCAL_ASSERTION_DUPLICATE_OBSERVATION');seen.add(key);
    chosen.push(createSourceAssertion(assertion,{expectedReference:assertion.sourceObservationReference,
      expectedBinding:assertion.binding?.sourceBinding,expectedClassificationProjection:assertion.classificationProjection}));
  }
  return bounded({...payload,localSourceAssertions:{schema:SOURCE_ASSERTIONS_SCHEMA,
    publicSelection:copy(selection),publicationScope:'original records only; sidecar is not part of the published manifest',
    association:'same validated GTIN only; record lineage and product-variant equivalence remain unresolved',
    coverage:{scope:'this configured eligible batch and query only; not whole-dataset coverage',configuredInputs:assertions.length,
      returned:chosen.length,globalTotal:null,
      dispositionCountsAsSupplied:chosen.reduce((counts,a)=>{const key=a.classificationProjection.classification.disposition;
        counts[key]=(counts[key]||0)+1;return counts;},{}),
      relationshipAssertionsCarried:chosen.reduce((count,a)=>count+a.classificationProjection.relationships.length,0),
      semanticAdmissionAndJoinability:'not inferred by this transport'},assertions:chosen}});
}

// A trusted producer or explicit source-view action supplies the WHOLE key.
// There is no array-index, name, GTIN-only or first-match selection fallback.
export function sourceAssertionSelectionKey(assertion){
  requireThat(assertion?.schema==='offmenu-local-source-assertion/1','LOCAL_ASSERTION_SELECTION_INPUT');
  return {schema:'offmenu-source-assertion-selection/1',reference:copy(assertion.sourceObservationReference),
    binding:copy(assertion.binding)};
}
export function selectSourceAssertion(assertions,key){
  requireThat(key?.schema==='offmenu-source-assertion-selection/1'&&Array.isArray(assertions),
    'LOCAL_ASSERTION_EXPLICIT_SELECTION_REQUIRED');
  const matches=assertions.filter(a=>stable(a.sourceObservationReference)===stable(key.reference)&&
    stable(a.binding)===stable(key.binding));
  requireThat(matches.length===1,'LOCAL_ASSERTION_SELECTION_NOT_UNIQUE');return matches[0];
}
export function makeSourcePhotoSelection(assertions,request,currentOutputUse){
  const a=selectSourceAssertion(assertions,request?.selectionKey),ref=a.sourceObservationReference,
    image=request.imageObservation,locator=image?.sourceLocator,asset=request.localAsset;
  requireThat(currentOutputUse?.state==='qualified'&&hex(currentOutputUse.runtimeSelectionSha256)&&
    stable(currentOutputUse.useSelectionRef)===stable(request.useSelectionRef),'LOCAL_ASSERTION_PHOTO_CURRENT_USE');
  requireThat(locator?.sourceId===ref.sourceId&&locator.releaseId===ref.releaseId&&
    locator.originalSha256===a.binding.sourceBinding.originalSha256&&
    locator.ordinal===ref.observationKey.record_ordinal&&image.photo?.sourceCode===ref.sourceLexicalValue,
    'LOCAL_ASSERTION_PHOTO_NATIVE_BINDING');
  requireThat(typeof asset?.path==='string'&&/^\/api\/off-photos\/[A-Za-z0-9_-]+\.(?:jpg|jpeg|png|webp)$/.test(asset.path)&&
    hex(asset.sha256)&&['image/jpeg','image/png','image/webp'].includes(asset.type)&&
    image.snapshotSeparation?.imageBytesSnapshot?.sha256===asset.sha256&&hex(image.retrieval?.sha256),
    'LOCAL_ASSERTION_PHOTO_ASSET_BINDING');
  // This is actual supplied native binding + selected field envelopes. No
  // records[] body, private observation, product join or photo grant is invented.
  return bounded({schema:'offmenu-source-assertion-photo-selection/1',reference:copy(ref),
    detail:{...copy(a.binding),fields:copy(a.fields),classificationProjection:copy(a.classificationProjection)},
    imageObservation:copy(image),useSelectionRef:copy(request.useSelectionRef),localAsset:copy(asset),
    currentOutputUse:copy(currentOutputUse)});
}

function publishedFields(record){
  const d=record.data,field=(value,path)=>({state:value===undefined?'missing':value===null?'null':'present',
    value:value??null,reasonCode:value===undefined?'not-projected-in-selected-public-record':value===null?'explicit-projected-null':null,
    fieldPointer:path,evidenceSha256:record.provenance?.sourceDocumentSha256??null,
    valueOrigin:'selected-public-record',sourceFieldState:'unknown',language:null});
  const fields={};
  for(const[name,key]of Object.entries(fieldsMap))fields[name]=field(d[key],'/data/'+key);
  for(const name of ['nutrientProfile','imageUrlReferences'])if(fields[name].state==='missing')
    fields[name]={...fields[name],state:'not-loaded',reasonCode:'representation-not-provided'};
  if(d.name===d.identifiers?.[0]?.value)fields.name={...fields.name,state:'null',value:null,reasonCode:'identifier-is-not-product-name'};
  fields.markets=field(record.countries,'/countries');fields.sourceProvenance=field(record.provenance,'/provenance');
  for(const[key,value]of Object.entries(d))if(!Object.hasOwn(fields,key))fields[key]=field(value,'/data/'+key);
  return fields;
}

export function projectPublishedRecord(record,{assertions:sidecar,selection}={}){
  requireThat(object(record?.data)&&object(record.provenance),'PUBLIC_RECORD_REQUIRED');
  const fields=publishedFields(record),sourceAssertions=[];
  let sourceAssertionAvailability={state:sidecar?'provided':'not-supplied',reasonCode:null,returned:0,globalCoverage:'unknown'};
  if(sidecar!==undefined)try{
    requireThat(sidecar?.schema===SOURCE_ASSERTIONS_SCHEMA&&object(selection)&&
      stable(sidecar.publicSelection)===stable(selection)&&record.releaseId===selection.releaseId,
      'LOCAL_ASSERTION_READER_SELECTION_MISMATCH');
    requireThat(Array.isArray(sidecar.assertions)&&sidecar.assertions.length<=25,'LOCAL_ASSERTION_COUNT_BOUND');
    for(const assertion of sidecar.assertions){
      const ref=assertion.sourceObservationReference;
      requireThat(assertion.schema==='offmenu-local-source-assertion/1'&&
        validSourceObservationReference(ref,ref?.originalLexicalValue)&&validGTIN(ref.originalLexicalValue)&&
        record.data.identifiers?.some(id=>id.system==='barcode'&&id.value===ref.originalLexicalValue),
        'LOCAL_ASSERTION_READER_IDENTIFIER_MISMATCH');
      sourceAssertions.push(createSourceAssertion(assertion,{expectedReference:ref,
        expectedBinding:assertion.binding?.sourceBinding,expectedClassificationProjection:assertion.classificationProjection}));
    }
    sourceAssertionAvailability={...sourceAssertionAvailability,state:sidecar.state==='unavailable'?'unavailable':'provided',
      reasonCode:sidecar.reasonCode??null,returned:sourceAssertions.length};
  }catch(error){
    if(!/^LOCAL_ASSERTION_/.test(error.message))throw error;
    sourceAssertions.length=0;sourceAssertionAvailability={...sourceAssertionAvailability,state:'unavailable',reasonCode:error.message};
  }
  const snapshot=selection?.manifestSha256||record.provenance.sourceDocumentSha256;
  const classificationProjection=hex(snapshot)?unresolvedProjection({sourceRecordId:record.id,
    snapshotSha256:snapshot,sourceObservationReference:null}):null;
  const match={id:record.id,name:fields.name.value,brand:fields.brand.value,ingredientsText:record.data.ingredientsText??null,
    provenance:{...record.provenance,releaseId:record.releaseId??null},
    detail:{fields,sourceBinding:{sourceId:record.provenance.sourceId},sourceAssertions,classificationProjection,
      sourceAssertionAvailability,
      assurance:'Published source record; additional local assertions are separately attributed, not merged or independently certified.'},
    publicRecord:record};
  // Preserve an actual supplied compatible native reference; never construct
  // one for a curated record from a bare GTIN or a competing sidecar assertion.
  const ref=record.sourceObservationReference;
  if(ref&&validSourceObservationReference(ref,ref.originalLexicalValue)&&
    ref.sourceId===record.provenance.sourceId&&record.data.identifiers?.some(id=>id.system==='barcode'&&id.value===ref.originalLexicalValue))
    match.sourceObservationReference=ref;
  if(sourceAssertions.length&&sidecar.currentOutputUse?.state==='qualified'){
    match.detail.currentOutputUse=copy(sidecar.currentOutputUse);
    if(sidecar.sourcePhotoSelection){
      try{
        const photo=sidecar.sourcePhotoSelection;
        const key={schema:'offmenu-source-assertion-selection/1',reference:photo.reference,
          binding:Object.fromEntries(bindingKeys.filter(k=>Object.hasOwn(photo.detail||{},k)).map(k=>[k,photo.detail[k]]))};
        const selected=selectSourceAssertion(sourceAssertions,key);
        requireThat(stable(photo.currentOutputUse)===stable(sidecar.currentOutputUse)&&
          stable(photo.detail.fields)===stable(selected.fields),'LOCAL_ASSERTION_PHOTO_READER_BINDING');
        match.detail.sourcePhotoSelection=makeSourcePhotoSelection(sourceAssertions,{selectionKey:key,
          imageObservation:photo.imageObservation,useSelectionRef:photo.useSelectionRef,localAsset:photo.localAsset},sidecar.currentOutputUse);
      }catch(error){if(!/^LOCAL_ASSERTION_/.test(error.message))throw error;
        match.detail.sourcePhotoSelectionAvailability={state:'unavailable',reasonCode:error.message};}
    }else if(sidecar.sourcePhotoSelectionAvailability)
      match.detail.sourcePhotoSelectionAvailability=copy(sidecar.sourcePhotoSelectionAvailability);
  }
  return bounded(match);
}

// Rows consumed by the existing scanner readout. Each source has its own
// heading, state, provenance and basis; null is never coerced to zero.
export function sourceAssertionReadout(detail,tab){
  const rows=[];
  if(detail?.sourceAssertionAvailability?.state==='unavailable')rows.push({label:'Additional source facts',
    text:'Unavailable in this response. The published barcode record is still shown; no source absence is established.'});
  const show=value=>value==null?'Unknown':Array.isArray(value)?value.length?value.map(show).join(', '):'No values in this projection; original presence unknown':
    object(value)?Object.entries(value).filter(([,v])=>v!=null).map(([k,v])=>k+': '+show(v)).join(' · ')||'Unknown':String(value);
  const fieldText=field=>!field?'Not captured; original presence unknown':field.state==='present'?show(field.value):
    field.state==='null'?'Unknown in this source projection':field.state==='not-loaded'?'Not loaded':
    field.state==='not-applicable'?'Not applicable as explicitly supplied by this source':
    ['unknown','unresolved'].includes(field.state)?'Unresolved in this source projection':
    ['restricted','rights-held'].includes(field.state)?'Not available for display':'Not supplied in this projection';
  for(const assertion of detail?.sourceAssertions||[]){
    const ref=assertion.sourceObservationReference,attribution=assertion.fields.sourceProvenance?.value?.attribution||ref.sourceId,
      prefix='Separate source · '+attribution+' · '+ref.releaseId;
    rows.push({label:prefix,text:'Same barcode; product variant match is unverified. These facts are shown separately.'});
    const classification=assertion.classificationProjection.classification;
    rows.push({label:prefix+' · source classification',text:classification.disposition+
      ' · ingredient applicability: '+classification.ingredientApplicability+' · scope: '+(classification.idScope||'unresolved')});
    const names=tab==='nutrition'?['nutritionSourceBasis','nutrientProfile','rawNutriments']:
      tab==='ingredients'?['ingredientDeclaration','sourceAllergenClaims','sourceTraceClaims']:
      tab==='source'?Object.keys(assertion.fields):['name','brand','markets','categories','sourceAllergenClaims','sourceTraceClaims','sourceDietaryLabelClaims'];
    for(const name of names){const f=assertion.fields[name];
      if(!f){rows.push({label:prefix+' · '+name,text:'Not captured in this selected representation; original presence unknown.'});continue;}
      rows.push({label:prefix+' · '+name,text:tab==='source'?JSON.stringify(f):
        name==='nutrientProfile'&&f.state==='present'?'Projected profile basis: '+show(f.value?.basis):fieldText(f)});
      if(name==='nutrientProfile'&&f.state==='present')for(const[nutrient,n]of Object.entries(f.value?.nutrients||{}))
        rows.push({label:prefix+' · '+nutrient,text:(n.value==null?'Unknown · not zero':show(n.value)+' '+(n.unit||'unit unknown'))+
          ' · basis: '+show(n.basis)+' · method: '+show(n.method)});
    }
    if(tab==='source')rows.push({label:prefix+' · exact source binding',text:JSON.stringify({sourceObservationReference:ref,binding:assertion.binding})});
    if(tab==='nutrition')rows.push({label:prefix+' · basis distinction',text:assertion.nutritionBasisRelationship});
  }
  return rows;
}
