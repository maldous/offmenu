#!/usr/bin/env python3
"""Project reviewed immutable NorthStar candidate sidecars; never promote identity/admission."""
import argparse,hashlib,json,os,re,tempfile
from pathlib import Path
BASE=Path('/offmenu/data/.offmenu-platform/corpus-recovery-20261028-v1')
SOURCE=BASE/'north-star-derived-20261028/full-bulk-v1'
OUT=BASE/'final-common-publication/north-star-publication-delta'
PREFIX='/common-data/derived-releases/north-star-structural-v2-20261028/'
SITE='a1df1508-4bb9-4b55-ab1f-88611e456e61'
BASE_URL='https://offmenu-corpus.netlify.app/common-data/releases/common-corpus-expanded-20261014/manifest.json'
def sha(b):return hashlib.sha256(b).hexdigest()
def project(m,proof,producer_sha,proof_sha,base_sha):
 if m.get('schemaVersion')!='offmenu-north-star-full-derivation/1' or m.get('complete') is not True or m.get('status')!='all-selected-packets-derived-and-consumer-queries-exercised':raise ValueError('ProducerIncomplete')
 if m.get('expectedAssets')!=m.get('completedAssets') or m.get('semanticStatus')!='candidate-not-admitted' or m.get('candidateOnly') is not True or m.get('originalsModified') is not False:raise ValueError('ProducerSemanticsMismatch')
 if proof.get('producerManifestSha256')!=producer_sha or proof.get('status')!='reviewed-source-scoped-consumer-proof' or proof.get('publicationScope')!='candidate-sidecars-only' or proof.get('sourceRightsPreserved') is not True or proof.get('privatePayloadExcluded') is not True:raise ValueError('PublicationReviewUnresolved')
 index=m['consumerIndex']
 if index.get('acceptedIdentityJoins')!=0 or index.get('servedAppQueries')!=0:raise ValueError('UnexpectedConsumerAdmission')
 files=[];seen=set()
 for f in m['files']:
  key=f.get('key')
  if not isinstance(key,str) or not re.fullmatch(r'shards/[0-9]{6}/derivations.jsonl.gz',key) or key in seen or not re.fullmatch('[0-9a-f]{64}',f.get('sha256','')) or type(f.get('bytes')) is not int or f['bytes']<0:raise ValueError('NonPublicArtifact')
  seen.add(key);files.append({k:f[k] for k in ('key','bytes','sha256','sidecarPackets')})
 if len(files)!=m['completedAssets']:raise ValueError('PublicShardCoverageMismatch')
 return {'schemaVersion':'offmenu-north-star-publication-projection/1','releaseId':'north-star-structural-v2-20261028','status':'reviewed-candidate-publication-projection','scope':'Full selected bulk-food structural sidecars only; recipe context, accepted culinary identity and application served coverage are separate obligations.','semanticStatus':'candidate-not-admitted','candidateOnly':True,'confidence':m['confidence'],'acceptedIdentityJoins':0,'servedAppQueries':0,'producerManifestSha256':producer_sha,'reviewedConsumerProofSha256':proof_sha,'producerPublicationState':{'publicationEligible':m.get('publicationEligible'),'publicAdmissionGranted':m.get('publicAdmissionGranted')},'baseDependencies':{**m['baseDependencies'],'servedBaseRelease':'common-corpus-expanded-20261014','servedBaseManifestUrl':BASE_URL,'servedBaseManifestByteSha256':base_sha},'selection':m['selection'],'counts':m['counts'],'consumerEvidence':{'queries':index['queries'],'scope':'Local full selected-source typed index queries, not application served coverage'},'files':files,'sourceRights':'Original citations and rights remain in the pinned selected base graph. No new identity or rights grant inferred.'}
def durable_write(path,data):
 with path.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
def sync_dir(path):
 fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
def publish_descriptor(path,data):
 # Exclusive hard-link publication cannot replace an existing descriptor.
 fd,temp=tempfile.mkstemp(prefix=path.name+'.tmp-',dir=path.parent)
 with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 os.link(temp,path);sync_dir(path.parent)
 os.unlink(temp);sync_dir(path.parent)
