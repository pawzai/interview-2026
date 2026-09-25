# System Design Cheatsheet

Last-hour revision. Numbers you should be able to quote without hesitating, and decision tables you can run on a whiteboard.

---

## The 45-minute time budget

| Minutes | What you do | The artifact you leave on the board |
| --- | --- | --- |
| 0-5 | Restate the problem, list capabilities, **cut the scope out loud** | An agreed 3-item scope |
| 5-10 | Extract the six non-functional numbers, then estimate | A table of numbers you will size against |
| 10-15 | API or core operations, then the data model at entity-and-key level | 2-3 signatures, 4-5 entities |
| 15-30 | Draw the smallest system that works, then scale it under **your own** numbers | The evolving diagram |
| 30-40 | The one hard part in depth - the constraint you named at minute 4 | Depth on the thing that matters |
| 40-45 | Failure modes, what you left out, what you would build first | A deferred list, visible |

**Leave undesigned, and say so:** auth beyond "a token is validated at the edge", CI/CD, dashboards, admin tooling, exact DDL, second-order features.

**Two failures this prevents:** twenty minutes on a data model and never reaching scale; reaching scale with no data model so nothing can be sized.

---

## Latency numbers every engineer should quote

| Operation | Time |
| --- | --- |
| L1 cache reference | 1 ns |
| L2 cache reference | 4 ns |
| Mutex lock/unlock | 25 ns |
| Main memory reference | 100 ns |
| Compress 1 KB | 2 µs |
| Send 1 KB over 1 Gbps network | 10 µs |
| SSD random read (4 KB) | 100 µs |
| Read 1 MB sequentially from memory | 100 µs |
| **Round trip within a datacenter** | **500 µs** |
| Read 1 MB sequentially from SSD | 1 ms |
| Disk seek (spinning) | 10 ms |
| Read 1 MB from spinning disk | 20 ms |

**Geography (round trips):**

| Path | RTT |
| --- | --- |
| Same rack / intra-AZ | 0.1-0.5 ms |
| Cross-AZ, same region | 0.5-2 ms |
| Cross-region, same continent | 10-30 ms |
| US East ↔ US West | 60-70 ms |
| US East ↔ Europe | 80-90 ms |
| Europe ↔ Singapore | 160-180 ms |
| US East ↔ Sydney | 200-230 ms |

**The three ratios that do the work:** memory is ~1,000x SSD; SSD is ~100x a cross-region hop; a cross-region hop is ~100x a same-datacenter hop. Fibre gives ~1 ms per 100 km, and real paths are 1.5-2x the great-circle distance.

**What geography forbids:** synchronous cross-continental replication (80 ms per commit); more than one cross-region round trip per user action; a page needing four sequential calls to a distant region.

---

## Estimation arithmetic

**Time:** 86,400 s/day (round to **10^5**), 2.6M s/month, 31.5M s/year (~3 x 10^7).

**Powers of two:** 2^10 = thousand (KB), 2^20 = million (MB), 2^30 = billion (GB), 2^40 = trillion (TB).

**Sizes:** byte 1 B · int 4 B · long/double/timestamp 8 B · UUID 16 B binary, 36 B text · short URL 100 B · tweet-sized record ~300 B · small JSON doc 1-2 KB · web page 2 MB · photo 0.2-2 MB · minute of 1080p ~50 MB.

**QPS from DAU:**

```
DAU x requests-per-user-per-day / 10^5  =  average QPS
average x peak factor                   =  peak QPS
peak factor: 2-3x global consumer, 5-10x single-country evening peak,
             separate spike calculation for scheduled events
```

**Storage:** `rows/year x bytes/row x 2-3 (indexes + overhead) x replication factor / 0.7 (headroom)`.

**Little's Law:** `L = λ x W`. Concurrency = arrival rate x time in system. Use it to size thread pools, connection pools and in-flight limits. **To reduce concurrency, reduce W, not raise L.**

**Utilization:** `W = S / (1 - ρ)`. At ρ=0.5, 2x service time. At 0.8, 5x. At 0.95, **20x**. Size for 40-60 percent.

**Arithmetic-minimum to fleet-size multipliers:** x2 utilization, x1.5 AZ redundancy, plus deploy headroom, warm-up, and the fact that the estimate is wrong. **3 servers of work is 8 servers of fleet.**

---

## Availability and downtime

| Target | Per month | Per year | What it costs architecturally |
| --- | --- | --- | --- |
| 99% | 7.2 h | 3.65 d | Nothing; a single instance with restarts |
| 99.9% | 43 min | 8.8 h | In-zone redundancy, health checks |
| 99.95% | 22 min | 4.4 h | Multi-AZ, automated failover |
| 99.99% | **4.3 min** | 53 min | Multi-AZ everything, no maintenance windows, sub-minute automated failover, load shedding |
| 99.999% | 26 s | 5.3 min | Multi-region active-active, no human in the recovery loop, a deploy system that cannot cause an outage |

