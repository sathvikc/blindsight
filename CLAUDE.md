# CLAUDE.md — agent onboarding for Blindsight

Definitive guidance for AI coding agents working in this repository. `AGENTS.md` points here; `docs/ARCHITECTURE.md` has the deep developer walkthrough; `docs/audit/` holds the production-readiness audit and roadmap.

## What this project is

**Blindsight** turns any image into a compact, structured **text descriptor** using classical image processing only — no AI models, no ML downloads, no GPU. The output gives a text-first LLM enough factual context (OCR text, colours, region geometry, shapes, QR/barcode values, EXIF) to answer *factual* questions about an image without paying to send the full image. It is deliberately honest about its limits: it extracts symbolic facts and defers *perceptual* questions (mood, scene meaning, identity) back to a real vision model. Benchmarked: 93% on factual questions vs 94% for full vision, at 32% fewer input tokens. `README.md` is the source of truth for behaviour and the public contract — read it first.

> Note: AGENTS.md historically referenced `vision.md` as the original spec. That file is **gitignored planning material and not present in the repo** — do not look for it or reference it; `README.md` carries the current design rationale.

## Architecture in one paragraph

`extract(path)` (in `extractor.py`) decodes the image **once** into an `ImageContext` (PIL / RGB ndarray / grayscale, `context.py`), then runs every module in `modules/__init__.py`'s `REGISTRY` in order (plus any opted-in third-party plugin modules — see `plugins.py` and the Plugins section below). Each module returns a serializable dict or raises; failures become `available=False` results and never abort extraction. After the modules, `layout.py` derives a cross-module section linking OCR text to regions (pure geometry over the two results — not a module itself). Everything is collected into an `ImageDescriptor` (`descriptor.py`) which renders via `formatter.py` to a `[Section]` text block or a JSON dict. `cli.py` wraps this in argparse.

## Layout

```
blindsight.py            # zero-install entry point: `python blindsight.py img`
blindsight/
  __init__.py            # public API: `from blindsight import extract`; __version__
  cli.py                 # argparse CLI (also the `blindsight` console script)
  extractor.py           # orchestrator: runs modules, then derives layout
  context.py             # ImageContext + ModuleUnavailable; image decoded once
  descriptor.py          # ImageDescriptor + ModuleResult data model
  formatter.py           # render descriptor -> text block or JSON
  geometry.py            # shared position (3x3 grid) / size naming helpers
  colornames.py          # RGB -> human colour name (nearest_name / accent_name)
  layout.py              # cross-module pass: links OCR text to regions
  relations.py           # region relations: bands, stacks, gradients, alignments
                         #   (all anti-hallucination thresholds live here, named)
  plugins.py             # third-party module discovery (entry-point group
                         #   "blindsight.modules"); opt-in, see Plugins below
  modules/               # one file per extractor (see contract below)
    __init__.py          # REGISTRY list = output order; load_registry() adds plugins
    stats, ocr, tables, colors, regions, structure, shapes, faces, codes, exif
tests/                   # pytest unit + property-based suites (90+ tests, ~15s)
benchmark/               # scoring + token-cost harness (no API key needed)
examples/                # sample images + committed descriptor/packet outputs
  regenerate.py          # refresh examples/results/ after output changes
.github/workflows/ci.yml # CI: pytest on py3.10 + py3.12, installs tesseract
```

Key data files:
- `benchmark/ground_truth.json` — questions + answers, tagged `factual`/`perceptual`.
- `benchmark/scorecard.csv` — **graded human evaluation data**; do not regenerate or
  edit casually, it holds the committed benchmark results.
- `examples/results/*.descriptor.txt` / `*.packet.txt` — committed fixtures; guarded by
  `tests/test_example_fixtures.py` against drift.

## The module contract

Every file in `blindsight/modules/` exposes exactly this interface — match it when
adding a module:

```python
NAME = "ocr"                        # stable machine key (JSON + --modules)
TITLE = "OCR"                       # section label in text output
def run(ctx: ImageContext) -> dict  # serializable data; may raise ModuleUnavailable
def render(data: dict) -> list[str] # data -> body lines (no [Header]; no leading indent)
```

Register the module in `modules/__init__.py`'s `REGISTRY` — **list position is the
output order**. The order is intentional: cheap factual signals first (stats, ocr,
colors), then structural, then metadata. Only built-in modules go in `REGISTRY`
directly; a module living outside this repo is a **plugin** (see below), not a
`REGISTRY` addition.

Core invariants — do not break these:

