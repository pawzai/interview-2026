# Generative AI Cheatsheet

Fast revision. Every claim here is expanded in [answers.md](answers.md); question numbers are the index. Treat every absolute figure as an **order of magnitude to reason with** - prices, context limits and tokens per second all moved last quarter, and interviewers know it. Show the arithmetic, not the memorized number.

---

## 1. Transformer behavior that changes your design

| Fact | Consequence |
| --- | --- |
| Generation is serial - one forward pass per token | Latency ∝ output tokens. No hardware fixes it. Stream, or be shorter (Q1) |
| Attention is O(n²) in sequence length | Long context costs superlinearly. Memory, not FLOPs, is the wall (Q3) |
| Facts live superposed in FFN weights | Not editable, not citable, not permissionable. Facts belong in retrieval or tools (Q5) |
| Attention profile is U-shaped (primacy + recency) | Critical instructions at the **end**. Middle of a long prompt is effectively invisible (Q7) |
| RoPE + post-training context extension | Advertised window ≠ trained length ≠ effective context. Measure your own (Q6, Q26) |
| MoE: memory scales with total params, compute with active | Cheap per token on an API, expensive to self-host (Q10) |
| Preference alignment produces sycophancy and confidence | Cannot be fixed by asking nicely. Fix with framing + evaluation that does not reward agreement (Q8) |

Pipeline stages: **pretraining** = knowledge → **SFT** = instruction-following and format → **preference tuning** = tone, helpfulness, refusal.

---

## 2. Token arithmetic

| Content | Tokens |
| --- | --- |
| English prose | ~4 chars/token, ~0.75 words/token |
| Code | ~3 chars/token |
| JSON | Expensive - braces, quotes, repeated keys |
| Non-Latin scripts | 2-4x English for the same meaning |
| A page of text | 500-700 tokens |
| A high-res image | 1,500-3,000 tokens |
| Base64 / UUID | ~1 token per 2-3 chars, all waste |

**Budget sections** (Q18): output reserve (subtract first) · system prompt · tools (100-300 each) · few-shot · retrieved context · history · user input. Cut order under pressure: history → retrieved chunks → examples. Never silently truncate user input.

**Prompt caching** (Q21): caches the KV state of a **prefix**. Read at ~10 percent of input price. Order = static first, volatile last. Killed by a timestamp, a request id, a user name, or unstable serialization near the top. Well-structured chat = 60-90 percent of input tokens cached.

Input is cheap, **output is 3-5x** (prefill is compute-bound and batched; decode is memory-bandwidth-bound) - Q19.

Cost doubled with no change? Check in order (Q20): output length → history growth → **cache hit rate collapse** → provider model change → retrieval returning more.

---

## 3. Decoding

| Knob | Effect |
| --- | --- |
| Greedy | argmax, no sampling randomness |
| Temperature | Divides logits before softmax. Sharpens (<1) or flattens (>1) |
| Top-k | Fixed candidate count |
| Top-p (nucleus) | Adaptive candidate set by cumulative probability. Best default |
| Repetition/frequency/presence penalties | **Zero for code and JSON** - keywords and syntax must repeat |

**Temperature 0 is not deterministic** (Q30): batch-dependent floating-point reduction order · MoE routing · a changed serving artifact (quantization, stack, build) · non-sampler variance upstream. Seeds fix one of four (Q40).

Set temperature *or* top-p, not both aggressively - they compose and double-count (Q31).

| Technique | Use |
| --- | --- |
| Constrained decoding | Guarantees schema validity by logit masking. Put a `reasoning` field **first** or you lose accuracy (Q36, Q89) |
| Speculative decoding | Draft model proposes k, target verifies in one pass. Exact same distribution. 2-3x at low batch, useless at high batch (Q37) |
| Self-consistency (n samples) | Best model-side confidence signal. Fails on *systematic* errors (Q38) |
| Beam search | For translation and ASR. Never for chat - highest-likelihood text is bland (Q33) |

