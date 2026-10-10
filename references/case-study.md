# Case study: a continuous underwater short

This public summary describes production lessons from a two-minute illustrated film: an underwater whale descends toward a city, a shrimp drives a taxi to a crab dojo, a throw leads into a mermaid lounge, and the camera pulls back for a city finale. Private conversations, provider request identifiers, account-specific model assets and original footage are not included.

## Findings from revisions

| Observed failure | Useful intervention | General lesson |
|---|---|---|
| Whale changes pigment during descent | Remove a conflicting destination image; edit its whale to match the accepted identity; distinguish surface markings from underwater illumination. | Resolve disagreement between input images before adding motion instructions. |
| Taxi changes between compositions | Use the accepted vehicle as a visual identity reference when editing the new frame. | A shared style LoRA does not lock an individual prop or character. |
| Dojo arrival loses architectural detail | Put lanterns, ornament and carved structure into the actual destination image, then propagate that design to the interior. | Production design must exist in the conditioning images. |
| A fight contains too much setup | Remove the introductory bow and begin with engagement; shorten the beat. | Pacing is choreography and duration, not just intensity adjectives. |
| Fighters reappear after the camera passes them | Remove distant fighters from the target; place an opaque partition between rooms; finish the throw before the camera travels. | Target geography must agree with the camera path. Sequence competing action demands. |
| A toast changes seating or character arrangement | Make the accepted current lounge the primary reference; use the old storyboard only for the desired gesture. | Reference roles prevent an action example from replacing the whole scene. |
| A city finale repeats the same vehicle and reverses direction | Remove overly specific location/vehicle references; specify diverse traffic; separate outward travel from the final hold. | Conditioning can unintentionally import content. An intentional terminal stop should not become every shot's ending. |

Prompts, references and seeds sometimes changed together. These are production observations, not controlled comparisons proving that one isolated parameter caused an improvement.

## Camera planning

The finished stills were initially composed independently. A later written camera plan included useful bridges and handoff rules, but those rules were not consistently enforced during generation and assembly. Planning must start before final stills: build scene geography, a camera route, a timed animatic and shared entry/exit states. Test difficult joins before making the full sequence.

## Why matching frames was insufficient

A last-frame image contains appearance and pose, but no preceding camera velocity or action trajectory. Independent image-to-video segments can each develop their own acceleration and deceleration. Instructions to settle into a final composition, followed by whole-clip concatenation, reinforced the stop/start feeling.

Use supported temporal continuation where appropriate, maintain motion through intermediate boundaries, generate editing handles within provider limits, and inspect normal-speed seam previews. If the selected edit point changes, update the next input accordingly. Requested duration is not measured duration. Provider overlap or combined-output behavior must also be handled explicitly.

## Continuity coordinator

A separate review pass compares the canonical identity/prop/location registry, the last accepted clip, the proposed inputs and the next planned shot. It tracks fixed material properties separately from lighting; counts and ownership of props; occluded objects; room adjacency; and action/motion state.

Persistent records matter more than the role's title. Accepted assets, review evidence, generation requests, pending jobs and dependency changes must survive conversation resets. A revised canonical asset should flag affected downstream work, while preserving the historical versions and already-paid results.

## Audio and presentation

Track requested, returned and edited durations separately. Do not infer actual tempo from a music prompt; verify loop points by listening and measurement. Metadata checks do not establish musical style or smooth movement. Preserve a project's preference to present each output before regenerating it, and record real user decisions instead of assuming approval from API success.
