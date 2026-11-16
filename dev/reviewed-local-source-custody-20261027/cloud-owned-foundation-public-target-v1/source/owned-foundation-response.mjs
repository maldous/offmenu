import {FOUNDATION_SELECTIONS,FOUNDATION_BLOBS} from './foundation-production-release.mjs';
import {createOwnedFoundationResponse} from './corpus/owned-foundation-response.mjs';
const fixed=new Map(Object.entries(FOUNDATION_BLOBS).map(([key,value])=>[key,Object.freeze({...value})]));
async function readBlob(key,descriptor){const d=fixed.get(key);if(!d||!descriptor||descriptor.key!==key||descriptor.sha256!==d.sha256||descriptor.bytes!==d.bytes||descriptor.uncompressedBytes!==d.uncompressedBytes||d.bytes>1048576)throw Error('OWN_FOUNDATION_BLOB_UNAVAILABLE');const bytes=Uint8Array.from(atob(d.bodyBase64),c=>c.charCodeAt(0));if(bytes.length!==d.bytes)throw Error('OWN_FOUNDATION_BLOB_UNAVAILABLE');return bytes;}
export const ownedFoundationResponse=createOwnedFoundationResponse({readBlob,selections:FOUNDATION_SELECTIONS});
