# Microservices Interview Preparation Pack

Distributed systems depth for **Principal Engineer / Technical Lead / Solution Architect** interviews: service boundaries, contracts, event-driven architecture, distributed data and consistency, sagas and idempotency, resilience, discovery and mesh, observability, cross-service security, release engineering, capacity, testing, and monolith decomposition.

---

## Read [01-java](../01-java/README.md) and [02-spring](../02-spring/README.md) first

This pack is **not** an introduction to microservices. It assumes the broad pass in the Java pack and the Spring Cloud material in the Spring pack, and starts where those stopped.

| Assumed known | Where this pack takes it |
| --- | --- |
| `01-java` Q165-166 boundaries, monolith versus microservices | Category 1 - context maps, coupling metrics, event storming, the evidence that proves a boundary is wrong |
| `01-java` Q167-168 REST maturity, idempotency, versioning | Category 2 - gRPC deadlines, protobuf evolution, expand-contract, consumer-driven contracts |
| `01-java` Q169-170 CAP, PACELC, eventual consistency | Category 4 - the full consistency hierarchy, consensus, logical clocks, quorums, CRDTs |
| `01-java` Q171-173 saga, outbox, idempotent payment API | Category 5 - pivot steps, saga isolation anomalies, outbox versus CDC, the inbox pattern, deduplication at scale |
| `01-java` Q174-176 exactly-once, Kafka internals, repartitioning | Category 3 - transactions and the LSO, cooperative rebalancing, schema registry compatibility, event versioning |
| `01-java` Q177-179 tracing, discovery, rate limiting | Categories 7 and 8 - deadline propagation, tail-based sampling, cardinality, mesh data plane |
| `01-java` Q181 graceful degradation | Category 6 - retry budgets, metastable failure, load shedding, error budget policy |
| `02-spring` Q205-220 Spring Cloud, Gateway, Resilience4j, Feign, Kafka | Categories 6 and 7 - the same concerns without the framework, so you can defend them on any stack |
| `02-spring` Q221-233 test slices, Testcontainers, contract tests | Category 12 - the honeycomb, `can-i-deploy`, fault injection, testing in production |
| `02-spring` Q259-260 modular monolith, multi-tenancy | Category 13 - silo/pool/bridge, strangler fig mechanics, parallel run verification |

Where a question here overlaps, it starts one level deeper. Nothing is restated.

**The answer frameworks are not repeated either.** The four-layer technical answer, CIDER for scenarios and STAR-L for behavioral questions are defined once in [../01-java/README.md](../01-java/README.md). Re-read that section before your first mock.

### Scope boundary

This pack is deliberately platform-agnostic. Kubernetes, service mesh and cloud messaging appear only where a microservices decision genuinely depends on them. The full treatment of AWS services lives in `05-aws`, and CI/CD, Kubernetes operations and incident tooling live in `07-devops`. Whole-system design rehearsals live in `04-system-design`; Category 14 here is the microservices-specific subset.

---

## Files in this pack

| File | Purpose | When to use |
| --- | --- | --- |
| [README.md](README.md) | Prerequisite map, roadmap, what interviewers probe | Read first |
| [questions.md](questions.md) | 258 questions across 16 categories | Daily drilling |
| [answers.md](answers.md) | Mechanism-level model answers | After attempting yourself |
| [scenario-questions.md](scenario-questions.md) | Distributed incidents, design exercises, leadership situations | Mock practice |
| [cheatsheet.md](cheatsheet.md) | Fast revision reference | Night before, and 30 minutes before |
| [quiz.html](quiz.html) | Interactive flashcard version | Active recall |

### quiz.html

Open it directly in a browser - no server, no internet connection needed. Search covers question and answer text, filter by category, difficulty or your own progress, and mark each question Known or Review with progress saved in the browser. Press `/` to focus search.

Generated from the markdown, so the markdown stays the source of truth. After editing any of the three source files:

