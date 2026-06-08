# Benchmark test sheet

For each question, answer it **twice** and grade each answer in `scorecard.csv`:

- **Condition A (descriptor):** paste the descriptor below (or the matching `results/<name>.packet.txt`) into a text-only model and answer from that alone.
- **Condition B (image):** give the real image to a multimodal model as the control.

Grade each answer `1` (correct), `0` (wrong), or `0.5` (partial) against the correct answer shown here. `type` tells you whether the fact is *factual* (text should be able to carry it) or *perceptual* (expected to need the pixels).

## receipt.png

<details><summary>descriptor</summary>

```
=== IMAGE DESCRIPTOR ===
source: examples/images/receipt.png
size: 420x560
modules: 8/8 available

[Stats]
  resolution: 420x560
  orientation: portrait
  aspect_ratio: 3:4
  brightness: bright
  contrast: medium

[OCR]
  text: "BLUE CART MARKET 123 Banjara Hills, Hyd Date: 2026-05-12 14:32 Receipt #: 004871 Milk IL x2 90.00 Brown Bread x1 45.00 Eggs (12) x1 120.00 Bananas 1kg x1 60.00 Coffee 200g x1 340.00 SUBTOTAL 655.00 GST 5% 32.75 TOTAL Rs 687.75 THANK YOU FOR SHOPPING"
  confidence: 87.4% (reliable)
  position: top-center
  size: medium

[Colors]
  dominant: white #FFFFFF (76%), white #FDFDFD (4%), white #FEFEFE (4%)
  grid:
    TL:white  TC:white  TR:white
    ML:white  MC:white  MR:white
    BL:white  BC:white  BR:white
  grayscale: true

[Structure]
  edge_density: medium
  lines: horizontal=true, vertical=false, diagonal=false
  layout: structured

[Shapes]
  count: 7
  - blob, small, bottom-center
  - blob, small, center
  - blob, small, top-center
  - blob, small, top-center
  - rectangle, small, bottom-center
  - triangle, small, top-left
  - polygon(6), small, top-center

[Faces]
  count: 0

[Codes]
  none

[EXIF]
  none

=========================
```

</details>

| # | type | question | correct answer |
|---|---|---|---|
| 1 | factual | What store issued this receipt? | Blue Cart Market |
| 2 | factual | What is the total amount? | Rs 687.75 |
| 3 | factual | How many eggs were purchased and at what price? | 12 eggs (one pack) for Rs 120.00 |
| 4 | factual | What date and time was this receipt issued? | 2026-05-12 at 14:32 |

## qr_code.png

<details><summary>descriptor</summary>

```
=== IMAGE DESCRIPTOR ===
source: examples/images/qr_code.png
size: 360x360
modules: 8/8 available

[Stats]
  resolution: 360x360
  orientation: square
  aspect_ratio: 1:1
  brightness: bright
  contrast: high

[OCR]
  text: (none detected)

[Colors]
  dominant: white #FFFFFF (52%), black #000000 (17%), black #020202 (7%), white #FBFBFB (5%), gray #7C7C7C (4%)
  grid:
    TL:light gray  TC:light gray  TR:light gray
    ML:gray  MC:gray  MR:light gray
    BL:light gray  BC:light gray  BR:light gray
  grayscale: true

[Structure]
  edge_density: medium
  lines: horizontal=true, vertical=true, diagonal=false
  layout: busy

[Shapes]
  count: 4
  - square, large, center
  - square, medium, bottom-left
  - square, medium, top-right
  - square, medium, top-left

[Faces]
  count: 0

[Codes]
  QR: https://sathvikc.github.io/lume-js/

[EXIF]
  none

=========================
```

</details>

| # | type | question | correct answer |
|---|---|---|---|
| 1 | factual | Is there a QR code in this image? | Yes |
| 2 | factual | What URL or value does the code contain? | https://sathvikc.github.io/lume-js/ |

## barcode.png

<details><summary>descriptor</summary>

