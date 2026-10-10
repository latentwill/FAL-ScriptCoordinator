# Provider capability routing

Research checked 2026-10-10. These are endpoint contracts, not quality guarantees. Before live generation, recheck official docs and record endpoint/model ID, API version, date, source URL, accepted input roles, durations, frame rates, ratios, audio controls, output semantics, costs if available, polling/recovery and storage expiry. Do not transplant UI capabilities into an API or one provider's limits into another.

| Integration | Useful documented control | Production implication |
|---|---|---|
| fal MiniMax H3 Max image-to-video | Optional first and last images; actual duration may exceed requested duration | Useful for compatible composition constraints; still inputs do not encode preceding velocity. [API](https://fal.ai/models/minimax/h3-max/image-to-video/api) |
| fal MiniMax H3 Max extend-video | Video input, next-beat prompt, combined or continuation output | Input is documented at 1.625–60 s and up to 50 MB. `duration` requests new footage. `extended` includes the source; `continuation` begins with a 1.625 s source repeat, with frame-rounding caveats. Align actual frames instead of appending blindly. [API](https://fal.ai/models/minimax/h3-max/extend-video/api) |
| Google Veo 3.1, Gemini API | First/last frames, references and extension on supported variants | Extension accepts Veo-generated videos; documented output combines source and extension. Verify the selected variant and mode rather than assuming arbitrary footage is supported. [Guide](https://ai.google.dev/gemini-api/docs/veo) |
| Runway developer API | Model-specific image/video conditioning and task IDs | Verify the particular model's controls. Archive successful output promptly: documented URLs expire after 24–48 hours. [Inputs](https://docs.dev.runwayml.com/assets/inputs/), [outputs](https://docs.dev.runwayml.com/assets/outputs/) |
| Kling 2.6 Pro via fal | Start image, optional end image; 5/10-second options on this endpoint | This is a versioned example, not a claim that 2.6 is the newest Kling. No extension overlap should be inferred from its keyframe support. [API](https://fal.ai/models/fal-ai/kling-video/v2.6/pro/image-to-video/api) |
| Luma Dream Machine API | Keyframes and extension using prior generated clips | Verify input restrictions and returned-file structure; do not assume MiniMax's overlap convention. [Video API](https://docs.lumalabs.ai/docs/video-generation) |

The recommendation to prefer video continuation for inherited motion is an inference about temporal conditioning, not a guarantee that an extension will preserve identity or velocity. Long clips can accumulate drift. Review periodically and re-anchor at motivated boundaries.

## Adapter contract

The bundled tools are provider-neutral bookkeeping and review tools. They do not implement live clients. For the chosen provider, use its maintained SDK or documented API and persist:

- Immutable request payload, seed, optional prompt expansion settings and the expanded prompt returned by the provider.
- Local immutable references and their roles; hosted URLs and expiry locally when needed. Credentials come from the environment, never the ledger.
- Submission claim before POST; request/operation/task ID immediately after it; status retrieval and result location.
- Requested duration vs measured duration, returned fps and frames, source overlap or combined-file semantics, source/result hashes, audio streams and final edit decision.

A client timeout does not establish that generation failed. Recover the job ID and poll when possible. Only retry a paid POST when provider evidence establishes non-submission, or create an explicitly authorized new attempt after acknowledging the unresolved original. The supplied ledger deliberately blocks automatic duplicate submission; it cannot offer network-level exactly-once delivery without provider idempotency.

For visual-only production, use a documented audio-disable setting if supported. Silence in a prompt is not an API guarantee. If unavoidable audio is returned, remove it in an explicit derived deliverable and verify zero audio streams. Attach custom music only within the user's authorized scope.

## Lessons from other skills

Two Luna research passes evaluated public workflows and official platform documentation. Community instructions are evidence of workflow design, not proof of vendor capability or rendering quality. The implementation here is original; no third-party source code was copied.

- [AIGC Film Studio](https://github.com/ifeihong/aigc-film-studio/blob/main/SKILL.md): adopted the asset registry, scene geography, continuity preflight and versioned repair records. Its broad model claims and numerical quality thresholds are not treated as verified facts.
- [visual-skills](https://github.com/smixs/visual-skills/blob/main/video/SKILL.md): adopted motivated camera movement, explicit spatial relationships and concise shot cards. Added executable boundary checks and durable state beyond prompt instructions.
- [reel-builder](https://github.com/Mikefluff/skills/blob/main/skills/reel-builder/SKILL.md): adopted component manifests and resume-aware asynchronous work. Its hard-cut reel assembly does not solve continuous camera travel; this package adds transition contracts and seam review.
- [Remotion's official skill](https://github.com/remotion-dev/skills/blob/main/skills/remotion-create/SKILL.md): useful downstream for editable, frame-based composition and previews. It does not repair inconsistent generated footage; keep it as an optional finishing layer.
- [video-director](https://github.com/event4u-app/agent-config/blob/main/dist/agent-src/skills/video-director/SKILL.md): adopted separating directorial intent from provider formatting. Avoided imposing one long fixed prompt format on every model.
