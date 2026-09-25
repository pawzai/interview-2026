# Generative AI Interview Questions

Questions are numbered continuously (`Q1`, `Q2`, ...) so that [answers.md](answers.md) can reference them directly.

Difficulty legend:

- `[C]` Core - you must answer this instantly and correctly.
- `[D]` Deep - expected of a senior engineer, requires mechanism-level detail.
- `[T]` Tricky - designed to catch you out; the obvious answer is usually wrong.
- `[A]` Architect - no single right answer, judged on trade-off reasoning.

Each category opens with an **Assumed known** line pointing at the `01-java`, `02-spring` and `04-system-design` questions this material builds on. If those are shaky, go back before continuing.

This pack is about **the model and the inference path**. Retrieval architecture is `09-rag`, agent orchestration is `10-ai-agents`, whole-system placement is `04-system-design` Category 14, and framework API surface is `02-spring` Category 13. Model names, context limits and prices move every quarter, so answer with the mechanism and treat any number as an order of magnitude to reason with.

---

## 1. How a transformer behaves, and why it matters to you

> Assumed known: `01-java` Q211-212 (LLM integration, RAG) and `04-system-design` Q209 (what changes when a component is an LLM call).

1. `[C]` Explain what an autoregressive language model computes, in one sentence, and what that immediately implies about latency.
2. `[D]` Walk the path of one token through a decoder-only transformer: embedding, attention, feed-forward, layer norm, output logits. What is learned and what is arithmetic?
3. `[D]` Self-attention is quadratic in sequence length. Show why from the mechanism, and state the two practical consequences you plan around.
4. `[D]` What are query, key and value, and why does multi-head attention help rather than just being a wider single head?
5. `[T]` A model "knows" a fact. Where is that fact, and why can you not edit it the way you would edit a row in a table?
6. `[D]` Positional encoding: why is it needed at all, and what is the difference between absolute, learned and rotary (RoPE) positions?
7. `[T]` A model advertises a 200k context window. Why does quality degrade well before you reach it, and what is the mechanism behind "lost in the middle"?
8. `[D]` Pretraining, supervised fine-tuning and preference alignment (RLHF/DPO). What behavior does each stage produce, and which one are you fighting when the model is sycophantic?
9. `[D]` What is a base model versus an instruction-tuned model versus a reasoning model? When would you deliberately want the base model?
10. `[D]` Mixture-of-experts: what is routed, what is the memory cost versus the compute cost, and why does it change your self-hosting arithmetic?
11. `[T]` "The model is just predicting the next token, so it cannot reason." Give the strongest version of that argument and the strongest rebuttal, then say what you actually rely on in production.
12. `[D]` What does a "reasoning" or extended-thinking model do differently at inference time, and what does it do to your latency, cost and observability?
13. `[D]` Multimodal models: how does an image or audio input enter the same token stream, and what does that do to your token accounting?
14. `[A]` An interviewer asks how much transformer internals matter to an application engineer. Give your position with two concrete production decisions that changed because of the mechanism.

---

## 2. Tokens, context windows and the arithmetic

> Assumed known: `01-java` Q214 (cost and latency control) and `04-system-design` Q212 (token-based cost and rate limits).

15. `[C]` What is a token, why is byte-pair encoding used, and what is the rule of thumb for English text, code and JSON?
16. `[D]` Why does the same document cost more tokens in Hindi or Japanese than in English, and what does that do to a multilingual product's unit economics?
17. `[T]` A user pastes a 40-page PDF. Estimate the tokens, the prefill cost and the latency before the first output token, showing your arithmetic.
18. `[D]` Break a request's token budget into its parts - system prompt, tools, history, retrieved context, user input, output reserve - and say which one you cut first under pressure.
19. `[D]` Input tokens and output tokens are priced differently, usually by three to five times. Explain why from the mechanism, not the price list.
20. `[T]` Your feature's average cost per request doubles with no code change and no traffic change. Give five mechanisms that produce that, in the order you would check them.
21. `[D]` Prompt caching (prefix caching): what exactly is cached, what invalidates it, and how do you structure a prompt to maximize the hit rate?
22. `[D]` What is the token overhead of a tool definition, and why does adding a twelfth tool degrade a working feature in two separate ways?
23. `[D]` Output length control: `max_tokens`, stop sequences, and instructing length in the prompt. Which is reliable, which is advisory, and what breaks when the limit is hit mid-structure?
24. `[T]` You truncate conversation history to fit the window. Give three truncation strategies and the specific product bug each one produces.
25. `[D]` Counting tokens correctly: why is a character or word heuristic dangerous for billing and limits, and what do you do when the tokenizer is not available client-side?
26. `[D]` Context window versus effective working context versus training sequence length. Why are these three different numbers?
27. `[D]` Long-context models versus retrieval for a 500-page corpus. Give the cost, latency and accuracy comparison with numbers.
28. `[A]` Set the token budget policy for a product with a free tier and an enterprise tier. What do you enforce, where, and what does the user see when they hit it?

