import {readFile,writeFile} from 'node:fs/promises';
import {configuration,verifyReceipt,verifyLiveRunner,processBirth} from './dev-lifecycle.mjs';
const config=configuration();
const receipt=JSON.parse(await readFile(config.receiptPath,'utf8'));
verifyReceipt(receipt,config);
function sameRunnerPresent(){
 try {
  const birth=processBirth(receipt.pid);
  return birth.bootId===receipt.bootId&&birth.startTicks===receipt.startTicks;
 }catch(error){if(error.code==='ENOENT'||error.code==='ESRCH')return false;throw error;}
}
if(sameRunnerPresent()) {
 verifyLiveRunner(receipt,config);
 process.kill(receipt.pid,'SIGTERM');
 for(let attempt=0;attempt<100&&sameRunnerPresent();attempt++)await new Promise(resolve=>setTimeout(resolve,100));
 if(sameRunnerPresent())throw new Error('Owned runner did not exit; no escalation signal sent.');
} else {
 // A reused PID is never signalled, nor described as the original live process.
 receipt.stopEvidence='recorded boot/start identity absent; no signal sent';
}
receipt.status='stopped';receipt.stoppedAt=new Date().toISOString();
receipt.stopEvidence ||= 'owner/run/cwd/command/boot/start identity verified; owned runner absent after stop';
await writeFile(config.receiptPath,JSON.stringify(receipt,null,2)+'\n');
console.log(JSON.stringify({status:receipt.status,pid:receipt.pid,runId:receipt.runId,stopEvidence:receipt.stopEvidence}));
