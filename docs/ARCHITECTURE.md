# Blindsight — Architecture

Developer documentation. Target: a new developer productive in under an hour. For agent-oriented quick reference see [`CLAUDE.md`](../CLAUDE.md); for user-facing behaviour and rationale see [`README.md`](../README.md) (the public contract).

## 1. The problem it solves

Sending an image to a multimodal LLM is accurate but expensive (hundreds to thousands of input tokens per image), and text-only models cannot accept images at all. Yet a large share of real questions about images are **factual, not perceptual**: *what does this screenshot say?*, *what URL is in this QR code?*, *which bar is tallest?*, *what are the brand colours?* Those answers live in symbolic facts that plain text carries perfectly.

Blindsight extracts exactly those facts with **classical image processing only** (no ML models, no GPU, no model API) and emits a compact, deterministic text descriptor a language model can reason over. The design intent is a *cheap first pass*: try the descriptor; fall back to the real image only when the question is genuinely perceptual. The tool is deliberately honest — it measures, it never interprets, and it prefers emitting nothing to inventing structure ("anti-hallucination" is a first-class design constraint, encoded as named thresholds).

Measured on the 11 showcase images / 36 questions (single graded pass, GPT-5 mini): **factual 93% (descriptor) vs 94% (vision)** at **32% fewer input tokens**; perceptual 11% vs 100% — the low perceptual score is the honest "send the image" signal, not a failure.

## 2. System architecture

```
                       ┌─────────────────────────────────────────────┐
   CLI                 │                 extractor.extract()          │
   blindsight.py ──┐   │                                             │
   __main__.py ────┼──▶│  context.load_context(path)                 │
   cli.main() ─────┘   │    │  decode ONCE → ImageContext             │
                       │    │  (pil original, rgb ≤1600px, gray,     │
   Library             │    │   true width/height)                   │
   from blindsight     │    ▼                                        │
     import extract ──▶│  for module in modules.REGISTRY:  (in order)│
                       │    stats → ocr → colors → regions →         │
                       │    structure → shapes → faces → codes → exif│
                       │    │    each: run(ctx) → dict               │
                       │    │    ModuleUnavailable / Exception       │
                       │    │      → ModuleResult(available=False)   │
                       │    ▼                                        │
                       │  layout.build(results)   (derived pass:     │
                       │    OCR line/word boxes × region bboxes —    │
                       │    pure relative geometry, no pixels;       │
                       │    inserted after the regions result)       │
                       │    ▼                                        │
                       │  ImageDescriptor(source, w, h, results[])   │
                       └───────────────┬─────────────────────────────┘
                                       │
                          ┌────────────┴────────────┐
                          ▼                         ▼
                 formatter.to_text()        formatter.to_json()
                 "[Stats]…[EXIF]" block     {"modules": {name: {...}}}
```

Three load-bearing decisions:

1. **Decode once, share everywhere.** `ImageContext` holds every representation a module might need (PIL image with EXIF, RGB ndarray, grayscale, BGR view). Modules never re-open the file. Large images are downscaled to max side 1600 for per-pixel work while `ctx.width/height` keep the true dimensions.
2. **Modules are independent and fallible.** The orchestrator wraps every module call; `ModuleUnavailable` (missing optional dep) and any other exception both become an `available=False` result with a note. A broken module degrades one section, never the descriptor.
3. **All geometry is relative** (fractions 0.0–1.0 of image extent). This is what lets `layout.py` link OCR text to regions with pure arithmetic even though OCR ran on the original-size image and regions ran on a ≤256px thumbnail.

The diagram above shows the built-in path (`modules.REGISTRY`); when a
caller opts into `enable_plugins=True`, `extract()` iterates
`modules.load_registry(enable_plugins=True)` instead, which is
`REGISTRY` with validated third-party modules appended after it (§3,
`plugins.py`) — the loop body is otherwise identical, including the same
per-module `ModuleUnavailable`/`Exception` handling.

## 3. Module-by-module walkthrough

### Core plumbing (`blindsight/`)

