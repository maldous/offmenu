import {t,setLocalizedText} from './i18n.js';
import {NATIVE_FORMATS, createPresentationGate, cameraError} from './scanner-model.js';
import {captureFromDecoder, selectableCaptures, requiresUPCEConfirmation} from './scanner-capture-envelope.js';

// Translate the visible aiming guide through the video's object-fit:cover crop.
// The returned rectangle is the only region submitted to both decoders.
export function cameraCrop(videoWidth,videoHeight,frame,guide,{mirror=false,rotate=false,fit='cover'}={}) {
  if(!(videoWidth>0&&videoHeight>0&&frame?.width>0&&frame?.height>0&&guide?.width>0&&guide?.height>0))return null;
  const scale=fit==='contain'?Math.min(frame.width/videoWidth,frame.height/videoHeight):Math.max(frame.width/videoWidth,frame.height/videoHeight);
  const imageLeft=frame.left+(frame.width-videoWidth*scale)/2;
  const imageTop=frame.top+(frame.height-videoHeight*scale)/2;
  const left=Math.max(frame.left,imageLeft,guide.left),top=Math.max(frame.top,imageTop,guide.top);
  const right=Math.min(frame.left+frame.width,imageLeft+videoWidth*scale,guide.left+guide.width);
  const bottom=Math.min(frame.top+frame.height,imageTop+videoHeight*scale,guide.top+guide.height);
  if(right-left<24||bottom-top<24)return null;
  let sx=(left-imageLeft)/scale;
  let sy=(top-imageTop)/scale;
  const sw=(right-left)/scale,sh=(bottom-top)/scale;
  if(Boolean(mirror)!==Boolean(rotate))sx=videoWidth-sx-sw;
  if(rotate)sy=videoHeight-sy-sh;
  return {sx:Math.max(0,sx),sy:Math.max(0,sy),sw:Math.min(sw,videoWidth-Math.max(0,sx)),sh:Math.min(sh,videoHeight-Math.max(0,sy))};
}

