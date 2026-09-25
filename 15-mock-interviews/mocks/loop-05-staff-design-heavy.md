# Loop 05 - Staff level, design-heavy

**The role.** A staff or principal engineer at a consumer-scale product company. Two of the five rounds are system design, and the distributed-data round is effectively a third. This is the loop that most closely resembles a large-company technical ladder interview.

**Total time.** 4 hours 15: 45 + 45 + 60 + 45 + 40, with 10-minute breaks. There is no hiring-manager warm-up in this loop, which is deliberate - some loops start cold at the hardest round, and that is worth rehearsing.

**What this loop is optimizing for.** Arithmetic, structure under ambiguity, and depth in distributed data. It is the least forgiving loop for a candidate who designs by naming components (Q70).

---

## Round 1 - System design, cold start (45 minutes)

**Persona.** A staff engineer. Deliberately vague in the first five minutes to see whether you extract requirements or start drawing (Q60, Q61).

Run **S10, real-time notification and fanout for twenty million users** (Q73).

### Opening prompt

> "Design a notification system. Twenty million users."

That is the whole prompt. The vagueness is the first test.

### What must happen in the first ten minutes

- Four to five scoping questions, no more (Q61), and the one that matters is the **fan-out distribution** - a system with a maximum of fifty recipients per event and one with a five-million tail are different systems.
- The connection arithmetic said out loud: 10 percent of 20 million concurrent is 2 million connections, therefore 20-40 gateway nodes, therefore the gateway is a separate tier.
- The broadcast arithmetic that forces the hybrid: 5 million materialized writes at 20,000 per second is four minutes.

If you have not written a number by minute ten, the round is already going badly (Q66).

### Follow-up ladder

1. *"Where does a user's connection actually live, and how does a message find it?"* - the registry versus broadcast-and-filter trade-off, with the node-count number that decides it.
2. *"A gateway node dies. Walk me through the next thirty seconds."* - reconnect storm, jittered backoff, gateway-side connection rate limiting, and resync from the last seen id. This is the operational question and it is where most candidates thin out.
3. *"A user has been offline for a week. What do they see?"* - retention policy, the per-user list, and whether unread count is exact or reconciled.

### Curveball - inject at minute 32

> "Product now wants notifications to be editable and retractable after they are sent."

**What is being scored.** Q68. Locate the blast radius before proposing: materialized rows must be updated or tombstoned, which is fine for the fan-out-on-write path and awkward for the broadcast path; already-delivered mobile pushes cannot be recalled, so the client must reconcile on open; and the read model now needs a version per notification. Cost it, then decide - and say the honest part: "a push already on someone's lock screen cannot be retracted, so 'retractable' means 'retractable in the app', and product needs to know that."

### Rubric focus

Depth and trade-offs. The hybrid threshold and the reconnect protocol are the two things the interviewer is listening for.

---

## Round 2 - Distributed data and consistency (45 minutes)

**Persona.** A database-leaning principal engineer. Precise, and will not accept a hand-wave about consistency.

| Minutes | Segment |
| --- | --- |
| 0-4 | Warm-up |
| 4-20 | Consistency and transactions |
| 20-34 | Sharding and scale |
| 34-40 | Migration |
| 40-45 | Questions |

### Opening prompt

> "A user updates their profile and immediately reloads the page. They see the old value. Tell me everything that could cause that."

**Model answer outline.** Enumerate by layer, briefly, and then say which is most likely: a CDN or browser cache; an application cache not invalidated or invalidated before the commit; a read replica with lag and no read-your-writes routing (the most likely, Q100); an eventually consistent store; a read from a different service with its own copy; or the write silently failing and returning 200. Then the diagnostic that discriminates: is it always, or a fraction of reloads, and does it correlate with load?

### Follow-up ladder

