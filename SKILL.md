---
name: fal-scriptcoordinator
description: Plan, generate, review, revise, and assemble multi-shot AI films across long conversations. Use for cinematic image-to-video, first/last-frame workflows, video extension, camera continuity, character/prop consistency, or resuming generative productions on fal/MiniMax, Veo, Runway, Kling, or Luma. Includes a durable offline production ledger and seam-review tools; live generation uses the chosen provider's verified API.
---

# FAL-ScriptCoordinator

Produce a film as connected action and camera paths, not a slideshow of attractive images. Preserve the user's approved creative choices and show results as requested. A still matches appearance; a video tail also contains motion. Neither guarantees continuity.

## Start or resume

1. Locate the existing project, assets, request logs and latest user decisions. Do not restart because the conversation was compacted. If a ledger exists, run `python scripts/production.py --project PROJECT resume`; reconcile submitted jobs with the provider before creating any new attempt. Treat `submitting` without a job ID as an ambiguous paid submission, never as permission to resubmit.
2. Preserve existing approvals, scope, budget and review preferences. For a new project, copy `assets/brief.example.json`, replace its example values, then run `init --config FILE`. Continue already authorized work; ask only for missing information that prevents it. Do not invent a budget or force approval at every shot.
3. Read [production protocol](references/production-protocol.md). For generation, read [provider adapters](references/providers.md), verify the exact endpoint's current schema, and store a capability snapshot. For CLI commands and recovery, read [ledger](references/ledger.md). For lessons from the underwater film, read [case study](references/case-study.md).
4. Keep user media and project credentials out of the reusable skill. Use environment credentials and authorized uploads only. Never print secrets or bundle live signed URLs into public exports. Provider output URLs are not permanent assets.

## Plan before making the final storyboard

- Lock the narrative beats, runtime, aspect ratio, delivery frame rate, emotional pace and sound policy. Separate intended editorial duration from requested generation duration and measured returned duration.
- Build a canonical asset registry: characters, proportions, surface markings, props, wardrobe, locations, lighting, reference roles and allowed state changes. Style references and LoRAs do not establish identity.
- Draw simple scene geography and a camera path before generating hero stills. Locate entrances, landmarks, vehicles, subjects and occluders. State what stays behind the camera. Use conceptual coordinates unless scale is actually known.
- Build shot cards using `assets/shot.example.json`. For each boundary record framing, camera heading/height, screen direction, movement speed class, subject pose/action phase, lens feel, visible objects and light direction. Connect exit state to next entry state. Treat plans as intent, not measured optical facts. Run `python scripts/lint_plan.py PLAN.json` to check declared joins before submission.
- Declare the join: continuous travel, match-on-action cut, occlusion, cutaway, deliberate hard cut, or intentional hold. Do not promise a continuous take between physically incompatible compositions. Favor motivated cuts when permitted; if the user wants continuous movement, redesign the route and bridges.
- Make a rough animatic and test the hardest two or three joins early. Approve the path before expensive detailed generation. Preserve one primary camera move per beat; when complex action conflicts with travel, sequence them.

## Coordinator pass before every submission

Perform a distinct continuity review, even when one agent performs all roles. Use the registry, actual accepted frame/tail and adjacent shot cards, not memory alone. Check:

1. Identity/material: anatomy, silhouettes, fixed pigment patches, costume, scale, count.
2. Props/state: which hand/claw holds what, glass counts, vehicle details, grip/landing phase.
3. Geography: doorway side, room adjacency, camera axis, subjects that must stay offscreen.
4. Motion: incoming/outgoing direction and speed; no unplanned arrival, stop, re-acceleration or camera reversal.
5. Inputs: no stale asset, conflicting end frame or irrelevant reference that reintroduces rejected content.
6. Timing/audio: readable action, generation handles, no accidental soundtrack.

Resolve contradictions in the images or shot plan before spending on motion. Log the findings with evidence. Another agent is optional and must be authorized under the host's delegation policy; the role does not require spawning one.

## Choose conditioning deliberately

- **Identity-critical opening:** use the accepted actual frame, plus role-specific canonical references if supported.
- **Precise destination:** use first+last frames only after checking geometry, identity and action-state compatibility. An end frame is a strong constraint, not decoration.
- **Uninterrupted travel:** prefer a supported video-extension/continuation input carrying recent motion. Describe the next beat. Do not assume image-to-video reconstructs incoming velocity from a still.
- **Bad destination:** edit that image first using the current accepted state as primary reference; use old artwork only for the intended gesture/design. Do not ask the video model to repair contradictory chairs, bodies or pigment maps while also moving the camera.
- **Intentional final hold:** stop once at the true ending while environmental motion continues. Do not apply this ending behavior to intermediate joins.

