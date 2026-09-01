# A1 — Real multilingual eval corpus

## Source
FLORES-200 (`facebook/flores` on Hugging Face), `devtest` split, accessed via
the `datasets` library after authenticating with a Hugging Face token
(dataset is gated, requires accepting terms on the dataset page).

## Languages
Four languages, chosen per the assignment's requirement (English, Hindi,
plus two Dravidian languages):

| code | language | script |
|---|---|---|
| eng_Latn | English | Latin |
| hin_Deva | Hindi | Devanagari |
| kan_Knda | Kannada | Kannada |
| tam_Taml | Tamil | Tamil |

## Size
1012 sentences per language, fully parallel (same underlying content
translated into every language, matched by a shared `id` field). Verified
alignment by checking `hin[0]['id'] == eng[0]['id'] == 1` and that all four
splits report exactly 1012 rows.

## Domain
FLORES-200's `devtest` split is sourced from Wikinews, Wikijunior, and
Wikivoyage articles (confirmed via the `domain`/`topic` fields on individual
rows, e.g. `domain: wikinews`, `topic: disease, research, canada`). This is
professionally translated, edited, **formal written prose** — news-article
and reference-style text, translated by professional translators rather
than scraped or machine-translated.

## Preprocessing
Each sentence was written one-per-line to `corpus_real/{lang}_flores.txt`,
with only `\n` characters inside a sentence replaced by a space and
leading/trailing whitespace stripped. No lowercasing, no Unicode
normalization, and no other transformation was applied at this stage —
any such steps are applied later, explicitly, inside the analysis script,
so their effect can be measured in isolation (see AUDIT.md).

## What this corpus can and cannot tell you

**Can tell you:** a fair, script-verified, sentence-aligned comparison of
tokenizer behavior across four languages on formal, edited, encyclopedic/
news-style prose — the kind of writing typical of documentation, articles,
or formal assistant replies.

**Cannot tell you:**
1. **Domain mismatch with the actual use case.** Part C of this assignment
   is about making assistant replies sound *casual and conversational* in
   Hindi/Kannada/Tamil/etc. FLORES-200 is the opposite register — formal,
   edited news prose, not casual chat, SMS-style code-mixing, or spoken
   colloquial phrasing. Tokenizer fertility measured here may not reflect
   fertility on the actual target text style; colloquial text often
   includes code-switching (mixing English words into Hindi sentences,
   for instance), which this corpus does not contain at all.
2. **Sample size caveat.** 1012 sentences per language is far larger than
   the original 10-sentence toy sample, but still small relative to
   production traffic; per-line fertility can be noisy, and 1012
   professionally-written sentences may not capture the long tail of
   real user inputs (typos, mixed scripts, very short queries, etc.).
3. **Script coverage, not dialect/register coverage.** Kannada and Tamil
   here are standard/formal written registers; regional dialectal
   variation, script romanization (writing Indic languages in Latin
   script, common in informal chat), and mixed-script inputs are not
   represented.