# Microservices Interview Questions

Questions are numbered continuously (`Q1`, `Q2`, ...) so that [answers.md](answers.md) can reference them directly.

Difficulty legend:

- `[C]` Core - you must answer this instantly and correctly.
- `[D]` Deep - expected of a senior engineer, requires mechanism-level detail.
- `[T]` Tricky - designed to catch you out; the obvious answer is usually wrong.
- `[A]` Architect - no single right answer, judged on trade-off reasoning.

Each category opens with an **Assumed known** line pointing at the `01-java` and `02-spring` questions this material builds on. If those are shaky, go back before continuing.

This pack is deliberately platform-agnostic. Kubernetes, service mesh and cloud messaging appear only where a microservices decision genuinely depends on them; the rest belongs to the AWS and DevOps packs.

---

## 1. Decomposition and service boundaries

> Assumed known: `01-java` Q165-166 (boundary signals, monolith versus microservices) and Q108-109 (hexagonal architecture, DDD).

1. `[C]` Bounded context, aggregate and service are three different things. Define each precisely and explain which one determines a deployment unit.
2. `[T]` "One service per aggregate" and "one service per bounded context" give different answers for the same domain. Which do you follow, and what goes wrong with the other?
3. `[D]` What is a context map, and what do the relationship patterns - shared kernel, customer-supplier, conformist, anti-corruption layer, published language, separate ways - each cost you operationally?
4. `[D]` Explain afferent and efferent coupling for services. Which one predicts that a boundary is wrong?
5. `[T]` Two services change together in 80 percent of releases. Is that a boundary problem, and how do you prove it rather than assert it?
6. `[C]` What is a distributed monolith? Name five symptoms that are visible in telemetry rather than in code.
7. `[D]` Conway's Law and the Inverse Conway Manoeuvre. When is reorganizing the teams the correct technical fix?
8. `[A]` Team Topologies - stream-aligned, enabling, complicated-subsystem, platform. How does this change the services you would draw?
9. `[D]` Why does entity-based decomposition (a "Customer service", an "Order service") tend to fail, and what is the capability-based alternative?
10. `[T]` A service has exactly one consumer and always changes with it. Is that automatically wrong?
11. `[D]` Event storming: what artefacts does it produce, and how do you get from pivotal events to candidate boundaries?
12. `[D]` What is the correct size for a microservice? Answer without using lines of code, and defend the metric you choose.
13. `[T]` Nanoservices - what specific costs appear once services get too small, and which of them are non-linear?
14. `[D]` Shared libraries across services: what is safe to share, what is never safe, and why is a shared domain model the classic mistake?
15. `[D]` How do you handle a genuinely cross-cutting concept, like "customer", that every context needs a slightly different view of?
16. `[A]` When do you deliberately merge two services back together? What evidence justifies it, and how do you sell it?
17. `[D]` What is the strangler fig pattern, and what makes the *first* extracted service the hardest one?
18. `[T]` Which of these should almost never be its own service: authentication, feature flags, a shared database access layer, an audit log, an email sender? Justify each.
19. `[D]` How do you split a shared database that four services already read from directly, without a big-bang cutover?
20. `[A]` A greenfield product, six engineers, unclear domain. How many services do you start with and what is your reasoning?

---

## 2. Synchronous communication and API contracts

> Assumed known: `01-java` Q167-168 (REST maturity, idempotency, versioning) and `02-spring` Q211 (declarative HTTP clients).

