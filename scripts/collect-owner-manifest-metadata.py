#!/usr/bin/env python3
"""Read only sixteen owner-readable manifests and print a sanitized custody receipt.
No administrator, service, mount, permission, network or publication operations.
"""
import argparse
from datetime import datetime, timezone
import errno
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import stat
import sys
from urllib.parse import urlsplit

ROOT = Path('/home/user/src/offmenu-data')
CANDIDATES = (
 'off-2026-10-12-lf', 'usda-2026-04', 'prices-2026-10-12', 'afcd-3',
 'cofid-2021', 'germany-bls-4.0', 'frida-5.5',
 'wikidata-businesses-20261013-native', 'dietary-guidelines-20261013',
 'wikibooks-2026-10-13-live', 'cnf-2015', 'mext-2023-main',
 'overture-food-places-2026-09-23.1', 'fineli-20.0',
 'foodfiles-2024-v01', 'sweden-food-2026-07-01',
)
REUSED = ('metadata/no-prior-manifest.json', 'metadata/fr-prior-manifest.json')
CAP = 64 * 1024
TOTAL = 2 * 1024 * 1024

class Blocked(Exception):
    pass

def reject(code):
    raise Blocked(code)

def strict_json(body):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out: reject('duplicate-json-key')
            out[key] = value
        return out
    try:
        return json.loads(body, object_pairs_hook=pairs,
                          parse_constant=lambda _: reject('nonfinite-json'))
    except (ValueError, UnicodeError, RecursionError):
        reject('invalid-json')

def signature(s):
    return (s.st_dev, s.st_ino, s.st_mode, s.st_uid, s.st_gid,
            s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns)

def no_acl(fd):
    try:
        os.getxattr(fd, 'system.posix_acl_access')
    except OSError as exc:
        if exc.errno in (errno.ENODATA, errno.ENOTSUP): return
        reject('unverified-acl')
    reject('acl-requires-review')

def read_source(path, owner):
    """Descriptor-anchored, bounded read; never follows even parent symlinks."""
    parent = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    fd = None
    identities = {0: 0, owner.pw_uid: owner.pw_gid}
    try:
        for part in path.parts[1:-1]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent)
            parent = nxt
            s = os.fstat(parent)
            if s.st_uid not in identities or s.st_gid != identities[s.st_uid] or s.st_mode & 0o002:
                reject('unsafe-parent')
            bit = stat.S_IXUSR if s.st_uid == owner.pw_uid else stat.S_IXGRP if s.st_gid == owner.pw_gid else stat.S_IXOTH
            if not s.st_mode & bit: reject('owner-traverse-denied')
            no_acl(parent)
        before = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
            or before.st_uid not in identities or before.st_gid != identities[before.st_uid]
            or before.st_mode & 0o113): reject('unsafe-file')
        # No root-only source access: the owner must be able to read the leaf.
        bit = stat.S_IRUSR if before.st_uid == owner.pw_uid else stat.S_IRGRP if before.st_gid == owner.pw_gid else stat.S_IROTH
        if not before.st_mode & bit: reject('owner-read-denied')
        if before.st_size > CAP: reject('oversized')
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        no_acl(fd)
        if signature(os.fstat(fd)) != signature(before): reject('source-changed')
        chunks = []; size = 0
        while size <= CAP:
            chunk = os.read(fd, min(8192, CAP + 1 - size))
            if not chunk: break
            chunks.append(chunk); size += len(chunk)
        if size != before.st_size or signature(os.fstat(fd)) != signature(before): reject('source-changed')
        return b''.join(chunks)
    finally:
        if fd is not None: os.close(fd)
        os.close(parent)

# Never copy arbitrary strings, URLs, nested manifests, file names, headers,
# commands, environment values, or rows. Origin-only URLs deliberately discard
# userinfo, path, query and fragment; full historical URLs remain owner-private.
def public_origin(value):
    if not isinstance(value, str) or len(value) > 2048: return None
    try:
        u = urlsplit(value)
        host = u.hostname
        if (u.scheme != 'https' or u.username or u.password or u.port not in (None, 443)
            or not host or not re.fullmatch(r'[a-zA-Z0-9.-]+', host)
            or '.' not in host or host.endswith(('.local', '.internal', '.localhost'))
            or re.fullmatch(r'[0-9.]+', host)): return None
        approved = ('openfoodfacts.org', 'usda.gov', 'foodstandards.gov.au', 'gov.uk',
                    'blsdb.de', 'frida.fooddata.dk', 'wikidata.org', 'wikibooks.org',
                    'canada.ca', 'mext.go.jp', 'overturemaps.org', 'fineli.fi',
                    'foodcomposition.co.nz', 'livsmedelsverket.se')
        host = host.lower()
        for domain in approved:
            if host == domain or host.endswith('.' + domain): return 'https://' + domain
        return None
    except ValueError: return None