1. *"It is about one in twenty and it is worse at 9am. Which one is it?"* - replica lag, worse under the morning write burst. Then the fix: session-pinned or primary-routed reads for a user who has written in the last few seconds, and lag as an SLI with an alert (Q56, Q100).
2. *"You cannot change the routing. What else?"* - write-through the cache on the same request, or return the written value from the write response and have the client use it. Both are real answers and both have costs; name them.
3. *"Now the same problem across two services, where the second service keeps its own copy."* - now it is an event-driven consistency problem: ordering, idempotency, and the fact that the user's read may hit the second service before its consumer has processed the event. The honest answers are to route the read to the owner, to accept and display staleness explicitly, or to make the write synchronous across both and pay the availability coupling (Q47).

### Second thread - minute 20

> "Single Postgres, four terabytes, write-heavy, growing forty percent a year. What do you do?"

**Outline.** Q97 and Q101. Establish the actual constraint first - throughput, size or blast radius - because the answers diverge. Then the ladder before sharding: archive and retention, partitioning, index audit (every index slows every write), moving read load to replicas, moving the analytics copy out entirely. And only then sharding, with the shard key determined by the dominant access pattern and an explicit answer for the cross-shard queries.

### Curveball - inject at minute 30

> "We already sharded by customer id last year. Our biggest customer is now nine percent of the data and their shard is on fire."

**What is being scored.** Whether you know the standard failure of tenant sharding and can respond without a full re-shard. The options, with costs: split that tenant across sub-shards with a composite key (works, adds a special case forever); give them a dedicated physical shard (operationally simple, and often what happens in practice - say that); move their heaviest workload off the shared path entirely, for example their analytics or their append-heavy table; or re-shard on a different key, which is a project rather than a fix. The strong close is the general lesson: **a shard key chosen from a balanced distribution is only balanced until a customer succeeds.**

### Rubric focus

Depth. This round is unusually unforgiving of surface answers.

---

## Round 3 - System design, second round (60 minutes)

**Persona.** A principal engineer. Wants breadth, then one deep dive of their choosing, and will ask for cost.

Run **S9, the multi-tenant document processing platform** (Q72), on the 45-minute clock with 15 minutes of extra depth.

### Opening prompt

> "Design a platform that ingests documents from business customers, extracts structured data, and serves the results over an API."

### Follow-up ladder

1. *"Why a state machine rather than a pipeline of queues?"* - separately retriable stages, queryable state for support, resume without repeating expensive stages, and an explicit needs-review state that is a first-class outcome rather than an error.
2. *"What does this cost per document, and where does the money go?"* - the arithmetic from S9. If you cannot produce a per-document figure, this round caps at a 2.
3. *"The model improves and you want to reprocess thirty million historical documents. Go."* - a throttled low-priority path with its own budget, writing new result versions rather than overwriting, which is why every result carries model, prompt and pipeline versions.

### Curveball - inject at minute 40

> "One customer is forty percent of your volume and they submit their entire month on the last working day."

**What is being scored.** Multi-tenant fairness, which is a genuinely hard problem and is where staff-level design shows. The content: per-tenant queues with weighted fair scheduling rather than a single FIFO, so one tenant's backlog cannot starve everyone; per-tenant concurrency caps; a commercial conversation about a submission SLA rather than an engineering-only answer; and the capacity decision - do you scale for their peak (expensive and idle) or give them a documented longer SLA on burst (cheaper, needs to be sold). Naming that this is partly a contract problem, not only a scheduling problem, is the staff-level move.

### Rubric focus

Trade-offs and production judgement. The cost arithmetic and the fairness answer carry the round.

---

## Round 4 - Architecture review (45 minutes)

**Persona.** A principal engineer presenting a design from another team, present in the room.

Run the review from **loop-01 round 4** with a different emphasis: the same order-update design, but this interviewer cares about ordering and scale rather than about the outbox.

### Opening prompt

> "Here is a design one of our teams is about to build. Tell me what you think, and be direct - they have not started yet, so this is the cheap moment to be wrong."

### What is different from loop-01

The emphasis moves to **S-style ordering analysis** (Q174): what is the partition key, is the consumer concurrent within a partition, does the retry path preserve order, what happens on a rebalance or a dead-letter replay. Walk a concrete two-event trace rather than stating the principle.

