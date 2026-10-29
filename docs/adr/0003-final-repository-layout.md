# ADR 0003: Final repository layout and installed package boundaries

- Status: adopted with implementation and focused behavior verification
- Standard: repository 2.0.0
- Base: c3e75993b577e85731cb57b01a5441cead9c0d35
- Supersedes: the retained root-layout and command-path decisions in ADRs 0001–0002

## Evidence and decision

The earlier standard correctly preserved operational custody and separated test
runtimes, but retained too many unrelated maintained roots. A passing filename
checker did not establish an adequate architecture. Actual build/import discovery
identified three Python packages, one browser/Worker application, one retailer
extension, two hosting adapters, unmounted integration candidates, source-data
contracts and developer/operations tools. Group those responsibilities explicitly.

Use a Python `src/` layout with explicit setuptools package discovery and package
data. Prove installation with a wheel imported outside the checkout, including
CIqual/Norway JSON resources. This prevents checkout imports from masking broken
installed packages. Keep one root Python manifest and one JavaScript lockfile;
the actual dependency graph does not justify adding workspace/package managers.

Group browser source/assets and its Worker under `apps/web/`, the extension under
`apps/retailer-extension/`, hosting adapters under `deploy/`, and inactive code
under `integrations/staged/` or `integrations/candidates/`. The browser URL and
published extension archive are external contracts; update source consumers and
prove generated output compatibility rather than changing those URLs.

Move schema/provenance contracts to `contracts/`, source bindings to
`config/source-bindings/`, and developer/data/operational programs to `tools/`.
Keep small build/bootstrap/check entrypoints under `scripts/`. Normalize authored
Python command filenames to snake case and update all current callers together.
Historic pinned filenames and source identities remain exact. Route current
physical source paths separately from historical qualification identities;
changed source cannot acquire historical dataset qualification by relocation.

Move research to `docs/research/` and frozen release/migration custody to
`archive/`. Preserve their original bytes. Dated evidence retains the paths true
at its recorded revision; the versioned migration map resolves those paths for
current developers. Keep narrow imported/pinned naming exceptions only.

## Local runtime and reversibility

Ignored dependencies, build output and private mounts (`node_modules/`, `dist/`,
`build/`, `data/`, `output/`, virtual environments and `.delivery/`) remain local.
No source layout can make a private mounted dataset safe to publish. The 49 exact
held operational files retain their existing paths and consumers. Old generated
roots, caches and private loose notes are moved recoverably into ignored storage
with a private restore journal; no data is permanently removed.

The root configuration files required by package/build/hosting tools remain at
the root. Existing private tool state remains ignored. New tracked roots fail
classification. A separate final-layout audit rejects maintained source in
retired roots, missing architecture entrypoints and tracked runtime/secrets.
Its success supplements packaging, import, build and behavior tests; it does not
replace them or establish application/production acceptance.

## Execution boundaries

LangGraph persists finite discovery/standards/check/accepted-output decisions.
Windmill executes bounded deterministic jobs. Symphony provides separately
admitted coding sessions with the existing authorized Codex subscription route.
Linear may supply the task/workpad for those sessions and is optional for local
execution. No duplicate scheduler or recursive manager is introduced. New paid
API charges, paid OpenRouter models and top-ups are outside this workstream;
existing Codex/Antigravity allowances and OpenRouter free models are authorized.

One integration writer owns the existing feature branch and reviewed integration
into `develop`. Legacy workers, hourly automation, Actions and production
activation remain suspended. Migration is not permission to resume them.
