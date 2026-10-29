#!/usr/bin/env python3
"""Prepare the two narrow unavailable-state edits in preserved production209 assets.

Never deploys. Exact baseline hashes and unique preimages protect the composed
scanner, auth and API graph. Outputs are private candidates under .delivery/.
"""
import argparse
import hashlib
import json
from pathlib import Path

BASELINES = {
    'demo-full-scanner.js': 'a7391197f0e5330e69e6baf07cd6d426d9b8d81ee1303f014585ee0221c07e9f',
    'shelf-scanner.js': 'c7e221452704426efd4ffc9ee72203f62a3be0ae457c8275d42d6ee72e95e185',
}
PREIMAGES = {
    'demo-full-scanner.js': [
        ('category.preferredLabel : "Not yet identified"', 'category.preferredLabel : latest?.status === "unavailable" ? "Lookup unavailable" : "Not yet identified"'),
        ('"Not applicable" : "Not yet identified"', '"Not applicable" : latest?.status === "unavailable" ? "Lookup unavailable" : "Not yet identified"'),
    ],
    'shelf-scanner.js': [
        ('t.preferredLabel:"Not yet identified",n=', 't.preferredLabel:e?.status==="unavailable"?"Lookup unavailable":"Not yet identified",n='),
        ('"Not applicable":"Not yet identified",a=', '"Not applicable":e?.status==="unavailable"?"Lookup unavailable":"Not yet identified",a='),
    ],
}


def sha(value):
    return hashlib.sha256(value).hexdigest()


def patch(name, source):
    if sha(source) != BASELINES[name]:
        raise ValueError(f'{name}: production209 baseline mismatch')
    text = source.decode('utf-8')
    for old, new in PREIMAGES[name]:
        if text.count(old) != 1:
            raise ValueError(f'{name}: exact single preimage required')
        text = text.replace(old, new, 1)
    return text.encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--public-input', type=Path, required=True)
    parser.add_argument('--private-input', type=Path, required=True)
    parser.add_argument('--output-directory', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / '.delivery'
    directory = args.output_directory.resolve()
    if not directory.is_relative_to(root.resolve()) or directory == root.resolve():
        parser.error('Select a private output directory inside this checkout .delivery/')
    candidates = {}
    for name, path in [('demo-full-scanner.js', args.public_input), ('shelf-scanner.js', args.private_input)]:
        candidates[name] = patch(name, path.read_bytes())
    if directory.exists():
        parser.error('Output directory already exists; reconcile retained candidates before retrying')
    directory.mkdir(parents=True, mode=0o700)
    receipt = {'scope': 'production209 unavailable labels only; no deployment', 'assets': {}}
    for name, content in candidates.items():
        (directory / name).write_bytes(content)
        receipt['assets'][name] = {'baseline_sha256': BASELINES[name], 'candidate_sha256': sha(content), 'edits': 2}
    (directory / 'manifest.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
