# Database Interview Questions

Questions are numbered continuously (`Q1`, `Q2`, ...) so that [answers.md](answers.md) can reference them directly.

Difficulty legend:

- `[C]` Core - you must answer this instantly and correctly.
- `[D]` Deep - expected of a senior engineer, requires mechanism-level detail.
- `[T]` Tricky - designed to catch you out; the obvious answer is usually wrong.
- `[A]` Architect - no single right answer, judged on trade-off reasoning.

Each category opens with an **Assumed known** line pointing at the `01-java`, `02-spring` and `03-microservices` questions this material builds on. If those are shaky, go back before continuing.

The relational material is anchored on PostgreSQL, with Oracle, MySQL/InnoDB and SQL Server contrasts wherever the mechanism differs. Say the engine you are describing; interviewers notice when you do.

---

## 1. Data modeling, keys and constraints

> Assumed known: `01-java` Q108-109 (DDD, hexagonal architecture) and `03-microservices` Q61 (database per service).

1. `[C]` Walk up the normal forms to BCNF with one example per level, and state the anomaly each one removes.
2. `[D]` Denormalization: name four distinct techniques, and for each, the invariant you now have to maintain in application code.
3. `[T]` "We denormalized for performance" - what evidence would you demand before accepting that, and what is the usual real cause of the slow query?
4. `[D]` Natural versus surrogate primary keys. Give the case where a natural key is clearly right and the case where it is clearly fatal.
5. `[D]` Auto-increment/sequence versus UUIDv4 versus UUIDv7/ULID as a primary key. Compare index locality, page splits, storage and replication behavior.
6. `[T]` Why does a random UUID primary key hurt an InnoDB clustered index more than a PostgreSQL heap table, and what does it still cost in PostgreSQL?
7. `[D]` Composite primary keys versus a surrogate plus a unique constraint. What changes for foreign keys, indexes and ORMs?
8. `[D]` Where do you enforce an invariant - database constraint, application code, or both? Give your rule and the cases that break it.
9. `[D]` Foreign keys in production: the locking they take on writes, the indexes they require, and the argument some teams make for dropping them.
10. `[T]` A foreign key with no index on the child column. What operation becomes catastrophically slow, and why does nothing warn you?
11. `[D]` Nullable columns: the three-valued logic consequences, the storage cost, and why "NULL means unknown" is not how most schemas use it.
12. `[D]` `CHECK` constraints, `EXCLUDE` constraints and unique partial indexes. Give a use case each that the others cannot express.
13. `[D]` Soft delete: the four ways to implement it, and what each one does to unique constraints, foreign keys and query correctness.
14. `[D]` Temporal data - valid time versus transaction time. How do you model a bitemporal table and what does querying "as of" cost?
15. `[T]` Storing money, timestamps and enumerations. Give the wrong choice most teams make for each and the concrete bug it produces.
16. `[D]` `TIMESTAMP WITH TIME ZONE` in PostgreSQL does not store a time zone. Explain what it does store and how to model a future appointment correctly.
17. `[D]` The EAV pattern: when is it defensible, what does it cost in the optimizer, and what are the alternatives?
18. `[D]` JSONB as a column type: what you gain, what you lose, how it is indexed, and the rule you use to decide between a column and a key in a document.
19. `[T]` A table with 180 columns, most of them null. What is wrong beyond aesthetics, and what does it do to the storage layer?
20. `[A]` Single-table inheritance, class-table inheritance and concrete-table inheritance. Which do you default to and why?
21. `[A]` You inherit a schema with no foreign keys, no constraints and `varchar(255)` everywhere. What do you change first, and how do you sequence it without stopping feature work?

---

## 2. SQL beyond CRUD

> Assumed known: basic `SELECT`, `JOIN`, `GROUP BY` and the ability to read a query. This category is about the parts that separate an application developer from someone who owns the data layer.

