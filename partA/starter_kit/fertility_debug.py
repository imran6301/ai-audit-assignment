import tiktoken
import unicodedata

enc = tiktoken.get_encoding("gpt2")
encode = enc.encode


def read_lines(path):
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            line = unicodedata.normalize("NFC", line)
            lines.append(line)
    return lines


def analyze(lines, do_lower, split_words):
    per_line_fertility = []
    for line in lines:
        if do_lower:
            line = line.lower()
        tokens = encode(line)
        if split_words:
            words = [w for w in line.split(" ") if w]  # fixed: drop empty strings
        else:
            words = line.split(" ")  # original buggy behavior
        per_line_fertility.append(len(tokens) / len(words))
    n = len(per_line_fertility)
    return sum(per_line_fertility) / n


corpora = {
    "eng": read_lines("corpus_sample/eng_sample.txt"),
    "hin": read_lines("corpus_sample/hin_sample.txt"),
}

combos = [
    ("original (lower=T, buggy split)", True, False),
    ("lower=F, buggy split",            False, False),
    ("lower=T, fixed split",            True, True),
    ("lower=F, fixed split (corrected)", False, True),
]

print(f"{'combo':<38}{'eng fert':>10}{'hin fert':>10}{'ratio':>8}")
print("-" * 66)
for label, do_lower, split_words in combos:
    fe = analyze(corpora["eng"], do_lower, split_words)
    fh = analyze(corpora["hin"], do_lower, split_words)
    print(f"{label:<38}{fe:>10.3f}{fh:>10.3f}{fh/fe:>8.2f}")