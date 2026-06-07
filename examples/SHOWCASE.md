# Showcase

A walkthrough of Blindsight on eleven real and synthetic images. For each one you
get the source image, the generated descriptor, and a set of questions a model
might be asked. The point of this folder is **honesty**: it shows where a pure
text descriptor is genuinely enough, and where it visibly is not.

Each row links the descriptor (`results/<name>.descriptor.txt`) and the
ready-to-paste model packet (`results/<name>.packet.txt`). The images live in
`images/`. Regenerate everything with:

```bash
python examples/make_synthetic_samples.py        # synthetic images
python benchmark/run_benchmark.py \
    --images examples/images --out examples/results \
    --questions examples/questions.json          # descriptors + packets
```

## How to read the verdicts

- ✅ **Answered from text** — the fact is in the descriptor, verbatim or trivially derived.
- ⚠️ **Partial** — the descriptor gets close but is noisy or ambiguous.
- ❌ **Needs the image** — genuinely perceptual; the descriptor honestly can't answer, which is the signal to fall back to a vision model.

---

## The factual wins — where text is enough

These are the cases the project is built for: symbolic information that survives
perfectly as text.

### `receipt.png` — document OCR

| Question | Verdict | From the descriptor |
|---|---|---|
| What store issued this receipt? | ✅ | OCR: "BLUE CART MARKET" |
| What is the total amount? | ✅ | OCR: "TOTAL Rs 687.75" |
| How many eggs and at what price? | ✅ | OCR: "Eggs (12) x1 120.00" |
| What date/time was it issued? | ✅ | OCR: "Date: 2026-05-12 14:32" |

OCR confidence 87.4% (reliable). A multimodal model would answer these the same
way — at a fraction of the cost here. **This is the core thesis working.**

### `qr_code.png` — machine-readable code

| Question | Verdict | From the descriptor |
|---|---|---|
| Is there a QR code? | ✅ | Codes: QR present |
| What value does it contain? | ✅ | `https://sathvikc.github.io/lume-js/` |

Decoded exactly by OpenCV's detector — no zbar dependency. The colour/shape
modules also correctly flag the three finder squares as "square, … " regions.
A vision model has to *read* this; Blindsight just *decodes* it.

### `app_ui.png` — app screenshot

| Question | Verdict | From the descriptor |
|---|---|---|
| What screen is this? | ✅ | OCR begins with the header; rows read as a settings list |
| List the menu options. | ✅ | OCR: Account, Notifications, Privacy, Appearance, Storage |
| Colour of the primary button? | ✅ | Colors: blue #2062E8 (19%) — the Save button |
| Which setting is toggled off? | ⚠️ | OCR garbles toggle glyphs ("@e"); the *off* state isn't legible from text |

A strong, realistic result: the textual content of a UI extracts well; the
*state* of a custom toggle widget does not. OCR confidence 62.4% flags the
uncertainty honestly.

### `blindsight_logo.png` — clean wordmark (the project's own logo)

| Question | Verdict | From the descriptor |
|---|---|---|
| Brand name? | ✅ | OCR: "BLINDSIGHT" (+ tagline "SEE DATA, NOT IMAGES") at 95.0% (reliable) |
| What does the emblem depict? | ❌ | Shapes see a polygon + squares — no "it's an eye made of binary" understanding |
| Main colours? | ✅ | Colors: white + navy blue #121154 |

Paired deliberately with `logo.png` below: this logo sets the name in a clean
sans-serif, so OCR reads the brand and tagline **correctly and confidently**
(though it returns them slightly out of reading order). The difference between
this success and the NOVA failure is entirely font styling — which is exactly the
variable that decides whether the text path is enough. The emblem itself (an eye
dissolving into binary) is invisible to the descriptor: it sees shapes, not
meaning.

---

## The partial cases — close, but read the fine print

### `barcode.png` — code the detector missed, OCR caught

| Question | Verdict | From the descriptor |
|---|---|---|
| What type of code? | ⚠️ | Not labelled as a barcode by the codes module |
| Decoded barcode number? | ✅ | OCR: "5901234123457" (96.0% confidence) |

A telling case. OpenCV's barcode decoder did **not** return a value, so the
Codes section says `none` — but the human-readable digits printed under the bars
were read by OCR with high confidence. The right answer leaked through a
different module. Worth noting the EAN-13 check digit (`...57`) is recovered.

### `bar_chart.png` — data viz

