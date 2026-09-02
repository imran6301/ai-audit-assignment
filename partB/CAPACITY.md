# B1 — KV-cache capacity from the model spec

## (a) KV-cache bytes per token

Formula: `2 (K and V) × n_layers × n_kv_heads × head_dim × bytes_per_element`

From `model_spec.md`: n_layers = 28, n_kv_heads (GQA) = 8 (not the 24 Q
heads — GQA shares K/V across groups of Q heads, which is the whole point
of GQA reducing KV cache size), head_dim = 128, KV cache precision = fp16
→ 2 bytes/element.

```
2 × 28 × 8 × 128 × 2 = 114,688 bytes/token  (~112 KB/token)
```

## (b) Max concurrent 4096-token sequences

**Weights:** 4.2B params × 2 bytes (fp16) = 8.4 GB.

**Memory available for KV cache:**
```
(24 GB × 0.92 gpu_memory_utilization) − 8.4 GB (weights) − 1.6 GB (overhead)
= 22.08 − 8.4 − 1.6
= 12.08 GB
```

**Bytes needed per full-length (4096-token) sequence:**
```
114,688 bytes/token × 4096 tokens = 469,762,048 bytes (~469.76 MB)
```

**Max concurrent sequences:**
```
12.08e9 / 469.76e6 = 25.72 → floor to 25
```

**Predicted max: 25 concurrent 4096-token sequences.**

## Checking the prediction against bench_log.csv

The `prompt_len=3584` rows have `prompt_len + gen_len = 3584 + 512 = 4096`,
matching `max_model_len` — these are the full-length-sequence rows to
check against.

| batch_size | kv_cache_util | preempted_seqs |
|---|---|---|
| 4  | 0.16 | 0 |
| 8  | 0.31 | 0 |
| 16 | 0.62 | 0 |
| 24 | 0.93 | 0 |
| 32 | 0.97 | 7 |
| 48 | 0.97 | 23 |

`kv_cache_util` climbs roughly linearly with batch size up to batch 24
(0.93, still under capacity, no preemptions). At batch 32, `preempted_seqs`
becomes nonzero (7) — the scheduler ran out of KV cache room and had to
evict/pause sequences mid-flight, and `kv_cache_util` plateaus at 0.97
(cache saturated) rather than continuing to climb.

**This matches the prediction well**: the last fully-healthy batch (24) and
the first batch that overflows (32) bracket the predicted ceiling of ~25
concurrent sequences almost exactly. The small gap between the predicted
25 and the observed transition (which happens somewhere between 24 and 32)
is consistent with real-world factors the idealized formula doesn't
capture — memory fragmentation, scheduling granularity (requests are
likely admitted/evicted in blocks, not one at a time), and the
`gpu_memory_utilization=0.92` safety margin already baked into the
prediction.
