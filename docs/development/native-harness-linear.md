# Native Linear metadata planning

`tools/delivery/linear_delivery.py` implements UIF-123's bounded, pure metadata
planner. It uses the UIF-122 contract module, the existing release policy and
fresh native observations. It has no Linear client, environment credential
reader, network call, persistent queue or workflow-state mutation. The root
integration owner alone may consume its desired actions through the existing
authenticated Linear connection. Coding children receive no credentials.

## Resolve current authority

Resolve issue UUID, project UUID and team UUID from Linear, never from a branch,
slug or a previous attempt. The 31 October 2026 native readback resolved:

| Native record | UUID |
| --- | --- |
| UIF team | `53f584e7-70a1-4b1e-b982-b815210e47d4` |
| UIF project | `ffb6c7d9-4eff-46eb-a805-99f0cc2edfa0` |
| OffMenu project | `ce60c1ab-a732-4a71-8471-14c9dc393886` |
| UIF-123 outcome in UIF | `67ce7259-7dee-473c-88ed-26a409a25b44` |

These are observed routing facts, not a new configuration binding. The old
`symphony-linear-binding.json` OffMenu issue remains historical/current to its
own runtime and is untouched. Select the actual project for every issue. Native
cross-project dependencies are allowed; they do not move or duplicate outcomes.

UIF-123's native blocker is UIF-121. UIF-122 is its parallel interface dependency;
compatibility must be checked before coherent acceptance, without serializing
independent implementation behind the whole UIF-122 outcome.

## Root adapter input and output

Python API: `plan_delivery(request, policy) -> dict`. Load `policy` using
`native_harness_contract.load_release_policy`. The planner calls the shared
`validate_handoff`, `validate_release_candidate` and bounded canonical
`fingerprint`; it does not copy those validators or read evidence references.
Malformed observations raise `LinearPlanError` or shared `ContractError`.

The version 1 request contains these exact fields:

| Field | Normalized native observations |
| --- | --- |
| `projects` | List of `{id, name, team_id}`; exact UUIDs, name `UIF` or `OffMenu`. |
| `outcomes` | List of `{id, identifier, project_id, team_id, state_type, blocked_by, pr_urls, milestone_ids}`. Identifier is `UIF-N`; `state_type` is a native `backlog`, `unstarted`, `started`, `completed` or `canceled`. |
| `blocked_by` within each outcome | Native incoming blocking relations, each `{id, state_type}`; preserve unresolved cross-project blockers. Canceled does not mean dependency completed. |
| `pr_urls` within each outcome | Existing native PR attachment URLs. |
| `milestone_ids` within each outcome | IDs of existing, exact-matching native milestone comments, verified by the root adapter. |
| `changes` | List of `{handoff, pull_request}`. Several handoffs, attempts and PRs may refer to the same outcome. No attempt identity is fabricated. |
| `dependencies` | Explicit root-selected desired `{issue_id, blocked_by_id}` relations, with both endpoints in `outcomes`. Never infer dependencies from a branch or copied backlog. |
| `effects` | Existing owner-custody `{action_id, status}` observations for `pending`, `unknown`, `denied`, `succeeded` or `failed` metadata actions. |
| optional `promotion` | `{candidate, issue_ids, pull_request, tag}`; candidate is the frozen shared release-candidate value, issue IDs explicitly select its constituent outcomes and each requires a source handoff in `changes`. |

Every request also has `version: 1`. Lists are bounded to 128 items, JSON is
bounded by the shared fingerprint traversal, and unknown fields fail closed.

`pull_request` is `{url, head, tree, base, merged, canonical_verified}` plus
`merge_commit` only when merged. URLs must be canonical
`https://github.com/maldous/offmenu/pull/N`. Hashes are exact lowercase Git
object IDs. Root must qualify head/tree and canonical merge/readback facts using
the existing GitHub adapter before setting `canonical_verified`; an untrusted
coding report cannot set it as acceptance. A develop PR must match its exact
handoff head/tree and target. A promotion PR must target main and match the
frozen candidate head/tree. Root selects constituent outcomes after verifying
their inclusion in that candidate; the planner does not inspect Git ancestry.