### Follow-up ladder

1. *"What is the cheapest fix?"* - partition by the entity whose order matters. Cheap, and it limits per-key parallelism, which is the cost to name.
2. *"And the most durable one?"* - make consumers order-independent with a version on the entity and drop stale updates. More work, correct under replay and rebalance, and it survives a future consumer that nobody has written yet.
3. *"They have already built the search indexer. Does it need to change?"* - depends on whether a stale index entry is self-correcting on the next update. Usually it is, which makes it a lower priority than the email sender, and saying that ranking out loud is the point.

### Curveball - inject at minute 34

> "The team lead says: 'we will just make everything single-partition, then ordering is guaranteed'."

**What is being scored.** Whether you can reject a correct-but-fatal idea kindly. It does guarantee ordering, and it caps throughput at one consumer's capacity, removes horizontal scaling entirely, and makes a single slow message a head-of-line block for the whole system. The redirect: "you want ordering per order, not global ordering - partitioning by order id gives you exactly the guarantee you need and keeps the parallelism" (Q98's redirect structure).

### Rubric focus

Communication. The findings are known; the delivery in front of the author is the round (Q166).

---

## Round 5 - Bar raiser and rapid fire (40 minutes)

**Persona.** A principal engineer running a deliberately mixed round to test breadth and consistency across the day.

| Minutes | Segment |
| --- | --- |
| 0-18 | Rapid fire |
| 18-30 | One deep thread |
| 30-36 | Consistency check |
| 36-40 | Your questions |

### Rapid fire - minutes 0-18

Twenty questions, roughly fifty seconds each. **The strategy is Q201: lead with the answer, one clause of justification, then stop.**

A representative set, drawn across the packs:

1. Default isolation level, and why.
2. When would you not use a message queue?
3. What breaks first when you add a read replica?
4. `synchronized` versus `ReentrantLock` - when does the difference matter?
5. What does a circuit breaker actually protect?
6. Cheapest way to halve an AWS bill you have never seen?
7. When is a cache the wrong answer?
8. What is the first thing you check on a slow query?
9. Blue-green or canary for a database-coupled deploy?
10. Why is exactly-once delivery impossible?
11. What does a readiness probe check that a liveness probe should not?
12. Highest-cardinality thing you would never put on a metric label?
13. When would you choose a monolith in 2026?
14. What does prompt caching break on?
15. One sentence: why is retrieval usually the bug, not the model?
16. What does `HttpOnly` protect against, and what does it not?
17. Idempotency key - who generates it?
18. Your p99 is bad and your p50 is fine. First hypothesis?
19. Terraform wants to replace rather than update. What do you do?
20. What is the most expensive mistake in a design review?

**Scoring note:** the failure mode is three-minute answers. Six questions covered out of twenty is a fail regardless of the quality of the six.

### The deep thread - minutes 18-30

The interviewer picks the rapid-fire answer you were weakest on and goes three levels down (Q30's ladder, applied to whatever you fumbled). This is deliberate and unavoidable; the score is on how you handle the edge (Q195, S6).

### Consistency check - minutes 30-36

> "Earlier today you told my colleague *[a design position]*. Just now you said *[something that sounds different]*. Which is it?"

**What is being scored.** Q192 - the bar raiser exists partly to catch inconsistency across a loop. Either reconcile them honestly ("both are true under different constraints, and the constraint is *[X]*") or concede the change of mind cleanly ("I have changed my view since this morning's round, because *[the thing your colleague said]*"). Both are fine. Pretending you did not say the first one is not.

### Rubric focus

Communication and depth. Brevity in the rapid fire and calmness at the edge.

---

## After the loop

- **Time the rapid fire.** Count questions covered. Under twelve is the finding.
- Across two design rounds, did you produce arithmetic in the first ten minutes both times, or only when you liked the problem?
- Did you name the weakest part of your own design in both rounds (Q71)? For a staff-level loop this single habit is worth more than any individual finding.
- Did rounds 1 and 3 use the same structure? They should. The clock in Part B is meant to become automatic.