**Composition:** `N` hard dependencies at 99.9 percent give `0.999^N`. Twelve gives **98.8 percent (8.6 h/month)**. Reclassifying dependencies from hard to soft is the cheapest availability lever there is.

**Fanout tail:** 5 parallel calls each with a 1 percent chance of exceeding p99 → `1 - 0.99^5 = 4.9 percent`. Your end-to-end p99 is bounded by your dependencies' **p95**.

**RPO ladder:** 24 h = nightly backup · 1 h = snapshots + log shipping · 5 min = async replication with lag alerting · ~0 = synchronous quorum, charged on every write forever.

---

## The six numbers to extract before drawing

1. Scale - DAU/MAU and requests per user per day → QPS → instance and shard count
2. Read:write ratio → whether caching and replicas are the design or an afterthought
3. Data volume and retention → single store versus sharded, and the storage tier
4. Latency target **as a percentile** → sync versus async, and whether cross-region calls are legal
5. Availability target and RPO/RTO → redundancy model and multi-region posture
6. Consistency requirement **per feature** → the hardest part of the design

Plus two soft ones that change designs: is traffic spiky or smooth, and is access global or regional.

---

## Storage selection

| Access pattern | Choice |
| --- | --- |
| Entity by id, with invariants across a few entities | Relational |
| Known composite key, millions of QPS, no ad-hoc queries | Key-value / DynamoDB |
| Append events, read a time range for one key | Wide-column, or a log, or a time-partitioned table |
| Arbitrary text, ranked by relevance, with facets | Search index |
| Aggregate a billion rows over arbitrary dimensions | Columnar warehouse |
| Traversal of unknown depth | Graph (bounded depth → recursive CTE) |
| Nearest neighbours in embedding space | Vector index |
| Large, immutable, streamed bytes | Object storage |

**One sentence each:** relational = default, invariants matter, queries will change · document = the aggregate is the unit of read and write · wide-column = high writes with partition-plus-range access · key-value = single known key, predictable latency at extreme scale · graph = variable-depth traversal *is* the query · time-series = append-only, keyed by time and tags, downsampled · object store = cheapest durable byte · search = relevance, tokenization, faceting.

**Every derived store (search, cache, warehouse, vector) needs a documented rebuild path from the system of record.**

**Default:** one well-run PostgreSQL plus object storage. Change it only for: a demonstrated write/volume ceiling, an access pattern relational serves badly *at the required scale*, or a geography/availability requirement it cannot meet.

**B-tree versus LSM:** B-tree = update in place, random IO, predictable latency, vacuum/bloat. LSM = sequential writes, higher total write amplification, worse tail during compaction, deletes are writes. LSM buys write throughput at the cost of a **compaction budget** you must plan (CPU, IO, free disk).

---

## Caching

| Strategy | Consistency | Failure behavior |
| --- | --- | --- |
| Cache-aside | Eventual; races on concurrent write/read | Cache down → all reads hit the store. **Default choice** |
| Read-through | Same, centralized | Loader is a dependency; stampede control built in |
| Write-through | Strong between cache and store | Write latency = both; cache down blocks writes |
| Write-behind | Store lags cache; **data loss window** | Cache loss = committed data loss |
| Refresh-ahead | Bounded staleness, no stampede | Wasted work on cold keys |

**Layers, in order:** browser → service worker → DNS → CDN edge → reverse proxy → in-process → distributed cache → materialized read model → DB buffer pool → storage. **Invalidation reach:** you can purge a CDN and Redis; you cannot purge a browser or a DNS resolver.

**Hit-ratio arithmetic:** `effective = h x hit + (1-h) x miss`. 90 percent hit with a 50 ms miss = 5.9 ms. 99 percent = 1.5 ms. **But the p99 of a cached endpoint is the miss path**, so a cache alone never meets a percentile SLO.

**Stampede: three mitigations** - single-flight per key, serve-stale-while-revalidating (soft TTL + hard TTL), jittered TTLs. Default = single-flight + jitter. Add `stale-if-error` at the CDN.

**Negative caching + a Bloom filter** for enumerable key spaces, or every miss reaches the origin.

**Family invalidation:** a generation counter in the key, `INCR` to invalidate everything under it in one write. Never `KEYS`.

**Key must contain every input that changes the output:** tenant, locale, currency, flag variant, API version, **permission scope**, serialization version. Version the key prefix instead of migrating values.

**Cache-Control:** `max-age` governs the browser (unpurgeable); `s-maxage` governs the CDN (purgeable). Keep browser TTLs short and shared TTLs long.

---

## Traffic and routing

| Algorithm | Use when |
| --- | --- |
| Round robin | Uniform request cost. Rarely true |
| Least connections | Variable duration - the cheap fix for a slow node |
| **Least request with power-of-two-choices** | The modern default; no herd effect |
| Peak EWMA | Heterogeneous backends, noisy neighbours |
| Consistent hashing (+ vnodes) | Affinity: warm cache, sticky session, sharded backend |

