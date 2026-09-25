# Database Cheatsheet

Fast revision. PostgreSQL unless another engine is named. Assumes [../01-java/cheatsheet.md](../01-java/cheatsheet.md) and [../02-spring/cheatsheet.md](../02-spring/cheatsheet.md).

---

## Isolation levels and anomalies

| Level | Dirty read | Non-repeatable read | Phantom | Lost update | **Write skew** |
| --- | --- | --- | --- | --- | --- |
| Read Uncommitted | allowed (PG: behaves as RC) | yes | yes | yes | yes |
| **Read Committed** (PG/Oracle/SQL Server default) | no | yes | yes | **yes** | yes |
| Repeatable Read (PG = snapshot isolation) | no | no | no (PG) / no (InnoDB, via gap locks) | no (PG aborts) / **yes (InnoDB)** | **yes** |
| Serializable (PG = SSI) | no | no | no | no | no |

**The ANSI table is incomplete.** It names three phenomena; write skew and lost update are not among them, which is why snapshot isolation can satisfy "Repeatable Read" and still corrupt data.

**Write skew**: two transactions read an overlapping set, each writes a *different* row, no write-write conflict, invariant broken. Doctors on call, double booking, overdraft across two accounts.

Fixes, in order: put the invariant in one statement (`UPDATE ... SET n = n - 1 WHERE n >= 1`) → let the database enforce it (`UNIQUE`, `CHECK`, `EXCLUDE`) → `SELECT ... FOR UPDATE` on what you read → `SERIALIZABLE` with a retry loop.

Retryable SQLSTATEs: **`40001`** serialization failure, **`40P01`** deadlock detected. Retry the **whole transaction**, never one statement.

---

## MVCC in one screen

```
UPDATE = insert new tuple (xmin=me) + set xmax on old tuple
      -> old versions stay until VACUUM
      -> VACUUM may only remove versions older than the OLDEST SNAPSHOT
      -> one long transaction anywhere = bloat EVERYWHERE
```

Pins the xmin horizon: a long transaction, **idle in transaction**, a prepared (2PC) transaction, a replication slot, `hot_standby_feedback` from a replica.

| Engine | Old versions live in | Failure mode |
| --- | --- | --- |
| PostgreSQL | the table | **bloat** |
| Oracle | undo segments | **ORA-01555 snapshot too old** |
| InnoDB | undo log / history list | both, mildly |

Autovacuum triggers at `50 + 0.2 * reltuples` dead tuples. **On a large table that is far too lax** - set `autovacuum_vacuum_scale_factor = 0.01` with a fixed threshold per table.

Wraparound: warn at `age(relfrozenxid)` ~500M, PostgreSQL screams at 40M remaining, refuses writes at 3M. Alert on it.

---

## Lock conflict, short form

| Statement | Table lock |
| --- | --- |
| `SELECT` | `ACCESS SHARE` |
| `INSERT`/`UPDATE`/`DELETE` | `ROW EXCLUSIVE` |
| `VACUUM`, `ANALYZE`, `CREATE INDEX CONCURRENTLY` | `SHARE UPDATE EXCLUSIVE` |
| `CREATE INDEX` (plain) | `SHARE` |
| **`ALTER TABLE`, `DROP`, `TRUNCATE`, `REINDEX`, `VACUUM FULL`** | **`ACCESS EXCLUSIVE`** - conflicts with everything, including `SELECT` |

**The lock queue is fair.** A blocked `ALTER TABLE` blocks every subsequent `SELECT`. Always:

```sql
SET lock_timeout = '2s';   -- then retry with backoff
```

Row locks, weakest to strongest: `FOR KEY SHARE` (what a **foreign key check** takes) < `FOR SHARE` < `FOR NO KEY UPDATE` (plain `UPDATE`) < `FOR UPDATE`.

Deadlock prevention: **consistent lock order** (`ORDER BY id ... FOR UPDATE` up front) and **short transactions**. Deadlock probability grows with the square of duration.

