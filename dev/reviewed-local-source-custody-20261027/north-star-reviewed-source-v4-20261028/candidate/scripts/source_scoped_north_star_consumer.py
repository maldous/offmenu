"""Bounded offline source-identifier lookup over exact immutable source pins.

This is not a serving activation or identity-admission service. Callers must
explicitly request candidate context; no external lookup or text matching is
performed. Indices and payloads stay on the authorized local worker.
"""
import gzip
import io
import json
import sqlite3
from urllib.parse import quote
from derive_north_star_bulk import checked_asset,sha_file,sha_bytes
from north_star_derivations import digest,PROP,REL,TYPE

# The resolved table is materialized from these same edge rows. Explicitly
# preserve its subject equality so SQLite can use the existing resolved_subject
# index instead of scanning the whole corpus for each source-key lookup.
PROFILE_EDGE_SQL = ('SELECT e.object,e.source_edge_id,e.source_edge_sha '
                    'FROM edges e JOIN resolved_edges r '
                    'ON r.id=e.id AND r.subject=e.subject WHERE e.subject=?')


def pinned_json(path,pin):
    b=path.read_bytes()
    if sha_bytes(b)!=pin:raise ValueError('manifest pin differs')
    return json.loads(b)


def readonly_index(path,pin):
    if sha_file(path)!=pin:raise ValueError('consumer index pin differs')
    db=sqlite3.connect('file:'+quote(str(path.resolve()),safe='/')+'?mode=ro&immutable=1',uri=True)
    db.execute('PRAGMA query_only=ON');db.execute('PRAGMA cache_size=-16384')
    return db