**L4 versus L7:** L4 sees the connection; L7 sees the request. With HTTP/2 or gRPC, L4 pins all of a connection's requests to one backend, so **internal gRPC needs L7 or client-side balancing**.

**Health checks:** liveness = shallow, never network. Readiness = shallow + local (own pools). **Dependency health is a metric, never a reason to leave the load balancer.** Configure fail-open when all targets are unhealthy.

**DNS is a routing decision cached by machines you do not control.** TTLs are advisory; the JVM historically cached forever. Use anycast or a global load balancer for failover, not DNS.

**Rate limiting:**

| Algorithm | State | Burst | Note |
| --- | --- | --- | --- |
| Fixed window | 1 counter | **2x limit at the boundary** | Trivially cheap, wrong |
| Sliding window log | 1 ts/request | Exact | O(limit) memory - unusable at scale |
| Sliding window counter | 2 counters | Smooth | The usual compromise |
| **Token bucket** | count + timestamp | Controlled burst, then rate | **Default** - burst and rate are separate dials |
| Leaky bucket (queue) | depth + drain rate | No burst downstream | Protects a fixed-capacity downstream |
| GCRA | 1 timestamp | Token-bucket semantics | Cheapest exact implementation |

**Distributed limiter:** authoritative bucket in Redis (Lua, atomic) + **local leases of N tokens**, so the hot path never blocks. Overshoot bounded by `nodes x block`. Declare fail-open (protective) or fail-closed (abuse) **per policy**.

**Per-instance limits behind a load balancer give `limit x instances`** and drift with autoscaling. Enforce at one choke point or with shared counters.

**Shed order:** crawlers/speculative → prefetch/batch/analytics → **retries (marked)** → authenticated clients → interactive reads → critical writes. In overload, maximize useful throughput, not fairness.

---

## Async, queues and streams

| Requirement | Choice |
| --- | --- |
| Do a task once, retry, many workers, order irrelevant | Work queue (SQS, RabbitMQ) |
| Many consumers of the same stream, replay, add consumers later | Log (Kafka) |
| Windowed aggregation, joins, late data | Stream processor (Flink, Kafka Streams) |
| Time-triggered, missed windows, arbitrary future timers | Durable timer store + dispatcher |

**Queue = transfer (consumed and gone). Log = storage (retained, per-consumer offsets).** If the consumer set will grow or you will ever reprocess, you need a log.

**Work queue essentials:** visibility timeout **> p99.9 processing time** (or heartbeat the lease) · ack after durability, never on receipt · backoff applied in the broker, not by a sleeping worker · DLQ with an alert, an owner and a replay path · attempt cap, or one poison message is a permanent hot loop.

**Ordering:** per-key is what you need and can have (partition by entity). Global ordering = one partition = one consumer = one machine's throughput. **Best escape: make operations idempotent and version-checked so order stops mattering.**

**Backpressure** must be applied where work *enters*. Every queue needs a declared max depth and a defined behavior at that depth. Unbounded queues turn a throughput problem into an outage.

**Consumer lag:** alert on the **derivative**, and on projected retention exhaustion. Two fixes that are not "more consumers": batch the downstream writes (10-50x), and reduce work per message.

**Retry amplification:** N retry layers multiply (`3^3 = 27`). Bound it with a **retry budget** (retries ≤ 10 percent of attempts → amplification ≤ 1.1x), a circuit breaker, backoff with full jitter, tiered retry queues, and shedding retries before first attempts. **Only one layer retries.**

**Exactly-once:** delivery does not exist; **effect** does. At-least-once delivery + idempotent consumer + offset stored in the same transaction as the effect. Not achievable for uncontrolled external side effects.

---

## Consistency ladder

| Level | A feature that needs it |
| --- | --- |
| Linearizable | Lock acquisition; "is this username taken"; an overdraft check |
| Sequential | Replicated state machine - a config store |
| Causal | A reply never appears before the comment it answers |
| Read-your-writes | Save profile then view it; post then see it in the list |
| Monotonic reads | A counter or feed that must not flicker backwards |
| Eventual | View counts, recommendations, search freshness, dashboards |

**Per operation, not per system.** Session consistency (read-your-writes + monotonic reads) is what users perceive as correctness and is far cheaper than linearizability.

**"Eventually consistent" is unspecifiable.** Replace with: a staleness SLO (`p99 < 2 s, max 30 s`), session guarantees on top, behavior when exceeded, and the list of things that are never stale. Measure with a **heartbeat writer** - write a timestamped row every second, read it from every replica and derived store, report `now() - written_at`.

**Read-your-writes, three implementations:** read-from-primary for a window (guessy, primary load) · **version/LSN token returned by the write and presented on reads** (correct, general) · sticky replica (cheapest, weakest). Fourth and often best: return the post-write state and do not read at all.

**CAP:** on partition, choose availability or linearizability. Nearly useless as a design tool. **PACELC's `ELC` clause is the design** - latency versus consistency during *normal* operation, which is 99.99 percent of the time.

