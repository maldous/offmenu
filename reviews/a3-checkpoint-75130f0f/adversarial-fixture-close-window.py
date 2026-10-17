"""Adversarial fixture for the A3 checkpoint review (A3-1).

NEW scenario, not a re-execution of the author's 12 tests. It targets the one
window the existing suite does not cover with equality evidence:

  * CLI defaults packets_per_file=1, records_per_packet=1 (four packet files);
  * interruption raised immediately AFTER the atomic rename of a NON-FIRST file
    (part-00002), i.e. in the close -> save_cursor window, deeper into the run
    than the author's part-00000 case;
  * then resume, and require the retained orphan bytes to be reused unchanged
    and the final package to be byte-identical (and manifest-identical modulo
    createdAt) to an uninterrupted run.

Runs from a sandbox copy of the frozen bytes with the documented M1 layout
(scripts/ beside corpus/). Small synthetic fixtures only; no repair/fault/corpus
runs.
"""
import gzip
import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

FREEZE = Path(__file__).resolve().parent / 'freeze'
DEPS = FREEZE / 'deps'
CANON = Path('/home/user/src/offmenu')

failed = []


def check(name, condition, detail=''):
    status = 'PASS' if condition else 'FAIL'
    if not condition:
        failed.append(f'{name}: {detail}')
    print(f'  [{status}] {name}{(" -- " + detail) if detail else ""}')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sandbox(root):
    """Materialize the documented M1 layout from the frozen bytes."""
    (root / 'scripts').mkdir(parents=True)
    (root / 'corpus').mkdir(parents=True)
    for name in ['align-places-common.py', 'places_checkpoint.py']:
        source = DEPS / name if (DEPS / name).is_file() else FREEZE / name
        shutil.copyfile(source, root / 'scripts' / name)
    for name in ['common-data.schema.json', 'common-data-contract.json']:
        shutil.copyfile(CANON / 'corpus' / name, root / 'corpus' / name)
    spec = importlib.util.spec_from_file_location('places', root / 'scripts' / 'align-places-common.py')
    places = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(places)
    return places


def normalized(directory, source, record, kind, data):
    destination = directory / 'records' / source
    destination.mkdir(parents=True, exist_ok=True)
    row = {
        "schemaVersion": "1.0", "kind": kind, "id": f"{source}:{kind}:{record}", "countries": ["AU"],
        "provenance": {"sourceId": source, "recordId": record, "url": "https://example.org/record",
                       "license": "CC0 1.0", "licenseUrl": "https://example.org/license",
                       "attribution": "Example", "visibility": "public", "releaseId": "fixture",
                       "sourceDate": "2026-10-14"},
        "data": data,
    }
    with gzip.open(destination / '00.jsonl.gz', 'wt', encoding='utf-8') as handle:
        handle.write(json.dumps(["offmenu:fixture", [row]]) + "\n")


def fixture(places, root):
    curated = root / 'curated'
    for source, kind in [('overture-food-places', 'site'), ('wikidata-food-businesses', 'organization')]:
        normalized(curated, source, '1', kind, {'name': 'Fixture'})
        path = curated / 'records' / source / '00.jsonl.gz'
        row = json.loads(gzip.decompress(path.read_bytes()))
        second = json.loads(json.dumps(row))
        second[1][0]['provenance']['recordId'] = '2'
        second[1][0]['id'] += '2'
        path.write_bytes(gzip.compress(('\n'.join(json.dumps(x) for x in [row, second]) + '\n').encode(), mtime=0))
    files = [{'key': str(p.relative_to(curated)), 'bytes': p.stat().st_size, 'sha256': places.digest(p)}
             for p in sorted(curated.rglob('*.gz'))]
    (curated / 'manifest.json').write_text(json.dumps({
        'releaseId': 'fixture', 'files': files,
        'sources': {s: {'releaseId': 'fixture', 'records': 2, 'license': 'CC0', 'attribution': 'Fixture',
                        'rawSourcePayloadPublished': False}
                    for s in ['overture-food-places', 'wikidata-food-businesses']}}))
    return curated


def package_bytes(output):
    return {str(p.relative_to(output)): p.read_bytes() for p in sorted(output.rglob('*')) if p.is_file()}


