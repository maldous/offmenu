import test from 'node:test';
import {readRetailBarcodes} from '../../public/scanner-decode.js';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {readBarcodes,prepareZXingModule} from 'zxing-wasm/reader';
import {validGTIN,retailCode,createPresentationGate,enhanceContrast,RETAIL_FORMATS} from '../../public/scanner-model.js';
prepareZXingModule({overrides:{wasmBinary:await readFile('node_modules/zxing-wasm/dist/reader/zxing_reader.wasm')}});
const code='4006381333931';
test('retail validation rejects errors, wrong lengths, non-retail data and bad checksums',()=>{
 assert.ok(validGTIN(code)); assert.ok(!validGTIN('4006381333932'));
 assert.equal(retailCode({format:'EAN-13',text:code}),code);
 assert.equal(retailCode({format:'ean_13',rawValue:'0036000291452'}),'036000291452');
 assert.equal(retailCode({format:'UPC-E',text:'04252614'}),'042100005264');
 for(const result of [{format:'EAN-13',text:'4006381333932'},{format:'QR_CODE',text:code},{format:'EAN-8',text:code},{format:'EAN-13',text:code,error:'Checksum'}])assert.equal(retailCode(result),null);
});
test('two fresh agreeing reads; slow processing or a dropped frame cannot double count',()=>{
 const g=createPresentationGate();assert.equal(g.observe([code],0),null);assert.equal(g.observe([code],140),code);
 assert.equal(g.observe([code],4000),null);assert.equal(g.observe([code],4140),null);
 g.observe([],5000);assert.equal(g.observe([code],6500),null);assert.equal(g.observe([code],6640),null);
 for(const t of [7000,7400,7800,8300])g.observe([],t);
 assert.equal(g.observe([code],8500),null);assert.equal(g.observe([code],8640),code);
});
test('ambiguous frames never accept and explicit rearm still requires consensus',()=>{
 const g=createPresentationGate();g.observe([code],0);assert.equal(g.observe([code,'12345670'],100),null);
 assert.equal(g.observe([code],200),null);assert.equal(g.observe([code],300),code);
 g.rearm();assert.equal(g.observe([code],400),null);assert.equal(g.observe([code],500),code);
});
// Independent EAN-13 encoder fixture, without using the decoder's writer.
function fixture({angle=0,mirror=false,invert=false,lowContrast=false}={}){
 const L=['0001101','0011001','0010011','0111101','0100011','0110001','0101111','0111011','0110111','0001011'];
 const G=['0100111','0110011','0011011','0100001','0011101','0111001','0000101','0010001','0001001','0010111'];
 const parity=['LLLLLL','LLGLGG','LLGGLG','LLGGGL','LGLLGG','LGGLLG','LGGGLL','LGLGLG','LGLGGL','LGGLGL'][Number(code[0])];
 const bits='000000000000101'+[...code.slice(1,7)].map((n,i)=>(parity[i]==='L'?L:G)[Number(n)]).join('')+'01010'+[...code.slice(7)].map(n=>L[Number(n)].replace(/[01]/g,b=>b==='1'?'0':'1')).join('')+'101000000000000';
 const w=bits.length*4,h=240,sw=angle%180?h:w,sh=angle%180?w:h,data=new Uint8ClampedArray(sw*sh*4);
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){
  const bar=y>=32&&y<h-32&&bits[Math.floor(x/4)]==='1';let v=bar?0:255;if(lowContrast)v=bar?115:170;if(invert)v=255-v;
  let xx=mirror?w-1-x:x,yy=y;
  if(angle===90)[xx,yy]=[h-1-yy,xx];if(angle===180)[xx,yy]=[w-1-xx,h-1-yy];if(angle===270)[xx,yy]=[yy,w-1-xx];
  const i=(yy*sw+xx)*4;data[i]=data[i+1]=data[i+2]=v;data[i+3]=255;
 }
 return {data,width:sw,height:sh};
}
for(const [name,variant] of Object.entries({plain:{},rotated90:{angle:90},upsideDown:{angle:180},rotated270:{angle:270},mirrored:{mirror:true},inverted:{invert:true},lowContrast:{lowContrast:true}})){
 test('real WASM decoder: '+name,async()=>{
  const image=fixture(variant);
  const results=await readRetailBarcodes(image);
  assert.ok(results.some(r=>retailCode(r)===code),name);
 });
}
test('contrast pass preserves the barcode and does not invent one in a flat frame',async()=>{
 const image=enhanceContrast(fixture({lowContrast:true}));
 assert.ok((await readBarcodes(image,{formats:RETAIL_FORMATS})).some(r=>retailCode(r)===code));
 const flat={width:400,height:200,data:new Uint8ClampedArray(400*200*4).fill(255)};
 assert.deepEqual(await readBarcodes(enhanceContrast(flat),{formats:RETAIL_FORMATS}),[]);
});
