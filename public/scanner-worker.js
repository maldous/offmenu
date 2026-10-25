import {prepareZXingModule} from 'zxing-wasm/reader';
import {readRetailBarcodes} from './scanner-decode.js';
import {projectZXingResult} from './scanner-capture-envelope.js';
prepareZXingModule({overrides:{locateFile:path=>path.endsWith('.wasm')?'/scanner.wasm':path}});
self.onmessage=async ({data:{id,image,enhance}})=>{
  try {
    const results=await readRetailBarcodes(image,enhance);
    self.postMessage({id,results:results.map(projectZXingResult)});
  } catch { self.postMessage({id,error:'The barcode decoder could not load. Reconnect and retry, or enter the barcode.'}); }
};
