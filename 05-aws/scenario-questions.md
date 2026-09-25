# Scenario Questions

Cloud production incidents, architecture design exercises and leadership situations.

Every scenario uses **CIDER**, defined in [../01-java/README.md](../01-java/README.md):

- **Clarify** - what you ask before answering. Never diagnose or design in silence.
- **Isolate** - narrow the failure domain or the core requirement.
- **Decide** - commit to an approach and name the trade-off.
- **Execute** - the concrete steps.
- **Reflect** - what you monitor, prevent, or would do differently.

Read the scenario, answer out loud for five minutes, then compare. The model responses are longer than you should speak - use them as the map, not the script. References like (Q68) point at [answers.md](answers.md).

---

## Part A - Production incidents

### S1. Throttled at 10 percent utilization

> The checkout API starts returning 429s at 11:40. The Lambda concurrency dashboard shows a peak of 140 against an account limit of 1000. Request volume is normal for a Tuesday. The team says "we have loads of headroom, this must be an AWS problem".

**Clarify.** Which component is returning the 429 - API Gateway or Lambda (Q203)? Is `Throttles` non-zero on the function, and on which function? Has anything been deployed, or any configuration changed - including reserved concurrency, an event source mapping, or a Parameter Store value? What is the function's `Duration` p99 right now versus an hour ago? Are other functions in the account affected? What does the account's aggregate `ConcurrentExecutions` look like, not just this function's?

**Isolate.** "Headroom at the account level" and "throttling" are compatible in four distinct ways, and the dashboard cannot distinguish them:

1. **Reserved concurrency on the function.** If someone set it to 150 to protect a database, 140 is not headroom - it is the ceiling (Q69, Q70). The account limit is irrelevant.
2. **Duration has increased.** Concurrency is `rate x duration` (Q67). A downstream that slowed from 200 ms to 2 s multiplies the concurrency requirement tenfold at the same request rate - and if a reserved limit exists, you hit it immediately. The peak of 140 may be the *throttled* level, not the demanded level, which is the crucial misreading.
3. **API Gateway throttling**, not Lambda - a stage, method or usage-plan limit, which rejects before Lambda is ever invoked and therefore shows nothing on the Lambda dashboard (Q56).
4. **Burst rate rather than steady state.** A spike needs concurrency *now*; Lambda scales in increments (Q71), so a short, sharp arrival pattern throttles while the account average looks tiny. A one-minute-average dashboard cannot show a five-second burst.

The first thing I check is the *source* of the 429 and the function's `Throttles` metric alongside `Duration` p99 - because 2 and 3 are the most common and they have opposite fixes.

**Decide.** Restore service by removing the binding constraint, not by raising the account limit - which is almost certainly not the constraint. If it is duration-driven, the real incident is the downstream and Lambda throttling is a symptom; treating the symptom by raising a limit converts a throttle into a database outage (Q200), so I will not do that blindly.

**Execute.**

1. Confirm where the 429 originates: API Gateway `4XXError` with throttling in the access log, versus Lambda `Throttles`.
2. Check the function's reserved concurrency. If it is set and binding, raise it *if* the downstream can take the load - checking the database's connection count and CPU before I do.
3. Check `Duration` p99 and the downstream's latency. If duration has risen, that is the incident: work the downstream (a hot DynamoDB partition, an exhausted connection pool, a slow third party).
4. If it is burst-driven, apply provisioned concurrency or accept the shape and look at whether the path can be buffered.
5. Verify recovery on the customer-facing error rate, not on the concurrency graph.
6. Raise the account limit as a *separate*, non-urgent action if the headroom is genuinely thin.

**Reflect.** Three fixes. **Alarm on `Throttles` at greater than zero** and on concurrency utilization against the *applicable* limit, not the account one (Q183). **Publish the concurrency arithmetic** for each critical function - required concurrency at peak, at p99 duration - so "we have headroom" is a computed number rather than a glance at a graph. And **stop using reserved concurrency as flow control**: protect the downstream with `maximumConcurrency` on the event source mapping or RDS Proxy, so backpressure replaces rejection (Q129, Q162).

> *Hook: a throttling incident whose root cause was duration or a reserved limit rather than request volume.*

---

### S2. One bad record has stalled a shard for six hours

> A Kinesis-driven pipeline that keeps the search index current is six hours behind for a subset of products. `IteratorAge` is climbing on one shard; the other 19 are at zero. There are no Lambda errors on the dashboard because the aggregate error rate is dominated by healthy shards. A merchant is on the phone.

**Clarify.** Which shard, and what is its `IncomingRecords` compared with the others? What does the consumer log for that shard - repeated identical errors, or nothing? What are the event source mapping's `MaximumRetryAttempts`, `MaximumRecordAgeInSeconds`, `BisectBatchOnFunctionError` and `DestinationConfig` settings? What is the stream's retention period - is any data already unrecoverable? Is the index stale, or wrong?

**Isolate.** A single lagging shard with healthy siblings is one of four things (Q112), and the log tells you which within a minute:

1. **A poison record.** Kinesis is ordered and the poller does not advance past a failing batch, so with the default `MaximumRetryAttempts: -1` one record blocks the shard forever (Q121). Repeated identical errors in the log.
2. **A hot partition key** - the shard is throughput-bound while others idle. Distinguished by `IncomingRecords` being much higher on that shard.
3. **A slow record class** - no errors, just per-record processing time above the arrival rate.
4. **Consumer-side capacity** for that shard specifically.

Given "no errors on the dashboard", I would look hard at whether the errors exist but are being averaged away - which is a monitoring failure layered on top of the incident, and worth naming separately.

**Decide.** Unblock the shard first and accept a bounded, recorded data loss rather than continuing to wait, because the business cost of six more hours of staleness exceeds the cost of replaying a handful of records afterwards. I will capture the blocking record before discarding it, so the loss is repairable.

**Execute.**

1. Read the consumer's logs for that shard, identify the failing record and its sequence number. **Capture the record** (from the log, or by reading the stream at that sequence number) before doing anything destructive.
2. Set `MaximumRetryAttempts` to a small number and configure an `OnFailure` destination if one is missing, so the discard is recorded rather than silent (Q120).
3. Enable `BisectBatchOnFunctionError` so only the bad record is sacrificed, not its whole batch.
4. Watch `IteratorAge` fall as the shard drains. Confirm the six-hour backlog is being consumed and estimate the catch-up time from the drain rate.
5. Fix the record's root cause in the handler - almost always a schema or encoding assumption - and classify it as unrecoverable so the handler routes it to a DLQ itself and returns success (which is the correct long-term behaviour).
6. Re-process the captured record once the handler is fixed, and verify the affected products in the index.

**Reflect.** **`IteratorAge` per shard is the single most important alarm on any stream consumer**, and the absence of it is why this was six hours rather than six minutes (Q121). The mapping's four error-handling settings should be defaults in the shared construct, not per-team decisions (Q245). The handler must **distinguish retryable from unrecoverable errors** - a malformed record should never be retried, ever. And the aggregate error-rate dashboard hid a total failure for a subset of data, which is an argument for **per-shard and per-tenant visibility** on anything partitioned.

> *Hook: a stream or partition-level stall you diagnosed, and the alarm you added.*

---

### S3. Every message in the DLQ, and none of them are bad

> An SQS-driven settlement worker has 40,000 messages in its dead letter queue. Sampling them shows valid payloads. `ApproximateReceiveCount` on every one is exactly 5, which is the queue's `maxReceiveCount`. The consumer's error rate is near zero. Somebody changed something yesterday.

**Clarify.** What changed yesterday - specifically, was `maximumConcurrency` set on the event source mapping, or reserved concurrency on the function, or a visibility timeout, or the function's timeout? What is the queue's `ApproximateAgeOfOldestMessage` and its arrival rate? What is the function's `Duration` p99 and `Throttles`? Is the settlement work idempotent - can these 40,000 be safely reprocessed? What is the business deadline for settlement?

**Isolate.** Valid payloads, no consumer errors, and a receive count pinned at exactly `maxReceiveCount` means the messages were **received and never successfully processed, without failing** - which is a throughput and lifecycle problem, not a data problem (Q130).

Two candidate mechanisms, and they often combine:

1. **A protective concurrency limit set below the arrival rate.** If `maximumConcurrency` (or reserved concurrency) was set to a number where `limit / duration < arrival_rate`, the queue becomes a leak: the backlog grows, messages sit, and every redelivery increments the receive count until they exhaust it (Q129, Q130).
2. **Visibility timeout shorter than processing time under contention.** Messages are picked up, the handler is still working when the lease expires, the message is redelivered - repeatedly, with no error logged, until the count runs out (Q100, Q101). Also produces *concurrent duplicate processing*, which for settlement is the more alarming implication.

If reserved concurrency was the change, throttles would be non-zero - so the throttle metric distinguishes the two.

**Decide.** Two problems to solve in order: **stop the queue leaking** (raise the limit or the timeout so the drain rate exceeds arrival), then **redrive the DLQ safely** at a controlled rate. And before I redrive anything, I need to know whether any of those 40,000 were *partially* processed, because settlement double-application is worse than settlement delay.

