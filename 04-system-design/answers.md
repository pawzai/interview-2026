# Answers

Model answers for [questions.md](questions.md). Numbers match the question numbers exactly.

Answers follow the four-layer structure defined in [../01-java/README.md](../01-java/README.md): direct answer, mechanism, trade-off, experience hook. Hooks are written as *italic placeholders* - replace them with real detail from Verizon India and Sonata Software.

This pack answers **selection, sizing and sequencing**. Where a mechanism is owned by another pack it is referenced rather than restated: storage internals in `../06-database/answers.md`, service interaction in `../03-microservices/answers.md`, framework detail in `../02-spring/answers.md`. Q241-255 are worked as full design exercises in [scenario-questions.md](scenario-questions.md). Q256-261 are story questions with no scripted answer.

Cloud examples are named where a concrete service makes the answer sharper; the reasoning is intended to hold on any provider.

---

## 1. Framing, requirements and SLOs

### Q1. The first five minutes

1. **Restate the problem in one sentence and get agreement.** "So we are building a system where a user posts a short message and their followers see it in their feed." This catches a misunderstanding while it is still free.
2. **Enumerate the functional scope, then cut it out loud.** List six or seven capabilities, pick three, and say "I will design these three and mention the others at the end if we have time." The artifact is an agreed scope.
3. **Extract the non-functional numbers** (Q2). Users, QPS, read/write ratio, data size, latency target, availability target, consistency need. The artifact is a table of numbers you will size against.
4. **Sketch the API or the core operations.** Two or three signatures. This forces the data model and stops the conversation drifting into infrastructure.
5. **Draw the smallest system that works**, then scale it under pressure from your own numbers. The artifact is a diagram you will spend the rest of the interview evolving.

The reason the order matters is that every later decision is justified by an earlier artifact. If you draw before you have numbers, every component is decoration and the interviewer knows it.

### Q2. Functional versus non-functional, and the six numbers

Functional requirements are what the system does; non-functional are the qualities the doing must have. Interviews are won on the second set because the functional list is usually obvious.

The six numbers I always extract:

| Number | Why it decides something |
| --- | --- |
| Scale - DAU/MAU and requests per user per day | Gives QPS, which gives instance count and shard count |
| Read:write ratio | Decides whether caching and replicas are the design or an afterthought |
| Data volume and retention | Decides single database versus sharded, and the storage tier |
| Latency target, as a percentile | Decides synchronous versus asynchronous, and whether cross-region calls are legal |
| Availability target and RPO/RTO | Decides redundancy model and multi-region posture |
| Consistency requirement, per feature | Decides the hardest part of the design (Q14) |

I also ask two soft questions that change designs more than people expect: is the traffic spiky or smooth, and is the access pattern global or regional.

### Q3. From business statement to bounded scope

Take "users should be able to share posts". I decompose it into candidate capabilities: create a post, attach media, share to followers, share to a group, reshare with comment, delete and propagate deletion, notify recipients, rank the recipient's view, moderate content, analytics on reach.

Then I make the cut explicitly: "I will design create, fanout to followers, and the follower read path, because those carry the scale. Media upload I will treat as a solved sub-problem and describe in one line. Moderation and ranking I will leave as extension points and come back to if we have time."

The mechanism that makes this work is announcing the cut rather than silently ignoring things. An interviewer's real question is whether you can identify which 20 percent of the problem contains the hard engineering. Saying "reshare is the same write path with a reference, so it adds no new problem" demonstrates that judgement in one sentence.

*Hook: a feature you deliberately scoped down at the design stage and what it saved.*

### Q4. "Design Twitter" with no constraints `[T]`

The wrong move is to start drawing. The second wrong move is to ask a long list of questions mechanically, which reads as a memorized script.

What I ask, in order, and why:

1. **Which Twitter?** Posting and reading a timeline, or search, or trends, or DMs, or ads. Four of those are separate systems.
2. **What scale?** If the interviewer says "you tell me", I state my own assumption out loud - 200 million DAU, 2 posts and 50 timeline reads per user per day - and ask them to correct it. Owning the assumption is better than having no number.
3. **Read or write heavy, and how skewed is the follower distribution?** For this problem that single answer determines fanout-on-write versus fanout-on-read (Q186).
4. **How fresh must the timeline be?** Seconds or minutes changes the entire pipeline.
5. **Global or single-region?**

Then I say what I am not doing. The whole exchange is 90 seconds. The signal is that I know which constraints are load-bearing for *this* problem rather than asking about all of them.

### Q5. Availability targets in downtime

| Target | Downtime per month | Downtime per year | What it costs architecturally |
| --- | --- | --- | --- |
| 99% | 7.2 hours | 3.65 days | Nothing special; a single instance with restarts |
| 99.9% | 43 minutes | 8.8 hours | Redundancy within a zone, health checks, no single-instance dependencies |
| 99.95% | 22 minutes | 4.4 hours | Multi-AZ, automated failover, no manual step in the recovery path |
| 99.99% | 4.3 minutes | 53 minutes | Multi-AZ everything, no maintenance windows, automated failover under a minute, load shedding rather than failing |
| 99.999% | 26 seconds | 5.3 minutes | Multi-region active-active, no human in the recovery loop, and a deployment system that cannot cause an outage |

The step from 99.9 to 99.99 is where cost roughly doubles, because everything manual has to become automatic. The step to 99.999 is where it multiplies, because the deploy pipeline and the control plane become part of the availability calculation. Note also that 99.99 percent leaves 4.3 minutes a month - less than a single unplanned restart of a stateful component, which is why "we will just restart it" stops being an answer.

### Q6. "Five nines" `[T]`

The number is usually wrong for three reasons. First, it is rarely measured against a defined SLI, so nobody can tell whether it was met; a 30-second full outage plus a day of 40 percent error rate can both be "available" under a naive ping check. Second, the client's own availability and the network between you cap what the user experiences, so five nines server-side is invisible if the mobile network is at 99 percent. Third, the deployment pipeline typically causes more downtime than infrastructure does, and nobody was proposing to change it.

What I offer instead: define the SLI precisely (successful requests over valid requests, measured at the edge, per endpoint class), set an SLO that is achievable and *slightly uncomfortable*, attach an error budget, and agree what happens when the budget is spent. Then I quantify the delta - "99.99 is a multi-AZ design we can build this quarter, 99.999 is active-active multi-region and roughly doubles the infrastructure bill plus two engineers of ongoing work" - and let the business choose with the price visible.

*Hook: a time you converted an availability demand into an error-budget conversation.*

### Q7. SLI, SLO, SLA, error budget

- **SLI** - the measurement. A ratio of good events to valid events, with both defined precisely.
- **SLO** - the target for that measurement over a window. "99.9 percent of valid requests succeed, measured over 28 rolling days."
- **SLA** - the contractual version, with consequences. Always looser than the SLO, so you have room to react before money is at stake.
- **Error budget** - `1 - SLO`, expressed as a quantity of failure you are permitted to spend. It is the mechanism that turns reliability from an argument into arithmetic.

The SLIs I would pick:

| Surface | SLI |
| --- | --- |
| Write API | Availability: non-5xx, non-timeout responses / valid requests. Plus latency: fraction of requests under 300 ms |
| Read API | Same availability form, plus a latency SLI, plus a *freshness* SLI if it reads a replica or cache |
| Async pipeline | Freshness: fraction of events processed within N seconds of enqueue. Plus completeness: events out / events in over a window |

The async one is where most teams go wrong: availability of the consumer is not a user-visible property, but end-to-end lag is.

### Q8. Why percentiles and windows, not averages

An average hides the shape. A service with 99 percent of requests at 10 ms and 1 percent at 5 seconds has a 60 ms average, which looks excellent and describes nobody's experience. Averages are also non-composable and insensitive to exactly the tail that causes timeouts, retries and cascading failure.

The window matters for a different reason: a percentile without a window is undefined. "p99 latency is 200 ms" over a year is compatible with a week of total unusability. A rolling 28-day window matches how error budgets are consumed and is short enough that a bad week is visible.

The failure this prevents concretely: alerting on average latency means a bad deploy that adds a 10-second timeout path to 2 percent of traffic never fires an alert, while 2 percent of users are unable to use the product. That is the incident I have seen most often disguised as "monitoring says we are fine".

### Q9. Which percentile for what

- **Design for p99.** It sets your timeout budgets, thread pool sizes and capacity, because the tail is what consumes resources and triggers retries.
- **Alert on the SLO burn rate**, not on a raw percentile. Multi-window burn-rate alerting (fast burn over an hour, slow burn over six) is the version that pages you for the right things.
- **The business feels p99 and p99.9, but not the way you think.** A user makes 20 requests to load a page, so a p99 per request is roughly an 18 percent chance the page has a slow component. That arithmetic is why "our p99 is fine" and "the app feels slow" are both true.

p50 is useful for one thing only: detecting a change in the bulk of traffic, which usually means a plan change, a cache change or a code path change rather than an infrastructure problem.

### Q10. Chained p99s `[T]`

Two mechanisms compound.

**Fanout.** If a request calls five services in parallel and each has an independent 1 percent chance of exceeding its p99, the probability that *at least one* does is `1 - 0.99^5 = 4.9 percent`. So your end-to-end p99 is bounded by roughly your dependencies' p95, not their p99. With 20 dependencies the p99 of the whole is somewhere near the p80 of each part.

**Sequential addition.** For serial calls, latencies add, but percentiles do not: the p99 of a sum is less than the sum of the p99s (they rarely all peak together), yet it is far worse than any individual p99.

There is a third effect people miss: the tails are usually *correlated*, not independent, because they share causes - a garbage collection pause, a saturated network link, a hot shard, a noisy neighbor. Correlation makes the real number worse than the independence math predicts.

The design consequences: reduce fanout, hedge requests (send a second request after the p95 elapses and take the first response), and make components degradable so a slow dependency yields a partial answer rather than a slow one.

### Q11. RPO and RTO

**RPO** (recovery point objective) is how much data you may lose, expressed as time. **RTO** (recovery time objective) is how long you may be down.

| RPO | What it forces |
| --- | --- |
| 24 hours | Nightly backup. Cheap, and honest about losing a day |
| 1 hour | Snapshots plus continuous log archiving (WAL/binlog shipping) with point-in-time recovery |
| 5 minutes | Asynchronous replication to a standby, with lag monitored and alerted below the target |
| ~0 | Synchronous replication with a quorum, which costs write latency on every single write forever |

The last row is the one to reason about out loud: RPO of zero is not a backup strategy, it is a commit-path decision. You are paying an extra round trip to another failure domain on every write - a millisecond within a zone, several across a region, tens of milliseconds across a continent (Q168).

RTO drives a different axis: backup-and-restore, pilot light, warm standby, or active-active (Q161). Restoring 5 TB from object storage is hours regardless of your intentions, which is why an RTO under 15 minutes means a running standby, not a restore.

### Q12. Read-heavy, write-heavy, balanced

**Read-heavy** (typical ratio 100:1 or more): the first three decisions are a cache tier, read replicas or a read model, and a CDN. Denormalize toward the read shape. Writes can be slower and more careful. This is the common case and the easy case.

**Write-heavy**: caching does almost nothing for you. The first three decisions are partitioning the write path, buffering it (a log or queue in front of the store), and choosing an LSM-based store that turns random writes into sequential ones. You will also confront ordering and idempotency early, because the write path is now distributed.

**Balanced**: usually means two workloads sharing a system by accident. The first decision is to look for the seam and split them, because a design that is optimal for neither is the worst outcome.

The signal in this answer is recognizing that "read-heavy" is permission to trade freshness for latency, and "write-heavy" is not.

### Q13. Finding the single hardest constraint

I look for the constraint that, if relaxed, would make the problem ordinary. Concretely I test five candidates against the numbers: write volume, fanout skew, latency floor imposed by geography, a strict consistency or correctness requirement, and cost. Then I say which one the design has to be organized around.

Examples: for a feed, the hard constraint is follower skew, not QPS. For payments, it is exactly-correct balances under retries, not throughput. For a metrics platform, it is cardinality. For a global write system, it is the speed of light. For a chat system, it is connection state, not messages per second.

Naming it early changes the interview because every subsequent decision becomes an argument about the same axis, which reads as coherent design rather than a tour of components. It also protects you: if you spend ten minutes on the API of a feed system and never mention the celebrity problem, you have failed the question no matter how good the API was.

### Q14. Partitioning data by consistency need

Take an e-commerce system and separate it:

| Data | Consistency needed | Consequence |
| --- | --- | --- |
| Payment and ledger entries | Linearizable, transactional | Single-region primary, synchronous commit, no caching of balances |
| Inventory decrement at checkout | Strong for the decrement, eventual for display | Reservation with a conditional write; the product page may show stale counts |
| Order status | Read-your-writes for the buyer | Route the buyer's reads to the primary or a session-pinned replica |
| Product catalogue | Eventual, seconds | Cache aggressively, replicate globally, CDN the images |
| Reviews, recommendations, "customers also bought" | Eventual, minutes to hours | Precomputed, served from a read model, degradable to nothing |

The technique is to write this table before designing anything, then notice that the strong-consistency column is small. The design principle that follows is **keep the linearizable core as small as you can and push everything else outward**, because the small core is the only part that has to pay for coordination (Q120).

### Q15. Real-time, globally correct, in two months `[A]`

I do not refuse; I decompose the request into the three dimensions and ask which one is actually the requirement.

"Real-time" usually means "the user should not have to refresh". That is satisfiable with a 2-second push, or often with optimistic UI plus eventual convergence, neither of which requires global synchronous machinery. "Globally correct" usually means one specific invariant - no double-booking, no double-charge, no duplicate username - not that all data is linearizable. "Two months" is the only genuinely hard constraint, because it is external.

So I reshape it: ship single-region with global read replicas and a defined staleness bound, put the one true invariant behind a single-writer component in one region, and expose latency honestly to users in other geographies. Then I state the follow-on: the multi-region write story is a quarter of work and I would rather do it deliberately in Q3 than badly now.

The framing I use with stakeholders is to give them a menu with prices rather than a no: here is the two-month version and what it does not do, here is the six-month version, here is what changes for the customer in each.

*Hook: a scope negotiation where you delivered the invariant and deferred the generality.*

### Q16. A three-hour problem in 45 minutes `[A]`

My budget:

| Minutes | Activity |
| --- | --- |
| 0-5 | Scope agreement and the cut (Q3) |
| 5-10 | Non-functional numbers and estimation (Q2, Q18) |
| 10-15 | API and data model sketch |
| 15-30 | The core design, drawn and then scaled under my own numbers |
| 30-40 | The one hard part, in depth - the thing I named in Q13 |
| 40-45 | Failure modes, what I left out, and what I would build first |

What I deliberately leave undesigned, announced as such: authentication and authorization beyond "a token is validated at the edge", the CI/CD pipeline, the exact monitoring dashboards, admin tooling, and any second-order feature. I also leave the schema at entity-and-key level rather than full DDL.

The two mistakes this budget prevents are spending twenty minutes on a data model and never reaching scale, and reaching scale with no data model so nothing can be sized. The other discipline is to keep a running list of deferred items visible on the board, so the interviewer can see that they were choices.

---

## 2. Back-of-the-envelope estimation and capacity math

### Q17. The numbers to memorize

| Operation | Order of magnitude |
| --- | --- |
| L1 cache reference | 1 ns |
| L2 cache reference | 4 ns |
| Main memory reference | 100 ns |
| Mutex lock/unlock | 25 ns |
| Compress 1 KB | 2 us |
| Send 1 KB over 1 Gbps network | 10 us |
| SSD random read (4 KB) | 100 us (0.1 ms) |
| Read 1 MB sequentially from memory | 100 us |
| Round trip within a datacenter | 500 us (0.5 ms) |
| Read 1 MB sequentially from SSD | 1 ms |
| Disk seek (spinning) | 10 ms |
| Read 1 MB from spinning disk | 20 ms |
| Round trip cross-region, same continent | 25-50 ms |
| Round trip intercontinental (e.g. Europe to US East) | 80-150 ms |

The three ratios that do the work in an interview: memory is ~1,000x faster than SSD, SSD is ~100x faster than a cross-region round trip, and a cross-region round trip is ~100x a same-datacenter one. Those ratios tell you immediately that a cache saves you a millisecond, a cross-region hop costs you 50 of them, and no amount of cleverness beats geography.

### Q18. 100M DAU at 10 requests/day

Average QPS: `100,000,000 x 10 = 1,000,000,000` requests/day. Seconds in a day is ~86,400, which I round to 100,000 for arithmetic. So average is `10^9 / 10^5 = 10,000 QPS`.

Peak: I assume a peak factor of **2-3x** for a globally distributed consumer product with a smeared diurnal curve, **5-10x** for a single-country product with a sharp evening peak, and treat anything event-driven (a ticket sale, a sports final, a marketing push) as a separate spike calculation rather than a factor. Here I would take 3x and say so: **~30,000 QPS peak**.

Why the factor and not the average is the design number: capacity is provisioned for peak, and the peak-to-average ratio is exactly the argument for autoscaling or queue-based leveling. I also state the correction I would apply in reality - measure the actual hourly curve, because "3x" is a placeholder for a graph nobody has drawn yet.

### Q19. The arithmetic toolkit

Seconds: 86,400 per day (~10^5), ~2.6 million per month, ~31.5 million per year (~3 x 10^7).

Powers of two: 2^10 = 1 thousand (KB), 2^20 = 1 million (MB), 2^30 = 1 billion (GB), 2^40 = 1 trillion (TB).

Sizes: `char/byte` 1 B, `int` 4 B, `long`/`double`/timestamp 8 B, UUID 16 B binary or 36 B as text, a short URL 100 B, a tweet-sized record with metadata ~300 B, a small JSON document 1-2 KB, a web page 2 MB, a photo 200 KB - 2 MB, a minute of 1080p video ~50 MB.

Worked example: 500 million rows/year at 300 B is `1.5 x 10^11 B = 150 GB/year` of raw row data. With B-tree indexes and per-row overhead I multiply by 2 to 3 for an OLTP store, giving 300-450 GB/year. That number then decides "single PostgreSQL instance for three years" versus "shard now", which is the actual question being asked.

### Q20. Storage for 500M records/year, 5 years, 3 replicas

Assume 500 B per record including a few indexed columns.

- Raw: `5 x 10^8 x 500 B = 250 GB/year`.
- Index and row overhead: x2.5 for a typical OLTP table with three or four indexes and per-tuple headers, giving **625 GB/year**.
- Five years: **~3 TB** logical.
- Replication factor 3: **~9 TB** provisioned.
- Backups (say 30 daily incrementals plus weekly fulls, compressed): add ~50 percent of logical, so ~1.5 TB.
- Free space headroom for vacuum/compaction and growth: never fill above 70 percent, so divide by 0.7 → **~15 TB of provisioned storage**.

The conclusions I draw out loud: 3 TB logical is comfortably a single well-run relational instance, so the honest recommendation is not to shard for volume; but 500 million rows a year on one table means partitioning by time from day one, and the retention policy (Q62) matters more to the bill than the instance class does.

### Q21. Cache memory for 200M objects at 2 KB, 80/20

Total dataset: `2 x 10^8 x 2 KB = 400 GB`.

Under an 80/20 distribution, 80 percent of accesses hit 20 percent of objects: `40 GB` of hot data. Cache overhead is real - Redis costs roughly 50-100 B per key for the key, the object header and the hash table entry, plus fragmentation - so I add 30 percent: **~52 GB**, which I would provision as ~64 GB usable.

That buys ~80 percent hit ratio. To push higher I have to fight the tail of the distribution: 90 percent of hits needs closer to 35-40 percent of the data (140-160 GB), and 95 percent needs most of it. That non-linearity is the answer to "why not just cache more" (Q77) - the marginal gigabyte buys progressively less, and at some point a bigger read replica is cheaper than a bigger cache.

I would also state the assumption I am least sure about: real access distributions are frequently more skewed than 80/20 (closer to Zipf with a heavy head), which makes the cache cheaper than this estimate. The way to find out is to sample production keys, not to argue.

### Q22. Why the honest answer is bigger than the arithmetic `[T]`

The arithmetic gives you the number of servers needed to do the work at 100 percent utilization on a perfect day. The second-order factors:

1. **Utilization target.** You run at 40-60 percent CPU, not 100 (Q28), so multiply by ~2.
2. **Redundancy.** You must survive an instance failure and an AZ failure. Across three AZs, losing one means the remaining two carry everything - so each AZ needs 50 percent headroom.
3. **Deployment.** A rolling deploy removes capacity while it runs; so does a node upgrade.
4. **Tail latency and queueing.** Near saturation, latency grows non-linearly, so the SLO is violated well before capacity is exhausted.
5. **Warm-up.** JIT, connection pools and caches mean a fresh instance is slower for its first minutes, which matters during a scale-out event.
6. **The estimate itself is wrong.** It was built on an assumed peak factor and an assumed cost per request.

So 3 becomes 8: `3 x 2 (utilization) = 6`, `x 1.5 (AZ redundancy) ≈ 9`, round to 8 with autoscaling headroom. The way to say this is to give the arithmetic minimum and then the multipliers, because the interviewer is testing whether you know the difference between a benchmark and a production fleet.

### Q23. 1M concurrent at 3 Mbps

`10^6 x 3 Mbps = 3 x 10^6 Mbps = 3 Tbps` of egress. At the top of a busy hour that is `3 Tbps / 8 = 375 GB/s`, or ~1.35 PB/hour.

No origin serves 3 Tbps. A single well-provisioned server does perhaps 10-25 Gbps, so origin-only would need 150+ machines *and* an interconnect nobody wants to buy. The design consequence is that this is a **CDN problem by arithmetic, not by preference**: the origin serves the CDN, the CDN serves users, and the origin's traffic is `3 Tbps x (1 - hit ratio)`. At a 95 percent hit ratio the origin sees 150 Gbps, which is a real but buildable fleet.

The cost note that earns credit: egress is the dominant line item in this design. At commodity CDN pricing of roughly $0.02-0.08 per GB, 1 PB/hour is enormous, which is why every large video platform negotiates custom rates, pushes for peering, and invests heavily in per-title encoding to cut bitrate - a 20 percent bitrate reduction is a 20 percent reduction in the biggest bill in the company.

### Q24. Little's Law, sized

`L = λ x W`: concurrency = arrival rate x time in system.

At 5,000 QPS with 40 ms service time: `L = 5,000 x 0.04 = 200` requests in flight.

- **Threads (blocking model):** you need ~200 threads busy to sustain this, so a pool of 200-256 across the fleet. Split over 8 instances that is 32 per instance - a sane number. If the answer had been 2,000 threads, the design conclusion is not "more threads" but "go non-blocking or reduce W".
- **Connections:** if each request holds a database connection for 10 ms of its 40 ms, database concurrency is `5,000 x 0.01 = 50`. That is the pool size across the fleet - and it is why 20 connections often outperforms 100 (`../06-database/answers.md` Q235): the pool exists to bound the database's concurrency, not to be generous to the application.

The insight worth stating: the way to cut concurrency requirements is to cut `W`, not to raise `L`. Halving service time halves every pool in the system.

### Q25. Shard count, and why above the minimum

Suppose the target is 60,000 writes/second and a shard sustains 8,000 writes/second within its latency SLO. Minimum is `60,000 / 8,000 = 7.5`, so 8.

I would provision **16 or 32**, for five reasons:

1. **Headroom for growth** - resharding is the most expensive operation in the system's life (Q138), so I buy years of runway now.
2. **Peak versus average** - the 60,000 is probably an average.
3. **Skew** - shards are never evenly loaded; the hottest shard runs 1.5-3x the mean, so the mean must be well below the ceiling.
4. **Failure** - losing a shard's primary means its replica absorbs the load.
5. **Rebalancing granularity** - more, smaller shards make it possible to move load without moving everything, which is the whole argument for virtual nodes (Q137).

I also pick a number that makes future splits clean (a power of two, or a large fixed vnode count mapped onto fewer physical nodes) so the doubling operation is a mechanical split rather than a rehash of the whole keyspace.

### Q26. Why 2x load is a cliff, not a slope `[T]`

Queueing theory: for an M/M/1 queue, response time is `W = S / (1 - ρ)` where `S` is service time and `ρ` is utilization. At `ρ = 0.5`, `W = 2S`. At `ρ = 0.8`, `W = 5S`. At `ρ = 0.95`, `W = 20S`. The curve is a hyperbola with an asymptote at 1, so a linear increase in load produces a super-linear increase in latency.

Then the amplifiers turn a latency problem into an outage:

- Slower responses mean more concurrent requests (Little's Law), which exhausts threads and connection pools.
- Clients time out and **retry**, adding load exactly when there is none to spare (Q153).
- Queues grow, so requests are served after the client has abandoned them - pure wasted work.
- Memory grows with in-flight requests, provoking garbage collection, which makes service time worse.
- Health checks time out, so instances are removed from the load balancer, concentrating load on the survivors.

That last loop is the definition of a **metastable failure**: the system stays down after the original overload disappears, because retries and cold caches now sustain it. The design answers are admission control and load shedding (Q94), because the only way to survive is to serve less than was asked.

### Q27. Rough monthly cost, and what dominates

A defensible sketch for a mid-sized system:

| Line | Rough basis | Note |
| --- | --- | --- |
| Compute | ~$50-100/month per always-on mid-size instance or container | Predictable, and the easiest to over-provision |
| Managed database | 2-4x the equivalent raw compute, plus storage and IOPS | Storage and IOPS often exceed the instance cost |
| Storage | Object storage ~$0.02/GB/month; block storage ~$0.10/GB/month; provisioned IOPS extra | Cheap until retention is unbounded |
| Data transfer | Egress to internet ~$0.05-0.09/GB; cross-AZ and cross-region each metered | The line nobody estimates |
| Managed premium | Kafka, search, cache and warehouse services carry a large multiple over self-hosted compute | Usually still worth it |

The one that dominates and surprises people is **data transfer**, in three flavors: internet egress for anything media-heavy, cross-AZ chatter from a service mesh or a replicated datastore that nobody realized was metered, and cross-region replication. The second surprise is **idle non-production environments**, which in many organizations are 30-40 percent of the bill for zero traffic.

The habit that matters: attach a cost estimate to the design while you are drawing it, and specifically to any arrow that crosses a zone, region or internet boundary.

### Q28. Utilization targets and queueing

You size for 40-60 percent because of the `W = S / (1 - ρ)` curve above (Q26) plus three practical constraints: you need room to absorb the failure of one AZ out of three, room for a rolling deploy, and room for the scale-out delay while autoscaling reacts (typically 1-5 minutes for VMs, 20-60 seconds for containers, and never instant).

Queueing theory says the knee is around 70-80 percent for a single server, and it moves *right* with more parallel servers (an M/M/c queue with c=20 tolerates higher utilization than one with c=2), which is why a large stateless fleet can run hotter than a single database. It moves *left* with variable service times, which is why any workload with a heavy tail - LLM calls, report generation, large uploads - must run at lower utilization or be isolated into its own pool (Q155).

Stateful components get lower targets still: a database at 80 percent CPU has no room for a vacuum, a rebuild, or a plan regression.

### Q29. Fanout with a 200-average, 50-million-max distribution

Average case: a write with 200 followers generating 200 timeline inserts. At 10,000 writes/second that is `2 x 10^6` inserts/second - large but shardable, and each insert is small.

Worst case: one write produces 50 million inserts. Even at 100,000 inserts/second/shard aggregate, that single write is 500 seconds of work for the whole cluster, and it arrives as a burst. It will saturate the fanout workers, starve every ordinary user's write, and blow through any queue's latency SLO.

The distribution, not the average, is the design:

- **Hybrid fanout** (Q186). Fanout-on-write for ordinary users, so reads are cheap. Fanout-on-read for accounts above a threshold - their followers pull from a per-author cache at read time and merge.
- **Threshold as a tunable**, not a constant, and measured from the actual follower histogram.
- **Priority separation:** celebrity fanout goes to its own queue so it cannot delay normal writes (Q94, Q155).

The reason this is the canonical example: it is a system where the p99.99 of one input dimension defines the entire architecture, and where designing for the mean produces something that fails on day one.

### Q30. Challenged by a factor of ten `[T]`

I do three things, in order.

First, **show the derivation, not the number**: "that came from 100 million DAU, 10 requests each, 86,400 seconds, times a 3x peak factor". Almost always the disagreement is about one input, and now it is visible.

Second, **ask which input they think is wrong**. If they say the peak factor is 10x rather than 3x, I accept it immediately and say what changes: "then peak is 100,000 QPS, so the connection tier becomes the constraint and I would put a queue in front of the write path rather than autoscaling into it."

Third, **check whether the decision is sensitive to the disagreement at all**. Often it is not: 10,000 or 100,000 QPS both say "shard it and cache it", and I say so - "the design is the same across that range; the difference is instance count, which is a capacity plan, not an architecture."

What I do not do is defend the number, and I also do not abandon my whole design because one input moved. The signal being tested is whether the design is *derived* from the numbers or merely accompanied by them.

### Q31. How much estimation is enough `[A]`

My rule: **estimate only until the number changes a decision, then stop and say which decision it changed.**

Concretely, estimation is worth it when it decides single-node versus distributed, cached versus not, synchronous versus asynchronous, one region versus several, or whether a component is affordable at all. Those are the five forks where an order of magnitude flips the answer.

It is theatre when it produces a precise instance count in a 45-minute design (that is a capacity exercise for a spreadsheet with real measurements), when it estimates something with no ceiling nearby, or when it computes a second decimal place from an assumption invented 30 seconds earlier.

The mature version, which I would say aloud: "I need one significant figure and the right power of ten. If the answer is within 3x of a ceiling, I will measure rather than estimate, because at that distance the estimate cannot decide it."

*Hook: an estimate that changed a build-versus-buy decision, and one that was ignored because it did not matter.*

---

## 3. API and interface design at system scale

### Q32. A CRUD resource, properly

```
POST   /v1/orders                 201 + Location, body = created resource
GET    /v1/orders/{id}            200, 404
GET    /v1/orders?status=OPEN&limit=50&cursor=...   200
DELETE /v1/orders/{id}            204, 404
PATCH  /v1/orders/{id}            200, 409 on version conflict
```

The details that matter:

- **Idempotency:** `POST` takes an `Idempotency-Key` header (Q35). `PUT`, `DELETE` and `GET` are naturally idempotent.
- **Concurrency:** `ETag` on `GET`, `If-Match` on `PATCH`/`PUT`, `409` or `412` on mismatch. Without this, last-write-wins is silently the contract.
- **Pagination:** cursor-based, with `{"items": [...], "next_cursor": "..."}`. `limit` has a documented default and maximum. No total count unless it is cheap, and if given, labelled approximate (`../06-database/answers.md` Q39).
- **Errors:** a single machine-readable envelope - `{"type", "title", "status", "detail", "instance", "errors": []}` (RFC 7807 shape) - with a stable `type` clients can branch on, never a message string.
- **Status codes:** 400 for malformed, 401 unauthenticated, 403 unauthorized, 404 for missing *or hidden*, 409 for state conflict, 422 for semantically invalid, 429 with `Retry-After`, 503 with `Retry-After` for shedding.
- **Timestamps** are RFC 3339 UTC, money is an integer minor unit plus a currency code, and enums are strings the client is told to treat as open.

### Q33. REST, gRPC, GraphQL, messaging

The criteria I actually apply:

| Question | Answer implies |
| --- | --- |
| Who is the consumer - an external third party, a browser, a mobile app, another one of my services? | External/browser → REST+JSON. Internal service-to-service → gRPC |
| Is the caller waiting for the result? | No → messaging/event contract |
| Do many different clients need many different subsets of the same graph? | GraphQL, or a BFF per client (Q46) |
| Do I control both ends and the deployment schedule? | If yes, gRPC's tighter coupling is affordable and its schema evolution rules are a feature |
| Is streaming (either direction) part of the requirement? | gRPC or SSE/WebSockets, not request-response REST |
| How many hops, and is per-call latency and CPU material? | High volume east-west → gRPC/protobuf saves real CPU and bytes |
| Who debugs it at 3 a.m., and with what tools? | REST's `curl`-ability is a genuine operational property |

My defaults: REST for anything public or browser-facing, gRPC for internal high-volume synchronous calls, events for anything where the caller should not wait, and GraphQL only when the client-diversity problem is real and I am prepared to staff the governance it needs (Q34).

### Q34. GraphQL's four system-level problems `[T]`

1. **N+1 and unbounded resolver fanout.** One innocuous query becomes hundreds of backend calls. Fix: DataLoader-style batching per request, and a hard budget on resolver calls.
2. **Query cost is unbounded and client-controlled.** A nested query can be quadratic. Fix: static query complexity analysis with a cost limit, depth limits, and persisted queries so only pre-approved documents are executable in production.
3. **Caching collapses.** HTTP caching keys on URL and method; a single `POST /graphql` defeats CDN and intermediary caching entirely. Fix: persisted queries over `GET` with cache-friendly URLs, plus per-entity caching behind the resolvers rather than per-response caching in front.
4. **Observability and rate limiting lose their unit.** Every request is the same endpoint, so per-endpoint latency, error rates and quotas mean nothing. Fix: attribute metrics per operation name and per field, and rate-limit on computed cost rather than request count.

A fifth, which is the one that bites organizationally: **authorization moves into every field resolver**, so it is enforced in hundreds of places instead of one. That needs a central policy layer, not resolver-by-resolver checks.

### Q35. Idempotent money movement

```
POST /v1/payments
Idempotency-Key: 7f9c2b1e-...            (client-generated, required)
{ "amount_minor": 250000, "currency": "INR", "destination": "acct_123" }
```

The specification:

- **Key generation:** the client generates it, once, before the first attempt, and reuses it for every retry of that logical operation. If the server generates it, retries cannot share it and the mechanism is useless.
- **Scope:** unique per `(api_key/tenant, endpoint, key)`. Never global - a shared key namespace across tenants is a cross-tenant data leak waiting to happen.
- **Storage:** a row inserted with a unique constraint on the scoped key *in the same transaction as the payment*, so the uniqueness and the effect commit or fail together. This is the whole trick; a separate cache check is a race.
- **Request fingerprint:** store a hash of the request body. Same key with a *different* body is a client bug: return `422`, do not silently return the old result.
- **Lifetime:** 24 hours to 7 days for a normal API; for payments I keep the record for the reconciliation window (often 30-90 days) because disputes reference it. Expiry is a partitioned-by-day table dropped by partition, not a `DELETE`.
- **Replay response:** the *original* result with the original status code, plus a header such as `Idempotent-Replay: true`. Returning 200 for a replay of a 201 is acceptable; returning a different body is not.
- **In-flight concurrent duplicate:** the second request finds the key row locked or present-but-incomplete. Return `409 Conflict` with `Retry-After: 1`, and never start a second charge.

### Q36. Pagination for a public API

| Style | Behavior | When |
| --- | --- | --- |
| Offset/limit | Simple, jumpable, but O(offset) at the database and unstable under concurrent writes - rows shift, so items are duplicated or skipped | Small, mostly static datasets; admin UIs with page numbers |
| Cursor (keyset) | Encodes the last seen sort key. O(1) with the right index, stable under inserts | The default for public APIs |
| Opaque state token | Encodes the sort key plus filters, a snapshot marker, and sometimes a server-side scroll context | Search and large exports, where consistency across pages matters |

What I expose: an **opaque, versioned cursor** - base64 of a signed struct containing the sort key tuple, the filter fingerprint and a format version. Opaque means I can change the internals without breaking clients; signed means clients cannot forge one into an expensive query; the filter fingerprint means I can reject a cursor reused with different filters instead of returning nonsense.

What I promise: pages are stable with respect to *deletions and updates* only in that you will not see the same item twice; newly inserted items may appear or not depending on their sort position; cursors expire after N hours; and `limit` is capped. What I refuse to promise is a total count, and a snapshot of the whole result set - that is an export API, not a list API.

### Q37. Long-running operations over HTTP

```
POST /v1/exports              → 202 Accepted
                                Location: /v1/exports/{id}
                                Retry-After: 5
GET  /v1/exports/{id}         → 200 {"status":"RUNNING","progress":0.4}
                              → 200 {"status":"SUCCEEDED","result_url":"..."}
                              → 200 {"status":"FAILED","error":{...}}
```

Key points:

- The **operation is a resource** with its own id, status, timestamps, progress and terminal result. `GET` on it always returns 200 - the HTTP status describes the retrieval, not the job. A `FAILED` job is a successful read.
- **Poll interval** is server-controlled via `Retry-After`, so you can back clients off during overload. Clients should also apply jitter. For long jobs, escalate to a webhook or SSE rather than letting a million clients poll every second.
- **Failure** is learned from the status resource's terminal state, with a structured error, a retryable flag, and a correlation id for support. A job that is stuck must also be able to reach `FAILED` - so it needs a lease and a timeout, otherwise it stays `RUNNING` forever and no client learns anything.
- The `POST` carries an idempotency key so a retried submission does not create a second job.
- Terminal results have a retention policy, stated in the response (`expires_at`), because "where is my export from March" is otherwise an unbounded storage commitment.

### Q38. Every layer that must cooperate for a safe retry `[T]`

1. **Client:** must retry with the *same* idempotency key, bounded attempts, exponential backoff with jitter, and only for retryable conditions (timeout, 429, 502/503/504, connection failure) - never for 4xx other than 429.
2. **Client library/SDK:** must not silently retry non-idempotent methods, and must not have its own hidden retry layer that multiplies the caller's (this is how three layers become eight attempts, Q111).
3. **Load balancer / proxy:** `retry-on` policies must be configured for idempotent requests only. A proxy that retries a `POST` on upstream timeout duplicates work invisibly.
4. **Service:** must implement the idempotency store *transactionally* with the effect (Q35), and must return the original response on replay.
5. **Database:** the uniqueness must be a constraint, not a `SELECT` then `INSERT` - the latter is a race under Read Committed (`../06-database/answers.md` Q36).
6. **Downstream calls made by the service:** each must itself be idempotent, with a *deterministic* key derived from the inbound key (e.g. `hash(inbound_key + step_name)`), not a fresh UUID per attempt. This is the step most designs miss.
7. **Message publication:** if the operation emits an event, the outbox pattern makes publication atomic with the state change; consumers dedupe on the event id.
8. **Timeouts:** the client's timeout must exceed the server's, or the client gives up on requests that will succeed, generating retries indefinitely.

The one-line summary for an interview: a retry is safe only if the *entire* path from client intent to the last side effect is keyed on one identity generated once.

### Q39. Bulk and batch endpoints

```
POST /v1/orders/batch
{ "items": [ {"ref":"a", ...}, {"ref":"b", ...} ] }

207 Multi-Status
{ "results": [
    {"ref":"a", "status": 201, "id": "ord_1"},
    {"ref":"b", "status": 422, "error": {"type":"invalid_currency", ...}}
] }
```

Decisions to state explicitly:

- **Partial success is the default** for bulk, and the response must be per-item, keyed by a client-supplied `ref` so the client can correlate without relying on array order. All-or-nothing is a different endpoint (`atomic: true`) and should be offered only if you can genuinely do it in one transaction.
- **Size limit:** I cap items per request (100-1,000 depending on item cost) and total body size (1-10 MB). The reason is not politeness: an unbounded batch is an unbounded transaction, an unbounded latency, an unbounded memory allocation and an unmetered rate-limit bypass.
- **Rate limiting counts items, not requests**, otherwise a batch endpoint is a hole in your quota system.
- **Idempotency** applies to the batch as a whole *and* per item; I key each item as `hash(batch_key + ref)` so a partial retry does not duplicate the items that succeeded.
- For anything above the cap, the answer is the async operation pattern (Q37) with a file in object storage, not a bigger limit.

### Q40. Versioning at the system level

What I commit to publicly: a **major version in the URI** (`/v1/`), never a breaking change within a major version, and additive changes any time. Clients must tolerate unknown fields and unknown enum values - stated in the documentation as a requirement, because it is the single thing that makes additive evolution possible.

Header-based negotiation is technically cleaner and operationally worse: it is invisible in logs, in a browser and in a support ticket, and cache keys forget it. I use headers only for opt-in previews of new behavior within a version.

The "never break" (single-version) strategy is the right target for internal APIs with continuous deployment, and unrealistic for external ones over a five-year horizon.

Retiring a version with real clients:

1. **Measure first** - per-version, per-client request counts. You cannot deprecate what you cannot attribute.
2. Announce with a date, and add `Sunset` and `Deprecation` headers plus a link, so it appears in client logs.
3. Provide a migration guide with a diff, not prose, and a compatibility shim if the change is mechanical.
4. **Brownouts**: return 410 for a scheduled few minutes, escalating in duration. This finds clients no email reached, which is most of them.
5. Enforce with per-client quotas that ratchet down rather than a cliff.
6. Keep one escape hatch: a named contractual exception for the two customers who genuinely cannot move, with an end date.

### Q41. Event versus HTTP compatibility

For HTTP, compatibility is a two-party, synchronous negotiation: you know your callers, you can see them in your logs, and both sides are live at the same moment. Backward compatibility (new server, old client) is usually enough.

For events, three things change:

1. **Consumers are unknown and unbounded.** You cannot enumerate who depends on a field.
2. **Both directions are required.** Old consumers must read new events (backward), and after a replay or a rollback, new consumers must read old events (forward). Schema registries call this `FULL` compatibility, and it means you can only add optional fields with defaults and remove optional fields - never rename, never retype, never make required.
3. **Events are stored, so the old format persists.** An HTTP contract change is over in an hour; an event format lives as long as your retention or your event store, which for an audit log may be seven years. Your consumers must handle every historical version forever, which is why a version field and a documented upcasting path belong in the design from day one.

The practical consequence: event schemas need a registry with enforced compatibility in CI, and a policy that a breaking change means a **new topic**, dual publication, and a consumer migration - not an edit.

### Q42. Designing for mobile clients

- **Payload:** one round trip per screen, not one per widget - so an aggregating endpoint or a BFF (Q46). Trim optional fields, use compact field names only if measured, and gzip/brotli everything. Return exactly the image variants the client will render, with URLs pointing at a CDN, rather than making the client compose them.
- **Chunking:** large uploads use resumable, chunked upload with a session id and per-chunk checksums, because a mobile connection will drop mid-upload. Downloads support range requests.
- **Offline:** the client queues mutations locally with a client-generated id, which doubles as the idempotency key (Q35). The server must therefore accept client-supplied ids. Reads use a delta/sync endpoint - `GET /sync?since=<token>` - returning changes and tombstones, so a client that was offline for a week does not refetch the world (Q193).
- **Retry policy I require of clients:** exponential backoff starting at 1 s with full jitter, a cap of ~60 s, respect for `Retry-After`, no retry on 4xx except 429, and a circuit breaker that stops retrying when the app is backgrounded. I publish this in the SDK rather than in documentation, because documentation is not a control.
- **Version skew:** old app versions live for years. The API must support the oldest version you have not force-upgraded, and a force-upgrade mechanism (a server-driven minimum version) has to exist from launch.

### Q43. Correct API, clients still cause an outage `[T]`

The controls belong in the contract, enforced at the edge:

1. **Quotas and rate limits per client**, with the headers and status code specified (Q44) so correct behavior is expressible.
2. **Pagination limits** - a maximum `limit`, and no unbounded list endpoint.
3. **Query cost limits** - maximum filter cardinality, maximum date range, maximum expansion depth, and a maximum result size. Unbounded expressiveness is an unbounded workload.
4. **Payload and batch size caps** (Q39).
5. **Timeouts stated in the contract** so a client knows when to give up, and a server-side `statement_timeout` that guarantees it.
6. **Concurrency limits per client**, which is the control people forget: a client honoring your rate limit with 500 parallel connections still exhausts your pool.
7. **Backoff requirements** and `Retry-After` semantics, with the SDK implementing them.
8. **Deprecation and brownout mechanics** (Q40), so you can shed a misbehaving integration.

The framing that matters: an API is a contract about *load*, not just about shape. If the contract permits a client to ask for something you cannot afford to serve, that client will eventually ask for it, without malice.

*Hook: an integration that took you down while behaving exactly as documented.*

### Q44. Rate limits in the API

Return on every response, or at least on throttled ones:

```
RateLimit-Limit: 1000
RateLimit-Remaining: 47
RateLimit-Reset: 30              (seconds until the window resets)
```

On rejection: **429 Too Many Requests**, with `Retry-After` in seconds, and a body identifying which limit was hit (`type: "rate_limit_exceeded"`, `scope: "per_tenant_write"`). Naming the limit is what turns a client's guessing game into a fix.

Use **503 with `Retry-After`** instead when you are shedding load rather than enforcing a quota - the distinction tells the client "you did nothing wrong, the system is degraded", which should drive different client behavior (back off harder, show a different message).

Expected client behavior, which I document and put in the SDK: track `RateLimit-Remaining` and pace proactively rather than sprinting into a wall; on 429, sleep for `Retry-After` with jitter; treat repeated 429s as a signal to reduce concurrency, not just to wait; never retry a 429 immediately; and surface quota exhaustion to the application rather than hiding it in an infinite retry loop.

### Q45. Webhooks as an outbound interface

- **Delivery guarantee:** at-least-once, and say so. Consumers must dedupe on the event id, which you include in a header along with a timestamp and event type.
- **Signing:** HMAC-SHA256 over `timestamp + "." + raw_body` with a per-endpoint secret, sent as a header, with the timestamp inside the signed payload so it cannot be replayed later. Support two active secrets so rotation is possible without downtime. Consumers must verify before parsing.
- **Retry schedule:** exponential with jitter - e.g. 10 s, 1 m, 5 m, 30 m, 2 h, 6 h, 24 h - for up to 24-72 hours, then park in a dead-letter store with a manual/API replay path. Success is a 2xx within a short timeout (5-10 s); a slow consumer is a failed delivery.
- **Ordering:** do not promise it. Offer per-entity sequence numbers so consumers can detect out-of-order and re-fetch current state. "Thin" webhooks that carry only an id and force a read-back are more robust than fat ones for exactly this reason.
- **The consumer's outage becomes your problem** in three ways: retry queues grow and consume your storage and workers; a slow consumer occupies delivery workers and starves others; and per-consumer failures generate support load. The controls are per-endpoint concurrency and queue isolation (a slow tenant must not block others), automatic disabling after a sustained failure window with notification, and a status endpoint the customer can self-serve. Egress also needs SSRF protection: resolve and validate destination IPs, block internal ranges, and use an egress proxy.

### Q46. BFF versus one API versus a composing gateway

| Option | Strength | Cost |
| --- | --- | --- |
| One general-purpose API | Single contract, single place for auth and limits, cheapest to run | Every client gets the union of everyone's needs; mobile over-fetches; changes are negotiated across all clients |
| BFF per client type | Each client's payload and round-trip count are optimal; the client team owns and deploys it | N codebases, N deployments, duplicated cross-cutting logic, and a strong tendency for business logic to leak in |
| Gateway with composition | One deployment, per-client views, no new services | The gateway becomes a shared monolith with 30 teams' logic in it - the anti-pattern from `../03-microservices/answers.md` Q107 |

My rule: start with one API. Add a BFF when a specific client's needs diverge *structurally* - typically mobile, where round trips and payload size are a product requirement, or a public API that must be stable while internal ones churn. Keep the BFF thin: composition, shaping, and client-specific caching only; no business rules, no writes that are not pass-through. Put authentication, rate limiting and observability in the gateway or mesh so the BFF does not reimplement them.

The GraphQL answer is a fourth option that is really "one BFF with a query language", and it carries the governance cost in Q34.

### Q47. Deprecation policy for 40 internal and 200 external clients `[A]`

**Policy.** Three tiers with different guarantees: external public (12-month deprecation notice, 6-month sunset window), external partner (6 months, negotiated), internal (30 days, or immediately with a migration PR from my team). Additive change is always allowed. Breaking change requires a new major version, and no more than two major versions are supported at once.

**Mechanism, because policy without enforcement is a wish:**

1. **Attribution.** Every request is authenticated and tagged with client id, version and operation. A dashboard shows per-version, per-client usage. This is the prerequisite for everything else.
2. **Machine-readable deprecation.** `Deprecation` and `Sunset` headers, plus the same information in the OpenAPI spec and the SDK, which logs a warning. Clients learn without reading email.
3. **CI enforcement.** A schema-diff gate that fails any PR introducing a breaking change to a published contract, with an explicit override that requires a version bump. Contract tests from `can-i-deploy` for internal consumers (`../03-microservices/answers.md` Q220).
4. **Brownouts** at 90, 60 and 30 days out, of increasing length, announced in advance. This is the only reliable way to find silent dependents.
5. **Quota ratchet** in the final month rather than a cliff, so the failure is gradual and visible.
6. **An exception register** with named owners and end dates, reviewed monthly. Exceptions are fine; unbounded exceptions are how you end up supporting v1 forever.

**What I would drive organizationally:** deprecation cost is borne by the provider today and the consumer never, which is why nothing ever gets retired. I would make each supported major version carry a visible operational cost against the owning team's budget, so keeping v1 alive competes with their roadmap.

*Hook: a version you retired, and the client you discovered only during a brownout.*

---

## 4. Storage selection and data modeling for a system

### Q48. The default, and what changes it

My default is a **single well-run relational database** - PostgreSQL - with the schema designed properly, plus object storage for blobs. It gives transactions, constraints, ad-hoc queries, JSON when needed, full-text search that is adequate to a surprising scale, and an operational story every engineer already knows.

The three pieces of evidence that would change it:

1. **A write rate or dataset size beyond a single primary's ceiling**, demonstrated with numbers rather than anticipated - tens of thousands of writes per second sustained, or tens of terabytes of hot data. Then I partition, then shard, then consider a distributed store.
2. **An access pattern the relational model serves badly at the required scale** - very high-cardinality time series, full-text relevance ranking, deep graph traversal, or vector similarity at high QPS. These get a purpose-built store *alongside* the relational one, fed by CDC or an outbox, not instead of it.
3. **An availability or geography requirement the primary cannot meet** - multi-region active-active writes, or a latency target that requires writes to be served locally on three continents.

What is *not* evidence: an anticipated scale that is three years away, a preference for a technology, or a single slow query (which is almost always an index problem - `../06-database/answers.md` Q3).

### Q49. Access pattern to storage engine

| Access pattern | Choice | Why |
| --- | --- | --- |
| "Get and update this entity by id, with invariants across a few entities" | Relational | Transactions and constraints are the requirement |
| "Get this item by a known composite key, millions of QPS, no ad-hoc queries" | Key-value / DynamoDB | Predictable O(1) access; you are paying for latency at scale, not for flexibility |
| "Append events, read a range for one key ordered by time" | Wide-column (Cassandra) or a log (Kafka) or a time-partitioned relational table | Write-optimized, range-per-partition reads |
| "Find documents matching arbitrary text, ranked by relevance, with facets" | Search index | Inverted index and scoring cannot be emulated by `LIKE` |
| "Aggregate a billion rows over arbitrary dimensions for a dashboard" | Columnar warehouse | Column pruning and vectorized scans; an OLTP row store cannot |
| "Traverse relationships of unknown depth" | Graph, or recursive CTE if depth is small and bounded | Index-free adjacency matters only when traversals are deep and frequent |
| "Nearest neighbors in embedding space" | Vector index (pgvector or a dedicated store, Q217-218) | ANN structures, not B-trees |

The discipline is to write the access patterns down *first*, as sentences with a frequency and a latency target attached, and to choose per pattern. Most real systems need two or three stores, not one and not seven (Q57).

### Q50. One sentence per family

- **Relational** - the default; choose it when correctness across multiple entities matters and query patterns will change.
- **Document** - choose it when the aggregate is the unit of read and write and there are no cross-document invariants.
- **Wide-column** - choose it when you have very high write volume with known partition-plus-range access and can design one table per query.
- **Key-value** - choose it when access is exclusively by a single known key and you need predictable latency at extreme scale.
- **Graph** - choose it when variable-depth traversal *is* the query, not a join.
- **Time-series** - choose it when data is append-only, keyed by time and tags, and read as ranges and aggregates with a downsampling policy.
- **Object store** - choose it for anything large, immutable and streamed; it is the cheapest durable byte in the industry.
- **Search index** - choose it when relevance ranking, tokenization or faceting is the requirement; never as a system of record.

The last clause is the one to volunteer: search indexes, caches and warehouses are **derived** stores. Every one of them needs a documented rebuild path from the system of record (Q197).

### Q51. "The data is graph-shaped" `[T]`

Almost all data is graph-shaped; that is not the deciding question. The deciding question is whether your *queries* are variable-depth traversals.

It is wrong when: traversals are depth 1-3 and known in advance (that is a join, and a relational database with the right indexes will beat a graph database on it); the working set fits in memory anyway; the volume is modest; or the real need is one recommendation feature, in which case a precomputed adjacency table refreshed nightly serves it at a fraction of the operational cost.

What a relational recursive query costs instead: PostgreSQL's `WITH RECURSIVE` does an iterative expansion, one index lookup per edge per level, with the intermediate result set materialized. For a bounded traversal over an indexed edge table it is fast - single-digit milliseconds for hundreds of edges. It degrades badly when the frontier explodes (a hub node with a million edges at level 2), when depth is unbounded, or when you need shortest-path or centrality semantics, because you are then writing a graph algorithm in SQL.

So my rule: bounded depth and a hot edge table → relational. Unbounded traversal, path semantics, or traversal as the core product feature → a graph store, accepting a second operational surface. And name the third option: keep the system of record relational and project the graph into a specialized store for the traversal use case.

### Q52. B-tree versus LSM from a design standpoint

| Property | B-tree (PostgreSQL, InnoDB) | LSM (RocksDB, Cassandra, ScyllaDB) |
| --- | --- | --- |
| Write path | Update in place; random IO; WAL for durability | Append to memtable + WAL, flush sorted files; sequential IO |
| Write amplification | Lower per write, but random | Higher total (compaction rewrites data repeatedly), but sequential |
| Read path | One tree walk; predictable, ~O(log n) | May touch several sorted files; bloom filters to skip; less predictable |
| Space | Fragmentation and bloat under churn | Temporary duplication until compaction; needs free space headroom |
| Latency profile | Stable | Good median, worse tail during compaction and flush |
| Delete | In-place mark, then vacuum | Tombstone, then compaction - deletes are writes (`../06-database/answers.md` Q203) |

What it means for a design: if the workload is write-heavy with a known read shape, LSM lets you buy write throughput that a B-tree cannot reach on the same hardware, at the cost of a **compaction budget** you must plan for - CPU, IO and free disk, and a p99 that moves when compaction runs. If reads are diverse and latency must be predictable, a B-tree store is the safer default. The design artifact I would produce either way: the compaction (or vacuum) headroom as an explicit line in the capacity plan, because it is the most common omission.

### Q53. Hot mutable part, large immutable part

Split them.

The **hot mutable part** - status, counters, current version pointer, permissions, a few indexed attributes - lives in the transactional store as a narrow row. Narrow rows mean more rows per page, a smaller working set, cheaper updates and, in PostgreSQL, a real chance of HOT updates that do not touch indexes.

The **large immutable part** - the document body, the rendered artifact, the media, the historical revisions - lives in object storage, addressed by a content hash or a version id, with the pointer in the row.

The mechanism that makes this safe: the immutable part is written **first** (it is content-addressed, so a duplicate write is free and a failed write leaves an orphan, not a corruption), then the row is updated to point at it. The orphan is reaped by a background sweep of unreferenced keys older than a grace period. Doing it in the other order gives you a row pointing at nothing, which is a user-visible error.

The trade-off: reads now need two fetches, and there is no transaction spanning them. That is acceptable because the second fetch is usually served by a CDN and the pointer swap is atomic - the user sees version N or version N+1, never a mixture. What you lose is the ability to query inside the immutable part, which is why anything searchable must be extracted into the row or an index at write time (Q54).

### Q54. What goes in the database, what goes in S3

In the database: identity, ownership, permissions, state, timestamps, the storage key, size, content type, checksum, and any attribute you need to filter or sort by. In object storage: the bytes.

Keeping them consistent:

1. **Write order:** bytes first, then metadata. Content-addressed keys (`sha256/ab/cd/<hash>`) make the byte write idempotent.
2. **Deletion order:** metadata first (so the object becomes unreachable immediately), then a **deferred, tombstoned** object delete via a reaper job after a grace period. Deleting bytes first creates 404s for live rows; deleting synchronously makes an undo impossible.
3. **Orphan reconciliation:** a periodic job comparing an inventory of the bucket against the metadata table, in both directions. Objects with no row older than the grace period are deleted; rows with no object are alarmed, because that is data loss and must be loud.
4. **Immutability and versioning:** bucket versioning plus object lock for anything with a compliance requirement, so a bug cannot destroy history.
5. **Lifecycle:** transition rules to infrequent-access and archive tiers driven by the same retention policy the metadata declares (Q62).

The single sentence for an interview: **object storage holds bytes, the database holds truth about the bytes, and there is a reconciler because there is no transaction between them.**

### Q55. 5 MB image in the database versus a URL `[T]`

**In the database.** Every backup, every replica, every restore and every dump now carries the image. The 200 GB database becomes 8 TB, so restore time (your RTO) grows by 40x, replication bandwidth grows, and the buffer cache is polluted by bytes nobody queries. In PostgreSQL large values go to TOAST and are chunked, so it *works*, but you are paying database-grade storage and IOPS prices for object-grade data, and you have coupled your recovery time to your media volume. Serving is also worse: bytes flow through your application and connection pool rather than from a CDN.

**A URL in the database.** The failure modes: the object can be deleted, moved or expire while the row still points at it (a dangling reference with no foreign key to protect you); an upload can succeed with no row or a row with no upload (Q54); the URL may embed a bucket, region or CDN hostname that becomes wrong after a migration; and a presigned URL persisted in the row expires and is useless.

The one people forget: **the URL is an access-control decision written into your data**. A public URL is permanent, guessable-if-sequential, and impossible to revoke once shared or cached. The correct design stores an opaque **storage key**, not a URL, and mints a short-lived presigned URL per request after an authorization check - so access control is evaluated every time and the location can change without a data migration.

### Q56. Presigned uploads, end to end

```
1. Client → API:      POST /uploads {filename, size, content_type}
2. API:               authorize; validate size/type; create row status=PENDING;
                      return presigned PUT URL (+ constraints), upload_id, expiry
3. Client → S3:       PUT bytes directly (or multipart for large files)
4. Client → API:      POST /uploads/{id}/complete {etag}
5. API:               HEAD object; verify size, type, checksum; status=READY;
                      enqueue post-processing (scan, thumbnail, index)
```

What goes wrong at each step, and the control:

- **Step 2** - an unconstrained presigned URL is an open upload endpoint. Bind `Content-Length` range, `Content-Type` and a key prefix into the policy, keep the expiry short (minutes), and rate-limit issuance per user.
- **Step 3** - the client can lie about content type, so the server must verify by sniffing bytes, not by trusting the header. Never serve user content from your primary domain; use a separate origin to contain XSS and set `Content-Disposition`.
- **Step 4 missing** - this is the common case: the upload succeeds and `complete` never arrives (app killed, network dropped). The row sits `PENDING` forever.
- **Step 5** - post-processing must be idempotent, because `complete` will be retried.

**Uploads that never complete** get two mechanisms: an **S3 event notification** on object creation, which lets the server complete the record without the client (making step 4 an optimization rather than a requirement), and a **sweeper** that expires `PENDING` rows past their deadline plus a bucket lifecycle rule aborting incomplete multipart uploads after a day - otherwise you pay storage for parts that are invisible in the console.

### Q57. How many datastores is too many

The cost of each additional store, which is what the question is really about: schema and migration tooling, backup and restore that has been *tested*, monitoring and alerting, capacity planning, version upgrades, security review and patching, an access-control model, a client library and its failure semantics, on-call expertise at 3 a.m., and - the big one - a synchronization path with a drift-detection story.

My rule of thumb for a single product team: **three stores is normal** (relational, cache, object store), **five is the practical ceiling** (add search and a log/stream), and beyond that each one needs a named owner and a written justification tied to an access pattern that the existing five demonstrably cannot serve.

"Too many" is better defined by a test than a number: if nobody on the team can answer "what is the restore procedure and when was it last exercised" for a store, you have one too many. The second test: if two stores hold the same data with no defined system of record, you do not have polyglot persistence, you have a consistency bug with a roadmap.

*Hook: a datastore you removed, and what it saved operationally.*

### Q58. One write path, two read shapes

**One store with a projection inside it.** The write goes to normalized tables; a materialized view, a summary table maintained by trigger, or a periodically refreshed table serves the second shape. Advantages: one transaction, one backup, one restore, no cross-store consistency problem, and the projection can be rebuilt with a single statement. Limits: the projection competes for the same IO and CPU as the write path, refresh is either transactional-and-expensive or asynchronous-and-stale, and the second shape cannot use a fundamentally different engine (no relevance ranking, no columnar scans).

**Two stores with a sync.** The write goes to the system of record; CDC or an outbox feeds a purpose-built second store. Advantages: each store is optimal, the read side scales independently, and the read side can be rebuilt from the log. Costs: eventual consistency with a lag you must bound and expose, a second operational surface (Q57), and a *permanent* reconciliation obligation - drift is not hypothetical, it is a quarterly occurrence.

My decision rule: stay in one store until the second read shape needs a different *engine class* (search, columnar, vector) or a different *scaling axis*. Then move, and when you do, make the sync a log-based projection with a documented full-rebuild path, not a dual write (`../03-microservices/answers.md` Q79). Dual writes are the version of this that always ends in drift.

### Q59. Time-series data

A general-purpose store struggles because the workload violates its assumptions: writes are a relentless append at high rate (B-tree index maintenance on every insert), the data is enormous but only recently written data is hot, queries are almost always a range scan plus an aggregate over one series, deletion is by *age* in bulk rather than by row, and the value columns compress extraordinarily well if stored columnar - an opportunity a row store cannot take.

The four properties a time-series design needs:

1. **Time partitioning** - so writes land in the newest partition (hot, cached, small index) and expiry is a partition drop rather than a `DELETE` of a billion rows.
2. **Series identity as a first-class key** - `(series_id, timestamp)` ordering, where `series_id` is a hash of the metric name plus its tag set, so a range read for one series is sequential. Tag cardinality is the real scaling limit (Q207).
3. **Columnar or delta-of-delta compression** - timestamps and slowly-changing float values compress 10-20x with specialized encodings. This is the difference between affordable and not.
4. **Downsampling and retention policy** - raw at high resolution for days, 1-minute rollups for weeks, hourly for months, with automatic transitions. Nobody queries per-second data from 18 months ago, but everybody asks for the trend.

PostgreSQL with declarative partitioning plus TimescaleDB-style compression covers a lot of ground before a dedicated store is justified.

### Q60. Append-only log as the system of record `[T]`

What it buys: a complete audit trail for free; the ability to rebuild any projection from scratch, which makes read models disposable and schema changes on the read side trivial; temporal queries ("what did this look like on Tuesday"); natural integration, since every consumer reads the same log; and no lost information from an in-place update.

What it hands you in year two:

1. **Schema evolution of old events.** You have events in five formats written by code that no longer exists, and every consumer must read all five forever (Q41). You need versioning and an upcasting layer, and you need it before you have the problem.
2. **Deletion is structurally opposed to your design.** GDPR erasure against an immutable log requires crypto-shredding (encrypt per subject, destroy the key) or rewriting history, and both need to be designed in advance (`../06-database/answers.md` Q275).
3. **Replay cost and duration.** Rebuilding a projection from 4 billion events takes hours or days, and during a real incident that is your recovery time. This forces snapshots, and snapshots reintroduce the versioning problem at the snapshot layer.
4. And a fourth that is worth naming: **queries against current state are not possible without a projection**, so you always have at least two representations and therefore a lag and a reconciliation.

My position: event sourcing is right for a bounded, high-value subdomain where history *is* the product - a ledger, an audit trail, a workflow with legal significance. Applying it to a whole system is a decision most teams regret, and the compromise I usually recommend is a mutable current-state store plus a durable event log for integration and audit (Q61).

### Q61. Where the immutable/mutable boundary goes

I place the boundary at the **aggregate that owns a legally or financially significant history**, and nowhere else.

Concretely, in an orders system: the ledger and the order state transitions are an append-only event stream (immutable, retained for years, the source of truth for "what happened"). Current order state, customer profile, catalogue and cart are mutable rows (the source of truth for "what is"). The events are emitted transactionally with the state change via an outbox, so the two cannot diverge.

What I materialize: current state for the transactional path; a per-customer order history read model; a daily balance snapshot so the ledger does not need full replay to answer "what is the balance"; and an analytics projection in the warehouse. Each materialization declares its staleness bound and has a rebuild command.

The rule I state out loud: **materialize a projection for every read pattern that cannot afford to fold the log, and snapshot every aggregate whose event count grows without bound.** The failure mode I am designing against is an aggregate with 10 million events whose reconstruction takes 40 seconds on the request path.

### Q62. Retention tiering

| Tier | Where | Access | Typical age | Cost shape |
| --- | --- | --- | --- | --- |
| Hot | Primary OLTP store, cached | Milliseconds, indexed, ad-hoc | 0-90 days | Most expensive per GB; keep it small |
| Warm | Time-partitioned tables, compressed; or a cheaper cluster | Sub-second, queryable, reduced indexes | 90 days - 1 year | Compression 5-20x helps most here |
| Cold | Object storage as Parquet, queried by an external engine | Seconds to minutes, analytical only | 1-7 years | ~$0.02/GB; a rounding error if partitioned well |
| Archive | Glacier-class storage | Hours to restore | Compliance horizon | Cheapest, and effectively write-only |
| Deleted | Gone, including from backups | - | After retention | The step everyone skips |

Transitions are triggered by **age on a declared partition key**, executed by an automated job, not by a human. Hot to warm is a partition attach plus compression; warm to cold is an export to Parquet then a partition drop; cold to archive is a lifecycle rule; archive to deleted is a lifecycle expiry.

Two things to say that show operational experience. First, retention must be **stated per data class in the design**, because "keep everything" is a decision with a compounding bill and a legal exposure. Second, backups have their own retention, so "deleted" is not achieved until the backups holding it have expired - which is why erasure requests need either a documented backup-expiry window or crypto-shredding.

### Q63. Designing for a monthly-changing schema

What survives frequent change:

- **A narrow, stable core** of columns that are genuinely universal - id, tenant, owner, timestamps, status, version - properly typed and constrained. These never change.
- **A JSONB (or equivalent) attribute bag** for the volatile part, with expression indexes on the specific keys that need filtering. New attributes need no migration; validation moves to the application, or to a `CHECK` with a JSON Schema function if you want the database to hold the line.
- **Additive-only discipline**: new nullable column or new key, never rename, never retype in place. Renames become expand-contract with a shadow column (`../06-database/answers.md` Q247-248).
- **Versioned rows** where the shape itself is domain-meaningful - store a `schema_version` and upcast on read.
- **Migrations as small, forward-only, independently deployable steps**, with the deployment rule that code must tolerate both the old and new shape (`../06-database/answers.md` Q243).

What to avoid: wide sparse tables that grow a column per feature (Q19 in the database pack's terms - 180 columns mostly null); EAV, which defeats the optimizer and turns every query into a self-join pyramid; a single-table inheritance design covering divergent subtypes; and any structure requiring a table rewrite to extend.

The judgement call to voice: a schema changing monthly usually means the domain is not understood yet, and the correct architectural response is to keep that area *flexible and cheap to change* rather than to model it precisely and pay for a migration every sprint.

### Q64. "Just use DynamoDB, it scales" `[T]`

The two questions:

1. **Do you know all your access patterns now, and are they stable?** DynamoDB requires you to design keys and indexes for the queries you will run; it does not support ad-hoc queries, and adding an unanticipated pattern means a new GSI (with its own capacity and back-pressure failure mode) or a full table rewrite. If the product is still discovering its queries, you are trading a schema migration for a data migration, which is worse.
2. **Are your invariants within a single item or a single partition?** Multi-item transactions exist but are limited (100 items, 4 MB) and cost double; there are no joins, no foreign keys, no `CHECK` constraints, and no cross-item consistency without application code. If the domain has real cross-entity invariants, you will implement them yourself and get them wrong somewhere.

If both answers are favorable, DynamoDB is genuinely excellent: single-digit-millisecond latency at essentially unbounded scale, no capacity planning, no failover to operate. If either is not, "it scales" is answering a question you do not have while creating one you cannot escape - and the honest comparison is against a partitioned PostgreSQL, which handles more load than most people assume (`../06-database/answers.md` Q193, Q212).

I would also add the cost note: on-demand pricing is superb for spiky and small, and expensive for sustained high-throughput uniform load, where provisioned capacity with autoscaling or a self-managed store wins.

### Q65. Transactional core, analytics, and full-text search `[A]`

**Shape.** One system of record, two derived stores, one log connecting them.

```
        writes
          │
   ┌──────▼───────┐   CDC / outbox    ┌──────────────┐
   │ PostgreSQL   │──────────────────▶│  Kafka log   │
   │ (truth)      │                   └──┬────────┬──┘
   └──────┬───────┘                      │        │
          │ replicas                     ▼        ▼
      reads (OLTP)              OpenSearch    Warehouse
                                (relevance)   (Parquet/columnar)
```

**Decisions and why.**

- **PostgreSQL is the single system of record.** Every invariant that must always hold is a constraint here. Time-partition the large tables from day one. Read replicas serve read-heavy OLTP traffic, with read-your-writes handled by routing the writer's own reads to the primary (Q119).
- **Search goes to a dedicated index**, fed from the log, because relevance ranking, analyzers and faceting are not emulable in SQL at quality (`../06-database/answers.md` Q214-217). It is explicitly *derived*: never written to directly, always rebuildable from the log, with a documented reindex procedure and a drift check comparing counts and a sampled checksum (Q197).
- **Analytics goes to a columnar store** fed by the same log, plus periodic full snapshots for correctness. Reporting never touches the OLTP primary, and never touches an OLTP replica either, because long analytical queries on a replica cause cancellations (`../06-database/answers.md` Q224).
- **The log is the integration point**, not point-to-point sync. One CDC pipeline, many consumers, independent offsets, replayable. This is what makes adding a fourth consumer a day of work rather than a project.

**Trade-offs I would state.** Two derived stores means two lags to bound and expose (search freshness target: seconds; analytics: minutes), a reconciliation job for each, and three operational surfaces instead of one. In exchange, each read pattern runs on an engine designed for it and the write path stays simple and correct. If the search requirement were modest - prefix and keyword matching over a few million rows - I would use PostgreSQL full-text search and delete a whole store from this diagram, and I would say so, because the cheapest architecture is the one with fewer boxes.

**Consistency contract, written down:** the transactional core is linearizable; search and analytics are eventually consistent with stated bounds; and no user-facing invariant is ever enforced by reading a derived store. That last sentence prevents the most common failure of this architecture - checking uniqueness against the search index.

*Hook: a system where you kept the derived stores honest with a drift check, and what it caught.*

---

## 5. Caching as an architectural tier

### Q66. Every cache layer from keystroke to row

| Layer | Good at | Typical hit latency |
| --- | --- | --- |
| Browser memory / HTTP cache | Repeat views by one user; zero network | 0 ms |
| Service worker / app local store | Offline and instant navigation | 0-1 ms |
| DNS resolver cache | Avoiding a lookup; also your failover enemy (Q88) | 0 ms |
| CDN edge | Static assets and cacheable public responses, near the user | 5-30 ms |
| Reverse proxy / gateway cache | Shared responses for many users; collapsing duplicate requests | 1-5 ms |
| Service in-process cache | Tiny, extremely hot, tolerant of staleness - config, feature flags, reference data | ~100 ns |
| Distributed cache (Redis/Memcached) | Shared hot objects, session state, computed results, rate-limit counters | 0.5-2 ms |
| Materialized read model / projection | Expensive joins and aggregates, precomputed | database latency |
| Database buffer pool | Pages the engine chose to keep; you do not control it directly | ~100 ns - 1 ms |
| Storage layer cache | Block-level; invisible to you | sub-ms |

The design point: each layer has a different **invalidation reach**. You can purge a CDN and a Redis key; you cannot purge a browser or a DNS resolver, which is why anything you may need to change quickly must not be cached where you cannot reach it. The corollary is that cache-control headers are an architectural decision, not a detail.

### Q67. The five caching strategies

| Strategy | Read | Write | Consistency | Failure behavior |
| --- | --- | --- | --- | --- |
| **Cache-aside** | Miss → load from store → populate | App writes store, then invalidates or updates cache | Eventual; races on concurrent write/read (Q72) | Cache down → all reads hit the store (Q76) |
| **Read-through** | Cache library loads on miss | Same as cache-aside | Same as cache-aside, but centralized | Loader becomes a dependency; stampede control is built in |
| **Write-through** | Always fresh for cached keys | Write goes to cache and store synchronously | Strong between cache and store | Write latency = both; cache down blocks writes unless bypassed |
| **Write-behind** | Fresh | Write to cache, flush to store asynchronously | Store lags cache; **data loss window** | Cache loss = committed data loss. Only acceptable for tolerable data |
| **Refresh-ahead** | Fresh, no miss penalty for hot keys | Cache proactively reloads before TTL expiry | Bounded staleness, no stampede | Wasted work on keys that were not going to be read |

My default is **cache-aside with a TTL and a jittered expiry**, because it fails safely (an unavailable cache degrades to slower, not wrong) and because it does not put the cache in the write path. I use write-through only for a small set of keys where a miss is unacceptable, refresh-ahead for a handful of expensive-and-always-hot keys, and write-behind essentially never for data I cannot regenerate.

### Q68. Where to put the cache

| Location | Criterion |
| --- | --- |
| Client | The data is per-user, changes rarely, and a stale read for its TTL is harmless. You accept that you cannot invalidate it |
| CDN | The response is identical for many users (or keyable by a small number of variants) and is large or geographically distant |
| Gateway / reverse proxy | The response is shared, and you want one place to collapse duplicate concurrent requests |
| Service-local (in-process) | The object is small, read at extremely high frequency, and tolerant of per-instance divergence for seconds - config, flags, reference data, compiled artifacts |
| Shared remote tier | The object is expensive to compute, shared across instances, and must be consistent across them - or it is state (sessions, rate-limit counters, locks) |

The decision reduces to two questions: **how many consumers share this value**, and **can I tolerate different instances disagreeing about it**. Per-user and shareable-widely push toward the edges; shared-and-must-agree pushes toward a remote tier.

The layering I use in practice: CDN for assets and public responses, a shared Redis tier for computed objects and state, and a small local cache for the handful of things read thousands of times a second - with the local cache's TTL kept to seconds precisely because it cannot be invalidated (Q69).

### Q69. Local in-process cache across 40 instances `[T]`

What goes wrong:

1. **Divergence.** Forty independent copies with independent expiry means forty possible answers. A user whose requests land on different instances sees values flap - a read-your-writes violation and a support nightmare (Q81).
2. **Invalidation is broadcast or nothing.** You need a pub/sub fan-out to all instances, and it is best-effort: an instance that missed the message is silently stale until its TTL, and a new instance starting mid-flight has no history.
3. **Memory multiplied.** 40 x 2 GB is 80 GB of RAM caching the same objects, versus 8 GB in a shared tier - and each instance's hit ratio is lower because each sees only 1/40th of the traffic.
4. **Cold start.** Every deploy and every scale-out event empties 1/40th of your cache and sends that traffic to the origin. During a rolling deploy, that is a sustained load increase exactly when you are least stable.

When it is still right: the value is effectively immutable or tolerant of seconds of staleness (feature flags, configuration, currency reference data, a compiled schema, a JWKS key set); the read frequency is so high that a 1 ms network hop is unaffordable (hundreds of thousands of reads/second); or the cache is a hedge against the shared tier being down. The safe pattern is a **two-tier cache**: a short-TTL local cache in front of the shared tier, which caps divergence at the local TTL while cutting remote traffic by an order of magnitude.

### Q70. Cache key design

What belongs in the key: the entity type, the identity, and **every input that changes the output** - tenant, locale, currency, feature-flag variant, API version, permission scope, and the serialization format version. A key that omits an input is a correctness bug that appears as "user A saw user B's data" (Q80).

```
v3:order:summary:{tenant}:{order_id}:{locale}       # version prefix in the key
```

**Versioning the key** rather than migrating values: when the value's shape changes, bump the prefix. The old keys age out by TTL and you never write a cache migration or serve a value your new code cannot parse. This is a small habit that removes an entire class of deployment incident.

**Invalidating a family** of keys - all of a tenant's summaries, say - cannot be done by key enumeration (`KEYS` is a production hazard, and `SCAN` is slow at scale). The technique is **indirection**: store a generation counter per family, include it in the key, and bump the counter to invalidate everything under it in one write.

```
gen = GET tenant:{t}:gen            # e.g. 41
key = v3:order:summary:{t}:{gen}:{order_id}
INCR tenant:{t}:gen                 # invalidates the whole family atomically
```

The orphaned values expire by TTL. The costs are one extra round trip per read (mitigated by caching the generation locally for a second) and dead memory until expiry - both cheap compared with the alternative.

### Q71. Choosing a TTL

A TTL is a promise about one thing only: **the maximum age of the data you may serve** - assuming no explicit invalidation happens. It is not a consistency mechanism; it is a bound on inconsistency.

How I choose it:

1. Start from the product tolerance: how stale may this be before a user is misled or a decision is wrong? For a product price, seconds. For a catalogue description, minutes. For a currency rate, whatever the business contract says. For an aggregate on a dashboard, whatever the refresh interval already implies.
2. Check the load arithmetic: origin QPS ≈ `unique_hot_keys / TTL` plus genuine misses. If 100,000 hot keys have a 60 s TTL, that is ~1,700 refreshes/second at the origin. If that is unaffordable, the TTL is too short *or* you need refresh-ahead (Q67).
3. Add **jitter** - a TTL of `60s ± 20%` per key - so keys written together do not expire together (Q73).
4. Layer two TTLs where it matters: a *soft* TTL after which you serve the stale value and refresh in the background, and a *hard* TTL after which you refuse to serve it. This gives you latency and a bounded worst case.

The mistake I would call out: choosing a long TTL to reduce origin load, then adding explicit invalidation to fix the staleness, and now depending on invalidation being reliable (Q72). Better to keep the TTL as the real guarantee and treat invalidation as an optimization.

### Q72. "We will invalidate on write" `[T]`

The three races, all real:

1. **Read-populate versus write-invalidate.** Reader misses, loads the old value from the store, and is descheduled. Writer commits and invalidates. Reader then populates the cache with the *pre-write* value, which now lives for the full TTL. Nothing detects it.
2. **Two writers.** Writer A commits v2 and invalidates; writer B commits v3 and invalidates; a reader interleaved between them may populate v2 after v3 is committed. Without a version in the value you cannot tell which is newer, so last-writer-to-the-cache wins, which is not last-writer-to-the-store.
3. **Non-atomicity of store-and-cache.** There is no transaction spanning them. Invalidate-before-commit exposes the old value to readers during the window; invalidate-after-commit leaves the old value cached if the process dies in between. Either way, a failed invalidation is silent.

Mitigations, in the order I apply them:

- **Delete, do not update, on write.** A delete is idempotent and cannot install a stale value.
- **Store a version or timestamp inside the cached value** and refuse to overwrite a newer one (`SET` with a compare, or a Lua script). This kills race 2.
- **Bound the damage with a modest TTL**, so every race self-heals. This is the reason TTL remains the real guarantee.
- **Make invalidation reliable by driving it from the log** - CDC or the outbox emits the change, and a consumer invalidates. Now invalidation is at-least-once and retried, rather than a best-effort call in a request that may fail.
- For the highest-value keys, **delayed double delete** (invalidate, then invalidate again after a short delay) closes race 1 cheaply, which is the standard trick when the log-driven approach is too much machinery.

### Q73. Stampede, thundering herd, dog-piling

All three are the same shape: many concurrent requests for a value that is not in the cache, all hitting the origin at once. The variants are expiry of one hot key (dog-pile), synchronized expiry of many keys, and a cold cache after a restart (Q76).

The three mitigations:

1. **Request coalescing / single-flight.** Per key, exactly one caller computes the value and the others wait on that result. In-process this is a `ConcurrentHashMap` of futures; across instances it is a short-lived lock in Redis (`SET key NX EX 5`) with the losers either waiting briefly or serving stale.
2. **Serve-stale-while-revalidating.** Keep a soft TTL and a hard TTL (Q71). On soft expiry, return the stale value immediately and trigger one background refresh. Users never wait for a recompute, and the origin sees one request per key per interval.
3. **Jittered TTLs and staggered warming**, so nothing expires in lockstep and a warm-up does not arrive as a spike.

The one I apply by default is **single-flight plus jitter**, because it needs no extra state and fixes the common case. Serve-stale is what I add for the expensive keys, and it is the one that saves you in an incident, because it means a slow origin degrades freshness rather than availability. At the CDN layer the same three ideas exist as request collapsing, `stale-while-revalidate` and `stale-if-error`, and I would set all three.

### Q74. Negative caching

Not caching a miss means every request for a non-existent key reaches the origin. Under attack - or merely under a buggy client enumerating ids - your cache provides zero protection and the database absorbs the full request rate. This is the **cache penetration** pattern, and it is the standard way a cache-fronted system falls over: the cache is at 99 percent hit ratio for real traffic and 0 percent for the attack.

The controls:

1. **Cache the negative result** with a short TTL (10-60 s, shorter than positives) and a distinguishable sentinel value so you never confuse "known absent" with "not cached".
2. **A Bloom filter of existing keys** in front of the lookup, when the key space is enumerable and large. A negative from the filter is definitive and costs no round trip; a positive falls through to the normal path. This is the standard answer for something like a URL shortener with a guessable key space.
3. **Validate the key shape before looking anything up.** A key that cannot exist (wrong length, failing checksum, wrong prefix) is rejected at the edge for free.
4. **Rate-limit by client on miss rate**, not just request rate. A client with a 95 percent miss ratio is either broken or hostile, and either way should be throttled.

The correctness caveat: a negative cache creates a window where a newly created object appears absent. Keep the negative TTL short, and invalidate the negative entry on create - which is one of the few places an explicit invalidation is genuinely required.

### Q75. Hit ratio

A "good" hit ratio depends entirely on what the miss costs. For a CDN serving assets, 95-99 percent. For an object cache in front of a database, 80-95 percent. For a semantic cache in front of an LLM, 20-40 percent is excellent.

The relationship to latency you promised is arithmetic, and it is the number to say out loud:

```
effective = hit_ratio x hit_latency + (1 - hit_ratio) x miss_latency
90% hit:  0.9 x 1 ms + 0.1 x 50 ms = 5.9 ms
99% hit:  0.99 x 1 ms + 0.01 x 50 ms = 1.5 ms
```

Two implications. First, the last percent of hit ratio matters more than the first ninety, because the miss path dominates the mean. Second - and this is the tail argument - the *p99* of a cached endpoint is essentially the miss path's latency, so caching improves the average dramatically and the p99 hardly at all. If your SLO is a percentile, a cache alone does not meet it; you also need the miss path to be fast.

**Why a high hit ratio can be a warning sign:** it may mean you are caching things that never change and should have been in the CDN or the binary; it may mean the TTL is far longer than the product tolerance and you are serving stale data nobody has complained about *yet*; it may mean the origin has quietly become incapable of serving the traffic the cache is absorbing, so a cache failure is now an outage rather than a slowdown (Q76). The last one is the dangerous case: a 99.9 percent hit ratio can hide a 1000x capacity gap.

### Q76. The cache tier fails completely `[T]`

Second by second, with a 95 percent hit ratio and 20,000 QPS:

- **0-1 s:** all 20,000 QPS reach the database instead of 1,000. That is 20x its normal load. Every request also takes longer because the database is saturated, so by Little's Law in-flight requests multiply.
- **1-5 s:** connection pools exhaust. Requests queue in the application, then time out. Threads are all blocked, so even endpoints that do not touch the database start failing.
- **5-15 s:** clients retry, adding load. Health checks time out, so instances are pulled from the load balancer, concentrating traffic on the remainder (Q87). Autoscaling begins reacting but new instances have cold pools and add connection pressure.
- **15-30 s:** the database is at 100 percent CPU or IO with a queue of doomed work. Even if the cache returns now, the stampede to refill it (Q73) keeps the database saturated - a metastable failure that outlives its cause (Q26).

Designing so it is survivable:

1. **Bound the load the origin can ever receive.** A concurrency limiter in front of the database (a semaphore sized from Little's Law) that rejects rather than queues. 1,000 served and 19,000 shed beats 0 served.
2. **Load shedding with priority** (Q94): serve authenticated interactive traffic, shed crawlers, prefetches and background jobs first.
3. **Single-flight and negative caching** so the refill is one request per key, not thousands (Q73, Q74).
4. **A local in-process cache as a second tier** (Q69) - even a 30-second local cache turns a total cache failure into a partial one.
5. **Serve stale on error** (`stale-if-error`) at the CDN and gateway, so a cache miss with a failing origin returns yesterday's answer rather than a 500.
6. **Circuit breaker on the origin**, so the application stops trying and fails fast, giving the database room to recover.
7. **Capacity honesty:** know your uncached capacity and monitor the ratio. If the origin can serve 5 percent of peak, that is a documented risk, not an accident.
8. **Cache redundancy** - a clustered cache with replicas so total failure requires more than one event.

### Q77. Sizing a cache

Start from the **working set**, not the dataset: how many distinct objects are accessed in a window comparable to your TTL. Measure it by sampling keys from production traffic, not by dividing the table size. Then add per-entry overhead (Redis: ~50-100 B per key for the hash entry, key string and object header; plus allocator fragmentation of 10-30 percent) and headroom so you are not evicting constantly.

The eviction policy encodes your assumption: `allkeys-lru` for a general object cache, `allkeys-lfu` when popularity is stable and you want to resist a scan polluting the cache, `volatile-*` variants when the instance holds both cache and state, and `noeviction` **only** when it holds state you cannot lose - in which case running out of memory is an outage, so it needs its own alert well before the ceiling.

**The marginal value of the last gigabyte** follows the access distribution and is steeply diminishing (Q21): under a Zipf-like distribution, going from 80 to 90 percent hit ratio may cost 3-4x the memory, and 90 to 95 percent another 3x. So the sizing method is to plot hit ratio against memory from real data (or model it), find the knee, and stop there. Beyond the knee, money is better spent making the miss path faster or adding a read replica - which also improves the p99 that the cache never touched (Q75).

### Q78. CDN in a design

**What I cache at the edge:** static assets with content-hashed filenames (immutable, cache forever); images and media, with the CDN doing format and size negotiation; public API responses that are identical for many users - catalogue pages, configuration, public profiles; and, with care, personalized fragments via edge compute (Q79). I also terminate TLS at the edge and let it absorb DDoS volume, which is half the value even at a zero hit ratio.

**Headers:**

```
# hashed asset
Cache-Control: public, max-age=31536000, immutable

# shared API response
Cache-Control: public, max-age=30, s-maxage=300, stale-while-revalidate=60, stale-if-error=86400
Vary: Accept-Encoding, Accept-Language
ETag: "v3-8f2a..."

# per-user
Cache-Control: private, no-store
```

The distinction that matters: `max-age` governs the browser (which you cannot purge), `s-maxage` governs the CDN (which you can). So keep browser TTLs short and shared TTLs long - you retain control. `Vary` must list every input that changes the response, and no more, because each value multiplies your cache entries; `Vary: Cookie` or `Vary: User-Agent` effectively disables caching.

**Global purge:** tag-based invalidation (surrogate keys) is what makes this operable - tag responses with the entity ids they depend on, then purge by tag when an entity changes, rather than enumerating URLs. Purges take seconds to propagate globally and are rate-limited by providers, so the design must not depend on purge for correctness; use versioned URLs for anything that must change instantly. Keep the purge path automated and driven from the same change events that invalidate Redis (Q72), so the two cannot disagree.

### Q79. Edge caching for personalized content

When every response differs, you cache the *parts* that do not.

1. **Split the response.** The page shell, layout, navigation, product data and images are shared and cacheable at the edge with a long TTL. The personalized parts - name, cart count, recommendations, pricing entitlements - are a small JSON payload fetched separately, or composed at the edge. This is the fundamental move: personalization is usually 5 percent of the bytes.
2. **Cache by cohort, not by user.** Most personalization has low real cardinality: locale, currency, device class, logged-in-or-not, membership tier, A/B bucket. Normalize the request into a cohort key at the edge and you get a cacheable variant space of tens rather than millions.
3. **Edge compute for assembly.** A worker at the edge fetches the cached shell, fetches or reads the per-user fragment (from an edge KV store or a cookie/JWT claim), and stitches them. The user gets one round trip to a nearby POP instead of one to your origin.
4. **Signed claims in the token.** Entitlements small enough to fit in a JWT can be read at the edge with no origin call at all, which is how authorization decisions become cacheable.
5. **ESI-style fragment caching** with per-fragment TTLs when the page is genuinely composite.

The trade-off to name: every cohort dimension multiplies the cache entries, so hit ratio falls as personalization deepens. And correctness is unforgiving here - a mis-keyed variant serves one user's data to another (Q80), so cohort keys must be derived from verified claims, never from a client-supplied header.

### Q80. Caching authenticated and permission-filtered data

The design that does not leak:

1. **Identity or scope is in the cache key, always** - and derived from the *verified* token, never from a header the client can set. `v3:doc:{doc_id}:scope:{permission_hash}` where the permission hash is a digest of the caller's effective roles and tenant.
2. **Separate the object from the decision.** Cache the document once, keyed by id and version; cache the authorization decision separately, keyed by `(subject, resource, action)` with a short TTL. The expensive object is shared across all users who may see it, and the cheap decision is per user. This is the pattern that gets you a high hit ratio without cross-user exposure (Q229).
3. **Never cache a filtered list under a non-user key.** "Documents I can see" is per-subject by definition. Cache the *unfiltered* candidate set (shared) and apply the filter per request, or cache the filtered result under a key including the subject and a permissions generation counter.
4. **Bump a generation counter on permission change** (Q70) so a revoked grant invalidates every decision and filtered list for that subject in one write. Without this, revocation waits for the TTL - which is the finding an auditor will raise.
5. **`Cache-Control: private, no-store` on anything personal** at the HTTP layer, and never `public` on a response that varied by identity. A shared proxy caching an authenticated response is the classic version of this bug.
6. **Fail closed.** If the permission lookup errors, do not serve from cache and do not assume the last decision. And make sure a cache miss cannot bypass the authorization check - the check must be outside the cache lookup, not inside the loader.

*Hook: a cache key that omitted a scope, and how it was caught.*

### Q81. Read-your-writes broke after adding a cache `[T]`

The mechanism: the write goes to the database and either invalidates the cache after commit or relies on TTL. The same user's immediate read arrives at a *different* instance, or a moment before the invalidation lands, and is served the pre-write value from the cache. The user sees their own change vanish. It is worse with a local cache (Q69) because 39 of 40 instances have not heard about the write, and worse again with a read replica behind the cache, because now there are two lags in series.

Two fixes:

1. **Write-through the cache for the writer's own key, inside the same code path that commits.** Update (or delete) the cache entry immediately after the transaction commits, and for the duration of a short window (a few seconds), route that user's reads past the cache. The window is tracked with a per-user marker - a `last_write_at` in the session or a small "recently wrote" key in Redis - which is the same mechanism used to pin reads to the primary (Q119).
2. **Version-aware reads.** The write returns a version or LSN to the client; the client sends it back on subsequent reads; the server serves from cache only if the cached value's version is greater than or equal to the one presented, otherwise it bypasses. This is more work but it is the general solution, and it composes with replicas as well as caches.

The cheap third option worth mentioning: for the writer's own view, render optimistically from the response body of the write rather than re-reading at all. It removes the problem instead of solving it, and it is what most good UIs do.

### Q82. A cache proposed to fix latency `[A]`

What I need to see before agreeing:

1. **Where the latency actually is.** A trace showing that the time is spent in the operation the cache would front. Half the time it is not - it is N+1 queries, a missing index, a serial fanout, or connection acquisition (`../06-database/answers.md` Q236).
2. **The read:write ratio and the reuse rate.** A cache is worthwhile only if the same value is read many times per write and per TTL. If every key is read once, the cache is pure overhead.
3. **The staleness the product tolerates**, stated by the product owner, not assumed by the engineer. This becomes the TTL (Q71).
4. **The invalidation plan and its failure mode**, including who invalidates on a change made by a different service or a manual script.
5. **The uncached capacity and the plan for cache failure** (Q76). If the answer is "the database cannot serve this traffic", the cache is now a critical dependency and needs its own availability design.
6. **The correctness analysis for identity and permissions** (Q80).

What would make me refuse: the underlying query is slow because of a fixable defect (fix that first - the cache would mask it and it will resurface at 3 a.m. after an eviction); the data is used to make a decision that must be correct now, such as a balance, a stock count at checkout, or an authorization outcome with a revocation requirement; nobody will own invalidation; or the cache is being proposed to hide a design where a single request fans out to fifteen services. In that last case the cache buys a quarter and costs a year.

The framing I use: **a cache is a bet that stale data is acceptable, paid for with a permanent correctness liability.** I am happy to take the bet when someone has priced it.

*Hook: a caching proposal you rejected in favor of fixing the underlying query, and the numbers.*

---

## 6. Load balancing, routing, gateways and traffic management

### Q83. L4 versus L7

**L4** operates on TCP/UDP. It sees IP addresses, ports and the connection, and nothing inside. It can do connection-level distribution, TLS passthrough, and very high throughput at very low latency because it can be little more than a NAT (or, with direct server return, not even in the response path). It cannot route by path, retry a request, or read a header.

**L7** terminates the connection and parses HTTP/gRPC. It sees method, path, headers, cookies and body, so it can do path and header routing, per-request load balancing (crucial for HTTP/2 and gRPC, where one connection carries many requests), retries, rate limiting, request/response transformation, compression, authentication, and per-request observability. It costs more CPU, adds a millisecond or two, and terminates TLS, which makes it a security boundary.

Where each sits:

```
Internet → [Anycast/GeoDNS] → L4 (NLB, DDoS absorption, TLS passthrough or termination)
        → L7 (ALB / Envoy / gateway: routing, auth, rate limit, retries)
        → service mesh sidecar (L7, per-request LB, mTLS, deadlines)
        → service
```

The point to volunteer: with HTTP/2 or gRPC, an L4 balancer distributes *connections*, so one long-lived connection pins all its requests to one backend and load becomes badly skewed. That is why internal gRPC traffic needs L7 balancing or client-side load balancing, and it is a mistake that appears in real production systems.

### Q84. Load balancing algorithms

| Algorithm | Behavior | Best when |
| --- | --- | --- |
| Round robin | Equal share per backend | Uniform request cost and uniform backends. Rarely true |
| Weighted round robin | Share proportional to a static weight | Heterogeneous instance sizes, canary traffic splits |
| Least connections | Send to the fewest in-flight | Variable request duration; the cheap fix for Q85 |
| Least request with power-of-two-choices (P2C) | Sample two backends, pick the less loaded | The modern default - near-optimal balance without the herd effect of global least-loaded |
| Peak EWMA | Weighted by a decaying average of observed latency | Heterogeneous backends and noisy neighbors; reacts to a slow node before connections pile up |
| Consistent hashing | Same key → same backend | Cache affinity, session affinity, sharded stateful backends |
| Maglev / ring hash | Consistent hashing with even distribution and minimal disruption | Large fleets where a membership change must not reshuffle everything |

Why P2C beats global least-loaded: with many balancers, all of them independently choose the *same* least-loaded backend and stampede it. Sampling two and picking the better gives you almost all the benefit with none of the herding, and it is O(1).

Why consistent hashing is a different tool: it is not about balance, it is about **affinity**. You use it when hitting the same backend has value (a warm local cache, an in-memory shard, a WebSocket connection) and you accept the imbalance that comes with it - hence virtual nodes (Q137).

### Q85. Round robin with unequal response times `[T]`

What breaks: round robin distributes *requests*, so a backend that is three times slower receives the same number of requests and accumulates three times the in-flight work. Its queue grows without bound, its latency climbs, and because it never stops receiving its share, it never recovers. One degraded instance in twenty therefore poisons the p99 of the whole service - and it is worse than a dead instance, because a dead one is removed by health checks and a slow one is not (Q159).

The fix is any algorithm that measures **outstanding work rather than requests**: least connections, or better, **least request with power-of-two-choices**, which converges on the same distribution without the stampede. Peak EWMA is stronger still when the cause is a persistently slow node rather than transient queueing, because it penalizes observed latency directly.

What I would add beyond the algorithm, because algorithm alone is not enough:

- **Outlier detection / passive health checking** (Envoy-style): eject a backend that exceeds a latency or error threshold relative to its peers, then admit it back gradually.
- **Concurrency limits per backend**, so no instance can accumulate an unbounded queue.
- **Request hedging** for read-only calls: after the p95 elapses, send a second request elsewhere and take the first answer. This makes one slow node invisible.

### Q86. Health checks

- **Liveness** - "is this process broken beyond recovery?" Failing it restarts the container. It must check almost nothing: that the event loop is turning. Anything else and you get restart loops during dependency outages.
- **Readiness** - "should this instance receive traffic right now?" Failing it removes the instance from the load balancer without killing it. This is where warm-up, connection-pool availability and graceful shutdown are expressed.
- **Startup** - a grace period so a slow-booting JVM is not killed by liveness before it has warmed up.
- **Shallow** check: process is up, event loop responsive, no local resource exhaustion. **Deep** check: verifies downstream dependencies - database, cache, a peer service.

The failure mode of a check that is too deep is in Q87. The rule I apply: **liveness is shallow, readiness is shallow-plus-local (own thread pool, own pool saturation), and dependency health is never a reason to remove yourself from the load balancer** - it is a reason to return a degraded response and fire an alert. The exception is a dependency without which the instance can do literally nothing *and* whose failure is instance-specific rather than global (a broken local connection pool, for example) - and even then, the check should be per-instance, not global.

Also: check intervals, thresholds and timeouts must be set so that a transient blip does not eject half the fleet, and so that a real failure is detected within the SLO. Two failures at a 5-second interval with a 2-second timeout is a reasonable default, and the timeout must be shorter than the interval.

### Q87. Deep health check causes a total outage `[T]`

The cascade: the health endpoint queries the database. The database has a brief problem - a failover, a lock storm, a saturated connection pool. Every instance's health check fails *simultaneously*, because they all depend on the same thing. The load balancer removes every instance from rotation. Now there are no healthy targets, so the load balancer returns 503 for everything - including all the endpoints that did not need the database at all. When the database recovers, all instances return at once with cold pools and a stampede of retries, so the recovery is slow and may fail.

Worse, in Kubernetes, if the deep check is wired to *liveness*, the kubelet restarts every pod. Now you have a full cold start of the fleet during a dependency incident, plus a `CrashLoopBackOff` that outlives the original cause.

The correct design:

1. **Readiness reflects only this instance's ability to serve**: process healthy, thread pool not saturated, warm-up complete, not shutting down. No shared dependency.
2. **Liveness is shallower still**, and never touches the network.
3. **Dependency health is a metric and an alert**, exposed on a separate `/health/dependencies` endpoint used by dashboards and humans - not by the load balancer.
4. **Handle dependency failure in the request path**: circuit breaker, fallback, degraded response, cached answer (Q157). The instance stays in rotation and serves what it can.
5. **Fail-open at the load balancer**: configure it so that when *all* targets are unhealthy it sends traffic anyway, on the theory that a possibly-degraded backend beats a guaranteed 503. Most modern balancers support this and it should be on.

The general principle: a health check should answer "will removing me help?" If every instance would be removed, the answer is no, and the check is measuring the wrong thing.

### Q88. DNS in a design

DNS is a routing decision cached by machines you do not control. That is the whole answer, and every consequence follows from it:

- **TTLs are advisory.** You set 60 seconds; ISP resolvers round up to 300 or 3600, corporate resolvers cache aggressively, and some clients ignore TTL entirely. The JVM historically cached resolutions **forever** by default (`networkaddress.cache.ttl`), and connection pools resolve once at pool creation, so a long-lived Java service can hold a stale IP for days.
- **You cannot observe it.** There is no metric telling you how many clients still have the old record.
- **Propagation is not atomic.** During a change, some clients go to the old target and some to the new, for an unbounded period.

So DNS is a poor failover mechanism: your RTO becomes "however long the slowest resolver and client caches take", which is minutes to hours, not seconds. It is also a poor load balancing mechanism, because per-client caching means load is distributed by *client population*, not by request.

What to use instead: **anycast or a global load balancer** for failover (the IP does not change, the routing does), health-checked target groups behind a stable hostname, and client-side load balancing with a discovery service for internal traffic. Keep DNS for coarse, slow-moving decisions - which region a hostname points at as a deliberate, planned change - and give those records a short TTL anyway, so that when you do need it, you have not made it worse.

### Q89. Anycast, GeoDNS, global load balancers

| Mechanism | How it routes | Failover speed | Precision | Cost/complexity |
| --- | --- | --- | --- | --- |
| **GeoDNS** | Resolver's location (not the user's) picks an answer | Minutes to hours - bounded by DNS caching (Q88) | Coarse; wrong when the resolver is far from the user or the user uses a public resolver | Cheap, widely available |
| **Anycast** | BGP announces the same IP from many locations; the network picks the nearest | Seconds - withdraw the announcement and traffic reroutes | Good for latency; but BGP paths are chosen by AS-path length, not latency, so occasionally odd | Needs IP space and provider support; CDNs and cloud global LBs give it to you |
| **Global load balancer** (Cloud Global LB, Front Door, Global Accelerator) | Anycast entry point plus health-checked backend selection at the edge | Seconds; health-driven, no client involvement | High - can consider health, capacity, latency and weights | Managed, priced per GB and per rule; the pragmatic default |

The recommendation I would give: use an **anycast-based global load balancer** as the entry point, with GeoDNS only if you need to steer between entirely separate stacks that cannot share an IP. Anycast also has a specific advantage for TCP-heavy and TLS-heavy traffic: the handshake terminates at the nearest POP, so you save one to three round trips before the request even starts - often more latency than the routing decision itself.

The anycast caveat worth knowing: a long-lived TCP connection can break if BGP reroutes mid-connection, since the new POP has no state for it. This is a non-issue for HTTP with retries and a real one for stateful protocols, which is why WebSocket termination often uses unicast regional endpoints behind an anycast front door.

### Q90. What belongs in an API gateway

**Belongs** (cross-cutting, identical for every service, and cheaper to do once):

- TLS termination, HTTP/2 and HTTP/3 handling, compression
- Authentication: token validation, signature verification, mTLS at the edge
- Coarse authorization: is this credential allowed to reach this route at all
- Rate limiting and quota enforcement per client (Q91)
- Request routing by path/host/header, and traffic splitting for canaries
- Request id generation, trace context propagation, access logging
- Payload size limits, timeouts, basic schema validation, WAF rules
- Response caching for shared responses
- Load shedding and circuit breaking at the edge

**Must not** (business logic, which turns the gateway into a shared monolith owned by nobody - `../03-microservices/answers.md` Q107):

- Domain validation and business rules
- Orchestration of multi-service workflows, saga coordination
- Data transformation encoding domain knowledge (field mapping, unit conversion, enrichment from other services)
- Fine-grained authorization requiring domain state ("can this user edit this document")
- Per-service special cases accumulated as a pile of scripts

The line I draw and defend: **the gateway may know about protocols, identities and routes; it may not know about the domain.** The test is "if a product requirement changes, does the gateway change?" If yes, that logic is in the wrong place. When teams need composition, the answer is a BFF they own (Q46), not a rule in the shared gateway - because the gateway's change-failure blast radius is every service at once, and its deployment cadence will never match 30 teams' needs.

### Q91. Rate limiting algorithms

| Algorithm | State per key | Burst behavior | Accuracy |
| --- | --- | --- | --- |
| **Fixed window** | 1 counter + window id | Allows 2x the limit across a window boundary | Poor at edges, trivially cheap |
| **Sliding window log** | Timestamp per request | Exact, no edge artifact | Exact, but O(limit) memory per key - unusable at high limits |
| **Sliding window counter** | 2 counters (current + previous window), weighted | Smooth, small edge error | Good; the usual production compromise |
| **Token bucket** | Token count + last refill timestamp | Allows a controlled burst up to bucket size, then steady rate | Good, and the most expressive - burst and rate are separate dials |
| **Leaky bucket (as a queue)** | Queue depth + drain rate | No burst passed downstream; smooths output | Good for protecting a fixed-capacity downstream; adds latency |
| **GCRA** | One timestamp | Token-bucket semantics with a single value | Exact and cheapest; less intuitive to explain |

My default is **token bucket** (or GCRA as its cheap implementation): two parameters that map directly onto what people actually want - "1,000 requests per minute, with bursts up to 100" - and O(1) state. I use leaky-bucket-as-a-queue when the goal is protecting a downstream with a hard concurrency ceiling rather than enforcing a contract, because there the right answer is to delay, not reject.

Fixed window is worth knowing only so you can explain the 2x boundary problem: with a 100/minute limit, a client sending 100 at 11:59:59 and 100 at 12:00:00 gets 200 requests in one second, entirely within policy.

### Q92. A distributed rate limiter at 50,000 QPS across 30 nodes

**Design.** Centralized counters in Redis with a local pre-check.

```
Node (local token bucket, small allowance)
  └─ every N ms or on local exhaustion → Redis (authoritative bucket, Lua script)
```

- **State lives in Redis**, one hash per `(key, policy)` holding tokens and last-refill time, mutated by a Lua script so refill-and-consume is atomic. Redis Cluster shards by key, so 50,000 QPS spread across the key space is comfortable - a single Redis node handles well over 100,000 simple ops/second, and the script is one round trip.
- **Batched leases, not per-request calls.** Each node requests a *block* of tokens (say 20, or 1 percent of the limit) and spends them locally, refreshing when the block runs low. This cuts Redis traffic by the block size and removes it from the hot path entirely. This is the key move: at 50,000 QPS you cannot afford a synchronous network hop per request for a control-plane concern.
- **Accuracy accepted:** with leases you may overshoot by up to `nodes x block_size` in the worst case. I size the block so that overshoot is a small percentage of the limit, and I state it: "the limit is enforced within about 5 percent, and never under-enforced by more than one lease." For a quota that is billed rather than protective, I use exact per-request counting on the smaller volume of billable events instead.
- **Failure mode is a decision, not an accident.** If Redis is unreachable: **fail open** with the local bucket at a conservative rate for a protective limit (availability matters more than precision), and **fail closed** for an abuse or security limit. This must be configured per policy and tested.
- **Sharding hot keys:** a single very hot key (one large tenant) becomes a hot Redis slot. Split it into N sub-keys, each with `limit/N`, and have nodes pick one by hash - the standard hot-key mitigation (Q140).

**What I would monitor:** allowed/rejected per policy, Redis script latency, lease round trips per second, and per-tenant rejection rates, because a spike in one tenant's rejections is either a customer incident or an attack.

### Q93. Per-instance rate limiting behind a load balancer `[T]`

If you configure 100 requests/minute per instance and you have 30 instances, a client whose requests are spread evenly by the balancer experiences an effective limit of **3,000/minute**, not 100. You have configured 1/30th of what you think, or 30x, depending on which direction you were worried about.

Worse, the effective limit is **unstable**: it changes when you autoscale (so a client's limit varies with your capacity, which is a bizarre contract), and it changes with balancing behavior - with sticky sessions or connection reuse, a client may hit one instance and get exactly 100, while another client fanning out over many connections gets 3,000. Two clients with identical behavior get different treatment, which is impossible to explain to a customer and impossible to test.

There is also a security consequence: an attacker who can open many connections gets the aggregate limit, so per-instance limiting provides almost no protection against the case it exists for.

The fixes, in order of preference: shared counters with local leases (Q92); or enforcement at a single choke point (the gateway or the edge CDN, which sees all traffic for a client); or - if you must stay per-instance - configure `limit / instance_count` and accept that the limit drifts, which only works with a fixed fleet size. Per-instance limits remain legitimate for one purpose: protecting *that instance's* own resources (a concurrency cap on in-flight requests), which is a bulkhead (Q155), not a quota.

### Q94. Admission control, load shedding, priority

**Admission control** decides at the entry point whether to accept a request at all, based on the system's ability to serve it - typically a concurrency limit derived from Little's Law, or an adaptive limiter (Netflix's concurrency-limits, TCP-Vegas-style) that infers capacity from observed latency. Accepting work you cannot finish is the core mistake in overload: it consumes resources and produces nothing (Q26).

**Load shedding** is dropping accepted-in-principle work when you are already over capacity, and doing it *cheaply and early* - at the edge, before the expensive parts of the request.

**Deciding what to drop** is the interesting part, and the answer is a priority scheme decided in advance:

| Priority | Class | Shed order |
| --- | --- | --- |
| 1 | Interactive user writes in a critical flow (checkout, payment) | Last |
| 2 | Interactive user reads | |
| 3 | Authenticated API clients within quota | |
| 4 | Retries (marked as such by the client) | |
| 5 | Prefetch, background sync, bulk/batch, analytics events | |
| 6 | Crawlers, unauthenticated scraping, speculative work | First |

Mechanics: the priority is carried in the request (a header set at the edge from the route and the credential, never trusted from the client), each tier has a concurrency budget, and shedding walks up from tier 6. Retries carry a `retry-attempt` header so they can be shed before first attempts - which is the control that breaks retry amplification (Q111). Shed responses are `503` with `Retry-After` (Q44), and they must be cheap: a shed request should cost microseconds.

The principle to state: **in overload, the goal is to maximize useful throughput, not to be fair.** Serving 80 percent of users perfectly beats serving 100 percent unusably.

### Q95. Sticky sessions, stateless, external state

| Approach | Deploy time | Failure time |
| --- | --- | --- |
| **Sticky sessions** (in-memory state, affinity by cookie/hash) | Every deploy destroys sessions unless you drain; rolling deploys log users out or lose their work. Scale-out does not rebalance existing sessions | Losing an instance loses its users' state outright; load is uneven and cannot be rebalanced |
| **Stateless** (all state in the token or the request) | Deploy freely, scale freely, no drain needed | An instance failure is invisible. Cost: token size, and no server-side revocation without extra machinery (Q226) |
| **External state** (session in Redis/database) | Deploy freely; state survives | An instance failure is invisible; but the state store is now a hard dependency and a new SPOF, and every request pays 0.5-2 ms |

My preference is **stateless for identity** (a signed token carrying claims) and **external state for anything genuinely session-scoped and large** - a multi-step form, a cart, a wizard - with a short TTL. That combination deploys freely and fails gracefully.

Sticky sessions remain legitimate in two cases: when the affinity is an *optimization* rather than a requirement (a warm local cache, where losing the instance costs latency and not correctness), and when the state is inherently connection-bound, as with WebSockets (Q182) - and there the design must still handle reconnection to a different node (Q185).

The deploy-time detail that matters most: with any affinity, graceful shutdown must **drain** - stop accepting new sessions, wait for existing ones with a deadline, then exit. Without a drain, every deploy is a small outage for a subset of users, which is exactly the kind of thing that shows up as an unexplained error-rate bump on every release.

### Q96. Connection management at the edge

- **Keep-alive is the single biggest latency win.** A new HTTPS connection is a TCP handshake (1 RTT) plus a TLS handshake (1 RTT with TLS 1.3, 2 with 1.2) before a byte of request is sent. At a 100 ms client RTT that is 200-300 ms of pure setup. Persistent connections amortize it away, TLS session resumption and 0-RTT reduce it for returning clients, and terminating at a nearby edge POP (Q89) shrinks the RTT that all of this multiplies.
- **Connection limits.** Each connection costs a file descriptor, socket buffers (tens of KB), and TLS session state. A server tuned for it handles hundreds of thousands; untuned, it exhausts ephemeral ports, file descriptors or memory. So the edge tier is sized by *connections*, and the service tier by *requests* - two different capacity models in one system.
- **Upstream connection pooling.** The edge should hold a small pool of long-lived connections to each backend rather than one per client connection; otherwise 100,000 client connections become 100,000 backend connections and the backend dies of accounting.
- **HTTP/2 and HTTP/3 change the arithmetic:** one client connection multiplexes many requests, so connection counts fall dramatically - but per-*connection* load balancing now skews badly (Q83), and one connection's head-of-line blocking (in HTTP/2 over TCP) affects all its streams. HTTP/3 over QUIC fixes the head-of-line problem and survives network changes, which matters for mobile.
- **Timeouts:** idle timeout on the client side (60-120 s), a shorter one upstream, and a request timeout that is *less* than the client's, so you control the failure. Also cap the number of requests per connection so connections rotate and rebalance across backends.

### Q97. Traffic shaping for a launch

Sequenced:

1. **Shadow (mirror) traffic** - weeks before. Copy real production traffic to the new path, discard the responses, and compare latency, error rates and (where possible) response diffs. Zero user risk, and it finds capacity and correctness problems while there is time to fix them. The trap is side effects: shadowed writes must go to an isolated store, or be suppressed.
2. **Dark launch behind a flag** - the code is deployed and dormant, enabled for internal users only. This decouples deployment from release, which is the single most valuable property of the whole list.
3. **Canary** - 1 percent of traffic, ideally pinned to a cohort so the experience is consistent, watched against a pre-agreed set of metrics (error rate, latency percentiles, business KPI, downstream saturation) with an automatic rollback threshold. The canary must run long enough to cover a full traffic cycle and at least one garbage collection or cache turnover, not five minutes.
4. **Ramp** - 5, 10, 25, 50, 100 percent, with a hold at each step long enough for the metrics to be statistically meaningful, and a bake period at 50 percent because that is where capacity problems first show.
5. **Kill switch** - a flag that reverts to the old path in seconds without a deploy, tested *before* the ramp begins. A rollback that requires a build is not a kill switch.

Two things that make this real rather than ceremonial: the rollback criteria are written down and automated before the ramp starts, and the metric comparison is canary-versus-baseline on the *same* time window, not canary-versus-yesterday.

### Q98. A 50x spike at a known time `[A]`

Knowing the time and date changes everything: this is a capacity and queueing problem, not an autoscaling problem, because autoscaling cannot react in the 30 seconds available.

**Before:**

1. **Pre-warm** - scale the fleet to full expected capacity well in advance (hours, not minutes), including the connection tier, the cache (pre-populated with the hot set), and any provisioned-capacity resource. Autoscaling is the backstop, not the plan.
2. **Load test at 1.5x the expected peak** against production-shaped data, and find the actual bottleneck rather than guessing. Do it early enough to fix what you find.
3. **Raise the ceilings that are not elastic**: database connections and pool sizes, provisioned IOPS, partition/shard counts (which often cannot change later, Q145), rate-limit configuration, and any quota on a managed service - cloud accounts have limits that will silently cap you.
4. **Simplify the critical path** for the event: reduce fanout, precompute what can be precomputed, make non-essential dependencies best-effort (Q163), and put the whole non-essential set behind flags you can turn off.
5. **Static-first**: push everything possible to the CDN with long TTLs - the landing page, the assets, the read-only view of whatever the event is about. A queue page or a countdown page should be a static object served entirely at the edge.

**During:**

6. **Queue the writes.** The spike is almost always a write spike (a sale, a registration, a vote). Accept the request, enqueue it, return 202 with a status resource (Q37), and drain at the rate the backend can sustain. This converts an availability problem into a latency problem, which is the trade you want. If fairness matters, use a virtual waiting room with signed position tokens.
7. **Admission control and priority shedding on** from the start, with retries shed before first attempts (Q94).
8. **Caps on expensive operations** - disable heavy reports, bulk endpoints and non-essential background jobs for the window.

**Around it:** a war room with a pre-agreed dashboard and pre-agreed decision thresholds; a rehearsal (a game day at the same scale) if the event matters commercially; and a written rollback and degrade plan naming who may pull each lever. Afterward, scale down deliberately and keep the load-test artifacts, because the next event will be bigger.

*Hook: a scheduled spike you prepared for, and which part of the estimate was wrong.*

---

## 7. Asynchronous processing, queues and streams

### Q99. When to go asynchronous

The four signals:

1. **The user does not need the result to continue.** Sending an email, generating a report, updating a search index, emitting an analytics event.
2. **The work is slow or variable relative to the latency budget.** Anything involving a third party, media processing, or an LLM call with a long tail (Q210).
3. **The work must survive failure and be retried.** A queue gives you durability, retries and a dead-letter path for free; an in-request call gives you none of that.
4. **The write rate is spiky and the downstream capacity is fixed.** A queue is a shock absorber that converts a spike into a delay (Q164).

A fifth that is really a variant: **fanout to many consumers**, where a synchronous call would mean the producer knowing all of them.

The counter-example: **anything the user must be told about immediately and cannot proceed without** - an authorization decision, a payment authorization result, an availability check at checkout, a validation error. Making these async does not remove the wait, it just moves it into a polling loop, adds a state machine, and makes the failure harder to report (Q102). The other counter-example is work small enough that the queue's overhead exceeds the work itself; a 2 ms database update does not need a message broker.

### Q100. Queue, log, stream processor, scheduler

| Requirement | Choice | Why |
| --- | --- | --- |
| "Resize each uploaded image once; retry failures; 100 workers" | **Work queue** (SQS, RabbitMQ) | Competing consumers, per-message ack, visibility timeout, DLQ. Order irrelevant |
| "Every service that cares should react to OrderPlaced, and I want to add consumers later and replay history" | **Log** (Kafka, Kinesis) | Retained, replayable, independent offsets per consumer group, ordered per partition |
| "Continuous 5-minute windowed aggregation with joins and late-arrival handling" | **Stream processor** (Flink, Kafka Streams) | Stateful operators, windowing, watermarks, checkpointed state |
| "Run this at 02:00 daily; also let a user schedule a reminder for an arbitrary future time" | **Scheduler** (cron/quartz for the first, a durable timer store for the second) | Time-triggered rather than event-triggered; needs missed-window and clock semantics (Q109) |

The distinction that matters most in a design discussion is **queue versus log**. A queue's message is consumed and gone - the queue is a *transfer* mechanism, and adding a second consumer means a second queue and a producer change. A log's message is retained and independently positioned per consumer - the log is a *storage* mechanism, and adding a consumer is a configuration change plus a replay. If you expect the set of consumers to grow, or you will ever need to reprocess, you want a log, and choosing a queue there is the decision teams most often regret.

### Q101. Instant success, 30 seconds of work

```
POST /v1/documents/{id}/publish
  ├─ validate synchronously (auth, ownership, schema)     ← fail here, visibly
  ├─ write intent row: status = QUEUED, job_id            ← same transaction
  ├─ outbox row → publisher → queue                       ← atomic with the above
  └─ 202 Accepted, Location: /v1/jobs/{job_id}
```

The pieces that make it feel instant *and* be correct:

1. **Validate synchronously.** Everything the user could have done wrong is checked before returning. Async failures should be infrastructure failures, not user errors, because a user error discovered 30 seconds later is a terrible experience.
2. **Persist the intent in the same transaction as the outbox row** (`../03-microservices/answers.md` Q92). Never enqueue and then write, or write and then enqueue - both lose work.
3. **Return a job resource** (Q37) so the client can poll, and push a completion signal (WebSocket, SSE or a webhook) so it usually does not have to.
4. **Optimistic UI:** the client shows the new state immediately with a "publishing…" affordance. Most of the perceived speed comes from here, not from the backend.
5. **Idempotent worker** keyed on the job id, because the message is at-least-once.
6. **Terminal failure is visible**: the job reaches `FAILED` with a reason, the user is notified in the same place they initiated it, and there is a retry action. A silent failure is worse than a synchronous error.
7. **A watchdog** that fails jobs stuck beyond a deadline, so `QUEUED` is never permanent.

### Q102. "Make it async" as a latency fix `[T]`

It genuinely helps when the *user's* next action does not depend on the result: the work is a side effect (notification, indexing, analytics), or the result is consumed later (a report, an export), or the user's mental model already accepts a delay (upload processing). Here you have removed the latency from the critical path and also gained retries and buffering.

It does not help - it just relocates the wait - when the user needs the answer to proceed. Making an availability check async means the client polls, so the user still waits the same wall-clock time, and you have added a job store, a polling load of `clients / poll_interval` requests per second, a state machine, two more failure modes (stuck jobs, lost notifications) and a worse error-reporting story. That is negative value.

The honest test I apply: **does the user's next screen depend on this result?** If yes, async is a distraction and the fix is to make the work faster - cache it, precompute it, parallelize the fanout, or reduce it. If no, async is right.

There is a middle case worth naming: work that must *appear* immediate but is genuinely slow. There the answer is optimistic UI plus async execution plus a compensating path if it fails (Q101) - which is a real design, not a relocation, because it changes what the user waits for rather than where the waiting happens.

### Q103. Work queue mechanics

- **Visibility timeout (or lease):** on delivery, the message is hidden from other consumers for N seconds. If the worker does not ack within N, it reappears. N must exceed the p99.9 processing time, or you get duplicate concurrent processing of the same message - the most common misconfiguration. For variable work, extend the lease periodically (heartbeat) rather than setting N to the worst case, because a long timeout also means a slow recovery from a crashed worker.
- **Ack after the work is durable**, never on receipt. Ack-on-receipt converts at-least-once into at-most-once and loses messages on a crash.
- **Retry with exponential backoff and jitter**, with the delay applied in the queue (a delay queue or a re-enqueue with a visibility delay) rather than by the worker sleeping - a sleeping worker is occupied capacity.
- **Dead-letter queue** after a bounded attempt count (5-10). The DLQ is not a graveyard: it needs an alert on depth, a triage owner, a tool to inspect and edit, and a replay path. A DLQ nobody reads is silent data loss.
- **Poison messages** - malformed, or triggering a deterministic bug - are the responsibility of the **consumer's owner**, and the mechanism is the attempt counter. Without a cap, one poison message plus infinite retries is a permanent hot loop that can consume the whole consumer group's capacity. This is the failure I have seen most often in queue-based systems.
- **Idempotency** at the consumer, because everything above is at-least-once (`../03-microservices/answers.md` Q52).

### Q104. Ordering guarantees

**Per-key ordering** is what you almost always need and can actually have: partition by entity id, one consumer per partition at a time, and all events for one order/user/account are processed in sequence. You give up: the ability to parallelize within a key, and even distribution (a hot key is a hot partition, Q140).

**Global ordering** requires a single partition, therefore a single consumer, therefore a throughput ceiling of one machine. You give up horizontal scalability entirely. It is almost never a real requirement - what people usually want is a *total order for auditing*, which a monotonic sequence number or a hybrid logical clock (Q129) provides without serializing the processing.

What you must give up for either, stated plainly: ordering and parallelism trade against each other, and ordering plus retries trade against liveness. If message 5 for a key fails and you must preserve order, message 6 cannot proceed - so a poison message blocks the key (or the partition) indefinitely. The escape is to make the consumer's operations **commutative or idempotent with version checks** so that order stops mattering: apply an update only if its version is newer, and out-of-order delivery becomes harmless. That is the design I push for, because it removes the constraint rather than paying for it.

### Q105. Strict ordering and high throughput `[T]`

The tension: ordering requires serialization at some scope; throughput requires parallelism. Within one ordering scope you cannot have both, because the second event cannot be processed until the first is done.

Three escapes:

1. **Shrink the ordering scope.** You almost never need a global order - you need order per account, per conversation, per device. Partition by that key and you get N-way parallelism with strict order inside each key. This is the right answer 90 percent of the time, and the design question becomes "what is the smallest scope that preserves correctness?"
2. **Make the operations order-insensitive.** Attach a version or a timestamp and apply last-write-wins-by-version, or use CRDT-style merge (Q131), or make each operation idempotent and commutative (set a field to a value rather than incrementing it). Then order does not matter and you can parallelize freely. This is the strongest answer when you can get it, because it eliminates the constraint.
3. **Order at the edges, parallelize in the middle.** Assign a sequence number at ingest (single-writer per key, cheap), process out of order in parallel, and re-sequence at the point where order is observable - a reorder buffer before delivery to a client, or an `ORDER BY sequence` on read. You pay buffering memory and a small latency for the reordering window, and you get both properties.

A fourth, pragmatic one: **batch within a key**. If a key produces bursts, process its events as an ordered batch in one unit of work; you get order and amortized throughput, just with a coarser granularity.

### Q106. Backpressure

Backpressure must be applied **at the point where work enters the system**, and propagated from the slowest stage upstream to that point. Anywhere else and you are just choosing which buffer overflows.

Mechanisms by transport: TCP flow control and HTTP/2 flow-control windows do it for you at the socket level; gRPC streaming exposes it; reactive frameworks make it explicit as request-N demand; a bounded queue with a *blocking or rejecting* put does it crudely but effectively; a consumer that stops polling does it in Kafka (lag grows, producers are unaffected); and a semaphore/concurrency limiter does it inside a service.

What happens without it: the fastest stage fills an unbounded buffer, memory grows until garbage collection thrashes or the process is killed, latency grows without bound so everything in the buffer is stale by the time it is processed, and failure - when it comes - loses the entire buffer at once. Unbounded queues turn a throughput problem into an outage, and they hide the problem until it is unfixable. **Every queue in a design should have a declared maximum depth and a defined behavior at that depth.**

Signalling upstream: within a process, block or reject. Across a network, return `429`/`503` with `Retry-After` (Q44), or in a streaming protocol reduce the flow-control window, or simply stop acking so the broker stops delivering. At the edge, admission control (Q94). The important part is that the signal reaches the *originator* - a system that pushes back only at stage 4 of 5 still accumulates in stages 1-3.

### Q107. Consumer lag

**Causes:** the consumer is slower than the producer (insufficient parallelism, slow downstream, an expensive per-message operation, GC pauses); a rebalance or restart cost; skew, where one partition's key is hot so one consumer is the bottleneck while others idle; a poison message being retried; or a producer spike.

**What it predicts:** end-to-end freshness, which is usually the actual SLI for an async pipeline (Q7). It is also the leading indicator for a **retention-driven data loss** - if lag exceeds the log's retention, the consumer's offset falls off the beginning and messages are lost permanently. And lag *derivative* is the number to alert on: a steady 10,000 is fine, a lag growing linearly for 10 minutes will not recover on its own.

**Two ways to shrink it without adding consumers** (which is capped by partition count anyway):

1. **Batch and pipeline the work.** Fetch larger batches, do downstream writes as bulk operations, and parallelize the *I/O within* a batch while preserving per-key order. Turning 500 single-row inserts into one 500-row insert is typically a 10-50x improvement, and it is the highest-value change in most lagging consumers.
2. **Reduce work per message.** Filter early (do not deserialize what you will discard), move enrichment lookups into a local cache, defer non-essential work to a second consumer group, and shed or sample low-value messages. Also fix the poison-message loop and the rebalance cost (cooperative rebalancing, `../03-microservices/answers.md` Q47), because both are pure waste.

Adding partitions is the third answer, but note it only helps future data and requires a repartition (Q144).

### Q108. Fanout patterns

| Pattern | Replay | Isolation |
| --- | --- | --- |
| **Queue per consumer** (publisher writes to N queues, or a fanout exchange) | None - once consumed, gone. Replay means the producer resends | Excellent: each consumer has its own queue, its own depth, its own DLQ. One slow consumer affects nobody |
| **Topic with subscriptions** (SNS→SQS, Pub/Sub, RabbitMQ exchange→queues) | Limited to each subscription's retention | Excellent, and the producer does not know the consumers. The broker does the fanout |
| **Shared log with independent offsets** (Kafka consumer groups) | Full, to the retention limit - rewind an offset and reprocess | Good but not perfect: consumers share the log's IO and page cache, and a consumer replaying from the start of a large topic can degrade others by evicting hot pages |

My default is the **shared log**, because replay is worth a great deal - it is how you recover from a consumer bug, how you build a new read model, and how you onboard a new team without a producer change. The cost is that consumers are coupled to the log's partitioning and schema.

The hybrid that works well in practice: a log as the backbone for durable, replayable domain events, plus a per-consumer queue in front of any consumer whose processing is slow, unreliable or externally-dependent - the log gives replay and history, the queue gives per-consumer retry, delay and DLQ semantics without polluting the log's offsets. That is exactly the shape of the webhook delivery problem (Q45).

### Q109. Scheduled and delayed jobs

**Design.** A durable timer store plus a dispatcher.

```
schedules(id, fire_at, payload, status, lease_owner, lease_until, attempt)
  index on (status, fire_at)

dispatcher (N replicas, every second):
  UPDATE schedules SET status='CLAIMED', lease_owner=me, lease_until=now()+30s
   WHERE status='PENDING' AND fire_at <= now()
   ORDER BY fire_at LIMIT 100
   FOR UPDATE SKIP LOCKED
  → publish to queue → status='FIRED'
```

- **At-least-once firing** is the only achievable guarantee: the dispatcher can crash between claiming and publishing, so the lease expires and another replica retries. Therefore every scheduled action must be idempotent, keyed on `(schedule_id, occurrence)` - the occurrence being the intended fire time for a recurring job, so a duplicate for the same window is detectable.
- **Missed windows** happen after an outage: on recovery, 40,000 jobs are overdue. The policy must be explicit per job type - *fire all* (catch-up, for billing), *fire once* (coalesce, for a cache refresh where only the latest matters), or *skip* (for a notification whose moment has passed). Encode it as a field, and cap catch-up firing rate so recovery does not become a self-inflicted spike.
- **Clock skew:** dispatchers must use the **store's** clock (`now()` evaluated server-side), not their own, so a skewed node cannot fire early or hold everything back. For sub-second precision, use a monotonic clock for intervals and the database clock for absolute times (Q129).
- **Duplicate suppression:** a unique constraint on `(job_key, occurrence)` in the *executor's* idempotency table - the same mechanism as Q35.
- **Scale:** a relational table with `SKIP LOCKED` handles millions of timers and tens of thousands of fires per second, and is far easier to operate than a bespoke timing wheel. For very high volume or very long horizons, bucket by time (a hashed timer wheel with per-minute buckets) so the query touches one small partition.

### Q110. Batch, micro-batch, streaming

| | Batch (hourly/daily) | Micro-batch (seconds-minutes) | Streaming (per event) |
| --- | --- | --- | --- |
| Latency | Hours | Seconds to minutes | Sub-second to seconds |
| Cost per event | Lowest - full parallelism, columnar reads, spot instances, no always-on state | Middle | Highest - always-on, stateful, and the state must be replicated |
| Correctness | Easiest: the window is closed, all data has arrived, reruns are trivial | Good; late data handled per batch | Hardest: late and out-of-order data, watermarks, and state that must be checkpointed |
| Reprocessing | Trivial - rerun the job | Trivial-ish | Hard - replay through a stateful topology, and the state may not be reconstructible |
| Operational load | Low; failures are retried tomorrow | Medium | High; a bug is live and continuous |

The honest position: **use batch until latency requirements force you off it**, and then use micro-batch, and only use true streaming when sub-second matters. A great many "streaming" systems exist because streaming was fashionable, and they cost 5-10x a batch job producing the same dashboard 30 seconds later than anyone needs.

What changes in correctness is the part to emphasize: a batch job over a closed window is exact. A streaming aggregation is a *continuously revised estimate*, because more data for that window may still arrive. That means the same query gives different answers at different times, and reconciling the streaming number against the batch number becomes a permanent chore - which is precisely why the lambda architecture existed and why people dislike it (Q203).

### Q111. Retry storms in a queue system `[T]`

The amplification: a consumer fails on a downstream error and re-enqueues. If the downstream is broken, every message fails, so every message is re-enqueued - the queue's throughput is now consumed by doomed work. With N retries configured, one incoming message becomes N+1 units of work, and if the retry is immediate the effective load on the broken downstream is multiplied by N+1 as well. Layer three such consumers and you have a 100x amplification of a partial outage into a total one.

Two extra amplifiers people miss: retried messages compete with *new* messages for the same consumer capacity, so fresh work starves; and the retry population grows even as the downstream recovers, so recovery is delayed by a backlog of retries - the metastable pattern again (Q26).

The controls that bound it:

1. **A retry budget**, not a retry count: retries may consume at most X percent (typically 10) of total attempts, measured over a rolling window, and are dropped beyond that. This bounds amplification at 1.1x no matter how broken things are (`../03-microservices/answers.md` Q86).
2. **Circuit breaker on the downstream**: stop attempting, fail fast, and stop pulling messages at all - a paused consumer is the correct response to a dead downstream. It also stops burning attempts.
3. **Exponential backoff with jitter, applied in the broker** via delay queues or per-attempt delay tiers, so retries are spread and do not occupy workers.
4. **Separate retry queues per attempt tier**, so retries cannot starve first attempts and can be deprioritized or shed independently (Q94).
5. **Attempt cap and DLQ** so nothing retries forever (Q103).
6. **No nested retries.** One layer owns retrying; the others fail fast. Multiplication across layers is how 3 becomes 243.

### Q112. Exactly-once processing, honestly

The honest version: **exactly-once *delivery* does not exist** across a network, because the sender cannot distinguish a lost message from a lost acknowledgement, so it must either resend (at-least-once) or not (at-most-once). What is achievable is **exactly-once *effect***: the observable state changes once, however many times the message is delivered.

What you build to get it:

1. **At-least-once delivery** as the transport guarantee.
2. **Idempotent consumers**, by one of three mechanisms: a deduplication table keyed on the message id, written in the same transaction as the effect; a conditional write with a version check (`UPDATE ... WHERE version = n`); or an operation that is naturally idempotent (set, not increment; upsert, not insert).
3. **Atomicity between the effect and the offset/ack.** This is the crux. If the effect lands in a database, store the consumed offset *in that database, in the same transaction* - then the commit of the effect and the record of consumption cannot diverge. Kafka's transactions achieve the same for Kafka-to-Kafka topologies by making the produce and the offset commit atomic within the log (`../03-microservices/answers.md` Q36).
4. **An outbox on the way out**, so any message the consumer emits is atomic with its state change.

What is *not* achievable: exactly-once effects on a side effect you do not control - sending an email, calling a third-party payment API, printing a document. There you get at-least-once plus the external system's own idempotency key, and if it has none, you get duplicates and a reconciliation process. Saying this plainly is the signal being tested.

### Q113. Replay without double-charging

The design that makes replay safe:

1. **Every effect is idempotent, keyed on the event id** (Q112). This is the foundation: if the consumer's write is `INSERT ... ON CONFLICT (event_id) DO NOTHING` or a version-checked update, replaying three days of events is a no-op for anything already applied. Replay safety is a property you build in advance; it cannot be added during the incident.
2. **Separate "replayable" from "external" effects.** The consumer that updates internal state is safe to replay. The consumer that calls a payment provider or sends an email is not, unless the provider is idempotent. So split them into different consumer groups, and during replay disable the external-effect consumers or run them in a mode that only reconciles rather than acts.
3. **Replay into a shadow, then swap.** For rebuilding a projection, write to a new table or index, verify it (row counts, checksums, spot comparisons against the live one), then atomically switch reads. This avoids the window where the projection is half-rebuilt and serving.
4. **Rate-limit the replay.** Three days of events at 100x normal rate will saturate the downstream store and degrade live traffic. Throttle to a fixed rate, run it on a separate consumer group with its own resource budget, and monitor live latency as the control signal.
5. **Bound it explicitly**: replay from a specific timestamp or offset to another specific one, recorded in a runbook, so a mistake is a small mistake.

The operational precondition worth stating: rehearse it. A replay path that has never been run is in the same category as a backup that has never been restored (Q162).

### Q114. Choosing a broker

| Option | The decisive question |
| --- | --- |
| **Kafka** | Do you need retention, replay, ordered partitions and many independent consumers of the same stream? If yes, nothing else does this well. If no, you are paying a large operational bill (or a managed premium) for features you will not use |
| **SQS/SNS** (or equivalent managed queue) | Is this a work queue where you want zero operations and effectively unlimited scale, and can you live without ordering (standard) or with limited throughput (FIFO)? Then this is almost always the right answer in a cloud environment |
| **RabbitMQ** | Do you need rich routing (topic/header exchanges), per-message TTL, priority queues, and low-latency request/reply - i.e. broker-side logic rather than a log? |
| **Database-backed queue** | Is the volume modest (thousands/second), and is *transactional atomicity with your data* the dominant requirement? Then `SELECT ... FOR UPDATE SKIP LOCKED` is a legitimate, boring, excellent choice - one fewer system (Q57) |

The advice I would actually give: start with a database-backed queue or a managed queue, and adopt Kafka when you have a *stream* problem (multiple consumers, replay, ordering, high volume) rather than a *task* problem. Introducing Kafka for a task queue is the most common over-engineering decision in this space, and the version I have seen most often is a three-broker cluster carrying 50 messages a second.

### Q115. An async backbone for 20 teams `[A]`

**Technical shape.** A shared Kafka (or managed equivalent) as the event backbone, with per-team queues in front of slow or externally-dependent consumers (Q108). A schema registry in the path. One CDC pipeline per system of record, using the outbox pattern so events are atomic with state changes.

**The governance that stops it becoming a mess - this is the actual answer:**

1. **Event ownership and naming.** Every topic has exactly one owning team and a name encoding domain and version: `orders.order-placed.v1`. Only the owner produces. This single rule prevents the most common decay, which is several teams writing to the same topic with different meanings.
2. **Schema registry with enforced compatibility** in CI: `FULL` compatibility required, breaking change means a new topic and a documented consumer migration (Q41). The registry is a gate, not a wiki.
3. **A published contract per event**: schema, semantics, ordering guarantee, delivery guarantee, expected volume, retention, and whether it is a domain event or a private implementation detail. The last distinction matters - teams must be able to publish internal events without them becoming an accidental public API.
4. **Consumer registration.** The owner can see who consumes their topic, which makes deprecation possible at all (Q47) and gives a blast-radius map.
5. **Standard client library** with the non-negotiables built in: at-least-once semantics, idempotency helpers, retry budgets, DLQ wiring, trace-context propagation, and metrics with consistent names. Governance implemented as a library succeeds; governance implemented as a document does not.
6. **Platform SLOs and quotas**: per-topic throughput and retention quotas, per-consumer-group lag alerting owned by the consuming team, and a documented broker availability SLO. Noisy-neighbor protection so one team's replay cannot degrade another's pipeline (Q108).
7. **A small set of rules with teeth**: no event carries PII without classification and a documented retention; no consumer group without an owner and an alert; no topic without a schema; events are facts about the past, never commands to a specific service.

**What I would explicitly avoid:** a central integration team that must approve every event (becomes the bottleneck, and Conway's Law will route around it); a canonical enterprise data model (never converges); and orchestration logic in the broker layer.

*Hook: an event platform you governed, and the one rule that mattered most.*

---

## 8. Consistency, coordination and time

### Q116. CAP, correctly, and PACELC

**CAP stated correctly:** in the presence of a network **partition**, a system must choose between remaining **available** (serving requests on both sides, accepting divergence) and remaining **consistent** (in the linearizable sense - refusing service on at least one side). It says nothing about latency, nothing about normal operation, and "consistency" means linearizability specifically, not the C in ACID.

**Why it is nearly useless as a design tool:** partitions are rare and brief; the interesting trade-offs happen the other 99.99 percent of the time. It is binary, whereas real systems have a spectrum of consistency levels (Q117) and choose different points per operation. It treats the system as one thing, whereas real systems are CP for payments and AP for the catalogue in the same request. And "choosing A" is not a design - the design is *what you do with the divergence*, which CAP does not discuss.

**PACELC** adds the useful half: **if Partition, then A or C; Else, then Latency or Consistency.** The `ELC` clause is the one that shapes actual systems - every synchronous replication decision, every quorum size, every "read from the primary or a replica" choice is a latency-versus-consistency trade made during *normal* operation. DynamoDB is PA/EL by default with PC/EC available per request; a single-primary PostgreSQL with synchronous commit is PC/EC; Cassandra with `LOCAL_QUORUM` is PA/EL.

The sentence I would use: CAP tells you what happens on the worst day, PACELC tells you what you pay for every day, and the second one is the design.

### Q117. The consistency ladder

| Level | Guarantee | A feature that needs it |
| --- | --- | --- |
| **Linearizable** | Every operation appears to happen instantaneously at a single point between invocation and response; there is one global order consistent with real time | Distributed lock acquisition; a uniqueness check ("is this username taken"); a balance check that must not permit an overdraft |
| **Sequential** | One global order that all nodes agree on, but not necessarily matching real time | A replicated state machine where all replicas must apply the same sequence - a config store |
| **Causal** | Operations that are causally related are seen in order by everyone; concurrent ones may differ | A comment thread: you must never see a reply before the comment it answers |
| **Read-your-writes** | A client always sees its own prior writes | "Save profile" followed by viewing the profile; posting a message and seeing it in the list |
| **Monotonic reads** | A client never sees time move backwards | A feed or a counter that must not flicker between old and new values as requests hit different replicas |
| **Eventual** | Replicas converge if writes stop | View counts, recommendations, search index freshness, an analytics dashboard |

The two points that earn credit: the ladder is **per operation, not per system** (Q14), and the middle rungs - read-your-writes plus monotonic reads, together called "session consistency" - are what users actually perceive as correctness, are far cheaper than linearizability, and are what most products should target by default.

### Q118. "Eventually" is how long `[T]`

"Eventual consistency" is a liveness property with no time bound: it promises convergence *if writes stop*, which they never do. As a specification it is unusable, because a system that converges in 200 ms and one that converges in 6 hours are both eventually consistent.

What a design must specify instead:

1. **A staleness bound as an SLO**: "99.9 percent of writes are visible on all read paths within 2 seconds; the maximum is 30 seconds, after which we alert." That is a number a product owner can accept or reject, and a number you can test.
2. **The session guarantees layered on top** - read-your-writes and monotonic reads for the user who made the change (Q117), because that is the staleness people actually notice.
3. **The behavior when the bound is exceeded**: degrade, warn the user, block writes, or fail the read.
4. **What is *never* stale**: the list of invariants enforced synchronously (Q120), so nobody has to guess.

**How to measure it:** replication lag is the proxy, but it must be measured end to end, not from the database's own counter. The reliable technique is a **heartbeat writer**: write a timestamped row to the primary every second, read it from each replica and each derived store, and report `now() - written_at` as the observed lag. That single metric covers replica lag, CDC lag, indexer lag and cache staleness with one mechanism, and it is what I would put on the dashboard and alert on. For queues, the same idea is end-to-end freshness (Q7).

### Q119. Read-your-writes across replicas

Three implementations:

1. **Read-from-primary for a window.** After a write, mark the session (a cookie, a Redis key, or a claim in the token) with a timestamp, and route that user's reads to the primary for the next N seconds. Cost: primary read load proportional to write rate x window, and a window that is a guess - too short and the guarantee breaks, too long and the primary carries the traffic you built replicas to avoid.
2. **Version-token (LSN) tracking.** The write response carries the replication position (`pg_current_wal_lsn()`, a GTID, a version stamp). The client returns it on subsequent reads; the router picks a replica whose applied position is at or beyond it, or waits briefly, or falls back to the primary. Cost: a token in the client contract and position tracking per replica. This is the correct general solution - precise, no guessing, and it composes with caches (Q81).
3. **Sticky routing to one replica per session**, with that replica's lag monitored. Cost: uneven load, a broken guarantee whenever the session moves (deploy, failover, scale-out), and it gives monotonic reads more reliably than read-your-writes. Cheapest to implement, weakest guarantee.

A fourth that is often best: **do not read at all.** Return the authoritative post-write state in the write's response and have the client render it, so there is no read to be stale. Combined with option 2 for subsequent navigation, this covers most real products.

I would also state the trap: adding a cache in front of any of these reintroduces the problem at the cache layer (Q81), so the session marker has to bypass the cache too.

### Q120. Placing and shrinking the strong-consistency boundary

**Where it goes:** around the smallest set of data that shares an invariant which must never be violated. Concretely, the boundary is a transactional aggregate - one account's balance, one product's inventory row, one booking calendar, one username registry - owned by a single writer with a serial order.

**How to keep it small**, which is the real skill:

1. **Reformulate invariants as local ones.** "Total across all accounts must equal X" is global and expensive. Double-entry bookkeeping makes it local: every transfer is two entries in one transaction, and the global invariant becomes a *derived* property you can audit rather than enforce.
2. **Reserve instead of confirm.** Inventory: a conditional decrement creating a short-lived reservation is a small, local, strongly-consistent operation; the rest of checkout can be eventual, with a compensating release on timeout.
3. **Escrow and partition the resource.** Split 1,000 units of stock into 10 buckets of 100, each independently and locally decremented. You lose the ability to sell the last unit optimally and gain 10x concurrency - the standard escrow trade.
4. **Move the check to the narrowest step.** A uniqueness constraint on one table is cheap; a distributed uniqueness check across services is not. Nominate one owner of the namespace.
5. **Accept detect-and-compensate for anything whose violation is recoverable.** Overbooking a flight by 0.01 percent with a compensation policy is a business decision that buys enormous architectural freedom - and it is the design most airlines actually use.

The framing: **coordination is a tax you pay per operation inside the boundary.** So the design goal is not to avoid coordination, it is to make the coordinated set small and the uncoordinated set large.

### Q121. Distributed transactions

**Two-phase commit.** A coordinator asks all participants to prepare, and commits only if all vote yes. Gives atomicity across heterogeneous resources. Costs: it is a **blocking** protocol - if the coordinator fails after prepare, participants hold locks *indefinitely* until it recovers, because they may neither commit nor abort. Availability becomes the product of all participants' availability plus the coordinator's, latency includes two round trips plus the slowest participant, and locks are held for the whole duration, which destroys throughput under contention.

**Sagas.** A sequence of local transactions, each with a compensating action; on failure, compensations run backwards. Gives availability and no distributed locks. Costs: no isolation, so intermediate states are visible (a partially-completed order), which produces anomalies you must design for; compensations are business logic, not rollback, and some actions cannot be compensated (an email is sent); and the state machine and its failure paths are substantial code (`../03-microservices/answers.md` Q56-60).

**Doing without.** Redesign so the transaction is not distributed: co-locate the data that shares an invariant in one store (which usually means the service boundary was wrong), or make the operation idempotent and eventually convergent so partial completion is self-healing.

| | Availability cost | When |
| --- | --- | --- |
| 2PC | Multiplicative; blocking on coordinator failure | Within one datastore, or across two resources you fully control, low volume, short transactions |
| Saga | Additive and degradable | Cross-service business processes, long-running, where compensation is meaningful |
| Redesign | None | Almost always the best answer, and the first one to propose |

### Q122. 2PC across three services `[T]`

What fails, specifically:

1. **Coordinator failure after prepare** leaves all three services holding locks with no authority to resolve. This is the textbook blocking problem, and in practice it means an operator manually resolving in-doubt transactions during an incident - `pg_prepared_xacts` entries that also pin the vacuum horizon and cause bloat (`../06-database/answers.md` Q93).
2. **Availability multiplies.** Three services at 99.9 percent plus a coordinator gives ~99.6 percent for the combined operation, before considering the network between them.
3. **Locks held across network hops** mean lock duration goes from microseconds to tens of milliseconds, so throughput on any contended row collapses by orders of magnitude.
4. **Heterogeneity.** Most modern components - Kafka, DynamoDB, S3, any REST API, most managed databases - simply do not implement XA, so the protocol cannot span the actual system.
5. **Operational reality:** it requires a transaction manager to be highly available and its recovery log to be durable, which is a piece of infrastructure nobody wants to own in 2026.

**What I propose instead:** first, check whether the three services should be one - if a single business operation cannot complete without atomically updating all three, the boundaries are probably wrong (`../03-microservices/answers.md` Q3). If they are genuinely separate, a **saga with a pivot step**: order the steps so that the irreversible one is last (or designated the pivot), everything before it is compensatable, everything after it is retriable-until-success. Add an outbox for atomic messaging, idempotency keys on every step, and a reconciliation job that finds and resolves stuck instances. Then state the visible consequence honestly: intermediate states exist and the UI must show them (`PENDING`, not a lie).

### Q123. Idempotency as a system property

- **Where keys are generated:** at the **originating** boundary, once, by the party that will retry - the client for an API call (Q35), the producer for a message, the caller for an internal RPC. Downstream steps derive their keys deterministically from it (`hash(root_key + step)`, Q38) so a retry at any level maps to the same key.
- **Where they are stored:** in the datastore that holds the effect, so uniqueness and effect commit atomically. A unique index on the scoped key is the enforcement; a cache is not.
- **How long they live:** at least as long as the maximum retry horizon of any client, which is longer than people think - a mobile app with an offline queue may retry after days. My default is 7 days for general APIs, 30-90 days for financial operations to cover the dispute and reconciliation window, and for message consumers, longer than the log's retention so a replay cannot double-apply (Q113).
- **The cleanup problem** is the part usually missed: an idempotency table grows at the full write rate of the system forever, and it is the highest-write table you have. `DELETE FROM ... WHERE created_at < ...` on a billion-row table is a bloat and lock disaster. The answer is **time-partitioning with partition drops** (`../06-database/answers.md` Q62), or a TTL-native store (DynamoDB TTL, Cassandra with a matching `gc_grace_seconds`), or a rotating pair of tables. Design the retention mechanism at the same time as the table, because retrofitting it onto a live billion-row table is a project.

One more system-level point: idempotency keys are a **privacy and multi-tenancy surface**. Scope them per tenant (Q35), and never let a key from one tenant collide with another's, or you have built a cross-tenant information leak.

### Q124. Distributed locking and leases

**When it is legitimate:** to prevent duplicated *work* (only one node runs this cron job, only one worker compacts this file), where a rare duplication is a performance problem, not a correctness one. It is also legitimate as an optimization to reduce contention on a resource that has its own correctness mechanism underneath.

**When it is not:** as the guarantee for correctness of a write. A lock cannot make a non-atomic operation atomic, because the lock and the operation are not atomic with each other. For correctness, use the datastore's own mechanisms - a unique constraint, a conditional write, `SELECT ... FOR UPDATE`, an optimistic version check, or a compare-and-swap. Those are enforced by the same component that stores the data, so no gap exists.

**A lease** is a lock with an expiry, which is necessary because a lock holder can die and a distributed system cannot distinguish dead from slow. The expiry guarantees liveness (the lock is eventually released) at the cost of safety: the lease can expire *while the holder still believes it holds it*, because the holder was stopped by a GC pause, a VM migration, or an unlucky scheduler.

**Why a lock without fencing is unsafe:** node A acquires the lease, pauses for 40 seconds, the lease expires, node B acquires it and writes, then A resumes and writes - believing it is the sole holder. Two writers, no error reported, data corrupted. The lock system cannot prevent this; only the *resource* can, by rejecting A's write. That is fencing (Q125).

### Q125. Redlock and fencing tokens `[T]`

What can still go wrong with a Redis lock (single-node or Redlock):

1. **Process pause.** Any of GC, page-fault storms, VM live migration, or CPU starvation can stop a holder for longer than the TTL. When it resumes it has no idea time passed. No amount of quorum fixes this, because the fault is in the *client*, not the lock service.
2. **Clock assumptions.** Redlock's safety argument depends on bounded clock drift across nodes and on bounded message delay. Both are assumptions about an asynchronous system that the system does not guarantee - if a node's clock jumps, its notion of TTL is wrong.
3. **Failover with async replication.** A single-node Redis lock replicated asynchronously: the primary acknowledges the lock, fails over before replicating, and the new primary has no record - so a second client acquires the same lock legitimately.
4. **A lock released by the wrong owner.** Deleting by key without checking a per-holder value releases someone else's lock. (Fixed by storing a random value and deleting via a compare-and-delete script - necessary but not sufficient.)

**The fencing token that fixes it:** the lock service issues a monotonically increasing token with each grant. The holder passes the token with every write to the protected resource, and **the resource rejects any write bearing a token lower than the highest it has seen**. Now the paused node A holds token 33, node B holds 34 and writes; when A resumes and writes with 33, the storage rejects it. Safety no longer depends on timing at all.

The consequence to state: fencing requires cooperation from the resource. If the resource cannot check a token - most caches, most filesystems, most third-party APIs - then you cannot make the lock safe, and you must either make the operation idempotent and order-insensitive, or move the correctness check into a store that does support conditional writes.

### Q126. Leader election

**What needs a leader:** a single writer for an ordering guarantee; a coordinator for a partition's state (a Kafka partition leader, a shard primary); a singleton job (a scheduler dispatcher, a compaction driver); and any operation that must not run twice.

**How it works:** a consensus-backed lease. Candidates attempt to write themselves into a coordination service (etcd, ZooKeeper, Consul) with a TTL and a fencing epoch; the winner renews continuously. Consensus (Raft/Paxos) gives you a *single* decision that survives failures - which is why you should never build this on a store without it. In a database-only stack, a row with a lease and a monotonically increasing epoch, updated conditionally, is the same pattern.

**Failover and the gap:** detection takes one lease TTL (typically 5-15 s), plus an election round (hundreds of milliseconds), plus the new leader's warm-up - loading state, rebuilding caches, recovering an uncommitted log tail. So the gap is seconds, and during it:

- Writes fail or queue. The design must decide which, and clients must be told (`503` + `Retry-After`, not a hang).
- The old leader may still believe it leads, so **every write must carry the epoch and be rejected if stale** (Q125). This is not optional; it is the only thing preventing split-brain damage.
- If the new leader must recover state, its first seconds are slower, so a thundering herd of retries at that moment is dangerous - hence backoff with jitter.

The trade-off dial: a short lease TTL means fast failover and a higher risk of spurious elections during a GC pause or a network blip (which are themselves disruptive); a long TTL means stability and a slow failover. I pick the TTL from the availability target and make the *client* experience explicit rather than optimizing the number in isolation.

### Q127. Unique ID generation

| Approach | Ordering | Size | Failure mode |
| --- | --- | --- | --- |
| **UUIDv4** | None | 128 bits | None - fully local. But random keys wreck index locality (`../06-database/answers.md` Q5-6) |
| **UUIDv7 / ULID** | Time-ordered to the millisecond, then random | 128 bits | None - fully local. Leaks creation time. The modern default |
| **Snowflake** (timestamp + node id + sequence) | Time-ordered, and roughly sortable across nodes | 64 bits | Needs unique node ids (a coordination or configuration problem) and a monotonic clock - a backwards clock step can produce duplicates unless handled |
| **Database sequence** | Strictly monotonic | 64 bits | The database is a dependency on every insert; a single sequence is a global serialization point |
| **Sequence blocks / hi-lo** | Monotonic per allocator, gaps between blocks | 64 bits | One round trip per block, then local. Lost blocks on restart create gaps (harmless). Excellent compromise |
| **Coordination service** (etcd/ZooKeeper counter) | Strict | any | A network round trip and a hard dependency per id. Avoid on a hot path |

My defaults: **UUIDv7** when clients must generate ids offline or ids must be non-guessable across tenants; **Snowflake-style 64-bit** when id size and sortability matter at very high volume (and I would then say how node ids are assigned, because that is the part that breaks); **sequence blocks** in a single-database system, because they are nearly free and keep ids compact.

Two design notes worth volunteering: sequential ids leak volume and enable enumeration, so a public identifier should be a separate opaque value even when the internal key is sequential; and "sortable by id" is a property people build product features on, so decide deliberately whether you are promising it.

### Q128. Split-brain `[T]`

**How it happens:** a network partition (or a partial one, or a GC pause that looks like one) separates the leader from the majority. The majority elects a new leader. The old leader has not noticed - it still accepts writes, because from its side only its peers vanished. Now two leaders accept conflicting writes to the same logical resource. On heal, you have two divergent histories and no principled way to merge them; someone's writes are silently lost.

**The three defenses:**

1. **Quorum / majority.** No leader may act without confirming it holds a majority. In a partition, the minority side loses the ability to serve writes at all - which is CAP's C over A, chosen deliberately. This requires an odd node count and, crucially, that clients cannot be served by a minority partition.
2. **Fencing with a monotonic epoch** (Q125). Every write carries the leader's term/epoch, and the storage layer rejects any write with an epoch lower than the highest seen. This is what makes the *old* leader harmless even if it is still running and still convinced. It converts a correctness disaster into a rejected request.
3. **STONITH / lease expiry with a hard stop.** The old leader must stop acting on its own, without needing to hear from anyone: it self-demotes when it cannot renew its lease within the TTL, and its lease TTL is strictly shorter than the time before a new leader may be elected. Combined with fencing, this closes the window.

A fourth, practically important one: **avoid a partitionable topology for the decision.** Use a single consensus system (etcd/Raft) as the sole source of leadership truth rather than each component inventing its own, and never let a witness/arbiter node be the tiebreaker for a resource it cannot verify - which is why an arbiter-only MongoDB replica set is a trap (`../06-database/answers.md` Q199).

### Q129. Clocks

- **NTP drift.** Ordinary servers are typically within a few milliseconds of true time, but can be tens or hundreds of milliseconds off, and can **step backwards** when corrected. A leap second or a misconfigured NTP source can produce a jump of a second or more.
- **Monotonic versus wall clock.** The monotonic clock only moves forward and is unaffected by NTP adjustments - it is the *only* correct source for measuring durations (timeouts, leases, latency). The wall clock (`System.currentTimeMillis`, `Instant.now`) is for absolute timestamps that humans and other systems must interpret, and it can go backwards. Using the wall clock for a timeout is a real bug: a backwards step makes a lease appear to have more time left than it does.
- **TrueTime** (Spanner) bounds the uncertainty with GPS and atomic clocks and *exposes* it: `TT.now()` returns an interval. Spanner then waits out the uncertainty before committing, which is how it achieves external consistency - it buys linearizability with latency, and it requires hardware most systems do not have.
- **Hybrid logical clocks** combine a physical timestamp with a logical counter, giving timestamps that are close to real time *and* guaranteed to respect causality. This is the practical choice for ordering events across nodes without special hardware, and it is what CockroachDB and several others use.

**Design decisions that depend on clock assumptions:** lease and lock expiry (Q124-125); last-write-wins conflict resolution (a skewed node's writes always win or always lose - this is why LWW plus NTP is dangerous); TTL-based cache and token expiry; scheduled job firing (Q109); ordering by timestamp in a log or event store; and any "happened before" judgement. My rule: **never derive correctness from a wall clock comparison across machines.** Use versions, epochs, sequence numbers or HLCs for ordering, monotonic clocks for durations, and treat wall-clock timestamps as descriptive metadata.

### Q130. Quorum arithmetic

With N replicas, a read quorum R and a write quorum W, `R + W > N` guarantees that any read set intersects any write set, so a read sees at least one replica holding the latest acknowledged write. Common configurations at N=3: `W=2, R=2` (balanced, tolerates one failure on both paths); `W=3, R=1` (fast reads, no write tolerance); `W=1, R=3` (fast writes, fragile reads). Note that `R + W > N` gives you *strong consistency for that key* only if reads also perform repair or read the newest version - and it says nothing about isolation across keys.

**What changes with a second region:**

1. **Latency enters the quorum.** With 3 replicas in region A and 3 in region B, a global `QUORUM` of 4 out of 6 must include at least one remote node, so every write pays a cross-region round trip - 30-80 ms added to every write, forever (Q168). This is the single most important consequence.
2. **Hence `LOCAL_QUORUM`.** Cassandra-style, you require a majority *within the local datacenter* (2 of 3) and replicate asynchronously across regions. Writes stay fast, and you lose the global guarantee: a read in region B may not see a write acknowledged in region A. `R + W > N` now holds only per region.
3. **Failure semantics change.** With `LOCAL_QUORUM`, losing a whole region does not block writes in the other, which is the availability you went multi-region for. With a global quorum, losing a region may block writes if the remainder is not a majority - so node placement matters, and an even split across two regions has no majority at all. Three regions, or two plus a witness, is the minimum for a global quorum that survives a region loss.
4. **Conflicts appear.** Once regions accept writes independently, concurrent writes to one key are possible and you need a resolution policy (Q131).

### Q131. Conflict resolution

| Strategy | How | Use when |
| --- | --- | --- |
| **Last-write-wins by timestamp** | Highest timestamp wins | Data where loss of a concurrent update is acceptable - a user's display preference, a cached denormalization. Dangerous with clock skew (Q129); use an HLC, not a wall clock |
| **Vector clocks / version vectors** | Detect concurrency precisely, surface siblings to the application | You need to *know* a conflict occurred rather than silently lose data - Dynamo-style stores. Cost: metadata growth and the application must resolve |
| **CRDTs** | Types whose merge is commutative, associative and idempotent - counters, sets, registers, sequences | Conflict-free convergence with no coordination: collaborative editing (Q191), presence, distributed counters, shopping carts |
| **Application merge** | Domain logic decides, possibly with the user | The conflict is semantically meaningful - two edits to a document, two changes to an order |

A case for each: LWW for "user changed their avatar in two tabs". Version vectors for a replicated key-value store where losing a write is unacceptable but you cannot merge automatically. A CRDT counter for "likes" across regions (a G-Counter converges without coordination and cannot lose an increment - which LWW absolutely can, and this is the canonical example of LWW being wrong). Application merge for a shopping cart, where the domain answer is usually union-with-max-quantity, or for a document, where the answer may be to ask the user.

The design rule: **choose the strategy before the conflict exists, per data type, and write it down.** The default in most systems is "whatever the database does by default", which is LWW, which silently loses data - and discovering that during an incident is how "we lost customer edits" happens.

### Q132. Global low-latency writes plus a strong uniqueness constraint `[A]`

**The compromise:** separate the two requirements, because they apply to different data.

1. **Partition the namespace and nominate an owner per partition.** Usernames beginning with a given hash range are owned by one region. A registration for a name in another region's range pays one cross-region round trip - but registration is rare, and the *common* writes (posts, updates, activity) stay local. This is the key insight: uniqueness applies to a small, low-volume subset of operations, and only that subset needs to pay.
2. **Reserve-then-confirm.** The uniqueness reservation is a small, strongly-consistent conditional write against the owning partition. Everything else about creating the account is eventual and local. The reservation has a TTL, so an abandoned signup self-heals.
3. **For genuinely global sequences or counters**, use a coordination-free construction: per-region ID ranges (Q127) so ids are globally unique without coordination, and CRDT counters where an approximate global total is acceptable.
4. **Where a real global invariant exists and must be linearizable** - a financial ledger, a regulatory limit - keep a **single-writer region** for that data and accept the latency for those operations only. State the number: "account creation takes 150 ms for users in Asia because it validates against a registry in Europe; posting a message takes 20 ms locally."

**Explaining it to a non-technical stakeholder:** "Some questions can only be answered in one place, because they are about *everyone* - like whether a username is already taken. Answering those needs a round trip to that one place, which is about the time it takes to blink. Everything a user does day to day is answered locally and feels instant. We are choosing to make the rare thing slightly slow so the common thing is fast, and to guarantee we never issue the same username twice - because the alternative is two customers with the same identity, and cleaning that up is worse than 150 milliseconds."

*Hook: a global-versus-local decision you made, and the number you quoted to the business.*

---

## 9. Partitioning, sharding and hotspots

### Q133. Vertical, horizontal, functional - in one system

Take an e-commerce platform:

- **Functional decomposition** - split by capability: catalogue, cart, orders, payments, fulfilment, each with its own datastore. This is the first and most valuable split, because it separates workloads with different scaling profiles and different consistency needs, and it needs no key design at all.
- **Vertical partitioning** - within the product entity, split the narrow hot columns (id, price, stock, status) from the wide cold ones (long description, specifications, marketing copy, media references) into separate tables or stores. The hot table now has far more rows per page and a much smaller working set (Q53).
- **Horizontal partitioning (sharding)** - within the orders table, split rows across shards by `customer_id`, so each shard holds a subset of customers with all their orders co-located.

The order matters: **functional first, vertical second, horizontal last**, because horizontal sharding is the only one that permanently complicates every query and every future migration. A great many teams shard when a functional split or a vertical split would have bought them years (Q148).

### Q134. Shard key selection

The four properties, each with the diagnostic question I ask:

1. **High cardinality.** *"How many distinct values will this have in three years?"* If the answer is in the hundreds, you cannot spread across thousands of partitions. Country code fails this; `customer_id` passes.
2. **Even distribution of both data and traffic.** *"Plot the top 100 values by request volume - how much of total traffic is in the top 1 percent?"* This is the question that finds the celebrity problem before it happens (Q140). Note that data-even and traffic-even are different properties, and traffic is the one that hurts first.
3. **Present in the majority of queries.** *"For each of my top ten queries, do I know the key value?"* If not, that query becomes a scatter-gather across every shard (Q139), and its latency becomes the p99 of the slowest shard. This is the property most often sacrificed and most often regretted.
4. **Immutable, or at least stable.** *"Can this value ever change for an existing row?"* A change means moving the row to a different shard, which is a distributed transaction you do not want. `tenant_id` is usually stable; `region` is not (customers relocate); `status` never qualifies.

A fifth property worth mentioning: **co-location of things read together.** If an order's line items must be fetched with the order, they must share the shard key, which is why the key is often the parent's id rather than the row's own (Q146).

### Q135. Range, hash, directory, geo

| Scheme | Rebalancing | Range queries | Hotspot risk |
| --- | --- | --- | --- |
| **Range** (contiguous key ranges per shard) | Easy - split a range in two, move half. Automatic in systems like HBase, Bigtable, CockroachDB | Native and efficient - a scan hits one or few shards | **High** - sequential or time-based keys write to one shard (Q136); popularity is often clustered |
| **Hash** (hash the key, modulo or ring) | Hard with plain modulo (rehashes everything); solved by consistent hashing with vnodes (Q137) | Impossible without scatter-gather - adjacent keys are on different shards | **Low** for data distribution; still high for a single hot key |
| **Directory / lookup** (an explicit map from key to shard) | **Easiest** - move a tenant, update one row in the map. Arbitrary placement | Depends on the placement you chose | Controllable - you can move a hot tenant to its own shard deliberately |
| **Geo** (partition by region/locality) | Moderate; a customer's move means a cross-partition migration | Good within a region, bad across | Uneven by nature - population and activity vary by orders of magnitude between regions |

My default for multi-tenant systems is **directory-based**, because the operational flexibility is enormous: you can place a large tenant alone, move a noisy one, and migrate one tenant at a time with a per-tenant cutover. The cost is a lookup service that must be highly available and cached, and which becomes a piece of infrastructure you own.

For high-volume uniform data, **hash with virtual nodes**. For time-series, **range on time** (which is time partitioning, and the hotspot on the newest partition is a feature, not a bug, because that is where the cache is).

### Q136. A monotonically increasing shard key `[T]`

What happens: with range partitioning, all new writes land in the last partition, so one shard absorbs 100 percent of the write traffic while the others are idle. You have bought the complexity of sharding and none of the write scalability. With hash partitioning the writes spread, but you have lost range scans, and the *reads* still concentrate if recent data is what people read.

Why it is tempting anyway: auto-increment ids and timestamps are the natural primary keys; they give perfect index locality on a single node (`../06-database/answers.md` Q5); they make "recent items" queries trivial; and they are already in the schema.

What to use instead, depending on the requirement:

- **Hash of the id** as the partition key, keeping the id as the sort key. Writes spread; point lookups still work; range-by-id does not.
- **A prefix that spreads, plus time inside the partition**: `partition = hash(entity_id) % N`, `sort = (timestamp, id)`. This is the standard wide-column design - many parallel time series rather than one.
- **Salting / write sharding**: prefix the key with `random(0..N)` and read all N prefixes for a range query. Crude but effective when writes must spread and range reads are rare and can afford a fanout of N.
- **Bucketed time**: partition on `(entity_id, time_bucket)` so a single entity's unbounded history is split into bounded partitions (`../06-database/answers.md` Q201).

The framing: a monotonic key optimizes for the single-node case and is exactly wrong for the distributed case. Recognizing that inversion is the point of the question.

### Q137. Consistent hashing with virtual nodes

**Why plain modulo fails:** `shard = hash(key) % N`. Change N from 10 to 11 and roughly 10/11 of all keys map somewhere new. Every cache entry is a miss, every stored row is in the wrong place, and the migration is "move almost everything". Adding a node becomes an all-or-nothing project rather than an operation.

**Consistent hashing:** place both nodes and keys on a hash ring; a key belongs to the first node clockwise. Adding a node claims only the arc between it and its predecessor, so roughly `1/N` of keys move, and only from one neighbor. Removing a node hands its arc to its successor.

**Why virtual nodes:** with one point per node, arcs are unequal - the variance is high, so with 10 nodes some own twice their share. Also, adding a node relieves only *one* neighbor, so the load is redistributed unevenly. Giving each physical node many points on the ring (**vnodes**) makes the distribution converge: with 100-256 vnodes per node the imbalance is a few percent, and adding a node takes a small slice from *every* existing node rather than half from one.

**How many:** 100-256 per physical node is the usual range - enough to smooth the distribution, not so many that the ring metadata and the per-vnode overhead (open files, compaction threads, repair units) become a problem. Cassandra's default moved down to 16 with the token-allocation algorithm precisely because high vnode counts hurt repair and availability.

**When a node is added:** it takes ownership of its vnodes' arcs; data streams from the previous owners; during the transfer both may serve (reads go to the old owner until handoff completes, or the system reads from both and reconciles). Nothing else moves. With replication factor R, the arcs' successors also change, so R nodes participate per arc - which is why a topology change is a background operation measured in hours for large datasets, and why it must be rate-limited so it does not degrade live traffic.

### Q138. Resharding a live system

The sequence, with the two cutover points marked:

1. **Prepare.** Add the new shards, empty. Ensure every write path goes through a routing layer (a library or a proxy) that reads shard mapping from a config store rather than from hard-coded modulo. If this is not true, that is the first project.
2. **Dual-write / start replication.** For the key ranges being moved, writes go to both the old and new shard. Implementation choices: application-level dual write (simple, and drift-prone), or - much better - **log-based replication** from the old shard to the new (CDC), which cannot miss a write and is replayable.
3. **Backfill.** Copy historical rows in batches, rate-limited, restartable, with progress tracked. Order does not matter if writes are idempotent and version-checked.
4. **Verify.** Row counts, checksums per key range, and a sampled row-by-row comparison. Also compare live query results from both sides for a period. Do not proceed on optimism.
5. **READ CUTOVER.** Flip reads for the moved ranges to the new shard, one range at a time, with an instant flag-based rollback. This is the first reversible cutover point; if latency or correctness looks wrong, flip back - the old shard is still being written.
6. **Bake.** Hours to days at full read traffic on the new shard, with the old one still receiving writes.
7. **WRITE CUTOVER.** Stop dual-writing; the new shard is authoritative. **This is the point of no return** - after it, the old shard's data is stale and rolling back means replaying the delta. Do it per range, in a low-traffic window, with a short write pause (or a brief 503 with retry) for the affected keys if strict correctness demands it.
8. **Decommission** after a retention period long enough to cover the worst rollback you can imagine - a week, not an hour.

The two things that make this survivable: **per-key-range granularity** (so the blast radius of any step is a fraction of the users) and **idempotent, version-checked writes** (so replays and overlaps are harmless). The thing that makes it impossible: not having a routing indirection layer, which is why I would build one before I needed it.

### Q139. Cross-shard queries

Three strategies:

1. **Scatter-gather.** Query every shard, merge in the coordinator. Cost: the latency is the **maximum** of all shards, not the average, so with 32 shards you are exposed to the p99.97 of a single shard - one slow shard sets your latency (Q10). Resource cost is multiplied by the shard count, so a scatter-gather at high QPS consumes the whole cluster. Pagination and sorting are painful: to return the top 20 globally you must fetch the top 20 from each shard and merge, and `OFFSET 1000` requires fetching 1,020 rows from every shard.
2. **Denormalize / maintain a global secondary index.** Keep a separate structure partitioned by the query's key, updated on write (Q143). Cost: write amplification, and eventual consistency between the index and the data - so the index can return a key whose row has changed or gone.
3. **Move the query out of the transactional store.** Feed a search index or a warehouse from the log and answer cross-shard analytical and search queries there (Q65). Cost: staleness and a second system, but this is the honest answer for anything that is really a reporting query.

The honest cost summary I would give: scatter-gather is fine for low-QPS admin and internal queries and unacceptable on a hot path; global indexes work but you now maintain a second partitioned dataset with its own drift; and the real answer for most "we need to query across shards" requirements is that the query belongs in a different store. If a *high-QPS user-facing* query needs cross-shard access, the shard key is wrong (Q134, property 3).

### Q140. A celebrity key at 40 percent of traffic `[T]`

Four mitigations:

1. **Read replicas for the hot key only.** Replicate that key's partition to N nodes and spread reads. Effective and cheap when the hot key is read-heavy, which it usually is.
2. **Cache it aggressively, in front and locally.** A per-instance in-process cache of the top-K keys with a 1-5 second TTL absorbs almost all of it, because 40 percent of traffic for one key means near-perfect cache efficiency (Q69). Add single-flight so a miss does not stampede (Q73).
3. **Split the key.** Write sharding: store the value under `key:0..N` and have readers pick one at random (for reads of a replicated value) or writers pick one and readers merge (for counters and append-only lists). This is the escrow/sub-key technique (Q92, Q192), and it works when the value can be decomposed.
4. **Dedicated capacity.** Move the hot key (or hot tenant) to its own shard or its own cluster, which directory-based partitioning makes easy (Q135). Also the answer for a hot *tenant* rather than a hot key.

Plus one that is not a mitigation but a design change: **change the read path** so the hot object is served from the CDN as a static object with a short TTL, taking it out of the datastore entirely. For a genuinely public hot object this is the strongest answer.

**What I would ship first:** the local cache plus single-flight, because it takes hours, needs no data migration, and handles the next celebrity automatically. Then measure, then decide between splitting and dedicated capacity based on whether the traffic is reads or writes.

### Q141. Detecting hotspots before they hurt

**Metrics:** per-partition (not aggregate) request rate, bytes and latency; per-partition storage size; and the **skew ratio** - hottest partition over mean partition - which is the single number to put on a dashboard. Aggregate utilization hides everything: a cluster at 30 percent average with one node at 95 percent looks healthy and is not (`../06-database/answers.md` Q207 for the DynamoDB version of exactly this).

**Sampling approach:** you cannot record a counter per key at scale, so use a **heavy-hitters sketch** - Count-Min Sketch or Space-Saving - maintained per node over a sliding window, reporting the top-K keys by request count and by bytes. That is O(K) memory and gives you the actual key names, which is what you need to act. Sample full request logs at a low rate as a cross-check, and tag them with the partition id so the analysis is a group-by rather than a guess.

**The alert:** skew ratio above a threshold (say 3x) sustained for 10 minutes, and separately, any single key exceeding a fixed percentage of a partition's capacity. Route it with the offending key names attached, because an alert saying "skew detected" without the key is not actionable.

The organizational half: hotspots are frequently created by a product change (a promotion, a featured item, a new large customer onboarded onto a shared shard), so the capacity review for any launch should include "which partition will this concentrate on".

### Q142. Multi-tenant partitioning

| Model | Isolation | Cost | Best for |
| --- | --- | --- | --- |
| **Tenant per shard/database** (silo) | Strong - noisy neighbors impossible, per-tenant backup and restore, easy residency compliance | High - per-tenant overhead, and migrations must run N times (`../06-database/answers.md` Q255) | Enterprise customers, regulated data, very large tenants |
| **Shared shards, tenant column** (pool) | Weak - enforced only by query correctness and quotas | Lowest - one schema, one migration, best density | Long-tail small tenants, self-serve tiers |
| **Bridge** - shared schema, tenant-aware routing, with the ability to promote a tenant to its own shard | Configurable per tenant | Middle | The pragmatic default for a SaaS platform |

The **giant-tenant problem** is the one that decides the architecture. Tenant sizes in a real SaaS span 4-6 orders of magnitude: the largest tenant may be bigger than the other 5,000 combined. Consequences: it will not fit on a shared shard; its queries will dominate; its data volume breaks per-shard assumptions; and it cannot be migrated using the same procedure as everyone else because its migration takes hours.

So the design must include, from day one: **directory-based routing** so any tenant can be placed anywhere (Q135); **per-tenant quotas** so a large tenant cannot consume a shared shard (Q231); a **promotion path** (move tenant X from a shared shard to a dedicated one) that is a documented, tested, rehearsed operation; and per-tenant capacity metrics so you see a tenant outgrowing its home before it hurts the neighbors. Retrofitting the promotion path during an incident is a bad week.

### Q143. Local versus global secondary indexes

**Local index** (per partition): each partition indexes its own rows. Writes are cheap - the index entry goes in the same partition, in the same transaction, atomically. Reads by the index require the partition key too; without it, you scatter-gather across all partitions (Q139). DynamoDB's LSI is this, and it is why an LSI must share the table's partition key.

**Global index** (partitioned independently by the indexed attribute): a read by the indexed attribute goes to exactly one partition of the index - a single-partition lookup, which is what you wanted. But the write must update a *different* partition from the row, so it is a cross-partition write: not atomic, done asynchronously, and therefore eventually consistent. DynamoDB's GSI is this, and it has the specific failure mode that if the GSI's write capacity is exhausted, back-pressure propagates to the **base table** and rejects writes (`../06-database/answers.md` Q206).

| | Write cost | Read cost |
| --- | --- | --- |
| Local | One partition, atomic, transactional | One partition if you know the partition key; N partitions if you do not |
| Global | Two partitions, asynchronous, eventually consistent, extra capacity | One partition |

The design consequence: use local indexes for alternate sort orders within an entity's data; use global indexes for genuine alternate access paths; and treat a global index as a derived store with a lag, meaning **never enforce uniqueness or an invariant through it** - it may not yet contain the row that would have conflicted.

### Q144. Partitioning a stateful stream job

The rule: **the job's partitioning must match the key of its state.** A stateful operator (an aggregation, a windowed count, a join) keeps state per key, and that state lives on the node processing that key's partition. So:

- **Co-partition the input with the state key.** If you aggregate per `user_id`, the input topic must be partitioned by `user_id`. Otherwise the framework must repartition (a shuffle through an internal topic), which costs a network hop, a write and a read per record.
- **Co-partition both sides of a join.** A stream-stream join on `order_id` requires both topics partitioned by `order_id` with the *same number of partitions and the same partitioner*. If they differ, one side is shuffled; if the partitioner differs subtly (a different hash function between a Java producer and a Python one, say), the join silently misses matches - a genuinely nasty bug.
- **Co-partition the changelog.** Kafka Streams' state stores are backed by changelog topics partitioned identically, which is what makes recovery possible: a new instance taking over partition 7 replays partition 7 of the changelog.

Why: state cannot be shared across nodes cheaply, so the framework's model is "the key's partition determines the node determines the state". Breaking that means either a shuffle or a distributed lookup, and both are order-of-magnitude costs.

The operational consequence: **partition count becomes a hard ceiling on parallelism** (Q145), and changing it invalidates the existing state, because key K now maps to a different partition than the state that describes it. Repartitioning a stateful job means a rebuild from the source with a new topic, not a config change (`../03-microservices/answers.md` Q40).

### Q145. Partition count that can never change `[T]`

Systems with this property (or near enough): **Kafka** - you can add partitions, but existing keys rehash to different partitions, breaking per-key ordering and invalidating any co-partitioned state (Q144), so in practice topics with keyed semantics are fixed. **Kinesis** - shards can be split and merged, but the sequence-ordering guarantee across a resharding boundary needs care. **Any hash-modulo scheme** without consistent hashing. **Stateful stream applications**, as above. **DynamoDB GSI key schemas** and any table whose partition key must change - the change is a table rebuild.

Designing around it:

1. **Over-provision partitions from the start.** Partitions are cheap to have and expensive to add: 3-10x the parallelism you need today. The limit is per-broker overhead (open file handles, replication threads, controller metadata) and rebalance duration, so hundreds to a few thousand per topic is fine, tens of thousands is not.
2. **Decouple partitions from consumers.** Consumers scale up to the partition count, so partition count sets your maximum consumer parallelism - a second reason to over-provision.
3. **Use a partition count with clean factors** (a power of two, or a highly composite number like 60 or 360) so that a future "split each partition into two" maps keys deterministically.
4. **Route with an indirection layer** so the mapping from key to partition is a decision you control, not a modulo baked into producers - then a future change is a config change plus a migration, not a rewrite.
5. **When change is unavoidable, do it as a new topic with dual publication and a consumer migration**, the same shape as the resharding sequence (Q138) - not as an in-place mutation.

### Q146. Data locality and co-location

**How you keep related data together:** make the shard key the *root entity's* identity, and include it in every child's key. An order and its line items share `order_id`; a customer, their addresses and their preferences share `customer_id`; a conversation and its messages share `conversation_id`. In a wide-column or key-value store this is explicit - the partition key is the root, the sort key distinguishes the children, so one query reads the whole aggregate. In a relational sharded system it means every child table carries the parent's shard key as a column, even when it is redundant, and every query includes it.

This is really the DDD aggregate boundary expressed physically: the aggregate is the unit of co-location, and the unit of transaction.

**What breaks the guarantee:**

1. **An entity with two natural parents.** A message belongs to a conversation and to a sender; you can co-locate with one, not both. You choose based on the dominant access pattern and pay a fanout for the other (or maintain a second, differently-partitioned copy - Q143).
2. **Many-to-many relationships.** A user in many groups: neither side can co-locate the other.
3. **Unbounded children.** A partition holding one entity's entire unbounded history eventually exceeds the partition size limit and becomes the hot partition. The fix is bucketing - `(conversation_id, month)` - which deliberately breaks locality to bound partition size.
4. **A shard key that changes** (Q134, property 4) - the row must move, and moving it out of its aggregate breaks locality until the move completes.
5. **Cross-aggregate operations** - a transfer between two accounts on different shards. That is a saga (Q121), and it is the price of the partitioning.

### Q147. Rebalancing traffic versus rebalancing data

**Rebalancing traffic** - adding replicas, adding cache capacity, routing reads elsewhere, moving a workload to a different time - is cheap, fast, and reversible. **Rebalancing data** - moving partitions between nodes, changing the shard key, resharding - is slow, risky and often irreversible (Q138).

So the diagnostic is: **is the problem reads or writes, and is it capacity or distribution?**

The cheap answer is enough when:

- The hotspot is read-driven. Replicas and caches solve it entirely (Q140), and they can be added in an afternoon.
- The imbalance is in *load* rather than in *data volume* - one partition gets more requests but is not larger. Traffic can be steered; data need not move.
- The imbalance is transient (a promotion, a launch, a batch job) and will pass. Moving data for a two-day event is a bad trade.
- The workload can be time-shifted: run the heavy job at 03:00 and the peak problem disappears.

The cheap answer is *not* enough when the hot partition is write-bound (replicas do not help writes), when a partition is approaching a hard size or throughput ceiling, or when the skew is structural - a shard key that will always concentrate (Q136). Those need data movement, and the sooner they are recognized the cheaper the movement is.

My working rule: **exhaust traffic-side options first and instrument well enough to know when they are exhausted**, because data movement is the one operation that can turn a performance problem into an outage.

### Q148. At 90 percent of the single-database ceiling `[A]`

The options, in the order I would evaluate them - cheapest and most reversible first:

1. **Verify the ceiling is real.** Is it CPU, IO, memory, connections, lock contention or a single query? A database at 90 percent CPU because of one unindexed query has no capacity problem (`../06-database/answers.md` Q3). This step is not a formality; in my experience it resolves the situation outright more often than not.
2. **Query and index optimization, plus connection pooling.** The top ten queries by total time usually account for most of the load. Reducing the biggest by 50 percent buys a year. Connection pool right-sizing and PgBouncer often buy more than an instance upgrade.
3. **Vertical scaling.** Doubling the instance is a maintenance window and a bill, and it buys 12-18 months. It is boring, it is instant, and it is almost always the correct next step because it buys time to do the rest properly. Refusing to scale up because sharding is "the real fix" is how teams end up sharding in a panic.
4. **Offload reads.** Read replicas for read-heavy traffic, a cache tier for hot objects, and move reporting off the primary entirely (Q65). If the workload is 95 percent reads, this *is* the answer and everything below is unnecessary.
5. **Offload writes that do not belong.** Move high-volume, low-value writes - audit logs, events, metrics, sessions - to stores designed for them. This is frequently 50 percent of the write volume and none of the business value.
6. **Vertical partitioning and archival.** Split hot columns from cold (Q133), and move data older than the retention boundary to cold storage (Q62). A 4 TB database is often 400 GB of hot data.
7. **Functional decomposition.** Split by capability into separate databases. Each is independently scalable, and this is a service boundary conversation as much as a data one - which makes it a bigger project but one with wider benefits.
8. **Horizontal sharding.** Last, because it is permanent and it complicates everything afterwards. If we get here, the prerequisites are a routing indirection layer, a shard key validated against the top ten queries (Q134), and the migration plan from Q138.

**Including "not sharding":** the honest recommendation in most cases is steps 1-6 plus a monitoring commitment, with a decision checkpoint - "we will revisit at 70 percent of the new ceiling, or when write volume doubles". I would also state the thing nobody says: sharding a 3 TB database is usually a mistake, because a single modern instance handles far more than teams assume, and the complexity is paid every day thereafter by every engineer.

*Hook: a scaling decision where the boring answer was right, and the growth curve that justified it.*

---

## 10. Reliability, failure modes and graceful degradation

### Q149. Finding single points of failure in two minutes

The method: **walk every box and arrow in the diagram and ask "if this one thing stops, what happens?"** Then check five specific categories that are almost always missed:

1. **Anything with a count of one** - one primary, one leader, one coordinator, one instance of a "small" service, one NAT gateway, one Redis node holding state.
2. **Shared dependencies that appear in every path** - the auth service, the config service, the feature-flag service, the discovery service, DNS, the certificate authority. These are the ones that turn a partial failure into a total one, and they are usually drawn as a small box at the side.
3. **The control plane** - the deploy pipeline, the secret store, the container registry, the autoscaler. If the data plane cannot survive their absence, they are SPOFs with a longer fuse (Q158).
4. **Anything not actually redundant despite appearances** - three instances in one AZ; two replicas that share a storage volume; an active-passive pair whose failover has never been tested; a "cluster" behind a single load balancer in a single subnet.
5. **The humans and the procedures** - one person who knows how to fail over, one runbook that assumes a tool that no longer exists.

The two-minute version in an interview: point at each component and say "redundant, redundant, single - and here is what happens", then name the one that would surprise the interviewer, which is usually the config or auth dependency.

### Q150. Redundancy models

| Model | Failover time | Cost | Notes |
| --- | --- | --- | --- |
| **Active-active** (all instances serving) | Zero to seconds - the load balancer stops sending traffic to the failed unit | 100 percent+ of capacity duplicated, but all of it is doing useful work; needs N+1 headroom | Requires statelessness or shared state; for writes across regions it introduces conflicts (Q171) |
| **Active-passive** (standby idle, promoted on failure) | Seconds to minutes - detection, promotion, DNS/route change, client reconnection, cache warm-up | Pays for idle capacity; simpler correctness (single writer) | The standby must be *exercised*, or the failover will not work when you need it |
| **N+1 / N+2** (spare capacity within a pool) | Zero for the failure itself | 1/N extra | The standard for stateless fleets; N+2 when a deploy also consumes a unit |
| **Warm standby scaled down** | Minutes - scale up plus warm-up | Fraction of full | The pragmatic multi-region choice (Q161) |

The subtleties worth stating: active-active's failover time is only near-zero if capacity headroom exists - failing over 50 percent of traffic onto a fleet running at 70 percent utilization simply moves the outage. And active-passive's real failover time is dominated not by promotion but by everything after it: connection pools reconnecting, caches cold, and the first minutes of traffic hitting an unwarmed system (Q174).

### Q151. Blast radius

**Definition:** the set of users, tenants, data or functionality affected by a single failure, deployment, or operator action. It is measured as a *fraction*, not a yes/no.

Four techniques that shrink it:

1. **Cells** (Q152). Partition the entire stack into independent copies, each serving a subset of users. A failure inside a cell affects `1/N` of users, and cells share nothing - not a database, not a cache, not a deployment.
2. **Shuffle sharding** (Q152). Assign each tenant a random *subset* of resources, so any single resource failure affects only the tenants sharing it, and no two tenants share the same full set.
3. **Bulkheads within a service** (Q155) - separate thread pools, connection pools and queues per dependency or per tenant class, so exhaustion in one does not consume the whole process.
4. **Staged deployment** - canary, then one cell, then one region, then the rest, with automated rollback (Q97). Most outages are caused by change, so the deployment blast radius is the one that matters most in practice.

Two more worth naming: **static stability** (Q158), which shrinks the blast radius of control-plane failures to zero for the data plane; and **isolating the control plane from the data plane** so an operator mistake in one cannot take out the other.

### Q152. Cells and shuffle sharding, with numbers

**Cell-based architecture.** The whole stack - load balancer, services, database, cache - is replicated into independent cells. A thin routing layer maps a user or tenant to a cell. Cells never talk to each other. With 10 cells, any cell-level failure affects 10 percent of users; a bad deploy rolled to one cell affects 10 percent; a poison workload from one tenant is contained to its cell. What you buy is a *bounded* worst case; what you pay is per-cell overhead (10 small databases cost more than one big one), a routing layer that must itself be extremely reliable and simple, and the loss of cross-cell queries.

**Shuffle sharding.** Instead of assigning each tenant to one shard, assign each tenant a random combination of `k` of `n` resources. With `n = 8` workers and `k = 2`, there are `C(8,2) = 28` distinct pairs. If one worker is poisoned by a bad tenant, the tenants affected are those whose pair includes it - `7/28 = 25 percent` share *one* of their two workers, but only the poisoning tenant itself has both compromised. Everyone else still has one healthy worker, so with retries they see degradation, not failure.

Scale it up: `n = 100`, `k = 5` gives `C(100,5) ≈ 75 million` combinations. The probability that another tenant shares *all five* workers with a given tenant is essentially zero, so a single bad tenant can fully impair only itself while touching 5 percent of the fleet. That is the striking number: **with 100 workers and 5 per tenant, one bad actor damages one tenant, not one twentieth of them.**

The requirement that makes it work is that clients retry across their assigned subset, and that the assignment is stable per tenant so the analysis holds.

### Q153. A retry that improved testing and caused an outage `[T]`

The mechanism, precisely:

In testing, failures were **independent and rare** - a dropped packet, one unlucky instance. A retry converts a 0.1 percent failure rate into 0.0001 percent, and costs 0.1 percent extra load. Excellent.

In production, failures are **correlated and load-induced**. The dependency slows down because it is near saturation. Requests time out. Every timed-out request is retried, so the offered load increases by the retry multiplier at exactly the moment the dependency has no capacity. More requests time out, so more are retried. The dependency is now serving a workload that is mostly retries of requests whose callers have already given up - pure waste - and it cannot recover even after the original trigger passes, because retries now sustain the overload. That is a **metastable failure** (Q26).

The multiplier is worse than it looks because it composes: with three layers each retrying twice, one user request becomes up to `3^3 = 27` requests at the bottom. And because retries are usually issued immediately or with a short fixed delay, they arrive synchronized, producing a spike rather than a spread.

The controls: **retry budgets** (retries capped at ~10 percent of total requests, so amplification is bounded at 1.1x regardless), **exponential backoff with full jitter**, **circuit breakers** so a failing dependency stops receiving traffic at all, **retry only at one layer**, **deadline propagation** so a retry is not issued when the original deadline has already passed, and **shedding retries before first attempts** at the server (Q94). Marking retries with a header is what makes that last one possible.

### Q154. Timeout budgets and deadline propagation

**Setting them so the total is bounded:** work backwards from the user-facing SLO. If the API must respond in 1,000 ms, then:

```
client timeout        1200 ms   (must exceed the server's, or the client gives up on work that will succeed)
  edge/gateway         1000 ms
    service A           900 ms
      service B         400 ms   (parallel with C)
      service C         400 ms
        database        200 ms
      retry budget      one retry of B or C fits inside the 900 ms
```

The rules: each layer's timeout is strictly less than its caller's, minus the time already spent and minus enough room for whatever it must do afterwards. Retries must fit *inside* the budget, which means a 400 ms call with one retry needs an 850 ms parent, not 450. And a serial chain of five 400 ms calls cannot live inside a 1,000 ms budget, which is a design finding, not a configuration problem.

**Deadline propagation** replaces the static arithmetic with a dynamic one: the caller passes an absolute deadline (gRPC does this natively; over HTTP it is a header carrying a timestamp or remaining milliseconds), and each hop computes its own remaining budget from it. Then a call that has already consumed 800 ms of a 1,000 ms budget gives its downstream 200 ms, not the configured 400 - and any hop that sees a deadline already passed **fails immediately without doing the work**. That last behavior is the biggest win: it eliminates all the doomed work that a saturated system would otherwise perform for clients who have gone away, which is precisely the work that prevents recovery.

I would also insist on the two properties people forget: the deadline must be enforced at the *resource* (a database `statement_timeout`, a socket timeout), not just in application code, and cancellation must actually propagate so an abandoned request stops consuming a connection.

### Q155. Bulkheads

Each contains something different:

| Bulkhead | Contains |
| --- | --- |
| **Separate thread pools per dependency** | A slow dependency can exhaust only its own pool, so requests that do not need it still get threads. The classic Hystrix model |
| **Separate connection pools** | One dependency's saturation cannot consume all database or HTTP connections |
| **Semaphore / concurrency limit per dependency** | Cheaper than a thread pool (no context switch cost) and bounds in-flight work; the right choice in async code where a thread pool is meaningless |
| **Separate queues per consumer or tenant class** | A backlog for one workload does not delay another (Q108) |
| **Separate deployments (process isolation)** | A memory leak, a crash, a CPU-hogging code path, or a bad deploy is contained to one workload. Also contains resource contention that in-process bulkheads cannot |
| **Separate clusters/cells per tenant tier** | Contains a noisy tenant, and lets you give different tiers different SLOs (Q152) |

The design guidance: bulkhead by **failure domain**, which usually means per downstream dependency and per workload class (interactive versus batch versus a specific large tenant). Sizing matters - the sum of the pools must not exceed what the process can support, and each pool must be large enough for its dependency's Little's Law requirement (Q24), or the bulkhead itself becomes the bottleneck.

The upgrade path worth stating: in-process bulkheads protect against a slow dependency; only *process* isolation protects against a bug in your own code. When a single service serves both a latency-critical interactive path and an expensive batch path, splitting the deployment is usually worth more than any amount of pool tuning.

### Q156. Twelve dependencies at 99.9 percent `[T]`

`0.999^12 = 0.988`, so 98.8 percent - about **8.6 hours of downtime a month**. Adding dependencies multiplies unavailability: twelve "three nines" services compose into barely "two nines".

Designing so the answer is wrong:

1. **Reclassify.** Most of those twelve are not *hard* dependencies (Q163). If ten of them are soft (the page renders without recommendations, without the loyalty balance, without the review summary), the availability of the critical path is `0.999^2 = 99.8 percent`, and the rest degrade features rather than failing requests. This single move is worth more than everything else combined.
2. **Cache with serve-stale.** A dependency whose last known answer is usable for minutes is effectively far more available than its own SLO: `stale-if-error` converts an outage into staleness (Q76).
3. **Fallbacks and defaults.** A static default, a cached value, an empty state that the UI handles gracefully. Each one converts a multiplication into an addition of degradation.
4. **Remove dependencies from the synchronous path.** Anything that does not affect the response should be an event, not a call (Q99). Twelve synchronous calls in one request is itself the finding.
5. **Parallelize what remains** so latency does not also multiply, and hedge the slow ones (Q10).
6. **Retries with budgets** raise the effective availability of a transient-failure dependency substantially - but only for independent failures, not correlated ones (Q153).

The sentence to say: **availability composes multiplicatively for hard dependencies and additively-in-degradation for soft ones, so the architecture question is how few hard dependencies the critical path can have.**

### Q157. Tiered fallback for a product page with six sources

| Source | Tier | Failure behavior |
| --- | --- | --- |
| Product core (name, images, description) | **Critical** | No fallback possible. If this is unavailable, return 503 for the page. Mitigate with a cache and a CDN so its effective availability is very high |
| Price | **Critical, with a bounded fallback** | Serve a cached price with an "as of" freshness bound (say 5 minutes). Beyond that, show the product without a price and disable purchase, rather than showing a wrong price - a wrong price is a legal and financial problem |
| Inventory / availability | **Important, degradable** | Fall back to a cached value, then to "check availability at checkout". Never block the page |
| Reviews and ratings | **Soft** | Cached, then omitted. The section disappears |
| Recommendations | **Soft** | Cached, then a static popular-items list, then omitted |
| Personalization (recently viewed, loyalty) | **Soft** | Omitted silently |

The mechanics that make it real:

- **Parallel fetch with per-source timeouts and per-source circuit breakers**, each bounded well inside the page budget, so a slow source costs its timeout and nothing more.
- **The page renders from whatever arrived.** Partial data is the normal case, not an error path, which means the template and the API contract must both treat every soft field as optional from day one - retrofitting that is the hard part.
- **Degradation is visible in telemetry**: a per-source "served degraded" counter, so a silently missing recommendations panel produces an alert rather than a slow decline in conversion nobody attributes.
- **The purchase path has its own, stricter rules**: at checkout, price and inventory become strictly consistent reads with no fallback, because that is where correctness matters (Q14). Degradation is acceptable while browsing and not while transacting - and drawing that line explicitly is the answer.

### Q158. Static stability

**Definition:** the system continues to operate correctly using its existing state when its dependencies - particularly control-plane dependencies - are unavailable. It does not need to *change* anything to keep working, and it does not fail because it cannot learn something new.

**How you design a control-plane failure so the data plane keeps serving:**

1. **The data plane never calls the control plane on the request path.** Configuration, routing tables, feature flags, service discovery results, authorization policies and certificates are pushed to or cached by the data plane, and used from local state.
2. **Cached state has no hard expiry on the failure path.** If the config service is down, keep using the last known good configuration indefinitely rather than expiring it and failing closed. This is the crucial inversion: the safe default is *stale*, not *absent*. Alert loudly, but keep serving.
3. **Pre-provision capacity rather than depending on scaling.** The canonical example: an active-passive failover that relies on autoscaling the passive side is not statically stable, because the control plane that scales it may be the thing that is broken. Run the standby at full size, and take the cost.
4. **Fail static, not closed.** If the health-checking system stops reporting, keep the last known target set rather than assuming everything is unhealthy (Q87). If the flag service is unreachable, use the last known flag values, and ship sane compiled-in defaults for the first boot.
5. **The recovery path must not depend on the thing that is broken.** A deploy pipeline that needs the service it deploys, or a secret store that needs the network it configures, is a circular dependency that turns an outage into a long outage.

The single test I would apply to a design: **if the entire control plane vanished for an hour, would the data plane keep serving existing traffic?** If not, the control plane's availability is silently your availability.

### Q159. Gray failure, partial partitions, slow nodes

**Gray failure** is degradation the system's own health checks do not see: a node passing its liveness probe while returning errors for 30 percent of real requests, or a disk that is slow but not failed, or a process that serves `/health` from a thread pool that is not the one serving traffic. The defining characteristic is **differential observability** - the component believes it is healthy, its monitoring agrees, and its clients disagree. That is why client-side metrics matter more than server-side ones for detection.

**Partial partitions** are worse than full ones: A can reach B, B can reach C, A cannot reach C. Now A and B disagree about C's state, health checks give contradictory answers depending on the observer, and consensus systems can flap - electing and re-electing leaders as different subsets of nodes reach different conclusions. Quorum-based systems are designed for symmetric partitions and behave badly under asymmetric ones.

**Why a slow node is worse than a dead one:**

- A dead node is detected and removed in seconds; a slow node stays in rotation and keeps receiving its share of traffic (Q85).
- Every request routed to it consumes a caller's thread, connection and deadline for the full timeout, so one slow node in twenty can occupy a large fraction of the *callers'* capacity - the damage is to the healthy nodes' clients.
- Retries land on it again, and hedged requests double its load.
- It poisons the p99 of the whole service, and it does so without producing an obvious error signal, so it is often diagnosed hours late.

Defenses: outlier detection based on comparative latency, not thresholds; concurrency limits per backend; hedged requests; client-perceived SLIs as the primary alerting signal; and a bias toward "fail fast and loudly" over "degrade quietly" in components you write - a process that cannot serve properly should exit.

### Q160. Chaos experiments against my own design

I would run them in order of "most likely to reveal something", not "most dramatic":

1. **Kill one instance of every stateless service** during traffic. Verifies health checks, connection draining, retry behavior and that nothing held local state. Should be a non-event; often is not.
2. **Add 500 ms of latency to one dependency**, then to one *instance* of a dependency. The second is the gray-failure test (Q159) and finds missing outlier detection and unbounded timeout budgets.
3. **Fail the cache tier entirely** (Q76). This is the experiment that most often reveals a system that cannot survive without its cache.
4. **Fail over the database primary.** Measures real failover time end to end, including connection pool recovery and application error handling - which is almost never what the documentation says.
5. **Make the control plane unavailable** - config service, flag service, discovery, secret store - and verify the data plane keeps serving (Q158).
6. **Saturate a dependency to the point of timeouts** and observe whether retry amplification appears (Q153). This is the one that predicts your next real outage.
7. **Partition one AZ** from the others, including partial and asymmetric partitions if the tooling allows.
8. **Fill a disk, exhaust a connection pool, exhaust file descriptors.** Resource exhaustion produces different (usually worse) behavior than a clean failure.
9. **Replay a poison message** and verify the DLQ path, attempt cap and alerting (Q103).

The framing that matters: chaos engineering is a **hypothesis test**, not vandalism. Each experiment is written as "we believe X will happen; if it does not, that is a finding", run in business hours with an abort switch, starting in staging and moving to a small production cell (Q152). And the value is mostly in the first few experiments - the basics fail far more often than the exotic scenarios.

### Q161. Disaster recovery models

| Model | RPO | RTO | Cost | What runs in the second site |
| --- | --- | --- | --- | --- |
| **Backup and restore** | Hours (last backup) | Hours to days | Lowest - storage only | Nothing. Infrastructure created on demand |
| **Pilot light** | Minutes (continuous replication) | Tens of minutes to hours | Low - a replicating database and templates | The data layer, minimal and small; compute is off |
| **Warm standby** | Seconds to minutes | Minutes | Medium - a scaled-down full stack | Everything, at reduced capacity; scale up on failover |
| **Multi-site active-active** | Near zero | Near zero | Highest - full duplicate capacity, plus conflict handling | Everything, serving traffic |

The realities that separate a plan from a document:

- **Restore time scales with data volume and is usually underestimated by an order of magnitude.** 5 TB from object storage at a realistic 200 MB/s is ~7 hours before the application starts, plus index rebuilds and cache warm-up. If the stated RTO is 2 hours, backup-and-restore does not meet it, whatever the plan says.
- **Warm standby's RTO is dominated by scale-up and warm-up**, not by promotion - so a statically stable, full-size standby (Q158) is the version that actually hits a short RTO.
- **RPO is set by the replication mode**, not by the DR model: asynchronous replication gives you seconds-to-minutes and a data-loss window equal to the lag at the moment of failure; only synchronous replication gives RPO zero, and it charges every write forever (Q11).
- **The failover of dependencies is the hard part** - DNS, certificates, third-party allowlists, secrets, message brokers with their own state, and anything that hard-codes a region (Q174).

My recommendation for most systems: warm standby in a second region for the data layer with pilot-light compute, tested monthly, plus honest documentation of the resulting RPO and RTO. Active-active only when the business case justifies the conflict-handling complexity (Q167).

### Q162. A backup never restored `[T]`

The three ways it is probably broken:

1. **It does not contain what you need.** The database is backed up but not the object storage it references, or not the schema-migration history, or not the secrets and certificates needed to start, or not the message broker's state, or not one of the four databases (someone added a service and nobody updated the backup job). Restoring gives you a system that cannot start.
2. **It is not readable.** The backup ran, exited zero, and wrote a corrupt or empty file - a failing `archive_command`, a truncated upload, an encryption key that has since rotated, a compression format the current tooling cannot read, or a snapshot that is not crash-consistent because it captured a running database without quiescing. A backup job's exit code is not evidence; only a restore is.
3. **It cannot be restored in the time you promised.** The mechanics work, and they take 14 hours because of volume, single-threaded restore, index rebuilds, or a bandwidth limit nobody measured. The RTO in the document is fiction.

A fourth, which is really the same failure: **nobody knows the procedure**. The person who wrote it has left, the runbook references a tool that no longer exists, and the restore requires a permission nobody currently has.

So the only meaningful control is a **scheduled, automated restore drill**: restore to an isolated environment on a schedule, run integrity checks and a smoke test against the restored data, record the wall-clock duration, and alert if the drill fails or exceeds the RTO. That number - measured, dated - is what you present as your RTO. Everything else is a hope with a cron job.

### Q163. Hard, soft and best-effort dependencies

| Class | Definition | Code | SLO impact |
| --- | --- | --- | --- |
| **Hard** | The request cannot be served correctly without it | No fallback. Fail fast with a clear error. Short timeout, circuit breaker to fail fast rather than hang | Multiplies into your availability (Q156). Minimize the count |
| **Soft** | The request can be served in a degraded form | Timeout well inside the budget, circuit breaker, cached or default fallback, and a `degraded` flag in the response and the metrics | Does not affect the availability SLI; affects a *feature-level* SLI you should track separately |
| **Best-effort** | The request does not depend on it at all - it is a side effect | Fire-and-forget via a queue, never in the request path. Failure is logged and retried asynchronously | No impact on the request SLO; needs its own freshness/completeness SLO (Q7) |

The classification is a **design artifact**, not a comment: it should be written into the service's documentation and encoded in the client configuration, because it determines the timeout, the fallback, the alert severity and the on-call response. It also drives the availability arithmetic: reclassifying a dependency from hard to soft is often the cheapest availability improvement available (Q156).

The two failure patterns this prevents: a soft dependency implemented as hard (a recommendations service outage taking down the product page), and a hard dependency treated as soft (returning a page with a silently missing price - Q157). Both are common, and both are classification errors rather than coding errors.

### Q164. Queue leveling versus autoscaling versus over-provisioning

| | Response time to a spike | Cost | What it does to the user |
| --- | --- | --- | --- |
| **Queue-based load leveling** | Instant - the queue absorbs it immediately | Lowest - you size for average, not peak | Work is accepted but completed later. Requires the operation to be async-tolerable (Q99) |
| **Autoscaling** | 1-5 minutes for VMs, 20-60 s for containers, seconds for serverless - plus warm-up | Pay for what you use; good for slow-moving diurnal curves | A gap of degraded or failed requests while scaling catches up |
| **Over-provisioning** | Instant | Highest - you pay for peak capacity continuously | Nothing; it just works |

The decision follows from the **shape of the spike and the nature of the work**:

- Predictable diurnal variation → autoscaling, with a schedule-based pre-scale so you lead the curve rather than follow it.
- A known event → over-provision, pre-warmed (Q98).
- Unpredictable, sharp spikes with async-tolerable work → queue leveling. This is the strongest option when it applies, because it needs no prediction at all.
- Unpredictable, sharp spikes with synchronous work → over-provision the headroom, plus admission control to protect the system when the headroom is exceeded (Q94). Autoscaling alone cannot save a system from a 30-second 10x spike.

In practice I combine them: queue everything that can be queued, autoscale for the diurnal curve, keep 40-50 percent headroom for the reaction gap, and use load shedding as the guarantee of last resort. The framing I would offer: autoscaling is a **cost optimization** with a reliability side effect, not a reliability mechanism - treating it as the spike defense is a common and expensive misunderstanding.

### Q165. 99.99 percent on 99.9 percent infrastructure `[A]`

The target allows 4.3 minutes of downtime a month; each component allows 43. So the strategy is to make component failures *not* be system failures.

**1. Redundancy that converts a component failure into a non-event.** Three instances across three AZs with N+1 headroom, so one instance or one AZ failing removes capacity, not availability. Two independent components at 99.9 percent, failing independently, give `1 - 0.001^2 = 99.9999 percent` - so redundancy is the primary lever, and the entire question is whether the failures are actually independent.

**2. Eliminate correlated failure, because that is what breaks the arithmetic.** Shared dependencies (Q149), shared configuration pushed simultaneously, a shared control plane, a shared certificate expiry, a shared bug in the same code deployed everywhere. Redundancy over identical software with a synchronized deploy is not redundancy against a bad deploy - hence cells and staged rollout (Q151-152).

**3. Reduce hard dependencies to a minimum** and make everything else degradable (Q156, Q163). Serving a slightly reduced product is not downtime, and this reclassification is where most of the improvement comes from.

**4. Take change out of the failure budget.** Most outages are caused by deployment. Canary plus automated rollback plus cells means a bad change costs `1/N` of users for the duration of the canary, not everyone for the duration of the incident (Q97).

**5. Make recovery automatic and fast.** 4.3 minutes a month means no human can be in the loop: automated failover, automated rollback, self-healing instance replacement. Anything requiring a page, a login and a decision has a floor of ~15 minutes.

**6. Static stability** (Q158), so control-plane failures - which are common and often provider-wide - do not become data-plane failures.

**7. Load shedding rather than falling over** (Q94), because partial availability is measured as partial, and a shed low-priority request may not even count against the SLI if the SLI is defined on critical traffic.

**What I would say honestly:** 99.99 percent measured as "successful critical requests over valid critical requests" is achievable this way in a single region with multi-AZ redundancy. 99.99 percent for *everything including a regional failure* requires multi-region, which is a much larger commitment (Q167), and I would put the numbers in front of the business before signing up to it. I would also insist on measuring it from the client's perspective from day one, because a target nobody measures is not a target.

*Hook: an availability target you renegotiated, or met, and the specific mechanism that did most of the work.*

---

## 11. Multi-region and geo-distribution

### Q166. Three reasons to go multi-region

1. **Latency** - serve users near them. Real and measurable: a user in Singapore talking to `us-east-1` pays 200+ ms per round trip, and a page needing three sequential calls is unusable. This is the most defensible reason.
2. **Regulatory / data residency** - the data must physically reside in a jurisdiction (Q176). Non-negotiable when it applies, and it forces the design regardless of engineering opinion.
3. **Disaster recovery / availability** - survive the loss of a region.

**The one that is usually a lie is the third**, or rather, it is usually stated as the reason and is rarely the real requirement. Full regional failures are rare - a handful per provider per year, usually partial - and most availability incidents are caused by deployments, configuration and application bugs, all of which replicate happily to your second region. A multi-region deployment adds a large amount of complexity that itself causes outages, so it is entirely possible to *reduce* availability by going multi-region. Meanwhile multi-AZ within one region already survives a datacenter loss and gets you to 99.99 percent (Q165).

So the questions I ask: what is the actual availability requirement, measured how; is there a regulatory driver; and where are the users. If the answer is "latency for real users in three continents" or "the regulator requires it", we go. If the answer is "in case us-east-1 goes down", I would first ask whether a warm standby with a tested 30-minute RTO (Q161) meets the business need at a tenth of the cost and complexity - and quantify the current, real sources of downtime, which are almost always change-related.

### Q167. Three topologies compared

| | Single region, multi-AZ | Active-passive multi-region | Active-active multi-region |
| --- | --- | --- | --- |
| **Availability** | 99.99 percent achievable; a full region loss is an outage | 99.99 percent+; survives a region loss with a failover event | 99.99-99.999 percent; survives a region loss with no failover |
| **RPO** | ~0 (synchronous within region) | Seconds to minutes (async cross-region replication) | ~0 in the local region; conflicting writes possible |
| **RTO** | Minutes for an AZ failure (automatic); indefinite for a region failure | 10-60 minutes realistically, including all the dependencies (Q174) | Seconds - traffic reroutes |
| **Write latency** | Low, local | Low, local (single writer) | Low if partitioned by home region; high if globally coordinated |
| **Cost** | Baseline | ~1.3-1.7x (idle or scaled-down standby, cross-region replication, egress) | ~2-2.5x (full duplicate capacity, replication both ways, egress, and the engineering) |
| **Complexity** | Low | Moderate - the failover procedure is the risk | High - conflict resolution, routing, split-brain, testing |

The recommendation I would give by default: **single region multi-AZ until there is a latency or regulatory reason**, then **active-passive** as the first step (it also serves DR), then **active-active partitioned by home region** (Q172) rather than true multi-master, because that gives most of the latency benefit with a fraction of the conflict complexity. True multi-master is for a small number of systems that genuinely need it and can afford the engineering.

The line I would add: the biggest hidden cost of active-passive is that the passive side rots. It must be exercised - ideally by serving real traffic periodically - or you have paid for a standby you cannot use (Q179).

### Q168. Physics

| Path | Round trip |
| --- | --- |
| Same rack / intra-AZ | 0.1-0.5 ms |
| Cross-AZ, same region | 0.5-2 ms |
| Cross-region, same continent (e.g. Ireland ↔ Frankfurt, Virginia ↔ Ohio) | 10-30 ms |
| US East ↔ US West | ~60-70 ms |
| US East ↔ Europe | ~80-90 ms |
| Europe ↔ Singapore | ~160-180 ms |
| US East ↔ Sydney | ~200-230 ms |

These are network round trips, and fibre gives you roughly two-thirds of the speed of light, so ~1 ms per 100 km of path - and real paths are 1.5-2x the great-circle distance.

**What they forbid:**

- **Synchronous cross-continental replication.** An 80 ms round trip added to every commit means a maximum of ~12 sequential writes per second per session, and every user action waits. This is why global synchronous writes are not a design, they are a wish.
- **Chatty protocols across regions.** Ten sequential cross-region calls at 80 ms is 800 ms of pure network. So a cross-region interaction must be a *single* round trip, batched, or asynchronous.
- **A global quorum on the write path** for a latency-sensitive system (Q130). Spanner does it and pays for it with commit-wait; most products cannot.
- **Serving a user from a distant region at all** if the page needs several dependent calls: 200 ms per round trip x 4 sequential calls = 800 ms before any processing.

What they *permit*: asynchronous replication anywhere; reads from a local replica; a single cross-region round trip on a rare operation (Q132); and CDN termination near the user, which converts the TLS handshake's 2-3 round trips from 200 ms into 20 (Q96).

### Q169. New failure modes of active-active `[T]`

1. **Write conflicts.** Two regions accept writes to the same entity concurrently, and there is no ordering between them. You now need a resolution policy (Q131), and the default - last-write-wins on wall-clock timestamps - silently loses data and depends on clock sync (Q129). Active-passive has one writer and therefore no conflicts at all.
2. **Split-brain during a partition.** Both regions are healthy, cannot see each other, and both keep accepting writes - by design. On heal you have two divergent histories (Q128). Active-passive fails closed on the passive side.
3. **Asymmetric and partial replication failure.** Region A→B works while B→A lags, so the regions have different views for hours, and a user whose session moves between them sees data disappear and reappear (a monotonic-reads violation).
4. **Cross-region cascading failure.** Because the regions are coupled by replication, an overload in one propagates: a write storm in A generates replication load in B; a schema change must be compatible with both simultaneously; and a poison record replicates. Active-passive has the same coupling in one direction only.
5. **Doubled deployment risk with a shared blast radius.** A bad schema migration or a bad deploy now hits both regions - and if the deployment is simultaneous, your "regional redundancy" provides no protection against the most common cause of outages.
6. **Routing complexity as a failure source.** The global routing layer, session affinity, and "which region owns this user right now" become their own set of bugs.
7. **Testing is genuinely hard.** You cannot easily reproduce a cross-region partition, so the conflict paths are the least-tested code in the system and are exercised for the first time during an incident.

The summary: active-active removes failover as an event and adds *divergence* as a continuous risk. It is a better answer for latency than for availability, and that reframing is usually the useful contribution.

### Q170. Routing users to a region

| Mechanism | Behavior |
| --- | --- |
| **GeoDNS** | Resolves by the *resolver's* location, cached for an uncontrollable time (Q88). Coarse and slow to change |
| **Anycast + global load balancer** | The network routes to the nearest healthy POP; the edge then selects a backend region by health, latency and weight. Fast failover, no client involvement. The default choice (Q89) |
| **Client-side selection** | The client measures latency to several endpoints and picks. Precise per user, works around bad BGP paths, and lets the client fail over instantly - but requires an SDK, a bootstrap endpoint, and it exposes your topology |

**A user who moves** is the interesting part, and there are two distinct cases:

- **A user who travels** (a laptop in a different country for a week). Routing should follow them for *reads* - they get the nearest read replica and low latency. But if the architecture partitions writes by home region (Q172), their writes must still go to their home region, so they experience higher write latency while travelling. That is the correct trade: correctness over latency for the rare case. The design must therefore separate "nearest region for reads" from "home region for writes", and carry the home region in the session or token so every request knows where to send a write.
- **A user who relocates permanently.** This is a *data migration*: move their records to the new home region, which means a per-user cutover - quiesce their writes briefly, replicate the tail, flip the home-region pointer, resume. It needs to be a supported, automated operation, not a manual database script, because it will be requested (and because residency rules may compel it, Q176).

The failure case to handle: if a user's home region is down, either promote a replica elsewhere (accepting the RPO) or refuse writes with a clear message. Silently accepting writes in a non-home region is how you create the conflicts you designed to avoid.

### Q171. Multi-region write models

| Model | How | Conflict exposure |
| --- | --- | --- |
| **Single writer, global reads** | One region owns all writes; others host read replicas | **None.** All writes are serialized by one primary. Cost: remote users pay full RTT on every write, and a primary-region failure means a promotion event |
| **Partitioned by home region** | Each entity (user, tenant, account) has one owning region that accepts its writes | **None for single-entity operations**, because each entity still has one writer. Conflicts only for cross-entity operations spanning regions, which are rare and can be handled as sagas. This is the sweet spot (Q172) |
| **True multi-master** | Any region accepts any write; replication is bidirectional | **Continuous.** Every entity can be written concurrently in two places. Requires a resolution strategy (Q131), and some conflicts have no correct automatic resolution |
| **Consensus-replicated global** (Spanner, CockroachDB, DynamoDB global tables with strong consistency) | Writes go through a quorum spanning regions | None - it is linearizable. Cost: every write pays a cross-region quorum, so 50-100 ms write latency (Q130, Q168) |

The recommendation: **partition by home region** for almost every product that needs local writes. It gives single-writer correctness per entity - so no conflict resolution, no CRDTs, no lost updates - while keeping writes local for the overwhelming majority of operations. True multi-master is justified when entities are genuinely written from everywhere (a globally shared document, a global inventory) and even then the answer is often a CRDT rather than conflict resolution.

The point to volunteer: the *interesting* conflicts are not concurrent edits to one field, they are **invariant violations across entities** - two regions each confirming the last seat, or each registering the same username (Q132). Those cannot be resolved by a merge function; they need either a single owner for the invariant or a business-level compensation.

### Q172. Home-region design and cross-region interactions

The model: every user has a `home_region` recorded authoritatively (in a small, globally-replicated directory). All writes for that user are executed in their home region; reads may be served locally anywhere from replicas with a stated staleness bound.

**A cross-region interaction between two users with different home regions** - user A in Europe messages user B in Singapore, or transfers money to them:

1. **Split the operation into per-entity local writes joined by an asynchronous event.** A's write (send the message, debit the account) happens locally in Europe, transactionally, in A's home region. It emits an event.
2. **The event is delivered to B's home region** where B's local write happens (append to B's inbox, credit B's account). Delivery is at-least-once, so B's write is idempotent on the event id.
3. **The user-visible contract is asynchronous**, and honestly so: A's action succeeds immediately and locally; B sees it after cross-region propagation - typically 100-300 ms, which for a message is imperceptible, and for a bank transfer is irrelevant.
4. **If the operation must be atomic across the two** (a transfer that must not create or destroy money), it is a **saga**: debit locally with a pending state, propagate, credit remotely, confirm back; on failure, compensate by reversing the debit. The intermediate state is visible and must be modelled (`PENDING_TRANSFER`), not hidden.
5. **For reads across regions** - A viewing B's profile - read the local replica of B's data. It is stale by the replication lag, which is fine for a profile and not fine for a balance, so the consistency table from Q14 decides per field.

The design cost to state plainly: **every cross-region interaction becomes asynchronous and every cross-region invariant becomes a saga.** That is acceptable when cross-region interactions are a minority of traffic, and it is the reason to choose the partitioning axis (user, tenant, geography) such that most interactions stay within one region. If most interactions are cross-region, home-region partitioning is the wrong model.

### Q173. Replication lag as a product concern

**Expose it.** The system should know its own lag end to end (Q118 - the heartbeat technique) and be able to answer "how stale is this data" per read path. That number belongs in three places: an internal dashboard and alert; a response header or field on API reads served from a replica (`X-Data-As-Of`); and, when it exceeds a threshold, the user interface.

**Bound it.** A staleness SLO with an alert (`p99 lag < 2 s, max < 30 s`), and a **circuit breaker on staleness**: if a replica's lag exceeds the bound, remove it from the read pool and send traffic to the primary or another replica. Serving from a replica 10 minutes behind is worse than serving slowly. This single control prevents most lag-related incidents.

**Design the UI for it:**

- **Read-your-writes for the actor** (Q119) - the person who made the change never sees stale data about their own change. This alone removes 90 percent of perceived inconsistency.
- **Optimistic rendering** - show the intended result immediately, reconcile in the background, and have a defined behavior if reconciliation fails.
- **"As of" labelling** on anything that is knowingly delayed: "Balance as of 2 minutes ago", "Updated 30 seconds ago". Users tolerate stated delay and are angered by silent wrongness.
- **Avoid showing a derived total next to its components** when the two have different lags, because the discrepancy is what users notice and report.
- **A visible degraded state** when lag exceeds the bound - "Data may be delayed" - rather than pretending.

The principle: **staleness is a product feature that must be specified, measured and displayed**, not an implementation detail. Teams that treat it as an implementation detail spend the following year on bug reports that are all the same bug.

### Q174. Failover succeeded and the system is still broken `[T]`

Four realistic reasons:

1. **A dependency did not fail over.** The application is now in region B and still calling a queue, cache, search cluster, secret store, or third-party endpoint in region A - because a hostname, an ARN or a connection string was region-specific and nobody enumerated them. Or a third party's IP allowlist contains only region A's NAT addresses, so all outbound calls are rejected.
2. **Capacity.** Region B was running at 20 percent scale because it was a warm standby, and it cannot absorb 100 percent of traffic. Autoscaling then fails or is too slow, or hits an account quota that was never raised in region B (this is extremely common - quotas are per-region and nobody tests them). The failover worked and the system is overloaded.
3. **Cold state.** Caches are empty, so the database in region B receives full uncached load and collapses (Q76). Connection pools are cold, JIT is cold, and any warm in-memory state (a rate limiter's counters, a session store, a local index) is gone. The failover succeeded into a stampede.
4. **Data.** The replica was behind, so recent writes are missing - orders that exist in the users' inboxes but not in the database, idempotency keys lost so retries duplicate, and sequences or ID generators that have gone backwards, producing primary key collisions. Or replication was configured for the database and not for one of the *other* stateful components.

Two more worth having ready: **DNS and client caching** meant a large fraction of traffic still went to region A for minutes or hours (Q88); and **the failover was partial** - some services moved, some did not - so requests now cross regions on every hop, adding 80 ms per call and breaking latency-sensitive paths.

The prevention is a **regional dependency inventory** (every external identifier tagged with its region), quota parity verified by automation, a full-size or rapidly-scalable standby (Q158), cache pre-warming as part of the failover runbook, and monthly exercises that measure all of it (Q179).

### Q175. Failover mechanics

**Automatic versus manual.** Automatic failover is required for anything with an RTO under ~15 minutes, because a human cannot be paged, oriented and confident faster than that. But automatic *regional* failover is dangerous: the failure signal is ambiguous (is the region down, or is my monitoring partitioned from it?), the action is disruptive and hard to reverse, and a false positive is a self-inflicted outage. So the usual answer is **automatic within a region (AZ-level, instance-level, database primary promotion) and human-initiated across regions**, with the *mechanism* fully automated so the human decision is a single button, not a runbook of forty steps.

**The health signal to trust:** not a single ping from a single vantage point. I want (a) client-perceived success rate from multiple external vantage points outside the affected region - because that is the only signal that measures what users experience (Q159); (b) corroboration from at least two independent observers; (c) a sustained window (30-60 seconds) so a blip does not trigger it; and (d) an explicit check that the *observer* is healthy, to avoid failing over because monitoring broke. Never trust a signal that originates inside the region being judged.

**Why a human in the loop:** the decision is not "is region A unhealthy" but "will moving to region B make things better", and that requires judgement about data loss (the current replication lag is a data-loss decision someone must own), about region B's readiness, and about whether the failure is regional at all or is a bug that will follow you. The compromise I favor: automated detection and a pre-computed recommendation with the numbers attached ("region A error rate 87 percent for 4 minutes; region B healthy; current replication lag 6 seconds; estimated data loss 6 seconds of writes; failover?"), one authorized human, one command, and a fully automated execution with a status feed.

### Q176. Data residency

Residency requirements say certain data about certain people must be stored (and sometimes processed, and sometimes only accessed) within a jurisdiction. GDPR itself does not require EU-only storage - it restricts *transfers* to countries without adequate protection, which is a legal mechanism rather than a geographic one - but several regimes (India's DPDP for some categories, China, Russia, various financial and health regulators, and many public-sector contracts) do impose hard localization.

**What it does to a global design:**

1. **Partitioning becomes non-negotiable and is dictated by geography** (Q135, Q172). You cannot choose the shard key for performance; residency chooses it for you.
2. **No global tables for regulated data.** Cross-region replication of personal data must be either eliminated or restricted to non-personal or pseudonymized derivatives. That kills the simple "global DynamoDB table" or "global read replica" answers.
3. **Backups, logs, metrics and traces are in scope.** This is the part that fails audits: the database is in Frankfurt and the application logs containing email addresses are shipped to a US observability vendor. Log scrubbing, regional log sinks and PII classification (Q233) become architectural requirements.
4. **Derived stores inherit the constraint** - the search index, the warehouse, the ML training set, the support tooling, the CRM export.
5. **Support and operations access** may itself be a "transfer", so an engineer in one country debugging another's data can be a violation. That drives regional access controls and just-in-time access with audit.
6. **A global control plane with regional data planes** is the standard resolution: identity, configuration, billing metadata and routing are global (and carry no regulated personal data), while all personal data lives regionally.

**Where the data actually lives:** a per-region data plane holding the personal data, a small global directory holding only a mapping from an opaque user id to a home region, and every derived store instantiated per region. The honest cost: per-region duplication of infrastructure, per-region migrations, no cross-region analytics without an aggregation step that strips identifiers, and a materially higher bill.

### Q177. Global uniqueness and global counters

**Global uniqueness** splits into two very different problems:

- **Unique *identifiers*** - solved without coordination. UUIDv7, or Snowflake with per-region node ids, or per-region ID ranges. Each region generates ids independently with a structural guarantee against collision. Latency: zero. This is the case that is easy, and it is what most "global uniqueness" requirements actually are.
- **Unique *user-chosen names*** (usernames, email addresses, subdomains, SKUs) - requires coordination, because two regions can be asked for the same name simultaneously. Achievable at the cost of one round trip to a single owner of the namespace: either a single global registry region (80-150 ms for a remote user) or a partitioned registry where each hash range has an owning region (Q132), which keeps most registrations local. There is no way to make this both globally correct and locally fast; anyone claiming otherwise is proposing eventual consistency with a conflict, which for usernames means telling a user later that their name is not theirs.

**Global counters:**

- **Approximate, converging** - achievable with zero coordination using a **CRDT counter**: each region maintains its own increment-only counter, replicas merge by summing per-region values, and the total converges. Read latency local, accuracy eventually exact once replication settles, and no increment is ever lost. This is the right answer for views, likes, and metrics.
- **Exact-at-read-time** - requires reading all regions (a cross-region fanout, so the slowest region's latency) or a single owning region.
- **A counter with a hard limit** ("only 1,000 tickets") - this is not a counter, it is a global invariant, and the answer is either single-owner or **escrow**: pre-allocate 100 tickets to each of 10 regions, allow local decrements, and rebalance the remainder as regions run out (Q120). You lose optimal utilization of the last few units and gain local latency, which is the standard and correct trade.

### Q178. Cross-region cost

The real multiplier over single-region, itemized:

| Item | Effect |
| --- | --- |
| **Duplicated compute** | 1x to 2x, depending on whether the second region is full-size (active-active or statically stable standby) or scaled down (pilot light) |
| **Duplicated storage** | ~2x for the data layer, plus per-region backups |
| **Replication egress** | Charged per GB leaving a region - typically $0.02/GB between regions. A system writing 1 TB/day of replicated changes pays ~$600/month for the privilege, and change volume is usually much larger than people estimate because it includes indexes and WAL, not just logical rows |
| **Cross-region request traffic** | Any request that crosses a region pays egress *and* latency. A chatty design multiplies this |
| **Duplicated managed services** | Two Kafka clusters, two search clusters, two cache tiers, two observability footprints. Managed services have per-cluster floors, so two half-size clusters cost more than one full-size |
| **Non-production** | If you replicate the topology in staging, everything above doubles again |
| **Engineering** | The largest real cost, and the one that never appears in the cloud bill |

**The realistic multiplier: 1.5-1.7x for active-passive with a scaled-down standby, 2-2.5x for active-active.** I would present it that way rather than as a precise number, and I would highlight the two line items that surprise people: replication egress (because it is proportional to write volume, which grows) and duplicated managed-service floors (because they are fixed and non-linear).

The cost optimizations worth knowing: compress and filter what you replicate (do not replicate derived data that can be rebuilt locally); keep cross-region chatter out of the request path; use a provider's private backbone where it is cheaper than internet egress; and consider whether the standby genuinely needs the full dataset or only the transactional core.

### Q179. Testing multi-region

**Monthly, as a scheduled exercise:**

1. **A real failover of a non-critical service**, in production, during business hours, with the team watching. Measure wall-clock time from decision to healthy, and compare it with the documented RTO.
2. **A database failover drill** in a production-like environment, measuring promotion time, application reconnection behavior and data loss at the moment of cut.
3. **Traffic-shift verification:** move 10 percent (then 50 percent) of live traffic to the standby region for an hour. This is the single most valuable exercise, because it proves capacity, quotas, dependency reachability and cold-cache behavior all at once - and it is far safer than discovering them during an incident (Q174).
4. **Quota and configuration parity check**, automated: compare limits, instance counts, IAM, secrets, certificates, allowlists and feature flags between regions, and alert on drift. Drift is continuous and silent.
5. **A restore drill** from backup in the standby region (Q162).
6. **Dependency inventory audit**: every external endpoint, ARN and hostname tagged with its region, verified reachable from the standby.

**Quarterly or annually:** a full game-day - simulate the loss of the primary region with the on-call team responding to the runbook cold, and treat every step that needed improvisation as a defect.

**Continuously:** synthetic probes from multiple external vantage points against *both* regions, so the standby's health is a monitored SLI rather than an assumption. A standby that is not monitored is not a standby.

The organizational insight: **the only reliable way to keep a standby working is to serve real traffic from it.** Active-active gets this for free, which is one of its underrated advantages; active-passive needs a deliberate, recurring traffic shift, and if the organization will not commit to that, it should be honest that the RTO is aspirational.

### Q180. Sequencing global expansion into three continents `[A]`

**Phase 0 - decide what problem we are solving (weeks).** Latency, residency, or availability (Q166)? Get the actual user distribution, the latency budget, and the legal requirements per country. The answer determines everything, and getting it wrong here wastes a year. Deliverable: a one-page requirement with numbers.

**Phase 1 - edge before backend (1-2 months, high value, low risk).** Put a CDN and an anycast global entry point in front of the existing single region. TLS terminates near the user, static assets and cacheable responses are served locally, and connections are pooled over the provider's backbone. This typically removes 40-60 percent of perceived latency for remote users for a small fraction of the cost of multi-region, and it is entirely reversible. Do this before anything else, always.

**Phase 2 - regional read paths (2-3 months).** Read replicas in each target region, with reads served locally and writes still going to the home region. Requires: read-your-writes handling (Q119), staleness bounds and exposure (Q173), and a routing layer that distinguishes read from write. Now remote users have fast reads and slow writes, which for most products is the majority of the experience.

**Phase 3 - make the architecture region-aware (3-4 months, the real work).** Introduce `home_region` as a first-class concept: a global directory, tokens and sessions carrying it, all write paths routing by it, and a per-user migration capability (Q170). Also the unglamorous prerequisites - a regional dependency inventory, per-region quotas and configuration parity automation, regional log and metric sinks, and per-region deployment with staged rollout. This phase buys nothing user-visible and everything afterwards depends on it.

**Phase 4 - regional write capability, one region at a time (3+ months).** Stand up a full data plane in the second region, migrate a cohort of users' home region to it, and run for a quarter before starting the third. Cross-region interactions become events and sagas (Q172).

**What I would not do yet:** true multi-master replication or a globally-distributed database (defer until home-region partitioning is proven insufficient); active-active for the *whole* system (start with the stateless tier and reads); moving the analytics platform (keep it central and aggregate); and any residency work for jurisdictions we have no customers in. I would also refuse to run phases 3 and 4 in parallel with a major feature program, because the failure mode of this work is a half-finished region-awareness that nobody can reason about.

**The checkpoint I would insist on:** after Phase 2, re-measure. Quite often the CDN plus local reads meets the actual latency requirement, and Phase 3-4 can be deferred by a year - which is a better outcome than completing them.

*Hook: a geographic expansion you sequenced, and the phase that delivered most of the benefit.*

---

## 12. Real-time delivery, push and fanout

### Q181. Five delivery mechanisms

- **Short polling** - the client asks every N seconds. Choose it when the update interval is long, the client count is modest, and simplicity beats everything. It is the correct answer far more often than engineers like, because it has no connection state, survives any network, and needs no special infrastructure.
- **Long polling** - the client asks and the server holds the request open until there is news or a timeout. Choose it when you need near-real-time push and cannot use WebSockets (a restrictive proxy, an old client), accepting that each waiting client occupies a connection.
- **Server-sent events** - a single long-lived HTTP response streaming text events, one direction, with automatic reconnection and event ids built into the protocol. Choose it when the flow is server-to-client only: notifications, live dashboards, progress updates, streaming LLM tokens. It is HTTP, so it works with existing infrastructure, and it is much simpler than WebSockets.
- **WebSockets** - full-duplex, low overhead per message, any payload. Choose it when the client also sends frequently (chat, collaborative editing, gaming, live cursors) or when per-message overhead matters at high rates.
- **Push notifications (APNs/FCM)** - the only way to reach a client that is not running. Choose it when the device may be backgrounded or offline, which for mobile means "always, in addition to one of the above".

The one-line criterion: **how fresh, which direction, and is the app running?** Not-running forces push notifications; server-to-client only favors SSE; bidirectional and chatty favors WebSockets; anything tolerant of seconds favors polling.

### Q182. 10 million concurrent WebSockets

**Per-connection budget.** A connection costs: kernel socket buffers (tunable, ~4-16 KB minimum for send and receive combined if tuned down from defaults), TLS session state (~10-20 KB with a modern stack), a file descriptor, and application-level state (user id, subscriptions, last-seen sequence, write queue) - call it 2-10 KB if you are disciplined. Realistically **20-50 KB per connection** for a well-tuned Go/Rust/Netty gateway with small buffers, and 100 KB+ if you are careless with per-connection objects or use a thread-per-connection model.

**Node count.** At 40 KB per connection, a 32 GB node holds ~500,000 connections in ~20 GB with headroom for the runtime, GC and message throughput. In practice teams run 100,000-500,000 per node; the binding constraint is usually not memory but **CPU during a reconnect storm** and per-message processing.

```
10,000,000 connections / 250,000 per node = 40 nodes
plus N+2 redundancy and headroom to absorb one node's failure → ~50 nodes
across 3 AZs, so losing one AZ leaves 33 nodes holding 10M → they must be sized for 300k each
```

**The rest of the design:**

- **The gateway is stateless about business logic** - it holds connections and subscriptions only, so it can be scaled and replaced. All durable state is elsewhere.
- **Kernel tuning is mandatory:** file descriptor limits, `somaxconn`, ephemeral port range (relevant for the upstream side), `tcp_mem`, and reduced per-socket buffers. Defaults will cap you around tens of thousands.
- **L4 load balancing** to the gateways with long idle timeouts, since L7 per-request balancing is meaningless for a single long connection (Q83).
- **A routing layer** so a message for user X reaches the node holding X's connection (Q185).
- **Heartbeats** (ping/pong every 30 s) to detect half-open connections, which are otherwise invisible and consume capacity indefinitely.
- **Deployment strategy:** every deploy disconnects everyone (Q184), so the design must include staggered, slow restarts and client-side reconnect with jitter - or connection draining that hands over gracefully.

### Q183. Presence at scale

**Data structure.** A per-user key with a TTL is the core: `presence:{user_id} → {status, last_seen, connection_node}` with a TTL of ~45 seconds, refreshed by a heartbeat every 15-30 seconds. Absence of the key *is* offline - no explicit offline event needed, which means a crashed client or a dead node self-heals. In Redis this is a `SET ... EX 45` per heartbeat, which is cheap and requires no cleanup job.

**Update rate arithmetic.** 10 million online users with a 30-second heartbeat is `10^7 / 30 ≈ 333,000` writes/second to the presence store. That is a sharded Redis workload, not a single instance. Two mitigations: batch heartbeats at the gateway (one node reports 250,000 users in a handful of pipelined commands per interval rather than 250,000 individual ones), and lengthen the heartbeat interval, trading detection latency for write volume. Batching is the important one - it reduces 333,000 round trips to a few hundred.

**Avoiding O(n^2).** The naive design broadcasts every status change to every friend, so a user with 5,000 friends generates 5,000 notifications per change, and with 10 million users flapping you get an unservable fanout. The standard fixes:

1. **Pull, not push, for the common case.** When a client opens a view, it asks for the presence of the *visible* subset - the 20 people on screen - as a single batched read. Nobody needs presence for 5,000 friends they are not looking at.
2. **Subscribe only to what is visible**, and unsubscribe on scroll. Presence subscriptions are ephemeral and bounded by screen size, which caps fanout at tens per client rather than thousands.
3. **Coalesce and rate-limit changes** - a user toggling between online and away should not generate a storm; debounce over several seconds and suppress no-op transitions.
4. **Do not treat presence as durable.** It is best-effort, it may be seconds stale, and that is an acceptable product contract. Trying to make presence reliable is where these systems go wrong.

### Q184. A gateway restart and 500,000 reconnects `[T]`

**The storm.** All 500,000 clients detect the disconnection within a second or two and reconnect immediately. Each reconnect is a TCP handshake, a TLS handshake (expensive - an RSA/ECDHE operation per connection, so this is CPU-bound), an authentication check (a token validation, possibly a database or cache read), a subscription restore, and usually a **backfill request** for missed messages (Q193). So one restart produces 500,000 simultaneous TLS handshakes, 500,000 auth lookups, and 500,000 history queries - each of which is far more expensive than the steady-state cost of holding a connection. The remaining gateway nodes, the auth service and the message store all see an instantaneous spike of 10-100x. They fail, which disconnects more clients, which reconnect. That is a metastable reconnect storm (Q26).

**Four controls:**

1. **Client-side exponential backoff with full jitter.** Reconnect after `random(0, min(cap, base x 2^attempt))`, not immediately. This alone spreads 500,000 reconnects over minutes instead of seconds and is the single most important control. It must be in the client SDK, because you cannot fix it later in the server.
2. **Server-directed reconnect pacing.** On a planned shutdown, send a `close` frame containing a reconnect delay and, ideally, a target endpoint - so the server distributes the reconnection schedule rather than hoping. Combined with a **staggered rollout** (restart 2 percent of nodes at a time, waiting for reconnections to settle), a full deploy never produces a storm at all.
3. **Admission control at the gateway.** A hard rate limit on new connection establishment per node (and per source), shedding excess with a `503` and a `Retry-After` so the expensive handshake path is protected (Q94). Better to admit 10,000/second calmly than to attempt 500,000 and complete none.
4. **Make reconnection cheap.** TLS session resumption to avoid the full handshake; a resumption token that carries the subscription set so no database lookup is needed; a signed token validated locally with a cached JWKS rather than a call to an auth service; and a bounded backfill (Q193) that returns "too much history, resync from a snapshot" rather than replaying a month of messages.

A fifth, which is the architectural version: **do not restart all gateways at once, ever** - and design them to be long-lived and rarely deployed, with business logic in separate services that can deploy freely.

### Q185. Routing a message to an unknown node

**Design A - a connection registry.** A shared store maps `user_id → gateway_node` (and possibly a list, since a user may have several devices). It is written on connect, deleted on disconnect, with a TTL as a safety net. To send, look up the node and forward directly (an RPC or a per-node queue).

- Pros: a single point lookup, minimal network traffic, exact delivery. Scales to very large numbers of nodes.
- Cons: the registry is a hard dependency on the send path and must be highly available and low latency (so: Redis, sharded, with a local cache). It is racy - a user reconnects to a different node while a message is in flight, so sends must tolerate "node no longer has this user" and retry via a lookup. And it is another stateful component to operate.

**Design B - broadcast / pub-sub to all nodes.** Publish the message on a topic; every gateway node subscribes and delivers to whichever of its connections match.

- Pros: no registry, no lookup, no races - the design is trivially correct and connection churn is invisible.
- Cons: every node receives every message. With 50 nodes, that is 50x the internal traffic, and each node spends CPU discarding messages that are not its. It works well up to a few tens of nodes and moderate message rates, and collapses beyond that.

**The hybrid that is usually right:** partition the *pub-sub topics* by a hash of the user id (say 256 channels), and have each node subscribe only to the channels containing its connected users. Now a message goes to a small subset of nodes rather than all of them, with no per-user registry to keep consistent. This is the sweet spot: no exact-state tracking, and traffic amplification of `nodes_per_channel` rather than `all nodes`.

For large conversation fanout, add a per-conversation channel so a group message is published once and each node delivers to its local members - which is the shape of Q187's answer.

### Q186. Push versus pull for a feed

**Fanout-on-write (push).** On post, write an entry into each follower's timeline store. Reads are a single sequential read of a precomputed list - fast, cheap, and cacheable. Writes cost `O(followers)`.

**Fanout-on-read (pull).** On read, fetch the recent posts of everyone the user follows and merge. Writes are `O(1)`. Reads cost `O(following)` lookups plus a merge - expensive, and hard to cache because every user's merge is unique.

**The crossover** is determined by the read:write ratio and the fanout distribution. The arithmetic: fanout-on-write costs `writes x avg_followers` units of work; fanout-on-read costs `reads x avg_following`. With a typical social ratio of 50-100 reads per write, and average following ≈ average followers, **fanout-on-write wins by an order of magnitude** for the average user - which is why it is the default. It stops winning when a single write's fanout is so large that it cannot be absorbed (Q187), or when followers are inactive: writing to 50 million timelines of which 2 percent are read that week is 98 percent wasted work.

**The hybrid, which is what production systems actually do:**

- Fanout-on-write for authors below a follower threshold (thousands to tens of thousands).
- Fanout-on-read for authors above it: their posts are not pushed; instead each reader, at read time, merges their precomputed timeline with a small number of "celebrity" author caches. Since a user follows few celebrities, this is a bounded merge of a handful of cached lists.
- **Activity-based pruning**: do not fan out to accounts inactive for N days; rebuild their timeline on demand when they return.
- **Bounded timelines**: keep the newest ~800 entries per user; older pages fall back to fanout-on-read.

Stating the threshold as a *tunable derived from the follower histogram* rather than a constant is the detail that shows you have run one of these.

### Q187. Fanout-on-write for 50 million followers `[T]`

What breaks: one post becomes 50 million writes. At an optimistic 100,000 timeline writes/second across the cluster, that is 500 seconds for a single post - and during those 500 seconds the fanout workers are entirely consumed, so every ordinary user's post is delayed behind it. The write burst also concentrates on whichever partitions those followers occupy, producing a hotspot; the queue backs up; and if the account posts three times in a minute, the backlog is unrecoverable. Latency SLOs for everyone collapse because of one write.

**The actual production answer:**

1. **Do not fan out at all above a threshold.** The celebrity's posts go into a per-author cache (a short list of recent posts, heavily cached and CDN-able). At read time, a user's timeline is `merge(precomputed_timeline, [author_cache for each celebrity I follow])`. Since a user follows few such accounts, this is a merge of the user's own list plus a handful of small cached lists - a few milliseconds, and the celebrity's post is visible instantly to everyone, which is *better* than fanout-on-write's 500-second tail.
2. **Isolate the fanout workload** so that even sub-threshold large accounts (100,000 followers) go to a separate queue with its own capacity, and cannot delay small-account fanout (Q94, Q155).
3. **Rate-limit and batch** the fanout: write timeline entries in bulk (500-1,000 rows per statement), and pace the job so it does not saturate the store.
4. **Prune aggressively** - skip inactive followers entirely, and cap timeline length.
5. **Make the threshold dynamic** on both follower count *and* observed follower activity, and re-evaluate it as the distribution shifts.

The insight worth stating: the hybrid is not a compromise, it is strictly better at both ends. Fanout-on-write gives cheap reads for the 99.9 percent of accounts where it is affordable; fanout-on-read gives instant publication for the accounts where fanout is not affordable at all.

### Q188. Ordering and dedup for a reconnecting client

**What the server provides:** a monotonically increasing **per-channel sequence number** assigned by a single writer for that channel (the conversation, the topic, the user's inbox). Not a timestamp - timestamps are not unique, not monotonic across nodes, and not gap-free (Q129). Each message carries `(channel_id, seq, message_id)`.

**What the client must send you on reconnect:** the highest contiguous sequence number it has processed per channel - a cursor, `last_seq`. Contiguity matters: if the client has 10, 11 and 13, it must report 11, not 13, or 12 is lost forever. The server then returns everything after `last_seq`, in order.

**Why this shape:**

- **Ordering** is guaranteed by delivering in sequence order and by the client buffering out-of-order arrivals until the gap fills (with a timeout that triggers a re-fetch).
- **Deduplication** is free: the client discards anything with `seq <= last_seq`. Since delivery is at-least-once, duplicates are expected, not exceptional.
- **Gap detection** is free: a jump in sequence means loss, and the client re-requests the range explicitly. This is the property timestamps cannot give you - with timestamps, the client cannot tell "nothing happened" from "I missed something".
- **Idempotent client state** means the server can resend freely, which makes the whole protocol simple.

Practical additions: acknowledgements from the client so the server can bound how much history it must retain per device; a per-device cursor (a user with three devices has three positions); and a "resync" response when `last_seq` is too old to serve incrementally (Q193), which converts an unbounded backfill into a snapshot fetch.

### Q189. Delivery and read receipts

**The state machine**, per message per recipient:

```
SENT (accepted by server, sequenced)
  → DELIVERED (recipient's device acknowledged receipt)
    → READ (recipient's client reports the message was displayed)
```

Transitions are monotonic and idempotent - a `DELIVERED` after a `READ` is discarded - which makes at-least-once acknowledgement safe.

**The write amplification is the problem.** In a 1:1 chat, one message produces 3 writes (sent, delivered, read) plus 2 notifications back to the sender. In a **group of 500**, one message produces up to `500 x 2 = 1,000` receipt writes and, naively, 1,000 status-update notifications to the sender - so a group chat's receipt traffic dwarfs its message traffic by two to three orders of magnitude. That is the design constraint.

**Where you cheat:**

1. **Aggregate, do not enumerate, for groups.** Store a per-recipient read position (`user_id → last_read_seq`) rather than a row per message per user. One update per user per read event, regardless of how many messages were read - so opening a chat with 200 unread messages is one write, not 200. This is the single most important optimization and it also gives you unread counts for free (`count of seq > last_read_seq`).
2. **Batch and debounce receipts.** The client sends one receipt per few seconds covering a range, not one per message.
3. **Do not push per-recipient receipt updates in large groups.** Above a size threshold, show an aggregate ("Read by 47") computed on demand from the read positions, and stop sending real-time updates. Many products simply disable per-person receipts in large groups, which is a product decision that saves an architecture.
4. **Delivery receipts are best-effort and not durable** for groups - store the aggregate, not the matrix.
5. **Privacy is a feature that saves you work**: a "read receipts off" setting removes the write entirely for those users.

### Q190. Mobile push

**Token lifecycle** - the part that is always underestimated:

- The device obtains a token from APNs/FCM and registers it with your backend, tagged with user, device, platform and app version.
- Tokens **change**: on app reinstall, on device restore, on OS update, and unpredictably. So the client must re-register on every launch, and the backend must upsert rather than insert.
- Tokens **die**: uninstalls, and long-inactive devices. The provider tells you via a rejection code (`Unregistered`, `InvalidRegistration`) or a feedback mechanism, and you **must** delete on those codes. A backend that ignores them accumulates dead tokens, and eventually most of its push volume is to the void - which providers may throttle you for.
- One user has many devices; one device may have several users over time. So the mapping is `(user, device)` and it needs cleanup on logout, or you push one user's notifications to another's phone.

**Delivery guarantees:** best-effort, at-most-once, unordered, and silently droppable. The provider may collapse notifications (only the latest survives for a given collapse key), delay them (power-saving modes, Doze, Low Power Mode), drop them entirely if the device has been offline beyond a retention window, or deliver them hours later. Silent/data-only pushes are throttled aggressively on both platforms.

**Therefore you cannot treat it as reliable**, and the design consequences are concrete:

1. **Push is a hint, not a transport.** The notification carries an id and a nudge; the app fetches authoritative state on open (Q193). Never put the only copy of data in a push payload.
2. **The in-app inbox is the source of truth**, reconciled on foreground.
3. **Badge counts must be computed server-side** and either sent as an absolute number or recomputed by the app on launch, because a delta-based count drifts the moment one push is lost.
4. **Deduplicate at the client** on notification id, since a push plus an in-app fetch may both surface the same event.
5. **Fanout must be rate-limited and batched** per provider, and per-token failures handled individually - a 500-token multicast returns per-token results, and ignoring them is how token lists rot.

### Q191. Collaborative editing: OT versus CRDT

**Operational transformation.** Clients send operations (insert at position 5, delete 3 characters at 12). A **central server** serializes them into a canonical order and transforms each incoming operation against the ones it did not know about, then broadcasts the transformed result. The server is essential and authoritative: it holds the single order, and correctness depends on the transformation functions satisfying algebraic properties that are notoriously hard to get right for rich content. Google Docs is the canonical OT system. Advantages: compact operations, small documents, and a natural place to enforce permissions and produce history.

**CRDTs.** Each character (or block) gets a globally unique, densely-orderable identifier, so insertions and deletions commute by construction. Any two replicas that have seen the same set of operations converge to the same document, with **no central coordination and no transformation**. The server can be a dumb relay or a peer. Advantages: offline editing works naturally, peer-to-peer is possible, and correctness is a property of the data type rather than of a transformation matrix. Costs: metadata per character (mitigated by modern designs like RGA/Yjs/Automerge, but still real), tombstones for deletions that need eventual garbage collection, and less intuitive handling of intention preservation (two users' concurrent edits converge, but the result may not be what either wanted).

**The server's role:**

| | OT | CRDT |
| --- | --- | --- |
| Server | **Required.** Assigns the total order and performs transformation | **Optional.** Relays operations, persists them, enforces access control, and provides a snapshot for new joiners |
| Offline | Hard - long divergence means many transformations | Natural - merge on reconnect |
| Complexity | In the algorithm, centrally | In the data structure, everywhere |

What I would choose in 2026: a **CRDT (Yjs or Automerge)** with a server that persists the operation log, serves snapshots, enforces authorization and handles presence. The reason is not elegance - it is that the server becomes simple and stateless-ish, offline works, and the hard correctness problem is solved by a library rather than by my transformation functions. I would keep the server authoritative for *permissions* and for the durable log, because "no central authority" is a distributed-systems property, not a product requirement.

### Q192. Live counters at three price points

**Design A - exact, transactional.** `UPDATE counters SET n = n + 1 WHERE id = ?` in the request. Exact, immediately consistent, and it serializes on a single row - so a hot object caps at a few thousand updates/second and every writer contends. Use for anything financially or legally significant. Cost: high contention, and a hot row is a hot page is a hot shard.

**Design B - sharded counter, exact-on-read.** Split into N sub-counters (`counter:{id}:{0..99}`), each writer increments a random one, readers sum all N. Contention drops by N; reads cost N lookups (cheap, and cacheable for a second). Still exact. This is the standard escrow/sub-key technique (Q140) and it is the right default for a high-write counter that must be correct. Cost: N-fold read amplification and a bit of machinery.

**Design C - buffered and approximate.** Each application instance accumulates increments in memory and flushes an aggregate every 1-10 seconds (`INCRBY key delta`), while reads are served from a cached value with a short TTL. Write volume to the store drops by orders of magnitude - 100,000 increments/second become a few hundred `INCRBY` calls. Accuracy: eventually correct within the flush interval, **except** that an instance crash loses its unflushed buffer, so the count can be permanently short by a few seconds of traffic. Perfect for views, impressions and likes; unacceptable for anything billed.

A fourth for extreme scale: **probabilistic** - HyperLogLog for unique counts (unique viewers) at ~1.6 percent error in 12 KB regardless of cardinality, and Count-Min Sketch for top-K. The right answer when the question is "roughly how many distinct users" over a billion events.

| | Accuracy | Write cost | Read cost |
| --- | --- | --- | --- |
| A - transactional | Exact, linearizable | 1 contended write per event | 1 read |
| B - sharded | Exact | 1 uncontended write per event | N reads (cacheable) |
| C - buffered | Approximate, small permanent loss possible | ~1 write per instance per interval | 1 cached read |
| D - probabilistic | ~1-2 percent error | 1 cheap op per event | 1 op |

The design point: **choose per counter, based on whether anyone would be harmed by being wrong by 0.1 percent.** Most product counters are C; billing counters are A or B; analytics cardinality is D. Using A everywhere is the common mistake, and it shows up as lock contention on the most popular object in the system.

### Q193. Backfill on reconnect

**How much history:** bounded by a policy, never by "everything since last_seq". Three tiers:

1. **Incremental** - if `now.seq - last_seq` is small (say under 500 messages, or under 24 hours), stream the delta from the channel's log. Fast, cheap, exact.
2. **Truncated with a gap marker** - if the delta is moderate, return the most recent N and an explicit `history_truncated` marker with a cursor, so the client can page backwards lazily if the user scrolls. The client's state stays correct because it knows there is a hole.
3. **Resync from a snapshot** - if the client is very stale (offline for a month), do not replay; return a `RESYNC_REQUIRED` response with a pointer to a current-state snapshot (the conversation list, unread counts, the last page of each active channel) and let the client discard its local delta expectations. This converts an unbounded operation into a bounded one.

**From where:** the channel's durable message log (partitioned by channel, ordered by sequence) for tiers 1 and 2, and a periodically-materialized snapshot for tier 3. Not from the gateway's memory, which has none, and not from a general-purpose database scan.

**Bounding the cost of a month-offline client:**

- The tiering above is the primary control - a very stale client costs one snapshot read, not a million-row scan.
- **Per-channel retention** for the incremental path (keep 30 days or 10,000 messages in the hot log; older data lives in cold storage reachable only by explicit paging).
- **Cap the total backfill bytes per reconnect** and per client per minute, and rate-limit resync requests, so a reconnect storm (Q184) cannot become a database incident.
- **Prioritize:** backfill the channels the user is actually looking at first, and the rest lazily. A client with 400 channels does not need all of them before showing the first screen.
- **Charge it to a separate resource pool** than live delivery, so backfill load cannot degrade real-time traffic (Q155).

### Q194. Chat, notifications and live dashboards - one tier or three `[A]`

**My recommendation: one connection tier, three logical channels.**

The connection tier - authentication, WebSocket/SSE termination, heartbeats, subscription management, reconnect and backfill mechanics, routing (Q185) - is expensive to build well and identical for all three use cases. Building it three times means three sets of the same subtle bugs: reconnect storms, half-open connections, sequence handling, deployment drain. It also means a mobile client holding three connections, which is a battery and reliability problem, and three separate scaling and on-call stories.

So: **one gateway** that multiplexes logically-separated subscriptions over a single physical connection per client, with per-channel sequence numbers and per-channel delivery semantics.

**What must stay separate, because the requirements genuinely differ:**

| | Chat | Notifications | Dashboards |
| --- | --- | --- | --- |
| Durability | Must never lose a message; durable log, receipts, backfill | Durable inbox, plus mobile push for offline (Q190) | Ephemeral - the latest value is all that matters |
| Ordering | Strict per conversation | Per user, loose | Irrelevant; supersede |
| Backfill | Full history paging (Q193) | Unread inbox on connect | Current snapshot only |
| Fanout | Per conversation members | Per user | Per subscribed metric, broadcast to many |
| Rate | Bursty, low volume per channel | Low | High, continuous, and safely droppable |

Those differences live in the **publishing and storage layer**, not the connection layer: chat gets a durable per-conversation log, notifications get a durable inbox plus a push bridge, dashboards get a fan-out from a metrics stream with conflation (drop intermediate values and send the latest - crucial, because a dashboard subscriber that falls behind must never build an unbounded backlog).

**The argument for three tiers, which I would acknowledge:** isolation. A dashboard broadcast storm should not degrade chat delivery. I would address that with per-channel-class quotas, separate publisher paths, and backpressure with conflation inside the shared gateway (Q106) - and I would keep *physical* separation as an option by making the gateway deployable as separate fleets with the same code, so that if the isolation argument wins later, it is a deployment change rather than a rewrite. That is the answer I would give: one codebase, one protocol, configurable into one or three fleets.

*Hook: a real-time tier you built or consolidated, and the isolation problem you had to solve.*

---

## 13. Search, ranking and the analytics path

### Q195. When a design needs a dedicated search system

The three triggers:

1. **Relevance ranking is the requirement.** The user types words and expects the *best* results, not the matching ones. That needs tokenization, stemming, stop words, synonyms, field boosting and a scoring function (BM25). `LIKE '%term%'` cannot rank, and cannot use an index for a leading wildcard either.
2. **Full-text scale beyond what the database's own index handles comfortably.** PostgreSQL's GIN + `tsvector` is genuinely good to millions of documents; beyond tens of millions with high query rates, or with heavy faceting and aggregation on the same query, a dedicated inverted index earns its place (`../06-database/answers.md` Q214).
3. **Query shape diversity** - arbitrary combinations of free text, filters, ranges, geo distance and facet counts in one request, with sub-100 ms latency. A relational optimizer cannot cover the combinatorial space with indexes; an inverted index with doc-value columns can.

A fourth trigger that is really an architectural one: **the read workload must not touch the transactional store** (Q65). Search traffic is bursty, unpredictable and often much higher volume than writes, and isolating it is worth a derived store on its own.

When *not* to: prefix matching, a handful of filters, modest volume, or "search" that is really a filtered list. Those belong in the database, and adding a search cluster for them is a second operational surface for no benefit (Q57).

### Q196. Autocomplete for 100 million queries a day

**Scale first.** `10^8 / 86,400 ≈ 1,200 QPS` average, 3-5x at peak, so ~5,000 QPS. But autocomplete fires **per keystroke**, so a 15-character query is up to 15 requests - the real number is closer to 20,000-50,000 QPS unless the client debounces. Debouncing at 100-150 ms and requiring 2-3 characters minimum is the first design decision, and it cuts load by 5-10x for free.

**Latency budget: 100 ms end to end** (above that it feels laggy, and the user has typed another character anyway). That decomposes into ~30 ms network, ~10 ms edge, ~20 ms service, leaving ~20 ms for the lookup and 20 ms of slack. This budget forbids a database query per keystroke and forbids any fanout.

**Data structure.** A **trie with precomputed top-K completions at each node** - each prefix node stores its 10 best suggestions with scores, so a lookup is a prefix walk and a return, no ranking at request time. Held entirely in memory (a few hundred MB for tens of millions of prefixes), replicated to every service instance so there is no network hop. For fuzzy matching, add a small edit-distance tolerance via a finite-state transducer or an n-gram index; for personalization, blend a small per-user recent-query list client-side rather than server-side.

Alternative implementations worth naming: Redis sorted sets keyed by prefix (`ZRANGEBYLEX`), simple and adequate to moderate scale; or Elasticsearch's completion suggester, which is an FST and is the buy-not-build answer.

**The update path** is offline, and that is the key insight: query logs → aggregate counts over a rolling window → score (frequency, recency decay, conversion rate, business boosts) → filter (blocklist, profanity, PII, spam) → rebuild the trie → publish as a versioned artifact → instances load it and swap atomically. Rebuild every 15 minutes to hourly; nothing about autocomplete needs to be real time except newly trending terms, which can be injected as a small overlay layer merged at query time.

**Caching:** short prefixes (1-3 characters) cover the overwhelming majority of traffic and are perfectly cacheable at the CDN with a 60-second TTL. That alone can absorb 70 percent of requests before they reach a service.

### Q197. Keeping a search index in sync

Ranked, best first:

1. **CDC from the database's log** (logical decoding, binlog). Cannot miss a change, because it reads the same log that defines the data; captures writes from *any* source including manual SQL and other services; replayable from a position; and requires no application change. Cost: a pipeline to operate, schema coupling to the physical tables, and the need to reconstruct domain documents from row-level changes.
2. **Outbox / domain events** written transactionally with the state change (`../03-microservices/answers.md` Q92). Also cannot lose a change, and the events are domain-shaped, so the indexer's job is simpler and the coupling is to a contract rather than to a table. Cost: application discipline - every write path must produce the event, and a script that bypasses the application silently breaks it.
3. **Periodic full reindex.** Simple, self-healing, and mandatory as a backstop regardless of what else you do. On its own it gives freshness measured in hours and costs a full read of the dataset each cycle.
4. **Dual write** (write to the database and the index in the same request). Last, and I would not ship it: there is no transaction across the two, so a partial failure leaves permanent drift, and it makes every write depend on the index's availability. It is the option that looks simplest and creates the most incidents.

**Detecting and repairing drift** - non-optional, because all of the above drift eventually:

- **Continuous count comparison** by bucket (per day, per tenant, per type) between source and index. Cheap and catches gross divergence.
- **Rolling checksum sweep**: walk the source in id order, compare `(id, version, hash_of_indexed_fields)` against the index, in bounded batches so a full pass completes daily or weekly. Emit a metric for the number of mismatches - the target is zero and any non-zero value is a bug to be found, not a number to be tolerated.
- **Repair by re-emitting** the affected documents through the normal indexing path, so the repair uses the same code as the steady state.
- **Version-guarded writes into the index** (only apply if the incoming version is newer), so out-of-order and replayed updates cannot resurrect stale data.
- **A tested full-rebuild procedure** into a new index alias with an atomic swap, with its duration measured - that duration is your recovery time for a corrupted index.

### Q198. Search returns a deleted document `[T]`

Every layer this could come from, and the fix at each:

1. **The indexing lag itself.** The delete has not yet propagated. Fix: bound and monitor the lag (Q118), and for deletes specifically, prioritize them over updates in the pipeline - a stale *presence* is worse than a stale field.
2. **The delete never produced an event.** A `DELETE` executed by a script, an admin tool, or a cascade that the application layer never saw, so no outbox row was written. Fix: CDC instead of application events (Q197), or a database trigger for the outbox, plus the reconciliation sweep that would have caught it.
3. **Soft delete not reflected in the index filter.** The row still exists with `deleted_at` set, the indexer maps it as a normal document, and the query has no `NOT deleted` clause. Fix: filter at index time (do not index deleted documents) *and* at query time (belt and braces), and make the index-time rule the primary one.
4. **The search engine's own visibility semantics.** Elasticsearch is near-real-time: a delete is recorded but not visible until the next refresh (default 1 s), and until segments merge, the document is a tombstone that is filtered on read. Fix: know the refresh interval, use `refresh=wait_for` for the rare case where the caller must observe its own delete, and never assume a 200 from the index API means visible (`../06-database/answers.md` Q215).
5. **A cached search response.** The query result was cached at the CDN, gateway, or in the application, and the cache does not know about the delete. Fix: short TTLs on search results, and invalidate by tag on entity change (Q78) - and accept that search results are the wrong thing to cache for long.
6. **A replica of the index that has not caught up**, or a cross-region index replica. Fix: staleness-aware routing (Q173).
7. **The result set is served from a stored cursor/scroll context** created before the delete. Fix: bound cursor lifetime and treat pagination as a snapshot with a stated expiry (Q36).
8. **Permission change rather than deletion** - the document exists but the user has lost access, and authorization is applied at index time rather than query time. Fix: enforce access at query time via a filter derived from the caller's identity (Q253), never by baking a snapshot of permissions into the document.

**The general defense**, which I would say last: the search index must never be the authority for *existence*. Search returns candidate ids; the read path fetches the current state from the system of record (or a strongly-consistent cache of it) and drops anything gone. That costs a batched lookup and eliminates the entire class of problem.

### Q199. Ranking as a system

**The retrieval-then-ranking split.** Retrieval selects a candidate set of hundreds to low thousands from millions of documents, using cheap, index-friendly signals (term match, filters, an embedding ANN lookup). Ranking then scores those candidates with an expensive model that can afford per-item features. Sometimes there is a third stage - a heavy reranker over the top 50 or 100.

The reason for the split is pure economics: a model costing 1 ms per item is unusable over 10 million documents and trivial over 200.

```
10,000,000 docs
  → retrieval (inverted index + ANN): 1,000 candidates      ~20 ms
    → lightweight ranking (linear/GBDT, cached features): 200      ~15 ms
      → heavy reranking (cross-encoder / LTR model): 20-50         ~30 ms
        → business rules, diversity, dedup, freshness              ~5 ms
```

**Feature availability at request time** is the constraint that shapes the whole thing. Features come in three classes: **static** (document attributes, precomputed popularity, embeddings) - materialized into the index or a feature store, free at request time; **contextual** (query, device, time, locale) - free; **user features** (history, affinities, recent behavior) - require a lookup, so they must come from a low-latency feature store with a strict timeout and a default, or be pushed into the client's request. Anything requiring a join or an aggregation at request time is not a feature, it is an outage waiting for peak traffic. So: precompute, cache in a feature store, and enforce a budget with a fallback to a query-only ranking if the feature lookup is slow.

**The latency budget per stage** must be enforced independently, with each stage degradable: if the reranker is slow or unavailable, return the lightweight ranking; if the feature store is slow, rank without user features. The result is worse but present - a soft dependency (Q163). The other essential property is **determinism for debugging**: log the candidate set, the feature values and the scores for a sampled fraction of queries, because "why did this rank here" is the most common question and it is unanswerable retrospectively without it.

### Q200. Faceted search and aggregations

**What is expensive:** a facet count is an aggregation over the *entire* matching set, not the returned page. Computing "142 results in Electronics, 87 in Books" over a 5-million-document match means touching 5 million documents' field values. Cost scales with match-set size and with the number of facet fields and their cardinality; high-cardinality facets (brand, seller, tag) are the killers, and nested or hierarchical facets multiply again. On top of that, facet counts cannot be cached per user if the match set depends on permissions.

**How you make it affordable:**

1. **Doc values / columnar field storage** rather than reading source documents - this is what makes engine-side faceting feasible at all, and it means the fields to be faceted must be declared and typed at index time.
2. **Cap the facet cardinality** you return: top 10-20 values plus "show more" that runs a targeted second query. Nobody needs 40,000 brands in a sidebar.
3. **Approximate counts** for high-cardinality facets - a cardinality sketch, or a sampled count with an "about" label. Product-acceptable and orders of magnitude cheaper.
4. **Precompute for common navigation paths.** Category landing pages and popular filter combinations have their facet counts materialized on a schedule, so the hottest 1 percent of requests do no aggregation at all. This is the highest-value optimization because facet traffic follows a steep power law.
5. **Restrict the match set first.** Facets computed after a category filter are cheap; facets over "everything" are not - so the UI should not offer an unfiltered facet panel over the entire catalogue.
6. **Separate the counting workload** onto its own replicas or a separate cluster if facet load competes with query latency.
7. **Drop counts under load.** Facets are a soft dependency: show the facet *values* without numbers when the system is stressed. Users barely notice, and it is a large capacity lever.

### Q201. Personalized results and caching

The layering, from most to least cacheable:

1. **The candidate retrieval, unpersonalized** - the top N results for `(query, filters, locale)` with no user signal. Highly cacheable, shared across all users, and this is the expensive part of the pipeline. A 60-second TTL here absorbs most of the load.
2. **Static ranking features and document data** - cached per document, shared, long TTL, invalidated on document change.
3. **The user's feature vector / affinity profile** - cached per user, TTL of minutes, updated asynchronously from behavior. Not per query.
4. **The personalized reranking** - **not cacheable** in general, because it is a function of (query, user, moment). It is also the *cheap* part, operating over 200 candidates.
5. **The rendered response** - cacheable only per user with a very short TTL, and worth it only for repeated identical requests (a user paging back and forth).

So the pattern is: **cache the expensive shared computation, compute the cheap personal part per request.** That gives a high hit ratio on the costly stage while keeping personalization real.

Two refinements. **Cohort caching** (Q79): if personalization is coarse - segment, region, tier, A/B bucket - cache the personalized result per cohort rather than per user, turning millions of variants into dozens. **Precomputation for logged-in users**: for feed-like surfaces where the query is implicit, compute the personalized set asynchronously and serve it from a per-user cache, refreshed on activity - which converts a request-time ranking problem into a background job (Q186).

The correctness caveat, as always: the cache key must include every input that changes the result, including the permission scope (Q80), or personalization becomes a data leak.

### Q202. The analytics path, with staleness marked

```
OLTP write
  │  [1] transaction commits
  ▼
WAL / binlog ──[2] CDC lag──▶ Kafka ──[3] consumer lag──▶ Raw landing zone (S3/Parquet)
                                                              │
                                                       [4] batch window
                                                              ▼
                                                    Transform (dbt / Spark)
                                                              │
                                                       [5] model build interval
                                                              ▼
                                                    Warehouse marts
                                                              │
                                                       [6] BI cache / extract
                                                              ▼
                                                        Dashboard
                                                              │
                                                       [7] browser refresh
```

Staleness is introduced at every numbered point:

1. **Commit visibility** - sub-millisecond; negligible but real for read-your-writes.
2. **CDC capture lag** - typically 100 ms to seconds; grows to minutes under write bursts or if the connector restarts.
3. **Consumer/ingest lag** - seconds; the landing zone usually batches into files, so add the file-close interval (1-15 minutes) which is often the dominant term.
4. **Batch scheduling** - the big one. An hourly job means up to 60 minutes of staleness before it even starts.
5. **Transformation runtime** - minutes to hours, and dependency chains multiply it: a mart three layers deep waits for all its ancestors.
6. **BI caching / extracts** - many BI tools cache aggressively or maintain extracts refreshed on their own schedule, adding minutes to hours that the data team does not control and often does not know about.
7. **The browser** - a dashboard open since this morning is showing this morning's data. Users read a stale screen and report a data bug.

The two lessons I would draw. First, **end-to-end freshness is the sum of every stage, and it is almost always dominated by the batch interval and the BI layer**, not by the pipeline engineering everyone focuses on. Second, freshness must be **displayed** - every dashboard shows "data as of HH:MM" computed from a watermark carried through the pipeline, not from the query time. That single change eliminates the largest category of analytics support tickets.

### Q203. Lambda versus Kappa in 2026

**Lambda** ran two pipelines - a batch layer for correct, complete historical results and a speed layer for low-latency approximate ones - with a serving layer merging them. It solved a real problem and created a worse one: the same business logic implemented twice, in two technologies, that must agree. They never do, and every discrepancy is a multi-day investigation.

**Kappa** ran one streaming pipeline and reprocessed history by replaying the log through the same code, eliminating the duplication.

**Is the distinction still useful?** As a framework for choosing an architecture, no - it is a historical artifact from a period when batch and streaming needed different engines. What survives is the *underlying question*, which is real and permanent: **how do you reprocess history with the same logic that handles live data?**

**What I actually build in 2026:**

- **One transformation logic, expressed once.** Modern engines (Flink, Spark Structured Streaming) run the same job in streaming and batch modes, and warehouse-native tools (dbt on an incremental model, or a materialized view in a lakehouse) express the logic once in SQL and let the platform decide.
- **A lakehouse table format** (Iceberg or Delta) as the serving substrate, which gives ACID appends, time travel, and the ability for a streaming writer and a batch backfill to target the same table safely. That is what dissolved the lambda problem - not a new architecture, but a table format that both layers can write to.
- **Streaming only where latency requires it** (Q110), which in most organizations is a small minority of pipelines. The default is incremental batch every 5-15 minutes, which is cheaper, simpler, easier to reason about, and indistinguishable from streaming for almost every dashboard.
- **Backfill as a first-class, tested operation** - the same job with a date range parameter, idempotent on its output partitions.

So my answer in an interview: I would not describe a design as lambda or kappa; I would say "one logic, one table format, incremental by default, streaming where the SLA demands it, and a backfill path that uses the same code."

### Q204. Real-time and historical over the same data

The standard shape is a **two-path read with a merge at query time**:

```
events → stream ──▶ real-time store (last minutes-hours, in memory / OLAP with fast ingest)
             └────▶ durable log ──▶ batch/compaction ──▶ historical store (columnar, partitioned)

query → router: [t-∞ , t-boundary] from historical
                (t-boundary , now]  from real-time
                merge, dedup, return
```

**Where the two paths meet** is the whole design problem, and the mechanisms that make it correct:

1. **A single, explicit boundary watermark.** One value, published by the compaction process, meaning "historical data is complete up to here". The router reads the boundary and splits the query at it. Never overlap by guesswork, and never let each path decide independently.
2. **Idempotent, deduplicable records.** Both paths may contain the boundary period during a handover, so records carry a unique id and the merge deduplicates. This makes the handover safe rather than exact.
3. **The same schema and the same semantics** on both sides, ideally the same transformation code, or you get the lambda divergence problem (Q203).
4. **Monotonic boundary advancement** with retention overlap: the real-time store keeps data for meaningfully longer than the compaction interval, so a delayed compaction does not create a hole.
5. **Late-arriving data policy** - if an event arrives for a period already compacted, either rewrite that partition (Iceberg/Delta make this feasible) or route it to a correction table merged at read time. Decide which, and state it.

Systems that implement this internally - Druid, Pinot, ClickHouse with a real-time and historical tier - are worth naming, because the right answer is often to use one of them rather than to build the router. But the design must still choose the boundary semantics and the late-data policy, since those are product decisions.

### Q205. "Real-time analytics" at three price points `[A]`

**First, establish what they mean.** I ask four questions: (1) What decision will you make from this number, and how quickly must you act on it? (2) If the number were 60 seconds old, what would go wrong? (3) Is anyone watching this screen continuously, or is it checked a few times a day? (4) Does the number need to be exact, or directionally correct? Nine times out of ten, "real time" means "not yesterday" - the current pipeline is a nightly batch and anything under an hour would delight them.

**Three designs:**

| | Latency | Approach | Cost |
| --- | --- | --- | --- |
| **A - Micro-batch on the warehouse** | 5-15 minutes | CDC into the lake, an incremental dbt model on a 5-minute schedule, a BI tool with caching disabled and a freshness label (Q202) | Low - reuses everything you already have; a few hundred dollars a month of extra compute |
| **B - Real-time OLAP store** | 1-10 seconds | Stream events (and CDC) into Druid/Pinot/ClickHouse; the dashboard queries it directly; historical tier for older data (Q204) | Medium-high - a new stateful cluster, a schema per use case, and an on-call story |
| **C - Precomputed streaming aggregates** | Sub-second | Flink or Kafka Streams maintaining the specific aggregates in a low-latency store, pushed to the browser over SSE (Q181) | High for generality, low for a fixed set - cheap if there are five metrics, very expensive if users want ad-hoc slicing |

**How I would recommend:** start with A, always. It is a week of work, it uses the existing platform, and it satisfies the actual requirement in most cases. Move to B when users need to *explore* recent data interactively (arbitrary group-bys over the last hour), which is the genuine justification for a real-time OLAP store. Use C only for a small, fixed set of high-visibility metrics - an operations wall display, a live event counter - where sub-second matters and the aggregates are known in advance.

The trap to name: **C looks cheapest because the first metric is easy, and it is the most expensive at metric number twenty**, because each one is a bespoke streaming job. B's cost is front-loaded and then flat, which is the opposite shape. Choosing between them is a question about how many metrics and how much ad-hoc exploration, not about latency.

### Q206. Event collection at scale

```
Client SDK ──batch, compress, retry──▶ Collector tier (stateless, edge)
                                          │ validate against registry
                                          │ enrich (geo, ts, session)
                                          ▼
                                       Kafka (raw topic)
                                          │
                                   ┌──────┴──────┐
                                   ▼             ▼
                            Landing zone     Real-time consumers
```

**Client SDK** responsibilities, which determine whether the whole system works: local buffering with a bounded queue and disk persistence so events survive an app restart; **batching** (send every N events or T seconds, not per event - this is the difference between 100,000 QPS and 2,000 QPS); compression; a client-generated event id for deduplication; a monotonic per-device sequence number so gaps are detectable; exponential backoff with jitter; and a hard cap so a broken client cannot flood you. Also a kill switch - a server-controlled configuration that can reduce a client's send rate or disable event types remotely, because you will need it.

**Collector tier**: stateless, horizontally scaled, placed at the edge so the client's round trip is short. It authenticates (or at least attributes) the sender, validates the payload against the schema registry, rejects or quarantines invalid events rather than poisoning downstream, enriches with server-side truth (received timestamp, IP-derived geo, resolved user id) - never trusting client timestamps as authoritative, because device clocks are wrong - and writes to the log. It must be able to accept-and-drop under extreme load in preference to failing, since analytics events are best-effort (Q163).

**Schema registry** in the path is what keeps a data platform from decaying: every event type has an owner, a schema, and enforced compatibility, checked in CI and again at the collector (Q115). Without it you get 400 variants of a "click" event and a warehouse nobody trusts.

**The sampling decision:** sample when volume is high and statistical accuracy suffices - high-frequency UI interactions, performance traces, log-like events. Do **not** sample events that feed billing, funnels with small denominators, security auditing, or per-user features. When you sample, do it **deterministically by a stable key** (hash of user or session, not random per event) so a user's journey is either fully present or fully absent - random per-event sampling destroys funnel analysis. Always record the sampling rate with the event so downstream can weight correctly, and prefer **head-based sampling at the SDK** for cost (the event never travels) with **tail-based sampling at the collector** where you need to keep all events for interesting sessions (an error, a conversion).

### Q207. Metrics storage

**Why a time-series database over a relational one:** the workload is an append-only firehose keyed by `(series, time)`, queried as range scans and aggregates, and expired by age. A row store pays B-tree maintenance on every insert, stores each sample as a full row with per-row overhead, cannot exploit the fact that consecutive timestamps and values are highly compressible, and deletes by age as a mass `DELETE`. A TSDB stores samples column-wise per series with **delta-of-delta encoding on timestamps and XOR encoding on float values**, achieving 10-20x compression (Gorilla-style, roughly 1-2 bytes per sample versus 16+), organizes data into time-bounded blocks so expiry is a block drop, and indexes series by label set (Q59).

**Cardinality is the real limit**, and it is the single most important thing to say. A "series" is a unique combination of metric name and all label values, and every series has its own index entry and in-memory chunk. Cardinality **multiplies**: 100 endpoints x 20 status codes x 50 instances x 10 regions = 1,000,000 series from one metric. Adding a single high-cardinality label - user id, request id, session id, full URL path, container id - multiplies by its cardinality and is how monitoring systems die. Memory per active series in Prometheus is on the order of a few KB, so a million series is gigabytes of resident memory before any query runs, and query cost scales with the number of series touched.

The controls: **never put an unbounded value in a label** (put it in a log or a trace instead); bound path labels by templating them (`/users/{id}`); enforce a cardinality budget per team with an alert on series growth rate; drop or aggregate labels at the ingest layer (relabelling) rather than at query time; and use exemplars to link a metric to a trace instead of adding identifying labels.

**Downsampling policy:** raw resolution (10-15 s) for 7-15 days, 1-minute rollups for 30-90 days, 5-minute or hourly for 13 months, with the rollups storing min/max/sum/count (not just the mean, or you lose the ability to compute anything correctly, and percentiles must be stored as histograms rather than pre-aggregated quantiles - averaging percentiles is meaningless). Expiry by block drop, and the retention tiers chosen from what people actually query: incident investigation needs raw for days, capacity planning needs hourly for a year.

### Q208. The data platform boundary `[A]`

**What product teams own:**

- **The events and datasets they produce**, as a *contract*: a versioned schema, documented semantics, a declared owner, an SLO for freshness and completeness, and compatibility guarantees (Q41). They are producers of data products, not just of application state.
- **The quality of their source data.** A field that is null 40 percent of the time is their defect, not the platform's.
- **The domain marts built from their own data**, if they choose to - the platform provides the tooling and the compute, the team provides the domain logic. This is what "data mesh" gets right: domain knowledge cannot be centralized, and a central team writing transformations for 30 domains becomes the bottleneck and the single biggest source of wrong numbers.

**What the platform owns:**

- **Ingestion, storage and compute** as self-service infrastructure: the CDC and event pipelines, the lake and table format, the warehouse, the orchestration engine, the BI tooling, the notebook environment.
- **The contract mechanism itself** - the schema registry, compatibility enforcement in CI, lineage capture, the data catalogue, freshness and quality monitoring as a framework teams plug into.
- **Cross-domain conformed dimensions** - the small set of entities everyone joins on (customer, product, date, region). This is deliberately small; the platform owns the shared vocabulary, not everyone's business logic.
- **Governance and compliance** - PII classification, access control, residency, retention, audit, and cost attribution.
- **Reliability of the platform's own SLAs.**

**How contracts are enforced** - the part that decides whether this works:

1. **In CI, at the producer.** A schema change that breaks compatibility fails the producer's build. This is the only enforcement point that reliably prevents breakage, because it stops the change before it exists.
2. **At the boundary, at runtime.** The collector or connector validates and quarantines non-conforming records into a dead-letter dataset with an alert to the producing team - never silently dropping and never silently accepting.
3. **Continuous quality tests as code** (dbt tests, Great Expectations style) run on every load: not-null, uniqueness, referential integrity, range and freshness. A failing test blocks the downstream build rather than publishing bad data, and it pages the *producing* team.
4. **Lineage plus consumer registration**, so a producer can see who depends on a field before changing it, and so a breakage has a blast-radius map (Q47).
5. **Cost and usage attribution** back to teams, which is what makes the incentives work - a team that pays for its own storage and compute prunes its own unused datasets.

**What I would explicitly avoid:** a central team writing all the transformations (bottleneck), a canonical enterprise-wide data model (never converges), and letting consumers build on raw tables directly - because that creates a coupling to the producer's physical schema that nobody can see and everybody breaks.

*Hook: a data contract you introduced, and the breakage it prevented or exposed.*

---

## 14. AI and ML in the request path

### Q209. What changes with an LLM in the design

Five properties, each with a design consequence:

1. **Latency is high and the distribution is extremely heavy-tailed.** A 2-second p50 with a 30-second p99 is normal, and it is driven by output length, which you cannot know in advance. Consequence: this cannot sit inside a 500 ms synchronous budget; it needs streaming, async, or a dedicated timeout regime (Q210).
2. **Output is non-deterministic.** The same input yields different outputs, so you cannot write an exact-match test, cannot cache naively on semantics, and cannot reproduce a bug from an input alone. Consequence: you must log inputs, outputs, model version and parameters, and testing becomes statistical (Q221).
3. **Cost is per token and variable per request**, by two or three orders of magnitude between a short and a long interaction. Consequence: cost is a *runtime* concern requiring metering, budgets and per-tenant quotas, not a capacity-planning concern (Q212).
4. **The dependency is usually external, rate-limited, and has its own availability - often lower than yours.** Consequence: it is a soft dependency with fallbacks, or your SLO is capped by theirs (Q224).
5. **The output can be wrong in ways that are plausible and unverifiable**, including harmful or leaking. Consequence: validation, guardrails and human review become part of the request path, and there must be a defined behavior when the output fails validation (Q220).

A sixth worth mentioning: **the model itself is a version that changes underneath you.** A provider deprecating or silently updating a model changes your product's behavior with no deploy on your side, which means model version pinning, an evaluation suite run against candidate versions, and a rollback path (Q214).

### Q210. Serving a 2-second p95 with a 30-second tail

The tail is the design problem, and it forces four things:

1. **Stream the response.** Token-by-token streaming over SSE turns a 20-second wait into a 400 ms time-to-first-token, and the perceived latency becomes TTFT, not total. This is the single most valuable change, and it means the client contract must be streaming from day one (Q211). Measure and SLO on **TTFT** and **inter-token latency** separately from total duration - a single "latency" metric tells you nothing useful here.
2. **Do not hold a thread.** At 30 seconds per request and even 100 concurrent requests, Little's Law gives 100 in-flight requests each occupying a connection for half a minute. A thread-per-request model needs 100 threads doing nothing but waiting; at 1,000 concurrent it is untenable. So: non-blocking IO end to end, or a dedicated bulkheaded pool that cannot starve the rest of the service (Q155). This is the most common architectural mistake in LLM integrations - dropping a 30-second call into a servlet thread pool sized for 50 ms work.
3. **Timeouts and budgets sized for the tail, and separated from everything else.** A 60-second timeout on this path with its own concurrency limit, its own circuit breaker, and its own queue - never sharing pools with fast endpoints. Deadline propagation matters: if the user has gone away, cancel the upstream call (both to save money and to free capacity), which requires the client abort to actually propagate.
4. **UX that makes 20 seconds acceptable:** stream, show progress or intermediate steps, allow cancellation, and for anything above ~30 seconds move to the async job pattern (Q37) with a notification rather than an open connection.

Additional levers on the latency itself: a smaller/faster model for simple requests (routing, Q214), shorter prompts (prompt tokens cost latency too), constrained output length, caching (Q215), and speculative or parallel decoding if you host the model yourself.

### Q211. Three inference contracts

**Synchronous request-response.** `POST /v1/summarize` returns the full result. Simple, cacheable, easy to test. Use only when the output is short and bounded (a classification, an extraction, a score) so the latency is predictable - typically under 2 seconds. The client contract is ordinary HTTP with a generous timeout and a documented `Retry-After` on 429/503.

**Streamed.** `POST /v1/chat` with `Accept: text/event-stream`, returning SSE frames.

```
event: token   data: {"delta":"Hello"}
event: token   data: {"delta":" world"}
event: usage   data: {"prompt_tokens":812,"completion_tokens":140}
event: done    data: {"finish_reason":"stop"}
event: error   data: {"type":"upstream_timeout","retryable":true}
```

The contract must specify: that a 200 status does **not** mean success (an error can arrive mid-stream, after headers are sent - so the client must handle a terminal error event); that the client may cancel by closing the connection, and that cancellation stops billing; that a heartbeat/comment frame keeps intermediaries from timing out the connection; and that partial output may be all the client gets. Buffering proxies must be disabled on this route, which is an infrastructure requirement, not a detail.

**Asynchronous.** `POST /v1/jobs` → `202` + job id; result by polling or webhook (Q37). Use for long, expensive or batch work - document processing, bulk classification, agentic workflows (Q222) - and for anything above ~60 seconds. The contract adds a status resource, a terminal state, a result location with an expiry, and an idempotency key on submission.

The design rule: **choose by expected duration** - under 2 seconds synchronous, 2-60 seconds streamed, above that asynchronous - and expose the streaming variant as the default for anything conversational, because it is the only one that makes the tail tolerable.

### Q212. Token budgets, metering, enforcement

**Metering.** Every call records `(tenant, user, feature, model, prompt_tokens, completion_tokens, cached_tokens, latency, outcome)` at the gateway (Q214), because only the gateway sees all traffic. Token counts come from the provider's usage response - authoritative - with a local tokenizer estimate as a pre-flight check. This record is both the billing source and the debugging source, so it goes to a durable store with a retention policy, not just to metrics.

**Budgeting.** Convert tokens to money at the point of metering (a per-model price table, versioned) so every dashboard is in currency, not tokens - this is what makes the conversation with finance and with product possible. Set budgets at three levels: per tenant (contractual), per feature (so one experimental feature cannot consume the company's spend), and per request (a maximum prompt and completion length, which is also a safety control).

**Enforcement**, and this is where designs are usually thin:

1. **Pre-flight rejection.** Estimate the prompt tokens and cap `max_tokens` before calling. Reject requests whose estimated cost exceeds the remaining budget, with a clear error. This is the only enforcement that prevents the spend, since post-hoc accounting cannot un-spend it.
2. **Token-bucket rate limiting denominated in tokens, not requests** (Q91). A request-based limit is meaningless when one request can be 200x another. The bucket refills at `tokens_per_minute`, and a large request consumes proportionally - which also naturally protects the upstream provider's own TPM limit.
3. **Per-tenant concurrency limits** in addition to rate, because concurrency is what causes queueing and tail latency (Q231).
4. **A hard monthly cap with a soft threshold**: at 80 percent of budget, alert the tenant and the account owner; at 100 percent, degrade (smaller model, cached-only, or refuse) according to a policy agreed in advance, never silently. Silent overspend and silent cut-off are both incidents.
5. **Attribution down to the feature and the prompt version**, so when spend doubles you can point at the change. Without this, cost regressions are unattributable and therefore permanent.

The one number to have ready: at typical 2026 frontier-model pricing, a single richly-contextualized RAG request (8,000 prompt tokens, 500 completion) costs on the order of cents, so **a feature at 10 requests/second costs thousands of dollars a day**. Saying that arithmetic out loud is what makes the budgeting machinery obviously necessary rather than bureaucratic.

### Q213. A provider degrading at 11 a.m. daily `[T]`

Design so it is a non-event:

1. **Multi-provider routing with health-aware failover.** The gateway (Q214) holds two or three providers behind a common interface with per-provider circuit breakers and latency-based routing. When provider A's p95 crosses a threshold, traffic shifts to B automatically. This requires prompt portability - which is a real constraint, so prompts and output parsing must be written to work across models, and the evaluation suite must be run against each.
2. **The same model from multiple deployments.** For the same provider, use several regions or deployments (and, in Azure-style setups, both provisioned and pay-as-you-go capacity), so failover does not require a different model and therefore no behavioral change. This is usually the cheapest resilience available.
3. **Provisioned/reserved capacity for the baseline** and on-demand for the peak. A daily 11 a.m. degradation is a shared-capacity contention problem, and provisioned throughput is precisely the product that solves it. This is often the *correct* answer to the question, and it is a commercial fix rather than an engineering one - worth saying.
4. **Model tiering under pressure.** Route to a smaller, faster model when latency degrades, accepting lower quality for availability. The routing decision is by request class: simple classifications always go to the small model anyway (which is also a large cost saving), and the large model is reserved for requests that need it.
5. **Caching, including semantic caching** (Q215), which cuts the volume exposed to the provider at all.
6. **Queue and defer what can be deferred.** Non-interactive work (batch summarization, background enrichment) moves to an async path with a rate limiter that fills the trough and empties during the peak - so the interactive traffic gets the capacity.
7. **Degrade visibly rather than hang.** If all providers are slow, the feature returns a cached or template response with an honest message, and the rest of the product is unaffected because this is a soft dependency (Q163).
8. **Measure it and hold the vendor to it.** Per-provider latency and error dashboards, an SLO on the *feature*, and the daily pattern documented and raised with the vendor - because a reproducible daily degradation is a contractual conversation, not just an engineering one.

### Q214. Model gateway design

A single internal service (or sidecar) that every AI call goes through. What sits in it:

| Concern | Why it belongs here |
| --- | --- |
| **Provider routing and failover** | One place implements multi-provider health, retries, and model tiering (Q213) |
| **Model version pinning and rollout** | Requests name a *logical* model ("summarizer-v3"); the gateway maps it to a concrete provider model. That mapping is a config change with canary and rollback - which is how you survive a provider deprecation |
| **Prompt versioning and templating** | Prompts are artifacts with versions, owners and evaluation results. Storing them here means a prompt change is auditable and rollable-back, not a code deploy scattered across services |
| **Caching** | Exact and semantic caching in one place, with a shared hit-rate benefit across services (Q215) |
| **Metering, budgets and quotas** | The only component that sees all traffic, so the only place these can be enforced (Q212) |
| **Rate limiting and concurrency control per tenant and per feature** | Protects both your system and the upstream provider's limits |
| **Guardrails** | Input filtering (prompt injection heuristics, PII redaction) and output filtering (safety, schema validation) applied uniformly (Q220) |
| **Audit and observability** | Full request/response logging with retention and access control, token accounting, latency and TTFT metrics, trace correlation, and sampled traces for evaluation |
| **Secret management** | Provider API keys live here, never in 30 services |

The architectural argument: without a gateway, every one of these concerns is reimplemented per team, inconsistently, and the organization has no answer to "what are we spending", "which prompt version produced this output", "can we switch providers", or "is PII leaving our network". With it, those become configuration.

The risks to acknowledge: it is on the critical path, so it must be simple, horizontally scalable and statically stable (Q158) - and it must not become a place where business logic accumulates (Q90). It also adds a hop (a millisecond or two, irrelevant against a 2-second call). I would run it as a thin, well-tested service with its own SLO, and expose it through a client library so teams get sensible defaults.

### Q215. Caching LLM responses

| Type | How | Hit-rate expectation | Correctness risk |
| --- | --- | --- | --- |
| **Exact match** | Hash of (model, params, full prompt) → response | Low in conversational use (1-5 percent), high in narrow automated use - classification, extraction, enrichment over repeating inputs (30-70 percent) | Essentially none, provided every input is in the key - including system prompt, temperature, tools and model version. Miss one and you serve a response generated under different rules |
| **Normalized match** | Canonicalize first: lowercase, trim, collapse whitespace, strip punctuation, sort independent fields | Adds a few points over exact | Low, but normalization can merge inputs that differ meaningfully ("not" removal, case-sensitive codes). Normalize conservatively |
| **Semantic** | Embed the prompt, ANN lookup, accept if cosine similarity exceeds a threshold | Highest - 20-40 percent on real conversational traffic, more on FAQ-shaped workloads | **Real.** Two semantically similar questions can require different answers: "can I cancel my order" versus "can I cancel my subscription" may embed closely and have different answers. And any user-specific or time-specific content cached across users is a correctness and privacy failure |

Additional layers worth naming: **prefix caching** offered by providers (a long, stable system prompt is cached server-side, cutting cost and TTFT substantially - often the single biggest cost win in a RAG system), and **caching the retrieval results** rather than the generation, which is safer and still removes most of the latency.

**How I would use them:** exact and normalized caching on by default at the gateway for all traffic; provider prefix caching exploited by structuring prompts with the stable content first; semantic caching enabled selectively per feature with a **high** similarity threshold, and never for a request whose response depends on the user, their permissions, their data, or the current time. The cache key must include tenant and permission scope wherever the response could be user-specific (Q80) - a semantic cache shared across tenants is a data leak with a plausible-sounding rationale.

And one measurement discipline: track the **quality** of cache hits, not just the rate. Sample cached responses through the evaluation suite (Q220), because a semantic cache silently degrading answer quality is invisible in every ordinary metric.

### Q216. Ingestion and indexing for 10M documents with daily updates

```
Sources ──▶ Crawl/pull (per-source connector, incremental by cursor or webhook)
   │
   ▼
Raw store (S3, immutable, content-addressed) ── content hash → dedup
   │
   ▼
Parse & extract (PDF/Office/HTML → text + structure + metadata)
   │
   ▼
Chunk (structure-aware, with overlap; carry parent references)
   │
   ▼
Embed (batched, versioned model) ──▶ Vector index + keyword index
   │                                        (metadata: acl, source, version, timestamps)
   ▼
Manifest / state table (doc → version, chunks, embedding model, status)
```

**Sizing.** 10 million documents averaging, say, 8 chunks each is **80 million vectors**. At 1,024 dimensions in float32 that is `80M x 1024 x 4 B = 328 GB` raw - which is the number that decides the architecture. With `float16` it halves; with product or scalar quantization it drops 4-8x to 40-80 GB, which fits in memory on a few nodes. So **quantization is not an optimization here, it is a requirement**, and the recall cost must be measured (Q217).

**Daily updates** are the part most designs get wrong:

1. **Incremental by change detection**, not full re-crawl: per-source cursors, webhooks where available, and a content hash so an unchanged document costs nothing. Re-embedding unchanged content is the largest avoidable cost in these systems.
2. **A manifest table as the source of truth** for what is indexed, at what version, with which embedding model. Every reconciliation, repair and rebuild is driven from it.
3. **Deletes and permission changes propagate promptly** - a document removed at the source must leave the index quickly, because a RAG answer citing a deleted or newly-restricted document is the failure mode that gets these systems switched off (Q253).
4. **Chunk-level versioning with atomic replacement**: write the new chunks, then flip the document's active version, then delete the old chunks. Never delete-then-insert, which creates a window where the document is missing.
5. **Embedding model versioning.** Vectors from different models are not comparable, so a model upgrade means re-embedding everything - 80 million embeddings, which at a realistic 1,000 embeddings/second is a day of compute and a real bill. Therefore: build into a **new index and swap by alias**, keep both during validation, and treat the model version as part of the index identity. Plan for this from the start, because it will happen at least annually.
6. **Backfill and steady state on separate capacity**, so a reindex does not degrade live retrieval.

**Throughput check for the initial build:** 80 million embeddings is the dominant cost. Batched at 256 per call with parallel workers, a few thousand embeddings/second is achievable, giving roughly 8-10 hours - so the initial index is a day, not a week, and the reindex path is an operation rather than a project.

### Q217. Vector search in a design

**The ANN trade-off triangle:** recall, latency and memory. You cannot have all three, and the design must state which you chose with a number.

| Index | Build cost | Query latency | Memory | Recall behavior |
| --- | --- | --- | --- | --- |
| **Flat (exact)** | None | O(n) - fine to ~100k vectors | Full vectors | 100 percent |
| **HNSW** | High (graph construction), incremental inserts OK | Very low, ~1-5 ms | High - graph plus vectors, 1.5-2x the vector size | 95-99 percent, tunable by `efSearch` |
| **IVF-PQ** | Moderate (needs training on a sample) | Low, tunable by `nprobe` | Low - quantized codes, 4-32x compression | 80-95 percent, degrades with aggressive quantization |
| **DiskANN-style** | High | Moderate (SSD-bound) | Low RAM, data on SSD | 90-95 percent, the choice when the index cannot fit in memory |

**Index build cost** matters more than people expect: HNSW construction over 80 million vectors is hours of CPU and cannot be trivially parallelized across a single index, and IVF requires a training pass. So a full rebuild is a scheduled operation, and incremental insert behavior (HNSW handles it; IVF needs periodic retraining as the distribution drifts) is a real selection criterion.

**The recall number you must state:** "recall@10 = 0.96 at p95 latency of 8 ms with `efSearch = 64`, measured against an exact-search ground truth on a 10,000-query sample." Without that measurement you do not know what your retrieval is missing, and in a RAG system missing retrieval presents as the model "not knowing" things it was given - which gets diagnosed as a model problem for weeks. I would make ground-truth recall a monitored metric, re-measured after every index or model change.

Two further design points: **filtered search** (restrict by tenant, ACL, date) interacts badly with graph indexes - pre-filtering breaks graph connectivity and post-filtering can return nothing, so the index must support native filtered traversal or you partition the index per tenant; and **hybrid retrieval** (Q219) recovers much of the recall lost to approximation, which is why nobody serious relies on vector search alone.

### Q218. A separate vector database alongside pgvector `[T]`

Justified when at least one of these is true:

1. **Scale beyond what pgvector serves comfortably.** pgvector with HNSW is genuinely good to roughly 10-50 million vectors on a well-provisioned instance, depending on dimension and latency target. At 80 million+ vectors (Q216), or with high query concurrency, a purpose-built store with quantization, sharding across nodes and disk-based indexes wins clearly.
2. **Memory economics.** Dedicated stores implement product quantization, binary quantization with rescoring, and tiered memory/SSD layouts. If quantization is what makes the index affordable (328 GB → 50 GB), and your relational engine does not offer it, that is a hard technical driver.
3. **Operational isolation.** Vector search is CPU and memory hungry and bursty; running it inside the transactional primary means an embedding query storm degrades your OLTP workload. Separating them is the same argument as separating search (Q65).
4. **Feature requirements** - native filtered ANN at high selectivity, multi-vector or late-interaction retrieval, built-in hybrid scoring and reranking, sub-second index updates at high write rates, or multi-tenant index isolation as a first-class concept.
5. **Independent scaling and rebuild.** Rebuilding an 80-million-vector index (Q216) inside your primary database is not something you want to schedule.

**When it is not justified** - and this is the more common case: fewer than a few million vectors; retrieval volume in the tens of QPS; a strong requirement to filter and join against relational data (which pgvector does natively and a separate store forces you to reimplement as a two-phase query); and a team that has one database and one operational competency. Adding a fifth datastore has the standing cost from Q57, plus a new synchronization and drift problem between the documents and their vectors.

My recommendation as a sequence: **start with pgvector**, measure recall and latency against real data and real volume, and move when a specific number crosses a specific threshold - not because a vector database is the expected answer. And if you do move, keep the manifest and the document metadata in PostgreSQL so the system of record stays singular (Q65).

### Q219. Hybrid retrieval and reranking

**Why hybrid.** Keyword (BM25) retrieval excels at exact terms, rare identifiers, product codes, names and negations - exactly where embeddings are weak, because an embedding of "error code E4021" is not reliably close to the document containing it. Vector retrieval excels at paraphrase and conceptual similarity, where keyword search fails entirely. Their failure modes are close to complementary, so combining them raises recall materially - typically the single largest quality improvement available in a RAG system, ahead of prompt engineering.

**How to combine.** Run both retrievers in parallel, then fuse. **Reciprocal rank fusion** is the pragmatic default: `score(d) = Σ 1/(k + rank_i(d))`, with `k ≈ 60`. It needs no score normalization (BM25 and cosine scores are not comparable), no tuning, and is robust. Weighted score fusion works if you normalize per retriever and are willing to tune the weight per corpus.

**Then rerank.** A cross-encoder scores each `(query, chunk)` pair jointly rather than comparing precomputed vectors, which is far more accurate and far more expensive - so it runs over the top 50-100 fused candidates and returns the top 5-10 for the prompt.

**Where the latency goes:**

```
keyword retrieval (top 100)      ~15 ms   ─┐ parallel
vector retrieval (top 100)       ~10 ms   ─┘
fusion (RRF)                      ~1 ms
cross-encoder rerank (100 pairs) ~80-200 ms   ← dominant
assemble prompt                   ~5 ms
LLM generation                  ~2,000 ms
```

So reranking is 5-10 percent of total latency but is the largest *controllable* pre-generation cost, and it is the thing to cut under load.

**What I cut under load, in order:** reduce the rerank candidate count (100 → 25, which loses little); switch to a smaller/distilled reranker; skip reranking entirely and use fused order; then reduce the retrieval `k` and the number of chunks in the prompt (which also cuts generation cost and latency). Each step is a config change, each is measurably worse in quality, and each is better than failing - so the degradation ladder should be explicit and tested, with the quality cost of each rung measured by the evaluation suite rather than guessed.

### Q220. Evaluation and guardrails in the request path

**What I check before returning**, in order of cost:

1. **Schema and format validation** (microseconds). If the output must be JSON matching a schema, validate it; on failure, retry once with the error fed back, then fail. Constrained decoding or a provider's structured-output mode makes this mostly unnecessary, and should be used where available.
2. **Deterministic policy checks** (microseconds to milliseconds): PII patterns in the output, blocked terms, links to disallowed domains, and - importantly - **leakage checks**: does the output contain content the user is not authorized to see, or the system prompt itself?
3. **Groundedness/citation check for RAG** (milliseconds to a second): every factual claim must map to a retrieved chunk. A cheap version verifies that cited chunk ids exist and were actually retrieved; a stronger version runs an NLI or LLM-as-judge check on the claim-to-evidence relationship.
4. **Safety classification** (50-300 ms): a small dedicated model for toxicity, self-harm, and jailbreak-output detection. Providers offer these; they are fast, and they are the main latency cost of guardrails.
5. **Business rules** - never give financial or medical advice, always include a disclaimer, never quote a price not in the retrieved context.

**On the input side**, before generation: prompt injection heuristics and classification, PII redaction before the text leaves your network, input length limits, and treating all retrieved content as **untrusted data**, not instructions (which is a prompt-structure discipline, not a filter).

**What it costs.** Deterministic checks are free. A safety classifier adds 50-300 ms; a groundedness check with a model adds 200 ms-1 s. Against a 2-second generation that is a 10-50 percent latency increase, which is why the design decisions are: run the cheap checks always; run model-based checks **in parallel with streaming** and be prepared to truncate the stream and replace the output if a check fails late (which requires the client contract to permit it - Q211); sample expensive evaluations offline rather than blocking every request; and tier the strictness by risk (an internal summarizer needs less than a customer-facing agent that can take actions).

**The behavior on failure must be specified**, not improvised: retry with a corrected instruction, fall back to a template or a retrieval-only answer, escalate to a human, or refuse with an honest message. And every block is logged with the reason, because a guardrail with no observability becomes either a silent quality problem or an unexplained user complaint.

### Q221. Testing a non-deterministic system

You cannot assert equality, so the suite is built from four layers:

1. **Deterministic contract tests.** Pin temperature to 0 (which reduces but does not eliminate variance), and assert on *structure* rather than content: valid JSON, required fields present, enum values in range, citations resolving to real chunks, no PII, length within bounds. These are fast, run on every commit, and catch the majority of regressions - most breakages are format breakages.
2. **A golden dataset with graded metrics.** 200-1,000 curated cases with expected properties, scored by automatic metrics: for retrieval, recall@k and MRR against known-relevant documents (this is the most objectively measurable and most valuable layer - Q217); for generation, exact-match or F1 on extraction tasks, and rubric-based **LLM-as-judge** scores for open-ended answers, validated against human labels on a sample so you know the judge is calibrated. Report aggregate scores with confidence intervals and **gate on a delta**, not an absolute: a build fails if the score drops more than X against the current baseline.
3. **Adversarial and regression cases.** Every production failure becomes a permanent test case - this is what makes the suite valuable over time. Plus a standing set of prompt-injection attempts, jailbreaks, out-of-scope questions (the answer should be "I don't know"), ambiguous inputs, and known-hard cases.
4. **Online evaluation.** A/B tests on real traffic with product metrics (task completion, escalation rate, thumbs-down rate, edit distance between the model's draft and what the user shipped), plus continuous sampling of production traffic through the offline judge so quality drift is detected without a release.

**The infrastructure that makes it work:** every prompt, model version and parameter set is a versioned artifact (Q214), every production request is logged with its full inputs and outputs, and the evaluation runs against a *pinned* model version so you can distinguish "our change regressed" from "the provider changed the model". Running the suite against a candidate provider model before switching is the control that turns a provider deprecation from an incident into a scheduled migration.

The honest framing for an interview: **you replace "is it correct" with "is it better than the previous version, on a defined distribution, by a margin larger than the noise"** - which is an experimental discipline, not a testing one, and it needs a statistician's caution about sample sizes.

### Q222. Agent orchestration in production

The controls that separate a demo from a production system:

1. **Step and budget limits.** A hard maximum on iterations (typically 10-25), on total tokens, on wall-clock time, and on money per run. An agent without these will loop, and the loop is expensive and invisible until the bill arrives. Termination must be explicit: success, budget exhausted, or explicit failure - never "the model stopped".
2. **Tools as real APIs with real contracts.** Each tool has a schema, a timeout, a retry policy, an idempotency key, and its own circuit breaker. Crucially, tools are **scoped by the user's permissions**, not the agent's service account - otherwise the agent is a privilege-escalation vector, and this is the single most important security property in the design. Write tools are separated from read tools and gated differently.
3. **State persistence per run.** The run is a durable resource: id, status, step history, tool calls and results, tokens spent, and the current plan. Persisted after every step, so a crash resumes rather than restarts, and so a human can inspect what happened. This is what makes the async job contract (Q211) the right shape for agents.
4. **Human-in-the-loop checkpoints.** A step classified as high-impact (spending money, sending external communication, modifying production data, anything irreversible) pauses the run and creates an approval task with the proposed action, its inputs, and the reasoning. The run resumes on approval, expires on timeout. Implementation is a durable state machine with a `WAITING_APPROVAL` state - not a blocking call.
5. **Idempotency across the whole run.** Every tool call is keyed on `(run_id, step_index)` so a resume or retry cannot double-execute a side effect (Q123). Without this, "resume after crash" means "charge the customer twice".
6. **Observability.** A trace per run with a span per step and per tool call, the full prompt and response retained (with a retention and access policy), token and cost attribution, and a queryable store - because the first question about any agent failure is "what did it actually do", and it is unanswerable without this.
7. **Sandboxing and blast radius.** Code execution in an isolated environment with no network and no credentials; file access scoped; egress filtered. Treat tool outputs and retrieved content as untrusted input to the next step (indirect prompt injection is the live threat).
8. **Kill switches**, per tool and per agent, so a misbehaving agent can be stopped without a deploy.

### Q223. GPU capacity

Why autoscaling GPUs is not like autoscaling web servers:

1. **Cold start is minutes, not seconds.** A GPU instance must be provisioned (and GPU capacity is frequently *unavailable* in a region, which is a failure mode web instances do not have), the container image is tens of gigabytes, and then model weights must be loaded into VRAM - 30 seconds to several minutes for a large model. So reactive autoscaling cannot follow a spike; you scale on a leading indicator (queue depth, or a schedule) with a warm pool, or you accept the gap.
2. **Batching is the throughput mechanism, and it conflicts with latency.** A GPU is efficient only when processing many sequences at once; **continuous (in-flight) batching** - adding and removing sequences from a running batch each decode step - is what makes serving economical, typically 5-20x the throughput of naive per-request execution. But a larger batch means each individual request's tokens arrive slightly slower, so there is a direct dial between throughput (cost) and TTFT/inter-token latency. This dial does not exist for stateless web serving.
3. **Concurrency is bounded by memory, not by CPU.** The KV cache grows with `batch_size x sequence_length`, and it is the binding constraint: a model with 20 GB of weights on an 80 GB card leaves 60 GB for KV cache, which at a few hundred KB per thousand tokens per sequence sets a hard ceiling on concurrent long conversations. Exceed it and requests are queued or preempted, not merely slowed. Paged attention and prefix sharing raise the ceiling substantially and are the reason to use a purpose-built server (vLLM, TGI, TensorRT-LLM) rather than a naive loop.
4. **The unit of capacity is coarse and expensive.** You cannot add 10 percent of a GPU. Scaling is in whole accelerators costing thousands of dollars a month, so utilization matters enormously and a 40 percent-utilized fleet is a serious cost problem rather than a comfortable safety margin.
5. **Prefill and decode have different profiles** - prefill is compute-bound and parallel, decode is memory-bandwidth-bound and sequential - which is why disaggregated serving (separate prefill and decode pools) exists at scale.

**Design consequences:** queue requests rather than autoscaling into a spike (Q164); separate interactive and batch traffic onto different pools with different batch settings (Q155); use provisioned capacity for the baseline and a hosted API for overflow; route simple requests to small models; and treat p95 TTFT as the SLO that determines batch configuration.

### Q224. An AI feature in the critical path of a 99.95 percent system `[A]`

**Frame it first:** the provider's 99.9 percent means 43 minutes a month; my budget is 22. A hard dependency on them makes my SLO unachievable by arithmetic (Q156). So the answer is one of three things, and I would present all three with costs.

**Option 1 (recommended): make it a soft dependency.** Design the feature so the product works without it.

- The AI output is an *enhancement* to a path that has a deterministic fallback: a template response, a rules-based answer, retrieval-only results without generation, a cached previous answer, or a graceful "this is unavailable right now" that does not block the user's task.
- The feature gets its own **feature-level SLO** (say 99.5 percent), tracked separately, while the *system* SLO stays 99.95 percent because a feature outage is a degradation, not a failure (Q163).
- This requires a product conversation, because someone must accept that the AI part is not guaranteed - and that conversation is the actual deliverable of this design.

**Option 2: raise the effective availability of the dependency** (and do this regardless of option 1).

- **Multi-provider with automatic failover** plus multi-deployment for the same model (Q213). Two independent providers at 99.9 percent, failing independently, give ~99.9999 percent - the caveat being that failures are correlated when the cause is your own network, your gateway, or a shared cloud region, so measure rather than assume.
- **Caching, including semantic** (Q215), which serves a meaningful fraction of traffic during an upstream outage.
- **A self-hosted small model as the last-resort tier**, giving degraded quality with availability under your own control. Expensive, and the right answer for a small number of genuinely critical features.
- **Provisioned capacity** to remove shared-tenancy contention.

**Option 3: move it off the critical path entirely.** Make the AI step asynchronous - the user's action completes deterministically and the AI enrichment arrives moments later (Q211). This is often available and often overlooked, and it converts an availability problem into a freshness one.

**What I would build:** option 1 as the architecture, option 2 as the implementation, option 3 wherever the product allows. And I would insist on stating the resulting numbers explicitly in the design document: system availability 99.95 percent, AI feature availability 99.5 percent, fallback behavior defined per surface, and a monitored SLI for "requests served with degraded AI" so the degradation is visible rather than discovered from user complaints.

*Hook: an AI feature you shipped with a defined fallback, and the day the fallback was used.*

---

## 15. Tenancy, security, cost and design-time observability

### Q225. Authentication and authorization in a diagram

**Authentication happens once per request, at the edge**, and once per session at login. The edge (gateway or mesh ingress) validates the credential - verifying a JWT signature against a cached JWKS, or exchanging a session cookie, or terminating mTLS - and converts it into a normalized identity that internal services can trust: a small set of claims propagated in a signed internal header or token. Internal services do **not** re-authenticate the end user against the identity provider; that would make the IdP a hard dependency on every hop (Q156).

**Authorization happens more than once, deliberately, at three levels:**

1. **Coarse, at the edge:** is this credential permitted to reach this route at all? Scope and audience checks, tenant validity, API key permissions. Cheap, uniform, and it stops the majority of bad traffic before it costs anything (Q90).
2. **Fine, in the service that owns the resource:** can *this* subject perform *this* action on *this* object? This requires domain state ("is the user a member of this workspace", "is the document shared with them") and therefore can only be answered by the owning service. It must never be delegated to the gateway.
3. **At the data layer, as defense in depth:** row-level security or a mandatory tenant predicate enforced by the persistence layer, so a missing `WHERE tenant_id = ?` is not a cross-tenant breach (Q270 in the database pack's terms, and Q230 here).

Service-to-service authentication is separate and continuous: mTLS or signed service tokens on every internal call (Q227), so the internal network is not a trust boundary.

The two mistakes worth naming: authorization only at the edge (so any service-to-service call, any internal tool, and any bug bypasses it), and authorization only in the application (so a direct database query or a misrouted request has no protection).

### Q226. Token design

| | Opaque token | JWT |
| --- | --- | --- |
| Validation | Requires a call to the issuer or a shared session store - a network hop per request | Local signature verification, no network call |
| Revocation | Immediate - delete the session | **Hard** - valid until expiry unless you add machinery |
| Size | Small (a random id) | Large (hundreds of bytes to KBs), sent on every request |
| Claims | Fetched, always current | Embedded, and *stale from the moment of issue* |
| Failure mode | The session store is a hard dependency and a SPOF | Statically stable - works when the IdP is down (Q158) |

**What the revocation requirement does to the design** - this is the crux. If you must revoke within seconds (a compromised account, a fired employee, a permission downgrade), then a long-lived JWT cannot satisfy it by itself, and you have four choices:

1. **Short access tokens (5-15 minutes) plus a refresh token.** Revocation is enforced at refresh time, so the worst-case exposure is the access token lifetime. This is the standard answer and the one I would default to: it keeps local validation for the common case and bounds the damage.
2. **A revocation/denylist check at the edge** against a small, fast store holding only revoked token ids or a per-user "not valid before" timestamp. One cheap cache lookup per request at a single choke point, not per service. This gives near-immediate revocation while preserving JWT's local-validation benefit for downstream hops.
3. **Opaque tokens with introspection at the edge**, cached briefly. Effectively the same shape as (2) with the roles reversed.
4. **A `token_version` claim** compared against a per-user counter, incremented on any credential or permission change - which also solves the stale-claims problem, because a permission change invalidates existing tokens.

My design: opaque, `HttpOnly`, `Secure`, `SameSite` cookies for browsers (so no token is exposed to JavaScript), exchanged at the edge for a short-lived internal JWT that downstream services validate locally; refresh tokens rotated on use with reuse detection; a denylist check at the edge; and permission claims kept out of the token where they change frequently, fetched instead from a cached policy decision (Q229).

### Q227. Service-to-service identity

| | mTLS (mesh-issued certificates) | Signed tokens (JWT/SPIFFE-JWT) |
| --- | --- | --- |
| What it proves | The *connection* peer's identity, cryptographically, at the transport layer | The *caller's* identity, verifiable by any hop, and forwardable |
| Rotation | Automated by the mesh; certificates typically live hours to a day, rotated transparently | Minutes; issued per call or per short window |
| Blast radius of a leaked credential | Small - a short-lived certificate bound to a workload identity, and it cannot be replayed from elsewhere if bound to the connection | Larger - a bearer token can be replayed by anyone who obtains it, unless sender-constrained (mTLS-bound or DPoP) |
| Works through | Direct connections and L7 proxies that terminate and re-originate | Any number of hops, including async and message-based flows |
| Cost | Handshake CPU; a certificate authority to operate (the mesh does it) | Signature verification; a JWKS distribution and cache |

**How I would combine them, because they answer different questions:** mTLS for *transport* authentication and encryption between workloads - it establishes "this connection comes from the payments service in namespace X" and it is enforced by infrastructure rather than by application code, which is its main virtue. Then a **forwarded identity token** carrying the *end user's* identity and the calling chain, so the resource owner can authorize on behalf of the user (Q225) rather than trusting the calling service's blanket authority.

The failure this prevents: with mTLS alone, service A can call any endpoint of service B that A is permitted to reach, so a compromised A can read any user's data. With a forwarded user identity, B authorizes per user, and a compromised A can only do what its current users could do.

The operational points: certificate rotation must be automatic and tested (an expired internal certificate is a classic total outage); the SPIFFE identity should be derived from the workload's platform identity rather than from a shared secret; and there must be a clear answer for non-HTTP paths - a message consumer cannot use mTLS to identify the original user, so the identity travels in the message envelope and is signed.

### Q228. A 24-hour JWT with no revocation `[T]`

**The concrete incident:** an employee is dismissed at 10:00 and their access is removed from the identity provider. Their laptop still holds an access token issued at 09:30, valid until 09:30 tomorrow. For the next 23.5 hours they can call every API the token's claims permit - reading customer data, exporting records, deleting resources - and every service validates the token happily, because the signature is good and the expiry has not passed. The IdP's audit log shows nothing, because no authentication occurs. The same shape applies to a token stolen via XSS or a leaked log: the attacker has a full day of authorized access and you have no mechanism to stop them short of rotating the signing key, which logs out every user in the system.

A second, quieter version of the same defect: a user's permissions are *downgraded* (removed from a project, moved to a read-only role) and their embedded claims still grant the old access for 24 hours. This one causes compliance findings rather than headlines, and it is far more common.

**Three fixes:**

1. **Short access tokens with refresh.** 5-15 minute access tokens, refresh tokens with rotation and reuse detection. Revocation applies at refresh, bounding exposure to minutes. Cheapest, standard, and sufficient for most systems.
2. **A revocation check at the edge**: a `jti` denylist, or better a per-subject `not_valid_before` timestamp in a fast store, consulted once per request at the gateway (Q226). Bumping the timestamp invalidates every existing token for that user immediately - which also handles the permission-downgrade case. This is the fix that gives true immediacy.
3. **Keep volatile authorization out of the token.** The token carries identity and stable attributes; permissions are resolved per request from a policy service with a short-lived cache (Q229). Then a permission change takes effect within the cache TTL, seconds rather than a day.

I would also add the operational controls that limit the damage regardless: bind tokens to a client where possible (mTLS-bound or DPoP) so a stolen bearer token is useless elsewhere, log token issuance and usage with subject and client so an incident is investigable, and have a tested "revoke everything" procedure with a key-rotation path.

### Q229. Authorization at scale

**RBAC** - permissions attached to roles, roles to users. Simple, auditable, understood by auditors, and it fails when the rule depends on the *object* ("the owner of this document", "a member of this workspace"), which is most real rules. Role explosion follows: `editor_project_A`, `editor_project_B`, and eventually tens of thousands of roles.

**ABAC** - a policy evaluates attributes of subject, object, action and environment. Expressive, handles ownership and context, and the cost is that the decision needs *data* (the object's owner, the user's department, the current time), so the decision point must be able to fetch it.

**ReBAC** (relationship-based, Zanzibar-style) is the third and increasingly the right answer for object-level permissions: permissions are derived from a graph of relationships (`document:42#viewer@group:eng#member`), evaluated by a dedicated service with a purpose-built index. It is what makes "who can see this document" answerable at scale, including the reverse query "what can this user see", which ABAC handles poorly.

**Where the decision happens:**

- **Coarse checks at the edge** (Q225) - route-level, scope-level.
- **Object-level checks in the owning service**, which either evaluates locally (it has the data) or calls a policy service. Calling out is right when policy is shared and complex; local evaluation is right when the service owns all the relevant state.
- **Policy as a sidecar or embedded library** (OPA-style) with policies distributed as versioned bundles: decisions are local and fast (microseconds), policies are managed centrally, and the data plane is statically stable if the bundle is cached (Q158).

**What I cache**, carefully: the **decision** for `(subject, object, action)` with a short TTL (seconds to a minute) and a per-subject generation counter bumped on any permission change, so revocation is immediate (Q70, Q80). Also the policy bundle itself, and the subject's attribute set. I do **not** cache decisions for long, and I do not cache a *filtered list* of objects under a non-subject key. And the cache must fail closed on a lookup error, with the exception that a *stale* cached decision is preferable to an outage - which is a deliberate, documented trade rather than an accident.

### Q230. Silo, pool, bridge

| | **Silo** (per-tenant infrastructure) | **Pool** (shared, tenant column) | **Bridge** (shared infra, per-tenant schema/namespace) |
| --- | --- | --- | --- |
| Security isolation | Strongest - separate database, separate credentials, often separate account/VPC. A query bug cannot cross tenants | Weakest - correctness of every query is the boundary | Strong-ish - separate schemas and per-schema credentials; a connection is scoped |
| Noisy neighbor | Impossible | The default failure mode; requires quotas (Q231) | Contained at the storage level, not at the compute level |
| Cost / density | Poor - per-tenant fixed overhead, and idle capacity per tenant | Best - one schema, one connection pool, high utilization | Middle |
| Operations | Migrations x N (Q255 in the database pack), monitoring x N, and N is the problem | One migration, one dashboard | Migrations x N schemas, but one cluster |
| Blast radius | 1 tenant | All tenants | All tenants for infrastructure, 1 for data |
| Residency / compliance | Easy - place the tenant's stack in the required jurisdiction | Hard | Moderate |

**How I would use them together**, which is the real answer: a **bridge/pool hybrid with a promotion path**. Long-tail and self-serve tenants share pooled infrastructure with a tenant column, row-level security and enforced quotas. Enterprise, regulated and very large tenants are promoted to silos. The routing layer is directory-based (Q135) so promotion is an operation rather than a re-architecture, and every tenant is addressed identically by the application regardless of where it lives.

The two things that make this survivable: **the tenant identifier is mandatory and enforced below the application** (RLS, or a schema-scoped connection) so an application bug is not a breach; and the **promotion procedure is built and rehearsed before it is needed** (Q142), because the first request for it will arrive with a contract attached.

### Q231. Tenant quotas and fairness

**What to limit** - request rate is necessary and not sufficient. The set that actually protects a shared system:

- **Rate** (requests/second) and **concurrency** (in-flight requests) - concurrency is the one that matters, because 10 concurrent slow queries hurt more than 100 fast ones (Q93).
- **Resource-weighted limits**: query cost units, tokens (Q212), rows scanned, bytes returned, CPU-seconds. A single unbounded query is worth thousands of small ones, so counting requests alone is a hole.
- **Storage, item counts, and object sizes.**
- **Background/async work**: queued jobs, exports, webhook deliveries - the paths teams forget, and where one tenant's bulk import starves everyone.

**Mechanisms for fairness:**

1. **Per-tenant token buckets** at the edge (Q92), with limits by plan tier, and headers so the tenant can behave correctly (Q44).
2. **Per-tenant concurrency slots** with a global admission controller, so the sum of concurrency is bounded and one tenant cannot occupy the pool.
3. **Fair queueing rather than FIFO** for shared workers: round-robin or weighted-fair across tenants, so a tenant that enqueues 100,000 jobs does not delay a tenant with 3. This is the single most effective fix for async unfairness, and FIFO is the most common default mistake.
4. **Shuffle sharding** (Q152) so a tenant's requests hit a subset of workers - one abusive tenant degrades a slice, not the fleet.
5. **Isolation for the largest tenants** - promote to a silo (Q230) rather than trying to contain them with quotas.
6. **Bulkheads by workload class** (Q155): interactive, bulk and export traffic in separate pools, so a tenant's export cannot slow anyone's UI.
7. **Priority-based shedding** under overload, with the tenant's tier as an input (Q94).

**What makes this real:** per-tenant metrics (rate, concurrency, cost, error rate, latency) as a first-class dashboard, so you can see who is causing what; quotas that are **visible to the tenant** and reported before they are enforced; and a documented process for raising a limit, because a quota with no escape valve just becomes a support queue. I would also enforce quotas in a **non-blocking, observe-first mode** at launch, to discover the real distribution before turning on rejection.

### Q232. Secrets and key management

**Where keys live:** in a managed KMS/HSM, and the *key material never leaves it*. Application code holds a reference (a key id) and calls the KMS to encrypt or decrypt small payloads, or - much more commonly - to unwrap a data key.

**Envelope encryption**, which is the answer to "what does it buy":

```
KMS master key (CMK, never exported, hardware-backed)
  └─ encrypts data encryption keys (DEKs)
        └─ each DEK encrypts a bounded set of data (a file, a row, a tenant, a day)
Store: ciphertext + wrapped DEK alongside it
```

It buys four things: **performance** - bulk data is encrypted locally with a symmetric DEK at gigabytes per second rather than round-tripping every byte to the KMS; **scale** - one KMS call per object rather than per byte, and the KMS's request quota stops being the bottleneck; **rotation without re-encryption** - rotating the master key means re-wrapping the DEKs (small, fast) rather than re-encrypting petabytes; and **blast radius reduction** - a leaked DEK exposes only its scope, and per-tenant DEKs enable **crypto-shredding**: destroy a tenant's (or subject's) DEK and their data is unrecoverable everywhere it exists, including in backups. That last property is how you satisfy erasure requirements against immutable stores and backups (Q60, and `../06-database/answers.md` Q275), and it is worth designing in from the start because it cannot be retrofitted.

**Rotation.** Master keys rotate on a schedule with the old versions retained for decryption. DEKs rotate by re-encrypting their scope, done lazily. Application credentials (database passwords, API keys) rotate automatically via short-lived dynamic credentials where the platform supports it (IAM-based database authentication, workload identity federation) - because the best secret is one that does not exist for long. Static long-lived secrets are the ones that leak.

**Distribution to workloads:** a workload identity (instance role, service account, SPIFFE identity) authenticates to the secret store and receives short-lived credentials at runtime. Never in an image, never in an environment variable committed to a repository, never in a configuration file in source control. And there must be a **tested rotation and revocation procedure**, plus detection: secret scanning in CI and in repositories, and alerting on unusual KMS decrypt volume, which is the signal for bulk exfiltration.

### Q233. PII in a design

**Where it enters:** user registration and profile, payment and identity documents, support conversations, uploaded content, device and location telemetry, third-party enrichment, and - the one that surprises people - free-text fields, where users put anything.

**Where it must not go:**

- **Logs and traces.** The dominant leak path. A request body logged at debug level, an exception message containing a row, a trace attribute with an email address, a URL with an identifier in the path recorded by every proxy in the chain.
- **Metrics labels** (Q207) - both a cardinality disaster and a data leak.
- **Analytics, warehouse and ML training datasets**, unless deliberately included with a lawful basis.
- **Lower environments.** Copying production to staging is the most common serious violation.
- **Third-party services** - observability vendors, support tooling, LLM providers (Q220), and anywhere data crosses a jurisdiction (Q176).
- **URLs and query strings**, which end up in browser history, referrer headers and every access log.
- **Caches and CDNs** (Q80), and backups whose retention exceeds the data's.

**The mechanisms that actually keep it out** - and the point is that these must be *structural*, not a coding guideline:

1. **Classification at the schema level.** Every field is tagged (`public`, `internal`, `pii`, `sensitive`) in a machine-readable schema, and the tags drive everything downstream: masking rules, export policies, retention, and access control. A guideline nobody can query is not a control.
2. **Typed wrappers in code** - a `SensitiveString` whose `toString()` redacts. This makes accidental logging structurally impossible rather than merely discouraged, and it is the single highest-leverage change in a Java codebase.
3. **Redaction in the logging pipeline** as defense in depth: pattern-based scrubbing of emails, card numbers, national identifiers and tokens at the collector, before storage.
4. **Synthetic or masked data for lower environments**, generated by a pipeline, with production access to lower environments impossible by construction. Format-preserving masking or tokenization keeps the data useful.
5. **Tokenization/vaulting** for the highest-sensitivity fields: the real value lives in one small, heavily-audited vault and the rest of the system carries a token. This shrinks the compliance scope enormously - PCI scope reduction is exactly this pattern.
6. **Automated scanning** for PII in places it should not be (logs, buckets, warehouse columns), with findings routed to owners.
7. **Retention and deletion as code** (Q62), including crypto-shredding for the immutable cases (Q232).

### Q234. Audit logging as a requirement

**What to record.** One entry per security- or business-significant event: `who` (subject id, and the *original* end user if the action was taken on their behalf, plus the acting service and, for administrative access, the approval reference), `what` (action, resource type and id, and the before/after values or a diff for changes), `when` (server timestamp, plus a monotonic sequence), `where` (source IP, client, session, request id, trace id), and `outcome` (success or failure, and the reason). Failed and denied attempts matter as much as successful ones - often more, since they are the attack signal.

**Immutability.** Append-only by construction: no `UPDATE`, no `DELETE` grant for any application role. Practically that means write-once storage - object storage with versioning and object lock, or a table whose only permission is `INSERT` with retention enforced by partition expiry. For tamper *evidence*, chain the records: each entry includes a hash of the previous one, and the head hash is periodically published or signed, so any modification or removal is detectable. That is far cheaper than a blockchain and satisfies every auditor I have met.

**Comparison of capture mechanisms:**

| | Completeness | Performance | Tamper resistance |
| --- | --- | --- | --- |
| **Application-level** (emit from the service) | Best *semantics* - knows the business intent and the actor - but misses anything that bypasses the application | Low cost, asynchronous | Depends on the sink |
| **Database triggers / audit tables** | Catches every change including manual SQL, but has no idea *who* the end user was or *why* | Write amplification on every change; contention on hot tables | Same database, so a privileged attacker can alter it |
| **Database audit extension / log-based (CDC)** | Complete at the data level; log-based capture is off the critical path | Minimal on the write path | Good if shipped immediately off-host to a write-once store |

**What I would build:** application-level audit events for business and security semantics (the primary source, because intent is what auditors ask about), plus log-based CDC as an independent, complete record of data change, both shipped **off-host immediately** to append-only storage with hash chaining. Two independent sources means a discrepancy is itself a detection signal.

**Retention and access:** retention set by the compliance requirement (frequently 1-7 years), tiered to cheap storage (Q62), queryable through a controlled interface with its *own* audit trail - because reading an audit log is a privileged action - and separated from application logs both in storage and in access control. And it needs an SLO: audit events must not be droppable under load, which makes audit a *hard* dependency (Q163) - one of the few places where failing the request is the correct behavior if the audit write fails.

### Q235. Observability designed in

What a new service must emit on day one, as a platform-provided default rather than a per-team decision:

**Traces.** Distributed tracing with W3C `traceparent` propagated on every inbound and outbound call, including through queues and message brokers (in the message envelope). Spans for every outbound dependency call with its target and outcome. Trace context attached to log lines and to metric exemplars so the three are navigable from each other. Sampling: head-based at a low rate for baseline, plus **tail-based retention of anything interesting** - errors, slow requests, a specific tenant (Q236).

**Metrics** - the small mandatory set:

- **RED per endpoint**: request rate, error rate, duration as a histogram (not an average, not a pre-computed percentile - a histogram, so percentiles can be aggregated correctly, Q207).
- **Per outbound dependency**: rate, error rate, duration, timeouts, circuit-breaker state, retries.
- **Saturation**: thread pool and connection pool utilization and queue depth, in-flight requests, queue lag for consumers.
- **USE for the runtime**: CPU, memory, GC pause time and frequency, file descriptors.
- **Business/SLI metrics**: the one or two counters that define whether the service is doing its job (orders accepted, messages delivered), because infrastructure metrics can all be green while the product is broken.
- **Cardinality discipline**: no unbounded label values, templated paths only (Q207).

**Logs.** Structured JSON, one event per line, with a mandatory context set - timestamp, level, service, version, environment, request id, trace id, span id, tenant id, subject id (pseudonymous), and outcome. No PII (Q233). Sampled at debug level, retained by level with different periods. Log *decisions and transitions*, not narration.

**Plus, and this is what separates a designed system from an instrumented one:** an SLO definition with its SLI query committed alongside the code; a dashboard as code; alerts based on symptoms and burn rate rather than causes; a runbook link in every alert; and a health endpoint that is shallow (Q86). If these are provided by a service template and a shared library, every service has them; if they are a checklist, half will not.

### Q236. 100 percent tracing at 50,000 QPS `[T]`

**The cost.** At 50,000 QPS with, say, 20 spans per request (a realistic number for a service calling five dependencies with a mesh in between), that is `10^6` spans/second. At ~500 bytes per span serialized, that is **500 MB/s, or ~43 TB/day**, before replication and indexing. Consequences: network bandwidth comparable to your production traffic; a collector fleet sized as a significant service in its own right; storage and indexing costs that frequently exceed the application's entire infrastructure bill; 5-15 percent CPU overhead in the application for span creation and serialization; and an ingestion pipeline whose failure becomes your problem. Vendor pricing for that volume is typically in the hundreds of thousands of dollars a month.

**What you actually do:**

1. **Head-based sampling at a low, deterministic rate** for the baseline - 0.1 to 1 percent, with the decision made once at the edge and propagated in `traceparent`, so a trace is complete or absent, never partial. Partial traces are worse than none.
2. **Tail-based sampling for the traces that matter.** Buffer spans at the collector until the trace completes, then keep it if it is interesting: any error, latency above a threshold, a specific tenant or endpoint under investigation, a rare code path. This gives you ~100 percent of the traces you would actually look at for a few percent of the volume, and it is the single most valuable configuration in tracing.
3. **Always-on cheap signals instead.** Metrics with **exemplars** - a histogram bucket carries a sample trace id - give you full-population latency data plus a jump-off point into a real trace. Combined with (2), this covers almost every investigation.
4. **Dynamic sampling.** Raise the rate for low-volume endpoints (which would otherwise never be sampled) and lower it for high-volume ones, so rare paths are represented. Sample per-endpoint to a target *rate* rather than a fixed percentage.
5. **On-demand elevation**: the ability to turn sampling to 100 percent for one tenant, endpoint or user for ten minutes during an incident, via configuration and without a deploy. This removes almost all of the argument for always-on full tracing.
6. **Reduce span cardinality** - do not create a span per database row, and drop mesh-generated spans that duplicate application ones.
7. **Retention tiering**: sampled traces for 7-30 days, error traces longer, aggregates indefinitely.

The framing: **tracing is a sampling problem, and the goal is not to record everything but to record everything you would look at.** Anyone proposing 100 percent has not multiplied the numbers.

### Q237. Cost as a design constraint

**The four levers:**

1. **Do less work.** Cache (Q75), batch, precompute, deduplicate, eliminate N+1 access, drop redundant calls. Algorithmic and architectural, and by far the highest leverage: a query rewrite that halves database load is free forever.
2. **Right-size and increase utilization.** Match instance families to the workload, run at a sensible utilization target (Q28), consolidate under-utilized services, kill idle non-production environments, and use autoscaling for real diurnal variation. This is where the quick wins are.
3. **Buy cheaper units of the same thing.** Reserved instances and savings plans for the steady baseline, spot for interruptible work, ARM/Graviton-class instances, cheaper storage tiers (Q62), and a serious look at managed-service premiums.
4. **Store and move less.** Retention policies, compression, lifecycle transitions, and eliminating unnecessary data movement - especially cross-AZ and cross-region traffic and internet egress (Q27, Q178).

**The one architectural decision that most affects the bill:** the **data architecture** - specifically, how much data you retain, at what resolution, in how many copies, and how many derived stores you maintain. Compute is elastic and can be tuned down next quarter; data volume compounds and every copy multiplies storage, replication, backup, egress and query cost. A retention policy decided at design time is worth more than a year of instance right-sizing. The close second is **whether egress crosses a boundary on the hot path**, because that is a per-request cost that scales with success.

The habit I would build into design reviews: put a rough monthly cost next to each component and each arrow in the diagram, and require a retention line for every store. That takes ten minutes and changes designs.

### Q238. Build, buy, managed

**The framework - five questions:**

1. **Is it differentiating?** Does a customer choose us because of this? If not, we should not be building it. This is the primary filter and it eliminates most candidates immediately.
2. **What is the total cost of ownership over three years**, including engineering time to build *and* to operate, on-call load, upgrades, security patching, and the opportunity cost of the roadmap not delivered? Engineering time is the expensive resource, not the license.
3. **What is the exit cost?** How coupled will we be, how much data will be locked in, and what would migration look like? High exit cost demands a much stronger case.
4. **Does it meet the non-negotiables** - security, residency, compliance, availability SLA, latency, and integration with our identity and observability?
5. **Where is the expertise?** A component nobody on the team can operate at 3 a.m. is a liability regardless of how well it benchmarks.

**Hidden costs by column:**

| | Hidden costs |
| --- | --- |
| **Build** | Operations and on-call forever; the 20 percent of features you did not build and will need; documentation and onboarding; security patching; the bus factor; and the fact that maintenance cost grows while the team's attention moves on |
| **Buy (self-hosted commercial)** | Licence escalation at renewal; version upgrades that are projects; consultants; per-seat or per-core pricing that punishes growth; vendor support quality; and integration work that is always larger than the demo suggested |
| **Managed / SaaS** | Egress and API-call charges; the cost cliff when usage grows (Q27); loss of control over upgrade timing; multi-tenant noisy neighbors; limits and quotas you discover under load; vendor availability becoming your availability (Q156); data residency constraints; and the accumulated integration surface that makes leaving expensive |

**My default:** managed services for undifferentiated infrastructure (databases, queues, object storage, identity, observability), buy for solved commodity problems with a strong market (payments, email, search-as-a-service), build only for the domain logic that is the business. The version of this argument I would make in a review is about **team attention**: every component we operate consumes a fraction of the team's capacity permanently, and that budget should be spent on the parts customers pay for.

### Q239. Compliance as an architectural force

**SOC 2** - the emphasis is on demonstrable control. Three design changes it typically compels:

1. **Access control with evidence**: least-privilege roles, no shared accounts, break-glass access that is time-bound, approved and logged, and an offboarding path that provably revokes (Q228).
2. **Comprehensive audit logging** of access and change, immutable and retained (Q234) - including infrastructure changes, so infrastructure-as-code with reviewed pull requests becomes the required deployment model.
3. **Change management in the pipeline**: peer review, separation of duties between author and deployer, automated tests as a gate, and a documented, tested backup/restore and incident process (Q162).

**PCI DSS** - the emphasis is on shrinking scope:

1. **Tokenization and a segregated cardholder environment.** The highest-value design move is to ensure card data never touches your systems - a hosted payment field or a vault provider - which reduces the compliance surface from the whole platform to an integration (Q233).
2. **Network segmentation** with explicit boundaries and monitored, restricted flows; encryption in transit and at rest with documented key management (Q232).
3. **Strict logging and monitoring** with defined retention, file-integrity monitoring, and quarterly scanning/annual testing - which pushes you toward immutable infrastructure.

**HIPAA-style health data** - the emphasis is on the data itself:

1. **Encryption everywhere plus per-subject key scoping**, with a business-associate agreement required for every processor - which constrains the vendor list, including observability and AI providers.
2. **Minimum necessary access**, enforced by fine-grained authorization and an access log that supports patient-level disclosure accounting - a real feature, not a byproduct.
3. **De-identification pipelines** for analytics and ML, with a documented method, plus data retention and disposal policies.

The general principle I would state: compliance regimes rarely dictate technology, but they consistently force **four** architectural properties - strong identity and least privilege, immutable audit, encryption with managed keys, and explicit data classification with retention. Designing those in from the start costs a fraction of retrofitting them, and they are good engineering regardless of the certificate.

### Q240. Cut cost 40 percent without changing the SLO `[A]`

**My evaluation order** - cheapest and least risky first, since the goal is 40 percent and the first three steps usually find most of it:

1. **Get attribution before touching anything.** Cost per service, per environment, per tenant, per component, with tags enforced. A 40 percent target is unachievable blind, and in every organization I have seen, the first week of attribution finds surprises worth several percent on their own.
2. **Eliminate waste** - the free wins. Idle and forgotten resources, orphaned volumes and snapshots, non-production environments running 24/7 (schedule them off outside working hours: a 65 percent saving on that whole line), over-provisioned instances with 5 percent utilization, duplicated tooling, unattached IPs, old load balancers. This is commonly 10-20 percent of a mature bill and carries zero SLO risk.
3. **Commercial levers.** Savings plans and reserved capacity for the steady baseline, spot for interruptible batch and CI, ARM instances, and a renegotiation of the largest vendor contracts. Another 10-20 percent of compute with no architectural change and no SLO impact - this is the single largest lever that costs no engineering time.
4. **Data lifecycle and retention.** Storage tiering, compression, dropping data nobody queries, reducing log and trace volume and retention (Q236), downsampling metrics (Q207). Frequently very large, because retention has usually never been revisited (Q237).
5. **Right-sizing with measurement**, not guesswork: instance families matched to workload, database instance classes, over-provisioned IOPS, and cache tiers larger than their working set (Q77).
6. **Architectural efficiency** - the engineering work: cut cross-AZ and egress traffic, remove redundant service hops, batch chatty calls, improve cache hit ratios, fix the expensive queries. Real savings, but weeks of effort, so it comes after the free wins.
7. **Consolidation.** Merge under-utilized services and remove a datastore nobody needs (Q57). Saves infrastructure and, more importantly, operational attention.

**What I would refuse**, and say so plainly at the start:

- Cutting **redundancy** - dropping to two AZs, removing the standby, reducing replica counts below what failover needs. That is not a cost saving, it is selling insurance and pretending the SLO is unaffected.
- Reducing **headroom** below the utilization target (Q28), which trades a visible cost for an invisible outage.
- Removing **backups, DR capability or audit retention**, or reducing test coverage and staging fidelity.
- Cutting **observability to the point where the SLO cannot be measured** - at which point we are not meeting the SLO, we are merely unable to tell.
- Deferring **security patching** or downgrading a compliance control.

**How I would present it:** a plan hitting 25-30 percent from steps 1-4 within a quarter with no SLO risk, the remainder from steps 5-7 with named engineering effort, and an explicit list of the things I will not do with the risk of each quantified - so that if the business insists, it is a documented decision with an owner rather than an engineering compromise made quietly.

*Hook: a cost programme you led, the percentage you achieved, and the cut you refused.*

---

## 16. Design exercises and leadership

Q241-255 are worked in full in [scenario-questions.md](scenario-questions.md), Part B. Each walkthrough follows the same spine so it is drillable: clarifying questions and the scope cut, non-functional targets, estimation with real numbers, the API sketch, the data model and storage choice, the diagram, the scaling path, failure and degradation, and the answer to "what if we change one requirement".

| Question | Worked as |
| --- | --- |
| Q241 URL shortener | S11 |
| Q242 Social news feed | S12 |
| Q243 Chat and messaging | S13 |
| Q244 Distributed rate limiter as a platform service | S14 |
| Q245 Notification platform | S15 |
| Q246 Marketplace search and autocomplete | S16 |
| Q247 Payments and ledger | S17 |
| Q248 Ride matching | S18 |
| Q249 Video upload and streaming | S19 |
| Q250 Metrics and observability platform | S20 |
| Q251 Multi-tenant SaaS control plane | S21 |
| Q252 Telecom-scale event ingestion | S22 |
| Q253 Enterprise RAG platform | S23 |
| Q254 Enterprise LLM gateway | S24 |
| Q255 Agent platform with human approval | S25 |

Q256-261 are story questions with no scripted answer. Use **STAR-L** (Situation, Task, Action, Result, Learning) from [../01-java/README.md](../01-java/README.md), keep each to two or three minutes, and quantify the Result. Worked examples of this style are in [scenario-questions.md](scenario-questions.md), Part C.
