# NOTEBOOK.md — chronological log

## Day 1 — Setup

- Confirmed Python + git installed. Created GitHub repo, local folder
  structure (`partA/partB/partC`, `partA/starter_kit/`).
- Set up venv, installed `tiktoken`, `transformers`, `sentencepiece`.
- **Dead end / friction:** ran the baseline `fertility.py` command using
  bash-style `\` line continuation in PowerShell — PowerShell doesn't
  support `\` for line continuation (uses backtick `` ` `` instead), threw
  parser errors. Fixed by putting the command on one line.
- Reproduced the baseline numbers exactly: eng fertility 1.27, hin 7.45,
  ratio 5.89x. This became the fixed reference point for everything after.
- **Recurring friction throughout the project:** the venv silently
  "de-activated" between terminal sessions/tabs multiple times (visible as
  `(.venv)` missing from the prompt, or `pip install` reporting packages
  going to the global `AppData\Roaming\Python` site-packages instead of
  `.venv`). Caused `ModuleNotFoundError` for `tiktoken` and later
  `datasets` more than once. Fixed each time by re-running
  `.venv\Scripts\Activate.ps1` and checking `(Get-Command python).Source`
  actually pointed inside `.venv`. Lesson: always verify the interpreter
  path, not just the `(.venv)` prompt text, before trusting an install.

## Day 1-2 — A2: auditing fertility.py

- Read through `analyze()` line by line. Two candidate bugs stood out from
  the comments: `.lower()` (comment claimed it removes noise) and
  `line.split(" ")` (naive whitespace split).
- **Hypothesis 1:** `.lower()` is not neutral across languages, since
  Devanagari has no case. Verified: `"नमस्ते दुनिया" == "नमस्ते दुनिया".lower()`
  is `True`, but the same check on an English string is `False`.
- **Hypothesis 2:** double spaces in the sample files (found one in
  `eng_sample.txt`: "books  in") produce phantom empty-string "words"
  from `.split(" ")`, inflating the word-count denominator and deflating
  fertility on affected lines.
- Built `fertility_debug.py` to isolate each bug independently (4 runs:
  original, lower-off, split-fixed, both-fixed) and measured the actual
  effect on the eng/hin ratio, rather than assuming either bug's
  direction or size.
- **Result, and a bit of a surprise:** the lowercase bug moved the ratio
  by ~3% (5.89 → 6.06 with lowercasing off) — real but small. The
  double-space bug moved it by <1%, because — checked — both corpora
  have a double-space instance, so the effect roughly cancels in the
  *ratio* even though it's a real per-line bug. Initially expected the
  double-space bug to matter more since it looked like the more obviously
  "wrong" code; the isolated measurement showed the opposite.
- **The harder-to-see issue:** spent the most time on whether tok/word is
  even a fair cross-lingual unit at all. Computed word-count and
  char-count ratios between parallel eng/hin sentences directly:
  hin/eng word ratio ≈ 0.78, hin/eng char ratio ≈ 0.65. These disagree
  with each other, which undercuts the report's claim that tok/word and
  tok/char "confirm" each other — they're measuring different things
  that happen to point the same direction, not the same thing measured
  twice.
- Checked `random.seed(1337)` via `Select-String -Pattern "random\."` —
  confirmed `random` is never called anywhere else in the file, so the
  seed does nothing. Considered flagging it as a bug on first read
  (looked suspicious), but the evidence rule meant checking first —
  decided not to flag it since it provably has zero effect.
- Checked `unicodedata.normalize("NFC", ...)` — confirmed this is correct
  practice for multilingual text (canonicalizes Unicode representation),
  not a bug.

## Day 2 — A1: building the real corpus

- Original sample corpora were only 10 sentences each — needed a real
  multilingual set (≥4 languages, including 2 Dravidian).
- **Dead end:** first attempt to load `facebook/flores` via
  `load_dataset(..., trust_remote_code=True)` failed —
  `trust_remote_code` is no longer supported by the current `datasets`
  library version, and separately the dataset turned out to be gated
  (requires HF account + accepting terms + auth token).
- Considered using a non-gated mirror (`Muennighoff/flores200`) as an
  alternative to avoid the auth step, but ended up authenticating
  properly instead (created HF token, `hf auth login`, accepted dataset
  terms on the HF website) and used the official `facebook/flores`
  dataset directly.
- Loaded `eng_Latn`, `hin_Deva`, `kan_Knda`, `tam_Taml`, `devtest` split.
  Verified all four report 1012 rows and that row 0's `id` field matches
  across languages (`id: 1`), confirming genuine sentence-level alignment
  rather than four independently-sized files.
