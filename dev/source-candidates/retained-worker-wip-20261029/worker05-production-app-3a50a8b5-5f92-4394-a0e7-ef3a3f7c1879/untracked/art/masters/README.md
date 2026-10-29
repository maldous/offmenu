# OffMenu original storyboard source

Primary editable standard source: offmenu-journey.blend. Its glTF2 binary export is offmenu-journey.glb. Blender4.0.2 was verified locally. Camera and prop transforms use the same24-second timeline; no animated lens or experimental glTF pointer extension.

Rebuild standard source/export: `blender --background --factory-startup --python art/masters/build_animatic.py`. The original mesh input is scene-input.json, generated from public/asset-family/geometry.js. This command writes its blend/GLB/timeline beside the script; run only under normal source custody.

Render-specific source: offmenu-journey-animatic.blend. line_materials.py creates the noise-free deterministic flat-shaded render treatment. These Blender shader effects are baked into the animatic and not presumed to transfer through glTF. Current video/publication acceptance remains provisional. LicenseRef-OffMenu-Original-Art, owner control; no external distribution grant is asserted.
