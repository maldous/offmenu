const headers={"X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", "Permissions-Policy": "camera=(self), microphone=()", "Content-Security-Policy": "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; media-src 'self' blob:; connect-src 'self' https://offmenu-corpus.netlify.app; worker-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"};
async function publicDemoProduct(request){
 const json=(value,status=200)=>Response.json(value,{status,headers:{...headers,'Cache-Control':'no-store'}});
 if(request.method!=='GET')return json({error:'Method not allowed.'},405);
 const barcode=new URL(request.url).searchParams.get('barcode')||'';
 if(!/^(?:\d{8}|\d{12}|\d{13}|\d{14})$/.test(barcode))return json({error:'Enter a valid barcode.'},400);
 return json({error:'OffMenu normalized product lookup is not available yet.',code:'OFFMENU_OWN_DATA_UNAVAILABLE',barcode,source:{name:'OffMenu',scope:'managed-normalized-inventory',available:false}},503);
}

export{publicDemoProduct};
