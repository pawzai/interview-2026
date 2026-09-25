# Scenario Questions

Data-layer production incidents, architecture exercises and leadership situations.

Every scenario uses **CIDER**, defined in [../01-java/README.md](../01-java/README.md):

- **Clarify** - what you ask before answering. Never diagnose or design in silence.
- **Isolate** - narrow the failure domain or the core requirement.
- **Decide** - commit to an approach and name the trade-off.
- **Execute** - the concrete steps.
- **Reflect** - what you monitor, prevent, or would do differently.

Read the scenario, answer out loud for five minutes, then compare. The model responses are longer than you should speak - use them as the map, not the script.

---

## Part A - Production incidents

### S1. The database is slow and nothing changed

> At 09:40 the API's p99 goes from 120 ms to 8 seconds. Database CPU is at 35 percent, which is normal. No deployment went out. The team is looking at you.

**Clarify.** Is *everything* slow or a subset of endpoints? When did it start, to the minute? Did anything change at that minute - a batch job, a scheduled report, a partner integration, a failover, an autoscaling event? Are error rates up, or just latency? Is the application seeing connection acquisition failures or slow queries? Is this the primary, a replica, or both?

**Isolate.** CPU at 35 percent with 8-second latency means the database is **waiting**, not computing. That narrows it to three families:

1. **Lock contention** - something holds a lock and everything queues behind it. The classic is a `SELECT` holding `ACCESS SHARE` behind which an `ALTER TABLE` queued, blocking all subsequent reads (`answers.md` Q100).
2. **IO wait** - the working set stopped fitting in memory, or storage degraded (a cloud volume exhausting burst credits is the version that "changes nothing").
3. **Waiting outside the database** - the connection pool is exhausted because connections are held rather than used (Q236), in which case the database is genuinely idle and innocent.

**Decide.** I do not theorize; I read the wait profile. `pg_stat_activity` answers all three families in one query, and the blocking-chain query answers the first one definitively.

**Execute.**

1. Run the blocking query (Q260). If there is a chain, find the root, look at what it is, and decide whether to `pg_cancel_backend` it. A single long transaction or a queued DDL is resolved in seconds.
2. Check `state = 'idle in transaction'` ordered by `xact_start`. A six-hour-old one explains bloat, blocked DDL and stalled vacuum simultaneously (Q93).
3. If no locks: compare `shared_blks_read` growth and the storage layer's latency and burst-credit metrics. A volume out of credits is a step change with no deployment.
4. If the database looks healthy: measure the application side - Hikari's `pending` and `usage` timers. Pool exhaustion presents as a database incident and is not one.
5. Check for a new heavy query in `pg_stat_statements` snapshots against yesterday's - a report someone scheduled, or a query whose plan flipped after autoanalyze crossed a threshold (Q78). "Nothing changed" and "statistics were refreshed" are compatible statements.

**Reflect.** The systemic fix is that this diagnosis should not require me. I would add the three leading alerts from Q261 (longest transaction age, blocked session count, connection utilization), put the blocking query in a runbook linked from the alert, set `lock_timeout` and `idle_in_transaction_session_timeout` as role defaults so this class self-heals, and add wait-event sampling so the profile is available retrospectively rather than only while I am watching.

> *Hook: an incident where the cause was a queued DDL, and the guardrail you added afterwards.*

---

### S2. A migration took the site down for eleven minutes

> A release included `ALTER TABLE orders ADD COLUMN customer_ref text`. The migration is documented as instant. The site was down for eleven minutes and recovered on its own when the migration finally completed.

**Clarify.** What else was running at the time? Was there a long-running query or report against `orders`? What is `lock_timeout` set to in the migration session - anything? Did the migration tool wrap several statements in one transaction? How long did the `ALTER` itself take once it started, versus how long it waited?

**Isolate.** The statement genuinely is metadata-only in PostgreSQL 11+ (Q245), so the eleven minutes were **not** the work - they were the wait plus the queue. The sequence is: a long-running `SELECT` held `ACCESS SHARE`; the `ALTER` requested `ACCESS EXCLUSIVE` and queued; PostgreSQL's fair lock queue then made every subsequent query on `orders` queue behind the `ALTER`, including trivial reads that would never have conflicted with the original `SELECT` (Q100). The site recovered "on its own" the moment the long query finished, the `ALTER` executed in microseconds, and the queue drained.

**Decide.** The fix is not to avoid this DDL - it is safe. The fix is to make **lock acquisition** bounded, so a migration can never hold a queue open.

**Execute.**

1. Immediate: add `SET lock_timeout = '2s'` to every migration, with retry-with-backoff around the DDL (Q250). A failed attempt costs nothing; a held queue costs the site.
2. Add a pre-flight check to the migration job: query `pg_stat_activity` for statements older than 30 seconds on the target tables and refuse to start (or report what it is waiting on) rather than queueing blindly.
3. Set `statement_timeout` as a default on the application role so no ordinary query can block DDL for eleven minutes in the first place (Q238). Long reports get an explicit exception with `SET LOCAL`.
4. Add a CI lint that fails any migration containing DDL without a `lock_timeout` (Q256).
5. Post-incident: check whether the long-running query itself should exist. It is often a report that belongs on a replica.

**Reflect.** What makes this incident instructive is that every individual belief was correct - the DDL *is* instant, the query *was* legitimate - and the outage came from the interaction. That is the argument for guardrails over knowledge: the next engineer will not know about the lock queue, and `lock_timeout` protects them anyway. I would also review whether migrations should run in the deployment window at all, versus a quieter scheduled slot for anything touching the largest tables.

> *Hook: a migration outage and the lint rule that came out of it.*

---

### S3. Writes are fine, then everything stops for thirty seconds, every few minutes

> Write latency is normally 4 ms. Every three to five minutes, for about thirty seconds, it goes to 2-3 seconds and a few requests time out. Reads are unaffected. It started after a data migration doubled the table's write rate.

**Clarify.** Is the pattern periodic and regular, or load-correlated? What do the storage write IOPS look like during the spike? What are `max_wal_size`, `checkpoint_timeout` and `checkpoint_completion_target`? What does `pg_stat_bgwriter` show for `checkpoints_timed` versus `checkpoints_req`? Is `synchronous_commit` on, and is there a synchronous standby?

