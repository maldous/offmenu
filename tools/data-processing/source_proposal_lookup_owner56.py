"""Local, immutable V2 source-proposal lookup. No canonical or gold admission."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

MANIFEST_SHA256 = 'b0df942a7f75e71cf157ed3aefedb7ca080265ea2136488792850c1564287bd6'
BUNDLE_SHA256 = '7dff66be08e1b0161223bd360ec9596e1dde28230bea578182947fb7833438a4'
FREEZE_SHA256 = '6e290fe026c4748e9b278a71e8db973f235aa95ef617733c8fc9151ceb5afeb7'


def pinned_json(path, digest):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('Frozen input digest mismatch')
    return json.loads(raw)


class SourceProposalLookup:
    def __init__(self, manifest_path, bundle_path):
        self._manifest = pinned_json(manifest_path, MANIFEST_SHA256)
        self._bundle = pinned_json(bundle_path, BUNDLE_SHA256)
        if self._bundle['frozenMaster']['sha256'] != FREEZE_SHA256:
            raise ValueError('Unexpected master freeze')
        self._index = {}
        for record in self._bundle['proposals']:
            identity = record['identity']
            key = (identity['sourceId'], identity['code'])
            self._index.setdefault(key, []).append(record)

    def lookup(self, source, code, language, release=None):
        if any(not isinstance(v, str) or not v for v in (source, code, language)):
            raise ValueError('source, code and language must be nonempty exact strings')
        if release is not None and (not isinstance(release, str) or not release):
            raise ValueError('release must be a nonempty exact string')
        records = self._index.get((source, code), [])
        if release is not None:
            records = [r for r in records if r['identity']['releaseBinding'] == release]
        result = {'source': source, 'code': code, 'language': language,
                  'status': 'unknown', 'reason': 'source-code-or-release-not-found',
                  'label': None, 'citations': [], 'availableLanguages': [],
                  'collisionDistinctions': [], 'canonicalAccepted': False,
                  'semanticGold': False, 'translationAccepted': False,
                  'crossSourceEquivalence': None, 'freezeSHA256': FREEZE_SHA256,
                  'bundleSHA256': BUNDLE_SHA256}
        if not records:
            return result
        if len(records) != 1:
            result['reason'] = 'ambiguous-source-release; specify release'
            return result
        r = records[0]
        p = r['originalProposal']
        labels = {p['language']: p['label']} if 'label' in p else {
            lang: v['literal'] for lang, v in p['sourceLabels'].items()}
        result.update(identity=copy.deepcopy(r['identity']), proposalId=r['proposalId'],
                      availableLanguages=sorted(labels), sourceReview=copy.deepcopy(r['sourceReview']),
                      sourceReviewScope=r['sourceReviewScope'],
                      proposalStatus=r['bundleStatus'], originalWorkflowStatus=p.get('workflowStatus'))
        if language not in labels:
            result['reason'] = 'language-not-available; no fallback or generated translation'
            return result
        rights = p.get('rights')
        if rights is None:
            rights = next(s['rights'] for s in self._manifest['sources']
                          if s['sourceId'] == source and s.get('release') == r['identity']['releaseBinding'])
        citations = [p['evidence']] if 'label' in p else [
            p['sourceLabels'][language]['citation'], p['componentCitation'],
            p['unit']['sourceLabels'][language]['citation']]
        collisions = [c for c in self._bundle['exactLiteralCollisions']
                      if c['language'] == language and
                      any(x['proposalId'] == r['proposalId'] for x in c['records'])]
        result.update(status='source-proposal', reason=None, label=labels[language],
                      citations=copy.deepcopy(citations), rights=copy.deepcopy(rights),
                      collisionDistinctions=copy.deepcopy(collisions))
        if 'unit' in p:
            result.update(unit=copy.deepcopy(p['unit']), denominator=copy.deepcopy(p['denominator']),
                          qualifiers=copy.deepcopy(p['qualifiers']), density=p['density'],
                          crossComponentEquivalence=p['crossComponentEquivalence'])
        return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--bundle', required=True, type=Path)
    parser.add_argument('--source', required=True)
    parser.add_argument('--code', required=True)
    parser.add_argument('--language', required=True)
    parser.add_argument('--release')
    args = parser.parse_args()
    try:
        lookup = SourceProposalLookup(args.manifest, args.bundle)
        print(json.dumps(lookup.lookup(args.source, args.code, args.language, args.release), ensure_ascii=False))
    except (ValueError, OSError) as error:
        parser.exit(2, str(error) + '\n')
