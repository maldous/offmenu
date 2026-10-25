import {selectProductVisual} from './product-visual-selector.js';
import {selectedPublisherPhotos,OFF_PHOTOS} from './off-photo-catalogue.js';
import {validSourceObservationReference} from './model.js';

export function mountScannerProductVisual(thumbnail,captionRoot,{onChange=()=>{}}={}) {
  const doc=thumbnail.ownerDocument;let epoch=0,key=null,failed=[],current=null;
  const text=(tag,value)=>{const node=doc.createElement(tag);node.textContent=value;return node;};
  function render(input,turn,notify=false) {
    const result=input?selectProductVisual(input,{failedSources:failed}):{
      tier:'app-fallback',kind:'image',src:doc.documentElement?.dataset.theme==='dark'?'/scanner-balanced-final-dark.svg':'/scanner-balanced-final.svg',
      alt:'OffMenu app icon; product photo unavailable',caption:'Product photo unavailable · no qualified category illustration'};
    current=result;thumbnail.replaceChildren();captionRoot.replaceChildren();thumbnail.dataset.visualTier=result.tier;
    if(result.kind==='image'){
      const image=doc.createElement('img');image.alt=result.alt;image.referrerPolicy='no-referrer';
      if(result.tier==='app-fallback')image.dataset.offmenuLogo='';
      image.onerror=()=>{
        if(turn!==epoch||image!==thumbnail.firstChild)return;
        if(input){failed=[...new Set([...failed,result.src])];render(input,turn,true);}
        else{thumbnail.replaceChildren(text('span','OffMenu'));current={...result,kind:'text',text:'OffMenu'};onChange(current);}
      };
      image.src=result.src;thumbnail.append(image);
    }else thumbnail.append(text('span',result.text));
    captionRoot.append(text('p',result.caption));
    if(result.tier==='product-photo'){
      captionRoot.append(text('p','Current publisher photo; membership in the retained snapshot is unverified.'));
      for(const [label,url] of [['Photo source',result.rights.sourcePage],['Photo licence',result.rights.photoLicensePage],
        [result.rights.license,result.rights.licenseUrl]]){
        const link=text('a',label);link.href=url;link.target='_blank';link.rel='noopener noreferrer';captionRoot.append(link);
      }
      captionRoot.append(text('p',result.rights.changes));
    }
    if(notify)onChange(result);return result;
  }
  return {show({reference=null,detail=null,entryId=null,generation=null,name='',theme='light',offline=false}={}){
    const valid=reference&&validSourceObservationReference(reference,reference.originalLexicalValue);
    const nextKey=JSON.stringify([entryId,generation,reference,detail?.referenceRecordId??null]);
    if(nextKey!==key){failed=[];key=nextKey;}
    const turn=++epoch;
    const input=valid?{sourceObservationReference:reference,selectedProductRecordId:detail?.referenceRecordId??null,
      sourceProductName:name,theme,offline,photoCandidates:selectedPublisherPhotos(reference,detail),
      categoryMappings:[],canonicalConcepts:[],permittedLocalAssets:OFF_PHOTOS.map(photo=>photo.path)}:null;
    return render(input,turn);
  },current:()=>current,destroy(){epoch++;thumbnail.replaceChildren();captionRoot.replaceChildren();}};
}
