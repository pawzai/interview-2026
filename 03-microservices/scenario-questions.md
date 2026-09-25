# Scenario Questions

Distributed systems production incidents, architecture exercises and leadership situations.

Every scenario uses **CIDER**, defined in [../01-java/README.md](../01-java/README.md):

- **Clarify** - what you ask before answering. Never diagnose or design in silence.
- **Isolate** - narrow the failure domain or the core requirement.
- **Decide** - commit to an approach and name the trade-off.
- **Execute** - the concrete steps.
- **Reflect** - what you monitor, prevent, or would do differently.

Read the scenario, answer out loud for five minutes, then compare. The model responses are longer than you should speak - use them as the map, not the script.

---

## Part A - Production incidents

### S1. The dependency recovered and nothing else did

> A downstream provider had a 20-minute outage. It has been healthy for 90 minutes. Your platform is still returning errors on most requests, CPU is pinned across the fleet, and scaling out has not helped.

**Clarify.** Is the downstream genuinely healthy - are direct calls from a shell succeeding? What is the *offered* load compared to normal? What is goodput (successful responses per second) versus throughput (requests processed)? Are queue depths growing? Are circuit breakers open, closed, or flapping? Did anything auto-scale, and did that make it better or worse?

**Isolate.** "The trigger is gone and the system is still down" is the definition of a **metastable failure state** (Q112). The system has two stable states and the outage moved it to the bad one, where the degradation itself now generates the load that sustains it. The sustaining loops, in order of likelihood:

1. **Retry amplification** (Q106). Three layers each retrying three times means the offered load is up to 27× normal. During the outage, clients queued and retried; now they are all retrying simultaneously and the system cannot serve even the original load at that multiple. The retries are the load.
2. **Queues full of expired work.** Requests whose clients gave up 40 minutes ago are still being processed, consuming 100 percent of capacity to produce responses nobody reads. High CPU, zero goodput - which matches the symptom exactly.
3. **Cold caches.** The outage emptied or evicted them; the recovery load all misses; the origin cannot serve full traffic uncached; the cache never warms because nothing completes.
4. **Thread and connection pool exhaustion** where slow work holds the resources that fast work needs to free them.
5. **Thundering herd** (Q113) - every client backing off by the same deterministic interval and retrying in synchronized waves.

Scaling out not helping is strong confirmation: if capacity were the constraint, more capacity would help. It is not a capacity problem, it is a feedback problem.

**Decide.** The counter-intuitive move is required: **reduce load aggressively rather than adding capacity**. Serving 30 percent of traffic successfully lets the system escape the bad state and then ramp; serving 100 percent badly never recovers. I would say this out loud to whoever is on the call, because "shed 70 percent of traffic during an outage" needs agreement before you do it.

**Execute.**

1. **Shed load at the edge** (Q110) - reject a large fraction immediately with 503 and `Retry-After`, prioritizing so that health checks and internal traffic are shed before interactive users. Cheap rejection, not queued rejection.
2. **Stop the retries.** Force circuit breakers open, or engage retry budgets, or disable retries at the gateway. This removes the amplification factor directly.
3. **Drain the queues of expired work** rather than processing it - if deadline propagation exists (Q104) this is automatic; if not, purge by age.
4. **Warm the caches** before restoring traffic, from a known key list if one exists.
5. **Ramp back gradually** - 10 percent, 25, 50, 100, watching goodput at each step. Do not remove the shedding all at once, or you re-enter the same state.
6. Only then consider whether capacity is actually short.

**Reflect.** The prevention list is the mechanism list inverted: **retry budgets** capped at 10-20 percent of successful traffic (Q106), **deadline propagation** so expired work is discarded rather than processed (Q104), **bounded queues** sized in latency terms rather than depth (Q189), **load shedding on queueing delay** as a standing capability rather than an incident improvisation, and **full jitter** on every backoff (Q105). I would also add a **goodput** metric alongside throughput, because the dashboards during this incident showed a busy, healthy-looking system.

The systemic point for the postmortem: capacity was never the defence. The defence is not generating the amplification, and that is a design property, not an operational one.

> *Hook: an amplification incident you worked, the multiplier you measured, and the retry budget you introduced afterwards.*

---

### S2. Orders stuck between paid and shipped

> Support reports 4,000 orders where the customer has been charged and nothing has shipped. They accumulated over the last six hours, during which the warehouse allocation service was down. It is back now. The oldest is six hours old and customers are calling.

**Clarify.** What states are the 4,000 in, and how many in each? Which ones are past the payment capture (the pivot, Q85)? Is the allocation service healthy and at what capacity? Does it expose an outcome lookup by idempotency key? Are new orders still entering the same state? Is there a regulatory or contractual clock on this?

**Isolate.** This is Q100 as a live incident. The critical realization is that the 4,000 are **not homogeneous**, and treating them as one batch is the main way this goes wrong. Segment first, from the saga state store (Q99):

- **Past the pivot** (payment captured, allocation pending) - these must be driven forward. Compensating would refund a customer whose order is valid, and there is no reversing a capture without a refund event.
- **Pre-pivot** (authorized but not captured) - these can be unwound cleanly.
- **Awaiting a reply that may still arrive** - a command was sent and no response received. A timeout is not a failure (Q33), so the outcome is *unknown*, not failed.
- **Genuinely ambiguous** - allocation may or may not have happened and there is no way to ask.

If that segmentation query is hard to run, that is the first finding of the postmortem.

**Decide.** Three principles, stated before touching anything:

1. **Never assume a timeout means failure.** Query the allocation service for the actual outcome using each saga's idempotency key (Q94). Most of the ambiguous pile becomes known, and this is what prevents double-allocation.
2. **Post-pivot first.** Those customers have paid; they are the ones with a live grievance.
3. **Do not release 4,000 retries into a service that just came back.** That is how you cause S1.

**Execute.**

1. **Rate-limit or pause new saga starts** if allocation is still fragile. Stop the pile growing before shrinking it.
2. **Reconcile**: for each stuck saga, call the outcome lookup with the original idempotency key. Classify into already-allocated, definitely-not-allocated, and unknown.
3. **Drive the post-pivot set forward** with a controlled replay - start at a small fraction of normal throughput, watch allocation's error rate and latency, ramp. Put a circuit breaker on the *replay job itself* so it stops rather than re-triggering the outage.
4. **Compensate the pre-pivot set**, rate-limited, verifying each compensation rather than assuming it.
5. **Communicate to customers before they call again** - a proactive message on the affected orders is worth more than any technical step here.
6. **Work the residual manually**, prioritized by value and age, with a defined escalation for cases needing a business decision.
7. **Reconcile at the end**: prove every one of the 4,000 reached a terminal state and that money captured matches orders fulfilled. Produce the number.

**Reflect.** Three preventions. **An alert on saga age** - the first hundred should have paged someone at the 20-minute mark, and 4,000 accumulating silently over six hours is the actual failure (Q99). **A circuit breaker in front of allocation** so sagas fail fast into an explicit `DEFERRED` state rather than sitting in `AWAITING_REPLY`, which makes them easy to find and safe to replay. And **bulk remediation tooling built in advance** - the segment-and-replay job should not be written during an incident. I would also ask whether the pivot can move later, so a downstream outage leaves fewer customers past the point of no return.

---

### S3. Duplicate charges after a routine redeployment

> Finance reports 340 customers charged twice within a 15-minute window yesterday. That window matches a routine rolling deployment of the payment service. The code has an idempotency check and the developer insists it is correct.

**Clarify.** What exactly does the idempotency check look like - where is the key generated, where is it stored, and is the check-and-claim atomic? Were the duplicates from the same client request retried, or from message redelivery? Do both charges share an idempotency key? What is the payment provider's own deduplication behaviour? Were consumer offsets involved - is this a message-driven path? Was there a rebalance during the deployment?

**Isolate.** A deployment window is the clue: rolling deployments produce three things that expose idempotency defects, and the correct answer distinguishes them.

1. **Check-then-act race** (Q97). If the implementation reads the idempotency store, finds nothing, then processes, then writes - two concurrent requests both pass the check. During a rolling deploy, in-flight requests are retried by the client or the gateway onto a *different instance*, creating exactly the concurrency this bug needs. It passes every sequential test and fails in production. This is my primary hypothesis.
2. **Deduplication state that is not shared or not durable.** An in-memory cache, or a Redis instance with a TTL shorter than the retry window, or a key store scoped per instance. A restart wipes it, and a rolling deploy restarts everything.
3. **Consumer rebalance replay** (Q46). If the charge is triggered by a message, a deployment causes a rebalance; uncommitted offsets mean messages are redelivered to a new instance and reprocessed. At-least-once delivery is guaranteed here, not merely possible (Q43), so the consumer must be idempotent against it - and if the effect is not in the same transaction as the offset or inbox record (Q98), it is not.
4. **Graceful shutdown missing** (Q118) - the old instance was SIGKILLed mid-processing, after charging and before committing.
5. **A key generated per attempt** rather than per logical operation (Q94), so the two attempts have different keys and the check is working perfectly on the wrong data.