**Quorum:** `R + W > N`. At N=3: `W=2,R=2` balanced. **Add a second region and a global quorum puts a cross-region RTT on every write** - hence `LOCAL_QUORUM` plus async cross-region replication, which loses the global guarantee.

**Distributed transactions:** 2PC = blocking on coordinator failure, multiplicative availability, locks across network hops, and unsupported by most modern components. Saga = availability, no isolation, compensations are business logic. **Redesign so it is not distributed** = the first option to propose.

**Locks:** legitimate for deduplicating *work*, never for correctness of a write (use a unique constraint, conditional write, or version check). A lease can expire while the holder still believes it holds it (GC pause, VM migration). **Only a fencing token checked by the resource makes it safe.**

**Clocks:** monotonic clock for durations, wall clock for absolute timestamps only. Never derive correctness from a wall-clock comparison across machines. Use versions, epochs, sequence numbers or HLCs for ordering.

**ID generation:** UUIDv7/ULID (time-ordered, local, 128 bits) = default · Snowflake (64 bits, sortable, needs node ids) = high volume · sequence blocks/hi-lo = single-database systems · UUIDv4 = wrecks index locality.

**Conflict resolution:** LWW (silently loses data; needs an HLC not a wall clock) · version vectors (detect, application resolves) · **CRDTs** (converge with no coordination - counters, sets, carts, collaborative text) · application merge. **Choose per data type, before the conflict exists.** The default in most systems is LWW, which loses data quietly.

---

## Partitioning and hotspots

**Order of attack: functional first, vertical second, horizontal last.** Horizontal sharding is the only one that permanently complicates every query afterwards.

**Shard key - four properties and the diagnostic question:**

1. High cardinality - "how many distinct values in three years?"
2. Even distribution of **traffic**, not just data - "what share of traffic is in the top 1 percent of values?"
3. Present in most queries - "for each of my top ten queries, do I know the key?"
4. Immutable - "can this value ever change for an existing row?"

| Scheme | Rebalance | Range queries | Hotspot risk |
| --- | --- | --- | --- |
| Range | Easy (split) | Native | **High** - sequential keys hit one shard |
| Hash | Needs consistent hashing + vnodes | Impossible without scatter-gather | Low for data, high for one hot key |
| **Directory** | **Easiest** - move a tenant, update one row | As placed | Controllable - place hot tenants alone |
| Geo | Moderate | Good in-region | Uneven by nature |

**Consistent hashing:** plain modulo moves `(N-1)/N` of keys. Consistent hashing moves `1/N`, from one neighbour. **Virtual nodes** (100-256 per physical node, fewer with modern token allocation) smooth the distribution and spread the relief across all nodes.

**Resharding sequence:** routing indirection exists → dual-write or log-based replication → backfill → verify (counts, checksums, sampled rows) → **READ CUTOVER** (reversible) → bake → **WRITE CUTOVER** (point of no return) → decommission after a real retention window. Per-key-range granularity plus idempotent version-checked writes are what make it survivable.

**Hot key - four mitigations:** replicas for that key · **local cache + single-flight** (ship this first) · split the key into sub-keys · dedicated capacity. Fifth and strongest for a public object: serve it from the CDN.

**Hotspot detection:** per-partition metrics and a **skew ratio** (hottest/mean) on the dashboard; heavy-hitters sketch (Count-Min / Space-Saving) to name the keys. Aggregate utilization hides everything.

**Local versus global secondary index:** local = same partition, atomic write, needs the partition key on read. Global = one-partition read, cross-partition async write, eventually consistent - **so never enforce uniqueness through it.**

**Partition count is often permanent** (Kafka with keyed semantics, stateful stream jobs, hash-modulo schemes). Over-provision 3-10x, choose a highly composite number, and route through an indirection layer.

**Single-database ceiling - evaluation order:** verify the ceiling is real → query and index optimization → **vertical scaling** (buys 12-18 months, do it) → offload reads → offload writes that do not belong → vertical partitioning and archival → functional decomposition → **horizontal sharding last**.

---

## Reliability and failure

**Find SPOFs in two minutes:** anything with a count of one · shared dependencies in every path (auth, config, flags, discovery, DNS, CA) · the control plane · things not actually redundant (three instances in one AZ, an untested failover) · the humans and the runbooks.

| Redundancy model | Failover | Cost |
| --- | --- | --- |
| Active-active | 0 to seconds (**only if headroom exists**) | 100%+ duplicated, all useful |
| Active-passive | Seconds to minutes; dominated by warm-up, not promotion | Idle capacity |
| N+1 / N+2 | 0 | 1/N extra |
| Warm standby scaled down | Minutes (scale-up + warm-up) | Fraction |

**Blast radius shrinkers:** cells · shuffle sharding · in-process bulkheads · **staged deployment** (most outages are caused by change).

