# Normal-owner manifest metadata receipt

## Scope and status

This replaces the proposed temporary v2 runner view. It requires no administrator access, service/mount/permission changes, sudo, new login, new credentials, or Actions run. Preparation and unit tests do not establish that it has run on Foo.

The normal-owner collector reads only `manifest.json` under the following sixteen exact directories in `/home/user/src/offmenu-data`:

`off-2026-10-12-lf`, `usda-2026-04`, `prices-2026-10-12`, `afcd-3`, `cofid-2021`, `germany-bls-4.0`, `frida-5.5`, `wikidata-businesses-20261013-native`, `dietary-guidelines-20261013`, `wikibooks-2026-10-13-live`, `cnf-2015`, `mext-2023-main`, `overture-food-places-2026-09-23.1`, `fineli-20.0`, `foodfiles-2024-v01`, `sweden-food-2026-07-01`.

There is no directory walk, raw payload read, or guessed path. Existing Norway/France v1 metadata references are listed as reused references only and are **not read or recopied** by this command. No claim is made about the four unresolved source paths.

## Safety and meaning of evidence

The collector requires uid/euid equal to the non-root `user` account and isolated Python. It rejects symlinks (including ancestors), hardlinked leaves, unknown ownership/group, world-write, executable files, ACL-bearing paths, owner-inaccessible paths, and manifests above 64 KiB. Reads are descriptor anchored and checked for concurrent change. The total source budget is 2 MiB; sixteen per-file caps imply at most 1 MiB in the normal fixed scope. Each candidate has its own sanitized result/error code.

Repository collector fields `archiveSha256` and `completedAt` are preserved in `collectionMetadata` with strict hash and timestamp validation. The archive value can represent a source archive or a collector bundle digest. Completion time describes normalization completion, never original acquisition time or freshness. Nested sourceFiles and partitions remain excluded.

The receipt includes sampled `manifestSha256`, `manifestBytes`, strictly typed source-claimed checksum/size/date fields, fixed approved public origins, and known license identifiers. URL userinfo, paths, queries, fragments, unknown domains, arbitrary text, nested records and row arrays are never copied. Field names that are not explicitly supported are omitted. `capturedAt` is collector time, never an inferred download date. `provenanceVerified` remains false. Manifest existence does not prove raw-file availability, native delivery, acquisition truth, licensing or runner acceptance.

The collector's final serialized receipt fits within 64 KiB, including its canonical `receiptSha256`. The canonical digest covers the sorted compact JSON before the digest field is appended. Each sanitized per-file digest covers its sorted compact JSON plus a newline. These are integrity/custody aids, not signatures or source authenticity guarantees.

## One owner command and receipt delivery

The delivery wrapper verifies the collector's compiled-in SHA-256, runs it in the same normal-owner process, and preserves a private local receipt directory (`0700`, files `0600`). It discovers the existing root-owned `gh` executable at `/usr/local/bin/gh`, falling back to `/usr/bin/gh`. It uses only existing environment token or gh stored authentication and does not print or save credential values. Raw gh stdout/stderr are not persisted; command exit codes, timeout/overflow state and numeric errno are retained.

Before publication, it verifies authenticated GitHub identity `maldous` / ID `6347545` and the private repository identity `maldous/offmenu`. The fixed approved destination is one comment on PR #30: https://github.com/maldous/offmenu/pull/30. No alternate destination, arbitrary path or arbitrary command arguments are supported.

Each wrapper run has a unique report ID. It makes at most **one** publication attempt. A timeout, overflow, failure, or unverified response is `uncertain-no-retry`; check PR #30 for the report ID before any further attempt. The posted body describes publication as `attempting-once`, since the outcome does not exist until after submission. The final local `receipt.json` and terminal summary report `posted`, `not-attempted`, or `uncertain-no-retry`, with a verified comment URL when available. `collection.json` remains available if GitHub access fails. Local receipt persistence is best-effort if disk/filesystem errors occur.

The comment is explicitly an **owner metadata receipt**, not a Foo Actions completion signal. This command does not write PR31/results/control, start a workflow, or fabricate a run ID. A report with all missing or rejected candidates can still be published as useful evidence; inspect `collection.status` and every candidate status.

## Pinned fetch/run handoff

The integrator must substitute the final reviewed full commit and both artifact SHA-256 values into the command below after verifying the remote bytes. Do not give the owner a floating branch fetch or an unresolved placeholder. The command uses the existing gh authentication to fetch only the two reviewed scripts, then verifies both hashes before execution. It requires no repository checkout and never executes downloaded bytes before verification.

```bash
set -eu
GH=/usr/local/bin/gh
[ -x "$GH" ] || GH=/usr/bin/gh
[ -x "$GH" ] || { printf '%s\n' 'Existing gh CLI is unavailable.'; exit 2; }
COMMIT=REVIEWED_FULL_COMMIT
WRAPPER_SHA=REVIEWED_WRAPPER_SHA256
COLLECTOR_SHA=REVIEWED_COLLECTOR_SHA256
WORK=$(mktemp -d /tmp/offmenu-owner-metadata-code.XXXXXX)
chmod 700 "$WORK"
for NAME in run-owner-manifest-metadata.py collect-owner-manifest-metadata.py; do
  if "$GH" api --hostname github.com "repos/maldous/offmenu/contents/scripts/$NAME?ref=$COMMIT" --jq .content > "$WORK/$NAME.b64"; then
    printf 'Fetch %s exit=0\n' "$NAME"
  else
    CODE=$?; printf 'Fetch %s exit=%s\n' "$NAME" "$CODE"; exit "$CODE"
  fi
  base64 --decode "$WORK/$NAME.b64" > "$WORK/$NAME"
  chmod 600 "$WORK/$NAME"
done
printf '%s  %s\n%s  %s\n' "$WRAPPER_SHA" "$WORK/run-owner-manifest-metadata.py" "$COLLECTOR_SHA" "$WORK/collect-owner-manifest-metadata.py" | sha256sum --check
/usr/bin/python3 -I "$WORK/run-owner-manifest-metadata.py" --commit "$COMMIT"
```

The `--commit` field records the reviewed commit selected by this pinned fetch command; the wrapper is not independently authenticating remote commit membership. Integrity comes from the integrator-provided reviewed artifact hashes and the wrapper's collector pin. The code/receipt directories are retained locally for custody. No administrator step or secret input is part of this command.

## Tests and remaining execution gate

Focused tests cover exact scope, malformed/duplicate JSON, bounded extraction, source symlink/oversize/owner rejection, non-root identity, receipt hashes and size, pinned dependency loading, exact publication destination, private receipt modes, owner/repository mismatch, missing gh, uncertain one-attempt publication, and real bounded subprocess timeout/output fixtures. GitHub calls are mocked in tests; no source read or publication on Foo occurs during testing.

Remaining work: independent review, integration with final commit/hash verification, and an actual normal-owner run through the supported execution route. A successful receipt closes only this metadata evidence request; downstream native/source-specific acceptance remains separate.
