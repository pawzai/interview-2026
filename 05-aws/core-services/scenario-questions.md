# Scenario Questions

Core-service production incidents and service-selection exercises.

Every scenario uses **CIDER**, defined in [../../01-java/README.md](../../01-java/README.md):

- **Clarify** - what you ask before answering. Never diagnose or design in silence.
- **Isolate** - narrow the failure domain or the core requirement.
- **Decide** - commit to an approach and name the trade-off.
- **Execute** - the concrete steps.
- **Reflect** - what you monitor, prevent, or would do differently.

Read the scenario, answer out loud for five minutes, then compare. The model responses are longer than you should speak - use them as the map, not the script. References like (Q68) point at [answers.md](answers.md) **in this pack**; references to the serverless pack are written out explicitly.

**Part A** is ten production incidents on core services. **Part B** works Q215-220 as full service-selection exercises. Part B answers are longer because the exercise is the whole answer.

---

## Part A - Production incidents

### S1. The instance that is fine at exactly 20 percent

> An internal reporting API has been getting slower for two weeks and is now unusable. It runs on a single `t3.medium`. The CPU graph shows a flat line at exactly 20 percent for the last three days. The team's conclusion is that the application has a bug, because "the instance is barely working".

**Clarify.** What is `CPUCreditBalance` doing over the last month, and is `CPUSurplusCreditBalance` non-zero? Is the instance in `standard` or `unlimited` mode? When did the line become flat, and does that point coincide with the balance reaching zero? What does the run queue look like inside the instance (`uptime`, `vmstat`)? Has request volume changed, or has a report been added? Is this the only instance?

**Isolate.** A CPU graph that is **flat at exactly the baseline** is not a measurement of demand - it is a measurement of a throttle (Q5). `t3.medium` has a 20 percent baseline per vCPU, and 20 percent is precisely where a credit-exhausted instance in standard mode sits. The shape confirms it: two weeks of gradual degradation followed by a hard floor is a credit balance draining, not a code regression, which would produce a step change at a deploy.

The confirming evidence is `CPUCreditBalance` at zero and a **load average well above the vCPU count** inside the instance - work queued behind a CPU ceiling. If the balance is healthy and the line is still flat at 20 percent, then it genuinely is the application, and I would go looking at thread pools and downstreams instead.

**Decide.** Restore service now by removing the throttle, then size from the demand you can finally see. I will not attempt to diagnose the application until the instance can actually run - **you cannot measure demand through a throttle**, which is the reason this has been mysterious for two weeks.

**Execute.**

1. Switch the instance to **`unlimited` mode** - immediate, no restart, and the instance can burst again within a minute. Accept that this converts a performance problem into a cost one temporarily.
2. Watch `CPUSurplusCreditBalance` and the actual CPU consumed once unthrottled. **That number is the real demand**, and it is the input to sizing.
3. Move to a non-burstable instance - `m6i.large` or whatever the observed demand justifies - during the next window (Q4).
4. Check whether other T-family instances in the estate are in the same state; this is rarely isolated.
5. Confirm recovery on the API's p99 latency, not on the CPU graph.

**Reflect.** Three things. **Alarm on `CPUCreditBalance` approaching zero** on every burstable instance - it is a free, unambiguous early warning that nobody had. **Establish a rule that T-family instances are for development and genuinely spiky low-average workloads only**, never for a production service with a steady floor (Q4). And more generally: **a metric flat at a round number is a ceiling until proven otherwise** - the same reasoning applies to EBS throughput at 125 MB/s (Q24), a connection pool at its maximum, and an ASG at its `max` (Q66).

> *Hook: a credit-exhaustion or throttle-shaped graph you misread, and how long it took.*

---

### S2. Healthy targets, intermittent 502s

> A Spring Boot service behind an ALB returns 502s to roughly one request in 500. All targets are healthy, CPU and memory are unremarkable, and the errors do not correlate with deployments or traffic volume. It has been happening for months and the team has learned to live with it. A new customer's monitoring has now flagged it.

**Clarify.** What is `target_status_code` in the ALB access logs for the failing requests - a value, or `-`? What is `target_processing_time` on those rows? Is the ALB's idle timeout still the default 60 seconds, and what is the application's keep-alive timeout? Are the errors distributed evenly across targets, or concentrated? Do backend logs show anything at all at those timestamps? Any correlation with GC pauses or with the age of a connection?

**Isolate.** A **low-rate, uncorrelated, long-running** 502 is almost diagnostic on its own. The access log settles it in one query (Q54):

- **`target_status_code` is `-`** - the target produced no response. That is a connection-level failure: the keep-alive race, a crash mid-request, or saturation.
- **`target_status_code` has a value** - the target responded and the ALB rejected it as malformed. That would be deterministic, not one in 500.

Given "no correlation with anything", the overwhelmingly likely cause is the **keep-alive timeout mismatch** (Q64): the backend closes a pooled connection at the moment the ALB dispatches a request onto it. The request is lost, the ALB reports 502, and the backend logs nothing because it never received it - which is exactly why months of looking at application logs found nothing.

Spring Boot with embedded Tomcat is a common offender because `server.tomcat.keep-alive-timeout` is frequently unset while the ALB sits at 60 seconds.

**Decide.** Fix the timeout ordering, which is a configuration change with no architectural cost. I will not add a retry at the client to mask it - a retry on a 502 for a non-idempotent request is a correctness problem, not a fix.

**Execute.**

1. Query the ALB access logs in Athena, grouping by `elb_status_code`, `target_status_code` and `target_processing_time`, to confirm the shape.
2. Read the application's actual keep-alive timeout. If it is below the ALB's 60 seconds, that is the answer.
3. Set the backend's keep-alive comfortably above the ALB idle timeout - 65-75 seconds against a 60-second ALB - and deploy.
4. Watch the 502 rate for 48 hours; this class of error needs volume to confirm.
5. If it persists, work the remaining causes in order: GC pause duration against the ALB timeout, thread pool exhaustion, and target-side request timeouts.

**Reflect.** Two changes and one cultural one. **Standardize the timeout ordering across the estate** - request duration < graceful shutdown < deregistration delay < lifecycle hook, and backend keep-alive > ALB idle timeout - and put it in the shared service construct so no service gets it wrong by default (Q59, Q64). **Enable ALB access logs everywhere** with Athena over them, because this investigation is thirty seconds with logs and weeks without. And the cultural one: **a persistent low-rate error is a defect with a cause, not background noise.** "One in 500" was acceptable until a customer measured it, and that is the wrong trigger for investigation.

> *Hook: a long-tolerated low-rate error whose cause turned out to be a single configuration value.*

---

### S3. The scale-in that drops requests

> Every scale-in event produces a small burst of client errors. The team has responded by setting the ASG's minimum to the peak level, so it never scales in - which has doubled the compute bill. The finance team has now noticed.

**Clarify.** What is the deregistration delay on the target group, and what is the service's p99.9 request duration? Does the application handle `SIGTERM`, and is graceful shutdown configured? Is there a terminate lifecycle hook, and what is its timeout? Are there long-lived connections - WebSockets, SSE, streaming, long-polling? Do the errors appear as connection resets at the client, or as 502s at the ALB? Does the same thing happen during deployments?

**Isolate.** The chain from "ASG decides to terminate" to "request dies" has several links, and any one of them being wrong produces this (Q78):

