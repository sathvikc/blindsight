# Graph Report - blindsight  (2026-07-18)

## Corpus Check
- 66 files · ~103,053 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 608 nodes · 1080 edges · 38 communities (28 shown, 10 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 24 edges (avg confidence: 0.59)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1f8bfe98`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Image Context & Geometry
- Descriptor Data Model
- CLI & Extract Entry
- Sample Image Fixtures
- OCR Module
- Color Naming
- Region Segmentation
- MCP Server
- MCP Server Tests
- Benchmark Scoring
- Image Loading & OCR Tests
- Table Reconstruction Tests
- Synthetic Sample Generation
- Capabilities MCP Tool
- Describe Image MCP Tool
- Inspect Region MCP Tool
- test_tables.py
- Release Template
- Blindsight Root
- What You Must Do When Invoked
- tables.py
- CLAUDE.md — agent onboarding for Blindsight
- graphify reference: extra exports and benchmark
- region_name
- ModuleUnavailable
- shapes.py
- graphify reference: query, path, explain
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- CLAUDE.md
- extraction-spec.md
- .github/pull_request_template.md
- __init__.py
- structure.py

## God Nodes (most connected - your core abstractions)
1. `extract()` - 41 edges
2. `ImageContext` - 25 edges
3. `_roundtrip()` - 19 edges
4. `ModuleUnavailable` - 17 edges
5. `region_name()` - 14 edges
6. `run()` - 14 edges
7. `examples/SHOWCASE.md` - 14 edges
8. `_call()` - 13 edges
9. `CLAUDE.md — agent onboarding for Blindsight` - 12 edges
10. `PluginLoadWarning` - 12 edges

## Surprising Connections (you probably didn't know these)
- `Blindsight eye/binary logo (root asset)` --semantically_similar_to--> `Blindsight logo: eye dissolving into binary, with tagline`  [AMBIGUOUS] [semantically similar]
  logo.png → examples/images/blindsight_logo.png
- `logo.svg (vector Blindsight logo)` --semantically_similar_to--> `Blindsight eye/binary logo (root asset)`  [AMBIGUOUS] [semantically similar]
  logo.svg → logo.png
- `test_extract_ignores_plugins_by_default()` --calls--> `extract()`  [INFERRED]
  tests/test_plugins.py → blindsight/extractor.py
- `test_extract_runs_an_enabled_plugin()` --calls--> `extract()`  [INFERRED]
  tests/test_plugins.py → blindsight/extractor.py
- `benchmark/test_sheet.md` --references--> `Mobile app Settings screen UI mockup`  [EXTRACTED]
  benchmark/test_sheet.md → examples/images/app_ui.png

## Import Cycles
- 1-file cycle: `blindsight/modules/__init__.py -> blindsight/modules/__init__.py`

## Hyperedges (group relationships)
- **Graded benchmark workflow: ground truth -> descriptors -> worksheet -> tally -> cost** — benchmark_ground_truth, benchmark_run_benchmark, benchmark_make_test_sheet, benchmark_score, benchmark_token_savings [EXTRACTED 0.85]

## Communities (38 total, 10 thin omitted)

### Community 0 - "Image Context & Geometry"
Cohesion: 0.16
Nodes (13): ImageContext, load_context(), ndarray, Shared image context passed to every module.  Loading and colour-space conversio, Pre-decoded views of a single image., OpenCV-ordered (BGR) view of the image., Load an image into an :class:`ImageContext`.      Large images are downscaled so, Any (+5 more)

### Community 1 - "Descriptor Data Model"
Cohesion: 0.07
Nodes (36): ImageDescriptor, ModuleResult, Any, Core data model for an extracted image description.  A descriptor is an ordered, Outcome of a single extraction module.      Attributes:         name: Stable mac, Render this section, including its ``[Title]`` header., Full descriptor for one image., Return the result for a module by machine name, if present. (+28 more)

### Community 2 - "CLI & Extract Entry"
Cohesion: 0.05
Nodes (54): ArgumentParser, _format_questions(), _iter_images(), main(), Path, _build_parser(), main(), Command-line interface for Blindsight. (+46 more)

### Community 3 - "Sample Image Fixtures"
Cohesion: 0.08
Nodes (16): benchmark/test_sheet.md, Mobile app Settings screen UI mockup, Quarterly revenue bar chart (Q1-Q4), EAN-13 barcode, digits 5901234123457, Blindsight logo: eye dissolving into binary, with tagline, NYC skyline photo across the river, cloudy sky, lume.js sun/moon logo with tagline 'ILLUMINATE YOUR UI', Coin-operated viewer overlooking hazy city skyline (+8 more)

### Community 4 - "OCR Module"
Cohesion: 0.11
Nodes (37): _beats(), _binarized_pass(), _candidates(), _conf_mass(), _deskew_pass(), _estimate_skew(), _extract_words(), _map_words() (+29 more)

### Community 5 - "Color Naming"
Cohesion: 0.10
Nodes (33): accent_name(), nearest_name(), Map an RGB triple to the nearest human-readable colour name.  A named colour ("n, Return the closest palette colour name by Euclidean distance in RGB., Format an RGB triple as ``#RRGGBB``., Return (hue 0-360, saturation 0-1, value 0-1) for an RGB triple., Name a colour by its hue, robust to low saturation.      Unlike :func:`nearest_n, _rgb_to_hsv() (+25 more)

### Community 6 - "Region Segmentation"
Cohesion: 0.11
Nodes (31): _aspect(), _components(), _pct(), Any, Image, ndarray, Region segmentation: describe the image as coloured regions plus relations.  Thi, Quantise a downscaled copy and return (labels, small_rgb, small_gray). (+23 more)

### Community 7 - "MCP Server"
Cohesion: 0.16
Nodes (27): _decode_base64(), _error(), _extract_from_source(), _fetch_url(), _handle_initialize(), handle_message(), _handle_tools_call(), main() (+19 more)

### Community 8 - "MCP Server Tests"
Cohesion: 0.16
Nodes (24): _call(), MCP server: the JSON-RPC surface a text-only model's client talks to.  Tests dri, Feed JSON-RPC messages through serve() and decode the responses., The loop the server is designed around: overview misses tiny text,     inspect_r, A simple scene: white page, blue rectangle, red circle., _roundtrip(), scene_path(), test_capabilities_lists_every_module() (+16 more)

### Community 9 - "Benchmark Scoring"
Cohesion: 0.14
Nodes (21): benchmark/ground_truth.json, _descriptor_text(), _load_ground_truth(), main(), Path, _write_scorecard(), _write_test_sheet(), benchmark/README.md (+13 more)

### Community 10 - "Image Loading & OCR Tests"
Cohesion: 0.28
Nodes (13): _font(), Image, OCR candidate passes on hard images: inverted, tilted, and text-free.  These tes, _run(), test_dark_noise_image_stays_text_free(), test_deskewed_boxes_land_back_in_original_space(), test_flat_image_stays_text_free(), test_light_on_dark_text_is_recovered() (+5 more)

### Community 11 - "Table Reconstruction Tests"
Cohesion: 0.14
Nodes (26): load_registry(), Return the modules to run: the built-in ``REGISTRY``, plus any third-party plugi, discover(), PluginLoadWarning, Any, Third-party extraction modules, discovered via Python entry points.  Blindsight', A plugin entry point failed to load or violated the module contract., Return a reason ``obj`` doesn't satisfy the module contract, or None. (+18 more)

### Community 12 - "Synthetic Sample Generation"
Cohesion: 0.35
Nodes (11): app_ui(), bar_chart(), barcode_img(), font(), logo(), main(), price_table(), qr_code() (+3 more)

### Community 18 - "test_tables.py"
Cohesion: 0.27
Nodes (13): _font(), Image, Tables module: ruled-grid reconstruction and its anti-hallucination gates.  The, _ruled_table(), _run(), test_cell_contents_keep_row_column_association(), test_chart_gridlines_alone_are_not_a_table(), test_flat_image_has_no_table() (+5 more)

### Community 21 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 22 - "tables.py"
Cohesion: 0.24
Nodes (12): _clip(), _crossings_exist(), _line_mask(), _line_positions(), Any, ndarray, Ruled-table reconstruction: grid geometry plus per-cell text.  Tables are the de, Keep only long straight runs in one direction via open-with-long-kernel. (+4 more)

### Community 24 - "CLAUDE.md — agent onboarding for Blindsight"
Cohesion: 0.04
Nodes (43): Architecture in one paragraph, CLAUDE.md — agent onboarding for Blindsight, Commands, Conventions to match, Gotchas, graphify, Layout, Plugins (+35 more)

### Community 25 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 26 - "region_name"
Cohesion: 0.24
Nodes (10): Geometry helpers shared across modules (position and size naming)., Name the 3x3 grid cell a centre point falls in, e.g. ``"top-center"``.      The, region_name(), _load_cascade(), _overlaps(), Any, Face detection via OpenCV Haar cascades (classical, no ML model download).  Runs, render() (+2 more)

### Community 27 - "ModuleUnavailable"
Cohesion: 0.29
Nodes (9): ModuleUnavailable, Exception, Raised by a module when an optional dependency or resource is missing.      The, _decode_barcodes(), _decode_qr(), Any, QR code and barcode decoding.  Uses OpenCV's built-in ``QRCodeDetector`` so no e, render() (+1 more)

### Community 28 - "shapes.py"
Cohesion: 0.27
Nodes (9): Bucket an object's area relative to the image into small/medium/large., size_bucket(), _classify(), Any, ndarray, Shape and contour analysis: count, classify, size, and locate regions.  Contours, render(), run() (+1 more)

### Community 29 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 30 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 31 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 32 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 38 - "__init__.py"
Cohesion: 0.33
Nodes (7): Extraction modules.  Each module exposes: NAME:  str                      machin, _aspect_ratio(), _orientation(), Any, Image statistics: dimensions, orientation, brightness, contrast, channels., render(), run()

### Community 40 - "structure.py"
Cohesion: 0.39
Nodes (7): _auto_canny(), _classify_lines(), Any, ndarray, Edge and structural layout: edge density, dominant line orientations, layout.  U, render(), run()

## Ambiguous Edges - Review These
- `logo.svg (vector Blindsight logo)` → `Blindsight eye/binary logo (root asset)`  [AMBIGUOUS]
  logo.svg · relation: semantically_similar_to
- `Blindsight eye/binary logo (root asset)` → `Blindsight logo: eye dissolving into binary, with tagline`  [AMBIGUOUS]
  logo.png · relation: semantically_similar_to

## Knowledge Gaps
- **86 isolated node(s):** `What this project is`, `Architecture in one paragraph`, `Layout`, `The module contract`, `Plugins` (+81 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `logo.svg (vector Blindsight logo)` and `Blindsight eye/binary logo (root asset)`?**
  _Edge tagged AMBIGUOUS (relation: semantically_similar_to) - confidence is low._
- **What is the exact relationship between `Blindsight eye/binary logo (root asset)` and `Blindsight logo: eye dissolving into binary, with tagline`?**
  _Edge tagged AMBIGUOUS (relation: semantically_similar_to) - confidence is low._
- **Why does `extract()` connect `CLI & Extract Entry` to `Descriptor Data Model`, `Color Naming`, `MCP Server`, `Benchmark Scoring`, `Table Reconstruction Tests`?**
  _High betweenness centrality (0.248) - this node is a cross-community bridge._
- **Why does `examples/SHOWCASE.md` connect `Sample Image Fixtures` to `CLI & Extract Entry`, `Synthetic Sample Generation`?**
  _High betweenness centrality (0.139) - this node is a cross-community bridge._
- **Why does `load_registry()` connect `Table Reconstruction Tests` to `Descriptor Data Model`, `CLI & Extract Entry`, `__init__.py`, `MCP Server`?**
  _High betweenness centrality (0.085) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `extract()` (e.g. with `test_extract_ignores_plugins_by_default()` and `test_extract_runs_an_enabled_plugin()`) actually correct?**
  _`extract()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `What this project is`, `Architecture in one paragraph`, `Layout` to the rest of the system?**
  _86 weakly-connected nodes found - possible documentation gaps or missing edges._