**Shuffle sharding numbers:** `n=8, k=2` → 28 combinations. `n=100, k=5` → ~75 million combinations, so one bad tenant fully impairs **only itself** while touching 5 percent of the fleet.

**Timeout budget:** each layer strictly less than its caller, retries fitting *inside* the budget. **Deadline propagation** (absolute deadline passed down; any hop seeing it expired fails immediately) eliminates doomed work - the property that lets a saturated system recover. Enforce at the resource (`statement_timeout`), not just in code.

**Bulkheads:** thread pool per dependency (slow dependency contained) · connection pool · semaphore (async) · queue per consumer/tenant · **separate deployment** (the only one that contains a bug in your own code).

**Graceful degradation ladder** for a composite page: critical with no fallback (503) · critical with a bounded cached fallback (a price, with an "as of" limit) · important-degradable (cached, then "check later") · soft (cached, then omitted). Partial data must be the *normal* path in the template and the contract.

**Static stability test:** if the entire control plane vanished for an hour, would the data plane keep serving existing traffic? Cached config with **no hard expiry on the failure path**, pre-provisioned capacity, fail static rather than closed.

**Gray failure:** a slow node is worse than a dead one - it stays in rotation, consumes callers' threads for the full timeout, attracts retries and hedges, and poisons the p99 without an error signal. Defenses: comparative outlier detection, per-backend concurrency limits, hedged requests, **client-perceived SLIs**.

**Metastable failure:** the system stays down after its cause disappears, sustained by retries and cold caches. Exit only by forcing offered load below capacity, warming, then releasing gradually.

**DR models:**

| Model | RPO | RTO | Cost |
| --- | --- | --- | --- |
| Backup and restore | Hours | Hours to days (**scales with volume - 5 TB is ~7 h before the app starts**) | Storage only |
| Pilot light | Minutes | Tens of minutes to hours | Low |
| Warm standby | Seconds-minutes | Minutes (dominated by scale-up and warm-up) | Medium |
| Multi-site active-active | ~0 | ~0 | Highest |

**A backup never restored is broken in three ways:** it does not contain what you need, it is not readable, or it cannot be restored in the time you promised. Only a **scheduled automated restore drill with a measured duration** produces a real RTO.

**Dependency classes:** hard (no fallback, fail fast, multiplies availability) · soft (timeout, breaker, cached fallback, `degraded` flag, feature-level SLI) · best-effort (queue, never in the request path, freshness SLO).

**Spike defenses:** queue-based leveling (instant, cheapest, needs async-tolerable work) · autoscaling (1-5 min VMs, 20-60 s containers - a cost optimization, **not** a spike defense) · over-provisioning (instant, expensive). For a known event: pre-warm, raise non-elastic ceilings, static-first, queue the writes.

---

## Multi-region

| | Single region multi-AZ | Active-passive | Active-active |
| --- | --- | --- | --- |
| Availability | 99.99% achievable; region loss = outage | 99.99%+ with a failover event | 99.99-99.999%, no failover |
| RPO | ~0 | Seconds-minutes | ~0 local; conflicts possible |
| RTO | Minutes (AZ) | 10-60 min realistically | Seconds |
| Write latency | Low | Low (single writer) | Low if partitioned by home region |
| Cost | 1x | **1.3-1.7x** | **2-2.5x** |

**Three reasons to go multi-region:** latency (most defensible) · residency (non-negotiable when it applies) · availability (**usually the stated reason and usually the wrong one** - most outages are change-related and replicate happily).

**Write models:** single writer + global reads (no conflicts, remote users pay RTT) · **partitioned by home region** (no conflicts for single-entity ops - the sweet spot) · true multi-master (continuous conflict exposure) · global consensus (linearizable, 50-100 ms writes).

**Home-region design:** every cross-region interaction becomes asynchronous, every cross-region invariant becomes a saga. Choose the partitioning axis so most interactions stay in one region.

**Failover that "succeeded" and is still broken - four causes:** a region-pinned dependency (hostname, ARN, third-party IP allowlist) · **capacity, including per-region quotas nobody raised** · cold caches and pools · missing data from replication lag, plus sequences going backwards.

**Testing:** monthly **traffic shift** of 10-50 percent into the standby (the only exercise that proves capacity, quotas, reachability and cold-cache behavior at once) · quota and config parity automation · restore drill · synthetic probes against **both** regions. A standby that never serves traffic rots.

**Global uniqueness:** identifiers = free (UUIDv7, Snowflake, per-region ranges). User-chosen names = one round trip to a namespace owner, partitioned by hash so most registrations stay local. Counters = CRDT (converging, never loses an increment) or **escrow** for a hard limit.

**Expansion sequence:** (0) decide the real reason → (1) **CDN + anycast edge** (removes 40-60 percent of perceived latency, reversible, do it first) → (2) regional read replicas → (3) make the architecture region-aware (`home_region`, dependency inventory, quota parity) → (4) regional writes, one region at a time. **Re-measure after step 2** - it often meets the requirement.

---

## Real-time delivery