Defaults: **code** T≈0-0.2, penalties 0 · **summarizer** T≈0.3-0.7 · **extractor** T=0 + constrained decoding (Q42).

---

## 4. Model selection

Apply the axes in this order (Q43): **hard constraints** (residency, licence, approval) → capability on your eval set → latency profile → cost at your volume → operational maturity (rate limits, deprecation policy) → exit cost.

| Benchmark red flag | Why (Q45-46) |
| --- | --- |
| Two points apart | Inside the noise at n=200 (±4 points) |
| Top of the board >90 percent | Saturated, cannot discriminate |
| Older than the training cutoff | Contaminated |
| Vendor-run | Harness and prompt optimized |

Test for memorization: rename variables, change numbers, reorder options. Real capability barely moves.

| Licence | Reality |
| --- | --- |
| Apache 2.0 / MIT | Genuinely permissive, patent grant |
| Llama-style community | Commercial with an acceptable-use policy, naming, sometimes output-training restrictions |
| Research-only | Unusable in a product, and a trap for prototypes |

**Routing** (Q53): by task (default, predictable) · by predicted difficulty (router has its own error rate) · escalate on failure (best accuracy per rupee). Cascade pays while escalation rate e < 1 − (c+v)/S - so almost always, **provided the validator is cheap** (Q222).

---

## 5-6. Prompting and structured output

System prompt order (Q60): role → environment → tools (and when *not* to use each) → policy → method → output contract → examples → **restated critical constraints at the end**.

| Rule | Why |
| --- | --- |
| Rules in the system prompt, data in the user message | Otherwise your policy and injected text have equal standing (Q59) |
| Positive over negative instructions | Mentioning a concept activates it; a prohibition specifies no alternative (Q65) |
| 2-5 few-shot examples, covering hard cases | A fifth can hurt: spurious patterns, dilution, contradiction (Q61-62) |
| Fence and escape every interpolated variable | Strip your own delimiter from user text (Q69) |
| Hard requirements are not prose | Schema, enum, validator, guardrail - not a sentence (Q67) |
| Prompts are code | Repo, PR, review, eval run attached, canary, one-minute rollback (Q68) |

| Structured output | Reliability |
| --- | --- |
| Prompt and parse | 85-98 percent. Fails on preamble, fences, truncation |
| JSON mode | Valid JSON, not necessarily your schema |
| Schema-constrained decoding | ~100 percent schema-valid. Still not semantically correct (Q79) |

Schema design (Q78): **good** - meaningful names, per-field `description`, `enum`, flat. **Ignored** - `pattern`, `format`, ranges, `minItems`. **Harmful** - deep nesting, `oneOf` unions, 300-value enums, recursion.

Abstention must be **representable** or the model must invent: nullable + a description saying "use null, do not infer", explicit sentinels (`NOT_PRESENT` vs `ILLEGIBLE`), a verbatim `source_text` field, `needs_review`. And do not score a guess the same as a null (Q81).

**Never accept an identifier the model generated** (Q84, Q172). Resolve server-side, constrain to live enums, authorize from the session. Batched tool calls are read-only; writes are one per turn, idempotent (Q85).

Repair loop (Q80): feed the **specific error** back, max two retries, truncation handled separately (raise `max_tokens` or split - do not blind-retry), then a defined failure. Monitor the repair rate.

---

## 7. Embeddings

| Fact | Consequence |
| --- | --- |
| Trained for *distributional* similarity | Opposites score 0.94. Never a semantic-equivalence test (Q93) |
| Normalized vectors: cosine = dot, and Euclidean is monotone-equivalent | Normalize at write and query; pin the metric with the index (Q92) |
| Weak on negation, numbers, entity identity, logic | Hybrid + metadata filters is a **correctness requirement**, not an optimization (Q99, Q102) |
| Scores are not probabilities, not comparable across models or queries | Rank with similarity, decide with a reranker or a calibrated threshold (Q103) |
| Asymmetric models need query/passage prefixes | Wrong or missing prefix = 10-30 percent recall loss, silently (Q96) |
| Embeddings are invertible enough to leak source text | Classify and protect the vector store like the text (Q105) |
| 3,072 → 768 dims costs 1-3 percent relative nDCG | 4x memory saving. Matryoshka truncation makes it cheap (Q95) |

