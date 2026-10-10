# Validation record

Checked 2026-10-10. The reusable skill is published as FAL-ScriptCoordinator. Installation is separate from repository publication.

- Skill-creator structural validation: passed.
- Python compilation: passed for all bundled scripts.
- Offline unit suite: **20 tests passed**. Covers interrupted submission/reopen, repeat claim rejection, concurrent single-winner claims, provider-ID reconciliation, show-before-regeneration, immutable reviews, dependency staleness, accepting a reviewed replacement derived from the old asset, preserving stale paid outputs, ancestor hash tampering, duplicate-ID rollback, missing/self dependencies, credential-field rejection, in-flight sibling blocking, dated capability checks, terminal-outcome classification, policy updates, required accepted plans, superseded-reference rejection, declared motion-state mismatches, unplanned stops, invalid durations and rational frame ranges.
- CLI smoke: created a separate example project and resumed its durable state successfully.
- Declared-plan linter: the bundled example passed; negative direction/stop/duration scenarios are covered by the suite.
- Media smoke: generated a 2-second, 48-frame, 24-fps, 960×540 silent seam preview from the existing accepted throw/reveal and cheers clips. Original files were not overwritten. This validates the media tool's execution, not the artistic smoothness of that seam.
- Independent Luna review identified ambiguous failure classification and aging provider capability checks; both received explicit controls and regression tests. The reviewer ran the earlier 15-test suite; the final expanded 20-test suite was run by the implementing agent.
- No paid generation, provider POST, secret disclosure, or changes to the film were needed for these tests.

## Reproduce

```sh
python -m unittest discover -s scripts -p 'test_*.py' -v
python scripts/lint_plan.py assets/plan.example.json
```

Python 3.10+ and standard library are sufficient for ledger/lint/tests. `ffmpeg` and `ffprobe` are additionally required for real media previews.

## Deliberate boundaries

The package enforces bookkeeping, declared contracts and evidence requirements. It cannot authenticate a claimed user decision, prove a provider receipt is genuine, interpret every visual continuity defect, or guarantee model compliance. Its seven-day capability-check window is an expiry heuristic, not a promise schemas remain stable that long. Keep verification and visual/audio review explicit.

Live generation uses separately verified provider APIs/SDKs. There are no bundled live multi-provider clients and no automated visual-quality model. The SQLite ledger prevents duplicate local claims, but network-level exactly-once submission depends on provider support and correct recovery. Project databases and private media stay outside this reusable package.
