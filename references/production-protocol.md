# Planning and continuity protocol

## Deliverables in dependency order

Brief and accepted user constraints → asset bible and scene geography → camera/action animatic → shot contracts → compatible reference frames → pilot joins → sequential generations → seam review → frame-based edit → full-film review.

Keep director, continuity coordinator, generator and editor as distinct passes. One agent may perform them all. The coordinator reviews proposed inputs before generation and observed outputs afterward; it does not just proofread the final prompt. Do not spawn assistants unless authorized by the user or host instructions.

## Camera design

Draw a top-down map with named positions, doorways and solid occluders. For a continuous journey, identify the path that can physically connect each composition. A large apparent scale change needs either travel through space, a lens change, or an editorial transition; do not leave the model to invent which. Distinguish dolly from optical zoom. Lens numbers are aesthetic intent unless actually controlled by the selected model.

Write entry/exit states as shared objects at a join. Each contains location, heading, height, framing, lens feel, motion direction, speed class, subject action phase, visible asset states and lighting. Define the coordinate convention once. Choose a motivated axis crossing or an establishing view when direction changes. A hidden cut behind a doorpost still needs compatible motion and geography on both sides.

For this film: preserve a slow descending ocean route, expand the city through parallax, follow one shrimp taxi toward a fixed doorway, accelerate within the approach, stabilize briefly for the readable throw, then travel right through one doorway into the lounge. Make the opaque partition hide the dojo. Finish with one city pullback and one deliberate terminal stop. Faster pacing does not require erratic camera acceleration; use shorter action beats and clearer gestures.

Run `python scripts/lint_plan.py PLAN.json` before generation. This checks declared contracts and catches an intermediate stopped exit or mismatched direction. It cannot infer geography from pixels or certify the animatic. An intentional stationary join is valid filmmaking: declare its deliberate hold/cut rather than falsely labeling it continuous travel.

## Identity and state bible

For each entity, store stable ID, accepted reference node, visible traits, fixed material properties, allowable changes, location and current state. Keep image reference roles explicit:

- Primary current frame: layout, characters, pose, props and light that must survive.
- Canonical identity: shape, pigment map, costume and identifying detail.
- Destination composition: where the camera should arrive; must not contradict identity.
- Gesture reference: action only; do not import its chairs, background or extra bodies.
- Style reference: rendering language, not entity or room replacement.

Examples: whale skin markings are intrinsic material; blue attenuation and caustics are lighting. One taxi has a specific roof, grille, headlight and fender design, with exactly one shrimp. Crab belts belong to named fighters and do not swap with screen position. Mermaid identities, tail hues, seats, glasses and table occupancy must persist through a toast. An occluded object is absent from the image, not destroyed or teleported elsewhere.

## Motion and edit strategy

Endpoint continuity has several levels: matching composition, matching velocity, then matching acceleration and action phase. A shared last/first frame only addresses the first. Avoid choreographing every chunk as an arrival. Use a moving temporal tail where supported, and carry one action phase across the selected edit point.

Budget handles within the provider's limit. Review the useful interior of a clip; choose trim points where camera and subject motion agree. If the next clip starts from a now-discarded endpoint, trimming alone may create a jump: regenerate its input from the new selected boundary or use supported video continuation. Do not spend on a complete chain before testing a hard join.

Inspect static architecture to separate camera flow from swimming fish, particles or limbs. Optical-flow estimates can help identify speed ramps, but particle drift, occlusion, warping and zoom complicate them. Record measurements as estimates; do not label a global flow number camera velocity without a suitable scene model.

Use an EDL with source node IDs and hashes, source frame ranges [in, out), timeline frame ranges, rational frame rates, speed factors, crop/pad, extension overlap and audio policy. Normalizing fps for final delivery can duplicate/drop frames; inspect movement after conforming. Trimming removes time, so re-budget the 120-second film rather than adding arbitrary dead holds.

## Repair ladder

1. Categorize failure: identity/material; count/prop; geography; action readability; camera path; boundary velocity; duration; audio; technical file.
2. Check actual input images and reference roles first. Repair a contradictory endpoint before rewriting motion.
3. Change the smallest useful variable group. Keep other settings/seed fixed where supported and log every changed field. Label comparisons confounded when several changes are necessary.
4. Separate complex action from camera movement, shorten excessive ceremonial buildup, or simplify the destination.
5. If repeated attempts fail, change conditioning mode or shot design within the user's scope. Ask only when a required creative decision exceeds it.
6. Show the result according to project policy, record the decision, and preserve rejected versions. Do not silently improve a result the user has approved.

## Review evidence and limitations

Preflight: annotated references and shot contracts. Postflight: full-speed clip, a seam preview with approximately two seconds on each side, boundary images and metadata. Record pass/fail/unknown per category, reviewer, artifact and frame/time span. Unknown is not pass. No video playback means motion QA remains unverified; no audio playback means timbre/genre remains unverified. Do not claim that a file's duration or silence proves creative quality.
