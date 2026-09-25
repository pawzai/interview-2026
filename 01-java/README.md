# Java Interview Preparation Pack

Preparation material for **Principal Engineer / Technical Lead / Solution Architect** interviews with a Java, Spring Boot, AWS, DevOps and AI focus.

Built for a candidate with **19 years of experience**:

| Period | Company | Primary stack |
| --- | --- | --- |
| 2007 - 2010 | Nittany Technologies | .NET, C#, ASP.NET, SQL Server |
| 2010 - 2022 | Verizon India | .NET moving into Java, Spring, microservices, telecom scale |
| 2022 - present | Sonata Software | Java 17+, Spring Boot, Spring Security, AWS, DevOps, AI integration |

---

## Files in this pack

| File | Purpose | When to use |
| --- | --- | --- |
| [README.md](README.md) | Roadmap, positioning, answer frameworks | Read first, revisit weekly |
| [questions.md](questions.md) | 256 categorized questions, core to principal level | Daily drilling, self-testing |
| [answers.md](answers.md) | Deep model answers with the tricky parts spelled out | After attempting questions yourself |
| [scenario-questions.md](scenario-questions.md) | Production incidents, architecture and leadership scenarios | Mock interview practice |
| [cheatsheet.md](cheatsheet.md) | Fast revision reference | Night before, and 30 min before the call |
| [quiz.html](quiz.html) | Interactive flashcard version of all 256 questions | Active recall practice |

### quiz.html

Open it directly in a browser - no server, no internet connection needed. Every question is collapsed by
default so you can answer out loud before expanding it.

- Search across question *and* answer text, filter by category, difficulty or your own progress.
- Mark each question **Known** or **Review**; progress is saved in the browser and survives a refresh.
- Press `/` to jump to search, `Esc` to clear it.

It is generated from the markdown, so the markdown stays the single source of truth. After editing
`questions.md`, `answers.md` or `scenario-questions.md`, regenerate with:

```bash
python tools/build-quiz.py 01-java
```

---

## How a 19-year candidate is actually evaluated

At this level, interviewers rarely care whether you can recite the `HashMap` load factor. They probe four things:

1. **Depth on demand.** Can you go three levels deeper than the answer you first gave? "Why?" three times in a row.
2. **Trade-off literacy.** Every answer should carry a cost, an alternative, and a condition under which you would choose differently.
3. **Production judgement.** Have you actually operated systems, or only built them? Incidents, rollbacks, on-call, cost, migrations.
4. **Influence.** How you make other engineers better, how you handle disagreement, how you decide when consensus fails.

Your .NET-to-Java transition is a strength, not a gap. Frame it as: *"I have implemented the same architectural patterns in two independent ecosystems, so I can tell which parts are essential and which are framework accidents."*

---

## Study roadmap

### Week 1 - Core Java depth

- Memory model, `equals`/`hashCode`, immutability, generics and type erasure
- Collections internals: `HashMap` treeification, `ConcurrentHashMap`, fail-fast iterators
- Exceptions, `try-with-resources`, `finally` traps
- Java 8 through 21: lambdas, streams, `Optional`, records, sealed types, pattern matching, virtual threads

### Week 2 - Concurrency and JVM

- `volatile`, `synchronized`, happens-before, `CompletableFuture`
- Executors, thread pool sizing, deadlock/livelock/starvation
- GC algorithms (G1, ZGC), heap tuning, memory leaks, native memory
- Profiling: JFR, async-profiler, heap dumps, thread dumps

### Week 3 - Spring and Spring Security

- Bean lifecycle, proxies, `@Transactional` self-invocation trap, scopes
- Boot auto-configuration, conditional beans, configuration properties
- Security filter chain, JWT vs session, OAuth2 / OIDC, method security
- Data access: JPA N+1, lazy loading, isolation levels, locking

### Week 4 - Distributed systems and AWS

- Microservice boundaries, saga, outbox, idempotency, CQRS
- Resilience: retries, circuit breakers, bulkheads, backpressure
- AWS: ECS/EKS, Lambda, RDS/Aurora, DynamoDB, SQS/SNS/Kinesis, IAM, VPC
- Observability: metrics, logs, traces, SLO/SLI, error budgets

### Week 5 - DevOps, AI and system design

- CI/CD pipelines, blue-green vs canary, IaC (Terraform/CDK), secrets
- Containers, Kubernetes essentials, cost optimization
- AI: RAG architecture, embeddings, vector stores, prompt/token cost control, guardrails, evaluation
- Full system design rehearsals under time pressure

### Week 6 - Mock interviews and story polish

- Work only from [scenario-questions.md](scenario-questions.md)
- Rehearse 10 STAR stories out loud, timed to 2-3 minutes each
- Re-read [cheatsheet.md](cheatsheet.md) daily

---

## Answer frameworks

### Technical questions - the four-layer answer

1. **Direct answer** in one sentence.
2. **Mechanism**: how it actually works under the hood.
3. **Trade-off**: cost, alternative, when you would not do it.
4. **Experience hook**: a one-line reference to where you used it in production.

> Example: *"`@Transactional` on a private or self-invoked method does nothing. Spring wraps the bean in a proxy, and self-invocation bypasses the proxy entirely. The fix is to split the method into another bean or use `AopContext.currentProxy()`, though I prefer splitting because the second option makes the proxying implicit. We hit this at Sonata when a retry path silently ran outside the transaction and produced partial writes."*

### Scenario questions - the CIDER structure

- **Clarify** the scope, scale, SLA and constraints before designing.
- **Isolate** the failure domain or the core requirement.
- **Decide** on an approach and state the trade-off explicitly.
- **Execute** with a concrete step-by-step plan.
- **Reflect** on what you would monitor, roll back or improve next.

### Behavioral questions - STAR-L

Situation, Task, Action, Result, and **Learning**. At 19 years of experience, the Learning is what separates you from a mid-level candidate. Always quantify the Result.

---

## Your story bank

Prepare these ten stories in advance. Replace the placeholders with real numbers from Nittany Technologies, Verizon India and Sonata Software.

1. Largest system you architected end to end (scale, users, throughput).
2. A production incident you led to resolution (detection, mitigation, RCA, prevention).
3. A performance problem you diagnosed and fixed (before/after numbers).
4. The .NET to Java migration or transition, and how you managed the risk.
5. A technical decision you lost, and how you supported the outcome anyway.
6. Mentoring a struggling engineer to independence.
7. A monolith-to-microservices or cloud migration you drove.
8. A security vulnerability you found or remediated.
9. An AI feature you shipped, including cost and quality controls.
10. A time you deliberately chose the "boring" solution and why it was right.

---

## Red flags to avoid

- Talking only about what your team did, never what *you* did.
- Answering architecture questions without asking about scale or constraints first.
- Naming technologies without naming the trade-off.
- Claiming ten years of a technology you touched for a quarter.
- Criticizing previous employers rather than describing constraints neutrally.

---

## Quick self-check before any interview

- [ ] I can explain the JVM memory model and GC choice in under three minutes.
- [ ] I can draw the Spring Security filter chain from memory.
- [ ] I can design a system for 10k requests/second and justify every component.
- [ ] I have three stories with concrete numbers attached.
- [ ] I have five thoughtful questions to ask the interviewer.