**Isolate.** A regular, periodic write stall with a matching IO burst is a **checkpoint spike** (Q128). The doubled write rate means WAL now reaches `max_wal_size` every few minutes, so checkpoints are *requested* rather than *timed* - `checkpoints_req` will dominate. Requested checkpoints are less spread out, and each one flushes a large volume of dirty buffers; on top of that, the first write to each page after a checkpoint carries a **full page image**, so WAL volume itself spikes after each checkpoint, which brings the next one sooner. It is a feedback loop that arrived with the write-rate change.

The alternative candidates, which the evidence should eliminate: a synchronous standby stalling (Q141 - check `pg_stat_replication` and whether the stall correlates with standby IO), vacuum on a large table, and a burst of WAL archiving.

**Decide.** Convert requested checkpoints back into timed ones and spread the flush, accepting a longer crash-recovery time. That trade is explicitly a dial between steady-state latency and RTO, and I would state the new RTO estimate as part of the change.

**Execute.**

1. Raise `max_wal_size` substantially (enough that `checkpoints_req` goes to near zero) and raise `checkpoint_timeout` to 15-30 minutes.
2. Confirm `checkpoint_completion_target = 0.9` so the flush is spread across the interval.
3. Verify the effect in `pg_stat_bgwriter` and in the latency percentiles, and recompute expected recovery time from the WAL volume per interval.
4. Check WAL disk capacity before raising the limits - a larger `max_wal_size` needs the space.
5. Separately, reduce the WAL being generated: are there indexes that broke HOT updates (Q130), or a batch job writing row-by-row that should batch (Q40)?

**Reflect.** The monitoring gap is that we alerted on latency but not on the leading signal. I would add `checkpoints_req` rate, WAL bytes per minute and checkpoint write volume to the dashboard, with an alert when requested checkpoints exceed timed ones - that is the point to act, weeks before users notice. I would also add a rule to the capacity review: any change that materially raises write volume gets a checkpoint and WAL review, because the settings that were correct at 1x are not correct at 2x.

> *Hook: a periodic latency spike you traced to checkpoints, and the RTO conversation that followed.*

---

### S4. Disk usage is growing and the row count is not

> A 400 GB database is growing 8 GB a week. `SELECT count(*)` on the main tables is flat. Nobody has added features.

**Clarify.** Which relations are growing - `pg_total_relation_size` by table, split into heap, indexes and TOAST? Is `pg_wal` part of the growth? What does `n_dead_tup` look like on the growing tables, and when did autovacuum last run on them? Are there any inactive replication slots? Any long-running transactions? What is the update rate on those tables?

**Isolate.** Flat row count with growing storage is **bloat** or **retained WAL**, and the split is the first thing to establish because the causes are different:

1. **`pg_wal` growing** - an inactive or lagging **replication slot** (Q148), a failing `archive_command`, or a stalled standby. This one ends in a full disk and a hard outage, so it is checked first.
2. **Heap and index growing** - dead tuples not being reclaimed. Either autovacuum cannot keep up with the churn (default `scale_factor` of 20 percent is far too lax on a large table, Q92), or something is **pinning the xmin horizon**: a long transaction, an idle-in-transaction session, an abandoned prepared transaction, a logical slot, or `hot_standby_feedback` from a replica running long reports (Q224).
3. **TOAST growing** - large values being rewritten, or an append-only pattern nobody accounted for.

**Decide.** Fix the cause before the symptom. Reclaiming space while the horizon is still pinned just regrows it.

**Execute.**

1. `SELECT slot_name, active, pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) FROM pg_replication_slots` - drop anything abandoned, and set `max_slot_wal_keep_size` so this cannot recur.
2. Find the oldest transaction in the system, and the oldest `xmin` across `pg_stat_activity`, `pg_prepared_xacts` and `pg_replication_slots`. Remove it, and set `idle_in_transaction_session_timeout`.
3. Per-table autovacuum tuning on the churning tables: `autovacuum_vacuum_scale_factor = 0.01` with a fixed threshold, and a higher `autovacuum_vacuum_cost_limit` so it can actually keep up.
4. Measure the bloat with `pgstattuple` and reclaim it with `pg_repack` (online) rather than `VACUUM FULL`, scheduling the largest tables first (Q95).
5. Check `fillfactor` and whether an index on a hot column has destroyed HOT updates (Q130) - that is often the underlying reason the churn became unmanageable.

**Reflect.** The monitoring should have caught this at week one: dead tuple ratio, time since last autovacuum, oldest transaction age, slot retained WAL and disk growth rate are all leading indicators (Q263), and all of them were moving before the disk did. I would add them with thresholds, add a monthly bloat report, and add "review autovacuum settings" to the checklist for any table crossing a size threshold - because the defaults are a function of table size and nobody revisits them as the table grows.

> *Hook: a bloat incident, the cause that pinned the horizon, and what the settings look like now.*

---

### S5. Deadlocks after a release

> Since yesterday's release, the error log has 200-400 `deadlock detected` errors per hour. Before, there were none. The release added a feature that updates two related tables.

**Clarify.** What do the deadlock log entries say - which two statements, which locks, which tables? Is it always the same pair? Is the new feature the one involved, or is it deadlocking with a pre-existing path? Are the failures user-visible, or is something retrying successfully? What is the isolation level, and is this PostgreSQL or MySQL?

**Isolate.** PostgreSQL's deadlock log prints both statements and the locks each holds and wants, which usually names the answer outright. The families (Q98, Q99, Q119):

1. **Inconsistent lock ordering** between the new code path and an existing one - the most likely, given the timing. Two transactions touching the same two rows or tables in opposite order.
2. **Batch statements whose row order differs** - `UPDATE ... WHERE id IN (...)` locks in plan order, which can differ between two sessions (Q99).
3. **Lock upgrade** - both transactions take a shared lock and then try to upgrade.
4. **Foreign key locks** nobody wrote - inserting a child takes `FOR KEY SHARE` on the parent (Q97), so the cycle can involve locks that appear in no statement.
5. On MySQL, **gap locks** from a check-then-insert pattern (Q118).

**Decide.** Deadlocks are a correctness-preserving mechanism - the database is protecting the data. So the immediate priority is to stop them being *user-visible* (retry), and the real fix is ordering discipline. I would do both, in that order, because they have different lead times.

**Execute.**

1. Same day: add a bounded retry with jitter around the affected operation for `40P01` - a deadlock victim's transaction is always safe to retry (Q103), provided the body has no non-database side effects. This converts errors into slightly slower successes.
2. Read the log entries and identify the two paths. Impose a canonical order: sort the entity ids before writing, and fix a global order across entity *types* (always `account` before `ledger_entry`).
3. Where a transaction touches a known set of rows, acquire them upfront in one statement: `SELECT ... WHERE id = ANY(?) ORDER BY id FOR UPDATE`.
4. Shorten the transaction - move any non-database work out of it, which reduces the collision window quadratically.
5. Add a metric for deadlock rate so the fix is verifiable rather than believed.