21. `[C]` REST, gRPC, GraphQL and plain messaging - give the decision framework you actually apply, with the deciding question for each.
22. `[D]` gRPC over HTTP/2: streaming modes, deadlines, and how head-of-line blocking differs from HTTP/1.1.
23. `[T]` A gRPC deadline is not the same as a client timeout. What does each one actually do, and which one propagates?
24. `[D]` Protobuf schema evolution rules - which changes are wire-compatible, which are source-compatible, and which are neither?
25. `[D]` GraphQL in a microservice estate: schema stitching versus federation, and what the N+1 problem becomes at service granularity.
26. `[T]` Why is a shared client SDK published by the *provider* team an anti-pattern, and when is it the pragmatic right answer?
27. `[C]` API versioning: URI, header, media type and no versioning at all. Which do you default to and how do you retire a version?
28. `[D]` What is Postel's Law and where does it actively harm you in a microservice contract?
29. `[D]` Consumer-driven contracts - the mechanism, the CI wiring, and what the provider build must do with the contracts.
30. `[T]` Contract tests pass and the integration still breaks. Give three realistic causes.
31. `[D]` Backwards compatibility versus forwards compatibility. Which does a rolling deployment actually require, and in which direction?
32. `[D]` The expand-contract (parallel change) pattern for an API and for a database column. Walk both through in order.
33. `[D]` HTTP status codes for a distributed system: which ones are safe to retry, and what does the client have to assume about 5xx versus a timeout with no response?
34. `[T]` A client receives a 504 from the gateway. What is the state of the write on the server, and what is the only safe thing the client can do?
35. `[D]` Pagination, filtering and partial responses in a service-to-service API. What breaks at scale with offset pagination?
36. `[D]` The Backend for Frontend pattern - what problem does it solve, and what problem does it create?
37. `[D]` API gateway aggregation versus client-side composition versus a dedicated aggregator service. Trade-offs.
38. `[A]` How do you govern API design across 40 teams without a central approval board becoming the bottleneck?

---

## 3. Asynchronous messaging and event-driven architecture

> Assumed known: `01-java` Q174-176 (exactly-once, Kafka partitions and consumer groups, repartitioning) and `02-spring` Q214-216 (Spring Cloud Stream, `@KafkaListener`, listener transactions).

39. `[C]` Event notification, event-carried state transfer, event sourcing and CQRS are four different things people call "event-driven". Define each and give the failure mode of each.
40. `[T]` Event-carried state transfer removes a synchronous call but introduces a subtler coupling. What is it?
41. `[D]` Commands, events and queries as message types: naming, ownership, and who is allowed to be the consumer of each.
42. `[D]` A log-based broker (Kafka, Pulsar) versus a queue broker (RabbitMQ, SQS). Which properties actually differ, and what does that mean for replay?
43. `[C]` Explain delivery semantics precisely: at-most-once, at-least-once, effectively-once. Where does each one place the burden?
44. `[T]` Kafka's exactly-once semantics - what exactly is it exactly-once *about*, and why does it not save you when your consumer writes to a database?
45. `[D]` Kafka transactions and `read_committed`: what the transaction coordinator does, what the LSO is, and what latency cost you pay.
46. `[D]` Consumer group rebalancing: eager versus cooperative-incremental, static membership, and why a long `max.poll.interval.ms` is both the fix and a new problem.
47. `[T]` Your consumer takes 40 seconds per message and the group rebalances constantly. Name all four configuration values involved and which one is actually wrong.
48. `[D]` Ordering guarantees: what Kafka orders, what it does not, and how ordering interacts with retries and DLQs.
49. `[T]` You need per-customer ordering and high throughput. Partitioning by customer creates hot partitions. How do you get both?
50. `[D]` Poison messages: detection, retry topics with escalating delay, dead letter queues, and the redrive procedure. Who decides when to replay?
51. `[T]` A DLQ that nobody reads is worse than no DLQ. What operational contract makes a DLQ actually work?
52. `[D]` Idempotent producers, `enable.idempotence`, sequence numbers, and what `acks=all` with `min.insync.replicas` really buys you.
53. `[D]` Consumer lag: how you measure it, why time lag matters more than offset lag, and what you alert on.
54. `[D]` Schema registry: compatibility modes (backward, forward, full, transitive), and which one you set for a topic with many independent consumers.
55. `[T]` Adding a required field to an event schema is backward-compatible by the registry's definition but still breaks production. Explain.
56. `[D]` Event versioning strategies: upcasting, multiple topics, envelope with a version field, and the tolerant reader.
57. `[D]` Event sourcing: the event store, snapshots, projections, and the two hardest operational problems.
58. `[T]` In an event-sourced system, how do you handle a GDPR deletion request against an immutable log?
59. `[D]` CQRS: when the read model lags, how do you avoid a user not seeing their own write?
60. `[A]` When would you refuse event-driven architecture for a system that appears to be a natural fit?