---

## Index decision table

| Need | Index |
| --- | --- |
| Equality, range, `ORDER BY`, uniqueness | **B-tree** |
| Full text, JSONB containment, array membership, trigram | **GIN** |
| Ranges, geometry, `EXCLUDE` constraints, k-NN | **GiST** |
| Huge append-only table ordered by time | **BRIN** (kilobytes for a terabyte) |
| Unanchored `LIKE '%x%'`, fuzzy match | **GIN + `pg_trgm`** |
| Only a subset is ever queried | **partial** (`WHERE status = 'ACTIVE'`) |
| `WHERE lower(email) = ?` | **expression index** |
| Make the scan index-only | key columns + **`INCLUDE`** |

**Column order**: all **equality** columns first, **one range column last**. `a = ? AND b > ? AND c = ?` wants `(a, c, b)`.

Leftmost prefix on `(a,b,c)`: `a`; `a,b`; `a,b,c`. Not `b` alone, and `c` is only a filter after a range on `b`.

**Six ways to kill an index**: function/cast on the column, leading `%`, broken leftmost prefix, type or collation mismatch, unprovable partial-index predicate (a **parameter** does not match `WHERE status='ACTIVE'`), bad or missing statistics.

**Write cost**: `INSERT` = one entry per index. `UPDATE` of an **indexed** column = new entries in **every** index. `UPDATE` of a non-indexed column = **HOT**, no index touched. Adding an index to a hot column destroys HOT for the whole table.

Always `CREATE INDEX CONCURRENTLY` in production. Verify `pg_index.indisvalid` afterwards.

---

## Reading `EXPLAIN (ANALYZE, BUFFERS)`

1. Find the **first bottom-up node where `rows` and `actual rows` diverge** - that is the cause; everything above it is a consequence.
2. `actual time` is **per loop** - multiply by `loops`.
3. `shared hit` vs `read` = cache vs IO.
4. `Rows Removed by Filter` = work thrown away, usually a missing index.
5. Spills: `Sort Method: external merge Disk:`, `Batches: >1`, bitmap `lossy=`. Fix with `SET LOCAL work_mem`.

**Bad estimate, four causes**: stale statistics → correlated columns (fix: `CREATE STATISTICS ... (dependencies, mcv)`) → function/expression in the predicate (fix: expression index or expression statistics) → bad `n_distinct` (fix: `ALTER TABLE ... SET (n_distinct = -0.3)`).

| Join | Wins when |
| --- | --- |
| Nested loop | small outer side, indexed inner side; only option for non-equality and `LATERAL` |
| Hash | large unordered inputs, one side fits `work_mem` |
| Merge | both inputs already sorted on the key |

Cost constants: `seq_page_cost = 1.0`, `random_page_cost = 4.0` **(set 1.1 on NVMe, 1.5-2.0 on network storage)**, `effective_cache_size` = 60-75 percent of RAM.

`work_mem` is **per node, per worker** - not per query. Global 256 MB with 200 connections is an OOM.

**Parameter sniffing / generic plans**: PG plans custom 5 times, then may lock in a generic plan. Fast with a literal + slow with a bind = this. Fix: `SET LOCAL plan_cache_mode = force_custom_plan`.

---

## Durability and WAL

```
COMMIT -> WAL record fsynced (+ standby ack if synchronous) -> client acknowledged
       -> data pages still dirty in memory, written at CHECKPOINT
```

| Setting | You lose | Verdict |
| --- | --- | --- |
| `synchronous_commit = off` | up to ~600 ms of **committed** transactions; stays consistent | legitimate per-transaction trade |
| `full_page_writes = off` | torn-page protection | only with atomic 8 KB storage |
| `fsync = off` | **the database** | never in production |