1. **Deregistration delay shorter than the longest request** - the load balancer stops draining and the instance goes.
2. **No `SIGTERM` handling** - the process dies immediately on shutdown, taking in-flight work with it. This is the most common single cause for a Java service, because graceful shutdown is not on by default in every configuration.
3. **No terminate lifecycle hook**, so the ASG proceeds to shutdown without coordination.
4. **Long-lived connections** that cannot complete within any drain window.

The tell that distinguishes 1 and 2: if errors also occur during **deployments**, it is the application's shutdown handling, since a rolling deployment exercises the same path.

**Decide.** Fix the ordering chain rather than the symptom. Pinning the minimum to peak is paying compute to avoid a five-line configuration fix, and it also means the fleet still drops requests during every deployment - so it does not even solve the whole problem.

**Execute.**

1. Measure p99.9 request duration from the ALB's `target_processing_time`. That is the number everything else is derived from.
2. Enable graceful shutdown in the application (`server.shutdown=graceful` and a shutdown phase timeout for Spring Boot), so `SIGTERM` stops accepting new work and finishes what is in flight.
3. Set the **deregistration delay above the graceful shutdown period**, and both above p99.9 duration.
4. Add a **terminate lifecycle hook** with a timeout above the deregistration delay if there is post-shutdown work to do.
5. Test by terminating an instance under load and watching for a single error - do not infer it from configuration.
6. Only then lower the ASG minimum back, one step at a time, watching the error rate.

**Reflect.** **Put the ordering in the shared construct** so it is right by default (Q59). **Test scale-in and deployment under load as part of the release process** - a synthetic load test that terminates an instance is a five-minute job and catches the whole class. And name the pattern for the team: **"we made the symptom go away by spending money" is a decision that should be recorded with its cost**, because otherwise it becomes invisible and permanent. The finance team found this; an engineering practice should have.

> *Hook: a workaround that cost real money and hid a five-minute fix.*

---

### S4. Failover took twenty minutes

> A regional outage forced a failover to the secondary region. Route 53 health checks and failover records were configured and had been tested. Traffic began moving after about four minutes but did not fully shift for twenty, and one internal Java service never moved at all until it was restarted manually.

**Clarify.** What was the TTL on the failover record, and what were the health check interval and failure threshold? Which clients were still hitting the primary at minute 15 - browsers, mobile, internal services, partners? What is `networkaddress.cache.ttl` set to in the Java services? Do the internal clients use connection pools, and what is their connection lifetime? How was the previous test performed - by flipping the record and checking `dig`, or with real clients?

**Isolate.** Three mechanisms compound, and the twenty-minute figure is the sum (Q88):

1. **Detection lag** - standard health checks at 30 seconds with a threshold of 3 is 90 seconds minimum, and an intermittently failing endpoint can oscillate for several minutes before crossing consistently. That accounts for the first four minutes.
2. **DNS caching beyond the TTL** - resolvers that clamp to their own minimums, corporate resolvers, browsers. This is the long tail from minute 4 to minute 20.
3. **Clients that never re-resolve** - and the Java service that required a restart is the diagnostic evidence. **The JVM caches DNS indefinitely** under some configurations unless `networkaddress.cache.ttl` is set explicitly. A connection pool that resolved once at startup will hold the dead address until the process dies.

And a fourth, implied by "had been tested": the test almost certainly flipped the record and confirmed resolution with `dig`, which measures step 2 in isolation and none of the client behaviour.

**Decide.** Reduce each layer, and accept that **DNS failover is structurally incapable of sub-minute recovery** - so if the business requires faster, the answer is a different mechanism, not better DNS tuning. I would present both: what DNS can be tuned to (2-3 minutes), and what Global Accelerator would give (around 30 seconds).

**Execute.**

1. **TTL to 60 seconds** on every failoverable record, and verify from external resolvers.
2. **Fast health checks** (10-second interval, threshold 2-3) against an endpoint that reflects real health, not a static 200 - and add a **calculated health check with a manual kill-switch child** so an operator can force failover without editing records (Q89).
3. **Set `networkaddress.cache.ttl` explicitly** in every JVM - a one-line fix with an outsized effect - and configure connection pools to expire and re-resolve.
4. For the partner and internal paths with strict RTO, propose **Global Accelerator** (Q109), which fails over on health checks in around 30 seconds with no DNS dependency at all.
5. **Re-drill with real clients**, measuring end to end, and record the measured number as the official RTO.

**Reflect.** The general lesson is worth stating plainly: **a failover test that does not include real clients tests the part that was never going to fail.** DNS propagation was fine; client behaviour was not. Beyond the fixes, I would **publish the measured RTO alongside the target** so the gap is visible and fundable (Q46), and **add the client DNS cache setting to the service baseline** so new services inherit it rather than each one being discovered during an incident.

> *Hook: a failover whose measured time far exceeded the design, and which layer was responsible.*

---

### S5. The cache that collapses at peak

> A Redis cache in front of the product catalogue works perfectly in load testing and falls over every Friday evening at peak. When it degrades, the database CPU goes to 100 percent and the site becomes unusable for fifteen minutes until traffic subsides. Adding a larger Redis node did not help.

**Clarify.** What do `Evictions`, `CacheHitRate`, `CurrConnections` and - critically - **`EngineCPUUtilization`** (not `CPUUtilization`) look like during the event? Is there a spike in `DatabaseMemoryUsagePercentage`? What is the eviction policy? Do all keys have TTLs, and are those TTLs jittered? What does the slow log show? Is the failure a gradual degradation or a cliff? Does the database load spike *before* or *after* the cache degrades?

**Isolate.** Four candidate mechanisms (Q154), and the metrics separate them quickly:

1. **Thundering herd** - popular keys expire together and hundreds of concurrent requests all recompute. Signalled by database load spiking *at* the moment of a TTL boundary, with cache hit rate dipping sharply and recovering.
2. **Eviction cascade** - the working set exceeds memory at peak, evictions climb, hit rate falls, database load rises, latency rises, more requests are concurrent, more is cached, more is evicted. A metastable failure that feeds itself.
3. **Single-thread saturation** - `EngineCPUUtilization` at 100 percent while overall `CPUUtilization` looks moderate. Caused by command volume or by a slow O(N) command blocking the thread.
4. **A hot key** saturating one shard.

**"A larger node did not help" is the most informative fact in the scenario.** More memory fixes mechanism 2; it does nothing for 1, 3 or 4. So the evidence points away from eviction and toward the herd or thread saturation - and the fifteen-minute self-resolving shape, with database CPU pegged, is characteristic of a **stampede**.

**Decide.** Address the stampede directly with request coalescing and jittered TTLs, and simultaneously protect the database so a future cache event degrades rather than fails. I want two independent fixes, because the cache will fail again for some other reason eventually and the database being able to survive it is the more durable property.

**Execute.**

1. Confirm from the metrics which mechanism it is - `EngineCPUUtilization` and the timing of the database spike relative to the hit-rate dip.
2. **Jitter every TTL** (base plus a random 10-20 percent) so keys stop expiring in lockstep. Cheapest fix, immediate effect.
3. **Add single-flight/lock-based coalescing** on cache misses for expensive keys, so one request recomputes and the others wait or serve stale.
4. Consider **probabilistic early refresh** for the hottest keys, so they are recomputed before expiry under low concurrency.
5. **Protect the database**: a connection limit or RDS Proxy (Q146) so a stampede queues rather than saturating, and a circuit breaker in the application.
6. **Re-run the load test with a cold cache, at production data volume and production concurrency** - the reason testing missed this is that it never did.