---

## 4. Distributed data and consistency

> Assumed known: `01-java` Q169-170 (CAP, PACELC, eventual consistency) and Q180 (caching strategies, invalidation, stampede).

61. `[C]` Database per service: what it actually forbids, and the three things teams do that quietly violate it.
62. `[C]` State the consistency models in order - linearizable, sequential, causal, read-your-writes, monotonic reads, eventual - and give a user-visible symptom of each being violated.
63. `[T]` "Strong consistency" is not one thing. Distinguish the consistency in CAP from the C in ACID, and explain why conflating them causes bad designs.
64. `[D]` Two-phase commit: the protocol, the blocking failure mode, and why XA across services is effectively unused today.
65. `[D]` Three-phase commit and Paxos Commit exist. Why did neither replace 2PC in practice?
66. `[D]` Consensus: what Raft actually guarantees, what a quorum is, and why an even number of nodes is a mistake.
67. `[T]` A leader election with a lease and a GC pause produces two leaders. What is the mechanism, and what is a fencing token?
68. `[D]` Logical clocks: Lamport timestamps versus vector clocks versus hybrid logical clocks. What can each detect that wall-clock time cannot?
69. `[T]` You use `updated_at` timestamps to resolve conflicts between two regions. Explain precisely how this loses data.
70. `[D]` CRDTs: what class of problem they solve, the difference between state-based and operation-based, and their real cost.
71. `[D]` Quorum reads and writes: what `W + R > N` guarantees, and what it still does not.
72. `[D]` Read replicas and replication lag: how do you give a user read-your-writes without routing everything to the primary?
73. `[D]` Sharding: key selection, resharding, hot shards, and why consistent hashing with virtual nodes is the usual answer.
74. `[T]` A distributed lock built on Redis - state the exact conditions under which it fails, and whether Redlock fixes them.
75. `[D]` Optimistic versus pessimistic concurrency across service boundaries. Where does a version number have to live?
76. `[D]` Distributed caching: cache-aside invalidation across services, TTL jitter, negative caching, and the thundering herd on cold start.
77. `[T]` Two services cache the same entity with different TTLs. What class of bug does this produce, and how do you detect it?
78. `[D]` Change data capture: log-based versus query-based, what the initial snapshot does, and what happens on connector restart.
79. `[D]` A data lake or reporting database fed from many services - how do you do this without recreating a shared database?
80. `[D]` Referential integrity across services no longer exists. What replaces it, and how do you detect orphans?
81. `[T]` Service A validated that customer X exists before creating an order; by commit time X was deleted. Is this a bug, and whose?
82. `[A]` A regulator asks for a point-in-time consistent report across seven services. How do you produce it?

---

## 5. Sagas, outbox and idempotency

> Assumed known: `01-java` Q171-173 (saga choreography versus orchestration, outbox, idempotent payment API) and `02-spring` Q248 (event publication registry).

