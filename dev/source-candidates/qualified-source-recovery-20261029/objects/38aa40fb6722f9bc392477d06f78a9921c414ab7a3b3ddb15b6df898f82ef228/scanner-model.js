// Camera reads are restricted to retail identifiers. Manual entry remains separate.
export const RETAIL_FORMATS = ['EAN-13', 'EAN-8', 'UPC-A', 'UPC-E'];
export const NATIVE_FORMATS = ['ean_13', 'ean_8', 'upc_a', 'upc_e'];

export function validGTIN(value) {
  if (!/^(?:\d{8}|\d{12}|\d{13}|\d{14})$/.test(value)) return false;
  let sum = 0;
  for (let i = value.length - 2, weight = 3; i >= 0; i--, weight = 4 - weight) sum += Number(value[i]) * weight;
  return (10 - sum % 10) % 10 === Number(value.at(-1));
}

export function retailCode(result) {
  const value = result.rawValue ?? result.text ?? '';
  const format = String(result.format || '').replace(/[-_ ]/g, '').toUpperCase();
  const length = {EAN13:13, EAN8:8, UPCA:12, UPCE:8}[format];
  if (!length || !new RegExp('^\\d{' + length + '}$').test(value) || result.error) return null;
  let code = value;
  if (format === 'UPCE') {
    // Expand the number system + six compressed digits + check digit to UPC-A.
    if (!/^[01]/.test(code)) return null;
    const [n,a,b,c,d,e,f,k] = code;
    code = f <= '2' ? n+a+b+f+'0000'+c+d+e+k : f === '3' ? n+a+b+c+'00000'+d+e+k : f === '4' ? n+a+b+c+d+'00000'+e+k : n+a+b+c+d+e+'0000'+f+k;
  }
  if (!validGTIN(code)) return null;
  // This is a standards-defined representation alias, not evidence of one source product. Callers retain and query the original lexical capture.
  return code.length === 13 && code.startsWith('0') ? code.slice(1) : code;
}

export function createPresentationGate({gap=1200, misses=4, confirmations=2}={}) {
  let held='', candidate='', count=0, last=0, emptySince=null, emptyCount=0;
  return {
    observe(codes, now) {
      const unique = [...new Set(codes.filter(Boolean))];
      if (unique.length !== 1) {
        candidate=''; count=0;
        if (unique.length) { emptySince=null; emptyCount=0; return null; }
        emptySince ??= now;
        if (++emptyCount >= misses && now-emptySince >= gap) held='';
        return null;
      }
      emptySince=null; emptyCount=0;
      const code=unique[0];
      if (code===candidate && now-last<=1800) count++; else { candidate=code; count=1; }
      last=now;
      if (count < confirmations || held===code) return null;
      held=code; return code;
    },
    rearm() { held=''; candidate=''; count=0; emptySince=null; emptyCount=0; }
  };
}

export function enhanceContrast(image) {
  const data=image.data, hist=new Uint32Array(256);
  for(let i=0;i<data.length;i+=4) hist[Math.round(data[i]*.299+data[i+1]*.587+data[i+2]*.114)]++;
  const pixels=data.length/4, threshold=pixels*.02;
  let low=0,high=255,n=0;
  while(low<255 && (n+=hist[low])<threshold) low++;
  n=0; while(high>low && (n+=hist[high])<threshold) high--;
  if(high-low<8) return image;
  for(let i=0;i<data.length;i+=4) {
    const y=Math.round(data[i]*.299+data[i+1]*.587+data[i+2]*.114);
    const v=Math.max(0,Math.min(255,Math.round((y-low)*255/(high-low))));
    data[i]=data[i+1]=data[i+2]=v;
  }
  return image;
}

export function cameraError(error) {
  return ({NotAllowedError:'Camera permission is blocked. Allow the camera in this site’s browser settings, then retry.',NotFoundError:'No camera found. Connect a camera or use a barcode photo or manual entry.',NotReadableError:'The camera is busy. Close other camera apps and retry.',OverconstrainedError:'This camera cannot use those settings. Try another camera.',SecurityError:'Open OffMenu directly over HTTPS to use the camera.'})[error?.name] || 'Camera could not start. Try another camera, a barcode photo, or manual entry.';
}