| File | Role | Notes |
|---|---|---|
| `context.py` | `ImageContext` dataclass + `load_context()` + `ModuleUnavailable` | Rec. 601 luma grayscale; EXIF orientation deliberately *not* auto-applied (the exif module reports it instead) |
| `extractor.py` | `extract(path, modules=None)` orchestrator | Runs REGISTRY subset, catches per-module failures, splices in the derived layout section after regions |
| `descriptor.py` | `ModuleResult`, `ImageDescriptor` | Each result carries its own `render` callable, keeping presentation next to the logic that produced the data. `descriptor.get(name)` looks up a section |
| `formatter.py` | `to_text()` / `to_json()` | Text: `=== IMAGE DESCRIPTOR ===` header, `source/size/modules` lines, one `[Section]` per result. JSON mirrors the same structure keyed by module name |
| `geometry.py` | `region_name(cx, cy, w, h)` → 3×3 grid cell name ("top-center", middle-center → "center"); `size_bucket(area, image_area)` → small (<2%) / medium (<15%) / large | Shared vocabulary so every module names positions identically |
| `colornames.py` | `nearest_name` (28-anchor curated palette, RGB nearest-neighbour), `accent_name` (hue-bucket naming robust to low saturation), `to_hex` | Every colour ships as *name + hex*; the name is what the LLM reasons with |
| `relations.py` | Pure functions over region dicts: `bands_stacks_gradients`, `baseline_groups`, `left_edge_groups` | **The anti-hallucination heart.** Every `UPPER_SNAKE` threshold has a comment naming the false positive it rejects (e.g. `_MIN_GROUP = 3`: "two edges coincide by chance constantly; three sharing an edge is structure") |
| `layout.py` | `build(results)` — derived cross-module section | Links each prominent OCR line to the *smallest* containing non-background region; labels baseline elements (bars) with the OCR word directly below them ("blue=Q1"). Accesses payload keys directly so a renamed key fails loudly (KeyError) instead of silently dropping the section |
| `plugins.py` | `discover(reserved_names=...)` — third-party module discovery over the `blindsight.modules` `importlib.metadata` entry-point group | Validates each entry point against the module contract, skips (with `PluginLoadWarning`) anything that fails to import, doesn't match the contract, or collides on `NAME`. Never raises — one bad plugin can't take down discovery of the rest |
| `cli.py` | argparse CLI: `image`, `-o/--output`, `-f/--format text|json`, `-m/--modules`, `--enable-plugins`, `--version` | Exit 2 for unknown module names, 1 for load errors, 0 otherwise |

### Extraction modules (`blindsight/modules/`) — the contract

```python
NAME  = "colors"                     # machine key (JSON key, --modules value)
TITLE = "Colors"                     # [Section] label
def run(ctx: ImageContext) -> dict   # serializable payload; may raise ModuleUnavailable
def render(data: dict) -> list[str]  # payload -> body lines (no header, no indent)
```

`REGISTRY` order in `modules/__init__.py` **is** the output order: cheap factual signals first (stats, ocr, colors), then structural, then metadata.

