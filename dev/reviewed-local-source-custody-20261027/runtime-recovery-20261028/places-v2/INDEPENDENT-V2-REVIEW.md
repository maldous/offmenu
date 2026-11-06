# Exact accepted-format correction review

Approved 2026-10-28 for the same first bounded fresh-output proof as v1. Actual v1 run failed before outputs/checkpoint because accepted input manifest uses `format`, not `schemaVersion`. V2 changes exactly that lookup; it still requires `offmenu-curated/1`. No fallback acceptance, transformation, cursor, checkpoint or storage behavior changed.

Independent 49 test executions pass (26 distinct cases, inherited duplication), including actual-format fixture, schemaVersion-only rejection and wrong-format rejection.

Runtime SHA256:
- producer: 8a43e699a0d29e01d9ec1ba8c70ef3cd943aeb796a067302631e7c00d71ca808 (unchanged)
- checkpoint: 5c972b26cb4fb3b8927a086290706f8523e1f804f2b87f7b464f7f9700204ce2 (unchanged)
- catalog: 51d7523c6fde3a661b36a92c9b3e37357b5c11aa692c9cb12c0e23190a4cbac5
- source manifest: 337b441475cfb426ee93ca4bb0e9e4042355ce9a0e670f9c3a73eb650e2254b5

Stage separately, read back hashes, confirm fresh output/checkpoint absence, keep accepted manifest byte pin, real validator, <=25k records/220s soft/300s hard and >=70GiB reserve. Inspect actual paused checkpoint/outputs. No existing checkpoint migration or legacy output reuse. Reviewer executed no Foo commands or writes.
