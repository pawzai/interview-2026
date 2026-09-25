# AI Agents Interview Preparation Pack

Agent-system depth for **Principal Engineer / Technical Lead / Solution Architect** interviews: when an agent is the right architecture and when a workflow beats it, loop mechanics and termination, tool contracts and selection at scale, planning and reflection, memory, multi-agent topologies, protocols and interop, execution environments, human oversight, durability and workflow engines, failure modes, agent security, evaluation, observability, cost and latency engineering, and the Java, Spring AI and AWS production path.

This pack is about **the system built around the model**. It is the answer to "can you build something that decides its own next action, acts on production systems, and still has a maximum blast radius you can state, a cost you can cap, and a failure rate you can measure". Interviewers separate candidates on this quickly: a candidate who says "we use ReAct with LangChain and it works well" has followed a tutorial; a candidate who explains why they capped the loop at eight steps, what happens to a half-completed refund when a worker dies, and how they proved a tool change did not regress selection accuracy is engineering.

---

## Read [01-java](../01-java/README.md), [03-microservices](../03-microservices/README.md), [08-genai](../08-genai/README.md), [09-rag](../09-rag/README.md) and [11-security](../11-security/README.md) first

This pack is **not** an introduction to agents. It starts where the orchestration material in the earlier packs stopped, and nothing there is restated.

| Assumed known | Where this pack takes it |
| --- | --- |
| `01-java` Q212-214 RAG and orchestration basics | Category 1 - the autonomy ladder, and the five questions that disqualify an agent |
| `01-java` Categories 1-3 API design, exceptions | Category 3 - tool contracts written for a model rather than a human |
| `03-microservices` Q40-50 service contracts, idempotency | Category 3 - why idempotency matters more when the *model* can repeat a call |
| `03-microservices` Categories 4-6 sagas, distributed data, resilience | Categories 11-12 - compensation over a dynamically-generated plan, bulkheads per tool |
| `03-microservices` Categories 1-3 decomposition and coupling | Category 7 - multi-agent topologies and why most of them are a distributed system with a nondeterministic scheduler |
| `07-devops` Categories 3-5 containers and isolation | Category 9 - sandbox boundaries for model-generated code |
| `07-devops` Category 8 observability | Category 15 - tracing a run whose trajectory differs every time |
| `08-genai` Q1-3 autoregressive generation, prefill and decode | Category 2 - the quadratic context problem in a loop |
| `08-genai` Q30 temperature 0 is not deterministic | Category 1 - where agent nondeterminism actually comes from |
| `08-genai` Q80 structured output and tool calling | Category 3 - what constrained decoding guarantees and what it does not |
| `08-genai` Q60-70 reasoning and test-time compute | Category 5 - planning, reflection, and where the evidence for self-critique fails |
| `08-genai` Category 10 evaluation discipline | Category 14 - trajectory evaluation, pass^k, and the offline-online gap |
| `08-genai` Categories 13-14 cost and serving | Category 16 - the agent cost model and its heavy tail |
| `09-rag` Categories 5-8 retrieval and reranking | Category 4 - tool retrieval as a retrieval problem, with a worse failure mode |
| `09-rag` Category 9 context assembly | Categories 2 and 6 - context as a projection of durable state |
| `09-rag` Q135 injection through retrieval | Category 13 - what changes when the model has tools |
| `11-security` Categories 1-4 AppSec, identity, authorization | Category 13 - the confused deputy, principal propagation, and least privilege for an agent |
| `11-security` Category 12 AI security | Category 13 - the lethal trifecta and containment over detection |

Where a question here overlaps, it starts one level deeper.

**The answer frameworks are not repeated either.** The four-layer technical answer, CIDER for scenarios and STAR-L for behavioral questions are defined once in [../01-java/README.md](../01-java/README.md). Re-read that section before your first mock.

### Scope boundary

**The model belongs to `08-genai`.** Transformer behavior, decoding, prompting technique, fine-tuning, quantization and inference serving are that pack. The model appears here only as a component whose output is an **untrusted proposal** your code validates and authorizes.