**Reflect.** The gap is that the release was reviewed for correctness but not for **lock order**, and no test exercised concurrent access to the new path. I would add a concurrency test for any feature that writes more than one table in a transaction (two threads, opposing order, asserting no deadlock), and add "what locks does this take, in what order" to the review checklist for transactional code. I would also make retry-on-`40P01` a framework-level default rather than a per-feature decision, so the next feature inherits it.

> *Hook: a deadlock storm, the ordering rule you introduced, and how you made retries the default.*

---

### S6. Users see their own updates disappear

> After a release that added read replicas, users report that saving a profile appears to work, but the next page shows the old values. It happens perhaps one time in five, more often at peak.

**Clarify.** Which reads go to replicas, and how is that decided? What is the replication lag at peak, measured how? Is the write and the subsequent read in the same user session and the same second? Do we have a session-affinity mechanism? Is this all endpoints or only the ones the release touched?

**Isolate.** This is a textbook **read-your-writes violation** (Q143): the write committed on the primary and the follow-up read was served by a replica that had not applied it yet. "One in five, worse at peak" fits exactly - lag grows with write volume, so the race widens under load.

The specific trap to name is that the routing was almost certainly driven by Spring's `@Transactional(readOnly = true)`, which means "this method does not write", not "stale data is acceptable" (Q145). Those are different statements, and conflating them is what shipped the bug.

**Decide.** Fix it in the routing layer as an explicit policy, not endpoint by endpoint. Short term I want the bug gone today; medium term I want a mechanism that cannot be got wrong by the next feature.

**Execute.**

1. Today: route the affected read paths to the primary, or add a **sticky-primary window** - after a write, that session reads from the primary for N seconds (a flag in the session or a signed cookie). Cheap, imprecise, and it removes the customer impact immediately.
2. Then: implement **LSN token routing** - capture `pg_current_wal_insert_lsn()` after each write, carry it in the session, and have the router send the read to a replica only if `pg_last_wal_replay_lsn() >= token`, otherwise to the primary. This is precise and it scales.
3. Separate the two concepts in the codebase: `readOnly` stays a transaction attribute, and a new explicit annotation or routing hint declares the **staleness tolerance** of a read. Default to the primary; opting into staleness is a deliberate act.
4. Pin each session to one replica so users do not also see **non-monotonic** reads (Q144).
5. Add replica lag to the dashboard with an alert, and make the router eject a replica above a hard threshold.

**Reflect.** The deeper issue is that "add read replicas" was treated as an infrastructure change when it is a **consistency model change** for the whole application. I would write down the guarantees the platform offers (read-your-writes within a session, bounded staleness elsewhere), implement them once centrally, and add an integration test that writes then immediately reads through the real routing layer with an artificially lagged replica. Also worth reflecting: the write response already contained the correct data, and the cheapest fix of all is often not re-reading at all.

> *Hook: the replica rollout that broke read-your-writes, and the routing policy you built afterwards.*

---

### S7. The cache restarted and took the database with it

> A Redis node was replaced during routine maintenance. Within 40 seconds the database was at 100 percent CPU, the application's connection pools were exhausted, and the site was down. It stayed down for 20 minutes, well after Redis was back.

**Clarify.** What was the cache hit rate before the event? What is the database's steady-state query rate versus its capacity? Does the application retry on timeout, and with what backoff? Is there a concurrency limit or circuit breaker in front of the database? Did Redis come back empty, and was there any warm-up? Why did it stay down after Redis returned?

**Isolate.** Two mechanisms compounded.

1. **Cold cache load amplification** (Q178). At a 99 percent hit rate, a cold cache multiplies database read load by 100x instantly. The database was correctly sized for the *miss* rate, which means it was 100x under-provisioned for this moment.
2. **Metastable failure.** The reason it stayed down after Redis returned is that timeouts triggered retries, retries added load, the added load caused more timeouts, and the system found a stable state at zero throughput. Meanwhile every request that timed out never populated the cache, so the cache stayed cold - the recovery mechanism was starved by the failure. This is the amplification pattern from `03-microservices` Q116.

**Decide.** Two separate fixes are needed, and confusing them is why this recurs: one prevents the cold cache, the other prevents a cold cache from being fatal. The second matters more, because there will always be an event you did not plan for.

**Execute.**

1. **Stop the retry amplification**: bounded retries with exponential backoff and jitter, a retry budget (retries capped as a fraction of total requests), and a circuit breaker in front of the database so that when it is saturated, requests fail fast instead of queueing.
2. **Single-flight** at the cache layer: N concurrent misses for the same key become one database query, with the others waiting or serving stale (Q177). This alone would have cut the burst enormously, because a cold-start burst is highly concentrated on the hot keys.
3. **Bound the load on the database independently of the cache**: a concurrency limiter (the connection pool sized as a bulkhead, Q235) plus load shedding that returns a degraded response rather than queueing.
4. **Make cold starts rare and gradual**: Redis persistence or a replica promotion instead of an empty node, a warm-up job that preloads the top-N keys before the node takes traffic, and slow-start in the load balancer.
5. **Game day**: kill the cache in a controlled test and confirm the system degrades rather than collapses.

**Reflect.** The framing I would take to the review is that a 99 percent hit rate is not a strength, it is a **dependency**: it means the database is sized for one percent of the traffic, and the cache is now a hard dependency masquerading as an optimization. I would put the cold-cache multiple on the capacity dashboard explicitly - "if the cache is lost, the database receives 100x" - and treat any increase in hit rate as an increase in blast radius, not just a win. That reframing is what makes the investment in shedding and single-flight easy to justify.

> *Hook: a cold-cache collapse and the amplification controls you added.*

---

### S8. A DynamoDB partition is throttling

> An order-processing service on DynamoDB starts throttling at 11:00 every weekday. Consumed capacity is at 40 percent of provisioned. The table is on-demand for reads and provisioned for writes.

**Clarify.** Which operations are throttled - table writes, or a GSI? What is the partition key, and what is the distribution of values? Does 11:00 correspond to a batch job, a partner feed, or a business peak? Are there hot *items* or hot *key ranges*? What does CloudWatch Contributor Insights show for the top partition keys?

