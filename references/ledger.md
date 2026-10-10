# Ledger operations and recovery

Python 3.10+; no third-party Python packages. Keep each production in its own folder outside this skill. Media review additionally requires `ffmpeg` and `ffprobe` on PATH. All commands below are run with the skill folder as working directory; use absolute paths if elsewhere.

```sh
python scripts/production.py --project /path/to/film init --config /path/to/brief.json
python scripts/production.py --project /path/to/film add --spec /path/to/node.json
python scripts/production.py --project /path/to/film review plan-v1 --decision accepted --evidence 'Agent coordinator reviewed against user message XYZ'
python scripts/production.py --project /path/to/film alias current-plan plan-v1 --evidence 'Current approved plan'
python scripts/production.py --project /path/to/film job --spec /path/to/job.json
python scripts/production.py --project /path/to/film claim shot03-v1
# Submit the stored payload once using the verified provider SDK/API.
python scripts/production.py --project /path/to/film submitted shot03-v1 --provider-id RETURNED_REQUEST_ID
# Poll that ID. Save the actual output locally, then:
python scripts/production.py --project /path/to/film complete shot03-v1 --output-id clip03-v1 --file /path/to/returned.mp4
python scripts/production.py --project /path/to/film shown shot03-v1 --evidence 'Actual display/message reference'
python scripts/production.py --project /path/to/film review clip03-v1 --decision accepted --evidence 'User message XYZ plus completed continuity review'
python scripts/production.py --project /path/to/film resume
```

`claim` does not submit or print the payload. The API adapter must use the unchanged `spec.input` saved by `job`, obtained from that immutable SQLite row or a hash-verified original spec. Do not silently change the payload after claiming. A missing provider ID means the next action is recovery, not another POST. `submitted` may reconcile the same ID repeatedly; changing it is rejected. `fail ID --outcome OUTCOME --evidence ...` requires an explicit classified outcome: `abandoned` for planned work, `not_submitted` for a claimed job with provider-confirmed non-submission, or `failed`/`canceled` for a submitted job with a saved provider ID. A client timeout or unknown outcome cannot be classified as terminal. Recover and record an ID before recording provider failure. The tool checks classification/state consistency, not the authenticity of provider evidence. It is not a shortcut around ambiguous job recovery. New attempts always have new IDs.

## Node format

```json
{"id":"plan-v1","kind":"plan","parents":[],"data":{"brief":"Approved camera route","review":"Actual review findings"}}
```

For media add `"file":"/absolute/path/to/file.png"`. The tool copies it into a content-addressed store, retains its extension, and hashes the copied bytes. Every parent must already exist; IDs and edges are immutable, so cycles cannot be introduced through this API. Parent relations mean production dependency, not merely an illustrative citation. Review evidence must describe an actual decision. The tool cannot determine whether a human really approved a string.

Use separate nodes for brief, camera plan, character/prop/location references, capability snapshot, generated image/clip, QA report and EDL. Put the shot card in node data and include its accepted node ID in each job's parents. Use all actual reference dependencies, not just the immediate first frame. This lets a changed whale identity invalidate later whale shots as well as their intermediate frames.

An accepted alias replacement preserves historical originals and marks affected descendants stale. A reviewed replacement derived from the old reference and its already-reviewed dependency path stay valid. A pending job using a superseded direct reference cannot be claimed. A job already running may finish; its output is archived but flagged stale if its references changed. Do not erase it or automatically spend again.

To retain a stale result after a conscious review, create a NEW node with the same file and the new accepted parents; explain the revalidation in its data/review evidence. The stale historical node remains untouched. To reverse an earlier canonical choice, create a reviewed new version; historical supersession is not erased by moving an alias back.

## Job format

See `assets/job.example.json`. Required fields: unique ID, shot ID, endpoint, exact input object, parent IDs, authorization_source, capability_source and an ISO-date capability_checked_at. Claims reject future-dated checks or checks older than seven days (a conservative workflow heuristic, not a provider guarantee); reverify and create a new immutable job spec after a long pause. Verify again whenever a schema change is known, even within that window. Include schema/model version, reference roles, prompt version and expected output semantics as additional fields. Core code guards provenance and lifecycle, not vendor-specific schema validity. Verify the request against the selected endpoint before `claim`.

`show_before_regeneration` is a project policy. If true, completed output must be presented before acceptance or another attempt of that shot. It does not require another user confirmation after every permitted action. If false, preserve the user's actual review preferences in the brief and follow them. To change a project preference, use `policy --config FILE --evidence "Actual user decision"` with the full updated configuration, preserving unrelated fields. It appends history rather than erasing the original policy. No output means there is nothing to present. An in-flight attempt of the same shot must be reconciled before another is claimed.

## File and database behavior

The ledger uses SQLite foreign keys, immediate transactions, WAL, full synchronization, immutable job specifications, an append-only event history and hashed local assets. Concurrent claims of the same job produce one winner. A filesystem import interrupted before the database commit may leave an unreferenced content blob; it does not become an accepted asset. There is no automatic garbage collection. Check hashes on resume before using assets.

Keep `production.sqlite`, its WAL/SHM files while active, and `assets/` together. Do not back up a running database by copying only `production.sqlite`; use SQLite backup or stop writers and copy the complete project. Resume output includes local creative data and decision evidence; it is a working handoff, not a sanitized public export. The secret-field check is a guardrail, not a complete DLP system: signed URLs and prompt text can still be sensitive.

## Plan and seam checks

```sh
python scripts/lint_plan.py assets/plan.example.json
python scripts/media_review.py probe /path/to/clip.mp4
python scripts/media_review.py seam /path/to/a.mp4 /path/to/b.mp4 /path/to/new-preview.mp4 --a-out 240 --b-in 12 --seconds 2 --fps 24
```

Frame ranges are zero-based and end-exclusive. A-out=240 means the last included A frame is 239; B-in=12 begins with frame 12. The preview pads to 960×540, preserves image aspect, normalizes output fps, and omits audio. It never overwrites an existing output or source. For VFR footage the window's seconds are approximate; indexed source trims remain exact. This preview does not remove provider overlaps or duplicate endpoints automatically—choose verified cut points first. Review sound separately in the final assembly.
