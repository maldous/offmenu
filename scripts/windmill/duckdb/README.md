# OffMenu pinned offline DuckDB runtime

## Scope and provenance

- DuckDB **1.5.6**, official CPython 3.12 Linux x86_64 wheel, MIT.
- Pin is deliberate and versioned; this does **not** claim 1.5.6 is the newest
  release. Avoid an unreviewed major-version upgrade during platform setup.
- Exact URL, SHA-256, upload date, byte length, license and dependency closure are
  in `lock.json`; no optional extras are selected. No pandas or PyArrow needed.
- Official metadata: <https://pypi.org/pypi/duckdb/1.5.6/json>.
- Package provenance: <https://pypi.org/project/duckdb/1.5.6/>. PyPI reports trusted
  publishing; independent Sigstore verification is not claimed.
- Metadata/wheel inspection: <https://windmill.aldous.info/run/01a17f71-7b7c-3234-ee25-895948805679?workspace=offmenu>.
- Exact installer validator tested against downloaded official wheel:
  <https://windmill.aldous.info/run/01a17f76-236c-2047-0edd-def9933ac2c7?workspace=offmenu>.
- Host preflight (solewriter): CPython 3.12.3, Linux x86_64, glibc 2.39;
  `venv`, `ensurepip` and `pip` discoverable.

## Actual Foo installation verification (2026-10-27)

**Installed and verified** under the sole Foo writer. Full machine-readable
result: `DEPLOYMENT-RECEIPT.json`; host receipt:
`/offmenu/data/.offmenu-platform/duckdb/1.5.6-bc9619ed7d4f/INSTALL-RECEIPT.json`.

- Final successful verification: <https://windmill.aldous.info/run/01a17f82-0543-9ded-f91c-7865478047a3?workspace=offmenu>.
- All 53 original installed wheel files rehashed against the pinned official
  wheel (excluding RECORD, which pip legitimately rewrites).
- Actual native import, 10,000-row Parquet write/readback and eight grouped
  results succeeded; ID sum 49,995,000; Parquet size 20,945 bytes.
- Actual effective settings: 4 threads, 8.0 GiB buffer, 20.0 GiB spill;
  external access, extension autoload and autoinstall disabled; config locked.
- One tiny verification trial: startup 0.036951 s, generation 0.001091 s,
  Parquet write 0.001515 s, readback 0.001410 s, group-by 0.001178 s,
  total 0.042967 s, peak RSS 68,184 KiB. These figures do not establish
  production throughput, a speedup or an optimum.
- Host-bundled pip 24.0 installed the package offline; no dependency extras.
- Transfer of the 21,568,087-byte wheel took 42.432 s in the observed run.

Actual API verification found that `allowed_directories` cannot be configured
in the initial connection map. The runtime was corrected in place, without
reinstalling the package or weakening final restrictions: parameterized
`SET allowed_directories = ?` after connection creation, then disable external
access, then lock configuration, all before any workload or returning the
connection. The current exact runtime SHA-256 is
`a894d076d7adc6d349a229d417094f7fc7a5b08aab43f83049ed1e7f3662abd0`.
The corrected final source is also embedded in the private worker draft.

The two failed pre-receipt attempts were configuration-only; no installation
success was claimed and no receipt existed until real verification passed.
`finalize_existing.py` preserves the bounded recovery procedure and refuses to
overwrite an existing receipt. Routine future checks should run `--smoke`, not
rerun the finalizer. Local synthetic/adversarial suite: **27 tests pass**.

### Independent deployed-runner and boundary verification

A second real run via the deployed runner passed with the same 10,000 rows,
Parquet hash and grouped-result hash. Elapsed 0.046102 s; peak RSS 68,124 KiB.
This is another correctness check, not a production throughput measurement.

- Runner: <https://windmill.aldous.info/run/01a17f82-b7fd-6156-a6ca-1d3ca87dc70f?workspace=offmenu>.
- Captured output/boundary checks: <https://windmill.aldous.info/run/01a17f82-cdbe-04f2-81fd-cbca01e71472?workspace=offmenu>.
- An actual attempt to read a synthetic CSV outside the configured allowlist was
  denied. An actual attempt to change `threads` after configuration lock was
  denied. No corpus or production dataset was used for these checks.
- Observed allowed directories were exactly the synthetic parent and its spill
  directory; community/unsigned extensions and external access were disabled,
  and configuration was locked.
- Full parsed evidence: `INDEPENDENT-VERIFICATION.json`.

## Installation design

The private Windmill worker downloads **only the official pinned package code**,
checks current versioned metadata, whole-wheel SHA-256 and all wheel RECORD
entries, then transfers 40 KiB chunks through the existing pinned-key
`offmenu-exec-v1` SSH channel. No private key is accepted in arguments, included in
source, logged or returned. No corpus/raw data leaves Foo.