---

## 3. Decoding, sampling and determinism

> Assumed known: `04-system-design` Q221 (non-determinism and testing) and `01-java` Q216 (evaluating a non-deterministic feature).

29. `[C]` Explain greedy decoding, temperature, top-k and top-p, in terms of what each does to the logit or probability distribution.
30. `[T]` You set `temperature = 0`. Give four independent reasons the output still varies between calls.
31. `[D]` Temperature and top-p are often set together. Explain the interaction and why setting both aggressively is usually a mistake.
32. `[D]` What are logprobs, what can you legitimately infer from them, and what do people wrongly infer?
33. `[D]` Beam search is standard in translation and almost never used for chat. Explain why, from the objective it optimizes.
34. `[D]` Repetition penalties, frequency and presence penalties: what problem are they patching, and what do they break when set too high?
35. `[T]` A summarization feature works at temperature 0.7 and gets *worse* at 0.0. What is going on, and what does that tell you about the prompt?
36. `[D]` Constrained decoding and grammar-based generation: how does masking logits guarantee valid JSON, and what does it cost in quality?
37. `[D]` Speculative decoding: what is speculated, how is correctness preserved, and what workload does it help least?
38. `[D]` Self-consistency and sampling n completions then voting. When does this pay for itself, and what is the cost multiplier?
39. `[T]` Two providers serve "the same" open-weights model and give different answers to the same prompt at temperature 0. Name three causes.
40. `[D]` Seeds and `system_fingerprint`: what reproducibility do they actually give you, and how do you build a test suite that does not depend on them?
41. `[D]` Streaming changes what decoding parameters mean for the user. What can you no longer do once the first token is out, and how do you design around it?
42. `[A]` Pick the decoding settings for three features - a code generator, a customer-facing summarizer and a data extractor - and defend each choice.

---

## 4. The model landscape and how to choose

> Assumed known: `04-system-design` Q214 (model gateway, routing and fallback) and `02-spring` Q246 (Spring AI versus wrapping the provider SDK).

43. `[C]` Name the axes you evaluate a model on, in the order you actually apply them to a real decision.
44. `[D]` Frontier API models, open-weights models and small local models. Give the honest capability, cost and control comparison in 2026 terms.
45. `[T]` A benchmark table shows model A beating model B by two points. List five reasons that number should not decide your architecture.
46. `[D]` Contamination and benchmark saturation: how do you tell whether a reported score means anything for your task?
47. `[D]` Build a model evaluation harness for a selection decision. What tasks, how many samples, what metrics, and what do you do about cost drift?
48. `[D]` "Open source" model licenses: what actually differs between Apache 2.0, Llama-style community licenses and research-only weights, and which questions does legal ask you?
49. `[D]` Small models fine-tuned on your task versus a frontier model prompted. Give the decision rule and the arithmetic that supports it.
50. `[T]` Your feature works on the frontier model and fails on the cheaper one. Before accepting the cost, what four things do you try?
51. `[D]` Model families and versioning: how do you handle a provider retiring a version, silently updating a pointer alias, or changing a default?
52. `[D]` Provider lock-in: what is genuinely portable, what is not, and what does an abstraction layer cost you in capability?
53. `[D]` Routing and cascades: route by task, route by difficulty, or escalate on failure. Compare the three, with the accuracy and cost effect of each.
54. `[D]` Latency profile as a selection criterion: time to first token, tokens per second, and tail behavior. Which matters for which product shape?
55. `[D]` Region, residency and sovereignty constraints on model choice. What does "our data stays in the EU" actually require you to verify?
56. `[T]` A vendor offers a model that is 30 percent cheaper with "comparable quality". Design the two-week experiment that answers whether to switch.
57. `[D]` Embedding models, rerankers, guardrail classifiers and speech models are separate selection decisions from the chat model. What changes for each?
58. `[A]` Set the model policy for an organization of 40 teams: approved models, how a new one gets approved, and who owns the bill.

---

## 5. Prompting as engineering, not craft

> Assumed known: `02-spring` Q237 (`ChatClient`, where prompts should live) and `01-java` Q211 (LLM integration architecture).