Changing the embedding model = **re-embed everything**, rebuild the index, re-tune thresholds, invalidate caches. Run it shadow-first with dual writes and a version tag per vector (Q97).

Better investment order: chunking → hybrid → filters → **reranker fine-tune** → embedding fine-tune (last, because it is a corpus migration) - Q100.

Retrieval architecture depth is `09-rag`.

---

## 8. Context engineering

Window as a budget with a written policy: fixed reserves (output, system, tools, state), elastic capped sections (retrieved context, history), fixed eviction order (Q108).

| Memory option | Failure |
| --- | --- |
| Full history | Cost climbs, dilution - but **cache-friendly**, so best for short sessions (Q109) |
| Sliding window | Forgets the original goal stated in turn one |
| Running summary | Drops the one specific detail; errors compound across re-summarization (Q110) |
| Structured state | Only what you modelled - and it is the right backbone |
| Retrieved history | Retrieval misses, loses continuity |

**Anything the system must not forget is a field, not a sentence in a summary.** Exact state (booking, cart, form) is a domain object mutated by validated tools, rendered into the prompt as an authoritative block (Q113).

Context rot (Q111): dilution + self-conditioning + accumulated contradictions + stale tool results. Fix by re-anchoring at the end, pruning superseded content, carrying state not transcript, compacting at a threshold.

Reordering to put retrieved context first **triples cost** - the cache is a strict prefix (Q115).

---

## 9. Adaptation

**Fine-tune for form, retrieve for facts.** (Q122)

| Rung | Cost | Fixes |
| --- | --- | --- |
| Prompting | Minutes | Behavior, format, most problems |
| Few-shot | Hours | Format, decision boundary |
| Retrieval | Days-weeks | **Knowledge**, freshness, citation, permissions |
| LoRA / PEFT | Weeks + permanent ownership | Form, style, narrow-task behavior, cost compression |
| Full fine-tune | Weeks, 5-10x cost, worse forgetting | Rarely justified in an application team |
| Continued pretraining | Months | Token distribution. Not knowledge |

Each rung is ~10x the previous in effort and maintenance. Move down only with an eval set proving the current rung has plateaued (Q121, Q140).

LoRA memory, 7B model (Q125): full FT ~90-120 GB · LoRA ~18-24 GB · QLoRA ~8-10 GB. `r` = capacity (8-16 for style, 32-64 for harder), `alpha/r` = effective scale.

| Risk | Detection |
| --- | --- |
| Catastrophic forgetting | A **general regression suite**: instruction-following, refusals, other formats, other languages, off-task inputs (Q127) |
| No abstention | Include abstention and refusal examples; score abstention as correct (Q81) |
| Contamination | Split by customer/document, not by row; report train/test overlap (Q131) |
| Overfitting | Learning curve at 25/50/100 percent of data (Q132) |
| Worse than base | **Check prompt-format mismatch first** (Q134) |

Mitigations for a fine-tune: LoRA, low LR, 1-3 epochs, **mix in 10-20 percent general instruction + refusal data**.

Extraction is the classic win: ~15-20x cost reduction at volume, plus latency (Q136). Maintenance cost ≈ 0.25 FTE per fine-tuned model, forever (Q138).

Distillation: filter the teacher's output, use **real** inputs, and answer the terms-of-service question about training on outputs before spending the compute (Q130).

---

## 10. Evaluation

The pyramid (Q142), widest first: deterministic assertions → golden set with references → LLM-judged rubric → human review → online metrics. **Push every check as far down as it will go.**

