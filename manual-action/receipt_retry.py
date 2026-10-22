"""Bounded, checkpoint-driven receipt transport recovery; never sleeps.

Only finite Git transport failures are retryable. Every delivery uses fresh
immutable receipt-branch evidence (including the first delivery after restart).
The four-retry budget is per invocation, not reset by an intervening success.
Local spools, rather than an unbounded in-memory queue, remain authoritative.
"""
from time import monotonic

MAX_BATCH_RECEIPTS = 512
MAX_BATCH_BYTES = 8 * 1024 * 1024
MAX_SCAN_ENTRIES = 4096
TRANSIENT = frozenset(('git_ls_remote_failed_local_work_preserved',
    'git_fetch_failed_local_work_preserved', 'git_push_failed_local_work_preserved',
    'git_timeout_local_work_preserved', 'receipt_branch_remote_changed_retry_preserved'))


class ReceiptRetry:
    def __init__(self, *, clock=None, announce=None, max_retries=4, base_delay=60, max_delay=600):
        if type(max_retries) is not int or not 0 <= max_retries <= 4:
            raise ValueError('invalid_receipt_retry_budget')
        if not 0 < base_delay <= max_delay <= 600:
            raise ValueError('invalid_receipt_retry_delay')
        self.clock = clock or monotonic
        self.announce = announce or (lambda message: None)
        self.max_retries, self.base_delay, self.max_delay = max_retries, base_delay, max_delay
        self.retries = self.failures = 0
        self.next_attempt = 0
        self.retry_pending = self.blocked = self.pending = False

    def attempt(self, operation):
        """Run at most one bounded batch; operation returns whether more remain."""
        self.pending = True
        if self.blocked or (self.retry_pending and
                (self.retries >= self.max_retries or self.clock() < self.next_attempt)):
            return False
        if self.retry_pending:
            self.retries += 1
        try:
            more = operation()
        except KeyboardInterrupt:
            raise  # Never classify user cancellation as a transport outage.
        except Exception as exc:
            reason = str(exc)
            self.retry_pending = reason in TRANSIENT
            self.blocked = not self.retry_pending
            if self.retry_pending:
                self.failures += 1
                delay = min(self.max_delay, self.base_delay * (2 ** min(self.failures-1, 4)))
                self.next_attempt = self.clock() + delay
                status = ('retry budget exhausted' if self.retries >= self.max_retries
                          else 'retry eligible at a later checkpoint')
            else:
                reason, status = 'receipt_delivery_refused_or_local_error', 'automatic retry stopped'
            self.announce('Receipt sync paused: '+reason+'; '+status+
                          '. Data processing continues; exact local checkpoints retained.')
            return False
        self.retry_pending = False
        self.failures = 0
        self.next_attempt = 0
        self.pending = bool(more)
        return True


def bounded_batch(directories, load, fail):
    """Read at most512 canonical envelopes /8MiB, without sorting a full spool.

    The loader enforces its own bounded JSON read and exact digest/name binding.
    One lookahead envelope is allowed for the byte boundary. Directory entries,
    including unexpected non-JSON entries, also have a finite scan bound.
    """
    import os
    batch, size, scanned = [], 0, 0
    for directory in directories:
        if not directory.exists():
            continue
        with os.scandir(directory) as entries:
            for entry in entries:
                scanned += 1
                if scanned > MAX_SCAN_ENTRIES:
                    raise fail('receipt_spool_entry_limit_preserved')
                if not entry.name.endswith('.json'):
                    continue
                if len(batch) >= MAX_BATCH_RECEIPTS:
                    return batch, True
                value, item_size = load(directory/entry.name)
                if item_size > MAX_BATCH_BYTES:
                    raise fail('receipt_spool_batch_bytes_limit_preserved')
                if batch and size + item_size > MAX_BATCH_BYTES:
                    return batch, True
                batch.append((value, directory/entry.name)); size += item_size
    return batch, False
