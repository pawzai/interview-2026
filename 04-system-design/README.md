# System Design Interview Preparation Pack

Whiteboard design for **Principal Engineer / Technical Lead / Solution Architect** interviews: requirement framing and SLO derivation, back-of-the-envelope estimation, API and storage selection, caching and traffic tiers, asynchronous backbones, consistency and coordination, partitioning, reliability, multi-region, real-time delivery, search and analytics, AI in the request path, tenancy, security, cost - and fifteen full design walkthroughs.

---

## Read the four prior packs first

This pack is **not** an introduction to distributed systems. It assumes the mechanism-level material in the Java, Spring, microservices and database packs, and spends its time on the decision you make on a blank whiteboard instead.

| Assumed known | Where this pack takes it |
| --- | --- |
| `01-java` Q108-109 DDD, hexagonal architecture | Category 1 - turning a vague business statement into a 40-minute scope, and deriving SLOs from it |
| `01-java` Q167-168 REST maturity, idempotency, versioning | Category 3 - idempotent money movement, cursor stability, deprecation with 200 external clients |
| `01-java` Q160-161, `06-database` Category 10 caching and Redis internals | Category 5 - caching as an architectural *tier*: where it goes, what it costs, and what happens when it dies |
| `02-spring` Q205-220 Gateway, Resilience4j, Spring Cloud | Category 6 - the same concerns as capacity and traffic decisions, without the framework |
| `02-spring` Q261-268 Spring AI | Category 14 - inference in the request path, model gateways, RAG platforms, GPU capacity |
| `03-microservices` Categories 3 and 5 Kafka internals, delivery semantics, sagas, outbox | Category 7 - queue versus log *selection*, backlog draining, replay, and governing an event backbone across 20 teams |
| `03-microservices` Category 4 CAP, consistency models, consensus, logical clocks | Category 8 - placing the strong-consistency boundary, fencing tokens, quorums across regions |
| `03-microservices` Category 6 timeouts, retries, circuit breakers, metastable failure | Category 10 - blast radius, cells, shuffle sharding, static stability, degradation ladders |
| `06-database` Categories 1-3, 9, 11-12 modeling, indexing, sharding, NoSQL families, search | Categories 4 and 9 - storage *selection* per access pattern, and shard-key evidence |
| `06-database` Category 8 replication and failover | Category 11 - multi-region topologies, home-region partitioning, failovers that half-worked |
| `06-database` Categories 15-16 observability, security, cost | Category 15 - designing observability in, tenancy models, and cost as a design constraint |

Where a question here overlaps, it starts one level deeper or asks the *selection* question rather than the mechanism question. Nothing is restated.

**The answer frameworks are not repeated either.** The four-layer technical answer, CIDER for scenarios and STAR-L for behavioral questions are defined once in [../01-java/README.md](../01-java/README.md). Re-read that section before your first mock.

### Scope boundary

`03-microservices` answers **"how do services interact correctly"**. `06-database` answers **"how does storage behave"**. This pack answers **"given a blank whiteboard and 45 minutes, which components do you pick, how do you size them, and in what order do you say it"**.

So component internals are out of scope and referenced rather than explained. What is unique to this pack: requirement framing and SLO derivation, back-of-the-envelope arithmetic, selection between storage/queue/cache/delivery options, geo-distribution, real-time fanout, AI in the request path, and **the interview performance itself** - whiteboard sequencing, the time budget, and recovering from a bad start.

Cloud-specific detail lives in `05-aws`; CI/CD and Kubernetes operations in `07-devops`; RAG and agent depth in `09-rag` and `10-ai-agents`; security depth in `11-security`.

---

## Files in this pack

| File | Purpose | When to use |
| --- | --- | --- |
| [README.md](README.md) | Prerequisite map, roadmap, what interviewers probe | Read first |
| [questions.md](questions.md) | 261 questions across 16 categories | Daily drilling |
| [answers.md](answers.md) | Mechanism-level model answers with explicit arithmetic | After attempting yourself |
| [scenario-questions.md](scenario-questions.md) | 10 incidents, **15 full design walkthroughs**, 5 leadership situations | Mock practice - the core of this pack |
| [cheatsheet.md](cheatsheet.md) | Numbers, decision tables, the time budget | Night before, and 30 minutes before |
| [quiz.html](quiz.html) | Interactive flashcard version | Active recall |

### quiz.html

Open it directly in a browser - no server, no internet connection needed. Search covers question and answer text, filter by category, difficulty or your own progress, and mark each question Known or Review with progress saved in the browser. Press `/` to focus search.

Generated from the markdown, so the markdown stays the source of truth. After editing any of the three source files:

```bash
python tools/build-quiz.py 04-system-design
```

---

## What interviewers actually probe at this level

