// Unmounted composition only. All readers and custody callbacks are trusted
// server dependencies; this module provides no route, store, key or authority.
import {createOwnedSnapshotExtractor} from './owned-snapshot-extractor.mjs';
import {createPrivatePortability, validatePrivatePayload, digest, canonical} from './private-portability-v1.mjs';

export function createOwnedBackupExporter({readAuthority, openSnapshot,
  authorizeSourceRecord, resolveKey, custody='server-envelope', clock}={}) {
  return Object.freeze({async exportOwnedBackup(request={}) {
    if(!request || typeof request!=='object' || Array.isArray(request) ||
      Object.keys(request).some(k=>!['packageId','recoveryRef','keyReference'].includes(k)))
      throw Error('Owned backup unavailable (REQUEST_SCOPE).');
    const {packageId,recoveryRef,keyReference}=request;
    // One fence spans extraction AND export. Keep it inside this invocation so
    // concurrent packages cannot share or replace each other's authority stamp.
    let authorityFence;
    const readFencedAuthority=async query=>{
      const current=canonical(await readAuthority(query));
      if(authorityFence===undefined)authorityFence=current;
      else if(current!==authorityFence)throw Error('Owned backup unavailable (AUTHORITY_CHANGED).');
      return JSON.parse(current);
    };
    const extractor=createOwnedSnapshotExtractor({readAuthority:readFencedAuthority, openSnapshot,
      authorizeSourceRecord, validatePayload:validatePrivatePayload, digest, clock});
    const portability=createPrivatePortability({readAuthority:readFencedAuthority, resolveKey, custody, clock});
    const snapshot=await extractor.extractOwnedSnapshot({packageId});
    if(snapshot.inventory.complete!==true || snapshot.blockers.length!==0)
      throw Error('Owned backup unavailable (INCOMPLETE_SNAPSHOT).');
    // Do not manufacture readAuthority.backupInventory from inventory.complete.
    // The existing exporter freshly checks the independently retained package
    // attestation/digest, identity, consent and deletion scope before encryption
    // and checks current authority again before returning the sealed package.
    return portability.exportPackage({packageId,kind:'owned-backup',
      sourceSchemaVersion:'offmenu-household-domain/1',payload:snapshot.payload,
      recoveryRef,keyReference});
  }});
}
