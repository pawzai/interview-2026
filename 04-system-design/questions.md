# System Design Interview Questions

Questions are numbered continuously (`Q1`, `Q2`, ...) so that [answers.md](answers.md) can reference them directly.

Difficulty legend:

- `[C]` Core - you must answer this instantly and correctly.
- `[D]` Deep - expected of a senior engineer, requires mechanism-level detail.
- `[T]` Tricky - designed to catch you out; the obvious answer is usually wrong.
- `[A]` Architect - no single right answer, judged on trade-off reasoning.

Each category opens with an **Assumed known** line pointing at the `01-java`, `02-spring`, `03-microservices` and `06-database` questions this material builds on. If those are shaky, go back before continuing.

This pack is about **selection, sizing and sequencing** - which components a system needs, what numbers justify them, and the order you say it on a whiteboard. Component internals live in the other packs and are not repeated.

---

## 1. Framing, requirements and SLOs

> Assumed known: `01-java` Q108-109 (DDD, hexagonal architecture) and `03-microservices` Q1-8 (boundaries, context maps).

1. `[C]` Give the first five minutes of any system design interview, in order, and the artifact each step produces.
2. `[C]` Functional versus non-functional requirements. List the six non-functional numbers you always extract before drawing anything.
3. `[D]` How do you turn a vague business statement ("users should be able to share posts") into a bounded scope you can design in 40 minutes? Show the cut you make and how you announce it.
4. `[T]` The interviewer says "design Twitter" and offers no constraints. What is the wrong move here, and what specifically do you ask?
5. `[D]` Availability targets: convert 99.9, 99.95, 99.99 and 99.999 percent into downtime per month, and state what each one costs architecturally.
6. `[T]` A stakeholder asks for "five nines". Explain why the number is almost always wrong, and what you offer instead.
7. `[D]` SLI, SLO, SLA and error budget. Define each and give the SLI you would pick for a write API, a read API and an async pipeline.
8. `[D]` Why is a latency SLO always expressed as a percentile plus a window rather than an average? Give the failure this prevents.
9. `[D]` p50, p95, p99, p99.9: which do you design for, which do you alert on, and which does the business feel?
10. `[T]` Every service in a chain of five meets its 99th-percentile SLO. Explain why the end-to-end p99 is still worse than any of them.
11. `[D]` RPO and RTO: define both, and derive the backup and replication strategy implied by RPO of 5 minutes versus RPO of zero.
12. `[D]` Read-heavy versus write-heavy versus balanced. What does each imply for your first three design decisions?
13. `[D]` How do you identify the single hardest constraint in a problem, and why does naming it early change the whole interview?
14. `[D]` Consistency requirements are rarely uniform across a product. Show how you partition one system's data by consistency need.
15. `[A]` A product owner wants a real-time global feature with a strict correctness guarantee and a two-month deadline. How do you reshape the requirement without saying no?
16. `[A]` You have 45 minutes and the problem is clearly a three-hour problem. Describe your time budget and what you deliberately leave undesigned.

---

## 2. Back-of-the-envelope estimation and capacity math