22. `[C]` `INNER`, `LEFT`, `RIGHT`, `FULL` and `CROSS` joins, plus semi-join and anti-join. Which SQL constructs produce the last two?
23. `[T]` Moving a predicate from the `ON` clause to the `WHERE` clause of a `LEFT JOIN` changes the result. Explain exactly why.
24. `[D]` `NOT IN`, `NOT EXISTS` and `LEFT JOIN ... IS NULL` for an anti-join. Which is wrong in the presence of NULLs, and which does the optimizer handle best?
25. `[D]` `UNION` versus `UNION ALL` versus `OR` in a `WHERE` clause. When is rewriting an `OR` as a `UNION ALL` a real optimization?
26. `[D]` Logical query processing order (`FROM`, `WHERE`, `GROUP BY`, `HAVING`, `SELECT`, `ORDER BY`, `LIMIT`) and the practical consequences - why you cannot reference a `SELECT` alias in `WHERE`.
27. `[D]` `HAVING` versus `WHERE` versus a filtered aggregate (`COUNT(*) FILTER (WHERE ...)`). Which do you reach for and why?
28. `[D]` Window functions: explain `PARTITION BY`, the frame clause, and the difference between `ROWS` and `RANGE` frames.
29. `[D]` `ROW_NUMBER`, `RANK`, `DENSE_RANK`, `LAG`, `LEAD`, `NTILE` - give a real reporting requirement that needs each.
30. `[T]` Write the "top N per group" query two ways, and explain which one the planner handles better and why.
31. `[D]` Common table expressions: when is a CTE an optimization fence, and how does that differ between PostgreSQL 11 and 12+, and versus MySQL?
32. `[D]` Recursive CTEs - the anchor/recursive structure, cycle protection, and one graph problem you would solve this way.
33. `[D]` `LATERAL` joins (`CROSS APPLY` in SQL Server): what problem do they solve that a plain join cannot?
34. `[D]` `GROUPING SETS`, `ROLLUP` and `CUBE`. What do they save over `UNION ALL` of separate aggregates?
35. `[D]` `INSERT ... ON CONFLICT` (upsert) in PostgreSQL versus `MERGE` versus `INSERT IGNORE`. Compare the concurrency behavior of each.
36. `[T]` Two concurrent upserts on the same key. What actually happens under Read Committed, and how can you still get a unique-violation error?
37. `[D]` `RETURNING` and data-modifying CTEs. Show how to move a row between tables atomically in one statement.
38. `[D]` Offset pagination versus keyset (seek) pagination. Give the exact query for keyset pagination over a non-unique sort column.
39. `[T]` `SELECT COUNT(*)` on a 200-million-row table takes 40 seconds. Explain why, in PostgreSQL specifically, and give three acceptable answers to "how many rows are there".
40. `[D]` Set-based thinking versus row-by-row: rewrite a "loop and update" procedure as a single statement, and say when the loop is genuinely better.
41. `[A]` Where does business logic in stored procedures and triggers belong in 2026? Give your position and the strongest argument against it.

---

## 3. Indexing

> Assumed known: `01-java` Q159 (composite index column order, covering indexes, why an index is ignored).

42. `[C]` Describe the structure of a B+tree index and why the depth stays small - give the arithmetic for a billion-row table.
43. `[D]` Clustered versus non-clustered index. How does an InnoDB secondary index lookup differ from a PostgreSQL index lookup?
44. `[D]` The leftmost-prefix rule for composite indexes. Given `(a, b, c)`, list precisely which predicates can use the index and how far.
45. `[T]` For a query with `WHERE a = ? AND b > ? AND c = ?`, what is the best column order for the index, and why is `c` nearly useless where it is?
46. `[D]` Index-only scans and PostgreSQL's visibility map. Why does an index-only scan sometimes still hit the heap, and what makes it stop?
47. `[D]` `INCLUDE` columns (covering indexes) versus adding the column to the key. What differs in size, ordering and uniqueness?
48. `[D]` Partial (filtered) indexes: give three high-value uses and the query-shape requirement that makes them usable.
49. `[D]` Expression indexes and why `WHERE lower(email) = ?` needs one. What does this do to the planner's statistics?
50. `[T]` Name six ways to make an existing index unusable by a query, without dropping it.
51. `[D]` Selectivity and cardinality. At what selectivity does a sequential scan beat an index scan, and why is the answer not a fixed percentage?
52. `[D]` Bitmap index scans in PostgreSQL - what problem they solve, what `lossy` means in the plan output, and how `work_mem` affects them.
53. `[D]` GIN, GiST, SP-GiST, BRIN and hash indexes. Give the workload each one is the right answer for.
54. `[D]` Full-text search inside PostgreSQL: `tsvector`, `tsquery`, GIN indexing, and where you would move to a dedicated search engine instead.
55. `[D]` Trigram indexes (`pg_trgm`) for `LIKE '%foo%'`. How do they work and what do they cost on write?
56. `[D]` The write cost of an index: what happens on `INSERT`, on `UPDATE` of an indexed column, and on `UPDATE` of a non-indexed column (HOT).
57. `[D]` Index bloat: how it happens, how you measure it, and `REINDEX CONCURRENTLY` versus rebuilding the table.
58. `[T]` A table has 14 indexes. What is the fastest defensible way to decide which to drop, and what must you check before dropping any?
59. `[D]` Unique indexes and how a deferred unique constraint changes concurrency. When do you need deferrable?
60. `[D]` `CREATE INDEX CONCURRENTLY` - what it costs, why it can fail leaving an invalid index, and the operational procedure around it.
61. `[T]` You add the perfect index and the query gets *slower*. Give three genuine mechanisms by which this happens.
62. `[A]` What is your standing index policy for a team - who approves them, what evidence is required, and how do you prevent index sprawl?

---

## 4. The optimizer and query tuning

> Assumed known: Category 3, and `01-java` Q159.