**Decide.** Prove which one before changing code, because the fixes differ and "add a check" applied to a race changes nothing while appearing to. The evidence: pull the two charge records for several affected customers and compare their idempotency keys, their instance IDs, their timestamps and their trace IDs. Same key on both means a race or a non-atomic claim; different keys means a key-generation problem; a rebalance in the logs at that moment means redelivery.

**Execute.**

1. **Contain**: refund the 340 duplicates and notify those customers before they discover it. Do this first; it is not the interesting part but it is the part that matters.
2. **Reproduce** the race in a test - two threads, one key, a latch to force overlap (Q207). If it reproduces, the diagnosis is confirmed and the test becomes the regression guard.
3. **Fix by claiming atomically**: `INSERT` the key with a unique constraint *before* doing the work, treating a constraint violation as "someone else owns this" (Q97). Return `409` for `IN_PROGRESS` and the stored response for `COMPLETED`.
4. **Move the claim into the same transaction as the effect** where possible, or into the inbox pattern for message-driven paths (Q93).
5. **Pass the idempotency key to the payment provider** so their deduplication is a second line of defence (Q230).
6. **Fix graceful shutdown** so in-flight work completes before the instance stops.
7. **Audit for the same pattern** in every other non-idempotent operation - this bug is rarely alone.

**Reflect.** The systemic issue is that idempotency was implemented as a *check* rather than as a *claim*, and nothing in the test suite exercised concurrency. Prevention: a shared test harness that runs every handler through duplicate, concurrent-duplicate and crash-after-effect cases automatically (Q207); a reconciliation control that compares charges against orders continuously and alerts on the first duplicate rather than the 340th; and a review rule that any check-then-act across a network boundary is presumed racy until proven otherwise.

---

### S4. One message stopped a partition

> A Kafka consumer for order events has zero lag on eleven partitions and 400,000 messages of lag on the twelfth. It has been that way for three hours. The consumer is alive, CPU is low, and there are no errors in the aggregate error-rate dashboard.

**Clarify.** What is the consumer doing with the message that is stuck - is it looping on a retry, or blocked on something? What exception, if any? Is the retry in-place or via a retry topic? Is ordering a genuine business requirement for this topic? What is downstream of this consumer and what is the impact of three hours of delay for that partition's customers?

**Isolate.** Lag on exactly one partition with the others healthy is the signature of a **poison message blocking an ordered partition** (Q48, Q50). The consumer is preserving ordering by refusing to advance past a message it cannot process, which is correct behaviour producing an unacceptable outcome.

Distinguish the causes:

1. **A deterministic processing failure** being retried in place forever - a deserialization error, a null field, an unknown enum value, a constraint violation. The most likely.
2. **A message that takes enormously longer than others** - a batch order with 10,000 lines hitting an N+1 (Q194) - so it is progressing but at an unusable rate, and possibly also exceeding `max.poll.interval.ms` and causing repeated rebalances (Q47).
3. **A downstream dependency that is broken only for this partition's key range** - one tenant's database shard, for example.
4. **A deadlock or a hung call with no timeout** (Q101), which would explain low CPU and no errors.

The absence of errors on the *aggregate* dashboard is itself a finding: one partition's continuous failure is 1/12 of one consumer's traffic, invisible in an estate-wide error rate. This is the Q151 aggregation-hiding problem.

**Decide.** The immediate question is whether ordering for this partition genuinely matters. If it does, the only way forward is to fix or remove the blocking message; if it does not, route it aside and let the partition drain. I would establish that with the domain owner rather than assuming, because the answer determines the whole response.

**Execute.**

1. **Identify the message.** Consume from the stuck offset with a separate tool or consumer group and inspect it, including its headers and its producing service.
2. **Assess the business impact of three hours** for the affected customers - that determines urgency and whether a partial-ordering compromise is acceptable.
3. **If ordering can be relaxed**: route the failing message to a DLQ with full context (Q50) and let the consumer advance. Fastest resolution.
4. **If ordering is required**: fix the cause. Deploy a code fix if it is a bug; correct the data if it is a data problem; or, if the message is genuinely invalid, get an explicit business decision to skip it and record that decision.
5. **Drain the backlog** with attention to whether 400,000 messages will overwhelm anything downstream - rate-limit if necessary.
6. **Handle the side effects of the delay** - any time-sensitive downstream action for those orders may now need remediation.

**Reflect.** Four preventions, in order of value:

- **Alert on per-partition lag, not aggregate lag** (Q53). Max lag across partitions, and lag measured in time rather than offsets. This alone would have caught it in minutes.
- **Alert on zero consumption with non-zero lag** - a consumer that is alive and making no progress is a distinct and highly actionable signal.
- **Classify exceptions explicitly** into retryable and permanent (Q50), defaulting unknown exceptions to permanent so a new bug surfaces rather than loops.
- **A bounded retry policy with a DLQ**, and a decision recorded per topic about whether ordering is worth partition blocking. The honest framing: **you can have ordering or non-blocking error handling, not both** (Q48), and that choice should be deliberate per topic rather than a default nobody chose.

I would also revisit whether the ordering requirement is really per-partition or per-entity, because a narrower ordering scope (Q49) would have limited the blast radius to one customer rather than one twelfth of the estate.

---

### S5. A slow third party took down everything

> A release added address verification from a third-party API to the checkout flow. Within 40 minutes every endpoint in the service was timing out - including the health endpoint and endpoints that touch neither checkout nor the third party. The third party is responding, just slowly: 8 seconds instead of 200ms.

**Clarify.** Is the verification call inside a transaction? What timeouts are configured on the HTTP client - and does the client have a *request* timeout or only a connect timeout? What is the thread pool and connection pool utilization? Is there a circuit breaker, and what is its state? Did the third party change, or did our call volume change?

**Isolate.** Total service failure caused by one new dependency is the signature of a **shared resource being held**, and the specific mechanism here is that the breaker never fired:

1. **A slow dependency is not a failing dependency** (Q108). A classic circuit breaker counts errors; 8-second successes produce zero errors, so it stays closed while every caller blocks. This is the central finding.
2. **Thread pool exhaustion.** With 200 request threads and an 8-second call, the service can serve 25 checkout requests per second before every thread is occupied. Once they are, *every* endpoint fails, because they share the pool. That is why unrelated endpoints died.
3. **The health endpoint failing** confirms it: it needs a thread too. And if readiness is failing for this reason across all instances simultaneously, the load balancer removes everything (Q117), converting a degraded service into a total outage.
4. **If the call is inside a transaction**, each in-flight request also holds a database connection for 8 seconds, so the connection pool goes too, and now other services sharing that database are affected (Q193).
5. **No bulkhead**, so there was no limit on how much of the service one dependency could consume (Q109).

**Decide.** Mitigate immediately, then fix structurally. Rolling back is the fastest mitigation and I would do that first unless address verification is legally required, because the structural fix is a code change and the service is down now.

**Execute.**

1. **Roll back**, or disable the verification behind a flag if one exists. Feature-flagging a new external dependency is exactly why flags exist (Q171).
2. **Verify recovery** - thread pool utilization returning to normal, error rate falling.
3. **Add the structural protections before re-enabling:**
   - A **request timeout** derived from the checkout latency budget (Q102), not the client default. 500ms, not 30 seconds.
   - A **bulkhead** limiting concurrent calls to this dependency to a small number (Q109), so it can never consume more than its share of threads. This is the most important one, because it protects regardless of whether detection works.
   - A **slow-call rate threshold** on the circuit breaker (Q108), so latency counts as failure.
   - A **defined fallback**: is address verification advisory or blocking? If advisory, proceed without it and flag the order for review. If blocking, fail that endpoint only. Decide deliberately per Q114, and do not return a fake "verified" (Q115).
4. **Move the call out of any transaction** (Q193).
5. **Fix the readiness probe** if it was checking anything shared (Q116).
6. Re-enable behind a canary at 1 percent.

**Reflect.** The systemic issue is that a new external dependency was added to the critical path with no resilience configuration and no review of what it could consume. Prevention: a **checklist gate** for any new outbound dependency - timeout, bulkhead, breaker, fallback, and a named criticality (Q114) - enforced in review; **platform defaults** so a client created through the standard library has a sane timeout and bulkhead even if nobody configures them; and a **fault-injection test** in CI proving the service degrades correctly when this dependency is slow (Q208), which would have caught it before release.

> *Hook: an incident where a slow dependency exhausted a shared pool, and the bulkhead defaults you introduced afterwards.*

---

### S6. The trace goes dark

> A customer complaint says an order took 40 minutes to confirm. The trace shows the API call completing in 180ms and then nothing. The order did eventually confirm. Nobody can explain the 40 minutes, and the team has been on it for two days.

**Clarify.** Is the confirmation path synchronous or event-driven? Which components are between the API and the confirmation - a broker, a scheduled job, an external callback? Does the trace ID appear in any downstream logs? Is this reproducible or a one-off? What was the consumer lag at that time?