**Reflect.** Three things. **The load test was not testing the failure mode**, and I would make cold-cache, full-concurrency testing a standard part of the suite. **`EngineCPUUtilization` versus `CPUUtilization` belongs on the dashboard** - the distinction is the difference between diagnosing this in five minutes and five weeks. And architecturally: **a cache whose failure takes down the service is not a cache, it is a dependency** - the database must be able to serve degraded traffic without the cache, even if slowly, and if it cannot, the cache is load-bearing and should be treated as such (MemoryDB, Q155, is one answer to that).

> *Hook: a cache-related outage, which of the four mechanisms it was, and how you reproduced it afterwards.*

---

### S6. The NAT gateway bill

> A quarterly cost review shows NAT gateway charges of about $18,000 per month across the organization, roughly 40 percent of the total network spend and larger than the compute for several of the workloads behind it. The platform team's response is to ask teams to "use less data".

**Clarify.** What is the split between the **hourly** charge (number of NAT gateways) and the **per-GB processing** charge? How many NAT gateways exist, across how many VPCs and AZs? What are the top destinations by volume - is it S3, ECR, DynamoDB, a third party, or genuine internet traffic? Are there VPC endpoints anywhere? Is there a Transit Gateway in the path as well, adding a second per-GB charge? Which accounts and workloads dominate?

**Isolate.** NAT costs decompose into two very different problems, and the fix is different for each (Q117, Q130):

- **Hourly charges** are a function of **NAT gateway count**: ~$32/month each, so 3 AZs across 40 VPCs is 120 gateways and ~$3,800/month before a byte moves. This is a **topology** problem, solved by centralized egress.
- **Per-GB processing** at ~$0.045/GB is a **traffic** problem, and the question is what the traffic *is*.

In almost every estate I have seen, the dominant traffic through NAT is **S3, ECR and DynamoDB** - which should not be going through NAT at all. **Gateway endpoints for S3 and DynamoDB are free**, and interface endpoints for ECR cost far less than the NAT processing they replace. A container estate pulling images through NAT on every task launch is the classic case.

The flow logs answer this definitively, using the destination address and the AWS IP ranges to classify traffic by service.

**Decide.** Attack the traffic first (the largest and cheapest win), then the topology. **"Use less data" is not an answer** - the data is doing useful work, and the cost is caused by the path it takes, not the volume. I would say that explicitly, because framing this as a team-behaviour problem sends forty teams on a pointless exercise.

**Execute.**

1. **Analyse flow logs** (with Athena) grouped by destination, classified against AWS IP ranges, to quantify what fraction is S3, ECR, DynamoDB and other AWS services.
2. **Deploy gateway endpoints for S3 and DynamoDB in every VPC.** Free, no downtime, and typically removes the majority of the traffic. Make it a landing zone default so new VPCs inherit it (Q123).
3. **Deploy interface endpoints** for the next tier - ECR (api, dkr, **and the S3 gateway endpoint for layers**), Systems Manager, Secrets Manager, CloudWatch Logs - and compare the endpoint hourly cost against the NAT processing saved per VPC. In a busy VPC it pays back easily; in an idle one it may not.
4. Re-measure. Then evaluate **centralized egress** for the remaining traffic (Q130), doing the arithmetic properly: centralization cuts the hourly charges dramatically but **adds TGW processing at $0.02/GB** to every remaining byte, so it is only a win once the endpoint work has removed the bulk of the volume.
5. Add **cost allocation by VPC and account** so the remaining spend has an owner.

**Reflect.** Two things beyond the fix. **This is a landing zone defect, not a team behaviour problem** - endpoints should have been in the VPC template from the first account, and the remediation cost is forty VPCs' worth of change that one template would have prevented. And **network cost needs an owner and a dashboard**, because it is invisible to the teams generating it: an engineer pulling a container image has no signal that it costs money, and no amount of asking will change that. The fix is architectural, permanently.

> *Hook: a network cost you traced to a path rather than a volume, and what the endpoint change saved.*

---

### S7. Multi-AZ failed over and the application did not recover

> An RDS Multi-AZ instance failed over cleanly at 02:14 - AWS's event log shows the failover completing in 74 seconds. The application did not recover until an engineer restarted every service at 02:51. The team's post-incident conclusion is "Multi-AZ does not work".

**Clarify.** What did the application log at 02:15 - connection errors, or successful connections to a read-only endpoint? What is the JVM's DNS cache setting? What connection pool is in use, and what are its validation, max-lifetime and eviction settings? Were the services connecting through the cluster endpoint, or had someone used an instance endpoint? Did *all* services fail to recover, or only some? Did any recover on their own before the restart?

**Isolate.** The database recovered in 74 seconds, which is normal (Q133). The 37 minutes belongs entirely to the application layer, and there are three candidates:

1. **DNS caching in the JVM.** RDS failover works by **repointing the endpoint's DNS record** at the new instance. A JVM caching DNS indefinitely resolves the old address forever, and only a restart clears it. This is the single most common cause and it matches the "restart fixed it" evidence exactly (Q88, Q135).
2. **A connection pool holding dead connections** - no validation query, no `maxLifetime`, so the pool hands out broken sockets indefinitely and never re-resolves.
3. **An instance endpoint in the configuration** rather than the cluster endpoint (Q139), in which case the application is pointed at a machine that is now a standby - and no amount of waiting fixes it.

If *some* services recovered and others did not, the difference between them is the answer.

**Decide.** The finding is not "Multi-AZ does not work" - it is that **the application's recovery, not the database's, is the RTO** (Q135). I would reframe the post-incident conclusion first, because the current one leads to the wrong remediation (people start proposing multi-region, which would fail identically).

**Execute.**

1. Confirm the endpoint in use is the cluster/writer endpoint everywhere, not an instance endpoint.
2. **Set `networkaddress.cache.ttl` explicitly** (30-60 seconds) in every JVM - via `JAVA_TOOL_OPTIONS` in the base image so it is not per-service.
3. Configure the connection pool properly: a **validation query or `testOnBorrow`**, a **`maxLifetime` shorter than any expected failover window**, and eviction of idle connections.
4. Ensure the application **retries transient database errors** with backoff rather than failing permanently.
5. **Drill it**: perform a `reboot with failover` in a lower environment under load, and measure how long until the application is serving. Repeat until the measured number is acceptable, then drill it in production during a window.
6. Consider **RDS Proxy** (Q146), which holds client connections across a failover and reduces application-visible failover time to seconds - often faster than fixing every application.

**Reflect.** **The measured RTO is the application's, not the database's**, and it should be recorded as such (Q46). **Add the DNS cache setting and pool configuration to the service baseline** so this is inherited rather than rediscovered. And run **failover drills on a schedule** - a Multi-AZ deployment that has never been failed over deliberately is an untested claim, and the first test should not be at 02:14.

> *Hook: a failover where the application layer, not the infrastructure, was the outage.*

---

### S8. The EKS cluster that stopped scheduling

> A Friday afternoon deployment doubles the pod count of a service temporarily during a rolling update. Pods begin sticking in `ContainerCreating`. New nodes join the cluster successfully but schedule nothing. The error is `failed to assign an IP address to container`.

**Clarify.** What are the subnet CIDR sizes for the node subnets, and how many free IPs remain in each? How many nodes and pods are running, and what instance types (which determines pods-per-node)? Is prefix delegation enabled on the VPC CNI? What are `WARM_IP_TARGET` and `MINIMUM_IP_TARGET` set to? Are there other consumers of these subnets - load balancers, RDS, interface endpoints, Fargate tasks? Is this the first time, or has it been getting tighter?

**Isolate.** This is **VPC CNI IP exhaustion** (Q174), and the mechanism explains every symptom including the confusing one:

