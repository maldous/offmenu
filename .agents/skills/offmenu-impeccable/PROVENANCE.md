# Impeccable provenance and installation scope

Prepared 2026-10-18. This folder is an OffMenu-specific, documentation-only adaptation of Impeccable. It is not the complete upstream package and has no optional runtime.

## Official source and pin

- Official site: https://impeccable.style/
- Official repository linked by that site: https://github.com/pbakaus/impeccable
- Selected release: skill-v4.6.0, published 2026-10-15.
- Immutable source commit: 8a0e198da34ebc5b936a9d5975fb7a3b1cf353b7
- Annotated tag object: 60470cd21d9bede0b926093325f3ae483d293c35
- The upstream tag is unsigned. A commit hash pins bytes; it is not a signature or a third-party security certification.
- Source files were retrieved through the GitHub connector and checked against their Git blob SHA-1 and byte lengths. UPSTREAM-MANIFEST.json additionally records SHA-256 hashes for each selected source and adapted reference.

## License and changes

The pinned repository declares Apache-2.0, copyright 2025 Paul Bakaus. LICENSE and NOTICE.md are retained verbatim. The upstream NOTICE identifies MIT-derived iOS/Android guidance; those native-platform reference files are not included in this web-only subset. The notice is retained conservatively.

Every adapted reference carries a prominent change notice. Adaptations remove optional runtime commands and live-mode routing, omit native routing, replace upstream command menus with static-reference guidance, remove React-specific examples, and subordinate generic aesthetic rules to the approved OffMenu brief. The OffMenu wrapper is a new file, not upstream-authored. This package is not endorsed by the upstream author.

## Additive project scope

The sole install destination is .agents/skills/offmenu-impeccable/. No global skill directory, existing frontend-design skill, AGENTS.md, PRODUCT.md, DESIGN.md, package manifest, lockfile, application code, or existing .impeccable configuration is replaced or edited.

This skill uses a distinct name to avoid replacing an incumbent skill. Before installing, inspect the actual destination and ancestors. If any destination already exists, stop and compare it; do not overwrite. Installation alone does not resume paused UI work.

## Deliberate exclusions

No upstream scripts, binaries, agents, browser bundles, native references, root SKILL.md, new-work/shape/init/document workflows, runtime configuration, hook manifest, extension, or installer is included. No package manager command, binary download, telemetry endpoint, local server, DOM injection, credential setup, CSP change, or security trust action is part of installation.

The standard upstream install can add project hooks and an engine. Its npm package version does not fully pin content: the engine's installer fetches the current universal skill bundle from https://impeccable.style/api/download/bundle/universal. This curated source snapshot avoids that floating-content path.

## Verification and use

Validate file hashes, the wrapper frontmatter, relative links, the absence of executable files, and the installation-only diff. The intended invocation after the project accepts the added folder is $offmenu-impeccable. Discovery on a specific Codex host must be checked separately; a repository commit does not prove that a particular checkout has received it.

The references are design guidance. Their examples and scores do not certify accessibility, performance, or browser support. Use the existing application toolchain and report checks actually performed. Any full upstream runtime installation or live-mode use needs a separate reviewed plan.

## Source documentation

- Installation and Codex paths: https://github.com/pbakaus/impeccable/blob/8a0e198da34ebc5b936a9d5975fb7a3b1cf353b7/README.md
- Hooks and trust: https://impeccable.style/docs/hooks/
- Privacy and telemetry: https://impeccable.style/privacy/
- Pinned license: https://github.com/pbakaus/impeccable/blob/8a0e198da34ebc5b936a9d5975fb7a3b1cf353b7/LICENSE