class SourceScopedConsumer:
    """The supplied roots must be authorized, immutable worker-local packages."""
    def __init__(self,source,bulk_derived,basis_derived,bulk_manifest_pin,basis_manifest_pin):
        self.source=source;self.bulk_root=bulk_derived;self.basis_root=basis_derived
        self.bulk=pinned_json(bulk_derived/'manifest.json',bulk_manifest_pin)
        self.basis=pinned_json(basis_derived/'manifest.json',basis_manifest_pin)
        if self.bulk.get('complete') is not True or self.basis.get('complete') is not True:
            raise ValueError('completed selected derived packages required')
        if any(m.get('semanticStatus')!='candidate-not-admitted' or m.get('publicationEligible') is not False for m in (self.bulk,self.basis)):
            raise ValueError('candidate semantic contract differs')
        source_pin=self.bulk['selection']['manifestByteSha256']
        if source_pin!=self.basis['selection']['normalizedManifestByteSha256']:
            raise ValueError('source selections differ')
        self.manifest=pinned_json(source/'manifest.json',source_pin)
        self.files={f['key']:f for f in self.manifest['files']}
        self.ordinals={f['key']:i for i,f in enumerate(f for f in self.manifest['files'] if f['key'].endswith('.jsonl.gz') and 'packets' in f)}
        self.bulk_files={f['key']:f for f in self.bulk['files']};self.basis_files={f['key']:f for f in self.basis['files']}
        self.index=readonly_index(bulk_derived/'consumer-index.sqlite',self.bulk['consumerIndex']['sqliteSha256'])
        try:self.locations=readonly_index(basis_derived/'matched-proof.sqlite',self.basis['consumerProof']['sqliteSha256'])
        except BaseException:self.index.close();raise
        self.pins={'sourceManifestByteSha256':source_pin,'bulkDerivedManifestByteSha256':bulk_manifest_pin,'basisDerivedManifestByteSha256':basis_manifest_pin}

    def close(self):self.index.close();self.locations.close()

    def _packet(self,resource_id,source_id,release):
        loc=self.locations.execute('SELECT asset_key,packet_ordinal,asset_sha FROM locations WHERE resource_id=?',(resource_id,)).fetchone()
        if loc is None:raise ValueError('source resource locator unresolved')
        key,ordinal,asset_sha=loc;entry=self.files.get(key)
        if not entry or entry['sha256']!=asset_sha or key not in self.ordinals:raise ValueError('source resource locator pin differs')
        with gzip.GzipFile(fileobj=io.BytesIO(checked_asset(self.source,entry))) as stream:
            packet=None
            for n,line in enumerate(stream):
                if n==ordinal:packet=json.loads(line);break
        if packet is None:raise ValueError('source resource packet ordinal missing')
        if len(packet['resources'])!=1:raise ValueError('selected single-resource bulk packet required')
        if len(packet['citations'])!=1:raise ValueError('selected single-citation bulk packet required')
        resources=[r for r in packet['resources'] if r['id']==resource_id]
        if len(resources)!=1:raise ValueError('source resource identity differs')
        resource=resources[0];citations={c['id']:c for c in packet['citations']}
        cid=packet['citations'][0]['id']
        if any(row['citationIds']!=[cid] for bucket in ('resources','assertions','relations') for row in packet[bucket]):
            raise ValueError('selected single-citation bulk references differ')
        if resource['scope'].get('visibility')!='public' or not resource['citationIds']:raise ValueError('public source context required')
        for bucket in ('resources','assertions','relations','citations'):
            if any(row['scope']!=resource['scope'] for row in packet[bucket]):raise ValueError('source packet scope differs')
        for cid in resource['citationIds']:
            c=citations.get(cid)
            if not c or c['scope']!=resource['scope'] or c['sourceId']!=source_id or str(c.get('revisionId'))!=release:
                raise ValueError('source release citation context differs')
        selection={'manifestByteSha256':self.pins['sourceManifestByteSha256'],'assetKey':key,'assetSha256':asset_sha,'packetOrdinal':ordinal}
        return packet,resource,selection

    def _sidecar(self,root,files,name,packet,resource_id,selection,selection_key):
        key=f"shards/{self.ordinals[selection['assetKey']]:06d}/"+name
        entry=files.get(key)
        if not entry:return None
        selected=[]
        with gzip.GzipFile(fileobj=io.BytesIO(checked_asset(root,entry))) as stream:
            for line in stream:
                row=json.loads(line)
                if row.get(selection_key)==selection and (selection_key=='inputSelection' or row.get('subjectId')==resource_id):selected.append(row)
        if len(selected)>1:raise ValueError('ambiguous derived packet context')
        if not selected:return None
        row=selected[0]
        if row['inputPacketCanonicalSha256']!=digest(packet) or row['status']!='candidate-not-admitted':raise ValueError('derived packet binding differs')
        return row

    def lookup(self,source_id,release,namespace,lexical_value,*,include_candidates=False):
        base={'schemaVersion':'offmenu-source-scoped-product-query/1','sourcePins':self.pins,'acceptedIdentityJoins':0,
              'automaticPlanningEligible':False,'nutritionAggregationEligible':False,'servedApplicationActivation':False}
        if include_candidates is not True:return dict(base,status='candidates-not-requested',products=[])
        if any(not isinstance(v,str) or not v for v in (source_id,release,namespace,lexical_value)):raise ValueError('explicit source/release/namespace/lexical key required')
        key=digest([source_id,release,namespace,lexical_value])
        rows=self.index.execute('SELECT DISTINCT i.subject,i.assertion_id,i.assertion_sha FROM identifiers i JOIN nodes n ON n.id=i.subject WHERE i.key_sha=? AND i.source=? AND i.release=? AND i.namespace=? AND i.lexical=? AND n.type=?',
                                (key,source_id,release,namespace,lexical_value,TYPE+'FoodProduct')).fetchall()
        products={r[0] for r in rows}
        if not products:return dict(base,status='source-key-not-found',products=[])
        if len(products)!=1:return dict(base,status='ambiguous-source-product-key',candidateProductCount=len(products),products=[])
        product_id=next(iter(products));packet,product,selection=self._packet(product_id,source_id,release)
        if product['type']!=TYPE+'FoodProduct':raise ValueError('source product type differs')
        facts={a['id']:a for a in packet['assertions']};identifier_evidence=[]
        for _,aid,pin in rows:
            a=facts.get(aid)
            if not a or digest(a)!=pin or a['subjectId']!=product_id or a['propertyId']!=PROP+'sourceIdentifier':raise ValueError('identifier evidence differs')
            f=a['value']['fields']
            if f['system']['value']!=namespace or f['value']['value']!=lexical_value:raise ValueError('exact identifier fields differ')
            identifier_evidence.append(a)
        edges=self.index.execute(PROFILE_EDGE_SQL,(product_id,)).fetchall()
        original_edges={e['id']:e for e in packet['relations']};profiles=[]
        for profile_id,eid,pin in edges:
            edge=original_edges.get(eid)
            if not edge or digest(edge)!=pin or edge['predicateId']!=REL+'hasCompositionObservation' or edge['subjectId']!=product_id or edge['objectId']!=profile_id:
                raise ValueError('explicit product profile edge differs')
            p,r,s=self._packet(profile_id,source_id,release)
            if r['type']!=TYPE+'FoodCompositionObservation':raise ValueError('source profile type differs')
            context=self._sidecar(self.bulk_root,self.bulk_files,'derivations.jsonl.gz',p,profile_id,s,'inputSelection')
            basis=self._sidecar(self.basis_root,self.basis_files,'basis-restorations.jsonl.gz',p,profile_id,s,'inputNormalizedSelection')
            profiles.append({'resource':r,'citations':p['citations'],'sourceEdge':edge,'sourceSelection':s,'nutrientContextCandidates':context,'perNutrientBasisCandidates':basis})
        return dict(base,status='source-scoped-candidate-context' if profiles else 'source-product-without-resolved-profile',
                    products=[{'resource':product,'citations':packet['citations'],'identifierEvidence':identifier_evidence,'sourceSelection':selection,'profiles':profiles}])
