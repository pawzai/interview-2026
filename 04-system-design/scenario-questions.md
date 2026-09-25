# Scenario Questions

Whole-system incidents, full design exercises and leadership situations.

Every scenario uses **CIDER**, defined in [../01-java/README.md](../01-java/README.md):

- **Clarify** - what you ask before answering. Never diagnose or design in silence.
- **Isolate** - narrow the failure domain or the core requirement.
- **Decide** - commit to an approach and name the trade-off.
- **Execute** - the concrete steps.
- **Reflect** - what you monitor, prevent, or would do differently.

Part B uses a fixed spine instead, because a design exercise is not a diagnosis: **Clarify and cut**, **Targets**, **Estimate**, **API**, **Data**, **Design**, **Scale**, **Failure**, and **Change one requirement**. Practising the same spine fifteen times is the point - in the interview you should be able to run it without thinking about the structure.

Read the scenario, answer out loud for the time noted, then compare. The model responses are longer than you should speak - use them as the map, not the script.

---

## Part A - Production incidents

### S1. The launch melted on day one

> A marketing campaign went live at 09:00. By 09:02 the site was returning 503s. Traffic was 8x the load test. The team scaled the web tier to 4x and nothing improved. It is 09:20 and the CEO is in the channel.

**Clarify.** What exactly is returning 503 - the load balancer with no healthy targets, the gateway shedding, or the application? Which endpoint? Is the database saturated, or idle? What do connection pool metrics show - `pending` acquisitions? Are we seeing timeouts or refusals? Did anything else change at 09:00 besides traffic? Is the traffic real users or a crawler following the campaign links?

**Isolate.** "Scaled the web tier and nothing improved" is the most informative sentence. It means the bottleneck is **downstream and shared**, so adding web instances added load rather than capacity. Three candidates:

1. **Database connection exhaustion.** More instances x a fixed pool per instance = more connections demanded, so scaling out made it worse. The signature is an idle-looking database and application-side acquisition timeouts (`../06-database/answers.md` Q236).
2. **A cold cache with a stampede** (`answers.md` Q73, Q76) - every request missing and hitting the origin, single-flight absent.
3. **All targets unhealthy** because a deep health check is failing on the saturated dependency, so the load balancer has nothing to route to (Q87) - which produces exactly "503 on everything" including endpoints that would have worked.

**Decide.** I stop scaling and start shedding. At 8x capacity the only path to a serving system is to serve less than is being asked. Restoring partial service now beats a correct diagnosis in an hour.

**Execute.**

1. **Turn on load shedding at the edge** with a concurrency limit sized to the last known-good throughput, priority-ordered so interactive traffic wins and crawlers, prefetches and retries are shed first (Q94). Accept a visible queue or error page for the excess.
2. **Serve the campaign landing page statically** from the CDN with a long TTL. If the campaign points at one page, that single change removes most of the load.
3. **Check the health-check hypothesis in 30 seconds** - if targets are flapping, switch the check to shallow or enable fail-open so the fleet returns to rotation.
4. **Cap the total database concurrency** with a proxy or a fleet-wide semaphore, so the database serves a bounded amount of work well instead of thrashing.
5. **Disable non-essential features** behind flags - recommendations, personalization, the activity feed - converting hard dependencies into absent ones (Q157).
6. **Then** scale, in the right place: the database's read capacity and the cache tier, not the web tier.

**Reflect.** The systemic failures are that the load test was 8x too small, and that the system had no admission control - so its behavior above capacity was undefined rather than degraded. Afterwards: load test at 2x the *marketing* forecast rather than the engineering forecast, and get the forecast from the people buying the traffic (Q98); make admission control and priority shedding permanent and exercised; add a "static launch page" pattern to the launch checklist; and add the pre-launch capacity review that raises non-elastic ceilings - pool sizes, quotas, partition counts. The cultural fix is that a campaign date is a capacity event and must appear on the engineering calendar with an owner.

> *Hook: a launch that exceeded its forecast, and the control that saved or failed it.*

---

### S2. The cache tier restarted and took the database with it

> A managed Redis cluster failed over at 14:12. It was unavailable for 40 seconds. The database has been at 100 percent CPU for 25 minutes and the site is down, even though Redis has been healthy for 24 of those minutes.

**Clarify.** What is the normal cache hit ratio, and what is the database's uncached capacity as a fraction of peak? Is the cache refilling - what is the hit ratio right now? Are we seeing many concurrent identical queries (a stampede) or a broad spread? Is there a circuit breaker on the database path, and is it open? What is the retry configuration in the application and the client SDKs?

**Isolate.** This is a textbook **metastable failure** (`answers.md` Q26, Q76). The 40-second trigger is over; the system stays down because of two self-sustaining loops:

1. **Stampede.** Every cache miss for the same hot key becomes an independent database query, so one key's traffic is amplified by its concurrency instead of being coalesced (Q73).
2. **Retry amplification.** Requests time out, clients retry, and the retries are indistinguishable from new work, so the offered load exceeds capacity permanently (Q153).

The database being at 100 percent CPU with the cache healthy is the confirmation: the cache cannot refill because every refill attempt is queued behind a saturated database, and the database cannot drain because the cache cannot refill.

**Decide.** Break the loop by force. The only way out of a metastable state is to reduce offered load below capacity, hold it there until the cache warms, then release. I will accept a brief, deliberate, partial outage to end an involuntary total one.

**Execute.**

