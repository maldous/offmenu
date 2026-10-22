"""One generated DB-envelope comparison; no files/corpus/AI/database calls.

Run from manual-action: python benchmark_normalization_parallel.py --rows 1024
This is not a Foo throughput promise. Serial and parallel both evaluate the same
real run_rules implementation once per record, compute the full artifact hash,
and compact before encoding. Spawn/IPC/startup are included in parallel time.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import time

from normalization_api import Versions
from normalization_core import digest
from normalization_parallel import RulesExecutor, _compact, _encoded


def record(index):
    payload = {'id': 'generated-' + str(index), 'kind': 'recipe',
        'title': 'Generated benchmark beans ' + str(index), 'language': 'en',
        'ingredients': [{'id': 'generated-ingredient-' + str(i),
            'source_name_text': 'beans ' + str(i), 'quantity': str(25 + i), 'unit': 'g',
            'raw_text': str(25 + i) + ' g beans ' + str(i), 'ordinal': i} for i in range(4)],
        'steps': [{'id': 'generated-step-' + str(i), 'ordinal': i,
            'raw_text': 'Mix beans ' + str(i % 4) + ' in a bowl for 2 minutes.'} for i in range(6)]}
    return {'domain': 'recipes', 'source_key': 'generated-benchmark-only',
        'source_version': 'generated-v1', 'record_id': payload['id'],
        'content_sha256': digest(payload), 'payload': payload,
        'provenance': {'rights_status': 'unverified', 'fixture_only': True}}


def batches(rows, size):
    for start in range(0, rows, size):
        yield [record(index) for index in range(start, min(start + size, rows))]


def maximum_overlap(events):
    points = [(event['start_ns'], 1) for event in events]
    points += [(event['end_ns'], -1) for event in events]
    active = peak = 0
    for _, delta in sorted(points):
        active += delta
        peak = max(active, peak)
    return peak


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rows', type=int, default=1024)
    parser.add_argument('--workers', type=int, default=16)
    parser.add_argument('--batch-rows', type=int, default=128)
    args = parser.parse_args()
    if not 1 <= args.rows <= 4096 or not 1 <= args.batch_rows <= 128:
        parser.error('generated comparison capped at 4096 rows and 128 per batch')
    versions = Versions().as_dict()
    serial_hash = hashlib.sha256()
    start = time.monotonic()
    for batch in batches(args.rows, args.batch_rows):
        for item in batch:
            serial_hash.update(_encoded(_compact(_encoded(item), versions)))
    serial_s = time.monotonic() - start
    parallel_hash, events = hashlib.sha256(), []
    start = time.monotonic()
    with RulesExecutor(workers=args.workers, on_task_done=events.append) as executor:
        for batch in batches(args.rows, args.batch_rows):
            results = executor.run_batch(batch)
            if any(result['error_code'] is not None for result in results):
                raise RuntimeError('generated_benchmark_record_failed')
            for result in results:
                parallel_hash.update(_encoded(result))
        actual_workers = executor.actual_workers
        stats = executor.stats
    parallel_s = time.monotonic() - start
    worker_span = max(event['end_ns'] for event in events) - min(event['start_ns'] for event in events)
    result = {'scope': 'generated-public-DB-envelopes-only; not Foo or actual corpus',
        'rows': args.rows, 'batch_rows': args.batch_rows,
        'requested_workers': args.workers, 'actual_spawned_workers': actual_workers,
        'distinct_child_pids': len(stats.worker_pids), 'parent_pid_absent': os.getpid() not in stats.worker_pids,
        'maximum_overlapping_cpu_tasks': maximum_overlap(events),
        'worker_cpu_seconds_per_worker_span_second': round(stats.worker_cpu_ns / worker_span, 3),
        'serial_seconds': round(serial_s, 4), 'parallel_seconds_including_spawn_ipc': round(parallel_s, 4),
        'serial_rows_per_second': round(args.rows / serial_s, 1),
        'parallel_rows_per_second': round(args.rows / parallel_s, 1),
        'observed_speed_ratio': round(serial_s / parallel_s, 3),
        'ordered_output_identical': serial_hash.hexdigest() == parallel_hash.hexdigest(),
        'output_sha256': parallel_hash.hexdigest(),
        'peak_inflight_tasks': stats.peak_inflight_tasks,
        'input_limit_bytes': executor.max_input_bytes, 'output_limit_bytes': executor.max_output_bytes,
        'worker_restarts': stats.worker_restarts}
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result['ordered_output_identical']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
