# FAL-ScriptCoordinator

A continuity coordinator and reusable agent skill for multi-shot AI filmmaking. Plan connected camera movement, preserve characters and props, review transitions, and resume long productions without losing accepted assets or duplicating generation jobs.

Built around fal workflows, with capability guidance for MiniMax, Veo, Runway, Kling and Luma. It combines creative production instructions with small, provider-neutral Python tools.

## What it does

- Plans scene geography, camera routes and entry/exit states before final storyboard images.
- Tracks character identity, props, locations and allowed state changes.
- Checks declared shot handoffs for mismatched direction, speed and action state.
- Keeps immutable asset versions, hashes, dependencies and review decisions in SQLite.
- Records submission state and provider job IDs to support recovery after interruption.
- Flags affected shots when a canonical reference changes.
- Preserves configurable presentation preferences, including showing an output before regenerating it.
- Creates local seam previews for reviewing adjacent clips at normal speed.

**Scope:** the scripts do not submit paid generation requests. An agent uses the selected provider's verified API/SDK and records its work in the ledger. Visual judgment, genuine review evidence and provider capability verification remain explicit tasks. This project is independent of fal and the model providers.

## Install as an agent skill

Clone the repository into your agent's skills directory under the skill identifier `fal-scriptcoordinator`. For a default Codex skills directory:

```sh
git clone https://github.com/latentwill/FAL-ScriptCoordinator.git "$HOME/.codex/skills/fal-scriptcoordinator"
```

Invoke it with a request such as:

> Use $fal-scriptcoordinator to plan a two-minute film with a continuous camera journey. Build the character and prop registry, test the difficult transitions, and preserve accepted shots across revisions.

The entry point is [SKILL.md](SKILL.md). The display name is **FAL-ScriptCoordinator**; the machine-readable skill identifier is **fal-scriptcoordinator**.

## Use the tools directly

Requirements: Python 3.10+ and its standard library. Video probing and seam previews additionally require `ffmpeg` and `ffprobe` on PATH. No API key is needed for these offline tools.

Run from the repository root:

```sh
# Review the example camera/shot contracts.
python3 scripts/lint_plan.py assets/plan.example.json

# Keep production data outside this reusable skill checkout.
# Copy and customize the brief for your project first.
python3 scripts/production.py --project ../my-film init --config assets/brief.example.json
python3 scripts/production.py --project ../my-film resume

# Inspect actual footage and make a new preview file.
python3 scripts/media_review.py probe /path/to/clip.mp4
python3 scripts/media_review.py seam /path/to/a.mp4 /path/to/b.mp4 /path/to/seam.mp4 --seconds 2 --fps 24
```

See [ledger operations](references/ledger.md) for registering assets, recording API jobs, reviewing outputs and recovering interrupted work. Example job URLs and decision references must be replaced with real authorized inputs before live production.

## Workflow

**Brief → asset bible and scene map → camera animatic → shot contracts → compatible references → pilot joins → generation → continuity review → frame-based edit.**

A matching last/first frame preserves a composition, not necessarily momentum. For sustained travel, consider supported video continuation and review velocity/action phase at the seam. An exact end image can help composition or damage continuity if it contradicts the starting identity or geography.

## Documentation

- [Skill instructions](SKILL.md)
- [Production and continuity protocol](references/production-protocol.md)
- [Provider capabilities and source links](references/providers.md)
- [Ledger commands and recovery](references/ledger.md)
- [Underwater-film case study](references/case-study.md)
- [Validation and limitations](references/validation.md)

Provider documentation changes. Capability notes are dated references, not permanent promises; verify the selected endpoint before a generation session.

## Development

```sh
python3 -m unittest discover -s scripts -p 'test_*.py' -v
python3 scripts/lint_plan.py assets/plan.example.json
python3 -m compileall -q scripts
```

The tests cover state transitions, recovery, concurrent claims, immutable assets, dependency staleness, presentation policy, capability-check expiry, and declared camera handoffs. They do not certify artistic quality or model compliance. GitHub Actions runs the offline checks on Python 3.10 and 3.12.

Keep credentials, provider receipts, project databases, production media and private conversation records in the production workspace rather than this repository. Public filmmaking lessons are included without the original request or conversation audit files.
