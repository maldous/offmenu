# Coherent native harness packages

`tools/delivery/native_harness_package.py` prepares a new immutable package from
accepted Git source, selected already-installed dependencies and explicit new
nonsecret configuration bytes. A separately admitted copier can materialize its
five fixed staging roles. Neither function installs, swaps current code, starts
a service, accesses a credential, grants permission or activates delivery BAU.
The original owner/publisher first installers and their receipts stay unchanged.
In particular, the old publisher preparer's fixed `bf9bd13f` source assertion is
never overridden to describe new code.

## Selected installed distributions

`selected_distribution_files(site, lock_bytes=..., upstream=...,
metadata_pins=...)` reads an existing canonical site-packages directory, never
modifies it and never runs its code. It resolves installed METADATA dependencies
from these fixed runtime roots:

- Stokowski 1.1.0, qualified against its reviewed upstream source revision/files;
- LangGraph and its SQLite checkpoint package;
- jsonschema and its actual transitive dependencies.

Every selected version must match `requirements.lock` or
`stokowski-requirements.lock`. Root Stokowski's version and exact installed
package file hashes come from the independently qualified upstream/installation
pin. No optional web server extras, downloads or new resolution are enabled.
Active dependency URLs or extras which are outside this profile are held.

Pass the two exact tracked lock byte strings and an upstream object with
`version`, `source_revision` and `files`. Its files map is site-relative
`stokowski/...` to SHA-256 and must cover the complete selected Stokowski package,
not just its version label. `metadata_pins` independently binds every selected
`.dist-info/METADATA`, `.dist-info/RECORD`, and any unhashed distribution metadata
row. A RECORD's own hash is not assumed to establish upstream authority.

The function uses actual installed RECORD rows. It verifies supplied SHA-256
URL-safe-base64 digests and sizes, refuses links, changed metadata, conflicting
lock versions, duplicate rows and missing dependencies. Output contains regular
package modules, native extensions, package resources and distribution metadata.
It excludes **all** `.pth`, `.egg-link`, bytecode caches and any paths escaping
site-packages, including generated command scripts. OffMenu source is exclusively
selected from Git. Namespace file overlap is allowed only for identical bytes.

It returns `(files, evidence)`: a map from
`lib/python3.12/site-packages/<record path>` to bytes and a bounded provenance
object with selected versions, original RECORD refs, metadata pins, lock hashes,
upstream pins and excluded rows. The exact public CA bundle `certifi/cacert.pem` is allowed
only as that pinned distribution resource (and its fixed venv prefixes); every
other `.pem` remains refused. The upgrade verifier needs the corresponding
reviewed resource exception before these real dependency closures can be adopted.
All returned bytes require independent
qualification before package production. Self-observed hashes never become
independent acceptance merely by passing them back into another helper.

The observed existing delivery environment can supply the 53-distribution
projection described in the private preparation evidence; it already contains
Stokowski, graph and schema packages. The existing sealed publisher environment
has graph/schema but lacks Stokowski. Neither observation qualifies a new
installed dependency closure. The legacy `environment_files` helper remains
unchanged; its custody/identity checks are never bypassed with fake metadata.

## Unprivileged package preparation

`prepare_coherent_package(stage, *, git_dir, head, tree, dependencies,
dependency_evidence, dependency_sha256, runtime, interpreter,
interpreter_sha256, interpreter_custody, node_sha256, node_custody, pyvenv_cfg, owner_current,
owner_catalog, publisher_config, config_pins, acceptance)` is nonroot only.

The owner supplies `PackageAcceptance(owner, head, tree, review)` as trusted
installation context, with a nonsecret independent review `{path,sha256}` ref.
It is not loaded from worker JSON. This object records source acceptance; it is
not root execution permission. Exact source/test/component and coherent runtime
acceptance remain the coordinating owner's separate responsibility.

