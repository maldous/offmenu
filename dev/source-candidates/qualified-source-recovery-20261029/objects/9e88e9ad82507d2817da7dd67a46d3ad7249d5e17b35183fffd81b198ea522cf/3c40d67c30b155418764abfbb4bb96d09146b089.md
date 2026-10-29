# Worker 27 ownership evidence integration contract

## Custody and requirement scope

One deliverable on `feature/ownership-evidence-20261014`, provisional base
`8652b312ce7989c5e4f2d49ae765d5d8daf5841d`. Morgan dispatch supplied fetch exit 0
at `2026-10-14T06:48:53.225632+00:00`; the worker verified branch and HEAD locally.
This is a code increment for owner review, not accepted source delivery or release
certification. Dataset01 retains source ownership. Development START is granted.

The complete DATA-05 register entry requires approved GS1 supplier/product identity
feeds (product research pp. 7-9): access/display/redistribution/retention and supplier
rights must be established; GTIN identity and source timestamps must be preserved.
The complete ENRICH-11 register entry requires all 938 source-catalogue entries and
country gaps retained/processed. The enrichment report's decision brief and entity
model (pp. 3-5) require distinct business/brand/site identities, dated control versus
consolidation/minority/franchise/licence, scoped manufacturing versus headquarters
origin, and fiscal-year size observations. Its p. 2 separately counts 947 regional
source-or-gap entries and 78 global references; these counts use different scopes
and are not evidence of usable coverage. Neither requirement is marked complete
by this adapter. Registers, source ledgers and corpora remain with their owners.

## Exact gap and delivered behavior

`public/evidence-model.js::ownershipPath` already follows verified control and
accounting-parent edges, optionally minority edges, checks current date boundaries,
and returns unknown when a path is missing. Synthetic tests prove these existing
cases. It has no typed business adapter or jurisdiction selection, and malformed
dates can pass its negative comparisons. Its shared implementation is unchanged.

`adaptBusinessEvidence({entities, assertions})` returns `{entities, assertions,
errors}`. Exact internal IDs are required. Entity kinds are company, site, brand
and product; names are descriptive only. Duplicate IDs and explicitly personal
records are rejected. Candidate identities remain candidates. No provider lookup,
name matching, collector, personal fixture or ultimate-owner inference is added.

Assertions require source ID/record ID, jurisdiction, scope, evidence class,
rights revision, retrieval date, effective start and freshness deadline. Optional
effective end and retention deadline must also parse as real calendar dates.
Accepted date forms are YYYY-MM-DD and UTC timestamps ending in Z. Intervals are
start-inclusive/end-exclusive. Source country, market and jurisdiction are retained
as separate fields; none substitutes for manufacturing origin. Unknown predicates
and incompatible entity/value types receive explicit errors rather than guessed
mappings. The adapter is a narrow projection, not a replacement raw-record archive.

Relationships retain distinct predicates: control, accounting-parent, minority,
franchise, licence, operating-brand (company to brand), site-operator (site to
company). Control relationships link company/brand to company. Manufacturing
origin applies to product/site; headquarters/incorporation applies to company.
Size records retain metric, nonnegative amount, unit, fiscal year, entity/group
basis and declared/estimated method; revenue requires currency. Size and absence
of parents do not imply independent ownership.

`businessOwnershipPath(adaptedModel, start, target, options)` evaluates only
verified exact identities and current control/accounting-parent edges; minority
is opt-in. It requires explicit admitted `status: 'active'` and excludes every
other or absent state, as well as expired or malformed temporal evidence.
Explicit market/jurisdiction options require matching fields on every
edge. Contradictory current parents of the same relationship type block traversal
through that subject. Cycles terminate. It returns evidence IDs for a matched path,
not an ultimate-owner verdict; a missing parent remains unknown. Accounting
consolidation is preserved as such and must not be labelled beneficial ownership.

## Owner integration and validation

