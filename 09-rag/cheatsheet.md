# Retrieval-Augmented Generation Cheatsheet

Fast revision. Every claim here is expanded in [answers.md](answers.md); question numbers are the index. Treat every absolute figure as an **order of magnitude to reason with** - dimensions, recall numbers, prices and index products all moved last quarter, and interviewers know it. Show the arithmetic, not the memorized number.

---

## 1. Why retrieval exists

RAG = **selecting the relevant subset of an authoritative corpus and putting it in front of the model at inference time** (Q1).

| Problem | Fine-tuning can solve it? |
| --- | --- |
| Staleness | No - update latency becomes days |
| Scale | No - lossy, unauditable |
| **Permissioning** | **Never.** Weights have no ACL |
| **Attribution** | **Never.** Facts are superposed in FFN weights |

The last two are categorical, not economic. That is the answer to "why not fine-tune on our docs" (Q2).

**Long context does not kill RAG** (Q3): cost (quadratic prefill), latency (seconds of TTFT), quality (effective ≠ advertised context), **permissions**, corpus scale, attribution. What it *does* change: precision matters less, recall@k matters more.

**Decision table** (Q8):

| Need | Tool |
| --- | --- |
| A live or computed value | **Tool call** - never retrieve a number a query can return |
| Per-user visibility, changing facts | **RAG** |
| Wrong style/format | **Fine-tune** (RAG will not help) |
| Small stable public corpus | **Long context + prompt caching** (Q10) |

**"RAG accuracy is 60 percent" - the one experiment:** oracle-context run. Put the known-correct text in the context and re-run. Correct now → retrieval/ingestion/assembly. Still wrong → generation (Q6).

---

## 2. Ingestion

Pipeline: **discover → fetch → parse → normalize → enrich → chunk → embed → index → verify** (Q15).

**Land raw bytes, content-addressed.** Then re-chunk and re-embed are batch jobs, not re-crawls. The decision that saves every future migration (Q15, Q62).

| PDF strategy | Cost | Fails on |
| --- | --- | --- |
| Text layer | free | scans, columns, tables, reading order |
| Layout-aware | ~1 s/page | complex tables |
| OCR | seconds/page | poor scans; confident garbage |
| Vision LLM | 1.5-3k tokens/page | cost, hallucinated cells |

Cascade between them and **record which path each page took** (Q17).

**Tables** (Q19): small → markdown chunk. Lookup questions → row-as-sentence. Aggregate questions → **database + tool**, index only a description. Always carry units, dates, captions.

**Metadata you will regret not having** (Q25): `embed_model_version`, `chunker_version`, **ACLs**, `effective_from/to` (≠ `modified_at`), the raw artifact, a stable chunk anchor.

**Dedup at ingestion** is the cheapest retrieval win in enterprise corpora - duplication is routinely 2-4× (Q24).

**Indexed but not retrievable - the ladder** (Q28): fetch by id → query with no filters → exact search → compare model versions → read the raw chunk text.

---

## 3. Chunking

Three reasons to chunk (Q31): **retrieval precision** (one vector = one idea), context economy, embedding input limits. Plus citation granularity.

**Bigger chunks can hurt retrieval** (Q34): vector averaging → corpus-average dilution → context dilution → silent truncation past the model's input limit.

**Resolution is decoupling, not compromise: index small, return large** (Q37, Q41).

| Corpus | Boundary |
| --- | --- |
| Contract | clause, never split a numbered clause |
| Runbook | whole procedure |
| Chat | thread / turn cluster |
| Code | declaration + signature + docstring |

Overlap: **10-15 percent**, insurance not strategy. 50 percent overlap doubles index, embedding bill and duplicate results (Q35).

**Deterministic section-path prefix** (Q44) is the cheapest quality win: 10-30 tokens/chunk, fixes the "It does not support this configuration" problem (Q39). LLM contextual enrichment (Q38) is the expensive version - do the free one first.

**Evaluating a chunker:** label answers as **character spans in the source document**, not chunk ids - otherwise no two chunking strategies are comparable (Q45).

---

## 4. Embeddings

Similar = **angle**, and "similar" means whatever the contrastive training objective made it mean (Q47).

**Leaderboards are a shortlist, not a decision** (Q49): domain shift, query shift, benchmark over-fitting, and your ANN + hybrid + reranker compress the differences.

**Evaluate with exact search, on your corpus, with and without your reranker** (Q48).

