"""One bounded private-index read; no listener, credentials, source acquisition or writes."""
import importlib.util
import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        raise ValueError('exact barcode argument required')
    spec = importlib.util.spec_from_file_location('prepared_lookup', Path(__file__).with_name('lookup.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    barcode = module.exact_barcode(sys.argv[1])
    reader = module.Lookup()
    try:
        result = reader.lookup(barcode)
    finally:
        reader.close()
    output = json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n'
    if len(output.encode()) > 65536:
        raise ValueError('bounded response exceeded')
    sys.stdout.write(output)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Never log source bodies, principals, credentials or exception contents.
        sys.stderr.write('PRIVATE_LOOKUP_READ_FAILED\n')
        sys.exit(2)