Minimum credible setup (Q141): 50-150 real labelled cases · a metric · a baseline · per-segment reporting · one repeatable command. Two days of work.

| Statistic | Number |
| --- | --- |
| SE of a pass rate at p=0.9, n=200 | ±4 points at 95 percent |
| To detect 10 points | ~150 cases |
| To detect 5 points | ~500-600 |
| To detect 2 points | ~3,000-4,000 |
| Non-determinism | n=3 samples per case, average per case |
| Best lever | **Paired comparison** - cuts required n by 2-4x |

Six CI-stable assertions (Q145): schema validity · grounding by construction (every number, date, id, quote present in the input) · banned/required content · bounds (tokens, latency, cost, retries) · structural properties (sums, ranges, language) · invariance across rephrasings.

Judge rules (Q147-149): one criterion per call · behavioral anchors per scale point · reason before score · **pairwise beats absolute** for change decisions · control for position (swap orderings), **length**, self-preference · validate against human labels with **kappa**, not raw agreement (90 percent agreement on a 90 percent base rate is zero information) · pin the judge version.

Gates (Q152): commit = assertions on fixtures · PR = 60-100 case subset, per-segment, **blocks on any segment regression even if the aggregate improves** · nightly = full set n=3 + judged + regression + safety · release = held-out set + human sample + canary plan.

Suite too expensive? Tier it, cache responses by (prompt hash, model version, params, input), move checks down the pyramid, cheapen the judge, use the batch API (Q153).

Green suite + unhappy users = **the suite is wrong**: selection bias · wrong metric dimension · aggregation hiding a segment · no multi-turn coverage · only the model evaluated · overfitted (Q144).

Online primary metric = **task resolution**, not satisfaction (Q154). Trust implicit signals with a cost attached: edit distance, regeneration, copy, escalation, repeat contact in 48h (Q155).

---

## 11. Hallucination and grounding

Definition that is measurable: *a claim that cannot be traced to a span of the provided context or to a tool result* (Q161).

Kinds: **intrinsic** (contradicts context) · **extrinsic** (unsupported by context) · **factually wrong** (needs external truth) · **fabricated identifiers** (the dangerous engineering class).

**Faithfulness is enforceable; factuality is not.** Promise the first, and make corpus accuracy the content owner's job (Q164, Q176).

RAG does not solve it (Q163): stale or wrong context · incomplete context filled from memory · misread context (numbers, entities, negation, dropped conditions) · retrieval missed and the model answered anyway.

| Confidence method | Worth |
| --- | --- |
| Token logprobs | Weak for correctness; good for **localizing** uncertainty and closed-set scoring |
| Verbalized confidence | Poor - clustered at 85-95, gameable |
| Sampling agreement | Best model-side signal; fails on systematic errors |
| **A separate verifier** (entailment, rules, tool check) | Strongest - uses information the generator lacked |
| Retrieval scores | Cheap upstream predictor of unanswerable questions |

Build a **composite** and calibrate it against labels. Uncalibrated confidence displayed to users is worse than none (Q167, Q174).

Verification ladder, cheapest first (Q169): rules/code (ms) → retrieval check → NLI entailment per claim (100-400 ms, parallel) → a second LLM with the sources (seconds, escalation only). Budget ~200-400 ms inside a 2 s interactive answer, run in parallel.

Citations: explicit ids in context, constrained to legal ids, **verbatim quoted span verified character-for-character**, and an uncited claim is an error rather than prose (Q165).

Arithmetic: the model **translates**, code **computes** (Q171).

Users trust the confident wrong answer over the hedged right one, so move uncertainty out of prose and into structure: sources, an explicit not-found state, editability, human handoff (Q173-174).

---

## 12. Safety