| Mechanism | Criterion |
| --- | --- |
| Short polling | Long update interval; simplicity wins. Correct more often than engineers like |
| Long polling | Near-real-time push without WebSockets |
| **SSE** | Server→client only: notifications, dashboards, streaming tokens. It is just HTTP |
| WebSockets | Client also sends frequently; per-message overhead matters |
| Push notifications | The app is not running. Always needed *in addition* on mobile |

**Connection sizing:** 20-50 KB per connection well-tuned (sockets + TLS + app state). 250,000/node → **10M connections = 40 nodes, ~50 with redundancy**. Tune fds, `somaxconn`, socket buffers. Binding constraint is usually CPU during a reconnect storm, not memory.

**Reconnect storm - four controls:** client exponential backoff with **full jitter** (most important, must be in the SDK) · server-directed reconnect pacing + staggered rollout (2 percent of nodes at a time) · admission control on new connections · make reconnection cheap (TLS resumption, resumption token carrying subscriptions, bounded backfill).

**Routing to an unknown node:** per-user registry (exact, racy, another stateful dependency) · broadcast to all nodes (trivially correct, `N`x traffic, dies beyond tens of nodes) · **hashed pub-sub channels (256 topics), each node subscribing only to channels containing its users** - the sweet spot.

**Push versus pull for a feed:** fanout-on-write wins by an order of magnitude at 50-100 reads per write. **Hybrid is strictly better at both ends**: fanout-on-write below a follower threshold, per-author cache merged at read time above it, skip inactive followers, cap timelines at ~800 entries.

**Ordering and dedup on reconnect:** per-channel monotonic **sequence numbers** (never timestamps), client sends its highest *contiguous* seq, server returns the delta. Gap detection and dedup both become free.

**Receipts:** store a **per-user read position**, not a row per message per user. One write per read event regardless of message count; unread counts fall out for free. Above a group-size threshold, aggregate rather than itemize.

**Live counters, four price points:** transactional (exact, contended) · **sharded sub-counters** (exact, uncontended, N reads) · buffered per-instance flush (approximate, small permanent loss possible, orders of magnitude cheaper) · HyperLogLog (~1.6 percent error in 12 KB for unique counts).

**Backfill tiers:** incremental delta (small gap) · truncated with an explicit gap marker · **`RESYNC_REQUIRED` + snapshot** (very stale). Rate-limit it and charge it to a different resource pool than live delivery.

---

## Search and analytics

**Dedicated search when:** relevance ranking is the requirement · full-text scale beyond the database's comfortable range · combinatorial query shapes (text + filters + ranges + geo + facets) under 100 ms · the read workload must not touch the transactional store.

**Index sync, ranked:** **CDC from the log** (cannot miss a change, replayable) → outbox/domain events (domain-shaped, needs discipline) → periodic full reindex (mandatory as a backstop regardless) → dual write (do not ship).

**Drift is not hypothetical.** Continuous count comparison by bucket, a rolling `(id, version, hash)` checksum sweep, version-guarded index writes, and a tested full-rebuild-with-alias-swap whose duration you have measured.

**Search must never be the authority for existence.** Return candidate ids; hydrate current state from the system of record. That removes an entire class of bug.

**Retrieval-then-ranking:** 10M docs → retrieval 1,000 candidates (~20 ms) → light ranking 200 (~15 ms) → heavy rerank 20-50 (~30 ms) → business rules (~5 ms). Features must be static (in the index), contextual (free), or from a **low-latency feature store with a timeout and a default**.

**Facets are aggregations over the whole match set**, not the page. Controls: doc values, capped cardinality, approximate counts, precomputed popular navigation paths, and **dropping counts under load** (a big lever, barely noticed).

**Analytics staleness accumulates at seven points:** commit → CDC lag → ingest/file-close interval → **batch window (usually dominant)** → transform runtime (multiplied by dependency depth) → **BI cache/extract (the other dominant one)** → the browser tab open since this morning. Display "data as of HH:MM" from a pipeline watermark.

**Lambda versus Kappa:** obsolete as an architecture choice. What survives is "how do you reprocess history with the same logic". Answer in 2026: one transformation logic, a lakehouse table format (Iceberg/Delta), **incremental batch by default**, streaming only where the SLA demands it, backfill as a parameterized run of the same job.

**Real-time analytics, three price points:** micro-batch on the warehouse (5-15 min, low cost, **start here**) · real-time OLAP store (1-10 s, justified by *interactive exploration* of recent data) · precomputed streaming aggregates (sub-second, cheap for five metrics, very expensive for twenty).

**Event collection:** SDK batches, buffers to disk, generates an event id and a monotonic sequence, backs off, and has a **server-controlled kill switch**. Collector validates against a registry, enriches with server-side truth (never trust client clocks), quarantines invalid. Sample **deterministically by a stable key**, never randomly per event, and record the rate.