83. `[C]` Saga: define it precisely, and explain what ACID property you are giving up and what replaces it.
84. `[D]` Compensating transactions - why they are not rollbacks, and what a semantic compensation looks like for a shipped parcel.
85. `[T]` Which steps of a saga must be compensatable, which must be retriable, and which must be neither? Why does the pivot step matter?
86. `[D]` Choreography versus orchestration: give the decision rule, and name the observability cost of each.
87. `[D]` How does a saga orchestrator persist its state, and what happens if it crashes between sending a command and recording that it sent it?
88. `[T]` A saga times out waiting for a reply that arrives later. What are the four possible outcomes and how do you make the late reply safe?
89. `[D]` Saga isolation anomalies: lost update, dirty read, fuzzy read. Explain the countermeasures - semantic lock, commutative updates, pessimistic view, reread value, version file, by-value.
90. `[C]` The transactional outbox: table design, the relay, and the exact ordering guarantees you get.
91. `[T]` Why is the outbox relay's delivery at-least-once and never exactly-once, no matter how carefully you write it?
92. `[D]` Outbox polling versus CDC-based outbox (log tailing). Compare latency, load, operational burden and failure modes.
93. `[D]` The listen-to-yourself pattern and the inbox pattern. When do you need an inbox as well as an outbox?
94. `[D]` Idempotency keys: who generates them, how long you retain them, what you store, and what you return on a replay.
95. `[T]` A client retries with the same idempotency key but a *different* request body. What do you do?
96. `[D]` Natural idempotency: which operations are inherently idempotent, and how do you turn `balance += 10` into one?
97. `[T]` Idempotency and concurrency: two identical requests with the same key arrive simultaneously on two instances. Walk through the race and the fix.
98. `[D]` Exactly-once *processing* on the consumer side: the transactional inbox, deduplication windows, and why the deduplication store is itself a scaling problem.
99. `[D]` How do you make a saga observable enough to answer "where is order 12345 right now" in under a minute?
100. `[A]` Design the recovery procedure for 4,000 sagas stuck in an intermediate state after a six-hour downstream outage.

---

## 6. Resilience and failure handling

> Assumed known: `01-java` Q179 (rate limiting algorithms) and Q181 (graceful degradation), `02-spring` Q210 (Resilience4j and aspect ordering).

101. `[D]` The eight fallacies of distributed computing. Pick three and give a production incident each one causes.
102. `[D]` Timeouts: connect, socket, request, and total. How do you choose the numbers rather than copying them?
103. `[T]` Why must a caller's timeout be *shorter* than its callee's, and what happens across five hops if it is not?
104. `[D]` Deadline propagation - what it is, how you implement it over HTTP and over messaging, and why it beats per-hop timeouts.
105. `[C]` Retries: which errors are retriable, why exponential backoff alone is insufficient, and what full jitter changes.
106. `[T]` Retries at three layers - client, gateway, service - multiply. Work out the amplification factor and describe the retry budget that fixes it.
107. `[C]` Circuit breaker: the three states, the exact metrics that trip it, and how the half-open probe should be limited.
108. `[T]` A circuit breaker on a dependency that is slow but not failing does nothing. Why, and what do you configure instead?
109. `[D]` Bulkheads: thread pool versus semaphore isolation, and how you size each.
110. `[D]` Load shedding versus rate limiting versus backpressure - three different things. Define each and where it belongs.
111. `[D]` Rate limiting in a distributed gateway: local counters, Redis token buckets, and why approximate limits are usually acceptable.
112. `[T]` What is a metastable failure state, and why does the system stay down after the original trigger is removed?
113. `[D]` The thundering herd on recovery: what causes it, and the three mechanisms that prevent it.
114. `[D]` Graceful degradation: static fallbacks, cached fallbacks, reduced functionality. How do you decide per endpoint?
115. `[T]` A fallback that returns an empty list caused a bigger incident than the failure would have. Explain how, and state the rule.
116. `[D]` Health checks: liveness versus readiness versus startup. What must a readiness check *not* do?
117. `[T]` Your readiness probe checks the database. The database blips. Explain the resulting outage.
118. `[D]` Graceful shutdown in a service that both serves HTTP and consumes from a queue - give the exact ordering of steps.
119. `[D]` Chaos engineering: the experiment structure, what you must have in place before your first one, and the blast radius controls.
120. `[A]` Define an error budget policy for a service with a 99.9 percent SLO and say what actually changes when it is exhausted.

---

## 7. Discovery, gateways, routing and service mesh

> Assumed known: `01-java` Q178 (service discovery, client versus server-side load balancing) and `02-spring` Q207-208, Q213, Q220 (Gateway internals, LoadBalancer, what not to adopt on Kubernetes).

