# Showcase

A walkthrough of Blindsight on eleven real and synthetic images. For each one you
get the source image, the generated descriptor, and a set of questions a model
might be asked. The point of this folder is **honesty**: it shows where a pure
text descriptor is genuinely enough, and where it visibly is not.

The descriptors now include a **spatial layout layer** — a "where" section that
fuses the OCR, shape, and face detections into explicit relations (reading-order
rows, value-over-label columns, containment, and "a repeating element with a
gap"). It computes nothing new from pixels; it only states how the existing
detections relate in space, which is exactly the *relational* information a flat
per-module listing loses. Its effect is most visible on `app_ui.png` and
`bar_chart.png` below.

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
| What screen is this? | ✅ | OCR header reads as a settings list |
| List the menu options. | ✅ | OCR, one row per line: Account, Notifications, Privacy, Appearance, Storage |
| Colour of the primary button? | ✅ | Colors: blue #2062E8 (19%) — the Save button |
| Which setting is toggled off? | ✅ | Layout pattern-break: *"'@' aligns down a column on other rows but is missing at: Privacy"* — the relation is now stated, not latent |

A strong, realistic result. Reading-order line reconstruction puts each setting on
its own line, so the menu enumerates cleanly, and the low-confidence refinement
pass lifts OCR confidence from 62.4% to **76.7% (reliable)** with an `@` toggle
glyph on every row except `Privacy`. Previously the *off* state was only *latent*
in that token pattern, and a model wouldn't commit to it — an honest ⚠️. The
**spatial layout layer now makes it explicit**: it detects that `@` recurs down a
column on four rows and names the one interior row where it goes missing —
`Privacy`. It also reports `rectangle ⊃ Save`, binding the button label to its
shape. The only remaining inference is the small, safe one that `@` *means* a
toggle; *which* row lacks it is no longer guesswork.

### `blindsight_logo.png` — clean wordmark (the project's own logo)

| Question | Verdict | From the descriptor |
|---|---|---|
| Brand name? | ✅ | OCR: "BLINDSIGHT" (+ tagline "SEE DATA, NOT IMAGES") at 95.0% (reliable) |
| What does the emblem depict? | ❌ | Shapes see a polygon + squares — no "it's an eye made of binary" understanding |
| Main colours? | ✅ | Colors: dominant white + navy blue #121154, **accent: light cyan #9CEDF3** |

This logo sets the name in a clean sans-serif, so OCR reads the brand and tagline
**correctly and confidently** at 95% (though it returns them slightly out of
reading order). The navy wordmark covers a large enough dark area that the colour
module captures it as a *dominant* colour (`navy blue #121154`), and the small
cyan detail surfaces on the **accent line** — so the descriptor hands the model
both brand colours. The emblem itself (an eye dissolving into binary) is invisible
to the descriptor: it sees shapes, not meaning. Paired with `logo.png` below,
whose amber identity is an even thinner accent: both logos now recover their brand
colour — one as a dominant, one purely from the accent line.

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
| How many bars? | ✅ | OCR lists four values in order (280 / 200 / 160 / 120) — the count is recoverable |
| Which quarter was highest? | ⚠️ | Layout binds value→quarter as columns (200/Q2, 160/Q3, 120/Q1), but OCR missed the highest bar's axis label (Q4), so the top value stays unbound |

A mixed case that improved markedly. The **spatial layout layer now binds each
value to the quarter beneath it** as aligned columns — `200 / Q2`, `160 / Q3`,
`120 / Qi` — exactly the relational mapping that used to be lost, plus
`polygon(7) ⊃ 280, 200, 160, 120` tying the bars to the plot area. So the
value→quarter relation is genuinely recovered for the labels OCR read. This
specific question is the unlucky one: the *highest* bar is 280, whose axis label
was never OCR'd (the axis reads `Qi Q2 Q3`, no Q4), so the top value has no quarter
to bind to. The honest result is that the descriptor can now report Q2=200,
Q3=160, Q1≈120 from the columns, but cannot name the highest quarter — a faithful
⚠️ that, importantly, does **not** hallucinate a pairing.

### `logo.png` — clean wordmark, brand colour recovered from a thin accent (the `lume.js` logo)

| Question | Verdict | From the descriptor |
|---|---|---|
| Brand name? | ✅ | OCR: "lume.js" at 73.1% (uncertain, but correct) |
| Tagline? | ✅ | OCR: "ILLUMINATE YOUR UI" |
| What does the emblem depict? | ❌ | Shapes see four small polygons (the sun's rays) — no "it's a sun" |
| Main accent colours? | ⚠️ | Colors: dominant white #FFFFFF (87%), **accent: orange #BA8F49** — the amber brand colour is recovered; the dark-slate wordmark is too small to clear the threshold |

The clean wordmark reads: both the brand and the tagline come through. The 73%
confidence — lower than `blindsight_logo`'s 95% — is the OCR honestly flagging
noise, since it also tried to read the sun-ray glyphs (`i ~( "nw`). Colour is the
instructive case. The logo's identity is amber, but amber is a thin accent on a
white field, so the *dominant* palette is 87% white and the image even reads as
grayscale on average — the dominant line alone would miss the brand entirely. The
colour module therefore adds an **accent line** that surfaces chromatic colours
sitting below the dominance floor, ranked by area. Here it recovers `orange` — the
amber mark — which is exactly what the question asks for. The dark-slate `lume`
wordmark is too small and too neutral to clear the accent threshold, so the answer
is correct but incomplete: a partial, not a miss. This is the mirror of
`blindsight_logo.png` above, whose navy is large enough to be dominant outright.

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
   model, far cheaper. This is the project's home turf, and reading-order line
   reconstruction keeps multi-line layouts (receipts, menus) intact for the model.
2. **Charts, logos, low-contrast text** — partial, but the relational gap is
   closing. The descriptor surfaces the right raw tokens (brand name, tagline,
   chart title, value labels), recovers small-area brand colours through the
   accent line, and the **spatial layout layer now recovers relations the flat
   listing lost** — binding chart values to their axis labels, naming the settings
   row whose toggle is missing, and tying a button to its label. What remains out
   of reach is bounded by upstream detection (a value whose axis label OCR never
   read cannot be bound) and by meaning (the emblem's depiction); the confidence
   scores and honest "missing"/"none" reports flag when to distrust it.
3. **Photographs and scene meaning** — out of scope by design. The descriptor
   reports honest negatives ("none detected", count 0) instead of guessing,
   which is exactly the cue to escalate to a real vision model.

The value isn't that the descriptor answers everything — it's that it answers the
*factual* subset cheaply and **tells you, via confidence and honest negatives,
when it can't.**
