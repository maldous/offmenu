#!/usr/bin/env python3
"""Read-only inventory of a retained sampled semantic lane; never grants admission."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


class InventoryError(ValueError):
    pass


def inventory(root):
    root = Path(root).resolve()
    pins = {}

    def read_bytes(name):
        path = (root / name).resolve()
        if not path.is_relative_to(root):
            raise InventoryError(f'path escapes lane: {name}')
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if name in pins and pins[name] != digest:
            raise InventoryError(f'input changed during inventory: {name}')
        pins[name] = digest
        return raw

    def read(name, lines=False):
        raw = read_bytes(name)
        return [json.loads(row) for row in raw.splitlines() if row.strip()] if lines else json.loads(raw)

    state = read('checkpoint/queue-state.json')['byItem']
    admission = read('admission/all.admission.json')
    queues = []
    for path in sorted((root / 'queue').glob('*.queue.jsonl')):
        queues.extend(read(path.relative_to(root).as_posix(), lines=True))
    ids = [row['itemId'] for row in queues]
    if len(ids) != len(set(ids)) or set(ids) != set(state):
        raise InventoryError('queue/checkpoint IDs differ or duplicate')
    judgments = {}
    models, fields, stages, datasets = Counter(), Counter(), Counter(), Counter()
    for path in sorted((root / 'judgments').glob('*/*.json')):
        name = path.relative_to(root).as_posix()
        row = read(name)
        item = row['itemId']
        if item in judgments:
            raise InventoryError(f'duplicate judgment: {item}')
        if item not in state or row['dataset'] != state[item]['dataset']:
            raise InventoryError(f'judgment/checkpoint mismatch: {item}')
        judgments[item] = (name, row)
        models[row['model']['modelId']] += 1
        if state[item]['status'] == 'done':
            if state[item]['file'] != name:
                raise InventoryError(f'checkpoint file mismatch: {item}')
            fields.update(f['provenanceState'] for f in row['fields'])
            stages[row['stage']] += 1
        for citation in row.get('citations', []):
            read(citation['sampleFile'])  # Pin evidence bytes; do not invent archive hashes.
    if set(judgments) != set(ids):
        raise InventoryError('judgment/queue IDs differ')
    done = {name for item, (name, _) in judgments.items() if state[item]['status'] == 'done'}
    blocked = {item for item in ids if state[item]['status'] == 'blocked'}
    admitted = admission['admitted']
    failed = admission['failed']
    if len(admitted) != len(set(admitted)) or set(admitted) != done:
        raise InventoryError('historical checker passed set differs from done set')
    if len(failed) != len(blocked) or {row['itemId'] for row in failed} != blocked:
        raise InventoryError('historical checker failed set differs from blocked set')
    for row in failed:
        if judgments[row['itemId']][0] != row['file']:
            raise InventoryError('historical failure file mismatch')
    for row in queues:
        datasets[row['dataset']] += 1
        if row['dataset'] != state[row['itemId']]['dataset']:
            raise InventoryError('queue/checkpoint dataset mismatch')
    expected = {'judgments': len(ids), 'admitted': len(done), 'failed': len(blocked)}
    if admission['totals'] != expected or admission.get('sampledOnly') is not True:
        raise InventoryError('historical checker totals/sampled scope mismatch')
    glossary = read('glossary/proposals.jsonl', lines=True)
    if any(row.get('status') != 'proposal-unfrozen' for row in glossary):
        raise InventoryError('glossary is no longer uniformly proposal-unfrozen')
    manifest = read('reviews/20261015-w02-corrections-manifest-W06.json')
    correction_matches = {}
    for row in manifest['changedFiles']:
        name = row['path']
        digest = hashlib.sha256(read_bytes(name)).hexdigest()
        correction_matches[name] = digest == row['postSha256']
    if not all(correction_matches.values()):
        raise InventoryError('documentary correction bytes differ from pinned generation')
    for name, digest in pins.items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
            raise InventoryError(f'input changed during inventory: {name}')
    return {
        'schema': 'semantic-candidate-inventory/1', 'sampledOnly': True,
        'queueItems': len(ids), 'checkpointStates': dict(Counter(v['status'] for v in state.values())),
        'datasets': dict(datasets), 'modelLabelsPreserved': dict(models),
        'doneFields': dict(fields), 'doneStages': dict(stages),
        'historicalCheckerCounts': expected,
        'checkerScope': 'Retained report reconciled by identity; semantic validation was not rerun.',
        'glossaryProposalRows': len(glossary), 'documentaryCorrectionBytesMatch': correction_matches,
        'admissionGranted': False, 'glossaryFrozen': False,
        'gates': ['Historical model labels require separate provenance qualification',
                  f'{len(blocked)} archive-pin blocked judgments remain excluded',
                  'new inventory requires distinct independent review and Morgan custody'],
        'inputSHA256': dict(sorted(pins.items())),
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lane', required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(inventory(args.lane), indent=2, ensure_ascii=False))
    except (InventoryError, KeyError, OSError, ValueError) as exc:
        parser.exit(1, f'inventory blocked: {exc}\n')
