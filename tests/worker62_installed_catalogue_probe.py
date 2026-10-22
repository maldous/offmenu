"""Run with python -I against one installed wheel/sdist target, outside the repo.

No source or metadata reader may execute. The default catalogue is exercised
without a configuration override; only the actual metadata boundary is stubbed.
"""
import argparse
import copy
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--installed-root', type=Path, required=True)
    parser.add_argument('--catalogue-sha256', required=True)
    args = parser.parse_args()
    installed = args.installed_root.resolve()
    sys.path.insert(0, str(installed))
    from offmenu import portfolio_worker62 as w
    from offmenu import portfolio_worker62_catalogue as catalogue
    from offmenu.refresh.core import canonical, sha
    assert Path(w.__file__).resolve().is_relative_to(installed)
    assert Path(catalogue.__file__).resolve().is_relative_to(installed)
    assert not (installed / 'docs/portfolios/worker62-inputs.json').exists()
    observed = []
    def no_actual_metadata(config):
        observed.append(copy.deepcopy(config))
        assert sha(canonical(config)) == args.catalogue_sha256
        return {}
    with tempfile.TemporaryDirectory(prefix='worker62-installed-output-') as directory:
        output = Path(directory) / 'output'
        with patch.object(w, 'load_metadata', side_effect=no_actual_metadata), \
                patch.object(w, '_read_regular', side_effect=AssertionError('actual metadata reader forbidden')), \
                patch.object(Path, 'read_bytes', side_effect=AssertionError('resource read forbidden')), \
                patch.object(Path, 'read_text', side_effect=AssertionError('resource read forbidden')), \
                patch('builtins.print'):
            assert w.main(['--now', '2026-10-18T00:00:00Z', '--output', str(output)]) == 0
        assert len(observed) == 1
        report = json.loads((output / 'metadata-report.json').read_bytes())
        assert report['metadataRecords'] == 0 and report['bodyOperations'] == 0
        assert len(report['outcomes']) == 10
        assert all(row['status'] == 'missing' and row['holds'] for row in report['outcomes'])
        print(json.dumps({'installedModule': str(Path(w.__file__).resolve()),
            'catalogueSha256': args.catalogue_sha256, 'defaultLoader': 'inert-literal-deepcopy',
            'mirrorRequired': False, 'metadataReadersInvoked': 0, 'bodyOperations': 0,
            'outcomes': 10, 'status': 'PASS'}, sort_keys=True))


if __name__ == '__main__':
    main()
