# Independent full-run and recipe-context review — 2026-10-28 07:19 UTC

Approved bulk runner `candidate/scripts/derive_north_star_bulk.py` SHA256 `3adc476be2a6694d62c76bb4d539f0fc698810fd3b942dc9ae501e940efde7a1` with unchanged approved core `fee258de07319fd19c0032701ea2731afabc1f560eb69c80f111088c65cf0509`.

Approved recipe-context builder `candidate/scripts/derive_recipe_context.py` SHA256 `a82cf054ff613467de1dc58c2a34a9f1e08e6c3f5d44ad24edd2d66c5e1ec214` for the selected manifest-bound finite normalized recipe assets, under existing exclusive output reservation.

Independently ran all candidate tests with real jsonschema_rs dependency: 50 pass in 0.594s (17 bulk, 22 core, 11 recipe). Bulk checks cover exact input/code/contract receipts, digest-checked shard reuse, source-release and scope/type constrained cross-packet queries, ambiguous lexical key exclusion, leading-zero preservation, unknown release exclusion, public-only inputs and interrupted slices. Four concrete corrections verified: persistent nonblocking output flock, fsync shard files/receipt/rename directories, owned receipt/config/SQLite scratch accounting, per-packet worker deadline with resumable uncommitted cleanup. Post-rename fsync failure preserves target for inspection/reuse. SQL VM progress handler handles deadline/budget without discarding committed imported shards.

Bulk output and SQL query counts remain candidate-only, not admitted identities or application-serving evidence. No changes to original packages, source authority, source holds or global qualification. Named output budget is sampled, not kernel-enforced; SQLite can have unlinked transient temp files, while shared filesystem free-space reserve still observes actual available space. Outer supervisor owns aggregate memory/cleanup. No claim of full-run success is made by this code review.

Recipe restoration uses the producer-declared original reference, exact native citation source/record/content/license/URL/revision when supplied, typed ingredient path and extent. Existing assertions are never replaced; null yield remains unknown; copied scaling code does not grant calculation safety. Unique staging now fsyncs files/directory before atomic rename and parent fsync; earlier/foreign staging and final outputs are preserved. Release binds imported helper source hashes as well as main source. This is additive restoration of existing normalized fields only, not recipe admission/nutrition or source identity interpretation.

No live Foo, Git, production or global-proof mutation performed by reviewer.