def main():
    work = Path(tempfile.mkdtemp(prefix='a3adv-'))
    print(f'sandbox: {work}')
    places = sandbox(work)
    print(f'executed frozen align-places-common.py sha256 {sha(work / "scripts" / "align-places-common.py")}')
    print(f'executed frozen places_checkpoint.py  sha256 {sha(work / "scripts" / "places_checkpoint.py")}')

    source = fixture(places, work / 'run')
    out = work / 'run' / 'out'

    # 1. adversarial interruption: after the atomic rename of part-00002
    original = places.atomic_bytes

    def write_then_interrupt(path, raw):
        original(path, raw)
        if Path(path).name == 'part-00002.jsonl.gz':
            raise RuntimeError('adversarial interruption in close->commit window')

    try:
        import unittest.mock as mock
        with mock.patch.object(places, 'atomic_bytes', write_then_interrupt):
            try:
                places.align(source, out, records_per_packet=1, packets_per_file=1)
                check('interruption_raised', False, 'run completed without the injected interruption')
            except RuntimeError as error:
                check('interruption_raised', 'close->commit window' in str(error), str(error))
    except Exception as error:  # pragma: no cover
        check('interruption_setup', False, repr(error))

    partial = work / 'run' / 'out.partial'
    checkpoint_path = work / 'run' / 'out.checkpoint.sqlite'
    on_disk = sorted(p.name for p in (partial / 'packets').glob('*'))
    orphan = partial / 'packets' / 'part-00002.jsonl.gz'
    orphan_before = sha(orphan) if orphan.is_file() else None
    print(f'  observed after interruption: partial files={on_disk} orphan_sha256={orphan_before}')
    check('interruption_left_nonfirst_orphan', on_disk == ['part-00000.jsonl.gz', 'part-00001.jsonl.gz', 'part-00002.jsonl.gz'],
          f'{on_disk}')
    check('crash_left_lock_released', not (work / 'run' / 'out.alignment.lock').exists(),
          'lock still present after the in-process interruption')
    check('no_final_output', not out.exists(), 'output directory exists after interruption')

    # 2. resume in the same window
    resumed = places.align(source, out, records_per_packet=1, packets_per_file=1, resume=True)
    orphan_after = sha(out / 'packets' / 'part-00002.jsonl.gz') if (out / 'packets' / 'part-00002.jsonl.gz').is_file() else None
    check('orphan_bytes_reused_unchanged', orphan_before is not None and orphan_before == orphan_after,
          f'before={orphan_before} after={orphan_after}')

    # 3. controlled-clock reference run.
    #    createdAt is deliberately RETAINED across resume, and the manifest payload
    #    digest covers createdAt, so an uncontrolled reference run differs in exactly
    #    those derived bytes. Hold the clock to the resumed run's createdAt (the same
    #    technique the author's own suite uses) so the only variable left is resume.
    import unittest.mock as mock
    expected_root = work / 'reference' / 'out'
    reference_source = fixture(places, work / 'reference')
    with mock.patch.object(places.dt, 'datetime') as clock:
        clock.now.return_value.isoformat.return_value = resumed['createdAt']
        expected = places.align(reference_source, expected_root, records_per_packet=1, packets_per_file=1)

    actual_bytes = package_bytes(out)
    expected_bytes = package_bytes(expected_root)
    differing = sorted(set(actual_bytes) ^ set(expected_bytes)) or \
        sorted(k for k in actual_bytes if actual_bytes[k] != expected_bytes[k])
    check('resumed_package_byte_identical', not differing, f'differing keys: {differing}')
    check('resumed_resource_count', resumed['counts'] == expected['counts'],
          f"{resumed['counts']} vs {expected['counts']}")
    check('resumed_manifest_identical', resumed == expected,
          'manifest fields differ: ' + str([k for k in set(resumed) | set(expected)
                                            if resumed.get(k) != expected.get(k)]))

    # 4. observation (not a failure): the creator timestamp is retained across resume,
    #    and manifestPayloadSha256 covers it, so two otherwise-identical runs built
    #    under different clocks never share a payload digest or manifest bytes.
    uncontrolled_root = work / 'uncontrolled' / 'out'
    uncontrolled_source = fixture(places, work / 'uncontrolled')
    uncontrolled = places.align(uncontrolled_source, uncontrolled_root, records_per_packet=1, packets_per_file=1)
    obs_diff = sorted(k for k in package_bytes(uncontrolled_root)
                      if package_bytes(uncontrolled_root)[k] != actual_bytes.get(k))
    other = [k for k in set(uncontrolled) | set(resumed) if uncontrolled.get(k) != resumed.get(k)]
    print(f'  [observation] different-clock reference differs in package keys {obs_diff} and manifest fields {other};'
          f' checkpoint retention kept createdAt={resumed["createdAt"]!r}')
    check('checkpoint_sidecar_not_in_package',
          all('checkpoint' not in k and '.pending' not in k for k in actual_bytes),
          f'package keys: {sorted(actual_bytes)}')

    print(f'\nworkdir retained for inspection: {work}')
    print(f'RESULT: {"ALL CHECKS PASSED" if not failed else str(len(failed)) + " CHECK(S) FAILED"}')
    for item in failed:
        print(f'  - {item}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