| Attack | Actor | Control class |
| --- | --- | --- |
| Prompt injection | A third party via content | Authorization and privilege separation |
| Jailbreaking | The user | Content policy, classifiers, refusal evals |
| Exfiltration | Either | Data access + **egress control** |

Injection is not solvable like SQLi: there is no code/data channel separation, only a **learned prior** about authority (Q116, Q178). "Ignore instructions in documents" fails - no enforcement, attacker writes last and closest, attacker can address the defense, unbounded phrasing, and it conflicts with the task (Q180).

Defense layers that hold when the model is fully subverted (Q181): **least-privilege tools** · authorization from the session, not the arguments · quarantined dual-model pattern · output constrained to enums/schema · **egress control** · human approval showing the resolved action · provenance tagging · classifiers (probabilistic, never last) · rate limits and audit.

**The lethal trifecta** (Q182): private data + untrusted content + external communication. Remove any one leg. Usually remove egress: draft, do not send.

Jailbreak families (Q186): role-play · encoding/obfuscation · many-shot saturation · low-resource languages · crescendo escalation. All exploit the fact that safety is a *learned behavior competing with other learned behaviors*.

Guardrails: run in **parallel**, not series; budget <200 ms; define the failure action per check; streaming needs buffering or a retraction path; log every trip (Q184). Measure **both** directions - over-refusal is the failure teams do not measure (Q157).

A 0.4 percent false-positive rate over an 8-turn conversation ≈ **3.2 percent of sessions affected**. The failure *mode* matters more than the rate - prefer graduated response to hard blocking (Q185).

Provider data terms to get in writing (Q188): no-training, retention and zero-retention option, region and failover, sub-processors, deletion scope, breach notification, IP indemnity, deprecation notice.

PII: prefer **pseudonymization with rehydration** over redaction; check whether the obligation is "must not be retained" rather than "must not be processed" before destroying utility (Q189-190).

Tenant leaks appear in: retrieval filters, tool authorization, prompt examples, **caches**, session lookup, logs, shared adapters, embeddings (Q191). Semantic cache across users is a confidentiality bug unless keyed by tenant + authorization scope + context identity (Q192).

EU AI Act in engineering terms (Q194): risk tier → transparency/disclosure and content marking for limited-risk; risk management, data governance, documentation, logging, human oversight, accuracy and conformity assessment for high-risk. GDPR is usually the binding constraint in practice.

---

## 13. Serving mechanics

| Phase | Bound by | Scales with |
| --- | --- | --- |
| Prefill | Compute | Prompt length → **TTFT** |
| Decode | Memory bandwidth | Model size / bandwidth, and batch → **inter-token latency** |

KV cache per token per sequence (Q198):

```
2 (K,V) x layers x kv_heads x head_dim x bytes_per_element
```

70B example (80 layers, 8 KV heads, 128 dim, FP16): **320 KB/token** → 2.56 GB at 8k → **82 GB at batch 32**, plus 140 GB of weights = 4+ GPUs (Q199). GQA/MQA is why long context is servable at all; FP8 weights buy cache, which buys concurrency.

| Technique | Win |
| --- | --- |
| Continuous batching | 2-4x throughput; much better TTFT; **variable** inter-token latency under load (Q200) |
| PagedAttention | Removes reservation waste, enables prefix sharing and preemption (Q201) |
| Quantization (weight-only FP8/INT8) | Nearly free speedup on bandwidth-bound decode (Q204) |

INT4 same benchmark, worse production: the error flips **close** decisions - rare entities, long context, multilingual, multi-step - and compounds autoregressively (Q205).

Parallelism (Q206): tensor = inside a node over NVLink, reduces latency · pipeline = across nodes, throughput only · expert = MoE · **data (replicas) whenever the model fits**.

Sizing (Q207): weights + KV cache + activations + 10-15 percent overhead. 13B FP16 on one 80 GB A100 ≈ 33 concurrent 8k sequences ≈ ~3 req/s. Size against **p95 context length**.

