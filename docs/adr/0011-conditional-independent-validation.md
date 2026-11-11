# ADR 0011: Conditional independent validation

- Status: owner-adopted; source integration pending; repository standard candidate 2.5.0
- Selected source policy: `tools/delivery/integration-policy.json`, version 2
- Reviewed policy bytes: `tools/delivery/integration-policy-v2-candidate.json`
- Owner adoption source: `441285d6ba19f0a2affe070c349b7261eb095350`

## Decision and boundary

Independent cloud source work need not depend on a Foo execution service when
its actual changes and required checks do not depend on Foo. After adoption,
permit that route only with an independent, exact-source semantic scope review.
Changes needing Foo services, deployment state, local data, permissions, execution
or installed integrations require Windmill. Unknown or disputed scope defaults
to Windmill. A docs-only label or a directory allowlist is not classification.
Mixed changes remain Foo-dependent unless the complete candidate is independently
established as Foo-independent. A scope reviewer must examine affected consumers
and necessary checks, not merely the changed filenames.

Use binding version 4 for existing PRs in the authenticated connector-owner lane.
Version 3 remains release promotion; historical version 1 and 2 integration
bindings/readers are preserved and never gain cloud eligibility. New labelled
cloud receipts are rejected through their legacy validation consumer. No protected
publisher installation, service migration, credentials, root transport, security
change, new scheduler, Actions execution or deployment is part of this decision.

## Evidence contract

Bind repository, exact branch, base, head, tree, complete sorted changed paths,
policy and capacity identity, original validation operation and accepted outputs.
The owner obtains the canonical Git diff independently, including deletions and
both paths of a rename. The cloud route requires a separate independent scope
review containing that same source identity, `foo-independent` classification,
reviewer, rationale, evidence identity, accepted verdict and no findings. The owner binds the complete implementation-author and provenance-owner set;
validation and review actors cannot belong to that set. Scope and semantic
reviewers may differ. Each retains provider, requested model and honestly known
or unknown model resolution; human reviewers may identify themselves as human. The independent exact-head semantic
review must bind both the scope review and the original validation receipt.

Both new routes require an original independently executed terminal receipt,
not a relabelled self-authored or stale pass, or a manufactured Windmill job.
The trusted owner may normalize fresh immutable Engine/cloud evidence into this
contract while preserving original operation, source and log identities. That
adapter must verify the original evidence rather than invent execution facts.
A separately admitted independent executor can run the accepted-base commands
against the exact cloud candidate and retain real logs without a Foo service.
Bind actual executor,
environment/dependency hashes, trusted validator revision from the accepted base,
commands, log hashes and per-check results. At least one required check must pass;
every required check must pass unskipped. Optional skipped coverage is explicit.
The owner and reviewer determine required coverage from the actual affected
behavior. This schema does not convert a focused check into full acceptance.
Cloud and Windmill receipts remain distinct; Windmill receipts retain job identity.

The version 4 contract pins receipt, scope and policy-adoption objects with
`fingerprint`, the controller's canonical JSON SHA-256. Its policy hash uses that
same canonical representation, not a file's whitespace-dependent byte hash.
Historical binding hashes are unchanged. Fingerprints prove content association,
not authentication. Only the authenticated integration owner may supply original
observations; worker reports, local filenames, booleans or hashes alone cannot
prove independent execution, accepted policy or review authority.

The gateway continues to consume the unchanged typed merge action after fresh
controller qualification. Retain sole-writer claims, exact head/base, independent
review, normal GitHub protections, publication-trigger checks, cancellation,
uncertain-effect reconciliation, and canonical merge parents/tree/ancestry checks.
The controller never executes commands supplied inside a receipt.

## Adoption and bootstrap

ADR 0005, lines 91–99 in the prior source, requires policy/validator changes to
receive independent review and verification under the previous policy before
taking effect for subsequent work. Version 1 requires bound Windmill validation.
The owner has explicitly authorized a one-time exception for this conditional
validation policy change: independent source review and cloud validation replace
that change's Windmill check. This is a governance exception, not a claim that
Windmill ran, and not authority for future policy changes to skip their controls.

Prepare the policy-only change from accepted `develop`, excluding unrelated
unmerged work. Freeze and independently review/test its exact source. The
integration owner retains an immutable exception record containing the original
authorization evidence hash, exact policy source head and policy hash, independent
review hash and original independent cloud validation receipt hash. The public
source contains no private approval text, receipt paths or runtime evidence.

Adoption verification is discriminated: `prior-policy` retains a real previous
policy validation receipt; `one-time-cloud-bootstrap` retains the separate cloud
receipt and named exception `offmenu-conditional-validation-20261111`. The latter
is restricted to the fixed initial policy digest. It cannot authorize different
future policy bytes. The exact source head is pinned off-repository by the owner,
avoiding a self-referential commit-hash field or an implementation-issued approval.

Exact source review, independent cloud validation and explicit owner adoption
are complete for the policy identified above. This source activation copies the
reviewed policy bytes into `integration-policy.json`; normal reviewed integration
is still pending. It remains subject to normal GitHub protections, sole-writer
ownership and canonical readback. No host configuration is changed. Before subsequent
candidates use v4, refresh their base to the accepted policy revision and obtain
fresh source review/validation. Do not make the initial policy candidate qualify
itself with v4 or report that a v1 Git base already contains the adopted policy.

Subsequent v4 admission consumes the separate owner-issued adoption record.
Canonical accepted-base observation must confirm the policy exists in accepted
control state. A candidate's own head cannot be its policy-adoption source. A
policy file merely present on a candidate branch, its `enabled` setting, or a
successful synthetic test cannot self-activate this lane. Future policy changes
continue to require verification under their previously accepted policy.
Source integration, policy adoption, runtime installation, validation qualification
and product acceptance remain separate facts.

## Verification and compatibility

Test eligible cloud evidence; unknown/Foo-dependent or self-classified scope;
stale source, base, tree, outputs, review, policy and adoption; missing/failed or
skipped required checks; implementation/executor identity collision; legacy
receipt rejection; and unchanged gateway/protection/readback behavior. Synthetic
fixtures are authored test inputs only, never production acceptance receipts.
Run prior accepted controller/gateway tests against candidate imports as well as
new tests. Preserve all existing v1/v2 fixtures and reader contracts.
