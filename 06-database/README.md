# Database Interview Preparation Pack

Data-layer depth for **Principal Engineer / Technical Lead / Solution Architect** interviews: relational modeling, SQL, indexing, the query optimizer, transactions and MVCC, storage and durability, replication and recovery, partitioning and sharding, caching and Redis, document and wide-column stores, search and analytics, the Java data layer, zero-downtime schema evolution, observability, security and cost, and polyglot persistence design.

The relational material is anchored on **PostgreSQL**, with Oracle, MySQL/InnoDB and SQL Server contrasts called out wherever the mechanism genuinely differs. That is deliberate: an interviewer can tell within two questions whether you learned "databases" or learned one engine's manual, and the way to prove the former is to describe a mechanism and then say how another engine does it differently.

---

## Read [01-java](../01-java/README.md), [02-spring](../02-spring/README.md) and [03-microservices](../03-microservices/README.md) first

This pack is **not** an introduction to databases. It starts where the data-access material in the earlier packs stopped, and nothing there is restated.

| Assumed known | Where this pack takes it |
| --- | --- |
| `01-java` Q122 isolation levels and the three anomalies | Category 5 - snapshot isolation, write skew, SSI, why the ANSI table is an incomplete model |
| `01-java` Q159 composite index order, covering indexes | Category 3 - B-tree mechanics, index-only scans and the visibility map, partial and expression indexes, write amplification |
| `01-java` Q151, Q153, Q154 N+1, second-level cache, locking | Category 13 - what Hibernate does to the *plan*, batching, and the version column's failure modes |
| `01-java` Q162 SQL versus NoSQL | Categories 11 and 17 - access-pattern-first selection, and the exercises where the honest answer is "both" |
| `01-java` Q163 Flyway and Liquibase | Category 14 - which DDL takes which lock, backfills, and the migrations that cannot be rolled back |
| `01-java` Q180 caching strategies | Category 10 - invalidation correctness, stampede arithmetic, Redis internals, why Redlock is contested |
| `01-java` Q187-188 RDS, Aurora, DynamoDB, partition keys | Categories 9, 11 and 16 - the storage architecture behind Aurora, single-table design, and the cost shape of each |
| `02-spring` Q64-65 `readOnly`, connection acquisition | Category 13 - replica routing correctness and connection lifetime under load |
| `02-spring` Q79, Q133-138 outbox, optimistic locking, Spring Data | Categories 6 and 13 - the same patterns at the SQL level, defensible without the framework |
| `02-spring` Q203 HikariCP defaults | Category 13 - pool sizing arithmetic and why a bigger pool usually makes latency worse |
| `03-microservices` Q61-63, Q71 database per service, consistency models, quorums | Categories 8 and 9 - how a single engine implements those guarantees, and where it lies about them |
| `03-microservices` Q78, Q90-93 CDC, outbox, inbox | Categories 12 and 14 - logical decoding, replication slots, snapshot behavior and connector restarts |
| `03-microservices` Q177, Q226 zero-downtime migration, dual write | Category 14 - the lock-level detail that makes those sequences safe or fatal |

Where a question here overlaps, it starts one level deeper.

**The answer frameworks are not repeated either.** The four-layer technical answer, CIDER for scenarios and STAR-L for behavioral questions are defined once in [../01-java/README.md](../01-java/README.md). Re-read that section before your first mock.

### Scope boundary

Distributed-systems theory (CAP, consensus, saga design) belongs to `03-microservices` and appears here only where a single database implements it. Cloud service selection, IAM and networking belong to `05-aws`. Whole-system rehearsals belong to `04-system-design`; Category 17 here is the data-architecture subset. Vector databases and embedding stores belong to `09-rag`.

---

## Files in this pack

| File | Purpose | When to use |
| --- | --- | --- |
| [README.md](README.md) | Prerequisite map, roadmap, what interviewers probe | Read first |
| [questions.md](questions.md) | 290 questions across 17 categories | Daily drilling |
| [answers.md](answers.md) | Mechanism-level model answers | After attempting yourself |
| [scenario-questions.md](scenario-questions.md) | Data incidents, design exercises, leadership situations | Mock practice |
| [cheatsheet.md](cheatsheet.md) | Fast revision reference | Night before, and 30 minutes before |
| [quiz.html](quiz.html) | Interactive flashcard version | Active recall |

### quiz.html

Open it directly in a browser - no server, no internet connection needed. Search covers question and answer text, filter by category, difficulty or your own progress, and mark each question Known or Review with progress saved in the browser. Press `/` to focus search.