Cold starts are 30 s to 10 min → no scale-to-zero for interactive. Use a warm floor, predictive scaling, baked weights, and burst-to-API overflow (Q208).

**Autoscale on queue wait and KV cache utilization, never GPU utilization** (Q209).

p99 = 8x p50? Output length variance → batch contention → prompt length variance in prefill. Plot latency against output tokens before blaming the network (Q210).

Stacks (Q212): **vLLM** default self-hosted · **TensorRT-LLM** max performance, slow iteration · **TGI** HF ecosystem · **llama.cpp** CPU/edge · **Ollama** laptops, never production.

Encoder models (embeddings, rerankers) are all-prefill: batch hard, cache by content hash, separate index and query fleets, CPU is viable (Q213).

---

## 14. Cost and capacity

Unit cost terms people forget (Q217): retries and repairs · guardrail and judge calls · embeddings and reranking · thinking tokens · cancelled and failed requests · evaluation spend.

**Cost per resolved task, not per call** (Q218) - otherwise you optimize towards a cheap model that needs 2.4 turns.

| Cache tier | Hit rate | Risk |
| --- | --- | --- |
| Prefix (KV) | 60-90 percent of input tokens | None. Always do it |
| Exact match | 5-15 percent | Staleness, cross-user leak if mis-keyed |
| Semantic | 10-30 percent claimed, less in reality | **High** - entity/number confusion, confidentiality |

Cost-halving ladder, in order (Q232): prefix caching (25-45 percent of input) → output length discipline (15-30 percent) → context hygiene (10-20 percent) → task routing (20-40 percent) → response caching → batch API for offline work → cascade with a cheap validator → fine-tune/distil the highest-volume task → self-host the small models → reserve capacity **last**, after optimizing.

Steps 1-3 alone are typically 40-50 percent in under two weeks with no quality risk.

Budget ladder (Q227): alert → reduce `max_tokens`/chunks/verification → cheaper model + longer cache TTL → throttle and queue → hard limit with a specific message → kill switch to the non-AI path. Each step visible in telemetry; the user sees nothing until step 3.

Limits to enforce (Q224): **concurrency per tenant** (the one that matters) · tokens/min and /day sliding · requests/min · cost per period · per-request caps. 429 with `Retry-After`, distinct reason codes, remaining-quota headers.

Metering (Q225): tag at the call site (tenant, feature, user, prompt version, model version), capture usage from the response, store **tokens not prices**, apply a versioned price table at query time, reconcile daily. An unattributable call is a bug.

Bill 40 percent above your accounting? Uncounted calls (guardrails, embeddings, judges, other teams) · failed/cancelled but billed · retries · invisible tokens · price/unit mismatch (Q226).

Latency budget for a 2 s p95 grounded answer (Q229): guardrail 80 · embed 20 · retrieve 100 · rerank 150 · **TTFT 600** · generate 800 · output checks 150 · overheads 100. Parallelize; name the elastic stages in advance.

---

## 15. Java and Spring production behavior