- **Graceful degradation.** A module that hits a missing dependency raises `ModuleUnavailable`; any other exception is caught by the orchestrator (`extractor.py:_run_module`). One module failing never aborts extraction — it is reported `unavailable` with a reason. Keep optional imports (`cv2`, `pytesseract`) guarded at module top with `try/except ImportError`.
- **Decode once.** Read pixels from `ctx` (`ctx.pil`, `ctx.rgb`, `ctx.gray`, `ctx.bgr`).
  Never re-open the file inside a module.
- **Relative coordinates.** Geometry is reported as fractions of width/height (0.0–1.0), never raw pixels — `ctx.rgb` may be a downscaled working copy (max side 1600) while `ctx.width/height` stay the true size. OCR coordinates come from `ctx.pil` (original size) and are normalised against `ctx.pil.size`. Relative coordinates are what let `layout.py` link modules purely by geometry.
- **Honesty over coverage.** Modules *measure*; they do not interpret. Prefer emitting nothing to inventing structure. Every threshold in `relations.py` exists to reject a specific observed false positive (each has a comment naming it); the shapes noise filter (`shapes.py`, large-blob rejection) exists for the same reason. Keep that bar.
- **Named colours.** Surface colours through `colornames` so output carries both hex
  and a human-readable name (the name is what the LLM reasons with).
- **Layout is not a module.** It is derived in `extractor.py` *after* all modules run, from the `ocr` and `regions` payloads, and inserted after the regions result. It appears only when both produced content, and cannot be selected via `--modules`. Its payload-key access is deliberately un-defensive: a renamed OCR/regions key must raise KeyError in tests, not silently drop the section (see `tests/test_layout.py:test_renamed_payload_key_fails_loudly`).

## Plugins

Third-party packages can add modules from outside this repo via a Python entry point, so the built-in `REGISTRY` never needs to grow for someone else's use case. Mechanics live in `blindsight/plugins.py`; `modules.load_registry(enable_plugins=True)` is the only thing that touches it, called from `extractor.extract(..., enable_plugins=True)`, the CLI's `--enable-plugins`, and the MCP server's `BLINDSIGHT_ENABLE_PLUGINS=1`.

- A plugin package registers under the `blindsight.modules` entry-point group and its target must satisfy the exact same module contract above (`NAME`, `TITLE`, `run`, `render`) — `plugins.discover()` validates this and skips (with a `PluginLoadWarning`, never an exception) anything that fails to import, doesn't match the contract, or reuses a `NAME` already taken by a built-in module or another plugin.
- Plugins are **opt-in everywhere**, never auto-loaded — an installed plugin package runs its code the moment discovery happens, so a caller who didn't ask for plugins must never get one silently.
- Plugins always append **after** the built-in `REGISTRY`; they cannot reorder or displace a built-in module's position, keeping the "cheap signals first" output order intact regardless of what's installed.
- When touching this system, keep the graceful-degradation invariant: one broken plugin must never prevent the built-ins, or other plugins, from running. `tests/test_plugins.py` covers discovery, validation, and the opt-in default with faked entry points (no real plugin package needed).

## Commands

There is **no committed virtualenv**; create one (or use `uv`). Requires Python 3.10–3.13 (3.14 lacks prebuilt OpenCV wheels). The system python3 on this machine is 3.9 — too old; use `uv` or an explicit newer interpreter.

```bash
# Setup, classic venv
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
brew install tesseract          # optional: enables the OCR module

# Run the tool (any of these)
python blindsight.py image.jpg
python blindsight.py image.jpg --format json
python blindsight.py image.jpg --modules ocr,colors,codes
python blindsight.py image.jpg --output descriptor.txt
python blindsight.py image.jpg --enable-plugins   # + third-party modules, if any installed
python -m blindsight image.jpg          # after pip install -e .
blindsight image.jpg                    # console script, after pip install -e .

# Tests — full suite is ~90 tests, ~15 s
.venv/bin/python -m pytest tests/ -q
# or, with no venv at all (verified working; mirrors CI deps):
uv run --python 3.12 --no-project --with "numpy>=1.24" --with "Pillow>=10.0" \
  --with opencv-python-headless --with pytesseract --with pytest \
  python -m pytest tests/ -q

# Benchmark loop (see benchmark/README.md for the full graded workflow)
python benchmark/run_benchmark.py --images examples/images \
    --out examples/results --questions examples/questions.json
python benchmark/token_savings.py --images examples/images --results examples/results
python benchmark/make_test_sheet.py     # -> test_sheet.md + blank scorecard.csv
python benchmark/score.py               # tally a graded scorecard.csv

# Regenerate committed example fixtures after an intentional output change
python examples/regenerate.py
```

