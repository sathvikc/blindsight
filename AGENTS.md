# AGENTS.md

Guidance for AI coding agents working in this repository.

**The definitive onboarding file is [`CLAUDE.md`](CLAUDE.md)** — everything that used to live here (project summary, layout, module contract, commands, testing and code conventions, honest constraints) has moved there, corrected and expanded. Read it first. `docs/ARCHITECTURE.md` has the full developer walkthrough, and `docs/audit/` holds the production-readiness audit and roadmap.

The three rules that matter most, restated so they are never missed:

1. **Graceful degradation.** One module failing never aborts extraction; missing optional deps raise `ModuleUnavailable` and are reported `unavailable`.
2. **Honesty over coverage.** Modules measure, they don't interpret. Prefer emitting nothing to inventing structure — the thresholds in `blindsight/relations.py` each reject a named false positive; keep that bar.
3. **Relative coordinates.** All geometry is fractions of width/height (0.0–1.0), never raw pixels.

Quick commands (details and gotchas in CLAUDE.md — note there is no committed `.venv`):

```bash
python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
.venv/bin/python -m pytest tests/ -q       # ~90 tests, ~15 s
python blindsight.py image.jpg             # run without installing
```
