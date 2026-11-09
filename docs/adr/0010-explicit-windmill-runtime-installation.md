# ADR 0010: Explicit installed Windmill runtime

Status: proposed source candidate; no live cutover accepted.

## Context

Canonical source and privately installed operational files currently share paths.
A clean checkout must not silently discard locally installed admission behavior,
opaque runtime custody, or callers bound to those files. Private `.delivery/` is
not traversable by the UID985 SSH executor and must not be opened broadly.

## Decision

Reserve `.offmenu-runtime/<content fingerprint>/` for the explicit installed runtime.
This is a new generated runtime location, not an ignore rule for existing dirty
files. Existing `scripts/windmill/` holds remain until all relevant callers have
completed a verified handoff. Repository source, tests and the installation tools
remain tracked; private payloads, host policy and receipts remain untracked.

Private staging retains the exact selected hold inventory and source provenance.
The production installation selects only four dependencies: maintained runner,
existing host policy, capacity64 checker, and its storage module. It does not
expose preservation backups or the other retained receipts/documents.

Installation is create-only under trusted owner UID1000. The intended access is
UID985 directory traversal/read and file read, with no write grant, no group/other
access, and no inherited/default ACLs. Security-permission changes require the
applicable action-time confirmation for the exact installation. No tool may infer
that approval from this ADR or a general cleanup instruction. Existing `.delivery`,
launcher, mounts, credentials and network controls are unchanged.

The installer verifies complete inventory, file bytes, owner, ACLs and source pin.
It leaves failed/partial installations for reconciliation rather than overwriting
them. Staging and installation assume one trusted writer; existing owner/root
and read-write container access mean content verification is not filesystem
immutability. Runtime consumers must run Python with bytecode writing disabled.

## Acceptance and rollback

Qualify execution through the actual `/offmenu` jail as UID985 with unchanged
logical state root, lock identities, admission behavior and opaque job receipts.
Verify all deployed argv changes against exact original script revisions. Changed
runner hashes can conflict with old job identities; status/cancel and uncertain
outcome reconciliation must remain available without replay.

Retain the old artifact and exact consumer configuration for rollback. Do not
modify live callers, enable schedules or remove held files merely because staging
or installation succeeds. Canonical cleanup follows source integration and verified
consumer handoff, followed by exact remote commit and clean-state verification.