Generated from the markdown, so the markdown stays the source of truth. After editing any of the three source files:

```bash
python tools/build-quiz.py 06-database
```

---

## What interviewers actually probe at this level

Database questions for a principal role are rarely "what is a foreign key". They are testing whether you have been on call for a database.

Six recurring themes:

1. **Can you read a plan, or do you guess?** The single most reliable separator. A candidate who says "add an index" is mid-level; a candidate who asks for `EXPLAIN (ANALYZE, BUFFERS)` and then points at the row-estimate error is senior; a candidate who explains *why* the estimate was wrong is principal.
2. **Do you know what a transaction actually guarantees?** Almost everyone can recite the four isolation levels. Very few know that Read Committed re-reads a row after a concurrent update, that snapshot isolation permits write skew, or that `SELECT ... FOR UPDATE` is the practical fix.
3. **Every index is a write tax.** Reads and writes trade against each other on the same table, and the interesting question is always which query you are willing to slow down.
4. **The failure was operational, not architectural.** Bloat, a long-running transaction pinning the xmin horizon, a migration that took an exclusive lock, a connection pool three times too large, autovacuum never keeping up. These are the incidents that actually happen, and the ones the interviewer has lived through.
5. **Correct answers are workload-shaped.** Read/write ratio, cardinality, access patterns, consistency requirement, data lifetime and growth rate. A candidate who names a store before asking for those is guessing.
6. **Data outlives everything.** Services get rewritten; the schema does not. Migration strategy, backward compatibility and the ability to restore are what make a data decision reversible, and reversibility is the thing you are really being assessed on.

---

## Study roadmap

### Week 1 - Modeling, SQL and indexing

Categories 1, 2 and 3. Be able to justify a normalization decision with a cardinality argument, write a window-function query without hesitating, and explain the leftmost-prefix rule and index-only scans from memory.

### Week 2 - The optimizer and transactions

Categories 4 and 5. The densest material in the pack. Work every `[T]` twice, and be able to walk an `EXPLAIN ANALYZE` out loud and state where the estimate went wrong.

### Week 3 - Concurrency, storage and durability

Categories 6 and 7. Write the `SKIP LOCKED` queue from memory, and be able to explain what happens between a `COMMIT` returning and the data being on disk.

### Week 4 - Replication, scaling and caching

Categories 8, 9 and 10. Form a defensible position on read replicas versus caching - you will be asked - and be able to compute a cache hit-rate benefit and a stampede burst.

### Week 5 - NoSQL, analytics and the Java data layer

Categories 11, 12 and 13. Design a DynamoDB single-table model out loud, and be able to size a connection pool with the arithmetic rather than the folklore.

### Week 6 - Operations, security and design

Categories 14, 15 and 16, then work only from [scenario-questions.md](scenario-questions.md). Category 17 is the rehearsal.

---

## Your data story bank

Prepare these with real detail from Verizon India and Sonata Software. Generic answers are transparent at 19 years of experience.

1. A query you took from unusable to fast, with the before and after numbers and what the plan showed.
2. A schema migration you ran on a large table with no downtime, including the lock you avoided.
3. A production incident caused by the database - bloat, lock contention, replication lag, a full disk - and the permanent fix.
4. A store-selection decision you made, including the option you rejected and what would have changed your mind.
5. A caching layer you introduced, with the hit rate and the invalidation bug you found afterwards.
6. A consistency compromise you made deliberately and explained to the business.
7. A restore you actually performed, or a restore drill you ran, with the measured RTO.
8. A data model you inherited and had to live with, and how you contained the damage.
9. A cost reduction on the data tier - right-sizing, storage class, retention, query elimination - with the number.
10. A standard you drove across teams you did not own: migration review, index policy, PII classification.

---

## Self-check before the interview

- [ ] I can read an `EXPLAIN (ANALYZE, BUFFERS)` out loud and identify the first wrong row estimate.
- [ ] I can state which anomaly each isolation level permits, including write skew, without hesitating.
- [ ] I can explain MVCC, why `UPDATE` creates a new row version, and what autovacuum has to do afterwards.
- [ ] I can write the expand-contract sequence for renaming a column on a 500-million-row table, including the rollback point.
- [ ] I can size a connection pool with arithmetic and defend a number smaller than the one people expect.
- [ ] I can design a DynamoDB single-table model for a stated access pattern and say when it is the wrong choice.
- [ ] I know our RPO and RTO, and I have restored a backup to prove them.
- [ ] I have three stories with concrete numbers attached.