63. `[C]` Walk through the stages a SQL statement passes: parse, rewrite, plan, execute. What is cached at each stage in PostgreSQL versus Oracle?
64. `[D]` How does a cost-based optimizer choose a plan? Explain cost units, `seq_page_cost`, `random_page_cost` and why the default ratio is wrong on SSD.
65. `[D]` Reading `EXPLAIN (ANALYZE, BUFFERS)`: what do `cost`, `rows`, `actual time`, `loops`, `shared hit` and `read` each tell you, and in what order do you read them?
66. `[T]` The plan says `rows=1` and `actual rows=4,200,000`. What is the first thing you check, and what are the four most common causes of a row-estimate error that large?
67. `[D]` Nested loop, hash join and merge join. State the cost model, the memory behavior and the condition under which each wins.
68. `[T]` A nested loop over 2 million rows appears in the plan. Is that always wrong? Explain when it is optimal.
69. `[D]` What statistics does the planner keep, how does `ANALYZE` collect them, and what is `default_statistics_target` actually controlling?
70. `[D]` Extended statistics (`CREATE STATISTICS`) for correlated columns. Give the query shape that needs them and the error they fix.
71. `[D]` Histogram, most-common-values list and `n_distinct`. Which one fails first on a skewed column, and how do you fix a bad `n_distinct`?
72. `[T]` Parameter sniffing (SQL Server) and generic versus custom plans (PostgreSQL prepared statements). Describe the failure and every available fix.
73. `[D]` Predicate pushdown, join reordering, subquery flattening and view merging. Which optimization does a CTE or a `LIMIT` block?
74. `[D]` Why does a function in a `WHERE` clause defeat an index, and what do `IMMUTABLE`, `STABLE` and `VOLATILE` change about planning?
75. `[T]` A query is fast with a literal and slow with a bind parameter. Explain both directions of this problem.
76. `[D]` `work_mem`: what uses it, what happens when a sort or hash exceeds it, and why setting it globally high is dangerous.
77. `[D]` Parallel query: when the planner chooses it, what a Gather node does, and why the speedup is sublinear.
78. `[D]` Plan regression after a data load or a version upgrade. How do you detect it, and what are your options for stabilizing a plan in PostgreSQL versus Oracle?
79. `[D]` Query hints: PostgreSQL deliberately has none. What do you do instead, and what does `pg_hint_plan` cost you?
80. `[T]` A query is slow only in production. List the causes you would check in order, given the same data volume in staging.
81. `[A]` A 200-line reporting query is at 90 seconds and the business wants 5. Give your full method, in order, and the point at which you stop tuning and change the architecture.

---

## 5. Transactions, isolation and MVCC

> Assumed known: `01-java` Q120-122 (propagation, rollback rules, isolation levels) and `03-microservices` Q63 (the C in CAP versus the C in ACID).

82. `[C]` ACID, precisely. For each letter, name the mechanism in the engine that provides it.
83. `[D]` The ANSI isolation levels and the anomalies they permit. Then explain what the ANSI table gets wrong.
84. `[D]` Snapshot isolation: how it differs from serializable, and what write skew is. Give a concrete correctness bug.
85. `[T]` Two doctors are on call; each checks "at least one other on call" and drops themselves, concurrently. Which isolation levels allow both to succeed, and give three fixes.
86. `[D]` PostgreSQL's Serializable Snapshot Isolation: what it detects, what it costs, and what your application must handle.
87. `[T]` PostgreSQL Repeatable Read and MySQL Repeatable Read are not the same thing. Give two behaviors that differ.
88. `[D]` Read Committed in PostgreSQL: what happens to an `UPDATE` that finds a row modified by a concurrent uncommitted transaction?
89. `[T]` Under Read Committed, a `SELECT` inside an `UPDATE ... WHERE` sees a different snapshot than the outer statement. Explain the lost-update scenario this creates.
90. `[D]` MVCC in PostgreSQL: `xmin`, `xmax`, tuple visibility, and why `UPDATE` is a delete plus an insert.
91. `[D]` Contrast PostgreSQL MVCC with Oracle's undo segments and InnoDB's undo log. Which one gets "snapshot too old" and which gets bloat?
92. `[D]` Autovacuum: what it actually does, the three thresholds that trigger it, and how to tell it is losing.
93. `[T]` A single idle-in-transaction session for six hours. Explain the chain of damage in precise terms.
94. `[D]` Transaction ID wraparound: the mechanism, the warnings, and what the emergency procedure is.
95. `[D]` `VACUUM` versus `VACUUM FULL` versus `pg_repack`. What locks does each take and when do you use which?
96. `[C]` PostgreSQL table-level lock modes and the conflict matrix. Which everyday statements take `ACCESS EXCLUSIVE`?
97. `[D]` Row locks, `FOR UPDATE`, `FOR NO KEY UPDATE`, `FOR SHARE`, `FOR KEY SHARE`. Which one does a foreign-key check take, and why does that matter?
98. `[D]` Deadlocks: how the engine detects them, which transaction is chosen as victim, and the two canonical prevention techniques.
99. `[T]` A deadlock between two transactions that update the same rows in the same order. How is that possible?
100. `[D]` Lock queues: why one blocked `ALTER TABLE` can block every subsequent `SELECT` on that table.
101. `[D]` `NOWAIT`, `SKIP LOCKED` and `lock_timeout`. Give the correct use of each.
102. `[D]` Two-phase commit and XA: the protocol, the in-doubt transaction problem, and why you should avoid it in a microservice estate.
103. `[T]` Your application catches a serialization failure. What is the *only* correct response, and what must be true of the transaction for that response to be safe?
104. `[A]` What isolation level do you set as the application default, and how do you handle the operations that need more?

