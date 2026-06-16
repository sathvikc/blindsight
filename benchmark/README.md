# Benchmark

This folder measures the project's two claims with no model API key required:

1. **Cost** — the text descriptor is much cheaper than sending the image.
2. **Accuracy** — on *factual* questions, the descriptor answers about as well as
   the real image; on *perceptual* questions it honestly cannot, and says so.

The cost number is fully automated. The accuracy number needs a human in the
loop (you paste prompts into whatever models you're comparing and grade the
answers), because that is the only honest way to score open-ended answers.

## Files

| File | Role |
|---|---|
| `ground_truth.json` | The questions and correct answers, each tagged `factual` or `perceptual`. |
| `run_benchmark.py`  | Generates `<name>.descriptor.txt` + `<name>.packet.txt` per image. |
| `token_savings.py`  | **Cost.** Descriptor tokens (tiktoken) vs image tokens (OpenAI / Anthropic formulas). Run it directly. |
| `make_test_sheet.py`| Builds `test_sheet.md` (readable worksheet) + `scorecard.csv` (blank grades) from the ground truth. |
| `score.py`          | **Accuracy.** Tallies a filled-in `scorecard.csv` into the headline factual-vs-perceptual table. |

## Cost — run it now

```bash
python benchmark/token_savings.py --images examples/images --results examples/results
```

Prints a per-image table and a total. Over the 11 showcase images the descriptor
path is 32% cheaper than the cheaper of the two image options — and small codes
(QR, barcode) are deliberately shown as *negative* savings, because a tiny image
is cheap to send and the honest comparison says so.

## Accuracy — the graded loop

```bash
# 1. generate descriptors + packets (if not already in examples/results)
python benchmark/run_benchmark.py --images examples/images \
    --out examples/results --questions examples/questions.json

# 2. build the worksheet and the blank scorecard
python benchmark/make_test_sheet.py

# 3. for each question, answer it twice and grade it in scorecard.csv:
#    - descriptor_grade : answer from the descriptor text alone (text model)
#    - image_grade      : answer from the real image (multimodal control)
#    grade each 1 (correct) / 0.5 (partial) / 0 (wrong)

# 4. tally
python benchmark/score.py
```

One multimodal subscription covers both conditions: paste the packet for the
text condition, attach the image for the control. No API credits required.

The headline you care about is the **factual** row of `score.py`: if the
descriptor scores high there while `token_savings.py` shows a large discount, the
project's premise holds. The perceptual row is expected to be low — that is the
tool being honest about when to fall back to real vision.
