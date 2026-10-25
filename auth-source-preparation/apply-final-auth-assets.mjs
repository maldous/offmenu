//00 build-time only. Exact original three asset preimages; all others retained.
import {createHash} from 'node:crypto';
import {FINAL_AUTH_ASSETS} from './dist/final-auth-assets.mjs';
const expected={'auth.js':'f82134eed690377d216612d297cee9cd058046e5f1198b681ef1a2c34d8af9cd',
  'auth-return-bridge.js':'fdd80162819472361807e81bc7845de745c60d63fcd083f9a398dc7f3b3d840e',
  'auth.html':'b5e6dd2604d9931b8fbb38456829e56b5afbb7f2ddcc09bfdbdbf745890356bd'};
export function applyFinalAuthAssets(assets){
  const next={...assets};
  for(const [name,pin]of Object.entries(expected)){
    if(typeof assets[name]!=='string'||createHash('sha256').update(assets[name]).digest('hex')!==pin)throw Error('EXACT_AUTH_PREIMAGE_REQUIRED');
    next[name]=FINAL_AUTH_ASSETS[name];
  }
  return next;
}