**Execute.**

1. Fix the flow: set `maximumConcurrency` above `arrival_rate x duration` with margin, and set the visibility timeout to at least six times the function timeout (Q100). Verify the live queue's age starts falling.
2. Raise `maxReceiveCount` and the message retention period so genuine transient contention no longer dead-letters valid work.
3. **Determine idempotency** before redriving. If the handler has an idempotency table keyed on a settlement ID, a redrive is safe and duplicates are no-ops. If it does not, I do not redrive - I first add one, or I reconcile against the downstream ledger to establish which of the 40,000 already applied.
4. Redrive **rate-limited**, into the live queue or a separate replay queue, watching the downstream's saturation rather than the queue depth (Q125). Never at full speed.
5. Reconcile: count in, count applied, count still outstanding, and confirm against the settlement system.

**Reflect.** The systemic fixes: **alarm on `ApproximateAgeOfOldestMessage`, not depth** - age is what tells you the drain rate is insufficient, and it would have fired yesterday (Q193). **Alarm on DLQ arrivals at greater than zero** (Q124) - 40,000 messages accumulated silently. **`maximumConcurrency` must be sized from the arrival rate**, and a change to it should require the same review as a code change, because it is a capacity decision disguised as a configuration value. And **idempotency is a precondition for having a DLQ at all**: a dead letter queue you cannot safely redrive is just a record of lost work.

> *Hook: a DLQ that filled with valid messages, and the limit or timeout that caused it.*

---

### S4. Every function in the account is failing at once

> At 09:15, functions across three unrelated services start throttling. A data team ran a backfill at 09:12. Your customer-facing API is returning 429s, the order pipeline is falling behind, and the backfill team says their job "is just reading from S3, it can't be us".

**Clarify.** What is the account's aggregate `ConcurrentExecutions` against the limit? Which functions are consuming it - is there a single dominant consumer? Does the backfill function have reserved concurrency? What invocation model is the backfill using - a distributed map, an S3-triggered fan-out, or a loop? Which of the affected paths are synchronous (losing requests now) versus asynchronous (accumulating)?

**Isolate.** **Lambda concurrency is an account-per-region resource shared by every function** (Q67, Q68). A backfill that fans out over an S3 prefix or a distributed map with an uncapped `MaxConcurrency` will consume everything available within seconds, and every other function in the account is then throttled - including the customer-facing API, which has no protection because nobody reserved capacity for it.

The backfill team is technically right and architecturally wrong: reading from S3 is harmless; invoking ten thousand concurrent functions to do it is not. This is a **noisy-neighbour failure inside a single account**, and it is the concrete argument for account boundaries as quota boundaries (Q2, Q4).

Consequences differ by path (Q72): synchronous callers are getting 429s and losing requests *now*; asynchronous paths are being retried by the platform and will mostly recover, though sustained throttling will start filling DLQs (Q130).

**Decide.** Stop the backfill immediately. It is a batch job with no deadline measured in minutes; the API is customer-facing. That is not a close call, and I would make it without negotiation - then protect the critical path structurally so the next backfill cannot do this.

**Execute.**

1. **Set reserved concurrency to a small number on the backfill function** (or disable its event source mapping / stop the Step Functions execution). Reserved concurrency is the fastest lever because it takes effect immediately and needs no cooperation from the backfill's code.
2. Confirm aggregate concurrency drops and the API's 429s stop. Verify on the customer-facing error rate.
3. **Reserve concurrency for the critical functions** - a floor for the API, so it can never be starved again (Q69). This is the fix that should already have existed.
4. Assess the asynchronous damage: check DLQ depths, message ages and `IteratorAge` across the affected pipelines, and confirm they are draining.
5. Request an account concurrency limit increase - as a follow-up, not as the fix.
6. Restart the backfill with a bounded `MaxConcurrency` (distributed map) or a reserved concurrency ceiling, and a rate that leaves headroom.

**Reflect.** Three structural changes. **Reserved concurrency as a standing policy**: a floor for tier-1 functions and a ceiling for batch functions, applied by the shared construct rather than remembered per team (Q69, Q245). **Batch and interactive workloads belong in separate accounts** where the quota is genuinely isolated - this incident is the business case (Q3). And **alarm on account-level concurrency utilization**, which is a signal nobody owns because it belongs to no single service; it should page the platform team.

> *Hook: a noisy-neighbour incident inside one account, and the isolation you introduced afterwards.*

---

### S5. The Lambda started producing duplicate identifiers

> Two weeks after enabling SnapStart on a Java function to fix cold starts, support reports duplicate order references. They are not frequent - a handful a day - and they are not reproducible in staging. The team's first theory is a race condition in the database.

**Clarify.** How is the order reference generated - a UUID, a random string, a sequence, a timestamp-plus-random? Are the duplicates *identical* or merely colliding on a prefix? Do the duplicated requests share anything - a time window, an availability zone, a version? What is the function's version and alias configuration, and when exactly did SnapStart go live relative to the first duplicate? Are there other symptoms - authentication failures, expired token errors?

**Isolate.** SnapStart snapshots the execution environment **after `INIT` and restores that same image many times** (Q73). Anything initialized once and assumed unique per environment is now identical across every restored environment. The classic consequence is a `Random` or `SecureRandom` instance created during initialization: every restored environment starts from the same seed and produces the **same sequence of values** (Q74). Duplicates therefore appear only between *concurrent, freshly restored* environments - which explains "a handful a day", "not reproducible in staging" (low concurrency, few restores), and why it began exactly when SnapStart did.

The database race theory is wrong and worth correcting carefully: the database is faithfully storing two genuinely identical references generated by two different environments.

I would also immediately check for the **sibling bug**: credentials, tokens or secrets captured in the snapshot and now stale on restore (Q74). They have the same cause and one is usually present when the other is.

**Decide.** Fix the identifier generation properly rather than disabling SnapStart, because SnapStart is solving a real problem and the bug is in our code's assumption, not in the feature. But I would disable it *temporarily* if the duplicate rate were causing material harm - a bounded, reversible mitigation while the fix ships.

**Execute.**

1. Confirm the mechanism: log the generated reference plus the environment's identity and the restore marker, and check whether duplicates correlate with concurrent cold restores.
2. **Immediate mitigation**: add a uniqueness constraint at the data layer - a conditional write on the reference (`attribute_not_exists`) so a collision fails loudly and is retried, rather than being stored (Q156). This stops customer impact within one deploy and is worth doing regardless of the root cause.
3. **The fix**: register a CRaC resource whose `afterRestore` re-seeds the RNG from fresh entropy; better still, generate the identifier **inside the handler** with a freshly seeded generator, or derive it from the Lambda request ID plus a ULID (Q225).
4. Audit `INIT` for every other captured assumption: cached secrets, assumed-role sessions, open connections, cached "instance IDs", anything time-bound.
5. Backfill: identify the affected orders and remediate with the business - this is a data-correction exercise, not just a code fix.

**Reflect.** The generalizable rule to state: **SnapStart changes `INIT` from "once per environment" to "once per snapshot", so every freshness and uniqueness assumption in initialization becomes a correctness bug.** That belongs in the review checklist for any function enabling it. Two supporting practices: **uniqueness enforced at the data layer** rather than trusted from the generator, so this class of bug fails loudly; and **a load test at realistic concurrency with cold restores** as part of enabling SnapStart, since staging's low concurrency structurally cannot reproduce it.

> *Hook: a SnapStart, native-image or environment-reuse bug you found, and how it surfaced.*

---

### S6. `too many connections` on Aurora at peak

> The order service moved from ECS to Lambda six weeks ago. It has been fine. Today, at the Monday morning peak, Aurora starts refusing connections. Lambda concurrency is at 600. The database's CPU is at 30 percent. Someone suggests scaling up the database.

**Clarify.** What is the connection pool size configured in the function? What instance class is Aurora, and what is its `max_connections`? Is there an RDS Proxy in the path? What is `DatabaseConnections` over the last hour, and does it track concurrency? Is the function in a VPC, and how many subnets? What else connects to this database - the old ECS service, batch jobs, analytics, a BI tool?

**Isolate.** Each Lambda execution environment is a separate process with its own pool, and nothing is shared (Q161). With a framework-default pool of 10 and 600 concurrent executions, the demand is up to **6,000 connections**. Aurora's `max_connections` scales with instance memory and is in the hundreds for small and mid classes, and each PostgreSQL connection costs several megabytes plus a backend process - so you exhaust connections long before CPU, which is exactly the observed shape.

"It has been fine for six weeks" is explained by concurrency: at 60 concurrent executions the pool math was survivable; at 600 it is not. This is a **latent capacity mismatch that traffic revealed**, not a new fault.

Scaling up the database would raise `max_connections` and would work temporarily - which is why it is tempting - but it treats a design mismatch with money, and the next traffic step repeats it.

**Decide.** Two immediate actions and one correct fix. Immediately: reduce the per-environment pool size (a configuration change with a deploy) and cap concurrency reaching the database. Correctly: put **RDS Proxy** in front so connection count decouples from Lambda concurrency, which is the design this architecture required from the day it moved to Lambda.