| Dims | Bytes/vec (fp32) | 50M chunks |
| --- | --- | --- |
| 768 | 3,072 | 154 GB |
| 1024 | 4,096 | 205 GB |
| 3072 | 12,288 | 614 GB |

Knee is usually 768-1024 for corpora under ~10M chunks; spend the money on hybrid + reranking instead (Q51).

**Matryoshka** (Q52): truncatable prefixes → small vectors in the ANN index, full vectors for rescoring. Normalize *after* truncation.

**Normalize at ingestion** → cosine ≡ inner product ≡ L2 ranking. Unnormalized + inner product = magnitude bias, silent (Q53-54).

**Asymmetric retrieval:** `query:` / `passage:` prefixes are not cosmetic. Forgetting one on the query path degrades quality silently (Q50).

**Anisotropy** (Q59): unrelated texts score 0.5-0.8. Therefore: no absolute thresholds (Q58), small dynamic range, low-information chunks sit near the centroid, and **rank fusion beats score fusion**.

**Fine-tune the reranker before the embedding model.** The reranker is not baked into the index (Q56, Q124).

---

## 5. Vector indexes

| Index | Build | Query | Note |
| --- | --- | --- | --- |
| Flat | 0 | O(N·d) | Correct below ~1M, and per-tenant |
| IVF | training pass | nprobe/nlist · N | Degrades as data drifts from centroids |
| HNSW | expensive | ~log N | Best in-memory; deletes and filters hurt |
| DiskANN | very expensive | SSD-bound | Makes billion-scale affordable |

**HNSW params** (Q65): `M` and `efConstruction` are build-time; **`efSearch` is the live recall/latency dial** - your degradation lever.

**Memory arithmetic, 50M × 1024-d** (Q70):

| | vectors | + HNSW graph (M=32) |
| --- | --- | --- |
| fp32 | 205 GB | +13-19 GB |
| int8 | 51 GB | +13-19 GB |
| binary | 6.4 GB | +13-19 GB (now larger than the vectors) |

**Always state the graph overhead** - it is what people forget.

**Quantization without rescoring is the mistake.** Wide candidate set on compressed vectors → rescore with full precision → recall recovers to within a point or two (Q68-69).

**Filtered search destroys HNSW recall** (Q72, Q150): the filtered subgraph is not navigable, so greedy search gets trapped with **no path** to the right region. Fix: selectivity-aware planning (very selective → brute-force the subset), or partition on the filter.

**Deletes = tombstones** (Q73). Effective recall decays as `efSearch` budget is spent on dead nodes. **Monitor the deleted-to-live ratio; rebuild at 10-20 percent.**

**Store selection** (Q75): 1M → pgvector or in-process. 50M → OpenSearch (you need BM25 anyway) or a dedicated vector DB. 2B → purpose-built only.

**pgvector gotchas** (Q76): `maintenance_work_mem` too small → an on-disk build that takes days; operator class mismatch (`<=>` vs `<->`) → silent sequential scan. Always `EXPLAIN ANALYZE`.

---

## 6. Hybrid search

**BM25 = rare term × saturated frequency × length normalization** (Q81).

**BM25 wins** (Q82): identifiers, rare proper nouns, jargon, verbatim quotes, negation, long pasted text. **Dense wins when the user's words differ from the document's words.** Complementary, not competing.

**Why dense fails on `ORD-4471`** (Q84): subword fragments carry no meaning, *and* the training objective actively blurs `ORD-4471` and `ORD-4472` - which is exactly the distinction you need. Not fixable by a better model.

**Use RRF, not score fusion** (Q85-86): `Σ 1/(k + rank)`. Scale-free. `k` large (60) = consensus; small = confident single hits. Score fusion breaks because cosine is compressed and BM25 is unbounded and query-length-dependent.

**Candidate depth: 50-200 per retriever, not 10.** Stage one is judged on **recall**; the reranker does precision (Q93, Q113).

**Hybrid can improve the mean and wreck the tail** (Q89) - fusion averages in a retriever that was completely wrong. Always measure per-query win/loss, not just the mean.

**Recall floors** (Q95): exact-title short circuit + curated best bets + a CI findability test. Track pinned-result coverage - a rising number means retrieval is degrading.

---

## 7. Query understanding

Four transformations (Q97): **contextualize → reformulate → decompose/expand → extract/route**. Adopt in that order of value per millisecond.

