# Independent review receipt — manual action package

Review accepted 22 October 2026, 01:09 UTC. The publisher records the independent reviewer’s final release message; this is bounded source review evidence, not provider approval or data-load authority.

## Decision and validation

Accepted for **bounded manual diagnostics and supplier source-review preparation only**. No remaining review blocker was reported for this scope. The package does not import retained data, prove source bytes were received in cloud, or establish caller/load readiness.

- 20/20 generated-fixture tests passed after corrections.
- Six independent negative-probe groups passed, including malformed-deflate handling.
- Shell-wrapper syntax and CLI help passed.
- Final README timing correction was read and accepted: observation is bounded by a 30-second alarm; final output fsync occurs outside that alarm, and stalled kernel/mount operations can delay signal handling.
- Source-return instructions require successful inspection plus manual source-only review; heuristic acceptance is not proof of absence of every secret or disguised dataset.
- Optional workflow inspected: pinned checkout action, contents-read permission, persisted credentials disabled, branch/path-filtered generated fixtures only. It does not execute Foo paths and is not a delivery or per-run gate.

No live Foo session, actual supplier capsule, retained import, raw dataset or credential was used in this review. No live operation is claimed validated.

## Frozen publication inputs

Every source/package input below matches the reviewer’s accepted SHA-256. This receipt was added by the publisher to preserve that decision without changing accepted inputs.

| Path | SHA-256 |
| --- | --- |
| `manual-action/foo_manual.py` | `fbf1de50988aed555bc946b45f6c56a50318a868ee0af7ea257c934f4b3b3ee3` |
| `manual-action/tests/test_foo_manual.py` | `7562a764e9fc9f437a25e8aa02b2ad0d45d6b181f1832c1d474a40e8fd106557` |
| `manual-action/README.md` | `baebef22784fcec02b8c542b0f60bc4b6c0f8b6022ce4a3c08e9098593875880` |
| `manual-action/PROVENANCE.md` | `38278b434c6b69d5535995aafdd2acf5943d4f2fa7bd53650b16d6cbeae277b3` |
| `manual-action/run.sh` | `b9c842a5546a8e06dd6fdd4b73f533d69765f85435f8b46345e04c132dcc5317` |
| `manual-action/.gitignore` | `5bacfb5c80fa24833d5e7e946e1184559037ebbfa9bead8929192df08af65e6f` |
| `manual-action/returns/.gitkeep` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `.github/workflows/manual-action-fixtures.yml` | `98aeb7bd6041aa6f0d1d2621deeab45467c1f65141928f2de7349e7ec542a45e` |