A moving-shot prompt should specify the observable action, one camera path, inherited motion, fixed identity, permitted illumination changes, and the exit state. Avoid asking each clip to form a complete dramatic beginning and ending. Example:

> Already tracking right at the incoming pace. The whale continues its existing downstroke while the camera descends beside it. Its pigment patches and silhouette remain fixed; only blue-green illumination changes with depth. City towers rise into view through parallax. Maintain the rightward descent through the final usable frames; the shot continues beyond the boundary without settling or a new reveal pose.

Use provider-native controls where available. Prompt wording is guidance, not a guarantee. Minimize contradictory negative lists; verify whether a negative-prompt field exists before sending one.

## Generate, inspect, present, decide

1. Persist the exact payload, model/endpoint, source assets, seed, capability source, authorization scope and intended duration with `job`. Claim once with `claim` immediately before the provider submission. Save the returned ID with `submitted` immediately afterward. The bundled ledger does not make paid API calls.
2. Poll the saved ID with bounded backoff. On interruption, resume polling. On an ambiguous submission, recover through provider history/support or document evidence of non-submission; never automatically repeat the POST. Download outputs to durable project storage when authorized for production, not to bypass media display restrictions.
3. Register the returned file with `complete`, probe actual media, and inspect it. Provider success means a file exists; it does not mean the film works. Keep original generations immutable.
4. Watch the clip and a seam preview at normal speed, then inspect boundary frames. Review appearance AND velocity/acceleration, action phase, geometry, counts and soundtrack. If the environment cannot play/listen, state that limitation and obtain human review; metadata or a contact sheet is not a motion/audio review.
5. Present before creative regeneration when that is the project's policy. Record `shown` with a real message/display reference. Only accept with an actual decision source and review findings. “Next shot” may be approval when session context clearly supports it; do not invent an approval.
6. For a redo, log observed failure → smallest structural change → comparison criteria → result. Hold seed/model/other parameters constant where supported for a useful comparison, but do not promise determinism. After repeated failures, simplify action, revise geometry or choose another supported conditioning mode rather than adding more adjectives.
7. Accept the new asset and update its canonical alias. The ledger flags descendants of the superseded asset as stale. Review them and create new versions where needed; do not silently regenerate already approved downstream work.

## Edit for continuous motion

- Budget usable footage plus optional head/tail handles within model limits; 0.5–1.0 seconds each is a starting heuristic. Inspect the actual motion to choose edit points. Do not trim blindly.
- Join at compatible moving phases, not automatically at each generated file's first and last frame. If trimming changes the handoff, derive the next generation from the selected outgoing frame/tail, not the discarded endpoint.
- For extensions, verify whether output is combined source+extension or continuation-with-overlap. Align the returned overlap in frames; never append the source twice. H3's overlap rule is endpoint-specific (see provider reference).
- Use `scripts/media_review.py seam` for a local boundary preview and exact rational duration information. It does not prove continuity or decide edit points. Preserve aspect ratio with pad/crop decisions, never unnoticed stretching.
- Use retiming only for measured residual pacing issues. A stationary pause remains stationary when sped up. Optical flow and dissolves can create warping, double limbs or ghosting; inspect before keeping them. Repeated start/stop choreography should be regenerated or reframed.
- Keep a frame-based edit decision list including source hashes, trim-in/out, speed changes, extension overlap removal and audio edits. Validate total runtime from the assembled file; then watch the whole film, not only isolated shots.

## Long-conversation handoff

At every completed or interrupted stage, persist decisions and run `resume`. The ledger retains immutable assets and jobs, accepted aliases, dependency staleness, presentation evidence, review decisions and unresolved submissions. Keep the brief, shot cards, capability snapshots and edit list as versioned nodes, not just chat text. Never substitute a remembered storyboard frame for the current accepted output. Provide the next concrete action and remaining uncertainty in the user update.

## Included tools and limits

`production.py` uses Python standard-library SQLite transactions and content hashes. `media_review.py` requires `ffmpeg` and `ffprobe`; it only reads sources and writes requested review artifacts. See [ledger](references/ledger.md) for commands and [validation](references/validation.md) for tested behavior. The tools enforce state/provenance; visual continuity, artistic quality and provider capability verification remain explicit review tasks. No live multi-provider SDK clients or automatic visual judge are bundled.