**Metrics:** cardinality is the limit, not sample volume. Series = metric x every label value, and it multiplies. Never put an unbounded value in a label. Store histograms, not pre-aggregated percentiles. Downsample: raw 15 s for 14 days, 1 min for 90 days, 5 min for 13 months, with min/max/sum/count.

---

## AI in the request path

**Five things that change:** heavy-tailed latency (2 s p50, 30 s p99) · non-determinism · per-token variable cost · an external dependency with lower availability than yours · plausible-but-wrong output. Sixth: the model version changes underneath you.

**Serving:** stream (TTFT ~400 ms beats a 20 s wait) · never hold a thread (800 concurrent x 4 s needs non-blocking IO) · its own bulkhead, timeout regime and circuit breaker · async job pattern above ~60 s. **SLO on TTFT and inter-token latency separately from total.**

**Contract by duration:** under 2 s synchronous · 2-60 s streamed SSE (a 200 does **not** mean success; a terminal error can arrive mid-stream) · above that asynchronous with a job resource.

**Caching:** exact/normalized (1-5 percent conversational, 30-70 percent narrow automated; near-zero correctness risk if every input is in the key) · **provider prefix caching** (often the largest cost win) · semantic (20-40 percent hit rate, **real correctness risk**, high threshold only, and **never shared across tenants or permission scopes**).

**Token budgets:** meter `(tenant, feature, model, prompt, completion, cached)` at the gateway; price it in currency; enforce **pre-flight** (post-hoc accounting cannot un-spend); rate-limit **in tokens, not requests**; per-tenant concurrency; soft threshold at 80 percent, defined degradation at 100.

**Cost arithmetic to have ready:** 8,000 prompt + 500 completion tokens is cents per request, so **a feature at 10 req/s is thousands of dollars a day.**

**RAG sizing:** 10M docs x 8 chunks = 80M vectors. 1,024 dims float32 = **328 GB** → quantized 4-8x = 40-80 GB, so quantization is a requirement, not an optimization. Initial embedding at ~1,000/s ≈ 8-10 hours. A model upgrade means re-embedding everything into a **new index with an alias swap**.

**ANN trade-offs:** flat (exact, to ~100k) · **HNSW** (1-5 ms, 95-99 percent recall, 1.5-2x memory, high build cost) · IVF-PQ (low memory, 80-95 percent recall, needs training) · DiskANN (low RAM, SSD-bound). **State a number: "recall@10 = 0.96 at p95 8 ms, measured against exact search on 10,000 queries."**

**Hybrid retrieval:** BM25 (exact terms, identifiers, negation) + vector (paraphrase, concepts), fused with **reciprocal rank fusion** (`k≈60`, no normalization needed), then a cross-encoder rerank over the top 50-100. Rerank is the dominant pre-generation latency (80-200 ms) and the first thing to cut under load.

**Guardrails cost:** deterministic checks free · safety classifier 50-300 ms · groundedness check 200 ms-1 s. Run cheap checks always, model checks **in parallel with streaming** with truncation permitted, sample expensive evaluations offline, tier strictness by risk. **Specify the on-failure behavior.**

**GPU capacity:** cold start is minutes (provisioning + a tens-of-GB image + weights into VRAM) · **continuous batching gives 5-20x throughput** but trades against TTFT · concurrency is bounded by KV cache memory, not CPU · capacity comes in whole accelerators · prefill is compute-bound, decode is memory-bandwidth-bound. Queue rather than autoscale.

**AI in a 99.95 percent system on a 99.9 percent provider:** make it a **soft dependency with a deterministic fallback and its own feature-level SLO** (the architecture) · multi-provider and multi-deployment failover, caching, a small self-hosted last-resort tier (the implementation) · move it off the critical path entirely where the product allows.

**Agents:** hard limits (steps, tokens, wall clock, spend) · tools scoped to **the user's** permissions, never a service account · durable state machine, stateless workers, `WAITING` runs occupy no compute · idempotency on `(run_id, step_n)` · risk-classified tools driving human approvals · sandboxing, and tool output treated as untrusted input.

---

## Tenancy, security, cost

| Tenancy | Isolation | Cost | For |
| --- | --- | --- | --- |
| Silo (per-tenant infra) | Strongest; easy residency | Poor density, migrations x N | Enterprise, regulated, very large tenants |
| Pool (shared, tenant column) | Weakest - query correctness is the boundary | Best | Long tail, self-serve |
| Bridge (shared infra, per-tenant schema) | Strong-ish | Middle | The pragmatic default |

**Tenant sizes span 4-6 orders of magnitude.** Design for the giant tenant from day one: directory-based routing, per-tenant quotas, and a **rehearsed promotion path** from pooled to dedicated.

**Quotas must cover** rate **and concurrency** and cost-weighted units (rows scanned, tokens) and storage and **async/background work**. Fairness comes from **fair queueing across tenants instead of FIFO** - the most common default mistake.

**Auth:** authenticate once at the edge; authorize three times - coarse at the edge, object-level in the owning service, and a mandatory tenant predicate/RLS at the data layer.