Every SSH request is one JSON object under the existing 65,536-byte cap. The
largest generated chunk request is about 56 KiB. Transfer is sequential over one
authenticated transport, offset-checked and retry-safe. Registry I/O happens on
the existing networked worker; jail network restrictions are unchanged.

`prepare` refuses a non-ignored destination, symlink ancestors, non-private or
foreign-owned roots, and existing staging paths. Each stage is exclusive and
random. Wheel chunks cannot follow symlinks or write multiply-linked files.
The final whole-wheel digest is rechecked on Foo. The strict archive validator
rejects traversal, links/special files, startup hooks, duplicates, unexpected
dependencies and incorrect RECORD coverage/hashes before installation.

Installation is standard `venv` with host-bundled `ensurepip`, followed by pip
with `--isolated --no-index --no-deps --no-cache-dir --no-compile --require-hashes
--only-binary=:all:` and a local `--find-links` directory. No source builds,
network bootstrap, global Python modification or optional dependencies.

Venvs are not relocatable: installation goes directly into the exclusive path
`/offmenu/data/.offmenu-platform/duckdb/1.5.6-bc9619ed7d4f`. An existing path is
never overwritten. `INSTALL-RECEIPT.json` appears only after the synthetic test
passes. Failure leaves an isolated incomplete installation for diagnosis; there
is no global/current pointer to accidentally select it. Removal/retry is done
only by the sole Foo writer after inspecting that specific failure.

## Solewriter execution

Private draft: `u/admin/duckdb_offline_install_20261027`.

1. `action=verify_registry`: no Foo connection, read-only registry verification.
2. `action=prepare`: returns a random `stage_id`.
3. `action=transfer, stage_id=<returned>, max_chunks=600`: complete transfer.
   Smaller batches are supported. Repeating transfer safely resumes at the
   receiver's verified chunk boundary. A partial chunk fails closed for diagnosis.
4. `action=install, stage_id=<returned>`: hash/RECORD validation, offline venv
   install, synthetic smoke and receipt. Inspect returned `ok` as well as tool
   job success: a successfully executed worker may return `ok=false`.
5. Independently rerun `python3 -I -S <versioned-path>/runtime.py --smoke` and
   inspect the receipt. Preserve the installation evidence; do not benchmark
   corpus data until its scope is known.

Only the designated Foo writer runs mutating actions. This package's author
created/verified the private draft but performed no Foo mutations.

## Runtime use and budgets

`runtime.connect(allowed_directories, temp_directory, budget=None)` requires explicit existing
absolute non-symlink authorized directories. It imports only the installed venv
package path, checks the version and creates an in-memory connection with:

- 4 query threads;
- 8 GiB DuckDB buffer limit;
- 20 GiB maximum spill in the explicit temp directory;
- extension autoinstall/autoload disabled;
- unsigned/community extensions disabled;
- external access disabled except the explicit local directory allowlist;
- configuration locked after setup.

Reviewed explicit integer budget overrides may reduce threads/memory/spill within
the baseline ceilings; increases require revisiting the approved configuration.
Defaults reserve substantial OS/Postgres/control headroom.

Use `python3 -I -S` to exclude global/user site initialization and `PYTHONPATH`.
The jail is the security boundary. DuckDB settings are defense in depth, not an
OS sandbox, and buffer/spill settings are not total process memory/disk limits.
Do not present the tiny smoke as a capacity benchmark or an optimum established
by production measurements. No model/local AI, daemon, Docker, sudo, service or
host-network change is involved.

`--smoke` generates 10,000 rows, writes Zstandard-compressed Parquet, reads it
back and checks row count, ID sum and category count, then scans/groups the
Parquet by category and verifies eight groups of 1,250 rows. It reports startup,
generation, write, readback and group-by timing separately, total elapsed time,
peak RSS, Parquet and grouped-result hashes and effective settings. A single
trial is not evidence of a speedup or measured optimum. Synthetic files are removed
when the test exits; no existing datasets are read.

Official behavior references:
<https://duckdb.org/docs/1.5/configuration/overview> and
<https://duckdb.org/docs/1.5/operations_manual/securing_duckdb/overview>.

## Local validation and rebuilding

```
python -m unittest discover -s scripts/windmill/duckdb -p 'test_*.py' -v
python scripts/windmill/duckdb/build_worker.py
(cd scripts/windmill/duckdb && sha256sum -c ARTIFACT-SHA256SUMS)
```

Run these commands from the repository root. The builder defaults to the reviewed
`scripts/windmill/windmill_foo_jobs.py` transport source. For a separate authoring
layout, pass its location explicitly with `--transport-client PATH`; there is no
hidden cloud-workspace fallback. Rebuilding embeds the current reviewed helper
files and existing public-pinned SSH transport logic, including its explicit
60-second per-command drain bound. It never reads the private key. The Windmill wrapper's own
`paramiko`/`wmill` dependencies are the existing worker transport dependencies,
not installed into the Foo DuckDB runtime. The original verification used worker
`paramiko==5.1.0` and `wmill==1.850.0`; no worker dependency upgrade is requested.
