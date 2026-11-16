# Adopted additive publication implementation

2026-10-28 07:33 UTC — original publication owner independently reviewed reviewer-authored durability correction. `project()` AST is unchanged from original; unique staging, fsynced manifest/directory entries, final delta rename under existing exclusive output reservation, exclusive durable descriptor publication last. Existing/foreign candidates are preserved. No actual dataset publication performed.

- Canonical projector: `prepare_north_star_projection_reviewed.py`
- SHA256: `75e7d573596d98679b18598e3ecbd04c859105913282b18beacfc5e5ab59386f`
- Original `prepare_north_star_projection.py` is retained for provenance only, NOT the executable publication handoff.
- Native additive uploader: `netlify_north_star_publisher.py`
- SHA256: `966ef21bc8771bae492c053fe9f0d54f1bae6395bb1fbbf3e042a36c8e076885`
- Native path: `u/admin/offmenu_netlify_north_star_publisher_20261028`
- Deployed source readback exactly matches local approved file; private ownership retained.
- Native read-only status verification job: `01a1816d-556b-d1b4-9445-ed22467a9e84`, existing fixed-site deployment `6ade30f984233b1725dc0501` ready; no Netlify mutation or credentials returned.
- Independent local test execution: 56 passing executions (49 distinct tests; original test class imports cause duplication).

Actual additive publication still requires final full-bulk manifest + reviewed consumer-proof receipt + exact actually served base manifest + reviewed projection descriptor. Namespace fixed `/common-data/derived-releases/north-star-structural-v2-20261028/`; only manifest and derivative shard gzip files. No base aliases, SQLite/query-index export, automatic application activation or identity admission. Recipe-context changes remain separately scoped.