59. `[C]` System prompt, developer prompt, user message, assistant message. What is each for, and what happens when you put instructions in the wrong one?
60. `[D]` Write the anatomy of a production system prompt: the sections you always include, in order, and why that order.
61. `[D]` Few-shot examples: how many, how chosen, and what makes an example harmful rather than helpful?
62. `[T]` Adding a fifth few-shot example makes accuracy worse. Give three mechanisms that explain it.
63. `[D]` Chain-of-thought prompting: what it does mechanically, when it is redundant on a reasoning model, and what it costs.
64. `[D]` Task decomposition versus one large prompt. Give the decision rule, and the failure mode of each direction taken too far.
65. `[D]` Negative instructions ("do not mention pricing") fail more often than positive ones. Explain why and how you rewrite them.
66. `[D]` Delimiters, XML-style tags and Markdown structure in prompts. Does it matter, and what is the evidence?
67. `[T]` Instruction placement: your critical constraint is in the middle of a 30k-token prompt and gets ignored. Give the fix and the mechanism behind it.
68. `[D]` Prompts as code: where do they live, how are they reviewed, versioned, tested and rolled back? Give the concrete setup.
69. `[D]` Prompt templating and injection through variables. How do you escape or fence user-supplied values inside a template?
70. `[D]` Localization: do you translate prompts, translate inputs, or instruct the output language? Compare quality, cost and maintenance.
71. `[D]` Prompt optimization tooling - DSPy-style compilation, automatic prompt search, and "let the model write the prompt". What do they buy and what do they cost you in reviewability?
72. `[T]` Someone improves the prompt and quality drops for a segment nobody tested. What process failure allowed that, and what gate do you add?
73. `[D]` Persona and tone instructions: what actually influences style, and why does the model drift back over a long conversation?
74. `[D]` Meta-prompting and self-critique passes. When does asking the model to check its own work help, and when is it theatre?
75. `[D]` How do you document a prompt so the next engineer can change it safely? What goes next to it in the repository?
76. `[A]` A team has one 4,000-token prompt doing six jobs, edited by five people. Plan the refactor, including how you prove you did not regress anything.

---

## 6. Structured output and tool interfaces

> Assumed known: `02-spring` Q239-240 (`entity()` structured output, tool calling and its security boundary).

77. `[C]` The three ways to get structured output - prompt and parse, JSON mode, and schema-constrained decoding. Compare reliability.
78. `[D]` JSON Schema as a contract with a model: which schema features help the model, which are ignored, and which actively hurt?
79. `[T]` The model returns valid JSON that is semantically wrong - a plausible enum value that does not exist in your system. Whose bug is it, and where do you catch it?
80. `[D]` Design the repair loop for invalid output: what you retry, what you change on retry, how many attempts, and when you stop.
81. `[D]` Optional fields, nulls and "I do not know" in a schema. How do you let the model abstain without inventing a value?
82. `[D]` Enums and closed vocabularies: how do you keep a 300-value taxonomy usable when it does not fit in the prompt?
83. `[D]` Tool/function definitions: naming, descriptions, parameter design. What does the model actually read, and what makes a tool get called wrongly?
84. `[T]` The model calls the right tool with a hallucinated argument value. Give three design changes that make that structurally impossible rather than unlikely.
85. `[D]` Parallel tool calls and multiple calls in one turn. What does that do to your idempotency and transaction boundaries?
86. `[D]` Tool results back into the context: formatting, size limits, truncation, and error messages the model can act on.
87. `[D]` Structured output versus tool calling for pure extraction. Which do you use and why does it matter operationally?
88. `[D]` Very large outputs - a 200-row table, a full document. How do you get structure without a single enormous generation?
89. `[T]` Constrained decoding guarantees the schema and your accuracy drops. Explain the mechanism and what you do about it.
90. `[A]` Design the extraction contract for a document-processing feature that must be auditable: schema, confidence, provenance and the human review path.

---

## 7. Embeddings and representation

> Assumed known: `01-java` Q213 (chunking, similarity metrics, hybrid search) and `04-system-design` Q217 (approximate nearest neighbor trade-offs). Retrieval architecture is `09-rag`.

