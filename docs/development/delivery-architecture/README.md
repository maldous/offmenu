# Accepted delivery architecture design, version 2.1

This is the editable design linked by the [canonical architecture guide](../delivery-architecture.md), not a second architecture or an application. The semantic owner remains `/root/resume_hld_layout`. The 24 nodes and 44 relations describe the target/end state; labels and operation annotations are not proof of deployed paths, model entitlement, tool credentials, exactly-once effects or continuous recovery. Use the guide and current issue evidence for implementation status.

## Read and reuse

- Open [accepted.svg](accepted.svg) for the accepted preview; edit [layout.json](layout.json) only through the canonical design owner.
- [source-custody.json](source-custody.json) binds the exact Library identities, archive/member hashes, repository base and extraction mapping.
- [offmenu-hld-v2.1.zip](offmenu-hld-v2.1.zip) preserves all 14 original members byte-for-byte, including the original README, exporter, checksums and prior QA/roundtrip records. Those records are design evidence from the source bundle, not fresh checks or runtime acceptance.

Portable consumption uses the JSON, [renderer](render_contract.py), [validator](validate_contract.py) and [routing helper](routing_metrics.py). The renderer's SVG path uses Python's standard library. The validator additionally requires NumPy and svgpathtools; PNG rendering additionally requires Inkscape, Pillow and the documented DejaVu fonts. No dependencies are installed or newly pinned by this custody change. The archived `export_contract.py` depends on its original source workspace and is not a portable entrypoint.

For a separately authorized future design revision in an existing suitable environment:

```sh
python validate_contract.py layout.json
python render_contract.py layout.json rebuilt.svg
```

The validator renders in memory; neither command was run for this extraction. Do not overwrite accepted artifacts when checking a revision. Layout edits require the canonical owner's synchronized route/port/label updates and independent review, as specified in the archived README. No automatic layout engine, model or network service is needed for these commands.

## Custody and limits

The archive and five extracted members retain exact accepted bytes. Only this repository usage note, the custody mapping and the architecture-guide pointer are authored here. The historical archive preserves its original filenames; extraction adds no filename exceptions. Workspace paths inside the original exporter/QA are historical source locators, not dependencies to fetch or permission to inspect private storage.

This source-only preservation does not assign a publication owner, configure services, enable automation or establish functional acceptance. No Actions, deployment, new spend/access/credentials, raw-data or personal export, OSM or CIX runtime is authorized. External developers can read this repository copy after the sole integrator accepts and publishes the reviewed candidate; this candidate itself is unmerged and unpushed.
