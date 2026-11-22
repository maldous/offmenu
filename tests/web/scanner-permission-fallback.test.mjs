import test from 'node:test';
import assert from 'node:assert/strict';
import {cameraError} from '../../apps/web/src/scanner-model.js';
import {t,setLanguage} from '../../apps/web/src/i18n.js';

test('camera denial truthfully identifies the manual path before optional camera retry',()=>{
 const message=cameraError({name:'NotAllowedError'});
 assert.match(message,/^Camera permission is blocked\./);
 assert.match(message,/type the barcode or use a USB \/ Bluetooth scanner\./);
 assert.match(message,/To retry with the camera, allow it in your browser settings\./);
 assert.doesNotMatch(message,/recognised|recognized|scan succeeded/i);
 setLanguage('ar');
 assert.match(t(message),/\p{Script=Arabic}/u);
});
