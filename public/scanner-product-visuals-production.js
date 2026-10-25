// Product image metadata is not in the selected public product-record contract.
// Keep the fixed photo slot honest until a separate, rights-qualified image route is bound.
export function mountScannerProductVisual(thumbnail,captionRoot){
  const doc=thumbnail.ownerDocument;
  const state={kind:'image',tier:'app-fallback',caption:'Product photo unavailable for this published release'};
  function show(){
    const image=doc.createElement('img');image.dataset.offmenuLogo='';image.alt='OffMenu app icon; product photo unavailable';
    image.src=doc.documentElement?.dataset.theme==='dark'?'/scanner-balanced-final-dark.svg':'/scanner-balanced-final.svg';
    thumbnail.replaceChildren(image);thumbnail.dataset.visualTier='app-fallback';
    captionRoot.replaceChildren();
  }
  return {show,current:()=>state};
}
