# Direct metadata synchronization — no GitHub Actions

This package replaces the failed capped metadata inventory and the Actions
transport for this recovery. Use the normal owner's existing `gh` login; no new
credentials, `sudo`, runner staging, workflow dispatch or local AI worker is used.

The exact helper SHA256 is
`758b56d4f57f17ab429ceed78048e1c94614e778623e7eeaf5ef61b2b933f63a`.
Download both `scripts/export-local-source.py` and
`scripts/direct_publish_metadata.py` from the same immutable custody commit and
verify the published SHA256s before running either. Use a new private temporary
directory; keep the earlier failed directory untouched.

Run `export-local-source.py inventory --job-prefix
foo-source-inventory-direct-20261027 --include-pinned-anchor-docs
--output-directory NEW_PACKET_DIRECTORY`, then run the direct publisher with
`--helper`, `--helper-sha256` and `--packet-directory`. The final user handoff pins
the immutable commit, both hashes and the exact commands.

The uploader validates the complete packet set, preserves exact packet bytes and
provenance, and uploads only eligible checkout metadata plus the three already
path/hash-pinned evidence JSON documents. It rejects arbitrary selected source
payloads. This does not publish the application code referenced by those documents.
Unhashed, excluded, missing or unreadable files remain explicit; the inventory
includes Python/JavaScript/TypeScript corpus modules as metadata, but not
corpus dataset/text/JSON bodies or recursive external runtime trees. Do not call
excluded or uninspected paths recovered.

It writes only under
`dev/reviewed-local-source-custody-20261027/direct-metadata/PACKET_SET_SHA256/`
on the existing `integration/reviewed-local-source-custody-20261027` branch. It
checks the exact workflow blob pins before any remote write: the retained general
workflow is dispatch-only, and the Foo workflow's push trigger is restricted to
the separate runner-control branch and request path. Neither workflow is changed.
Installed repository checks such as GitGuardian may still inspect the commit;
they are not an Actions service-processing job.

The metadata commit has exactly one parent: the current custody branch tip. The
publisher rechecks that tip and uses `force:false`; competing work stops the
update rather than overwriting it. Repeating an already preserved, byte-identical
packet set reports its existing location; conflicting content is never replaced.
An uncertain ref update is read back, never blindly retried. Local working files,
Git index, branches and history are not modified. Main, develop, runtime and live
README remain untouched.

After the command returns the actual immutable commit and packet-set hash, the
same cloud preservation lane reads the packets directly from GitHub, verifies
them and selects the outstanding reviewed source. Metadata transport is not a
claim that all15/preload, cover, localhost alias, own-data or client13 source has
already been recovered or adopted.

Validation is focused and synthetic: the helper owner verified 45 cases including
50,001 eligible entries, full streamed custody and mutation checks; the direct
publisher has six mock-network/real-validator tests. Test source is retained with
`.source.txt` suffixes to prevent accidental discovery. Restore those suffixes
only in an isolated test copy, preserving the `scripts/` and `tests/` layout.