**Isolate.** The trace ending at the API boundary means **context is not propagated across the async boundary** (Q140). The work continued; the observability did not. That is the actual problem to solve, and the 40 minutes is a symptom whose cause is currently unknowable.

Where context is lost:

1. **The message producer does not inject `traceparent` into message headers.** The most common cause. Auto-instrumentation covers the standard Kafka client but not a custom serializer, a wrapper, an outbox relay, or a bridge that reconstructs the message.
2. **The outbox relay** (Q90) reads a row and publishes it, and the row does not carry the trace context - so the trace ends at the database write. This is a very common gap in outbox implementations and it should be a stored column.
3. **A thread pool boundary** inside a service, where the context was not captured and restored (Q140).
4. **A scheduled job** picks up the work with no incoming context and starts a fresh root trace with no link back (Q140).
5. **Sampling** - the trace was sampled at the edge but a downstream service made an independent decision, so the spans exist and are fragmented.

For the 40 minutes itself, the candidates are: consumer lag on the relevant partition (S4), a retry with a long backoff, a scheduled job that runs every 30 minutes so the work waited for the next tick, or a DLQ redrive.

**Decide.** Two days of investigation with no answer means the tooling is the bottleneck, not the analysis. I would stop investigating this instance and **fix the propagation first**, because the next occurrence then answers itself in minutes. That is a hard argument to make while a customer is unhappy, so I would pair it with a targeted manual reconstruction for this one order.

**Execute.**

1. **Reconstruct manually** for this order: use the order ID as the join key across every service's logs, and build the timeline by hand. This is exactly what a business correlation ID exists for (Q146), and if the order ID is not logged consistently everywhere, that is finding number two.
2. **Fix trace context propagation across every async boundary:**
   - Inject `traceparent` into message headers at produce time (Q140).
   - **Store the trace context in the outbox row** and restore it in the relay, so the trace survives the database hop.
   - Wrap every executor so context is captured and restored, with a clear in a `finally`.
   - Scheduled jobs start a new root trace and add **span links** to the originating traces of the records they process (Q143).
   - Use **links rather than parent-child** for fire-and-forget consumption, so the parent's duration is not distorted.
3. **Add the business key as a span attribute and a mandatory log field** (Q146, Q147), so order ID is a first-class query dimension everywhere.
4. **Add lag and queue-age metrics** per topic so a 40-minute delay is visible without a trace at all.
5. Once propagated, wait for the next occurrence and read the answer.

**Reflect.** The deeper issue is that observability was treated as per-service instrumentation rather than as an end-to-end property, so it works within a service and fails between them - which is precisely inverted for a distributed system. Prevention: propagation across async boundaries becomes a **platform library responsibility** with wrapped executors, an outbox that carries context, and a Kafka wrapper that injects headers by default (Q154). And a standing test: every async path must have an integration test asserting that a trace ID survives it. That test is cheap and it prevents the entire class.

---

### S7. Everyone read a different price

> For 12 minutes, some customers saw a promotional price on the product page and were charged the standard price at checkout. 900 orders are affected. Both services report normal operation with no errors, and both were serving "correct" data according to their own logs.

**Clarify.** Where does each service get the price - the same source, or its own copy? Are there caches involved, and what are their TTLs? Was there a price change deployed or published at the start of the window? Is the checkout price recomputed or carried from the basket? What is the financial exposure and is there a regulatory obligation to honour the displayed price?

**Isolate.** Both services internally consistent, mutually inconsistent, no errors - this is **cross-service temporal inconsistency** (Q77). The catalogue and the pricing service each hold a cached copy of the price with a different TTL, so a price change propagated to one before the other, and for the duration of the difference the system was coherently wrong.

The specific mechanisms to check:

1. **Different cache TTLs** for the same entity in two services - the direct Q77 case.
2. **Event-driven invalidation that raced** - the evict arrived before the repopulate in one service and after in the other, so one cached the stale value indefinitely with no TTL backstop.
3. **The checkout recomputes rather than carrying the quoted price**, so the basket's price and the charged price come from different reads at different times. This is a design flaw independent of caching.
4. **A partial rollout** of a pricing rule change (Q176) where two services evaluated the same flag differently.

The 12-minute window is diagnostic: compare it against the TTLs. If it matches the difference between two TTLs, that is the answer.

**Decide.** This has a customer-trust and possibly a legal dimension, so the business decision - honour the displayed price or not - comes before the technical fix and is not mine to make. I would get that decision started in parallel with the investigation.

**Execute.**

1. **Quantify** the 900 orders and the financial difference, and hand it to the business with a recommendation.
2. **Confirm the mechanism** by comparing cache configurations and the timing of the price publication against the window.
3. **Immediate mitigation**: align the TTLs, or invalidate both caches, so the window closes.
4. **Structural fix, in order of preference:**
   - **One owner for price.** Checkout should not cache a price independently; it should either call pricing or use the price **quoted into the basket**, with the quote carrying an expiry. A quoted price with a stated validity period is the correct domain model here and it eliminates the whole class.
   - If multiple services must hold a copy, **include the source version in every response and trace** (Q77), so a mismatch at the aggregation point is detectable rather than silent.
   - **Standardize TTLs per entity type** as a platform default, so no two services independently choose.
5. **Add reconciliation**: a continuous job comparing the price shown by each service's public API for a sample of SKUs, alerting on any divergence (Q77).

**Reflect.** Two things worth saying in the postmortem. First, **the absence of errors is what made this expensive** - every technical indicator was green throughout (Q151), and the only signal was customer complaints. The fix is business-level and cross-service consistency monitoring, not more error alerting. Second, this is a **boundary problem wearing a caching costume**: two services owning a view of the same value with no agreement about freshness is a data-ownership failure (Q15), and the durable fix is to decide who owns price and make everyone else derive it.

---

### S8. Two instances both believed they were the leader

> A nightly reconciliation job runs on a single leader instance elected via a Redis lock. Last night it ran twice, concurrently, and wrote 200,000 duplicate ledger entries. The lock code looks correct and has been in production for two years.

**Clarify.** How is the lock acquired and released - is there a TTL, and is the release guarded by an ownership check? Is Redis replicated, and was there a failover last night? What were the GC logs on the instance that held the lock? How long does the job run relative to the lock TTL? Does the ledger write have any uniqueness constraint?

**Isolate.** Two holders of a lock that "looks correct" has a small set of causes (Q74), and the two-year clean history points at a rare trigger:

1. **The holder paused past the TTL** (Q67). A stop-the-world GC pause, a VM migration, a hypervisor suspend or a disk stall freezes the instance; the lock expires; another instance legitimately acquires it; the first resumes still believing it holds the lock. **No lock service can prevent this**, because the process that must check is the process that was frozen. If the job runs for 30 minutes against a 60-second TTL with a refresh loop, a pause longer than the TTL is entirely plausible.
2. **A Redis failover.** The lock was written to the master, acknowledged, and the master died before replicating. A replica was promoted with no record of the lock, and a second instance acquired it. Asynchronous replication makes this a normal outcome of a normal failover, not an exotic failure.
3. **A clock jump** on the Redis node affecting key expiry.
4. **The refresh loop stopped** - the watchdog thread died or was starved - while the job continued.

Check the GC logs and the Redis failover history for last night; one of them will match the window.

**Decide.** The important framing: this is a **correctness lock, not an efficiency lock** (Q74), and correctness locks should not be built on Redis. Fixing the lock is treating the symptom; the durable fix is to make the *write* safe regardless of how many leaders there are. I would do both, but I would prioritize the second, because the first can always fail again.

**Execute.**

1. **Contain**: identify and reverse the 200,000 duplicate entries. If the ledger is append-only (as it should be), that means compensating entries, not deletions, with a clear reconciliation record.
2. **Make the write idempotent** (Q96). Every ledger entry gets a deterministic operation ID - derived from the run date and the source record - with a **unique constraint**. A second concurrent run then produces constraint violations rather than duplicates. This is the fix that actually holds, because it does not depend on the lock being correct.
3. **Add a fencing token** (Q67) if a lock is retained: acquire the lease from a consensus store (etcd, ZooKeeper) that issues a monotonic token, carry it on every write, and have the *database* reject any write with a token lower than the highest seen. Correctness then depends on the resource, not on the client's belief.
4. **Or remove the lock entirely** - make the job resumable and idempotent, partition the work by key so two runners cannot touch the same records, or move to a platform-provided scheduler with genuine single-execution semantics.
5. **Bound the job's work per lock acquisition** - checkpointing in small batches means a lost lock costs one batch, not the whole run.

**Reflect.** The lesson to put in the postmortem is the one that generalizes: **a distributed lock is a hint, not a guarantee.** It provides efficiency (usually one runner) and never correctness (exactly one runner), because the failure mode - a paused client - is outside its control. Anywhere a double-execution corrupts data, the protection must be at the resource: a unique constraint, a conditional update, or a fencing token. I would audit for other places relying on a lock for correctness, because this pattern is rarely used only once.

