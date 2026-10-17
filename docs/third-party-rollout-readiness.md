# Third-party rollout readiness

No deployment, account change, credential entry, external scan, email delivery, or production qualification is part of this plan. The schema test verifies that the canonical schema is structurally equivalent to the archived baseline plus ten additive service/care migrations, and that replay preserves a private sentinel record.

The delivery path is the existing local DEV SERVER with WireMock for rapid UI prototyping, followed by a production build/deployment using real provider URLs. There is no intermediate staging or UAT environment. Mock endpoint success does not qualify real providers; production URLs and authenticated provider behavior require separate evidence. This records the environment requirement and does not authorize deployment or starting another runtime owner.

1. Apply the reviewed additive schema to a disposable local D1 test fixture and run the focused schema, care, service, admin, and locale tests. Roll back by stopping application routing to the new endpoints; do not drop tables containing retained records.
2. Keep all optional client services disabled. Confirm an OffMenu-owned Sentry project, privacy configuration, consent policy, error filtering, and budget before diagnostics. Confirm sender, domain authentication, quota, retention, and provider evidence before any outbound email; email remains disabled until then.
3. Enable native care updates and in-app notifications only after role-gating, CAS/audit, retention, and owner-isolation tests pass. Administrative roles remain unqualified until fresh trusted Identity role verification is demonstrated in the target environment.
4. Activate third-party consent services in Arabic only after a licensed, vendor-supported Arabic consent policy or approved external CMP is available. The interface may use its explicit English fallback while translation work remains incomplete. Do not generate or imply an Arabic legal policy.
5. Treat default budgets as conservative application controls, not proof of Cloudflare, D1, email, or AI capacity. Record plan limits, current usage, reset time, and rollback owner before enabling each capability.

If a readiness check fails, disable its configuration flag and route, preserve value-free audit evidence and retained private records, and investigate in the existing local development/test setup. Do not claim production readiness from local tests alone.
