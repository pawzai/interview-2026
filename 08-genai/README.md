# Generative AI Interview Preparation Pack

Model-layer depth for **Principal Engineer / Technical Lead / Solution Architect** interviews: how a transformer behaves and why that shapes your design, token and context arithmetic, decoding and determinism, model selection, prompting as engineering, structured output and tool interfaces, embeddings as model artifacts, context engineering, adaptation from prompting through LoRA to distillation, evaluation, hallucination and abstention, safety and prompt injection, inference and serving mechanics, cost and capacity engineering, the Java and Spring production path, and LLMOps.

This pack is about **the model and the inference path**. It is the answer to "do you understand the thing you are building on, or are you calling an API and hoping". An interviewer can tell within three questions: a candidate who says "we set temperature to 0.7" is using a library, a candidate who explains what temperature does to the logit distribution and why it is the wrong dial for their problem is engineering.

---

## Read [01-java](../01-java/README.md), [02-spring](../02-spring/README.md) and [04-system-design](../04-system-design/README.md) first

This pack is **not** an introduction to LLMs. It starts where the AI material in the earlier packs stopped, and nothing there is restated.

| Assumed known | Where this pack takes it |
| --- | --- |
| `01-java` Q211 integrating an LLM into a Spring Boot service | Category 15 - the failure modes of that architecture under load, timeouts around a streaming call, and provider abstraction that survives a model swap |
| `01-java` Q212, Q228 what RAG is, hybrid search | Categories 7 and 11 - embeddings as model artifacts and grounding as a model behavior. Retrieval architecture itself is [09-rag](../09-rag/README.md) |
| `01-java` Q213 chunking, similarity metrics | Category 7 - embedding model selection, dimensionality, normalization, and what re-embedding costs you |
| `01-java` Q214 controlling LLM cost and latency | Categories 2, 13 and 14 - the token arithmetic, prefill versus decode, and routing and cascade economics with numbers |
| `01-java` Q215 prompt injection against a tool-using agent | Category 12 - why it is unsolved, the defense layers that actually help, and how to test them |
| `01-java` Q216 evaluating a non-deterministic feature | Category 10 - twenty questions on it, because this is the single most common gap at principal level |
| `01-java` Q217 streaming with SSE, WebSocket, WebFlux | Category 15 - cancellation, backpressure, partial-output error handling and what a proxy does to your stream |
| `01-java` Q219 PII and third-party providers | Category 12 and Category 16 - data flow classification, retention terms, and what an audit actually asks for |
| `02-spring` Q237-246 Spring AI - `ChatClient`, advisors, `entity()`, tool calling, `VectorStore`, chat memory | Categories 6, 8 and 15 - what those abstractions are hiding, the cost defect inside chat memory, and when you wrap the provider SDK yourself |
| `04-system-design` Q209-216 LLM as a component, inference modes, token budgets, gateways, semantic caching | Categories 13 and 14 - the mechanics underneath those design choices: KV cache, batching, quantization, TTFT versus inter-token latency |
| `04-system-design` Q220-221 guardrails and non-determinism in the request path | Categories 10, 11 and 12 - the guardrail taxonomy, judge reliability, and the regression suite in detail |
| `04-system-design` Q223 GPU capacity | Category 13 - the arithmetic: memory per token of KV cache, batch size versus latency, cold start, and the self-host break-even |

Where a question here overlaps, it starts one level deeper.

**The answer frameworks are not repeated either.** The four-layer technical answer, CIDER for scenarios and STAR-L for behavioral questions are defined once in [../01-java/README.md](../01-java/README.md). Re-read that section before your first mock.

### Scope boundary

**Retrieval belongs to [09-rag](../09-rag/README.md).** Embeddings appear here as model artifacts - what an embedding model is, how to choose one, what its geometry implies. Chunking strategy, vector index types and their recall curves, reranking, query rewriting and the full retrieval pipeline are that pack. Category 11 covers grounding as a *model behavior*, not as a retrieval architecture.

**Agents belong to [10-ai-agents](../10-ai-agents/README.md).** Tool calling appears here as a model capability: how the schema shapes the model's output, constrained decoding, and what happens when the call is malformed. The loop, planning, memory across steps, multi-agent topologies and MCP servers are that pack.

**Placement in a system belongs to `04-system-design`.** Where the LLM sits, what fails around it, gateway design and capacity in a whole-system diagram are Category 14 there. Here we go inside the box.

**Framework API surface belongs to `02-spring`.** Category 15 here is about production behavior - timeouts, cancellation, observability, cost attribution, provider abstraction - not about Spring AI method signatures.

**Security depth belongs to `11-security`.** Category 12 covers the attacks specific to models. Application and cloud security generally is that pack.

Model numbers, context limits and prices move every quarter. Everything here is written so the **reasoning** survives the numbers changing, and where a figure is quoted it is labelled as an order of magnitude to reason with rather than a fact to recite.

---

## Files in this pack

| File | Purpose | When to use |
| --- | --- | --- |
| [README.md](README.md) | Prerequisite map, roadmap, what interviewers probe | Read first |
| [questions.md](questions.md) | 278 questions across 17 categories | Daily drilling |
| [answers.md](answers.md) | Mechanism-level model answers | After attempting yourself |
| [scenario-questions.md](scenario-questions.md) | AI production incidents, design exercises, leadership situations | Mock practice |
| [cheatsheet.md](cheatsheet.md) | Fast revision reference | Night before, and 30 minutes before |
| [quiz.html](quiz.html) | Interactive flashcard version | Active recall |