---

### S9. A schema change nobody noticed for nine days

> A producer added a field to an event and changed `status` from being set at dispatch to being set at label creation. Nine days later, finance reports that the delivery-date SLA report has been wrong for over a week. Contract tests passed, the schema registry passed, and no alerts fired.

**Clarify.** Was the semantic change intentional and known to the producing team? Which consumers depend on `status` and does the producer know who they are? What is the financial or contractual exposure of nine days of wrong SLA reporting? Is the raw event history retained so the correct values can be recomputed?

**Isolate.** Everything passed because **every check was structural and the change was semantic** (Q55, Q205). The field's name, type and presence are unchanged; only its *meaning* moved. A schema registry validates the wire format; a contract test validates the shape; neither can know that `SHIPPED` used to mean "handed to the carrier" and now means "label printed", a difference of roughly a day.

The compounding factors:

1. **The producer could not see its consumers.** With events, there is no call site and no per-field usage telemetry, so the producing team had no way to know that a downstream SLA calculation depended on the timing semantics (Q40). This is the invisible-coupling problem in its purest form.
2. **The consumer had no invariant assertion.** A delivery date one day earlier than physically possible should have been detectable, and nothing checked.
3. **Nine days to detection** because the only consumer of the report is a monthly-ish finance process. There was no continuous reconciliation.

**Decide.** Two workstreams: correct the data, and close the class of failure. The data correction is possible only if the raw events are retained - which is the strongest practical argument for a log-based broker with generous retention (Q42), and I would check that first because it determines whether this is recoverable at all.

**Execute.**

1. **Quantify** the affected period and records, and tell finance the number before they ask.
2. **Recompute** the SLA report by replaying the retained events with the corrected interpretation, or by joining against the carrier's own handover timestamps if available. Restate the report with an explanatory note.
3. **Decide the intended semantics with the business** - which meaning of `SHIPPED` is correct - rather than assuming the old one was.
4. **Fix forward properly** using the expand-contract pattern for semantics (Q205): introduce a **new, unambiguously named field** (`labelCreatedAt` alongside `carrierHandoverAt`), populate both, migrate consumers, then remove. Never repurpose an existing field's meaning.
5. **Add invariant assertions** at the consumer: reject or alert on a delivery date that is impossible relative to the order date.

**Reflect.** Three preventions, and the third is the important one:

- **Encode meaning in the name.** Ambiguous fields like `status` and `date` are where semantic drift hides. Explicit names make a semantic change into a structural one, which tooling can catch.
- **Treat a semantic change as a breaking change**, with the same process as a structural one. This is a policy and review matter, and it needs to be written down because it is not intuitive.
- **Make consumers visible to producers.** A published event contract with a registry of known consumers, so the producing team can answer "who depends on this and how" before changing it. Without that, event-driven architecture trades a visible dependency for an invisible one (Q40), and this incident is what that trade costs.

I would also add **continuous reconciliation** on the SLA figures rather than discovering errors at month-end, because nine days of undetected wrongness is the actual severity here - the change itself was a one-line edit.

---

### S10. Cross-zone traffic tripled the bill

> Finance flags that cloud spend rose 60 percent over two months while request volume grew 15 percent. The largest single line item is inter-availability-zone data transfer, which nobody recognizes as a cost the application should be generating.

**Clarify.** When did it start - gradually or as a step? What changed around that point: a deployment, a cluster upgrade, a scaling policy change, a new service? Which services generate the most cross-zone traffic? Is the cluster spread across three zones and are workloads zone-aware? Has anything changed about payload sizes?

**Isolate.** Cost per request rising while volume is flat means **per-request efficiency has halved** (Q200), so this is not a scaling story. Cross-AZ transfer specifically points at *where* traffic flows rather than how much:

1. **Random pod-to-pod routing across zones.** By default, Kubernetes Services route to any healthy endpoint regardless of zone, so with three zones roughly two thirds of every internal call crosses a zone boundary and is billed. This is the baseline state of most clusters and it is invisible until someone reads the bill.
2. **A recent change made it worse**: more services (more internal hops per request), a service mesh added (every hop now traverses two proxies and may be routed differently), a change to topology-aware routing, or a rescheduling event that spread previously co-located pods.
3. **Payload size growth** - an event-carried-state-transfer change that tripled message size multiplies every cross-zone byte.
4. **Kafka consumers reading from non-local brokers**, which is often the single largest contributor and is fixable with follower fetching.
5. **Chatty interfaces** - an N+1 (Q194) generates cross-zone calls at N times the rate, so an efficiency bug and a cost bug are the same bug.
6. **Observability data** shipped cross-zone (Q153).

**Decide.** Attribute before optimizing. Without per-service cost attribution this is guesswork, and getting attribution in place is worth more than the immediate saving because it prevents recurrence. I would time-box the attribution work to a few days and then act on the top two contributors.

**Execute.**

1. **Get attribution**: VPC flow logs or the mesh's own telemetry, aggregated by source and destination service and by zone pair. This names the top contributors within hours and it is usually two or three services.
2. **Correlate with the change** that started it - overlay the cost curve with deployment and cluster events.
3. **Apply topology-aware routing** so calls prefer same-zone endpoints, with fallback across zones for availability. Kubernetes topology-aware hints, or the mesh's locality-aware load balancing. This is the single largest lever and it is a configuration change.
4. **Enable Kafka follower fetching** so consumers read from a same-zone replica.
5. **Reduce the traffic itself**: fix the N+1s the attribution surfaces, batch chatty calls (Q195), compress large payloads, and reconsider any event carrying more state than consumers use.
6. **Check the availability trade explicitly** before rolling out zone affinity - preferring same-zone concentrates load and can create a capacity problem if one zone's replicas are insufficient. Topology hints handle this, but it must be verified rather than assumed.
7. **Measure the effect** and report the saving.

**Reflect.** The systemic gap is that **cost was not a monitored signal with an owner** (Q153, Q200). Prevention: cost per request per service on a dashboard with an anomaly alert, so this is caught in days rather than at a quarterly review; cost attribution to teams, because unattributed cost is nobody's problem; and a cost consideration in the review checklist for changes that plausibly affect unit economics - a new dependency, a payload change, a topology change. I would also note for the architecture record that **inter-service chattiness has a direct, measurable cloud cost**, which is a useful new argument in future boundary discussions (Q13).

> *Hook: a cost investigation you ran, what the attribution revealed, and the saving.*

---

## Part B - Architecture and design

### S11. An event-driven fulfilment flow recoverable from any outage (Q235)

**Clarify.** Six services - which, and what are the irreversible steps? What is the order volume and peak shape? What does "recoverable" mean to the business: eventual completion, or completion within a stated time? Is customer-visible partial progress acceptable? Are any of the six third-party or otherwise outside our control? What is the acceptable end-to-end latency for the happy path?

**The shape.** Six participants with branching and compensation is well past the choreography threshold (Q86), so this is **orchestrated**: an order fulfilment orchestrator holding the workflow as explicit, persisted state, sending commands and receiving replies over a broker.

```
Orchestrator
  1. Inventory      reserve            → compensatable (release)
  2. Payment        authorize          → compensatable (void)
  3. Order          confirm            → compensatable (cancel)
  4. Payment        capture            → PIVOT
  5. Warehouse      allocate & pick    → retriable
  6. Shipping       book carrier       → retriable
  7. Notification   notify customer    → retriable
```

**The design decisions and why each one is what makes it recoverable:**

1. **Pivot placed as late as possible** (Q85). Everything fallible and reversible happens first; capture is the point of no return; everything after is retriable-forever. A six-hour outage of the warehouse service therefore leaves orders that must be *driven forward*, not unwound - which is a much better business outcome than 4,000 refunds.
2. **Outbox in every participant and in the orchestrator** (Q90). No participant ever performs a state change and a publish as two operations. The orchestrator's state transition and the command it emits are one local transaction, so a crash between deciding and sending is impossible (Q87).
3. **Every participant is idempotent** (Q94, Q98), with the command's ID as the idempotency key and an inbox table claimed in the same transaction as the effect (Q93). This is what makes at-least-once delivery survivable and what makes replay a safe operational tool rather than a risk.
4. **Every step has a timeout and every timeout means *unknown*, not failed** (Q33). On timeout, the orchestrator **queries the participant for the outcome** by idempotency key before deciding. This requires every participant to expose an outcome lookup, and I would make that a mandatory part of the participant contract - it is the single most valuable interface requirement in the design.
5. **Late replies are handled state-dependently** (Q88). A success arriving for a step already compensated triggers compensation of that step plus a reconciliation record. Dropping it loses money.
6. **Saga state is queryable by business key** (Q99): current step, full transition history with timestamps and attempt counts, and the saga ID propagated as trace baggage so the state links to the trace. "Where is order 12345" is one query.
7. **Explicit intermediate states in the domain model.** `AWAITING_ALLOCATION` is a real business state that support sees and reports handle, not a transient implementation detail (Q83).
8. **A `DEFERRED` state fronted by circuit breakers.** When a participant is down, the orchestrator fails fast into `DEFERRED` rather than accumulating thousands of sagas in `AWAITING_REPLY` (S2). Deferred sagas are a queryable, replayable set with an alert on depth.