91. `[C]` What is a text embedding, what is the vector space, and what does cosine similarity actually measure?
92. `[D]` Cosine, dot product and Euclidean distance. When are they equivalent, and what breaks when the vectors are not normalized?
93. `[T]` Two sentences with opposite meaning have 0.94 cosine similarity. Explain why, and what that means for a similarity threshold in your code.
94. `[D]` How do you choose an embedding model? Give the criteria in order, including the ones that are not accuracy.
95. `[D]` Dimensionality: what do you lose going from 3,072 to 768 dimensions, and what is Matryoshka truncation doing?
96. `[D]` Symmetric versus asymmetric embedding tasks, and why some models need a query prefix or instruction to work correctly.
97. `[T]` You change embedding models. What exactly must be rebuilt, what breaks silently, and how do you run the migration with a live index?
98. `[D]` Embedding drift over time - new vocabulary, new products, seasonal language. How do you detect it and what do you do?
99. `[D]` What information does an embedding fail to capture? Give four categories and the retrieval failure each one causes.
100. `[D]` Fine-tuning or adapting an embedding model on your domain. What data do you need, what gain is realistic, and what does it cost you operationally?
101. `[D]` Multi-vector and late-interaction representations (ColBERT-style) versus a single dense vector. What is the trade-off?
102. `[D]` Sparse, dense and hybrid representations. What does each one get right that the other cannot?
103. `[T]` Similarity scores are not probabilities and are not comparable across models or queries. Explain, and give the correct way to set a cut-off.
104. `[D]` Embedding non-text: images, code, tabular rows, user behavior. What changes about the pipeline and the evaluation?
105. `[D]` Privacy: can an embedding leak its source text? What does inversion research say, and how does that change how you store vectors?
106. `[A]` A team wants to use embedding similarity as a classifier. Give your position, the cases where it is right, and what you would build instead.

---

## 8. Context engineering and conversation state

> Assumed known: `02-spring` Q243 (chat memory, unbounded history as a cost defect) and `04-system-design` Q215 (caching LLM responses).

107. `[C]` What is context engineering, and why is it a better frame than prompt engineering for a production feature?
108. `[D]` The context window as a budget with an allocation policy. Write the policy: fixed reserves, elastic sections, and eviction order.
109. `[D]` Conversation memory options - full history, sliding window, running summary, structured state, retrieved history. Compare cost, fidelity and failure modes.
110. `[T]` A running summary of the conversation loses the one detail the user cares about. Why is this structurally likely, and what do you do instead?
111. `[D]` Context rot: quality degrading as a session gets longer even inside the window. What causes it and what are the interventions?
112. `[D]` Compaction and handoff: when a session must continue past the window, what do you carry forward and in what form?
113. `[D]` Multi-turn state that must be exact - a booking, a form, a cart. Why does it not belong in the conversation, and where does it go?
114. `[D]` Prompt cache design: order sections so the stable prefix is long, and quantify the saving on a real request shape.
115. `[T]` You reorder your prompt to put retrieved context first and cost triples. Explain the mechanism.
116. `[D]` Instruction hierarchy across system prompt, tool output and user message. What should the model trust, and what does it actually trust?
117. `[D]` What do you log about context, given that it may contain PII and is your only debugging artifact? Design the compromise.
118. `[D]` Personalization in context: user profile, preferences and history. What goes in every request, what goes in on demand, and what is the staleness contract?
119. `[D]` Session storage: where does conversation state live, what is the retention policy, and what does a right-to-erasure request require?
120. `[A]` Design the context strategy for an assistant used all day by the same user across a week of work. State what you deliberately forget.

---

## 9. Adaptation: prompting, fine-tuning, distillation

> Assumed known: `01-java` Q212 (RAG and its failure modes) and `04-system-design` Q209 (LLM as a component). Retrieval depth is `09-rag`.

121. `[C]` The adaptation ladder - prompting, few-shot, retrieval, fine-tuning, continued pretraining. State the decision rule for moving down a rung.
122. `[D]` What can fine-tuning do that prompting cannot, and what does prompting do that fine-tuning cannot? Be precise; most candidates get this backwards.
123. `[T]` "We will fine-tune it on our documentation so it knows our product." What is wrong with that plan, and what would you do instead?
124. `[D]` Supervised fine-tuning: dataset size, format, quality bar, and the split you need before you start.
125. `[D]` LoRA and QLoRA: what is actually being trained, the memory arithmetic, and what rank and alpha control.
126. `[D]` Full fine-tuning versus parameter-efficient methods. Give the cost, quality and operational comparison, including serving.
127. `[D]` Catastrophic forgetting: how does it show up after a fine-tune, and how do you detect it before your users do?
128. `[D]` Preference tuning - RLHF, DPO and the simpler variants. What problem needs preference data rather than labelled examples?
129. `[T]` A fine-tune improves your metric by 12 points and users complain more. Give three explanations.
130. `[D]` Distillation: teacher-student setup, how you generate the data, and the license and terms-of-service question you must ask.
131. `[D]` Data curation for a fine-tune: deduplication, contamination against your eval set, label noise, and the class-balance trap.
132. `[D]` How much data is enough? Give the way you decide empirically rather than by rule of thumb.
133. `[D]` Serving a fine-tuned model: adapter hot-swapping, multi-tenant adapters, versioning and rollback.
134. `[T]` Your provider's fine-tuning API produces a model that is worse than the base model at temperature 0. What do you check first?
135. `[D]` Continued pretraining on a domain corpus: when is it justified, what does it cost, and what does it not fix?
136. `[D]` Structured extraction is the classic fine-tuning win. Explain why it works so well there, with the economics.
137. `[D]` Fine-tuning for style, format and refusal behavior versus for knowledge. Which is reliable and which is not?
138. `[D]` The maintenance cost of a fine-tune: base model deprecation, data drift, re-training cadence, evaluation debt.
139. `[T]` You fine-tune a small model to match a frontier model on your task and hit 96 percent of its quality at 8 percent of the cost. What are the three questions before you ship it?
140. `[A]` A team proposes fine-tuning to fix a quality problem. Run the decision with them: what evidence you require, what you try first, and what would make you agree.

