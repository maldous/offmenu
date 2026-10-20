#!/usr/bin/env python3
"""Build a local processing-provenance ledger from a source-parse run manifest.

The builder reads manifests and hashes existing output artifacts; it does not
read originals, run parsers, call models, or perform network operations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

SCHEMA_VERSION = 'offmenu-processing-provenance-ledger/1'


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _stage(*, status: str, method: str | None, engine: dict,
           input_location: str | None = None, input_sha256: str | None = None,
           outputs: list[dict] | None = None, validation_status: str,
           validation_evidence: list[dict] | None = None,
           issues: list[str] | None = None, agent_provenance: dict | None = None) -> dict:
    return {
        'status': status,
        'method': method,
        'engine': engine,
        'input': {'location': input_location, 'sha256': input_sha256},
        'cachedOutput': outputs or [],
        'processingDate': {'value': None, 'status': 'unknown',
                           'evidence': ['No processing timestamp is embedded in the source run manifest.']},
        'validation': {'status': validation_status, 'evidence': validation_evidence or [],
                       'unresolvedIssues': issues or []},
        'agentProvenance': agent_provenance,
    }


def build_ledger(run_manifest: Path) -> dict:
    run_manifest = run_manifest.resolve(strict=True)
    run = json.loads(run_manifest.read_text(encoding='utf-8'))
    if run.get('schemaVersion') != 'offmenu-source-parse-run/1':
        raise ValueError('unsupported-source-run-manifest-schema')
    run_sha = sha256_file(run_manifest)
    entries = []
    for item in run.get('assets', []):
        source_id = item.get('sourceId')
        record_id = item.get('sourceRecordId')
        asset_id = f'{source_id}:{record_id}' if source_id and record_id else None
        manifest_value = item.get('manifestPath')
        asset_manifest = Path(manifest_value) if manifest_value else None
        if asset_manifest and not asset_manifest.is_absolute():
            asset_manifest = run_manifest.parent / asset_manifest
        evidence = [{'type': 'run-manifest', 'location': str(run_manifest),
                     'sha256': run_sha}]
        original_sha = item.get('inputSHA256')
        source_location = item.get('inputPath')
        output_artifacts = []
        parse_status = 'complete' if item.get('status') == 'complete' else 'failed'
        parse_validation = 'passed' if parse_status == 'complete' else 'failed'
        parse_issues = [] if parse_status == 'complete' else [item.get('errorCode') or 'parse did not complete']

        if asset_manifest and asset_manifest.is_file() and not asset_manifest.is_symlink():
            asset_manifest_sha = sha256_file(asset_manifest)
            evidence.append({'type': 'asset-parse-manifest', 'location': str(asset_manifest),
                             'sha256': asset_manifest_sha})
            manifest = json.loads(asset_manifest.read_text(encoding='utf-8'))
            if (manifest.get('status') != 'complete' or
                    manifest.get('inputSHA256') != original_sha or
                    manifest.get('identity', {}).get('parserVersion') != item.get('parserVersion')):
                parse_status, parse_validation = 'failed', 'failed'
                parse_issues.append('asset parse manifest does not agree with the run entry')
            for name, expected in manifest.get('artifacts', {}).items():
                artifact_path = asset_manifest.parent / name
                if artifact_path.is_symlink() or not artifact_path.is_file():
                    parse_status, parse_validation = 'failed', 'failed'
                    parse_issues.append(f'output artifact missing or not regular: {name}')
                    continue
                actual_sha = sha256_file(artifact_path)
                if actual_sha != expected.get('sha256') or artifact_path.stat().st_size != expected.get('bytes'):
                    parse_status, parse_validation = 'failed', 'failed'
                    parse_issues.append(f'output artifact checksum/size mismatch: {name}')
                output_artifacts.append({'location': str(artifact_path), 'sha256': actual_sha,
                                         'bytes': artifact_path.stat().st_size,
                                         'artifactName': name})
        elif parse_status == 'complete':
            parse_status, parse_validation = 'failed', 'failed'
            parse_issues.append('asset parse manifest unavailable for output verification')

        if item.get('parserVersion'):
            parser_id = item['parserVersion']
            engine = {'kind': 'script', 'identity': parser_id,
                      'scriptLocation': 'offmenu/refresh/source_faithful_parse.py',
                      'version': parser_id.rsplit('/', 1)[-1],
                      'runtimeVersion': 'unknown'}
            method = 'code'
        else:
            engine = {'kind': 'unknown', 'identity': 'unknown', 'version': 'unknown',
                      'runtimeVersion': 'unknown'}
            method = 'code' if parse_status != 'failed' else None

        parse_evidence = evidence + [
            {'type': 'output-artifact', 'location': output['location'],
             'sha256': output['sha256']} for output in output_artifacts]
        parse = _stage(status=parse_status, method=method, engine=engine,
            input_location=source_location, input_sha256=original_sha,
            outputs=output_artifacts, validation_status=parse_validation,
            validation_evidence=parse_evidence, issues=parse_issues)
        if parse_validation == 'passed' and output_artifacts:
            normalize_status, normalize_validation = 'not-run', 'not-run'
            normalize_issues = ['Normalization was not performed in the source-faithful parse run.']
        else:
            normalize_status, normalize_validation = 'blocked', 'not-run'
            normalize_issues = ['Parse output is not validated; normalization is blocked.']
        normalize = _stage(status=normalize_status, method=None,
            engine={'kind': 'not-run', 'identity': 'not-run', 'version': 'not-run'},
            input_location=output_artifacts[0]['location'] if output_artifacts else None,
            input_sha256=output_artifacts[0]['sha256'] if output_artifacts else None,
            validation_status=normalize_validation,
            validation_evidence=evidence,
            issues=normalize_issues)
        translate = _stage(status='not-run', method=None,
            engine={'kind': 'not-run', 'identity': 'not-run', 'version': 'not-run'},
            validation_status='not-run', validation_evidence=evidence,
            issues=['English translation was not performed; no normalized input exists.'])
        entries.append({
            'assetId': asset_id,
            'source': {'sourceId': source_id, 'sourceRecordId': record_id,
                       'kind': item.get('kind'), 'country': item.get('country'),
                       'location': source_location, 'inputSHA256': original_sha},
            'stages': {'parse': parse, 'normalize': normalize,
                       'englishTranslation': translate},
            'sourceReferences': evidence,
        })
    return {
        'schemaVersion': SCHEMA_VERSION,
        'generatedAt': datetime.now(timezone.utc).isoformat(),
        'sourceRunManifest': {'location': str(run_manifest), 'sha256': run_sha,
                              'schemaVersion': run.get('schemaVersion')},
        'processingStages': ['parse', 'normalize', 'englishTranslation'],
        'assetCount': len(entries),
        'assets': entries,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run-manifest', required=True, type=Path)
    ap.add_argument('--output', required=True, type=Path,
                    help='local ledger path; do not publish source locations outside the private workspace')
    args = ap.parse_args(argv)
    try:
        ledger = build_ledger(args.run_manifest)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        data = (json.dumps(ledger, ensure_ascii=False, sort_keys=True,
                           separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')
        if args.output.exists():
            raise ValueError('output-already-exists; choose a new versioned output path')
        args.output.write_bytes(data)
        print(json.dumps({'status': 'complete', 'assets': ledger['assetCount'],
                          'output': str(args.output),
                          'sha256': hashlib.sha256(data).hexdigest()}, sort_keys=True))
        return 0
    except Exception as exc:
        print(f'processing-provenance-build-failed: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