### quiz.html

Open it directly in a browser - no server, no internet connection needed. Search covers question and answer text, filter by category, difficulty or your own progress, and mark each question Known or Review with progress saved in the browser. Press `/` to focus search.

Generated from the markdown, so the markdown stays the source of truth. After editing any of the three source files:

```bash
python tools/build-quiz.py 08-genai
```

---

## What interviewers actually probe at this level

AI questions for a principal role are rarely "what is a transformer". They are testing whether you have operated an AI feature that real users depend on.

Six recurring themes:

1. **Do you know what the model is actually doing?** Not the paper, the consequences. Why output quality degrades when the important instruction is in the middle of a long prompt. Why `temperature = 0` is not deterministic. Why the same prompt costs different amounts on Tuesday. A candidate who can only describe the API is mid-level; a candidate who can predict a failure from the mechanism is principal.
2. **Can you evaluate it, or do you ship on vibes?** The most reliable separator in this domain. Almost every team has a prompt; very few have a golden set, a labelled failure taxonomy, an inter-annotator agreement number, or a judge they have validated against humans. "How do you know the change was an improvement?" ends most AI interviews early.
3. **Do you have the arithmetic?** Tokens per request, cost per thousand requests, KV cache bytes per token, tokens per second per GPU, cache hit rate, the break-even point on self-hosting. This is the estimation skill from `04-system-design` applied to a domain where most candidates have never done the sums.
4. **The failure was operational, not architectural.** A provider deprecating a model, a silent model update changing behavior, a cost spike from unbounded conversation history, a prompt edit with no review, an eval suite that passes while users complain. These are the incidents that actually happen.
5. **Where is the boundary between the model and your system?** Non-determinism has to be contained somewhere. Validation, retries, fallbacks, abstention, kill switches, and the honest answer that some products should not be built on a model at all.
6. **Judgement about when not to use it.** The strongest signal at 19 years of experience is being able to say "this should be a rules engine and a search box" and defend it. Enthusiasm is cheap in 2026; discrimination is not.

---

## Study roadmap

### Week 1 - Mechanism and arithmetic

Categories 1, 2 and 3. Be able to explain attention's quadratic cost, compute a token budget for a request without a calculator, and state precisely why a temperature of zero still gives you different answers.

### Week 2 - Prompting, structure and representation

Categories 4, 5, 6 and 7. Write a system prompt you would defend in review, design a tool schema that constrains the model rather than trusting it, and choose an embedding model with a stated reason.

### Week 3 - Context and adaptation

Categories 8 and 9. The most commonly bluffed material in the pack. Be able to draw the decision tree from prompting to RAG to LoRA to full fine-tuning with the cost and turnaround of each, and say what evidence moves you down it.

### Week 4 - Evaluation, grounding and safety

Categories 10, 11 and 12. Work every `[T]`. Be able to design a regression suite for a non-deterministic system out loud in five minutes, and explain why LLM-as-judge agrees with your team and still misleads you.

### Week 5 - Serving, cost and the Java path

Categories 13, 14 and 15. Do the GPU memory and throughput arithmetic on paper, compute a self-host break-even, and be able to walk a streaming request through a Spring service including what happens when the client disconnects.

### Week 6 - Operations and design

Category 16, then work only from [scenario-questions.md](scenario-questions.md). Category 17 is the rehearsal.

---

## Your AI story bank

Prepare these with real detail from Sonata Software and the AI work from 2024 onwards. Generic answers are transparent at 19 years of experience, and in this domain especially - everyone has read the same blog posts.

1. An AI feature you took to production, with the users, the quality bar and how you measured it.
2. An evaluation suite you built, including what it caught that manual review had missed.
3. A cost problem you found and fixed, with the before and after numbers and what caused it.
4. A latency problem specific to generation - the tail, the streaming contract, or a cascade you introduced.
5. A quality regression you diagnosed to a specific cause: a prompt edit, a provider model update, a retrieval change, a fine-tune.
6. A safety or data-handling decision you made, and what you refused to send to a third-party provider.
7. A build-versus-buy or self-host-versus-API decision, including the option you rejected and what would have changed your mind.
8. A time you argued that AI was the wrong tool, and what you shipped instead.
9. A fine-tune, distillation or model swap you evaluated - including one that did not pay off.
10. A standard you drove across teams you did not own: prompt review, eval gates in CI, PII classification, model approval.

---

## Self-check before the interview

- [ ] I can explain why attention is quadratic in sequence length and what that means for my context budget.
- [ ] I can compute the token cost of a feature per thousand requests in my head, to within an order of magnitude.
- [ ] I can state four distinct reasons the same prompt returns different output, and which ones I can eliminate.
- [ ] I can draw the adaptation decision tree and name the evidence that moves me from prompting to fine-tuning.
- [ ] I can design an evaluation suite for a non-deterministic feature, including how I validate the judge.
- [ ] I can list the layers of prompt-injection defense and say honestly which ones can be bypassed.
- [ ] I can size the KV cache for a given model, batch and context length, and compute tokens per second per GPU.
- [ ] I can compute the break-even point between an API provider and self-hosting, including the people cost.
- [ ] I know what happens to a streaming response when the client disconnects mid-generation in my service.
- [ ] I have three stories with concrete numbers attached, and one where the answer was not to use a model.