**Contextualization is not optional in multi-turn.** "What about for enterprise?" → "refund window for the enterprise plan" (Q99). Bound history to 2-4 turns; never chain rewrites; **always fuse with the raw-query results** so a bad rewrite degrades to no-change (Q98).

**Decomposition (parallel, sub-questions known up front) ≠ multi-hop (sequential, bridge entity unknown)** (Q100 vs Q211).

**Filter extraction** (Q107): constrained output, **validate every value against reality**, drop rather than guess, parse dates in code, zero-result fallback that relaxes filters, and show the filters as removable chips.

**Routing** (Q103-104): rules first, then a classifier, and **fan out when uncertain** - extra compute beats a confident wrong route. Design routes so errors are detectable downstream (zero rows → try the other route).

**Latency** (Q108): only one small-model call may sit on the critical path. Speculatively retrieve with the raw query while the rewrite is generating.

**Caching**: cache the user-independent parts (embedding, rewrite, route). Anything user-dependent needs **permission scope in the key** (Q110).

---

## 8. Reranking

**The asymmetry** (Q113-114): bi-encoder precomputes because the doc vector is query-independent; cross-encoder cannot be indexed **by definition** - its representation is a function of both inputs.

Cross-encoder is typically **5-15 nDCG points** better, and widest exactly where bi-encoders fail: negation, exact entities, qualifiers.

**Candidate count**: pick N at the knee of the recall curve (usually ~100), then check it fits the budget (Q115). ~430 tokens × 100 = 43k tokens through the model ≈ 20-60 ms on a small GPU cross-encoder (Q119).

**Better nDCG, unchanged answers?** (Q116) - (1) the generator consumed a set, not an order; (2) recall was the binding constraint; (3) failure is downstream; (4) the metric is insensitive. If you pass k=20 to a long-context model you may not need the reranker at all.

**Cannot afford it** (Q125): skip it when the first-stage score gap is large (covers 40-70 percent of queries), cascade a tiny model first, cache scores, truncate documents to title + first 200 tokens.

**Business logic goes after reranking, not inside retrieval** (Q120): hard constraints = pre-filters; preferences = an explicit multiplicative policy score; editorial pins last. Log each term separately or you cannot explain a ranking (Q126).

**Reranker scores are not probabilities** - Platt/isotonic calibration on a few hundred labelled pairs is what makes a threshold defensible (Q123).

---

## 9. Context assembly

Order of decisions (Q127): threshold → dedup/merge → parent expand → diversity → budget fit **by tokens** → order → format → place → compress → sanitize.

**Quality is inverted-U in k** (Q128). Typically 3-8 chunks factual, 10-20 synthesis. **Measure your own curve.**

**More context hurts** (Q129): attention dilution, lost-in-the-middle, and topically-similar distractors (wrong version, wrong region) which are far worse than random text.

**Order relevance-ascending so the best chunk is last**, adjacent to the question and the generation point (Q130).

**Context block** (Q132): delimiter + `[1]` label + source + **date + status** + section. ~25-45 tokens/chunk. Dates and status are the highest-value fields - without them the model cannot resolve conflicts or prefer current sources.

**Placement and caching** (Q134): `[static system prompt] [history] [retrieved context] [question]`. Retrieved content above the system prompt = 0 percent prompt-cache hit rate and double the bill.

**Citations reliable, not plausible** (Q133): short integer labels, server-side label→source mapping (so a hallucinated `[9]` is detectable), sentence-level contract, post-hoc verification.

**Injection in a chunk** (Q135): retrieval is an untrusted input path. The only real control is **least privilege at the tool boundary** - design so a successful injection is not catastrophic. Sanitize, delimit, tier by provenance, scan output - none sufficient alone.

**Multi-turn: re-retrieve, do not keep old chunks** (Q141). Keep a 20-token reference, not 400 tokens of text.

**Assembly is a pure function** - test the invariants (budget never exceeded, labels bijective, chunks never truncated mid-sentence, deterministic) (Q142).

---

## 10. Permissions

**You cannot filter after generation** (Q143) - the model already read it, and there is no regex for "this paraphrases a restricted document". Complete mediation.

**Permissions are always a pre-filter** (Q145). Post-filter breaks recall (asked for 10, got 3) *and* lets restricted content transit generation, logs and caches. Keep a post-retrieval assertion as defense-in-depth - it should never fire.

**Normalize every source's ACL model to `allow_principals` at ingestion**; resolve inheritance there; resolve the user's principals at query time; the filter is a set intersection (Q144). **Documents with no resolvable ACL are not indexed - fail closed.**