Every pod gets a real VPC IP from the node's subnet. The CNI **pre-allocates a warm pool** of IPs per node, so each node reserves far more addresses than it currently uses. **Nodes joining successfully but scheduling nothing** is the diagnostic signature: the node itself gets a primary IP (one address, available), but cannot obtain the secondary IPs its pods need.

The rolling update is the trigger rather than the cause - it temporarily doubles pod count, which is exactly the surge the subnet had no headroom for. The cluster has been running near the limit and nobody could see it, because **there is no default alarm on subnet IP availability**.

**Decide.** Restore capacity immediately by the least disruptive means, then fix the structural problem. I will not resize the existing subnets - a VPC subnet's CIDR cannot be changed, so that path is a rebuild and is not available during an incident.

**Execute.**

*Now:*

1. **Reduce the surge** - lower `maxSurge` on the deployment or scale down a non-critical workload to free IPs, so the rollout can complete.
2. Check for **leaked ENIs** from terminated nodes or pods, which occasionally hold addresses.

*Today:*

3. **Add a secondary CIDR to the VPC** - `100.64.0.0/16` from the shared address space, which does not consume RFC 1918 (Q127) - and **create new node subnets in it**. Node groups placed in the new subnets get plenty of addresses, and nothing existing is renumbered. This is the standard, least-disruptive fix.
4. **Enable prefix delegation** on the VPC CNI so ENIs are assigned `/28` prefixes rather than individual addresses, dramatically increasing pods per node. Do this on the new subnets, since prefix allocation on a fragmented subnet can fail.
5. Tune `WARM_IP_TARGET` and `MINIMUM_IP_TARGET` to reduce over-allocation, accepting slightly slower pod starts.

*This quarter:*

6. Evaluate **IPv6 for the cluster**, which removes the constraint structurally.

**Reflect.** Three things. **Alarm on available IPs per subnet** - this is a trivially available metric that nobody had, and it converts a Friday outage into a Tuesday ticket. **The IP plan is part of the cluster's capacity plan**, and pods-per-node times node count times warm pool should be computed at design time rather than discovered. And a broader point about EKS: **the control plane being managed does not make the networking managed** (Q173) - this is exactly the category of work that the "EKS reduces operational burden" argument tends to overlook.

> *Hook: a capacity limit that was invisible until it was breached, and the alarm you added.*

---

### S9. Snapshots, but no backups

> A production PostgreSQL on EC2 is corrupted by a bad migration at 14:00 on a Tuesday. The team restores from the most recent EBS snapshot, taken at 02:00. The restored volume performs so badly the database is unusable for the first hour, and when it does come up, twelve hours of transactions are missing. The recovery plan said RTO 2 hours, RPO 1 hour.

**Clarify.** Were WAL archives being shipped anywhere, or was the snapshot the only artifact? Was the snapshot application-consistent - was the database quiesced or the filesystem frozen? Is there a read replica or a standby? Are there snapshots in another account or region? What does the recovery plan actually specify as the mechanism, and when was it last tested?

**Isolate.** Three separate failures, and the scenario is a good example of how they compound (Q45, Q46):

1. **RPO failure - twelve hours instead of one.** Daily snapshots give a **24-hour RPO at best**, not one hour. The plan's RPO was never achievable with the mechanism in place; nobody had done the arithmetic. Point-in-time recovery requires **continuous WAL archiving**, which was not happening.
2. **RTO failure from snapshot hydration.** A volume restored from a snapshot is **lazily loaded** - blocks are fetched from S3 on first access, so it performs terribly until hydrated (Q29). The plan's RTO was presumably measured on a warm volume or not measured at all.
3. **Consistency risk.** A crash-consistent snapshot of a running database may or may not recover cleanly. It happened to work here; that was luck.

The underlying failure is that **the plan documented an aspiration and nobody tested it**. Both numbers were fiction.

**Decide.** Recover what is recoverable now, then rebuild the backup design around a **tested** RTO and RPO rather than a stated one. I would also be explicit with the business that twelve hours of data is likely unrecoverable, early, rather than discovering it after eight hours of hope.

**Execute.**

*Now:*

1. Check for **any other source of the missing twelve hours** - a replica, WAL files on the original volume (if it still exists and is only logically corrupted), application-level audit logs, a downstream data warehouse or ETL target, or message queues that can be replayed. The original volume should not be deleted until this is exhausted.
2. **Pre-warm the restored volume** (`fio` read pass) or enable **Fast Snapshot Restore** if further restores are expected (Q28).

*This week:*

3. **Move to RDS or Aurora** if there is no strong reason not to (Q132) - continuous backups, PITR to the second, and automated Multi-AZ, which eliminates this entire class of problem. This is the recommendation, and I would make it plainly.
4. If it must stay self-managed: **continuous WAL archiving to S3** (`pgBackRest` or `wal-g`), giving genuine PITR, plus base backups on a schedule.
5. **AWS Backup** with a vault in a **separate account**, Vault Lock enabled (Q44).

*Ongoing:*

6. **Automated quarterly restore tests** into an isolated environment, with the wall-clock time recorded as the official RTO and automated validation of the restored data.

**Reflect.** The sentence to take away: **an untested backup is a hypothesis, and a documented RTO that has never been measured is a number someone made up.** Beyond the mechanics, I would change how recovery targets are set: **the plan should state the *measured* RTO and RPO alongside the target**, with the gap visible as a funded risk (Q46). And I would add the hydration effect to the organization's knowledge explicitly, because "the restore completed" and "the service is usable" are different events and the difference is an hour.

> *Hook: a restore that revealed the recovery plan was untested, and what the measured numbers turned out to be.*

---

### S10. The migration wave that broke on latency

> Wave 3 of a data-centre migration moves an order-processing application to EC2. Everything passes functional testing. On Monday morning, order processing takes 40 seconds per order instead of 2, and the business escalates within an hour. Nothing is erroring.

**Clarify.** Where is the database - did it move in this wave, or is it still on-premises? What is the round-trip latency between the EC2 instance and the database now, versus what it was on-premises? How many database round trips does one order require? Was the dependency mapped in discovery? What did the functional testing environment look like - was the database local to the test instance? Is the connection over Direct Connect or VPN?

**Isolate.** "Slow but not erroring", appearing only under real use, immediately after a partial move, is the **chatty application across a WAN** problem (Q193).

The arithmetic makes it obvious: the application was designed for a **0.5 ms** local database round trip. Over Direct Connect to the on-premises data centre it is perhaps **20-30 ms**. An operation making **200 sequential round trips** goes from 100 ms to 5 seconds; one making 1,500 - which an ORM with lazy loading in a loop will happily do - goes from under a second to 40. **The code did not change; the constant did.**

Two things confirm it: the latency per operation should be an integer multiple of the round trip, and the database itself will show low load, because it is answering quickly and waiting.

The root cause is a **wave planning failure** - the application and its database were split across waves, which the dependency map should have prevented (Q193). And **functional testing did not reproduce the topology**, which is why it passed.

**Decide.** Restore performance fastest by removing the WAN hop, not by optimizing the application - a query-count reduction is the right long-term fix and it is a development project, not an incident response. The options are roll back, or accelerate the database's move.

**Execute.**

*Now:*