Dataset01 must supply already permitted, reviewed assertions with stable IDs and
source custody. This adapter does not grant rights or independently verify imported
claims. Run existing admission/entitlement checks before display or publication;
use the returned evidence IDs to show original source, effective dates, scope and
relationship type. Keep reporting exceptions and unmapped provider fields in the
owner's source records. Do not promote candidates or silently drop adapter errors.
No serving endpoint or UI is wired in this increment; that is an integration step
for Morgan review on a freshly fetched provisional develop with recorded custody.

Original candidate validation passed 18/18 tests (9 focused synthetic cases plus
9 existing regression cases), using two test-file child processes. See the review
correction below for current validation. Tests spawn no children and perform no
Git writes, network calls or provider access. No Git fixtures were needed.
Inherited GIT_* variables are stripped for tests and the scoped actual commit;
Git identity and disabled hooks are command-scoped, with no persistent settings.

Shared primary checkout before commit: HEAD and refs/heads/main both
`8652b312ce7989c5e4f2d49ae765d5d8daf5841d`; index SHA-256
`4332ef16a3df2cd9032b4f099a74425a111bd2e5448e0f5066c5f3f3cb54f389`.
Post-commit readback must match all three values. Commit scope is exclusively this
document, `public/business-evidence-model.js` and its focused test file.

## Worker 11 F1 correction: explicit assertion-state admission

Prior immutable candidate `6c9f85db8258dc41cf236af01e48b934e49de2f3` remains in
branch history. Worker 11 reproduced a medium finding: the three-state exclusion
list admitted `invalid`, `expired`, `superseded`, `rejected`, `unknown`, new state
strings and absent legacy status. Such a row could establish a path or suppress
a usable competing parent. Root cause was unvalidated metadata forwarding paired
with a denylist before conflict detection.

The supported usable projection state is now exactly the string `active`.
It means the source owner has explicitly admitted this assertion's evidence state
for this projection, independently of identity `matchStatus`. Dataset01 must map
source lifecycle states deliberately from retained source evidence and review;
the adapter performs no alias mapping, automatic upgrading or source validation.
Source spelling such as `valid` or `ACTIVE` is unsupported until an owner-reviewed
normalization contract establishes it; neither maps implicitly to active.
Do not fill missing legacy states with active. Absent/null/empty/unrecognized
status is withheld as unknown, even with verified identities and current dates.
An explicit active state still needs all existing identity, scope, temporal and
upstream permission checks; it is not certification or a rights grant.

Structurally valid rows with unusable states remain in returned assertions with
their original status (including absence), source/date/jurisdiction/rights metadata
unchanged and receive `Assertion state is not explicitly admitted active` in
`errors`. They are retained for review, not usable traversal evidence. The path
function independently applies the same positive state check, including for old
adapted models, before forming conflicts. A single unusable row yields unknown;
an unusable competing parent cannot block an otherwise valid active path. Two
contradictory active parents still block traversal. No source or production caller
has been changed.

Before the code fix, the two new regression groups ran with `--test-name-pattern='only explicit|unusable competing'`
and failed (exit 1, 0/2 passed), reproducing missing state validation and invalid
competing-parent suppression. After the fix, the command below passed 20/20
(11 focused synthetic groups and 9 existing regression groups), exit 0:

`node --test --test-isolation=none --test-concurrency=1 tests-web/business-evidence-model.test.mjs tests-web/global-data.test.mjs`

Both runs stripped every inherited GIT_* variable. In-process test isolation spawned
no test-file child processes. Coverage includes invalid/unrecognized/absent/active
states, original metadata/input preservation, direct path protection, competing
parents in both orders, active conflicts, and candidate identity remaining unknown.
The correction started with the same primary HEAD/main/index values recorded
above; post-commit readback is reported with the new immutable commit and binary
diff hash. Worker 11 targeted recheck and Morgan verdict/integration remain pending.
