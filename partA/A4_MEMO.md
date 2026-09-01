# A4 — Recommendation memo

## Corrected headline numbers

The original report's 5.89× Hindi-vs-English "fertility" gap (tok/word,
GPT-2) is not a reliable basis for a cost/routing decision — it conflates
tokenizer inefficiency with an unrelated artifact of whitespace-word
segmentation (see AUDIT.md), and was measured on 10 unrepresentative
sentences (see CORPUS.md).

On a 200-sentence slice of FLORES-200 (real parallel corpus, 4 languages),
measuring **tokens per UTF-8 byte** — the denominator that actually holds
constant what a routing decision cares about (see ANALYSIS.md) — the
picture is:

| lang | GPT-2 (tok/byte, ratio to eng) | XLM-RoBERTa (tok/byte, ratio to eng) |
|---|---|---|
| eng | 1.00× | 1.00× |
| hin | 2.87× | 0.49× |
| kan | 4.72× | 0.48× |
| tam | 4.80× | 0.43× |

## Recommendation

**Do not route Indic traffic to a separate model/pipeline as a cost
mitigation.** The original report's root cause ("this is a property of the
script, not the tokenizer") is contradicted by our data: switching only the
tokenizer (GPT-2 → a multilingual-aware tokenizer) inverts the entire
result — Hindi/Kannada/Tamil go from costing ~3-5× English to costing
*less* than English. The dominant driver of serving cost here is
**tokenizer vocabulary coverage for Indic scripts, not an inherent property
of the languages.**

**Concrete recommendation:** evaluate and adopt a production tokenizer
with genuine multilingual training coverage (not necessarily
XLM-RoBERTa specifically — it's an encoder tokenizer, not built for
generation; evaluate generation-capable multilingual tokenizers, e.g.
those behind mT5/BLOOM/Llama-3-class multilingual vocabularies) before
committing to a 6× cost budget or a separate routing path. A tokenizer
swap is a one-time engineering cost; a permanent 6× serving-cost budget
is a recurring one, and our evidence suggests it is not necessary.

## Biggest caveat

FLORES-200 is professionally-translated, formal news/reference prose —
not the casual conversational text this system actually needs to serve
(see CORPUS.md and Part C). Fertility on formal text may not transfer
directly to fertility on casual/code-mixed chat-style input, which often
mixes scripts and includes informal spellings. This analysis establishes
that **tokenizer choice matters far more than language identity** for
Indic serving cost — it does not establish the exact multiplier for
production traffic, which should be re-measured on real (anonymized)
traffic samples before finalizing a cost budget.

## Metric to monitor in production

**Tokens generated per UTF-8 byte of output, segmented by language**,
tracked continuously post-launch. If a newly-adopted tokenizer's
real-traffic byte-efficiency for Hindi/Kannada/Tamil drifts materially
worse than what this offline FLORES-based analysis predicted, that is the
signal this analysis's domain-mismatch caveat was significant enough to
revisit the recommendation.