export function setupScanner({canScan,onCode,onStream,onStartGesture,autoResume=false,storage}) {
  const $=id=>document.getElementById(id), video=$('video'), canvas=document.createElement('canvas');
  const context=canvas.getContext('2d',{willReadFrequently:true});
  const gate=createPresentationGate();
  let stream=null, token=0, timer=null, worker=null, pending=null, job=0, native=null, wake=null;
  let running=false, starting=false, lastFrame=-1, attempts=0, started=0, lastRead=0, lastCodes=[], track=null;
  let preferences={mode:'handheld',camera:'environment',mirror:false,rotate:false,enhance:true};
  try { preferences={...preferences,...JSON.parse((storage ?? localStorage).getItem('offmenu-scanner-v2')||'{}')}; } catch {}
  if(!['handheld','bench','stand'].includes(preferences.mode)) preferences.mode='bench';
  const status=text=>{setLocalizedText($('scanner-status'),text);};
  const save=()=>{try{(storage ?? localStorage).setItem('offmenu-scanner-v2',JSON.stringify(preferences));}catch{}};
  const range=cap=>cap && Number.isFinite(cap.min) && Number.isFinite(cap.max) && cap.max>cap.min;
  const caps=()=>{try{return track?.getCapabilities?.()||{};}catch{return {};}};
  function preview() {
    // Display transforms never touch pixels submitted to either barcode decoder.
    video.style.transform=`rotate(${preferences.rotate?180:0}deg) scaleX(${preferences.mirror?-1:1})`;
    $('scanner-mirror').checked=preferences.mirror;
    $('scanner-rotate').checked=preferences.rotate;
    $('scanner-enhance').checked=preferences.enhance;
  }
  function guide() {
    $('scanner-mode').value=preferences.mode;
    setLocalizedText($('scanner-placement'),preferences.mode==='bench'?t('Screen-up bench: front camera faces the barcode. Start around 30–50 cm away and move slowly until the bars look sharp. Fixed-focus lenses may need more distance; use a rear-camera stand if they stay blurry.'):preferences.mode==='stand'?t('Hands-free rear: prop the phone securely upright or in a stand, with the rear lens exposed. Move each barcode into view and pause for the beep. A phone lying screen-up blocks its rear camera.'):t('Handheld: rear camera recommended. Start around 15–30 cm from the barcode; move back if it blurs. Keep the entire code and its blank edges visible. Tilt shiny packaging away from glare.'));
  }
  async function keepAwake(sessionToken) {
    if(!navigator.wakeLock?.request) return;
    try {
      const lock=await navigator.wakeLock.request('screen');
      if(sessionToken!==token || !running) await lock.release(); else wake=lock;
    } catch { /* Optional: some browsers and power modes do not allow a wake lock. */ }
  }
  function closeDecoder() {
    worker?.terminate(); worker=null;
    if(pending) { clearTimeout(pending.timeout); pending.reject(Error(t('Decoder stopped'))); pending=null; }
  }
  function stop({announce=true}={}) {
    token++; running=false; starting=false; clearTimeout(timer); closeDecoder(); native=null;
    stream?.getTracks().forEach(t=>t.stop()); stream=null; track=null; onStream(null);
    video.srcObject=null; video.hidden=true;
    $('camera-stage').hidden=true; $('scanner-controls').hidden=true; if($('stop'))$('stop').hidden=true;
    if($('scan'))$('scan').disabled=false; $('scanner-photo').disabled=false;
    $('scanner-rearm').disabled=true;
    if(wake) { void wake.release().catch(()=>{}); wake=null; }
    gate.rearm(); lastFrame=-1; lastCodes=[];
    if(announce) status('Camera stopped. Your scanned items are kept.');
  }
  async function setting(values) {
    const activeTrack=track;
    if(!activeTrack) return false;
    try { await activeTrack.applyConstraints({advanced:[values]}); return activeTrack===track; }
    catch { status('This camera/browser could not apply that control. Scanning continues with its current settings.'); return false; }
  }
  function showControls() {
    const c=caps(), settings=track?.getSettings?.()||{};
    const modes=c.focusMode||[];
    $('scanner-focus').replaceChildren();
    for(const [mode,label] of [['continuous','Autofocus'],['single-shot','Focus once'],['manual','Manual focus']]) {
      if(modes.includes(mode) && (mode!=='manual'||range(c.focusDistance))) $('scanner-focus').add(new Option(label,mode));
    }
    $('scanner-focus-row').hidden=!$('scanner-focus').options.length;
    $('scanner-focus').value=settings.focusMode||$('scanner-focus').options[0]?.value||'';
    $('scanner-focus-distance-row').hidden=$('scanner-focus').value!=='manual'||!range(c.focusDistance);
    for(const [id,cap,key] of [['zoom',c.zoom,'zoom'],['focus-distance',c.focusDistance,'focusDistance'],['exposure',c.exposureCompensation,'exposureCompensation']]) {
      const input=$('scanner-'+id);
      if(id!=='focus-distance') $('scanner-'+id+'-row').hidden=!range(cap);
      if(range(cap)) { input.min=cap.min; input.max=cap.max; input.step=cap.step||((cap.max-cap.min)/100); input.value=settings[key]??cap.min; }
    }
    $('scanner-torch').hidden=!c.torch;
    $('scanner-torch').setAttribute('aria-pressed',String(!!settings.torch));
    setLocalizedText($('scanner-torch'),settings.torch?t('Light on'):t('Light off'));
    setLocalizedText($('scanner-capabilities'),`${settings.width||video.videoWidth} × ${settings.height||video.videoHeight} · `+(modes.includes('continuous')?'autofocus control available':modes.length?'focus controls available':'focus control not exposed; lens may be fixed-focus or managed by the camera')+` · ${native?'native + enhanced decoder':'enhanced decoder'}`);
  }
  async function enumerate() {
    const devices=(await navigator.mediaDevices.enumerateDevices()).filter(d=>d.kind==='videoinput');
    const selected=track?.getSettings?.().deviceId;
    const select=$('scanner-camera'); select.replaceChildren(new Option('Rear camera (automatic)','environment'),new Option('Front camera (automatic)','user'));
    devices.forEach((d,i)=>select.add(new Option(d.label||`Camera ${i+1}`,d.deviceId)));
    select.value=devices.some(d=>d.deviceId===selected)?selected:preferences.camera;
  }
  function decode(image,enhance) {
    if(!worker) {
      worker=new Worker('/scanner-worker.js',{type:'module'});
      worker.onmessage=({data})=>{
        if(!pending || pending.id!==data.id) return;
        const request=pending; pending=null; clearTimeout(request.timeout);
        data.error?request.reject(Error(data.error)):request.resolve(data.results);
      };
      worker.onerror=()=>closeDecoder();
    }
    return new Promise((resolve,reject)=>{
      const id=++job;
      pending={id,resolve,reject,timeout:setTimeout(()=>closeDecoder(),15000)};
      worker.postMessage({id,image,enhance},[image.data.buffer]);
    });
  }
  function pixels(source=video,limit=1920) {
    const width=source.videoWidth||source.width, height=source.videoHeight||source.height;
    if(!width||!height) throw Error(t('No camera frame yet'));
    const guide=$('capture-guide')||$('camera-stage')?.querySelector('.scanner-guide');
    const crop=source===video&&guide?cameraCrop(width,height,video.getBoundingClientRect(),guide.getBoundingClientRect(),{...preferences,fit:getComputedStyle(video).objectFit}):null;
    if(source===video&&!crop) throw Error(t('Visible aiming area unavailable'));
    const sw=crop?.sw||width,sh=crop?.sh||height;
    const scale=Math.min(1,limit/Math.max(sw,sh));
    canvas.width=Math.max(1,Math.round(sw*scale)); canvas.height=Math.max(1,Math.round(sh*scale));
    context.drawImage(source,crop?.sx||0,crop?.sy||0,sw,sh,0,0,canvas.width,canvas.height);
    return context.getImageData(0,0,canvas.width,canvas.height);
  }
  async function loop(sessionToken) {
    if(sessionToken!==token || !running) return;
    if(!canScan()){timer=setTimeout(()=>void loop(sessionToken),140);return;}
    const begin=performance.now();
    try {
      if(video.readyState>=2 && video.currentTime!==lastFrame) {
        lastFrame=video.currentTime; attempts++;
        let results=[],decoderPath='native';
        const frame=pixels();
        if(native) {
          try { results=await native.detect(canvas); } catch { native=null; }
        }
        if(sessionToken!==token) return;
        // Serial fallback: never queue frames behind an in-flight decode.
        if(!requiresUPCEConfirmation(results,'native') && !selectableCaptures(results,'native').length && (!native || attempts%3===0)) {results=await decode(frame,preferences.enhance);decoderPath='zxing-wasm';}
        if(sessionToken!==token) return;
        const captures=requiresUPCEConfirmation(results,decoderPath)?[]:selectableCaptures(results,decoderPath);
        const codes=[...new Set(captures.map(x=>x.lookupLexicalValue+'\u0000'+(x.lookupSymbology||'')))];
        lastCodes=codes;
        const accepted=gate.observe(codes,performance.now());
        if(accepted) {
          const captureEnvelope=captures.find(x=>x.lookupLexicalValue+'\u0000'+(x.lookupSymbology||'')===accepted);
          lastRead=performance.now(); onCode(captureEnvelope.lookupLexicalValue,{captureEnvelope,
            originalCaptures:[{value:captureEnvelope.lookupLexicalValue,symbology:captureEnvelope.lookupSymbology}]});
          setLocalizedText($('scanner-last'),"Accepted: {v0}",{v0:(captureEnvelope.lookupLexicalValue)});
          status('Accepted ✓ Move this item away. Present the next barcode.');
          $('camera-stage').classList.add('scan-accepted');
          setTimeout(()=>$('camera-stage').classList.remove('scan-accepted'),500);
        } else if(codes.length>1) status('More than one barcode visible. Present one product at a time.');
        else if(codes.length===1 && performance.now()-lastRead>2000) status(lastRead?'Ready for next item. Remove this barcode fully before the next identical pack.':'Reading… Hold one barcode steady.');
        else if(lastRead && !codes.length) status('Ready for next item. Previous product details are retained.');
        else if(!lastRead && performance.now()-started>6000) status(results.some(x=>captureFromDecoder(x,decoderPath).status==='manual-required')?'Decoder representation needs manual confirmation. Use Type code to preserve the printed value.':'No readable code yet. Pause movement, move farther away if blurred, and avoid glare. Try another lens or a photo.');
      }
    } catch {
      if(sessionToken!==token) return;
      if(native) { status('Enhanced decoder unavailable; using the device decoder.'); }
      else { stop({announce:false}); status('Barcode decoder unavailable. Reconnect and reopen the camera, or type the barcode.'); return; }
    }
    if(sessionToken===token && running) timer=setTimeout(()=>void loop(sessionToken),Math.max(70,140-(performance.now()-begin)));
  }
  async function start() {
    if(!canScan()||running||starting) return;
    stop({announce:false}); starting=true;const sessionToken=token;
    if($('scan'))$('scan').disabled=true;if($('stop'))$('stop').hidden=false;
    status('Opening camera…');
    // Audio resume must begin in the user gesture, before the permission dialog.
    void onStartGesture?.();
    try {
      if(!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) throw {name:'SecurityError'};
      const camera=preferences.camera;
      const selection=['environment','user'].includes(camera)?{facingMode:{ideal:camera}}:{deviceId:{exact:camera}};
      let acquired;
      try { acquired=await navigator.mediaDevices.getUserMedia({audio:false,video:{...selection,width:{ideal:1920},height:{ideal:1080},frameRate:{ideal:30}}}); }
      catch(error) {
        if(error.name!=='OverconstrainedError' || sessionToken!==token) throw error;
        acquired=await navigator.mediaDevices.getUserMedia({audio:false,video:selection});
      }
      if(sessionToken!==token) { acquired.getTracks().forEach(t=>t.stop()); return; }
      stream=acquired; track=stream.getVideoTracks()[0]; onStream(stream);
      track.addEventListener('ended',()=>{if(sessionToken===token){stop({announce:false});status('Camera disconnected. Reconnect and open the scanner again.');}});
      video.srcObject=stream; video.hidden=false; $('camera-stage').hidden=false;
      await video.play(); if(sessionToken!==token) return;
      const c=caps();
      for(const key of ['focusMode','exposureMode','whiteBalanceMode']) {
        if(c[key]?.includes('continuous')) await setting({[key]:'continuous'});
        if(sessionToken!==token) return;
      }
      native=null;
      if('BarcodeDetector' in window) {
        try { const supported=await BarcodeDetector.getSupportedFormats(); if(NATIVE_FORMATS.every(f=>supported.includes(f))) native=new BarcodeDetector({formats:NATIVE_FORMATS}); } catch {}
      }
      if(sessionToken!==token) return;
      try { await enumerate(); } catch { /* Automatic facing modes remain available. */ }
      if(sessionToken!==token) return;
      preview(); showControls(); $('scanner-controls').hidden=false; $('scanner-rearm').disabled=false;
      running=true;starting=false; started=performance.now(); lastRead=0; attempts=0;
      status('Ready. Present one barcode and pause briefly.');
      void keepAwake(sessionToken); void loop(sessionToken);
    } catch(error) { if(sessionToken===token){stop({announce:false});status(cameraError(error));} }
  }
  $('scanner-mode').onchange=()=>{
    preferences.mode=$('scanner-mode').value;
    preferences.camera=preferences.mode==='bench'?'user':'environment';
    preferences.mirror=preferences.mode==='bench'; preferences.rotate=false;
    $('scanner-camera').value=preferences.camera; guide(); preview(); save();
    if(running||starting){stop({announce:false});void start();}
  };
  $('scanner-camera').onchange=()=>{
    preferences.camera=$('scanner-camera').value; save();
    if(running||starting){stop({announce:false});void start();}
  };
  for(const key of ['mirror','rotate','enhance']) $('scanner-'+key).onchange=()=>{preferences[key]=$('scanner-'+key).checked;preview();save();};
  $('scanner-torch').onclick=async()=>{await setting({torch:!track?.getSettings?.().torch});showControls();};
  $('scanner-focus').onchange=async()=>{await setting({focusMode:$('scanner-focus').value});showControls();};
  for(const [id,key] of [['zoom','zoom'],['focus-distance','focusDistance'],['exposure','exposureCompensation']]) $('scanner-'+id).onchange=async()=>{
    const values={[key]:Number($('scanner-'+id).value)}; if(key==='focusDistance') values.focusMode='manual';
    await setting(values); showControls();
  };
  $('scanner-rearm').onclick=()=>{gate.rearm();status('Ready to count the next identical pack. Keep its barcode in view.');};
  $('scanner-photo').onchange=async()=>{
    const file=$('scanner-photo').files[0]; $('scanner-photo').value='';
    if(!file || !canScan()) return;
    stop({announce:false}); const photoToken=token;
    if(file.size>20_000_000) return status('Choose an image smaller than 20 MB.');
    $('scanner-photo').disabled=true; status('Reading barcode photo…');
    let bitmap;
    try {
      bitmap=await createImageBitmap(file);
      if(photoToken!==token) return;
      const results=await decode(pixels(bitmap,2560),preferences.enhance);
      if(photoToken!==token) return;
      const captures=requiresUPCEConfirmation(results,'photo-zxing-wasm')?[]:selectableCaptures(results,'photo-zxing-wasm');
      const codes=[...new Set(captures.map(x=>x.lookupLexicalValue+'\u0000'+(x.lookupSymbology||'')))];
      if(codes.length!==1) return status(codes.length?'Several barcodes found. Crop the photo to one product.':results.length?'Decoder representation needs manual confirmation. Type the printed code.':'No retail barcode found. Use a sharp photo of the entire barcode, including its blank edges.');
      const captureEnvelope=captures[0];
      onCode(captureEnvelope.lookupLexicalValue,{captureKind:'photo',captureEnvelope,
        originalCaptures:[{value:captureEnvelope.lookupLexicalValue,symbology:captureEnvelope.lookupSymbology}]}); setLocalizedText($('scanner-last'),"Accepted from photo: {v0}",{v0:(captureEnvelope.lookupLexicalValue)}); status('Photo accepted ✓');
    } catch { if(photoToken===token) status('Photo could not be decoded. Try a JPEG/PNG photo or enter the barcode.'); }
    finally { bitmap?.close(); if(photoToken===token){closeDecoder();$('scanner-photo').disabled=false;if(autoResume&&canScan())void start();} }
  };
  if($('scan'))$('scan').onclick=()=>void start();if($('stop'))$('stop').onclick=()=>stop();
  document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();else if(autoResume&&canScan())void start();});
  if(autoResume&&navigator.permissions?.query)void navigator.permissions.query({name:'camera'}).then(p=>p.addEventListener('change',()=>{if(p.state==='granted'&&!document.hidden&&canScan())void start();})).catch(()=>{});
  window.addEventListener('pagehide',()=>stop());
  guide(); preview();
  if(!['environment','user'].includes(preferences.camera)) $('scanner-camera').add(new Option('Last used camera',preferences.camera));
  $('scanner-camera').value=preferences.camera;
  return {stop,start,noteAccepted(){if(running){lastRead=performance.now();status('Ready for next item. Previous product details are retained.');}}};
}