| Replication mode | RPO | Cost |
| --- | --- | --- |
| async | seconds | none |
| `on` (sync) | 0 | RTT + standby fsync per commit |
| `remote_apply` | 0, and replica reads are current | + replay |
| `ANY 1 (s1, s2)` quorum | 0 | RTT to the fastest - **the sane default** |

**One synchronous standby that dies = the primary stops committing.** Always quorum with two candidates.

`shared_buffers` ~25 percent of RAM in PostgreSQL (OS cache is the second tier); Oracle uses direct IO, so it takes nearly everything.

Checkpoints: `checkpoints_req >> checkpoints_timed` means raise `max_wal_size`. Trade = longer crash recovery.

---

## Replication and recovery

| | Physical / streaming | Logical |
| --- | --- | --- |
| Granularity | whole cluster, block level | selected tables, row level |
| Cross major version | no | **yes** (upgrade path) |
| Subscriber writable | no | yes |
| DDL replicated | yes | **no** |

**Replication slots** guarantee WAL retention - and an abandoned slot fills the disk and pins the xmin horizon. Alert on `active = false` and retained bytes. Set `max_slot_wal_keep_size`.

**Read-your-writes** after adding replicas: sticky-primary window → LSN token routing → `remote_apply` → do not re-read at all. `readOnly = true` means "no writes", **not** "stale is fine".

```
RTO = fetch backup + restore + replay WAL (single-threaded!) + verify + cut over
```

More frequent base backups is the main RTO lever. A **delayed replica** (`recovery_min_apply_delay = '1h'`) is the cheapest protection against a bad `DELETE` - replication copies mistakes instantly, backups take hours to undo them.

Five reasons a "successful" backup will not restore: never tested, WAL archive incomplete, nowhere big enough to restore to, key/credentials gone, missing roles/extensions/config.

---

## Scaling decision order

**Reads**: fix queries and indexes → cache → replicas → materialized views → denormalized read models (CQRS).

**Writes**: reduce writes (batching, fewer indexes, HOT) → scale up → partition → move non-relational workloads out → shard.

"Just add a read replica" for a **write-bound** system makes it worse: every replica applies every write, and `hot_standby_feedback` blocks vacuum on the primary.

| | Solves |
| --- | --- |
| Replication | read scale, HA, DR. **Not** write throughput or size |
| Partitioning | manageability, retention, pruning. **Not** write throughput |
| Sharding | write throughput and size. Costs cross-shard everything |

Shard key must be: high cardinality, evenly distributed **by volume**, present in most queries, aligned with transactions, and immutable. `tenant_id` usually - until one tenant is 30 percent, then a routing **directory** with per-tenant placement.

Partition key must be in **every unique constraint and primary key**. Drop a partition instead of `DELETE` - milliseconds versus hours plus bloat.

---

## Caching

| Pattern | Failure mode |
| --- | --- |
| Cache-aside | stale entry until TTL if invalidation races |
| Write-through | write latency is the sum of both |
| Write-behind | **data loss** if the cache dies |

**Delete the key, do not update it** - ordering between two writers is not guaranteed, and the cached value is usually a projection you cannot recompute correctly at write time.

The permanent-stale race: reader misses → reads V1 → writer updates to V2 and invalidates (nothing there) → reader writes V1. Fix: delayed double delete, or conditional set with a version. **Always set a TTL** so it self-heals.

Jitter: 10-25 percent, so N keys expiring together spread over `2j` seconds instead of one instant.

Stampede: **stale-while-revalidate + single-flight lock**. `@Cacheable(sync = true)` is per-JVM only - with 20 pods you still get 20 loads.

**A 99 percent hit rate means the database is sized for 1 percent of traffic.** A cold cache is a 100x step change plus a retry storm. Warm up, shed load, single-flight, game-day it.

Redis: single-threaded execution, so `KEYS`, `SMEMBERS` on a huge set, and a looping Lua script block **everything**. `allkeys-lfu` for a cache, `noeviction` for a store. `volatile-*` with no TTLs set = OOM errors that look like broken LRU.

