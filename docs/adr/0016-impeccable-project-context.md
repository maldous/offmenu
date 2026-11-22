# ADR 0016 — Impeccable project context

Proposed for repository standard 2.5.6.

Impeccable reads durable product context from `PRODUCT.md` and the team's
build preference from `.impeccable/config.json`. Keeping them at those paths
lets another checkout use the same brief and preference. The README remains
the reference for delivery status across the household workflow.

Classify the product brief and shared configuration in the root manifest.
Recognize the tool's uppercase filename and exclude the developer's
`.impeccable/config.local.json` from Git. Verify the two shared files appear
in Git's source inventory and pass the repository naming and layout checks.