1. **Clamp database concurrency** to a value the database can actually serve (from Little's Law, or empirically the last known-good in-flight count). Everything above it is rejected fast, not queued.
2. **Shed retries first** at the edge, then non-interactive traffic (Q94). If retries are 60 percent of the load, this alone may be sufficient.
3. **Warm the cache deliberately**: run a warming job that populates the top-K keys directly from the database at a controlled rate, ahead of user traffic. This is far cheaper than letting user traffic do it.
4. **Enable single-flight** if it is a config flag; if it is not, that is the first code change afterwards.
5. **Release load gradually** - 10 percent, 25, 50 - watching hit ratio and database CPU, not error rate. Releasing all at once re-enters the loop.

**Reflect.** The design defect is that the database could serve only a small fraction of peak, making the cache a hard dependency with no acknowledgement of that fact. Afterwards I would: implement single-flight and `stale-if-error` (Q73), add a short-TTL local cache as a second tier so a shared-cache failure is partial (Q69), add a permanent database concurrency limiter, implement retry budgets and mark retries so they can be shed (Q111), and add a **cache-loss game day** to measure the real uncached capacity and publish it as a known risk. I would also add the leading metric - hit ratio and origin QPS - to the dashboard with an alert, because the exposure was there for months before it was exercised.

> *Hook: a cache-dependency incident, the uncached capacity number you discovered, and what you changed.*

---

### S3. Two services both think they own the write

> Duplicate charges have appeared for about 300 customers over the last week. Each duplicate is 40-90 seconds apart, same amount, same card, different payment ids. Nothing in the deployment log correlates. The payment service has three instances behind a queue-driven worker.

**Clarify.** Are the duplicates from the same inbound request (a retry) or two distinct inbound requests? Do they share an idempotency key? What is the queue's visibility timeout, and what is the p99.9 processing time of the worker? Are the workers logging lease extensions? Does the payment provider return an idempotency key on its side, and are we sending one? Do the duplicates cluster in time - during deploys, or during periods of high latency?

**Isolate.** "40-90 seconds apart, same amount, different payment ids" is the signature of **at-least-once redelivery combined with a missing or non-atomic idempotency check** (`answers.md` Q103, Q112). Concretely, three candidates ordered by likelihood:

1. **Visibility timeout shorter than the p99.9 processing time.** The worker takes 65 seconds during a slow period; the timeout is 60; the broker redelivers; a second worker processes the same message concurrently. This matches the 40-90 second spread exactly, and it explains the correlation with slow periods rather than with deploys.
2. **Idempotency implemented as `SELECT` then `INSERT`** rather than as a unique constraint in the same transaction as the effect - a race under Read Committed (`../06-database/answers.md` Q36) that only manifests under true concurrency.
3. **A downstream call keyed with a fresh UUID per attempt**, so the provider sees two distinct requests even though our own layer deduplicated (Q38).

**Decide.** Stop the bleeding first with the cheapest safe change, then fix the mechanism properly. I do not begin with a refactor while customers are being charged twice.

**Execute.**

1. **Immediately:** raise the visibility timeout well above the observed p99.9, or better, implement lease heartbeat extension. This removes the trigger within minutes.
2. **Same day:** make the idempotency record a **unique constraint written in the same transaction as the charge**, scoped to `(tenant, endpoint, key)` (Q35). Any second attempt fails on the constraint rather than on a check.
3. **Derive the provider's idempotency key deterministically** from our root key plus the step name, so a retry at any level maps to one provider-side operation (Q38).
4. **Reconcile and remediate:** query the provider for all charges in the window, match against our records, identify duplicates, refund them proactively, and contact the affected customers before they contact us.
5. **Add a detection control** that would have caught this in hours instead of a week: an alert on two successful charges for the same card and amount within a short window.

**Reflect.** Three lessons. First, **at-least-once is not a broker setting, it is a property of every distributed write**, and the consumer's idempotency is the only real guarantee - so a payment path must be reviewed against that assumption explicitly. Second, the visibility timeout is a *correctness* parameter masquerading as a tuning knob, and it should be derived from the measured p99.9 with a documented margin, checked in CI against the metric. Third, the detection gap is the worst part: a week of duplicate charges with no alert means we were relying on customers as our monitoring. I would add reconciliation against the payment provider as a standing daily job with an alerting threshold, because in financial flows reconciliation is not a nicety, it is the control.

> *Hook: a duplicate-write incident, the atomicity defect behind it, and the reconciliation job that came out of it.*

---

### S4. The region failover worked and the system is still broken

> The primary region became unreachable at 03:40. Failover to the standby region completed at 03:52 and was reported successful. At 04:10 the error rate is 60 percent, latency is 4 seconds, and nobody knows why.

**Clarify.** Which requests are failing - all, or a subset by endpoint? What are the errors: timeouts, 5xx from our services, or 5xx from a dependency? Is the standby region's fleet at its intended size, and did it autoscale? What is the database's state - promoted, and how far behind was it? Are outbound calls to third parties succeeding? What does the cache hit ratio look like? Are there requests crossing back to the primary region?

**Isolate.** Four candidates, all classic (`answers.md` Q174), and the evidence separates them quickly:

1. **A dependency did not fail over.** Some hostname, ARN or connection string is region-pinned - a queue, a search cluster, a secret store - or a third party's IP allowlist contains only the primary region's egress addresses. Signature: a specific subset of endpoints failing with timeouts to one target.
2. **Capacity.** The standby was warm at 25 percent scale and cannot serve 100 percent of traffic; autoscaling is either too slow or blocked by a per-region quota nobody raised. Signature: saturation metrics high, errors broad, latency high across the board.
3. **Cold state.** Empty caches mean full uncached load on a freshly promoted database - which is S2 in a different costume. Signature: hit ratio near zero, database saturated.
4. **Data.** The replica was behind, so recent writes are missing, sequences may have gone backwards, and idempotency records are gone - producing correctness errors rather than timeouts.

**Decide.** With 60 percent errors, I triage in the order that restores service fastest: capacity and cold state first (they are the most common and the most mechanical), dependency reachability in parallel, and data integrity as a separate track that must not block restoration but must be assessed before we tell anyone we have recovered.

**Execute.**

1. **Scale the standby to full size immediately**, manually, bypassing autoscaling. Check the region's service quotas and raise them; this is a frequent hard stop.
2. **Shed load to below the region's current capacity** and warm the caches deliberately (S2), releasing traffic in steps.
3. **Run the dependency inventory check** - a script that verifies every external endpoint is reachable from this region. If it does not exist, this incident is where it gets written.
4. **Establish the data position**: what was the replication lag at the cut, which writes are missing, and what is the reconciliation plan. Communicate it as a known quantity rather than an unknown.
5. **Verify no traffic is crossing back** to the primary region, which would add 80 ms per hop and may be silently failing.

**Reflect.** The failover "succeeded" because we measured the wrong thing - promotion completing, not the system serving. Afterwards: define failover success as an SLI (successful requests in the standby region), not a step in a runbook. Build the **regional dependency inventory** as an enforced artifact, with a CI check that no region-specific identifier exists outside it. Automate **quota and configuration parity** checks between regions with drift alerting. Make the standby statically stable at full size (Q158), because a standby that must scale during a disaster depends on the control plane during the exact event that stresses the control plane. And run **monthly traffic shifts** into the standby (Q179) - the only reliable way to keep it working is to use it.

> *Hook: a failover that exposed a hidden regional dependency, and the inventory you built afterwards.*

---

### S5. Latency is fine at p50 and users are furious

> The dashboard shows p50 at 80 ms and average at 140 ms, comfortably inside the SLO. Support tickets say the app is "unusably slow". The product manager wants to know who is right.

**Clarify.** What does p99 and p99.9 look like, and per endpoint rather than aggregated? How many requests does one user-visible screen make? Where is the measurement taken - server-side, or at the client? Are the slow reports concentrated in a tenant, a region, a device class, or an account size? What is the error and timeout rate, since a timed-out request often does not appear in the latency histogram at all?

**Isolate.** Both are right, and there are four distinct mechanisms that produce this exact discrepancy (`answers.md` Q9, Q10):

1. **Per-request percentiles do not describe a page.** If a screen makes 20 calls and each has a 1 percent chance of being slow, roughly `1 - 0.99^20 = 18 percent` of screens contain a slow call. The user experiences the *maximum*, not the percentile.
2. **The average hides the tail** (Q8). A 1 percent population at 5 seconds moves the average by 50 ms and ruins the experience of that 1 percent - who are the people filing tickets.
3. **Server-side measurement excludes the parts users feel**: DNS, TLS, queueing at the edge, network on a mobile connection, and client rendering. It also excludes requests that never arrived.
4. **Aggregation hides a segment.** A large tenant whose queries scan more data, or a region routed to a distant backend, can be uniformly terrible while the global p50 is fine - because they are a small share of traffic.

**Decide.** I would not argue about the number; I would change what we measure. The SLI must be defined on something the user experiences, and it must be segmentable.

**Execute.**

1. **Add client-side (RUM) measurement** of the user-visible operation - time to interactive for the screen, not per request. This becomes the primary SLI; server-side latency becomes a diagnostic.
2. **Break out p99 and p99.9 per endpoint, per tenant, per region and per device class.** Then find the segment. In my experience it is one of: a specific large tenant, a specific endpoint with an unindexed path, or one region's routing.
3. **Count requests per screen** and reduce fanout, because that arithmetic is often the whole answer - a screen making 20 sequential calls cannot be fast whatever the percentiles say.
4. **Check what is missing from the histogram**: timeouts, connection failures and client-side abandonment. A histogram of successful requests is a survivorship-biased view.
5. **Hedge or degrade the slow tail** (Q10, Q157) rather than only optimizing the median.

**Reflect.** The real defect is that the SLO was defined where it was easy to measure rather than where the user is, which meant the monitoring could be green while the product was failing. Afterwards: define SLIs on user-visible operations, always include a per-segment view, always alert on burn rate rather than a raw percentile, and treat "average latency" as a metric we do not display. I would also add the discipline of comparing the support-ticket signal with the dashboard monthly, because a persistent divergence between the two is itself a monitoring defect.

> *Hook: a case where the dashboards were green and the product was broken, and how you closed the gap.*

---

### S6. One customer's traffic is degrading everyone

> Since a large customer was onboarded on Monday, p99 for all tenants has doubled and two smaller customers have complained. The new customer is inside their contracted request rate.

**Clarify.** What is their share of *requests*, of *concurrency*, of database rows scanned, of queue depth, and of storage? Which shard or partition are they on? Are their requests different in shape - larger date ranges, bigger result sets, more expensive filters? Is the degradation continuous or bursty? Are they using a bulk or export endpoint? Where exactly is the queueing - the web tier, the pool, the database, the worker fleet?

**Isolate.** "Within their contracted rate" plus "degrading everyone" is the standard signature of quotas measured in the wrong unit (`answers.md` Q231). Likely mechanisms:

1. **Concurrency, not rate.** 200 concurrent requests at 2 seconds each is far more damaging than 2,000 short requests per second, and a request-rate quota does not constrain it (Q93).
2. **Cost per request.** Their dataset is 100x larger, so the same query scans 100x the rows. The quota counts requests; the system consumes work.
3. **Shared shard contention.** They landed on a pooled shard and are now its dominant tenant, so everyone co-located with them suffers (Q142).
4. **FIFO queueing in async workers**, so their 200,000 queued jobs delay everyone else's three (Q231).

**Decide.** Contain first, then re-architect the quota model. I will not ask the customer to reduce usage they are contractually entitled to; the defect is ours.

**Execute.**

1. **Immediate containment:** a per-tenant concurrency limit at the edge, set from the historical distribution so it constrains the outlier without affecting anyone else. This is usually a configuration change and it works within minutes.
2. **Switch async workers to fair queueing** (weighted round-robin across tenants) instead of FIFO. Frequently the single largest improvement, and invisible to the tenants who were not causing the problem.
3. **Bulkhead by workload class** (Q155): move bulk, export and report traffic into a separate pool so it cannot occupy interactive capacity.
4. **Move the large tenant to a dedicated shard** (a silo), which is why directory-based routing exists (Q135, Q230). This is the durable fix for a tenant of this size.
5. **Add cost-weighted quotas** - rows scanned or query cost units, not just requests - and enforce a maximum result-set size and date range on the expensive endpoints (Q43).

**Reflect.** The onboarding process treated a large customer as a commercial event rather than a capacity event. Afterwards: a **tenant sizing review** as a gate before onboarding anyone above a threshold, with an explicit placement decision (pooled or dedicated); per-tenant metrics for rate, concurrency, cost and share of shard as a standing dashboard; quotas expressed in resource units and visible to tenants; and shuffle sharding so the next such tenant degrades a slice rather than the whole (Q152). The organizational point I would make is that "noisy neighbor" is not a customer behavior problem, it is a missing isolation mechanism, and the sales team should be able to sell to large customers without asking engineering's permission.

> *Hook: a tenant who exposed a missing isolation mechanism, and what you built.*

---

### S7. The queue is 40 million messages deep and growing

> An async pipeline that normally runs at zero lag is 40 million messages behind after a downstream API was slow for two hours. The downstream recovered an hour ago. Lag is still growing.

**Clarify.** What is the current consumer throughput versus the producer rate - is lag growing because we are slower than the inflow, or because we are stuck? What is the retry configuration, and what fraction of processing attempts are retries? Is the downstream actually healthy now, or healthy-when-lightly-loaded? What is the log's retention, and how long until the oldest unprocessed message expires? Is the partition count limiting consumer parallelism? Are there poison messages in a hot retry loop?

**Isolate.** Lag still growing after recovery means throughput is below the inflow rate, and there are three usual causes (`answers.md` Q107, Q111):

1. **Retry occupancy.** Retried messages compete with new ones for the same workers, so effective throughput for *new* work is a fraction of capacity - and if retries are re-enqueued to the same queue with short delays, most attempts are doomed replays.
2. **The downstream is only healthy at low load.** We are now offering it 5x normal traffic (catch-up plus current), so it degrades again - a self-inflicted repeat of the original outage.
3. **Parallelism is capped by partition count** (Q145), so adding consumers does nothing.

The urgent constraint is **retention**: if the oldest message will expire before we process it, the lag becomes permanent data loss, and that deadline sets the whole plan.

**Decide.** Priorities in order: (1) do not lose data - extend retention or drain to durable storage; (2) get current traffic flowing again, because live users matter more than the backlog; (3) drain the backlog at a rate the downstream can sustain. That means deliberately **separating live traffic from catch-up**, which is the key decision.

**Execute.**

1. **Extend the log's retention immediately** (or start copying unprocessed messages to object storage) so the deadline is removed and we can think.
2. **Split the workload.** Route new messages to a fresh consumer group or topic served by dedicated capacity, so live processing returns to zero lag now. The backlog becomes a separate, bounded job.
3. **Fix the retry behavior:** separate retry queues per attempt tier, exponential backoff applied in the broker, a retry budget, and a circuit breaker on the downstream so we stop generating doomed attempts (Q111).
4. **Drain the backlog at a controlled rate** with the downstream's latency as the control signal - increase concurrency until its p99 rises, then hold. Batch the downstream calls if it supports it; batching is usually a 10x improvement (Q107).
5. **Check for poison messages** and route them to the DLQ rather than letting them consume a worker indefinitely.
6. **Decide, explicitly, whether the whole backlog is worth processing.** If these are analytics events, dropping messages older than a threshold may be the right answer, and it should be a stated decision with a business owner - not something that happens silently at retention expiry.

**Reflect.** Three preventable failures: no separation between live and catch-up processing, retries that amplified rather than absorbed, and no alert on lag *derivative* (Q107) - which would have paged us during the two-hour outage rather than three hours later. Afterwards: alert on lag growth rate and on projected retention exhaustion; make backlog draining a rehearsed runbook with a rate limiter; implement retry budgets and tiered retry queues as platform defaults (Q115); over-provision partitions so parallelism is available when needed (Q145); and add a documented drop policy per topic so the "is this data worth it" decision is made in advance.

> *Hook: a backlog you drained, the separation you introduced, and the data you decided not to process.*

---

### S8. A single hot key is melting one shard

> A product went viral. One item's page is 45 percent of all read traffic. The shard holding it is at 100 percent CPU; the other 15 shards are at 12 percent. Cache hit ratio for that key is 70 percent.

**Clarify.** Reads or writes? What is the 30 percent miss actually caused by - TTL expiry, evictions, or a stampede on each expiry? Is the response identical for all users, or personalized? What is the TTL? Is there single-flight on the miss path? Is the item's data changing, or is it static? Is the load from real users or from a scraper?

**Isolate.** 70 percent hit ratio on a key receiving 45 percent of traffic is the whole problem: the 30 percent that misses is itself an enormous absolute volume, and it all lands on one shard. The likely mechanisms (`answers.md` Q140, Q73):

1. **No request coalescing.** On each TTL expiry, thousands of concurrent requests all miss and all query the database - so the origin sees a spike per TTL period rather than one refill.
2. **Eviction pressure**, if the cache is undersized and the hot key is being evicted between reads.
3. **Personalization in the cache key**, splitting one hot object into many variants and destroying the hit ratio (Q79).
4. **No edge caching**, so every request travels to origin infrastructure for an object that is probably identical for everyone.

**Decide.** For a read-hot, mostly-static, publicly-identical object, the correct answer is to serve it from the edge and stop involving the shard at all. That is minutes of work and removes the problem rather than redistributing it.

**Execute.**

1. **Put the item response behind the CDN** with a short `s-maxage` (30-60 s), `stale-while-revalidate` and `stale-if-error` (Q78). A 45-percent-of-traffic object at even a 95 percent edge hit ratio reduces origin load by an order of magnitude immediately.
2. **Enable single-flight** on the miss path so one request per key per interval reaches the database (Q73), and add TTL jitter.
3. **Add a short-TTL local in-process cache** for the top-K keys, so each instance absorbs its share without a network hop (Q69).
4. **Split personalization out of the shared response** - the shared shell cached, the personal fragment fetched separately (Q79).
5. **Add read replicas for that shard** if writes are not the issue, and steer that key's reads to them (Q147) - traffic rebalancing before data rebalancing.
6. Only if it is **write**-hot: split the key (sub-keys with a merge on read) or move it to dedicated capacity (Q140).

**Reflect.** The gap is detection: we learned about the hotspot from CPU saturation, not from a hotspot signal. Afterwards: per-partition metrics with a **skew ratio** on the dashboard and an alert, plus heavy-hitter sketch sampling that names the offending keys (Q141); single-flight, jitter and `stale-if-error` as platform defaults rather than per-team choices; and the CDN as the first line for any publicly-identical response, decided at design time. The broader lesson to state: a system designed for the average key will be broken by the popular one, and popularity is always Zipf-distributed, so the hot-key path deserves a design rather than a reaction.

> *Hook: a hot-key event, the mitigation you shipped first, and the detection you added.*

---

### S9. The AI feature is timing out and taking the checkout with it

> An LLM-powered product recommendation panel was added to the checkout page last month. This morning the provider is slow. Checkout conversion has dropped 30 percent and the checkout service's thread pool is exhausted.

**Clarify.** Is the recommendation call synchronous and inline with the checkout request? What timeout is configured? Does it share a thread pool and connection pool with the checkout path? Is there a circuit breaker, and a fallback? What is the provider's current latency, and is it failing or just slow? Is the panel required for checkout to function, in any product sense?

**Isolate.** The failure is architectural, not operational (`answers.md` Q209-210, Q224): a **soft dependency was wired as a hard one, sharing a bulkhead with a critical path**. Specifically:

1. A 20-second upstream call inside a request whose budget is 500 ms holds a thread for 40x its allowance. By Little's Law, modest concurrency exhausts the pool (Q24).
2. Pool exhaustion means checkout requests that need no recommendation cannot get a thread - so a cosmetic panel has taken down the revenue path. This is the definition of a missing bulkhead (Q155).
3. No circuit breaker means we keep offering traffic to a degraded provider, and no fallback means every failure is user-visible.

**Decide.** Disable the feature now, then re-architect it as a genuinely soft dependency. There is no diagnosis worth 30 percent of conversion.

**Execute.**

1. **Kill switch the panel** - a flag, no deploy. Conversion should recover within minutes. If no such flag exists, that is finding number one.
2. **Isolate it** before re-enabling: its own bounded thread pool or, better, an async non-blocking client; its own connection pool; a timeout of 1-2 seconds, not 20; a circuit breaker; and a concurrency cap (Q155, Q210).
3. **Add a deterministic fallback** - cached recommendations, a popular-items list, or an empty panel that the layout handles gracefully (Q157, Q224).
4. **Move it off the critical path entirely.** The panel should load *after* the page, from a separate endpoint, so its latency is never the page's latency. This is the real fix and it makes the timeout question almost irrelevant.
5. **Cache aggressively**, including a semantic or cohort cache (Q215, Q201), so most requests never reach the provider.
6. **Add multi-provider failover and a smaller-model tier** for degraded operation (Q213).

**Reflect.** The process failure is that an AI feature was added to the checkout path without a dependency classification (Q163) or a fallback, and without anyone asking what happens when the provider is slow - which is a certainty, not a risk. Afterwards: a rule that **no new dependency enters a critical path without a declared class, a timeout, a bulkhead, a fallback and a kill switch**, enforced in design review; a feature-level SLO for the AI panel separate from the checkout SLO, so its degradation is visible and acceptable (Q224); and a game-day exercise injecting provider latency, because this exact scenario is the most predictable AI-era incident there is.

> *Hook: an AI or third-party dependency you had to demote from hard to soft, and how you argued it.*

---

### S10. A schema change to one service broke three others

> A team renamed a field in an event they publish. Their CI passed, their deploy was clean. Overnight, three downstream consumers silently stopped populating a field, and a customer-facing report has been wrong for 18 hours.

**Clarify.** What exactly changed - a rename, a type change, a semantic change? Is there a schema registry, and was compatibility enforced? Are consumers deserializing strictly or leniently? Did the consumers *fail* or silently write nulls? How was the report's wrongness detected, and how long could it have gone unnoticed? Is the affected data recoverable from the log?

**Isolate.** Two distinct failures, and the second is worse (`answers.md` Q41, Q115):

1. **A breaking change was publishable.** A rename is a delete plus an add, which is not backward-compatible for an event contract. Nothing prevented it because there was no enforced registry in CI, and the producer's own tests could not detect a change to consumers they do not know about.
2. **Consumers failed silently.** Lenient deserialization mapped the missing field to null and carried on. A hard failure would have paged someone in minutes; a silent null produced 18 hours of quietly wrong data and a customer-visible report defect - and it will happen again in a way nobody notices at all.

The organizational root cause is that the event was a **public contract with no contract mechanism**, and the producer had no way to know who depended on it.

**Decide.** Restore correctness by replay rather than by backfill scripts, then close both gaps - publication-side enforcement and consumption-side loudness. The second is the one people forget and it matters more.

**Execute.**

1. **Immediate:** revert the producer to the old field name (or publish both fields), so consumers recover without changes on their side.
2. **Repair the data by replaying** the affected window through the consumers, which is safe because consumers are idempotent - and if they are not, that is finding number two (Q113).
3. **Correct the customer-facing report** and communicate, since it was externally visible for 18 hours.
4. **Publication side:** a schema registry in the path with `FULL` compatibility enforced in CI, so this change fails the producer's build. A genuinely breaking change requires a new topic version with dual publication and a consumer migration (Q41, Q115).
5. **Consumption side:** fail loudly. Required fields validated on deserialization, with an alert and a DLQ rather than a null. Add data-quality tests on the output (not-null, range, freshness) that block the downstream build (Q208).
6. **Register consumers** so the producer can see dependents before changing anything (Q47).

**Reflect.** The systemic lesson is that **an event is an API**, and the reason this happened is that it was treated as an implementation detail. Afterwards I would drive three platform changes: registry-enforced compatibility as a non-negotiable gate; a standard client library that validates required fields and dead-letters rather than nulling (governance implemented as a library succeeds where a document does not, Q115); and lineage plus consumer registration so blast radius is knowable. I would also make the point that this was not the publishing team's fault - the platform permitted it, and blaming the team guarantees a recurrence while fixing the gate prevents it.

> *Hook: a contract breakage you saw, and the enforcement mechanism you introduced.*

---

## Part B - Design exercises

Each of these is a 40-45 minute exercise. Work the spine out loud - **Clarify and cut, Targets, Estimate, API, Data, Design, Scale, Failure, Change one requirement** - before reading. The estimates are shown with their arithmetic because in an interview the arithmetic *is* the answer; a number with no derivation is worth nothing (`answers.md` Q30).

### S11. A URL shortener at 100 million redirects a day (Q241)

**Clarify and cut.** Are custom aliases required? (Yes.) Do links expire? (Optional expiry.) Is click analytics real-time or batch? (Batch, minutes acceptable.) Is the link space public and guessable - do we need unguessable codes for private links? (Both types.) Multi-region? (Reads globally, writes can be single-region.) I will design creation, redirection and analytics ingestion, and treat the analytics query layer and abuse detection as mentioned-not-designed.

**Targets.** Redirect availability 99.99 percent (a broken link is worse than a slow one); redirect p99 under 50 ms at the edge; creation p99 under 200 ms; analytics freshness under 5 minutes; links durable forever unless expired.

**Estimate.**

```
Redirects:  10^8 / 86,400 ≈ 1,160 QPS average; x3 peak ≈ 3,500 QPS
Creates:    read:write ratio of roughly 100:1 → ~12 QPS average, ~40 peak
Storage:    assume 100M new links/year
            per row: code(8) + url(~200) + owner(16) + timestamps(16) + flags ≈ 300 B
            → 30 GB/year raw, x2.5 for indexes ≈ 75 GB/year
            5 years ≈ 375 GB → comfortably one relational instance (answers.md Q48)
Hot set:    click distribution is steeply Zipf; the top 1% of links get ~70% of traffic
            1M hot links x 300 B ≈ 300 MB → the entire hot set fits in memory trivially
Analytics:  10^8 click events/day at ~200 B ≈ 20 GB/day raw → 7 TB/year → columnar + retention tiering
```

The conclusion to state immediately: **this is not a scale problem, it is a latency and availability problem.** 3,500 QPS and 375 GB are small; the interesting engineering is the read path's latency and the analytics volume, which is 200x the link data.

**API.**

```
POST /v1/links            {url, custom_alias?, expires_at?, private?}
                          Idempotency-Key required
                          → 201 {code, short_url, created_at}
                          → 409 if custom_alias taken
GET  /{code}              → 301/302 to target, or 404, or 410 if expired
GET  /v1/links/{code}     → metadata + click summary (owner only)
```

`302` versus `301`: **302 (or 307)**, deliberately. A 301 is cached by browsers indefinitely, which means we lose analytics, cannot change the target, and cannot revoke a malicious link. The cost is that every click reaches us, which is exactly what we want here.

**Data.**

```
links(code PK, target_url, owner_id, created_at, expires_at, is_private, disabled_at)
custom aliases: same table, unique constraint on code
clicks: event stream → columnar store, partitioned by day
        (code, ts, ip_hash, ua_class, referrer_host, geo)
counters: per-code aggregate, updated from the stream
```

**Code generation.** Two schemes for the two link types. For public short links, a **counter-derived code**: take a value from a pre-allocated block (hi-lo, `answers.md` Q127) and base62-encode it, giving 7 characters for `62^7 ≈ 3.5 x 10^12` links. No collision check needed, which removes a round trip and a race. For private links, **random 10-12 characters from a CSPRNG** so they are unguessable, with a unique-constraint insert and retry on the (vanishingly rare) collision. Custom aliases are user-supplied with a unique constraint, a reserved-word blocklist, and a check against confusable characters.

**Design.**

```
                 ┌──────────────── CDN / edge (302 cached briefly) ────────────┐
User ──▶ Anycast GLB ──▶ Redirect service (stateless, many regions)            │
                              │  1. local LRU cache (top-K codes)              │
                              │  2. Redis (regional, hot set)                  │
                              │  3. PostgreSQL read replica (regional)         │
                              └─▶ click event ──▶ Kafka ──▶ columnar store
                                                       └──▶ counter aggregator

Creation ──▶ API service ──▶ PostgreSQL primary (single region) ──▶ replication
```

Three cache layers because the hot set is tiny and immutable-ish: an in-process LRU of the top 100,000 codes (a few tens of MB, sub-microsecond), a regional Redis for the broader hot set, and a regional read replica as the floor. Negative caching and a Bloom filter of existing codes (Q74) matter here specifically, because a guessable-looking code space invites enumeration and every miss would otherwise reach the database.

The click event is emitted **asynchronously, after the redirect response is sent** - the user must never wait for analytics, and losing a click event is acceptable (a best-effort dependency, Q163).

**Scale.** The read path scales by adding stateless regions with local caches; the write path barely needs to scale at all. The analytics path is where the volume is, and it scales by partitioning the stream by code and the storage by day, with pre-aggregation into per-code-per-hour rollups so the query layer never scans raw events for a summary.

**Failure.**

- **Cache tier down:** replicas serve; capacity check says a single replica handles 3,500 QPS of point lookups easily, so this is a latency event, not an outage (contrast S2, where the arithmetic was hostile).
- **Primary region down:** creation stops (accept it, or promote a replica), redirects continue everywhere from regional replicas and caches. This is the key property - **the critical path is read-only and therefore survives a write-side outage.**
- **Kafka down:** clicks are dropped or buffered locally with a bounded queue; redirects unaffected.
- **A malicious link:** a `disabled_at` flag, propagated by cache invalidation with a short TTL as the backstop, plus an edge-level blocklist for the urgent case.

**Change one requirement.** *"Analytics must be real-time, per click, with no loss."* Then the click emission becomes a durable write on the critical path, which changes everything: the redirect now depends on the event pipeline's availability, so I would write to a local durable buffer with an ack before responding, and accept a small latency increase - or push back and ask whether "no loss" is worth coupling the redirect path's 99.99 percent target to a streaming system.

---

### S12. A social news feed for 200 million users (Q242)

**Clarify and cut.** Chronological or ranked? (Ranked, but I will design the delivery and treat ranking as a pluggable stage.) Follower distribution? (Median ~200, maximum ~50 million - four orders of magnitude, and this is the constraint.) Freshness target? (Seconds for followed accounts.) Do we support reshares, mentions, and deletion propagation? (Yes, and deletion must be prompt.) I will design write, fanout, timeline read and the ranking hook; I will not design media handling, moderation or search.

**Targets.** Timeline read p99 under 200 ms; post visible to active followers within 5 seconds at p99; timeline read availability 99.95 percent; post write availability 99.99 percent (losing a user's post is unacceptable); degradation permitted to a chronological feed if ranking is unavailable.

**Estimate.**

```
Users:      200M total, assume 100M DAU
Posts:      2 posts/user/day for 20% of DAU → ~40M posts/day → 460/s avg, ~1,400/s peak
Reads:      50 timeline views/DAU/day → 5 x 10^9 /day → 58,000 QPS avg, ~175,000 peak
Fanout:     40M posts x 200 avg followers = 8 x 10^9 timeline writes/day
            → 92,000 writes/s average, ~300,000 peak      ← the real number
Timeline:   keep 800 entries/user x 100M active users x 32 B (post_id, author, score, ts)
            = 2.5 TB in the timeline store → memory-resident across a sharded cluster
Posts:      40M/day x 500 B = 20 GB/day → 7 TB/year
```

The two numbers that decide the design: **reads outnumber writes ~125:1**, so precomputation wins; and **fanout writes are 200x post writes**, so fanout is the dominant workload and the celebrity case is unaffordable (Q187).

**API.**

```
POST /v1/posts                {text, media_ids?, reply_to?}  Idempotency-Key
                              → 201 {post_id, created_at}
GET  /v1/timeline?cursor=...  → {items:[{post_id, author, ...}], next_cursor}
GET  /v1/users/{id}/posts     → author timeline (own posts, cheap)
DELETE /v1/posts/{id}         → 204, tombstone propagated
```

Cursor is opaque and encodes `(score, post_id)` so pagination is stable under insertion (Q36).

**Data.**

```
posts(post_id PK, author_id, body, created_at, deleted_at)     -- sharded by post_id
social_graph: followers(author_id, follower_id)  -- sharded by author_id (for fanout reads)
              following(follower_id, author_id)  -- sharded by follower_id (for pull path)
timeline(user_id, score, post_id)                -- sharded by user_id, capped at 800
author_cache(author_id → recent 200 post_ids)    -- for the pull path
```

The graph is stored twice, partitioned both ways, because fanout needs "who follows X" and the pull path needs "whom does Y follow" - a deliberate denormalization (Q143).

**Design.** Hybrid fanout, which is the whole answer (Q186-187):

```
POST ──▶ post service ──▶ posts store (durable, the source of truth)
                              │ outbox
                              ▼
                           Kafka: post-created
                              │
                    ┌─────────┴──────────┐
                    ▼                    ▼
          fanout worker            author_cache updater
       (if followers < T)          (always)
                    │
                    ▼
             timeline store (per-user list, capped)

GET timeline ──▶ timeline service
                   ├─ read precomputed timeline (one sequential read)
                   ├─ read author_cache for each followed "large" account (few)
                   ├─ merge + dedupe
                   ├─ ranking stage (features + model, degradable)
                   └─ hydrate post bodies (batched multi-get, cached)
```

- **Below the threshold T** (say 100,000 followers): fanout-on-write. Reads are one sequential read.
- **Above T**: no fanout. The author's recent posts live in a heavily cached `author_cache`, and readers merge at read time. Since a user follows few such accounts, the merge is bounded and cheap - and the post is visible *instantly*, which is better than fanout would have achieved.
- **Inactive followers are skipped** in fanout; their timeline is rebuilt on return. This typically removes half the fanout volume.
- **Timelines are capped** at ~800 entries; deeper pages fall back to the pull path.
- **Ranking is a separate stage** operating on ~500 merged candidates, with precomputed features and a strict timeout, degrading to chronological order (Q199).

**Scale.** Fanout workers scale horizontally, partitioned by author, with **separate queues by follower-count band** so a 90,000-follower fanout cannot delay ordinary ones (Q94). The timeline store is sharded by `user_id` - perfectly even distribution, since users are uniform. The post store is sharded by `post_id`. Hydration is the read amplifier: 800 timeline entries need 800 post bodies, so batched multi-get plus a post cache with a very high hit ratio is essential, and posts are immutable, which makes that cache easy.

**Failure.**

- **Fanout lag:** the timeline is stale; the pull path for large accounts still works. Degradation, not failure. Alert on lag derivative (S7).
- **Timeline store partition down:** affected users get a fully pull-based timeline - slower and more expensive, but present. Worth building for exactly this reason.
- **Ranking service down:** chronological order (Q157).
- **Deletion:** a tombstone must propagate to up to 50 million timelines. Do it lazily - filter deleted post ids at read time using a small, fast tombstone set, and clean timelines in the background. Correctness at read time, no fanout storm.

**Change one requirement.** *"Strictly chronological, no ranking."* Then the merge becomes a k-way merge on timestamp and the ranking stage disappears, which is simpler - but I lose the ability to drop low-value posts, so timelines must hold more entries and the pull path gets more expensive. *"Freshness must be sub-second for all followers, including the 50-million account."* Then fanout-on-write is definitively impossible and the pull path must serve everything for large accounts, so I would push the author's post to a CDN-backed object and have clients poll or subscribe - accepting that "sub-second to 50 million people" is a broadcast problem, not a database problem.

---

### S13. Chat and messaging with groups, presence and receipts (Q243)

**Clarify and cut.** One-to-one and groups - what group size? (Up to 500 for now, 100,000 for "channels" later.) Must messages be durable and ordered? (Yes, strictly ordered per conversation, never lost.) End-to-end encryption? (Not in scope, but I will note where it changes the design.) Multi-device? (Yes - three devices per user.) I will design message send/deliver, ordering, presence, receipts and reconnection; I will not design media, calls or moderation.

**Targets.** Message durability: no acknowledged message is ever lost. Delivery p99 under 500 ms for online recipients. Send availability 99.99 percent. Ordering: strict per conversation. Presence: best-effort, 30-second accuracy. Reconnect backfill p99 under 2 seconds.

**Estimate.**

```
Users:        50M DAU, 10M concurrent connections at peak
Messages:     40 sent/DAU/day → 2 x 10^9 /day → 23,000/s avg, ~70,000/s peak
Delivery:     avg 3 recipients (1:1 plus groups) x 3 devices ≈ 9 deliveries/message
              → ~600,000 deliveries/s at peak                ← the dominant number
Connections:  10M concurrent at ~40 KB each ≈ 400 GB of connection state
              → 10M / 250,000 per node = 40 gateway nodes, ~50 with redundancy
Storage:      2 x 10^9 msgs/day x 300 B = 600 GB/day → 220 TB/year
              → time-partitioned, tiered to cold storage (answers.md Q62)
Presence:     10M users / 30 s heartbeat = 333,000 writes/s → must be batched at the gateway
```

**API.** WebSocket with a small framed protocol, plus HTTP for history.

```
→ {"t":"send","cid":"conv_9","client_msg_id":"uuid","body":"..."}
← {"t":"ack","client_msg_id":"uuid","msg_id":"...","seq":10482}
← {"t":"msg","cid":"conv_9","seq":10483,"from":"u_7","body":"..."}
→ {"t":"read","cid":"conv_9","upto_seq":10483}
→ {"t":"resume","cursors":{"conv_9":10480,"conv_3":992}}
← {"t":"resync","cid":"conv_12"}     # too stale for incremental

GET /v1/conversations/{cid}/messages?before_seq=...&limit=50
```

`client_msg_id` is the idempotency key, so a resend after a lost ack does not duplicate. `seq` is a per-conversation monotonic sequence - not a timestamp (Q188).

**Data.**

```
messages(conv_id, seq, msg_id, sender_id, body, created_at)
    PK (conv_id, seq)  -- sharded by conv_id, bucketed by month to bound partitions
conversations(conv_id, type, member_count, last_seq)
members(conv_id, user_id, joined_at, last_read_seq, last_delivered_seq)
    -- read position per user, NOT a row per message per user (answers.md Q189)
presence: presence:{user_id} → {status, node} with 45 s TTL
devices(user_id, device_id, push_token, last_seen)
```

**Sequence assignment** is the correctness core: one writer per conversation assigns `seq`. Implemented as a conditional increment of `conversations.last_seq` in the same transaction as the message insert (a per-conversation serialization point - fine, because conversations are independent and each has low write volume). This gives strict ordering and gap-free numbering without a global coordinator.

**Design.**

```
Client ──WSS──▶ L4 LB ──▶ Gateway fleet (connections, subscriptions, heartbeats)
                              │                        ▲
                              │ publish                │ subscribe to hashed channels
                              ▼                        │
                        Message service ──────▶ Pub/Sub (256 channels by conv_id hash)
                              │
                              ├─▶ message store (durable, sequenced)
                              ├─▶ read-position store
                              └─▶ push bridge ──▶ APNs/FCM (for offline devices)
```

**Routing** uses the hashed-channel hybrid (Q185): each gateway subscribes only to the channels covering its connected users' conversations, so a message reaches a small subset of nodes rather than all 50, and no per-user connection registry must be kept consistent.

**The send path, ordered so durability precedes delivery:** authenticate → authorize membership → dedupe on `client_msg_id` → assign `seq` and persist → **ack the sender** → publish for delivery. The ack means "durably stored", not "delivered", which is the correct contract; delivery status arrives later as receipts.

**Presence** is a per-user key with a TTL, heartbeats batched at the gateway (one pipelined batch per node per interval instead of 250,000 individual writes), and read on demand for the visible subset only - never broadcast to all contacts (Q183).

**Receipts** use per-user read positions, not per-message rows: one write per user per read event regardless of how many messages were read, which turns a 500-member group's receipt storm into 500 small updates and gives unread counts for free (Q189). Above a group-size threshold, per-person receipts are aggregated rather than itemized.

**Scale.** Gateways scale by connection count and are the expensive tier; the message service scales by conversation shard; the message store partitions by `conv_id` with monthly buckets so no partition grows unbounded (Q146). For 100,000-member channels, the fanout model inverts: do not deliver to each member, publish once to a channel object and let clients pull - the same push/pull crossover as S12.

**Failure.**

- **Gateway node dies:** its 250,000 clients reconnect with backoff and jitter, resume from their cursors, and receive the delta. Nothing is lost because delivery is a pull-with-cursor, not a push-and-forget (Q188).
- **Deploy:** staggered, 2 percent of nodes at a time, with server-directed reconnect pacing - otherwise a reconnect storm (Q184).
- **Pub/sub down:** messages are still durably stored and acked; delivery falls back to clients polling their cursors. Degraded latency, no loss - which is why the durable store must not depend on the delivery path.
- **Push provider down:** offline users are notified late; the in-app inbox reconciles on open (Q190).

**Change one requirement.** *"End-to-end encryption."* The server can no longer read message bodies, so search moves to the client, server-side moderation becomes impossible, multi-device requires a key-distribution protocol with per-device sessions, and backfill for a new device needs a re-encryption or key-transfer scheme. Ordering, sequencing and delivery are unaffected - which is worth saying, because it shows the layering is right. *"Groups of 100,000 with receipts."* Receipts become aggregate-only, presence is disabled for the group, and delivery becomes pull-based.

---

### S14. A distributed rate limiter as a platform service (Q244)

**Clarify and cut.** Who are the users? (200 internal services, protecting themselves and enforcing customer quotas.) What accuracy is required? (Protective limits: approximate is fine. Billing quotas: exact.) Is it a library, a sidecar or a service? (I will argue for a library with a shared backend, with a service mode for non-JVM callers.) Latency budget? (Under 1 ms added at p99 - this is the binding constraint.) I will design the enforcement mechanism, the state layer, the policy model and the failure semantics.

**Targets.** Added latency p99 under 1 ms; availability higher than any caller (99.99 percent), with a defined behavior when unavailable; accuracy within 5 percent for protective limits and exact for metered ones; policy change propagation under 30 seconds.

**Estimate.**

```
Traffic:   200 services x avg 500 QPS = 100,000 QPS of limit decisions, peak ~300,000
Naive:     one Redis round trip per decision = 300,000 Redis ops/s
           → feasible but expensive, and it puts a network hop in every request
Batched:   lease blocks of 20 tokens → 15,000 Redis ops/s          ← 20x reduction
Keys:      200 services x (policies x tenants). Assume 50,000 distinct tenants
           x 3 policies = 150,000 active keys. At ~100 B each = 15 MB. Trivial
Hot keys:  the largest tenant may be 30% of one service's traffic → key splitting needed
```

The arithmetic drives the central decision: **a synchronous network call per request is affordable but wrong**, because it adds latency and a hard dependency to every request in the organization. Batched leases remove both.

**API.** A library, because that is what makes adoption and latency work:

```java
RateLimiter limiter = platform.limiter("orders-api");

Decision d = limiter.check(Key.of(tenantId), Policy.WRITE, /* cost */ 1);
if (!d.allowed()) return tooManyRequests(d.retryAfter(), d.policyName());
```

Policies are declared as configuration, not code:

```yaml
policies:
  - name: write
    scope: tenant
    algorithm: token_bucket
    rate: 1000/minute
    burst: 200
    on_backend_failure: fail_open      # explicit, per policy
  - name: export
    scope: tenant
    algorithm: leaky_bucket
    concurrency: 2
    on_backend_failure: fail_closed
```

**Data.** One Redis hash per `(policy, key)` holding `{tokens, last_refill_ms}`, mutated by a Lua script so refill-and-consume is atomic. Redis Cluster shards by key. Policy definitions live in a config store, pushed to libraries and cached locally.

**Design.**

```
Service process
  ├─ local token allowance (leased block)  ← decision made here, ~100 ns
  ├─ async lease refill when allowance low
  └─ Redis Cluster (authoritative buckets, Lua CAS)
         ▲
         └─ policy config pushed from control plane (cached locally, statically stable)
```

The mechanism (Q92): each process leases a block of tokens from the authoritative bucket and spends them locally. Refill happens asynchronously when the block is low, so the hot path never blocks on the network. Overshoot is bounded by `processes x block_size`, and I size the block so that overshoot is under 5 percent of the limit - and I *state* that bound in the documentation rather than implying exactness.

**Algorithm: token bucket** as the default, because rate and burst are separate dials that map onto what people actually want, with O(1) state (Q91). Leaky-bucket-as-a-queue for concurrency limits where delaying beats rejecting.

**Hot keys** are split into N sub-keys each with `limit/N`, with callers choosing by hash - the standard mitigation, applied automatically above a traffic threshold (Q140).

**Exact metering** takes a different path: the *decision* is approximate and fast, and the *accounting* is an exact event stream aggregated asynchronously for billing. Trying to make one mechanism serve both is the design error to avoid.

**Scale.** Redis Cluster scales by key hash, and the lease mechanism means Redis traffic grows 20x slower than request traffic. The control plane is not on the hot path and can be small.

**Failure.** This is the most important section, because a rate limiter is a dependency of everything:

- **Redis unavailable:** behavior is a **per-policy declared decision**. Protective limits **fail open** with the local allowance continuing at a conservative rate - availability of the protected service matters more than precision. Abuse and security limits **fail closed**. Making this explicit per policy, and testing both paths, is the design's key safety property.
- **Control plane unavailable:** libraries use the last known good policy indefinitely (Q158). A rate limiter that fails because it cannot fetch configuration is worse than no rate limiter.
- **A policy misconfiguration** (someone sets `rate: 10/minute` on a hot endpoint) is the most likely real incident, so: policy changes are reviewed, canaried, and deployable in **observe-only mode** first, with per-policy metrics on allowed/rejected before enforcement is turned on.
- **The limiter itself must not be the bottleneck:** local decisions, no allocation on the hot path, and a hard rule that a `check()` call never blocks.

**Change one requirement.** *"Limits must be exact, globally, with no overshoot."* Then leases are impossible and every decision is a synchronous atomic operation against a single authority for that key - so I would add ~0.5 ms to every request, cap throughput per key at what one Redis shard can serve, and require callers to accept a hard dependency. I would push back hard and ask which limits genuinely need exactness, because in my experience it is the billing ones, and those are better served by exact *accounting* after the fact than by exact *enforcement* before it.

---

### S15. A notification platform across 30 producing teams (Q245)

**Clarify and cut.** Channels? (Email, SMS, mobile push; in-app inbox as a fourth.) Who owns the content? (Producing teams own templates; the platform owns delivery.) Are there per-user preferences and quiet hours? (Yes, and regulatory unsubscribe requirements for marketing.) Volume mix? (Transactional and marketing, with different rules.) I will design the ingestion contract, preference and dedup logic, channel delivery, and the governance; I will not design the template authoring UI or campaign scheduling.

**Targets.** Transactional notifications: delivered to the provider within 30 seconds at p99, at-least-once, never lost. Marketing: minutes acceptable. Availability of the ingestion API 99.99 percent (producers must never be blocked). No user receives a notification they have opted out of - a correctness requirement, not a best-effort one.

**Estimate.**

```
Users:       50M, of whom 20M reachable by push, 40M by email, 15M by SMS
Volume:      transactional 5M/day, marketing 20M/day (bursty: a campaign is 10M in an hour)
             → transactional ~60/s avg; marketing peak 10M/3600 ≈ 2,800/s
Fanout:      1 notification event → up to 3 channels x devices → ~2.5 sends/event
Providers:   each has its own rate limits (e.g. push 10k/s, SMS 200/s per number pool,
             email 5k/s) → provider rate limiting is a hard design constraint
Storage:     25M/day x 500 B (event + status history) = 12 GB/day → 4.5 TB/year
             → 90-day hot retention, then aggregate + archive
```

The design-shaping fact: **marketing bursts are 50x transactional steady state, and providers have fixed rate ceilings.** So the platform is fundamentally a rate-controlled queue, and the interesting problem is fairness and prioritization, not throughput.

**API.** One ingestion contract, deliberately narrow:

```
POST /v1/notifications
{
  "template": "order.shipped.v3",
  "recipient": {"user_id": "u_7"},          // never raw email/phone from producers
  "params": {"order_id": "...", "eta": "..."},
  "category": "transactional",              // drives preference and priority rules
  "dedup_key": "order.shipped:ord_882",
  "channels": ["auto"]                       // platform decides, per preferences
}
→ 202 {notification_id}
GET /v1/notifications/{id}  → per-channel status history
```

Three deliberate constraints in that contract: producers send a **user id, not an address**, so the platform owns contactability and consent; producers send **template plus params, not rendered content**, so localization, branding and compliance footers are centrally enforced; and a **`dedup_key`** is mandatory, so retries and duplicate triggers collapse.

**Data.**

```
notifications(id, template, user_id, category, dedup_key, params, created_at, status)
    unique (user_id, dedup_key)                       -- idempotency
deliveries(id, notification_id, channel, address_ref, provider, status,
           attempts, next_attempt_at, provider_msg_id)
preferences(user_id, category, channel, enabled, quiet_hours_tz, frequency_cap)
suppressions(address_hash, reason, created_at)          -- bounces, complaints, unsubscribes
contacts(user_id, channel, address_encrypted, verified_at)   -- PII, tokenized
templates(name, version, channel, locale, body, approved_by, approved_at)
```

**Design.**

```
Producers ──▶ Ingestion API ──▶ Kafka: notification-requested
                                     │
                              Decision worker
                                ├─ dedup (unique dedup_key)
                                ├─ resolve contacts + verify
                                ├─ apply preferences, quiet hours, frequency caps
                                ├─ check suppression list
                                ├─ render template (locale, params)
                                └─▶ per-channel queues (priority: transactional | marketing)
                                          │
                     ┌────────────────────┼────────────────────┐
                     ▼                    ▼                    ▼
              Push dispatcher      Email dispatcher      SMS dispatcher
              (rate-limited,       (rate-limited,        (rate-limited,
               token lifecycle)     bounce handling)      number pools)
                     └──────────── status events ──▶ deliveries store ──▶ inbox + reporting
```

The **decision worker is the heart of the platform** and the reason it exists: consent, suppression, quiet hours, frequency capping and localization are enforced in exactly one place. Thirty teams cannot each be trusted to check an unsubscribe list, and the regulatory exposure of getting it wrong is real.

**Per-channel dispatchers** each own their provider's peculiarities: push token lifecycle and per-token error handling (Q190); email bounce and complaint feedback loops feeding the suppression list; SMS number pools, country routing and cost. Each dispatcher has its own rate limiter matched to the provider's ceiling, its own retry schedule, and its own DLQ.

**Priority and fairness:** separate queues per priority class, and **fair queueing across producing teams within a class** (Q231), so one team's 10-million campaign cannot delay another team's password-reset emails. This is the single most important operational property.

**Scale.** Ingestion and the decision worker scale horizontally, partitioned by `user_id` (which also keeps a user's frequency cap decisions on one partition, avoiding races). Dispatchers scale up to the provider's rate limit and no further - so the queue absorbs bursts by design (Q164), and the campaign's completion time is a function of the provider ceiling, which must be communicated to marketing rather than engineered around.

**Failure.**

- **A provider is down or slow:** its dispatcher's circuit breaker opens, its queue grows, other channels are unaffected. Transactional notifications may failover to a secondary provider; marketing waits.
- **Ingestion must never fail** for producers, so it validates minimally, writes to the log, and returns 202. All the expensive logic is downstream.
- **A bad template or a bad campaign** is the highest-probability incident: a template change that renders wrongly, or a campaign targeting the wrong segment. Controls: template versioning with approval, a mandatory canary send to an internal cohort, a **global kill switch per template and per campaign**, and a rate ramp on campaigns so a mistake reaches 10,000 people rather than 10 million.
- **Duplicate storms** from a producer replaying events: absorbed by `dedup_key` plus per-user frequency caps, which are the last line of defense against a producer bug becoming a user-visible flood.

**Change one requirement.** *"Notifications must be delivered exactly once."* Impossible for email, SMS and push, because the providers themselves are at-least-once and unverifiable (Q190). What I can offer is exactly-once *attempt* per `dedup_key` on our side plus provider-level idempotency where offered, and I would state that plainly rather than promise something undeliverable. *"Marketing must go out within 5 minutes of a campaign launch."* Then the provider rate ceiling becomes the binding constraint: 10 million emails in 5 minutes is 33,000/second, so this is a commercial negotiation with the provider (or multiple providers in parallel), not an engineering change.

---

### S16. Marketplace search and autocomplete at 500 million listings (Q246)

**Clarify and cut.** Near-real-time inventory - what does that mean? (A sold-out item must disappear from results within seconds.) Personalized ranking? (Yes, but degradable.) Faceted navigation? (Yes - category, price, brand, location.) Geo-scoped? (Yes, distance filtering.) I will design indexing, query, autocomplete and the inventory freshness path; I will not design the ranking model itself or seller tooling.

**Targets.** Search p99 under 300 ms; autocomplete p99 under 100 ms; inventory change reflected in results within 10 seconds at p99; search availability 99.95 percent, degradable to unpersonalized and unfaceted; recall against a ground-truth set measured and monitored (`answers.md` Q217).

**Estimate.**

```
Listings:    500M active. Per document ~2 KB (title, description, attributes, facets)
             → 1 TB of source documents
Index:       inverted index + doc values ≈ 1.5-2x source for a searchable subset
             → shard target 30-50 GB per shard → 500M / (10M docs/shard) ≈ 50 shards
             x 2 replicas = 150 shard copies → ~30-40 data nodes
Queries:     20M searches/day → 230 QPS avg, ~700 peak
             autocomplete at ~8 keystroke-requests per search, debounced to ~3
             → 60M/day → 700 QPS avg, ~2,000 peak
Updates:     inventory/price changes: 5% of listings/day = 25M/day → 290/s avg,
             bursty to several thousand/s during promotions       ← the freshness problem
New/edited:  2M/day → 25/s
```

The interesting tension: **50 shards means every non-trivial query is a scatter-gather across 50 shards, so query latency is the max of 50 shard latencies** (Q139, Q10) - which makes tail latency, not throughput, the engineering problem.

**API.**

```
GET /v1/search?q=running+shoes&category=footwear&price_max=5000
               &lat=..&lon=..&radius_km=25&sort=relevance&cursor=...
→ { items:[...], facets:{category:[...], brand:[...]}, total_approx: 14200, next_cursor }

GET /v1/autocomplete?q=runn&lat=..&lon=..
→ { suggestions:[{text, type, category_hint}] }
```

`total_approx` is labelled approximate deliberately (Q200), and facet counts may be omitted under load.

**Data.**

```
Source of truth:  PostgreSQL — listings, inventory, prices, sellers
Search index:     OpenSearch — 50 shards, documents denormalized for query
Autocomplete:     in-memory trie with precomputed top-K per prefix, versioned artifact
Cache:            Redis — hot query results, facet counts for popular navigation paths
```

The index document is **denormalized** - seller rating, category path, computed popularity and geo point are all embedded - because a join at query time is impossible.

**Design.**

```
PostgreSQL ──logical decoding (CDC)──▶ Kafka ──▶ Indexer ──▶ OpenSearch
                                                     │            ▲
     inventory service ──fast lane──────────────────┘             │
                                                                   │
Query ──▶ Search API ──┬─ cache lookup (query+filters+cohort)      │
                       ├─ retrieval (BM25 + filters + geo) ────────┘
                       ├─ facet aggregation (capped, approximate)
                       ├─ rerank (personalization, timeout + fallback)
                       └─ hydrate: batched fetch of current price/availability
```

Three design decisions worth defending:

1. **CDC, not dual write** (Q197). The index is derived, rebuildable, and never authoritative. Drift detection runs continuously (count comparison plus a rolling checksum sweep), and there is a tested full-reindex-with-alias-swap procedure whose duration is measured - because that duration is the recovery time for a corrupted index.
2. **A fast lane for inventory.** The 10-second freshness requirement applies to *availability*, not to descriptions. So inventory and price changes bypass the general indexing pipeline via a partial-update path, and - critically - the read path **hydrates availability from the source of truth** for the results it returns. That means a sold-out item is filtered at read time even if the index has not caught up, which converts a hard freshness requirement into a batched lookup of 50 ids. This is the answer to S16's central tension, and it is the same principle as "search returns candidate ids, the source of truth decides existence" (Q198).
3. **Autocomplete is built offline** from query logs into a versioned trie artifact, loaded in-process by every API instance, with short prefixes cached at the CDN (Q196). No datastore is involved in the hot path.

**Scale.** Query throughput scales by adding index replicas; the scatter-gather cost is reduced by **routing** - if a query is category- or geo-scoped, route it to a subset of shards by using the scope as a routing key, which turns a 50-shard fanout into a 5-shard one. Facet cost is controlled by capping cardinality, approximating high-cardinality facets, and precomputing counts for the popular navigation paths that make up most traffic (Q200).

**Failure.**

- **Personalization service down:** unpersonalized ranking. Visible only as slightly worse relevance (Q199).
- **Facet aggregation slow:** return facet values without counts. A large capacity lever that users barely notice.
- **Index cluster degraded:** serve from the query result cache with `stale-if-error`; for a total outage, fall back to a database-backed category browse - poor, but not a blank page.
- **A shard is slow:** the whole query is slow, so per-shard timeouts with partial results (return 45 shards' worth and mark the response partial) plus adaptive replica selection. This is the single most important tail-latency control.
- **Reindex needed:** alias swap, with both indexes live during validation.

**Change one requirement.** *"Inventory must be exact in results, never showing a sold-out item."* Then read-time hydration becomes mandatory (as designed) and I would additionally take a reservation-style approach at the point of add-to-cart, accepting that search results are candidates and the authoritative check happens later - because filtering 500 million documents against real-time inventory at query time is not achievable, and pretending otherwise is the mistake. *"Sub-50 ms search."* Then the scatter-gather must shrink: aggressive routing, fewer shards, a smaller searchable subset, and a much higher cache hit ratio - and I would question whether the 50 ms is a real requirement or a preference.

---

### S17. Payments and a ledger with exact balances (Q247)

**Clarify and cut.** What operations? (Authorize and capture card payments, transfers between internal accounts, refunds, and payouts.) Must balances be exact? (Yes - this is the defining requirement.) Multi-currency? (Yes, no cross-currency conversion inside a single transfer.) Do we hold funds? (Yes, internal wallet balances.) I will design the ledger, the idempotency and state machine for external payments, and reconciliation; I will not design fraud scoring, chargeback workflow or the PSP integration details beyond their contract.

**Targets.** **Correctness above availability**: no money created or destroyed, ever, and the ledger must balance to zero at all times. Authorization p99 under 2 seconds (bounded by the PSP). Availability 99.95 percent for payment initiation, with a defined behavior when the PSP is unavailable. Every external movement reconciled daily with zero unexplained differences.

**Estimate.**

```
Volume:     5M payments/day → 58/s avg, ~200/s peak. Small.
Ledger:     double-entry, so 2+ entries per movement; with fees and taxes, ~6 entries
            → 30M entries/day → 350/s avg, ~1,200/s peak
Storage:    30M entries/day x 200 B = 6 GB/day → 2.2 TB/year, retained 7-10 years
            → 20 TB, time-partitioned, immutable, tiered
Balances:   10M accounts. Balance = sum of entries, so it must be materialized
            (summing 7 years of entries per read is not viable)
Contention: a merchant settlement account may receive 200 entries/s → hot row
```

State the conclusion: **throughput is trivial; the entire difficulty is correctness under retries, partial failures and hot accounts.**

**API.**

```
POST /v1/payments          {amount_minor, currency, source, destination, ...}
                           Idempotency-Key: <client-generated, required>
                           → 201 {payment_id, status: "PENDING"|"AUTHORIZED"}
                           → 409 if same key with a different body
POST /v1/payments/{id}/capture   {amount_minor?}   Idempotency-Key
POST /v1/refunds           {payment_id, amount_minor}  Idempotency-Key
GET  /v1/accounts/{id}/balance   → {available_minor, pending_minor, as_of}
GET  /v1/accounts/{id}/entries?cursor=...
```

Money is always an **integer minor unit plus an ISO currency code** - never a float, never a decimal string parsed loosely. Idempotency keys are client-generated, stored transactionally with the effect, and retained for the dispute window (Q35, Q123).

**Data.**

```
accounts(id, owner, currency, type)              -- type: user_wallet, merchant, fee, psp_clearing
entries(id, txn_id, account_id, currency, amount_minor /* signed */, created_at)
    PK (txn_id, account_id) — immutable, append-only, time-partitioned
    CHECK: per txn_id, SUM(amount_minor) = 0 per currency        ← the core invariant
transactions(txn_id, type, external_ref, status, created_at)
balances(account_id, currency, available_minor, pending_minor, version, last_entry_id)
payments(payment_id, idempotency_key UNIQUE, state, psp_ref, amount, ...)
```

**Double-entry is the design.** Every movement is a set of entries summing to zero, so "money was created" becomes structurally impossible rather than a thing you check for. The global invariant (total assets equal total liabilities) becomes a *local* one enforced per transaction - which is the key move that keeps the strong-consistency boundary small (`answers.md` Q120).

**Balances are materialized** in the same transaction as the entries, with a version column. So `balances` is a cache with a proof: it can be recomputed from `entries` at any time, and a nightly job does exactly that and alarms on any difference.

**Design.**

```
Client ──▶ Payment API
              ├─ idempotency check (unique constraint, same txn)
              ├─ authorization + limits
              ├─ state machine: PENDING → AUTHORIZED → CAPTURED → SETTLED
              │                      └──▶ FAILED / EXPIRED
              ├─ ledger write (entries + balance update, ONE transaction)
              └─ outbox ──▶ Kafka ──▶ [notifications, analytics, reporting]

              PSP call: separate, retriable, keyed on derived idempotency key
                        with a state-reconciliation poll for unknown outcomes
```

**The hard part is the boundary between our transaction and the PSP's.** There is no distributed transaction available (Q121-122), so:

1. Write the intent (`PENDING`) and commit. Now we have a durable record before any external call.
2. Call the PSP with a **deterministic idempotency key derived from our payment id** (Q38), so any retry maps to one PSP operation.
3. On a **known** outcome, record it and write the ledger entries.
4. On an **unknown** outcome (timeout, connection failure), do **not** guess. Leave the payment in a `PENDING_UNKNOWN` state and let a reconciler poll the PSP for the operation's status by our key. This is the single most important design decision: an unknown outcome must never be resolved by assumption, because both assumptions produce money errors.
5. A **daily reconciliation** against the PSP's settlement file is the authoritative control, and any unexplained difference is a P1 (Q234's spirit).

**Hot accounts** (a merchant settlement account) are handled by **entry batching**: individual entries are always written, but the balance update is aggregated - either by batching entries into a single balance update per short window, or by sharding the balance into sub-balances summed on read (Q192, design B). The entries remain exact; only the materialized balance's update path is optimized.

**Scale.** Shard by `account_id` for balances and by `txn_id` for entries, but note that a transfer touches two accounts, which may be on different shards. Two options: co-locate all accounts of one tenant/currency on a shard so most transfers are local, or accept a two-phase saga for cross-shard transfers with a pending state. I would start **unsharded** - 1,200 entries/second is well within one PostgreSQL primary - and say so, because sharding a ledger is a project that should be deferred as long as possible (Q148).

**Failure.**

- **PSP unavailable:** payment initiation returns a clear "temporarily unavailable" rather than queueing silently. Queueing a payment the user thinks succeeded is worse than an honest error.
- **Our database unavailable:** payments stop. Correct behavior - do not accept money movements you cannot record.
- **A crash between PSP success and ledger write:** the reconciler finds it. This is why the intent is written first and why reconciliation is mandatory rather than a nicety.
- **A bug that writes unbalanced entries:** prevented by a database-level constraint, not by code review.
- **Duplicate charge:** prevented at three layers - client idempotency key, unique constraint in the same transaction, and derived PSP key (S3).

**Change one requirement.** *"Support cross-currency transfers."* Then a transfer becomes two balanced transactions plus an FX position, with a rate captured at a specific instant and an explicit FX gain/loss account - and the "sum to zero" invariant becomes per-currency, which it already is in this schema. *"Real-time balances across 5 regions."* Then either a single writer per account with global reads (my recommendation - accounts have a natural home) or a hard conversation about the fact that a globally-consistent balance requires cross-region coordination on every write (Q132, Q177).

---

### S18. Ride matching with driver location ingestion (Q248)

**Clarify and cut.** Scale? (2 million active drivers, 500,000 concurrent rides at peak, one metro at a time - matching is inherently local.) Location update frequency? (Every 4 seconds while online.) Must matching be optimal or good? (Good and fast; a 2-second match beats an optimal 20-second one.) I will design location ingestion, geospatial matching, the trip lifecycle and dispatch; I will not design pricing, routing/ETA models or driver payouts.

**Targets.** Location ingest availability 99.99 percent and lossy-tolerant (dropping one update is fine); match latency p99 under 3 seconds from request to driver offer; trip state transitions durable and exactly-once-effect; trip lifecycle availability 99.99 percent (a ride in progress must never break).

**Estimate.**

```
Location:   2M drivers / 4 s = 500,000 updates/s        ← the dominant write load
            per update ~100 B → 50 MB/s ingest, 4.3 TB/day if all retained
            → do NOT retain all of it in a transactional store
Current:    2M driver current positions x 200 B = 400 MB → fits in memory, sharded by geo
Trips:      assume 10M trips/day → 115/s avg, ~400/s peak. Small.
            each trip has ~10 state transitions → 4,000/s peak of durable writes
Matching:   400 requests/s peak; each searches a radius containing maybe 50-200 drivers
Geo index:  per-metro; 100 metros; the largest has 200,000 concurrent drivers
```

The shape to state: **two workloads with opposite requirements sharing one system.** Location is a 500,000/second lossy firehose; trips are a 400/second durable state machine. They must not share infrastructure, and separating them is the primary design decision.

**API.**

```
# Driver
POST /v1/drivers/location   {lat, lon, heading, speed, ts}    # UDP-like semantics, batched
POST /v1/drivers/status     {status: ONLINE|OFFLINE|ON_TRIP}
POST /v1/offers/{id}/accept                                   Idempotency-Key

# Rider
POST /v1/rides              {pickup, dropoff, product}        Idempotency-Key
                            → 201 {ride_id, status: SEARCHING}
GET  /v1/rides/{id}         → state + assigned driver + live position
                            (or SSE stream for live updates)
```

**Data.**

```
Location (ephemeral):   Redis per metro — geospatial index (GEOADD / H3 cell buckets)
                        driver:{id} → {lat, lon, ts, status} with 30 s TTL
Location (history):     Kafka → object storage (Parquet, partitioned by day/metro)
Trips (durable):        PostgreSQL — rides, offers, state transitions, sharded by metro
Matching state:         in-memory per matching shard, rebuilt from Redis on restart
```

**Design.**

```
Driver app ──batched──▶ Location ingest (stateless, regional)
                             ├─▶ Redis geo index (current position, per metro)   [hot path]
                             └─▶ Kafka ──▶ object storage (history, analytics)   [cold path]

Rider app ──▶ Ride service ──▶ Matching service (per metro shard)
                  │                  ├─ query geo index: candidates within radius
                  │                  ├─ filter: status, product, rating, recent rejections
                  │                  ├─ score: ETA (from a routing service), utilization
                  │                  └─ offer to top driver(s), with a timeout
                  ├─ trip state machine (PostgreSQL, durable)
                  └─ dispatch/notify ──▶ driver + rider (push/WebSocket)
```

Four decisions worth defending:

1. **Location is ephemeral and lossy by design.** Current position lives in Redis with a TTL, so a driver who disappears self-heals (the same pattern as presence, Q183). Losing a single update costs nothing; the next one arrives in 4 seconds. This is what makes 500,000 writes/second affordable - it is a cache, not a database.
2. **Geospatial indexing by cell, per metro.** Drivers are bucketed into H3 (or geohash) cells; a radius search reads the covering cells plus their neighbors. Sharding by metro is natural, gives perfect locality (matching never crosses metros), and bounds the largest shard at one city's driver population.
3. **Matching is a short-lived, in-memory optimization** over 50-200 candidates - a small problem. The scaling axis is metros, not drivers. Batched matching (collecting requests over a 1-2 second window and solving an assignment problem) produces materially better assignments than greedy first-come matching, and 1-2 seconds is within budget - a good trade to volunteer.
4. **The trip is the durable object and gets a proper state machine**: `SEARCHING → OFFERED → ACCEPTED → ARRIVING → IN_PROGRESS → COMPLETED`, with every transition idempotent on `(ride_id, transition)` and persisted before it is acted upon. An offer has a hard timeout so a non-responding driver cannot stall a rider.

**Scale.** Location ingest scales horizontally and is stateless; Redis scales by metro shard. Matching scales by metro; the largest metro is one shard's worth of work and can be sub-sharded by geographic region within the city if needed. Trips are low volume and can stay on a single partitioned relational store per region.

**Failure.**

- **Redis geo index lost:** matching degrades badly for ~4 seconds until drivers repopulate it with their next update. That self-healing property is why the TTL design is right, and it should be stated explicitly as a resilience feature.
- **Location ingest down:** existing trips continue (their state is in PostgreSQL); new matching degrades to stale positions, then fails. Riders see "no drivers available", which is honest.
- **Matching service down for one metro:** blast radius is one city (Q152) - which is the argument for per-metro sharding beyond mere performance.
- **A driver's app loses connectivity mid-trip:** the trip state is server-side and durable, so the trip does not break; the rider sees a stale position with an "as of" indicator (Q173).
- **Double assignment** (two riders matched to one driver): prevented by a conditional state transition on the driver's status - a compare-and-set, not a check-then-act.

**Change one requirement.** *"Match optimally across the whole city, considering future demand."* Then matching becomes a periodic global optimization rather than a per-request search, which raises match latency and requires a demand forecast - a legitimate trade that I would A/B test rather than assume. *"Location history must be exact and queryable per driver in real time."* Then the cold path becomes a real-time store (a time-series database partitioned by driver) and the cost multiplies, so I would ask what decision the query supports, because "exact and real-time" for 4.3 TB/day is a very expensive requirement.

---

### S19. Video upload, transcoding and streaming (Q249)

**Clarify and cut.** Scale? (100,000 uploads/day, 1 million concurrent viewers at peak.) Live or on-demand? (On-demand; I will note where live differs.) DRM required? (Yes for premium content, token-based access for the rest.) Adaptive bitrate? (Yes.) I will design upload, the transcoding pipeline, delivery and access control; I will not design the player, recommendations or the CMS.

**Targets.** Upload must be resumable and never lose a completed upload. Time from upload complete to playable: p50 under 5 minutes, p99 under 30 minutes, with a low-resolution rendition available first. Playback start p99 under 2 seconds; rebuffer ratio under 0.5 percent. Delivery availability 99.99 percent.

**Estimate.**

```
Uploads:    100,000/day, avg 500 MB → 50 TB/day ingested
            → 1.2 GB/s average ingest if smeared; peak 3-5x → direct-to-object-storage,
              never through the application tier
Transcode:  ~6 renditions (240p→1080p) x roughly 1x realtime per rendition on a GPU
            avg video 10 min → ~60 min of transcode work per upload
            100,000 x 60 min = 100,000 hours/day = 4,167 concurrent transcode hours
            → with GPU acceleration at ~8x realtime: ~520 concurrent GPU workers
            → this is the dominant cost centre                    ← state this
Storage:    source 50 TB/day + renditions ~1.5x source = 125 TB/day → 45 PB/year
            → aggressive lifecycle tiering is mandatory, not optional
Delivery:   1M concurrent x 3 Mbps avg = 3 Tbps egress (answers.md Q23)
            → CDN by arithmetic; origin sees 3 Tbps x (1 - hit ratio)
```

Two numbers dominate and should be said out loud: **transcoding is the compute bill (hundreds of GPUs) and egress is the money bill (3 Tbps)**. Everything else is detail.

**API.**

```
POST /v1/videos                    {title, ...} → {video_id, upload_url(s), upload_id}
PUT  <presigned multipart part URLs>            # direct to object storage
POST /v1/videos/{id}/complete      {parts:[{n,etag}]} → 202
GET  /v1/videos/{id}               → {status: UPLOADED|TRANSCODING|READY|FAILED,
                                      renditions:[...], playback_token_url}
GET  /v1/videos/{id}/playback      → {manifest_url (signed, short-lived), drm_license_url}
```

**Data.**

```
videos(id, owner, title, status, source_key, duration, created_at)
renditions(video_id, profile, key, bitrate, width, height, status)
jobs(id, video_id, profile, state, attempts, worker_lease, priority)
Object storage: /source/{video_id}/original
                /hls/{video_id}/{profile}/segment_*.ts + playlist.m3u8
                /dash/{video_id}/...
```

**Design.**

```
Client ──presigned multipart──▶ Object storage (source bucket)
                                     │ S3 event notification
                                     ▼
                               Ingest handler ── validate, probe (ffprobe), create jobs
                                     │
                                     ▼
                            Transcode job queue (priority: low-res first)
                                     │
                    ┌────────────────┴────────────────┐
                    ▼                                 ▼
            GPU worker pool (spot-heavy)      CPU workers (audio, thumbnails, captions)
                    │
                    ▼
            Renditions + HLS/DASH manifests ──▶ Object storage (delivery bucket)
                    │
                    ▼
            Packaging + encryption (CENC keys → DRM key service)
                    │
                    ▼
              CDN ──▶ Viewers (signed manifest URLs, short-lived)
```

Design decisions worth defending:

1. **Uploads go directly to object storage** with presigned multipart URLs, never through the application (Q56). Multipart gives resumability, per-part retry, and parallelism. The **S3 event notification is the authoritative completion signal**, so a client that dies before calling `complete` still gets its video processed - which is the failure mode that matters, since 500 MB mobile uploads fail often.
2. **Transcoding is a fan-out of independent jobs**, one per rendition, so they run in parallel and a single failure retries in isolation. **The lowest rendition is prioritized** so the video becomes playable in a minute or two while higher renditions arrive - the single biggest perceived-latency win.
3. **Segment-level parallelism** for long videos: split the source into chunks, transcode chunks in parallel, concatenate. This turns a 2-hour video from a 15-minute serial job into a 1-minute parallel one, at the cost of careful GOP-aligned splitting.
4. **Spot/preemptible GPUs** for the bulk of transcoding, with checkpointing at segment boundaries so a preemption loses seconds of work. This is where the cost saving is, and it is safe precisely because the work is chunked and idempotent.
5. **Delivery is entirely CDN**, with signed short-lived manifest URLs and per-segment tokens so a leaked URL expires. DRM (Widevine/FairPlay/PlayReady) for premium content via a licence service; token-based access for the rest.

**Scale.** Transcoding scales by worker count and is the elastic part - a queue absorbs the upload burst and workers drain it (Q164), so upload spikes become completion-time variance rather than failures. Delivery scales entirely at the CDN; origin capacity is `total_egress x (1 - hit_ratio)`, so per-title encoding and cache-friendly segment sizes are direct cost levers. Storage scales by lifecycle policy: source files to archive after processing, unpopular renditions deleted and regenerated on demand, popular ones kept hot.

**Failure.**

- **Transcode job fails:** retry with backoff; after N attempts, DLQ with an alert and the video marked `FAILED` with a user-visible reason. Never silently stuck.
- **Worker dies mid-job:** the lease expires, another worker picks it up; chunk-level idempotency means partial output is discarded or reused safely.
- **Object storage unavailable:** uploads and playback both stop. Mitigated by multi-region buckets for delivery, and by the CDN continuing to serve cached content - which for a video service means most viewers are unaffected.
- **CDN origin overload** (a viral video with a cold cache): origin shielding (a mid-tier cache), request collapsing at the edge, and pre-warming for scheduled releases.
- **Poison media** (a malformed file that crashes the transcoder): sandboxed workers, resource limits, an attempt cap, and a quarantine path - because user-supplied media is the most hostile input in this system.

**Change one requirement.** *"Live streaming."* Everything changes: ingest becomes RTMP/SRT with a persistent connection, transcoding becomes real-time with a hard latency budget (so no chunk parallelism), packaging becomes low-latency HLS/DASH with partial segments, and there is no queue to absorb bursts - capacity must be provisioned ahead of the event (Q98). Delivery is similar but with much shorter cache TTLs. *"Playback must start in under 500 ms."* Then I would pre-position the first segments at the edge, reduce segment duration, and use a lower initial bitrate with fast ramp-up - a player and packaging problem more than a backend one.

---

### S20. A metrics platform at 10 million data points per second (Q250)

**Clarify and cut.** 13-month retention at what resolution? (Raw for days, rollups thereafter.) Who queries it? (Dashboards, alerting, and ad-hoc investigation.) Multi-tenant across teams? (Yes, with per-team quotas.) Must alerting be part of it? (Yes - it is the highest-availability consumer.) I will design ingestion, storage, query and alerting; I will not design the agent's internals or the dashboard UI.

**Targets.** Ingestion availability 99.99 percent and lossy-tolerant at the margin (dropping 0.01 percent of samples is acceptable; dropping an alert is not). Ingest-to-queryable under 10 seconds at p99. Dashboard query p99 under 2 seconds for a 6-hour window, under 10 seconds for 30 days. Alert evaluation must not be blocked by dashboard queries.

**Estimate.**

```
Ingest:     10M samples/s
Storage:    raw sample ≈ 16 B naive (8 B ts + 8 B value)
            → 160 MB/s → 13.8 TB/day → 5 PB/year uncompressed
            with delta-of-delta + XOR compression at ~1.5 B/sample (answers.md Q207):
            → 15 MB/s → 1.3 TB/day raw tier
Retention:  raw 15 s for 14 days      = 18 TB
            1 min rollup for 90 days  = ~4.5 TB
            5 min rollup for 13 months= ~2.5 TB
            → ~25 TB total. Manageable.                    ← compression is the design
Series:     10M samples/s at a 15 s scrape interval = 150M active series
            at ~3 KB/series of index and in-memory chunk state = 450 GB of RAM
            → cardinality, not sample volume, is the binding constraint
Nodes:      shard by series hash; ~20-30 ingest/storage nodes with replication factor 2
```

Say the conclusion plainly: **sample volume is a compression problem (solved), and series cardinality is the real limit** (Q207). The platform's hardest job is protecting itself from its users' labels.

**API.**

```
POST /v1/write            (Prometheus remote-write / OTLP, snappy-compressed protobuf)
GET  /v1/query?query=...&time=...            (instant)
GET  /v1/query_range?query=...&start&end&step
POST /v1/rules            (alerting and recording rules, per team, as code)
```

**Data.**

```
Ingest node:  head block in memory (2 h), WAL on local disk
Persisted:    immutable time-bounded blocks (2 h → compacted to 2 h/1 d/1 w)
              per block: chunks (compressed samples) + index (label → series postings)
Object store: blocks older than the local retention, queried remotely
Rollups:      downsampled blocks (1 min, 5 min) written by a compactor
Metadata:     series index; per-tenant cardinality accounting
```

**Design.**

```
Agents ──remote-write──▶ Distributor (stateless)
                            ├─ authenticate, attribute to tenant
                            ├─ enforce cardinality + rate limits         ← critical
                            ├─ relabel/drop high-cardinality labels
                            └─ hash by (tenant, series) → Ingesters (RF=2)
                                        │
                                Ingester: head block + WAL
                                        │ every 2 h
                                        ▼
                                Object storage (immutable blocks)
                                        │
                                  Compactor ──▶ compaction + downsampling + retention
                                        │
Query ──▶ Query frontend (split, cache, queue by tenant)
              └─▶ Queriers ──┬─ Ingesters (recent data)
                             └─ Store gateway ──▶ object storage blocks (historical)

Alerting ──▶ Ruler (evaluates rules on its own capacity, separate from dashboards)
```

Five decisions worth defending:

1. **Write path and read path are separated by an immutable block boundary.** Ingesters hold only recent data in memory with a WAL for crash recovery; everything older is immutable files in object storage. This makes historical storage cheap and infinitely scalable, and makes the stateful part small.
2. **The distributor enforces cardinality**, because this is the only place it can be stopped before it costs anything. Per-tenant limits on active series, on new series creation rate, on labels per metric and on label-value length; relabelling rules that drop known-bad labels; and a **hard rejection with a clear error** rather than silent acceptance. A platform that accepts unbounded cardinality will be destroyed by a well-meaning team adding a `request_id` label.
3. **Replication factor 2 (or 3) across ingesters** with quorum writes, so an ingester crash loses nothing. Combined with the WAL, this is what makes "lossy-tolerant" apply only to the extreme margin.
4. **Alerting runs on separate capacity from dashboards**, with its own ingesters-read path and its own resource budget (Q155). An ad-hoc 30-day query must never delay alert evaluation - and this isolation is the single most important reliability property of a monitoring platform, since the platform's job is to tell you when things are broken.
5. **Query frontend splits, caches and queues.** Long-range queries are split by time interval, executed in parallel, and the per-interval results cached (historical intervals are immutable, so the cache hit ratio is excellent). Per-tenant query queues prevent one team's expensive query from starving others.

**Scale.** Ingest scales by adding ingesters (rehashing series, which is disruptive - so over-provision, Q145). Historical query scales by adding stateless queriers and store gateways. Storage scales with object storage, which is effectively unbounded. Retention and rollups are what keep cost flat as volume grows.

**Failure.**

- **Ingester dies:** replication means no loss; the WAL replays on restart. Its share of series is redistributed, which briefly raises memory on peers - so headroom matters.
- **Object storage slow:** recent-data queries and alerting are unaffected (they read from ingesters); historical queries degrade. Correct prioritization.
- **A cardinality bomb:** rejected at the distributor with a per-tenant alert naming the offending metric. Without this control, it is an outage.
- **The platform's own monitoring** must not depend on the platform - a small independent watchdog with its own storage, because a monitoring system that cannot report its own failure is a single point of failure for everything (Q149).
- **Query overload:** per-tenant queues, query cost limits, and a maximum series-touched limit that fails a query rather than the cluster.

**Change one requirement.** *"Support high-cardinality exploration - per-user, per-request metrics."* Then this is not a metrics problem; it is a tracing or event-analytics problem, and I would route it to a columnar event store rather than distorting the TSDB (Q207, Q236). Saying no to this, with the alternative named, is the right answer. *"Sub-second alerting."* Then rule evaluation must run on the ingest path (a streaming evaluation) rather than by querying, which is a significant addition and only worth it for a small set of critical rules.

---

### S21. A multi-tenant SaaS control plane (Q251)

**Clarify and cut.** How many tenants? (5,000 today, target 50,000; sizes spanning five orders of magnitude.) What does the control plane own? (Tenant lifecycle, provisioning, configuration, entitlements, and placement.) Is the data plane single-tenant or shared? (Both - pooled by default, siloed for enterprise.) I will design tenant lifecycle, placement and routing, configuration propagation and blast-radius control; I will not design billing or the product features themselves.

**Targets.** **The data plane must keep serving when the control plane is entirely down** (static stability - `answers.md` Q158) - this is the defining requirement. Provisioning a new tenant end to end under 5 minutes. Configuration change propagation under 60 seconds. Control plane availability 99.9 percent (lower than the data plane, deliberately, and that must be safe).

**Estimate.**

```
Tenants:    50,000 target. Size distribution ~Zipf: the top 20 tenants may be
            larger than the remaining 49,980 combined      ← the design constraint
Control:    tenant CRUD, config reads. Config reads dominate:
            if the data plane reads config per request, that is the whole traffic volume
            → config MUST be pushed and cached, never read per request
Provision:  50-200 new tenants/day → 2/hour. Trivial volume, high complexity
Data plane: pooled cells, each serving ~2,000 small tenants;
            50,000 / 2,000 = 25 cells, plus dedicated silos for large tenants
Config:     ~20 KB per tenant of effective configuration → 1 GB total, fully cacheable
```

**API.**

```
POST   /v1/tenants               {name, plan, region, ...} → 202 {tenant_id, provisioning_id}
GET    /v1/tenants/{id}          → {status, cell, plan, limits, features}
PATCH  /v1/tenants/{id}          {plan?, limits?, features?}
POST   /v1/tenants/{id}/suspend  |  /resume  |  /migrate {target_cell}
DELETE /v1/tenants/{id}          → soft delete, retention window, then purge
GET    /v1/tenants/{id}/config   → effective config (versioned, ETag)
```

**Data.**

```
tenants(id, name, plan, region, cell_id, status, created_at, deleted_at)
placements(tenant_id, cell_id, moved_at)          -- the directory (answers.md Q135)
entitlements(tenant_id, feature, enabled, limits_json, effective_from)
config_versions(tenant_id, version, payload, published_at)
provisioning_workflows(id, tenant_id, state, step, attempts, error)
cells(id, region, capacity, tenant_count, status)   -- pooled | dedicated
```

**Design.**

```
                      ┌──────────── Control plane (regional, 99.9%) ───────────┐
Admin/API ──▶ Tenant service ──▶ tenant/placement/entitlement stores           │
                  │                                                            │
                  ├──▶ Provisioning workflow engine (durable, idempotent steps) │
                  │        create schema/namespace → seed data → DNS →          │
                  │        secrets → search index → verify → mark ACTIVE        │
                  │                                                            │
                  └──▶ Config publisher ──▶ versioned config bundles ──────────┘
                                                       │ push / poll
        ┌──────────────────────────────────────────────┴───────────────┐
        ▼                                                              ▼
   Router (edge)                                            Data plane cells
   tenant → cell mapping,                                   (each: app + db + cache,
   cached, statically stable                                 local config cache)
```

Five decisions worth defending:

1. **Directory-based placement, not hash-based.** A tenant's cell is an explicit row, so any tenant can be placed anywhere, moved individually, or promoted from pooled to dedicated. This flexibility is the single most valuable property of a multi-tenant control plane, and hash-based placement forfeits it (Q135, Q142).
2. **Static stability is the architecture, not a feature.** The router and every cell cache their configuration and placement data locally with **no hard expiry on the failure path**: if the control plane is unreachable, they keep using the last known good state indefinitely and alert loudly (Q158). This is why the control plane can have a lower SLO than the data plane. The test I would state: if the control plane were deleted for an hour, every existing tenant would keep working perfectly, and only provisioning and configuration changes would stop.
3. **Provisioning is a durable workflow, not a request.** A dozen steps across several systems, each idempotent, each retried, with the whole thing resumable and inspectable (Q109, Q222). Partial provisioning is the normal failure and must be recoverable without manual database surgery.
4. **Cells bound the blast radius** (Q152). Each cell is an independent stack serving ~2,000 tenants; cells share nothing; deployments roll cell by cell. A bad release or a poison workload affects 4 percent of small tenants instead of all of them. Large tenants get their own cell, which is both isolation and a commercial feature.
5. **Configuration is versioned and pushed, with the effective config computed centrally.** Cells never compute entitlements from rules; they receive a resolved bundle with a version. This makes "what configuration is tenant X running" answerable, and makes rollback a matter of republishing an earlier version.

**Scale.** Cells scale by count, which is the whole point - growth is adding cells, not growing one. The control plane's data is tiny (1 GB of config for 50,000 tenants), so it never needs sharding. The load that would have scaled with traffic - config reads - has been designed out by pushing rather than pulling.

**Failure.**

- **Control plane down:** data plane unaffected (by design). Provisioning queues. Admin operations fail visibly.
- **Router's placement cache stale:** a recently migrated tenant might be routed to its old cell. Handled by the old cell returning a redirect during a migration window, rather than by requiring perfect cache coherence.
- **A cell fails:** 2,000 tenants affected; others fine. Recovery is cell-local, and the tenants can be evacuated to another cell using the same migration machinery used for promotion.
- **A tenant migration fails mid-flight:** the workflow is resumable and the placement flip is the single atomic cutover point, with the source kept intact until verification passes (the same shape as resharding, Q138).
- **A configuration mistake** applied to all tenants is the highest-probability serious incident: mitigated by publishing config as versioned bundles rolled out cell by cell with automatic rollback, exactly like code.

**Change one requirement.** *"Every tenant must be able to choose their own region for residency."* Then cells become region-scoped, the tenant directory must be globally replicated (it is small, so this is fine), and the control plane becomes global-with-regional-data-planes (Q176) - which is close to what this design already is, and worth pointing out. *"Tenants can be provisioned in under 10 seconds."* Then provisioning must not create infrastructure on demand: pre-warm a pool of empty tenant slots in each cell and allocate one, turning a multi-minute workflow into a row update.

---

### S22. Telecom-scale event ingestion at 500,000 events per second (Q252)

**Clarify and cut.** What are the events? (Network usage records - session start/stop, data volume, location - feeding billing and investigation.) "Billing-grade accuracy" means what exactly? (No event lost, no event double-counted, and the total must be reconcilable against the network elements' own counters.) Query needs? (Ad-hoc investigation over 90 days, plus daily billing aggregation.) I will design ingestion, deduplication, aggregation and the query path; I will not design rating/pricing logic or the network elements.

**Targets.** **Zero loss** for billable events - this dominates everything. Exactly-once *effect* in the billing aggregate. Ingest-to-queryable under 5 minutes. Billing aggregation complete and reconciled within 2 hours of period close. Ingestion availability 99.99 percent, and when it is unavailable, the network elements' own buffers must be able to cover the gap.

**Estimate.**

```
Ingest:      500,000 events/s, each ~400 B (identifiers, volumes, timestamps, cell id)
             → 200 MB/s → 17 TB/day raw                       ← the volume problem
Compressed:  columnar Parquet with sorted keys typically 8-12x → ~1.7 TB/day
             90-day hot: 150 TB; 7-year regulatory archive: ~4.4 PB in cold storage
Dedup:       need to detect duplicates across a window. At 500k/s with a 24 h window
             that is 43 x 10^9 keys — far too many for an exact in-memory set
             → dedup must be scoped, partitioned, and bounded (see Design)
Aggregation: per-subscriber-per-day rollups: 50M subscribers x ~20 rows = 1 x 10^9 rows/day
             → columnar, partitioned by day
Kafka:       200 MB/s x RF=3 = 600 MB/s of broker write; retention 7 days = 10 TB/broker set
```

The shape to state: **this is a throughput and correctness problem, not a latency problem.** Nothing here is user-facing at millisecond scale; everything is about not losing or double-counting a single record among 43 billion a day.

**API.** Machine-to-machine ingestion, batched:

```
POST /v1/events/batch          (protobuf, gzipped, up to 5,000 events)
  headers: X-Source-Id, X-Batch-Seq, Idempotency-Key
  → 202 {accepted: 5000, batch_id}
  → 429 with Retry-After under backpressure          ← sources must buffer, not drop
```

Every event carries a **source-assigned unique id** (`source_id + local_sequence + timestamp`) - this is non-negotiable and it is what makes deduplication possible at all. A source that cannot provide one cannot be made billing-grade.

**Data.**

```
Kafka: raw-events, partitioned by subscriber_id hash (256+ partitions)
Landing: object storage, Parquet, partitioned by (event_date, hour, partition)
Dedup state: per-partition RocksDB/state store keyed by event_id, TTL = dedup window
Aggregates: usage_daily(subscriber_id, date, service, bytes, sessions, ...)
            partitioned by date, columnar
Reconciliation: source_counters(source_id, window, event_count, byte_total)
```

**Design.**

```
Network elements ──batch, buffered locally──▶ Collector tier (stateless, multi-AZ)
                                                  ├─ authenticate source
                                                  ├─ schema validate (registry)
                                                  ├─ reject invalid → quarantine topic
                                                  └─▶ Kafka raw-events (acks=all, RF=3)
                                                            │
                                        ┌───────────────────┴─────────────────┐
                                        ▼                                     ▼
                              Dedup + enrich (stateful stream,        Raw archival sink
                              partitioned by subscriber)              (Parquet, immutable)
                                        │
                                        ▼
                              clean-events topic
                                        │
                        ┌───────────────┴───────────────┐
                        ▼                               ▼
              Aggregation (windowed,            Investigation store
              per subscriber per day)           (columnar, 90 days)
                        │
                        ▼
              Billing aggregates ──▶ reconciliation vs source counters ──▶ billing
```

Five decisions worth defending:

1. **Durability at the front door.** The collector writes to Kafka with `acks=all` and RF=3 before returning 202, so an accepted event is durable. And critically, **the collector applies backpressure (429) rather than dropping** - the network elements buffer locally, which is the property that lets us take the ingest tier down for maintenance without losing billable data. This inverts the usual "analytics events are best-effort" stance because these are money.
2. **Deduplication is bounded and partitioned.** Partitioning by `subscriber_id` means all of a subscriber's events land in one partition, so the dedup state is local (a RocksDB-backed keyed state store) rather than global. State is keyed on `event_id` with a TTL equal to the agreed dedup window (say 48 hours, from the sources' maximum retry horizon), which bounds memory to `partition_rate x window` rather than to all events ever. This is the answer to the 43-billion-key problem: never make dedup global.
3. **Exactly-once effect via idempotent aggregation, not via delivery guarantees.** The aggregation is expressed as an upsert keyed on `(subscriber_id, date, service)` computed from deduplicated events, with the stream processor's checkpointing making the state and the offsets atomic (Q112). Replaying a partition recomputes the same aggregate.
4. **Raw archival is independent of processing.** A separate sink writes every raw event to immutable Parquet regardless of what the processing pipeline does. That means any processing bug is recoverable by replay from the archive - which for a billing system is the difference between a bad week and a regulatory incident.
5. **Reconciliation is the control that makes "billing-grade" true.** Each source reports its own periodic counts and byte totals; the pipeline compares its own totals against them per window and alarms on any difference beyond a tiny tolerance. Without this, "no loss" is a hope. With it, loss is detected within one window and the gap can be re-requested from the source's buffer.

**Scale.** Everything partitions by `subscriber_id`: collectors are stateless, Kafka partitions set the parallelism ceiling (so over-provision - Q145), dedup and aggregation state scale with partitions, and the columnar store scales by day partitions. 500,000/second across 256 partitions is 2,000/second per partition, which is comfortable for a stateful operator.

**Failure.**

- **Collector tier down:** sources buffer and retry; 429s tell them to slow down. The design's key resilience property.
- **Kafka partition unavailable:** the collector fails that partition's writes and the source retries; nothing is acknowledged that is not durable.
- **Dedup state lost:** rebuild from the changelog topic; while rebuilding, that partition's processing pauses rather than passing duplicates through. Correctness over liveness, which is the right choice here.
- **A duplicate storm from a source replaying a day of events:** absorbed by dedup, and visible in the reconciliation counters as a discrepancy between events received and events accepted - which is exactly the signal you want.
- **A late-arriving batch after the billing window closed:** an explicit policy - a correction record applied to a restated aggregate, with an audit trail (Q204's late-data policy).

**Change one requirement.** *"Investigation queries must return in under a second over 90 days."* Then the columnar store needs pre-aggregation and careful sort keys, or a dedicated OLAP engine (ClickHouse/Druid) with the query patterns known in advance - and I would ask which queries, because "arbitrary sub-second over 150 TB" is a very different budget from "these six queries sub-second". *"Real-time balance enforcement - cut off a subscriber at their limit within seconds."* Then a low-latency path is needed alongside the billing path: an approximate running counter per subscriber updated from the stream, used for enforcement, reconciled against the exact aggregate - approximate for speed, exact for money (Q192).

---

### S23. An enterprise RAG platform for 50 business units (Q253)

**Clarify and cut.** Each unit has its own corpus with its own access rules - can a user in unit A ever see unit B's documents? (Only if explicitly shared; default deny.) Document-level or user-level permissions? (Document-level ACLs inherited from the source systems - SharePoint, Confluence, file shares.) Volume? (10 million documents total, growing, daily updates.) I will design ingestion, permission-aware retrieval, generation and evaluation; I will not design the chat UI or per-unit prompt tuning.

**Targets.** **Zero unauthorized disclosure** - this is the requirement that outranks all others, and a single leak ends the platform's adoption. Answer latency p95 under 6 seconds with streaming (TTFT under 1.5 s). Freshness: source change reflected within 1 hour; a *permission revocation* reflected within 5 minutes. Availability 99.9 percent, degradable to retrieval-only.

**Estimate.**

```
Documents:  10M, avg 8 chunks → 80M chunks/vectors             (answers.md Q216)
Vectors:    80M x 1024 dims x 4 B = 328 GB float32
            → quantized (int8/PQ) at 4-8x: 40-80 GB → fits a small cluster in memory
Updates:    2% of documents change daily = 200,000 docs → 1.6M chunks re-embedded/day
            at 1,000 embeddings/s = ~27 min. Fine.
Queries:    50 units x 500 users x 5 queries/day = 125,000/day → 1.5 QPS avg, ~8 peak
            → tiny. This is NOT a throughput problem.
Cost:       8,000 prompt + 500 completion tokens per query x 125,000/day
            → ~1.06 x 10^9 tokens/day. At frontier pricing this is the dominant cost
            → per-unit budgets and caching are mandatory (answers.md Q212)
```

Say it explicitly: **retrieval throughput is trivial; the hard problems are permission correctness, freshness of revocation, and cost.**

**API.**

```
POST /v1/ask
{ "question": "...", "unit": "finance", "conversation_id": "...", "filters": {...} }
→ SSE stream: token deltas, then citations, then usage
   citations: [{doc_id, title, url, chunk_id, score, last_modified}]

POST /v1/feedback  {message_id, rating, comment}
GET  /v1/corpora/{unit}/status  → {documents, chunks, last_sync, errors}
```

Citations are mandatory in the contract, not optional: an answer without sources is unverifiable, and in an enterprise setting unverifiable is unusable.

**Data.**

```
documents(id, unit, source_system, source_id, uri, title, version,
          content_hash, acl_snapshot, indexed_at, deleted_at)
chunks(id, document_id, ordinal, text, token_count, embedding_model_version)
vectors: ANN index, partitioned by unit, metadata {doc_id, unit, acl_key, updated_at}
keyword index: BM25 over the same chunks (for hybrid retrieval)
acl(document_id, principal_id, permission)     -- mirrored from source systems
conversations, messages, feedback, evaluations
```

**Design.**

```
Source systems ──connectors (incremental, webhook or cursor)──▶ Ingestion
   SharePoint,        │
   Confluence,        ├─ fetch content + ACLs together (never separately)
   file shares,       ├─ content hash → skip unchanged
   wikis              ├─ parse → chunk (structure-aware, with overlap)
                      ├─ embed (batched, model version recorded)
                      └─▶ vector index (per unit) + keyword index + manifest

Query ──▶ RAG service
            ├─ resolve caller's principals (user + groups) from the identity provider
            ├─ retrieve: hybrid (BM25 + vector), FILTERED by permission at query time
            ├─ post-filter: re-check ACLs against the source of truth for the top K
            ├─ rerank (cross-encoder over top 50 → top 8)
            ├─ assemble prompt (retrieved content marked as untrusted data)
            ├─ generate via the model gateway (budgets, caching, guardrails)
            └─ verify: citations resolve, groundedness check, then stream
```

Five decisions, and the first three are all about the same thing:

1. **Permissions are enforced at query time, twice.** The vector and keyword indexes carry ACL metadata so retrieval is *pre-filtered* to what the caller may see (which also keeps recall meaningful - post-filtering a top-50 down to three results is a quality disaster). Then the top candidates are **re-checked against the authoritative ACL store** before being placed in the prompt. Pre-filter for recall, post-check for correctness. Never bake a permission snapshot into the document and trust it (Q198, case 8).
2. **Content and ACLs are ingested together, atomically.** A document whose content is updated but whose ACL is stale is a disclosure waiting to happen. The connector fetches both, and the manifest records the ACL version alongside the content version.
3. **Revocation propagates in minutes, independently of re-indexing.** ACL changes come through a separate, high-priority path that updates the ACL store and the index metadata without re-embedding anything. This is why the 5-minute revocation target is achievable while the 1-hour content target is not - and separating them is the design insight. Deletions likewise take a fast path.
4. **Per-unit index partitioning.** Each business unit's vectors live in their own index partition, which gives isolation (a bug cannot cross units), independent rebuild, per-unit quotas, and residency options. It also makes filtered ANN cheap, since the unit filter is a partition selection rather than a predicate (Q217).
5. **Everything goes through the model gateway** (Q214): per-unit token budgets and cost attribution, caching (exact and prefix, with semantic caching scoped *within* a unit and permission scope, never across - Q215), guardrails, prompt versioning, and provider failover.

**Scale.** Query volume is small, so scaling is about corpus size and update throughput: ingestion workers scale horizontally per connector, embedding is a batched GPU or API workload, and the vector index scales by unit partition. The re-embedding cost of a model upgrade (80 million chunks) is the largest scheduled operation and must be planned as a build-into-new-index-and-swap (Q216).

**Failure.**

- **Generation unavailable:** degrade to **retrieval-only** - return the ranked passages with citations and no synthesized answer. Genuinely useful, and it means the platform is never fully down (Q224).
- **A connector fails:** that unit's corpus goes stale, visibly, on the status endpoint. Staleness is displayed, never hidden (Q173).
- **The ACL store is unavailable:** **fail closed.** Return no results rather than unfiltered results. This must be the tested default, because the alternative is a disclosure incident.
- **Recall regression** after an index or model change: caught by a monitored recall@k metric against a ground-truth set (Q217) and by the evaluation suite gating the change (Q221).
- **Prompt injection via document content:** retrieved text is framed as untrusted data, the system prompt is not modifiable by content, output guardrails check for instruction-following and for leakage of the prompt, and tool use is not available in this design at all - which is itself a mitigation.

**Change one requirement.** *"Users must be able to ask questions across all 50 units."* Then retrieval must span partitions with a per-unit permission filter, so the fanout grows and the permission logic becomes the bottleneck - workable, but I would insist on a **default-deny with explicit cross-unit sharing**, because "search everything" plus enterprise ACLs is where these systems leak. *"Answers must cite only approved sources and never be wrong."* The second half is not achievable; what I can offer is a restricted corpus, mandatory citations, a groundedness check that refuses to answer when evidence is weak, and a human review path for high-stakes categories (Q220) - and I would say so plainly rather than accept an impossible requirement.

---

### S24. An enterprise LLM gateway (Q254)

**Clarify and cut.** Who are the callers? (60 internal applications plus ad-hoc developer use.) Which providers? (Two commercial APIs plus one self-hosted open model.) Is prompt management in scope? (Yes - versioned prompts as artifacts.) Is this on the critical path of customer-facing systems? (Yes for some.) I will design routing, quotas, caching, safety, observability and cost attribution; I will not design individual application prompts or model fine-tuning.

**Targets.** Added latency p99 under 30 ms excluding the upstream call (so the gateway is invisible against a 2-second generation). Availability 99.99 percent - **higher than any provider**, achieved by failover. Cost attribution accurate to the request. Policy change propagation under 60 seconds. No PII leaves the network without an explicit, audited allowance.

**Estimate.**

```
Traffic:    60 apps, aggregate 200 requests/s peak (LLM traffic is low-QPS, high-latency)
Concurrency: 200 req/s x 4 s avg duration = 800 concurrent in-flight (Little's Law)
             → non-blocking IO mandatory; a thread-per-request model needs 800+ threads
Tokens:     avg 3,000 prompt + 400 completion = 3,400 tokens/request
            200/s x 3,400 = 680,000 tokens/s peak; ~20 x 10^9 tokens/day
            → at frontier pricing this is a very large monthly figure
            → caching and model tiering are cost levers worth millions, not percent
Cache:      exact+prefix hit ratio 15-25% typical; semantic adds 10-20% where enabled
            → a 30% overall hit ratio is a 30% cost reduction. This justifies the gateway alone
Logging:    200/s x (3,400 tokens x ~4 B) ≈ 2.7 MB/s of prompt/response text
            → 230 GB/day if fully retained → sampling + retention tiering required
```

**API.** Provider-agnostic, deliberately close to a familiar shape so migration is cheap:

```
POST /v1/chat/completions
{
  "model": "summarizer",              // LOGICAL name, mapped by the gateway
  "messages": [...],
  "prompt_ref": "order.summary.v7",   // optional: server-side prompt template
  "params": {...},
  "stream": true
}
headers: X-App-Id (from mTLS identity), X-Tenant-Id, X-Purpose

→ SSE stream, terminating with a usage frame:
   {"prompt_tokens":3102,"completion_tokens":380,"cached_tokens":2800,
    "provider":"vendor-a","model":"...","cost_micros":4210,"request_id":"..."}
```

The **logical model name** is the most important element in the contract: applications never name a provider model, so a deprecation, a price change, or a failover is a gateway configuration change rather than 60 application deploys.

**Data.**

```
logical_models(name, version, routing_policy, fallbacks[], params_defaults)
providers(id, endpoint, credentials_ref, rate_limits, health)
prompts(ref, version, template, owner, eval_score, approved_at)
policies(app_id|tenant_id, tpm, rpm, concurrency, monthly_budget, allowed_models,
         pii_policy, on_failure)
usage_events(request_id, app, tenant, purpose, model, provider, tokens, cost, latency,
             ttft, outcome, cache_status)          -- durable, the billing source
audit_log(request_id, prompt_hash, response_hash, guardrail_verdicts, principal)
cache: exact/normalized (Redis), semantic (vector index, scoped by tenant+policy)
```

**Design.**

```
App ──mTLS──▶ Gateway (stateless, non-blocking, multi-AZ)
                 1. authenticate app identity; resolve policy
                 2. input guardrails: PII detection/redaction, injection heuristics,
                    size limits                                    [fail closed]
                 3. resolve logical model → provider + concrete model + params
                 4. quota check: token bucket in tokens, concurrency slot   [pre-flight]
                 5. cache lookup: exact → normalized → semantic (if enabled for policy)
                 6. call provider (streaming), with hedging/failover on error or slowness
                 7. output guardrails: schema, safety, leakage        [may truncate stream]
                 8. meter: tokens, cost, latency, TTFT → usage_events
                 9. audit: hashed prompt/response + verdicts → append-only store
```

Six decisions worth defending:

1. **Non-blocking end to end.** 800 concurrent in-flight requests with 30-second tails makes any thread-per-request design untenable (Q210). The gateway is I/O-bound and must be built accordingly, with its own bulkheads per provider.
2. **Logical models with config-driven routing** - the property that makes everything else possible: failover (Q213), model tiering for cost, canarying a new model version, and surviving a provider deprecation without touching applications.
3. **Quotas denominated in tokens and concurrency, not requests** (Q212). A request-based limit is meaningless when one request can be 200x another, and concurrency is what actually causes queueing.
4. **Caching as a first-class cost mechanism.** Exact and normalized caching for everyone; provider prefix caching exploited by structuring prompts stable-content-first (often the single largest saving); semantic caching enabled per policy with a high threshold and **scoped by tenant and permission** - never shared across tenants (Q215).
5. **Guardrails at the boundary, uniformly.** PII redaction before data leaves the network is a compliance control that cannot be delegated to 60 teams. Output checks run in parallel with streaming, with the contract permitting a late terminal error (Q220).
6. **Metering is durable and is the billing source**, not a metrics side effect. Every request produces a usage event with app, tenant and *purpose*, so cost is attributable to a feature and a business owner - which is what makes cost conversations possible at all.

**Scale.** Stateless and horizontally scalable; the state (quota buckets, caches) is in Redis with the same lease technique as S14 for the hot path. The gateway's own capacity is set by concurrency, not QPS.

**Failure.** The gateway is a dependency of 60 applications, so its failure modes matter more than its features:

- **A provider is slow or down:** circuit breaker per provider, automatic failover to the fallback list, and hedging for idempotent requests. This is how 99.99 percent is achieved on top of 99.9 percent providers (Q224).
- **All providers down:** return a structured, retryable error promptly. Applications must have their own fallbacks - the gateway cannot invent an answer, and pretending otherwise would be worse.
- **Redis (quota/cache) down:** **fail open on quotas** with a conservative local allowance, and skip the cache. Availability of 60 applications outranks precise quota enforcement - declared per policy, and tested (S14).
- **Control plane / config store down:** last known good configuration used indefinitely (Q158). A gateway that cannot serve because it cannot read its config would be an unforgivable design.
- **A guardrail service down:** this is the interesting one, and the answer must be **per policy**: fail closed for high-risk categories (customer-facing, regulated), fail open with an audit flag for low-risk internal use. Making that an explicit policy decision rather than an accident is the point.
- **A bad prompt version** rolled out widely: prompts are versioned artifacts with evaluation gates and canary rollout, and there is a one-click revert.

**Change one requirement.** *"All inference must be on self-hosted models - no external providers."* Then the gateway's routing becomes an internal load balancer over GPU pools, and the hard problems shift to GPU capacity, batching and cold starts (Q223) - the gateway's role grows to include queueing and admission control against a fixed, expensive capacity. *"Sub-second p99 total latency."* Then most generation work must move to small models or be cached, because a frontier model cannot meet that - so I would reframe it as a per-use-case latency budget with model tiering, and challenge whether the p99 requirement is real.

---

### S25. An agent platform with human approval checkpoints (Q255)

**Clarify and cut.** What do agents do? (Multi-step workflows against internal systems - creating tickets, updating records, running queries, sending communications.) Who authorizes the actions? (The requesting user; the agent acts on their behalf, never with its own elevated identity.) How many tools? (Around 40, across 12 internal systems.) Are workflows long-running? (Minutes to days, given human approvals.) I will design the execution model, tool contracts, state, approvals, safety and observability; I will not design individual agent prompts.

**Targets.** **No action is ever taken outside the requesting user's authority** - the security requirement that dominates. No side effect executed twice, ever. A run must survive process restarts and resume exactly. Every action auditable with its full reasoning chain. Bounded cost per run - no unbounded loops.

**Estimate.**

```
Runs:       2,000 runs/day → 0.02/s. Throughput is irrelevant.
Steps:      avg 8 steps/run, p99 25 (hard cap)
            → 16,000 model calls + ~10,000 tool calls per day
Duration:   median 90 s; with approvals, p99 measured in hours or days
            → concurrent in-flight runs can be thousands, mostly WAITING
            → the execution model must not hold resources while waiting  ← key insight
Cost:       8 steps x ~6,000 tokens = 48,000 tokens/run x 2,000 = 96M tokens/day
            → per-run budget caps are essential (a looping agent is expensive fast)
State:      ~50 KB of step history per run x 2,000/day, retained 1 year = 36 GB. Trivial.
```

The design-shaping observation: **thousands of concurrent runs, almost all of them idle, waiting on a human or a slow tool.** That forbids any design where a run occupies a thread or a process, and mandates a durable, event-driven state machine.

**API.**

```
POST /v1/runs         {agent: "onboarding-assistant", input: {...}, on_behalf_of: <user>}
                      Idempotency-Key
                      → 202 {run_id, status: "RUNNING"}
GET  /v1/runs/{id}    → {status, steps:[{n, type, tool, input, output, tokens, ts}],
                         pending_approval?, cost_micros}
GET  /v1/runs/{id}/events    (SSE: live step stream)
POST /v1/runs/{id}/approvals/{approval_id}   {decision: approve|reject, comment}
POST /v1/runs/{id}/cancel
```

**Data.**

```
runs(id, agent, agent_version, principal, status, step_count, tokens_used,
     cost_micros, budget_micros, started_at, deadline_at, idempotency_key UNIQUE)
steps(run_id, n, type, model_call|tool_call, input_json, output_json,
      tokens, latency_ms, created_at)              -- append-only
tool_calls(run_id, n, tool, idempotency_key UNIQUE, request, response, status)
approvals(id, run_id, step_n, action_summary, risk_class, requested_at,
          decided_by, decision, decided_at, expires_at)
tools(name, version, schema, timeout_ms, risk_class, required_scopes, rate_limit)
```

**Design.**

```
POST /runs ──▶ Run service ──▶ durable run record ──▶ work queue
                                                          │
                        ┌─────────────────────────────────┘
                        ▼
                Step executor (stateless worker, leased)
                  ├─ load run state
                  ├─ check budget/step/deadline limits         [terminate if exceeded]
                  ├─ call model via LLM gateway (S24) → next action
                  ├─ if tool call:
                  │     ├─ validate against tool schema
                  │     ├─ authorize: user's scopes ∩ tool's required scopes   ← critical
                  │     ├─ if risk_class = HIGH → create approval, status=WAITING, EXIT
                  │     └─ execute with idempotency key (run_id, step_n)
                  ├─ append step, persist state
                  └─ re-enqueue for the next step (or terminate)

Approval granted ──▶ event ──▶ re-enqueue run at the paused step
```

Six decisions worth defending:

1. **The run is a durable state machine, and the worker is stateless.** Each step is: load state, do one thing, persist, re-enqueue. A worker crash loses at most one in-flight step, which is retried. A run waiting for approval occupies **no compute at all** - it is a row with `status = WAITING`. This is the only design that supports thousands of day-long runs (Q222).
2. **Authorization is the user's, not the agent's.** The agent executes tools with the requesting user's scopes, intersected with the agent's own allowlist. There is no service account with broad privileges - because an agent with elevated privileges plus a prompt-injection vector is a privilege-escalation machine, and this is the single most important property in the design.
3. **Every tool call is idempotent on `(run_id, step_n)`**, enforced by a unique constraint (Q123). Without this, "resume after crash" means "send the email twice" or "charge twice". Tools that cannot be made idempotent are classified as HIGH risk and always require approval.
4. **Hard limits, always.** Maximum steps, maximum tokens, maximum wall-clock, maximum spend per run - checked before every step, with a defined terminal state when exceeded. An agent without these will loop, and the loop is invisible until the bill or the audit log reveals it.
5. **Risk-classified tools drive approvals.** Read-only tools execute freely. Reversible writes execute with audit. Irreversible or externally-visible actions (sending communications, spending money, deleting data, changing production configuration) require a **human approval** with the proposed action, its inputs and the agent's reasoning presented for review. Approvals expire, and expiry terminates the run rather than leaving it hanging.
6. **Untrusted content is untrusted at every step.** Tool outputs and retrieved documents are data, never instructions; code execution is sandboxed with no credentials and no network egress; and the reasoning chain is logged so an injection attempt is investigable after the fact.

**Scale.** Throughput is negligible; the scaling axis is *concurrent waiting runs*, which is a row count. Workers scale with active step execution only. The LLM gateway (S24) absorbs the model-call concurrency.

**Failure.**

- **Worker crash mid-step:** the lease expires, another worker resumes from the last persisted step. Idempotency keys make a partially-executed tool call safe to retry.
- **A tool is down:** per-tool circuit breaker and timeout; the step fails with a typed error that the agent can observe and route around, or the run terminates with a clear reason. A hung tool must not hang a run - hence per-tool timeouts.
- **The model produces an invalid tool call:** schema validation rejects it, the error is fed back once, and a second failure terminates the step rather than looping.
- **An approval is never answered:** expiry, then a terminal state and a notification. No zombie runs.
- **A misbehaving agent:** per-agent and per-tool kill switches, plus the ability to suspend an agent version instantly without a deploy.
- **A prompt-injection-driven malicious action:** blocked by the scope intersection (it cannot exceed the user's authority), by risk-class approvals (it cannot do anything irreversible unattended), and detected by the audit trail. **Defense in depth is the answer here, not a filter** - and saying that is the point.

**Change one requirement.** *"No human approvals - agents must act autonomously."* Then the entire safety argument rests on scope restriction and reversibility, so I would insist on: only reversible actions available to autonomous agents, a compensating action defined for every tool, a spend cap, anomaly detection on action volume, and a mandatory dry-run mode with a diff for anything touching production data. And I would document the residual risk explicitly rather than let it be implicit. *"Runs must complete in under 10 seconds."* Then the approval mechanism is incompatible with the requirement, so the workflow must be split: a fast autonomous path for low-risk actions and an asynchronous path for anything needing approval.

---

## Part C - Leadership situations

### S26. You are defending the boring design

> In a design review, a senior engineer proposes event sourcing with CQRS, Kafka, a service mesh and multi-region active-active for a new internal product with 40 users and a two-quarter deadline. The room is excited. You think it is wrong. The engineer is respected and will be doing the work.

**Clarify.** Before opposing anything, I ask questions that make the requirements visible: what is the expected user count in year two? What is the write volume? Which invariants need strong consistency? What is the availability target the business has actually asked for, and what does an hour of downtime cost? Who operates this at 3 a.m.? What is the team's existing experience with each component? Which of these choices would be hard to reverse in six months?

**Isolate.** The disagreement is rarely about technology; it is about which risk we are optimizing against. The engineer is optimizing against *future scale*. I am optimizing against *delivery risk and operational cost*, because for 40 users and two quarters, the probability of not shipping vastly exceeds the probability of hitting a scale ceiling. And several of these choices - event sourcing especially - are extremely expensive to reverse (`answers.md` Q60), which is the asymmetry that matters.

**Decide.** I will not win this by asserting seniority, and I do not want to - if I overrule and the project struggles, the team learns that decisions come from authority rather than reasoning. So I reframe it as a **reversibility and cost question with numbers**, and I concede the parts where the engineer is right.

**Execute.**

1. **Concede genuinely.** A durable event log for integration and audit is a good idea and I would keep it. Saying so first makes the rest a conversation rather than a defeat.
2. **Put the arithmetic on the board.** 40 users, whatever the write volume is - a single PostgreSQL instance is three orders of magnitude from its ceiling (Q148). That is not an opinion.
3. **Price the operational cost**: five new components, each with backup, monitoring, upgrade, security and on-call obligations (Q57), against a team of four. Name the person who will be paged.
4. **Sort the decisions by reversibility.** Adding Kafka later is a week. Removing event sourcing later is a rewrite. So the default should be the reversible choice, and the burden of proof falls on the irreversible ones.
5. **Offer a concrete alternative with the seams preserved**: a modular monolith on PostgreSQL, with an outbox so events exist from day one, and clear module boundaries so extraction is possible. The engineer's architecture remains *reachable*.
6. **Agree the trigger.** "We revisit when write volume exceeds X or when a second team needs to consume this." Now the decision is not "no", it is "not yet, and here is the condition".

**Reflect.** What makes this work is separating the engineer's judgement from the decision - they may be entirely right about where the system ends up and wrong about when. Afterwards I would write the decision down as an ADR with the trigger conditions, so the next person does not relitigate it, and so that if I was wrong the record shows why. I would also check my own bias: the boring answer is right often enough that I should be suspicious of how comfortable I am giving it, and I would ask a peer to argue the other side before the review, not after.

> *Hook: a design review where you argued for less, and how it turned out.*

---

### S27. Your design was overruled and it is going badly

> Six months ago you argued against a design decision - a shared database across three new services - and were overruled by a peer architect with more organizational support. It is now causing exactly the coupling problems you predicted. Two teams are blocked on each other weekly. You are in a meeting where the topic comes up.

**Clarify.** Before saying anything, I want facts rather than vindication: how many incidents or blocked releases are attributable to this, with dates? What is the measured cost - engineering days lost, releases delayed? What has changed since the original decision (team size, volume, roadmap) that would change the analysis? And critically: what would it cost to change now, and what would it cost to make the current design work better?

**Isolate.** There are two separate problems and they must not be conflated. The technical problem is coupling through a shared schema, which has known remedies at several price points. The organizational problem is that being right retrospectively is worth nothing, and if I position this as "I told you so", I will win the argument and lose the ability to influence the next one. The peer architect is not the problem; the decision process is.

**Decide.** I say nothing about the original disagreement. I bring evidence about the present cost and options for the future, and I let the data make the argument that I made unsuccessfully in prose six months ago. If it is asked directly whether this was foreseen, I answer honestly and briefly and move on.

**Execute.**

1. **Quantify the current cost** in the currency the business uses: releases delayed, hours of cross-team coordination per sprint, incidents caused by a schema change. "Two teams blocked weekly" becomes "roughly 20 engineering days a quarter plus three delayed releases".
2. **Present options with prices, not a single recommendation**: (a) keep the shared database and add discipline - schema ownership per table, expand-contract migrations enforced in CI, a shared-change review process (cheap, weeks, partial relief); (b) split the schema into per-service ownership within one database instance, with no cross-schema queries (medium); (c) full separation with an API or event contract between them (expensive, a quarter, full relief).
3. **Recommend the middle option** in most cases, because it removes most of the coupling for a fraction of the cost of full separation, and it is a step toward (c) rather than a detour.
4. **Give the peer architect a way to agree without losing face.** Frame it as new evidence, which is true: six months of operational data did not exist when the decision was made. "The decision was reasonable with what we knew; here is what we know now."
5. **Fix the process, separately and later.** Propose that reversibility and a review trigger be recorded in every significant architecture decision, so the next contested call has a built-in checkpoint rather than requiring someone to reopen it.

**Reflect.** The lesson I actually took is about how I argued the first time: I made a correct architectural case and lost because I did not attach a cost or a measurable prediction to it. Now I write predictions down - "if we do this, I expect cross-team coordination cost to rise; we should measure blocked releases" - because a prediction that can be checked converts a disagreement into an experiment, and it makes the eventual conversation about data rather than about who was right. I would also be candid that the second-order damage of relitigating decisions is real, and that I would rather have a team that decides quickly and revisits on evidence than one that is slow and always correct.

> *Hook: a decision you lost, what it cost, and how you handled being right later.*

---

### S28. The cost mandate conflicts with the reliability target

> The CFO has mandated a 40 percent infrastructure cost reduction this year. Your platform's SLO is 99.99 percent, contractually committed to three enterprise customers. Your engineering manager has already promised the finance team that "there will be no impact on reliability". You have been asked to deliver the plan.

**Clarify.** What is the 40 percent measured against - total spend, or spend growth? Is the target for the fiscal year or by year end? Which cost lines are in scope (production only, or all environments, or vendor contracts too)? Are the three contracts' SLAs financially backed, and what are the penalties? Is there flexibility on *when* the 40 percent lands? And, importantly, who owns the decision if the two goals genuinely conflict?

**Isolate.** The premise "no impact on reliability" is doing a lot of work and needs to be tested rather than accepted. In my experience 25-30 percent of a mature bill is genuinely recoverable with no reliability impact - waste, commercial levers, retention, right-sizing (`answers.md` Q240). The last 10-15 percent is where the trade-offs live. So the honest position is: most of this is achievable safely, and the remainder requires a decision that is not mine to make alone.

**Decide.** I deliver a plan in three tranches, with the reliability implication of each stated explicitly, and I make the conflict visible early rather than discovering it in month eight. I will not quietly cut redundancy to hit a number and let the SLO fail later - that converts a budget problem into an incident and a contractual liability.

**Execute.**

1. **Get attribution first.** Cost per service, per environment, per customer. Nothing can be decided without it, and it usually finds surprises worth several percent immediately.
2. **Tranche 1 - zero reliability impact, ~20-25 percent.** Idle and orphaned resources, non-production environments scheduled off outside working hours, savings plans and reserved capacity for the steady baseline, spot for CI and batch, log and metric retention reduction, storage tiering, and renegotiation of the two largest vendor contracts. Deliverable in a quarter, mostly configuration and commercial work.
3. **Tranche 2 - engineering effort, no reliability impact, ~8-12 percent.** Cross-AZ and egress traffic reduction, cache hit ratio improvements, expensive query fixes, service consolidation, removing a datastore. Weeks of engineering each, so it needs roadmap space - which is itself a cost the finance team should see.
4. **Tranche 3 - requires an explicit decision.** Reducing redundancy below N+1, dropping the warm standby region, cutting observability, or renegotiating the SLO with the three customers. **I present this as a decision with named consequences and a price**, not as an engineering option: "removing the standby saves X per month and changes our RTO from 20 minutes to 6 hours, which breaches two contracts."
5. **Correct the promise, carefully and early.** I would speak to my manager before the plan is presented, privately, with the numbers: "we can deliver 30 percent with no reliability impact and I can show you exactly how; the last 10 requires either more time or a decision about the SLO. I would rather we present that now than in Q4." Letting an unachievable promise stand is a disservice to them.
6. **Instrument it.** Monthly cost-per-service reporting and a cost-per-transaction metric, so the reduction is visible and so regressions are caught. Otherwise the savings evaporate within two quarters.

**Reflect.** The systemic issue is that cost had no owner and no visibility, which is why 40 percent was recoverable in the first place - and the durable fix is not a project but a practice: cost attribution per team, a cost line in design reviews (Q237), and a quarterly efficiency review. On the leadership side, my job here is to convert an unbounded mandate into a menu with prices and to make sure the trade-off decision is made by the person accountable for both budget and contracts, with the consequences written down. What I will not do is accept an unachievable target silently and let the shortfall surface as an outage.

> *Hook: a cost programme you led, the number you hit, and the trade-off you escalated.*

---

### S29. You have to kill a system that people are proud of

> A platform team spent 18 months building an internal service mesh and developer platform. It has three users. Two other teams built their own alternatives. The platform's two engineers are excellent and deeply invested. You have been asked to decide its future.

**Clarify.** Why does it have three users - is it not useful, not usable, not marketed, or was the need overestimated? What do the two alternatives do that this does not? What would it cost to make it succeed - is this a distribution problem or a product problem? What is the ongoing cost of keeping it (the two engineers, plus the infrastructure, plus the support burden on its three users)? What would the three users do if it were withdrawn? And what would these two engineers work on instead - is there something more valuable?

**Isolate.** The failure is almost never technical. Internal platforms fail for two reasons: they solved a problem the organization did not feel acutely, or they required teams to adopt something without making adoption obviously cheaper than the alternative. The existence of two competing home-grown alternatives is the diagnostic - it means the need was real and this solution was not the path of least resistance. That is a product and distribution failure, and it is usually a failure of how the work was commissioned rather than how it was built.

**Decide.** I would decide based on whether the *need* is real and whether *this* is the best vehicle for it. Most often the answer is: consolidate rather than kill - keep the parts that solve a real problem, adopt whichever alternative has traction, and redeploy the engineers onto something with demand. And I would make the decision quickly, because a platform with three users and no clear future is demoralizing for everyone, and slow ambiguity is crueller than a clear decision.

**Execute.**

1. **Talk to the two engineers first, before any wider discussion.** They will know more about why adoption failed than anyone, and hearing it from me rather than through a reorganization is the minimum they are owed. I would ask, genuinely: what would you do if this were your call?
2. **Talk to the non-adopters.** Ten conversations with teams that chose something else is the most valuable data available, and it usually produces a clear answer within a week.
3. **Separate the decision into parts.** Rarely is the whole thing worthless: perhaps the mesh is unnecessary but the CI templates are excellent, or the observability integration is genuinely better than the alternatives. Preserve what works, name it, and move it somewhere it will be used.
4. **Decide and announce with reasoning, not euphemism.** "We are stopping investment in X because adoption showed the organization needs Y; here is what we are keeping, here is the migration path for the three users, and here is what the team is moving to." Vague language is read as a lack of confidence and everyone knows what it means anyway.
5. **Protect the people explicitly and visibly.** The failure is not theirs, and I would say that publicly and specifically - the requirement was inadequately validated before 18 months were committed, which is a leadership failure. Their next assignment should be visibly good, because how an organization treats people whose project is cancelled determines whether anyone takes an ambitious bet again.
6. **Support the three users properly** with a funded migration, not an abandonment. Otherwise the lesson the organization learns is that adopting an internal platform is risky, which poisons the next one.

**Reflect.** The systemic lesson is about how platform work is commissioned: 18 months with no adoption checkpoint should have been impossible. What I would change is to require internal platforms to have a named pilot team committed *before* the build, an adoption target at 3 and 6 months, and a stop condition agreed at the start - so cancellation is a pre-agreed outcome rather than a judgement on anybody. I would also apply the golden-path principle: an internal platform succeeds only when it is the easiest option, not merely the recommended one, and if teams are routing around it, the platform is wrong rather than the teams.

> *Hook: a system you decommissioned or did not build, and how you handled the people.*

---

### S30. Raising the design standard across teams you do not own

> You have been asked to improve architecture quality across eight teams in a 90-person engineering organization. You have no direct authority over any of them. Two team leads are excellent, four are competent and busy, and two are actively resistant to "architecture people".

**Clarify.** What problem is this actually solving - are we having incidents, missing deadlines, accumulating unmaintainable systems, or is it a perception issue? What evidence exists? What has been tried before, and why did it fail (this determines what the resistant leads are resistant *to*)? What authority do I have - can I gate anything, or only advise? What does the sponsor consider success in six months?

**Isolate.** Standards imposed from outside fail, reliably, for a structural reason: the person writing the standard does not pay the cost of following it. Anything that reads as a review board, a checklist gate, or a document to be complied with will be routed around, and the two resistant leads will be proved right in front of everyone. So the mechanism has to make the good path the *cheap* path, and the influence has to be earned by delivering something teams want.

**Decide.** I would work by **defaults, evidence and demonstration rather than by mandate**, sequence adoption through the willing teams, and accept that the resistant teams come last and come voluntarily. I would also insist on a small number of genuinely non-negotiable items, because "everything is a guideline" is its own failure.

**Execute.**

1. **Earn standing by helping first.** Pick the hardest current problem in one of the two excellent teams and do real work on it - not advice, work. Nothing purchases credibility with the resistant leads faster than the enthusiastic ones saying "he actually helped".
2. **Establish shared evidence.** A simple, objective picture everyone can see: incident causes by category, change failure rate, lead time, cost per service, SLO attainment. Standards arguments become data arguments, and data is not personal. This alone often changes behavior with no intervention.
3. **Ship golden paths, not documents.** A service template with tracing, metrics, health checks, structured logging, SLO definitions, CI, and a database migration setup already wired in (Q235). Teams adopt it because it saves them two weeks, not because it is mandated. Adoption of a template is measurable, which makes progress visible.
4. **Make the platform enforce what matters.** The few genuinely non-negotiable rules - schema compatibility in CI (S10), no unbounded metric labels, no secrets in code, every service has an owner and an alert - are implemented as automated gates in the pipeline and in shared libraries, not as review items. Governance in a library succeeds; governance in a wiki does not (Q115).
5. **Make design review peer-to-peer and lightweight.** A weekly optional session where engineers present designs to *each other*, with me as a participant rather than an approver, and a one-page ADR template. Optional but genuinely useful sessions become well-attended; mandatory ones become theatre.
6. **Grow the standard through people, not process.** Identify one engineer per team who cares about design, invest in them, and let the standard propagate through peers who live with the consequences. Within a year that group, not I, is the mechanism.
7. **Handle the resistant leads individually and without confrontation.** Find out what they are actually protecting - usually delivery pressure and a history of being slowed by process. Offer something that helps them hit a deadline, ask nothing in return, and let the golden path arrive with the next new service rather than as a retrofit demand.

**Reflect.** How I would measure success at six months: adoption of the template for new services, change failure rate, incidents with a repeat root cause, and whether design conversations are happening without me in the room. The last one is the real target - if the improvement depends on my attention, I have built a dependency rather than a capability. The mistake I would guard against is over-standardizing: eight teams do not need identical architectures, they need consistent *interfaces, operability and safety*, and the ability to differ where the domain justifies it. Insisting on uniformity is how architecture functions become resented, and the resistant leads are usually reacting to a real memory of that.

> *Hook: a standard you drove across teams you did not own, and the mechanism that made it stick.*