Redis lock: `SET key <token> NX PX 30000`, release via Lua compare-and-delete, and a **fencing token** checked at the resource. Redlock's safety assumes bounded clock drift and no long pauses - for correctness, use fencing or idempotency instead.

---

## NoSQL quick reference

**MongoDB**: embed if accessed with the parent, bounded, and updated together; reference otherwise. 16 MB document limit ends the argument. **ESR** index rule = Equality, Sort, Range. Read-your-writes = `w:"majority"` + `readConcern:"majority"` + a causally consistent session. An **arbiter** preserves elections while destroying durability - use three data-bearing members.

**Cassandra**: `((partition key), clustering columns)`; one table per query. Keep partitions under ~100 MB - bucket by time. `R + W > N`; `LOCAL_QUORUM` is fast and **not** cross-DC consistent. Tombstones make deletes into writes; a queue workload produces tombstone storms and aborted reads. LWT = Paxos = 4x latency, use rarely.

**DynamoDB**: write the access-pattern inventory **first**. Single table, overloaded `PK`/`SK`. GSI = eventually consistent, own capacity, and **an under-provisioned GSI throttles the base table**. Per-partition limits are 1,000 WCU / 3,000 RCU regardless of provisioning - a date in the partition key is a guaranteed hot partition. On-demand costs ~6-7x provisioned per unit, so break-even is ~15-20 percent utilization. `TransactWriteItems` = 100 items, 2x write cost. TTL deletes within ~48 h and appears in the stream.

---

## Java data layer

`JOIN FETCH` + pagination = **in-memory pagination of the whole result** (`HHH000104`). Fix: page over ids, then fetch by `id IN (:ids)` with the `ORDER BY` repeated.

Two `List` collections fetched together = `MultipleBagFetchException`. Fix: `Set`, or one collection per query, or `@BatchSize`.

Batching needs `batch_size` **and** `order_inserts`/`order_updates`. **`IDENTITY` generation disables insert batching** - use a pooled sequence. Add `reWriteBatchedInserts=true` for another few times faster.

Streaming a large result needs **autocommit off** + forward-only + `fetchSize > 0`, plus `clear()` every N rows.