---

## 6. Application-side concurrency and queueing

> Assumed known: Category 5, `01-java` Q154 (optimistic versus pessimistic locking) and `02-spring` Q79, Q133.

105. `[D]` Optimistic locking with a version column: the exact SQL, what the retry loop must look like, and where the pattern breaks.
106. `[T]` Optimistic locking with a `updated_at` timestamp instead of a version counter. Give two ways this silently loses updates.
107. `[D]` Pessimistic locking with `SELECT ... FOR UPDATE`: lock duration, ordering discipline, and the throughput ceiling it creates.
108. `[D]` When do you choose pessimistic over optimistic? Give the contention arithmetic that decides it.
109. `[D]` Write the SQL for a work queue using `FOR UPDATE SKIP LOCKED`, including claim, visibility timeout and retry.
110. `[T]` Why is a database-backed queue often the right answer, and at what point does it stop being one? Be specific about the failure mode.
111. `[D]` PostgreSQL advisory locks: session versus transaction scope, and a real use for each. How do they differ from a row lock?
112. `[D]` Implementing a distributed leader election or a singleton scheduled job with only the database. Compare against ShedLock and ZooKeeper.
113. `[D]` Counters at high contention: row lock, `UPDATE ... SET n = n + 1`, sharded counters, and an approximate counter. Compare throughput and correctness.
114. `[D]` Idempotency at the storage layer: the idempotency-key table design, the unique constraint, and how you handle a retry that arrives while the first request is still in flight.
115. `[T]` An `INSERT ... ON CONFLICT DO NOTHING` returns zero rows. What are the three possible states of the world, and how do you distinguish them?
116. `[D]` The transactional outbox at the SQL level: table design, index, the relay query, and cleanup. What ordering does it guarantee?
117. `[D]` `LISTEN`/`NOTIFY` in PostgreSQL: delivery semantics, the payload limit, and why it is not a replacement for a queue.
118. `[D]` Gap locks and next-key locks in InnoDB. Give a deadlock they cause that does not exist in PostgreSQL.
119. `[T]` Two transactions insert then update the same logical entity in opposite order. Show the deadlock and give the fix that does not require changing the isolation level.
120. `[D]` Long-running batch jobs against an OLTP table: how do you avoid blocking, bloat and replication lag all at once?
121. `[A]` A team wants to hold a database transaction open across a user's multi-step wizard. Talk them out of it, and give them a design that works.

---

## 7. Storage internals and durability

> Assumed known: Category 5 (MVCC) and `01-java` Q84 (memory areas), for the analogy to buffer management.

122. `[C]` Describe the page/block structure of a heap table, and what a tuple header contains.
123. `[D]` The buffer pool / shared buffers: how pages are found, the eviction strategy, and why PostgreSQL relies on the OS page cache as well.
124. `[D]` Sizing `shared_buffers`, `effective_cache_size` and the OS cache. Why is "give the database 90 percent of RAM" wrong for PostgreSQL and right for Oracle?
125. `[D]` Write-ahead logging: the protocol, what `COMMIT` waits for, and what is actually durable when the client gets its acknowledgment.
126. `[D]` `synchronous_commit = off`, `fsync = off` and `full_page_writes`. What exactly do you lose with each, and which is never acceptable?
127. `[T]` A `COMMIT` returned successfully and the row is gone after a power loss. Give every layer at which this could have happened.
128. `[D]` Checkpoints: what triggers them, what a checkpoint spike looks like in metrics, and how you smooth it.
129. `[D]` TOAST: when a value is toasted, the four storage strategies, and the performance surprise a large `text` column creates.
130. `[D]` HOT updates and `fillfactor`. Which updates qualify as HOT, and how does an index on a frequently updated column destroy this?
131. `[D]` Table bloat versus index bloat: how each is created, measured and fixed, and why disk usage does not fall after a `DELETE`.
132. `[D]` B-tree versus LSM tree. Compare write amplification, read amplification, space amplification and compaction behavior.
133. `[T]` "LSM is faster for writes." Under what workload is that false, and what does compaction do to your p99?
134. `[D]` Row store versus column store: physical layout, compression ratios, and the query shapes each destroys.
135. `[D]` Compression: page-level, column-level and dictionary encoding. What does it buy beyond disk, and what does it cost on CPU?
136. `[D]` How is durability achieved on cloud storage? Explain Aurora's log-structured approach and why it claims to avoid full page writes.
137. `[T]` Your database is on network-attached storage with a 1ms round trip. Which specific operations become the bottleneck, and what do you tune?
138. `[D]` Temporary files and spilling to disk: which operations spill, how you detect it, and the two ways to stop it.

---

## 8. Replication, high availability and recovery

> Assumed known: `03-microservices` Q62, Q66, Q71 (consistency models, consensus, quorums).