---

## 10. Evaluation

> Assumed known: `01-java` Q216 and `02-spring` Q245 (testing and evaluating a non-deterministic feature) and `04-system-design` Q221 (regression suites).

141. `[C]` Why is "we tested it and it looked good" not an answer, and what is the minimum credible evaluation setup?
142. `[D]` Build the evaluation pyramid for an AI feature: unit-level assertions, golden set, LLM-judged, human review, online metrics. What belongs where?
143. `[D]` Constructing a golden set: how many cases, how selected, who labels, and how you keep it from going stale.
144. `[T]` Your golden set is 200 hand-picked cases and the feature passes at 94 percent while users are unhappy. Diagnose the evaluation, not the feature.
145. `[D]` Deterministic assertions on non-deterministic output. Give six checks that are stable enough for CI.
146. `[D]` Reference-based metrics - exact match, F1, BLEU, ROUGE, BERTScore. What is each still good for, and where do they mislead?
147. `[D]` LLM-as-judge: how you write the rubric, why pairwise beats absolute scoring, and the biases you must control for.
148. `[T]` Your judge agrees with your team 90 percent of the time. Why might it still be useless, and what do you measure instead?
149. `[D]` Validating the judge: agreement with humans, Cohen's kappa, and what you do when they disagree.
150. `[D]` Sample size and significance: how many cases before a two-point difference means anything, given non-determinism?
151. `[D]` Failure taxonomy: how do you build one from real outputs, and how does it change what you optimize?
152. `[D]` Regression gates in CI: what runs on every commit, what runs nightly, what blocks a release, and what it costs per run.
153. `[T]` An eval suite that costs 40 dollars per run gets skipped by the team. Fix that without losing coverage.
154. `[D]` Online evaluation: A/B testing a generative feature. What is your primary metric, and why is user satisfaction usually the wrong one to start with?
155. `[D]` Implicit signals - regeneration, copy, edit distance, abandonment, thumbs. Which are trustworthy and how do you instrument them?
156. `[D]` Evaluating a multi-step or multi-component feature: end-to-end versus per-component. How do you attribute a failure?
157. `[D]` Evaluating safety and refusal behavior specifically. What does the suite look like and who owns it?
158. `[D]` Drift detection in production: what do you monitor when there is no label, and what triggers a re-evaluation?
159. `[T]` A provider silently updates the model behind your alias. What in your setup detects it, and how fast?
160. `[A]` Set the evaluation standard for an organization shipping ten AI features. What is mandatory, what is advisory, and how do you make it cheap enough to be followed?

---

## 11. Hallucination, grounding and abstention

> Assumed known: `01-java` Q212 (naive RAG failure modes) and `04-system-design` Q220 (guardrails in the request path).