**How it survives any single-service outage:**

| Failed service | Behaviour |
| --- | --- |
| Inventory | Pre-pivot: sagas park in `DEFERRED`, retried on recovery. No money taken |
| Payment | Pre-pivot: same. Post-pivot capture: retried; if capture fails permanently, the order is flagged for manual resolution with the authorization still valid |
| Warehouse | Post-pivot: retried indefinitely with escalating backoff; customer notified of delay after a threshold |
| Shipping | Post-pivot: retried; alternative carrier as a fallback route |
| Notification | Retried; failure is logged, never blocks the order |
| **Orchestrator** | Stateless apart from its store; restarts and resumes from persisted state. The recovery sweeper picks up sagas past their deadline |
| **Broker** | Outbox rows accumulate; the relay drains them on recovery. Nothing is lost |

**Operational capabilities I would build alongside**, because they are what make it recoverable in practice rather than in theory:

- **A saga age alert** at a fraction of the expected duration (S2's missing control).
- **Bulk remediation tooling**: segment stuck sagas by state and pivot position, and replay or compensate with rate limiting and a circuit breaker on the remediation job itself (Q100).
- **A reconciliation job** proving that captured payments and fulfilled orders agree, with the residual reported.
- **Compensation-path tests**, including timeout-then-late-success, generated per step (Q213).

**What I would not do**: choreography (unanswerable "where is this order"), a distributed transaction (Q64), or event sourcing for the orchestrator unless there is a specific audit requirement - a persisted state machine with a transition history gives the same operational benefit at a fraction of the cost.

> *Hook: a saga you designed, where you placed the pivot, and the outage that tested it.*

---

### S12. Multi-region active-active with one strongly-consistent entity (Q236)

**Clarify.** What is the entity that needs strong consistency, and what is its write rate? What are the regions and the inter-region latency (typically 70-100ms US-EU, 150ms+ US-APAC)? Is the driver latency, availability, or data residency - because those lead to different designs? What is the RTO and RPO? Is a regional failure expected to be transparent to users, or is a brief degradation acceptable? Are there residency constraints preventing data from leaving a region?

**The core insight to state early**: active-active with strong consistency on a single entity requires either **cross-region consensus** (correct, and it costs a round trip on every write) or **single-region ownership per entity** (fast, and it costs availability for that entity if its home region is lost). There is no third option, and PACELC (Q63) says the latency cost is paid on every write even with no partition. Which one to choose depends entirely on the write rate and the availability requirement for that one entity, so I would establish those numbers before designing.

**The architecture:**

**For the eventually-consistent majority (90+ percent of the system):**

- **Full active-active.** Each region has a complete stack, its own database, and serves all reads and writes locally.
- **Asynchronous cross-region replication** of events, not of database rows - each region publishes its domain events to a global stream (MirrorMaker, or a globally-replicated topic) and regional consumers build local projections.
- **Conflict avoidance by ownership**: each entity has a **home region** derived from a stable attribute (customer's region, tenant's region), and writes for that entity are routed there. Concurrent conflicting writes then cannot occur, which is far better than resolving them (Q69).
- Where genuinely concurrent writes must be allowed, **commutative or CRDT-shaped data** (Q70), never last-write-wins on timestamps.
- **Session guarantees** (Q62) via sticky routing and position tokens (Q72), so a user always sees their own writes even though the global state is eventual.

**For the one strongly-consistent entity** - say, account balance or seat inventory - I would present both options and pick based on the clarified numbers:

**Option A: single-region ownership with a home region per entity.**

- Each entity has a home region; all writes route there; reads may be served locally from a replica with a freshness token or routed home when linearizability is required.
- **Cost**: writes from a non-home region pay one cross-region round trip (70-150ms). Loss of the home region makes that entity's writes unavailable until failover, which requires a promotion decision and a fencing mechanism to avoid split-brain (Q67).
- **When it wins**: high write rate, entities naturally partitioned by geography, and a brief per-entity unavailability during a regional failure is acceptable.

**Option B: cross-region consensus** (Spanner, CockroachDB, YugabyteDB, or a Raft group per shard).

- Writes commit via a quorum across at least three regions, so no single region's loss affects availability or correctness.
- **Cost**: every write pays a cross-region consensus round trip - the latency is a floor set by geography, and it applies even in the no-failure case. Also an operational and licensing cost.
- **When it wins**: the entity's writes are low-rate but must never be unavailable, and correctness is worth 100-200ms per write.

**My default recommendation**: Option A, with the entity's home region chosen by the customer's own region so the common case is local and fast, and Option B reserved for the case where the business genuinely cannot tolerate per-entity unavailability. And I would say explicitly that **three regions is the minimum for Option B**, because a two-region quorum tolerates no failures (Q66).

**The hard problems to name, because interviewers look for them:**

1. **Split-brain during a partition.** Any failover must be fenced (Q67) - a monotonic epoch that the storage layer enforces - or you get two writers and silent corruption. Automatic failover for a strongly-consistent entity is dangerous; I would prefer a human-in-the-loop promotion with a fast, rehearsed runbook.
2. **Replication lag becoming user-visible.** A user travelling between regions, or a request routed differently, sees data go backwards (Q62). Session tokens are the mitigation and they must be designed in, not retrofitted.
3. **Cross-region cost.** Inter-region egress is expensive and replicating everything is a large recurring bill (S10). Replicate deliberately.
4. **Testing.** A partition between regions must be exercised regularly (Q119), or the failover path is theoretical.
5. **Data residency** may forbid an entity leaving its region entirely, which rules out Option B for that data and forces Option A regardless of the availability argument.

**What I would monitor**: cross-region replication lag as a first-class SLI, per-region write latency split by home and non-home, conflict and divergence rates, and a continuous reconciliation of the strongly-consistent entity against its regional replicas.

---

### S13. A 200ms customer dashboard over nine services (Q237)

**Clarify.** Which of the nine are on the critical path versus enhancement? What are each service's current p50 and p99? Is the 200ms a p99 or an average - and for which percentile of users? How fresh must each section be - can any tolerate minutes-old data? Is partial rendering acceptable to the product owner? What is the request rate and the read-to-write ratio? Is the dashboard personalized per user, or largely shared?

**The arithmetic first, because it decides the design.** Nine parallel calls each with a p99 of 100ms gives an aggregate p99 corresponding to each service's **p99.9** (Q187) - realistically 300-500ms. So **nine synchronous parallel calls cannot meet a 200ms p99**, and the design must reduce the number of calls on the critical path, not merely parallelize them. Saying this early, with the arithmetic, is the substance of the answer.

**The design, in layers:**

**1. Precompute what you can.** The dominant technique. Most dashboard content is derived from events the services already publish, so build a **read model** (Q39, CQRS) - a denormalized per-customer document maintained by consuming domain events from all nine services and updated asynchronously. A single key-value read then serves most of the page in single-digit milliseconds.

- Storage: a document store or key-value store keyed by customer ID, sized for a point read.
- Freshness: bounded by consumer lag, which is monitored as an SLI (Q53). For most dashboard sections, seconds of staleness is invisible.
- **Rebuildable from the event log** (Q57), which is what makes a projection bug survivable.

**2. Classify each of the nine sections by freshness requirement**, with the product owner, into three tiers:

| Tier | Example | Source |
| --- | --- | --- |
| Must be live | Account balance, current order status | Synchronous call, on the critical path |
| Seconds-stale acceptable | Recent orders, loyalty points, recommendations | Read model |
| Minutes-stale acceptable | Spend summary, usage charts, offers | Read model, or a cached aggregate |

The goal is to get the "must be live" tier down to **one or two calls**. That is a product conversation as much as a technical one, and it is usually achievable - most sections that people assume must be live do not need to be.

**3. For the remaining live calls:**

- **Parallel with a total deadline** and per-call deadlines derived from it (Q104). Never serial.
- **Per-field partial-failure policy** decided in advance (Q114, Q237's real difficulty): each section is either critical (fail the page), degraded-stale (serve the read model's value with an "as of" indicator), or omitted. Never a fabricated empty value (Q115).
- **A hedged request** after p95 for idempotent reads, taking the first response (Q187). This converts the tail into a small amount of extra load and is the most effective single tail mitigation.
- **Request coalescing** so concurrent identical lookups share one call (Q113).

**4. Deliver progressively.** Return the read model's content immediately and stream or lazy-load the live sections. The user-perceived latency is then the read model's latency, and the 200ms budget applies to first meaningful paint rather than to the last byte. This is often the change that makes the whole thing feasible, and it is worth raising even if the stated requirement is a single response.

**5. Cache at the edge** for anything shareable, with a short TTL and jitter (Q76).

**The trade-offs I would state plainly:**

- The read model introduces **eventual consistency**, and the user's *own* recent actions must still appear immediately (Q59) - so a write returns its result and the client renders it optimistically, or the affected section reads live for a short window after a write.
- The read model is **another thing to operate**: consumer lag, projection bugs, rebuild time (Q57). Rebuild time in particular must be measured, not assumed.
- **Nine event streams to consume** is real coupling to nine services' event contracts (Q40).

**What I would monitor**: dashboard p99 end to end and per section, projection lag per source, partial-degradation rate per section (so you know how often users see a degraded page), and read-model rebuild duration.

**What I would reject**: nine synchronous calls with a tighter timeout each (the arithmetic does not work), a gateway doing the aggregation (Q127), and caching the whole dashboard for a long TTL (staleness on the sections that matter most).

---

### S14. Ingesting 500,000 IoT messages per second (Q238)

**Clarify.** Message size (this changes everything - 200 bytes versus 5KB is 100MB/s versus 2.5GB/s)? Is 500k the peak or the average, and what is the peak factor? What is the alerting latency requirement - sub-second, or a minute? What is the historical query pattern: per-device time ranges, or cross-device aggregates? What retention is required at what granularity? Is out-of-order and late-arriving data expected (it always is with field devices on flaky networks)? Can any data be dropped, or is every message required? What is the device authentication model?

**The scale framing.** At 500k messages/second with 500-byte messages, that is 250MB/s ingress, 21TB/day raw. Retention and granularity dominate the cost, so the tiering decision is a bigger design lever than the ingestion pipeline.

**The architecture:**

```
Devices → MQTT / HTTP edge gateway (auth, validate, batch)
              ↓
        Kafka (partitioned by device ID)
              ↓
     ┌────────┴────────┐
     ↓                 ↓
Stream processing   Batch sink
(alerting, windows) (columnar, object storage)
     ↓                 ↓
Alert service      Time-series DB (recent) + Iceberg/Parquet (historical)
```

**The key decisions:**

1. **A protocol suited to devices.** MQTT for constrained devices (small headers, persistent connections, QoS levels, last-will for disconnect detection); HTTP with batching for gateways that aggregate many sensors. **Batching at the edge is essential** - 500k individual TCP requests per second is a connection-handling problem before it is a data problem, and batching 100 readings per message reduces it to 5k messages/second at the ingestion tier.

2. **Kafka as the buffer and the single ingestion point**, partitioned by device ID so per-device ordering holds (Q48) and consumers can scale to the partition count. Partition count sized for the *consumer* parallelism needed, with headroom - repartitioning later breaks ordering (Q49), so over-provision partitions from the start (this is the one place I would deliberately over-provision).

3. **Two independent consumer paths from the same log**, which is precisely why a log-based broker rather than a queue (Q42):
   - **Real-time**: a stream processor (Flink, Kafka Streams) doing windowed aggregation, threshold detection and anomaly detection, emitting alerts. Sub-second from ingestion to alert.
   - **Historical**: a sink writing to columnar files (Parquet, in an Iceberg or Delta table) partitioned by date and device group, plus a time-series database for the recent window where interactive queries live.

4. **Event time, not processing time**, with watermarks. Field devices buffer during connectivity loss and deliver hours late; windowing on arrival time produces wrong aggregates. Define a lateness allowance, and route data beyond it to a late-arrival path that triggers recomputation of the affected windows rather than being dropped silently.

5. **Deduplication** on a device-supplied message ID within a bounded window (Q98). MQTT QoS 1 is at-least-once and device firmware retries, so duplicates are routine. Idempotent writes at the sink (upsert on device ID plus timestamp) are better than a dedup store at this volume.

6. **Tiered retention**, which is where the cost is controlled:
   - Raw, full-resolution: 7-30 days in the time-series store.
   - Downsampled (1-minute, then 1-hour): months to years.
   - Raw archive in object storage: as long as required, queryable but slow.
   This is a data-governance decision with the business, not an engineering default.

7. **Backpressure and load shedding** (Q110, Q196). The ingestion tier must have a defined behaviour when downstream is saturated: for telemetry, **at-most-once with sampling is often acceptable** (Q43), so shedding the least-valuable stream (routine heartbeats) while preserving alerts is the right degradation. Decide this per message type in advance.

8. **Device identity and authentication** - per-device certificates or tokens, with revocation, and per-device rate limiting so a malfunctioning or compromised fleet cannot flood the pipeline. At this scale a firmware bug that increases reporting frequency tenfold is a realistic and serious incident.

**The hard parts to name**: partition count as a long-lived, hard-to-change decision; hot devices or hot device groups creating skewed partitions (Q49); the cost of storage dominating the cost of compute by a wide margin; late data forcing window recomputation and therefore restatement of historical aggregates; and schema evolution across a device fleet you cannot upgrade synchronously (Q54, `FULL_TRANSITIVE` and tolerant readers are mandatory here).

**What I would monitor**: ingestion rate and lag per partition, end-to-end latency from device timestamp to alert, late-arrival rate, per-device message-rate anomalies, dedup rate, and storage cost per device per month.

---

### S15. Partner integration architecture, inbound and outbound (Q239)

**Clarify.** How many partners, and what is the expected growth? Are they large enterprises with their own standards, or small integrators? Is the relationship symmetrical - do they call us and do we call them? What is the commercial model (are they paying us, or are we paying them)? Are there regulatory requirements (open banking, PSD2)? What is the onboarding SLA the business wants - weeks or days? Do partners act on their own behalf, or on behalf of *their* users?

**The framing that shapes everything**: partners are **untrusted, unmanaged, slow-moving and contractually bound**. Every property differs from an internal consumer - you cannot ask them to upgrade, you cannot see their code, their outages are your incidents, and a breaking change is a contractual matter. So the partner boundary needs its own design, not an extension of the internal one.

**Inbound - partners calling us:**

1. **A dedicated partner gateway**, separate from the internal and consumer edges. Different rate limits, different quotas, different auth requirements, its own audit stream, and its own scaling and blast radius. Separating it means a partner traffic spike cannot affect consumer checkout.
2. **A deliberately narrow, stable public API** - a published language (Q3), not an exposure of internal services. Versioned, additive-only, with a formal deprecation policy and sunset headers (Q27). Partner APIs age in years, so the compatibility discipline must be much stricter than internally.
3. **Authentication**: OAuth2 client credentials with **private_key_jwt or mTLS client authentication**, not shared secrets (Q170). Per-partner clients so usage is attributable, revocable and rate-limitable independently.
4. **Authorization by contract**: scopes derived from the commercial agreement, enforced at the gateway and re-checked at the service. Where the partner acts on behalf of an end user, that is a **delegation flow with recorded consent** (Q157), not the same mechanism as machine-to-machine - conflating them is a serious and common error.
5. **Per-partner rate limits and quotas** (Q218), with quota consumption visible to the partner via an API and a portal so they can self-manage.
6. **Idempotency keys mandatory** on every write endpoint (Q94). Partners retry aggressively and unpredictably; without keys you will get duplicates.
7. **Asynchronous by default for anything slow.** A partner submitting work gets a `202` with a resource to poll or a webhook, so their timeout behaviour cannot hold our threads.

**Outbound - us calling partners:**

1. **An anti-corruption layer per partner** (Q3). Their model never enters our domain; an adapter translates. Each partner's quirks are contained in one deletable component.
2. **Per-partner resilience configuration** - circuit breakers, timeouts and bulkheads tuned per partner's measured reliability (Q109). One unreliable partner must not consume shared capacity.
3. **Queue-based, never on the synchronous request path** where avoidable, so a partner outage becomes lag rather than an outage.
4. **Explicit fallback policy per call** (Q114) - what happens when this partner is down, decided with the business in advance.
5. **A partner SLA dashboard** - their availability and latency as measured by us, which is also the artefact that makes commercial conversations possible.

**Webhooks - us notifying partners** (the part most often designed badly):

- **At-least-once with retries and exponential backoff**, a signed payload (HMAC with a per-partner secret, plus a timestamp to prevent replay), and an event ID so the partner can deduplicate.
- **A disable-after-N-failures policy** with notification, so a dead partner endpoint does not consume our capacity forever.
- **A replay API** so a partner who missed events can fetch them, which removes the pressure to retry indefinitely.
- **Ordering is not guaranteed** and the contract must say so, with a sequence number so partners can detect gaps.

**Onboarding as a product**, because this is what determines whether the architecture scales commercially: self-service credential provisioning, a sandbox with realistic data, published OpenAPI specs, generated client SDKs (Q26 - generated, never hand-written with logic), a getting-started guide, and a test suite the partner can run against the sandbox. The measure of success is **time from contract signature to first successful production call**, and it should be days.

**What I would monitor**: per-partner request rate, error rate, latency and quota consumption; webhook delivery success and lag per partner; per-partner API version usage (Q27), which is what makes deprecation possible; and per-partner cost to serve.

---

### S16. Incident response for 40 services across 12 teams (Q240)

**Clarify.** What are the current SLOs and are they agreed with the business? What is the existing on-call arrangement - per team, or a central operations team? What is the current MTTR and incident volume? Is there a service catalogue with ownership? What is the organizational appetite for teams carrying pagers? Are there regulatory notification obligations?

**The founding principle: you build it, you run it.** The team that owns a service is on call for it. Central operations teams for microservices fail predictably - they cannot understand forty services deeply enough to diagnose them, they have no authority to fix the code, and they remove the feedback loop that makes teams build operable software. Every other decision follows from this one, and it is the one that needs executive support.

**Ownership and routing:**

- **A service catalogue** as the single source of truth: for every service, the owning team, the on-call rotation, the SLOs, the runbooks, the dependencies, the dashboards and the escalation path. Every alert routes via the catalogue, so there is never an "who owns this?" moment at 3am.
- **No service without an owner.** A service whose team disbanded gets reassigned or decommissioned, explicitly. Unowned services are where the worst incidents live.
- **Alert routing to the owning team**, with a documented escalation to a secondary and then to an incident commander.

**Alerting discipline** - the most important quality control:

- **Alert on symptoms, not causes**: SLO burn rate (Q150) and business metrics, not CPU. Multi-window multi-burn-rate so severity maps to urgency arithmetically rather than by opinion.
- **Every page must be actionable and urgent.** Anything else is a ticket or a dashboard. I would enforce this with a review of every page-worthy alert and a standing rule that a page nobody acted on gets deleted or downgraded.
- **Measure alert quality**: pages per shift, percentage actioned, percentage false. A rotation receiving more than a couple of pages per shift is being degraded, and fixing that is a leadership responsibility, not the on-call engineer's problem.
- **Business-outcome alerts** as a backstop for the "green dashboards during an outage" case (Q151).

**The incident process:**

- **A declared severity scale** with objective criteria, so declaring is not a judgement call.
- **An incident commander role**, rotating and trained, separate from the person debugging. For a cross-service incident this is essential - someone must coordinate, communicate and decide while others investigate.
- **A single incident channel** per incident, with a scribe, and a communications lead for anything customer-facing.
- **Cross-service incidents** are the hard case: the owning team of the *symptom* declares and holds the incident; the commander pulls in dependency teams. There must be a rehearsed way to reach another team's on-call directly, without a ticket.
- **A shared dependency map and estate-wide dashboard** so the commander can see the whole system, not just one service. This is what a mesh or uniform telemetry buys you (Q136, Q154).

**Learning:**

- **Blameless postmortems**, mandatory above a severity threshold, published estate-wide. The publication matters more than the document - forty services means the same failure mode recurs in other teams, and the only defence is shared learning.
- **Action items with owners and dates**, tracked to completion. Postmortem actions that are never done are the single clearest signal that the process is theatre.
- **A quarterly cross-estate review** of incident themes, feeding the platform roadmap. If five teams hit the same class of failure, that is a platform gap, not five team failures.

**Sustainability**, which is the part that determines whether this survives:

- **Rotation size of at least six** so the burden is tolerable. A team of three cannot sustain a rotation, and that is an argument about team size, not about on-call.
- **Compensation or time off in lieu** for out-of-hours work.
- **Follow-the-sun** if there are teams in multiple time zones, which is far better than night shifts.
- **A standing allocation of capacity to reliability work**, and an error budget policy that redirects capacity automatically when a service is unreliable (Q120). Without that, on-call load only ever increases.

**What I would measure**: MTTD and MTTR, incident count by severity, pages per rotation, percentage of postmortem actions completed on time, and SLO attainment per service. And I would report **pages per rotation** to leadership alongside delivery metrics, because it is the number that predicts attrition.

> *Hook: an on-call model you designed or reformed, and what happened to page volume and attrition.*

---

## Part C - Leadership and platform ownership

### S17. The team wants to split into thirty services

> A team of eight is starting a new product. They have drawn an architecture with thirty microservices and want to begin. They are enthusiastic and technically strong, and they see your hesitation as a lack of ambition.

**Clarify with them, not at them.** What problem does each boundary solve? Which of the thirty have a different scaling profile, a different availability requirement, or a different owner? How long will it take to build the platform - pipelines, observability, on-call - for thirty services? Who is on call for thirty services with eight people? What happens when the domain understanding changes in three months?

**The argument I would make.** Microservices buy independent deployment, independent scaling and team autonomy (Q20). With eight engineers in one team, there is nobody to be autonomous from. They will pay the full distribution cost - network hops, distributed debugging, saga complexity, thirty pipelines, thirty dashboards, thirty on-call surfaces - and receive none of the benefits, and they will do it while the domain is least understood, which is when boundaries are most likely to be wrong. A wrong boundary in a modular monolith is a refactor; a wrong boundary between services is a migration.

**What I would propose instead**, and it must be a real alternative rather than a refusal: a **modular monolith with enforced boundaries** (Q219) - separate modules with build-time dependency rules, separate schemas with no cross-schema joins, in-process domain events shaped exactly as they would be over a broker. They get the modularity they want, they keep the option to extract, and extraction becomes cheap because the data is already separated. Then extract when a specific module develops a specific operational reason.

**How I would run the conversation.** Not as a veto. I would ask them to write down, for each of the thirty, the operational reason it is separate - and let the exercise do the work, because most of the boundaries will have no answer beyond "it is a different noun". I would also be honest that they may be right about two or three of them, and agree to start with those. And I would offer a commitment in return: we revisit in three months with data, and if a module needs extraction we do it.

**What I would not do**: win on authority. A team that complies without agreeing will let the module boundaries erode, and then the modular monolith becomes a big ball of mud that proves them right.

> *Hook: a decomposition you talked a team out of, or into, and how it turned out.*

---

### S18. Two teams have built two event schemas for the same thing

> Team A publishes `OrderPlaced` with one shape. Team B publishes `order.created` with a different shape and different semantics. Six services consume one or the other. Both teams believe theirs is the standard and neither will move.

**What is actually happening.** This is not a schema disagreement, it is an **unowned domain concept**. Two teams both needed to publish order events, neither owned the order lifecycle, so both invented one. The technical symptom is duplicate events; the cause is that nobody was accountable for the order domain (Q7). Solving the schema without solving the ownership guarantees a repeat.

**How I would approach it.**

1. **Establish ownership first, separately from the schema argument.** Who owns the order lifecycle as a business capability? That team owns the event. This is a question for the engineering leadership and the product owners, and framing it as an ownership decision rather than a design decision removes the personal stake both teams have in "their" schema.
2. **Make the cost visible.** Six consumers, two schemas, divergent semantics: how many defects has this caused, how much duplicated consumer code exists, and what happens when the two diverge further? A concrete number changes the conversation from preference to cost.
3. **Design the target schema jointly**, with both teams and the consumers in the room, taking the best of both rather than declaring a winner. This matters politically - "we merged them" is acceptable to both; "yours won" is acceptable to one.
4. **Migrate with dual publication** (Q56): the new owner publishes the agreed event, both legacy events continue during a defined window, consumers migrate one at a time with usage metrics per topic, and the legacy topics are retired with a brownout (Q27). Nobody is asked to break anything.
5. **Close the gap that allowed it**: a **schema and event registry** where every published event is discoverable with its owner (Q38), and a rule that a new event type must be registered before it is published. This is cheap and it prevents the whole class.

**The escalation, if it comes to that.** If both teams still refuse, this is a decision, not a negotiation, and someone with authority must make it. I would make it, document the reasoning, and take the responsibility - because an unresolved ownership dispute costs far more than a decision either team dislikes. But I would spend real effort on 1-3 first, because a decision imposed on two unwilling teams tends to be complied with rather than adopted.

---

### S19. A senior engineer says the resilience standards are over-engineering

> A respected senior engineer is publicly resisting the estate-wide resilience standards - retry budgets, deadline propagation, circuit breakers. Their argument: "our dependencies are reliable, this is complexity for its own sake, and it makes the code harder to read." Other engineers are listening to them.

**Take the argument seriously, because part of it is right.** Resilience configuration does add complexity, plenty of it is cargo-culted, and a circuit breaker with wrong thresholds is worse than none. If I dismiss the objection, I lose the room and I probably deserve to.

**What I would do:**

1. **Understand the specific objection.** "Over-engineering" usually means something concrete: it is hard to test, it is hard to reason about, the defaults are wrong for their workload, or it caused a confusing incident. Each has a different answer, and the last one is a genuine failure of mine to address.
2. **Use evidence, not principle.** Pull the incident history: how many of the last twenty incidents were amplification, cascading timeouts, or a slow dependency exhausting a pool (S1, S5)? If the answer is "several", the evidence makes the argument. If the answer is "none", **they may be right for their context**, and I should say so.
3. **Distinguish the mandatory from the default** (Q234). I would look hard at whether the standard is genuinely all-mandatory, and I suspect it is not. The things that must be universal - deadline propagation, retry budgets - are the ones where one non-participant harms everyone else. Circuit breaker thresholds are a service-level choice. Narrowing the mandate to what genuinely must be uniform is often the resolution, and it concedes something real.
4. **Attack the complexity, not the objection.** If resilience configuration is hard to read, that is a platform failure. Sensible defaults in the platform library, so the common case needs no configuration at all, removes most of the objection legitimately. "You are right that this is too complex; help me make it simpler" is both true and disarming.
5. **Engage them directly and privately first**, and if they have a good case, let them change the standard. A respected sceptic converted into a co-author is worth more than a compliant team.

**The line I would hold**: dependencies being reliable today is not an argument, because resilience controls exist for the day they are not, and that day is not predictable. I would make that point with a specific incident rather than as a maxim.

**What I would not do**: escalate to authority early, or frame it as insubordination. They are doing something valuable - stress-testing a standard - and the standard is better if it survives.

---

### S20. Your platform library caused an estate-wide outage

> A release of the shared platform library introduced a bug in the retry logic. Eleven services adopted it over two days and all eleven degraded. Teams are angry, and two are talking about forking the library or removing it entirely.

**The immediate response** is straightforward and should be visibly fast: identify the bug, publish a fixed version, communicate the exact impact and the fix, and help affected teams upgrade rather than telling them to. Then a public, blameless postmortem written by the platform team about the platform team, published estate-wide.

**The harder part is the trust damage**, and it is the real question. A shared library is a shared risk, and this incident proved the risk is real. Teams considering a fork are responding rationally to evidence.

**What I would say and do:**

1. **Own it completely and specifically.** Not "an issue was identified" - "we shipped a bug in retry backoff, eleven services were affected for up to nine hours, here is exactly what happened and here is what we are changing." Vagueness is what turns an incident into a credibility loss.
2. **Fix the process, visibly**, and name each change:
   - **Dogfood first**: the platform team's own services run every release for a defined soak period before publication.
   - **Canary adoption**: a new library version is adopted by one or two volunteer services first, with a defined bake, before general availability. This bounds the blast radius of the next one to two services rather than eleven.
   - **Better tests** for the specific class of bug, including fault injection (Q208).
   - **Release notes that state the risk** of each change, so teams can decide their own adoption timing.
   - **A documented rollback path** and a commitment to support the previous version.
3. **Address the fork argument honestly.** A fork is a legitimate option and I would not forbid it. But I would put the trade in front of them: forking means owning the retry logic, the tracing propagation, the security updates and the next CVE response for themselves, forever. Most teams do not want that once it is stated plainly. And if one does, and can sustain it, that may be the right answer for them - a platform that cannot be opted out of is a tax, not a product.
4. **Reduce the coupling structurally.** The deeper lesson is that a library that eleven services adopt within two days has *no* rollout control (Q182). The changes above give it some. And it is worth asking whether the riskiest concerns - the ones needing urgent estate-wide change - belong in the mesh rather than a library (Q131), precisely because a proxy can be rolled out gradually and rolled back centrally.
5. **Give teams control of adoption timing**, with a long support window and no forced upgrades except for security. Teams accept shared risk much more readily when they choose when to take it.

**Reflect.** The line I would use in the postmortem: **a shared library concentrates leverage and concentrates risk, and we had built the leverage without building the risk controls.** That is honest, it is the actual finding, and it points at the fix.

---

### S21. Rolling out contract testing across teams you do not own

> You believe consumer-driven contract testing would remove most of the estate's integration failures. You have no authority over the twelve teams, several of whom have their own priorities and some scepticism about "another mandate from architecture".

**The approach: demonstrate value with volunteers, then let demand pull it.** A mandate from someone without authority produces malicious compliance - pacts written to pass rather than to describe real usage, which is worse than nothing because it creates false confidence.

**How I would run it:**

1. **Find the pain and quantify it.** Pull the last six months of incidents and count the ones caused by an integration break - a provider change that broke a consumer. Put a number on the incident hours and the delivery delay. That number is the entire argument, and it is far more persuasive than the practice.
2. **Find two willing teams**, ideally a consumer-provider pair who have recently broken each other. Recent pain is the best recruiting tool. Work *with* them, hands-on - I would write the first pacts myself rather than handing over a document.
3. **Make it work end to end for that pair**, including the part that delivers the value: the broker, the webhook-triggered provider verification, and `can-i-deploy` gating both pipelines (Q204). Contract tests without `can-i-deploy` are documentation; the gate is what removes the coordination.
4. **Measure and publish**: integration defects before and after, and - the metric teams actually care about - **whether they can now deploy without checking with each other**. Deployment independence is the benefit that sells it, not test coverage.
5. **Let the pair tell the story**, in an engineering forum, in their own words. Peer advocacy beats architectural advocacy by a wide margin.
6. **Remove the friction for the next adopters**: put pact publication and verification into the service template and the shared pipeline (Q234), so adopting is adding a few lines rather than a project. Offer to do the first integration for any team that asks.
7. **Track adoption publicly** as information, not as a scoreboard for shaming, and pair it with an offer of help.
8. **Only then, and only with leadership backing, make it a gate for new services** (Q154). Gating new services is politically cheap because nobody is inconvenienced retroactively, and it stops the problem growing while the backlog is worked.

**On the scepticism specifically**: I would name it rather than work around it. "You are right that architecture has pushed things before that did not help. Here is the number, here are two teams who tried it, and here is what it did for them. I am not asking you to adopt it - I am asking you to look at their result." Inviting judgement rather than requesting compliance is what converts sceptics.

> *Hook: a practice you rolled out without authority, the adoption curve, and the team that refused.*

---

### S22. Explaining eventual consistency to an executive

> A director is furious. A customer complained that they updated their address and the confirmation email showed the old one. The director wants to know why "the system does not know its own data" and is questioning the microservices architecture.

**Do not start with CAP.** The director is not asking a technical question; they are asking whether the architecture is fit for purpose and whether they can trust the team. Answering with a theorem confirms their suspicion that engineering is more interested in cleverness than in customers.

**What I would say, roughly in this order:**

1. **Acknowledge the customer's experience as a genuine defect.** "That should not have happened, and we are fixing it." Not "that is expected behaviour" - which is true and is the worst possible opening.
2. **Explain the mechanism in business terms, briefly.** "The address is stored by one part of the system and the email is sent by another. The update reached the second part about two seconds later, and the email went out in that window. It is a timing gap, not lost or wrong data - the address was correct everywhere within a few seconds."
3. **Explain why the design is that way, in terms of a benefit they care about.** "The parts are separate so that a problem with email never stops a customer updating their details, and so the address service stays up when other things fail. The cost of that is a small delay in propagation. It is a deliberate trade and it is usually the right one."
4. **Be specific about the fix**, because that is what they actually want: "Two changes. The email will read the address at the moment it sends rather than from a copy, and confirmation emails for a change will be delayed by a few seconds so the update has propagated. Both this sprint."
5. **Be honest about where the trade is not right.** "There are places where a delay would be unacceptable - anything involving money, or a payment method. Those are designed differently and are immediately consistent. We chose that deliberately for those and not for this. On reflection, an address confirmation is close enough to the line that it should have been in the first group."

**What that last point does** is the important part: it shows the trade-off was made *per case* with judgement, not applied blanket-fashion because it was easier. That is what restores confidence in the team's decision-making, which is what the conversation is really about.

**What I would avoid**: CAP, "eventual consistency", "distributed systems are hard", blaming another team, and any suggestion that the customer's expectation was unreasonable.

**Afterwards**, I would look for the systemic version of the question: where else does a user see their own stale write (Q59)? Read-your-writes for a user's own actions is nearly always required, and eventual consistency between *different* users is nearly always fine. Scoping the fix that way makes it a small piece of work rather than an architectural retreat - and being able to report that back closes the loop with the director on their terms.

> *Hook: a time you explained a technical trade-off to a non-technical executive, and what you changed as a result.*

---

## Practice protocol

**Weeks 1-4.** One Part A scenario per day. Set a timer for five minutes and answer out loud, in CIDER order, before reading anything. Record yourself occasionally - the gap between what you think you said and what you said is where the practice value is.

**Week 5.** Part B, one per day, 25 minutes each with a whiteboard or paper. Start every one by clarifying for at least two minutes; a design answer that begins with a diagram is a weak answer. Force yourself to state at least three trade-offs explicitly and to name one thing you would deliberately not build.

**Week 6.** Part C, plus your own stories. These have no model answer that can be yours - use the responses here as a structure and substitute real detail from Verizon India and Sonata Software. Two to three minutes each, timed, with a quantified result.

**Throughout:**

- If an answer takes more than four minutes, it is too long. Interviewers interrupt good answers; they let bad ones run.
- For every scenario, be able to name **what you would monitor afterwards**. The Reflect step is where principal-level candidates separate themselves, and it is the step people skip when they run out of time.
- Whenever a model answer cites a question number, go and read that answer. The scenarios are deliberately built from the same material, and the cross-references are the revision path.