**Isolate.** Provisioned capacity is a table-level number but it is consumed **per partition**, and each physical partition has hard limits of 1,000 WCU and 3,000 RCU regardless of provisioning (Q207). Forty percent overall with throttling means the traffic is concentrated. The likely shapes:

1. A **time-based partition key** (`ORDER#2026-09-01`) so every write for the day lands on one partition - and 11:00 is simply the point where the day's rate crosses the limit.
2. A **whale key** - one large merchant or tenant.
3. A **GSI** whose provisioned capacity is lower than the write rate it must absorb, which back-pressures the base table and throttles writes to a table that is itself fine (Q206). This is the one that most often looks inexplicable.

**Decide.** Diagnose which of the three before changing anything, because the remedies are different and expensive to undo. Contributor Insights answers it in minutes.

**Execute.**

1. Enable Contributor Insights and identify the top partition keys by consumed capacity. Check the GSI's throttle metrics separately from the table's.
2. If it is a GSI: move it to on-demand or provision it well above the base table's write rate, and question whether the indexed attribute is too low-cardinality to be a sensible GSI key.
3. If it is a time-based key: **remove time from the partition key**. Move the date to the sort key and use a business identifier as the partition key, or add a shard suffix (`ORDER#2026-09-01#03` over N shards) with parallel reads.
4. If it is a whale: shard that key specifically, or use a write-sharded aggregate (Q113) if the hot item is a counter.
5. Short term while the model change ships: switch writes to on-demand (which absorbs bursts far better than auto-scaling, Q208) and add client-side retry with exponential backoff and jitter, which the SDK does by default but is often misconfigured.

**Reflect.** The root cause is a **key design** decision, and the lesson is that in DynamoDB the key is the capacity plan. I would add the access-pattern inventory (Q205) to the design review for any new table, add per-partition throttle alerting rather than relying on aggregate capacity, and be explicit in the team's guidance that any key containing a date or a monotonic value is a hot partition waiting for growth.

> *Hook: a hot partition you found and the key redesign that fixed it.*

---

### S9. A restore drill misses its RTO by a factor of six

> The documented RTO is one hour. The quarterly drill restores the 2 TB production database in six hours and fifteen minutes. The business was told one hour.

**Clarify.** Where did the time actually go - fetching the backup, decompressing, restoring, replaying WAL, or verification and cutover? How old was the base backup relative to the recovery target? Is the backup logical or physical? What is the restore target's instance class and storage throughput? Was the restore parallelized? Is the one-hour RTO a business requirement or a number someone wrote down?

**Isolate.** Break the six hours into its components (Q152), because each has a different lever:

- **Fetching** 2 TB from object storage - bounded by network throughput; parallelizable.
- **Restoring/decompressing** - bounded by CPU and local disk write throughput; parallelizable with pgBackRest's process count.
- **WAL replay** - **single-threaded** and usually the dominant term if the base backup is old. A weekly base backup with 100 GB of WAL per day means up to 700 GB to replay at perhaps 100 MB/s, which is two hours on its own.
- **Verification and cutover** - often forgotten in the plan and significant in reality.

If it is a `pg_dump` restore, the answer is different again: index rebuilds dominate, and that architecture cannot meet a one-hour RTO at this size at all (Q151).

**Decide.** RTO is bought, not declared. I would present the cost of each hour of improvement and let the business choose - and in parallel correct the documented number today, because a wrong RTO in a plan is worse than an honest one.

**Execute.**

1. **Reduce WAL replay** by taking base backups far more frequently - daily or twice daily, or use incremental backups. This is usually the biggest single win and the cheapest.
2. **Parallelize** the fetch and restore (pgBackRest `--process-max`), and restore to storage with enough write throughput; the restore target is often under-specified because it is "only a drill".
3. **Change the architecture if the RTO demands it**: a warm standby with automated promotion gives an RTO in seconds to minutes and is the honest answer to a one-hour requirement (Q156). Backups then serve the *logical corruption* case, which has a different and more forgiving RTO.
4. Add a **delayed replica** (Q149) so the most common recovery - a bad delete or migration - takes minutes rather than a full restore.
5. Automate the drill and publish the measured time each quarter as a metric, not a report.

**Reflect.** The valuable outcome is not the fix, it is that the drill existed and produced a number - most organizations discover this during the incident. I would make three changes to how we work: RTO and RPO are stated with the *measured* evidence next to them, any change that affects WAL volume or database size triggers a re-measurement, and the drill includes the full path (application start, smoke test, DNS) rather than just the database, because the last mile is where the other surprises live.

> *Hook: a restore drill that failed its target, and what you changed to hit it.*

---

### S10. One query's plan flipped overnight

> A query that ran in 40 ms for two years now takes 90 seconds. The code has not changed. It started at 03:15. Restarting the application does not help; running it with a literal instead of a parameter makes it fast again.

**Clarify.** What ran at 03:15 - a batch load, `ANALYZE`, autovacuum, a partition rollover, a minor version upgrade? Is the query prepared (server-side) and executed many times per session? What does the plan look like now versus what it presumably was? What is the parameter's distribution - is one value very common and another very rare?

**Isolate.** "Fast with a literal, slow with a parameter" is a **generic plan** problem (Q72, Q75). PostgreSQL plans a prepared statement with the actual values for five executions, then compares the average custom-plan cost against a generic plan and, if the generic plan is not more expensive, locks it in. On a **skewed** column that generic plan is good for the average value and catastrophic for the ones your traffic actually uses.

Why now: something changed the statistics at 03:15 so that the generic plan's estimated cost dropped below the custom average - a bulk load changing the distribution, an autoanalyze refreshing the MCV list, or a new partition shifting `reltuples`. The code did not change; the cost comparison did.

The adjacent candidates to rule out: stale statistics after a bulk load (Q66 - check `last_autoanalyze`), a dropped or invalid index, and a correlation the planner cannot see (Q70).

**Decide.** Two horizons. Restore service now with the smallest safe change, then remove the class of problem so it does not recur on a different query.

**Execute.**

1. Confirm the diagnosis: `EXPLAIN (ANALYZE, BUFFERS)` for the parameterized form and the literal form, side by side. Look for the row-estimate divergence, and check `pg_stat_statements` for when the mean stepped up.
2. Immediate mitigation, in order of preference: `SET LOCAL plan_cache_mode = force_custom_plan` for that transaction; or disable server-side prepares for that statement; or run `ANALYZE` with a higher statistics target on the skewed column, which may make the generic plan good enough (Q69).
3. If the estimate is wrong because of correlated predicates, add extended statistics (Q70).
4. Consider whether the query should be reshaped so the good plan is the only cheap plan - usually an index that makes the selective path obvious.
5. Re-measure and record the plan, so the next regression has a baseline to diff against.