def main():
 p=argparse.ArgumentParser();p.add_argument('--producer-manifest-sha256',required=True);p.add_argument('--consumer-proof-sha256',required=True);p.add_argument('--served-base-manifest-sha256',required=True);p.add_argument('--base-deploy-id',required=True);a=p.parse_args()
 for pin in (a.producer_manifest_sha256,a.consumer_proof_sha256,a.served_base_manifest_sha256):assert re.fullmatch('[0-9a-f]{64}',pin)
 assert re.fullmatch('[0-9a-f]{24}',a.base_deploy_id)
 mb=(SOURCE/'manifest.json').read_bytes();pb=(SOURCE/'reviewed-consumer-proof.json').read_bytes();assert sha(mb)==a.producer_manifest_sha256 and sha(pb)==a.consumer_proof_sha256
 projection=project(json.loads(mb),json.loads(pb),a.producer_manifest_sha256,a.consumer_proof_sha256,a.served_base_manifest_sha256)
 descriptor=BASE/'final-common-publication/north-star-publication-delta.json';assert not OUT.exists() and not descriptor.exists(),'Reconcile existing immutable candidate rather than overwrite'
 OUT.parent.mkdir(parents=True,exist_ok=True)
 staging=Path(tempfile.mkdtemp(prefix=OUT.name+'.tmp-',dir=OUT.parent));sync_dir(OUT.parent)
 target=staging/PREFIX.lstrip('/');target.mkdir(parents=True);files=[]
 for f in projection['files']:
  source=SOURCE/f['key'];assert source.is_file() and not source.is_symlink();h1=hashlib.sha1();h256=hashlib.sha256();size=0
  with source.open('rb') as stream:
   for b in iter(lambda:stream.read(1048576),b''):h1.update(b);h256.update(b);size+=len(b)
  assert size==f['bytes'] and h256.hexdigest()==f['sha256']
  dest=target/f['key'];dest.parent.mkdir(parents=True,exist_ok=True);os.link(source,dest)
  files.append({'path':PREFIX+f['key'],'bytes':size,'sha1':h1.hexdigest(),'sha256':h256.hexdigest()})
 b=(json.dumps(projection,ensure_ascii=False,separators=(',',':'))+'\n').encode();durable_write(target/'manifest.json',b);files.append({'path':PREFIX+'manifest.json','bytes':len(b),'sha1':hashlib.sha1(b).hexdigest(),'sha256':sha(b)})
 d={'schemaVersion':'offmenu-netlify-north-star-delta/1','siteId':SITE,'baseDeployId':a.base_deploy_id,'consumerProofSha256':a.consumer_proof_sha256,'producerManifestSha256':a.producer_manifest_sha256,'servedBaseManifestSha256':a.served_base_manifest_sha256,'semanticStatus':'candidate-not-admitted','acceptedIdentityJoins':0,'servedAppQueries':0,'files':files}
 db=(json.dumps(d,separators=(',',':'))+'\n').encode()
 # Caller retains the approved exclusive publication output-root reservation.
 # Foreign/earlier staging is never reused or removed. Descriptor is published
 # only after the complete delta and every directory entry are durable.
 for directory in sorted((p for p in staging.rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True):sync_dir(directory)
 sync_dir(staging)
 assert not OUT.exists() and not descriptor.exists(),'Reconcile existing immutable candidate rather than overwrite'
 os.rename(staging,OUT);sync_dir(OUT.parent)
 publish_descriptor(descriptor,db)
 print(json.dumps({'status':'north_star_candidate_projection_ready_not_published','descriptor_sha256':sha(db),'descriptor_bytes':len(db),'projection_manifest_sha256':sha(b),'delta_files':len(files),'semanticStatus':'candidate-not-admitted','acceptedIdentityJoins':0,'servedAppQueries':0}))
if __name__=='__main__':main()
