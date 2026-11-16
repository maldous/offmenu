"""Cooperative aggregate admission, not a cgroup or security boundary.

The supervisor owns a common lock while reading every reservation and committing
its durable marker. Limits are operating demand, never ceiling x job count.
"""
import os
from pathlib import Path

JOB_CEILING = 64
WORKER_CEILING = 256
OVERHEAD_CEILING = 8
GIB = 1024**3
CPU_RESERVE = 4
MEMORY_RESERVE = 8 * GIB
MEMORY_BUDGET = 54 * GIB
DISK_RESERVE = 70 * GIB
PROCESS_BUDGET = JOB_CEILING * (WORKER_CEILING + OVERHEAD_CEILING)


def overlap(a, b):
    a, b = Path(a), Path(b)
    return a == b or a in b.parents or b in a.parents


def validate_resources(value, mode, scope=Path('/offmenu')):
    fields = {'workers', 'overhead_processes', 'cpu_millis', 'memory_bytes',
              'output_bytes', 'read_roots', 'write_roots'}
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError('CapacityResourceSchema')
    limits = {'workers': (1, WORKER_CEILING),
              'overhead_processes': (1, OVERHEAD_CEILING),
              'cpu_millis': (1, 27000), 'memory_bytes': (1024**2, MEMORY_BUDGET),
              'output_bytes': (0, 64 * GIB)}
    for key, (low, high) in limits.items():
        if type(value[key]) is not int or not low <= value[key] <= high:
            raise ValueError('CapacityResourceRange')
    for key in ('read_roots', 'write_roots'):
        paths = value[key]
        if not isinstance(paths, list) or len(paths) > 32:
            raise ValueError('CapacityRootCount')
        for raw in paths:
            if not isinstance(raw, str) or len(raw) > 4096:
                raise ValueError('CapacityRootValue')
            path = Path(raw)
            if not path.is_absolute() or '..' in path.parts or str(path) != raw:
                raise ValueError('CapacityRootCanonical')
            if path != scope and scope not in path.parents:
                raise ValueError('CapacityRootScope')
            if any(p.is_symlink() for p in (path, *path.parents)):
                raise ValueError('CapacityRootSymlink')
        if len(set(paths)) != len(paths):
            raise ValueError('CapacityRootDuplicate')
    if mode == 'read' and value['write_roots']:
        raise ValueError('CapacityReadHasWrites')
    if mode == 'write' and not value['write_roots']:
        raise ValueError('CapacityWritesUndeclared')
    # A pooled writer must not modify the shared coordinator itself.
    control = scope / 'data/.offmenu-platform'
    protected = [control / name for name in ('locks', 'jobs', 'checkpoints')]
    protected += [scope / 'scripts/windmill']
    if any(overlap(p, q) for p in value['write_roots'] for q in protected):
        raise ValueError('CapacityCoordinatorWrite')
    return value


def requested_processes(value):
    return value['workers'] + value['overhead_processes']


def memory_available():
    with open('/proc/meminfo') as f:
        for line in f:
            if line.startswith('MemAvailable:'):
                return int(line.split()[1]) * 1024
    raise ValueError('CapacityMemoryUnavailable')


def free_bytes(root):
    fs = os.statvfs(root)
    return fs.f_bavail * fs.f_frsize


def decide(request, active, cpu_count, available_memory, available_disk):
    """Pure conservative decision; caller validates records under one lock.

    CPU demand is independent of worker count, so 256 I/O workers can request
    1000 millicores rather than 256 physical CPUs. RAM/disk checks subtract all
    outstanding declarations, even when current usage already appears in the
    observed free amount; this may queue work conservatively, never oversubscribe.
    """
    if len(active) >= JOB_CEILING:
        return 'capacity_slots_active'
    all_resources = [*active, request]
    if sum(x['cpu_millis'] for x in all_resources) > max(0, cpu_count - CPU_RESERVE) * 1000:
        return 'capacity_cpu_reserved'
    memory = sum(x['memory_bytes'] for x in all_resources)
    if memory > min(MEMORY_BUDGET, available_memory - MEMORY_RESERVE):
        return 'capacity_memory_reserved'
    if sum(requested_processes(x) for x in all_resources) > PROCESS_BUDGET:
        return 'capacity_processes_reserved'
    if sum(x['output_bytes'] for x in all_resources) + DISK_RESERVE + JOB_CEILING * 2 * 1024**2 > available_disk:
        return 'capacity_disk_reserved'
    for other in active:
        if (any(overlap(a, b) for a in request['write_roots'] for b in other['write_roots'] + other['read_roots'])
                or any(overlap(a, b) for a in request['read_roots'] for b in other['write_roots'])):
            return 'capacity_paths_conflict'
    return None