**Retrieval belongs to `09-rag`.** Chunking, embeddings, ANN indexes, hybrid search, reranking and permission-aware retrieval are that pack. Retrieval appears here as **a capability the agent calls** and as the contract between the two systems (Q258).

**Distributed-systems fundamentals belong to `03-microservices`.** Sagas, idempotency, circuit breakers, backpressure and consumer-driven contracts are that pack. They appear here only where the agent changes them - most notably that the retry sources include a nondeterministic component you do not control.

**Application and cloud security belong to `11-security`.** Category 13 here covers only what is specific to agents: injection escalating to action, the confused deputy in an agent, the lethal trifecta, and containment as the response.

**Whole-system placement belongs to `04-system-design`.** Where an agent sits in a product architecture is that pack. Here we go inside the loop.

Frameworks, provider APIs and protocol versions churn every quarter. Everything here is written so the **mechanism** survives the products changing, and where a figure is quoted it is labelled as an order of magnitude to reason with rather than a fact to recite.

---

## Files in this pack

| File | Purpose | When to use |
| --- | --- | --- |
| [README.md](README.md) | Prerequisite map, roadmap, what interviewers probe | Read first |
| [questions.md](questions.md) | 272 questions across 17 categories | Daily drilling |
| [answers.md](answers.md) | Mechanism-level model answers | After attempting yourself |
| [scenario-questions.md](scenario-questions.md) | Agent incidents, design exercises, leadership situations | Mock practice |
| [cheatsheet.md](cheatsheet.md) | Fast revision reference | Night before, and 30 minutes before |
| [quiz.html](quiz.html) | Interactive flashcard version | Active recall |

### quiz.html

Open it directly in a browser - no server, no internet connection needed. Search covers question and answer text, filter by category, difficulty or your own progress, and mark each question Known or Review with progress saved in the browser. Press `/` to focus search.

Generated from the markdown, so the markdown stays the source of truth. After editing any of the three source files:

```bash
python tools/build-quiz.py 10-ai-agents
```

---

## What interviewers actually probe at this level

Agent questions for a principal role are rarely "what is ReAct". They are testing whether you have run an autonomous system that touched something that mattered.

Six recurring themes:

1. **Judgement about whether to build one at all.** The strongest signal at this level is being able to say "this is a flowchart, build the flowchart" or "this is a router plus five workflows" and defend it on cost, testability and blast radius (Q3, Q5, Q13). A candidate who reaches for an agent because the problem involves an LLM has failed the question before the design starts.
2. **Do you bound the damage?** "If an attacker controlled this agent for an hour, what is the maximum damage and how long until we notice?" is the question a security reviewer, a CFO and a good interviewer all ask in different words. The answer is capability restriction, scope in code, aggregate limits, reversibility by design, and reconciliation - not an accuracy figure (Q173, Q194).
3. **Do you have the arithmetic?** The quadratic context term, the cost of a step, the effect of caching, the compounding of per-step reliability over a trajectory, the 2-4× cost of splitting one agent into three. Most candidates have never done these sums, and they are what turn an opinion into a design (Q93, Q227, Q12).
4. **What happens when it half-finishes?** Partial side effects, crash and resume, duplicate execution, compensation over a dynamically-generated plan. This is the cluster that separates people who have operated an agent from people who have demoed one (Q148, Q150, Q157, Q164).
5. **How do you know it works?** Almost every team has a demo; very few have an eval set built from production traces, trajectory assertions, k repetitions with confidence intervals, and a release gate that covers cost and safety as well as success. "How did you know the tool you added did not regress the other tasks?" ends most agent interviews early (Q44, Q199, Q203, Q209).
6. **Prompt injection with tools.** The moment the agent reads untrusted content and holds a write tool, this is an authorization architecture, not a prompting problem. Candidates who answer with delimiters and a classifier are answering the 2023 question; the answer is trust separation and containment (Q128, Q183, Q190).

---

## Study roadmap

### Week 1 - Framing and the loop