| Question | Verdict | From the descriptor |
|---|---|---|
| Title of the chart? | ✅ | OCR: "Quarterly Revenue (Cr)" |
| How many bars? | ❌ | Shapes merged the bars into one `polygon(7)` — count is unreliable |
| Which quarter was highest? | ⚠️ | OCR recovers values (200/160/120/280) and labels, but their pairing is lost |

Honest failure mode: classical contour detection can't separate adjacent bars,
and OCR reads the value labels out of spatial order ("…120 Qi Q2 Q3 280"). A
model *might* infer Q4=280 is highest from the numbers, but the descriptor
doesn't hand it the bar→value mapping. Charts are a "send the image" signal.

### `logo.png` — stylised branding

| Question | Verdict | From the descriptor |
|---|---|---|
| Brand name? | ❌ | OCR misread "NOVA" as "Orem" (60.0% confidence) |
| Geometric shape it's built around? | ⚠️ | Shapes report polygons/circles, but not cleanly "hexagon" |
| Main colours? | ✅ | Colors: white + blue #2163E8 |

Stylised display type defeats OCR — exactly the limitation the README warns
about. The low confidence (60%) is the tell: a consumer should treat this brand
name as unreliable and verify against the image. Contrast with
`blindsight_logo.png` above, where a clean font reads correctly at 85% — same
module, opposite outcome, font styling the only difference.

---

## The perceptual cases — text is honestly not enough

These are photographs. They show the descriptor's ceiling clearly, which is the
*point* of including them: this is where you pay for a real vision model.

### `portrait_face.jpg` — a person

| Question | Verdict | From the descriptor |
|---|---|---|
| How many people? | ✅ | Faces: count 1 (center) |
| Dominant background colour? | ⚠️ | Colors lead with a dark brown / gray / salmon skin-and-scene mix; no single clean "background" |
| Is the person smiling? | ❌ | No expression analysis — needs the image |
| Approximate age? | ❌ | Out of scope entirely |

Face *counting* works (Haar cascade); face *understanding* does not. A clean
split between what classical CV can and cannot do.

> The portrait is a **synthetic, GAN-generated face** (no real person), so the
> showcase carries no likeness or model-release concerns and is safe to publish.

### `landscape.jpg` — outdoor scene (city skyline)

| Question | Verdict | From the descriptor |
|---|---|---|
| Indoor or outdoor? | ⚠️ | Inferable (bright, sky-toned top, low edge density) but not stated outright |
| Dominant colour of the upper half? | ✅ | Grid top row: light gray (overcast sky) |
| Any readable text? | ✅ | OCR: none detected — correct |
| What city/landmark? | ❌ | No landmark recognition — needs the image |

The 3×3 colour grid earns its keep here: it localises "sky on top, ground below"
without any scene understanding.

### `street_scene.jpg` — colour-dominant scene

| Question | Verdict | From the descriptor |
|---|---|---|
| Single dominant colour? | ✅ | Colors: sky blue across the whole grid (~69% combined) |
| Any human faces? | ✅ | Faces: count 0 — correct |
| What objects are on the table? | ❌ | No object recognition — needs the image |

A crisp demonstration of the boundary: "what colour" and "are there faces" are
answerable; "what objects" is not.

### `photo_square.jpg` — embossed text in a photo

| Question | Verdict | From the descriptor |
|---|---|---|
| What text is visible? | ❌ | OCR: none detected — the embossed, low-contrast text is missed |
| How many faces? | ✅ | Faces: count 0 |
| Describe what's happening? | ❌ | Narrative/scene meaning — explicitly out of scope |

The hardest OCR case in the set: text that's physically present but low-contrast
and non-planar. The descriptor correctly reports *no* readable text rather than
hallucinating — a safe failure.

---

## What the showcase demonstrates

1. **Documents, codes, and UI text** — Blindsight answers as well as a vision
   model, far cheaper. This is the project's home turf.
2. **Charts, stylised logos, low-contrast text** — partial. The descriptor often
   surfaces the right raw tokens but loses the structure or misreads them; the
   confidence scores flag when to distrust it.
3. **Photographs and scene meaning** — out of scope by design. The descriptor
   reports honest negatives ("none detected", count 0) instead of guessing,
   which is exactly the cue to escalate to a real vision model.

The value isn't that the descriptor answers everything — it's that it answers the
*factual* subset cheaply and **tells you, via confidence and honest negatives,
when it can't.**