**ACL sync** (Q147): incremental for freshness + **periodic full reconciliation** for correctness, with the reconciliation **drift count** as the alert. Container permission changes affect thousands of documents from one event.

**The cache is where leaks happen** (Q148): key = `hash(query, index_version, permission_scope)`, scope derived server-side. **Every derived artifact inherits the permission scope of its sources** - caches, summaries, logs, evals, analytics.

**Semantic cache + permissions = two approximations stacked on an authorization boundary.** Prefer exact-match caching within a scope (Q153).

**GDPR delete locations** (Q156): source, raw store, parsed text, chunks, vector index, lexical index, 4 caches, backups, logs, eval sets, fine-tune data, conversation history, warehouse. Honest guarantee: live systems in 24 h, backups on the rotation cycle, **and a fine-tuned model cannot be un-trained**.

**Cross-tenant test fixtures must be deliberately similar** across tenants, or the test does not exercise the bug (Q157).

---

## 11. Evaluation

**Recall@N is the ceiling on everything downstream** (Q161). Measure it at two k's: candidate stage (~100, the ceiling) and generator stage (~8, predicts answer quality). The gap between them **is** the reranker's contribution.

**Golden set** (Q162): 200 minimum, 500-1000 to slice. Sampled from **production logs**, stratified, labelled by domain experts as **source spans**, with **20-30 percent unanswerable questions**, versioned in git, every incident adds a case, labels re-validated quarterly.

**Five ways a 95 percent golden set lies** (Q163): wrong query distribution, circular construction from chunks, binary relevance hiding partial coverage, aggregation hiding a broken segment, and measuring something the user does not care about.

**Synthetic queries** (Q164) are biased toward answerable, single-chunk, vocabulary-echoing, uniformly-distributed questions. Use them for coverage; use human-labelled production queries for decisions.

| Metric | Needs ground truth? |
| --- | --- |
| Faithfulness | No - reference-free, runs on production |
| Answer relevance | No |
| Context precision | LLM-judgeable |
| **Context recall** | **Yes - and it is the ceiling metric** |

**Faithfulness 0.94 + angry users** (Q168): faithful to the wrong-but-plausible context, to a wrong corpus, to incomplete context, or correct-but-useless. **Never report faithfulness without context recall.**

**Validate the judge against human-human agreement, not an absolute** (Q167, Q177). Relevance labelling agrees at κ ≈ 0.5-0.7 - that is your ceiling and your noise floor.

**Segments that matter** (Q175): source, doc type, query type, language, tenant, answerability, document age, turn position, permission breadth. **Gate on the minimum segment, not the mean.**

**A/B sizing** (Q172): `n ≈ 16·p(1−p)/δ²` per arm; randomize by user; pre-register the affected segment or the effect is diluted to nothing.

**CI budget** (Q174): PR < 5 min (units, permissions, 30-50 query smoke set) blocking; nightly < 1 hour (full golden set, end-to-end, segments) blocking promotion.

---

## 12. Grounding

**Instructions are a prior; verification is a control** (Q181). "Answer only from the context" is insufficient because the model's parametric prior is strong, alignment rewards helpfulness, and conflict resolution is unspecified (Q180).

**Citation verification ladder** (Q169): structural validity (free) → **every number/date/entity appears verbatim** (free, catches the dangerous errors) → embedding similarity → NLI cross-encoder → LLM judge offline. Run the free ones on 100 percent of traffic.

**Streaming weakens this control** - the unverified text has already been shown. That is a deliberate trade, not an oversight (Q183).

**Abstention triggers** (Q184): nothing above the calibrated bar → context does not address the question → the model says so → verification failed → policy. **Converge on one component that logs which trigger fired.**

**Users hate abstention** (Q185) - so redesign the refusal (name the scope, show near-misses, offer the next step) before moving the threshold. Most hatred is about receiving *nothing*.

**Conflicts** (Q187): the model applies **your precedence rules** (authority tier, then effective date) or surfaces the conflict. It never resolves policy on its own authority.

**Numbers** (Q191): exact-match verification against the cited chunk, **no arithmetic in the generator** (tool or SQL), carry units/currency/period/date.

**Confidence signals** (Q193): show **evidence and provenance**, never an uncalibrated percentage. Staleness, coverage gaps, conflict and abstention are honest; a 85 percent badge is not.