`git_dir` is the real local common Git object directory, including when the
source checkout is a linked worktree. Existing `git_closure` selects the accepted
head's complete checkout, safe detached metadata and commit-only ancestry.
`validate_git_payload` then checks that closed graph and checkout without
executing Git as root. No hooks, filters, replacement refs or full historical
payload copy are introduced. Current archived evidence exceptions retain their
original exact tree references.

Dependencies are the selected file map above. `dependency_sha256` independently
pins `SHA256(protected_owner_install.encoded({path: SHA256(bytes)}))`, sorted by
path. The producer never invokes pip or modifies an existing virtual environment.
Supply exact interpreter bytes and their independently qualified hash, plus an
`interpreter_custody` `{path,sha256}` reference to actual native OS custody
qualification. A sandbox-mapped UID is not actual host ownership. The root owner
must establish that custody through its approved host route; no synthetic
metadata can satisfy production admission. The supplied Python 3.12 pyvenv.cfg
must retain disabled system-site-packages and its qualified `/bin` or `/usr/bin`
home. Interpreter output is one regular `bin/python`; no actor-owned interpreter
symlinks, bootstrap scripts or editable references enter the sealed dependency
role. Root does not execute this interpreter during materialization.

`runtime` is the exact selected existing runtime beneath current configuration's
`runtime_root`, distinct from that common root. The producer receives explicit
new `owner_current`, `owner_catalog` and `publisher_config` JSON bytes and their
independently supplied `config_pins`; it never reads the installed configuration.
It checks coherent source hashes, publisher identity, source head and Python
hash. The caller must additionally obtain current full config/schema, catalog,
workflow, original installation and policy acceptance; the byte copier does not
infer that semantic qualification from a pin. No empty catalog or new successful
installation receipt is invented by this API. Production config belongs to the
owner, not coding-child requests.

The owner binding is generated from those bytes, exact selected runtime, source
root, catalog and Python hashes. Publisher code is a complete delivery seam:
all maintained delivery Python modules, native RPC/lifecycle hooks and their
statically resolved local Python imports, fixed JS publisher/adapter/gateway
imports, and explicit schema/config resources. This covers RPC source strings
without assuming the old eleven-file release subset is sufficient. Unknown
variable dynamic imports, missing native/relative imports and missing local JS
modules fail closed. Deployment-specific external runtime capabilities still
require coherent validation; static source inclusion is not runtime acceptance.

The shared UIF-122 wrapper descriptor is `native-harness-closure.json`, installed
as root-owned 0444 at `/opt/offmenu-publisher/native-harness-closure.json`.
It is exactly `{version:1, kind:'native-publisher-closure-v1', source_head,
source_tree, node_sha256, files}`. `files` binds every selected publisher source
and dependency regular file, including the wrapper, runner, capacity policy,
bounded owner readers and interpreter; it excludes the descriptor itself.
The producer then includes the descriptor hash in the full publisher role.
Serialization is sorted compact ASCII JSON plus one newline, and its identity
is SHA-256 of those exact bytes. Bounds are 16 MiB and 50,000 file entries.
`source_head` identifies installed harness code, distinct from a work candidate.
`node_sha256` and `node_custody` must come from independent qualification of the
fixed `/usr/bin/node`; this API does not read or select another executable.
Neither the descriptor nor its hash grants root authority, and publisher config
codePins retains its existing narrow allowlist.

The create-only private stage contains `manifest.json` and content-addressed
`payload/<sha256>` files. The manifest records the accepted source, review and
custody refs, dependency provenance and complete fixed-role expected closures:

| Role | Eventual active target | Package content |
| --- | --- | --- |
| owner_source | `/opt/offmenu-stokowski-current/source` | Exact accepted checkout and detached Git closure |
| owner_venv | `/opt/offmenu-stokowski-current/venv` | Selected dependencies, interpreter and pyvenv.cfg |
| owner_config | `/etc/offmenu-stokowski-current` | current.json, catalog.json, binding.json |
| publisher | `/opt/offmenu-publisher` | Coherent delivery import closure and the same dependency bytes under venv/ |
| publisher_config | `/etc/offmenu-publisher/config.json` | This single JSON file only |

