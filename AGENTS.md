# AGENTS.md

Guidance for AI coding agents working in this repository.

**The definitive onboarding file is [`CLAUDE.md`](CLAUDE.md)** — everything that used to live here (project summary, layout, module contract, commands, testing and code conventions, honest constraints) has moved there, corrected and expanded. Read it first. `docs/ARCHITECTURE.md` has the full developer walkthrough, and `docs/audit/` holds the production-readiness audit and roadmap.

The three rules that matter most, restated so they are never missed:

1. **Graceful degradation.** One module failing never aborts extraction; missing optional deps raise `ModuleUnavailable` and are reported `unavailable`. 2. **Honesty over coverage.** Modules measure, they don't interpret. Prefer emitting nothing to inventing structure — the thresholds in `blindsight/relations.py` each reject a named false positive; keep that bar. 3. **Relative coordinates.** All geometry is fractions of width/height (0.0–1.0), never raw pixels.

Quick commands (details and gotchas in CLAUDE.md — note there is no committed `.venv`):

```bash
python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
.venv/bin/python -m pytest tests/ -q       # ~90 tests, ~15 s
python blindsight.py image.jpg             # run without installing
```

## Layout

```
blindsight.py            # zero-install entry point: `python blindsight.py img`
blindsight/
  __init__.py            # public API: `from blindsight import extract`
  cli.py                 # argparse CLI (also the `blindsight` console script)
  mcp_server.py          # MCP stdio server (stdlib JSON-RPC, no SDK) — gives
                         #   text-only models tool access to the descriptors
  extractor.py           # orchestrator: runs modules, then derives layout
  context.py             # ImageContext: image decoded once into PIL/RGB/gray
  descriptor.py          # ImageDescriptor + ModuleResult data model
  formatter.py           # render descriptor -> text block or JSON
  geometry.py            # shared position/size naming helpers
  colornames.py          # RGB -> human colour name (nearest_name / accent_name)
  layout.py              # cross-module pass: links OCR text to regions
  modules/               # one file per extractor (see contract below)
    __init__.py          # REGISTRY list = output order
    stats, ocr, tables, colors, regions, structure, shapes, faces, codes, exif
tests/                   # pytest unit + property-based suites
benchmark/               # scoring harness (no API key needed)
examples/                # sample images + committed descriptor/packet outputs
.github/workflows/ci.yml # CI: pytest on py3.10 + py3.12, installs tesseract
```

## The module contract

Every file in `blindsight/modules/` exposes exactly this interface — match it when adding a module:

```python
NAME = "ocr"                       # stable machine key (JSON + --modules)
TITLE = "OCR"                      # section label in text output
def run(ctx: ImageContext) -> dict # serializable data; may raise ModuleUnavailable
def render(data: dict) -> list[str]# data -> body lines (no [Header]; no leading indent)
```

Register the module in `modules/__init__.py`'s `REGISTRY` — **list position is the output order**. The order is intentional: cheap factual signals first (stats, ocr, tables, colors), then structural, then metadata.

Core invariants — do not break these:

- **Graceful degradation.** A module that hits a missing dependency raises
`ModuleUnavailable`; any other exception is caught by the orchestrator. One module failing never aborts extraction — it is reported `unavailable` with a reason. Keep optional imports (`cv2`, `pytesseract`) guarded.
- **Decode once.** Read pixels from `ctx` (`ctx.pil`, `ctx.rgb`, `ctx.gray`,
`ctx.bgr`). Never re-open the file inside a module.
- **Relative coordinates.** Geometry is reported as fractions of width/height
(0.0–1.0), never raw pixels — `ctx.rgb` may be a downscaled working copy while `ctx.width/height` stay the true size. This is what lets `layout.py` link modules purely by geometry.
- **Honesty over coverage.** Modules *measure*; they do not interpret. Prefer
emitting nothing to inventing structure. The regions filters and the shapes noise filter exist specifically to avoid hallucinated facts — keep that bar.
- **Named colours.** Surface colours through `colornames` so output carries both
hex and a human-readable name (the name is what the LLM reasons with).

`layout` is special: it is **not** a module. It is derived in `extractor.py`
*after* all modules run, from the `ocr` and `regions` results, so it never affects module independence. It appears only when both produced content.

## Commands

```bash
# Setup (Python 3.10–3.13; 3.14 lacks OpenCV wheels)
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
brew install tesseract          # optional: enables the OCR module

# Run the tool
python blindsight.py image.jpg
python blindsight.py image.jpg --format json
python blindsight.py image.jpg --modules ocr,colors,codes
python blindsight.py image.jpg --output descriptor.txt

# Run the MCP server (stdio transport; wire it into any MCP client)
python -m blindsight.mcp_server

# Tests (this repo's venv is at .venv)
.venv/bin/python -m pytest tests/ -q

# Benchmark loop (see benchmark/README.md)
python benchmark/run_benchmark.py --images ./images --out benchmark/out --questions benchmark/ground_truth.json
```

Note: a shell hook may rewrite bare commands to `rtk <cmd>`, which can swallow pytest's summary. Invoke `.venv/bin/python -m pytest` directly to see real results.

## Testing conventions

- `tests/test_*.py` are standard pytest unit tests against synthesized images.
- Tests that need Tesseract to *read* synthetic text draw it with the DejaVu
fonts (`/usr/share/fonts/truetype/dejavu/…`, installed in CI) and skip when Tesseract is missing. `tests/test_mcp_server.py` drives the MCP server with real newline-delimited JSON-RPC frames through `serve()` — add protocol tests there, not against internal handlers.
- `tests/test_random_property.py` is **property-based**: each test draws random
instances of an image *family* (vertical/horizontal bars, gradients, UI rows, flat/noise) from seeded RNGs and asserts the regions module recovers counts, orderings and proportions — and **invents no structure** on featureless images. New seeds are new images, so add families rather than fixed fixtures.
- CI installs `opencv-python-headless` (no display libs on runners) — the `cv2`
API is identical, so don't rely on GUI functions.
- When you change extractor output, the committed files under
`examples/results/*.descriptor.txt` and `*.packet.txt` will drift. Regenerate them deliberately (don't hand-edit) and call out the change.

## Conventions to match

- `from __future__ import annotations` at the top of every module; modern type
hints (`list[str]`, `X | None`).
- Module-level tuned constants are named in `UPPER_SNAKE` with a comment
explaining *why* the threshold is what it is. Keep that habit — these thresholds are the heart of the "don't hallucinate" behaviour.
- Docstrings explain rationale and trade-offs, not just mechanics. The existing
ones are unusually thorough; keep new code at the same altitude.
- Standard library + numpy/Pillow/OpenCV only. Adding a dependency needs a
strong reason — a design goal is *few* system dependencies. This extends to the MCP server: it speaks the protocol's stdio subset directly on the standard library rather than pulling in an SDK. OpenCV is pinned `<5` (5.0 removes `cv2.CascadeClassifier` and changes APIs the modules use).
- Keep `render()` output compact and deterministic; token economy is the point
of the project.

## Honest constraints (don't "fix" these — they're intentional)

The tool deliberately won't interpret scene meaning/mood, identify specific people/brands/landmarks, read handwriting reliably, or detect non-frontal faces. These are escalation signals telling the caller to fall back to a real vision model. Don't add speculative interpretation to close these "gaps".