**Correct-from-parametric-knowledge is a bug** (Q190): unverifiable, unmaintainable, unpermissioned, and you cannot keep the good half of the behavior that produced it.

---

## 13. Freshness

**Ask freshness as a number with a consequence** (Q195):

| Requirement | Architecture |
| --- | --- |
| Days | Batch rebuild |
| Minutes | Event-driven incremental + tombstones + compaction |
| **Seconds** | **Do not index it. Use a tool call** |

Almost always **per source**, not per system.

**CDC** (Q196): webhooks for latency + polling for correctness + **full crawl for reconciliation**. Deletion detection is the hard part and the crawl is usually the only reliable signal.

**Edit = delete all chunks for the source id, write the new set** - insert-then-delete, never delete-then-insert (Q197).

**Still cited after deletion** (Q198): never detected · tombstoned in one index only · caches without source-id tags · a duplicate under another id · derived artifacts (summaries, graph nodes) · a stale replica or snapshot.

**Blue-green** (Q200): build offline → **catch up the delta from a watermark** → validate (counts, golden set, findability, permissions, load) → **flip the alias** → keep the old one warm → **warm the new one before the flip**.

**Re-embedding 50M chunks ≈ 20B tokens** (Q201): on an API that is rate-limit-bound at ~3 days; self-hosted it is hours. This is why self-hosted embeddings buy migration freedom.

**Mixed old/new vectors** (Q202): spaces are **incomparable**, results look plausible, nothing errors. Prevent structurally - bind model version to the index and fail startup on mismatch.

**Zero documents indexed for a week** (Q208): the job succeeded at doing nothing. **Monitor outcomes (freshness lag, expected volume, canary document, reconciliation drift), not activities.**

---

## 14. Advanced patterns

**Multi-hop** (Q211) is defeated by a **bridge entity the query does not name** - you cannot retrieve on information you do not have yet. Distinct from multi-part decomposition.

**Iterative loops terminate on:** model declares sufficiency · hard cap 3-5 · no new information · budget · declining scores (Q212).

**GraphRAG** (Q213-214) answers global/thematic, relational and entity-centric questions. Costs an LLM pass per chunk plus summarization, and **entity resolution is where it dies**. The three questions: what can it answer that vector search cannot, is the schema stable, who maintains it. Most enterprise graph projects do not reach sustained value.

**Text-to-SQL** (Q216): retrieve the schema subset, prefer a curated semantic layer, then **parse the AST, allow-list tables, execute as a restricted role with RLS, inject LIMIT and a timeout, read-only replica**. Show the SQL to the user.

**"What changed this year?"** (Q220) - standard RAG cannot answer it because **absence is not retrievable**. Version the corpus, compute diffs at ingestion, **index the change records as documents**.

**"How many tickets mention X?"** (Q221) - top-k is a relevance sample, not a population. **Retrieval answers "what does the corpus say"; a query answers "how many".** Materialize the attribute as metadata at ingestion, or expose an aggregation tool.

**Personalization** (Q222): prefer **context** (what you are working on) over **profile** (what you usually do) - more predictive, less invasive, no filter bubble.

**Index-time vs query-time** (Q225): `index_cost × corpus × rebuild_freq` vs `query_cost × volume`. Precompute **facts**, not judgements - anything precomputed can go stale.

---

## 15. Serving

**Latency budget** (Q227): understanding 150-400 ms · embed 15-60 · vector 10-40 · lexical 5-25 · rerank 30-120 · assemble 5-15 · **generation TTFT 400-1500 · streaming 1-3 s**.

**Retrieval is 15-25 percent of the total. Generation dominates, and output length is the tail** (Q228). Vector search is rarely the tail.

**Critical path** (Q229): contextualize → retrieve → rerank → assemble → prefill → first token. **Speculatively retrieve on the raw query while the rewrite generates.**

**Best TTFT win is usually UI:** stream the retrieved sources at ~600 ms instead of a blank screen until 1,800 ms (Q230).

**p99 = 10× p50 causes** (Q231): output length · filtered search cliff · cold cache · shard fan-out tail amplification · retry storms · maintenance interference. Tails are **concentrated in a subpopulation**, so slice by tenant, filter and output length.

**Cost model** (Q234-235): generation **input tokens** usually dominate, because retrieved context is paid on every request. Forgotten terms: amortized ingestion, index memory as standing cost, dual-index capacity, retries, nightly eval runs, logging.