| Concern | Rule |
| --- | --- |
| Boundary | Port in domain terms; provider details, prompts, schema, retries, validation in the adapter. **No unvalidated output crosses it** (Q233) |
| Timeouts | Streaming: **idle/inter-event** timeout, not total-response. Plus an application deadline propagated to the call (Q234-235) |
| Truncation | Check `finish_reason`; a stream must end with an explicit terminal status or truncation reads as an answer (Q23, Q235) |
| Retries | **One**, jittered, only when no bytes were produced. Retry into a *different* path. Count and cost them (Q236) |
| Idempotency | Key from caller intent or `tool_call_id` + args hash; store the **response**; check inside the side-effect transaction (Q237) |
| Streaming | SSE default. Disable proxy buffering, heartbeats every 10-20 s, `Last-Event-ID` resume from a **server-side buffer** (Q238) |
| Cancellation | Propagate the disconnect to the provider; bound cost with `max_tokens` rather than relying on it. Track cancellation rate (Q239) |
| Threading | **Virtual threads + an explicit semaphore** sized to the provider quota. Platform threads break at pool size (Q240) |
| Transactions | **Never an LLM call inside one** - connection pool exhaustion is a full outage (Q241) |
| Bulkhead / breaker | Per provider *and* per model tier. Count slow calls as failures; do **not** count 429s. Longer open duration, multiple probes (Q242) |
| Fallback | Cached / cheaper model / non-AI path / honest failure - chosen by what a *wrong* answer costs vs no answer (Q243) |
| Observability | Spans per stage; model span carries resolved version, prompt version, token counts, cost, tenant. **Surface a response id to the user** (Q244) |
| Logging | Metadata everywhere; content sampled 1-5 percent + 100 percent of failures into a separate restricted store. Never in the shared APM (Q245) |
| Testing | Stub the port for domain tests; recorded provider responses for adapters; assert on **properties and the rendered prompt**, never on generated text (Q246) |
| Attribution | Context is a required parameter; ban direct SDK imports with an ArchUnit rule; gateway rejects untagged calls (Q247) |
| Rollout | Prompt and model version as config, flag-based canary by tenant hash, **sub-minute kill switch, exercised quarterly** (Q248) |
| Abstraction | Abstract the call; expose an explicit **capability model**; do not abstract quality, fine-tunes, embeddings or the batch API (Q249) |

---

## 16. LLMOps

Release descriptor pins the whole tuple (Q252): prompt@v · model@version · params · tools@v · schema@v · guardrails@v · embedding@v · index@v · retrieval params · eval suite@v + scores. Promote, canary and roll back **as one unit**. Byte-identical reproduction is not achievable on a hosted model - say so.

Pipeline (Q253): local eval → PR gate (subset, per-segment, blocking) → nightly full + safety → descriptor + staging smoke → canary 1-5 percent with a segment-complete population → ramp 25/50/100 → post-release canary eval. Half a day to two days for a prompt change; a week for a model change.

**Shadow** compares outputs on identical inputs - decidable in hours, no user risk, cannot see behavior or multi-turn. **Canary** measures behavior - needs days plus a 48-hour repeat-contact window (Q254).

Deprecation runbook (Q256): inventory from telemetry (not the registry alone) → buy the extension if cheap → evaluate successor + one alternative → **retrain fine-tunes early, they are the long pole** → shadow → canary → keep a 25 percent time buffer.

Monitoring panels (Q259): volume/errors · TTFT and total latency · **token distributions** · cost per request and per resolved task · cache hit rate · canary and judged-sample quality · behavior rates (refusal, abstention, repair, truncation, escalation) · guardrail trips · retrieval health · user signals · versions in production.

**Leading indicator: token distributions + behavior rates.** They move before complaints and before the invoice.

Alerts without labels (Q260): canary score control limits · refusal rate step change (both directions) · output tokens ±25 percent · cost/request ±20 percent · cache hit floor · repair rate multiple · guardrail trips both ways · **model fingerprint change** · retrieval no-result step. Compare against hour-of-week, not fixed thresholds.

Sev-2 = the feature is up and wrong. First five actions (Q258): blast radius from telemetry → diff **everything not code, including the provider fingerprint** → stop the bleeding (descriptor rollback or kill switch) → preserve evidence before retention expires → contain downstream consequences of outputs already acted on.

Ownership fix (Q264): an owning team in the service catalogue · the eval set as an owned asset · on-call for AI alerts · a review cadence · launch is not done without owner + dashboard + alerts + runbook + eval + kill switch · **a sanctioned decommission path**.

Platform split (Q266). **Centralize**: gateway, provider contracts and registry, eval harness and judge, safety suite, shared small models, observability schema, patterns. **Federate**: prompts, eval cases, corpora, UX, model choice within the approved set, feature ownership. **Refuse**: writing others' prompts, approving each release, owning others' quality.