**Execute.**

1. **Cap the blast radius now**: set reserved concurrency on the function to a level the database can support (`max_connections / pool_size`, with margin for other clients), accepting throttling as the lesser harm - and alarm on it so the throttling is visible rather than silent (Q70's caveat applies, and I would say so).
2. **Reduce the pool to 1-2 per environment** and redeploy. A Lambda environment serves one invocation at a time, so a pool of 10 is nine idle connections per environment (Q79). This alone is often a 5-10x reduction.
3. Verify `DatabaseConnections` falls and errors stop.
4. **Deploy RDS Proxy**, with the function connecting to the proxy endpoint and IAM authentication (Q162). Then check `DatabaseConnectionsCurrentlySessionPinned` - if the ORM issues session-level `SET` statements the multiplexing will not happen, and that must be fixed for the proxy to be worth anything.
5. Move the async paths behind SQS with `maximumConcurrency` so the drain rate is bounded by backpressure rather than by rejection (Q129).
6. Then remove the emergency reserved-concurrency cap.

**Reflect.** The design lesson: **serverless compute and connection-pooled relational databases are architecturally mismatched, and RDS Proxy or the Data API is a required component, not an optimization** (Q161). Beyond that: the migration from ECS to Lambda should have included a connection-model review - the same code, the same pool setting, a completely different concurrency model. And the honest question for the postmortem is whether this workload's access pattern is relational at all; if it is key-value, DynamoDB has no connection model and the failure mode does not exist.

> *Hook: a connection-exhaustion incident after a serverless migration, and the fix you shipped first.*

---

### S7. The bill doubled overnight and nobody deployed

> Finance flags that yesterday's spend was double the daily average. Cost Explorer shows the increase is almost entirely Lambda invocations and CloudWatch Logs. There were no deployments. The engineering team's first response is that the numbers must be wrong.

**Clarify.** Which functions, specifically - is the invocation increase concentrated or spread? What is the invocation count versus the previous day, and does it correlate with any customer traffic increase? Was anything changed that is not a deployment - a feature flag, a Parameter Store value, an event source mapping, an S3 notification, a schedule? Are there any errors correlating with the increase? Is `RecursiveInvocationsDropped` non-zero?

**Isolate.** A large invocation increase with no traffic increase and no deploy has a small number of causes, and they are distinguishable within minutes:

1. **A recursive invocation loop.** A function triggered by S3 events writing back into the same bucket, or an EventBridge rule whose target emits an event that matches the rule (Q175). Invocation count explodes, log volume explodes with it, and the cost graph shows exactly this shape. **This is my first hypothesis** given both Lambda and Logs rose together.
2. **Retry amplification.** A downstream degraded, and retries at three layers multiplied invocations by an order of magnitude (Q200) - and every retry logs. The tell is a non-zero error rate.
3. **A configuration change that is not a deploy**: a feature flag enabling an expensive path, a batching window removed, an event source mapping's batch size set to 1 (ten times the invocations for the same messages), a new S3 notification, or verbose logging enabled during an investigation and left on (Q254).
4. **A new or replayed event source** - a DLQ redrive, an EventBridge replay, a backfill, or a third-party integration's changed sync schedule.

"The numbers must be wrong" is almost never true, and I would move past it quickly by finding the *hour* the step change occurred, then the function, then CloudTrail for what changed in that hour.

**Decide.** Stop the spend first if it is still ongoing - a loop or an amplification is actively costing money and consuming concurrency that other workloads need. Then find the cause. I would not wait for consensus on the cause before capping the cost.

**Execute.**

1. Cost Explorer at **hourly/daily granularity** by usage type to find the exact time of the step; then CloudWatch invocation counts per function for the same window.
2. If it is ongoing and unexplained: **set reserved concurrency low on the suspect function** to cap the rate, or disable its trigger. This bounds the bill immediately and is reversible.
3. CloudTrail for the window: what was created, updated or enabled, and by whom.
4. Confirm the mechanism (loop, retry, config) and fix it - break the loop by separating buckets or scoping the notification (Q175), fix the downstream, revert the configuration.
5. Quantify the total cost of the event and report it, including the log-ingestion component, which is usually the surprise.
6. Check for collateral damage: did the concurrency consumption throttle anything else (S4)?

**Reflect.** The controls that would have caught it: a **billing alarm and Cost Anomaly Detection** routed to the engineering team rather than to finance (Q256) - detection should be hours, not a day; **reserved concurrency as a standing ceiling** on non-critical functions so any loop has a bounded cost; **the structural fix for recursion** (never write into a bucket that triggers you, Q175) as a construct-level default; and **treating configuration as a deploy** - flags, mappings and parameters need change records, because "nobody deployed" was true and irrelevant.

> *Hook: a cost spike you traced, the mechanism, and the guardrail you added.*

---

### S8. The failover ran and the standby could not take the load

> A regional degradation triggers your documented failover. The runbook executes cleanly - Route 53 shifts, the standby's health checks pass. Ten minutes later the standby is throttling, the queue is backing up, and the incident is now worse than the original degradation.

**Clarify.** What exactly is throttling - Lambda concurrency, API Gateway, DynamoDB, SES, KMS, a third party? What is the standby's Lambda concurrency limit and its DynamoDB capacity mode? When was the last full-traffic failover drill, and at what percentage of traffic? Is the data replicated and current, or is this purely capacity? Can we fail back, and is the original region actually unable to serve?

**Isolate.** This is the quota asymmetry of Q223. The primary region's limits were raised incrementally over years - Lambda concurrency, API Gateway throttles, DynamoDB table limits, SES sending quotas, KMS request rates - each by a support ticket nobody recorded as configuration. **The standby is at defaults**, because service quotas are per-account-per-region and none of that was replicated. Drills at 5-10 percent of traffic never approached the ceilings, so the runbook was validated against a load that could not reveal the problem.

The related possibilities to check in the same breath: **cold everything** - no provisioned concurrency, cold caches, an empty DAX cluster, a DynamoDB table in provisioned mode whose auto-scaling has never seen this load (and reacts in minutes, Q152); and **on-demand's "twice the previous peak"** ceiling, which for a table that has never taken production traffic is a very low bar.

**Decide.** I have two bad options and must choose explicitly: **fail back to a degraded primary**, or **shed load in the standby** so it serves a subset correctly while quotas are raised. If the primary is degraded rather than down, failing back is usually right - a partially degraded region serving most traffic beats a healthy region serving none. If the primary is genuinely gone, I shed load deliberately and prioritize.

**Execute.**

1. Identify the binding limit precisely - the throttle metrics name it. Do not guess.
2. **Open an urgent quota increase** with AWS support in parallel with everything else; some limits are raised in minutes and it costs nothing to ask early.
3. Decide fail-back versus load-shed, say the decision out loud in the incident channel with the reasoning, and take it.
4. If shedding: apply API Gateway throttles that **prioritize** - protect checkout, throttle browse; disable non-essential asynchronous consumers to free concurrency; turn off batch and analytics paths.
5. Switch DynamoDB to on-demand if it is provisioned and lagging (a one-way change for 24 hours, so state the trade-off).
6. Verify against the customer-facing signal, and communicate a degraded-service status honestly.

**Reflect.** The fixes, in order of value. **Automated quota parity checking** between regions - ARC readiness checks, or a scheduled job comparing Service Quotas and alarming on divergence (Q220). This is the single control that would have prevented it. **Full-traffic failover drills**, running in the standby for days rather than minutes, alternating the primary region if possible (Q211). **Quotas as code**: every limit increase recorded in the IaC repository with the region as a parameter, so raising it in one region prompts the other. And a postmortem finding worth stating plainly: **a runbook that has only been tested at low volume has not been tested** - the drill's success was misleading information, which is worse than no information.

> *Hook: a failover or drill that revealed a quota or configuration asymmetry, and how you closed it.*

---

### S9. The API is fine and the users are not

> Customers report the app is slow. API Gateway `Latency` p50 is 90 ms, `5XXError` is zero, Lambda `Duration` average is 120 ms, and every dashboard is green. The mobile team insists something is wrong. Two hours have been spent arguing.

**Clarify.** Which users, which geography, which app version, and which screens? Is it slow or is it intermittently failing? What does the mobile team's own telemetry say - time to first byte, total request time, error retries? What is API Gateway's `Latency` at **p99**, not p50 or average? What is the cold-start rate on the functions in that path? Is there an authorizer in the path?

**Isolate.** Green dashboards and unhappy users almost always means **the dashboard is measuring a different quantity from the user's experience** (Q184). The specific gaps in this stack:

1. **Averages hide bimodal distributions.** A 120 ms average `Duration` with a 5 percent cold-start rate at 3 seconds is a p95 nobody is looking at - and `Duration` **excludes `InitDuration` entirely**, so cold starts are invisible on the default dashboard by construction.
2. **The authorizer.** A Lambda authorizer adds a full invocation, including its own cold starts, and its cache key may be defeating the cache (Q55). Its latency appears in API Gateway's `Latency` but not in the backend function's `Duration`.
3. **Everything before API Gateway.** DNS, TLS, CloudFront, the mobile network, and the client's own retry behaviour. If the client retries a slow request, the *successful* attempt looks fine in our metrics and the user waited three times as long.
4. **Per-tenant or per-geography concentration.** A hot DynamoDB partition or a regional edge issue affects a subset; aggregate percentiles average it away.
5. **Chattiness**: if a screen makes eight calls, an 90 ms p50 is a 720 ms screen, and the fix is the API design, not the latency.

**Decide.** Stop arguing about whose dashboard is right and get a measurement neither side owns: **client-side latency**. Then decompose the server-side number into its actual components rather than the one metric that happens to be graphed.

**Execute.**

1. Ask the mobile team for their p50/p95/p99 by screen and by region, with retry counts. If they do not have it, that is the first fix.
2. Look at API Gateway `Latency` **p99** versus `IntegrationLatency` p99 - the gap is the gateway plus the authorizer, and it isolates the layer immediately.
3. Count cold starts: `InitDuration` occurrences over invocations, and the p99 of `Duration + InitDuration`.
4. Check the authorizer's invocation count relative to request count - if it is close to 1:1, the cache is not working.
5. Add a **canary** from a representative region measuring the full journey (Q195), so there is an authoritative number that is neither team's.
6. Fix what the decomposition names: provisioned concurrency or SnapStart for cold starts, authorizer caching, a composite endpoint for chattiness, or CloudFront for TLS and backbone if the geography points there (Q62).

**Reflect.** The systemic issues. **Percentiles, not averages**, on every latency dashboard - and `Duration + InitDuration` as the graphed quantity for any function on a user path. **An SLI measured at the edge with client-side RUM as a second signal** (Q194), so "is it slow" is answerable from data rather than by escalation. And an organizational point worth making: two hours of argument happened because there was **no shared, trusted measurement** - the highest-value output of this incident is that number existing, not the specific fix.

> *Hook: a latency dispute you resolved by introducing a measurement both sides trusted.*

---

### S10. The replay fixed the data and broke the business

> A bug meant three days of `OrderShipped` events were not consumed by the notifications service. The team replays them from the EventBridge archive. Within minutes, customers are receiving hundreds of duplicate emails and SMS messages, some for orders that were subsequently cancelled. The replay is still running.

**Clarify.** Is the replay still in progress and can it be stopped? What was the replay's scope - the whole bus, or a specific rule? Which consumers were subscribed to the replayed rules? Is the notifications service idempotent, and on what key? What has already been sent, and can we tell? Is there a suppression mechanism for outbound messages?

**Isolate.** Three failures compounded, and separating them matters for the fix:

1. **The replay targeted more than the broken consumer.** An EventBridge replay to the *bus* delivers to every matching rule, so consumers that had already processed those events three days ago processed them again (Q110). Only the notifications service needed them.
2. **The consumers are not idempotent.** A replay is by definition reprocessing; without an idempotency key on the event ID, every replayed event is a new action (Q126).
3. **Time-dependent and stale state.** Replayed events carry their original `time` but the world has moved on: orders were cancelled, addresses changed, promotions expired. Sending a shipping notification for a cancelled order is not a duplicate - it is *wrong*, and it is the more serious of the two harms.

Plus the fanout multiplier: replayed events may have caused consumers to emit their own events, so the blast radius exceeds the replay's nominal scope.

**Decide.** Stop the replay immediately - the cost of stopping is a partially repaired dataset, the cost of continuing is more customer harm, and that is not close. Then suppress outbound messaging at the boundary rather than trying to fix consumers under pressure.

**Execute.**

1. **Cancel the replay.** If it cannot be cancelled, disable the rules it is delivering to, which stops delivery at the bus.
2. **Kill the outbound channel**: disable the notifications service's sending path (a feature flag, or reserved concurrency of zero, or revoke the SES/SNS permission). Stopping the send is more reliable than stopping the input.
3. Quantify: how many messages went out, to how many customers, and how many were for cancelled or changed orders. Get this number early because it drives the customer-communication decision.
4. Engage support and comms - this is now a customer-trust incident, not only a technical one, and an apology plus a clear explanation is part of the remediation.
5. Reconcile the actual data gap: which `OrderShipped` events genuinely still need processing, filtered against current order state.
6. Process the true remainder **through a dedicated path** - a one-off consumer reading a curated list, with current-state validation and a suppression window for anything cancelled - not through a bus replay.

**Reflect.** The rules I would write down afterwards. **A replay is a production write operation**: announced, scoped to a single rule, rate-limited, rehearsed in non-production, and approved like a deploy (Q110). **Consumers must be idempotent on the event ID before replay is available as a recovery tool** - otherwise the tool is a hazard, and I would gate access to the archive on that. **Outbound side effects need a current-state check**, not just an event: a notification handler should verify the order is still shippable before sending, which makes stale events harmless. And **every consumer should honour the `replay-name` field**, so a replayed event can be treated differently - reprocessed for data repair, suppressed for notifications. That single convention would have prevented this entirely.

> *Hook: a replay or redrive that caused a second incident, and the control you introduced.*

---

## Part B - Design exercises

These are the category 17 questions worked in full. Give yourself twenty minutes each, out loud, before reading.

### S11. Design a serverless order-processing platform for a retailer (Q261)

> 3,000 orders per minute at peak, a 20x Black Friday spike, integration with a third-party payment provider, and a 99.95 percent availability target. Design it, justify every service, and state the cost.

**Clarify.** Is payment authorization synchronous to the customer, or can we accept the order and authorize asynchronously? What is the acceptable time from order placed to confirmation? What is the average order payload size and the number of line items? Who else consumes order events - analytics, partners, warehouse? What is the provider's rate limit and does it support idempotency keys and status queries? Is the 99.95 target on order *acceptance* or on the whole fulfilment chain? What is the peak duration - a few hours or a whole weekend?

**Isolate the numbers first.** 3,000 orders/minute is **50 orders/second**; a 20x spike is **1,000 orders/second**. At a 200 ms accept handler that is `1000 x 0.2 =` **200 concurrent executions** at peak (Q67) - comfortable, and the burst rate is the thing to check, not the ceiling (Q71). The 99.95 target is 21.9 minutes per month, and the composed SLA of a synchronous chain through the payment provider cannot deliver it (Q214) - which forces the central design decision.

**Decide - the architecture.**

```
CloudFront (WAF, TLS at edge, static assets)
  -> HTTP API (JWT authorizer)
     -> AcceptOrder Lambda  [provisioned concurrency at the p90 band]
          TransactWriteItems: order item + idempotency record   (DynamoDB, on-demand)
          return 202 + orderId
  DynamoDB Streams -> EventBridge Pipes -> orders-bus  [the outbox, Q128]
     rule -> Step Functions Standard, execution name = order-{orderId}
                AuthorizePayment  (idempotency key = orderId; unknown -> VerifyPaymentStatus)
                ReserveInventory  (SDK integration, conditional write)
                CreateShipment    (carrier API, jittered retries)
                EmitOrderCompleted (SDK integration -> EventBridge)
                Catch -> ReleaseInventory -> RefundPayment -> ManualQueue (alarmed)
     rule -> SQS -> notifications consumer
     rule -> Kinesis -> Firehose -> S3 (Parquet) -> Athena   [analytics]
     rule -> SQS -> warehouse integration
```

**Justification, service by service:**

- **Accept-and-persist, authorize asynchronously.** This is the decision that makes 99.95 achievable: the customer-facing path depends only on API Gateway, Lambda and DynamoDB, and the unreliable third party is off the critical path (Q214). Provider downtime becomes a latency event, not an availability event.
- **HTTP API, not REST.** Roughly a third of the cost, lower latency, and we need none of REST's exclusive features - WAF sits on CloudFront (Q50, Q51).
- **DynamoDB on-demand.** A 20x spike is exactly the traffic shape on-demand exists for; provisioned auto-scaling reacts in minutes and would throttle (Q154). Single table, `PK = ORDER#<id>` with line items in the same item collection so the order and its items are one read (Q149). Pre-warm before Black Friday by ramping, because on-demand scales to twice the previous peak (Q154).
- **`TransactWriteItems` for order plus idempotency record**, so acceptance is atomic and a client retry is a no-op (Q126, Q155). The 2x capacity cost is worth it here and nowhere else.
- **DynamoDB Streams as the outbox.** The event is a consequence of the commit, so an order can never be accepted without its event being published (Q128).
- **EventBridge as the domain bus**, one rule per consumer, each with its own queue and DLQ - so adding the partner integration later touches no producer (Q107, Q105).
- **Step Functions Standard** for the fulfilment process: it has compensation, retries, an SLA and a manual path, and "where is order 123" must be answerable (Q132, Q140). Deterministic execution names make duplicate starts impossible.
- **Provisioned concurrency on the accept function**, scheduled up before the peak: at a 99.95 target with a latency expectation, a multi-second cold start on the checkout path is not acceptable (Q69, Q96).
- **Kinesis plus Firehose for analytics**, so analytical consumers never touch the transactional path.

**Execute - the Black Friday preparation**, because a 20x spike is the interesting part:

1. **Raise quotas weeks ahead**: Lambda account concurrency, API Gateway account throttle, SES if notifications go by email (Q198). This is a support ticket with lead time.
2. **Load test at 20x**, not at 2x - and specifically test the *arrival shape*, because the burst rate is a distinct limit (Q71).
3. **Reserved concurrency floors** on the accept and payment functions, ceilings on batch and analytics functions, so nothing can starve checkout (S4).
4. **Pre-scale**: provisioned concurrency scheduled, DynamoDB pre-warmed, provider rate limits confirmed and raised.
5. **Load shedding plan**: API Gateway throttles that protect checkout and shed browse; a documented decision about which consumers to disable.
6. **A game day** injecting provider failure and a concurrency squeeze (Q212).

**The cost, at steady state** (order acceptance path, ~130 million orders/year is not this business - use 3,000/min x 8 peak hours plus a diurnal curve, call it **50 million orders/month** for arithmetic):

| Line | Calculation | Monthly |
| --- | --- | --- |
| HTTP API | 50M requests x $1.00/M | $50 |
| Lambda accept | 50M x 200 ms x 512 MB = 5M GB-s | $83 + $10 requests |
| Provisioned concurrency | ~200 units x 730 h (scheduled, so less) | ~$300-600 |
| DynamoDB on-demand | 50M transactional writes (2 WRU each) + reads | ~$150-250 |
| Step Functions Standard | 50M x ~8 transitions = 400M | **~$10,000** |
| EventBridge | 50M custom events x $1/M | $50 |
| CloudWatch Logs | ~50 GB | $25 |
| Kinesis + Firehose + S3 | modest | ~$200 |
| **Total** | | **≈ $11,000-12,000/month** |

**And immediately the observation that matters**: Step Functions Standard dominates at over 80 percent of the cost (Q143). So the design decision to revisit is the state machine - either reduce the transition count (combine steps, use direct SDK integrations rather than Lambda-per-step which does not reduce transitions, or move the high-volume happy path to an **Express child workflow** invoked from a Standard parent), or accept the cost as the price of the auditable, queryable process. For a retailer where "where is my order" is a support cost, I would argue the $10,000 buys more than it costs - but I would state the number, present the Express alternative, and let the business choose. **Naming the dominant cost line and offering the alternative is the answer**, not producing a small number.

**Reflect.** What I would monitor: order acceptance SLI at the edge, time-to-authorization p99, the manual-intervention queue depth, provider error rate, and cost per order (Q257). What I would rehearse: provider outage, concurrency squeeze, and a Step Functions version deploy with executions in flight (Q146). The biggest risk in the design is the **payment provider's unknown-outcome case**, and the reconciliation job against their settlement file is what makes it survivable (Q131).

---

### S12. Design a multi-tenant SaaS for 500 tenants (Q262)

> 500 tenants ranging from 10 to 100,000 users each, per-tenant isolation, noisy-neighbour control and per-tenant cost reporting. Design it.

**Clarify.** What does "isolation" mean contractually - correct authorization, separate encryption keys, separate storage, or separate accounts? Is there a residency requirement per tenant? What is the largest tenant as a percentage of total load (the noisy-neighbour risk)? Is per-tenant cost reporting for internal margin analysis or for customer-facing billing? What are the tenants' latency expectations, and do they differ by tier? Can we offer tiers with different isolation and price?

**Isolate the core tension.** 10 to 100,000 users is a **10,000x range**. A single architecture cannot be economical for the small tenants and safe for the large ones, so the answer is a **tiered isolation model** with one codebase, and the interview point is being explicit about the tiers rather than picking one.

**Decide.**

| Tier | Tenants | Data isolation | Compute | Why |
| --- | --- | --- | --- | --- |
| **Pool** | ~450 small | Shared DynamoDB table, `PK = TENANT#<id>#...`, IAM `dynamodb:LeadingKeys` condition on a tenant-scoped session | Shared functions | Cheapest; isolation enforced by **credentials**, so a code bug cannot cross tenants |
| **Bridge** | ~45 mid | Dedicated table (or dedicated index space), shared functions, per-tenant rate limits | Shared functions with per-tenant concurrency accounting | Independent capacity and metrics; attributable cost |
| **Silo** | ~5 largest / regulated | Dedicated account, dedicated stack, own KMS key, own region if required | Dedicated functions and tables | Full blast-radius and quota isolation; supports residency and cryptographic separation |

The same CDK application deploys all three - the tier is a parameter, not a fork. **Designing for silo from day one is essential** even if nobody needs it yet, because retrofitting it is a rewrite (Q165).

**The data layer:**

- **DynamoDB single table per tier**, tenant as the leading partition-key component (Q149, Q165). This gives locality, prefix-scoped IAM, and per-tenant lifecycle.
- **Tenant-scoped credentials**: the API's authorizer resolves the tenant from the JWT, and the handler assumes a session with a **session policy** constraining `LeadingKeys` to that tenant. This is the control that makes pooled isolation defensible - the enforcement is in IAM, not in a `WHERE` clause someone might forget.
- **Derived stores from the change stream**: search (OpenSearch), analytics (Kinesis → Firehose → S3, partitioned by tenant), aggregates. One write path, everything else rebuildable (Q165).
- **Per-tenant KMS keys** for silo tenants; a single service key for pool.

**Noisy-neighbour control**, in four layers because one is never enough:

1. **Per-tenant rate limits at the edge** - a Redis token bucket or API Gateway usage plans keyed per tenant, sized by their plan. This is the primary control and it must be a *product* concept (plan limits), not an ops setting.
2. **Per-tenant concurrency accounting** on async paths: a queue per tier (not per tenant - 500 queues is unmanageable), with `maximumConcurrency` per queue, and fair-share dispatch within it. For the largest tenants, their own queue.
3. **Physical separation of the analytics path** from the operational store, so a tenant's large report cannot slow another's writes.
4. **Per-tenant DynamoDB visibility**: Contributor Insights to find a hot tenant partition (Q152), and the ability to promote a tenant to bridge/silo as a *remediation*, not just a sale.

**Per-tenant cost reporting** - the part most designs handwave:

- Tags work for silo tenants (dedicated account or dedicated resources) - attribution is free (Q255).
- For pool and bridge, cost is **not taggable**, so it must be **computed**: emit per-tenant usage metrics via EMF on every request (requests, GB written, events processed, storage bytes from a periodic scan), then allocate the shared bill in proportion. Monthly job: Athena over the Cost and Usage Report joined to the usage counters, publishing cost per tenant and **cost per tenant per active user** as the unit metric (Q257).
- Report the unallocated percentage as a tracked number; if it exceeds ~15 percent the model is not working.

**Execute - sequencing.** Build pool first with the tenant-scoped credential model and the usage metrics from day one (retrofitting per-tenant metering is painful); add the bridge tier when the first tenant's metrics justify it; build silo when the first contract requires it, using the same IaC with a different parameter. Onboarding must be fully automated - a new tenant is a DynamoDB record and a Cognito group for pool, a stack deployment for silo.

**Reflect.** The risks I would name: **the pooled tenant's blast radius** (a bug in the credential-scoping logic is a cross-tenant data breach, so that code path deserves the most testing and review in the system); **tier migration** (moving a tenant from pool to silo is a data migration under load, and it should be rehearsed before it is sold); and **the largest tenant becoming a majority of load**, at which point the economics of pooling collapse and the pricing model needs to reflect it. The metric I would watch is **cost per active user per tier** - if pool's unit cost approaches silo's, the pooling is not earning its complexity.

---

### S13. Design a document ingestion and search platform (Q263)

> 50,000 documents a day, OCR, extraction, semantic search, and a seven-year retention obligation. Design it.

**Clarify.** What document types and what size distribution? Is OCR needed for all of them or only scanned images? What is the acceptable ingestion-to-searchable latency - seconds, minutes, or hours? What is the search workload - keyword, semantic, or both, and at what query rate? Who can see which documents (is search results filtering per-user)? What does the seven-year obligation require - immutability, legal hold, provable deletion? Is there a residency constraint? Are documents ever updated, or append-only?

**Isolate the numbers.** 50,000/day is **~0.6/second average**, with a realistic business-hours peak of perhaps 5-10/second and batch drops of thousands. Over seven years that is **128 million documents**. So: ingestion is low-throughput (which means Lambda is comfortable and cost is dominated by processing, not by request rate), and **storage and object count are the scaling dimension** (Q181).

**Decide.**

```
Upload:  presigned POST (policy-constrained) -> s3://docs-quarantine/<tenant>/<uuid>/original
         S3 event -> EventBridge
Pipeline: Step Functions Standard, one execution per document
   1. Validate (magic bytes, size, virus scan)  -> reject to quarantine-failed
   2. Choice: needs OCR?
        yes -> Textract (.sync via Step Functions) -> text + layout to S3
        no  -> extract text directly (PDF/Office parser in a container-image Lambda)
   3. Enrich: entity extraction (Comprehend), classification, metadata
   4. Chunk + embed (Bedrock embeddings) -> vectors
   5. Index: OpenSearch Serverless (BM25 + kNN vectors)
   6. Promote: copy original to s3://docs/<tenant>/yyyy/mm/<docId>/, apply Object Lock
   7. Write metadata item to DynamoDB, emit DocumentIndexed event
   Catch -> failure state -> DLQ + alarm + partial-result record
Search:  API Gateway -> Lambda -> OpenSearch (hybrid query, tenant + ACL filter)
         -> presigned URLs for retrieval
```

**Justification of the key choices:**

- **Step Functions Standard per document**, not a chain of Lambdas. Documents fail in interesting ways, OCR is long-running, and "why is document X not searchable" must be answerable three days later - which is exactly the execution-history argument (Q132, Q144). At 1.5 million documents/month x ~10 transitions, the cost is around $375/month, which is trivial relative to the processing.
- **Textract via `.sync`** rather than a polling Lambda: it removes the poller and the state (Q136). OCR is minutes-long, so Lambda's 15-minute limit is a real risk for large documents and `.sync` sidesteps it entirely.
- **A container-image Lambda** for document parsing, because the dependency set (parsers, fonts, native libraries) exceeds the ZIP limit (Q77).
- **Quarantine-then-promote**, so unvalidated content never lands in the durable store, and the recursion trap is structurally avoided (Q173, Q175).
- **OpenSearch Serverless for hybrid search** - keyword plus vector in one query, with per-tenant and per-ACL filtering. The alternative (a dedicated vector database) adds a system for a capability OpenSearch has.
- **DynamoDB as the metadata index**, so search results, permissions, retention class and legal-hold state are queryable without listing S3 (Q181).
- **S3 as the source of truth**, with the index rebuildable by replaying from the metadata table - which is what makes an embedding-model upgrade a re-index rather than a crisis.

**Retention and compliance**, which is half the problem:

- **Object Lock in Compliance mode** with a 7-year retention applied on promotion, in a bucket in a separate account with an SCP preventing configuration change (Q176). This is what makes the obligation defensible rather than aspirational.
- **Legal hold** per document, driven by the DynamoDB metadata, with CloudTrail data events and an alarm on every hold change.
- **Lifecycle by age**: Standard for 90 days, Standard-IA to 1 year, **Glacier Instant Retrieval** for years 1-7 - explicitly *Instant* rather than Flexible, so a discovery request is a millisecond retrieval rather than a four-hour ticket (Q169, Q181).
- **Deletion at 7 years is an application-driven, audited process**, not a lifecycle rule, because a legal hold must suspend it and because "we can prove we deleted it" is part of the requirement.
- **Derived artifacts** (thumbnails, extracted text, embeddings) in a separate bucket in One Zone-IA, since they are regenerable.

**The cost shape**, and the honest observation: at 50,000 documents/day the bill is dominated by **Textract and embeddings**, not by infrastructure. Textract at roughly $1.50 per 1,000 pages, at say 5 pages per document, is `1.5M docs/month x 5 pages = 7.5M pages` ≈ **$11,000/month** - two orders of magnitude above the Step Functions, Lambda and S3 lines combined. So the optimization work is: **do not OCR what does not need it** (a cheap content check first), cache by content hash so duplicate documents are processed once, batch where the API supports it, and pick the cheapest Textract API that answers the question (detect-text versus analyze-document). Naming that the AI/ML services dominate, and optimizing there rather than tuning Lambda memory, is the senior answer.

**Reflect.** What I would monitor: ingestion-to-searchable p99, the failure queue, per-stage cost per document, and index freshness. The risks: **embedding-model upgrades** (a re-index of 128 million documents is a project, so version the embeddings and support two indexes during migration); **object count** driving costs and `LIST` behaviour (Q181); and the **poison-document class** - a PDF that crashes the parser, which must fail into a DLQ with the document preserved rather than retrying forever (Q121's lesson applied to a different transport).

---

### S14. Migrate a Java monolith on-premises onto AWS with no big-bang cutover (Q264)

> A Java monolith runs on-premises with an Oracle database. The business will not accept a big-bang cutover or a delivery freeze. Design the migration, including data and the rollback point at every stage.

**Clarify.** What is the monolith's size and coupling - can any part be extracted, or is it a single deployable? What is the database size, schema complexity and Oracle-specific feature usage (PL/SQL, packages, jobs, sequences)? What is the peak load and the latency requirement? Is there a hard deadline (a data-centre exit, a licence renewal)? What is the current deployment frequency and test coverage? What is the acceptable downtime for the *final* database cutover - because that number drives everything?

**Isolate the strategy.** "No big-bang, no freeze" rules out re-architecting first. So the sequence must be **lift, then shift, then decompose** - move the workload with minimal change, get it running and observable on AWS, then improve. And the database must move **last or separately**, because combining a compute migration with a data migration doubles the risk of the riskiest step.

**Decide - five stages, each independently valuable and independently reversible:**

**Stage 0 - Foundation (weeks 1-4).** Accounts and landing zone (Q3, Q7), network connectivity (Site-to-Site VPN first for speed, Direct Connect ordered in parallel, Q48), IaC and pipeline with OIDC, observability baseline. *Rollback: nothing is live; delete.*

**Stage 1 - Containerize and run in parallel (weeks 4-10).** Build the monolith as a container image, deploy on **ECS Fargate** behind an ALB in AWS, **still connecting to the on-premises Oracle over the VPN/Direct Connect**. Route a small percentage of read-only traffic to it via weighted DNS. This is the single most valuable stage: it proves the network, the image, the configuration, the observability and the deployment path, while the database - the risky part - has not moved.
*Rollback: DNS weight to zero. Instant, no data implications.*
*The thing to watch: cross-link latency on every database call. If the monolith is chatty, this stage will expose it, and that information is worth having early.*

**Stage 2 - Migrate the database (weeks 10-18).** The hardest stage, so it gets the most care.

- **Schema conversion**: AWS SCT to Aurora PostgreSQL if the Oracle-specific surface is manageable; **Oracle on RDS** if PL/SQL and packages make conversion a multi-quarter project. I would make this call on evidence from SCT's assessment report, not on preference - and I would say that choosing RDS for Oracle is a legitimate answer that keeps licence cost and buys time.
- **DMS with change data capture**: full load, then continuous replication, running for **weeks** while both databases are live. Validate with DMS data validation plus application-level reconciliation queries.
- **Cutover**: at a chosen low-traffic window, quiesce writes (a maintenance page or a queue in front of the write path for minutes), let CDC drain to zero lag, flip the connection string, verify, resume. Target minutes, not hours.
- *Rollback: reverse CDC replication configured **before** cutover, so the on-premises database continues receiving changes and a fail-back is a connection-string flip. Establishing reverse replication in advance is the single most important rollback preparation in the whole programme, and it is the one people skip.*

**Stage 3 - Shift the remaining traffic and decommission the on-premises compute (weeks 18-22).** DNS to 100 percent AWS, run through a full peak cycle, then decommission. *Rollback: DNS weight back, with the on-premises stack kept warm for a defined window - I would keep it for one full month past cutover.*

**Stage 4 - Decompose, incrementally and only where justified (ongoing).** Strangler-fig: put the ALB (or API Gateway) in front, extract one bounded context at a time into a Lambda or Fargate service with its own data, route that path away from the monolith, and leave the monolith owning everything else - possibly forever. Priority order: the parts with a different scaling shape (spiky, batch, scheduled), the parts changing most often, and the parts that are cheap to extract. **Explicitly not a plan to eliminate the monolith** - a plan to stop it being the bottleneck. *Rollback per extraction: route the path back to the monolith, which still contains the code.*

**Execute - the practices that make this work regardless of stage:**

- **Every stage ships to production and delivers value**, so the programme is never a long branch. This is what makes "no freeze" achievable.
- **Dual-run and compare** wherever possible: shadow traffic to the AWS stack, compare responses, before shifting real users.
- **The rollback path is built and tested before the forward step**, not documented after.
- **One variable at a time**: never change the compute platform and the database in the same step, never combine a refactor with a migration.
- **Data reconciliation as a standing job** through stages 2-3, alarming on divergence.

**Reflect.** What I would tell the sponsor: the timeline is dominated by stage 2, and the honest risk is Oracle-specific database features, so I would fund the SCT assessment in week one before committing to a date. What I would refuse: a big-bang weekend cutover, combining the database move with a decomposition, and decommissioning the on-premises stack before a full peak cycle has run on AWS. The measure of success is not "the monolith is gone" but **deploy frequency, change failure rate and cost per transaction**, before and after - and I would set those baselines in stage 0 so the programme can be judged on outcomes rather than on activity.

---

### S15. Run a Well-Architected review on a system you are handed cold (Q265)

> You are asked to review a system you have never seen. You have half a day with the team and a week to produce something. What do you ask, in what order, and what does your output contain?

**Clarify - the meta-question first.** Who commissioned this and why? A review requested by the team is a collaboration; one requested by leadership because they are worried is a different conversation and I need to know which, because it determines whether people tell me the truth. What decision will the output inform - funding, a go-live, a re-platform, an audit? Is there an incident or a cost event behind it? And what is *not* in scope, so the review has edges?

**Isolate - the sequence of questions.** I do not start with the pillars. I start with the business and the failure history, because those tell me where to spend the half day.

**Round 1 - the system's purpose and shape (30 minutes).**
- What does this system do, for whom, and what happens to the business if it is down for an hour? For a day?
- Draw the architecture on a whiteboard, from the client to the data store, live, with the team. **Whatever they draw from memory is the real architecture**, and the gaps in the drawing are the first finding.
- What is the traffic - requests per second, shape, growth?

**Round 2 - the evidence (60 minutes).** This is where a review earns its value, because I ask for artefacts rather than opinions:
- **Show me the last three incidents** - what happened, how long to detect, how long to recover, what changed afterwards. Incident history is the highest-signal input in the whole review.
- **Show me the dashboard you look at during an incident.** If it does not exist, or nobody can find it, that is a finding.
- **Show me the SLO** and its current attainment. Usually there is none.
- **Show me the last deploy and the last rollback.** How long did each take?
- **Show me the bill**, broken down.
- **Show me the DR test.** When, and what was measured?
- **Show me the quota sheet** - which limits are you near?

**Round 3 - the pillars, as a checklist against what I have learned (90 minutes).** Now the framework is useful, because I am filling gaps rather than fishing:
- **Operational excellence**: IaC coverage, deploy and rollback mechanics, runbooks, on-call, postmortems.
- **Security**: identity model, least privilege, secrets, encryption, network boundaries, logging and detection - deferring detail to the security review (`11-security`).
- **Reliability**: single points of failure, retry topology (Q199), timeouts (Q201), quotas (Q198), backup/restore with measured RTO (Q208), multi-AZ and DR.
- **Performance efficiency**: whether the compute and data choices match the workload's shape (Q83), where latency actually goes, caching.
- **Cost optimization**: unit cost, commitments, waste, the top line items (Q250).
- **Sustainability**: honestly, mostly a proxy for efficiency - Graviton, right-sizing, storage classes.

**Round 4 - the questions that are not in the framework (30 minutes).** These are the ones that distinguish a review from a checklist:
- **What are you afraid of?** Engineers know where the bodies are; ask directly and they will tell you.
- **What would you fix if you had two weeks and nobody stopped you?**
- **What is the one thing that would take you longest to recover from?**
- **Who is the only person who knows how X works?** (Key-person risk is a reliability risk and appears in no pillar.)

**Decide - what the output document contains**, and this is the substance of the answer:

1. **An executive summary of one page**: the three risks that matter, in business language, with an estimated likelihood and impact. Not thirty findings - three. A review that produces a long undifferentiated list gets ignored.
2. **The architecture diagram** as I now understand it, which is often the most useful artefact the team receives, because it is the first accurate one.
3. **A risk register**, each item with: the finding, the *mechanism* by which it causes harm (not "no multi-AZ" but "an AZ event takes egress down for the whole VPC because there is one NAT gateway"), the blast radius, the remediation, an effort estimate, and an **owner**.
4. **A prioritized remediation plan in three tiers**: this week (cheap, high-value - alarms, retention policies, a missing DLQ, a quota increase), this quarter (structural but scoped), and this year (architectural).
5. **The trade-offs I am recommending they accept.** This is the part that makes it a principal-level document: "you are not buying 99.99 for this workload, and here is why that is correct", "single-region is the right choice given the cost of the alternative", "this technical debt is cheaper to carry than to fix". A review that lists only problems is a checklist; a review that names accepted risks is engineering judgement.
6. **What I could not assess**, and what evidence would be needed. Honesty about the limits of a half-day review protects everyone.
7. **A small number of metrics to track**, so the review is re-runnable and progress is measurable rather than remembered.

**Reflect.** How I would run it to get honest answers: no managers in the technical session; frame findings as system properties rather than people's mistakes; share the draft with the team *before* leadership and let them correct it, which both improves accuracy and means they own the remediation. What I would not do: produce a scored pillar report as the primary output (it satisfies the process and changes nothing), or recommend a re-platform on half a day of information. And the test of whether the review worked is not whether the document was approved - it is whether the "this week" tier was actually done within a month.

---

## Part C - Leadership situations

These have no single right answer. They assess judgement, honesty and whether you have actually held the responsibility. Use **STAR-L** and quantify.

### S16. The team that will not leave their own account

> One product team runs everything in a single shared AWS account they have owned for four years, outside the landing zone, with long-lived IAM users, no CloudTrail archive and their own bespoke deploy scripts. They ship faster than anyone else and their service is the company's most reliable. Security wants them migrated this quarter. They have refused twice.

**Clarify.** What specifically is the risk - a compliance obligation with a date, an audit finding, or a general standards concern? What has been asked of them before, and what did they say? What does the migration actually require of them in engineering time? Is their velocity *because* of the account, or incidental to it? Who owns the decision if they refuse again?

**The judgement.** Two facts are both true: they are right that the platform's paved road is probably slower and less capable than the thing they built, and security is right that long-lived IAM users and no audit trail is an unacceptable risk. A mandate will produce grudging, minimal compliance and a quarter of hostility. What I would do:

1. **Separate the non-negotiable from the negotiable, explicitly.** Non-negotiable: no long-lived access keys, CloudTrail to an immutable archive, GuardDuty, and the account inside Organizations under an SCP. Negotiable: their pipeline, their IaC tool, their deploy scripts, their account structure beyond the above. Most "standards" resistance is resistance to the negotiable parts bundled with the non-negotiable ones, and unbundling them usually collapses the conflict.
2. **Do the work for them, first.** I would have the platform team enrol their account into Organizations, set up the OIDC role and the CloudTrail archive, and hand them a pull request. The cost to the platform team is days; the cost to the argument is enormous. Asking a fast team to slow down to satisfy someone else's checklist is a request they will always resist; removing the work is a different conversation.
3. **Learn from them, publicly.** Their deploy scripts are faster than the paved road for a reason. I would spend a day with them, find what the platform's road is missing, and fix it - and say in the platform's channel that the change came from them. That converts an adversary into a contributor and improves the road for everyone.
4. **Be honest about the risk with leadership**, in mechanism terms: "a leaked key from this account has no audit trail and no blast-radius boundary; that is the exposure, and it is not about their competence."
5. **If they still refuse the non-negotiables**, that is an escalation - and I would make it cleanly, once, with the specific items and the specific risk, and let the accountable executive decide. I would not run a war of attrition.

**Reflect.** The lesson I would state: **standards adopted under mandate are maintained under duress.** The measure of a platform is whether the fastest team chooses it, so a refusal from your best team is primarily information about your platform. And the thing I would be careful about: if this team is genuinely faster because they escaped the platform, migrating them may cost the company more than the risk it removes - so I would want the risk quantified rather than asserted before spending the political capital.

> *Hook: a standard you drove into a resistant team, what you unbundled, and what you learned from them.*

---

### S17. You are asked to go multi-region by a date, and you do not think it is right

> After a competitor's public outage, an executive commits publicly to "full multi-region redundancy by end of quarter". Your estate is single-region, well-run, and at 99.94 percent measured availability. You have one meeting.

**Clarify.** What is the actual driver - a customer contract, a regulator, board optics, or genuine risk concern? What availability number are we committing to, measured how? Is there a customer who will leave without it? What budget and headcount come with the commitment?

**The judgement.** I would not open with "that is a bad idea". I would open with the arithmetic and the alternative, then let the numbers carry the argument (Q229).

1. **Convert the commitment into a number.** 99.99 is 4.4 minutes a month. Our current 99.94 is about 26 minutes. So the gap is 22 minutes a month - and then the crucial question: **what caused those 26 minutes?** In almost every estate the answer is deploys and configuration, not regional failure. A second region does nothing about a bad deploy and doubles the surface for one (Q227).
2. **Show what active-active actually costs**: roughly double the infrastructure for the stateful tiers, a materially slower release process, conflict-resolution correctness work with silent failure modes (Q216), and a quarterly failover drill programme that must be staffed. Present it as a permanent operating cost, not a project.
3. **Show that the theoretical availability gain is not achievable in a quarter.** An untested multi-region deployment is *less* reliable than a well-run single region, and the failure modes are new and unfamiliar. A rushed multi-region by a date is the most likely way to *cause* the outage we are trying to prevent - and I would say that plainly.
4. **Offer the credible alternative, staged.** In one quarter: DR to a second region as a pilot light with a tested, rehearsed 15-minute RTO (which for a serverless estate is cheap, Q210), plus attacking change failure rate - canaries with automatic rollback, progressive delivery, sub-five-minute rollback. That plausibly takes us from 99.94 to 99.97 and gives a defensible answer to a customer asking about regional failure. In two to three further quarters: active-active for the read and accept paths, if the business still wants it.
5. **Give the executive something to say publicly** that is true: "we can survive the loss of a region with a tested recovery in under 20 minutes" is a strong statement, and it is one I can deliver by the date.

**Reflect.** The principle: **my job is to convert an availability aspiration into an availability number with a price, and then let the business choose** - not to accept an engineering commitment made in a press cycle, and not to refuse it either. The failure mode I would avoid is winning the argument and being seen as an obstacle; the way to avoid it is to arrive with a plan that delivers by the date, even if it is not the plan that was announced.

> *Hook: a commitment you renegotiated with numbers, and what you delivered instead.*

---

### S18. The engineer whose backfill took down production

> A senior engineer runs a backfill that consumes the account's Lambda concurrency and throttles the customer-facing API for 25 minutes (scenario S4). They found it, stopped it and wrote the postmortem themselves. In the review, a director asks what the consequence will be for the individual.

**The judgement.** My answer in the room is unambiguous and I would give it immediately, because hesitation is itself a signal to every engineer watching: **the consequence for the individual is nothing, and the consequence for the system is a list of changes.** Then the reasoning, stated to the director rather than about them:

1. **The engineer did nothing unusual.** They ran a batch job in an account that permitted a batch job to consume every unit of shared concurrency. Any engineer could have done it, and if we punish this one, the next person hides it for twenty minutes while trying to fix it quietly - which is how a 25-minute incident becomes a two-hour one.
2. **They detected, mitigated and documented it themselves.** That is exactly the behaviour we want, and it is the behaviour we destroy by attaching consequences to it.
3. **The system failed, and the failure is specific and fixable**: no reserved concurrency floor on tier-1 functions, no ceiling on batch functions, batch and interactive workloads sharing an account and therefore a quota, and no alarm on account-level concurrency utilization. Those four items are the output of the postmortem (Q69, Q3).
4. **If there is an accountability question, it points at me**, not at them - the guardrails were my responsibility, and I would say so in the room. That is usually the sentence that ends the conversation productively.

**What I would do afterwards**, because "blameless" is not "consequence-free for the organization":

- Ship the four guardrails, with dates and owners, and report completion.
- Ask the engineer to present the postmortem to the wider engineering group. It reframes them as the person who found a systemic gap, which is what they are, and it spreads the lesson faster than a document.
- Check privately how they are doing. People who cause incidents often take it much harder than anyone realizes, and a senior engineer who becomes cautious is a real loss.

**Where I would draw a line**, because a completely absolute answer is not credible: repeated disregard for an agreed control, or concealment, is a performance conversation - held privately, never in a postmortem. The distinction is **a mistake inside a permissive system versus a deliberate bypass of a control**, and the postmortem is not the venue for the second either.

**Reflect.** The lesson to state: **an incident caused by one person doing an ordinary thing is always a systems finding.** The measure of whether your culture is actually blameless is not the policy document - it is whether the next engineer reports their own mistake in the first minute.

> *Hook: a blameless postmortem you led where someone wanted a consequence, and what you shipped instead.*

---

### S19. Two teams, one shared DynamoDB table, and a deadline

> The pricing team needs to change an attribute's type on a table that the catalogue team also reads directly. Catalogue cannot absorb the change for six weeks. Pricing has a commitment in two weeks. Both have escalated to you. Neither reports to you.

**Clarify.** What exactly is the change, and is there a version of it that is additive? Who owns the table? How many other consumers are there - is it really only two? What breaks for catalogue if the change ships - a runtime failure, or a data-interpretation error? What is the actual commitment pricing has made, and to whom?

**The judgement.** The immediate conflict is solvable; the underlying problem is that two teams share a table, which means the table is a public API with no contract (Q21, Q150). I would solve both, in that order, and be explicit that I am doing two things.

**The immediate resolution - the expand-contract play.** Almost every "we must change a field's type" conflict dissolves into: **add a new attribute, write both, let consumers migrate, remove the old one later.**

1. Pricing adds `priceMinorUnits` alongside the existing `price`, and **dual-writes both** for the transition. Ships in days, no coordination required, meets the two-week commitment.
2. Catalogue migrates to the new attribute on their own schedule within the six weeks.
3. The old attribute is removed in a third, scheduled step with a named date and owner - and **I would make sure that step has a ticket and an owner before agreeing to the plan**, because the failure mode of expand-contract is that the contract phase never happens and you accumulate both fields forever.

If dual-writing is genuinely impossible, the fallback is a translation layer: catalogue reads through a thin adapter (a Lambda, or a projection into their own table from the change stream) that presents the old shape. More work, same principle - **decouple the two teams' timelines rather than choosing whose deadline wins.**

**The structural fix**, which I would raise in the same conversation but not make a precondition:

- **Catalogue should not read pricing's table.** It should consume an event (`PriceChanged`) or call an API, so pricing can change their storage whenever they like. I would propose a concrete plan: pricing emits events from the table's change stream (Q128), catalogue builds its own projection, and direct table access is removed with a date. That is a quarter of work, and this incident is the business case for funding it.
- **In the meantime, document the shared table as an interface** with a named owner and a change process, because an undocumented shared dependency will produce this escalation again next month.

**How I would run the conversation**, given I have no authority over either team: get both leads in one room (not a thread), state the constraint from each side back to them so both feel heard, put the expand-contract option on the whiteboard, and let them agree to it - because a solution they choose will actually be implemented. I would only decide unilaterally if they cannot agree, and then I would say clearly that I am deciding and why.

**Reflect.** The lesson: **most cross-team deadline conflicts are false dilemmas created by a missing abstraction.** The escalation asks "whose deadline wins"; the engineering answer is usually "neither has to lose, and here is the interface we should have had". And the second lesson, for me: this escalation is a symptom of an architectural boundary violation that someone should have caught at design time - so I would ask why direct cross-team table access was permitted, and whether there are others.

> *Hook: a cross-team conflict you resolved with a compatibility strategy, and the boundary you fixed afterwards.*

---

### S20. You inherit an estate nobody understands, and finance wants 25 percent

> You have been in the role three weeks. The AWS bill is $180,000 a month across 40 accounts with inconsistent tagging. The CFO wants a 25 percent reduction this quarter. The engineering teams are already stretched and morale is low after a reorganization.

**Clarify.** Twenty-five percent of absolute spend or per unit of business (Q257)? Is the business growing, and by how much? Is this a cash-flow requirement with a hard date, or a target? What happens if we deliver 15 percent? Do I have authority to make changes in teams that do not report to me, or must everything go through their backlogs?

**The judgement.** Three constraints - a number, a deadline, and a stretched, demoralized organization - and the third is the one that determines the approach. A cost programme run *at* teams will fail and will make morale worse; one run *for* them can actually improve morale, because engineers generally dislike waste.

**What I would do:**

1. **Renegotiate the metric before accepting the target.** If the business is growing 20 percent, absolute and per-unit targets are wildly different asks, and I would get that written down in week one. I would also state early - not at the end of the quarter - what I believe is achievable safely, so the conversation is a forecast rather than a failure.
2. **Take the work off the teams for the first half.** The largest wins require almost no engineering time: **commitments** sized to the measured floor (Q252), deleting unambiguous waste, retention and lifecycle policies, non-production shutdown schedules. That is plausibly 12-18 percent, delivered by me and a small group, with teams asked only to confirm nothing is in use. **Delivering most of the number without spending team capacity is the whole strategy**, and it buys the credibility for anything I need from them later.
3. **Make the visibility a gift, not a stick.** Every team gets a weekly message showing their own cost, their unit cost, and their top three line items (Q256). Framed as "here is information you did not have", not "here is your bill". Several teams will act on it unprompted, and those are the wins to publicise.
4. **Name the exclusions publicly and up front**: multi-AZ, backups, DR, security controls, and the observability needed to run an incident are not on the table (Q258). Saying this in the first all-hands does two things - it protects the estate, and it tells engineers that I am not going to trade their on-call quality for a finance target. That is worth more to morale than any tooling.
5. **Be honest about the gap.** If the safe number is 18 percent, I would put the remaining 7 percent in front of the CFO as an explicit choice: architectural work over two quarters, or reduced resilience with the risk documented and signed. **I would not silently deliver 25 percent by deleting the standby region** - and being visibly unwilling to do that is part of establishing what kind of leader I am, three weeks in.
6. **Fix the attribution as a durable outcome**, not just the number: tagging enforced in IaC and the pipeline, Cost Categories, per-team reporting, unit cost metrics (Q255, Q257). The quarter's saving is one-off; the ability to see cost is permanent, and it is what stops the next 25 percent request being another fire drill.

**Reflect.** What I would consider success: the number delivered or the gap honestly negotiated; **no reliability regression** (tracked explicitly - change failure rate, SLO attainment, MTTR before and after, Q259); teams having spent almost no capacity; and cost visible per team afterwards. What I would watch for in myself: the temptation to demonstrate impact quickly by touching things I do not understand yet, in an estate I have known for three weeks - which is precisely how a cost programme causes an outage.

> *Hook: a cost mandate you were given early in a role, what you delivered, and how you protected the teams and the estate.*
