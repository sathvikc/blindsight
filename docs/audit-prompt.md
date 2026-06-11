# Reusable Code-Audit Prompt

A standing, project-aware prompt for auditing this library. It is **not** tied to
any one branch or feature. Use it any time to get an independent, skeptical
review — either of the whole branch or of just the latest changes.

Open a **fresh session at the repo root**, pick a mode below, and paste the
**Shared Context** block followed by the block for that mode.

- **Mode A — Whole branch / full feature.** Audits everything the current branch
  adds on top of its base (or the whole module if you point it at one). Use when
  you want a complete review of a feature before merging.
- **Mode B — New changes only.** Audits just the most recent change set (latest
  commit, or uncommitted work). Use for a fast review of an incremental edit
  without re-reviewing the whole branch.

The auditor is told to **report only — make no code changes**.

---

## Shared Context (paste first, for either mode)

```
You are auditing this repository as an INDEPENDENT, SKEPTICAL reviewer. Your job
is to find problems, not to validate work. Assume the author may have
overfitted to example images or made changes that look good on the showcase but
won't generalise. Prefer concrete, reproducible findings over vibes.

PROJECT GOAL (judge everything against this)
- This is a classical computer-vision library (NO machine learning, NO model
  inference) written in Python. It turns an image into a COMPACT, STRUCTURED
  TEXT descriptor.
- The descriptor's purpose: let a TEXT-FIRST language model answer factual
  questions about the image cheaply, from the text alone, without seeing the
  pixels. So every line in the descriptor must (a) be something classical CV can
  actually justify from the image, and (b) earn its token cost by helping a
  model answer real questions — not add noise.
- Two non-negotiables: HONESTY (never assert a detail the geometry/CV does not
  support; decline ambiguous cases rather than guess) and GENERALISATION (rules
  must key on relative geometry / image-independent reasoning, never on the
  specific pixels, labels, or coordinates of the example images).

ORIENT YOURSELF FIRST
- Read README.md for the intended scope and module list.
- Skim blindsight/ (the package), tests/, and examples/results/*.descriptor.txt
  (sample descriptors as a model would receive them).
- Note: some files in the repo are intentionally excluded from version control
  and from scope. Audit only tracked source, tests, and example outputs.

WHAT TO EVALUATE
1. Goal alignment: does each piece of output actually help a TEXT-ONLY model
   answer questions, or does it add tokens/noise? Read the rendered descriptors
   and judge as if you were the LLM consuming them.
2. Overfitting hunt (the #1 risk): for every threshold, ratio, or heuristic, ask
   "is this a principled rule on RELATIVE geometry, or is it tuned to the sample
   images?" Try to construct an input that breaks it.
3. False positives: could the code invent a relation/detection that isn't really
   there (a spurious alignment, a wrong containment, a mislabelled structure)?
   Check that any "conservatism" claims in comments actually hold.
4. Honesty on unstructured inputs (photos, scenery): confirm it does not
   fabricate structure where there is none.
5. Tests: are they genuinely held-out (synthetic, not the showcase coordinates),
   or do they secretly encode the example images? What cases are MISSING
   (e.g. right-to-left text, rotation/skew, dense tables, ties, multi-element
   gaps, empty input, huge inputs)? Run the suite:
     source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/ -q
6. Backward compatibility: do changes leave existing modules' output unchanged
   unless that change was the explicit intent?
7. Code quality: dead code, unclear naming, duplicated logic, anything that
   silently won't generalise.

DELIVERABLE
- A one-line VERDICT: is the code under review sound and merge-ready toward the
  project goal? (yes / yes-with-fixes / no)
- A PRIORITISED list of concrete issues. For each: a file:line reference, a tag
  from [overfit] [false-positive] [honesty] [missing-test] [compat] [quality],
  the problem, and a suggested fix.
- At least one ADVERSARIAL input you actually reasoned through that the code
  gets wrong or handles awkwardly (or state clearly that you could not find one).
- Anything that is well-designed and should NOT be changed (so good decisions
  aren't accidentally undone later).

Do NOT modify any files. Report only.
```

---

## Mode A — Whole branch / full feature

```
SCOPE: the entire set of changes this branch adds on top of its base branch,
reviewed as one coherent feature.

Determine the scope yourself:
- Identify the base: `git merge-base HEAD main` (fall back to `master` or the
  repo's default branch if `main` does not exist).
- Review the full diff:  `git diff <base>..HEAD`
- List touched files:     `git diff --name-only <base>..HEAD`
- Read each changed/added source file IN FULL (not just the diff hunks) so you
  judge the design, not only the edits.

Then carry out the evaluation from the Shared Context against this whole-branch
scope and produce the deliverable.
```

---

## Mode B — New changes only

```
SCOPE: only the most recent change set — do not re-review the rest of the branch
except as needed to understand the new code.

Determine the scope yourself, in this order of preference:
- If there are uncommitted changes (`git status --porcelain` is non-empty):
  review `git diff HEAD` (unstaged + staged: `git diff HEAD`) plus any untracked
  files shown by `git status`.
- Otherwise review the latest commit only: `git show HEAD` and
  `git diff HEAD~1..HEAD`.
- List the touched files and read each one enough to judge the new lines IN
  CONTEXT (open the surrounding function/module, not just the hunk).

Focus the evaluation from the Shared Context on what these specific changes add
or alter: do they generalise, stay honest, avoid false positives, carry
adequate held-out tests, and leave unrelated output unchanged? Produce the
deliverable scoped to these changes.
```

---

## Notes

- Run `pytest` as part of every audit — a green suite that only encodes the
  sample images is worse than a red one; the auditor is asked to check both.
- If the auditor finds an overfitting or false-positive issue, the fix should be
  validated with a **new held-out synthetic test** (image-independent), never by
  tuning a threshold until the showcase passes.
- This prompt is intentionally generic. It will stay valid as new modules are
  added, because it audits against the project goal rather than a fixed feature.