def sanitize(body, candidate):
    raw = strict_json(body)
    if not isinstance(raw, dict): reject('manifest-not-object')
    download = {}
    # Only top-level known metadata; never recursively traverse data arrays.
    for key in ('sha256', 'download_sha256', 'source_sha256'):
        value = raw.get(key)
        if isinstance(value, str) and re.fullmatch(r'[0-9a-fA-F]{64}', value): download[key] = value.lower()
    for key in ('bytes', 'size_bytes', 'download_bytes'):
        value = raw.get(key)
        if type(value) is int and 0 <= value <= 2**63 - 1: download[key] = value
    for key in ('downloaded_at', 'retrieved_at', 'fetched_at'):
        value = raw.get(key)
        if isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2}))?', value): download[key] = value
    provenance = {}
    for key in ('url', 'source_url', 'download_url', 'homepage'):
        value = public_origin(raw.get(key))
        if value: provenance[key + '_origin'] = value
    licenses = {'CC0-1.0', 'CC-BY-4.0', 'CC-BY-SA-4.0', 'ODbL-1.0', 'OGL-UK-3.0', 'PDDL-1.0'}
    if isinstance(raw.get('license'), str) and raw['license'] in licenses: provenance['license'] = raw['license']
    return {'schemaVersion': 'offmenu-manifest-metadata/2', 'candidate': candidate,
            'manifestSha256': hashlib.sha256(body).hexdigest(), 'manifestBytes': len(body),
            'originalDownloadMetadata': download, 'provenance': provenance,
            'provenanceVerified': False}

def collect(owner):
    outputs = {}; statuses = {}; total = 0
    for candidate in CANDIDATES:
        try:
            body = read_source(ROOT / candidate / 'manifest.json', owner)
            total += len(body)
            if total > TOTAL: reject('aggregate-limit')
            clean = sanitize(body, candidate)
            outputs[candidate + '.json'] = (json.dumps(clean, sort_keys=True, separators=(',', ':')) + '\n').encode()
            statuses[candidate] = 'sanitized'
        except FileNotFoundError: statuses[candidate] = 'missing'
        except Blocked as exc: statuses[candidate] = str(exc)
        except OSError: statuses[candidate] = 'unsafe-or-unreadable'
    return outputs, statuses, total

def run():
    report = {'schemaVersion': 'offmenu-owner-manifest-metadata/1',
              'status': 'blocked', 'sourcePermissionsChanged': False,
              'runnerAccessChanged': False, 'rawRowsCopied': False,
              'networkUsed': False, 'published': False,
              'reusedExistingViewReferences': list(REUSED),
              'existingViewReferencesRead': False,
              'capturedAt': datetime.now(timezone.utc).isoformat()}
    try:
        owner = pwd.getpwnam('user')
        if os.getuid() != owner.pw_uid or os.geteuid() != owner.pw_uid or owner.pw_uid == 0:
            reject('normal-owner-identity-required')
        if not sys.flags.isolated: reject('isolated-python-required')
        outputs, statuses, total = collect(owner)
        report.update(candidates=statuses, sourceBytesRead=total, selectedCount=len(outputs),
                      metadata={name: strict_json(body) for name, body in outputs.items()},
                      sanitizedSha256={name: hashlib.sha256(body).hexdigest() for name, body in outputs.items()})
        report['status'] = 'collected' if outputs else 'no-safe-manifest'
    except (Exception, KeyboardInterrupt) as exc:
        report['errorCode'] = str(exc) if isinstance(exc, Blocked) else 'owner-collection-failed'
    canonical = json.dumps(report, sort_keys=True, separators=(',', ':')).encode()
    if len(canonical) > 64 * 1024 - 128:
        report = {'schemaVersion':'offmenu-owner-manifest-metadata/1', 'status':'blocked', 'errorCode':'receipt-limit'}
        canonical = json.dumps(report, sort_keys=True, separators=(',', ':')).encode()
    report['receiptSha256'] = hashlib.sha256(canonical).hexdigest()
    return report

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()  # No arbitrary paths, commands, destinations or source IDs.
    report = run()
    print(json.dumps(report, sort_keys=True, separators=(',', ':')))
    return 0 if report['status'] == 'collected' else 2

if __name__ == '__main__': sys.exit(main())
