"""OFF-LIVE candidate for soleUI/05; never an execution or selection receipt.

Use only after accepted source installation and independent output qualification.
Trusted startup configuration supplies both pins; HTTP JSON supplies neither.
No loader, network call, source scan, full-file hash or writable database open.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import re
import sqlite3
import stat


@dataclass(frozen=True)
class SelectedDatabase:
    path: Path
    identity: tuple  # selected device,inode,size,mtime_ns,ctime_ns
    digest: str  # independent qualified receipt, not calculated per request


def identity(s):
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


@contextmanager
def held_readonly(selected):
    if (type(selected) is not SelectedDatabase or not selected.path.is_absolute()
            or not re.fullmatch(r'[a-f0-9]{64}', selected.digest)
            or type(selected.identity) is not tuple or len(selected.identity) != 5):
        raise ValueError('trusted-database-selection-required')
    fd = os.open(selected.path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    db = None
    def check():
        held = os.fstat(fd)
        named = os.lstat(selected.path)
        if (not stat.S_ISREG(held.st_mode) or not stat.S_ISREG(named.st_mode)
                or identity(held) != selected.identity or identity(named) != selected.identity):
            raise ValueError('selected-database-custody-changed')
    try:
        check()
        db = sqlite3.connect(f'file:/proc/self/fd/{fd}?mode=ro&immutable=1', uri=True)
        yield db, check
        check()
    finally:
        if db is not None:
            db.set_progress_handler(None, 0)
            db.close()
        os.close(fd)


def selected_detail_page(observations, *, identifier_database, identifier_run_id,
                         detail_database, detail_selection, store_api):
    """All keyword context is native trusted configuration, never HTTP fields.

    observations are the already produced current indexed identifier page.
    store_api is the exact accepted pinned product_detail_store module.
    Return the reader envelope unchanged, including availability and variants.
    Caller keeps ordinary rows/cursor/generation and enforces the aggregate
    256KiB HTTP response bound; failures remain typed errors, never empty misses.
    """
    if (type(observations) is not list or len(observations) > 25
            or type(identifier_run_id) is not str or not identifier_run_id
            or type(detail_selection) is not store_api.ProductDetailQuerySelection
            or identifier_database.digest != detail_selection.identifier_database_sha256):
        raise ValueError('independent-generation-context-required')
    with held_readonly(identifier_database) as (identifier_db, check_identifier):
        with held_readonly(detail_database) as (detail_db, check_detail):
            result = store_api.read_product_details(
                detail_db, observations,
                selection=detail_selection,
                identifier_evidence=store_api.CurrentIdentifierEvidence(
                    identifier_db, identifier_run_id, identifier_database.digest),
                max_candidates=100, max_result_bytes=262144,
                max_steps=100000, max_seconds=5)
            check_identifier()
            check_detail()
            return result