Closures contain `directories` and `files`; the root directory uses `""`.
Files declare mode/uid/gid/size/hash. These are **expected** root custody values,
not observed sealing of actor files. Directory modes are fixed 0755; ordinary
files 0444; the two fixed interpreters 0555. Publisher config alone is 0440,
UID 0/GID 976. No caller-selected permission or host destination is applied.
Interrupted actor output remains intact and cannot be overwritten or reused.

## Separately admitted fixed staging

`materialize(package, expected_sha256=..., admission=...)` accepts only a typed
`MaterializeAdmission(owner, package_sha256, operation_id,
host_confirmation_sha256, expires_at)` supplied by the sole qualified root
loader after independent package review and actual host confirmation. No CLI
constructs this capability from a manifest, JSON message, UID alone or worker
success. The actual root loader/privilege boundary must be separately qualified;
there is no workspace-to-root execution route in this component.

The copier rehashes the whole package, refuses unknown roles, extra entries,
links, changed payload bytes and any metadata outside fixed role policy. It
revalidates the full Git checkout/object graph and identical publisher
source/dependency bytes. Every input and destination is qualified before either fence is written.
Admission is rechecked after full qualification and parent checks, immediately
before each directory/file mutation, each bounded write chunk and metadata
change, and after final readback before any completion claim. A write already
begun may finish its current bounded system call; expiry prevents the next
mutation from starting. Expiry leaves all original partial custody intact.

The first create-only fence is
`/var/lib/offmenu-publisher/native-package-closure-<closure-sha256>.intent.json`,
where the closure hash is SHA-256 of canonical `protected.encoded(roles)` bytes.
It records the exact package, original operation and confirmation identities.
Only then is the operation-specific
`/var/lib/offmenu-publisher/native-package-<operation>.intent.json` written.
Thus a crash between fences, a partial copy, or changing operation ID cannot
bypass custody of the same immutable full-role closure. Neither fence is
removed, rewritten or automatically recovered here. The operation ID is a fixed
lowercase SHA-256 identifier.

For the four directory roles, destinations are sibling
`.native-upgrade-<operation>-<role>.new` slots matching the upgrade helper's
convention. For publisher config, the destination is exactly:

`/etc/offmenu-publisher/.native-upgrade-<operation>-publisher_config.new.json`

The existing directory and key remain untouched and unread. The copier does
not enumerate that directory, hash the key, relocate it, or include a `.pem`
in its manifest. Final adoption requires the separately reviewed file-only
publisher-config upgrade contract, rather than the older full-directory role.

Copies are bounded bytes with fixed root modes/owners and create-only writes;
no module import, payload interpreter, shell, Git, hooks or candidate command
runs during this step. Resulting content and metadata are read back. Neither
current targets nor original receipts are changed. Any partial failure leaves
the exact intent and existing partial stages for owner reconciliation; an intent
or occupied slot prevents replay. There is no automatic cleanup, overwrite,
rollback, second operation ID escape, source merge, service start or activation.
The coordinating owner separately supplies actual quiescence, old closure and
rollback qualification to the upgrade route.

## Verification

The bounded tests exercise real tiny Git closures, transitive native import
coverage, RECORD exclusion and tampering, upstream/unhashed metadata pins,
links/collisions, exact package verification before effects, fixed-role metadata,
file-only publisher config, no payload execution, expiry during qualification,
copy chunks/metadata and final readback, changed-ID partial-copy and
crash-between-fences no-replay, and
rejection of JSON/foreign-owner admission. The private synthetic host mapping is
restricted to an unprivileged disposable `/tmp` tree and cannot qualify actual
UID/GID custody. Run with the installed delivery interpreter:

```sh
PYTHONPATH=src:tools/delivery /path/to/pinned/python -m unittest discover \
  -s tests/delivery -p test_native_harness_package.py -v
```

These source tests do not materialize a real host, prove actual root ownership,
read a credential or accept delivery BAU. Independent exact-source review and
coherent package/runtime/adoption evidence remain required.
