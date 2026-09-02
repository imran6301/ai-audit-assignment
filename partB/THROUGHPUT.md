# B2/B3/B4 — Throughput anomaly in the long-context sweep

## B2 — The anomaly

`reported_tok_s` climbs with batch size through batch 24 (565 → 902 →
1311 → 1607) then **drops** at batch 32 (1384) and drops further at batch
48 (1298) — the opposite of naive "bigger batch = more throughput."

This inflection point exactly coincides with `preempted_seqs` going from
0 (batches 4-24) to 7 (batch 32) to 23 (batch 48), and with `kv_cache_util`
plateauing at 0.97 instead of continuing to climb.

**Mechanism:** at batch 24, KV-cache utilization is already at 0.93 (see
B1) — near the ~25-sequence capacity ceiling calculated from the model
spec. At batch 32 and 48, the scheduler admits more concurrent sequences
than the KV cache can hold simultaneously, forcing it to preempt
(evict/pause) sequences mid-generation. Preempted sequences lose their
in-progress KV cache state and must be re-processed (partial re-prefill)
when resumed, so a growing share of total compute is spent on
recomputation rather than new-token generation — this is why aggregate
`reported_tok_s` falls even as batch size (nominal parallelism) rises.
`e2e_ms_p95` confirms this from the user side: it more than doubles from
batch 24 (69.2s) to batch 48 (105.4s), showing individual requests wait
far longer even while the aggregate throughput counter looks only
mildly degraded.

**Proposed fix:** cap the admitted batch size (or effective concurrent
sequence count) at or below the KV-cache-derived ceiling (~24-25
sequences for 4096-token sequences on this GPU/config, per B1), rather
than allowing the scheduler to over-admit and rely on preemption to
recover. Predicted effect: batches at or below ~24 concurrent long
sequences should avoid preemption entirely (as batches 4-24 already show,
`preempted_seqs=0` throughout), preserving throughput growth instead of
the observed regression, at the cost of queuing excess requests rather
than admitting and later evicting them.

## B3 — Root cause and honest goodput

**The misread column:** `reported_tok_s` is computed as
`(prompt_len + gen_len) × num_requests / wall_clock_s` — i.e. it counts
one-time prefill tokens and per-step decode tokens identically. Verified
directly: `(3584+512)×24/61.16 = 1607.3`, matching the batch-24
`reported_tok_s` value (1607.4) almost exactly; same match at batch 16
long-prompt (1311.5 vs 1311.4) and batch 16 short-prompt (883.4 vs 883.2).

Prefill tokens are processed in one parallel pass and are cheap per-token;
decode tokens are produced sequentially, one per step, gated by memory
bandwidth, and are what a user is actually waiting on. Blending the two
into one "tok/s" number makes long-prompt/short-generation configurations
look artificially fast, since most of their counted "tokens" are cheap
prefill, not the slow autoregressive decode a user experiences as latency.

**Honest decode goodput at batch 24, two independent derivations:**

1. Wall-clock method: generated tokens only ÷ wall clock time:
   `24 × 512 / 61.16 = 200.9 tok/s`
2. Inter-token-latency method: `1000 / itl_ms_p50` gives per-sequence
   decode rate; multiplied by batch size (sequences decode in parallel):
   `(1000 / 96.07) × 24 = 249.8 tok/s`

Both land far below the reported 1607.4 tok/s (roughly 6-8× lower). They
don't match each other exactly because the wall-clock method includes the
one-time prefill/TTFT delay (pessimistic, "request to done") while the ITL
method measures only steady-state decode speed once generation is
underway (optimistic, "once it's running"); true user-perceived goodput
sits between the two.

**What the report should have said:** instead of "longer prompts give
better throughput; batch 48 will deliver ~3200 tok/s," it should have
reported that `reported_tok_s` conflates prefill and decode tokens, that
true decode goodput at batch 24 is ~200-250 tok/s (not 1607), and that
batch 48 is not a valid linear extrapolation point at all — it is already
deep in KV-cache-preemption territory (23/48 sequences preempted per the
log), where throughput is actively regressing, not scaling.

## B4 — Metric to confirm the B2 mechanism

To directly confirm that preemption-driven recomputation (not some other
cause) is responsible for the batch-32/48 throughput drop, the metric to
pull is **the count (or %) of re-prefilled / recomputed prompt tokens per
second from the serving engine's internal scheduler stats** (e.g. vLLM
exposes this as recompute or "preemption recompute" counters; other
engines expose similar "tokens re-processed due to eviction" stats),
rather than relying only on `preempted_seqs` and `kv_cache_util`, which
show that preemption is *happening* but not how much *wasted work* it is
causing. If the B2 mechanism is correct, this metric should be ~0 for
batches 4-24 (matching `preempted_seqs=0`) and should rise sharply at
batch 32 and further at batch 48, tracking the `preempted_seqs` counts
(7 and 23) — with the recomputed-token volume large enough to plausibly
account for the ~14% drop in `reported_tok_s` between batch 24 and batch
32 (1607.4 → 1384.0), since each preempted sequence's partially-completed
prefill work would need to be redone from scratch on resumption.
