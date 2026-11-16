#!/usr/bin/env python3
"""Counts only: exact namespace keys and candidate paths in a completed index."""
import argparse,collections,fcntl,hashlib,json,os,sqlite3,time
from pathlib import Path
from urllib.parse import quote
SQL='''SELECT key_sha,min(source),min(release),min(namespace),count(DISTINCT subject),
max(EXISTS(SELECT 1 FROM resolved_edges e WHERE e.subject=i.subject)),
max(EXISTS(SELECT 1 FROM resolved_edges e WHERE e.subject=i.subject AND e.has_context=1))
FROM identifiers i GROUP BY key_sha'''

def sha_file(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def summarize(rows):
    groups={}
    for _,source,release,namespace,products,profile,context in rows:
        group=groups.setdefault((source,release,namespace),collections.Counter())
        group['sourceScopedKeys']+=1
        if products==1:
            group['uniqueProductKeys']+=1;group['productProfileKeys']+=int(bool(profile));group['productProfileContextKeys']+=int(bool(context))
        else:group['ambiguousProductKeysNotMerged']+=1
    return [dict(sourceId=s,sourceRelease=r,namespace=n,**dict(c)) for (s,r,n),c in sorted(groups.items())]

def inspect(package,deadline_seconds=600):
    deadline=time.monotonic()+deadline_seconds
    manifest_path=package/'manifest.json'
    with (package/'.writer.lock').open('rb') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_SH|fcntl.LOCK_NB)
        b=manifest_path.read_bytes();m=json.loads(b)
        if not m.get('complete') or m.get('semanticStatus')!='candidate-not-admitted':raise ValueError('CompletedCandidateManifestRequired')
        dbpath=package/'consumer-index.sqlite'
        if sha_file(dbpath)!=m['consumerIndex']['sqliteSha256']:raise ValueError('ConsumerIndexDigestMismatch')
        uri='file:'+quote(str(dbpath.resolve()),safe='/')+'?mode=ro&immutable=1'
        db=sqlite3.connect(uri,uri=True)
        try:
            db.execute('PRAGMA query_only=ON');db.execute('PRAGMA cache_size=-32768');db.execute('PRAGMA temp_store=MEMORY')
            db.set_progress_handler(lambda:int(time.monotonic()>=deadline),10000)
            groups=summarize(db.execute(SQL))
        finally:db.close()
        totals={k:sum(g.get(k,0) for g in groups) for k in ('sourceScopedKeys','uniqueProductKeys','ambiguousProductKeysNotMerged','productProfileKeys','productProfileContextKeys')}
        expected=m['consumerIndex']['queries']
        for actual,prior in [('sourceScopedKeys','sourceScopedProductIdentifierKeys'),('uniqueProductKeys','uniqueSourceScopedProductKeys'),('ambiguousProductKeysNotMerged','ambiguousProductKeysNotMerged'),('productProfileKeys','identifierProductProfileJoins'),('productProfileContextKeys','identifierProductProfileNutrientContextJoins')]:
            if totals[actual]!=expected[prior]['count']:raise ValueError('NamespaceAggregateReconciliationMismatch')
        return {'schemaVersion':'offmenu-north-star-namespace-query-proof/1','inputManifestByteSha256':hashlib.sha256(b).hexdigest(),
                'inputSqliteSha256':m['consumerIndex']['sqliteSha256'],'sourceSelection':m['selection'],'query':SQL,
                'groups':groups,'totals':totals,'lexicalValuesExported':False,'crossNamespaceEquivalenceAsserted':False,
                'candidateOnly':True,'acceptedIdentityJoins':0,'servedAppQueries':0,
                'inputConstraint':'Pinned single-citation bulk producer; not a general merged-source packet proof.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('package',type=Path);a=p.parse_args();print(json.dumps(inspect(a.package),sort_keys=True))