139. `[C]` Physical (streaming) versus logical replication. What each replicates, what each cannot do, and the version-compatibility rules.
140. `[D]` Asynchronous, synchronous and quorum-based synchronous commit. State the RPO of each and the latency cost.
141. `[T]` `synchronous_standby_names` with one standby, and that standby dies. What happens to your primary, and what does that teach you about synchronous replication?
142. `[D]` Replication lag: the three ways to measure it, what causes it, and why a lag of zero bytes can still mean stale reads.
143. `[T]` A user updates their profile and immediately sees the old value. Explain the mechanism and give four fixes ranked by cost.
144. `[D]` Read-your-writes, monotonic reads and consistent prefix at the level of a single database with replicas. How do you actually implement each?
145. `[D]` Routing reads to replicas: where the decision belongs, how you handle staleness bounds, and what breaks in a transaction.
146. `[D]` Failover: automatic versus manual, the role of Patroni/etcd or RDS multi-AZ, and what fencing/STONITH prevents.
147. `[T]` Split brain after a network partition between primary and standby. Describe how two primaries accept writes and how you recover.
148. `[D]` Replication slots: what problem they solve, and the operational danger they create.
149. `[D]` Cascading replication, delayed replicas and why a delayed replica is a genuinely useful backup.
150. `[D]` Logical replication and CDC: how logical decoding works, what a publication/subscription is, and the DDL limitation.
151. `[D]` Backups: full, incremental, `pg_dump` versus physical base backup, and why a `pg_dump` is not a backup strategy at scale.
152. `[D]` Point-in-time recovery: the WAL archive, the recovery target, and the arithmetic that determines your real RTO.
153. `[T]` Your backups have succeeded every night for two years. Give five reasons you may still be unable to restore.
154. `[D]` RPO and RTO: define them, and show how the architecture changes as RPO goes from 24 hours to 5 minutes to zero.
155. `[D]` Multi-region: active-passive, active-active, and the specific reason active-active relational writes are so hard.
156. `[A]` Design the HA and DR posture for a system with a 15-minute RTO and near-zero RPO, and state what it costs.

---

## 9. Partitioning, sharding and distributed SQL

> Assumed known: `03-microservices` Q73 (sharding, hot shards, consistent hashing) and Category 8 here.

157. `[C]` Partitioning versus sharding versus replication. Define each and say which problem each actually solves.
158. `[D]` Range, list and hash partitioning in PostgreSQL. Give the workload that suits each.
159. `[D]` Partition pruning: when it happens at plan time versus execution time, and the query shapes that defeat it entirely.
160. `[T]` You partition a table by month and the queries get slower. Give three realistic reasons.
161. `[D]` What must a partition key satisfy to be included in a primary key or unique index, and what does that do to your model?
162. `[D]` Detaching, attaching and dropping partitions. How does this turn data retention from a `DELETE` problem into a metadata operation?
163. `[D]` Choosing a shard key: the four properties you evaluate, and the failure produced by getting each one wrong.
164. `[T]` You sharded by `customer_id` and one customer is 30 percent of the volume. What are your options, ranked?
165. `[D]` Resharding a live system: consistent hashing with virtual nodes, double-writing, and how you verify before cutover.
166. `[D]` Cross-shard queries, joins and transactions. What do you give up, and what patterns keep you out of that territory?
167. `[D]` Distributed SQL: how Spanner, CockroachDB and YugabyteDB achieve serializable transactions across nodes. What is TrueTime doing?
168. `[D]` Aurora's architecture: separated compute and storage, the quorum of six, and why failover is fast. What does it not fix?
169. `[D]` Vitess and Citus as sharding layers over MySQL and PostgreSQL. What do they add and what leaks through?
170. `[T]` "Just add a read replica" is offered as the fix for a write-bound system. Explain why it makes things worse.
171. `[D]` Scaling reads: replicas, caching, materialized views and denormalized read models. Give the decision order.
172. `[A]` At what point do you shard a PostgreSQL database, and what would you do for the two years before that point?

---

## 10. Caching and Redis

> Assumed known: `01-java` Q180 (caching strategies, invalidation, stampede) and `02-spring` Q52-55, Q140 (cache abstraction, Redis template).

