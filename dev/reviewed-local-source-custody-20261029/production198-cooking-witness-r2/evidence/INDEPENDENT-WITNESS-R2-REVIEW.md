# Independent cooking witness R2 review

Final approval communicated 2026-10-28 21:02:46 UTC; receipt written 21:17 UTC.

Approved exact Worker module `c2ddec2cf5b1965160160eab24e1a2cd43f8395f7095906955ff67148b95c180` (2585134 bytes), Foo-built helper `b98427279bb9a04fa081140cbbbb2711f6146ffe6bee37599122da8ee18c1193`, embedded app `19c11668db13b88a4c77ddd565dbf7853928b9c0c22cebe1da87fa3742cdb7a5`.

R1 review reproduced a private-citation leak: public parent provenance with retained private citation produced public/shared witness. Corrected pure R2 codec `8b2032742e0b3f14bae9d5f6ae314cca8f1162a2aa6aa1591bea573047afe304` conservatively checks retained nested evidence. Independent probes covered private/missing citation visibility, nested private provenance and unknown nested citations, including forged outer-public flags; all omit the witness from sharing. Explicit-public control is retained. Unknown upstream version, detached/frozen snapshot and mismatched batch rejection checks passed.

Independent VM checks executed actual final Worker lg, CA, SA and cg functions with the exact Foo-built helper: batch/history witness preservation, zero/unknown repeated validation, omission of nested-private witness including forged public flag, invalid batch rejection and rebound history rejection. Recipe and unused lot/record dependencies were explicit test doubles; no claim of full authenticated cloud roundtrip or real private-data access. Existing validation runs before additive successful-return preservation. Server SA uses the same privacy helper as the client.

Independent reverse reconstruction removed only helper injection, the three server seams and embedded app replacement, reproducing exact197 module `08f5ae17eec6b5bede7c746391952cd3f8190507c7ebccd6abb6cb0c66d3d4a4`. Other server/asset bytes remain unchanged. No duplicate heavy build, production mutation, new source admission or authenticated acceptance gate by reviewer. Foo146 combined/18 focused/7 legacy tests and subsequent serving readback are integrator-owned evidence, not independently rerun here.