---

## Numbers worth quoting

**Tokens and cost**
- 4 chars ≈ 1 token (English); 3 chars (code); 2-4x for non-Latin scripts
- A page ≈ 600 tokens; a high-res image ≈ 1,500-3,000 tokens
- A tool definition ≈ 100-300 tokens, on every request
- Output priced 3-5x input; cached input read at ~10 percent
- Well-structured chat: 60-90 percent of input tokens served from cache
- 40-page PDF ≈ 30k tokens ≈ $0.10 input at $3/M, and 2-4 s of prefill

**Latency**
- TTFT under 500 ms feels instant; over 3 s feels broken
- Reading speed ≈ 10-15 tokens/s, so 30 tokens/s hides a mediocre decode rate
- Voice needs TTFT under ~300 ms end to end
- p99 is typically 3-8x p50 for generation
- Groundedness checks: 200-400 ms if run in parallel

**Serving**
- 70B FP16: 140 GB weights; KV cache ~320 KB/token → 2.56 GB at 8k
- 13B FP16 on one 80 GB A100: ~33 concurrent 8k sequences, ~3 req/s
- Continuous batching: 2-4x throughput over static
- Speculative decoding: 2-3x at low batch, negative at high batch
- Cold start: 30 s (baked weights, local NVMe) to 10 min (object storage)
- Self-host break-even vs API needs sustained volume **and** >60 percent utilization

**Evaluation**
- Golden set: 150-300 cases; PR subset 60-100
- n=200, p=0.9 → ±4 points at 95 percent confidence
- Detect 10 points ≈ 150 cases; 5 points ≈ 550; 2 points ≈ 3,500
- Paired comparison cuts required n by 2-4x
- Judge kappa: <0.4 unusable, 0.6-0.8 good, >0.8 suspicious on open tasks
- Hallucination review: 150 responses/week ≈ 0.5 FTE

**Adaptation**
- Fine-tune data: 500-2,000 examples for a narrow task; quality beats quantity
- LoRA on 7B: ~20 GB; QLoRA: ~9 GB
- Mix 10-20 percent general + refusal data to limit forgetting
- Small fine-tuned vs frontier prompted: 10-25x cheaper at volume
- Fine-tune maintenance ≈ 0.25 FTE per model, permanently

**Cost engineering**
- Prefix caching: 25-45 percent of input cost
- Output length discipline: 15-30 percent of total
- Task routing: 20-40 percent
- Batch API: ~50 percent on eligible work
- Cascade at 20 percent escalation with a cheap validator: ~70 percent saving
- Realistic portfolio saving in two quarters: 30-45 percent

**Safety and quality**
- 0.4 percent false-positive rate × 8 turns ≈ 3.2 percent of sessions affected
- Thumbs response rate: 1-3 percent, biased to extremes
- Embedding dimension 3,072 → 768: 1-3 percent relative nDCG, 4x memory saved
- Wrong query/passage prefix: 10-30 percent recall loss, silently

---

## The ten sentences to have ready

1. Generation is serial, so **output length is the latency**, and streaming or brevity are the only fixes.
2. Attention is quadratic and U-shaped, so **long context costs superlinearly and the middle is invisible** - put the constraint at the end.
3. **Fine-tune for form, retrieve for facts.**
4. **Temperature zero is not deterministic**, so test properties, not strings.
5. The model's output is **untrusted input** until validated at a boundary the code owns.
6. **Faithfulness is enforceable; factuality is not** - promise the measurable one.
7. Prompt injection has no code/data separation, so design for a **fully subverted model**: least privilege, authorization from the session, no egress.
8. For inference, capacity is **memory and queue wait**, not GPU utilization.
9. **Cost per resolved task**, not per call - and the first 40 percent of savings is caching, output length and context hygiene.
10. A green eval suite with unhappy users means **the suite is wrong**; re-sample from production and report per segment.