```
=== IMAGE DESCRIPTOR ===
source: examples/images/barcode.png
size: 523x280
modules: 8/8 available

[Stats]
  resolution: 523x280
  orientation: landscape
  aspect_ratio: 523:280
  brightness: bright
  contrast: high

[OCR]
  text: "5901234123457"
  confidence: 96.0% (reliable)
  position: bottom-center
  size: large

[Colors]
  dominant: white #FFFFFF (56%), black #000000 (11%), white #FDFDFD (7%), black #060606 (6%), gray #707070 (5%)
  grid:
    TL:light gray  TC:gray  TR:light gray
    ML:light gray  MC:gray  MR:light gray
    BL:white  BC:white  BR:white
  grayscale: true

[Structure]
  edge_density: medium
  lines: horizontal=true, vertical=true, diagonal=false
  layout: busy

[Shapes]
  count: 12
  - triangle, medium, center
  - blob, small, right
  - blob, small, center
  - blob, small, left
  - blob, small, right
  - blob, small, center
  - blob, small, center
  - blob, small, center
  - blob, small, center
  - blob, small, center
  - blob, small, left
  - blob, small, center

[Faces]
  count: 0

[Codes]
  none

[EXIF]
  none

=========================
```

</details>

| # | type | question | correct answer |
|---|---|---|---|
| 1 | factual | What type of code is shown? | A 1D barcode (EAN-13) |
| 2 | factual | What is the decoded barcode number? | 5901234123457 |

## bar_chart.png

<details><summary>descriptor</summary>

```
=== IMAGE DESCRIPTOR ===
source: examples/images/bar_chart.png
size: 640x420
modules: 8/8 available

[Stats]
  resolution: 640x420
  orientation: landscape
  aspect_ratio: 32:21
  brightness: bright
  contrast: medium

[OCR]
  text: "Quarterly Revenue (Cr) 200 160 120 Qi Q2 Q3 280"
  confidence: 89.9% (reliable)
  position: top-left
  size: medium

[Colors]
  dominant: white #FFFFFF (64%), red #D9302A (9%), orange #DE831F (7%), lime green #52AA54 (5%), gray #43638C (5%)
  grid:
    TL:white  TC:white  TR:light gray
    ML:white  MC:beige  MR:salmon
    BL:light blue  BC:beige  BR:beige
  grayscale: false

[Structure]
  edge_density: low
  lines: horizontal=true, vertical=true, diagonal=false
  layout: structured

[Shapes]
  count: 2
  - polygon(7), large, center
  - triangle, small, top-left

[Faces]
  count: 0

[Codes]
  none

[EXIF]
  none

=========================
```

</details>

| # | type | question | correct answer |
|---|---|---|---|
| 1 | factual | What is the title of this chart? | Quarterly Revenue (Cr) |
| 2 | factual | How many bars does the chart contain? | 4 (Q1-Q4) |
| 3 | factual | Which quarter had the highest revenue? | Q4 (280) |

## app_ui.png

<details><summary>descriptor</summary>

```
=== IMAGE DESCRIPTOR ===
source: examples/images/app_ui.png
size: 390x700
modules: 8/8 available

[Stats]
  resolution: 390x700
  orientation: portrait
  aspect_ratio: 39:70
  brightness: bright
  contrast: medium

[OCR]
  text: "Account @e Notifications @e Privacy Appearance @e Storage @e Save"
  confidence: 62.4% (uncertain)
  position: top-left
  size: medium

[Colors]
  dominant: white #F5F6F8 (38%), white #FFFFFF (31%), blue #2062E8 (19%)
  grid:
    TL:light blue  TC:light blue  TR:light blue
    ML:white  MC:white  MR:white
    BL:light blue  BC:light blue  BR:light blue
  grayscale: false

[Structure]
  edge_density: low
  lines: horizontal=true, vertical=false, diagonal=false
  layout: structured

[Shapes]
  count: 4
  - rectangle, medium, bottom-center
  - triangle, small, top-left
  - rectangle, small, top-left
  - triangle, small, left

[Faces]
  count: 0

[Codes]
  none

[EXIF]
  none

=========================
```

</details>

| # | type | question | correct answer |
|---|---|---|---|
| 1 | factual | What screen of the app is this? | Settings |
| 2 | factual | List the menu options shown. | Account, Notifications, Privacy, Appearance, Storage |
| 3 | factual | What colour is the primary action button? | Blue (the Save button) |
| 4 | perceptual | Which setting is toggled off? | Privacy |

## logo.png

<details><summary>descriptor</summary>