```bash
python tools/build-quiz.py 03-microservices
```

---

## What interviewers actually probe at this level

Microservices questions for a principal role are almost never "what is a microservice". They are testing whether you have operated a distributed system long enough to have been hurt by it.

Five recurring themes:

1. **You cannot tell the difference between slow and dead.** Timeouts, retries, circuit breakers, health checks and consensus all exist because a network gives you no way to distinguish a failed peer from a slow one. Most trick questions in this pack collapse into that single sentence.
2. **Every write that spans a boundary is at-least-once.** Not the messaging system, not the framework, not exactly-once semantics changes this. The consumer's idempotency is the only real guarantee, and candidates who know that answer half of Categories 3 and 5 in one move.
3. **Coupling moves, it does not disappear.** Splitting a service converts compile-time coupling into runtime, schema and temporal coupling. A strong candidate names which kind of coupling a design trades for which, rather than claiming decoupling.
4. **The failure mode is usually amplification, not the original fault.** Retry storms, thundering herds, metastable states, connection pool exhaustion, cascading timeouts. The interesting question is never "what broke" but "why did it stay broken".
5. **Organizational cause, technical symptom.** A great many distributed architecture problems are Conway's Law with extra steps. Being able to say "this is a team boundary problem wearing a service boundary costume" is a principal-level signal.

---

## Study roadmap

### Week 1 - Boundaries and contracts

Categories 1 and 2. Be able to justify a decomposition with coupling evidence rather than taste, and to write out the expand-contract sequence for both an API and a column from memory.

### Week 2 - Events and data

Categories 3 and 4. The densest material in the pack. Work every `[T]` twice, and make sure you can state the delivery-semantics answer without hedging.

### Week 3 - Sagas and resilience

Categories 5 and 6. Draw a saga with its pivot step, and be able to compute a retry amplification factor out loud.

### Week 4 - Runtime and observability

Categories 7, 8 and 9. Form a defensible position on service mesh - you will be asked - and be able to describe multi-window burn-rate alerting.

### Week 5 - Release, capacity and testing

Categories 10, 11 and 12. Little's Law, parallel-fanout latency arithmetic, and the CI gates that make independent deployment safe.

### Week 6 - Migration, design and mock

Categories 13 and 14, then work only from [scenario-questions.md](scenario-questions.md).

### Week 7 - Broker topology and legacy integration

Category 15. Broker choice, RabbitMQ topology ownership, enterprise integration patterns, bridging a legacy MQ estate and message-level security. Pair it with [`02-spring`](../02-spring/questions.md) categories 16 and 17 for the client-side APIs - this category deliberately covers the broker and the estate rather than the annotations.

---

## Your microservices story bank

Prepare these with real detail from Verizon India and Sonata Software. Generic answers are transparent at 19 years of experience.

1. A decomposition you led - the boundaries you chose, the one you got wrong, and how you found out.
2. A distributed incident where the amplification was worse than the fault, with the numbers.
3. A consistency decision you made deliberately, and how you explained it to the business.
4. An integration with an unreliable third party, and the specific resilience controls you added.
5. A messaging design where you chose the ordering and delivery guarantees consciously.
6. A migration you ran with zero customer-visible downtime, including the rollback point you never used.
7. A piece of distributed infrastructure you removed, and what it saved.
8. A standard you drove across teams you did not own.

---

## Self-check before the interview

- [ ] I can explain in one sentence why exactly-once delivery does not exist, and what to build instead.
- [ ] I can compute the retry amplification across three layers and describe the budget that fixes it.
- [ ] I can draw a saga, mark the pivot step, and name two isolation anomalies with countermeasures.
- [ ] I can state the expand-contract sequence for a column rename across two services, including the rollback point.
- [ ] I have a defensible position on service mesh versus libraries, and on when to stay monolithic.
- [ ] I have three stories with concrete numbers attached.