121. `[C]` Service discovery: client-side, server-side and DNS-based. What does each cost in failure modes, not features?
122. `[T]` DNS-based discovery with a 30-second TTL - name three specific ways this bites you, including one inside the JVM.
123. `[D]` Health-check-driven deregistration: what is the window during which traffic goes to a dead instance, and how do you shrink it?
124. `[D]` Load balancing algorithms: round-robin, least-connections, peak EWMA, power of two choices. Which handles a slow instance best and why?
125. `[T]` One instance in a pool is degraded but passing health checks. Round-robin keeps sending it traffic. What are your options?
126. `[C]` API gateway responsibilities - and the list of things that should never be in the gateway.
127. `[T]` Why does putting business logic or response transformation in the gateway eventually create a second monolith?
128. `[D]` Service mesh: the data plane and control plane, what a sidecar actually intercepts, and how mTLS is established.
129. `[D]` Sidecar versus sidecar-less (ambient, eBPF) meshes. What changes in the cost and failure model?
130. `[T]` Adding a mesh added 8ms of p99 latency per hop. Where does it come from, and which parts can you actually remove?
131. `[D]` What does a mesh give you that a well-written library does not, and what does the library give you that the mesh cannot?
132. `[D]` Traffic shifting: canary, blue-green, mirroring (shadow traffic) and A/B. Which are safe for writes?
133. `[T]` You mirror production traffic to a new version. What must you guarantee about the shadow service, and what goes wrong if you do not?
134. `[D]` East-west versus north-south traffic: which controls belong at each boundary?
135. `[D]` Zero-trust networking between services: what replaces the network perimeter, and how does identity get to the workload?
136. `[A]` You run 40 services on Kubernetes. Argue both for and against adopting a service mesh, then decide.

---

## 8. Distributed observability

> Assumed known: `01-java` Q177 (trace context across async boundaries) and Q198-201 (metrics, logs, SLO/SLI), `02-spring` Q189-192 (Micrometer, Observation API).

137. `[C]` Metrics, logs, traces and profiles - what question is each one *best* at answering, and which is the wrong tool for "why is this one request slow"?
138. `[D]` OpenTelemetry: the API/SDK split, the collector, and why the collector is worth running even for one service.
139. `[D]` W3C `traceparent` and `tracestate`: the field layout, and what the sampled flag actually controls.
140. `[T]` Trace context lost across a thread pool, a message queue and a scheduled job - give the mechanism and the fix for each.
141. `[D]` Head-based versus tail-based sampling. What can tail-based do that head-based structurally cannot, and what does it cost?
142. `[T]` You sample at 1 percent and your traces show no errors. Explain why, and what you change.
143. `[D]` Span attributes, events and links. When do you use a link instead of a parent-child relationship?
144. `[D]` Cardinality: why a `user_id` label destroys a metrics backend, and what you do when you genuinely need per-customer visibility.
145. `[D]` The RED and USE methods. Which applies to a service and which to a resource, and what does each miss?
146. `[D]` Correlation IDs versus trace IDs - do you need both? How do they reach the log line?
147. `[D]` Structured logging in a distributed estate: the mandatory field set, and what must never appear in a log.
148. `[T]` Averages lie. Explain why you cannot average p99s across instances, and what you do instead.
149. `[D]` SLI selection: request-based versus window-based, and how you pick the threshold defensibly.
150. `[D]` Error budgets: the arithmetic for 99.9 percent, burn-rate alerting, and multi-window multi-burn-rate alerts.
151. `[T]` Your dashboards are green during a customer-visible outage. Give four realistic reasons.
152. `[D]` Distributed debugging: given a slow p99 with no errors, describe the sequence of signals you look at, in order.
153. `[D]` Observability cost control: what you drop, what you aggregate, what you keep at full fidelity, and who decides.
154. `[A]` Design the observability standard you would mandate for 40 services, and how you would get it adopted without a mandate.

---

## 9. Security across service boundaries

> Assumed known: `01-java` Q132-149 material via `02-spring` Categories 8-9 (filter chain, JWT, OAuth2 grants, resource servers, token relay).

