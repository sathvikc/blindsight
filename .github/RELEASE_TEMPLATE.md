# Blindsight vX.Y.Z — YYYY-MM-DD

<!-- 1–3 sentence headline. What's the story of this release? -->

---

## Highlights

<!-- The 1–3 most important things a user needs to know. -->

---

## New Features

<!-- One bullet per new module, extraction capability, or tool. Link to docs where useful. -->

-

---

## Bug Fixes

<!-- One bullet per fix. Reference the issue number if one exists. -->

-

---

## Performance

<!-- Only include if there's a measurable improvement (faster extraction, fewer tokens, etc). -->

-

---

## Breaking Changes

<!-- Empty table = no breaking changes. Always include migration path. -->

| Change | Migration |
|--------|-----------|
| — | — |

---

## Deprecations

<!-- APIs that still work but will be removed in a future major. -->

-

---

## Tests

<!-- Test count and any notable new coverage areas. -->

**X tests passing** (from Y in vPREV)

---

## Install

```bash
pip install blindsight==X.Y.Z
```

**From source:**

```bash
pip install git+https://github.com/sathvikc/blindsight.git@vX.Y.Z
```

**Quick start:**

```python
from blindsight import extract

descriptor = extract("photo.jpg")
print(descriptor.to_text())      # LLM-friendly text block
print(descriptor.to_json())      # Structured dict with coordinates
```

---

## Benchmark

**Factual accuracy:** X% (descriptor) vs Y% (full vision model)  
**Token efficiency:** Z% fewer tokens than sending full image

---

## Full Changelog

[CHANGELOG.md · vX.Y.Z](https://github.com/sathvikc/blindsight/blob/main/CHANGELOG.md#xyz---yyyy-mm-dd)

**Compare:** https://github.com/sathvikc/blindsight/compare/vPREV...vX.Y.Z

---

<!-- Delete unused sections before publishing. -->