161. `[C]` Define hallucination precisely enough to be measurable, and name the three distinct kinds.
162. `[D]` Why does a language model hallucinate at all? Give the mechanism, and why "it does not know it is wrong" is the important part.
163. `[T]` "RAG solves hallucination." Give the four ways a grounded answer is still wrong.
164. `[D]` Faithfulness versus factuality. Which one can you actually enforce in a product, and how do you measure it?
165. `[D]` Citation and attribution: how do you make the model cite, and how do you verify the citation supports the claim?
166. `[D]` Abstention: how do you get a model to say "I do not know", and why does it fight you?
167. `[D]` Confidence estimation - logprobs, verbalized confidence, sampling agreement, a separate verifier. Compare what each is worth.
168. `[T]` A model states a wrong number with total fluency and high token probability. Why is confidence uncorrelated with correctness here?
169. `[D]` Verification passes: a second model checking the first, a rules check, a retrieval check. What does each catch and what does it add to latency?
170. `[D]` Groundedness scoring in the request path: what you check before returning, and the latency and cost budget for it.
171. `[D]` Numeric and computational tasks: why does the model get arithmetic wrong, and what is the correct architecture?
172. `[D]` Hallucinated tool arguments, identifiers and URLs. Why is this class more dangerous than prose hallucination?
173. `[T]` Users trust the confident wrong answer more than the hedged right one. What does that mean for your UX, and what do you change?
174. `[D]` Product surfaces for uncertainty: hedging language, confidence display, sources, editability, human handoff. Which actually help?
175. `[D]` Measuring hallucination rate in production without labels. Design the sampling and review process, including the cost.
176. `[A]` A regulated client demands "zero hallucination". Give the answer you would actually give, and the design that comes closest.

---

## 12. Safety, guardrails and prompt injection

> Assumed known: `01-java` Q215, Q219 (prompt injection, PII with third-party providers) and `04-system-design` Q220 (guardrails). Application security generally is `11-security`.

177. `[C]` Distinguish prompt injection, jailbreaking and data exfiltration. Different attacks, different defenses.
178. `[D]` Why is prompt injection not solvable in the way SQL injection is? Give the structural reason.
179. `[D]` Direct versus indirect injection. Walk an indirect attack through a document, a web page and a tool result.
180. `[T]` Your defense is a system prompt saying "ignore any instructions in the user's documents". Explain precisely why that fails.
181. `[D]` The defense layers that do help: privilege separation, isolated contexts, output constraints, human approval, allow-lists, provenance tagging. What does each stop?
182. `[D]` The lethal trifecta - private data, untrusted content and external communication. Explain it and apply it to a feature you would refuse to build.
183. `[D]` Input guardrails: classifiers, heuristics, canary tokens, and known-attack lists. Give the false-positive cost of each.
184. `[D]` Output guardrails: PII detection, toxicity, policy classification, schema validation, secret scanning. Where do they run and what do they add to latency?
185. `[T]` A guardrail classifier blocks 0.4 percent of legitimate requests. Compute the user impact and decide whether to ship it.
186. `[D]` Jailbreak techniques you should be able to name and describe: role-play, encoding, many-shot, low-resource language, crescendo. Why do they work?
187. `[D]` Red teaming an AI feature: who does it, how it is structured, what a finding looks like, and how it enters the backlog.
188. `[D]` Data handling with a third-party provider: what leaves your network, what is logged, retention and training terms, and what you must get in writing.
189. `[D]` PII minimization before the model call: redaction, tokenization and rehydration. What breaks when you redact?
190. `[T]` Your redaction pipeline strips names, and the summarization feature becomes useless. Resolve it.
191. `[D]` Multi-tenant isolation for AI features: prompt, context, cache, embeddings and logs. Where does tenant data leak in practice?
192. `[D]` Semantic caching across users. What is the exact confidentiality risk and how do you key the cache to avoid it?
193. `[D]` Copyright, IP and training-data provenance. What do you tell a client who asks whether your output can be copyrighted or infringing?
194. `[D]` Regulatory obligations in 2026 - EU AI Act risk tiers, transparency and disclosure duties, sector rules. What do they actually require you to build?
195. `[T]` Legal asks you to guarantee the model will never produce prohibited output. Give your honest answer and the design that makes the risk acceptable.
196. `[A]` Design the AI safety review that a feature must pass before launch, proportionate enough that teams do not route around it.

---

## 13. Inference and serving mechanics

> Assumed known: `04-system-design` Q210-211, Q223 (serving path, inference modes, GPU capacity).