**Reflect.** The gap is detection: this ran for hours before anyone connected the latency to a plan. I would add `auto_explain` with a duration threshold so the actual plan of a slow execution is captured automatically, snapshot `pg_stat_statements` on a schedule so per-query latency is trendable, and alert on a step change in a query's mean time rather than only on overall latency. I would also note the honest limitation of the platform here (Q78): PostgreSQL has no plan baselines, so stability comes from statistics quality and query shape rather than from pinning - which is a reason to keep an eye on the queries whose parameters are skewed.

> *Hook: a plan regression, how you detected it, and the monitoring you added.*

---

## Part B - Design exercises

These are the worked answers to Q279-284 in [questions.md](questions.md). Design out loud for five to ten minutes before reading. In an interview, spend the first two minutes on Clarify - a candidate who starts drawing before asking about scale has already lost most of the marks.

### S11. Multi-tenant SaaS data layer at 5,000 tenants (Q279)

> Design the data layer for a B2B SaaS platform growing from 300 to 5,000 tenants. Tenants range from 5 users to 3,000. Some enterprise customers demand contractual data isolation. The team is 25 engineers across five services.

**Clarify.** What is the total data volume and the distribution across tenants - is the largest tenant 100x the median or 10,000x? What is the write rate, and is it steady or batch-driven? What do the enterprise isolation demands actually say - separate database, separate encryption key, separate region, or just an attestation? Is there any cross-tenant query requirement (internal analytics, benchmarking features)? What are the per-tenant backup and restore expectations? Can a tenant be migrated between placements with a maintenance window, or must it be online?

**Isolate.** The core tension is that **the model that scales to 5,000 tenants (shared schema) is not the model that satisfies contractual isolation (database per tenant)**, and picking one for everybody makes either the long tail unaffordable or the enterprise deals unwinnable. The second-order requirement, which is the one that actually bites, is that **migration between placements must be routine**, because tenants grow and contracts change.

**Decide.** A **tiered placement model** with a routing directory, following the pool/bridge/silo pattern:

- **Pool** - shared schema with `tenant_id` on every table, for the long tail. This is the default and where 95 percent of tenants live.
- **Silo** - a dedicated database (and, if required, a dedicated encryption key and region) for enterprise tenants who pay for it. Same schema, same code, same migration pipeline.
- No **bridge** (schema-per-tenant) tier: it gives the migration cost of silo with the isolation of pool, and at 5,000 tenants the catalog and migration overhead is unpleasant (Q254, Q255).

The trade I would state: the tiered model costs a routing layer and a tenant-migration tool up front, and buys the ability to say yes to an enterprise deal without a re-architecture.

**Execute.**

