# Part C — Decision memo: casual tone in Hindi/Kannada/Tamil/Telugu/Bengali/Marathi

## Recommendation

**Hybrid, phased by reviewer coverage:** ship **(c) prompt-engineering only**
immediately, to all 6 languages, as the launch baseline. In parallel, use
the 2-week A100 window to build **(b) a small (≤1B) inference-time
rewriter**, trained and evaluated **only on Hindi + Kannada** — the two
languages with any native-speaker reviewer coverage. Tamil, Telugu,
Bengali, Marathi stay on prompt-engineering-only for this launch; extending
the rewriter to them is explicitly out of scope until reviewer coverage
exists for those languages too.

**Why not full SFT (path a):** SFT needs a meaningfully larger volume of
*verified* casual-register training data to avoid degrading quality, and
verification capacity here is fixed at 20 reviewer-hours total, covering
only 2 of 6 target languages. Committing the whole 2-week compute budget
to an SFT pass we can only properly verify for 1/3 of the languages is a
poor match for the constraint that's actually binding here — reviewer
coverage, not compute.

**Why not prompt-engineering only, permanently (path c alone):** it's the
safe floor (ships day 1, zero training risk, works across all 6 languages
immediately) but is typically the weakest lever for register shift —
models often only mildly adjust tone from a system prompt alone. Using it
as the *baseline* while investing spare capacity in a stronger fix for the
2 verifiable languages captures the upside without betting the whole
timeline on an unverifiable outcome.

## Assumptions (explicitly labelled)

- "No external API budget" restricts *paid* third-party API usage; using
  the org's own already-available model for synthetic data generation
  (self-distillation-style rewriting) is assumed in-budget.
- The A100-80GB is available exclusively for this project for the full 2
  weeks (no contention).
- "Casual enough" is a real, ratable dimension the reviewer can score
  consistently (assumes a short rubric is defined on day 1, not invented
  ad hoc per rating).
- A ≤1B rewriter can be meaningfully fine-tuned (e.g. via LoRA) on a
  single A100 within a few hours per iteration, leaving room for multiple
  iteration cycles inside the 2-week window.

## Back-of-envelope arithmetic

**Reviewer capacity:** 10 h/week × 2 weeks = 20 reviewer-hours total,
split across Hindi + Kannada. At ~2 minutes per rated example (rate one
casual-vs-formal pair, not write one), that's ~600 ratings total, ~300
per language — enough for both (a) a training-data quality spot-check and
(b) a held-out evaluation set, if kept small (e.g. 100 held-out eval
prompts per language, using the remaining ~200 ratings/language for
training-data verification).

**Data volume for the rewriter:** generate a larger pool of synthetic
formal→casual rewrite pairs (e.g. 3,000-5,000 per language) using the
main model itself as the generator, then have the reviewer verify/accept
a ~10-15% sample (~300-500 pairs/language) rather than every pair —
rejected-sample rate from that check becomes a data-quality estimate for
the unreviewed remainder.

**Training cost:** LoRA fine-tuning a ≤1B model on a few thousand examples
on an A100-80GB is on the order of a few GPU-hours per run, not days —
leaves room for 3-5 iteration cycles (data fixes, hyperparameter changes)
within the 2-week window, plus time for the day-1 prompt-engineering
baseline to ship independently.

## Success metric (numeric threshold)

For **Hindi and Kannada only** (the only languages we can actually
measure): on a held-out set of 100 prompts per language, the
native-speaker reviewer rates rewriter output as "casual enough" (per a
day-1-defined rubric, binary or 1-5 scale collapsed to pass/fail) at
**≥70%**, and this must be a real improvement over the prompt-engineering
baseline measured on the same 100 prompts (not just an absolute number in
isolation).

## Kill criterion

If, by **day 10 of the 14-day compute window**, a paired comparison
(≥50 prompts, reviewer picks rewriter output vs. prompt-engineering-only
output blind) shows the rewriter preferred **less than 60%** of the time,
abandon the rewriter for this launch. Ship prompt-engineering-only across
all 6 languages instead, and treat the rewriter as a post-launch
follow-up once more reviewer bandwidth (for the other 4 languages) is
available.

## Day-1 experiment

Before touching any training: run the **current model with a casual-tone
system prompt** (no fine-tuning) on ~20 hand-picked prompts each in Hindi
and Kannada, and have the reviewer give a first-pass formality rating.
This establishes the prompt-engineering baseline number the rewriter must
beat, in parallel with defining the rubric and starting synthetic data
generation for the rewriter track — so day 1 produces both a shippable
floor and the yardstick for everything after it.