173. `[C]` Cache-aside, read-through, write-through, write-behind and refresh-ahead. State the consistency guarantee and the failure mode of each.
174. `[T]` With cache-aside, describe the exact interleaving that leaves a stale value in the cache permanently, and the two standard fixes.
175. `[D]` Invalidate versus update on write. Why is "delete the key" almost always safer than "write the new value"?
176. `[D]` TTL strategy: how you choose one, why you add jitter, and the arithmetic for how much jitter.
177. `[D]` Cache stampede, dogpile and thundering herd. Compare locking, early recomputation and stale-while-revalidate.
178. `[T]` Your cache hit rate is 99 percent and the database still falls over when the cache restarts. Compute why, and describe the warm-up strategy.
179. `[D]` Cache penetration (misses for keys that do not exist) and cache avalanche. Give the mitigation for each, including bloom filters.
180. `[D]` Redis single-threaded event loop: what that buys, and which commands can therefore ruin your latency.
181. `[D]` Redis data structures beyond strings - hashes, sorted sets, sets, lists, streams, HyperLogLog, bitmaps. Give a production use for five of them.
182. `[D]` Redis expiration: lazy versus active expiry, and the eviction policies. Which `maxmemory-policy` do you set for a pure cache and which for a store?
183. `[T]` Redis reports 6 GB used with a 6 GB `maxmemory` and starts rejecting writes despite an LRU policy. Give the likely causes.
184. `[D]` Redis persistence: RDB, AOF and the hybrid. What is your data loss window with each, and what does `fsync everysec` really mean?
185. `[D]` Redis Cluster: hash slots, resharding, `MOVED` and `ASK` redirects, and why multi-key operations are restricted.
186. `[D]` Redis Sentinel versus Cluster versus a managed service. When does replication give you consistency, and when does it not?
187. `[T]` A distributed lock in Redis: the correct `SET NX PX` implementation with a fencing token, and the precise argument against Redlock.
188. `[D]` Rate limiting in Redis: fixed window, sliding window log, sliding window counter and token bucket. Give the data structure and the cost of each.
189. `[D]` Redis as a store of record: what has to be true, and what you must accept about durability.
190. `[T]` Caching at four layers - client, CDN, application and database. What goes wrong when two of them have different TTLs?
191. `[A]` A team proposes caching everything for 60 seconds to fix a latency problem. What do you ask, and when is this actually the right answer?

---

## 11. Document and wide-column stores

> Assumed known: `01-java` Q162 (SQL versus NoSQL), Q187-188 (DynamoDB partition keys, GSI versus LSI) and `03-microservices` Q71 (quorums).

192. `[C]` Give the four NoSQL families - key-value, document, wide-column, graph - and the access pattern each is shaped for.
193. `[T]` "NoSQL scales better than SQL." Take this apart precisely: what is actually being traded, and what does a modern PostgreSQL do that undermines the claim?
194. `[D]` Schema-on-read versus schema-on-write. Where does the validation debt actually land, and how do you manage it?
195. `[D]` MongoDB: embedding versus referencing. Give the three questions that decide it and the 16 MB constraint that ends the argument.
196. `[D]` MongoDB indexes - compound, multikey, partial, TTL, wildcard. What is the ESR rule and why does it exist?
197. `[D]` MongoDB write concern (`w`, `j`, `wtimeout`) and read concern (`local`, `majority`, `linearizable`). Which combination gives read-your-writes?
198. `[T]` MongoDB multi-document transactions exist. Why is needing them usually a modeling smell, and what do they cost on a sharded cluster?
199. `[D]` MongoDB replica sets: elections, the oplog, rollback of un-replicated writes, and why an arbiter is a trap.
200. `[D]` Cassandra data modeling: partition key versus clustering key, and why you design one table per query.
201. `[T]` A Cassandra partition grows unbounded. What breaks first, and what is the standard bucketing fix?
202. `[D]` Cassandra tunable consistency: `ONE`, `QUORUM`, `LOCAL_QUORUM`, `ALL`, and how `R + W > N` plays out across data centers.
203. `[D]` Tombstones in Cassandra: why deletes are writes, what `gc_grace_seconds` protects, and how a tombstone storm kills reads.
204. `[D]` Cassandra lightweight transactions and Paxos. What do they cost, and what is the correct usage rate?
205. `[D]` DynamoDB single-table design: overloaded keys, item collections, and the access-pattern inventory you build first.
206. `[D]` DynamoDB GSI versus LSI: consistency, capacity, key constraints, and the GSI back-pressure failure mode.
207. `[T]` A DynamoDB partition is throttling while total consumed capacity is well below provisioned. Explain adaptive capacity and what you actually change.
208. `[D]` DynamoDB capacity: on-demand versus provisioned with auto-scaling. Where is the cost cliff, and how do you choose?
209. `[D]` DynamoDB transactions, conditional writes and optimistic concurrency. What is the item and size limit, and what does `TransactWriteItems` cost?
210. `[D]` DynamoDB Streams and TTL: the delivery guarantees, the deletion delay, and the pattern for archiving to S3.
211. `[T]` You need an aggregate ("total orders per customer this month") in DynamoDB. Give three approaches and the consistency of each.
212. `[A]` A team wants to replace PostgreSQL with DynamoDB for a system with reporting requirements and a changing access pattern. Make the case both ways and give your recommendation.

---

## 12. Search, analytics and data platform

> Assumed known: `03-microservices` Q78-79 (change data capture, feeding a reporting database without recreating a shared database).

