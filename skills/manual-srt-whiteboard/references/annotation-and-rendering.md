# Annotation and rendering guidance

Read this reference only when planning illustrations, editing whiteboard annotations, or reviewing a rendered result.

## Visual language

- Prefer a restrained hand-drawn composition with clear conceptual relationships, ample negative space, and consistent line, character, and palette treatment across the series.
- For the warm-paper preset, use a warm beige background near `#F5EBD7`, dark-gray sketch lines, and sparse red, orange, or blue accents. Do not apply this preset to Tasks that selected a different style artifact.
- Generated source images should not contain text, letters, numbers, logos, or watermarks. When key text is enabled, keep it as a separate local overlay artifact so it can be revised without regenerating the source image.
- Keep subjects sufficiently separated for reliable semantic regions. Avoid accidental overlaps unless the composition requires them and the annotation can protect them.

## Semantic annotation

- Read the persisted source text for the relevant Unit and inspect the actual source image before annotating. Neither text-only guesses nor purely geometric ordering are sufficient.
- Map visible subjects to narrative events, normally moving from context to key subject, action or change, then reaction or outcome.
- Preserve stable `unit_id` and `visual_id` identities. Do not change Unit text, source ranges, Visual count, order, or Timeline boundaries during annotation.
- Use integer pixel coordinates in the source-image coordinate system. The annotation canvas must equal the source image dimensions, and every region must remain inside it.
- Keep sequence values continuous. Labels and narrative roles should explain why the region appears at that point in the story.
- Use protected regions when a broad or overlapping rectangle could reveal a later subject prematurely.

## Timing and mask invariants

- Timeline artifacts are authoritative. Manual annotation can refine how drawing progresses inside a Visual Item, but cannot invent or replace Voice Unit timing.
- At time `t`, a region may reveal pixels only after its persisted start boundary and only up to its current drawing progress.
- Pixels belonging to later regions or explicit protected regions must remain hidden until their own reveal begins.
- For a single moving pen, prefer non-overlapping region intervals with a short breathing gap when the Timeline permits it.
- A region may divide its interval between line work and color fill, but that internal ratio is a rendering choice rather than a new timing source.
- Preserve a complete final frame long enough to be visually inspected without extending the authoritative clip duration.

## Review checklist

Inspect observable frames or playback, not only JSON fields:

- Opening: expected background is visible and no future line, fill, label, or subject leaks early.
- Mid-reveal: the pen or reveal frontier follows the intended subject; overlaps remain protected.
- Completion: the full intended image is present, overlays are readable, and no region is missing.
- Sequence: visual events follow the persisted narration and Timeline.
- Output: dimensions, frame rate, duration tolerance, manifest identity, and validation result satisfy the renderer Work Order.
- Composition: every Voice and Visual is used exactly once, subtitles do not cross Voice Unit boundaries, and final validation passes.

Visual acceptance remains a user decision even when all structural checks pass.