**Embedding cost up with flat query volume** (Q236) → it is ingestion-side: a reprocessing loop, a re-embed job, enrichment turned on, retries, or a query-side cache-key regression. **Break down embedding tokens by caller.**

**Degradation ladder** (Q238): cache harder → skip rewrite → fewer rerank candidates → lower `efSearch` → smaller k → cap output → skip verification → smaller model → **retrieval-only** → queue → shed. Early rungs trade cost; late rungs trade product.

**Timeouts** (Q239): a **deadline budget** propagated down, not independent timeouts that sum past your SLO. Every timeout has a **degraded result**, not an error - RAG is naturally redundant.

**50 percent cost cut** (Q242): reduce k to the measured optimum (15-20 percent) · fix prompt caching (10-15) · model cascade (10-15) · caching layers (5-10) · self-hosted reranker (5-15) · output length (5-8) · quantization (5-10) · ingestion hygiene (3-5).

---

## 16. Java and Spring

**Port:** `Retriever.retrieve(query, principal)` returning domain types. **Permission scope is a parameter of the port, injected server-side** - make it impossible to call without a principal (Q243).

**Spring AI `VectorStore`** is portable for add/delete/similaritySearch/filters; it **leaks** on index tuning, hybrid search, filter strategy, transactions, bulk load, deletes and score semantics. Use it *behind* your own port, not as the domain interface (Q244).

**Spring Batch over Spring AI ETL** when you need restartability, checkpointing, skip/retry policies, partitioning and job metadata - i.e. any real backfill (Q245).

**Relational + vector write is not atomic** → **transactional outbox** + periodic reconciliation. Or use pgvector in the same database and get a real transaction (Q246).

**Row committed, vector failed** (Q247): the document exists everywhere except search. Reconciliation job comparing `(id, hash, version)` both ways, repairing through the normal path, with **drift as the alert**.

**pgvector pooling** (Q248): pool ≈ cores (queries are CPU-bound, not OLTP); **`SET LOCAL` for `hnsw.ef_search` or it leaks to the next borrower**; separate pools per workload.

**Batch embedding** (Q249): batch by **tokens**, bounded concurrency, backpressure, client-side rate limiting, item-level failure isolation, content-hash idempotency, a spend cap.

**Query path = IO-bound** → **virtual threads plus explicit bulkheads** (virtual threads remove the accidental backpressure a bounded pool gave you) (Q250).

**Testcontainers for stores** (filter semantics, ACL overlap, deletes cannot be mocked); stub the embedder deterministically; contract-test every `Retriever` implementation (Q251).

**One release descriptor** pinning index snapshot + embed model hash + chunker + retrieval config + reranker + prompt + policy + glossary, with the eval run attached (Q254). These components have **compatibility constraints**, not just versions.

**Embedding model = part of the index identity, not a dependency.** Pin by hash; assert at startup against the index's declared hash; exclude from dependency bots (Q255).

---

## 17. The lines that win interviews

1. **"Permissions and attribution are why fine-tuning is not an option - no budget fixes them."** (Q2)
2. **"The oracle-context experiment splits retrieval from generation in an afternoon."** (Q6)
3. **"Label answers as source spans, not chunk ids - otherwise no two chunkers are comparable."** (Q45)
4. **"Index small, return large."** (Q37)
5. **"Dense retrieval is trained to blur exactly the distinction an order number needs."** (Q84)
6. **"Use RRF - ranks are scale-free, scores are not."** (Q86)
7. **"Stage one is judged on recall, stage two on precision."** (Q113)
8. **"A filtered HNSW subgraph is not navigable, so the right neighbors are never visited."** (Q72)
9. **"Quantization without rescoring is the mistake."** (Q68)
10. **"Permissions are a pre-filter. A post-filter means the model already read it."** (Q145)
11. **"Every derived artifact inherits the permission scope of its sources."** (Q148)
12. **"Faithfulness measures internal consistency; correctness needs a reference."** (Q168)
13. **"Gate on the minimum segment, not the mean."** (Q175)
14. **"Retrieval answers what the corpus says; a query answers how many."** (Q221)
15. **"Monitor outcomes, not activities - the pipeline succeeded at doing nothing."** (Q208)
16. **"A ranking symptom usually has a metadata root cause."** (Q121)
17. **"You cannot make a system truthful over an untruthful corpus."** (Q23)
18. **"Retrieval turns your document store into an untrusted input path."** (Q135)