**Pool size**: `concurrency = throughput x latency` (Little's Law), and ~`cores * 2` at the server, **summed across all services**. 100 connections queue *inside* the database, where it is far more expensive. 10-20 beats 100.

`maxLifetime` **must be shorter** than the database's, the proxy's and the load balancer's idle timeouts, or you hand out dead sockets.

`statement_timeout` (server) is the only thing that actually stops a runaway query. A JDBC **socket** timeout abandons the socket and leaves the query running.

PgBouncer **transaction mode** forbids: session prepared statements (before 1.21), `SET` outside a transaction, session advisory locks, `LISTEN`/`NOTIFY`, temp tables, `WITH HOLD` cursors.

---

## Zero-downtime migration

**The rule**: old and new code run simultaneously against one schema, so every change must be compatible with both.

```
expand -> dual write + backfill -> switch reads (LAST ROLLBACK POINT) -> stop old writes -> drop (a later release)
```

| Instant (metadata only) | Rewrites / scans the table |
| --- | --- |
| `ADD COLUMN` (no default, or a **non-volatile** default, PG 11+) | `ADD COLUMN` with a **volatile** default |
| `DROP COLUMN`, `RENAME` | `ALTER COLUMN TYPE` (most) |
| `ADD CONSTRAINT ... NOT VALID` | `SET NOT NULL` without a proving `CHECK` |
| `SET NOT NULL` **with** a validated `CHECK` (PG 12+) | `ADD PRIMARY KEY` / `ADD UNIQUE` directly |
| widening `varchar(n)`, `numeric` precision | `CLUSTER`, `VACUUM FULL`, plain `REINDEX` |

`NOT NULL` safely: `ADD CHECK (col IS NOT NULL) NOT VALID` → backfill → `VALIDATE CONSTRAINT` → `SET NOT NULL` → drop the check.

Type change on a big table: new column → **trigger** to sync → batched backfill → indexes `CONCURRENTLY` → switch reads → drop.

Backfill: key-range batches (never `OFFSET`), one transaction per batch, **throttle on replication lag**, persisted cursor, idempotent, killable, with an ETA metric.

`down` scripts are a trap - untested, and they cannot restore destroyed data. **Forward-only, backward-compatible**, with the drop one release behind.

---

## Security and cost

Roles: **owner/migration** (DDL, CI only) / **application** (DML on named tables, no DDL) / **read-only** / **humans**. `ALTER DEFAULT PRIVILEGES` or the app breaks after every migration.

Multi-tenant isolation: application `WHERE tenant_id = ?` is **not** a security control. Add **RLS with `FORCE ROW LEVEL SECURITY`** and a non-owner role, tenant from the verified principal only, `SET LOCAL`, tenant in every cache key and index prefix.

Injection survives in: dynamic `ORDER BY`/identifiers (allow-list), `LIKE` patterns, IN-lists (use `= ANY(?)`), JPQL string building, native queries, `to_tsquery` input.

**TDE protects the disk, not the query.** Anyone who can authenticate gets plaintext. Column encryption is what protects against people; deterministic encryption leaks the equality pattern.

GDPR erasure against immutable stores: **crypto-shredding** (delete the per-subject key), tombstone + compaction, keep personal data out of events and in a deletable profile, and bounded backup retention plus a suppression list on restore.

Cost surprises: cross-AZ transfer, Aurora **per-IO** charges (bad indexes cost money directly), backup storage on a bloated table, forgotten provisioned IOPS, and one GSI per write duplicated.

Cheapest wins before resizing: **delete data** (retention, unused indexes, cold partitions) → **fix the top 5 queries by total time** → buy reservations. Non-production on a schedule is ~60 percent off.

---

## Incident first five minutes

1. Database or application? CPU/IO vs the pool's `pending` and `usage` timers.
2. `pg_stat_activity` - what is running, longest first.
3. **Blocking chain** - `pg_blocking_pids()`. Highest payoff per second.
4. `idle in transaction` ordered by `xact_start`.
5. What changed - deploy, migration, batch job, failover, autoanalyze.

Then: `pg_stat_statements` **sorted by `total_exec_time`, not mean** (rank work, not queries), and the wait-event profile.

Alert on the **leading** indicators: longest transaction age, blocked sessions, connection utilization, slot retained WAL, `age(relfrozenxid)`, dead-tuple ratio, disk trend. Cache hit ratio and replication lag are **lagging** - dashboard them, do not page on them.

Mean latency flat + users unhappy = look at p99 by endpoint and tenant, and at **errors**, which complete fast and improve your mean.

---

## Numbers worth quoting

| | |
| --- | --- |
| B-tree depth for 1 billion rows | 4 levels; the top two are always cached |
| Page size | 8 KB; TOAST above ~2 KB per row |
| Random UUID PK | page splits, bigger index, worse cache - use UUIDv7 |
| Sequential scan vs index crossover | not a fixed percentage - depends on correlation and `random_page_cost` |
| Connection pool | ~`cores * 2`, summed across services; 10-20 not 100 |
| Commit on 1 ms network storage | ~1,000 commits/s per writer without group commit |
| Autovacuum default trigger | 20 percent of the table - far too lax above ~10M rows |
| Redis lock | `SET NX PX` + Lua release + fencing token |
| DynamoDB partition | 1,000 WCU / 3,000 RCU hard limit |
| DynamoDB on-demand | ~6-7x provisioned per unit; break-even ~15-20 percent |
| Cassandra partition | keep under ~100 MB / 100k rows |
| Elasticsearch shard | 10-50 GB; refresh interval 1 s |
| Cache hit rate 99 percent | cold cache = **100x** load on the database |
