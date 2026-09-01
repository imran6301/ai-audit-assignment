# A2 — Audit of `fertility.py`

## Setup
Baseline reproduction (from `starter_kit/`):

```
python fertility.py --corpus eng=corpus_sample/eng_sample.txt --corpus hin=corpus_sample/hin_sample.txt --tokenizer gpt2
```

Output:
```
eng   1.27   0.226
hin   7.45   1.579
hin is 5.89x the fertility of eng
```

This matches REPORT_v0.md exactly, confirming the environment and starting point before any changes.

## Bug 1 — Asymmetric lowercasing

`analyze()` calls `line = line.lower()` before encoding, with the comment
"lowercase so casing doesn't add noise to the comparison." This assumption
is false for Hindi.

Evidence:
```python
>>> "Hello World" == "Hello World".lower()
False
>>> "नमस्ते दुनिया" == "नमस्ते दुनिया".lower()
True
```
Devanagari has no case distinction, so `.lower()` is a no-op on Hindi text
but actively changes English text before it reaches the tokenizer. Since
GPT-2's BPE merges are case-sensitive, this asymmetrically alters English's
token count while leaving Hindi's untouched.

Measured effect (isolated in `fertility_debug.py`, toggling only `do_lower`,
split bug held constant):

| lower | eng fertility | hin fertility | ratio |
|---|---|---|---|
| True  | 1.265 | 7.448 | 5.89 |
| False | 1.229 | 7.448 | 6.06 |

Hindi fertility is invariant to this flag (as expected). English fertility
drops ~3% with lowercasing off. Net effect on the headline ratio: **+0.17
(≈3%)** — lowercasing makes English look slightly better than it should,
which slightly inflates the "Hindi is worse" ratio. Real, but small.

## Bug 2 — Double-space produces phantom empty "words"

`words = line.split(" ")` does not collapse repeated spaces:
```python
>>> "a  b".split(" ")
['a', '', 'b']
```
Both sample files contain at least one double space (e.g. `eng_sample.txt`
line "Please keep the books  in the cupboard." → counted as 8 "words"
instead of 7). This inflates the word-count denominator on affected lines,
which *deflates* fertility for those lines.

Isolated effect (split bug toggled, lowercasing held constant):

| split | eng fertility | hin fertility | ratio |
|---|---|---|---|
| buggy (unfixed) | 1.265 | 7.448 | 5.89 |
| fixed (drop empty strings) | 1.283 | 7.598 | 5.92 |

Both languages have a double-space instance in the sample files, so the
bug affects both corpora in the same direction and magnitude is small:
the ratio moves by **~0.03 (≈0.5%)**. This is a real bug in the code, but
it is not a meaningful driver of the report's headline 5.89× claim.

## Conceptual flaw — tokens-per-whitespace-word is not a cross-lingual-fair unit

The script (and the report) treat "tokens ÷ whitespace-split word count"
as directly comparable across English and Hindi, and further claim tok/char
"confirms" tok/word. Both claims are unsupported.

Evidence, from the 10 parallel sample sentences:
```python
word ratio hin/eng: 0.782   # Hindi has 22% fewer whitespace words
char ratio hin/eng: 0.647   # Hindi has 35% fewer characters
```
For the same content, Hindi needs noticeably fewer *characters* (Devanagari
is more information-dense per character) but only moderately fewer
*whitespace words* — the two ratios disagree with each other. That means
tok/word and tok/char are not independently confirming the same underlying
signal, as REPORT_v0.md Finding #2 claims; they are two different,
non-equivalent units, and their apparent "agreement" (both showing Hindi as
worse) is not evidence they are measuring the same effect correctly.
Concretely: a chunk of Hindi text delimited by whitespace often carries
more semantic content per word than the English equivalent (e.g. fused
postpositions), so a high tokens-per-word count partly reflects "Hindi
words are bigger units," not "the tokenizer handles Hindi poorly."

This is why A3 asks for denominators like per-byte or per-grapheme-cluster:
they hold something closer to "amount of content" constant across scripts,
rather than an artifact of each language's whitespace conventions.

## Checked and confirmed non-issues

- **`random.seed(1337)`**: `random` is imported and seeded but never called
  elsewhere in the file (verified via `Select-String -Path fertility.py
  -Pattern "random\."`, only one match). Dead code, no effect on output —
  not flagged as a bug since it demonstrably does nothing.
- **`unicodedata.normalize("NFC", line)`**: correct practice for
  multilingual text — normalizes Unicode into a canonical form so
  visually-identical strings don't tokenize differently due to encoding
  variants (e.g. combining vs. precomposed Devanagari characters). Verified
  this does not alter any of the sample sentences' visible content; kept
  as-is in the corrected version.

## Summary table

| Item | Type | Direction/magnitude on 5.89x ratio |
|---|---|---|
| Asymmetric `.lower()` | code bug | +≈3% (inflates Hindi-worse ratio) |
| Double-space → empty word | code bug | +≈0.5% (both langs, ~cancels) |
| tok/word not cross-lingual-fair | conceptual | not quantifiable as a %, but invalidates the "two metrics agree" claim |
| unused `random.seed` | non-issue | none |
| NFC normalization | non-issue (correct) | none |
