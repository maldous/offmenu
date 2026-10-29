# Blender-authored kitchen animatic — P42.2

One persistent kitchen scene, one camera, 24 seconds / 576 rendered frames at24fps. Default viewport plays a pre-rendered Blender animatic; `mode=live3d` retains the experimental native mesh viewer. This is a rough animatic, not final artwork or production acceptance. Camera/object keyframes are in art/masters/offmenu-journey.blend; sampled transforms in public/asset-family/camera-timeline.json; GLB exports standard transform channels. No animated lens/material-extension support is assumed.

| Caption time | Beat / causal action | Camera choreography |
|---|---|---|
|0–3.43s|Adult scans milk barcode; orange scan line moves|Overview moves toward the person, phone and barcode; above worktop|
|3.43–6.86s|Orange stock token moves to storage; cupboard door opens on right hinge|Travels toward cupboard, rotates to reveal interior|
|6.86–10.29s|Recipe idea beside actual ingredient model|Moves to recipe card, changes azimuth and elevation|
|10.29–13.71s|Plan marker slides onto meal-plan card|Moves toward plan while retaining adjacent recipe/storage context|
|13.71–17.14s|Missing-food shopping bag|Traverses toward bag and cooking area|
|17.14–20.57s|Appliance / meal; animated steam|Above-counter view of cook area, revealing side faces|
|20.57–24s|Replenishment / return to whole kitchen|Returns to overview so journey loops without scene replacement|

HTML captions fade below the visual viewport. Media currentTime drives captions, progress and control state. Chapter buttons and range scrubbing seek the same movie; Pause/Replay affect that clock. Reduced motion uses retained static storyboard frames. Mobile/tablet emulate layout only, not physical-device performance.

## Known boundaries

Current person/model detail remains simplified. The proof demonstrates camera and prop choreography, not a skeletal character-performance rig or live inventory changes. Remaining twenty-choice detailed models and final line-art refinement need human review. GLB standard geometry/material/transform export is independent of Blender-only flat shading; no automatic outline effect transfer is claimed. Three.js is absent from this worktree and has not been silently added.

## Retained failures

Build64: human rejected below-table view, missing supports, chapter geometry swapping and slow startup. P42.1 intermediates: head clipping, clamped elapsed-time progression and high live-WebGL startup cost observed; retained evidence is not counted as success. Initial Cycles animatic: grain rejected internally. Source and intermediate receipts remain alongside successor evidence.