Third-party packages can satisfy this same contract from outside the repo and register under the `blindsight.modules` entry-point group (`plugins.py`); `modules.load_registry(enable_plugins=True)` appends any discovered, validated ones after `REGISTRY`, leaving the built-in order untouched. See §4 for the `extract()` parameter and the [README's Plugins section](../README.md#plugins) for the package-author-facing walkthrough.

| Module | Technique | Output highlights |
|---|---|---|
| `stats` | numpy means/stds on gray + RGB | resolution, orientation, aspect ratio (gcd-reduced), brightness (dark/mid/bright), contrast (low/medium/high), per-channel stats (JSON only) |
| `ocr` | Tesseract via `pytesseract` (optional ×2: pip package *and* system binary) | Reading-order lines rebuilt from block/para/line indices; average confidence; largest-text position/size; `line_boxes` + `word_boxes` in relative coords (consumed by layout). Low-confidence first pass (<75) triggers an upscale+Otsu refinement pass, kept only if it scores higher and **only when text was already found** — honest negatives stay negative |
| `tables` | Morphological ruling-line detection (OpenCV) → cell grid → one OCR pass bucketed into cells | Rows of pipe-separated cell values, row/column associations intact. Only emits when the grid is *drawn* (≥3 lines each way, spanning, actually crossing, text-sized cells) — whitespace-only column alignment is deliberately not inferred |
| `colors` | Pillow median-cut quantisation (≤200px thumbnail, 8 bins) | dominant palette (≥4% coverage, top 5), *accent* colours (0.4–4% coverage, chromatic, hue not already dominant — catches brand marks), 3×3 grid where each cell reports its *most common* colour (bucketed mode, not mean — a mean invents colours that exist nowhere), grayscale flag |
| `regions` | Quantise ≤256px copy (10 bins) → per-bin connected components (OpenCV), morphological open to kill speckle | Per region: colour name+hex, area fraction, bbox (relative), 3×3 position, smooth/textured, background flag (touches all 4 edges + ≥30% area). Then delegates to `relations.py` for bands / stacks / gradients / baseline groups / left-edge groups |
| `structure` | Auto-Canny (thresholds from median intensity) + probabilistic Hough | edge density, line orientations present (h/v/diagonal), layout character (minimal/structured/busy) |
| `shapes` | Canny → dilate → external contours → Douglas-Peucker + circularity | count, class (triangle/square/rectangle/circle/polygon(n)/blob), size bucket, position. Large (≥15%) polygons/blobs are dropped — they are almost always several touching objects merged by dilation |
| `faces` | OpenCV Haar cascades, frontal + profile, IoU>0.5 dedup | count + rough positions only; never identity |
| `codes` | OpenCV `QRCodeDetector` (+ `cv2.barcode` when the build ships it) | decoded values. Defensive against OpenCV's version-varying return arities |
| `exif` | PIL `getexif()` | capture date, device make+model, orientation, GPS reduced to a **presence flag** (deliberate privacy choice — never coordinates) |

### Data flow end-to-end (text path)

1. `cli.main()` parses args, validates module names against `REGISTRY`.
2. `extract()` → `load_context()` decodes the file once.
3. Each registered (and selected) module gets the shared `ctx`, returns a dict.
4. `layout.build(results)` runs if both `ocr` and `regions` are available and
   non-empty; its `ModuleResult` is inserted right after regions.
5. `ImageDescriptor.to_text()` → `formatter.to_text()` → each `ModuleResult.to_lines()`
   calls the module's own `render(data)`; unavailable sections render as
   `unavailable: <reason>`.
6. CLI prints to stdout or writes `--output` (status note goes to stderr so stdout
   stays pipeable).

## 4. Public API surface

Intentionally tiny (`blindsight/__init__.py`):

```python
from blindsight import extract, ImageDescriptor, ModuleResult

d = extract("photo.jpg")                 # all built-in modules
d = extract("photo.jpg", modules=["ocr", "colors"])
d = extract("photo.jpg", enable_plugins=True)   # + third-party modules, if any installed
d.to_text()      # -> str, the LLM-ready block
d.to_json()      # -> dict, same structure
d.get("ocr")     # -> ModuleResult | None  (.available, .data, .note)
d.source, d.width, d.height
__version__      # "0.1.0" (also in pyproject.toml — keep in sync)
```

CLI: `blindsight IMG [-o FILE] [-f text|json] [-m mod1,mod2] [--enable-plugins]
[--version]`, also reachable as `python blindsight.py` (no install) and
`python -m blindsight`. The MCP server (`mcp_server.py`) reads the same
opt-in as an env var, `BLINDSIGHT_ENABLE_PLUGINS=1`, checked once at
import time since there is no argv to pass through an MCP client config.

Everything else (module payload key names, relations dict shapes) is internal but
*contractual between modules*: `layout.py` requires `ocr.data["line_boxes"/"word_boxes"]`
and `regions.data["regions"/"baseline_groups"]` and fails loudly if they are renamed.

## 5. Dependency rationale

| Dependency | Why | Could it go? |
|---|---|---|
| `numpy` | array math everywhere | No |
| `Pillow` | decoding, EXIF, median-cut quantiser (avoids a colour-science dep) | No |
| `opencv-python` | connected components, Canny/Hough, contours, Haar cascades, QR decoding (avoids zbar) | No — but CI substitutes `opencv-python-headless` (identical API, no GUI libs); never use `cv2.imshow` etc. |
| `pytesseract` (optional extra) | OCR; also needs the system `tesseract` binary | Yes — OCR degrades to `unavailable` |
| `pytest` (dev extra) | tests | dev only |
| `tiktoken` (uninstalled, soft) | exact token counts in `benchmark/token_savings.py`; falls back to len/4 | soft |
| `qrcode` (uninstalled, script-only) | `examples/make_synthetic_samples.py` only | script-only, macOS-only fonts too |

Design goal: *few system dependencies*. Adding a dependency needs a strong reason.

## 6. Extension points

1. **New extraction module** — the designed extension path. Create `blindsight/modules/yourmod.py` with `NAME/TITLE/run/render`, guard optional imports, report relative geometry, name colours via `colornames`, then append to `REGISTRY` at the position matching its information value. Add unit tests with synthesised images, and a property-based family if it detects structure.
2. **New relation heuristic** — add a pure function in `relations.py` over region dicts, with named thresholds and a comment per threshold naming the false positive it rejects. Wire it into `regions.run()` and `regions.render()`. Must pass `tests/test_random_property.py::test_random_featureless_images_invent_no_structure`.
3. **New derived cross-module section** — follow `layout.py`: consume module *results* (not pixels) in `extractor.extract()` after the loop; return `None` when there is nothing to say; access payload keys directly so contract drift fails loudly.
4. **New output format** — add a function in `formatter.py` and a `--format` choice in `cli.py`; keep it deterministic and compact.
5. **Colour vocabulary** — add anchors to `_PALETTE` / hue buckets in `colornames.py`; `tests/test_colors_accent.py` guards existing names against regression.

## 7. How the benchmark works

The benchmark measures the project's two claims **without any model API key** (the human pastes prompts into whatever models they compare):

```
benchmark/ground_truth.json      questions + answers, tagged factual|perceptual
        │
        ▼
run_benchmark.py --images … --questions …
        │   per image: <name>.descriptor.txt  (condition A context)
        │              <name>.packet.txt      (ready-to-paste prompt: descriptor
        ▼                                      + that image's questions)
make_test_sheet.py  → test_sheet.md (readable worksheet)
        │           → scorecard.csv (blank descriptor_grade / image_grade columns)
        ▼
  [human grades each answer 1 / 0.5 / 0, both conditions]
        ▼
score.py            → factual vs perceptual table + headline sentence
token_savings.py    → cost side: descriptor tokens (tiktoken o200k_base, or len/4)
                      vs vendor image-token formulas (OpenAI tile formula;
                      Anthropic w*h/750 after 1568px resize)
```

`make_test_sheet.py` deliberately splits "what to grade" from "tally the grades" (score.py) so the grader commits to grades before seeing totals.

**Committed results** (11 showcase images, 36 questions, graded once with GPT-5 mini; reproduced by running `score.py` on the committed `scorecard.csv`):

| Condition | Factual (n=27) | Perceptual (n=9) | Overall (n=36) |
|---|---|---|---|
| descriptor (text) | **93%** | 11% | 72% |
| image (control) | 94% | 100% | 96% |

Token cost: 32% cheaper than the cheaper of the two image options across the showcase set (per `token_savings.py`); small QR/barcode images honestly show *negative* savings. One notable case: the QR-code URL question scored 1.0 from the descriptor vs 0.0 from the vision model — OpenCV *decodes* the code; a vision model cannot read one from pixels. These are single-pass numbers on a small set, not statistics.

`examples/regenerate.py` re-runs the pipeline over `examples/images/` to refresh the committed fixtures in `examples/results/`, which `tests/test_example_fixtures.py` guards against silent drift (deterministic sections only: Stats, Colors, Regions, Codes — OCR is Tesseract-version dependent and Faces varies by cascade data).

## 8. Test suite shape (90 tests, ~15 s)

| File | Kind | Covers |
|---|---|---|
| `test_extractor.py` | unit | pipeline wiring, module subset selection, failure isolation, geometry helpers, text/JSON shape |
| `test_regions.py` | unit, synthesised images | baseline groups, bands, stacks, gradients, left edges, no-relations-on-plain |
| `test_random_property.py` | property-based, seeded RNG families | vertical/horizontal bars recover order+proportion; gradients ≠ rows; UI rows collapse to stacks; featureless images invent nothing |
| `test_relations.py` | unit, crafted dicts | gradient merging edge cases: unsorted input, value-equal duplicates, alternating rows |
| `test_layout.py` | unit, crafted results | containment linking, smallest-region-wins, baseline labels, loud KeyError contract |
| `test_ocr_layout.py` | unit, no Tesseract | reading-order reconstruction (`_order_lines`) |
| `test_colors_accent.py` | unit | hue-aware accent naming, accent surfacing, no-regression on dominant names |
| `test_example_fixtures.py` | fixture guard | committed showcase descriptors vs current output |

Known coverage gaps (see `docs/audit/PRODUCTION_AUDIT.md`): `cli.py`, `codes.py`, `exif.py`, `faces.py`, `structure.py`, `stats` renderer, formatter unavailable-path, `context.py` downscaling, all benchmark scripts.
