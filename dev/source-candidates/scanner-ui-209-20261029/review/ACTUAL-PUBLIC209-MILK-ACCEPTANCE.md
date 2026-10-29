# Actual public209 milk UI acceptance — FAIL

2026-10-29 02:02–02:04 UTC. Fresh supported cloud browser tab19 at https://offmenu.aldous.info/demo/scanner.html. Exactly one manual original barcode4088700055496, Barcode namespace, No hint exact lexical lookup. No camera permission, image, login, Google, private session, pantry/save/finish, extra API request, or repeat lookup.

Integrator supplied published version d52f5aca-2c52-4104-b6ba-2a3d386a968b, deployment03bc85e5-fe20-45f2-87a4-524546856019 and readback public asset SHA a7391197f0e5330e69e6baf07cd6d426d9b8d81ee1303f014585ee0221c07e9f. Reviewer did not independently download script during UI acceptance. Actual consumed new behavior verified by visible209-specific pending/final message strings, not a separate browser resource-byte hash.

Submitted around02:03:05. Initial visible state: original code retained, checking owned source facts (up to40seconds); Category and Ingredient match Lookup in progress. No camera found was already displayed; no camera grant attempted.

By02:03:24 settled result:
- Product name and Brand both em dash, no Champ iced coffee/Farmdale.
- Original barcode4088700055496 retained.
- Category and ingredient match Not yet identified; pack dash; photo unavailable.
- “Barcode retained · no qualified details in the selected source indexes. Other sources may differ. · Additional source facts or coverage unavailable; inspect retained observations.”
- “Product lookup is unavailable for this release. Your scanned code is retained in this session; no product has been identified.”
- Overview shows zero OFF and zero USDA foundation observations.

Screenshot ACTUAL-PUBLIC209-MILK-FAIL.png captures actual settled result. Bounded retained browser error/warn logs show only extension metadata errors; own-origin offmenu.aldous.info filter returned none. No causal inference from extension errors, no timeout claim (result arrived before40s). This is a genuine displayed failure with functioning browser capability, not proof of the underlying request or validation cause. No hidden state/raw response/network interception performed.

Reported promptly to sole integrator and efficiency coordinator. Source27offline tests remain passed but do not supersede this actual production failure. Private route remains offline-source tested only. Do not claim the user's scanner issue fixed or ask them to retry based on this acceptance.