A system design round for a principal role is not a recall test. There is no correct answer to "design Twitter", and the interviewer knows it. Five recurring themes:

1. **They are testing sequencing and vocabulary, not knowledge.** Two candidates can name the same components and score differently because one derived them from stated numbers and the other listed them. The signal is whether each box on the board is justified by something said earlier - which is why the first five minutes matter more than the last twenty.
2. **Every number must have a derivation.** "We would need about eight servers" is worthless; "10,000 QPS at 40 ms service time is 400 concurrent requests, so 8 instances at 50 in-flight each with headroom" is the whole answer. When challenged by a factor of ten, showing the inputs beats defending the output.
3. **Naming the load-bearing constraint is the differentiator.** For a feed it is follower skew, not QPS. For payments it is correctness under retries. For a metrics platform it is cardinality. For a global write system it is the speed of light. Candidates who spend ten minutes on the API of a feed system and never mention the celebrity problem have failed the question regardless of how good the API was.
4. **Trade-offs must be priced, not listed.** "There is a trade-off between consistency and latency" scores nothing. "Making that write quorum global adds 80 ms to every commit forever, so I would partition by home region and pay the round trip only on username registration" scores everything.
5. **They are hiring someone who will still be right in two years.** So the boring, reversible design defended with a trigger condition beats the ambitious one presented with certainty. The same applies to what you *refuse* - the candidate who says "I would not shard a 3 TB database, and here is what I would do instead" is demonstrating the judgement the role is for.

A sixth, specific to 2026: **AI components are now assumed in the question**, and the interesting probe is not whether you can name a vector database. It is whether you treat a non-deterministic, heavy-tailed, per-token-priced dependency with a lower SLA than your own as a soft dependency with a fallback - or as a normal service call.

---

## Study roadmap

### Week 1 - Framing, estimation, APIs

Categories 1, 2 and 3. Memorize the latency table and the estimation arithmetic in [cheatsheet.md](cheatsheet.md) until you can produce QPS and storage figures without pausing. Practise the first five minutes of a design out loud, ten times, on ten different problems - it is the highest-leverage drill in this pack.

### Week 2 - Storage, caching, traffic

Categories 4, 5 and 6. Be able to map an access pattern to a store and defend it, and to describe what happens second by second when a cache tier dies.

### Week 3 - Async and consistency

Categories 7 and 8. The densest material here. Work every `[T]` twice, and be able to place a strong-consistency boundary and explain how you keep it small.

### Week 4 - Partitioning, reliability, multi-region

Categories 9, 10 and 11. Compute a shuffle-sharding combination count out loud, state the resharding sequence from memory with both cutover points marked, and form a defensible position on when *not* to go multi-region.

### Week 5 - Real-time, data, AI, cost

Categories 12, 13, 14 and 15. Be able to size a WebSocket tier and a vector index, and to argue an AI feature's availability arithmetic.

### Week 6 - Design rehearsal only

Work exclusively from [scenario-questions.md](scenario-questions.md). Three walkthroughs from Part B per day, timed at 40 minutes, spoken aloud, using the same spine every time. Then the Part A incidents, then Part C. **This week is the pack** - the questions and answers exist to make it possible.

---

## Your system design story bank

Prepare these with real detail from Verizon India and Sonata Software. Generic answers are transparent at 19 years of experience.

1. A system you designed end to end - the constraint you organized it around, and the estimate that decided a component.
2. A design you got wrong at scale, how you found out, and what the correction cost.
3. A capacity or launch event you prepared for, and which part of the forecast was wrong.
4. A deliberately boring choice you defended against a more exciting one, with the trigger you agreed for revisiting it.
5. A consistency or staleness decision you made and explained to a non-technical stakeholder, including the number you quoted.
6. A multi-region or geo-distribution decision - including one you deferred, and why.
7. A cost programme you led: the percentage, the biggest lever, and the cut you refused.
8. A system you decommissioned or did not build, and how you handled the people.
9. A design standard you drove across teams you did not own, and the mechanism that made it stick.

---

## Self-check before the interview

- [ ] I can run the first five minutes of any design - restate, scope, cut, extract six numbers - without thinking about the structure.
- [ ] I can quote the latency table, convert DAU to peak QPS, and size storage and a thread pool from memory.
- [ ] I can name the load-bearing constraint for each of the fifteen Part B exercises in one sentence each.
- [ ] I can state the resharding sequence with both cutover points, and say which one is irreversible.
- [ ] I can explain what happens in the 30 seconds after a cache tier fails, and how to design so it is survivable.
- [ ] I can compute composed availability across N dependencies and describe how reclassification fixes it.
- [ ] I can argue both sides of multi-region and say when I would refuse.
- [ ] I can put an AI component in a critical path with a stated fallback and a feature-level SLO.
- [ ] I have three stories with concrete numbers attached, and one about a design I got wrong.