155. `[C]` Edge authentication with internal trust versus end-to-end token propagation. State the threat model each one assumes.
156. `[T]` "We validate the JWT at the gateway and pass user ID in a header internally." What exactly is the vulnerability, and when is it acceptable?
157. `[D]` Token exchange (RFC 8693) and the on-behalf-of flow. What problem do they solve that plain token relay does not?
158. `[D]` Service-to-service authentication: mTLS, mutual JWT, SPIFFE/SPIRE. How does each bootstrap identity?
159. `[D]` What is a SPIFFE ID and an SVID, and how does workload attestation actually work?
160. `[T]` Certificate rotation in a mesh with a 24-hour lifetime - what breaks if a service caches the trust bundle, and what is the correct rotation order?
161. `[D]` Authorization in a distributed system: centralized PDP, embedded policy engine, or per-service logic. Compare latency, consistency and blast radius.
162. `[D]` Token lifetime, revocation and introspection. Why is a short-lived JWT usually better than a revocation list?
163. `[T]` A downstream service receives a valid token with more scopes than the operation needs. Whose bug is that, and what pattern prevents it?
164. `[D]` The confused deputy problem in a microservice estate - give a concrete example and the fix.
165. `[D]` Secrets distribution to services: static secrets, dynamic secrets, workload identity. Rank them and justify.
166. `[D]` Multi-tenant data isolation: what enforces it, and why "every query includes a tenant_id" is not sufficient.
167. `[D]` Audit logging that a regulator will accept: what is recorded, where, and how you prove it was not tampered with.
168. `[T]` An internal service is only reachable from the VPC, so it has no authentication. Enumerate the ways this becomes an incident.
169. `[D]` Supply chain: SBOM, signed images, admission control, and what you do when a CVE lands in a base image used by 40 services.
170. `[A]` Design the authentication and authorization architecture for a system with web, mobile, partner API and internal batch consumers.

---

## 10. Deployment, release and runtime topology

> Assumed known: `01-java` Q202-204 (CI/CD, blue-green versus canary, IaC) and `02-spring` Q262 (multi-service migration planning).

171. `[C]` Deployment versus release. Why does separating them change your entire risk posture?
172. `[C]` Rolling, blue-green, canary and dark launch. Give the rollback time and the data-migration constraint of each.
173. `[T]` Blue-green with a shared database - state the exact schema rules that make it safe.
174. `[D]` Canary analysis: which metrics you compare, why absolute thresholds are wrong, and what a control group buys you.
175. `[D]` Feature flags: release flags, ops flags, experiment flags, permission flags. Which ones must have an expiry date and why?
176. `[T]` A feature flag evaluated in two services disagrees for the same request. How does that happen and how do you prevent it?
177. `[D]` Database migrations with zero downtime across N instances - the expand-migrate-contract sequence in full.
178. `[T]` You need to rename a column used by two services. Write out the deployment order, including the rollback point.
179. `[D]` Backwards-compatible message schema changes during a rolling deploy - what must be true about producers and consumers, and in which order do you deploy them?
180. `[D]` Independent deployability: what genuinely blocks it in most estates, and how do you measure whether you have it?
181. `[T]` Your services are independently deployable but you still have a release train. What does that tell you?
182. `[D]` Versioning and compatibility policy for a shared platform library used by 40 services.
183. `[D]` Environment strategy: how many pre-production environments do you actually need, and what does each one prove?
184. `[D]` Configuration across services: what belongs in the image, in the environment, in a config service, and in the database?
185. `[T]` A configuration change caused a bigger outage than any code change that year. What controls does configuration need that it usually lacks?
186. `[A]` Design the release process for a system where three services must ship a coordinated change and one is owned by another company.

---

## 11. Performance, scalability and capacity

> Assumed known: `01-java` Q194 (auto-scaling, why CPU is often wrong) and Q180 (caching).

