# Atomic reconciliation owner hook (R3 delta)

This narrow additive API change composes the reviewed R2 standalone helper with
an independently prepared bounded orchestration engine. It changes no runner,
source, cache, namespace policy, or reconciliation interpretation.

```python
def before_commit(db, batch_result):
    # Inside the helper's BEGIN IMMEDIATE, after all graph writes.
    # A copy of {'new', 'reused', 'gold_status', 'review_status'} is supplied.
    pages = db.execute('PRAGMA page_count').fetchone()[0]
    page_size = db.execute('PRAGMA page_size').fetchone()[0]
    free_pages = db.execute('PRAGMA freelist_count').fetchone()[0]
    # Owner checks cancellation, source snapshots, free reserve, actual logical
    # growth and/or occupied pages; raises to reject the entire transaction.
    # Owner writes its checkpoint, counters and quarantine with this connection.
    db.execute('INSERT INTO owner_checkpoint(cursor, processed) VALUES(?, ?)',
               (selected_cursor, next_processed_count))

result = ingest_cache_keys(state, domain, selected_keys, graph,
                           before_commit=before_commit)
# Also available directly: graph.ingest_artifacts(artifacts, before_commit=...)
```

The callback runs **exactly once** per admitted transaction, including an empty
artifact/key batch. If source/cache admission fails before a transaction begins,
the callback is not invoked. Any callback exception, including cancellation or
`KeyboardInterrupt`, rolls back graph facts, receipts, and owner checkpoint rows
together. The helper commits only after successful callback return.

The callback receives the same SQLite connection; use `execute`/`executemany`.
Transaction and savepoint control SQL are denied by a temporary SQLite authorizer,
including `commit()`, `ROLLBACK`, and `executescript()`'s implicit commit. The guard
is removed in `finally` before the helper commits or rolls back. This protects
against accidental inner transaction boundaries; callbacks are trusted owner code,
not a sandbox for untrusted scripts. They must not change the authorizer, close
the connection, or perform external side effects.

A rolled-back sample can inspect actual page growth after projection and raise a
private owner sentinel exception to discard it. A focused test verifies that the
logical page count and on-disk DB size return to the pre-sample values. Page count
alone measures logical file pages, not occupied pages or total filesystem usage;
consider freelist count and journal/WAL/reserve separately. The owner may also set
`PRAGMA max_page_count` before transactions as a hard logical-file growth limit.
No hypothetical whole-corpus capacity forecast is provided by this helper.

Evidence: the original **24** reconciliation tests plus **8** new hook tests pass.
The added tests cover commit/rollback of facts and checkpoint/quarantine together,
empty batches, adapter forwarding, actual rolled-back sample page growth, rejected
nested transaction controls, interrupt recovery, and invalid-hook refusal. All use
generated fixtures. R2 files and its frozen patch remain unchanged in their original
workspace. No live database, active runner, remote branch, or publication was touched.