```
=== IMAGE DESCRIPTOR ===
source: examples/images/logo.png
size: 1024x1024
modules: 8/8 available

[Stats]
  resolution: 1024x1024
  orientation: square
  aspect_ratio: 1:1
  brightness: bright
  contrast: medium

[OCR]
  text: "i ~( “nw lume.js ILLUMINATE YOUR UI"
  confidence: 73.1% (uncertain)
  position: top-center
  size: large

[Colors]
  dominant: white #FFFFFF (87%)
  grid:
    TL:white  TC:white  TR:white
    ML:white  MC:white  MR:white
    BL:white  BC:light gray  BR:white
  grayscale: true

[Structure]
  edge_density: low
  lines: horizontal=false, vertical=true, diagonal=false
  layout: structured

[Shapes]
  count: 4
  - polygon(7), small, bottom-center
  - polygon(7), small, bottom-left
  - polygon(6), small, bottom-center
  - polygon(8), small, bottom-right

[Faces]
  count: 0

[Codes]
  none

[EXIF]
  none

=========================
```

</details>

| # | type | question | correct answer |
|---|---|---|---|
| 1 | factual | What is the brand name in this logo? | lume.js |
| 2 | factual | What is the tagline shown beneath the brand name? | ILLUMINATE YOUR UI |
| 3 | perceptual | What does the logo's emblem depict? | A stylised sun / crescent (light) mark |
| 4 | factual | What are the main accent colours used? | Amber/orange and dark slate, on white |

## blindsight_logo.png

<details><summary>descriptor</summary>

```
=== IMAGE DESCRIPTOR ===
source: examples/images/blindsight_logo.png
size: 1024x1024
modules: 8/8 available

[Stats]
  resolution: 1024x1024
  orientation: square
  aspect_ratio: 1:1
  brightness: bright
  contrast: medium

[OCR]
  text: "MAGES SEE DATA, NOT BLINDSIGHT"
  confidence: 95.0% (reliable)
  position: center
  size: large

[Colors]
  dominant: white #FFFFFF (79%), navy blue #121154 (5%)
  grid:
    TL:white  TC:light gray  TR:white
    ML:white  MC:light gray  MR:white
    BL:white  BC:white  BR:white
  grayscale: true

[Structure]
  edge_density: low
  lines: horizontal=false, vertical=true, diagonal=false
  layout: structured

[Shapes]
  count: 3
  - polygon(7), medium, center
  - square, small, center
  - square, small, left

[Faces]
  count: 0

[Codes]
  none

[EXIF]
  none

=========================
```

</details>

| # | type | question | correct answer |
|---|---|---|---|
| 1 | factual | What is the brand name in this logo? | BLINDSIGHT |
| 2 | perceptual | What does the emblem depict? | An eye dissolving into binary digits |
| 3 | factual | What are the main colours used? | Navy blue / indigo and cyan, on white |

## portrait_face.jpg

<details><summary>descriptor</summary>

```
=== IMAGE DESCRIPTOR ===
source: examples/images/portrait_face.jpg
size: 1024x1024
modules: 8/8 available

[Stats]
  resolution: 1024x1024
  orientation: square
  aspect_ratio: 1:1
  brightness: mid
  contrast: medium

[OCR]
  text: (none detected)

[Colors]
  dominant: dark brown #402D20 (20%), gray #AE8776 (14%), gray #946E5F (12%), dark brown #362B24 (12%), salmon #CBA290 (12%)
  grid:
    TL:dark brown  TC:gray  TR:dark brown
    ML:dark gray  MC:gray  MR:brown
    BL:dark gray  BC:gray  BR:dark gray
  grayscale: false

[Structure]
  edge_density: medium
  lines: horizontal=true, vertical=true, diagonal=true
  layout: busy

[Shapes]
  count: 1
  - polygon(7), small, right

[Faces]
  count: 1
  positions: center

[Codes]
  none

[EXIF]
  none

=========================
```

</details>

| # | type | question | correct answer |
|---|---|---|---|
| 1 | factual | How many people are in this image? | 1 |
| 2 | factual | What is the dominant background colour? | Brown |
| 3 | perceptual | Is the person smiling? | Yes, a slight closed-mouth smile |
| 4 | perceptual | Approximately what is the person's age? | Early teens (~12-14) |

## landscape.jpg

<details><summary>descriptor</summary>