1. Quantify it: measure the round-trip latency and count the queries per order (from the database's statement log or an APM trace). Confirm the multiplication. This takes fifteen minutes and turns an argument into a fact.
2. **Decide between rollback and roll-forward** against the pre-agreed decision criteria (Q192). If the database can be moved within the acceptable window, roll forward; otherwise **roll back to on-premises**, which should be possible because the source was kept intact (Q185).
3. Communicate the decision and the timeline to the business immediately.

*This week:*

4. **Move the database into the same wave** and re-cut over, with the application and database co-located.
5. **Re-examine every remaining wave** for the same split, using the dependency map - this is very unlikely to be the only instance.

*Later:*

6. Reduce the query count in the application, which makes it resilient to latency in general and is worth doing regardless.

**Reflect.** Three changes to the programme, which matters more than the individual fix. **Waves must contain an application and its tightly-coupled dependencies** - and where that is impossible, the split must be explicitly latency-tested before cutover, not after. **Add a latency test to the wave acceptance criteria**: run the application on AWS against the on-premises dependencies *before* the cutover (a stage-1 parallel run), which surfaces this while rollback is trivial. And **functional testing must reproduce the network topology** - a test environment with a local database validates the code and nothing about the migration.

> *Hook: a migration or decomposition where latency, not correctness, was the failure, and how you caught it (or did not).*

---

## Part B - Service-selection exercises

These work Q215-220. Each has more than one defensible answer; what is being assessed is whether you establish constraints before naming services, quote deciding numbers, and say what you are giving up.

### S11. Five workloads, one compute decision each (Q215)

> A steady internal API; a nightly 6-hour batch job; a spiky public webhook receiver; a GPU inference service; and a legacy Windows application whose licence is tied to physical cores.

**Clarify.** For all five: what is the actual utilization profile, and does the team have container or serverless experience? Specifically - is the internal API's traffic genuinely flat or does it follow business hours? Is the batch job parallelizable or a single long-running process? What is the webhook's peak-to-average ratio and its latency requirement? Is the GPU workload latency-sensitive (online inference) or throughput-oriented (batch scoring)? And for the Windows application: which licence, how many cores, and can it be re-licensed or replaced?

**Isolate.** Each workload has a **different binding constraint**, and naming it is the answer:

| Workload | Binding constraint |
| --- | --- |
| Steady internal API | Cost efficiency at constant load |
| Nightly batch | Duration and interruption tolerance |
| Spiky webhook | Elasticity and idle cost |
| GPU inference | Hardware availability and utilization |
| Legacy Windows | **Licensing**, which is not a technical constraint at all |

**Decide, per workload:**

**1. Steady internal API → ECS on Fargate, or EC2 with a Savings Plan if the fleet is large.**

Constant load means elasticity is worth little and per-unit cost is worth a lot. Fargate for operational simplicity; if the fleet is big enough that the per-task premium is material at high, steady utilization (Q169), EC2 with a **Compute Savings Plan** covering the floor is cheaper. **The deciding number is utilization**: above roughly 60-70 percent sustained packing efficiency, EC2 wins on cost; below it, Fargate wins once operational time is counted. *Not Lambda* - constant load means always-warm concurrency, which Lambda prices badly.

**2. Nightly 6-hour batch → AWS Batch on Spot** (Q176).

Six hours excludes Lambda (15-minute limit) outright. The job is interruption-tolerant by nature and runs when nobody is watching, so **Spot at 70-90 percent savings** is close to free money, and Batch's built-in retry makes interruption a scheduling event rather than a failure. If the job is parallelizable, array jobs give both speed and better Spot resilience. *Giving up*: it may occasionally take longer or restart. For a nightly job with a morning deadline, that is acceptable - and I would put a fallback On-Demand compute environment second in the queue so a Spot drought does not miss the deadline.

**3. Spiky public webhook → Lambda behind API Gateway.**

High peak-to-average is exactly Lambda's economic case: pay per invocation, scale to the spike, pay nothing at idle. The receiver should do the minimum - validate, authenticate, write to SQS or EventBridge, return 200 - with processing decoupled behind it, so a spike becomes a queue rather than a load problem. *Giving up*: cold starts (mitigate with a lightweight runtime, or provisioned concurrency if the latency SLO is tight), and a per-request cost that would be poor at sustained high volume. **The deciding number is the peak-to-average ratio**: above about 10:1, serverless wins decisively; below 3:1, containers are cheaper.

**4. GPU inference → depends on the latency requirement, and this is where I would push back hardest.**

- **Online, latency-sensitive** → **SageMaker real-time endpoints** or ECS/EKS on `g5`/`inf2` instances. SageMaker if the team wants managed model deployment, autoscaling and A/B variants; ECS/EKS if it must sit inside the existing platform.
- **Batch or asynchronous scoring** → **SageMaker batch transform** or **AWS Batch on GPU Spot**, which is dramatically cheaper.
- **Consider Inferentia (`inf2`)** rather than GPU - for supported models it is substantially cheaper per inference, and checking is a day's work with a large payoff.

*Giving up*: GPU instances are expensive and often poorly utilized, so **the real design question is batching and utilization**, not instance choice. A GPU endpoint at 8 percent utilization is the most common waste in an ML estate.

**5. Legacy Windows with core-tied licence → EC2 Dedicated Hosts** (Q12).

This is the one where the technical answer is dictated by a non-technical constraint. A per-physical-core licence requires **visibility and control of the physical cores**, which only Dedicated Hosts provide - Dedicated Instances are not sufficient, and this distinction is the point of the question. Use **License Manager** to track and enforce, and **host affinity** so the instance returns to the same host across stop/start.

*Giving up*: you pay for the whole host whether you fill it or not, so **bin-packing other Windows workloads onto the same host is an actual design activity** and often the difference between a viable and a non-viable business case. And I would raise the strategic question: the licence, not the infrastructure, dominates this workload's cost, so the highest-value work is re-licensing, moving to licence-included, or replacing the application - not optimizing the compute.

**Reflect.** The pattern across all five: **three were decided by the load shape, one by hardware, and one by a contract.** The mistake to avoid is having a favourite platform - a team that puts all five on EKS has ignored four different constraints. And I would note that the fifth workload's answer is a holding position: the right long-term action is to remove the licence constraint, and saying so is part of the answer.

> *Hook: a set of workloads where you deliberately used different platforms, and how you justified the heterogeneity.*

---

### S12. Five storage decisions (Q216)

> A shared filesystem for 200 editing workstations; a 400 TB archive with a legal hold; a Postgres data volume needing 30,000 IOPS; container image layers; and clickstream data queried monthly.

**Clarify.** Editing workstations - Windows or Linux, what content, and what aggregate throughput? Archive - what retrieval expectation, and what does the legal hold require (retention period, immutability, audit)? Postgres - is 30,000 IOPS measured or assumed, what is the I/O size, and is the instance capable of driving it? Container images - how many pulls per day and from where? Clickstream - what volume per month, what query shape, and how many consumers?

**Decide:**

**1. Shared filesystem, 200 editing workstations → FSx for Windows File Server** (if Windows/Premiere/Avid, the common case), **or FSx for Lustre** if this is render or transcode throughput rather than interactive editing (Q39).

The deciding factors are **protocol and throughput**. Editing workstations expect SMB with AD integration; the tooling assumes it. **Not EFS**: NFS latency and per-GB cost make it the wrong tool for interactive 4K, and 200 concurrent editors is a throughput requirement measured in GB/s. *Giving up*: FSx is provisioned - you size capacity and throughput and manage them, unlike EFS's elasticity. Deploy Multi-AZ, and pair with **workstations in AWS** if the editors are remote, because moving 4K to a local workstation is a worse problem than moving pixels.

**2. 400 TB archive with a legal hold → S3 with Object Lock, class chosen by retrieval expectation.**

**Object Lock in compliance mode** is the mechanism the legal hold requires - WORM, with a retention period that nobody including root can shorten. That is the non-negotiable part.

The class depends entirely on the retrieval answer:

| Retrieval need | Class | ~Cost/TB/month |
| --- | --- | --- |
| Occasionally, immediately | Glacier Instant Retrieval | ~$4 |
| Planned, hours acceptable | Glacier Flexible Retrieval | ~$3.6 |
| Effectively never | Deep Archive | ~$1 |

At 400 TB the spread between Instant Retrieval and Deep Archive is roughly **$1,200/month**, so the retrieval question is worth asking properly rather than defaulting to the cheapest. For a legal hold specifically, **Deep Archive's 12-hour retrieval is usually fine** because legal discovery has lead time - but confirm, because a regulator with a 24-hour response requirement changes it. *Giving up*: retrieval fees and latency, and **Deep Archive has a 180-day minimum storage duration**, which matters if the hold might be lifted early.

**3. Postgres needing 30,000 IOPS → gp3 striped, or io2, and I would verify the number first** (Q21, Q33).

The deciding numbers: **gp3 caps at 16,000 IOPS per volume**, so 30,000 needs either **multiple gp3 volumes striped with LVM** (aggregate the limits, cheapest) or **io2** (single volume, sub-millisecond latency, 99.999 percent durability, considerably more expensive).

I would choose based on two things: **is the requirement latency consistency or raw IOPS?** If p99 latency variance matters, io2. If it is throughput, striped gp3 at roughly a third of the cost. And **check the instance's EBS ceiling first** (Q26) - buying 30,000 IOPS for an instance that can drive 12,000 is pure waste, and this is a common error.

*Giving up*: striping multiplies failure probability across volumes and complicates snapshots. *And the question I would actually ask*: is 30,000 IOPS a measured requirement or a compensation for a missing index? Buying IOPS to fix a query is the most expensive possible solution.

**4. Container image layers → ECR** (Q175).

Not really a storage question - it is a registry question, and the answer is ECR with **lifecycle policies** (untagged images expire after 7 days, keep the last N tagged), **tag immutability** on production repositories, **enhanced scanning**, and **cross-region replication** for multi-region deployments. The storage cost is trivial; the costs that matter are **the NAT gateway charges from pulling** (Q123 - use ECR and S3 endpoints) and **unbounded accumulation** without lifecycle rules. *Giving up*: nothing meaningful; there is no reasonable alternative on AWS.

**5. Clickstream queried monthly → S3 as partitioned Parquet, queried with Athena** (Q159).

Monthly queries mean a running warehouse is unjustifiable. Land it with **Firehose** doing format conversion to Parquet and dynamic partitioning by date (Q162), lifecycle to Infrequent Access after 30 days and Glacier Instant Retrieval after a year, and query with **Athena**.

The deciding numbers are the ones that make Athena viable at all: **partitioning by date plus Parquet plus selecting only needed columns changes the scan by 100-1000x**, which is the difference between a $500 query and a $0.50 one. *Giving up*: query latency (seconds to minutes, not sub-second) and concurrency - fine for monthly analysis, wrong if it later becomes a dashboard, at which point Redshift Serverless becomes the answer.

**Reflect.** The through-line: **four of the five were decided by a single number or constraint** - protocol, retrieval time, the 16,000 IOPS ceiling, and query frequency - and quoting that number is what turns a list of services into a decision. The fifth (ECR) is the reminder that not every storage question is a storage question. And in two of the five, the most valuable contribution was challenging the requirement rather than answering it.

> *Hook: a storage decision where the deciding number was different from what the requester assumed.*

---

### S13. Connectivity for a hybrid enterprise (Q217)

> Three data centres, 40 AWS accounts, a partner requiring private access to one internal API, and a compliance rule that no workload traffic may traverse the public internet.

**Clarify.** What bandwidth per data centre, and is there an existing Direct Connect anywhere? Are the three data centres already interconnected, and do they need to reach AWS independently or through a hub? How many regions? Does "no public internet" include AWS service endpoints (S3, ECR) or only workload-to-workload traffic - because that distinction changes the design substantially? What is the partner's technical capability - are they on AWS? What is the timeline, given Direct Connect lead times?

**Isolate.** Four distinct requirements, three of which have clean standard answers and one of which is the interesting one:

1. **40 accounts to each other** → Transit Gateway.
2. **Three data centres to AWS** → Direct Connect with resilience.
3. **Partner to one internal API** → the interesting one. Peering exposes too much; the internet is forbidden.
4. **No public internet** → VPC endpoints everywhere, and this is the requirement that touches every other decision.

**Decide.**

**Inter-account connectivity: Transit Gateway per region, with route-table segmentation** (Q116, Q118). Forty accounts is far past the point where peering is manageable. Segment with associated/propagated route tables into prod, non-prod and shared services, so production cannot route to non-production at the routing layer rather than by security group.

**Data centre connectivity: Direct Connect at two locations, into a Direct Connect Gateway, with transit VIFs to the TGWs** (Q120, Q121). Two locations gives AWS's **"high resiliency"** model; if the compliance posture demands it, four connections across two locations gives maximum resiliency. **Order immediately** - the lead time is weeks to months and it is the critical path. **Site-to-Site VPN over the internet as an interim and as backup** - and note that a VPN traverses the public internet but is encrypted, so whether it satisfies the compliance rule is a question to settle with the compliance team **early**, in writing. If it does not, the interim connectivity option disappears and the timeline is dictated entirely by the DX lead time. That is the single most important thing to establish in week one.

Verify **path diversity** with the carriers rather than trusting "two circuits" (Q122).

**The partner: PrivateLink** (Q124). This is the right answer for four reasons: it exposes **exactly one service endpoint**, not a network; it is **unidirectional**, so the partner cannot reach anything else; **CIDR overlap is irrelevant**, so the partner's addressing is not our problem; and traffic **never touches the internet**, satisfying the compliance rule natively.

Implementation: the internal API behind an **NLB**, an **endpoint service** with the partner's account in the allowlist, and the partner creates an interface endpoint in their VPC. If the partner is not on AWS, the fallback is **DX or VPN into a dedicated DMZ VPC** with tightly scoped routing - substantially more work and more exposure, which is worth pricing so the partner has an incentive to be on AWS.

*What I explicitly reject*: VPC peering with the partner (exposes the whole network, breaks on CIDR overlap, and gives them a route into our estate), and a public API with IP allowlisting (violates the compliance rule and depends on their egress addressing).

**No public internet: VPC endpoints as a landing zone default.** **Gateway endpoints for S3 and DynamoDB in every VPC** (free), and **interface endpoints** for everything else the workloads use - ECR api and dkr, Systems Manager, Secrets Manager, KMS, CloudWatch Logs, STS. Centralize the interface endpoints in a shared services VPC with **private DNS shared across accounts** where per-VPC endpoints would be too costly (Q123, Q131). Enforce with an **SCP denying the creation of internet gateways and NAT gateways** in workload accounts, so the rule is structural rather than aspirational - and add **endpoint policies** restricting access to your own organization's resources, which closes the exfiltration path (Q123).

**Execute**, in order of lead time:

1. **Week 1**: order Direct Connect at two locations; settle the VPN-versus-compliance question in writing.
2. **Weeks 1-4**: IPAM and CIDR plan (the unrecoverable decision, Q129); Transit Gateway per region; shared services VPC with endpoints; the SCP set.
3. **Weeks 2-6**: VPN as interim connectivity if permitted; TGW route table segmentation; RAM sharing of attachments and Resolver rules.
4. **Weeks 4-8**: PrivateLink endpoint service for the partner, tested end to end with them.
5. **On DX delivery**: transit VIFs, BGP with DX preferred, VPN demoted to backup, **and a tested failover** with the measured throughput degradation documented (Q121).

**Reflect.** Two things I would flag to the sponsor. **The compliance rule has a cost**: VPC endpoints across 40 accounts have an hourly charge, and centralized egress with inspection adds per-GB processing - the rule is right, and it should be budgeted rather than discovered. And **the partner integration is the piece most likely to slip**, because it depends on another organization's timeline and technical capability; I would start that conversation in week one rather than treating it as the last item.

> *Hook: a hybrid connectivity design with a third-party integration, and which requirement turned out to be hardest.*

---

### S14. Six access patterns, one application (Q218)

> Pick the data store for six access patterns in one application, and say what you would give up by forcing them all into one store.

Taking a plausible e-commerce set: **(a)** fetch a customer's order by ID; **(b)** list a customer's orders, newest first; **(c)** full-text search across products with facets; **(d)** a real-time "trending products" leaderboard; **(e)** a session store; **(f)** monthly revenue analysis by region and category.

**Clarify.** What are the volumes and rates for each? What consistency does each require - can search be seconds stale, can the leaderboard be approximate? What is the team's operational capacity, because every additional store is a permanent cost? Is there an existing store already in place? And which of these is on the customer's critical path versus internal?

**Decide, per pattern:**

| # | Pattern | Store | Why |
| --- | --- | --- | --- |
| a | Order by ID | **DynamoDB** (PK `ORDER#id`) | Single-digit-millisecond key lookup at any scale, no capacity management on-demand |
| b | Customer's orders, newest first | **DynamoDB**, same table (PK `CUSTOMER#id`, SK `ORDER#<timestamp>`) | Same table, same query - this is the single-table pattern, and no second store is needed |
| c | Product search with facets | **OpenSearch** | Relevance ranking, faceted aggregation and fuzzy matching are what it exists for; nothing else does it acceptably |
| d | Trending leaderboard | **ElastiCache Redis** (sorted set) | `ZINCRBY`/`ZREVRANGE` is a single operation; approximate and ephemeral by nature |
| e | Session store | **ElastiCache Redis**, or **DynamoDB with TTL** | Redis if already present and latency is critical; DynamoDB with TTL if you want one fewer system and can accept a few more milliseconds |
| f | Monthly revenue analysis | **S3 + Athena** (or Redshift if concurrency demands) | Monthly frequency cannot justify a running warehouse; partitioned Parquet with Athena is orders of magnitude cheaper |

So: **three or four stores**, not six - DynamoDB serves two patterns, Redis serves two, and the analytical pattern is a lake rather than a database.

**The data flow matters as much as the choices**: DynamoDB is the **source of truth**; **DynamoDB Streams** feed OpenSearch (search index) and the S3 lake (analytics) asynchronously. That gives one write path and eventually-consistent derived views, which is the correct shape - the alternative, writing to three stores from the application, creates a distributed-transaction problem nobody wants.

**What you give up by forcing all six into one store** - taken seriously, per candidate:

**All in PostgreSQL/Aurora**: genuinely the most defensible single-store answer, and worth arguing. You get (a), (b) and (e) trivially; (c) via full-text search, which is adequate for modest catalogues and poor at relevance ranking and facets at scale; (d) via a table with an index, which will become a write-contention hotspot; (f) directly, which **puts analytical scans on the transactional database** - the thing that most often takes it down. *You give up*: search quality, leaderboard write throughput, and the isolation between OLTP and OLAP. *You gain*: one system, transactions across all of it, one backup story, one thing to operate, and no eventual-consistency bugs. **For a small team and a moderate scale, this is the right answer**, and saying so is more valuable than reciting six services.

**All in DynamoDB**: (a), (b), (e) excellent. (c) impossible - there is no full-text search, and building it means a scan or a second store anyway. (d) possible but awkward and expensive at high write rates. (f) requires exporting to S3 regardless. *You give up*: two of the six outright.

**All in OpenSearch**: tempting because it can technically serve most of them. *You give up*: durability guarantees (it is not a primary store), transactional semantics, and cost control - and you inherit the operational liability of Q163.

**Reflect.** The judgement being tested is **restraint**. The naive answer picks six specialized services; the good answer picks three or four and **names the consolidation**; the best answer also says **at what scale and team size the single-store answer is correct**. I would present it as: "start with Aurora and Redis - two systems, covers all six adequately - and split out OpenSearch when search quality becomes a product problem, and the lake when analytical queries start affecting the transactional database. Here are the specific signals that trigger each split." **Every additional store is a permanent operational and cognitive cost** (Q164), and the architecture should earn each one.

> *Hook: a polyglot persistence decision, and whether you later consolidated or split further.*

---

### S15. Thirty percent off an EC2 and RDS estate in one quarter (Q219)

> Reduce the cost of an EC2-and-RDS-heavy estate by 30 percent in one quarter without reducing reliability. Sequence the work.

**Clarify.** What is the current monthly spend and its breakdown by service, account and environment? What is the existing commitment coverage and utilization? Is there tagging, and what is its coverage? Is there any CloudWatch agent deployment, or is memory invisible? What is the change appetite - can we touch production this quarter? Is there a planned migration or shutdown that would make commitments a mistake? And who owns the outcome, because a cost programme without an owner does not finish.

**Isolate.** Thirty percent in a quarter is achievable in an untouched estate, and the sequencing matters more than the individual actions. Two sequencing rules dominate:

1. **Eliminate and right-size before committing.** Buying Savings Plans first locks in the waste, and a three-year commitment against a fleet you are about to halve is the worst possible outcome. This is the mistake most cost programmes make.
2. **Take the zero-risk wins first**, because they fund credibility for the riskier ones and deliver savings while the analysis for the rest is still running.

**Decide and execute, in four waves:**

**Weeks 1-2: instrument, and take the free wins.**

*Instrument* (nothing else works without this): install the **CloudWatch agent** everywhere via State Manager so **memory is visible** (Q212) - without it, Compute Optimizer is guessing (Q208); enforce **tagging** and chase the unowned resources; enable **CUR into S3 with Athena** and **Cost Anomaly Detection** (Q209).

*Free wins, no reliability risk whatsoever:*

- **Delete orphans**: unattached EBS volumes, old snapshots, unassociated Elastic IPs, idle load balancers, empty log groups. Typically 2-4 percent.
- **Set retention on every CloudWatch log group** - the default is forever (Q212).
- **gp2 → gp3** across the fleet: ~20 percent off EBS with no performance loss, though **check throughput on large volumes** (Q20). Often 3-5 percent of total.
- **Delete stopped instances** that have been stopped for 30+ days, after owner confirmation.

*Expected: 5-8 percent.*

**Weeks 2-4: non-production scheduling.**

**Shut down non-production outside business hours** (Q213) - tag-driven, opt-out, with a self-service override and a two-week warning period. Non-production is typically 30-40 percent of an estate, and this takes 60-70 percent off its compute. **Aurora Serverless v2 or scheduled stop for non-production databases.**

This is the single largest low-risk item, and it carries **zero production risk by construction**.

*Expected: a further 8-12 percent.*

**Weeks 4-9: right-sizing.**

With 30+ days of memory-inclusive metrics:

- **Generation upgrades** first (`m5` → `m6i`, and Graviton where dependencies allow, Q16): cheaper *and* faster, the lowest-risk change of all.
- **Downsize** where p99 CPU and memory are both well under target across a full business cycle **including month-end**. One size step at a time, non-production first, nothing else changed in the same window.
- **RDS right-sizing** carefully and last - **never from CPU alone**, because memory and buffer cache are the constraint (Q147). Use Performance Insights, not Compute Optimizer, for these.
- **Delete or consolidate** duplicated environments and abandoned workloads.

*Expected: a further 8-12 percent.*

**Weeks 9-12: commit.**

Only now, against the **reduced** floor:

- **Compute Savings Plans** sized to the trailing minimum hourly spend, bought in **tranches** rather than one purchase (Q210). Prefer Compute over EC2 Instance plans for flexibility, and one-year terms for anything that might change.
- **RDS Reserved Instances** for the databases that are demonstrably stable.
- Target **70-85 percent coverage** at ~100 percent utilization, not 100 percent coverage.

*Expected: a further 10-15 percent of remaining spend.*

**How reliability is protected**, since that is the stated constraint and the thing a cost programme most often violates:

- **Track p99 latency, error rate and availability before and after every wave**, and make the cost report include them. A saving purchased with reliability is not a saving.
- **No changes during peak or month-end**, and a change freeze around known business events.
- **One change at a time per workload**, so a regression is attributable.
- **Owner confirmation** before deleting or downsizing anything, with a documented exception process for DR standbys, licence servers and burst-capacity headroom (Q208).
- **Nothing touched** that has a licence tied to instance size or core count without checking the licence.

**Reflect.** Two things. **The sequencing is the answer** - the same four actions in the wrong order (commit first, right-size second) achieves less and locks in mistakes for three years. And **the ongoing mechanism matters more than the quarter**: without monthly Compute Optimizer review, tagging enforced in IaC, cost visibility given to the teams generating the spend, and anomaly detection, the estate re-inflates within a year. I would close the quarter by handing over a **running process**, not a completed project - and report the reliability metrics alongside the saving so the constraint is demonstrably met rather than asserted.

> *Hook: a cost reduction programme, the sequencing you used, and whether the savings persisted.*

---

### S16. DR for an unmodifiable legacy three-tier application (Q220)

> A legacy three-tier application on EC2. RTO 4 hours, RPO 15 minutes. The application cannot be modified.

**Clarify.** What are the three tiers concretely - web, app, and which database? Is the database RDS or self-managed on EC2, because that changes everything? What does "cannot be modified" cover - no code changes, or also no configuration changes, no version upgrades, no AMI rebuilds? Are there hard-coded IP addresses or hostnames anywhere? What is the licence position for a second region? What state lives outside the database - local files, uploads, session state on disk? What is the failback expectation, and has anyone costed the downtime the RTO is protecting against?

**Isolate.** The constraints define the strategy almost completely:

- **RPO 15 minutes** rules out backup-and-restore from daily or hourly snapshots. It requires **continuous or near-continuous replication** of the database.
- **RTO 4 hours** is generous. It rules out needing a hot standby, and specifically **permits a pilot light** - infrastructure defined but not running, with the data layer replicating.
- **"Cannot be modified"** rules out application-level replication, active-active, and anything requiring the app to be region-aware. It also means **session state and local files must be handled at the infrastructure layer**, and this is where legacy three-tier applications usually hide their real DR problem.

Mapping to the four standard strategies: **backup and restore** (RPO too weak), **pilot light** (fits), **warm standby** (over-provisioned for a 4-hour RTO, and more expensive), **multi-site active-active** (impossible without modification). **Pilot light is the answer**, and the reasoning is the RTO/RPO pair.

**Decide: pilot light in a second region.**

```
Primary region                        DR region
--------------                        ---------
Web tier (ASG, ALB)      ---------->  ASG with desired=0, ALB pre-created
App tier (ASG)           ---------->  ASG with desired=0
RDS (Multi-AZ)           ==CRR====>   Cross-region read replica (running)
                                        or Aurora Global Database (headless)
EBS/EFS data             ==sync===>   Replicated (AWS Backup / DataSync / EFS replication)
AMIs                     --copy--->   Replicated
Route 53 failover record with health checks
Everything in IaC, deployed and current in both regions
```

**The database is the critical decision:**

- **If RDS**: a **cross-region read replica**, running continuously. Replication lag is typically well under 15 minutes, which meets the RPO, and promotion takes minutes. Monitor **`ReplicaLag` as a DR-readiness metric**, not just a performance one - the RPO *is* the lag at the moment of failure (Q136).
- **If Aurora**: **Aurora Global Database with a headless secondary** (Q141) - sub-second replication, storage-cost-only until needed, and RTO under a minute for the promotion itself. Strictly better, and the argument for migrating to Aurora if the application permits.
- **If self-managed on EC2**: native replication (PostgreSQL streaming, MySQL replication) to a standby instance in the DR region, plus WAL/binlog archiving to S3 with cross-region replication as a second line. **This is the weakest option and the one I would try hardest to change** - moving to RDS is a platform change, not an application change, so it may well fall inside "cannot be modified".

**The rest:**

- **Compute**: ASGs and launch templates deployed in the DR region with **desired capacity 0**. AMIs copied cross-region on every build (Q180). Cost is near zero until failover, and scaling out is one API call.
- **Non-database state**: this is where legacy applications fail their DR test. **Find it explicitly** - uploaded files, generated reports, local caches, session state on disk. Replicate with **EFS cross-region replication**, **S3 CRR**, or **AWS Backup cross-region copy** depending on where it lives. If session state is on local disk and cannot be moved, accept that failover logs everyone out and **document it** rather than discovering it during a test.
- **Network**: the DR VPC pre-built with **non-overlapping CIDRs** (Q129), security groups, and any hybrid connectivity - a second Direct Connect or VPN into the DR region, which is a lead-time item.
- **DNS**: Route 53 **failover records with health checks**, TTL at 60 seconds. And given the Q88/S4 lesson: expect DNS to contribute several minutes, and **check for hard-coded IPs and JVM DNS caching** in the legacy application, which is exactly the kind of place they live.
- **Everything in IaC**, deployed to both regions continuously, so the DR region does not drift.

**Failover runbook**, as an **SSM Automation document** rather than a wiki page (Q200): promote the replica → scale the app tier ASG → wait for health → scale the web tier ASG → verify → flip the Route 53 record → validate → communicate. Automated end to end, with a manual approval gate at the promotion step because promotion is irreversible.

**Execute and prove it:**

1. Build it in IaC and deploy both regions.
2. **Test the failover quarterly**, in a real drill, and **record the measured RTO and RPO** (Q46). The measured numbers are the real ones; the target is an aspiration until then.
3. Test **failback**, which is harder than failover - it requires reverse replication and is the step people skip until they need it.
4. Track **replication lag as a continuous SLO** with an alarm, since it is the RPO.

**Reflect.** Three things to state to the business. **The pilot light costs roughly 10-20 percent of the primary** - replicated storage, a running replica, copied AMIs, and the DR network - which is the honest price of a 4-hour RTO and is far below a warm standby. **The measured RTO will be longer than the sum of the technical steps** because detection and the decision to fail over are human and typically add 15-30 minutes (Q46), so the runbook should include who decides and on what criteria, agreed in advance. And **"cannot be modified" is the real risk**: the application's hidden assumptions - hard-coded addresses, local state, licence keys tied to a host - are what break DR tests, and the only way to find them is to run the drill. A DR plan for an application that has never been failed over is a document, not a capability.

> *Hook: a DR strategy you designed for a system you could not change, and what the first real drill revealed.*