187. `[D]` Latency arithmetic: a request fanning out to five services in parallel with p99 of 100ms each. What is the resulting p99, and why?
188. `[T]` Why does adding a replica sometimes make p99 latency worse?
189. `[C]` Little's Law - state it, and use it to size a thread pool and a queue for a known throughput and latency target.
190. `[D]` The Universal Scalability Law: contention and coherency. What does the coherency term predict that Amdahl's Law does not?
191. `[D]` Queue depth as a scaling signal versus CPU versus request rate. Which do you scale on for a consumer, and why?
192. `[T]` Auto-scaling on a lagging metric with a slow startup time oscillates. Describe the fix precisely.
193. `[D]` Connection pool sizing across services: why the sum of all service pools must be checked against the database limit, and what happens when it is not.
194. `[D]` The N+1 problem at service granularity - how it appears, how you detect it in traces, and the three fixes.
195. `[D]` Batching and coalescing requests: request collapsing, micro-batching, and the latency they add.
196. `[D]` Backpressure end to end: how does a slow database eventually tell an HTTP client to slow down, and what breaks the chain?
197. `[T]` Async and non-blocking do not increase capacity by themselves. Explain what they actually change and when they help.
198. `[D]` Capacity planning: how do you turn a business forecast into an instance count you can defend in a review?
199. `[D]` Load testing a microservice estate: what you must test that a single-service load test cannot reveal.
200. `[A]` Cost per request has doubled while traffic grew 20 percent. Walk through your investigation.

---

## 12. Testing distributed systems

> Assumed known: `01-java` Q128-129 (test pyramid, mocking) and `02-spring` Q221-233 (test slices, Testcontainers, contract tests).

201. `[C]` The test pyramid versus the test honeycomb for microservices. Which do you argue for and why?
202. `[D]` Component testing a single service with its dependencies stubbed - what is in scope, and what is the stub fidelity problem?
203. `[T]` Why is a full end-to-end environment with all 40 services a trap, and what do you do when leadership insists on one?
204. `[D]` Consumer-driven contract testing in detail: the pact broker, `can-i-deploy`, and how it gates a pipeline.
205. `[T]` Contract tests give you compatibility but not correctness. Give an example of a change that passes contracts and destroys production.
206. `[D]` Testing asynchronous flows deterministically - what do you assert on, and how do you avoid `Thread.sleep`?
207. `[D]` Testing idempotency, retries and duplicate delivery. Design the test cases.
208. `[D]` Fault injection in tests: latency, errors, partitions. Where do you inject and how do you keep it out of production?
209. `[D]` Testing with real infrastructure: Testcontainers, ephemeral namespaces, and the cost model of each.
210. `[T]` Your integration test suite is flaky at 3 percent. Why is that worse than 30 percent, and how do you attack it?
211. `[D]` Testing in production: synthetic monitoring, canary requests, shadow traffic. What safety properties must hold?
212. `[D]` Data management for tests: fixtures, factories, anonymized production data. What are the legal and practical constraints?
213. `[D]` How do you test a saga's compensation paths, including the ones that only occur under partial failure?
214. `[A]` Define the testing strategy and the CI gates for a 40-service estate where any team can deploy any time.

---

## 13. Multi-tenancy, versioning and monolith decomposition

> Assumed known: `01-java` Q166 (monolith versus microservices) and `02-spring` Q259-260 (modular monolith, multi-tenancy in Spring).

215. `[C]` Multi-tenancy models: silo, pool and bridge. Give the cost, isolation and noisy-neighbour profile of each.
216. `[T]` A single enterprise customer demands their data in a separate database. What does that one exception do to your deployment pipeline and your on-call?
217. `[D]` Tenant context propagation across services and async boundaries. Where does it live and how is it validated?
218. `[D]` Per-tenant rate limiting, quotas and cost attribution. How do you know what a tenant costs you?
219. `[D]` The modular monolith as a destination rather than a stepping stone. When is it the right final answer?
220. `[D]` The strangler fig in detail: the facade, the routing rules, the data synchronization, and how you know a slice is done.
221. `[T]` During a strangler migration, both the monolith and the new service can write the same data. What are your options, ranked?
222. `[D]` Branch by abstraction versus parallel run versus dark launch for a risky extraction. Compare confidence and cost.
223. `[D]` How do you verify a parallel run - what do you compare, what discrepancies are acceptable, and who signs off?
224. `[D]` Extracting a service from a monolith: the order of operations for code, data, and traffic. Which comes last and why?
225. `[T]` The extracted service is slower than the monolith method it replaced. Is that a failure? How do you frame it?
226. `[D]` Data migration approaches: dual write, CDC-based sync, and a one-shot cutover. Rank them by risk.
227. `[D]` How do you decide when to stop a decomposition programme that has run for two years?
228. `[A]` A 12-year-old monolith, 300 tables, 40 engineers, no tests, feature delivery still required. Give your 18-month plan.