Gotcha: a shell hook on this machine may rewrite bare commands to `rtk <cmd>`, which can swallow pytest's summary. Invoke `.venv/bin/python -m pytest` (or the uv command above) directly to see real results.

## Testing conventions

- `tests/test_*.py` are standard pytest unit tests against images **synthesised in-memory** — the suite needs no asset files, no network, and no Tesseract binary (OCR tests target the pure ordering logic or assert on availability handling).
- `tests/test_random_property.py` is **property-based**: each test draws random instances of an image *family* (vertical/horizontal bars, gradients, UI rows, flat/noise) from seeded RNGs (`SEEDS = range(8)`) and asserts the regions module recovers counts, orderings and proportions — and **invents no structure** on featureless images. New seeds are new images; add families rather than fixed fixtures.
- `tests/test_example_fixtures.py` re-extracts two showcase images and compares the deterministic sections (Stats, Colors, Regions, Codes) against the committed `examples/results/*.descriptor.txt`. If it fails after an intentional change, run `python examples/regenerate.py` and commit the refreshed results — never hand-edit them.
- CI installs `opencv-python-headless` (runners have no display libs) — the `cv2` API is identical, so don't rely on GUI functions (`imshow`, etc.).

## Conventions to match

- `from __future__ import annotations` at the top of every module; modern type hints
  (`list[str]`, `X | None`).
- Module-level tuned constants in `UPPER_SNAKE` with a comment explaining *why* the threshold is what it is (see `relations.py` for the exemplar). These thresholds are the heart of the "don't hallucinate" behaviour.
- Docstrings explain rationale and trade-offs, not just mechanics. The existing ones are unusually thorough; keep new code at the same altitude.
- Standard library + numpy/Pillow/OpenCV only. Adding a dependency needs a strong reason — *few* system dependencies is a design goal (e.g. QR decoding uses OpenCV's built-in detector, not zbar; palettes use Pillow's quantiser, not scikit).
- Keep `render()` output compact and deterministic; token economy is the point of the
  project.
- Version string lives in **two places**: `pyproject.toml` and `blindsight/__init__.py.__version__`. Bump both together.

## Gotchas

- **`blindsight.py` (file) vs `blindsight/` (package)** coexist at the repo root. Python resolves `import blindsight` to the package (packages win), so it works — but don't "clean up" either without checking the README usage examples and the console script.
- **OCR is optional twice over**: the `pytesseract` pip package *and* the system `tesseract` binary must both be present. Missing either yields an `unavailable` OCR section, not an error.
- `examples/make_synthetic_samples.py` needs the `qrcode` package (not in requirements.txt) and hardcodes **macOS font paths** — it only runs on macOS as-is.
- `benchmark/run_benchmark.py` and `token_savings.py` do `sys.path.insert(0, repo root)` so they run from a checkout without installation.
- `token_savings.py` uses `tiktoken` if installed, else a ~4 chars/token estimate.
- EXIF orientation is **not** auto-applied on load (`context.py`); the EXIF module
  reports it explicitly instead. Don't add auto-rotation without understanding this.
- Grayscale conversion is hand-rolled Rec. 601 luma in two places (`context.py`, `modules/regions.py:_segment`) rather than `cv2.cvtColor` — keeps behaviour identical whether or not OpenCV variants differ.

## What NOT to touch

- **`examples/results/*.txt`** — regenerate with `examples/regenerate.py`, never hand-edit; call out the change in your commit message.
- **`benchmark/scorecard.csv` and `benchmark/test_sheet.md`** — committed *graded* benchmark data behind the README's headline numbers. Regenerating blanks the grades.
- **Thresholds in `relations.py` / `shapes.py` / `colors.py`** — each rejects a named false positive. If you must tune one, the property-based suite must still pass for all seeds, and add a seed/family reproducing the case that motivated the change.
- **The honest constraints.** The tool deliberately won't interpret scene meaning or mood, identify people/brands/landmarks, read handwriting reliably, or detect non-frontal faces consistently. These are escalation signals telling the caller to fall back to a real vision model. Don't add speculative interpretation to close these "gaps".
- **`.gitignore`d planning files** (`vision.md`, `marc-algorithm.md`) — private notes, never commit them. `.claude/` is ignored *except* `CLAUDE.md`, `settings.json`, and `skills/graphify/`, which are graphify's shared project config and are tracked.
- **Module output order** in `REGISTRY` — deliberate (cheap factual signals first).

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
