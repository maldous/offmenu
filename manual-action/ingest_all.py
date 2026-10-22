#!/usr/bin/env python3
"""Manual local entry point; ./run uses the same reviewed Python API."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from ingest_engine import run_ingest, run_default
from runner_paths import resolve_layout


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir',default=str(Path(__file__).parent/'.local-results'/'ingest'))
    parser.add_argument('--root',action='append',dest='roots')
    parser.add_argument('--catalog',help='Explicit private JSON catalog with sources list')
    parser.add_argument('--acquired-cache-root',help='Exact reviewed acquired cache root; read-only, no fetching')
    parser.add_argument('--acquired-manifest',help='Reviewed acquired source manifest')
    parser.add_argument('--workers',type=int,default=8)
    parser.add_argument('--batch-size',type=int,default=500)
    parser.add_argument('--max-batch-bytes',type=int,default=16*1024*1024)
    parser.add_argument('--max-record-bytes',type=int,default=4*1024*1024)
    parser.add_argument('--max-indexed-fields',type=int,default=128)
    parser.add_argument('--reserve-bytes',type=int,default=2*1024**3)
    parser.add_argument('--max-rows-per-source',type=int,default=0)
    parser.add_argument('--max-seconds',type=float,default=0)
    parser.add_argument('--report',dest='report_path')
    parser.add_argument('--report-interval',type=float,default=60)
    parser.add_argument('--max-files',type=int,default=250000)
    parser.add_argument('--max-depth',type=int,default=40)
    parser.add_argument('--max-scan-seconds',type=float,default=120)
    args=vars(parser.parse_args(argv))
    for name in ('acquired_cache_root', 'acquired_manifest'):
        if args.get(name) is None:
            args.pop(name, None)
    catalog=args.pop('catalog')
    state=str(resolve_layout(args.pop('state_dir')).ingest)
    if args.get('roots') is None:
        args.pop('roots',None)
    if catalog:
        with open(catalog,encoding='utf-8') as stream:
            value=json.load(stream)
        report=run_ingest(value['sources'] if isinstance(value,dict) else value,{'state_dir':state,**args})
    else:
        workers=args.pop('workers')
        report=run_default(state,workers=workers,options=args)
    print(json.dumps(report,sort_keys=True))
    return 0 if report['status']=='complete' else 2


if __name__=='__main__':
    raise SystemExit(main())