---

## 14. Architecture design exercises

> Assumed known: everything above. These are open-ended; you are judged on the questions you ask and the trade-offs you name, not the diagram.

229. `[A]` Design an order management platform for an e-commerce business handling 5,000 orders per minute at peak. Name your boundaries and justify each.
230. `[A]` Design a payment processing system that must never double-charge, integrating three external providers with different reliability.
231. `[A]` Design the migration of a real-time telecom billing system from a monolith to services with zero customer-visible downtime.
232. `[A]` Design a notification platform - email, SMS, push, in-app - with per-tenant rate limits, preferences and delivery guarantees.
233. `[A]` Design an inventory system for 200 warehouses where overselling is unacceptable but availability is business-critical.
234. `[A]` Design the platform layer - the golden path - that 40 product teams will build on. What do you make mandatory?
235. `[A]` Design an event-driven order fulfilment flow spanning six services, and make it fully recoverable from any single-service outage.
236. `[A]` Design a multi-region active-active deployment for a system with strong consistency requirements on one entity and eventual consistency everywhere else.
237. `[A]` Design the read path for a customer dashboard that aggregates data from nine services with a 200ms p99 budget.
238. `[A]` Design a system that ingests 500,000 IoT telemetry messages per second and supports both real-time alerting and historical query.
239. `[A]` Design the API and integration architecture for onboarding third-party partners who will call you and whom you will call.
240. `[A]` Design the incident-response and operational model for an estate of 40 services owned by 12 teams.

---

## 15. Broker topology and legacy integration

> Assumed known: category 3 above (delivery semantics, DLQs, ordering) and `02-spring` categories 16-17 for the Spring client APIs - `JmsTemplate`, `@RabbitListener`, Spring Integration and Spring Web Services. This category is about the broker and the estate, not the annotations.

241. `[D]` Design the exchange, queue and binding topology for an estate of 30 services on RabbitMQ. Who owns each object, and what stops it drifting?
242. `[T]` Quorum queues versus classic mirrored queues - what changed and why, and what does a lazy queue protect you from?
243. `[C]` Competing consumers versus fan-out subscription - when does a queue broker genuinely beat a log-based one?
244. `[D]` Router, splitter, aggregator and claim check - which of these justify an integration layer, and which are better as ordinary code in a service?
245. `[T]` You must bring a legacy IBM MQ or JMS estate into an event-driven architecture. Describe the bridge, and the mistake that turns it into permanent coupling.
246. `[D]` A partner integration that must remain SOAP with WS-Security, inside an otherwise event-driven estate. Where does it live and what does it expose inward?
247. `[D]` Message-level security - signing and encrypting payloads across brokers. When is transport security not enough, and what does it cost you operationally?
248. `[A]` One estate, three workloads: high-volume clickstream, per-customer order events requiring ordering, and low-volume partner file notifications. Choose Kafka, RabbitMQ or SQS for each and defend it.

---

## 16. Leadership and organizational

These have no model answer on purpose - they must be your own stories from Verizon India and Sonata Software. Use STAR-L and quantify the result.

249. Tell me about a service boundary you got wrong, how you discovered it, and what it cost to fix.
250. Describe a distributed systems incident you led, from detection to prevention.
251. How do you convince a team that wants to split a monolith into 30 services that they should start with three?
252. Tell me about a time you removed a piece of distributed infrastructure rather than adding one.
253. How do you handle a team that owns a service everyone depends on and that is always the bottleneck?
254. Describe how you introduced an estate-wide standard - contracts, observability, or resilience - without formal authority.
255. Tell me about a migration you stopped or descoped, and how you justified it.
256. How do you set up on-call and ownership for services whose original authors have left?
257. Describe a disagreement with an architect or principal peer about a distributed design, and the outcome.
258. Which widely recommended microservices practice do you consider harmful, and how do you argue against it?
