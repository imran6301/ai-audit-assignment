"""
fertility_corrected.py
Corrected cross-language tokenizer analysis: real FLORES-200 corpus,
2 tokenizers, 3 denominators, bugs from AUDIT.md fixed.
"""
import tiktoken
from transformers import AutoTokenizer

# ---- tokenizers ----
gpt2_enc = tiktoken.get_encoding("gpt2")
xlmr_tok = AutoTokenizer.from_pretrained("xlm-roberta-base")

tokenizers = {
    "gpt2": lambda s: gpt2_enc.encode(s),
    "xlm-roberta": lambda s: xlmr_tok.encode(s, add_special_tokens=False),
}

# ---- corpus ----
langs = ["eng", "hin", "kan", "tam"]
N = 200  # slice size, keep it small for now

corpora = {}
for lang in langs:
    with open(f"corpus_real/{lang}_flores.txt", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    corpora[lang] = lines[:N]

# ---- denominators ----
def word_count(line):
    # FIXED: drop empty strings from double/leading/trailing spaces
    return len([w for w in line.split(" ") if w])

def byte_count(line):
    return len(line.encode("utf-8"))

def grapheme_count(line):
    # approximation without extra deps: count unicode codepoints
    # (true grapheme clustering needs the `grapheme` or `regex` package;
    # we'll upgrade this if time allows, and document it as a limitation)
    return len(line)

denominators = {
    "word": word_count,
    "byte": byte_count,
    "grapheme_approx": grapheme_count,
}

# ---- run ----
results = {}  # results[tokenizer][lang][denom] = avg ratio
for tok_name, encode in tokenizers.items():
    results[tok_name] = {}
    for lang in langs:
        lines = corpora[lang]
        sums = {d: 0.0 for d in denominators}
        for line in lines:
            # FIXED: no lowercasing (bug from AUDIT.md removed)
            n_tokens = len(encode(line))
            for dname, dfunc in denominators.items():
                denom_val = dfunc(line)
                sums[dname] += n_tokens / denom_val
        results[tok_name][lang] = {d: sums[d] / len(lines) for d in denominators}

# ---- print table ----
for tok_name in tokenizers:
    print(f"\n=== tokenizer: {tok_name} ===")
    print(f"{'lang':<6}{'tok/word':>12}{'tok/byte':>12}{'tok/graph':>12}")
    for lang in langs:
        r = results[tok_name][lang]
        print(f"{lang:<6}{r['word']:>12.3f}{r['byte']:>12.4f}{r['grapheme_approx']:>12.4f}")