**Tokens:** JWT = local validation, statically stable, **hard to revoke**. Opaque = immediate revocation, a network hop, a SPOF. Resolution: short access tokens (5-15 min) + rotating refresh + a per-subject `not_valid_before` check at the edge + volatile permissions kept out of the token.

**A 24-hour JWT with no revocation** means a dismissed employee or a stolen token has a full day of authorized access, invisible to the IdP's logs - and a permission *downgrade* takes a day to apply.

**Service identity:** mTLS for transport identity (infrastructure-enforced, short certificates) **plus** a forwarded end-user identity token, so the resource owner authorizes per user rather than trusting the caller's blanket authority.

**Envelope encryption** buys performance, KMS-quota scale, rotation without re-encryption, and **crypto-shredding** (destroy a per-subject DEK to make data unrecoverable everywhere, including backups). Design it in; it cannot be retrofitted.

**PII stays out** via schema-level classification, typed wrappers whose `toString()` redacts, pipeline redaction, synthetic lower environments, tokenization/vaulting for the highest sensitivity, automated scanning, and retention as code. Leak paths people forget: metric labels, URLs, traces, third-party observability, backups.

**Audit:** application events (intent) **plus** log-based CDC (completeness), shipped off-host immediately to append-only storage with **hash chaining** for tamper evidence. Audit is one of the few *hard* dependencies - a failed audit write should fail the request.

**Tracing cost:** 50,000 QPS x 20 spans x 500 B = **500 MB/s ≈ 43 TB/day**. Therefore: 0.1-1 percent head sampling with the decision made once at the edge, **tail-based retention of errors and slow traces**, metric exemplars as the always-on signal, dynamic per-endpoint rates, and on-demand elevation to 100 percent for ten minutes.

**Cost levers:** do less work (highest leverage) · right-size and raise utilization · buy cheaper units (reservations, spot, ARM) · store and move less. **The data architecture - retention, resolution, copy count, number of derived stores - affects the bill more than any compute decision.**

**Rough costs:** compute ~$50-100/month per always-on mid-size instance · managed database 2-4x equivalent compute plus storage and IOPS · object storage ~$0.02/GB/month · block storage ~$0.10/GB/month · **internet egress $0.05-0.09/GB** · cross-region transfer ~$0.02/GB. **Data transfer is the line nobody estimates**, and idle non-production is often 30-40 percent of the bill.

**40 percent cost cut:** 20-25 percent from waste and commercial levers (no reliability impact) · 8-12 percent from engineering efficiency · the remainder requires an explicit decision. **Refuse** to cut redundancy, headroom, backups, DR, audit retention, or observability below the point where the SLO can be measured - and escalate that as a named decision with a price.

---

## Numbers worth quoting

- **86,400 seconds/day**, rounded to 10^5 for arithmetic.
- **100M DAU x 10 requests = 10,000 QPS average, ~30,000 peak** at 3x.
- **0.5 ms** intra-datacenter RTT; **80 ms** transatlantic; **200 ms** to Sydney.
- **99.99 percent = 4.3 minutes a month** - less than one unplanned restart of a stateful component.
- **Twelve hard dependencies at 99.9 percent = 98.8 percent (8.6 hours/month).**
- **`W = S/(1-ρ)`**: 20x service time at 95 percent utilization.
- **3 servers of work is 8 servers of fleet.**
- **Five parallel calls make your p99 their p95.**
- **1M concurrent viewers at 3 Mbps = 3 Tbps** - a CDN problem by arithmetic.
- **10M WebSockets at 40 KB = 400 GB, ~40-50 nodes.**
- **One post to 50M followers = 500 seconds of cluster time** - hence hybrid fanout.
- **150M active series x ~3 KB = 450 GB of RAM** - cardinality, not samples, is the limit.
- **80M vectors x 1,024 dims x 4 B = 328 GB**, quantized to 40-80 GB.
- **50,000 QPS x 20 spans = 43 TB of traces a day.**
- **Retries capped at 10 percent of attempts bound amplification at 1.1x.**
- **`n=100, k=5` shuffle sharding = 75 million combinations**, so one bad tenant harms one tenant.
- **Restoring 5 TB from object storage is ~7 hours** before the application starts.
- **A cache hit ratio of 99.9 percent can hide a 1000x capacity gap.**

---

## Five sentences that earn credit

1. "The hardest constraint here is X, so I am going to organize the design around it." *(Naming the load-bearing constraint at minute four.)*
2. "That came from these inputs - which one do you think is wrong?" *(Defending a derivation, not a number.)*
3. "This is eventually consistent with a p99 staleness of 2 seconds, and here is what is never stale." *(Specifying instead of hand-waving.)*
4. "That is a soft dependency, so the fallback is Y and the feature has its own SLO." *(Availability arithmetic as a design tool.)*
5. "The cheapest correct answer is the boring one; here is the trigger that would change my mind." *(Reversibility, with a checkpoint.)*