```
=== IMAGE DESCRIPTOR ===
source: examples/images/landscape.jpg
size: 800x533
modules: 8/8 available

[Stats]
  resolution: 800x533
  orientation: landscape
  aspect_ratio: 800:533
  brightness: bright
  contrast: medium

[OCR]
  text: (none detected)

[Colors]
  dominant: light gray #C7C9CD (16%), white #F8F0EA (13%), white #EFE8E5 (12%), dark gray #454B54 (12%), light gray #E2DCDA (12%)
  grid:
    TL:light gray  TC:light gray  TR:light gray
    ML:light gray  MC:light gray  MR:light gray
    BL:gray  BC:gray  BR:gray
  grayscale: false

[Structure]
  edge_density: low
  lines: horizontal=true, vertical=false, diagonal=false
  layout: structured

[Shapes]
  count: 1
  - blob, medium, bottom-center

[Faces]
  count: 0

[Codes]
  none

[EXIF]
  orientation: landscape

=========================
```

</details>

| # | type | question | correct answer |
|---|---|---|---|
| 1 | perceptual | Is this an indoor or outdoor scene? | Outdoor |
| 2 | factual | What is the dominant colour of the upper half of the image? | Blue sky with white clouds |
| 3 | factual | Is there any readable text in this image? | No |
| 4 | perceptual | What city or landmark is shown? | New York City (Manhattan skyline; Empire State Building) |

## street_scene.jpg

<details><summary>descriptor</summary>

```
=== IMAGE DESCRIPTOR ===
source: examples/images/street_scene.jpg
size: 800x533
modules: 8/8 available

[Stats]
  resolution: 800x533
  orientation: landscape
  aspect_ratio: 800:533
  brightness: mid
  contrast: low

[OCR]
  text: (none detected)

[Colors]
  dominant: sky blue #7FC0E9 (18%), sky blue #5FB0E0 (15%), sky blue #78BCE8 (13%), sky blue #6FB5E2 (12%), sky blue #65A2CD (11%)
  grid:
    TL:sky blue  TC:sky blue  TR:sky blue
    ML:sky blue  MC:sky blue  MR:sky blue
    BL:sky blue  BC:gray  BR:sky blue
  grayscale: false

[Structure]
  edge_density: low
  lines: horizontal=true, vertical=true, diagonal=true
  layout: structured

[Shapes]
  count: 1
  - polygon(5), medium, bottom-center

[Faces]
  count: 0

[Codes]
  none

[EXIF]
  orientation: landscape

=========================
```

</details>

| # | type | question | correct answer |
|---|---|---|---|
| 1 | factual | What is the single dominant colour in this image? | Blue |
| 2 | factual | Are there any human faces in the image? | No |
| 3 | perceptual | What objects are sitting on the table? | A patterned glass holding a plant sprig, and a clear glass jar |

## photo_square.jpg

<details><summary>descriptor</summary>

```
=== IMAGE DESCRIPTOR ===
source: examples/images/photo_square.jpg
size: 640x640
modules: 8/8 available

[Stats]
  resolution: 640x640
  orientation: square
  aspect_ratio: 1:1
  brightness: mid
  contrast: high

[OCR]
  text: (none detected)

[Colors]
  dominant: black #110C0C (13%), light gray #D8CFCA (13%), light gray #E6DCD6 (12%), light gray #C6BDB8 (12%), dark gray #4C4749 (12%)
  grid:
    TL:light gray  TC:light gray  TR:light gray
    ML:gray  MC:gray  MR:gray
    BL:dark gray  BC:dark gray  BR:dark gray
  grayscale: false

[Structure]
  edge_density: medium
  lines: horizontal=true, vertical=false, diagonal=true
  layout: busy

[Shapes]
  count: 3
  - polygon(6), large, center
  - triangle, small, bottom-center
  - rectangle, small, center

[Faces]
  count: 0

[Codes]
  none

[EXIF]
  orientation: landscape

=========================
```

</details>

| # | type | question | correct answer |
|---|---|---|---|
| 1 | factual | What text is visible in the image? | TURN TO CLEAR VISION |
| 2 | factual | How many human faces are present? | 0 |
| 3 | perceptual | Describe what is physically happening in this scene. | Looking through a coin-operated tower viewer at a hazy city skyline from an observation deck |

