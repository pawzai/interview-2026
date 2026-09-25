# Retrieval-Augmented Generation Interview Preparation Pack

Retrieval-layer depth for **Principal Engineer / Technical Lead / Solution Architect** interviews: when retrieval is the right answer and when it is not, ingestion and parsing, chunking and its failure modes, embeddings for retrieval, ANN index mechanics and their arithmetic, lexical and hybrid search, query understanding and routing, reranking, context assembly, permission-aware retrieval, evaluation, grounding and abstention, index lifecycle and freshness, advanced patterns, serving cost and latency, and the Java and Spring production path.

This pack is about **the retrieval system**. It is the answer to "can you build something that finds the right five paragraphs out of forty million, prove that it did, and keep it correct for two years". Interviewers separate candidates on this quickly: a candidate who says "we chunk at 512 tokens with 50 overlap and use cosine similarity" has followed a tutorial; a candidate who explains why bigger chunks reduced their recall, what their filter did to HNSW navigability, and how they measured any of it is engineering.

---

## Read [01-java](../01-java/README.md), [04-system-design](../04-system-design/README.md), [06-database](../06-database/README.md) and [08-genai](../08-genai/README.md) first

This pack is **not** an introduction to RAG. It starts where the retrieval material in the earlier packs stopped, and nothing there is restated.

| Assumed known | Where this pack takes it |
| --- | --- |
| `01-java` Q212 what RAG is | Category 1 - when it is the wrong architecture, and the decision criteria against fine-tuning, long context and tool calls |
| `01-java` Q213 chunking, similarity metrics | Category 3 - why bigger chunks reduce retrieval quality, small-to-big, and how to evaluate a chunker in isolation |
| `01-java` Q228 hybrid search | Category 6 - BM25 mechanics, why score fusion is usually wrong, and RRF |
| `04-system-design` Q106 component selection | Category 5 - the memory arithmetic that actually decides pgvector versus OpenSearch versus a dedicated store |
| `06-database` Categories 3-4 indexing and the optimizer | Category 5 - ANN as an index with a recall knob, and why a selective filter collapses HNSW recall |
| `06-database` Q95 full-text search | Category 6 - analyzers, field boosts and exact-match retrieval as a first-class requirement |
| `08-genai` Q5 facts live in weights | Category 1 - permissioning and attribution as categorical reasons retrieval exists |
| `08-genai` Q7 lost in the middle | Category 9 - context ordering, the inverted-U in k, and why doubling context lowers accuracy |
| `08-genai` Q21 prompt caching | Category 9 - where the retrieved block must sit, and what putting it first costs you |
| `08-genai` Category 7 embeddings as model artifacts | Category 4 - embeddings as a *retrieval* component: asymmetry, anisotropy, quantization, re-embedding migrations |
| `08-genai` Category 10 evaluation | Category 11 - retrieval-specific metrics, span labelling, and the five ways a golden set lies |
| `08-genai` Category 11 grounding as model behavior | Category 12 - citation verification, abstention design and the faithful-but-wrong failure |
| `08-genai` Q135, Category 12 prompt injection | Category 9 - retrieval as an untrusted input path into the prompt |
| `11-security` Category 4 authorization models | Category 10 - permission-aware retrieval across incompatible source ACL models |

Where a question here overlaps, it starts one level deeper.

**The answer frameworks are not repeated either.** The four-layer technical answer, CIDER for scenarios and STAR-L for behavioral questions are defined once in [../01-java/README.md](../01-java/README.md). Re-read that section before your first mock.

### Scope boundary

**The model belongs to `08-genai`.** Transformer behavior, decoding, token arithmetic, model selection, prompting technique, fine-tuning and serving mechanics are that pack. Embeddings appear here as a *retrieval* component - selection, dimensionality, quantization, migration - not as a model artifact.

**The agent loop belongs to `10-ai-agents`.** Iterative and agentic retrieval appear here only as a boundary (Category 14) and as the interface the retrieval service exposes (Q259). Planning, memory, tool orchestration, multi-agent topologies and MCP are the next pack.

**Whole-system placement belongs to `04-system-design`.** Where retrieval sits in a product architecture, and capacity in a whole-system diagram, is Category 14 there. Here we go inside the box.

**Framework API surface belongs to `02-spring`.** Category 16 here is about production behavior - transactions across two stores, pooling under a vector workload, reconciliation, versioning - not about Spring AI method signatures.

**Application and cloud security belongs to `11-security`.** Category 10 covers the authorization problems specific to retrieval.

Index products, embedding model names and their benchmark scores move every quarter. Everything here is written so the **reasoning** survives the numbers changing, and where a figure is quoted it is labelled as an order of magnitude to reason with rather than a fact to recite.

---

## Files in this pack

| File | Purpose | When to use |
| --- | --- | --- |
| [README.md](README.md) | Prerequisite map, roadmap, what interviewers probe | Read first |
| [questions.md](questions.md) | 272 questions across 17 categories | Daily drilling |
| [answers.md](answers.md) | Mechanism-level model answers | After attempting yourself |
| [scenario-questions.md](scenario-questions.md) | Retrieval incidents, design exercises, leadership situations | Mock practice |
| [cheatsheet.md](cheatsheet.md) | Fast revision reference | Night before, and 30 minutes before |
| [quiz.html](quiz.html) | Interactive flashcard version | Active recall |

### quiz.html

Open it directly in a browser - no server, no internet connection needed. Search covers question and answer text, filter by category, difficulty or your own progress, and mark each question Known or Review with progress saved in the browser. Press `/` to focus search.