213. `[C]` OLTP versus OLAP: contrast the workload, the schema, the storage layout and the isolation requirement.
214. `[D]` Elasticsearch/OpenSearch: the inverted index, analyzers, and what a shard actually is. How do you choose shard count?
215. `[T]` Elasticsearch is "near real time". Explain refresh, flush and merge, and what your application must not assume after an indexing call returns.
216. `[D]` Keeping a search index in sync with the database: dual write, outbox, CDC and periodic reindex. Rank them and say how you reconcile drift.
217. `[D]` Relevance: TF-IDF versus BM25, boosting, and why "the results are wrong" is a product problem before it is a technical one.
218. `[D]` Star schema, snowflake schema and a wide flat table. When does dimensional modeling still pay for itself?
219. `[D]` Slowly changing dimensions types 1, 2 and 3. Show the type 2 row layout and the query it enables.
220. `[D]` Columnar formats - Parquet and ORC: row groups, column chunks, encodings, and predicate pushdown via statistics.
221. `[D]` Warehouse versus lakehouse: what table formats like Iceberg or Delta add over files in object storage.
222. `[D]` ETL versus ELT, and where transformation belongs when the warehouse is cheap and elastic.
223. `[D]` Materialized views: incremental versus full refresh, staleness, and the PostgreSQL limitation you have to work around.
224. `[T]` Reporting runs against a read replica and is now causing query cancellations on that replica. Explain the exact mechanism and both fixes.
225. `[D]` Streaming versus batch for analytics. What does exactly-once mean in a streaming aggregation, and what is a watermark?
226. `[A]` The business wants "real-time dashboards" on OLTP data. Establish the actual requirement and design the path.

---

## 13. The Java data layer against a real database

> Assumed known: `01-java` Q150-154 (JPA lifecycle, N+1, caches, locking), `02-spring` Q121-138 (Spring Data), Q203 (HikariCP) and `03-microservices` Q193 (pool sizing across services).