Promotion `tag` is null until observed, then
`{name, commit, tree, immutable_verified}`. It must match the canonical merged
release commit and candidate tree. Root alone qualifies immutable tag readback;
this flag is not inferred from a tag name or successful API request.

The returned `actions` have `version: 1`, `action_id`, `kind`, `issue_id` and
`project_id`, plus the following finite payloads:

| Kind | Payload | Root consumption |
| --- | --- | --- |
| `linear-link-pr` | `url` | Ensure the native PR link/attachment exists on that exact outcome. |
| `linear-ensure-dependency` | `blocked_by_id` | Ensure that native incoming blocking relation exists, preserving other relations. |
| `linear-record-source-milestone` | `milestone_id`, `milestone` | Record one native comment containing the exact structured milestone and a stable `native-source-milestone:<milestone_id>` marker. |

`action_id` is the shared fingerprint of the action body without `action_id`.
`milestone_id` fingerprints the exact milestone. Root's comment readback must
match the structured content and marker before reporting the ID as present;
a marker alone is insufficient. A source milestone records source/PR/merge facts.
Release milestones also retain the immutable candidate ID, tag and the full
explicit sorted constituent issue list. Promotion PR links are emitted for every
constituent issue even if its feature PR is already linked.

Duplicate desired actions collapse by ID. Native PR/relation/comment readbacks
suppress no-ops. Every supplied prior effect suppresses replay and returns a
`holds` entry with `owner-reconcile-native-readback`. Success without readback is
still held; failure is not permission to retry. Root persists intent in its
existing custody before mutation, records the effect there and obtains fresh
native readback. Unknown effects reconcile the same ID; denied actions retain
the authority hold. Metadata repair never reruns a source merge, job or attempt.
This planner owns no retry journal or autonomous scheduling loop.

`dependencies` in the result reports only whether native blockers are completed.
Desired missing relations remain unresolved until readback, even when their
target is already completed. This is an observation, not coding admission or a
second Ready queue. Actual provider/resource/ownership admission remains required.

## Source milestones and acceptance

Verified develop merges produce `source-integrated`. Canonical main promotion
with immutable tag readback produces `source-released`. These observations do
not prove profile qualification, delivery BAU adoption, deployment or product
acceptance. The planner always returns `workflow_state_changes: []` and
`deployment_acceptance: "not-established"`; it never requests Done. A root owner
may close a source-only outcome only under its own exact acceptance contract.
Product Done needs separate product acceptance evidence. Existing old operation,
attempt, lease and job IDs/readers retain their original interpretation.

The legacy integration controller's `update-linear`/Done action is not silently
reinterpreted or patched by this component. UIF-127/root must route the new finite
actions and prevent the legacy completion route from applying to native harness
outcomes during coherent adoption. This source component is not installed runtime
acceptance or permission to activate it.

## Local checks and CLI

From the selected source checkout, after the shared module is integrated:

```sh
PYTHONPATH=src:tools/delivery /home/user/src/offmenu/.venv-delivery/bin/python \
  -m unittest discover -s tests/delivery -p test_linear_delivery.py -v
PYTHONPATH=src:tools/delivery /home/user/src/offmenu/.venv-delivery/bin/python \
  tools/delivery/linear_delivery.py --request .delivery/linear-observation.json \
  --policy config/delivery-release-policy.json
```

The CLI reads bounded local JSON and prints the plan; invalid input returns code
2 with a generic diagnosis and does not echo input. There is no apply command.
During disjoint implementation, compatibility checks may append the exact
authorized UIF-122 sibling `tools/delivery` path to `PYTHONPATH`; record its source
hash and rerun against the final accepted coherent source before adoption.
