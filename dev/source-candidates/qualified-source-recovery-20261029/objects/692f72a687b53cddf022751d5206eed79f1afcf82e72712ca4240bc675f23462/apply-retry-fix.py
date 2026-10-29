from pathlib import Path
import hashlib,re
root=Path('/tmp/offmenu-worker00-pr42-20261018');p=root/'offmenu/refresh/product_adapters.py';s=p.read_text()
start=s.index("        manifest = {'schemaVersion': 'offmenu-product-candidate/1'")
end=s.index("        (pending / 'manifest.json').write_bytes",start)
constructor=s[start:end]
body=constructor.replace('        manifest = ', '    return ',1)
body='\n'.join(line[4:] if i else line for i,line in enumerate(body.splitlines()))+'\n'
# Keep a single complete manifest constructor shared by creation and replay.
helper='''def _candidate_stats(path, limits):
    """Recompute displayed metadata from the verified bounded candidate bytes."""
    count = total = 0
    kinds = {}
    with path.open('rb') as source:
        while True:
            line = source.readline(limits.max_line_bytes + 1)
            if not line:
                break
            total += len(line)
            if len(line) > limits.max_line_bytes or total > limits.max_output_bytes:
                raise RefreshError('product-retry-candidate-bound')
            packet = strict_json(line)
            if (not isinstance(packet, list) or len(packet) != 1
                    or not isinstance(packet[0], dict) or not isinstance(packet[0].get('kind'), str)):
                raise RefreshError('product-retry-candidate-shape')
            kind = packet[0]['kind']
            kinds[kind] = kinds.get(kind, 0) + 1
            count += 1
    return count, total, kinds


def _candidate_manifest(context, files, contract, hashes, raw_rows, count, kinds, output_bytes):
'''+body.replace('budget.rows','raw_rows')+'\n\n'
s=s[:start]+"        manifest = _candidate_manifest(context, files, contract, hashes, budget.rows, count, kinds, output_bytes)\n"+s[end:]
needle="\ndef normalize_products(context, inputs, destination, *, limits=ProductLimits()):";assert s.count(needle)==1;s=s.replace(needle,'\n'+helper+needle)
old="""        for name, checksum in manifest['outputHashes'].items():
            if name not in ('candidate.jsonl', 'source.sqlite') or _hash(_safe(destination / name), limits.max_output_bytes if name == 'candidate.jsonl' else limits.max_database_bytes) != checksum:
                raise RefreshError('product-retry-output-mismatch')
        if set(manifest['outputHashes']) != {'candidate.jsonl', 'source.sqlite'}:
            raise RefreshError('product-retry-output-mismatch')
        return manifest
"""
new="""        hashes = manifest.get('outputHashes')
        if not isinstance(hashes, dict) or set(hashes) != {'candidate.jsonl', 'source.sqlite'}:
            raise RefreshError('product-retry-output-mismatch')
        for name, checksum in hashes.items():
            if _hash(_safe(destination / name), limits.max_output_bytes if name == 'candidate.jsonl' else limits.max_database_bytes) != checksum:
                raise RefreshError('product-retry-output-mismatch')
        count, output_bytes, kinds = _candidate_stats(destination / 'candidate.jsonl', limits)
        with sqlite3.connect((destination / 'source.sqlite').as_uri() + '?mode=ro&immutable=1', uri=True) as db:
            raw_rows = db.execute('SELECT COUNT(*) FROM raw').fetchone()[0]
        expected = _candidate_manifest(context, files, contract, hashes, raw_rows, count, kinds, output_bytes)
        # Canonical bytes also distinguish JSON false from numeric zero.
        if canonical(manifest) != canonical(expected):
            raise RefreshError('product-retry-manifest-mismatch')
        return manifest
""";assert old in s;s=s.replace(old,new);p.write_text(s)
p=root/'offmenu/refresh/product_origin_stage.py';s=p.read_text().replace('ProductContext, ProductLimits, _hash, _safe, _zip_metadata','ProductContext, ProductLimits, _candidate_stats, _hash, _safe, _zip_metadata')
start=s.index("        manifest = {**source_manifest, 'schemaVersion': VERSION");end=s.index('        qualification = qualify(',start);constructor=s[start:end];body=constructor.replace('        manifest = ','    return ',1);body='\n'.join(line[4:] if i else line for i,line in enumerate(body.splitlines()))+'\n';helper='''def _stage_manifest(source_manifest, stage_contract, hashes, count, candidate_bytes, originals):
'''+body+'\n\n';s=s[:start]+"        manifest = _stage_manifest(source_manifest, stage_contract, hashes, count, candidate_bytes, originals)\n"+s[end:];needle='\ndef qualify_product_origins(';s=s.replace(needle,'\n'+helper+needle)
needle="            qualification = qualify(enriched_contract, root, destination / 'candidate.jsonl', manifest)"
replacement="""            count, candidate_bytes, kinds = _candidate_stats(destination / 'candidate.jsonl', limits)
            expected = _stage_manifest(source_manifest, stage_contract, manifest['outputHashes'], count, candidate_bytes, originals)
            if canonical(manifest) != canonical(expected):
                raise RefreshError('product-origin-stage-manifest-mismatch')
"""+needle;assert s.count(needle)==1;s=s.replace(needle,replacement);p.write_text(s)
# The origin emitter explicitly binds exact adapter implementation identity.
p=root/'offmenu/refresh/product_field_origins.py';s=p.read_text();pin=hashlib.sha256((root/'offmenu/refresh/product_adapters.py').read_bytes()).hexdigest();s,n=re.subn(r"ADAPTER_SHA256 = '[a-f0-9]{64}'", "ADAPTER_SHA256 = '"+pin+"'",s);assert n==1;p.write_text(s);print('new reviewed dependency pin requires independent review:',pin)