197. `[C]` Prefill versus decode. Explain the two phases, which is compute-bound, which is memory-bandwidth-bound, and what each means for latency.
198. `[D]` The KV cache: what is stored, why it exists, and the formula for its size per token.
199. `[T]` Compute the KV cache for a 70-billion-parameter model at 8k context with a batch of 32. Show the arithmetic and say what it implies about your GPU.
200. `[D]` Continuous (in-flight) batching versus static batching. Why did it change throughput so much, and what does it do to individual latency?
201. `[D]` PagedAttention and KV cache paging. What problem does it solve and what does it enable?
202. `[D]` Throughput versus latency on a single GPU: draw the curve as batch size grows and mark where you would operate.
203. `[D]` Time to first token and inter-token latency. What dominates each, and which do you optimize for a chat UI versus a batch job?
204. `[D]` Quantization: FP16, FP8, INT8, INT4, and weight-only versus activation quantization. What breaks, and how do you verify quality after quantizing?
205. `[T]` INT4 quantization gives you the same benchmark score and worse production behavior. Give two mechanisms.
206. `[D]` Tensor, pipeline and expert parallelism. When do you need each, and what does the interconnect have to do with it?
207. `[D]` GPU memory budget: weights, KV cache, activations, fragmentation and overhead. Size a deployment for a stated model and load.
208. `[D]` Cold starts: model load time, weight streaming, and why scale-to-zero is hard for inference. What do you do instead?
209. `[D]` Autoscaling inference: what signal do you scale on, given that requests are not equal-cost and queueing is invisible in CPU metrics?
210. `[T]` Your p50 is fine and p99 is eight times higher. Give the three causes specific to generation, before you blame the network.
211. `[D]` Admission control and queueing for inference: what you shed, what you queue, and the contract you give the caller.
212. `[D]` vLLM, TGI, TensorRT-LLM, llama.cpp and Ollama. What is each for, and where would you not use it?
213. `[D]` Serving embedding and reranking models: how is the workload profile different from generation, and what does that change?
214. `[D]` CPU, GPU and accelerator options in 2026, including inference-specific hardware. When is CPU inference the right answer?
215. `[D]` Multi-model serving on shared hardware: bin-packing, adapter multiplexing, and isolation between tenants.
216. `[A]` Decide between a managed API, a managed open-weights endpoint and self-hosted GPUs for a stated workload. Show the numbers and the non-cost factors.

---

## 14. Cost, latency and capacity engineering

> Assumed known: `04-system-design` Q212, Q215 (token cost and rate limits, response caching) and Category 13 above.

217. `[C]` Build the unit-cost model for an AI feature: what are the terms, and which one do people forget?
218. `[D]` Cost per resolved user task rather than cost per call. Why does the framing change the decisions you make?
219. `[T]` A feature is profitable at the average and loses money on 3 percent of users. Find the mechanism and fix it without capping the good users.
220. `[D]` Caching tiers - exact-match, normalized, semantic, and prompt prefix caching. Give the realistic hit rate and the risk of each.
221. `[D]` Batch and asynchronous APIs at a discount. What workloads move there, and what changes in your product contract?
222. `[D]` Cascades and routing for cost: the arithmetic of a two-tier cascade, including the escalation rate at which it stops paying.
223. `[D]` Output length is the biggest cost lever nobody pulls. How do you shorten output without degrading the product?
224. `[D]` Rate limits, quotas and fair use across tenants. What do you enforce, in which units, and what does the 429 path look like?
225. `[D]` Metering and cost attribution: how do you get from a provider invoice to a per-team, per-feature, per-tenant number?
226. `[T]` Your provider bill is 40 percent higher than your own token accounting. Give five reasons.
227. `[D]` Budget enforcement in code: soft limits, hard limits, degradation ladders, and what the user sees at each step.
228. `[D]` Capacity planning against provider rate limits and quotas. How do you plan a launch you cannot load-test at full scale?
229. `[D]` Latency budget for a generative feature end to end. Allocate it across guardrails, retrieval, prefill, generation and post-processing.
230. `[D]` Reserved capacity, provisioned throughput and committed spend. When do you commit, and what is the risk?
231. `[T]` Reducing latency increases your cost per request by 60 percent. Present that trade-off to a product owner and get a decision.
232. `[A]` Cut the cost of an AI product by half with the quality bar unchanged. Give the ordered plan and the expected contribution of each step.

---

## 15. Building it in Java and Spring

> Assumed known: `02-spring` Q237-246 (Spring AI API surface) and `01-java` Q211, Q217 (integration architecture, streaming). This category is about production behavior, not method signatures.