- Dumped to `corpus_real/{lang}_flores.txt`, one sentence per line, no
  preprocessing applied at this stage (preprocessing choices are applied
  explicitly later, inside the analysis script, so their effects stay
  measurable — this mirrors the lesson from the A2 audit about not
  silently baking in transformations).

## Day 2-3 — A3: corrected analysis

- Picked two tokenizers: GPT-2 (matches the original report, for
  contrast) and `xlm-roberta-base` (multilingual-aware).
- Built `fertility_corrected.py` with the A2 bug fixes applied (no
  lowercasing, split fixed to drop empty strings from double spaces) and
  three denominators: tok/word, tok/byte, tok/grapheme (approximated as
  raw codepoint count — flagged as an approximation, not true grapheme
  clustering, in the script's own comments, since true clustering needs
  an extra dependency not otherwise required).
- Ran on a 200-sentence slice per language (kept small deliberately —
  faster to debug, and the assignment doesn't require using the full
  corpus for the exploratory pass).
- **Key result, and the most surprising one of the whole project:** under
  GPT-2, Kannada/Tamil tok/byte ratios vs English were ~4.7-4.8x (roughly
  matching or exceeding the original report's framing). Under
  XLM-RoBERTa, the same three languages came out *cheaper* than English
  per byte (ratios ~0.43-0.49x) — a full inversion, produced by nothing
  except changing which tokenizer was used. This directly undercuts the
  original report's claim that the fertility gap is "a property of the
  script, not the tokenizer."
- Worked through which denominator should actually drive a routing
  decision: rejected tok/word (established in A2 as confounded by
  language-specific whitespace conventions), and reasoned that tok/byte
  is the more defensible choice since UTF-8 byte count is what's
  actually billed/transmitted, independent of a language's word
  segmentation habits.

## Day 3 — B1: KV-cache capacity

- Computed KV-cache bytes/token from the model spec:
  `2 × 28 layers × 8 KV-heads (GQA, not the 24 Q-heads) × 128 head_dim ×
  2 bytes (fp16) = 114,688 bytes/token`.
- Computed weights size (8.4 GB) and remaining KV budget after weights +
  overhead (~12.08 GB), giving a predicted max of ~25 concurrent
  4096-token sequences.
- Checked against `bench_log.csv`: `kv_cache_util` reaches 0.93 (near
  capacity, no preemption) at batch 24, and `preempted_seqs` first
  becomes nonzero at batch 32 — brackets the predicted ~25 ceiling
  closely, validating the arithmetic against real scheduler behavior.

## Day 3 — B2-B4: throughput anomaly

- Noticed `reported_tok_s` rises with batch size up through batch 24,
  then *falls* at batch 32 and 48 — coincides exactly with
  `preempted_seqs` going nonzero.
- **Hypothesis:** preemption forces recomputation of evicted sequences'
  progress, wasting compute and dragging down aggregate throughput.
- Computed goodput two independent ways at batch 24 (generated-tokens ÷
  wall-clock: ~201 tok/s; and via `itl_ms_p50`: ~250 tok/s) — both far
  below the reported 1607.4 tok/s figure, confirming `reported_tok_s`
  overstates real generation speed substantially.
- **Traced the root cause directly:** tested whether `reported_tok_s`
  counts prompt tokens too, not just generated ones. Computed
  `(prompt_len+gen_len)×num_requests/wall_clock_s` for three rows and
  got near-exact matches to the logged `reported_tok_s` values (1607.3
  vs 1607.4, 1311.5 vs 1311.4, 883.4 vs 883.2) — confirmed the column
  blends cheap one-shot prefill tokens with slow sequential decode
  tokens, which is why prompt-heavy rows look artificially fast and why
  the report's "longer prompts = better throughput" and "batch 48 ≈
  3200 tok/s" conclusions don't hold up.

## Day 3-4 — Part C and wrap-up

- Worked through the three options against the actual constraints —
  the binding constraint turned out to be reviewer coverage (only
  Hindi + Kannada have any native-speaker review capacity, out of 6
  target languages), not compute or timeline, which shaped the final
  recommendation toward a phased approach rather than picking one path
  outright for all six languages.
- Cleaned up repo structure; fixed a couple of git/PowerShell friction
  points along the way (branch name `master` vs `main`, files created
  but not yet `git add`ed, path issues running scripts from the wrong
  working directory relative to `corpus_real/`).

## Open questions / things I'd do with more time

- True grapheme-cluster counting (rather than the raw-codepoint
  approximation used) for a more accurate per-grapheme denominator.
- Running the corrected analysis on the full 1012-sentence corpus rather
  than the 200-sentence slice, to check the tokenizer-inversion result
  holds at scale.
- Confirming the B4 recompute-counter recommendation against the actual
  serving framework in use, rather than a general vLLM-style assumption.
