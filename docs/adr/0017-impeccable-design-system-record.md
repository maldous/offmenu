# ADR 0017 — Impeccable design system record

Proposed for repository standard 2.5.7.

OffMenu now has a durable, user-confirmed visual system rather than a local Live
session alone. `DESIGN.md` is the normative portable record of its extracted
tokens and the visual invariants that matter across new surfaces. Its companion
`.impeccable/design.json` carries panel-only extensions such as tonal ramps,
motion, elevation and renderable component examples.

The accepted light environment is the visibly green `#d9efda` canvas. The
original animated blue-bracket and white-glass barcode-bowl sign is the logo
wherever product identity appears. The record preserves its reduced-motion,
offscreen-pause and material-fallback requirements without placing any private
source path, runtime receipt, screenshot or injected preview bytes in source.

Share `.impeccable/live/config.json` because it describes the repository's
static HTML targets and safe insertion convention. Ignore every other item
under `.impeccable/live/`: they contain host-specific paths, process details,
sessions, tokens, injected-file journals or generated snapshots. The decision
does not enable a Live server, modify product runtime behavior, or authorize
publishing.

Classify `DESIGN.md` as a root design-system record, add its uppercase name to
the conventional filename allowance, and retain `.impeccable/` as shared design
workflow configuration. Verify the source records with the repository layout
check and Impeccable's sidecar-aware document validation.