227. `[C]` What SQL does Hibernate actually issue for a lazy `@ManyToOne`, an `@OneToMany` with `JOIN FETCH`, and a `@BatchSize` collection?
228. `[T]` `JOIN FETCH` combined with pagination. What does Hibernate do, what warning does it log, and what is the correct two-query solution?
229. `[D]` The MultipleBagFetchException and why two `List` collections cannot be fetched in one query. What are the fixes?
230. `[D]` Dirty checking and flush ordering. Why can a flush produce a constraint violation the code order suggests should not happen?
231. `[T]` An `@Transactional(readOnly = true)` method still issues an `UPDATE`. Give the mechanisms by which this happens.
232. `[D]` JDBC batching with Hibernate: `batch_size`, `order_inserts`, `order_updates`, and why `IDENTITY` generation disables it.
233. `[D]` PostgreSQL `reWriteBatchedInserts` and why a JDBC batch is not one round trip without it. What speedup should you expect?
234. `[D]` Fetch size and streaming a large result: what `setFetchSize` does in the PostgreSQL driver, and the three conditions required for a real cursor.
235. `[D]` Connection pool sizing: give the arithmetic (Little's Law and the core-count heuristic) and explain why 100 connections is usually worse than 20.
236. `[T]` Under load the application reports connection timeouts while the database is 20 percent utilized. Walk through the diagnosis.
237. `[D]` Pool timeouts that matter: `connectionTimeout`, `maxLifetime`, `idleTimeout`, `validationTimeout`, and how they must relate to the database and any proxy in between.
238. `[D]` Statement timeout, `lock_timeout`, `idle_in_transaction_session_timeout` and the JDBC socket timeout. Which one actually stops a runaway query, and where do you set each?
239. `[D]` Prepared statement caching in the driver, in the pool and in the server. Where does PgBouncer break this and what mode do you need?
240. `[D]` PgBouncer session, transaction and statement pooling. What does transaction pooling forbid in your application code?
241. `[T]` A retry on a failed `INSERT` creates a duplicate. Which JDBC/driver errors are safe to retry and which are ambiguous?
242. `[A]` When would you drop JPA for jOOQ, Spring Data JDBC or plain SQL? Give the criteria you would apply to a real codebase.

---

## 14. Schema evolution and zero-downtime migrations

> Assumed known: `01-java` Q163 (Flyway, Liquibase) and `03-microservices` Q32, Q173, Q177, Q226 (expand-contract, blue-green with a shared database, dual write).

243. `[C]` State the rule that makes rolling deployment safe with respect to schema, in one sentence, and derive the expand-contract steps from it.
244. `[D]` Which PostgreSQL DDL statements take `ACCESS EXCLUSIVE`, and which of those are nonetheless instant? Give the modern fast paths.
245. `[T]` `ALTER TABLE ADD COLUMN ... DEFAULT ...` used to rewrite the whole table. What changed, and which variant still rewrites?
246. `[D]` Adding a `NOT NULL` constraint to a large table without a long lock. Give the full sequence including `NOT VALID` and `VALIDATE`.
247. `[D]` Renaming a column across two deployed versions of an application. Write the full sequence and mark the rollback point.
248. `[D]` Changing a column type on a 500-million-row table. Give the shadow-column approach with backfill, and the trigger you need.
249. `[D]` Backfilling: batching strategy, throttling against replication lag, restartability, and how you verify completion.
250. `[T]` A migration acquires a lock behind a long-running `SELECT` and everything stops. Explain the lock queue and the `lock_timeout` retry pattern that avoids it.
251. `[D]` Migration tooling in CI/CD: who runs migrations, whether they run in the application startup or a separate job, and how you handle N instances starting at once.
252. `[D]` Rollback: which migrations are reversible, why `down` scripts are a trap, and what you do instead.
253. `[D]` `gh-ost` and `pt-online-schema-change` for MySQL. How do they work, and what is the PostgreSQL equivalent story?
254. `[D]` Multi-tenancy: shared schema with a tenant column, schema per tenant, database per tenant. Compare migration cost, blast radius and noisy neighbors.
255. `[T]` You have 4,000 tenants in schema-per-tenant and a migration takes 8 seconds each. What now?
256. `[A]` Design the review and safety process for schema changes in an organization with 30 teams sharing five databases.

---

## 15. Observability, troubleshooting and capacity

> Assumed known: `03-microservices` Q193, Q196 (pool sizing, backpressure) and Category 4 here.

257. `[C]` The database is slow. Give your first five minutes, in order, and the question each step answers.
258. `[D]` `pg_stat_statements`: what it aggregates, the columns you actually read, and how you use it to rank work rather than queries.
259. `[D]` Wait event analysis: the wait classes, what a lock wait versus an IO wait versus a buffer pin means, and how you sample them.
260. `[D]` `pg_stat_activity`: the states, what `idle in transaction` costs, and the queries you keep saved for an incident.
261. `[D]` The dashboard you would build for a production PostgreSQL: name ten metrics and the alert threshold for each.
262. `[T]` Mean query time is flat and users are complaining. What are you missing, and what do you measure instead?
263. `[D]` Cache hit ratio, checkpoint frequency, dead tuple counts, transaction age, replication lag - which of these are leading indicators and which are lagging?
264. `[D]` Capacity planning: how do you forecast storage, IOPS and connections a year out, and what growth pattern breaks the forecast?
265. `[D]` Load testing a database realistically: data volume, cardinality, cache state and concurrency. What do most load tests get wrong?
266. `[A]` Set the SLOs for a shared database platform used by 30 services, and say how you enforce them without becoming a bottleneck.

---

## 16. Security, compliance and cost

> Assumed known: `01-java` Q147 (SQL injection in a JPA application) and `03-microservices` Q166 (multi-tenant data isolation).

267. `[C]` Least privilege for a database: the roles you create, what the application user must not have, and how migrations get their privileges.
268. `[D]` SQL injection beyond string concatenation: dynamic ORDER BY, `LIKE` patterns, IN-lists, JPQL and native queries. Give the safe pattern for each.
269. `[D]` PostgreSQL row-level security: how policies are evaluated, the `BYPASSRLS` risk, and the performance implication.
270. `[T]` Multi-tenant isolation enforced only by `WHERE tenant_id = ?` in application code. Give three realistic ways that fails and the defense in depth.
271. `[D]` Encryption at rest, in transit and at the column level. What does each actually protect against, and what does TDE not protect against?
272. `[D]` Key management for column-level encryption, and what searchable encryption or deterministic encryption costs you.
273. `[D]` PII: classification, masking in lower environments, tokenization, and the pipeline that keeps production data out of a laptop.
274. `[D]` Auditing: database audit extensions, trigger-based audit tables, and log-based capture. Compare completeness, performance and tamper resistance.
275. `[T]` GDPR right to erasure against an append-only event store, backups and a data warehouse. How is this actually satisfied?
276. `[D]` Managed database cost shape: instance, storage, IOPS, backup, data transfer and the ones that surprise people. Compare RDS, Aurora and DynamoDB.
277. `[D]` Right-sizing a database: the signals you use, the risk of scaling down, and the three cheapest wins before you change instance class.
278. `[A]` Data retention and archival policy: who decides, how you enforce it technically, and how retention interacts with partitioning.

---

## 17. Data architecture design exercises and leadership

> Assumed known: everything above. The design questions are worked in full in [scenario-questions.md](scenario-questions.md); the leadership questions have no scripted answer.

279. `[A]` Design the data layer for a multi-tenant SaaS platform reaching 5,000 tenants, including isolation, migration and noisy-neighbor control.
280. `[A]` Design an audit and event store taking 50,000 writes per second with a seven-year retention requirement and ad-hoc investigation queries.
281. `[A]` Design the storage for a global product catalogue: read-heavy, multi-region, tolerant of seconds of staleness, with an admin path that is not.
282. `[A]` Design the read path for an analytics dashboard that must not touch the OLTP primary and must be at most five minutes stale.
283. `[A]` Design the data separation for pulling an orders service out of a monolith whose four modules all read the same tables.
284. `[A]` Design storage and access for a system handling both transactional bookings and a recommendation feature over the same entities.
285. A time you chose the boring database and were proved right - or wrong.
286. A data-layer decision you made that you would reverse today, and what it would take to reverse it.
287. A time you drove a schema or data standard across teams you did not own.
288. A database incident you led as incident commander, including what you told the business while it was still burning.
289. A time you told a product owner that their requirement was going to cost a rewrite of the data model.
290. How you have built database competence in a team that treated the database as someone else's problem.