> Assumed known: `06-database` Q264 (capacity planning) and `03-microservices` Q188-190 (Little's Law, latency arithmetic).

17. `[C]` The numbers every engineer should have memorized: L1, main memory, SSD random read, network round trip within a datacenter, cross-region round trip, and disk seek. Give orders of magnitude.
18. `[C]` Convert 100 million daily active users with 10 requests per day into average QPS and peak QPS. State the peak factor you assume and why.
19. `[D]` Seconds in a day, powers of two to 2^40, and bytes per common data type. Show how you use these to size a table without a calculator.
20. `[D]` Estimate storage for a system storing 500 million records a year with a five-year retention and three replicas. Include index and metadata overhead.
21. `[D]` Estimate the memory needed to cache the hot set for a system with 200 million objects averaging 2 KB, given an 80/20 access distribution.
22. `[T]` Your estimate says 8 servers. The interviewer asks why not 3. What second-order factors make the honest answer larger than the arithmetic?
23. `[D]` Estimate the bandwidth for a video service streaming 1 million concurrent users at 3 Mbps, and say what that means for CDN versus origin.
24. `[D]` Little's Law: state it, and use it to size a thread pool and a connection pool for a service at 5,000 QPS with 40 ms service time.
25. `[D]` Compute the number of shards needed given a per-shard write ceiling, and explain why you pick a number well above the arithmetic minimum.
26. `[T]` Why does a system sized for average load fall over at 2x average, rather than degrading by a factor of two?
27. `[D]` Estimate the cost per month of a design in rough terms: compute, storage, egress, and the managed-service premium. Which one usually dominates and surprises people?
28. `[D]` Utilization targets: why do you size for 40-60 percent CPU rather than 85 percent, and what does queueing theory say happens near saturation?
29. `[D]` Estimate the fanout cost of a social write where the average user has 200 followers and the worst has 50 million. What does the distribution do to your design?
30. `[T]` The interviewer challenges an estimate by a factor of ten. How do you respond without either capitulating or defending a number you invented?
31. `[A]` How much estimation is enough? Give the rule you use for when a number changes a decision and when it is theatre.

---

## 3. API and interface design at system scale

> Assumed known: `01-java` Q167-168 (REST maturity, idempotency, versioning) and `03-microservices` Q16-30 (contracts, gRPC, protobuf evolution, expand-contract).

32. `[C]` Design the public API for a resource with create, read, list and delete. Give the paths, methods, status codes and the pagination contract.
33. `[D]` REST versus gRPC versus GraphQL versus a message contract. Give the decision criteria you actually apply, not the feature list.
34. `[T]` GraphQL removes over-fetching. Name the four new problems it creates at the system level and what you must build to control them.
35. `[D]` Design an idempotent write API for money movement. Specify the key, its scope, its lifetime and the response for a replay.
36. `[D]` Pagination for a public API: offset, cursor, and a token that encodes state. Which do you expose, and what do you promise about stability?
37. `[D]` Long-running operations over HTTP: 202 plus a status resource, polling intervals, and how the client learns about failure.
38. `[T]` A client retries a request that actually succeeded but timed out. Walk through every layer that must cooperate for the retry to be safe.
39. `[D]` Bulk and batch endpoints: partial success semantics, the response shape, and the size limit you enforce and why.
40. `[D]` API versioning at the system level: URI, header, and never-break. What do you commit to, and how do you retire a version with real clients?
41. `[D]` Backward and forward compatibility for an event contract versus an HTTP contract. What differs, and why is the event harder?
42. `[D]` Designing for mobile clients: payload shape, chunking, offline queueing, and the retry policy you require of them.
43. `[T]` Your API is correct and your clients still hammer you into an outage. What controls belong in the contract itself?
44. `[D]` Rate limits as part of the API: the headers you return, the status code, and how a client is supposed to behave.
45. `[D]` Webhooks as an outbound interface: delivery guarantees, signing, retry schedule, and how a consumer's outage becomes your problem.
46. `[D]` BFF (backend for frontend) versus a single general API versus an API gateway with composition. When is each right?
47. `[A]` You own an API used by 40 internal teams and 200 external customers. Design the deprecation policy and the mechanism that enforces it.

---

## 4. Storage selection and data modeling for a system

> Assumed known: `06-database` Categories 1-3 and 11 (modeling, SQL, indexing, NoSQL families), `03-microservices` Q61 (database per service).

48. `[C]` Give your default storage choice for a new system and the three pieces of evidence that would make you change it.
49. `[D]` Walk from access pattern to storage engine. Show the mapping for five concrete access patterns.
50. `[D]` Relational, document, wide-column, key-value, graph, time-series, object store, search index. For each, the one sentence that decides it.
51. `[T]` "We need a graph database because the data is graph-shaped." When is this wrong, and what does a relational recursive query cost instead?
52. `[D]` B-tree versus LSM-tree storage engines from a *design* standpoint: what does each imply for your write path, read latency and compaction budget?
53. `[D]` Design the data model for an entity with a hot mutable part and a large immutable part. Where do the two live and why?
54. `[D]` Blob and object storage in a design: what goes in the database, what goes in S3, and how the two stay consistent.
55. `[T]` Storing a 5 MB image in the database versus a URL in the database. Give the failure mode of each, including the one people forget about the URL.
56. `[D]` Presigned uploads: the full sequence, what can go wrong at each step, and how you handle an upload that never completes.
57. `[D]` Polyglot persistence: how many datastores is too many, and what does each additional one cost operationally?
58. `[D]` Designing a write path that must serve two very different read shapes. Contrast one store with a projection versus two stores with a sync.
59. `[D]` Time-series data: why a general-purpose store struggles, and the four properties a time-series design needs.
60. `[T]` An append-only log as the system of record. What does this buy you, and what three problems does it hand you in year two?
61. `[D]` Immutable event storage versus mutable current state. Where do you place the boundary in a design, and what do you materialize?
62. `[D]` Data retention in the design: hot, warm, cold and deleted. Show the tiering and what triggers each transition.
63. `[D]` Design for a schema you know will change monthly. What structures survive that, and which ones must you avoid?
64. `[T]` The interviewer says "just use DynamoDB, it scales". Give the two questions that determine whether that is true for this problem.
65. `[A]` Design the storage layer for a system with a strict transactional core, a large analytical requirement, and a full-text search need.

---

## 5. Caching as an architectural tier

> Assumed known: `06-database` Category 10 (caching and Redis internals, stampede, eviction) and `01-java` Q160-161.

66. `[C]` Name every cache layer between a user's keystroke and a database row, and what each one is good at.
67. `[D]` Cache-aside, read-through, write-through, write-behind and refresh-ahead. Give the consistency and failure behavior of each.
68. `[D]` Where do you put the cache: client, CDN, gateway, service-local, or a shared remote tier? Give the criterion for each.
69. `[T]` A local in-process cache across 40 instances. What exactly goes wrong, and when is it still the right answer?
70. `[D]` Cache key design: what belongs in the key, versioning the key, and how you invalidate a family of keys at once.
71. `[D]` TTL selection: how do you choose one, and what does a TTL actually promise about staleness?
72. `[T]` "We will invalidate the cache on write." Explain why this is harder than it sounds in a distributed system, and the three races involved.
73. `[D]` Cache stampede, thundering herd and dog-piling. Give the three mitigations and the one you apply by default.
74. `[D]` Negative caching and the empty-result problem. What does not caching a miss cost you under attack?
75. `[D]` Hit ratio: what is a good one, how does it relate to the latency you promised, and why can a higher hit ratio be a warning sign?
76. `[T]` The cache tier fails completely. Walk through what happens to the database in the next 30 seconds, and design so this is survivable.
77. `[D]` Sizing a cache: working set, eviction policy, and the marginal value of the last gigabyte.
78. `[D]` CDN in a design: what you cache at the edge, cache-control headers you set, and how you purge globally.
79. `[D]` Edge compute and edge caching for personalized content. What can be cached when every response differs?
80. `[D]` Caching authenticated and permission-filtered data. Give a design that does not leak between users.
81. `[T]` Your read-your-writes guarantee broke after adding a cache. Explain the exact mechanism and two fixes.
82. `[A]` A team proposes a cache to fix a latency problem. What do you need to see before agreeing, and what would make you refuse?

---

## 6. Load balancing, routing, gateways and traffic management

> Assumed known: `03-microservices` Q97-110 (discovery, mesh, gateway) and `02-spring` Q205-210 (Gateway, Resilience4j).

83. `[C]` L4 versus L7 load balancing. What can each see, what can each do, and where does each sit in your diagram?
84. `[D]` Load balancing algorithms: round robin, least connections, least request with power-of-two-choices, consistent hashing, EWMA. When does each beat the others?
85. `[T]` Round robin across instances with wildly different response times. What breaks, and which algorithm fixes it?
86. `[D]` Health checks: liveness, readiness, deep versus shallow, and the failure mode of a check that is too deep.
87. `[T]` A deep health check causes a total outage when one dependency degrades. Explain the cascade and the correct design.
88. `[D]` DNS in a design: TTLs, client caching you cannot control, and why DNS is a poor failover mechanism.
89. `[D]` Anycast, GeoDNS and global load balancers. Compare failover speed, precision and cost.
90. `[D]` What belongs in an API gateway and what must not. Give the line you draw and defend it.
91. `[D]` Rate limiting algorithms: fixed window, sliding window log, sliding window counter, token bucket, leaky bucket. Give the memory cost and burst behavior of each.
92. `[D]` Design a distributed rate limiter for 50,000 QPS across 30 nodes. Specify where state lives and the accuracy you accept.
93. `[T]` A rate limiter enforced per instance behind a load balancer. What is the actual limit a client experiences, and why is it not what you configured.
94. `[D]` Admission control, load shedding and priority queues. How do you decide *what* to drop when you must drop something?
95. `[D]` Sticky sessions versus stateless services versus external session state. What does each cost at deploy time and at failure time?
96. `[D]` Connection management at the edge: keep-alive, connection limits, TLS termination and the cost of a new handshake.
97. `[D]` Traffic shaping for a launch: canary, ramp, shadow traffic and the kill switch. Sequence them.
98. `[A]` Design the traffic layer for a system expecting a 50x spike at a known time on a known date.

---

## 7. Asynchronous processing, queues and streams

> Assumed known: `03-microservices` Categories 3 and 5 (Kafka internals, delivery semantics, sagas, outbox, idempotency).

99. `[C]` What makes an operation a candidate for asynchronous processing? Give the four signals and one counter-example.
100. `[D]` Queue versus log versus stream processor versus scheduler. Map four concrete requirements onto these.
101. `[D]` Design the async path for a user action that must appear to succeed instantly but takes 30 seconds of work.
102. `[T]` "We will make it async" as an answer to a latency problem. When does this genuinely help, and when does it just move the latency somewhere the user still feels it?
103. `[D]` Work queue design: visibility timeout, ack, retry with backoff, dead-letter queue, and who is responsible for poison messages.
104. `[D]` Ordering guarantees in a design: per-key ordering, global ordering, and what you must give up to get either.
105. `[T]` You need strict ordering and high throughput on the same stream. Explain the tension and give three ways to escape it.
106. `[D]` Backpressure in a pipeline: where it must be applied, what happens if it is not, and how you signal it upstream.
107. `[D]` Consumer lag: what causes it, what it predicts, and the two ways to shrink it that do not involve more consumers.
108. `[D]` Fanout patterns: queue per consumer, topic with subscriptions, and a shared log with independent offsets. Compare replay and isolation.
109. `[D]` Design a scheduled and delayed job system: at-least-once firing, missed windows, clock skew and duplicate suppression.
110. `[D]` Batch versus micro-batch versus streaming for the same aggregation. What changes in latency, cost and correctness?
111. `[T]` A retry storm in a queue-based system. Explain the amplification and the specific controls that bound it.
112. `[D]` Exactly-once processing in a design: state the honest version of the guarantee and what you build to get its effect.
113. `[D]` Designing for replay: how do you reprocess three days of events without double-charging anyone?
114. `[D]` Choosing between Kafka, SQS/SNS, RabbitMQ and a database-backed queue for a given design. Give the decisive question for each.
115. `[A]` Design the asynchronous backbone for a platform with 20 teams, including the governance that stops it becoming a distributed mess.

---

## 8. Consistency, coordination and time

> Assumed known: `03-microservices` Category 4 (CAP, PACELC, consistency models, consensus, logical clocks) and `06-database` Categories 5-6 (transactions, MVCC).

116. `[C]` State CAP correctly, then state why it is nearly useless as a design tool and what PACELC adds.
117. `[D]` The consistency ladder: linearizable, sequential, causal, read-your-writes, monotonic reads, eventual. Give a product feature that needs each.
118. `[T]` "Eventually consistent" - eventually is how long? What must a design specify instead, and how do you measure it?
119. `[D]` Read-your-writes across a read-replica topology: give three implementations and their costs.
120. `[D]` Where do you place a strong-consistency boundary in a large system, and how do you keep it small?
121. `[D]` Distributed transactions: two-phase commit, sagas, and doing without. What does each cost in availability?
122. `[T]` A design uses 2PC across three services. What specifically fails, and what do you propose instead?
123. `[D]` Idempotency as a system property: where keys are generated, where they are stored, how long they live, and the cleanup problem.
124. `[D]` Distributed locking: when it is legitimate, what a lease is, and why a lock without fencing is unsafe.
125. `[T]` Redlock, or a lock in Redis with a TTL. Explain precisely what can still go wrong and the fencing token that fixes it.
126. `[D]` Leader election in a design: what needs a leader, how failover works, and what happens during the gap.
127. `[D]` Unique ID generation at scale: UUIDv7, Snowflake, database sequence blocks, and a coordination service. Compare ordering, size and failure modes.
128. `[T]` Two nodes both believe they are the leader. Describe the split-brain, how it happens, and the three defenses.
129. `[D]` Clocks: NTP drift, monotonic versus wall clock, TrueTime and hybrid logical clocks. Which design decisions depend on clock assumptions?
130. `[D]` Quorum arithmetic: `R + W > N`, and what changes when you add a second region.
131. `[D]` Conflict resolution for concurrent writes: last-write-wins, vector clocks, CRDTs, and application merge. Give a case for each.
132. `[A]` A product wants both global low-latency writes and a strong uniqueness constraint. Design the compromise and explain it to a non-technical stakeholder.

---

## 9. Partitioning, sharding and hotspots

> Assumed known: `06-database` Category 9 (sharding, resharding, hotspots) and `03-microservices` Q40 (repartitioning).

133. `[C]` Vertical versus horizontal partitioning versus functional decomposition. Give an example of each in one system.
134. `[D]` Shard key selection: the four properties a good key has, and the diagnostic question you ask about each.
135. `[D]` Range, hash, directory-based and geo partitioning. Compare rebalancing, range queries and hotspot risk.
136. `[T]` A monotonically increasing shard key. What happens, why is it tempting anyway, and what do you use instead?
137. `[D]` Consistent hashing with virtual nodes: why plain modulo fails, how many vnodes, and what happens when a node is added.
138. `[D]` Resharding a live system with no downtime. Give the full sequence including the read and write cutover points.
139. `[D]` Cross-shard queries and joins: the three strategies and the honest cost of each.
140. `[T]` A single celebrity key receives 40 percent of traffic. Give four mitigations and the one you would ship first.
141. `[D]` Detecting hotspots before they hurt: the metrics, the sampling approach, and the alert.
142. `[D]` Multi-tenant partitioning: tenant per shard, shared shards, and the giant-tenant problem.
143. `[D]` Secondary indexes over a partitioned dataset: local versus global. What does each cost on write and on read?
144. `[D]` Partitioning a stateful stream-processing job. What must co-partition with what, and why?
145. `[T]` Your partition count is a configuration value that can never change. Which systems have this property and how do you design around it?
146. `[D]` Data locality and co-location: how do you keep an entity's related data on one shard, and what breaks the guarantee?
147. `[D]` Rebalancing traffic versus rebalancing data. When is the cheap answer enough?
148. `[A]` A system is at 90 percent of its single-database ceiling in six months. Present the options in the order you would evaluate them, including not sharding.

---

## 10. Reliability, failure modes and graceful degradation

> Assumed known: `03-microservices` Category 6 (timeouts, retries, circuit breakers, retry budgets, metastable failure) and `07-devops` for tooling.

149. `[C]` Single points of failure: how do you find them in your own design in two minutes?
150. `[D]` Redundancy models: active-active, active-passive, N+1, and the cost and failover time of each.
151. `[D]` Blast radius: define it, and give four architectural techniques that shrink it.
152. `[D]` Cell-based architecture and shuffle sharding. What do they actually buy, with numbers?
153. `[T]` Adding a retry improved success rate in testing and caused an outage in production. Explain the mechanism precisely.
154. `[D]` Timeout budgets across a call chain: how do you set them so the total is bounded, and what is deadline propagation?
155. `[D]` Bulkheads and isolation: thread pools, connection pools, separate deployments. What does each contain?
156. `[T]` Every dependency is 99.9 percent available and there are twelve of them. Compute the result, then design so the answer is wrong.
157. `[D]` Graceful degradation: design the tiered fallback for a product page with six data sources.
158. `[D]` Static stability: what it means, and how you design a control plane failure so the data plane keeps serving.
159. `[D]` The failure modes of a healthy-looking system: gray failure, partial partitions, slow nodes. Why is a slow node worse than a dead one?
160. `[D]` Chaos engineering as a design input: which experiments would you run against your own design first?
161. `[D]` Disaster recovery: backup, pilot light, warm standby, multi-site. Map them onto RPO and RTO with costs.
162. `[T]` A backup strategy that has never been restored. What are the three ways it is probably broken?
163. `[D]` Dependency classification: hard, soft, and best-effort. How does the classification change the code and the SLO?
164. `[D]` Queue-based load leveling versus autoscaling versus over-provisioning as a spike defense. Compare response time and cost.
165. `[A]` Design the reliability strategy for a system whose availability target is 99.99 percent on infrastructure that offers 99.9 percent.

---

## 11. Multi-region and geo-distribution

> Assumed known: `06-database` Category 8 (replication, failover) and `03-microservices` Q71-74 (quorums, consensus).

166. `[C]` The three reasons to go multi-region, and the one that is usually a lie. Which one applies to your design?
167. `[D]` Single region multi-AZ, active-passive multi-region, active-active multi-region. Give the availability, RPO/RTO and cost of each.
168. `[D]` Physics in a design: quote the round-trip latency for intra-AZ, cross-AZ, cross-region within a continent, and intercontinental. What do these forbid?
169. `[T]` "Active-active gives us better availability." What new failure modes does it introduce that active-passive does not have?
170. `[D]` Routing users to a region: GeoDNS, anycast, client-side selection. How do you handle a user who moves?
171. `[D]` Multi-region writes: single-writer with global reads, partitioned by home region, and true multi-master. Compare conflict exposure.
172. `[D]` Home-region (partition-by-geography) design: how do you handle a cross-region interaction between two users with different home regions?
173. `[D]` Replication lag as a product concern: how do you expose it, bound it, and design a UI that tolerates it?
174. `[T]` A region failover completed successfully and the system is still broken. Give four realistic reasons.
175. `[D]` Failover mechanics: automatic versus manual, the health signal you trust, and why you probably want a human in the loop.
176. `[D]` Data residency and sovereignty: what does GDPR-style residency do to a global design, and where does the data actually live?
177. `[D]` Global uniqueness and global counters across regions. What is achievable and at what latency?
178. `[D]` Cross-region cost: egress, replication traffic and duplicated capacity. What is the real multiplier over single-region?
179. `[D]` Testing multi-region: how do you know failover works without a real disaster, and what do you run monthly?
180. `[A]` A business wants global expansion into three continents next year. Sequence the architectural work and say what you would not do yet.

---

## 12. Real-time delivery, push and fanout

> Assumed known: `03-microservices` Category 3 (event streaming) and Category 7 here (queues).

181. `[C]` Short polling, long polling, server-sent events, WebSockets and push notifications. Give the one-line criterion for each.
182. `[D]` Design the connection tier for 10 million concurrent WebSocket connections. Give the per-connection memory budget and the node count.
183. `[D]` Presence ("who is online") at scale: the data structure, the update rate, and how you avoid an O(n^2) problem.
184. `[T]` A WebSocket gateway restarts and 500,000 clients reconnect at once. Describe the storm and the four controls that prevent it.
185. `[D]` Routing a message to a user whose connection is on an unknown node. Give two designs and their trade-offs.
186. `[D]` Push versus pull for a feed: fanout-on-write, fanout-on-read, and the hybrid. Give the crossover point.
187. `[T]` Fanout-on-write for a user with 50 million followers. What breaks, and what is the actual production answer?
188. `[D]` Ordering and deduplication of messages delivered to a client that reconnects. What does the client have to send you?
189. `[D]` Delivery receipts and read receipts: the state machine, the write amplification, and where you cheat.
190. `[D]` Mobile push (APNs/FCM) in a design: the token lifecycle, delivery guarantees, and why you cannot treat it as reliable.
191. `[D]` Real-time collaborative editing: operational transforms versus CRDTs, and what the server's role is in each.
192. `[D]` Live counters (views, likes, viewers) at high write rates. Give three designs at different accuracy and cost points.
193. `[D]` Backfill on reconnect: how much history, from where, and how you bound the cost of a client that was offline for a month.
194. `[A]` Design the real-time layer for a product that needs chat, notifications and live dashboards. Argue for one tier or three.

---

## 13. Search, ranking and the analytics path

> Assumed known: `06-database` Category 12 (Elasticsearch, star schemas, columnar formats, CDC) and `03-microservices` Q78-79.

195. `[C]` When does a design need a dedicated search system rather than a database query? Give the three triggers.
196. `[D]` Design autocomplete for 100 million queries a day. Give the data structure, the update path and the latency budget.
197. `[D]` Keeping a search index in sync with the source of truth: rank the options and say how you detect and repair drift.
198. `[T]` Search returns a document the user just deleted. Explain every layer this could come from and the fix at each.
199. `[D]` Ranking as a system: the retrieval-then-ranking split, feature availability at request time, and the latency budget for each stage.
200. `[D]` Faceted search and aggregations at scale. What is expensive, and how do you precompute?
201. `[D]` Personalized search results and caching. Which parts are cacheable and how do you layer them?
202. `[D]` The analytics path: from OLTP write to dashboard. Draw it and mark every point where staleness is introduced.
203. `[D]` Lambda versus Kappa architecture. Is the distinction still useful in 2026, and what do you actually build?
204. `[D]` Designing for both real-time and historical queries over the same data. Where do the two paths meet?
205. `[T]` The business asks for "real-time analytics". Establish what they mean and give the three designs at three different price points.
206. `[D]` Event collection at scale: client SDK, collector tier, schema registry and the sampling decision.
207. `[D]` Metrics storage: why a time-series database over a relational one, cardinality as the real limit, and downsampling policy.
208. `[A]` Design the data platform boundary for a product organization: what the product teams own, what the platform owns, and how data contracts are enforced.

---

## 14. AI and ML in the request path

> Assumed known: `02-spring` Q261-268 (Spring AI) and `01-java` Q225-240 (AI engineering first pass). Depth on RAG and agents lives in `09-rag` and `10-ai-agents`.

209. `[C]` What changes about a system design when a component is an LLM call rather than a deterministic service? Give five properties.
210. `[D]` Design the serving path for a model with a 2-second p95 and a 30-second tail. What does the tail do to your timeouts, threads and UX?
211. `[D]` Synchronous inference, streamed inference and asynchronous inference. Give the client contract for each.
212. `[D]` Token-based cost and rate limits: how do you budget, meter and enforce them per tenant?
213. `[T]` A provider's API degrades to 20-second latencies at 11 a.m. every day. Design so this is a non-event.
214. `[D]` Model gateway design: routing, fallback across providers, caching, prompt versioning and audit. What sits in it?
215. `[D]` Caching LLM responses: exact-match, normalized, and semantic caching. Give the hit-rate expectation and the correctness risk of each.
216. `[D]` Design the ingestion and indexing pipeline for a RAG system over 10 million documents with daily updates.
217. `[D]` Vector search in a design: approximate nearest neighbor trade-offs, index build cost, and the recall number you must state.
218. `[T]` A vector database is added alongside PostgreSQL with pgvector already in place. When is the separate system justified?
219. `[D]` Hybrid retrieval (keyword plus vector) and reranking. Where does the latency go and what do you cut under load?
220. `[D]` Evaluation and guardrails in the request path: what you check before returning, and what that costs in latency.
221. `[D]` Non-determinism and testing: how do you build a regression suite for a system whose output varies?
222. `[D]` Agent orchestration in production: step limits, tool timeouts, state persistence, and human-in-the-loop checkpoints.
223. `[D]` GPU capacity in a design: batching, concurrency, cold starts, and why autoscaling GPUs is not like autoscaling web servers.
224. `[A]` A product wants an AI feature in the critical path of a 99.95 percent-available system whose provider offers 99.9 percent. Design the answer.

---

## 15. Tenancy, security, cost and design-time observability

> Assumed known: `06-database` Categories 15-16 (observability, security, cost), `03-microservices` Categories 8-9 (tracing, cross-service security), `11-security` for depth.

225. `[C]` Authentication versus authorization in a system diagram: where does each happen, and how many times?
226. `[D]` Token design: opaque versus JWT, lifetime, refresh, and revocation. What does the revocation requirement do to your design?
227. `[D]` Service-to-service identity: mTLS, signed tokens, and a mesh. Compare rotation and blast radius.
228. `[T]` A JWT with a 24-hour lifetime and no revocation list. Give the concrete incident this causes and three fixes.
229. `[D]` Authorization at scale: RBAC, ABAC and a policy service. Where does the decision happen and what do you cache?
230. `[D]` Multi-tenant isolation: silo, pool and bridge models. Give the security, cost and noisy-neighbor profile of each.
231. `[D]` Design tenant-level quotas and fairness so one customer cannot degrade another.
232. `[D]` Secrets and key management in a design: where keys live, rotation, and what an envelope encryption scheme buys.
233. `[D]` PII in a design: where it enters, where it must not go, and the mechanisms that keep it out of logs and lower environments.
234. `[D]` Audit logging as a first-class requirement: what you record, immutability, retention, and query access.
235. `[D]` Observability designed in rather than added: the traces, metrics and logs a new service must emit on day one.
236. `[T]` Full tracing at 100 percent sampling on a 50,000-QPS system. What does it cost, and what do you actually do?
237. `[D]` Cost as a design constraint: the four levers you pull, and the one architectural decision that most affects the bill.
238. `[D]` Build versus buy versus managed service. Give the decision framework and the hidden costs of each column.
239. `[D]` Compliance requirements (SOC 2, PCI, HIPAA-style) as architectural forces. Name three design changes each typically compels.
240. `[A]` You are told to cut infrastructure cost by 40 percent without changing the SLO. Give your evaluation order and what you would refuse.

---

## 16. Design exercises and leadership

> Assumed known: everything above. Q241-255 are worked in full in [scenario-questions.md](scenario-questions.md); Q256-261 have no scripted answer.

241. `[A]` Design a URL shortener serving 100 million redirects a day with custom aliases and click analytics.
242. `[A]` Design a social news feed for 200 million users where the follower distribution spans four orders of magnitude.
243. `[A]` Design a chat and messaging system with one-to-one and group conversations, presence, and delivery receipts.
244. `[A]` Design a distributed rate limiter offered as a platform service to 200 internal services.
245. `[A]` Design a notification platform delivering email, SMS and push across 30 producing teams with per-user preferences.
246. `[A]` Design search and autocomplete for a marketplace with 500 million listings and near-real-time inventory.
247. `[A]` Design a payments and ledger system with exactly-correct balances, idempotent charges and a reconciliation path.
248. `[A]` Design ride matching for a mobility platform: driver location ingestion, geospatial matching and trip lifecycle.
249. `[A]` Design a video upload and streaming pipeline with transcoding, adaptive bitrate delivery and content protection.
250. `[A]` Design a metrics and observability platform ingesting 10 million data points per second with 13-month retention.
251. `[A]` Design the control plane for a multi-tenant SaaS platform: provisioning, tenant lifecycle, configuration and blast-radius control.
252. `[A]` Design telecom-scale event ingestion: 500,000 network events per second, with billing-grade accuracy and an investigation query path.
253. `[A]` Design an enterprise RAG platform serving 50 business units over their own document corpora with per-unit access control.
254. `[A]` Design an LLM gateway for an enterprise: multi-provider routing, per-tenant quotas, caching, safety checks and cost attribution.
255. `[A]` Design an agent platform that executes multi-step workflows against internal systems with human approval checkpoints.
256. A design you chose that was deliberately less exciting than the alternative, and how you defended it.
257. A design you got wrong at scale, how you found out, and what the correction cost.
258. A time you overruled a design review, or were overruled, and what happened next.
259. A time you had to hit a cost target that conflicted with a reliability target.
260. A system you decommissioned or deliberately did not build, and how you made that case.
261. How you have raised the design standard across teams you did not own.