Generated from the markdown, so the markdown stays the source of truth. After editing any of the three source files:

```bash
python tools/build-quiz.py 09-rag
```

---

## What interviewers actually probe at this level

RAG questions for a principal role are rarely "what is a vector database". They are testing whether you have operated a retrieval system that people depend on.

Six recurring themes:

1. **Can you separate retrieval failure from generation failure?** The single most common diagnostic question in the domain, and most candidates cannot answer it cleanly. The oracle-context experiment (Q6), recall@k as the ceiling metric (Q161), and per-stage observability (Q252) are what a principal engineer reaches for. A candidate who responds to "quality is 60 percent" by tuning the prompt has failed the question.
2. **Do you have the arithmetic?** Index memory including graph overhead, re-embedding tokens and duration, cost per query by component, latency budget by stage. This is the estimation skill from `04-system-design` applied to a domain where the numbers are unfamiliar and most candidates have never done the sums (Q70, Q201, Q235).
3. **How do you know it works?** Almost every team has a pipeline; very few have a golden set sampled from production logs, labelled as source spans, with unanswerable questions in it and per-segment gates. "How did you measure that the change was an improvement?" ends most RAG interviews early (Q162, Q163, Q175).
4. **Permissions and provenance.** The moment two users may see different documents, retrieval becomes an authorization system. Pre-filtering, ACL normalization across incompatible sources, cache scoping, deletion lineage and the audit trail are where enterprise RAG actually gets hard - and they are the questions that distinguish someone who has shipped from someone who has prototyped (Q143-158).
5. **The failure was in ingestion or in the corpus.** A flattened table, a missed deletion, a superseded document outranking the current one, a pipeline that succeeded at processing nothing. The incidents that actually happen are rarely about the vector index (Q18, Q121, Q198, Q208).
6. **Judgement about when not to build it.** The strongest signal at 19 years of experience is being able to say "this corpus is 300k tokens, put it in the prompt" or "this is a search box and a link" and defend it with cost, latency and evaluation arguments (Q7, Q10, Q221).

---

## Study roadmap

### Week 1 - Framing and the pipeline

Categories 1, 2 and 3. Be able to say in one sentence what RAG is and what it is for, run the oracle-context argument out loud, and explain why increasing chunk size can reduce retrieval quality.

### Week 2 - Representation and the index

Categories 4, 5 and 6. Do the memory arithmetic on paper including HNSW graph overhead, explain why a selective filter collapses recall, and defend hybrid search with the query types where each retriever wins.

### Week 3 - The query path

Categories 7, 8 and 9. Work every `[T]`. Be able to design the query pipeline for a multi-turn assistant, justify a candidate count with a recall curve, and explain the inverted-U in k with the attention mechanism behind it.

### Week 4 - Permissions and evaluation

Categories 10 and 11. The two categories that separate production experience from prototype experience. Be able to design permission-aware retrieval across incompatible ACL models, and build a golden set out loud - who labels it, how, and what it must contain.

### Week 5 - Grounding, lifecycle and advanced patterns

Categories 12, 13 and 14. Be able to design citation verification, state the deletion enumeration from memory, and explain why "what changed this year" and "how many tickets mention X" need different architectures.

### Week 6 - Serving, Java, and design

Categories 15 and 16, then work only from [scenario-questions.md](scenario-questions.md). Category 17 is the rehearsal.

---

## Your retrieval story bank

Prepare these with real detail from Sonata Software and the AI work from 2024 onwards. Generic answers are transparent at 19 years of experience, and in this domain especially - the specifics of a corpus are what make the work real.

1. A retrieval system you took to production: the corpus, its size, the users, the quality bar and how you measured it.
2. An evaluation set you built - who labelled it, how many queries, and what it caught that manual review had missed.
3. A quality problem that turned out to be ingestion or data, not retrieval, and how you found it.
4. A permission or isolation requirement you designed for, and the source system whose model did not translate.
5. A cost or latency problem you owned, with the before and after numbers and the dominant term.
6. An index or embedding model migration you executed on a live system.
7. A freshness or deletion incident, and the monitoring you added afterwards.
8. A time you argued that retrieval was the wrong architecture, and what you shipped instead.
9. A conflict between a metric and a user group, and how you resolved it with data without dismissing them.
10. A standard you drove across teams you did not own: an eval harness, a shared judge, a permission enforcement point, a release descriptor.

---

## Self-check before the interview

- [ ] I can define RAG in one sentence without saying "chunk" or "vector", and name the two problems fine-tuning can never solve.
- [ ] I can run the oracle-context experiment argument to separate retrieval failure from generation failure.
- [ ] I can compute the memory footprint of an index at a given scale, including HNSW graph overhead, and say what quantization changes.
- [ ] I can explain why a selective filter destroys HNSW recall, and give three fixes.
- [ ] I can name six query types where BM25 beats a dense retriever, and say why RRF beats score fusion.
- [ ] I can justify a reranker candidate count with a recall curve and a latency budget.
- [ ] I can explain why more retrieved context can lower answer accuracy, with the attention mechanism behind it.
- [ ] I can design permission-aware retrieval as a pre-filter and enumerate where a leak actually happens.
- [ ] I can describe how to build a golden set, including who labels it and why answers are labelled as source spans.
- [ ] I can enumerate every location a document must be deleted from, and state the guarantee I can honestly offer.
- [ ] I can compute cost per query by component and say which term dominates.
- [ ] I have three stories with concrete numbers attached, and one where the answer was not to build retrieval at all.
