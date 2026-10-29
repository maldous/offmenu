import {readBarcodes} from 'zxing-wasm/reader';
import {RETAIL_FORMATS, enhanceContrast} from './scanner-model.js';
const options={formats:RETAIL_FORMATS,tryHarder:true,tryRotate:true,tryInvert:true,tryDownscale:true,minLineCount:3,maxNumberOfSymbols:4,returnErrors:false};
function inverse(image) {
  const data=new Uint8ClampedArray(image.data);
  for(let i=0;i<data.length;i+=4) { data[i]=255-data[i];data[i+1]=255-data[i+1];data[i+2]=255-data[i+2]; }
  return {data,width:image.width,height:image.height};
}
export async function readRetailBarcodes(image,enhance=true) {
  let results=await readBarcodes(image,options);
  // ZXing's tryInvert does not cover every linear format. Explicit inversion
  // is required for reversed-reflectance EAN/UPC (verified by fixtures).
  if(!results.length) results=await readBarcodes(inverse(image),options);
  if(!results.length && enhance) {
    const boosted=enhanceContrast({data:new Uint8ClampedArray(image.data),width:image.width,height:image.height});
    results=await readBarcodes(boosted,options);
    if(!results.length) results=await readBarcodes(inverse(boosted),options);
  }
  return results;
}