Categories 1, 2 and 3. Be able to define an agent in one sentence, run the autonomy ladder out loud, enumerate every termination condition a production loop needs, and write a tool schema and a tool error message that a model can actually use.

### Week 2 - Selection, planning and memory

Categories 4, 5 and 6. Do the tool-definition token arithmetic, explain why adding a tool degrades unrelated tasks, state the trust order validation > verification > reflection and defend it, and design a memory store with keys, supersession and permissions.

### Week 3 - Topologies, protocols and environments

Categories 7, 8 and 9. Work every `[T]`. Be able to do the multi-agent cost arithmetic, enumerate what installing a third-party MCP server trusts it with, and give four ways a network-isolated sandbox can still cause harm.

### Week 4 - Oversight, durability and failure

Categories 10, 11 and 12. The three categories that separate production experience from prototype experience. Be able to reason through a 99 percent approval rate, state the two-phase side-effect record from memory, and present the failure taxonomy and control matrix.

### Week 5 - Security and evaluation

Categories 13 and 14. Be able to construct the email-to-ticket exfiltration attack unprompted, explain containment versus detection, and build an agent eval set out loud including trajectory assertions and the statistics.

### Week 6 - Cost, observability, Java and design

Categories 15, 16 and 17, then work only from [scenario-questions.md](scenario-questions.md). Category 17's design questions are the rehearsal.

---

## Your agent story bank

Prepare these with real detail from Sonata Software and the AI work from 2024 onwards. Generic answers are transparent at 19 years of experience, and in this domain especially - the specifics of what an agent was allowed to do, and what happened when it was wrong, are what make the work real.

1. An agent or automation you took to production: the autonomy rung you chose, what you deliberately did not automate, and why.
2. A time you argued against an agent and shipped something simpler, with the comparison that won the argument.
3. An agent failure you owned - cost, a wrong action, a data exposure - and the structural change you made afterwards.
4. A cost or latency problem in an agentic system, with the before and after numbers and the term that dominated.
5. An evaluation capability you built for a nondeterministic system, and what it caught that review had missed.
6. A tool contract or platform standard you drove across teams you did not own.
7. A security design you defended at a review, and the bound you led with rather than an accuracy figure.
8. A durability or resume bug, and the two-phase record or idempotency design that closed it.
9. A human-oversight design where you reduced approvals to increase safety, and how you measured it.
10. A stakeholder who wanted more autonomy than the system could safely support, and how you kept their support while narrowing the scope.

---

## Self-check before the interview

- [ ] I can define an agent in one sentence and name what structurally follows from the model owning the control flow.
- [ ] I can walk the autonomy ladder and say what control is given up at each rung.
- [ ] I can give the five questions that disqualify an agent, and the answers that disqualify it.
- [ ] I can enumerate every termination condition a production loop needs, and say why each produces a different outcome status.
- [ ] I can derive the quadratic context cost and give three mitigations with the arithmetic.
- [ ] I can write a tool schema and a tool error message for a model, and say what the schema actually enforces versus what I must validate.
- [ ] I can explain why adding a tool degrades unrelated tasks, and what evaluation gate catches it.
- [ ] I can state the trust order validation > verification > reflection and defend it against "we added a reflection step".
- [ ] I can do the multi-agent cost arithmetic and defend or reject a topology with a measured comparison.
- [ ] I can construct an indirect prompt injection attack end to end and explain why containment beats detection.
- [ ] I can explain the lethal trifecta and give the architectural response, not a mitigation.
- [ ] I can describe the two-phase side-effect record and say exactly why a resumed run would otherwise double-execute.
- [ ] I can reason through a 99 percent approval rate in both directions and say how I would measure which it is.
- [ ] I can build an agent eval set out loud - what is in a case, how many, where they come from, and the statistics I would report.
- [ ] I can answer "if an attacker controlled this agent for an hour, what is the maximum damage and how long until we notice?"
- [ ] I have three stories with concrete numbers attached, and one where the answer was not to build an agent at all.