233. `[C]` Design the module boundary for AI code in a Spring service: what is behind a port, what is a provider detail, and what does the domain see?
234. `[D]` Timeouts for a call that legitimately takes 60 seconds. What do you set, at how many layers, and what is the interaction with a streaming response?
235. `[T]` A `RestClient` read timeout on a streaming call fires mid-generation. What has the user seen, what have you been billed for, and what do you do?
236. `[D]` Retries against a generative endpoint: what is safe to retry, what is not, and how do you avoid paying twice for the same answer?
237. `[D]` Idempotency for a request that costs money and has side effects. Design the key and the store.
238. `[D]` Streaming to a browser: SSE versus WebSocket versus WebFlux, plus proxies, buffering, heartbeats and reconnection with resume.
239. `[D]` Client disconnects mid-stream. What must your code do so you stop paying, and what does the provider actually charge you?
240. `[D]` Threading: blocking provider SDK calls in a servlet container, virtual threads, and reactive. What breaks at what concurrency?
241. `[T]` A synchronous LLM call inside a database transaction. Name every problem, in order of severity.
242. `[D]` Bulkheads and circuit breakers around a provider: what you isolate, the thresholds you choose, and what half-open means for a 30-second call.
243. `[D]` Fallback behavior: cached answer, cheaper model, degraded non-AI path, or an honest failure. How do you choose per feature?
244. `[D]` Observability for AI calls: the spans, attributes and metrics you need, and how you correlate a user complaint to an exact prompt and response.
245. `[D]` Logging prompts and completions when they contain PII. Design the sampling, redaction and retention policy.
246. `[D]` Testing: what do you stub, where do you record and replay, and what do you run against the real provider?
247. `[D]` Cost attribution in code: where the tenant, feature and user tags are set, and how you stop an unattributed call from shipping.
248. `[D]` Configuration and rollout: prompt and model version as configuration, feature flags, canaries and a kill switch that works in one minute.
249. `[D]` Multi-provider abstraction in Java: what you can express portably, where the leaks are, and what you deliberately do not abstract.
250. `[A]` You inherit a service with provider SDK calls scattered across 30 classes, prompts inline as string concatenation, no cost tracking and no evaluation. Sequence the remediation.

---

## 16. LLMOps, lifecycle and governance

> Assumed known: `04-system-design` Q213-214 (provider degradation, model gateway) and Categories 10 and 14 above.

251. `[C]` What is in an AI feature's release artifact beyond the code, and what does that do to your definition of a deployment?
252. `[D]` Versioning: prompt, model, tool schema, retrieval index and eval suite all version independently. How do you pin a combination and reproduce a past output?
253. `[D]` The AI release pipeline: what gates exist between a prompt edit and production, and how long does the whole thing take?
254. `[D]` Canary and shadow deployment for a generative change. What do you compare, and how long until you can decide?
255. `[T]` A prompt change is a one-line diff with a bigger blast radius than a schema migration. Convince a team that resents the process.
256. `[D]` Provider model deprecation with 60 days notice. Give the runbook.
257. `[D]` The data flywheel: capturing production interactions, labelling them, and feeding evals and fine-tunes. What consent and retention questions gate it?
258. `[D]` Incident response for an AI feature: what does a sev-2 look like, what are the first five actions, and what is your rollback?
259. `[D]` Monitoring an AI feature: the dashboard panels you actually need, and which of them is the leading indicator.
260. `[D]` Alerting without labels: what thresholds do you set on refusal rate, output length, latency, cost per request, cache hit rate and guardrail trips?
261. `[D]` Feedback collection in the product: what you ask, when, and how you avoid a signal that only unhappy users generate.
262. `[D]` Model and prompt registry: what is registered, what metadata, and who approves a promotion?
263. `[D]` Documentation and disclosure: model cards, system cards, and what you publish to users about AI involvement.
264. `[T]` Nobody owns the AI feature after launch - the team moved on and quality is drifting. What structural fix do you make?
265. `[D]` Build the cost and quality review cadence: what is reviewed, by whom, monthly versus quarterly, and what decisions it can make.
266. `[A]` Design the AI platform capability for an organization of 40 teams: what is centralized, what is federated, and what you refuse to own.

---

## 17. GenAI design exercises and leadership

> Assumed known: everything above. The design questions are worked in full in [scenario-questions.md](scenario-questions.md); the leadership questions have no scripted answer.

267. `[A]` Design a document-extraction service processing 200,000 invoices a day into a strict schema, with an accuracy target and a human review path.
268. `[A]` Design the evaluation and release platform that lets 30 teams change prompts and models safely.
269. `[A]` Design a self-hosted inference platform for a bank that cannot send data to a third-party provider, with the capacity and cost arithmetic.
270. `[A]` Design a customer-facing support assistant for 2 million users, with a cost ceiling per conversation and a hard requirement never to state a wrong policy.
271. `[A]` Design a code-assistance feature inside an internal developer platform, including IP handling, latency targets and how you prove it helps.
272. `[A]` Design the cost and quality control plane for an organization spending 4 million dollars a year across providers and self-hosted models.
273. An AI feature you shipped that users actually adopted - and what you measured to know.
274. A time you argued against an AI solution and shipped something simpler instead.
275. An AI quality or cost incident you owned, and the permanent fix.
276. A decision about AI you made that you would reverse today, and what it would take to reverse it.
277. How you have built AI engineering competence in a team that had only used a chat interface.
278. How you handle an executive who has decided on the technology before the problem is defined.