1. **Routing directory** - a small, highly cached, highly available lookup from tenant to connection target, consulted at the start of every request. Placement is data, not configuration, so moving a tenant is a row change plus a data move.
2. **Tenant context established once**, at authentication, from the verified principal - never from a request parameter (Q270). Propagated as a request-scoped value and applied as `SET LOCAL app.tenant_id` at transaction start.
3. **Row-level security** on every table in the pool, with `FORCE ROW LEVEL SECURITY` and a non-owner application role (Q269). This is the control that makes a forgotten `WHERE` clause return zero rows instead of everyone's data - and at 25 engineers, someone will forget.
4. **`tenant_id` as the leading column** of every index that matters, and in every cache key, message key and search document.
5. **Noisy-neighbour control**: per-tenant rate limiting at the API, `statement_timeout` on the application role, and a per-tenant query-cost metric so one tenant's report cannot consume the pool. Promotion to silo is the escalation path for a tenant that outgrows the pool - which is a commercial conversation as much as a technical one.
6. **Migrations** run once per placement through the same pipeline, parallelized across silos, backward compatible always (Q243), with a per-placement version table so partial rollout is visible.
7. **Per-tenant restore** for the pool is the hard case: solve it with a logical export path (extract one tenant's rows into a staging schema from a PITR clone) and rehearse it, because it *will* be asked for after a tenant deletes their own data.

**Reflect.** What I would monitor: per-tenant data volume and query cost (to spot the tenant about to become a problem), placement distribution, migration duration per placement, and RLS policy coverage as a CI check. The decision I would revisit at 10,000 tenants is whether the pool needs to become several pools (shards), which the routing directory makes an incremental change rather than a rewrite - and that is the main reason the directory exists from day one rather than a config file.

> *Hook: a multi-tenant model you designed or migrated, and the first enterprise deal that tested it.*

---

### S12. An audit and event store at 50,000 writes per second (Q280)

> Design an audit store taking 50,000 events per second, retained for seven years, with occasional ad-hoc investigation queries ("everything user X did in March 2024") and a regulatory requirement that records are tamper-evident.

**Clarify.** What is the average event size - 500 bytes or 5 KB? That is the difference between 25 MB/s and 250 MB/s, and between 5 TB and 50 TB per year. Is 50k the peak or the average, and what is the peak-to-average ratio? What is the acceptable ingest latency, and may events be lost on a crash or is durability required per event? What are the query patterns - by subject, by time, by event type, full text? What is the acceptable query latency for an investigation: seconds, or "we'll get back to you tomorrow"? Does tamper-evident mean append-only storage, cryptographic chaining, or a third-party attestation? And who can read it - because that changes the security design more than the storage does.

**Isolate.** Three requirements pull in different directions: **ingest** wants an append-optimized, partitioned, cheap-per-byte path; **seven-year retention** wants object storage at pennies per GB; **ad-hoc investigation** wants an index, which is expensive at this volume. Trying to satisfy all three in one system is the failure mode - either you pay for a hot index over 50 TB of cold data, or investigations take a full scan.

**Decide.** A **tiered pipeline** with one ingest path and three storage tiers, plus a narrow index that spans them:

1. **Ingest**: append to a log (Kafka or Kinesis), partitioned by subject id so per-subject ordering is preserved. The log absorbs bursts, decouples producers from storage, and gives replay for free. At 50k/s with 1 KB events this is unremarkable for Kafka.
2. **Hot tier** (last 30-90 days): a columnar or time-series analytics store - ClickHouse, or the warehouse - partitioned by day and sorted by `(subject_id, timestamp)`. Investigations of recent activity are the common case and are answered in seconds.
3. **Cold tier** (everything): Parquet in object storage, partitioned by `year/month/day`, sorted by subject within each file so predicate pushdown skips row groups (Q220), registered as an Iceberg table so it can be queried by Athena/Trino without a restore (Q221).
4. **A subject index**: a small mapping from subject id to the (partition, file) locations containing their events, so "everything user X did in March 2024" is a bounded set of file reads rather than a scan of a month. This is the piece that makes the cold tier usable and the piece teams usually omit.

**Tamper evidence**: hash each event with the previous event's hash to form a per-partition chain, and periodically publish the chain head to a separate system (an append-only ledger, or simply a signed digest to a different account with object-lock retention). That gives detectability without requiring exotic storage. Object Lock / WORM on the cold tier with a compliance retention period covers the "cannot be deleted" requirement, and it must be applied in an **account with different credentials** from the one that writes.

**Execute.** Ingest with idempotency (a deterministic event id so replay does not duplicate), batch writes into the hot tier in micro-batches of a few seconds, run the Parquet conversion as a scheduled compaction job producing files of 128-512 MB (not thousands of small ones), expire hot-tier partitions on schedule, and verify the chain periodically as a job that alerts on a break.

**Reflect.** What I would watch: ingest lag on the log, compaction backlog, small-file count in the lake (the classic silent degradation), query latency by tier, and cost per TB per tier. The thing I would push back on during design is the retention itself (Q278) - "seven years of everything" is often "seven years of a legally defined subset, and 90 days of the rest", and establishing that distinction is worth more than any technical optimization here.

> *Hook: an event or audit store you built, its volume, and what retention actually cost.*

---

### S13. A global read-heavy product catalogue (Q281)

> Design storage for a product catalogue serving users in Europe, North America and Asia. Reads are 10,000 per second globally and latency-sensitive; writes are a few hundred per day from an internal admin tool, and the admin must see their change immediately.

**Clarify.** How large is the catalogue - 10,000 products or 50 million? How much staleness is acceptable for shoppers: seconds, a minute, an hour? Are there per-region variations (price, availability, legal restrictions) or is it one global dataset? Is search part of this, or a separate system? Is any part of the read path personalized (which would defeat shared caching)? What is the consequence of showing a stale price - a display issue, or a legal one?

**Isolate.** The workload is extremely asymmetric: reads exceed writes by roughly a million to one, and the two paths have opposite requirements. The shopper path wants **low latency, high volume, tolerant of seconds of staleness**; the admin path wants **strong consistency, trivial volume**. Designing one system that satisfies both means over-engineering the read path or under-serving the admin. The other constraint is geography: no amount of database tuning fixes 150 ms of speed-of-light latency between Singapore and Frankfurt, so the data must be *near* the reader.

**Decide.** **A single-writer primary with globally distributed read copies, and a separate admin read path that goes to the primary.**

- **Write path**: one regional primary (PostgreSQL) as the source of truth, with the full relational model, constraints and admin workflow. A few hundred writes per day needs nothing more.
- **Distribution**: on commit, publish the changed product as a document via the outbox or CDC (Q216), into a per-region read store - a document store or a read replica per region, and behind it a CDN for the truly cacheable responses.
- **Read path**: shoppers read the local region's copy. Staleness is the propagation delay, typically under a second, and bounded by monitoring.
- **Admin path**: the admin tool reads and writes the **primary** directly, so it always sees its own writes with no special mechanism. This is the move that removes the hardest requirement almost for free - and it is available because admin volume is negligible.
- **CDN** in front for anonymous catalogue pages, with cache keys that include region and locale, and **explicit purge on publish** so a price change propagates in seconds rather than at TTL expiry (Q190).

**Execute.** Version each product document so an out-of-order update cannot overwrite a newer one; make the publish idempotent; add a reconciliation job comparing the primary against each region's copy by checksum, with a drift metric and a targeted repair path; give the admin tool a "publish" action with a visible propagation status so the human knows when shoppers can see it; and keep a per-region staleness metric (write timestamp to read-visible timestamp) as an SLI.

**Reflect.** The trade I would state plainly is that I have chosen **eventual consistency for shoppers and strong consistency for the admin**, and that this is legitimate only because a shopper seeing a one-second-old description is harmless. If the business says a *price* change must be globally atomic - a legal requirement in some markets - the design changes: prices move to a separately versioned artefact with an effective-from timestamp, published ahead of time and activated by clock, which is how retail actually solves it. That is the question I would make sure to ask before drawing anything.

> *Hook: a globally distributed read model you built, and the staleness you had to negotiate.*

---

### S14. An analytics read path that must not touch the primary (Q282)

> The business wants dashboards and ad-hoc analysis over operational data. The OLTP primary is already at 60 percent CPU at peak and has caused two incidents this year. Data may be up to five minutes stale.

**Clarify.** How many concurrent analysts and dashboards, and what is the query shape - a fixed set of aggregates, or genuinely ad-hoc SQL? What data volume is in scope - the whole database or a dozen tables? Do the analysts need row-level detail or aggregates? Who owns the metric definitions? Is five minutes a real requirement or an aspiration (Q226)? Is there an existing warehouse, and what is the appetite for another piece of infrastructure?

**Isolate.** The requirement is really three: **isolation** (analytics must not consume OLTP capacity), **query shape** (scans and aggregates, which a row store serves badly), and **freshness** (five minutes, which rules out a nightly batch and does not require streaming). The trap is to solve only the first by pointing the BI tool at a read replica - which isolates CPU but brings the query-cancellation problem (Q224), still uses a row store for scan workloads, and puts an uncontrolled workload one `hot_standby_feedback` setting away from damaging the primary.

**Decide.** **CDC from the primary into a columnar analytics store, with a modelled semantic layer on top.**

1. **Capture**: logical decoding via Debezium on a dedicated replication slot (with `max_slot_wal_keep_size` set so a stalled connector cannot fill the primary's disk - Q148). CDC rather than query-based extraction, because it does not scan the source and it captures deletes.
2. **Land**: raw change events into the analytics store or object storage, then merge into current-state tables. At this scale the warehouse's own merge (or an Iceberg table with upserts) is enough; micro-batch every one to two minutes to hit the five-minute target with margin.
3. **Model**: a curated layer of tested SQL models (dbt or equivalent) producing conformed dimensions and fact tables, with slowly-changing dimensions where history matters (Q218, Q219). This is where metric definitions live, and it is the part that determines whether anyone trusts the numbers.
4. **Serve**: dashboards read **pre-aggregated rollups**, never raw facts, so a dashboard load is hundreds of rows. Ad-hoc analysts get the curated layer with a query cost limit.

**Execute.** Start with the 10-15 tables the dashboards actually need rather than replicating everything; add freshness monitoring as a first-class SLI (a heartbeat row written to the source and measured at the destination); reconcile row counts and key checksums nightly with a drift alert; handle schema changes in the source explicitly, since logical decoding does not replicate DDL (Q150) and an unhandled column addition is the most common pipeline break; and give the analytics store its own budget and owner.

**Reflect.** The organizational point matters as much as the technical one: the two incidents this year happened because analytics and operations shared a system with no boundary, and the fix is a boundary, not a tuning exercise. I would define who owns freshness, who owns metric definitions and who is allowed to run arbitrary SQL, and I would keep a deliberately unglamorous fallback - a read replica with a low `statement_timeout` - for the genuinely one-off investigation that does not justify a model. The sequencing I would propose is to run the replica-plus-summary-tables version first for a quarter, because most dashboards are rebuilt twice before the definitions stabilize, and building the pipeline before the definitions is how you get an expensive pipeline serving the wrong numbers.

> *Hook: an analytics path you separated from OLTP, and what it did to the primary's incident rate.*

---

### S15. Data separation for extracting an orders service (Q283)

> A monolith has four modules - orders, inventory, billing and reporting - all reading and writing the same PostgreSQL schema, with foreign keys and joins across all of it. The orders module is to become its own service. 200 million order rows.

**Clarify.** Which tables does orders genuinely own, and which does it merely read? What are the actual cross-module joins in production, ranked by frequency - not what the model implies, but what `pg_stat_statements` shows? Are there cross-module transactions, and what invariants do they protect? What is the acceptable consistency between orders and the others afterwards - can inventory see an order one second late? What is the deadline, and is there an appetite for a period of dual running?

**Isolate.** The hard part is not the code, it is that **the foreign keys and joins encode invariants nobody has written down**. Splitting the data converts compile-time and transactional coupling into runtime and temporal coupling (`03-microservices` Q61), and the question is which of those invariants must survive as strong consistency, which become eventually consistent, and which turn out not to be invariants at all.

The order of operations is also fixed by risk: **code first, data last** (`03-microservices` Q224). Splitting the tables before the code is isolated leaves you with a distributed system *and* a monolith.

**Decide.** A strangler-style separation with the data move last and reversible at every step.

**Execute.**

1. **Establish the boundary in code, inside the monolith.** Orders becomes a module with an explicit interface; every cross-module access to orders' tables is routed through it. This is the step that discovers the real coupling, and it is entirely reversible. Enforce it with an architecture test that fails the build on a direct table reference.
2. **Break the read joins.** For each cross-module join, decide: does the other module need a *copy* of the data (denormalize a few columns, kept in sync by events), an *API call* (acceptable if it is not in a hot loop), or was the join only serving a report (in which case it moves to the analytics path, S14)? Do this while everything is still in one database, so each change is independently verifiable.
3. **Break the write transactions.** For each cross-module transaction, either keep both writes on one side of the boundary (often the right answer - the boundary was wrong), or convert it to a saga with compensations plus an outbox for the event (`03-microservices` Q83, Q90). Every conversion needs an explicit answer to "what does the system look like between the two steps".
4. **Remove the cross-boundary foreign keys**, replacing each with a documented reconciliation check that alerts on orphans. This is the moment the database stops enforcing the invariant, so the alert is not optional.
5. **Move the data.** Logical replication of the orders tables to a new database, running until lag is negligible; the new service reads from the new database in shadow mode and its results are compared against the monolith's; then writes cut over per traffic slice with the ability to route back.
6. **Decommission** the old tables only after a retention period, with a backup of the dropped tables taken deliberately.

**Reflect.** The measures I would watch during the migration: orphan counts from the reconciliation checks, saga completion and compensation rates, p99 of the paths that became network calls, and replication lag during the move. The judgement call I would flag to stakeholders is step 3 - each transaction converted to a saga is a *business* decision about what the system may show a user in an intermediate state, and it needs a product owner, not an architect, to sign it off. And the honest possibility to keep open is that step 2 reveals the boundary is wrong: if orders and inventory change together in most releases, the correct outcome of this exercise is to keep them together and split something else (`03-microservices` Q5).

> *Hook: a service extraction you led, the invariant the foreign key was hiding, and what you found in step 2.*

---

### S16. Bookings and recommendations over the same entities (Q284)

> A travel platform needs transactional bookings (no double-booking, payment consistency, audit) and a recommendation feature that scores and ranks the same inventory using behavioural data. Both are user-facing, both are latency-sensitive.

**Clarify.** What is the booking volume versus the recommendation query volume - probably a 100:1 ratio, which matters enormously? How fresh must recommendations be with respect to availability: may we recommend something that just sold out, and what is the user experience if we do? How large is the inventory, and how large is the behavioural dataset? Is the recommendation model computed offline and served, or computed at request time? What is the latency budget for a recommendation response? Is there a legal or financial consequence to a double booking (yes, always) and to a bad recommendation (usually not)?

**Isolate.** The two workloads have opposite characteristics and must not share a system: booking is **write-contended, strongly consistent, low volume, and correctness-critical**; recommendation is **read-heavy, high volume, tolerant of staleness, and quality-critical rather than correctness-critical**. The shared entity - inventory - is what tempts people to use one store, and the failure mode of doing so is that a recommendation scan competes with a booking transaction for the same rows and the same buffer pool.

**Decide.** **A transactional core plus a derived read model, with the availability check as the seam.**

- **Bookings** on PostgreSQL. The double-booking invariant is enforced by the database, not the application: an `EXCLUDE USING gist (resource_id WITH =, during WITH &&)` constraint makes overlapping reservations impossible regardless of concurrency (Q12), which is far stronger than a check-then-insert under any isolation level (Q84). Payment consistency via the outbox and a saga with the payment provider; audit via a temporal or append-only design (Q14).
- **Recommendations** served from a derived read model - a document or key-value store keyed by user or by context, holding pre-scored candidate sets, refreshed by an offline scoring pipeline and updated incrementally from behavioural events. Serving is a key lookup, so latency is predictable and the load never touches the booking database.
- **The seam**: recommendations are allowed to be *stale about availability*, and the booking flow performs the **authoritative availability check at the point of intent** - when the user clicks through, and again transactionally at confirm. Showing a recommendation for something that just sold out is acceptable if the next screen handles it gracefully; the reverse, selling something twice, is not.
- **Freshness**: availability changes propagate to the read model via CDC or the outbox within seconds, so the window is small and bounded, and hot items can be filtered at serve time against a small, cheap availability cache.

**Execute.** Build the availability check as a single service-owned operation used by both paths so there is one definition; make the recommendation pipeline's input the same event stream that feeds analytics (one pipeline, several consumers); measure the "recommended but unavailable" rate as a product metric, because it is the direct measure of whether the staleness budget is right; and load-test the booking path with the recommendation traffic present, since the whole point of the design is that they do not interact.

**Reflect.** The reasoning I would want an interviewer to hear is the classification: **one invariant is a hard constraint enforced by the database, everything else is a quality metric with a staleness budget**. Once you say that out loud, the architecture follows - the hard constraint gets a small, boring, transactional store, and the quality metric gets a derived model optimized for reads. The failure mode I would call out is the opposite instinct, which is to make recommendations strongly consistent "to be safe": it couples the two systems, puts scan traffic on the booking database, and buys nothing a user can perceive.

> *Hook: a system where you separated a hard invariant from a soft one, and the constraint you pushed into the database.*

---

## Part C - Leadership situations

No model answer is scripted for Part C in the sense of a correct technical response - these assess judgement, influence and how you behave when the answer is not yours to choose. Use **STAR-L** and keep each to two or three minutes. The notes below are the *shape* of a strong answer, not a script.

### S17. A team refuses to add the index

> A team owns a table that is causing lock waits across a shared database. You are not their manager. Their tech lead believes the problem is your service's query and declines to change anything before their next planning cycle, six weeks away.

**Shape of a strong answer.** Lead with **evidence, not authority**: bring the plan, the wait profile and the measured impact on both services, and frame it as a shared problem rather than an accusation - the fastest way to lose this is to arrive with a verdict. Then separate the *immediate* mitigation (something you can do on your side today: a query rewrite, a rate limit, moving a report to a replica) from the *root* fix, and offer to do the work yourself - "I'll write the migration, you review it" removes the capacity objection, which is usually the real objection. If they are right that your query is at fault, say so immediately and loudly; being visibly willing to be wrong is what makes the next conversation easy.

Escalate only with a specific ask and a deadline, and escalate to a *shared* forum rather than up a management chain. The systemic reflection is that this conflict exists because a shared database has no ownership model - the durable outcome is a written contract for who owns which table and what the response expectation is for a cross-team performance issue, not a win in this instance.

> *Hook: a cross-team performance dispute, how you resolved it, and what you changed so it did not recur.*

---

### S18. You are the incident commander and the database is down

> A storage failure has taken the primary offline. Failover has not completed cleanly. Twelve people are in the call, the CEO has joined, and two engineers are proposing different recovery actions.

**Shape of a strong answer.** The technical content matters less than the structure. Establish **roles** immediately - you are commanding, not typing; one person drives the database, one writes the timeline, one owns communications. Establish the **facts** before the actions: what is the current state of the primary and each replica, what is the last known good LSN, is there any chance of a second writer (Q147). Then make the **decision explicit and single-threaded**: two engineers running different recovery actions on the same cluster is how a recoverable incident becomes a data-loss incident, so state the chosen path, name who executes it, and have everyone else stop.

Communicate on a fixed cadence with what you know, what you are doing and when you will next update - and give the business an honest RPO estimate rather than an optimistic one, because the number they hear first is the one they plan around. Preserve evidence before destructive steps (a snapshot of both nodes before any rewind). Say "I don't know yet, here is how we will know" rather than speculating in front of the CEO.

Afterwards: a blameless review with a timeline, and the observation that the interesting questions are usually about **detection and decision latency**, not about the storage failure.

> *Hook: an incident you commanded, the decision you made with incomplete information, and what the review changed.*

---

### S19. The team treats the database as someone else's problem

> You join a team of eight strong Java engineers. Nobody reads plans, migrations are written by whoever is nearest, and the phrase "the database is slow" appears in three retrospectives in a row.

**Shape of a strong answer.** Do not start with training - start by making the **feedback loop short**, because capability follows visibility. Put the top queries by total time on a dashboard the team sees daily, and make the plan of a slow query appear automatically in the logs (`auto_explain`). Then work one real problem end to end with an engineer pairing, and let the result speak: a query taken from 900 ms to 12 ms in an afternoon converts more people than a lunch-and-learn.

Then institutionalize it in the places work already flows through: the migration lint in CI (which teaches by failing with an explanation), a "what does the plan look like" line in the PR template for anything touching a query, and a rotating role that reviews the week's slowest queries. Write down the five things that cause 80 percent of the incidents in this codebase, specific to it, rather than a general database guide nobody reads.

The measure of success is not that everyone can recite MVCC; it is that the team catches its own problems before you do, and that "the database is slow" gets replaced in retrospectives by a specific query name.

> *Hook: a team whose database competence you raised, what you did first, and how you knew it worked.*

---

### S20. The product owner's requirement needs a data model rewrite

> Six weeks before a launch, the product owner asks for a feature that requires versioning every entity - full history, point-in-time queries, and the ability to correct the past. The current model has none of it, and 40 tables.

**Shape of a strong answer.** First, **separate the requirement from the implementation**: "full history" from a product owner usually means one of three things - an audit trail ("who changed this"), an undo feature, or genuine bitemporal correction ("what did we believe in March") - and they cost wildly different amounts (Q14). Find out which by asking what decision the feature supports and who uses it. Very often the answer is an audit table on four tables, not versioning on forty.

Then **price the options honestly and in their terms**: the cheap version, what it does and does not give, and when; the full version, and what it displaces. Do not present a single number, and do not present "impossible" - present the trade. Offer a **staged path**: the audit trail now (which is additive, low risk and ships before launch), the schema shaped so versioning can be added per entity later, and the full bitemporal model for the entities that genuinely need it, after launch.

The leadership content is refusing both failure modes - the heroic yes that misses the launch, and the flat no that makes engineering a wall. And the reflection is usually about *when* this requirement should have surfaced: a regulatory or audit requirement discovered six weeks before launch is a discovery-process problem, and the durable fix is a data-requirements checklist (retention, history, erasure, residency) applied at the start of a project rather than at the end.

> *Hook: a late requirement you re-scoped, what you shipped instead, and how the conversation went.*
