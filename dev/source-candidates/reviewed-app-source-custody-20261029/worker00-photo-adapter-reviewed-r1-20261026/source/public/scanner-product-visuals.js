import {associateProductVisual,afterProductVisualAssociationFailure} from './product-visual-association.js';
import {validSourceObservationReference} from './model.js';

export function mountScannerProductVisual(thumbnail,captionRoot,{onChange=()=>{}}={}) {
  const doc=thumbnail.ownerDocument;let epoch=0,key=null,failed=[],current=null;
  const text=(tag,value)=>{const node=doc.createElement(tag);node.textContent=value;return node;};
  function render(input,turn,notify=false,previous=null) {
    const selected=input??{theme:doc.documentElement?.dataset.theme==='dark'?'dark':'light'};
    const association=previous?afterProductVisualAssociationFailure(selected,previous,{failedSources:failed}):
      associateProductVisual(selected,{failedSources:failed});
    const result=input?association.visual:{...association.visual,alt:'OffMenu app icon; product photo unavailable'};
    current=result;thumbnail.replaceChildren();captionRoot.replaceChildren();thumbnail.dataset.visualTier=result.tier;
    if(result.kind==='image'){
      const image=doc.createElement('img');image.alt=result.alt;image.referrerPolicy='no-referrer';
      if(result.tier==='app-fallback')image.dataset.offmenuLogo='';
      image.onerror=()=>{
        if(turn!==epoch||image!==thumbnail.firstChild)return;
        if(input){failed=[...new Set([...failed,result.src])];render(input,turn,true,association);}
        else{thumbnail.replaceChildren(text('span','OffMenu'));current={...result,kind:'text',text:'OffMenu'};onChange(current);}
      };
      image.src=result.src;thumbnail.append(image);
    }else thumbnail.append(text('span',result.text));
    captionRoot.append(text('p',result.caption));
    if(result.tier==='product-photo'){
      const details=text('details',''),credit=result.rights.attributionDetails;
      details.append(text('summary','Photo source and licence'),text('p',result.rights.attribution));
      details.append(text('p','Current publisher photo; membership in the retained snapshot is unverified.'));
      for(const [label,url] of [['Product on Open Food Facts',credit?.productUrl||result.rights.sourcePage],['Photo source',result.rights.sourcePage],['Photo licence',result.rights.photoLicensePage],
        [result.rights.license,result.rights.licenseUrl]]){
        const link=text('a',label);link.href=url;link.target='_blank';link.rel='noopener noreferrer';details.append(link);
      }
      for(const notice of credit?.notices||[])details.append(text('p',notice.field+': '+notice.text));
      details.append(text('p',result.rights.changes));
      if(credit?.packagingRights?.qualification)details.append(text('p',credit.packagingRights.qualification));
      captionRoot.append(details);
    }
    if(notify)onChange(result);return result;
  }
  return {show({reference=null,detail=null,entryId=null,generation=null,name='',theme='light',offline=false}={}){
    const valid=reference&&validSourceObservationReference(reference,reference.originalLexicalValue);
    const nextKey=JSON.stringify([entryId,generation,reference,detail?.referenceRecordId??null]);
    if(nextKey!==key){failed=[];key=nextKey;}
    const turn=++epoch;
    const input=valid?{reference,detail,name,theme,offline}:null;
    return render(input,turn);
  },current:()=>current,destroy(){epoch++;thumbnail.replaceChildren();captionRoot.replaceChildren();}};
}
