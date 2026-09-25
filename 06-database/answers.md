# Answers

Model answers for [questions.md](questions.md). Numbers match the question numbers exactly.

Answers follow the four-layer structure defined in [../01-java/README.md](../01-java/README.md): direct answer, mechanism, trade-off, experience hook. Hooks are written as *italic placeholders* - replace them with real detail from Verizon India and Sonata Software.

Unqualified statements about mechanism refer to **PostgreSQL**; other engines are named explicitly. Q279-284 are worked as full design exercises in [scenario-questions.md](scenario-questions.md). Q285-290 are story questions with no scripted answer.

---

## 1. Data modeling, keys and constraints

### Q1. Normal forms to BCNF

- **1NF** - atomic column values, no repeating groups. Removes the "three phone columns" and the comma-separated list that no index can help.
- **2NF** - no partial dependency on part of a composite key. In `order_line(order_id, sku, qty, customer_name)`, `customer_name` depends on `order_id` alone; update it in one row and the rows disagree.
- **3NF** - no transitive dependency. `employee(id, dept_id, dept_name)`: renaming a department means updating every employee row, and a department with no employees cannot exist at all.
- **BCNF** - every determinant is a candidate key. It matters only for overlapping candidate keys, and it is the level teams reach without noticing.

The point to make in an interview is that normalization is not aesthetic; each level removes a class of *anomaly* (insert, update, delete) that would otherwise have to be prevented by application discipline, and application discipline is not a constraint.

### Q2. Denormalization techniques

1. **Duplicated column** - copy `customer_name` onto `order`. Invariant: keep it in sync, or declare it a snapshot (which is often the truth - the name at the time of the order).
2. **Precomputed aggregate** - `order.total`, `customer.order_count`. Invariant: every write path updates it, including deletes and admin scripts.
3. **Collapsed relation** - store an address inline rather than in its own table. Invariant: the sub-entity has no independent identity, and you accept you cannot query it globally.
4. **Materialized read model** - a whole table shaped for one query. Invariant: a defined staleness bound and a rebuild path.

The trade-off is always the same: you convert a join at read time into a write-time obligation plus a correctness risk. Prefer techniques the *database* can enforce - a materialized view, a generated column, a trigger - over ones that live in application memory.

### Q3. "We denormalized for performance" `[T]`

I would ask for the plan before and after, and the actual latency percentiles. In my experience the join was almost never the cost. The usual real causes are a missing or mis-ordered index, N+1 access from an ORM, a row-estimate error producing a nested loop over millions of rows, or a query returning far more data than the screen shows.

The reason to push back is that denormalization is permanent and its cost is paid forever in correctness, while the actual fix is usually a one-line index. I accept denormalization when the join is across a service or storage boundary, when the aggregate is over a volume that cannot be scanned in the latency budget, or when the read shape is genuinely different from the write shape - and then I prefer an explicit read model over quietly duplicated columns.

*Hook: a query blamed on normalization that turned out to be a row-estimate problem.*

### Q4. Natural versus surrogate keys

A **surrogate** key is my default: it is stable, narrow, meaningless and therefore cannot change when the business changes its mind.

A **natural** key is clearly right when the value is genuinely immutable and externally defined and you want the constraint for free - an ISO country code, a currency code, a composite of two surrogate keys in a join table. It is clearly fatal when the "unique, unchanging" business value turns out to be neither: national identifiers get reissued, email addresses change, SKUs get reused after a merger. Rewriting a natural key means rewriting every child row and every foreign key index.

The pragmatic answer is both: a surrogate primary key for referential plumbing, and a unique constraint on the natural key so the database still enforces the business rule.

### Q5. Sequence versus UUIDv4 versus UUIDv7

| | Sequence/identity | UUIDv4 | UUIDv7 / ULID |
| --- | --- | --- | --- |
| Width | 8 bytes | 16 bytes | 16 bytes |
| Index locality | Perfect, right-hand insert | None - every insert lands on a random page | Near-perfect, time-ordered prefix |
| Page splits | Minimal | Constant, 50/50 splits and low fill | Minimal |
| Generatable client-side | No | Yes | Yes |
| Leaks information | Row count and rate | Nothing | Creation time |

Sequences also create a hot right-hand edge of the index, which matters only at extreme insert rates, and they need coordination in a multi-writer or offline-capable system. UUIDv4 buys you client-side generation and merge-ability at the cost of write amplification and a bigger index at every level. UUIDv7 is the modern default when you need client-side generation: you keep locality and lose only the fact that creation time is inferable.

### Q6. Random UUID in InnoDB versus PostgreSQL `[T]`

InnoDB stores the table *in* the primary key (a clustered index), and every secondary index stores the primary key as its row pointer. A random primary key therefore scatters the actual row data across the whole tablespace on insert, causing page splits in the data itself, and inflates every secondary index by the key width.

PostgreSQL has a heap: rows are appended wherever there is space regardless of key, so the *table* stays sequential. But the primary key index is still a B-tree receiving random keys, so you get the same index page splits, low fill factor, higher index size, and a working set that no longer fits in `shared_buffers`. Range queries over the key are also useless, and index bloat after churn is worse.

So the InnoDB penalty is larger, but "PostgreSQL doesn't care" is wrong - the index and the buffer cache both care.

### Q7. Composite primary key versus surrogate plus unique constraint

A composite key is honest about identity and avoids a pointless column in pure join tables. The costs appear at the edges: every child table repeats all key columns, every foreign key index gets wider, ORMs need an `@IdClass`/`@EmbeddedId` with `equals`/`hashCode` written correctly, and a REST resource identifier becomes a compound value.

A surrogate plus a unique constraint gives narrow foreign keys, trivial ORM mapping and a single-column identifier for URLs, at the cost of an extra column and the possibility that someone forgets the unique constraint - at which point the model silently permits duplicates.

I use composite keys for pure association tables and partitioned tables where the partition key must be in the key, and surrogate keys elsewhere.

### Q8. Where to enforce an invariant

My rule: **anything that must always be true goes in the database**, because the database is the only component every writer passes through. Application code enforces the rules that need context the database does not have.

Concretely, in the database: nullability, uniqueness, referential integrity, value domains (`CHECK`, enums), and mutually exclusive ranges (`EXCLUDE`). In the application: multi-aggregate rules, anything requiring a network call, anything that varies by tenant or feature flag, and anything with a user-facing message that needs to be graceful.

The cases that break the rule are cross-row invariants under concurrency (an application check under Read Committed is not a constraint - see Q85), soft-deleted rows breaking unique constraints (Q13), and constraints so expensive at scale that they must become an asynchronous reconciliation with an alarm. When I remove a constraint for performance I add the reconciliation job in the same change, otherwise the invariant becomes a hope.

### Q9. Foreign keys in production

A foreign key is implemented as two triggers: on child insert/update the parent row is locked with `FOR KEY SHARE`, and on parent delete/key-update the child table is searched. The costs are therefore a lock on the parent row for the duration of the child transaction, a required index on the child column for delete performance, and extra work on every write.

Teams drop them for three reasons: bulk load speed, sharding (a foreign key cannot cross a shard), and migration convenience. The argument is weaker than it sounds - the alternative is orphan rows that you discover during an incident. I keep foreign keys in OLTP, drop them deliberately in analytics and staging tables, and if a shard boundary forces it, I add a reconciliation check with an alert rather than pretending the relationship does not exist.

### Q10. Missing index on the foreign key child column `[T]`

Deleting or updating the key of a **parent** row becomes a full scan of the child table, once per parent row. Nothing warns you because the constraint itself is satisfied - it is only the check that is slow - and because most engines create an index automatically for the *primary* key side but not the *referencing* side.

The visible symptom is a delete of a few hundred parent rows that takes minutes and blocks, or a cascade delete that produces a lock storm across several tables. In PostgreSQL you can find these with a query joining `pg_constraint` against `pg_index` looking for `confrelid` columns with no leading index. I treat "every foreign key column has an index" as a schema lint rule, with an explicit exemption comment where the child table is tiny.

### Q11. Nullable columns

Three-valued logic is the real cost: `NULL = NULL` is unknown, `NOT IN` with a NULL in the list returns no rows (Q24), `COUNT(col)` skips nulls while `COUNT(*)` does not, and unique constraints permit multiple NULLs in standard SQL. Aggregates and joins quietly change meaning.

Storage-wise a null is cheap in PostgreSQL - a bit in the tuple's null bitmap, and the column occupies no space - so "nulls waste space" is not the argument.

The real problem is semantic: NULL means "unknown", but most schemas use it for "not applicable", "not yet supplied" and "the default" simultaneously, so no query can distinguish them. My preference is to make columns `NOT NULL` with a default wherever the value is genuinely always present, and to split a group of mutually exclusive nullable columns into a separate table or a discriminated design rather than encoding the state in which columns happen to be null.

### Q12. `CHECK`, `EXCLUDE` and unique partial indexes

- **`CHECK`** constrains a single row: `CHECK (end_date > start_date)`, `CHECK (status IN (...))`, `CHECK (amount >= 0)`. It cannot see other rows.
- **Unique partial index** constrains a set of rows conditionally: "only one active subscription per customer" is `CREATE UNIQUE INDEX ON subscription (customer_id) WHERE status = 'ACTIVE'`. A plain unique constraint cannot express the condition.
- **`EXCLUDE`** constrains rows against each other with an arbitrary operator, which uniqueness cannot: "no two bookings for the same room may overlap in time" is `EXCLUDE USING gist (room_id WITH =, during WITH &&)`. This is the only one of the three that solves the double-booking race correctly at the storage layer.

The last point is the interview payload: an overlap check written as `SELECT` then `INSERT` in application code is a write-skew bug (Q84) and an `EXCLUDE` constraint is not.

### Q13. Soft delete

The four implementations, with what each breaks:

1. **`deleted_at timestamptz NULL`** - the common one. Every query must add `WHERE deleted_at IS NULL`, and forgetting once is a data leak. Unique constraints now block reuse of a value held by a deleted row.
2. **`is_deleted boolean`** - the same, with less information, and a low-cardinality column that misleads the planner.
3. **Move to an archive table** - deletes are real deletes plus an insert. Constraints, indexes and query correctness stay clean; the cost is a second table and losing foreign keys into the archive.
4. **Temporal/versioned table** (Q14) - the row is closed with an end timestamp. The most correct and the most work.

Fixes for the classic problems: make uniqueness partial (`UNIQUE (email) WHERE deleted_at IS NULL`) or include the deletion marker in the key using a sentinel rather than NULL; expose only views that filter, and grant the application access to the views rather than the tables; and confirm with the business whether they want *undelete* or *audit history*, because they usually want the second, and an archive table gives it more honestly.

### Q14. Bitemporal modeling

**Valid time** is when the fact was true in the world; **transaction time** is when the database believed it. Bitemporal tables keep both, as two ranges: `valid_from/valid_to` and `system_from/system_to` (PostgreSQL range types plus `EXCLUDE` constraints make this enforceable).

A correction to a past salary changes valid time; the record of when you learned about it is transaction time. That combination answers both "what was their salary in March" and "what did we think their March salary was when we ran the March payroll" - which is the question auditors and regulators actually ask.

The costs are real: every "current" query needs a predicate on both ranges (so index on the ranges, or maintain a current-row view), updates become close-and-insert, and row counts grow with churn. I would only pay for it where correction history has legal or financial consequences - payroll, pricing, insurance, billing - and use a plain audit table everywhere else.

### Q15. Money, timestamps and enumerations `[T]`

- **Money as `float`/`double`** - binary floating point cannot represent 0.10, so sums drift and reconciliations fail by pennies that nobody can explain. Use `numeric`/`DECIMAL` with an explicit scale, or an integer count of minor units, and always store the currency alongside the amount.
- **Timestamps as `timestamp` without time zone**, or as local time - the classic bug appears at a DST transition, where an hour repeats and ordering breaks, or when a second region comes online. Store `timestamptz` (an absolute instant) and convert at the edges.
- **Enumerations as free `varchar`** - you get 'ACTIVE', 'Active' and 'active' within a year. The alternatives are a database enum type (fast, compact, but altering it is a schema migration and removing a value is very awkward) or a lookup table with a foreign key (flexible, joinable, attribute-carrying). I default to a lookup table for domain concepts, a `CHECK` constraint for small fixed technical sets.

### Q16. `timestamptz` does not store a time zone

`timestamptz` stores a UTC instant in eight bytes. On input it converts *from* the session `TimeZone`; on output it converts *to* it. The zone is never stored, so it is the correct type for anything that happened - events, audit rows, created/updated timestamps.

A future appointment is a different kind of value. "9 a.m. on 14 March in Berlin" must survive a change to the German time zone rules, and an instant will not: if the government moves the transition, the instant now points at 8 a.m. So you store the local wall-clock time (`timestamp` without zone) plus the IANA zone identifier (`Europe/Berlin`), and resolve to an instant when you need to schedule or compare. Storing the resolved instant as well, as a derived column you can rebuild from the tzdata release, is a reasonable optimization.

### Q17. The EAV pattern

Entity-Attribute-Value stores `(entity_id, attribute, value)` rows instead of columns. It is defensible when attributes are genuinely user-defined at runtime and unbounded - a product catalogue where each category has its own specifications, a form builder, a lab-results system.

The optimizer cost is severe. Every attribute is a self-join, so a five-attribute filter is a five-way join; the value column is text so there are no useful statistics or type-correct comparisons; selectivity estimates are wrong everywhere; and no constraint can express "price must be numeric and positive".

The alternatives, in the order I would try them: a JSONB column with a GIN index and a `CHECK` on the required keys (which keeps one row per entity and gives containment queries); a table per entity type where the set of types is bounded; a sparse wide table where types share most attributes; or a document store if this is the *whole* domain rather than a corner of it. Where EAV survives, I keep the hot, queryable attributes as real columns and let EAV hold the tail.

### Q18. JSONB as a column type

You gain schema flexibility, one round trip for a whole aggregate, and containment/path queries with a GIN index (`WHERE doc @> '{"status":"ACTIVE"}'`). `jsonb` is parsed and stored in a binary form, so it is slower to write and faster to query than `json`, and it does not preserve key order or duplicates.

You lose per-field constraints and defaults, per-field statistics (so the planner guesses selectivity for a path predicate, which is the most common cause of a bad plan on a JSONB table), cheap type changes, and column-level grants. Values also get TOASTed once large (Q129), so touching one field can mean detoasting the whole document.

My rule: a field is a **column** if it is queried, filtered, sorted, constrained, or referenced by another table; it lives in the **document** if it is a payload read as a whole, sparse, caller-defined, or a schemaless third-party blob. Expression indexes on specific paths, or PostgreSQL 12+ generated columns extracting a path, are the middle ground when a document field becomes hot.

### Q19. 180 columns, mostly null `[T]`

Beyond aesthetics, the concrete problems are: the row exceeds what fits neatly in an 8 KB page once a few text fields are populated, so you get TOASTing and extra IO; every `SELECT *` reads the full tuple; the null bitmap grows; and `UPDATE` writes a whole new row version regardless of how few columns changed, so write amplification is proportional to the *table's* width, not the change.

Structurally, the mostly-null groups are almost always a subtype relationship or an optional one-to-one that was flattened, so no constraint can say "these six columns are all null or all present". The planner also has 180 columns of statistics to keep and correlation it cannot model.

The fix is to split by lifecycle and by subtype: hot narrow core table, one table per optional group, and JSONB for the genuinely sparse tail. Splitting also lets the hot table stay in cache, which is usually where the measurable win comes from.

### Q20. Inheritance mapping strategies

- **Single table** (one table, discriminator, all subtype columns nullable) - fastest, no joins, polymorphic queries are trivial. Cost: subtype columns cannot be `NOT NULL`, the table grows wide, and the schema does not express the model.
- **Class table** (a base table plus one table per subtype, joined on the shared key) - fully normalized, constraints work per subtype. Cost: every read is a join, polymorphic queries join everything, inserts touch two tables.
- **Concrete table** (one complete table per subtype, no base table) - no joins, constraints work. Cost: polymorphic queries are a `UNION ALL`, shared columns are duplicated, and a shared identity across subtypes needs an external sequence.

I default to **single table** when the subtypes differ by a handful of columns and are queried polymorphically, and **class table** when subtypes have substantial independent state and are usually queried by concrete type. Concrete-table is a fit when the subtypes barely interact, which usually means they should not have shared a hierarchy at all.

### Q21. Inheriting a schema with no constraints `[A]`

First I measure rather than reform. I would inventory the actual violations - orphan rows, duplicate "unique" values, out-of-domain statuses - because the number decides everything. Then, in order:

1. **Stop the bleeding on new data**: add constraints as `NOT VALID` (foreign keys and checks can be added without scanning), so all *new* rows are enforced while historical violations are tolerated. This is cheap, non-blocking and immediately useful.
2. **Add uniqueness and foreign keys on the tables that cause incidents**, prioritized by the on-call log rather than by the model's ugliness.
3. **Clean the historical violations** with backfill jobs owned by the team that owns the data, then `VALIDATE CONSTRAINT` (a lighter lock than adding it validated).
4. **Type and width corrections** last, since they need shadow columns and backfills (Q248), and `varchar(255)` is annoying rather than dangerous.

The sequencing rule I would sell to the business is that every constraint is added on the back of a feature that touches that table, so remediation rides with delivery and never becomes a project that gets cancelled at 60 percent.

*Hook: a legacy schema you tightened incrementally, and the first constraint that caught a real bug.*

---

## 2. SQL beyond CRUD

### Q22. Join types, semi-join and anti-join

`INNER` keeps matching pairs; `LEFT`/`RIGHT` keep all rows of one side, padding with NULLs; `FULL` keeps both; `CROSS` is the Cartesian product.

A **semi-join** returns rows from the left side that have *at least one* match, without duplicating them and without exposing the right side's columns - written as `EXISTS` or `IN`. An **anti-join** returns left rows with *no* match - written as `NOT EXISTS`, or `LEFT JOIN ... WHERE right.key IS NULL`.

The distinction matters because they are separate physical operators in the plan (`Hash Semi Join`, `Hash Anti Join`) and because an inner join used where a semi-join was meant silently multiplies rows when the right side has duplicates - the most common cause of inflated `SUM` values in reports.

### Q23. Predicate in `ON` versus `WHERE` on a `LEFT JOIN` `[T]`

The `ON` clause decides which right-hand rows are *eligible to match*; the outer join then adds NULL-extended rows for unmatched left rows. The `WHERE` clause runs *after* that, on the joined result.

So `LEFT JOIN payment p ON p.order_id = o.id AND p.status = 'OK'` returns every order, with NULL payment columns where there is no successful payment. Moving `p.status = 'OK'` to `WHERE` filters out the NULL-extended rows too - because `NULL = 'OK'` is unknown - and silently converts the query into an inner join.

The rule: a predicate on the *nullable* side belongs in `ON`; a predicate on the preserved side belongs in `WHERE`. The exception is `WHERE p.id IS NULL`, which is the anti-join idiom and is deliberately applied afterwards.

### Q24. `NOT IN`, `NOT EXISTS`, `LEFT JOIN ... IS NULL`

`NOT IN` is the wrong one. If the subquery returns a single NULL, the whole predicate evaluates to unknown for every row and the query returns *nothing* - `x NOT IN (1, NULL)` is `x <> 1 AND x <> NULL`, which can never be true. This bug survives testing because it only appears once a NULL arrives.

`NOT EXISTS` has correct NULL semantics and is what I use. The planner turns it into a hash anti-join, which is the same physical operator as the `LEFT JOIN ... IS NULL` form, so their performance is usually identical in PostgreSQL; `NOT EXISTS` reads better and does not risk column-name ambiguity.

Caveat for other engines: older MySQL versions optimized these very differently, and Oracle needs the column declared `NOT NULL` (or an explicit filter) before it can use the anti-join transformation with `NOT IN`.

### Q25. `UNION`, `UNION ALL` and `OR`

`UNION` deduplicates, which means a sort or hash over the whole result - so use `UNION ALL` unless you actually need distinct rows and cannot guarantee them structurally.

Rewriting an `OR` as `UNION ALL` is a real optimization when the two branches can each use a *different* index and the results are disjoint: `WHERE email = ? OR phone = ?` may produce a full scan, while two indexed lookups combined with `UNION` are two page reads. PostgreSQL often does this itself with a **bitmap OR** over two indexes, so check the plan first; MySQL's index merge is less reliable, and this rewrite pays off more often there.

The rewrite hurts when the branches overlap heavily (you now need `UNION` and its dedup cost), when the query has `ORDER BY ... LIMIT` (each branch has to be sorted), or when the OR is over the same column and could just be an `IN` list.

### Q26. Logical processing order

`FROM` and joins, then `WHERE`, then `GROUP BY`, then aggregate functions, then `HAVING`, then window functions, then `SELECT` (including aliases), then `DISTINCT`, then `ORDER BY`, then `LIMIT`/`OFFSET`.

The consequences: you cannot reference a `SELECT` alias in `WHERE` or `GROUP BY` (the alias does not exist yet) but you can in `ORDER BY`; you cannot filter on an aggregate in `WHERE`; and you cannot filter on a window function anywhere except a wrapping subquery, because windows are computed after `HAVING` (which is exactly why "top N per group" needs a subquery - Q30).

This is the *logical* order. The optimizer is free to execute in any order that yields the same result, which is why a `WHERE` predicate can be pushed below a join and a `LIMIT` can stop a sort early.

### Q27. `HAVING` versus `WHERE` versus `FILTER`

`WHERE` filters rows before grouping and can use indexes; `HAVING` filters groups after aggregation and cannot. Putting a non-aggregate predicate in `HAVING` is therefore both slower and misleading - PostgreSQL will often push it down anyway, but the intent is wrong.

`COUNT(*) FILTER (WHERE status = 'PAID')` is the one I reach for most, because it lets a single pass compute several conditional aggregates side by side:

```sql
SELECT customer_id,
       count(*)                                   AS orders,
       count(*) FILTER (WHERE status = 'PAID')    AS paid,
       sum(total) FILTER (WHERE created_at > now() - interval '30 days') AS recent_value
FROM   orders GROUP BY customer_id;
```

The alternative - three self-joined subqueries, or `SUM(CASE WHEN ... THEN 1 ELSE 0 END)` - scans repeatedly or reads worse. `FILTER` is standard SQL and supported by PostgreSQL and SQLite; on MySQL and SQL Server you fall back to the `CASE` form.

### Q28. Window function anatomy

A window function computes a value over a *frame* of rows related to the current row, without collapsing rows the way `GROUP BY` does.

`PARTITION BY` splits the rows into independent groups; `ORDER BY` inside the `OVER` clause defines the ordering within the partition, which also defines the default frame; the frame clause narrows it further.

The frame difference matters: `ROWS BETWEEN 2 PRECEDING AND CURRENT ROW` counts *physical rows*, while `RANGE BETWEEN 2 PRECEDING AND CURRENT ROW` counts *values* in the ordering column and so includes all peers with the same value. The default frame when you supply `ORDER BY` is `RANGE UNBOUNDED PRECEDING TO CURRENT ROW`, which means a running `SUM` over a column with ties jumps at each tie rather than incrementing per row. Almost everyone who reports "my running total is wrong" has hit exactly this and needs `ROWS`.

`GROUPS` frames (PostgreSQL 11+) count peer groups, which is occasionally the honest answer for time buckets.

### Q29. The ranking and offset functions

- `ROW_NUMBER` - deduplication ("keep the newest row per key"), and stable pagination cursors.
- `RANK` - leaderboards where ties share a position and the next position skips (1, 1, 3).
- `DENSE_RANK` - "top three distinct prices" where you want no gaps (1, 1, 2).
- `LAG`/`LEAD` - period-over-period deltas, detecting state transitions in an event log, and computing the gap between consecutive events for a session timeout.
- `NTILE` - bucketing customers into deciles for segmentation.

The one worth demonstrating is `LAG` for state transitions: `CASE WHEN status <> lag(status) OVER (PARTITION BY order_id ORDER BY at) THEN 1 END` turns an event table into a transition table in one pass, which otherwise takes a self-join per row.

### Q30. Top N per group `[T]`

Two forms:

```sql
-- window function
SELECT * FROM (
  SELECT o.*, row_number() OVER (PARTITION BY customer_id ORDER BY created_at DESC) rn
  FROM orders o) t
WHERE rn <= 3;

-- lateral
SELECT c.id, o.*
FROM customers c
CROSS JOIN LATERAL (
  SELECT * FROM orders o WHERE o.customer_id = c.id
  ORDER BY created_at DESC LIMIT 3) o;
```

The window version must read and sort *every* order before discarding all but three per customer. The `LATERAL` version does an index scan on `(customer_id, created_at DESC)` per customer and stops after three rows, so with a suitable index it is dramatically faster when N is small and the group count is much smaller than the row count. The window version wins when you are processing most of the table anyway, or when there is no index on the ordering column so a single sort beats thousands of small ones.

This is the question where saying "it depends on the index and the group cardinality" *and then saying which way each pushes* is the whole answer.

### Q31. CTEs and the optimization fence

Before PostgreSQL 12, every `WITH` was materialized: executed once, results stored, predicates never pushed in. That made a CTE a deliberate fence - useful to force a plan, harmful when it prevented an index from being used because the outer `WHERE` could not reach inside.

From 12, a CTE that is non-recursive, side-effect free and referenced once is inlined by default, and you control it explicitly with `MATERIALIZED` / `NOT MATERIALIZED`.

MySQL 8 inlines (merges) CTEs when it can, similar to a derived table. Oracle decides by cost and has `/*+ MATERIALIZE */` and `/*+ INLINE */` hints.

The practical consequence: on PostgreSQL 12+ a CTE is a readability construct, not a performance construct, and if you inherit a query written for the old behavior, adding `MATERIALIZED` restores it exactly. `MATERIALIZED` is still genuinely useful when a CTE is referenced several times and is expensive, or when it contains a data-modifying statement.

### Q32. Recursive CTEs

```sql
WITH RECURSIVE tree AS (
  SELECT id, parent_id, name, 1 AS depth, ARRAY[id] AS path
  FROM   category WHERE parent_id IS NULL          -- anchor
  UNION ALL
  SELECT c.id, c.parent_id, c.name, t.depth + 1, t.path || c.id
  FROM   category c JOIN tree t ON c.parent_id = t.id
  WHERE  NOT c.id = ANY(t.path)                    -- cycle protection
)
SELECT * FROM tree;
```

The anchor runs once; the recursive term runs repeatedly against only the *previous* iteration's rows until it produces none. `UNION` (rather than `UNION ALL`) deduplicates each round, which handles simple cycles at a cost; carrying an explicit path array is the general protection and gives you the path for free. PostgreSQL 14+ supports `CYCLE` and `SEARCH` clauses that generate exactly this.

Real uses: bill-of-materials explosion, organizational hierarchy with depth, category trees, permission inheritance, and graph reachability with a depth cap. Beyond a few million edges or variable-length shortest-path queries, this is where I would look at a graph database or a materialized closure table instead - the recursive CTE has no index on the intermediate result and re-joins the base table every iteration.

### Q33. `LATERAL` joins

`LATERAL` lets the right-hand subquery reference columns from the left-hand row - effectively a correlated subquery that can return multiple rows and multiple columns. A plain join cannot do that: its right side is evaluated independently.

The three cases where it is the natural answer: top-N-per-group (Q30); calling a set-returning function per row (`CROSS JOIN LATERAL jsonb_array_elements(doc->'items')`); and computing several correlated aggregates for each row in one pass without repeating the subquery three times.

`CROSS JOIN LATERAL` drops the left row when the subquery is empty; `LEFT JOIN LATERAL ... ON true` keeps it - the distinction people always get wrong first time. SQL Server spells these `CROSS APPLY` and `OUTER APPLY`; Oracle 12c+ supports both `LATERAL` and `CROSS APPLY`.

### Q34. `GROUPING SETS`, `ROLLUP`, `CUBE`

`GROUPING SETS ((a,b),(a),())` computes several groupings in **one pass** over the input. `ROLLUP(a,b)` is the hierarchical subset - `(a,b)`, `(a)`, `()` - for subtotals down a drill-down path. `CUBE(a,b)` is all 2^n combinations, for a pivot in every direction.

Against `UNION ALL` of separate aggregate queries you save (n-1) scans and sorts of the same data, which on a large fact table is the difference between one expensive pass and four. You also get a single consistent snapshot, whereas separate queries in Read Committed can each see different data.

The one gotcha is telling a subtotal row apart from a genuine NULL in the grouping column - `GROUPING(a)` returns 1 for the aggregated-away case, and you need it in the `SELECT` if the column is nullable.

### Q35. Upsert: `ON CONFLICT`, `MERGE`, `INSERT IGNORE`

`INSERT ... ON CONFLICT (key) DO UPDATE` is atomic at the row level: PostgreSQL attempts the insert, and on a unique-violation from a *specified* arbiter index it takes the row lock and applies the update, with the new row visible as `excluded`. It is safe under concurrency and is what I use.

`MERGE` (SQL standard, Oracle, SQL Server, PostgreSQL 15+) is more general - it can insert, update and delete from a source relation - but it is *not* atomic in the same sense: it decides the action from a snapshot, so two concurrent `MERGE`s can both take the INSERT branch and one fails with a unique violation, or under Read Committed you get lost updates. Oracle and SQL Server both require a unique index and careful locking to make it safe; SQL Server's `MERGE` has a long history of concurrency bugs and most practitioners avoid it.

`INSERT IGNORE` (MySQL) suppresses *all* errors, not just duplicate keys, which turns a data-type error into a silently skipped row. `INSERT ... ON DUPLICATE KEY UPDATE` is the MySQL equivalent worth using.

### Q36. Concurrent upserts `[T]`

Under Read Committed, `ON CONFLICT DO UPDATE` handles the race internally: the second inserter blocks on the first's row lock, and when the first commits, the second re-reads and applies its update. That is why it is the recommended pattern.

You can still get a unique violation in three situations. First, `ON CONFLICT` only handles the conflict on the **arbiter index you named** - a violation of a *different* unique constraint is raised normally. Second, `DO NOTHING` with a concurrent insert that later rolls back can leave you with neither an insert nor a row to read (Q115). Third, under **Repeatable Read or Serializable**, the second transaction cannot see the newly committed row without violating its snapshot, so instead of updating it aborts with a serialization failure - which your retry loop must handle.

The related trap: `ON CONFLICT DO UPDATE` acquires a row lock even when the update is a no-op, so a high-frequency "upsert the same key" pattern serializes on one row and can deadlock if two statements touch multiple keys in different orders.

### Q37. `RETURNING` and data-modifying CTEs

`RETURNING` gives back rows affected by `INSERT`/`UPDATE`/`DELETE` in the same round trip - the generated key, the previous state, the computed default - with no second query and no race.

Combined with a CTE, it moves rows atomically:

```sql
WITH moved AS (
  DELETE FROM job_queue WHERE id = $1 RETURNING *
)
INSERT INTO job_archive SELECT *, now() FROM moved;
```

Both statements run in the **same snapshot** and the same statement, so no other transaction can observe the row in neither table or in both. The rules to know: all sub-statements see the same snapshot (so a data-modifying CTE cannot see another one's changes), execution order between them is not guaranteed except through data dependency, and trying to update the same row twice in one statement is undefined.

### Q38. Keyset pagination

Offset pagination makes the database produce and discard `OFFSET` rows, so page 10,000 costs 10,000 pages of work, and a concurrent insert shifts every subsequent page (rows are duplicated or skipped).

Keyset pagination remembers the last row's sort values and asks for what follows. For a non-unique sort column you must append a tiebreaker and compare as a row value:

```sql
SELECT ... FROM orders
WHERE  (created_at, id) < ($last_created_at, $last_id)   -- descending
ORDER  BY created_at DESC, id DESC
LIMIT  50;
```

with an index on `(created_at DESC, id DESC)`. Row-value comparison is the important detail - the naive `created_at < ? OR (created_at = ? AND id < ?)` is correct but frequently plans worse.

The cost is that you lose random access to page N and "jump to last page", so it fits infinite scroll and API cursors rather than a numbered pager over a small table, where `OFFSET` is perfectly fine.

### Q39. `SELECT COUNT(*)` on 200 million rows `[T]`

In PostgreSQL, an exact count must visit every row, because MVCC visibility lives in the tuples: the index cannot tell you whether a given row version is visible to your snapshot. An index-only scan can help when the visibility map is mostly all-visible, but it is still a full traversal. (InnoDB is in the same position; MyISAM and SQL Server keep a maintained row count and can answer instantly, which is where the expectation comes from.)

Three acceptable answers to "how many rows":

1. **An estimate** from `pg_class.reltuples`, or the planner's own estimate via `EXPLAIN` - accurate to a few percent right after `ANALYZE`, and free.
2. **A maintained counter** - a summary table updated by trigger or by the application, or a periodic job. Correct, but adds write contention (mitigate with sharded counters, Q113).
3. **A bounded count** - `SELECT count(*) FROM (SELECT 1 FROM t WHERE ... LIMIT 1000) x`, which powers "1,000+ results" in a UI and costs almost nothing.

The best answer starts with a question: nobody needs an exact count of 200 million rows; they need pagination metadata or a business metric, and both have cheaper implementations.

### Q40. Set-based versus row-by-row

A loop that issues one `UPDATE` per row pays parse, plan, network round trip, and a WAL record per row, and it holds the transaction open for the whole loop. The set-based form does one plan, one pass, one write batch:

```sql
UPDATE orders o
SET    status = 'EXPIRED'
FROM   payment p
WHERE  p.order_id = o.id AND p.state = 'FAILED' AND o.status = 'PENDING';
```

Typical improvements are one to two orders of magnitude, mostly from eliminating round trips.

The loop is genuinely better when the single statement would (a) lock too much for too long - a 50-million-row update blocks, bloats and creates replication lag, so you batch by key range with a commit per batch (Q249); (b) need per-row branching that SQL cannot express, such as calling an external service; or (c) risk exceeding `work_mem` or the undo/WAL capacity. The rule I use is: set-based within a batch, batched across the table.

### Q41. Stored procedures and triggers in 2026 `[A]`

My position: **constraints and integrity in the database, business logic in the application.** Triggers are acceptable for mechanical, invisible concerns - audit rows, `updated_at`, maintaining a denormalized counter or a search vector - and stored procedures for data-intensive work where moving the data to the application is the actual cost, such as a batch reconciliation over tens of millions of rows.

The reasons are practical, not ideological: procedural SQL has poor tooling for testing, code review, dependency injection and refactoring; it is deployed by a different mechanism than the application, so a rollback becomes two rollbacks; it is invisible in a stack trace, so debugging a trigger cascade during an incident is much harder; and it makes the database a shared runtime that no team owns, which is the coupling problem `03-microservices` Q61 is about.

The strongest argument against me is latency and atomicity: a procedure that does five statements does them in one round trip inside one transaction, and at high volume that difference is real - it is precisely why the outbox relay and batch jobs sometimes belong there. The second-strongest is that when several applications and an ETL all write the same tables, the database is the only place a rule can be enforced. I would concede both cases and still require that the logic be version-controlled, migration-deployed and tested like any other code.

*Hook: a trigger cascade that made an incident harder to diagnose, or a batch you deliberately pushed into the database.*

---

## 3. Indexing

### Q42. B+tree structure and depth

A B+tree stores keys in internal pages that route the search, and *all* the data pointers in leaf pages, which are linked to each other so a range scan walks sideways without returning to the root. PostgreSQL's implementation is a Lehman-Yao B-link tree, which allows concurrent reads during page splits without locking the whole tree.

The arithmetic: an 8 KB page holding, say, a 16-byte key plus pointer overhead fits roughly 300-400 entries. Three levels index about 400^3 = 64 million leaf entries, four levels about 25 billion. So a billion-row table is **four levels deep**, and a point lookup is at most four page reads - and the root and most of the second level are permanently in cache, so it is realistically one or two physical reads.

That is the number to quote when someone claims an index "must be slow because the table is huge": B-tree cost grows logarithmically, and the log base is in the hundreds.

### Q43. Clustered versus non-clustered

In InnoDB the table *is* the primary key B-tree - the leaf pages contain the full rows (a clustered index). A secondary index leaf holds the indexed columns plus the **primary key value**, so a lookup by secondary index is two traversals: the secondary tree, then the primary tree. Consequences: a wide primary key inflates every secondary index; primary-key range scans are sequential; and a covering secondary index avoids the second traversal.

PostgreSQL has no clustered index. The heap is unordered and every index leaf holds a **TID** (physical page and offset), so every index is "secondary" and every match costs one extra heap page fetch unless the index-only path applies (Q46). `CLUSTER` physically reorders the table once, but nothing maintains that order afterwards.

The practical differences: PostgreSQL treats all indexes equally so there is no primary-key privilege to design around, but it pays a heap fetch that InnoDB avoids for primary-key access, and it needs the visibility map to make index-only scans possible.

### Q44. Leftmost prefix on `(a, b, c)`

The index is sorted by `a`, then `b` within equal `a`, then `c`. So a scan can use, in order, an equality or range on `a`; then `b` only if `a` was an equality; then `c` only if both `a` and `b` were equalities.

| Predicate | Usable |
| --- | --- |
| `a = ?` | Yes, full range on `a` |
| `a = ? AND b = ?` | Yes, both as access predicates |
| `a = ? AND b = ? AND c = ?` | Yes, all three |
| `a = ? AND c = ?` | `a` seeks; `c` is only a filter on the rows found |
| `a > ? AND b = ?` | `a` seeks; `b` is only a filter |
| `b = ?` alone | Not as an access predicate |

The nuance PostgreSQL adds: it *can* still scan the whole index and filter on `b` alone (a full index scan), which is cheaper than a heap scan if the index is much narrower than the table - so "the index is not used at all" is not strictly true, but it is not the seek you wanted. The index also serves `ORDER BY a, b` for free.

### Q45. Column order for `a = ?, b > ?, c = ?` `[T]`

`(a, c, b)`. Put **all equality columns first**, then the range column last.

The reason is that a B-tree seek can only maintain a contiguous range: once you consume a range predicate on `b`, everything after `b` in the key is no longer sorted within the scanned span, so `c` degenerates to a filter applied to every row the range returns. With `(a, b, c)` you seek on `a = ?` plus `b > ?` and then check `c` on each of possibly millions of rows. With `(a, c, b)` you seek directly to the `(a, c)` pair and read only the qualifying `b` range.

`c` still earns its place in the index even in the wrong position - it can be evaluated from the index rather than the heap - but as an *access* predicate it is worthless there. The general rule to state: equality columns first (most selective first among them matters less than people think), one range column last, and any purely-returned columns in `INCLUDE`.

### Q46. Index-only scans and the visibility map

PostgreSQL index entries do not carry MVCC information, so it normally has to visit the heap tuple to check visibility. The **visibility map** is a two-bit-per-page structure that marks pages where *all* tuples are visible to all transactions. During an index-only scan the executor checks the map: if the page is all-visible, it returns the values straight from the index; if not, it fetches the heap tuple after all.

So an index-only scan degrades toward an ordinary index scan when the table has recent writes, and the plan shows this as `Heap Fetches: N`. What makes it stop being index-only: a write-heavy table where autovacuum cannot keep up (vacuum is what sets the visibility bits), a long-running transaction holding back the xmin horizon so pages can never be marked all-visible, or simply querying a column that is not in the index.

The operational fix is aggressive autovacuum settings on that table, not more indexes.

### Q47. `INCLUDE` columns versus key columns

`INCLUDE` columns are stored **only in the leaf pages** and are not part of the ordering. Compared with adding the column to the key:

- **Size**: `INCLUDE` keeps internal pages narrow, so the tree stays shallower and the non-leaf levels stay in cache.
- **Ordering**: an included column cannot be used for seeking, range filtering as an access predicate, or `ORDER BY`.
- **Uniqueness**: with a unique index, `INCLUDE` columns are excluded from the uniqueness check - which is exactly what you want for `UNIQUE (email) INCLUDE (display_name)`.
- **Types**: `INCLUDE` accepts types with no B-tree operator class at all.

I use `INCLUDE` when the column is only there to make a scan index-only, and a key column when I need it for filtering or ordering.

### Q48. Partial indexes

A partial index covers only rows matching a predicate, so it is smaller, cheaper to maintain, and often dramatically more selective.

Three high-value uses: (1) the active subset - `WHERE deleted_at IS NULL` or `WHERE status = 'ACTIVE'` on a table where 99 percent of rows are historical; (2) enforcing conditional uniqueness, which no plain constraint can do (Q12); (3) indexing a rare value - `WHERE status = 'FAILED'` on a queue table where failures are 0.1 percent, giving a tiny index for the query that matters at 3 a.m.

The requirement is that the planner must be able to *prove* the query predicate implies the index predicate, and its proof engine is deliberately simple. `WHERE status = 'ACTIVE'` matches an index on `WHERE status = 'ACTIVE'`, but `WHERE status = $1` does not, even when the parameter happens to be 'ACTIVE'. That single fact catches most people: partial indexes and parameterized queries fight each other, and you often need the literal or a dedicated query path.

### Q49. Expression indexes

`WHERE lower(email) = ?` cannot use an index on `email`, because the index stores the raw values and the planner will not invert an arbitrary function. `CREATE INDEX ON users (lower(email))` stores the computed value and matches the expression textually.

The statistics consequence is the interesting part: PostgreSQL collects a **separate statistics entry for the expression**, so after `ANALYZE` the planner knows the distribution of `lower(email)` rather than guessing. That is often a bigger win than the index itself for a skewed expression, and it is why `CREATE STATISTICS` on an expression is sometimes worthwhile even without an index.

Requirements and costs: the function must be `IMMUTABLE` (so `lower()` in a fixed collation is fine, `now()` is not), and the expression is evaluated on every insert and on every update of the underlying column. For case-insensitive matching specifically, a `citext` column or a case-insensitive ICU collation is the cleaner long-term answer.

### Q50. Six ways to make an index unusable `[T]`

1. **Wrap the column in a function or a cast** - `WHERE date(created_at) = ?`, or comparing a `varchar` column to an integer parameter, which forces an implicit cast on the *column*.
2. **Leading wildcard** - `LIKE '%term'` cannot use a B-tree (use `pg_trgm`, Q55).
3. **Break the leftmost prefix** - query only `b` from `(a, b)` (Q44).
4. **Type or collation mismatch** - a `text` column indexed under one collation compared under another, or `varchar` vs `text` across a join in some engines.
5. **`OR` across columns with no bitmap plan available**, or a predicate the planner cannot prove matches a partial index (Q48).
6. **Low selectivity or bad statistics** - the planner correctly concludes a sequential scan is cheaper, or incorrectly concludes it because `ANALYZE` has not run (Q69).

Honourable mentions: `NOT`/`<>` predicates, `ORDER BY` with a direction the index cannot satisfy in a multi-column mix (`a ASC, b DESC` needs a matching index), and parallel/JIT settings changing the cost comparison.

### Q51. Selectivity and the crossover point

Selectivity is the fraction of rows a predicate keeps. An index scan costs roughly one random page read per matching row (in the worst case, one heap page per row), while a sequential scan reads every page but sequentially and with readahead.

The crossover is therefore not a fixed percentage. It depends on: the ratio `random_page_cost / seq_page_cost` (default 4.0, realistic on SSD is 1.1-2.0); **correlation** between the index order and the physical row order, which PostgreSQL tracks per column - a perfectly correlated column means the "random" fetches are actually sequential, so an index can win at 50 percent selectivity; the row width, which determines rows per page; and whether the scan can be index-only.

The commonly quoted "5 to 10 percent" is a heuristic for an uncorrelated column on spinning disk. The right answer in an interview is the list of factors plus the observation that a *bitmap* index scan exists precisely to interpolate between the two extremes.

### Q52. Bitmap index scans

A bitmap index scan solves the "too many rows for an index scan, too few for a sequential scan" middle ground, and the "combine two indexes" problem. It runs the index scan first, builds an in-memory bitmap of matching heap **pages**, and then reads those pages in *physical order* - turning random IO into something close to sequential and visiting each page once even if it holds twenty matches.

Because it produces page-level results, the heap access is followed by a **recheck** of the original condition, which is why you see `Recheck Cond` in the plan.

`lossy` means the bitmap ran out of `work_mem` and degraded from tracking individual tuples to tracking whole pages, so every tuple on those pages must be rechecked. `Heap Blocks: exact=1200 lossy=48000` in `EXPLAIN ANALYZE` is a direct signal that raising `work_mem` for that query will help. `BitmapAnd`/`BitmapOr` nodes combine bitmaps from several indexes, which is how PostgreSQL uses two single-column indexes for an `AND` - usefully, but never as well as one correct composite index.

### Q53. Index types by workload

| Type | Workload |
| --- | --- |
| **B-tree** | Everything ordered: equality, ranges, `ORDER BY`, uniqueness. The default and right answer 90 percent of the time. |
| **GIN** | One row contains many searchable values: full-text `tsvector`, JSONB containment, array membership, trigrams. Fast reads, slow and bulky writes, mitigated by the pending-list (`fastupdate`). |
| **GiST** | Overlap and nearest-neighbour on complex types: geometry (PostGIS), ranges and `EXCLUDE` constraints, k-NN ordering. Lossy, so it rechecks. |
| **SP-GiST** | Non-balanced partitioned structures: quadtrees, radix trees on text prefixes, IP addresses. |
| **BRIN** | Enormous, naturally ordered, append-only tables - time-series by timestamp. Stores min/max per block range, so the index is kilobytes for a terabyte table. Useless if physical order and value order diverge. |
| **Hash** | Equality only, on very wide keys where a B-tree would be large. WAL-logged and crash-safe since PostgreSQL 10, but the niche is narrow; B-tree is usually as good. |

BRIN is the one worth volunteering: for an append-only events table, a BRIN index on `created_at` gives most of the range-scan benefit for a fraction of a percent of the storage and near-zero write cost.

### Q54. Full-text search in PostgreSQL

`to_tsvector(config, text)` normalizes text into lexemes with positions, applying the configuration's parser, dictionaries and stemming; `to_tsquery`/`plainto_tsquery`/`websearch_to_tsquery` build the query side; the `@@` operator matches; `ts_rank`/`ts_rank_cd` scores. A GIN index over a stored generated `tsvector` column is the standard setup, with `setweight` used to weight title above body.

It is genuinely good enough for: search within a tenant's data, admin search, "find the document", and anything where the corpus is a table you already have and consistency with the transactional data matters (no sync pipeline, no dual write).

I move to Elasticsearch or OpenSearch when I need relevance tuning as a product feature (custom analyzers per language, synonyms, fuzzy matching, learning-to-rank), faceted aggregation over large result sets, sub-100ms search across tens of millions of documents, or a search team who need to iterate without a database migration. The cost of moving is the sync pipeline and its drift (Q216), which is exactly why I do not move earlier than necessary.

### Q55. Trigram indexes

`pg_trgm` decomposes a string into overlapping three-character sequences (`hello` becomes `  h`, ` he`, `hel`, `ell`, `llo`, `lo `). A GIN or GiST index over those trigrams lets `LIKE '%ell%'`, `ILIKE`, and similarity (`%` operator, `word_similarity`) find candidate rows by intersecting posting lists, then rechecking the actual pattern.

It is the answer to unanchored `LIKE`, to typo-tolerant name lookup, and to "search box over a few columns" without leaving the database.

Costs: the index is large (many trigrams per row), writes pay for extracting and inserting all of them, patterns shorter than three characters cannot be indexed at all, and the recheck means selectivity estimates are rough. GIN is faster to search and slower to update; GiST is smaller and supports distance ordering. On a write-heavy table I would measure the insert regression before shipping it.

### Q56. The write cost of an index

- **`INSERT`**: one index entry per index, each potentially causing a page split. This is why bulk loads drop indexes and rebuild them.
- **`UPDATE` of an indexed column**: because MVCC writes a new tuple version, the new tuple needs new entries in **every** index, not just the one on the changed column, and the old entries remain until vacuum.
- **`UPDATE` of a non-indexed column**: eligible for a **HOT update** (Q130) - the new version is placed on the same page and chained from the old one, and **no index is touched at all**. This is the single most important write optimization in PostgreSQL.

The consequences to state: adding an index to a frequently updated column can destroy HOT eligibility across the whole table and multiply write IO; leaving `fillfactor` at 100 on a hot table means no room on the page for the new version, which also breaks HOT; and every extra index is paid for on every write, every vacuum and every backup, not just on inserts.

### Q57. Index bloat

Bloat is dead space in index pages: deleted or updated entries are only removed by vacuum, page splits leave pages half full, and a random-key workload (Q6) or a table with heavy churn leaves indexes far larger than their live data. B-trees do not merge underfull pages back together, so an index that grew during a bulk delete never shrinks on its own.

Measure it with the `pgstattuple`/`pgstatindex` extensions for accuracy, or the common estimate queries against `pg_class` and `pg_stats` for a cheap approximation; the operational signal is index size growing while row count is flat, and cache hit ratio falling.

`REINDEX CONCURRENTLY` (PostgreSQL 12+) rebuilds an index without an exclusive lock - it builds a new index, swaps, then drops the old - at the cost of double the disk space during the build and a failure mode that leaves an invalid index behind (`_ccnew`), which you must clean up. `pg_repack` rewrites the *table* and all its indexes online and is what I use when the heap is bloated too. `VACUUM FULL` does both but takes `ACCESS EXCLUSIVE` for the duration, so it is a maintenance-window tool only.

### Q58. Fourteen indexes, which to drop `[T]`

Fastest defensible method: read `pg_stat_user_indexes` for `idx_scan` counts, reset the statistics at a known point, and let it run through a **full business cycle** - including month-end, quarterly reporting and the batch jobs. Anything with `idx_scan = 0` after that is a candidate. Cross-reference `pg_stat_statements` to see which queries actually run.

Before dropping any, check four things: (1) it is not enforcing a **unique constraint** or backing a **primary key** or **foreign key** - those are constraints, not just indexes; (2) it is not needed by a query on a *replica*, since index statistics are per-node and reporting often runs elsewhere; (3) it is not the index used only by an emergency runbook or the annual audit query; (4) whether a broader index makes it redundant - `(a)` is redundant if `(a, b)` exists, though not vice versa.

The safe procedure is to make it invisible first: PostgreSQL has no invisible-index feature (MySQL 8 and Oracle do), so the equivalent is dropping it inside a transaction in a maintenance window with the recreate script ready, or reindexing it as `INVALID`. In practice I drop with a `CREATE INDEX CONCURRENTLY` script prepared and the size noted, so restoring takes minutes.

### Q59. Unique and deferrable constraints

A unique index enforces uniqueness at **statement** time: the inserting transaction takes a lock on the index entry and a concurrent duplicate blocks until the first commits or rolls back. That is why a unique constraint is a genuine concurrency control, not just a check.

`DEFERRABLE INITIALLY DEFERRED` postpones the check to `COMMIT`. You need it when a legal intermediate state violates the constraint - renumbering positions in an ordered list (`UPDATE items SET pos = pos + 1`) is the classic, along with swapping two unique values, and circular foreign key references between two tables inserted in one transaction.

Costs: deferred checks accumulate in a per-transaction queue, so a large batch uses memory and reports all failures late, when the transaction is expensive to lose. PostgreSQL also cannot use a deferrable unique constraint as the arbiter for `ON CONFLICT`. So I make constraints deferrable only where an intermediate violation is genuinely required.

### Q60. `CREATE INDEX CONCURRENTLY`

It avoids the `ACCESS EXCLUSIVE`-equivalent write lock of a normal index build by doing **two passes** over the table plus waits: build from a snapshot, then a second pass to catch rows changed during the first, waiting for all transactions older than each phase to finish. Reads and writes continue throughout.

The costs: it takes roughly twice as long and more IO; it cannot run inside a transaction block (so a migration tool must be told not to wrap it); it waits on **any** long-running transaction, including on a hot standby with `hot_standby_feedback`, so one idle-in-transaction session stalls it indefinitely; and if it fails it leaves an **invalid index** that consumes writes but is never used by queries.

The procedure I run: check for long transactions first, run it outside the deployment transaction with a generous timeout and monitoring, then verify `pg_index.indisvalid`; if invalid, `DROP INDEX CONCURRENTLY` and retry. On a partitioned table you build on each partition and then attach, because building on the parent takes a strong lock.

### Q61. A new index makes the query slower `[T]`

Three genuine mechanisms:

1. **The planner switches to a worse plan.** The new index changes the cost landscape; a bad row estimate that was harmless with a hash join now produces a nested loop driven by the new index, executed millions of times. This is the most common case, and the plan diff proves it.
2. **The index is correct but the access pattern is bad.** The optimizer chose an index scan where a bitmap or sequential scan was better - typically low correlation, high row count, and a `random_page_cost` that does not reflect SSD. Random single-row heap fetches for 30 percent of a table is slower than reading the table.
3. **The write cost lands on the read path.** The index broke HOT updates (Q56, Q130), so the table now bloats faster, pages hold fewer live rows, autovacuum runs constantly, and *every* query on that table reads more pages. This one is invisible if you only look at the query you were tuning.

There is also a fourth, self-inflicted case: the index was created but never analyzed, or a partial/expression index shifted the statistics so a different query regressed. Always compare plans before and after, and look at the table's overall throughput, not just the target query.

### Q62. Index policy for a team `[A]`

What I would put in place, in the order it earns its keep:

1. **Evidence required with the change.** Any new index arrives with the query, the `EXPLAIN (ANALYZE, BUFFERS)` before, the expected plan after, and the estimated size. No evidence, no index. This alone stops most sprawl, because half of proposed indexes turn out to duplicate an existing one.
2. **Owned by the team that owns the table**, reviewed by whoever is on call for that database - not by a central architecture board, which becomes a queue.
3. **Automated hygiene**: a weekly report of unused indexes (`idx_scan = 0` over a full cycle), redundant prefixes, duplicate definitions, bloat above a threshold, and foreign keys with no index. Reported to the owning team, not to a central backlog.
4. **A budget, not a ban**: a soft cap (say six indexes per OLTP table) that requires a written justification to exceed, which makes the write cost visible in the conversation.
5. **Always `CONCURRENTLY` in production**, always with the drop script attached.

The cultural point is that indexes are the cheapest performance intervention and the easiest to accumulate; the policy exists to keep the *removal* path as easy as the addition path.

*Hook: an index review that removed a third of a schema's indexes and improved write latency.*

---

## 4. The optimizer and query tuning

### Q63. Parse, rewrite, plan, execute

**Parse** produces a syntax tree and resolves names against the catalog. **Rewrite** applies rules - view expansion, row-level security predicates. **Plan** enumerates access paths and join orders and picks the cheapest by estimated cost. **Execute** runs the plan tree, pulling tuples through the nodes.

Caching differs sharply. PostgreSQL has **no shared plan cache**: plans are cached per session in prepared statements (and by PL/pgSQL for its statements), so every connection plans independently and a pooler that reuses sessions changes the behavior (Q239). It caches *data* pages in `shared_buffers` but never query results.

Oracle has a **shared pool** with a library cache keyed by exact SQL text, so all sessions share one plan, and it adds bind-variable peeking, adaptive cursor sharing and SQL plan baselines on top. SQL Server likewise caches plans server-wide, which is the origin of parameter sniffing (Q72). The consequence: hard-parse cost is a real concern in Oracle and drives bind-variable discipline; in PostgreSQL the same discipline is about avoiding plan-cache misses per session and about SQL injection, not about a shared pool.

### Q64. Cost-based planning and the cost constants

The planner assigns each candidate path an abstract cost and picks the minimum. The unit is arbitrary: `seq_page_cost = 1.0` by definition, and everything else is relative to it - `random_page_cost = 4.0`, `cpu_tuple_cost = 0.01`, `cpu_index_tuple_cost = 0.005`, `cpu_operator_cost = 0.0025`.

Total cost is estimated rows times per-row CPU cost plus estimated page reads times the relevant page cost, propagated up the tree. `effective_cache_size` is not a memory allocation; it tells the planner how much of the table is *likely* already cached, which reduces the effective cost of an index scan.

The default 4:1 ratio encodes a spinning disk, where a random seek genuinely costs several times a sequential read. On SSD or cloud block storage the real ratio is closer to 1.1-2.0, and leaving it at 4.0 systematically biases the planner toward sequential scans - one of the highest-value single settings to change. I set `random_page_cost = 1.1` on NVMe and around 1.5-2.0 on network storage, and I set `effective_cache_size` to roughly 60-75 percent of system RAM.

### Q65. Reading `EXPLAIN (ANALYZE, BUFFERS)`

Fields: `cost=start..total` is the planner's estimate in cost units (start cost is the work before the first row, which is why a sort's start cost is high); `rows` is the estimate **per loop**; `actual time=start..total` is measured milliseconds **per loop**; `loops` is how many times the node ran, so total time is `actual time * loops`; `shared hit` is pages found in `shared_buffers` and `read` is pages fetched from the OS or disk.

How I read it, in order:

1. Find the node where `rows` and `actual rows` diverge most, going **bottom-up** - the first bad estimate causes every wrong decision above it (Q66).
2. Multiply `actual time` by `loops` to find where the wall clock actually went; a node showing 0.03 ms with 400,000 loops is the problem, not the 20 ms sort.
3. Look at `read` versus `hit` to distinguish an IO problem from a CPU/row-volume problem.
4. Look for `Rows Removed by Filter`, which means work done and thrown away - usually a missing or mis-ordered index.
5. Check for spills: `Sort Method: external merge Disk: 240MB`, or `lossy` bitmap blocks (Q52).

The point to make out loud: I tune the *first wrong estimate*, not the slowest node.

### Q66. `rows=1` versus 4.2 million actual `[T]`

First thing I check: when did `ANALYZE` last run on that table - `pg_stat_user_tables.last_autoanalyze` - and how many rows have changed since.

The four common causes of an error of that magnitude:

1. **Stale or missing statistics** after a bulk load, a restore, or a table growing fast enough that the autoanalyze threshold lags. A restored database with no `ANALYZE` is the classic.
2. **Correlated predicates.** The planner multiplies selectivities as if independent, so `WHERE city = 'Bengaluru' AND state = 'Karnataka'` gets estimated as the product of two fractions when the second is implied by the first. Fixed with extended statistics (Q70).
3. **An expression or function the planner cannot see through** - `WHERE lower(email) = ?` or a `STABLE` function in the predicate falls back to a hard-coded default selectivity (0.5 percent for equality). Fixed with an expression index or `CREATE STATISTICS` on the expression.
4. **Skew the statistics do not capture** - `n_distinct` estimated badly on a large table (it is sampled, and it is wrong on scale-with-table columns), or a value that is not in the MCV list but is enormously common.

Non-statistical causes worth naming: a join on a column with a non-uniform distribution, and estimates through a `LIMIT` inside a subquery. The action is the same either way - `ANALYZE`, then extended statistics or a `n_distinct` override, then reshaping the query if the estimate is structurally unknowable.

### Q67. Nested loop, hash join, merge join

| | Nested loop | Hash join | Merge join |
| --- | --- | --- | --- |
| Cost model | outer rows x inner lookup | build side rows + probe side rows | sort both + one pass |
| Memory | negligible | hash table of the build side, `work_mem` | sort buffers, `work_mem` |
| Needs | an index on the inner side to be viable | equality join condition | both inputs sorted on the key |
| Wins when | outer side is small and inner has an index | one side fits in memory, no useful ordering | inputs already sorted, or output must be sorted |
| Fails when | outer side is large - cost is multiplicative | build side exceeds `work_mem`, spilling to batches | sorting is expensive and nothing needs the order |

Nested loop is the only one that supports non-equality joins and `LATERAL`. Hash join is the workhorse for large unordered joins, and its degradation mode is graceful but expensive (multi-batch spill to disk). Merge join is often chosen when both sides come from index scans in key order, which is free ordering.

The failure everyone has seen: a nested loop chosen because the outer estimate said 5 rows, executed 5 million times.

### Q68. A nested loop over 2 million rows `[T]`

Not always wrong. It is optimal when the inner side is a **unique index lookup on a cached table** - two million lookups into a small, fully cached dimension table is a few hundred nanoseconds each and beats building a hash table over a large outer relation. It is also the only option for a `LATERAL` or a non-equality join, and it is the right choice under `LIMIT`, where it can produce the first rows immediately while a hash join must build first.

What makes it wrong is the combination of a large outer side, an inner side that is *not* an index lookup (a nested loop over a sequential scan is quadratic), or an inner side too large to stay in cache so every probe is a random read.

So the diagnostic question is not "is there a nested loop" but "what is `loops` times the per-loop cost, and was the outer row estimate right". If the outer estimate is right and the inner is an index probe on cached pages, leave it alone.

### Q69. Planner statistics and `ANALYZE`

Per column, in `pg_statistic` (readable via `pg_stats`): the fraction of nulls, average width, `n_distinct`, a **most-common-values** list with their frequencies, a **histogram** of the remaining values, and the physical/logical **correlation**. Per table, in `pg_class`: `reltuples` and `relpages`.

`ANALYZE` takes a **random sample** - by default 300 x `default_statistics_target` rows, so 30,000 rows at the default of 100 - and computes those structures from the sample. It is not a full scan, which is why it is cheap and why `n_distinct` on a huge table is often badly wrong.

`default_statistics_target` controls both the sample size and the number of MCV/histogram entries. Raising it (per column, with `ALTER TABLE ... ALTER COLUMN ... SET STATISTICS 1000`) gives a finer histogram and a longer MCV list, which is the fix for a skewed column where a few values dominate. The cost is a longer `ANALYZE` and slightly slower planning. I raise it selectively on the columns that drive bad plans rather than globally.

### Q70. Extended statistics

`CREATE STATISTICS` declares that a set of columns should be analyzed **together**, fixing the planner's independence assumption. Three kinds: `ndistinct` (the number of distinct combinations, which fixes `GROUP BY` and join estimates), `dependencies` (functional dependency, which fixes equality predicates where one column implies another), and `mcv` (a multivariate most-common-values list, which handles skewed combinations and inequality predicates).

The query shape that needs it: two or more predicates on correlated columns of the same table.

```sql
CREATE STATISTICS city_state (dependencies, mcv) ON city, state FROM addresses;
ANALYZE addresses;
```

Without it, `WHERE city = 'Bengaluru' AND state = 'Karnataka'` is estimated as 0.001 x 0.03 of the table when the true selectivity is 0.001 - a 30x underestimate that turns a hash join into a nested loop. PostgreSQL 14+ also supports statistics on expressions, which fixes the function-in-predicate case from Q66.

### Q71. Histogram, MCV and `n_distinct`

The **MCV list** holds the most frequent values with exact frequencies; the **histogram** divides the remaining values into equal-frequency buckets; `n_distinct` is the estimated number of distinct values (negative values mean "a fraction of the table", which is how it expresses scale-with-table columns).

`n_distinct` fails first on a skewed or large column, because it is extrapolated from a small sample and sampling cannot see distinctness reliably - a column with 10 million distinct values in a 500-million-row table can be estimated at 200,000. Everything downstream is then wrong: `GROUP BY` cardinality, join size, hash table sizing.

The fix is an override, which is one of the few "hints" PostgreSQL does offer:

```sql
ALTER TABLE events ALTER COLUMN session_id SET (n_distinct = -0.3);
ANALYZE events;
```

For skew where a few values dominate, raise the statistics target instead so those values land in the MCV list and get exact frequencies. The two problems look similar and have different fixes, which is worth saying explicitly.

### Q72. Parameter sniffing and generic plans `[T]`

**SQL Server / Oracle**: the plan is compiled on first execution using the *actual* parameter values ("sniffed") and cached server-wide. If the first call passes an atypical value - a customer with three orders when most have three million, or vice versa - every later execution gets a plan tuned for the wrong distribution. Fixes: `OPTIMIZE FOR` a representative value or `OPTIMIZE FOR UNKNOWN`, `RECOMPILE` per execution, plan guides/baselines, splitting into separate procedures per shape, or Oracle's adaptive cursor sharing which detects the problem and keeps multiple plans.

**PostgreSQL**: a prepared statement is planned with the actual values for the first five executions (a **custom plan** each time), then it compares the average custom-plan cost with a **generic plan** cost, and if the generic plan is not more expensive it switches permanently. The failure is the mirror image: a query over a skewed column gets locked into a generic plan that is good on average and terrible for the values that matter. Fixes: `plan_cache_mode = force_custom_plan` (session or per-transaction), avoiding server-side prepared statements for that query, or using a literal.

The commonality worth stating: both engines are trading plan-compilation cost against plan quality, and the failure always happens on skewed data.

### Q73. Transformations, and what blocks them

**Predicate pushdown** moves a filter as close to the scan as possible so fewer rows are produced. **Join reordering** searches permutations of join order (exhaustively below `join_collapse_limit`, then greedily, and via GEQO above `geqo_threshold`). **Subquery flattening** and **view merging** pull a subquery or view into the outer query so its tables participate in the global join ordering.

What blocks them: a **materialized CTE** is an optimization fence in both directions (Q31); a subquery with `LIMIT`, `OFFSET`, `DISTINCT ON` or a window function cannot be flattened because the row set would change; an aggregate or `GROUP BY` blocks pushdown of predicates that reference the aggregate; a volatile function anywhere prevents reordering and caching; and `OFFSET 0` is the traditional deliberate fence.

`LIMIT` is the interesting one: it does not block pushdown but it changes the cost model, because the planner optimizes for the *first* N rows and will happily choose a plan with a terrible total cost but a low start cost - which is why "add `LIMIT 10` and it got slower" happens.

### Q74. Functions in `WHERE`, and volatility

An index stores `f(column)` only if you built an expression index on exactly that expression; otherwise the planner cannot invert an arbitrary function, so `WHERE f(col) = ?` must evaluate `f` for every row - a sequential scan with a filter.

Volatility classes:

- **`IMMUTABLE`** - same inputs always give the same result, forever (`lower`, arithmetic). Can be constant-folded at plan time, usable in expression indexes and in partial index predicates.
- **`STABLE`** - constant within a single statement, but may vary between statements (`now()`, anything reading the database, `current_setting`). Can be evaluated once per statement and used with an index scan as a *parameter*, but cannot be indexed.
- **`VOLATILE`** - may change per row (`random()`, `nextval`, anything with side effects). Evaluated per row, blocks many optimizations, and cannot be pushed into a scan safely.

Two practical consequences: declaring a function `VOLATILE` when it is really `STABLE` (the default for a new function is `VOLATILE`) is a common, invisible performance bug; and a `STABLE` function in a predicate has no statistics, so the planner uses a default selectivity - which is a frequent cause of the Q66 estimate error.

### Q75. Literal fast, bind parameter slow - and the reverse `[T]`

**Literal fast, bind slow**: with a literal the planner knows the value and can consult the MCV list and histogram, choosing an index scan for a rare value. With a bind parameter under a generic plan it must use average selectivity, so a rare value gets a plan built for the common case (Q72). Also, a partial index whose predicate matches the literal cannot be proven to match a parameter (Q48), and `LIKE 'abc%'` with a literal can be rewritten into a range while `LIKE ?` cannot be, unless the driver plans per execution.

**Bind fast, literal slow**: on Oracle and SQL Server, literals produce a distinct SQL text per value, so every execution hard-parses, floods the shared pool with single-use cursors and burns CPU on parsing - the reason `CURSOR_SHARING` and bind discipline exist. There is also the security direction: literals mean string building, which means SQL injection.

The synthesis: use bind parameters as the default for correctness and parse cost, and make the exception explicit for the small number of queries over skewed columns where you need per-value planning - via `force_custom_plan`, or by not using a server-side prepared statement for that one query.

### Q76. `work_mem`

`work_mem` is the memory limit for **each sort, hash table, hash aggregate, bitmap and materialize node**, per node, per parallel worker - not per query and not per connection. A single query with three sorts and two hash joins running with four parallel workers can use many multiples of it.

When a sort exceeds it, PostgreSQL switches to an external merge sort, writing runs to temporary files (`Sort Method: external merge Disk: 512MB` in the plan). A hash join spills into multiple batches, rereading both sides. A hash aggregate before PostgreSQL 13 could not spill at all and simply exceeded the limit; from 13 it spills to disk, which is safer and can be a surprise regression.

Setting it globally high is dangerous precisely because of the multiplication: 256 MB with 200 connections and several nodes each is far more than the machine has, and the failure is the OOM killer taking down the postmaster. My approach is a modest global value (16-64 MB depending on the workload), raised per session or per transaction for known heavy reporting queries, plus `SET LOCAL` inside the transaction so it cannot leak into a pooled connection.

### Q77. Parallel query

The planner considers a parallel plan when the table is larger than `min_parallel_table_scan_size`, the query is not parallel-unsafe (no volatile functions writing data, no cursors, no `FOR UPDATE`), and the estimated cost is high enough that `parallel_setup_cost` and `parallel_tuple_cost` are worth paying. Worker count comes from the relation size, `max_parallel_workers_per_gather` and the global worker pool.

A **Gather** node collects tuples from the workers into the leader in arbitrary order; **Gather Merge** preserves sort order from workers that each produced sorted output. The leader also participates in the scan unless it is busy consuming.

Speedup is sublinear because of the fixed startup cost of forking workers and setting up shared memory, the tuple-transfer cost through the shared queue, the parts of the plan that cannot be parallelized (the final aggregate combine, anything above the Gather), and contention for IO bandwidth and the buffer pool - Amdahl's law applied to a query. It also competes with concurrency: on an OLTP system with 200 active sessions, parallelism steals capacity from other queries, which is why I frequently reduce it on OLTP nodes and raise it on the reporting replica.

### Q78. Plan regression

Detection: I want per-query latency tracked over time, which means `pg_stat_statements` snapshots (mean and total time per `queryid`) compared release over release and after any bulk load or upgrade, plus `auto_explain` with `log_min_duration` set so the actual plan of a slow execution is captured rather than reconstructed later. A regression shows as one `queryid` whose mean time steps up while its call count is flat.

Stabilizing in **PostgreSQL**: there is no plan baseline mechanism. The tools are: refresh or strengthen statistics (`ANALYZE`, statistics target, extended statistics), fix the cost constants, restructure the query so the good plan is the only cheap one (this is what "tuning" mostly means here), `pg_hint_plan` if you must, and in extreme cases disabling an operator for a session (`SET enable_nestloop = off`) as a *diagnostic* rather than a fix.

**Oracle** has SQL Plan Management: capture baselines, and the optimizer will only use a new plan after it has been verified as faster, which makes upgrades far safer. SQL Server has the Query Store with forced plans and automatic plan-regression correction. Naming this difference honestly - PostgreSQL trades plan stability for simplicity - is a strong signal in an interview.

### Q79. No hints in PostgreSQL

The project's position is that hints encode a decision made with today's data and today's statistics, and they silently become wrong; the supportable path is to fix the information the planner has.

So what I do instead, in order: `ANALYZE` and statistics targets; extended statistics for correlation; expression indexes so the predicate is visible; cost constants that match the hardware; rewriting the query (turning a correlated subquery into a join, adding a `LATERAL`, splitting an `OR`, materializing a CTE deliberately); and, when a query genuinely cannot be planned well, materializing an intermediate result into a temporary table with its own `ANALYZE`.

`pg_hint_plan` exists and works, but it costs you: it is an extension that must be installed and upgraded in lockstep, hints are attached to query text so they break when the ORM changes whitespace, and they freeze a decision that nobody revisits. I would use it as a temporary stabilizer with a ticket to remove it, in the same spirit as `@Lazy` on a circular dependency.

### Q80. Slow only in production `[T]`

With the same data volume in staging, I check in this order, because it is cheapest-first and each step eliminates a class:

1. **Concurrency.** Staging runs the query alone; production runs it with 300 other sessions. Lock waits, buffer contention, IO saturation and CPU steal all appear only under load. Check `pg_stat_activity` wait events during a slow execution.
2. **Cache state.** Production's working set may not fit in `shared_buffers` while staging's smaller total footprint does. Compare `shared hit` versus `read` in the plan.
3. **Statistics and plan.** Get the *actual production plan* with `auto_explain`, not the staging plan. Different statistics, different `n_distinct`, different parameter values under a generic plan (Q72).
4. **Data distribution.** Same row count is not the same distribution: production has one customer with 40 percent of the rows, staging has a uniform generator. This is the single most common cause I have seen.
5. **Configuration and hardware.** `work_mem`, `random_page_cost`, parallel settings, instance class, storage IOPS credits and burst balance.
6. **Bloat and vacuum state.** Production has been running for two years; staging was restored last week.
7. **The environment around it** - a pooler in transaction mode, a read replica with lag, an ORM issuing a different statement, or a different driver version.

### Q81. 90 seconds to 5 on a reporting query `[A]`

My method, in order:

1. **Establish the requirement.** Is 5 seconds a hard SLA, is the result needed live, and how fresh must it be? Half of these problems dissolve into "this can be a materialized view refreshed every 10 minutes".
2. **Get the plan** with `EXPLAIN (ANALYZE, BUFFERS)` and find the first badly wrong estimate and the node with the real wall clock (Q65).
3. **Cheap structural wins**: statistics, an index that turns a scan into a seek, removing a function from a predicate, replacing `OFFSET` with keyset, eliminating a redundant `DISTINCT` that hides a join fan-out.
4. **Rewrite**: push aggregation down before joining, replace correlated subqueries, use `FILTER` aggregates instead of repeated scans, split into a CTE that materializes a small intermediate result and `ANALYZE` a temp table if needed.
5. **Resource tuning**: `work_mem` for this query, parallel workers, running it on a replica.
6. **Change the shape of the data**: a covering index, a partial index for the reported subset, partitioning so the report prunes to one month, a materialized view or a summary table maintained incrementally.

**Where I stop tuning and change the architecture**: when the query must read a substantial fraction of a large fact table to produce its answer, no index can help because there is no selective predicate, and each iteration is buying 10-20 percent rather than a factor. At that point I am optimizing the wrong layer - the answer is a pre-aggregated model, a columnar store, or moving the workload off OLTP entirely (Q226). I would also stop if the business freshness requirement turns out to be "this morning", because then the whole problem is a scheduled job.

*Hook: a report you took from minutes to seconds, and the point at which you stopped tuning and changed the model.*

---

## 5. Transactions, isolation and MVCC

### Q82. ACID and the mechanism behind each letter

- **Atomicity** - the write-ahead log plus the commit record. Either the commit record is durable and the transaction happened, or recovery undoes it. In PostgreSQL, undo is implicit: uncommitted tuple versions simply never become visible. In InnoDB and Oracle it is an explicit undo log.
- **Consistency** - constraints, triggers and foreign keys. This is the letter the database contributes least to: it means "the transaction moves the database from one valid state to another", and the validity rules are yours.
- **Isolation** - MVCC snapshots plus locking. This is the letter with a dial on it, which is the whole of Q83.
- **Durability** - `fsync` of the WAL before `COMMIT` returns, plus checkpoints and (in a replicated setup) synchronous standbys.

The sentence worth having ready: atomicity and durability are provided by the log, isolation by MVCC and locks, and consistency by you.

### Q83. ANSI isolation levels, and what the standard gets wrong

| Level | Dirty read | Non-repeatable read | Phantom read |
| --- | --- | --- | --- |
| Read Uncommitted | possible | possible | possible |
| Read Committed | no | possible | possible |
| Repeatable Read | no | no | possible |
| Serializable | no | no | no |

What the standard gets wrong:

1. **It defines levels by which of three anomalies they forbid, and those three are not an exhaustive list.** The best-known omission is **write skew** (Q84), which snapshot isolation permits while forbidding all three listed anomalies - so a database can be "Repeatable Read" and still corrupt data. Lost update and read skew are similarly absent.
2. **The definitions are phenomenon-based and were written around lock-based implementations.** MVCC engines satisfy the letter of the definitions by completely different means, so the same level name means different things in different engines (Q87).
3. **Real engines do not implement what they claim.** PostgreSQL's Read Uncommitted behaves as Read Committed; PostgreSQL's Repeatable Read is snapshot isolation; Oracle's "Serializable" is also snapshot isolation and permits write skew.

The correct mental model is Berenson et al's "A Critique of ANSI SQL Isolation Levels": think in terms of snapshot isolation versus true serializability, and know which one your engine gives you under each name.

### Q84. Snapshot isolation and write skew

Under snapshot isolation, every transaction reads from a consistent snapshot taken at its start, and two concurrent transactions conflict only if they **write the same row** (first-updater-wins). Serializability requires the outcome to be equivalent to *some* serial order, which is a stronger claim.

**Write skew** is the gap: two transactions read an overlapping set of rows, each makes a decision based on what it read, and each writes a *different* row. No write-write conflict occurs, so both commit, and the combined result violates an invariant that each transaction individually preserved.

Concrete bug, from a system I would describe as a booking application: the rule is that a meeting room may not be double-booked. Each transaction runs `SELECT count(*) FROM booking WHERE room = 7 AND during && '[10:00,11:00)'`, sees zero, and inserts its own row. Two different rows are inserted, no conflict is detected, and the room is booked twice. The same pattern covers overdraft checks across two accounts, "at least one of X must remain", and inventory reservations.

### Q85. The on-call doctors `[T]`

Both succeed under **Read Committed** and under **snapshot isolation / Repeatable Read** (PostgreSQL RR, Oracle "Serializable", MySQL RR). Each transaction reads a snapshot showing two doctors on call, concludes it is safe to drop itself, and updates a *different* row - no write-write conflict, both commit, nobody is on call.

Three fixes:

1. **True serializable isolation** (PostgreSQL `SERIALIZABLE`, which is SSI). One transaction is aborted with a serialization failure and must be retried; the retry sees one doctor and refuses.
2. **Materialize the conflict / take an explicit lock.** `SELECT ... FROM doctor WHERE shift_id = ? FOR UPDATE` locks all the rows you read, converting the invisible read-write conflict into a real lock conflict. This is the fix that works at any isolation level and is what I usually reach for.
3. **Model the invariant as a single row.** Keep a `shift(on_call_count)` row and update it in the same transaction, or use a constraint the database can enforce - a `CHECK` on a counter column, or an `EXCLUDE` constraint for the overlapping-booking variant (Q12). Then the conflict is a write-write conflict and the engine handles it.

The general principle: write skew happens because the thing you read is not the thing you wrote, so either make the engine track reads (SSI), lock what you read, or write what you read.

### Q86. PostgreSQL Serializable Snapshot Isolation

SSI runs snapshot isolation and additionally tracks read-write **dependencies** between concurrent transactions using predicate locks (SIREAD locks) at tuple, page or relation granularity. Serializability is violated only if there is a cycle in the dependency graph, and every such cycle contains a transaction with a "dangerous structure" - an incoming and an outgoing rw-dependency. When PostgreSQL detects that pattern, it aborts one transaction with `40001 could not serialize access`.

Costs: memory for the predicate locks (which escalate from tuple to page to relation as they grow, increasing false positives), tracking overhead on reads, **false aborts** - it is conservative, so some serializable schedules are rejected - and a throughput ceiling under high conflict. It also requires that read-only transactions participate (`DEFERRABLE` read-only transactions get an optimization), and it does not work across replicas.

What your application must handle: **every** transaction, including read-only ones, can fail with `40001` at commit time, and the only correct response is to retry the whole transaction from the beginning (Q103). That means transaction bodies must be side-effect free apart from database writes - no email sent, no message published mid-transaction.

### Q87. PostgreSQL RR versus MySQL RR `[T]`

Two behaviors that differ:

1. **Write conflicts.** In PostgreSQL Repeatable Read, if your transaction tries to update a row that was updated and committed by a concurrent transaction after your snapshot, you get `ERROR: could not serialize access due to concurrent update` and must retry. In InnoDB Repeatable Read, the update succeeds: reads use the snapshot but writes see the *latest* committed row and lock it. That means InnoDB RR permits **lost updates** in read-modify-write patterns that PostgreSQL rejects.
2. **Phantoms.** InnoDB uses **next-key locking** (gap locks, Q118) for locking reads, which prevents phantoms in a way the standard does not require at RR - so `SELECT ... FOR UPDATE` in InnoDB blocks inserts into the scanned range, while PostgreSQL RR allows the insert and simply does not show it to you.

A third, worth mentioning: PostgreSQL RR takes its snapshot at the **first statement**, not at `BEGIN`, and InnoDB does the same for consistent reads - but Oracle's read-only transactions and MySQL's `START TRANSACTION WITH CONSISTENT SNAPSHOT` differ again.

The takeaway: "we run at Repeatable Read" tells you almost nothing portable, and code that relies on RR semantics does not survive an engine migration.

### Q88. Read Committed and a concurrently updated row

In Read Committed each **statement** takes a fresh snapshot. If an `UPDATE ... WHERE` finds a row that a concurrent uncommitted transaction has modified, it blocks on that row's lock. When the other transaction commits, PostgreSQL does not simply fail - it **re-evaluates the `WHERE` clause against the new version** of the row (an EvalPlanQual re-check). If the row still matches, the update proceeds on the new version; if it no longer matches, the row is silently skipped. If the other transaction rolled back, the update proceeds on the original version.

Two consequences to state. First, an `UPDATE ... WHERE status = 'PENDING'` that blocks and then finds the row is now `'PAID'` updates **nothing** and reports zero rows - the application must check the row count, and most do not. Second, the statement is now working with a mix of snapshot times: the rows it selected came from the statement snapshot, but a re-checked row came from after another commit, which is exactly the inconsistency Q89 exploits.

### Q89. Lost update under Read Committed `[T]`

The pattern is read-modify-write across two statements:

```sql
BEGIN;                                  -- T1                 -- T2
SELECT balance FROM account WHERE id=1; -- reads 100
                                        --                    SELECT balance -> 100
                                        --                    UPDATE ... SET balance = 100 - 30; COMMIT;
UPDATE account SET balance = 100 - 50 WHERE id=1;  -- writes 50
COMMIT;                                 -- T2's withdrawal is gone
```

The `SELECT` read a value from a snapshot; the `UPDATE` wrote a value computed from that stale read. No error is raised because the row lock was only held for the instant of the update. Read Committed permits this by design; **Repeatable Read in PostgreSQL would abort T1** with a serialization error, and InnoDB RR would not (Q87).

The three fixes, in the order I would apply them: (1) do the arithmetic **in the statement** - `UPDATE account SET balance = balance - 50 WHERE id = 1 AND balance >= 50` - which takes the row lock and reads the current value atomically, and lets you check the affected row count; (2) `SELECT ... FOR UPDATE` before the read if you genuinely need application-side logic; (3) an optimistic version column with a retry loop (Q105).

### Q90. MVCC in PostgreSQL

Every tuple carries `xmin` (the transaction that created it) and `xmax` (the transaction that deleted or superseded it), plus infomask bits recording whether those transactions committed. A tuple is visible to a snapshot if `xmin` is committed and within the snapshot, and `xmax` is unset, aborted, or outside the snapshot. The snapshot itself is the set of transaction IDs in progress at the time it was taken.

Therefore `UPDATE` cannot modify in place: it writes a **new tuple version** with a new `xmin` and sets `xmax` on the old one. Readers of older snapshots continue to see the old version. The physical consequences are large: the table grows on update, indexes may need new entries pointing at the new tuple (unless HOT applies, Q130), and dead tuples accumulate until vacuum reclaims them.

The three sentences that answer half of Category 7: **readers never block writers and writers never block readers**, because they read different versions; the cost of that is space and vacuum; and vacuum's ability to reclaim space is bounded by the oldest snapshot still running.

### Q91. PostgreSQL versus Oracle undo versus InnoDB undo

**PostgreSQL** keeps old versions in the table itself. Reads of old versions are cheap (they are right there), but the table bloats and vacuum is mandatory. There is no "snapshot too old" for normal operation, but a long transaction pins the xmin horizon and prevents cleanup, so the failure mode is **unbounded bloat**.

**Oracle** keeps only the current version in the data block and reconstructs old versions from **undo segments**, applying undo records backwards. Reads of old versions cost extra work, undo space is a finite tablespace, and when it is recycled before a long query finishes you get **ORA-01555 snapshot too old**. No bloat, but long queries fail.

**InnoDB** does the same with rollback segments and undo logs; long transactions grow the **history list**, purge falls behind, and secondary index entries accumulate - so it has a bit of both failure modes.

The trade summarised: PostgreSQL chose "readers never fail, but you must vacuum"; Oracle chose "no bloat, but readers can fail". The operational discipline differs accordingly - PostgreSQL DBAs hunt long transactions to protect vacuum, Oracle DBAs size undo to protect long reports.

### Q92. Autovacuum

Autovacuum runs `VACUUM` and `ANALYZE` in the background. `VACUUM` removes dead tuples, marks space reusable in the free space map, updates the **visibility map** (which enables index-only scans, Q46), freezes old tuples to prevent wraparound (Q94), and truncates trailing empty pages.

The thresholds: vacuum triggers when dead tuples exceed `autovacuum_vacuum_threshold + autovacuum_vacuum_scale_factor * reltuples` (default 50 + 20 percent); analyze triggers similarly with `autovacuum_analyze_scale_factor` (10 percent); and an anti-wraparound vacuum is forced when table age exceeds `autovacuum_freeze_max_age`, which cannot be skipped. Work is rate-limited by `autovacuum_vacuum_cost_delay` and `cost_limit`, and parallelism by `autovacuum_max_workers`.

How to tell it is losing: `pg_stat_user_tables.n_dead_tup` growing steadily, `last_autovacuum` old on a busy table, table size growing while row count is flat, vacuum runs appearing in `pg_stat_progress_vacuum` for hours, and eventually `pg_class.relfrozenxid` age climbing toward the wraparound warnings. The default 20 percent scale factor is wrong for large tables - 20 percent of 500 million rows is 100 million dead tuples before it even starts - so I set per-table scale factors near zero with a fixed threshold on big hot tables, and raise `cost_limit` so vacuum is allowed to keep up.

### Q93. Six hours idle in transaction `[T]`

The chain, in order:

1. The session holds an open snapshot, so the **xmin horizon** cannot advance.
2. `VACUUM` may not remove any tuple version that could still be visible to that snapshot, so dead tuples accumulate in every table it touches - **including tables the idle session never read**, because the horizon is global.
3. Tables and indexes bloat. Pages hold fewer live rows, so every query reads more pages and the cache hit ratio falls. Queries across the whole database get slower.
4. The visibility map is not updated, so **index-only scans degrade** into heap fetches.
5. If the session holds any lock - even one taken by a completed statement - every conflicting operation queues behind it, and `ALTER TABLE` behind it blocks all subsequent readers (Q100).
6. Transaction ID age keeps climbing toward wraparound; the anti-wraparound vacuum cannot freeze rows newer than the horizon, so in the extreme you approach a forced shutdown (Q94).
7. On a replica with `hot_standby_feedback = on`, the same effect propagates to the **primary**.

The defenses: `idle_in_transaction_session_timeout` (I set it to seconds, not minutes, on OLTP), monitoring on `max(now() - xact_start)` for active and idle-in-transaction sessions, and never opening a transaction before a network call (`02-spring` Q76).

### Q94. Transaction ID wraparound

Transaction IDs are 32-bit and compared modulo 2^31, so any given transaction can only "see" 2 billion transactions into the past. Tuples must therefore be **frozen** - marked as visible to everyone - before their age reaches that limit, which is what vacuum's freeze phase does.

The escalation: at `autovacuum_freeze_max_age` (default 200 million) an anti-wraparound autovacuum is launched on the table and cannot be cancelled by the usual means; at 40 million remaining PostgreSQL logs warnings on every commit; at 3 million it refuses new write transactions and stops the database to protect the data, requiring a single-user-mode vacuum. Modern versions handle much of this better, and PostgreSQL 14+ made anti-wraparound vacuums far less likely to be blocked, but the failure still occurs in the field.

The emergency procedure: find the oldest tables with `SELECT relname, age(relfrozenxid) FROM pg_class ORDER BY age DESC`, kill whatever is blocking cleanup (long transactions, abandoned replication slots, prepared transactions - all three pin the horizon), raise vacuum's cost limit so it can actually finish, and run `VACUUM (FREEZE)` on the worst tables. The permanent fix is monitoring `age(relfrozenxid)` as a first-class alert, well below the warning threshold.

### Q95. `VACUUM` versus `VACUUM FULL` versus `pg_repack`

- **`VACUUM`** takes a `SHARE UPDATE EXCLUSIVE` lock - concurrent with reads and writes, conflicting only with DDL and other vacuums. It marks dead space reusable *within* the table but does not return it to the OS (except trailing empty pages). This is the routine operation and should be automatic.
- **`VACUUM FULL`** rewrites the entire table into a new file, reclaiming all space and rebuilding indexes, under **`ACCESS EXCLUSIVE`** - no reads, no writes, for the whole duration, and it needs disk space for a second copy. Maintenance windows only.
- **`pg_repack`** achieves the same compaction online: it builds a copy with triggers capturing concurrent changes, then swaps under a brief exclusive lock. It needs double the disk space, a superuser-ish role, and the swap moment can still block briefly, but for a bloated 500 GB table on a 24/7 system it is the practical answer.

The decision: routine vacuum always; `pg_repack` when bloat has already happened on a table you cannot take offline; `VACUUM FULL` only when you have a window and no extension. And the real fix is always upstream - find out why vacuum fell behind (Q92, Q93).

### Q96. Table lock modes and the conflict matrix

Eight modes, weakest to strongest: `ACCESS SHARE`, `ROW SHARE`, `ROW EXCLUSIVE`, `SHARE UPDATE EXCLUSIVE`, `SHARE`, `SHARE ROW EXCLUSIVE`, `EXCLUSIVE`, `ACCESS EXCLUSIVE`.

What everyday statements take:

| Statement | Lock |
| --- | --- |
| `SELECT` | `ACCESS SHARE` |
| `SELECT FOR UPDATE/SHARE` | `ROW SHARE` |
| `INSERT`, `UPDATE`, `DELETE`, `MERGE` | `ROW EXCLUSIVE` |
| `VACUUM` (non-full), `ANALYZE`, `CREATE INDEX CONCURRENTLY` | `SHARE UPDATE EXCLUSIVE` |
| `CREATE INDEX` (non-concurrent) | `SHARE` |
| `ALTER TABLE` (most forms), `DROP TABLE`, `TRUNCATE`, `REINDEX`, `VACUUM FULL`, `CLUSTER`, `REFRESH MATERIALIZED VIEW` (non-concurrent) | **`ACCESS EXCLUSIVE`** |

The rule to memorize: `ACCESS EXCLUSIVE` conflicts with **everything, including plain `SELECT`**, and `ROW EXCLUSIVE` (ordinary DML) conflicts with `SHARE` and above but not with itself. That is why concurrent writers do not block each other at the table level, and why one `ALTER TABLE` stops the world (Q100).

### Q97. Row lock modes

Four strengths, weakest to strongest: `FOR KEY SHARE`, `FOR SHARE`, `FOR NO KEY UPDATE`, `FOR UPDATE`.

- `FOR UPDATE` - the strongest; blocks all other row locks and any update or delete.
- `FOR NO KEY UPDATE` - what a plain `UPDATE` that does not change any unique-key column acquires. It permits concurrent `FOR KEY SHARE`.
- `FOR SHARE` - a read lock; several transactions may hold it, blocks updates.
- `FOR KEY SHARE` - the weakest; only blocks changes to key columns and deletes.

**A foreign key check takes `FOR KEY SHARE` on the parent row.** That matters because it means inserting a child row does *not* block a concurrent non-key update of the parent (since PostgreSQL 9.3), which removed a huge source of contention on reference tables. But it *does* block a delete of the parent and any change to the parent's key, and it does conflict with `SELECT ... FOR UPDATE` on the parent - so application code that pessimistically locks a parent row before inserting children serializes every child insert, which is a common self-inflicted throughput ceiling.

### Q98. Deadlock detection and prevention

Detection: after a lock wait exceeds `deadlock_timeout` (default 1 second), the waiting process runs a check of the wait-for graph; if it finds a cycle, the **transaction that detected it** - that is, the one whose wait triggered the check - is aborted with `40P01`, and the others proceed. It is a timeout-triggered graph search, not continuous detection, which is why the deadlock timeout also acts as a throttle on the cost of checking. InnoDB maintains a wait-for graph continuously and picks the transaction with the least work done as victim.

The two canonical preventions:

1. **Consistent lock ordering.** Always acquire rows in a deterministic order - sort the IDs before updating a batch, always debit the lower account ID first. This eliminates the cycle by construction and is the fix that scales.
2. **Shorten and narrow the transaction.** Fewer rows locked, held for less time, no external calls inside, no user think-time. Deadlock probability rises roughly with the square of transaction duration.

Supporting techniques: `SELECT ... FOR UPDATE` upfront on all rows you will touch (take the locks at the start, in order, rather than escalating late), `NOWAIT`/`lock_timeout` to fail fast, and a retry loop for `40P01` since a deadlock victim's work is always safe to retry.

### Q99. Deadlock despite the same order `[T]`

Several genuine mechanisms:

1. **The statement's own row order is not your order.** `UPDATE t SET ... WHERE id IN (1,2,3)` locks rows in whatever order the *plan* produces - index order, heap order, or parallel worker order - which can differ between two sessions if they use different plans or different predicates. Two batch updates with overlapping sets deadlock even though both "went in ascending order".
2. **Indexes and foreign keys add locks you did not write.** An update touching a unique-key column locks index entries; a child insert takes `FOR KEY SHARE` on a parent (Q97); a cascade delete locks child rows. The cycle is between locks nobody named.
3. **Lock escalation across modes.** Both transactions take a shared lock on the same row and then both try to upgrade to exclusive - a classic upgrade deadlock, which no ordering discipline prevents.
4. **InnoDB gap locks** (Q118) create conflicts on ranges rather than rows, so two inserts of *different* keys can deadlock.

The fixes: `ORDER BY id FOR UPDATE` in an explicit locking `SELECT` before the update (which forces the order), avoiding shared-then-exclusive upgrades by taking `FOR UPDATE` immediately, and reading the `deadlock` log entry, which prints both statements and the locks - it names the answer far faster than reasoning about it.

### Q100. One blocked `ALTER TABLE` blocks everything

`ALTER TABLE` requests `ACCESS EXCLUSIVE`. If a long-running `SELECT` holds `ACCESS SHARE`, the `ALTER` waits. Crucially, PostgreSQL's lock manager is **fair**: a new lock request that conflicts with any *queued* request also waits, rather than jumping ahead. So every subsequent `SELECT` - which would happily have coexisted with the running one - now queues behind the `ALTER`.

The result is a full outage on that table caused by a DDL statement that would have taken a millisecond. Connections pile up, the pool exhausts, and the symptom presented to you is "the application is down", not "a migration is waiting".

The mitigation is a standard part of every migration I write:

```sql
SET lock_timeout = '3s';
ALTER TABLE ... ;   -- retry the whole thing on failure, with backoff
```

so the migration gives up quickly instead of holding the queue open, and you retry until you catch a quiet moment. Complementary measures: kill or wait out long transactions before running DDL, avoid DDL during batch windows, and prefer the lock-free DDL forms (Q244).

### Q101. `NOWAIT`, `SKIP LOCKED`, `lock_timeout`

- **`NOWAIT`** - fail immediately with an error if the row is locked. Use it when the caller has something better to do and a wait is meaningless: an interactive "edit this record" where you want to tell the user instantly that someone else has it.
- **`SKIP LOCKED`** - silently omit locked rows from the result. Use it for work queues, where any unclaimed row will do (Q109). Never use it where you need a complete result set, because it changes the answer.
- **`lock_timeout`** - a session or transaction setting that bounds *any* lock wait. Use it defensively around DDL (Q100) and in any background job that must not become the head of a lock queue. `statement_timeout` is its blunter cousin, bounding the whole statement.

The distinction to make: `NOWAIT` and `SKIP LOCKED` are per-statement semantics chosen by the query author; `lock_timeout` is an operational guardrail applied to code that did not ask for it.

### Q102. Two-phase commit and XA

The protocol: a coordinator asks each resource manager to `PREPARE`; each writes its changes durably and replies "ready", after which it **must** be able to commit; when all are ready the coordinator writes its own commit decision and tells everyone to `COMMIT`. In PostgreSQL this is `PREPARE TRANSACTION` / `COMMIT PREPARED`.

The in-doubt problem: between prepare and the coordinator's decision, a participant holds all its locks and cannot decide by itself. If the coordinator dies, the transaction stays prepared **forever** - locks held, rows unvacuumable, the xmin horizon pinned (Q93) - until a human resolves it. `max_prepared_transactions` defaults to zero in PostgreSQL for exactly this reason.

Why avoid it in a microservice estate: it makes availability the *product* of all participants' availability, it is a blocking protocol so a coordinator failure is an outage rather than a degradation, it holds locks across a network round trip so throughput collapses under contention, and most modern participants (Kafka, DynamoDB, HTTP APIs) do not support it at all. The alternative is the saga plus the transactional outbox plus consumer idempotency (`03-microservices` Q83, Q90) - eventual consistency with compensations, which is weaker but composable and non-blocking.

### Q103. Handling a serialization failure `[T]`

The only correct response is to **retry the entire transaction from the beginning**, with a small randomized backoff and a bounded attempt count. You may not retry a single statement, and you may not "fix up" the result - the transaction's snapshot is dead, and the whole point is that its reads were invalidated.

For the retry to be safe, the transaction body must be **idempotent from the application's point of view**, which in practice means: all its side effects are database writes inside the same transaction; it publishes messages via the outbox rather than directly; it does not send email, call a payment gateway or mutate in-memory state mid-transaction; and it re-reads everything it needs rather than reusing values fetched before the failed attempt.

That is a design constraint on the whole codebase, not an exception handler. The other half of the answer is which codes to catch: `40001` (serialization failure) and `40P01` (deadlock detected) are both retryable by definition. A unique violation is *not* automatically retryable - retrying blindly turns a race into a loop - and needs the idempotency-key treatment instead (Q114).

### Q104. Default isolation level `[A]`

I default to **Read Committed** - the PostgreSQL, Oracle and SQL Server default - because it never fails with a serialization error, so every application path does not need a retry loop, and because the vast majority of operations are single-statement or genuinely independent.

Then I handle the operations that need more, in this order of preference:

1. **Write the invariant into a single statement.** `UPDATE ... SET balance = balance - ? WHERE id = ? AND balance >= ?` and check the row count. No isolation change required, and it is the fastest.
2. **Let the database enforce it.** A unique constraint, `EXCLUDE`, or a `CHECK` on a maintained counter turns the race into a constraint violation (Q12).
3. **Explicit locking.** `SELECT ... FOR UPDATE` on the rows the decision depends on, in a consistent order (Q85, Q98).
4. **Repeatable Read** for multi-statement reads that must be internally consistent - a report, an export, a balance reconciliation - where a retry on a write conflict is acceptable.
5. **Serializable** for the small set of operations with genuine write skew risk where the invariant cannot be expressed as a constraint, accepting that these paths need the retry loop from Q103.

The thing I would not do is set Serializable globally and hope the framework retries: throughput falls, false aborts appear in paths nobody has tested, and the retry logic is exactly the code that has never been exercised.

*Hook: a race condition you fixed by moving the invariant into the database rather than raising the isolation level.*

---

## 6. Application-side concurrency and queueing

### Q105. Optimistic locking with a version column

```sql
UPDATE order SET status = ?, version = version + 1
WHERE  id = ? AND version = ?;
-- 0 rows affected => someone else won
```

The whole mechanism is in the `WHERE` clause plus the affected-row count. No lock is held between read and write, so readers never block; the conflict is detected at write time.

The retry loop must **re-read the current state and re-apply the business decision**, not just re-issue the same update with a new version - otherwise you have implemented last-write-wins with extra steps. It also needs a bounded attempt count, a small randomized delay, and an idempotent body for the same reasons as Q103.

Where the pattern breaks: (1) when conflicts are frequent, retries dominate and throughput collapses - past roughly 10-20 percent conflict rate, pessimistic locking is faster (Q108); (2) when the decision depends on rows *other* than the one you version - that is write skew again, and the version column on one row does not see it; (3) with batch updates, where one conflicting row fails the whole batch; (4) when the "same" logical entity is spread across several rows or tables, so a single version number does not represent it.

### Q106. Timestamp instead of a version counter `[T]`

Two concrete ways it loses updates:

1. **Clock resolution and equality.** If two updates fall in the same clock tick - and `now()` in PostgreSQL is the *transaction* start time, identical for everything in one transaction - the `WHERE updated_at = ?` predicate matches for both, and the second silently overwrites the first with no conflict detected. On systems where the timestamp is truncated to milliseconds, this happens constantly under load.
2. **Clock skew and non-monotonicity.** If the timestamp is generated by the *application* rather than the database, two application servers with 50 ms of skew produce out-of-order timestamps; a "newer" write carries an older timestamp and is either rejected or, in a last-write-wins merge, discarded. NTP corrections can move a clock backwards. This is the same failure `03-microservices` Q69 describes for cross-region conflict resolution.

A third, less obvious: `updated_at` is usually maintained by a trigger for auditing, and someone eventually writes a data-fix script that updates rows without touching it, which breaks the invariant silently.

An integer version counter has none of these properties - it is monotonic by construction and requires no clock. Use the timestamp for humans and the counter for concurrency.

### Q107. Pessimistic locking with `FOR UPDATE`

`SELECT ... FOR UPDATE` takes an exclusive row lock immediately and holds it until the transaction ends. Other transactions attempting to lock or update the same row block (or fail with `NOWAIT`, or skip with `SKIP LOCKED`).

Three disciplines make it safe: lock for the **shortest possible transaction** (never across a user interaction or an HTTP call), acquire locks in a **deterministic order** (Q98), and lock **at the start** rather than upgrading a shared lock later.

The throughput ceiling is arithmetic: if a locked section takes `t` milliseconds and all requests contend on the same row, maximum throughput is `1000/t` per second regardless of hardware. A 20 ms critical section on one hot row caps you at 50 transactions per second, and adding application instances makes the queue longer rather than the system faster. That number - not a preference - is what decides between this and the alternatives (sharded counters, queueing, or restructuring so the contention disappears).

### Q108. Choosing pessimistic over optimistic

The arithmetic: with optimistic locking, expected work per successful transaction is roughly `t / (1 - p)` where `p` is the conflict probability, because a proportion `p` of attempts is wasted and must be redone. Conflict probability rises with the number of concurrent writers to the same row and with transaction duration. Below a few percent conflict, optimistic is clearly better - no locks, no blocking, no deadlocks. Around 10-20 percent, the wasted work and the retry latency start to dominate and pessimistic wins, because a queue is more efficient than a collision.

The other inputs: how expensive the transaction body is (an expensive body makes wasted retries costly, favouring pessimistic), whether the user experience can tolerate "someone else changed this, please review" (favouring optimistic - it is often the *correct* UX for a human editing a record), and whether the work is user-facing (a retry adds latency) or a background job (a retry is free).

My default: optimistic for user-edited entities and low-contention rows, pessimistic for hot rows with short critical sections such as inventory decrements and queue claims, and neither where the operation can be expressed as a single conditional `UPDATE` (Q104).

### Q109. A work queue with `SKIP LOCKED`

```sql
-- claim
WITH claimed AS (
  SELECT id FROM job
  WHERE  state = 'READY' AND run_after <= now()
  ORDER  BY priority DESC, run_after
  FOR UPDATE SKIP LOCKED
  LIMIT  10
)
UPDATE job j
SET    state = 'RUNNING', locked_by = $worker, locked_until = now() + interval '5 minutes',
       attempts = attempts + 1
FROM   claimed c WHERE j.id = c.id
RETURNING j.*;
```

`SKIP LOCKED` is what makes this scale: each worker takes different rows instead of queueing behind the same one, so throughput grows with worker count.

The rest of the design: an index on `(state, run_after)` or a partial index `WHERE state = 'READY'` so the scan is small; `locked_until` as the **visibility timeout**, with a reaper that returns rows whose lease has expired to `READY` (this handles a worker that crashed mid-job); `attempts` with a maximum, moving exhausted jobs to a `FAILED`/dead-letter state instead of looping forever; and `run_after = now() + backoff` on a retryable failure. Completion is a `DELETE` (with an archive if you need history), because leaving completed rows in the table destroys the index over time.

### Q110. When a database queue stops being right `[T]`

It is the right answer far more often than people think: you get transactional enqueue for free (the outbox problem disappears - Q116), exactly the durability and backup story you already have, SQL for inspection and manual intervention during an incident, no new infrastructure to run and secure, and easy correctness because claims are rows.

It stops being right at three specific points:

1. **Throughput.** Every claim is an `UPDATE`, which under MVCC means a new row version plus index churn plus WAL plus vacuum. Somewhere in the low thousands of jobs per second on a normal instance, the queue table's vacuum load starts affecting the rest of the database - and the failure mode is not "the queue is slow", it is "the whole database is slow", which is what makes it dangerous.
2. **Fan-out and retention.** Multiple independent consumer groups, replay of history, or long retention are Kafka's job, not a table's.
3. **Polling cost.** Low-latency work needs frequent polling from many workers, and that polling load exists even when the queue is empty (`LISTEN`/`NOTIFY` mitigates this, Q117).

The specific failure to name: bloat. A high-churn queue table with default autovacuum settings grows until the "get next job" query is scanning tens of thousands of dead tuples, latency climbs, workers poll harder, and it spirals. Aggressive per-table autovacuum settings are mandatory from day one.

### Q111. Advisory locks

Advisory locks are named locks (a 64-bit key, or two 32-bit keys) that the database tracks but attaches no meaning to. Nothing is locked in the data; the application agrees on the convention.

- **Session-scoped** (`pg_advisory_lock`) is held until explicitly released or the session ends. Use it for a long-running singleton process - one migration runner, one leader (Q112) - where the lock must outlive individual transactions. The danger is that a leaked session holds it until the connection dies, and with a pooler you may not get the same session back.
- **Transaction-scoped** (`pg_advisory_xact_lock`) is released automatically at commit or rollback. This is the safe default and the one I use: it cannot leak, and it works correctly through a transaction-pooling proxy.

Against a row lock: an advisory lock needs no row to exist (so you can serialize on a *future* key, such as "creating the account for email X"), it does not bloat the table with a row version, and it can protect a critical section that spans several tables. What it does not give you is any protection against code that ignores the convention - it is cooperative, so it belongs to a small number of well-documented critical sections rather than as a general concurrency mechanism.

### Q112. Leader election and singleton jobs with the database

Two workable patterns. **Advisory lock**: each instance tries `pg_try_advisory_lock(job_key)` at schedule time; exactly one succeeds and runs. Transaction-scoped if the job is short, session-scoped with a heartbeat if it is long. **Lease row**: a `lock` table with `(name, holder, expires_at)`, claimed with a conditional `UPDATE ... WHERE expires_at < now()` and renewed by a heartbeat - which is exactly what ShedLock does.

Compared with the alternatives:

| | Database lock | ShedLock | ZooKeeper/etcd |
| --- | --- | --- | --- |
| New infrastructure | none | none | a cluster to run |
| Failure detection | lease expiry (seconds) | lease expiry | session/ephemeral node (sub-second) |
| Fencing token | you must add it | no | yes, the zxid/revision |
| Correctness under GC pause | weak - the old leader may still be running | weak | still needs fencing at the resource |

The honest caveat for all of them: a lease tells you the *previous* holder's lease expired, not that it stopped working. If the job has external side effects, a paused leader can wake up and act after another leader has started. Where that matters, the resource itself must reject stale writers using a fencing token; where it does not - most idempotent batch jobs - ShedLock or an advisory lock is completely adequate and vastly cheaper than a coordination cluster.

### Q113. High-contention counters

| Approach | Throughput | Correctness |
| --- | --- | --- |
| `SELECT ... FOR UPDATE` then update | worst - two round trips inside the lock | exact |
| `UPDATE t SET n = n + 1` | better - lock held for the statement only | exact |
| Sharded counter: N rows, random shard, `SUM` to read | N times better | exact, reads cost a sum |
| Approximate: sample, or HyperLogLog in Redis | unbounded | approximate |

The mechanism behind the ceiling is that all writers serialize on one row's lock, and each update also writes a new tuple version, so the row's page becomes a bloat hotspot as well as a lock hotspot.

The sharded counter is the standard fix: insert into or update one of N rows chosen at random (`shard_id = hash(random()) % 64`), and read with `SELECT sum(n)`. Writes scale roughly linearly with N; reads cost an aggregate over N rows, which is trivial. A variant that suits high-write, low-read cases better is **append-only**: insert a row per event and roll up periodically into a summary row, which turns lock contention into pure appends at the cost of a maintenance job.

I would also ask whether the counter needs to be transactional at all. View counts, likes and rate limiters usually belong in Redis (Q188); order totals and account balances belong in the database with exact semantics.

### Q114. Idempotency keys at the storage layer

The table:

```sql
CREATE TABLE idempotency (
  key           text PRIMARY KEY,
  request_hash  text NOT NULL,
  state         text NOT NULL,           -- IN_PROGRESS | DONE
  response      jsonb,
  created_at    timestamptz NOT NULL DEFAULT now()
);
```

The flow: in the same transaction as the business write, `INSERT` the key. The **primary key is the concurrency control** - the unique index makes exactly one inserter win. On success, store the response and mark `DONE`. Return the stored response on any later request with the same key.

The in-flight retry is the interesting case. A second request arriving while the first is uncommitted **blocks** on the unique index entry until the first transaction ends - which is correct but ties up a connection. My preferred behavior is a short `lock_timeout` and then a `409 Conflict` with `Retry-After`, telling the client the original is still processing; the alternative, waiting, risks a thundering herd of blocked connections when a slow request is retried by an impatient client.

Two more details that matter: store a **hash of the request body** and reject a reused key with different content (`422`), because a client bug reusing keys is worse than no idempotency; and give the table a TTL with a partitioned or time-indexed cleanup, since it grows at the rate of your total request volume.

### Q115. `ON CONFLICT DO NOTHING` returns zero rows `[T]`

Three possible states of the world:

1. **A committed row with that key already exists.** The normal case.
2. **A concurrent, still-uncommitted transaction inserted that key.** `DO NOTHING` does *not* block - it skips - so you get zero rows while no visible row exists. If that transaction later rolls back, the key is free and you have neither inserted nor found anything.
3. **The conflict was on a different constraint** than the one you expected, if you omitted the conflict target - `DO NOTHING` without a target swallows *any* unique or exclusion violation, so a genuine data error looks identical to a duplicate.

Distinguishing them: follow the insert with a `SELECT` for the key in the same transaction. A row found means case 1. No row found means case 2 (or your snapshot predates the commit under Repeatable Read). Always specify the conflict target so case 3 cannot hide.

The robust pattern when you need the row back is `ON CONFLICT (key) DO UPDATE SET key = EXCLUDED.key RETURNING *` - a deliberate no-op update that takes the row lock, waits for the concurrent transaction, and always returns the row. The cost is a dead tuple per call, so use it where correctness matters more than churn.

### Q116. The outbox at SQL level

```sql
CREATE TABLE outbox (
  id            bigserial PRIMARY KEY,
  aggregate_id  text NOT NULL,
  type          text NOT NULL,
  payload       jsonb NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now(),
  published_at  timestamptz
);
CREATE INDEX ON outbox (id) WHERE published_at IS NULL;
```

The business write and the outbox insert are in **one transaction**, so the event exists if and only if the state change did. The relay claims with `SELECT ... ORDER BY id FOR UPDATE SKIP LOCKED LIMIT n`, publishes, then marks or deletes.

Ordering guarantees, stated precisely: you get **per-aggregate ordering only if** the relay is single-threaded per aggregate (or partitions its claims by `aggregate_id` hash) *and* the broker preserves order for the key you publish with. You do **not** get global ordering, because `bigserial` values are assigned at insert time but become visible at commit time, so a transaction that took the id 100 can commit after the one holding 101 - a relay reading by id can therefore skip a row that appears later. The fixes are to read with a lag window (only rows older than a few seconds), or to use a monotonic commit-order source such as logical decoding (Q92 in `03-microservices` terms: CDC-based outbox).

Cleanup matters as much as the design: delete published rows promptly, or partition by day and drop partitions, because this table is high-churn and will bloat exactly like a queue (Q110).

### Q117. `LISTEN`/`NOTIFY`

`NOTIFY channel, 'payload'` queues a notification that is delivered **at commit** to every session currently `LISTEN`ing on that channel, over their existing connection. Duplicate identical notifications within one transaction are collapsed.

The semantics: **at-most-once, to currently connected listeners only**. A listener that is down, restarting or reconnecting misses everything sent in the meantime; there is no persistence, no replay, no acknowledgement, no consumer group. The payload is limited to 8000 bytes, and the whole notification queue is a fixed-size (8 GB) shared area that, if a listener stalls, fills and eventually **blocks committing transactions** - a genuinely nasty failure mode. Notifications also do not cross replication to a standby, and a transaction-pooling proxy such as PgBouncer breaks `LISTEN` entirely.

So it is not a queue. What it is excellent at is **eliminating polling latency** on top of a real queue table: workers `LISTEN` for a wake-up signal and, on receipt, run the `SKIP LOCKED` claim query, while still polling on a slow timer as a backstop. That gives millisecond latency with durable semantics, and the missed-notification case costs you only the polling interval.

### Q118. Gap locks and next-key locks

InnoDB at Repeatable Read locks not just matched rows but the **gaps between index entries**. A *record lock* covers an index entry; a *gap lock* covers the open interval between two entries; a *next-key lock* is the union of a record and the gap before it. This is how InnoDB prevents phantoms at RR - it locks the range, so a concurrent insert into that range blocks.

A deadlock this causes and PostgreSQL does not have:

```
-- table has rows with id 10 and 20
T1: SELECT * FROM t WHERE id = 15 FOR UPDATE;  -- gap lock on (10,20)
T2: SELECT * FROM t WHERE id = 17 FOR UPDATE;  -- gap lock on (10,20) - compatible, both granted
T1: INSERT INTO t VALUES (15);                 -- waits for T2's gap lock
T2: INSERT INTO t VALUES (17);                 -- waits for T1's gap lock -> deadlock
```

Two transactions inserting **different** keys deadlock, because gap locks are shared for reading but block insertion. This is a classic InnoDB surprise in "check then insert" code and in upsert-heavy workloads. PostgreSQL has no gap locks: it detects phantoms only at Serializable, via SSI predicate locks, and would allow both inserts here.

The mitigations in InnoDB: use `READ COMMITTED` (which mostly disables gap locking) if your application does not rely on RR phantom protection, or replace check-then-insert with a real `INSERT ... ON DUPLICATE KEY UPDATE`.

### Q119. Insert-then-update in opposite order `[T]`

```
T1: INSERT parent A          T2: INSERT parent B
T1: UPDATE parent B          T2: UPDATE parent A     -> deadlock
```

Each transaction holds a lock on the row it created (an uncommitted row is locked by its creator) and then waits for the other's. It is the classic cycle, made less obvious because one of the locks was taken by an `INSERT` rather than an explicit lock statement. The same shape appears with foreign key checks: inserting a child takes `FOR KEY SHARE` on the parent (Q97), so two transactions inserting children of each other's parents deadlock without either writing a shared row.

The fix that does not touch isolation: impose a **deterministic ordering on the keys** and process them in that order within a transaction - sort the batch by primary key before writing, and where the entities are of different types, fix a global type order (always `account` before `ledger`, never the reverse). For the batch case specifically, `SELECT ... WHERE id = ANY(?) ORDER BY id FOR UPDATE` at the start of the transaction acquires everything in a canonical order before any work begins.

The complementary measures are shortening the transaction so the window is small, and a retry on `40P01` - a deadlock victim is always safe to retry (Q103).

### Q120. Long batch jobs against an OLTP table

The three problems are related, so the technique addresses all of them at once: **batch, commit, throttle**.

- **Blocking**: never take locks on a large set at once. Process in key-range chunks of a few thousand rows, each in its own transaction, with `lock_timeout` set so a chunk that meets contention gives up and retries rather than heading a lock queue (Q100).
- **Bloat**: each chunk's dead tuples must be reclaimable, which requires the transaction to *end*. One 40-million-row `UPDATE` produces 40 million dead tuples that vacuum cannot touch until it commits, and a table that doubles in size. Committing per chunk lets autovacuum interleave; on very large jobs I trigger `VACUUM` explicitly between chunks.
- **Replication lag**: every chunk generates WAL, and a standby applying WAL single-threaded will fall behind. The job should **measure lag** (`pg_stat_replication.replay_lag` or the LSN difference) between chunks and sleep until it recovers - a simple feedback loop that makes the job self-throttling and prevents the batch from breaking read-replica reads (Q143).

Additional discipline: make the job **restartable** by driving it from a persisted cursor rather than an offset, make each chunk idempotent, and run it with a lower `statement_timeout` and a dedicated database role so you can identify and kill it instantly. Schedule by lag and load, not by clock alone.

### Q121. A transaction across a user's wizard `[A]`

Why it does not work: a database transaction holds locks and a snapshot for its whole life, so a wizard open for ten minutes means ten minutes of held row locks, ten minutes of blocked writers, and ten minutes during which vacuum cannot advance the xmin horizon **for the entire database** (Q93). Multiply by concurrent users and you exhaust `max_connections`, because every open transaction pins a connection - which is also incompatible with any connection pool, and impossible with transaction-mode PgBouncer. Then the user closes the laptop and nothing commits until a timeout fires. Finally, a load balancer, a rolling deployment or a failover kills the connection and the half-finished work vanishes with no way to recover it.

The design that works, in order of preference:

1. **Persist the draft.** The wizard writes each step to a `draft` row or table (or a JSONB document) with its own lifecycle, committed each step. The final "submit" is one short transaction that validates and promotes the draft into the real tables. The user can resume tomorrow, on another device, and you can report on abandonment.
2. **Optimistic concurrency on submit.** The draft records the version of anything it depends on; the promoting transaction re-validates and returns a friendly conflict if the world moved (Q105).
3. **A reservation, if the business needs one.** If the point of the long transaction was really "hold this seat/stock for the user", model it explicitly as a reservation row with an expiry and a background reaper. That is a business concept with a business rule, and it survives restarts, which a lock does not.

The framing I would use with the team: they are asking for a *business* lock with a *technical* mechanism that was never designed to be held across human time. Make the lock a row, and everything else becomes easy.

*Hook: a long-held transaction you found in production and what replacing it did to lock waits.*

---

## 7. Storage internals and durability

### Q122. Page and tuple structure

A PostgreSQL heap page is 8 KB (compile-time constant) and has four parts: a 24-byte **page header** (checksum, LSN of the last change, free-space pointers), an array of **item pointers** (line pointers) growing from the front, **free space** in the middle, and the **tuples** themselves growing from the back. Item pointers give a stable address (page, offset) so a tuple can move within a page during compaction without invalidating index entries - and they are what a HOT chain repoints.

A tuple header is 23 bytes plus alignment: `t_xmin`, `t_xmax` (MVCC, Q90), `t_cid`/`t_ctid` (the command id, and the pointer to the next version - the basis of HOT chains), `t_infomask` bits caching whether xmin/xmax committed so visibility checks avoid consulting the commit log, and the null bitmap.

Two consequences worth stating: a row can never exceed a page, which is why wide values must be TOASTed (Q129); and column order affects size because of alignment padding - putting eight-byte columns first and one-byte columns last can shrink a wide row measurably.

### Q123. Shared buffers and the OS page cache

`shared_buffers` is an array of 8 KB frames with a hash table mapping (relation, fork, block) to a frame. A backend looking for a page hashes it, and on a miss reads from the OS, evicting a victim chosen by a **clock sweep** with usage counts - a cheap approximation of LRU that also resists sequential scans flooding the cache (large sequential scans use a small ring buffer rather than evicting everything). Dirty pages are written by the background writer and the checkpointer, not usually by the backend that dirtied them.

PostgreSQL deliberately relies on the OS page cache as a second tier: it uses buffered IO rather than direct IO, so a page missing from `shared_buffers` is often still in RAM, and a "read" in `EXPLAIN (BUFFERS)` may be a memory copy rather than a disk IO. The design choice keeps PostgreSQL portable and lets the OS manage a large cache, at the cost of double-buffering the same page in both caches.

### Q124. Sizing `shared_buffers`

Because of the double-buffering above, giving PostgreSQL nearly all of RAM is counterproductive: pages are cached twice, the clock sweep and checkpoint work grow with the buffer count, and the OS loses the memory it needs for the file cache, temp files, sorts (`work_mem`) and connection overhead. The conventional starting point is **25 percent of RAM** for `shared_buffers`, and `effective_cache_size` set to 60-75 percent to tell the planner how much is *probably* cached in total (it allocates nothing). Larger values can help on very large machines with a working set that fits, but it needs measuring, not assuming.

Oracle is the opposite because it uses **direct IO** and manages its own SGA buffer cache, bypassing the OS cache entirely - so there is no double-buffering and giving it the memory is exactly right. SQL Server behaves similarly.

The other reason not to over-allocate in PostgreSQL: a bigger buffer pool means more dirty pages at each checkpoint, which makes the checkpoint IO spike worse (Q128).

### Q125. Write-ahead logging

The protocol is: before any data page change reaches disk, the log record describing it must be durable. Each page carries the **LSN** of the last WAL record that modified it, and the checkpointer will not write a page until the WAL up to its LSN is flushed.

At `COMMIT`, the backend writes a commit record and waits for the WAL to be `fsync`ed up to that LSN (and, with synchronous replication, for the standby to confirm it - Q140). Only then does the client get its acknowledgement. The data pages themselves are still dirty in memory; recovery replays the WAL forward from the last checkpoint to reconstruct them.

So what is durable when the client is acknowledged is **the log record, in the WAL files**, not the table. That is the whole design: sequential, small writes at commit time; random, batched writes later. It is also why WAL storage latency, not table storage latency, determines commit throughput, and why putting WAL on faster storage is one of the highest-leverage hardware changes.

### Q126. `synchronous_commit`, `fsync`, `full_page_writes`

- **`synchronous_commit = off`** - the commit record is written to the WAL buffer but the backend does not wait for the `fsync`. You lose up to `wal_writer_delay` x 3 (a few hundred milliseconds) of **committed transactions** on a crash, but the database stays **consistent** - it is a bounded data-loss window, not corruption. This is a legitimate, per-transaction setting for low-value high-volume writes (telemetry, click events), and it is a large throughput win.
- **`fsync = off`** - PostgreSQL never forces anything to stable storage. A crash can leave the database **corrupt and unrecoverable**, because pages and WAL can be reordered arbitrarily. Never acceptable in production; defensible for a throwaway CI database that is rebuilt from scratch.
- **`full_page_writes = off`** - PostgreSQL stops writing a full image of each page the first time it is modified after a checkpoint. Those images exist to survive **torn pages** (a partial 8 KB write when the storage's atomic unit is 4 KB or 512 bytes). Turning it off is safe only on storage that guarantees atomic 8 KB writes - some SANs, ZFS with matching record size, Aurora's log-structured storage - and corrupts on ordinary hardware.

The ranking: `synchronous_commit = off` is a considered trade; `full_page_writes = off` requires a storage guarantee in writing; `fsync = off` is never a production option.

### Q127. Committed, then gone after power loss `[T]`

Layer by layer, any of these breaks the chain:

1. **`synchronous_commit = off`** or `commit_delay` in PostgreSQL - the acknowledgement came before the flush (Q126). Configuration, not a bug.
2. **The filesystem lied.** `fsync` returned success while data sat in a write buffer; some filesystems and older kernels also *lost the error* on a failed writeback and returned success to the next `fsync` (the "fsyncgate" issue), so a failed write was never retried.
3. **A volatile disk cache.** The drive acknowledged the write from its own DRAM cache with no power-loss protection, or a RAID controller had a write-back cache with a dead battery. Consumer SSDs are the classic case.
4. **A virtualization or network storage layer** that buffers, or an NFS mount with the wrong options.
5. **Replication assumptions**: the primary crashed permanently and you failed over to an **asynchronous** standby that had not received the commit. The write was durable - just not on the machine you now use (Q140).
6. **The application never committed** - autocommit off and a connection reset, or a pooler returning a connection that rolled back.

How I would investigate: check `synchronous_commit` first, then the storage stack's cache settings (`hdparm`, controller battery state, cloud volume type), then whether a failover happened at that moment. And the preventive answer: test it. A power-cut test with a write-verifying tool, or at minimum a documented storage configuration, is the only way anyone actually knows.

### Q128. Checkpoints

A checkpoint flushes all dirty shared buffers to disk and writes a checkpoint record, so that recovery need only replay WAL from that point. It is triggered by `checkpoint_timeout` (default 5 minutes), by WAL volume reaching `max_wal_size`, or explicitly by `CHECKPOINT`, a base backup or a shutdown.

A checkpoint spike looks like: a periodic burst of write IO and IO wait, a latency spike in write transactions every N minutes, a corresponding spike in WAL volume (because the first write to each page after a checkpoint carries a **full page image**, Q126), and in `pg_stat_bgwriter` a high `checkpoints_req` relative to `checkpoints_timed`.

Smoothing it: raise `max_wal_size` so checkpoints are time-driven rather than volume-driven (`checkpoints_req` should be near zero), raise `checkpoint_timeout` to 15-30 minutes to spread the work and reduce full-page-image volume, and keep `checkpoint_completion_target` at 0.9 so the flush is spread across most of the interval. The trade is recovery time: fewer checkpoints means more WAL to replay after a crash, so the setting is really a dial between steady-state latency and RTO.

### Q129. TOAST

A tuple cannot span a page, so when a row exceeds roughly 2 KB (`TOAST_TUPLE_THRESHOLD`), PostgreSQL compresses and/or moves the largest variable-length values out to a side table, leaving an 18-byte pointer in the row. The side table is chunked into ~2 KB pieces with its own index.

The four strategies, set per column:

- `PLAIN` - no compression or out-of-line storage (fixed-width types only).
- `EXTENDED` - compress, then move out of line if still too big. The default for `text`, `jsonb`, `bytea`.
- `EXTERNAL` - move out of line without compressing. Faster substring and streaming access on large values, at the cost of space.
- `MAIN` - compress but avoid moving out of line if at all possible.

The performance surprise: a large `text` or `jsonb` column is *cheap* to ignore - `SELECT id, status` never touches the TOAST table - but expensive to touch, because reading it means an index lookup plus several chunk reads plus decompression. So `SELECT *` on a table with a big document column is dramatically more expensive than selecting the columns you need, and an `UPDATE` that does not modify the TOASTed column does not rewrite it (the pointer is copied), which is why updating a small flag on a document row is cheaper than people expect.

### Q130. HOT updates and `fillfactor`

A **Heap-Only Tuple** update places the new row version on the **same page** as the old one and links them with a `t_ctid` chain, updating no index at all - existing index entries continue to point at the original line pointer, which now redirects to the newest version. Index maintenance disappears, and the space from dead versions in the chain can be reclaimed by page pruning without a full vacuum.

Two conditions must both hold: **no indexed column is modified**, and **the new version fits on the same page**.

`fillfactor` (default 100 for heaps) controls how full a page is packed on insert. Setting it to 80-90 on a frequently updated table reserves space so later versions fit, which is precisely what keeps HOT working.

The failure mode this explains: adding an index on a column that is updated on every write - a `last_seen_at`, a `status` that churns, a counter - takes the table from mostly-HOT to zero-HOT. Suddenly every update writes to all indexes, WAL volume multiplies, indexes bloat, and autovacuum cannot keep up. It is a genuinely non-obvious way that one index harms a table globally (Q61).

### Q131. Table bloat versus index bloat

**Table bloat** is dead tuples plus unusable free space in heap pages: created by updates and deletes under MVCC, reclaimed *for reuse* by vacuum but not returned to the OS. **Index bloat** is dead entries and half-empty pages from splits: B-trees do not merge underfull pages, so an index never shrinks on its own.

Why disk usage does not fall after a `DELETE`: the rows become dead tuples, vacuum marks their space reusable in the free space map, and PostgreSQL then reuses it for future inserts. The file only shrinks if the free space is at the *end* of the relation, which vacuum can truncate. Deleting 90 percent of a table scattered throughout leaves the file the same size.

Measure with `pgstattuple` (exact, but it scans) or the standard estimate queries (cheap, approximate), and watch the ratio of table size to `n_live_tup * avg_width`. Fix the heap with `pg_repack` or `VACUUM FULL` (Q95), the index with `REINDEX CONCURRENTLY` (Q57) - and then fix the cause, which is nearly always autovacuum being too slow for the table's churn or a long transaction pinning the horizon.

### Q132. B-tree versus LSM

| | B-tree | LSM tree |
| --- | --- | --- |
| Write path | in-place (or new version) page write, random IO | append to memtable, flush sorted runs, sequential IO |
| Write amplification | ~1 page per change plus WAL, but random | high over time - each level rewrites data during compaction (often 10-30x) |
| Read amplification | ~tree depth, one path | must check memtable plus several SSTables per level; bloom filters cut this |
| Space amplification | bloat from splits, typically 1.2-1.5x | obsolete versions until compacted; leveled ~1.1x, tiered can be 2x+ |
| Range scans | excellent, leaves are linked | good, but merges across runs |
| Latency profile | predictable | good median, **compaction causes p99 spikes** |

LSM (RocksDB, Cassandra, HBase, ScyllaDB) wins on ingest-heavy workloads because it turns random writes into sequential ones and defers the reorganization. B-trees win on read-heavy and update-in-place workloads and give more predictable latency.

### Q133. "LSM is faster for writes" `[T]`

It is false in three situations. First, an **update-heavy workload on a small dataset that fits in cache**: a B-tree updates a cached page and writes one WAL record, while the LSM writes the record, then rewrites it repeatedly through every compaction level - total bytes written to disk are far higher. Second, a **read-modify-write workload**, because the LSM must first do a (more expensive) read, and many LSM engines then need a read-before-write for correctness. Third, **sustained** write throughput near the disk's limit: the LSM's advertised speed is the memtable append, but compaction runs in the background consuming the same IO budget, so steady-state throughput is bounded by write amplification, not by the append rate.

What compaction does to p99: it competes for disk bandwidth and CPU (compression), evicts the page cache with data nobody asked for, and in the worst case triggers **write stalls** when the memtable cannot flush because L0 has too many files - at which point writes block entirely for hundreds of milliseconds. This is the Cassandra and RocksDB operational reality: the median is excellent, the tail is where you spend your time, and tuning is mostly about compaction strategy (leveled versus size-tiered versus time-window) and giving compaction enough headroom.

### Q134. Row store versus column store

A row store keeps a whole tuple contiguously, so reading one row is one page read and writing one row is one page write. A column store keeps each column's values together in large blocks, so reading three columns of a billion-row table touches only those columns.

Compression is the multiplier: a column of values of the same type with low cardinality compresses 5-20x with dictionary and run-length encoding, versus perhaps 2-3x for mixed-type rows. Less data read means less IO, and vectorized execution over a packed array is far more CPU-efficient per row.

What each destroys: a column store is terrible at `SELECT *` for one row (it must assemble the row from N column blocks), at single-row `INSERT`/`UPDATE`/`DELETE` (blocks are large and often immutable, so updates become delete-markers plus rewrite), and at point lookups without a suitable index. A row store is terrible at scanning two columns of a 200-column table, because it reads all 200.

Hence the split: OLTP on row stores, analytics on column stores, and hybrid engines (Aurora, SQL Server columnstore indexes, Oracle In-Memory) that keep both representations of the same data.

### Q135. Compression

**Page-level** compression (InnoDB page compression, ZFS) compresses whole pages transparently; it is simple but must decompress a whole page to read a row, and the compressed page still occupies a fixed slot. **Column-level** compression in a columnar format compresses runs of a single type, achieving much better ratios. **Dictionary encoding** replaces repeated values with small integer codes, which is what makes low-cardinality string columns nearly free and, crucially, lets some engines evaluate predicates **directly on the encoded values** without decompressing.

What it buys beyond disk: fewer bytes read means fewer IOs and better effective cache capacity - a 5x compression ratio means 5x more data fits in the buffer pool, which is usually a larger win than the disk saving. On network-attached or object storage, it also cuts transfer time and cost directly.

What it costs: CPU on read and write (mitigated by fast codecs such as LZ4 and Zstandard, which are chosen precisely because decompression is faster than the IO saved), higher latency on point lookups, and in some engines a loss of in-place update. The rule of thumb: use LZ4 or Zstd level 1 for hot data where CPU matters, higher Zstd levels for cold and archival data.

### Q136. Durability on cloud storage, and Aurora

Ordinary cloud databases run the same WAL protocol over a network block device (EBS): every `fsync` is a network round trip, so commit latency is bounded by storage latency and the WAL device's throughput.

Aurora changes the contract: the database instance **does not write data pages at all**. It ships only WAL records to a purpose-built distributed storage layer of six replicas across three availability zones, and a write is durable when **four of six** acknowledge (a write quorum with `W=4, R=3, N=6`, so it survives an entire AZ plus one more node). The storage nodes apply the log to materialize pages in the background, on demand.

That removes the two biggest write amplifiers: no checkpoint page flushes across the network, and **no full-page writes**, because the storage layer's page materialization is atomic by construction rather than depending on 8 KB atomic sector writes (Q126). Aurora claims roughly an order-of-magnitude reduction in bytes written compared with mirrored PostgreSQL.

What it does not fix: single-writer architecture (one primary for writes, unless you use multi-master with its own conflict rules), commit latency still crossing AZs, per-IO pricing that can dominate the bill on write-heavy workloads, and none of your query-level problems.

### Q137. Network-attached storage with 1 ms round trip `[T]`

The operations that become the bottleneck are the **synchronous, serial** ones - anything where the database must wait for storage before continuing:

1. **WAL `fsync` at commit.** Every commit costs at least one round trip, so a single-threaded writer is capped near 1,000 commits per second regardless of CPU. This is the dominant effect.
2. **Random single-page reads** on a buffer-pool miss - an index scan fetching 10,000 scattered heap pages now costs 10 seconds of pure latency, because they are issued one at a time.
3. **Checkpoint bursts** and any operation that must flush many pages.

What you tune: enable **`commit_delay`/group commit** so concurrent commits share one flush, which converts N round trips into one and is the single biggest win; raise `effective_io_concurrency` so bitmap heap scans issue prefetches in parallel; raise `random_page_cost` relative to `seq_page_cost` to tell the planner that random access really is expensive here; increase `shared_buffers` and `effective_cache_size` so more reads never reach storage; batch application writes so fewer transactions each commit more work; and, where the workload allows, `synchronous_commit = off` for the low-value paths (Q126). If the platform allows it, putting WAL on a lower-latency volume than the data files is the structural fix.

### Q138. Temp files and spilling

Operations that spill: sorts (`ORDER BY`, merge joins, `CREATE INDEX`), hash joins and hash aggregates when the hash table exceeds `work_mem`, materialized CTEs and `Materialize` nodes, large bitmap scans (which degrade to lossy first, Q52), and window functions with big frames.

Detection: `log_temp_files = 0` logs every temp file with its size; `pg_stat_database.temp_files` and `temp_bytes` give the running totals; and in `EXPLAIN (ANALYZE)` look for `Sort Method: external merge Disk: NNNkB`, `Batches: 8` on a hash join (more than 1 means spilling), or `Disk: NNNkB` on a hash aggregate.

The two ways to stop it: **give the operation more memory** - `SET LOCAL work_mem` for that transaction, sized to the observed spill plus headroom, rather than globally (Q76); or **make the operation smaller** - an index that provides the required order so no sort is needed at all, a more selective predicate, aggregation pushed down before the join, or partitioning so only one partition is processed. The index route is strictly better when available, because it removes the work rather than funding it.

*Hook: a spill you found with `log_temp_files` and what removing it did to p99.*

---

## 8. Replication, high availability and recovery

### Q139. Physical versus logical replication

**Physical (streaming)** replication ships the WAL byte stream and the standby replays it at the block level. It replicates **everything** - all databases, all tables, DDL, indexes, even physical layout - and produces a byte-identical copy. It cannot replicate a subset, cannot write to the standby, and requires the **same major version and same architecture** on both ends.

**Logical** replication decodes the WAL into row-level change events (insert/update/delete with column values) and applies them as SQL on the subscriber. It replicates **selected tables** in selected databases, allows the subscriber to have extra tables, extra indexes and its own writes, and works **across major versions** - which is what makes it the standard tool for near-zero-downtime upgrades and for feeding CDC pipelines.

Logical's limitations are the interview payload: **DDL is not replicated** (you must apply schema changes on both sides in the right order), the publisher needs `wal_level = logical` and a **replication slot** per subscription (Q148), tables need a replica identity - a primary key, or `REPLICA IDENTITY FULL` which is expensive - sequences are not replicated, and initial synchronization copies data table by table.

### Q140. Async, sync and quorum commit

| Mode | Commit waits for | RPO | Latency cost |
| --- | --- | --- | --- |
| `off` / async | local WAL flush only | seconds of transactions (whatever is unshipped) | none |
| `remote_write` | standby has received and written to OS | zero unless the standby OS crashes too | one network round trip |
| `on` (default sync) | standby has **flushed** to disk | zero for a primary-only failure | round trip plus standby fsync |
| `remote_apply` | standby has **applied** and made visible | zero, and reads on that standby are current | round trip plus fsync plus replay |
| quorum (`ANY k (...)`) | any k of the listed standbys | zero while k survive | round trip to the k-th fastest |

The point to make: synchronous replication protects **durability**, not availability, and the latency is added to *every* commit, so a cross-region synchronous standby means every write pays the inter-region RTT - typically 20-80 ms, which is a throughput collapse for chatty workloads. Quorum (`ANY 1 (s1, s2, s3)`) is the practical compromise: you wait for the fastest of several standbys, so one slow node does not stall commits, and you still have a durable copy elsewhere. `remote_apply` is the only mode that gives read-your-writes on the standby, and it is the slowest.

### Q141. The only synchronous standby dies `[T]`

The primary **stops committing**. Every commit waits indefinitely for an acknowledgement that will never come; sessions hang in `SyncRep` wait state, connections accumulate, and the application sees writes hanging rather than failing. Reads continue to work, which makes the diagnosis confusing. The transactions are already durable locally and *will* be visible after a restart, but the client never gets an acknowledgement.

What it teaches: **synchronous replication with a single standby converts a durability guarantee into an availability liability.** You have chosen RPO=0 and paid for it with a system whose write availability is the *product* of two machines' availability - worse than the primary alone.

The correct configurations: at least **two** synchronous candidates with quorum (`synchronous_standby_names = 'ANY 1 (s1, s2)'`), so any one can fail without stalling; monitoring that alerts on a missing sync standby immediately; and an explicit, documented **operational decision** about whether to degrade to async during an outage (`ALTER SYSTEM SET synchronous_standby_names = ''; SELECT pg_reload_conf();`). That decision is a business one - it trades RPO for availability - and it must be made before the incident, not during it.

### Q142. Measuring replication lag

Three measurements, and they answer different questions:

1. **Byte lag** - `pg_current_wal_lsn() - replay_lsn` from `pg_stat_replication` on the primary. It tells you how much WAL is outstanding, which matters for slot growth and failover data loss, but it says nothing about time.
2. **Time lag** - `write_lag`, `flush_lag`, `replay_lag` in `pg_stat_replication`, or on the standby `now() - pg_last_xact_replay_timestamp()`. This is what a user experiences.
3. **Application-level lag** - a heartbeat row written on the primary every second and read on the standby; the difference is end-to-end staleness including any pooler or router.

Causes: standby CPU or IO too slow to keep up (recovery replay is largely **single-threaded**, so a primary with 16 concurrent writers can outpace one replay process); a long-running query on the standby conflicting with replay and, with `max_standby_streaming_delay`, deliberately pausing it; network bandwidth; and a bulk operation generating WAL faster than it can be shipped (Q120).

Why zero byte lag can still mean stale reads: `pg_last_xact_replay_timestamp()` only advances when there are transactions to replay, so an **idle** primary shows growing "time lag" that is meaningless; and conversely, a standby that has *received* and *flushed* all WAL may not have *applied* it - `write_lag` zero, `replay_lag` not. Always compare `replay_lsn`, not `flush_lsn`, for read staleness.

### Q143. Updates their profile, sees the old value `[T]`

The mechanism: the write went to the primary, the subsequent read was routed to a replica, and the replica had not yet applied that transaction. This is a **read-your-writes** violation, and it is the single most common bug introduced by adding read replicas.

Four fixes, cheapest first:

1. **Route reads to the primary within a short window after a write** - a "sticky primary" flag in the session or a cookie for N seconds. Trivial to implement, imprecise, and it puts some read load back on the primary. This is what most systems actually do.
2. **LSN-based routing.** Capture `pg_current_wal_insert_lsn()` after the write, pass it with the request (a token in the session or the response), and have the router either wait for `pg_last_wal_replay_lsn() >= token` on a replica or fall back to the primary. Precise, correct, and it needs plumbing through the application.
3. **`synchronous_commit = remote_apply`** for the writes that need it, so the commit does not return until the designated standby has applied it. Correct and simple, but it adds the round trip plus replay to every such write and only covers the synchronous standby (Q140).
4. **Do not read after write at all** - return the written state from the write response, and treat the subsequent read as a refresh. Often the best answer, because the correct value is already in hand.

The general framing: read replicas break read-your-writes by construction, so the fix belongs in the routing layer as an explicit policy, not in individual features discovering it one by one.

### Q144. Session guarantees with replicas

- **Read-your-writes**: the LSN token or sticky-primary approach from Q143. The invariant is "never read from a replica whose `replay_lsn` is behind the LSN of my last write".
- **Monotonic reads** (never see time go backwards): pin a session to **one** replica for its lifetime - consistent hashing on session id in the router - because the violation comes from bouncing between replicas at different lag. Alternatively carry the last-read LSN forward as a floor for the next read, which is the same token mechanism.
- **Consistent prefix** (never see effects before causes): comes free from physical replication, since WAL is applied in commit order. It is *not* free with logical replication across multiple publications or with per-table CDC pipelines, where two tables can arrive out of order - which is why a CDC-fed read model needs a single ordered stream per aggregate or a transaction-aware consumer.

The implementation point: all three are properties of the **routing layer**, and it needs a place to store per-session state (LSN token, pinned replica) plus a staleness bound after which it falls back to the primary. Building that once, centrally, is far cheaper than every service rediscovering the problem.

### Q145. Routing reads to replicas

The decision belongs in **one place**, and I prefer it explicit at the call site rather than magic: an annotation or a routing hint that says "this read tolerates staleness of up to N seconds", resolved by a routing component (a `DataSource` router, PgBouncer/pgpool, or a proxy such as RDS Proxy). Making it implicit - "all `readOnly = true` goes to a replica" - is how the Q143 bug ships, because `readOnly` was written to mean "no writes", not "stale data is acceptable".

Staleness handling: the router checks the replica's replay lag against the request's bound and falls back to the primary if it is exceeded, and it removes a replica from rotation entirely above a hard threshold. Publishing the lag as a metric with an alert is part of the deal.

What breaks inside a transaction: a transaction must be pinned to a single node, so the decision is made **at transaction start** and cannot change mid-way; a transaction that begins read-only and then writes must fail or restart (Spring's `readOnly` hint is applied at the boundary for exactly this reason - `02-spring` Q64); and a read-write transaction that happens to contain only reads still occupies the primary. Also, replicas cannot take row locks, so `SELECT ... FOR UPDATE` and advisory locks must go to the primary, and temp tables and sequences do not exist on a standby.

### Q146. Failover

**Manual** failover means a human decides; it is slower (minutes) but it never fires spuriously. **Automatic** failover means a coordinator with a consensus store decides; it is faster (seconds to tens of seconds) but a false positive - a network blip, a long GC pause, a saturated primary - promotes a standby unnecessarily, and every unnecessary promotion is an incident of its own.

Patroni is the standard PostgreSQL implementation: each node runs an agent that holds a **leader key with a TTL** in etcd/Consul/ZooKeeper. The leader renews it; if it fails to renew, the key expires, the remaining agents run an election, the best-positioned standby (most WAL received) is promoted, and the others are reconfigured to follow it. RDS/Aurora multi-AZ does the equivalent inside the managed service, moving a DNS name or an endpoint to the new writer.

**Fencing (STONITH)** exists because the old primary may still be alive and reachable by *some* clients - a partitioned network, a paused VM that resumes. Without fencing you get two primaries accepting writes (Q147). Fencing forcibly removes the old primary from service: power it off, revoke its storage lease, drop its network route, or - the software equivalent Patroni uses - have the demoted node's own agent shut PostgreSQL down when it loses the leader key, plus a `watchdog` device that reboots the node if the agent itself hangs. The other half is that **clients must be fenced too**, which is why the endpoint must move rather than clients keeping a list of hosts.

### Q147. Split brain `[T]`

Sequence: the network partitions between the primary and the coordinator. The coordinator cannot see the primary, declares it dead, and promotes a standby. Meanwhile the old primary is perfectly healthy on its side of the partition and continues accepting writes from any application instance that can still reach it - a second application zone, a stale DNS cache, a client holding an established TCP connection. Now two nodes have diverged: both have accepted different transactions at the same WAL positions.

Recovery is genuinely painful because there is no automatic merge. The steps: stop writes to both immediately; decide which timeline is authoritative (normally the promoted one, because clients have already read from it); take a backup of both before touching anything; use `pg_waldump` and application-level queries to **extract the transactions that exist only on the losing node**; rebuild the loser as a standby of the winner - `pg_rewind` if the WAL is available, otherwise a full base backup; and then reconcile the extracted transactions by hand or by replaying them through the application, which is a business exercise, not a database one.

Prevention is the whole answer: quorum-based coordination (an odd number of coordinator nodes so a minority partition cannot elect), fencing/STONITH so the old primary is actively stopped, a single endpoint that clients cannot bypass, and - if the data is critical - synchronous replication, which prevents the *silent* acceptance of writes that will be lost.

### Q148. Replication slots

A slot is a named, persistent record on the primary of how far a consumer has consumed. Its purpose is to guarantee that the primary **retains the WAL** a standby or logical subscriber still needs, and (with `hot_standby_feedback`) that it does not vacuum away row versions the consumer might still need. Without a slot, a standby that disconnects for longer than `wal_keep_size` allows can no longer catch up and must be rebuilt.

The danger is the same property: a slot that stops being consumed - a decommissioned replica nobody dropped, a paused Debezium connector, a broken subscription - causes the primary to retain WAL **forever**. `pg_wal` grows until the disk fills, and a full WAL disk takes the primary down hard. Logical slots additionally hold back the xmin horizon, so vacuum stalls and bloat accumulates database-wide (Q93).

Operational rules: monitor `pg_replication_slots` for `active = false` and for `pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)` above a threshold - this is a mandatory alert, not a nice-to-have; set `max_slot_wal_keep_size` (PostgreSQL 13+) so the primary invalidates a runaway slot rather than dying; and make dropping the slot part of the runbook for decommissioning any replica or connector.

### Q149. Cascading replication and delayed replicas

**Cascading** lets a standby serve WAL to further standbys instead of every replica streaming from the primary. It reduces network fan-out and CPU on the primary, which matters with many replicas or across regions - one cross-region link feeding a local tree. The cost is added lag for the downstream tier and a more complex failover topology.

A **delayed replica** (`recovery_min_apply_delay = '1h'`) receives WAL immediately but deliberately applies it an hour late. It is genuinely useful because it protects against the failure class that backups protect against *slowly* and replicas do not protect against at all: **logical corruption**. A `DELETE` without a `WHERE`, a bad migration, an application bug writing garbage - all replicate to a normal standby in milliseconds. With a delayed replica you have a window in which the pre-damage state is live and queryable, so you can extract the correct rows in minutes instead of restoring a multi-terabyte backup and replaying WAL for hours.

It is a complement to, not a replacement for, PITR: its window is fixed and short, it can be spoiled by an operator who lets it catch up, and it does not survive a storage failure. But as an RTO reduction for the most common human error, an hour-delayed replica is cheap insurance.

### Q150. Logical decoding and CDC

Logical decoding reads the WAL, reassembles it into transactions, and passes each change to an **output plugin** (`pgoutput` for native logical replication, `wal2json` or `decoderbufs` for Debezium) which formats it. A **publication** on the publisher names the tables and operations to expose; a **subscription** on the subscriber creates a slot and an apply worker. Changes are delivered **in commit order**, only for committed transactions (in PostgreSQL 14+ optionally streamed while in progress), and each change carries the new tuple plus, depending on `REPLICA IDENTITY`, the old key or the full old row.

For CDC, the important properties are: commit-ordered so causality is preserved; at-least-once on restart, because the consumer's confirmed LSN is the checkpoint and anything after it is re-sent - so consumers must be idempotent; and an initial **snapshot** phase that reads the current table contents before switching to streaming.

The DDL limitation is the one to name: **DDL is not decoded**. Adding a column on the publisher does not create it on the subscriber, and the apply worker will error or silently ignore data depending on the direction of the mismatch. So schema changes need an explicit ordering discipline - additive changes on the subscriber first, on the publisher second; drops in the reverse order - which is the expand-contract pattern applied to replication (Q247).

### Q151. Backups

**`pg_dump`** is a logical backup: it produces SQL or an archive of the *contents* from a single consistent snapshot. It is portable across versions and architectures, restores selectively, and produces a compact file. But it is a **full** dump every time, it takes as long as reading the whole database, restoring means re-executing every insert and rebuilding every index (which on a terabyte can be many hours), and it gives no point-in-time capability - only the instant of the dump.

**A physical base backup** (`pg_basebackup`, pgBackRest, Barman, or a storage snapshot) copies the data files plus the WAL generated during the copy. Combined with **continuous WAL archiving** it supports PITR to any second (Q152), supports **incremental/differential** backups (pgBackRest block-level, PostgreSQL 17 native incremental), restores by copying files rather than replaying SQL, and can be taken from a standby.

Why `pg_dump` is not a strategy at scale: the RTO is measured in hours-to-days for a large database, the RPO is the dump interval (typically 24 hours), and it takes a long-running transaction on the source, which pins the xmin horizon and bloats the database while it runs (Q93). It remains excellent for per-table exports, cross-version migration and small databases - just not as the disaster recovery plan.

### Q152. Point-in-time recovery

Three ingredients: a **base backup** (a physical copy plus the WAL to make it consistent), a **continuous WAL archive** (every completed WAL segment shipped to durable storage via `archive_command` or `pg_receivewal`), and a **recovery target** - `recovery_target_time`, `_lsn`, `_xid` or `_name` - set at restore time. Recovery restores the base backup, then replays archived WAL forward until the target, then stops and promotes.

The RTO arithmetic is what people miss:

```
RTO = fetch base backup from object storage
    + restore/decompress it to local disk
    + fetch and replay WAL from the backup to the target
    + verification and application cutover
```

Replay is largely **single-threaded**, so it proceeds at maybe 50-200 MB/s of WAL; a system producing 100 GB of WAL a day and a base backup taken weekly means up to 700 GB to replay - hours, before the restore itself. That is why base backup **frequency** is the main RTO lever, and why "we have PITR" without a measured restore is a claim, not a capability.

The RPO, separately, is the archive lag: with `archive_command` you can lose the current, unarchived segment (up to 16 MB of WAL), so `archive_timeout` or streaming with `pg_receivewal --synchronous` closes that gap.

### Q153. Backups succeed but you cannot restore `[T]`

Five realistic reasons:

1. **Nobody has ever tested a restore.** The backup job reports success on writing a file; nothing verifies the file is a valid, complete, restorable backup. This is by far the most common.
2. **The WAL archive is incomplete.** The base backup is fine but `archive_command` has been failing silently (or the retention policy expired the WAL needed to make the base backup consistent), so the backup cannot even reach a consistent state, let alone your target time.
3. **The restore does not fit.** No machine with enough disk, no capacity in the account, or a restore time far beyond the RTO nobody measured - technically restorable, operationally useless.
4. **Encryption or credentials.** The backups are encrypted with a KMS key in the account that was lost, the key was rotated and old versions deleted, or the credentials to read the bucket live in the system that is down.
5. **Something outside the database is missing** - the roles and grants (not included in `pg_dump` of a single database), tablespaces, extensions of the right version, large objects, the exact PostgreSQL minor version, or `postgresql.conf`. The data restores and the application still cannot start.

Honourable mentions: backups stored in the same account/region that the disaster destroyed; a logical backup that has silently been dumping only one schema since a refactor; and ransomware encrypting the backup share because it was mounted writable.

The only answer that counts is a **scheduled restore drill** into a scratch environment, automated, with the RTO recorded and a smoke test that the application starts and a known row exists.

### Q154. RPO and RTO

**RPO** (recovery point objective) is how much *data* you can afford to lose, measured in time: it is determined by your replication and archiving, not by your restore process. **RTO** (recovery time objective) is how long you can be *down*: it is determined by detection, decision, and the restore/failover mechanics.

How the architecture changes:

| Target | RPO 24h | RPO 5 min | RPO ~0 |
| --- | --- | --- | --- |
| Mechanism | nightly backup | continuous WAL archiving with frequent segment closure | synchronous replication (Q140) |
| Cost | trivial | modest - archive storage and monitoring | every commit pays a network round trip |
| Failure mode | lose a day's work | lose the unarchived segment | write availability tied to two nodes |

And on the RTO side: hours means "restore from backup"; 15 minutes means "a warm standby, automated promotion, and a single endpoint clients follow"; under a minute means "automated failover with health checks tuned aggressively and clients that reconnect", accepting occasional false promotions. Below that you are talking about multi-writer or active-active, and the cost curve turns vertical (Q155).

The essential point: these are **business** numbers. My job is to price each level and make the business choose, and then to prove the chosen level with a drill rather than a diagram.

### Q155. Multi-region

**Active-passive**: writes in one region, asynchronous replication to a standby region, failover promotes it. RPO is the cross-region lag (seconds), RTO is the promotion plus DNS/endpoint propagation. This covers regional disaster and is what most systems should do.

**Active-active**: both regions accept writes. This is where relational databases struggle, and the reason is fundamental rather than a missing feature: a relational system's guarantees - unique constraints, foreign keys, `SELECT ... FOR UPDATE`, serializable transactions - all require **coordination among all writers**. Coordinating synchronously across regions means every write pays 50-150 ms of speed-of-light latency, which destroys OLTP throughput. Coordinating asynchronously means two regions can allocate the same invoice number, both sell the last item, or update the same row concurrently - and then you need conflict resolution, which the relational model has no answer for (last-write-wins loses data, Q106 and `03-microservices` Q69).

The practical designs: **partition writes by region** so each row has a home region and no two regions write the same data (Spanner-style geo-partitioning, or simply routing customers to their region); accept **eventual consistency with CRDTs or application-level merge** for the data that can tolerate it; or use a distributed SQL engine that pays the coordination cost explicitly and honestly (Q167). What I would refuse is asynchronous multi-master on a conventional engine with "we'll resolve conflicts later", because "later" means a data-quality incident with no clean resolution.

### Q156. HA and DR for 15-minute RTO, near-zero RPO `[A]`

**Clarify first**: is 15 minutes the RTO for a *regional* disaster or for an instance failure? Near-zero RPO means how many seconds, and for which data - all of it, or the financial subset? What is the acceptable write-latency increase? Those answers move the cost by an order of magnitude.

The design I would propose for a single-region-primary system:

- **Within the region**: a synchronous standby in a second AZ with quorum commit (`ANY 1 (az2a, az2b)`) so a single standby failure cannot stall writes (Q141). This gives RPO=0 for an instance or AZ failure and, with automated promotion (Patroni or the managed equivalent), an RTO of well under a minute. Cost: one round trip per commit within the region, typically 1-2 ms.
- **Cross-region**: an **asynchronous** standby in a second region, plus continuous WAL archiving to object storage in that region. RPO here is the replication lag - seconds - and RTO is a promotion plus endpoint change. Synchronous cross-region is what I would *not* do, and I would say why: it makes every commit pay the inter-region RTT and makes the far region a liability for write availability.
- **Logical corruption**: a delayed replica at one hour (Q149) plus PITR from the archive, because neither replication nor failover protects against a bad `DELETE`.
- **Client side**: a single endpoint (DNS with a low TTL, or a proxy) that clients follow, connection retry with backoff in every service, and idempotent writes so a retry after failover does not double-charge.
- **Proof**: an automated monthly game day - kill the primary, measure the actual RTO; and a quarterly regional failover test and restore drill with the numbers published.

**What it costs**: roughly double the compute (standbys are idle capacity you pay for), cross-region data transfer on every WAL byte, object storage for the archive, and 1-2 ms added to every write within the region. The honest caveat I would give the business: the 15-minute RTO is achievable technically, and the thing that will actually make you miss it is **detection and decision time**, not the database - so the investment must include the alerting, the runbook and the authority to fail over without a meeting.

*Hook: a failover you ran for real, and the difference between the measured RTO and the one in the document.*

---

## 9. Partitioning, sharding and distributed SQL

### Q157. Partitioning, sharding, replication

- **Replication** copies the *same* data to more nodes. It solves read scaling, availability and disaster recovery. It does **not** solve write throughput or data volume - every node still holds everything and applies every write.
- **Partitioning** splits one table into pieces **within one database**. It solves manageability - vacuum, index size, retention by dropping a partition, and query pruning. It does **not** solve write throughput, because it is still one server.
- **Sharding** splits the data across **independent databases**. It is the only one of the three that scales writes and total dataset size. It costs you cross-shard queries, cross-shard transactions, global uniqueness and operational complexity.

The sequence I would apply: replication first (cheap, solves the common case), then partitioning (contained, no application change if the key is already in the queries), then sharding last (expensive, invasive, irreversible in practice).

### Q158. Range, list and hash partitioning

- **Range** - by a continuous value, almost always time: `PARTITION BY RANGE (created_at)` with one partition per month. Suits time-series, event and audit tables where queries filter by a period and retention is "drop anything older than N months". This is the majority of real use.
- **List** - by an enumerable discriminator: region, tenant tier, country. Suits a workload where queries always filter by that value and where you want to manage partitions differently (different tablespaces, different retention, per-tenant vacuum settings).
- **Hash** - by a hash of the key into N equal partitions. It does not help pruning for range queries, and it gives no retention story. Its purpose is **spreading contention and size evenly** when there is no natural range - a very hot table where you want the index and vacuum work split, or a preparatory step toward sharding by the same key.

The default question I ask is "what will you drop, and what do queries filter by". If those answers are the same column, range partitioning by that column is almost certainly right; if the answer is "nothing, and everything", partitioning may be the wrong tool.

### Q159. Partition pruning

**Plan-time pruning** happens when the planner can evaluate the partition key predicate against the boundaries using constants - `WHERE created_at >= '2026-01-01'` - and it simply excludes those partitions from the plan. **Execution-time pruning** (PostgreSQL 11+, `enable_partition_pruning`) handles parameters and values only known at runtime: a generic prepared plan, a value from a subquery, or the inner side of a nested loop, shown in the plan as `Subplans Removed: N`.

Query shapes that defeat pruning entirely:

- **No predicate on the partition key at all** - the most common. If you partition by `created_at` and every query filters by `customer_id`, you have all the maintenance cost and none of the benefit.
- **The key wrapped in a function** or a non-immutable expression: `WHERE date_trunc('month', created_at) = ?`.
- **A type or collation mismatch** forcing a cast on the column side.
- **`OR` across the partition key and something else**, which can force scanning everything.
- **A join on the partition key without a constant** - partition-wise join helps only if `enable_partitionwise_join` is on and the partitioning schemes match exactly.

The operational tell is a plan listing every partition, and a query time that grows as you add partitions instead of staying flat.

### Q160. Monthly partitions made it slower `[T]`

Three realistic causes:

1. **Queries do not filter on the partition key**, so every query now scans all partitions and the planner must lock, plan and open each one. With 60 monthly partitions, planning time alone can exceed the old execution time, and `max_locks_per_transaction` becomes a real constraint.
2. **Too many partitions for the access pattern.** Each partition has its own indexes, so an index that was one B-tree of depth 4 is now 60 B-trees of depth 3 - and a query touching all of them does 60 index descents plus 60 sets of buffer lookups instead of one. Append/MergeAppend across many children also costs more than a single scan.
3. **Lost global ordering or global uniqueness.** A `ORDER BY created_at LIMIT 10` that used to be an index scan stopping after 10 rows may now need a MergeAppend across partitions; and any unique constraint not containing the partition key had to be dropped, so the query that relied on it now does something worse (Q161).

There is a fourth in the field: partitioning was added *and* the statistics were never regathered, so the planner has no per-partition statistics and estimates badly. Always `ANALYZE` after partitioning.

### Q161. Partition key in the primary key

A unique index in PostgreSQL is per-partition, not global, so the engine can only guarantee uniqueness across the whole table if **every partition can decide locally** - which requires the **partition key to be part of every unique constraint and primary key**.

The consequences for the model are real. If you partition `orders` by `created_at`, the primary key must become `(id, created_at)`. That is fine internally but it changes every foreign key referencing orders to a composite, changes your ORM mapping, and means an `id` alone is no longer a guaranteed unique lookup - a query by `id` without the date must scan all partitions, so external references need to carry the date (or you keep a small global lookup table mapping `id` to partition key, which is another thing to maintain).

The mitigations: choose a partition key that is already part of the natural identity (tenant id, account id) so the composite is honest; embed the partition key **inside** the identifier (a ULID whose timestamp prefix is the partition key, or `tenant:id`), so callers always carry it; or accept the scan for the rare by-id path. This constraint is the main reason partitioning is not transparent, and being able to state it precisely is the point of the question.

### Q162. Detach, attach, drop

`DROP TABLE partition_2024_01` removes a month of data in **milliseconds** as a catalog operation plus a file unlink - no row-by-row deletion, no dead tuples, no vacuum, no WAL proportional to the data, no bloat. Compare that with `DELETE FROM events WHERE created_at < ...` on 200 million rows: hours of work, an enormous WAL burst, replication lag, 200 million dead tuples, and a table that does not shrink (Q131).

`DETACH PARTITION` removes it from the parent while keeping the table, which is how you archive: detach, then `COPY` it to object storage or move it to cheaper storage, then drop. `DETACH ... CONCURRENTLY` (PostgreSQL 14+) avoids the `ACCESS EXCLUSIVE` lock on the parent that a plain detach requires.

`ATTACH PARTITION` adds a pre-loaded table as a partition, which is how you bulk-load: create a standalone table, load and index it at full speed with no contention on the live table, add a `CHECK` constraint matching the partition bounds so the attach can skip its validation scan, then attach - a fast metadata operation.

The operational requirement this creates: **partition maintenance must be automated** (pg_partman or a scheduled job) to create future partitions ahead of time and drop expired ones. A partitioned table with no future partition and no default silently rejects inserts, which is a memorable 2 a.m. incident.

### Q163. Choosing a shard key

The four properties, and the failure from getting each wrong:

1. **High cardinality** - enough distinct values to spread across all shards and to keep spreading as you grow. Get it wrong (sharding by country, status, or a boolean) and you cannot use more shards than you have values.
2. **Even distribution** - the values must be roughly uniform in *volume*, not just in count. Get it wrong and one shard holds 30 percent of the data (Q164).
3. **Query alignment** - the key must appear in the overwhelming majority of queries, so they can be routed to one shard. Get it wrong and every query is a scatter-gather across all shards, which is slower than the unsharded system and fails when any shard is slow.
4. **Transaction alignment** - data that changes together should live together. Get it wrong and ordinary business operations need cross-shard transactions, which means sagas or 2PC (Q102, Q166).

A fifth, practical one: **stability**. The key must never change for a row, because changing it means moving the row between shards.

In practice `tenant_id` or `customer_id` satisfies all of them for most B2B and consumer systems, which is why it is the usual answer - and why it fails exactly when one tenant is enormous.

### Q164. One customer is 30 percent of volume `[T]`

Ranked options:

1. **Give them a dedicated shard.** Route that customer's key to a shard of their own (a routing exception in the lookup table, which is why a **directory-based** router beats pure hashing). Cheap, immediate, and it does not change the model. This is what I would do first, and it is the pattern that later becomes "dedicated infrastructure for enterprise tenants".
2. **Add a second dimension to the key for that tenant** - shard by `(tenant_id, sub_key)` where the sub-key is order id, region or a hash bucket, so the whale is spread over several shards while everyone else stays on one. Correct and scalable; the cost is that queries for that tenant become scatter-gather, so it works only if their queries are naturally scoped by the sub-key too.
3. **Split by entity rather than tenant** for the biggest tables - shard `orders` by `order_id` while keeping `customer` by tenant. Solves volume, but breaks tenant-scoped queries and transactions.
4. **Vertical split**: move that tenant's heaviest feature (event history, documents) to a different store entirely.
5. **Rebalance more finely** - many more virtual shards than physical nodes, so the whale's shards can be spread across nodes (Q165). Helps with node-level load but not with a single logical shard being too big.

The point to make: the moment you have one whale you will have three, so the answer must be a *mechanism* (a routing directory with per-tenant placement) rather than a one-off fix.

### Q165. Resharding a live system

The mechanism that makes it tractable is **consistent hashing with virtual nodes**: hash keys onto a ring, place many virtual nodes per physical node, and moving one physical node moves only its virtual nodes' key ranges - roughly `1/N` of the data instead of rehashing everything. Equivalent in practice: define far more logical shards than physical nodes (say 1024) and map logical to physical in a directory, so rebalancing is a mapping change plus a data move.

The migration itself:

1. **Dual-write** the affected key ranges to both old and new placement, or enable CDC from old to new, while all reads still go to the old.
2. **Backfill** the historical data for those ranges, in batches with throttling (Q249).
3. **Verify**: row counts, checksums per key range, and a shadow-read comparison where a sample of reads is executed against both and diffed - with a metric for mismatches. Do not skip this; it is the only thing that catches an application path that writes to only one side.
4. **Cut over reads** per key range, not globally, so blast radius is a fraction of the traffic and rollback is a routing change.
5. **Stop dual writes**, then decommission after a retention period long enough to roll back.

The properties that make it safe are that every step is reversible, the unit of change is a key range rather than the whole system, and verification runs before and during the cutover, not after.

### Q166. Cross-shard queries, joins and transactions

What you give up: a **join** across shards has to be executed by the application or a coordinator - fetch from both sides and join in memory, which is unbounded work and no optimizer help. A **query without the shard key** becomes scatter-gather: it is sent to all shards, so its latency is the *slowest* shard's latency, its failure probability is `1-(1-p)^N`, and it consumes capacity everywhere. **Aggregates and sorting** need a merge step, and `LIMIT` becomes "fetch `LIMIT` from each shard, then re-sort". **Transactions** across shards need 2PC (Q102) or a saga; **global uniqueness** and cross-shard foreign keys no longer exist.

The patterns that keep you out of that territory:

- **Choose the key so it is in every hot query** (Q163), and treat any query without it as a design smell requiring review.
- **Replicate small reference tables to every shard**, so joins to them stay local.
- **Denormalize deliberately** - carry the few columns from the other aggregate that queries need, accepting the staleness.
- **Serve cross-cutting queries from a different store**: a search index or an analytics warehouse fed by CDC handles "find all orders matching X across all tenants" far better than a scatter-gather (Q216).
- **Bound the fan-out**: allow scatter-gather only for admin and background paths, with a timeout and partial-results semantics, never on a user-facing hot path.

### Q167. Distributed SQL and TrueTime

These systems provide serializable (or externally consistent) transactions across nodes by combining three things: **data sharded into ranges**, each range **replicated by Raft** so a write is committed by a majority of its replicas, and a **distributed transaction protocol** (two-phase commit across the ranges involved, coordinated through the same Raft groups so the coordinator itself is fault-tolerant - which removes the classic blocking-coordinator problem from Q102).

The remaining problem is ordering transactions globally without a single clock. **Spanner's TrueTime** is an API that returns an *interval* `[earliest, latest]` guaranteed to contain the true time, backed by GPS receivers and atomic clocks in every data centre, with an uncertainty bound of a few milliseconds. Spanner assigns each transaction a commit timestamp and then **waits out the uncertainty** ("commit wait") before making it visible, which guarantees that if T1 commits before T2 begins in real time, T1's timestamp is smaller. That is external consistency (linearizability) for the whole database - and it costs a few milliseconds of added commit latency, which is Google buying a hardware guarantee to avoid a coordination round trip.

**CockroachDB** has no atomic clocks, so it uses HLC timestamps with a configured `max_offset` (default 500 ms) and, instead of waiting, **restarts** transactions that read a value inside their uncertainty window. **YugabyteDB** offers both a hybrid-clock mode and a clock-bound mode. The trade is stated cleanly: Spanner pays latency on every commit for a hardware-backed bound; CockroachDB pays occasional retries and a weaker guarantee by default.

### Q168. Aurora's architecture

Compute and storage are separated. The database instance keeps the buffer pool and the query engine but **writes only WAL records** to a distributed storage service, which holds six copies of each 10 GB segment across three AZs. Writes are acknowledged on a **quorum of four of six**, reads need three of six, and the storage nodes materialize pages from the log independently and continuously. Replicas attach to the *same* storage rather than replaying a WAL stream, so replica lag is typically tens of milliseconds and adding a replica copies no data.

Why failover is fast: a replica already shares the storage, so promotion does not require replaying WAL or copying anything - it is largely a matter of the new writer establishing its position and invalidating cached pages, typically under 30 seconds (faster with the cluster endpoint and RDS Proxy holding client connections).

What it does not fix: it is still **one writer** for the cluster, so write throughput is bounded by a single instance; it does not change the SQL engine's behavior, so all your query, index, lock and vacuum problems are identical; its IO pricing means a write-heavy or badly indexed workload can be dramatically more expensive than provisioned storage; the maximum volume is finite (128 TB); and cross-region is still asynchronous (Aurora Global Database, ~1 s RPO). The honest summary: Aurora fixes storage durability, replica lag and failover time, and fixes nothing above the storage layer.

### Q169. Vitess and Citus

**Vitess** sits in front of MySQL: `vtgate` is a proxy speaking the MySQL protocol that parses queries, consults a **VSchema** describing how each table is sharded, and routes or scatters accordingly; `vttablet` manages each MySQL instance. It adds transparent sharding, online resharding with automatic cutover, connection pooling, query rewriting and guardrails against dangerous queries. It is what runs YouTube and Slack.

**Citus** is a PostgreSQL extension: a coordinator holds the metadata and distributes tables by a hash of the distribution column across worker nodes, pushing down whole queries where possible, running parallel fragments and merging results otherwise. It also supports **reference tables** replicated to every node (which is how you keep joins local) and columnar storage for analytics.

What leaks through in both: queries **without the distribution key** become scatter-gather with all the properties of Q166; **cross-shard transactions** are supported but expensive (Citus uses 2PC, Vitess offers weaker modes by default); **DDL** must be applied everywhere and some forms are restricted; **unique constraints and foreign keys** must include the distribution column or be restricted to reference tables; sequences and `AUTO_INCREMENT` need special handling; and the optimizer's estimates across shards are weaker than a single node's. They remove most of the routing work and none of the modeling work - the shard key decision (Q163) is still yours and still the thing that determines success.

### Q170. "Just add a read replica" for a write-bound system `[T]`

Every replica applies **every write** that the primary does. Adding a replica therefore adds zero write capacity and actively subtracts from it:

- The primary must **stream WAL** to one more consumer - network and CPU on the primary.
- If replicas use slots with `hot_standby_feedback = on`, they **hold back the primary's xmin horizon**, so vacuum falls further behind exactly when write volume is high, which increases bloat and makes writes slower still (Q93, Q148).
- Recovery replay on a standby is largely single-threaded, so a write-bound primary produces WAL faster than the replica can apply it: lag grows, and any read routed there returns stale data, generating support tickets that look like new bugs (Q143).
- Operationally you now have more nodes to patch, monitor, fail over and pay for.

So the intervention makes the symptom worse and adds a second symptom. The correct responses to a write-bound system are: reduce write volume (batching, eliminating redundant updates, removing unnecessary indexes so each write costs less - Q56), make writes cheaper (HOT updates, fillfactor, fewer indexes, `synchronous_commit` for low-value writes), move a write-heavy workload to a store designed for it (events to Kafka, counters to Redis), scale up the primary, or shard (Q172).

The diagnostic that settles the argument: look at whether the primary is saturated on WAL/IO/CPU during writes, and what proportion of time is spent on read queries. If reads are 20 percent of the load, no amount of read scaling matters.

### Q171. Scaling reads, in order

1. **Fix the queries and indexes first.** The cheapest read capacity is the work you stop doing. A single missing index or an N+1 loop routinely accounts for the majority of read load, and no amount of infrastructure fixes it.
2. **Cache** the hot, repeated, tolerably stale reads (Q173). Highest leverage per rupee, and it removes load rather than distributing it - but it adds an invalidation problem.
3. **Read replicas** for read volume that must be fresh-ish and diverse (not cacheable because every query differs). Adds staleness and routing complexity (Q145).
4. **Materialized views / summary tables** for expensive aggregates that many readers share. Converts repeated expensive computation into a scheduled one.
5. **Denormalized read models** (CQRS) fed by CDC or the outbox, when the read shape is fundamentally different from the write shape - a search index, a document per screen. The most powerful and the most expensive to operate, because it introduces a sync pipeline and drift.

The decision order is deliberately cheapest-and-most-reversible first. The question I ask at each step is "what fraction of the read load does this remove, and what does it cost me in staleness?" - and I make the staleness explicit, because every layer after step 1 introduces some.

### Q172. When to shard PostgreSQL `[A]`

**When**: I shard when one or more of these is true and cannot be resolved otherwise - the write throughput exceeds what the largest single instance can sustain; the dataset has grown to where routine operations (vacuum, index builds, backup, restore) no longer fit in any window, which usually bites well before query performance does; the RTO is unachievable because restoring the volume takes too long; or one tenant's load must be isolated from another's for contractual reasons. Note that "the table is big" is not on that list.

**What I would do for the two years before that point**, roughly in order:

1. Query and index hygiene, and killing N+1 (the largest single lever, every time).
2. Connection pooling done properly - PgBouncer in transaction mode with a sane pool size (Q235, Q240).
3. Caching for the read hot path, and read replicas for the rest (Q171).
4. **Partitioning** the two or three tables that dominate volume, by time or tenant, so vacuum, retention and index size become manageable (Q158). This buys the most time per unit of effort and is fully reversible.
5. Moving non-relational workloads out: events to Kafka or a time-series store, blobs to object storage, counters and sessions to Redis, search to a search engine. Databases usually grow because they are being used as five things at once.
6. Vertical scaling - which is unfashionable but buys years; modern instances go to hundreds of cores and terabytes of RAM.
7. **Functional partitioning** - splitting a bounded context onto its own database - before hash sharding, because it follows an existing boundary and needs no key.

And the preparation that makes eventual sharding cheap: make sure the shard key (usually `tenant_id`) is present on every table and in every query from day one, keep cross-tenant queries out of the hot path, and avoid depending on global sequences and cross-aggregate transactions. If the model is shard-ready, sharding becomes a routing project rather than a rewrite.

*Hook: a system where you deferred sharding for years with partitioning and caching, and what finally forced the decision.*

---

## 10. Caching and Redis

### Q173. The caching patterns

| Pattern | Read path | Write path | Consistency | Failure mode |
| --- | --- | --- | --- | --- |
| **Cache-aside** | miss -> load from DB -> populate | write DB, invalidate cache | eventual; races possible (Q174) | stale entry if invalidation is lost |
| **Read-through** | cache library loads on miss | as above, via the library | same, but centralized | a cache outage becomes a database outage unless bypassed |
| **Write-through** | always a hit after write | write cache and DB synchronously | strong between the two, if both succeed | write latency is the sum; partial failure needs care |
| **Write-behind** | as above | write cache, flush to DB asynchronously | DB lags the cache | **data loss** if the cache dies before flushing |
| **Refresh-ahead** | hit; entry refreshed before expiry | unchanged | staleness bounded by refresh interval | wasted refreshes for cold keys |

Cache-aside is the default because it is simple, the cache is optional (a cache outage degrades rather than breaks), and it caches only what is actually read. Write-through suits read-heavy data that must never be stale after a write. Write-behind buys write throughput and is only acceptable for data you can lose - metrics, counters, last-seen timestamps.

### Q174. The permanent stale entry `[T]`

The interleaving, with a reader filling the cache and a writer invalidating it:

```
Reader:  cache miss
Reader:  SELECT -> reads value V1
                                  Writer: UPDATE row to V2
                                  Writer: DELETE cache key      (nothing there yet)
Reader:  SET cache key = V1       (writes the stale value, with a full TTL)
```

The cache now holds V1 while the database holds V2, and nothing will correct it until the TTL expires - which is why "forever" is only bounded by the TTL, and why an infinite TTL turns this into a permanent bug.

The two standard fixes:

1. **Delete twice (delayed double delete)**: the writer invalidates, updates the database, and schedules a second invalidation a short interval later (longer than the maximum read-then-write gap). Simple, probabilistic, widely used.
2. **Set with a version or use an atomic conditional write**: the reader writes to the cache only if the entry is still absent or older, using the row's version/`xmin` as part of the value and `SET ... NX` or a Lua compare-and-set. Deterministic, slightly more code.

Also effective in practice: **always use a TTL** so any inconsistency is self-healing; and prefer invalidating **after** the database commit, never before, so a rolled-back transaction cannot leave the cache showing a value that never existed.

### Q175. Invalidate versus update on write

"Delete the key" is safer for three reasons:

1. **Concurrency.** Two writers updating the same row produce two cache writes whose arrival order at the cache is not guaranteed to match their commit order at the database, so the cache can end up holding the older value permanently. Deletion is idempotent and order-independent: whoever deletes last, the next reader repopulates from the source of truth.
2. **Correctness of the derived value.** The cached entry is often not the row - it is a projection, an aggregate, a rendered document. The writer usually does not have all the inputs needed to compute the new cached value correctly, and computing it wrong is worse than a miss.
3. **Cost.** Updating writes a value that may never be read; deleting costs nothing and repopulation happens only if someone actually needs it. On a large fan-out (one row appearing in 40 cached views), deleting is much cheaper than recomputing all 40.

The exception is a very hot key where a miss would cause a stampede (Q177): there, updating in place - or refresh-ahead - avoids the thundering herd, and it is worth the extra care.

### Q176. TTL and jitter

Choosing a TTL is a business question first: how stale may this be before it is wrong? Then a technical one: how expensive is a miss, and how often does the underlying data change? A useful frame is that the TTL bounds your worst-case inconsistency when an invalidation is lost, so I set it as the *maximum tolerable staleness* rather than as a performance knob, and I rely on explicit invalidation for freshness.

**Jitter** exists because identical TTLs synchronize. A thousand keys populated by the same deployment or the same batch job all expire in the same second, and the database receives a thousand simultaneous misses - an avalanche (Q179), repeating every TTL period.

The arithmetic: with base TTL `T` and jitter `±j`, expirations are spread over `2j`, so the peak miss rate falls from `N` per instant to roughly `N/(2j)` per second. For 100,000 keys with a 10-minute TTL and 10 percent jitter (±60 s), that is 100,000 misses spread over 120 seconds - about 830 per second instead of a single 100,000-request spike. I use 10-25 percent jitter as a default: `ttl = base * (0.9 + random() * 0.2)`.

### Q177. Stampede, dogpile, thundering herd

All three name the same shape: a popular key expires (or the cache restarts) and N concurrent requests all miss and all recompute the same expensive value simultaneously.

| Mitigation | How it works | Cost |
| --- | --- | --- |
| **Locking / single-flight** | the first miss takes a short-lived lock (`SET key:lock NX EX 5`); others wait briefly and re-read, or return stale | added latency for the waiters; the lock holder can die, so it needs a TTL and a fallback |
| **Early recomputation (probabilistic)** | each reader recomputes with probability rising as expiry approaches (XFetch: recompute if `now - delta*beta*ln(rand) >= expiry`) | occasional redundant work, no coordination, elegant and stateless |
| **Stale-while-revalidate** | serve the expired value immediately and refresh in the background | requires storing the value past its logical expiry; readers get bounded staleness |

I default to **stale-while-revalidate plus single-flight**: the value is stored with a logical expiry inside it and a much longer physical TTL, so a reader that finds it logically stale returns it immediately and triggers exactly one background refresh. Nobody waits, the database sees one query, and the only cost is bounded staleness. Spring's `@Cacheable(sync = true)` gives you the single-flight half within one JVM (`02-spring` Q52) - note it is per-instance, so with 20 pods you still get 20 concurrent loads, which is why the lock needs to be in Redis rather than in the process.

### Q178. 99 percent hit rate and the cache restarts `[T]`

The arithmetic is the point. Suppose the application serves 20,000 reads per second with a 99 percent hit rate: the database currently sees 200 reads per second and is sized comfortably for that. When the cache restarts empty, the database receives **20,000 reads per second** - a 100x step change, instantly. Even if the database could theoretically serve 2,000, it is now 10x over capacity: queues build, latency rises, connection pools exhaust, the application times out and *retries*, which adds more load, and the system enters a metastable failure that does not recover even after the cache is warm, because the retry storm keeps it saturated.

The general form: your database is sized for the **miss rate**, and the cache hit rate is a multiplier on how far you are from the cliff. A 99 percent hit rate means you are 100x under-provisioned for a cold cache.

The warm-up strategy:

1. **Never restart into full traffic.** Warm the cache before the instance takes traffic - a preload job for the known-hot key set (the top N keys by access, exported periodically), or replay a sample of recent requests.
2. **Persistence and replicas**: Redis with AOF/RDB restores its dataset on restart, and a replica promotion keeps the working set - so the cold-cache event should be rare and planned rather than a routine restart.
3. **Protect the database independently**: a concurrency limiter or bulkhead on database access (a small connection pool is itself a limiter), single-flight so N misses for the same key become one query, and load shedding that returns a degraded response rather than queueing.
4. **Gradual ramp**: bring the instance into the load balancer slowly (slow start), so misses arrive at a rate the database can absorb.

The test that proves it: kill the cache in a game day and watch. Most teams discover this in production instead.

### Q179. Penetration and avalanche

**Cache penetration** is repeated misses for keys that **do not exist** in the database either - typically an attacker enumerating ids, or a client bug requesting a deleted resource in a loop. The cache never helps because there is nothing to store, so every request reaches the database.

Mitigations: **cache the negative result** with a short TTL (`key -> NOT_FOUND`, 30-60 s), which is the simplest and handles most real cases; **validate the key shape** before querying (a UUID that is not a UUID, an id outside the allocated range); and a **Bloom filter** of all existing keys in front of the cache - a probabilistic set with no false negatives, so "not in the filter" definitively means "does not exist" and the query is skipped. A Bloom filter for 100 million keys at a 1 percent false-positive rate is about 120 MB, which is why it is attractive at scale; the cost is that it must be kept in sync with deletions (which Bloom filters cannot do - you need a counting or cuckoo filter, or periodic rebuilds).

**Cache avalanche** is mass simultaneous expiry or a cache-tier failure sending the whole load to the database at once. Mitigations: TTL jitter (Q176), cache clustering so one node's failure loses only a fraction of the keys, persistence so a restart is not a cold start (Q178), a circuit breaker in front of the database, and a small in-process L1 cache that absorbs the first wave even when Redis is unreachable.

### Q180. The single-threaded event loop

Redis executes commands one at a time in a single thread (IO is now multi-threaded in Redis 6+, but **command execution is still serial**). What that buys: every command is atomic with no locking, no context switching, no race conditions inside the data structures, and predictable microsecond latency; it is also why `INCR`, `SETNX` and Lua scripts are trustworthy primitives for distributed coordination.

The consequence is that **any slow command blocks everything else**. The ones to know:

- `KEYS *` - O(N) over the entire keyspace. Use `SCAN`, which is cursor-based and incremental.
- `FLUSHALL`/`FLUSHDB` synchronously, or `DEL` of a huge collection - use `UNLINK` and the async variants, which free memory in a background thread.
- `SMEMBERS`, `HGETALL`, `LRANGE 0 -1` on a collection with a million elements - O(N) serialization into the reply buffer.
- `SORT`, `SUNION`/`SINTER` over large sets, `ZRANGEBYSCORE` returning huge ranges.
- A **Lua script** that loops - it holds the thread for its whole duration, and cannot be interrupted safely once it has written.
- `SAVE` (as opposed to `BGSAVE`), and the fork for `BGSAVE` on a large dataset, which pauses the process for the fork's page-table copy.

The operational rules: use `SCAN` families, keep collections bounded, set `slowlog-log-slower-than` to a low value and actually read the slow log, and treat "p99 latency spiked across every key" as a signal that someone ran an O(N) command.

### Q181. Redis data structures

Five with production uses:

1. **Sorted sets (ZSET)** - leaderboards, but far more usefully a **priority queue or time-index**: score by timestamp, then `ZRANGEBYSCORE` for "everything due before now" (delayed jobs), or `ZREMRANGEBYSCORE` to trim a sliding window (rate limiting, Q188).
2. **Hashes** - a small object stored field-wise, so you can read or increment one field without deserializing the whole thing. Session objects and per-entity counters. Small hashes are stored in a memory-efficient listpack encoding, which makes them dramatically cheaper than N separate keys.
3. **Sets** - membership and set algebra: unique visitors, tags, "has this user seen this item", and `SINTER` for simple recommendations.
4. **Streams** - an append-only log with consumer groups, acknowledgements and pending-entry tracking. A genuine lightweight queue when you want Kafka semantics without Kafka, with `XAUTOCLAIM` for recovering messages from a dead consumer.
5. **HyperLogLog** - approximate distinct counts in 12 KB regardless of cardinality, with about 0.8 percent error. Unique visitors per day per page, at a scale where exact sets would be gigabytes.

**Bitmaps** deserve a mention for daily active users (one bit per user id per day, then `BITCOUNT`/`BITOP` for retention analysis), and **lists** for simple FIFO with `BLPOP`, though Streams are the better modern choice.

### Q182. Expiration and eviction

**Expiration** happens two ways: **lazily**, when a key is accessed and found expired, and **actively**, via a background cycle that samples 20 random keys with TTLs, deletes the expired ones, and repeats while more than 25 percent of the sample was expired. The consequence is that expired keys can occupy memory for some time after their TTL, so `used_memory` lags what you expect - and a huge number of keys expiring at once causes a CPU spike in the active cycle.

**Eviction** happens when `maxmemory` is reached, governed by `maxmemory-policy`:

- `noeviction` - writes fail with an error. Correct for a **store of record**, where silently losing data is worse than an error.
- `allkeys-lru` / `allkeys-lfu` - evict from all keys. Correct for a **pure cache**. LFU (Redis 4+) is usually better than LRU because it resists a scan of cold keys evicting the genuinely hot ones.
- `volatile-lru` / `volatile-lfu` / `volatile-ttl` / `volatile-random` - evict only keys with a TTL. Useful for a **mixed** instance holding both cache entries (with TTL) and persistent structures (without) - though I prefer separating those into different instances entirely.

So: `allkeys-lfu` for a cache, `noeviction` for a store, and separate instances rather than a `volatile-*` policy where possible, because a mixed instance means a cache surge can start failing writes for the durable data.

### Q183. 6 GB used, rejecting writes despite LRU `[T]`

Likely causes:

1. **The policy is `volatile-*` and no keys have a TTL.** Redis can only evict keys with an expiry set, finds no candidates, and returns OOM errors. This is the most common cause and looks exactly like "LRU is not working".
2. **Memory fragmentation.** `used_memory` counts what Redis allocated logically, but the allocator holds much more from the OS (`used_memory_rss`); a `mem_fragmentation_ratio` well above 1.5 after churn means the real footprint is larger than the limit accounts for. Activedefrag helps.
3. **Non-evictable overhead counts toward `maxmemory`**: client output buffers (a slow consumer of a large `HGETALL`, or a replica buffer), the AOF rewrite buffer, and the replication backlog. A single slow client can consume gigabytes.
4. **A few enormous keys.** Eviction removes *keys*; if one key is 3 GB, evicting a hundred small keys frees nothing meaningful, and LRU sampling may never pick the big one.
5. **`maxmemory` is not set at all** on a replica, or set lower than expected in a managed service that reserves overhead.

Diagnosis: `INFO memory` for `used_memory`, `used_memory_rss`, `maxmemory_policy` and the fragmentation ratio; `MEMORY DOCTOR`; `--bigkeys` or `MEMORY USAGE` to find giants; `CLIENT LIST` for output buffer sizes; and `INFO stats` for `evicted_keys`, which being zero while OOM errors occur points straight at cause 1.

### Q184. Persistence

**RDB** is a point-in-time fork-and-dump of the whole dataset, taken every N seconds/changes. Data loss window: everything since the last snapshot - typically minutes. Fast to load, compact, and the fork can double memory usage transiently and pause the process while page tables are copied.

**AOF** appends every write command to a log, rewritten periodically to stay compact. With `appendfsync everysec` the loss window is **up to one second**; with `always` it is effectively zero but each write costs an fsync (Redis becomes disk-bound, typically an order of magnitude slower); with `no` it is whatever the OS buffers.

**Hybrid** (`aof-use-rdb-preamble yes`, the modern default): the AOF rewrite writes an RDB snapshot as the preamble followed by subsequent commands, giving RDB's fast load and AOF's small loss window.

What `everysec` really means: the fsync happens in a background thread once a second, so you lose up to one second **plus** whatever is in flight - and if the disk stalls, Redis will either block the write path or accumulate unflushed data, so a slow disk turns into latency in the main thread. It is also worth saying that persistence protects against a **process restart**, not against a node loss unless the storage survives, and that in a replicated setup the durability story is really replication plus persistence together (`WAIT` gives you a weak acknowledgement of replica receipt, not a quorum commit).

### Q185. Redis Cluster

The keyspace is divided into **16,384 hash slots**; each key maps to `CRC16(key) mod 16384`, and each master owns a range of slots. Clients cache the slot-to-node map and route directly, so there is no proxy in the data path.

Resharding moves slots between nodes one key at a time while both remain online, which is where the two redirects come from: **`MOVED`** means the slot has permanently moved - the client updates its map and retries at the new node; **`ASK`** means the slot is currently migrating and *this particular key* has already moved - the client retries once at the target with an `ASKING` prefix, without updating its map. A correct client library must handle both; a naive one breaks during resharding.

Multi-key operations are restricted to keys in the **same slot**, because a transaction or a `MGET` cannot span nodes. The escape hatch is **hash tags**: `user:{1234}:profile` and `user:{1234}:sessions` hash only the part inside the braces, so they land in the same slot and can be operated on together. That makes co-location a modeling decision - and an over-used hash tag creates a hot slot that cannot be split, which is the Redis version of a bad shard key (Q163).

### Q186. Sentinel versus Cluster versus managed

**Sentinel** is HA without sharding: one master, N replicas, and a quorum of Sentinel processes that monitor and promote. Simple, keeps all multi-key operations working, but capacity is one node's memory and one node's throughput.

**Cluster** is sharding plus HA: data split over slots, each master with its own replicas, automatic failover per shard. Scales memory and throughput horizontally, at the cost of the multi-key restrictions above and a smarter client.

**Managed** (ElastiCache, MemoryDB, Redis Cloud) is one of those two with the operations outsourced. Worth naming the difference between ElastiCache Redis (asynchronous replication, so failover can lose writes) and **MemoryDB** (writes committed to a multi-AZ transaction log before acknowledgement, so it is durable and can be a store of record) - that distinction is exactly the Q189 question.

When replication gives you consistency: **it does not**, in ordinary Redis. Replication is **asynchronous** - the master acknowledges the client immediately and propagates afterwards - so a failover loses any writes not yet replicated, and a partitioned old master can accept writes that are discarded on rejoin. `WAIT n timeout` blocks until `n` replicas have acknowledged, which narrows the window but is not a quorum protocol and does not prevent the split-brain case. Consistency requires either a system built on a consensus log (MemoryDB, or Redis Raft) or an architecture where losing recent writes is acceptable - which for a cache it is.

### Q187. A distributed lock in Redis `[T]`

The correct single-instance implementation:

```
SET lock:resource <random-token> NX PX 30000        -- acquire, atomic, with expiry
-- release, only if we still hold it (Lua, so it is atomic):
if redis.call("get", KEYS[1]) == ARGV[1] then return redis.call("del", KEYS[1]) else return 0 end
```

Three details matter: `NX` plus `PX` in **one** command (a separate `EXPIRE` can be lost if the client dies in between, leaving a permanent lock); a **random token** so you can only release your own lock (otherwise a client whose lock expired deletes the next holder's); and the compare-and-delete in **Lua** so it is atomic.

The **fencing token** is the part people omit. Because the lock can expire while the holder is still working - a GC pause, a slow disk, a network stall - two clients can believe they hold it. No amount of lock-service cleverness prevents that; the *resource* must reject stale writers. So the lock hands out a monotonically increasing number (`INCR lock:resource:fence`), the client passes it with every write, and the storage rejects any write carrying a token lower than the highest it has seen.

The argument against **Redlock** (acquire on a majority of N independent masters): Martin Kleppmann's critique is that its safety depends on bounded clock drift and bounded process pauses, and neither is guaranteed - a clock jump on one node or a long GC pause invalidates the mutual exclusion, and since the algorithm has no fencing token there is nothing downstream to catch it. Antirez's response is that the timing assumptions are reasonable in practice and that Redlock targets efficiency, not correctness. My position for an interview: for **efficiency** (avoid duplicate work, and a rare double-run is harmless) a single-instance Redis lock is fine and Redlock is unnecessary complexity; for **correctness** (money, exactly-once side effects) neither is sufficient without fencing at the resource, and I would use a consensus system or make the operation idempotent instead.

### Q188. Rate limiting in Redis

| Algorithm | Structure | Cost | Behavior |
| --- | --- | --- | --- |
| **Fixed window** | `INCR key:{user}:{minute}` with `EXPIRE` | O(1), one key per window | simplest; allows a 2x burst across the boundary |
| **Sliding window log** | ZSET of request timestamps; `ZREMRANGEBYSCORE` then `ZCARD` then `ZADD` | O(log n), memory proportional to the limit per user | exact, but expensive at high limits |
| **Sliding window counter** | two fixed-window counters, weighted by position in the window | O(1), two keys | very close to exact, cheap - the usual production choice |
| **Token bucket** | hash with `tokens` and `last_refill`, refilled by elapsed time in a Lua script | O(1), one key | allows controlled bursts, expresses "10/s with a burst of 50" naturally |

All of them must be **atomic**, which in Redis means either a single command or a Lua script - a read-then-write from the application is a race that lets N clients each pass the check.

I default to the **sliding window counter** for API rate limiting (cheap, accurate enough, no burst at the boundary) and **token bucket** where bursts are legitimate and should be explicitly budgeted. The sliding window log is worth its cost only when the limit is small and exactness is contractual.

### Q189. Redis as a store of record

What has to be true: the data must be **reconstructible or genuinely losable**, or you must run a variant with a durable replication log. With ordinary Redis, an acknowledged write can be lost in three ways - the fsync window (`everysec` = up to a second, Q184), asynchronous replication losing unpropagated writes at failover (Q186), and eviction silently removing keys if the policy is not `noeviction`.

So if I am using Redis as a store of record I set `appendfsync everysec` at minimum (`always` if the write rate allows), `maxmemory-policy noeviction` with alerting well before the limit, replication with automatic failover, and I accept and document the loss window. Better still, I use a variant with a consensus-backed log (**MemoryDB**) where writes are durable across AZs before acknowledgement.

The legitimate cases: rate limiter state, session state where a logout on failover is acceptable, real-time leaderboards, presence, deduplication windows, and any derived data with a rebuild path from a durable source. The cases where I would refuse: money, orders, anything with a legal retention requirement, and anything whose loss cannot be detected. The question I ask the team is "if this instance vanished right now, what would we do?" - if the answer is "rebuild it from Postgres in ten minutes", Redis is a fine home; if the answer is a silence, it is not.

### Q190. Four caching layers with different TTLs `[T]`

The layers - browser/client, CDN, application (Redis), database (result and buffer cache) - compose **multiplicatively**: worst-case staleness is the *sum* of the TTLs beneath the point of change, not the maximum. A 60-second application TTL under a 300-second CDN TTL under a 600-second browser cache means a user can see data up to 16 minutes old, and no single team's configuration explains it.

What actually goes wrong:

1. **Invalidation reaches only one layer.** Your deploy purges Redis; the CDN keeps serving the old page for its full TTL, and the browser keeps its copy longer still. Users report a bug that no engineer can reproduce, because their own cache expired.
2. **Inconsistent views within one page.** The HTML comes from the CDN (5 minutes old), an API call bypasses the CDN and returns fresh data, and the page renders contradictory numbers.
3. **Non-monotonic reads.** A user refreshes and sees new, then old, then new, because two CDN edges or two application instances have entries of different ages.
4. **Debugging is layered**, so an incident spends its first thirty minutes establishing which layer is serving the stale value.

The disciplines: make the **innermost TTL the shortest**, so a lower layer never outlives the layer above it in a way that surprises you; use **content-addressed or versioned URLs** for anything immutable (fingerprinted assets can then have a one-year TTL and never need purging); reserve **explicit purge** for the CDN on publish events and accept that browser caches cannot be purged at all, so `Cache-Control: no-cache` with an `ETag` is the right default for HTML; and document the total staleness budget as a single number the product owner has agreed to, rather than four numbers nobody has added up.

### Q191. Cache everything for 60 seconds `[A]`

**What I ask.** Which endpoints, and what is the read/write ratio on each? What is the actual latency problem - p50 or p99, and is it the database or something else (a downstream call, a serialization cost, GC)? What is the business tolerance for staleness on each screen, and are any of them *transactional* views where a user acts on the number they see? What happens when a user writes and immediately reads - do we get read-your-writes? Is the data per-user (in which case the hit rate may be near zero and the cache is pure overhead) or shared? And how do we invalidate on write, or are we relying on the TTL alone?

**When it is actually right.** A blanket short TTL is a genuinely good answer when the data is **shared, read-dominated and inherently stale-tolerant** - a product catalogue, reference data, a pricing table, a public feed, a dashboard aggregate - and especially when the alternative is a complex invalidation scheme whose bugs would cause *worse* inconsistency than 60 seconds does. Sixty seconds also caps the damage: it is self-healing, it needs no invalidation plumbing, and it is trivially reversible. For a system under acute load pressure it is often the right *first* move precisely because it is cheap and can be undone.

**Where I would push back.** On anything a user just wrote (read-your-writes breaks visibly and generates support tickets), on per-user data with low reuse (you pay memory and complexity for a 2 percent hit rate), on anything where a stale read drives a decision with money attached (inventory, balance, entitlement), and on the assumption that caching fixes a latency problem that is actually a query problem - if p99 is bad because of a missing index, the cache hides it until the cache misses, and then the incident is worse (Q178).

**The counter-proposal** I would usually make: cache the top three endpoints by volume with explicit TTLs chosen per endpoint from the staleness budget, add invalidation on write for the ones that need it, add jitter and single-flight, and instrument hit rate and staleness. That is a week's work rather than a day's, and it does not produce a systemic bug that surfaces in six months as "the data is sometimes wrong".

*Hook: a blanket cache that fixed a launch, and the invalidation bug you found afterwards.*

---

## 11. Document and wide-column stores

### Q192. The four families

- **Key-value** (Redis, DynamoDB in its simplest use, Memcached) - get and put by an opaque key. Shaped for point access at very high throughput, with no server-side query.
- **Document** (MongoDB, Couchbase, DocumentDB) - a key plus a structured, queryable value. Shaped for "load the whole aggregate by id, and occasionally query inside it".
- **Wide-column** (Cassandra, HBase, ScyllaDB, Bigtable) - a partition key selecting a row, and within it many sorted columns. Shaped for "give me a slice of a time-ordered series within one partition", at very high write rates.
- **Graph** (Neo4j, Neptune, JanusGraph) - nodes and edges with index-free adjacency. Shaped for traversals of unknown depth, where a relational recursive join would be quadratic.

The point to add: each one is fast at exactly the access pattern its physical layout supports, and slow at everything else. That is the actual difference from a relational database, which is mediocre at everything and lets you change your mind - which is a feature until you know your access patterns and a cost afterwards.

### Q193. "NoSQL scales better" `[T]`

What is actually traded is **coordination**. A system scales horizontally in proportion to how little cross-node agreement each operation needs. NoSQL stores achieve that by *removing features*: no cross-partition transactions, no joins, no global secondary constraints, no ad-hoc queries, often no strong consistency by default. Those removals are what allow linear scaling - not the data model, and not the absence of SQL.

Two things undermine the claim as usually stated. First, **a relational database can make the same trade**: shard it, forbid cross-shard queries and constraints, and you get the same scaling with the same restrictions (Q169) - which is exactly what Vitess and Citus do. Second, **modern PostgreSQL absorbed most of the differentiators**: JSONB with GIN indexing gives schema flexibility, logical replication and partitioning give operational scale, `SKIP LOCKED` gives queueing, and a single well-tuned instance handles workloads that in 2012 genuinely required a cluster - tens of thousands of writes per second on commodity hardware.

So the honest framing: choose NoSQL when the access pattern is known, narrow and enormous, or when the data model genuinely is not relational (documents, wide time-series, graphs). Do not choose it for "scale" without stating the write rate and the dataset size, because the numbers are usually well within one relational node.

### Q194. Schema-on-read versus schema-on-write

Schema-on-write validates at insert: the database rejects bad data, and every reader can rely on the shape. Schema-on-read accepts anything and each reader interprets it.

The debt does not disappear - it **lands on every reader, forever, and at runtime rather than at write time**. In a schema-on-read store with three years of history, a single field may exist in five shapes: absent, string, integer, string-that-looks-like-an-integer, and an object added last year. Every consumer must handle all five, and a consumer written today silently breaks on documents written in 2023. Worse, the failure surfaces in production at read time, on the oldest and least-tested data.

How I manage it: **validate at the boundary anyway** - MongoDB's JSON Schema validators, or the application's own schema with a version field on every document; **version documents explicitly** (`schemaVersion: 3`) and migrate lazily on read *and* eagerly with a background job, so the tail of old shapes is finite; keep the number of supported versions small and enforce it with a "no reads of version < N" alert; and treat a field's type as part of a contract owned by the writing service (`03-microservices` Q24). Schema-on-read is a deployment convenience, not an absence of schema - the schema is in the code, and the question is only whether it is written down.

### Q195. MongoDB: embed or reference

The three questions:

1. **Is the child ever accessed independently of the parent?** If yes (a comment that can be linked directly, a product line in a report across orders), reference. Embedded data cannot be queried as a first-class collection without an aggregation pipeline.
2. **What is the cardinality, and is it bounded?** One-to-few embeds well; one-to-many with a known small bound (addresses, order lines) embeds; one-to-unbounded (events, comments on a viral post) must reference or bucket, because the document grows without limit.
3. **What is the read/write ratio and the update granularity?** Embedding makes reads one round trip and atomic single-document writes; but every update rewrites - and may **move** - the whole document, so a hot small field inside a big document is expensive.

The **16 MB document limit** ends the argument for the unbounded cases: once a document can grow without a hard ceiling, embedding is a time bomb that fails only after the system has been live long enough to matter. The standard resolution is the **subset pattern** (embed the most recent or most relevant N children, reference the rest) or **bucketing** (a document per parent per time window holding up to N children), which also keeps working-set size sane.

### Q196. MongoDB indexes and the ESR rule

Types: **compound** (multiple fields, with the same leftmost-prefix rule as a B-tree), **multikey** (automatically created when a field is an array - one index entry per element, and a compound index may contain at most one array field), **partial** (`partialFilterExpression`, the equivalent of a partial index), **TTL** (a background thread deletes documents once an indexed date is older than `expireAfterSeconds` - deletion runs about once a minute, so expiry is approximate), **wildcard** (`$**`, indexes unknown field names - useful for genuinely dynamic attributes, expensive and no substitute for knowing your queries), plus text, geospatial and hashed.

**ESR** is the ordering rule for compound indexes: **Equality** fields first, then **Sort** fields, then **Range** fields. It exists because the index is a sorted structure: equality predicates narrow to a contiguous span; within that span the entries are already in the sort field's order, so the sort is free; and a range must come last because after consuming it the remaining fields are no longer sorted usefully. Getting it wrong produces the two classic symptoms - an in-memory `SORT` stage (which fails outright above 32 MB unless it can spill) and a large `totalKeysExamined` relative to `nReturned` in `explain()`. It is the same reasoning as Q45, with a name.

### Q197. Write concern and read concern

**Write concern** is durability: `w: 1` means the primary acknowledged; `w: "majority"` means a majority of the replica set has it, so it survives a failover; `j: true` adds a journal flush to disk; `wtimeout` bounds the wait (and note that a timeout does **not** roll the write back - it may still commit).

**Read concern** is visibility: `local` returns the node's most recent data, which may later be rolled back; `majority` returns only data acknowledged by a majority, so it can never be rolled back; `linearizable` additionally guarantees you see all writes that completed before the read began, at the cost of a round trip to confirm the node is still primary; `snapshot` gives a consistent point-in-time view for transactions.

**Read-your-writes** comes from `w: "majority"` + `readConcern: "majority"` + reading in the same **causally consistent session** (the driver carries a cluster time and the server waits for it). Causal consistency in a session is the mechanism that makes it work even when the read goes to a secondary; without the session, a majority read from a lagging secondary can still miss your write. The pragmatic default for most applications is `w: "majority"` with primary reads.

### Q198. Multi-document transactions as a smell `[T]`

MongoDB has had multi-document ACID transactions since 4.0 (replica set) and 4.2 (sharded), so the capability is real. But the document model's premise is that **the document is the transaction boundary**: you embed what changes together, so a single-document update is already atomic. Reaching for a multi-document transaction usually means the aggregate was split across documents in a way the access pattern does not support - which is a modeling decision to revisit, not a feature to lean on.

The costs make that concrete. A transaction holds a snapshot, and MongoDB has a default 60-second limit; WiredTiger keeps the transaction's history in cache, so long or large transactions cause cache pressure and can stall other operations; write conflicts abort the transaction and the application must retry (the drivers provide a retry helper, and it must be idempotent). On a **sharded** cluster it is far worse: a distributed transaction runs two-phase commit across shards with a coordinator, taking multiple network round trips, holding locks across them, and blocking chunk migrations for the affected ranges. Throughput drops by an order of magnitude compared with single-document writes.

So my rule: transactions are a correctness backstop for the rare cross-aggregate operation (a transfer, a cascading delete), not a routine pattern. If they appear in a hot path, the schema is wrong.

### Q199. Replica sets, oplog, rollback, arbiters

A replica set has one primary and N secondaries. The primary records every change in the **oplog** - a capped collection of idempotent operations - and secondaries tail it and apply it. Idempotency matters: an `$inc` is recorded as the resulting `$set`, so re-applying an oplog entry is safe.

**Elections** use a Raft-like protocol: when the primary is unreachable for `electionTimeoutMillis` (default 10 s), the members vote, and a candidate needs a **majority of all voting members** to win. That majority requirement is what prevents split brain, and it is why the set must have an odd number of votes.

**Rollback** is the consequence of asynchronous replication: if the primary accepts writes with `w: 1`, fails, and a secondary that never received those writes is elected, the old primary on rejoin must **undo** them - they are written to a rollback file and are effectively lost. `w: "majority"` prevents this by not acknowledging until the write cannot be rolled back.

**Why an arbiter is a trap**: it votes but holds no data. With a primary, one secondary and an arbiter (P-S-A), losing the secondary leaves a majority of votes so the primary stays up - but there is now only **one copy of the data**, and `w: "majority"` (majority of *data-bearing* members = 2) can never be satisfied, so majority writes hang. You have preserved availability of the *election* while destroying durability and the write path. Three data-bearing members is the correct configuration; an arbiter is a cost saving that buys a worse failure mode.

### Q200. Cassandra data modeling

The primary key is `((partition key), clustering columns)`. The **partition key** determines which node(s) hold the data, via the token ring - it is the unit of locality and the only thing a query can efficiently target. **Clustering columns** determine the sort order *within* the partition, so they support range slices and ordered reads, but only within one partition.

You design **one table per query** because there is no join, no ad-hoc filtering, and no query planner worth appealing to. A query that does not specify the partition key must scan the whole cluster (`ALLOW FILTERING`, which is a warning label, not a feature). So the process is: enumerate the queries first, then design a table whose primary key exactly matches each one's access path, then denormalize the data into all of them at write time. Writes are cheap in an LSM store (Q132), so duplicating data across five tables is the intended trade.

The consequence to state plainly: in Cassandra the **query workload is the schema**, and adding a new query pattern later means adding a new table and backfilling it. That is the real cost of choosing it, and the reason it belongs where the access patterns are known and stable.

### Q201. An unbounded partition `[T]`

What breaks first: **reads**. A read must reconstruct the row from the memtable plus every SSTable containing part of the partition, and a huge partition means large scans, large results held in memory on the coordinator and the replica, and heap pressure that shows up as GC pauses. Then **compaction** struggles because a partition cannot be split across SSTables usefully, so compacting it rewrites enormous amounts of data. Then **repair** and streaming (bootstrapping a new node) slow to a crawl because the unit of transfer is large. Cassandra warns above 100 MB and the practical guidance is to keep partitions under about 100 MB and 100,000 rows.

The standard fix is **bucketing**: add a synthetic component to the partition key that bounds its size. For time-series, `((sensor_id, day), timestamp)` instead of `((sensor_id), timestamp)`, so each partition holds one day of readings. For an unbounded list, `((user_id, bucket), item_id)` with `bucket = floor(sequence / 10000)`.

The cost of bucketing is that a query spanning buckets becomes several queries (which the client issues in parallel and merges), and the client must know the bucket boundaries - so the bucket granularity is chosen from the read pattern: fine enough to bound size, coarse enough that a typical query touches one or two buckets.

### Q202. Tunable consistency

Each read and write specifies how many replicas must respond: `ONE`, `QUORUM` (a majority of all replicas across all data centres), `LOCAL_QUORUM` (a majority within the local data centre), `ALL`, plus `LOCAL_ONE` and `EACH_QUORUM`.

`R + W > N` guarantees that the read set and the write set overlap in at least one replica, so a read sees the latest acknowledged write - strong consistency for a single key, with last-write-wins by timestamp resolving conflicts. With `N = 3`, `W = QUORUM (2)` and `R = QUORUM (2)`, `2 + 2 > 3` holds, and you tolerate one replica being down on each side.

Across data centres the arithmetic gets interesting. With `N = 3` in each of two DCs (`N = 6` total), `QUORUM` is 4 - which means every operation waits for a cross-DC round trip, adding tens of milliseconds. `LOCAL_QUORUM` (2 of the local 3) keeps latency local and is what almost everyone uses, but `LOCAL_QUORUM` reads in DC2 do **not** overlap with `LOCAL_QUORUM` writes in DC1, so you get eventual consistency across DCs even though each DC is internally consistent. If you need cross-DC strong consistency you must use `EACH_QUORUM` writes or `QUORUM`, and pay the latency.

Two footnotes worth having: last-write-wins depends on clock synchronization, so clock skew silently loses writes (Q106); and read repair plus anti-entropy repair are what converge the replicas that were not part of the quorum.

### Q203. Tombstones

A delete in an LSM store cannot modify the existing SSTables, so it writes a **tombstone** - a marker with a timestamp saying "this is deleted". Reads must merge tombstones with the live data to know that a value is gone. The same applies to TTL expiry, to setting a column to null, and to inserting a null in a collection.

`gc_grace_seconds` (default 10 days) is how long tombstones are retained before compaction may remove them. It exists to prevent **zombie data**: if a replica was down when the delete happened and the tombstone were purged before that replica came back and was repaired, the old live value would be resurrected during the next read repair. So the rule is that a full repair must complete within `gc_grace_seconds`, and lowering it without a reliable repair schedule reintroduces resurrection.

A **tombstone storm** kills reads because a read of a range must scan and merge every tombstone in that range. A queue-like table (insert, read, delete) accumulates millions of tombstones in the partitions being scanned; the read touches all of them to return zero live rows, blows past `tombstone_warn_threshold` (1,000) and then `tombstone_failure_threshold` (100,000), and the query is **aborted**. This is why "use Cassandra as a queue" is the canonical anti-pattern. The mitigations are to model deletes away (TTL with time-bucketed partitions that are dropped whole, rather than row deletes), to avoid inserting nulls, and to keep range scans away from deleted regions.

### Q204. Lightweight transactions

An LWT (`INSERT ... IF NOT EXISTS`, `UPDATE ... IF column = value`) provides linearizable compare-and-set for a single partition, implemented with **Paxos**. The cost is four round trips among the replicas - prepare/promise, read, propose/accept, commit - instead of one, so an LWT is roughly **4x the latency** of a normal write and considerably more expensive in coordination; under contention on the same partition, competing proposals cause retries and can livelock.

They also do not compose: an LWT is linearizable only for that one partition, so two LWTs are not a transaction, and mixing LWT and non-LWT writes to the same partition breaks the guarantee entirely (a plain write can overwrite a Paxos-agreed value).

The correct usage rate is **rare and deliberate**: unique username registration, a state transition that must happen exactly once, claiming a resource. If LWTs are on the hot path - or if a significant fraction of writes use them - the workload wants a different store, because you are paying for consensus on a system chosen for avoiding it.

### Q205. DynamoDB single-table design

The premise is that DynamoDB has no joins, and a query can only target one table and one index at a time - so if a screen needs an order plus its items plus the customer, they must live in the **same partition** to be fetched in one query. Single-table design puts multiple entity types in one table with **generic key names** (`PK`, `SK`) whose values are overloaded: `PK = CUSTOMER#123`, `SK = PROFILE` for the customer; `PK = CUSTOMER#123`, `SK = ORDER#2026-01-05#456` for their orders. A single `Query` on `PK = CUSTOMER#123` with `begins_with(SK, 'ORDER#')` returns exactly the item collection you need, sorted, in one request.

The **item collection** (all items sharing a partition key) is therefore the unit of co-location, and the sort key is designed as a hierarchical, sortable string so prefix queries slice it.

The process is inverted from relational design: you **write down every access pattern first** - the exact query, its filters, its sort order, its cardinality and its frequency - and only then design keys that serve them, adding GSIs for the patterns the base table cannot answer. That inventory is the deliverable; the schema falls out of it.

The honest caveat: this optimizes hard for known patterns and is genuinely painful when a new access pattern appears, since it may need a new GSI plus a backfill, or a table redesign. Which is precisely the Q212 argument.

### Q206. GSI versus LSI

| | LSI (local) | GSI (global) |
| --- | --- | --- |
| Partition key | same as the table | any attribute |
| When created | **only at table creation** | any time |
| Consistency | strongly consistent reads available | **eventually consistent only** |
| Capacity | shares the table's | its own, separate |
| Constraint | item collection (all items with that PK, across table and LSIs) capped at **10 GB** | no size limit |
| Uniqueness | inherits the table's | none - keys need not be unique |

The GSI back-pressure failure mode is the one to know: a GSI is maintained **asynchronously** by DynamoDB, and it has its **own** provisioned capacity. If writes to the table produce index updates faster than the GSI's capacity allows, the internal replication queue backs up; the GSI falls further behind (reads return stale data), and if it cannot catch up, **DynamoDB throttles the writes to the base table itself**. So an under-provisioned GSI takes down writes to a well-provisioned table - a coupling that surprises people, and the reason GSIs should be on-demand or generously provisioned, and the reason you do not create a GSI on a high-churn attribute with low selectivity.

### Q207. Throttling below provisioned capacity `[T]`

Capacity is provisioned for the table but consumed **per partition**. DynamoDB splits data across physical partitions by the hash of the partition key, and each partition has hard physical limits - 3,000 read units and 1,000 write units per second, regardless of what the table is provisioned for. A hot key or a hot key range therefore throttles while the table total looks fine.

**Adaptive capacity** mitigates this automatically: DynamoDB continuously reallocates the table's provisioned throughput toward the partitions receiving traffic (instantly, since 2019), and it will **isolate a frequently accessed item** by splitting the partition. But it cannot exceed the per-partition physical limits, and it cannot help a **single item** that is hotter than 3,000 RCU - the classic "one popular product" or "one tenant's counter" case.

What you actually change: **write dispersion** in the key. Add a suffix or shard to the partition key (`PRODUCT#123#7` across 10 shards, reading all 10 in parallel and merging); use a **write-sharded counter** for aggregates (Q113); cache the single hot item in DAX or the application so most reads never reach DynamoDB; or, for a read-hot item, exploit that eventually consistent reads cost half. And if the hot key is a **time-based key** (`DATE#2026-09-01`), the fix is to remove the time from the partition key, because it will always concentrate today's traffic on one partition.

### Q208. On-demand versus provisioned

**Provisioned** charges for capacity reserved per hour whether you use it or not; **on-demand** charges per request at roughly **6-7x** the per-unit price of provisioned.

The break-even therefore sits around **15-20 percent sustained utilization**: if your average consumption is above that fraction of the peak you would have to provision, provisioned with auto-scaling is cheaper; below it, on-demand is. The cliff is sharp because it is a straight multiple - a steady, predictable workload on on-demand can cost five times what it should, and a spiky workload on provisioned either throttles at the peaks or wastes most of its reservation.

How I choose: **on-demand** for a new workload with unknown traffic, for genuinely spiky or event-driven traffic, and for dev/test where the baseline is near zero; **provisioned with auto-scaling plus reserved capacity** for a mature, steady workload with a known profile. The other consideration is that auto-scaling reacts in minutes, so it does not protect against a sudden spike - a workload with sharp, unpredictable bursts belongs on on-demand even if the average would favour provisioned. I would also note that on-demand tables now scale to double their previous peak instantly and beyond that with warming, so the throttling risk during a launch is much lower than with auto-scaling.

### Q209. Transactions, conditional writes, optimistic concurrency

**Conditional writes** (`ConditionExpression`) are the primitive: `PutItem` with `attribute_not_exists(PK)` gives you insert-if-absent, and `UpdateItem ... SET version = :new WHERE version = :old` gives optimistic locking (Q105) with a single request and no locks held. This is the mechanism to reach for by default - it costs the same as a normal write and fails with `ConditionalCheckFailedException`.

**`TransactWriteItems`** provides ACID across up to **100 items** (and up to 4 MB) in one or more tables in one region, using a two-phase protocol internally. Costs: **twice** the write capacity units of the same writes done individually (prepare plus commit), higher latency, and `TransactionCanceledException` when any condition fails or when items conflict with another transaction - which the application must handle and retry. `TransactGetItems` similarly gives a consistent snapshot read at double the read cost.

Limits worth quoting: item size 400 KB, transaction 100 items / 4 MB, no cross-region transactions, and a transaction may not include two operations on the same item.

The design guidance is the same as MongoDB's (Q198): model so that the common case is a single-item conditional write, and reserve transactions for the genuine cross-item invariant - reserving inventory while creating an order, or enforcing uniqueness by writing a `UNIQUE#email` sentinel item alongside the entity in one transaction, which is the standard DynamoDB uniqueness pattern.

### Q210. Streams and TTL

**DynamoDB Streams** is an ordered, 24-hour log of item-level changes, sharded to mirror the table's partitions. Ordering is guaranteed **per partition key**, not globally. Delivery to a consumer (Lambda, or KCL) is **at-least-once**, so consumers must be idempotent, and a Lambda failure retries the whole batch by default - which means one poison record can block that shard until it expires unless you configure bisect-on-error, a maximum retry count and an on-failure destination. Stream view types let you receive `KEYS_ONLY`, `NEW_IMAGE`, `OLD_IMAGE` or `NEW_AND_OLD_IMAGES`, and the old image is what makes CDC-style consumers possible.

**TTL** deletes items whose designated epoch-seconds attribute is in the past. The important operational facts: deletion is **asynchronous and best-effort, typically within 48 hours** of expiry - so expired items remain readable and must be filtered out by the application; the deletes consume no write capacity; and they **do** appear in the stream, flagged with `userIdentity.principalId = "dynamodb.amazonaws.com"`, which is what distinguishes an expiry from a real delete.

That combination gives the standard archive pattern: set a TTL on hot items, subscribe a Lambda to the stream, and on a TTL-originated `REMOVE` event write the old image to S3 (in Parquet, partitioned by date) for analytics and long-term retention. The result is a hot table that stays small and a cheap, queryable archive - with the caveat that you must handle at-least-once delivery, so the S3 write should be keyed deterministically.

### Q211. An aggregate in DynamoDB `[T]`

Three approaches:

1. **Compute on read** - `Query` the item collection and sum client-side. **Strongly consistent** if you use a consistent read, correct, and needs no extra machinery. Costs read units proportional to the number of items, so it is fine for tens of items and unacceptable for tens of thousands - and it scales with the busiest customer, not the average.
2. **Maintain a counter item** in the same transaction as the write: `TransactWriteItems` containing the new order and an `ADD total :1` on the aggregate item. **Strongly consistent** and read-cheap, at double write cost, a 100-item transaction limit, and contention on the counter item if the write rate is high (Q207 - shard the counter if so).
3. **Update it asynchronously from the stream** - a Lambda consumes the change and increments the aggregate. **Eventually consistent** (typically sub-second, but unbounded during a consumer backlog), no impact on write latency, and it must be idempotent because delivery is at-least-once - which for a counter means either keeping a processed-sequence-number set or making the update a set-to-computed-value rather than an increment.

Which I would choose depends on the read/write ratio and the consistency requirement, and I would say so: option 1 for small collections, option 2 when the number must be exact at read time and write volume is moderate, option 3 for high volume where "within a second" is acceptable. The meta-point worth making is that DynamoDB has no `GROUP BY` by design - aggregation is a **write-time** decision, and discovering you need one later is exactly the Q212 problem.

### Q212. PostgreSQL to DynamoDB with reporting needs `[A]`

**The case for DynamoDB.** Predictable single-digit-millisecond latency at any scale, no instance to size or patch, no vacuum, no connection limits (which matters enormously for Lambda-based architectures), automatic multi-AZ durability, seamless scaling for spiky traffic, per-request pricing that goes to near zero when idle, and global tables if multi-region ever arrives. If the access patterns are genuinely key-based and high-volume, it removes an entire category of operational work.

**The case against, for this system specifically.** Two of the stated facts are disqualifying on their own. **Reporting requirements** mean ad-hoc aggregation, and DynamoDB has none - every aggregate is a write-time design decision (Q211) or an export to Athena/Redshift, which means building and operating a second pipeline. **A changing access pattern** is the exact thing single-table design trades away: each new pattern is a new GSI (with its own capacity, cost and back-pressure risk, Q206) or a full table redesign plus backfill, and there is no `WHERE` clause to fall back on. Add the loss of joins, transactions across more than 100 items, constraints, and the ability for an analyst to answer a question without an engineer.

**My recommendation.** Stay on PostgreSQL, and address whatever motivated the proposal directly - if it is operational burden, use a managed service (Aurora Serverless v2); if it is a scaling limit, get the actual numbers first, because a single instance handles far more than most teams assume (Q172); if it is one specific hot access pattern (session store, event ingestion, a per-user feed), move **that** to DynamoDB and keep the relational core, which is a far better trade than a wholesale migration.

**What would change my mind**: access patterns that are stable and demonstrably key-based, a write rate or dataset size beyond a comfortable single-node envelope, a hard requirement for multi-region active-active, and a separate analytics path that already exists - in which case DynamoDB plus a stream to S3 and Athena is a coherent architecture rather than a gap.

*Hook: a store-selection decision you made or reversed, and the access pattern that decided it.*

---

## 12. Search, analytics and data platform

### Q213. OLTP versus OLAP

| | OLTP | OLAP |
| --- | --- | --- |
| Workload | many small reads and writes by key, high concurrency | few large scans and aggregates, low concurrency |
| Latency target | milliseconds per operation | seconds to minutes per query |
| Schema | normalized, constraint-heavy | dimensional or wide/flat, denormalized |
| Storage | row-oriented (Q134) | column-oriented, compressed |
| Indexing | many selective B-trees | zone maps, min/max statistics, partitioning; few or no indexes |
| Isolation | genuinely required - concurrent writers | mostly single-writer batch loads; snapshot reads |
| Sizing | working set in memory, IOPS-bound | scan throughput and parallelism, bandwidth-bound |

The reason they cannot share a system happily is that every choice is opposite: the row store that makes an OLTP update cheap makes a 200-column scan expensive, and the compression that makes a scan cheap makes a single-row update expensive. Running both on one instance means the analytics scans evict the OLTP working set from cache and saturate the IO the transactions need - which is the practical incident behind Q224 and Q226.

### Q214. Elasticsearch fundamentals

The **inverted index** maps each term to the sorted list of documents containing it (plus positions and frequencies), so a term query is a dictionary lookup and a list intersection rather than a scan. **Analyzers** decide what the terms are: a character filter, a tokenizer, and token filters (lowercasing, stop words, stemming, synonyms, n-grams). The analyzer applied at index time and at query time must be compatible, and changing an analyzer requires **reindexing**, because the stored terms were produced by the old one - the most common cause of "search stopped matching after a config change".

A **shard** is a complete, independent Lucene index; the index is the union of its shards, and a query is executed on every shard and merged. That makes shard count the main scaling knob and the main mistake: too few and you cannot parallelize or grow; too many and every query pays coordination overhead across all of them, and the cluster state (held on the master) becomes large and slow.

How to choose: size shards by **target size** rather than count - 10-50 GB per shard for search workloads, and enough shards to spread across nodes but not more. For time-based data, use a **rollover** strategy (data streams / ILM) that creates a new index per period so shard count grows with retention rather than being fixed at creation, and delete whole indices instead of documents. Primary shard count is immutable after creation, so getting it wrong means a reindex - which is why the rollover pattern is the standard answer.

### Q215. "Near real time" `[T]`

Three separate operations, often conflated:

- **Refresh** makes recent writes **visible to search**. It creates a new Lucene segment from the in-memory buffer and reopens the searcher. Default interval is **1 second** (and, since 7.x, only when the index has been searched recently).
- **Flush** makes writes **durable** in the Lucene index: it commits the segments and clears the translog. Durability before that point comes from the **translog**, which is fsynced on every request by default (`index.translog.durability: request`).
- **Merge** consolidates many small segments into fewer large ones in the background, reclaiming space from deleted documents (deletes are tombstones, as in any LSM-shaped system) and keeping search fast.

What the application must not assume after an index call returns: **that the document is searchable**. It is durable (with default translog settings) and it is retrievable by `GET` by id (which reads the translog), but a search issued immediately afterwards will typically not find it. The classic bug is "create then redirect to the search results page", which shows the user a list without their new item.

The options: wait for the refresh interval; use `?refresh=wait_for` on the write (blocks until the next scheduled refresh - acceptable); use `?refresh=true` (forces an immediate refresh - do **not** do this per request, it destroys indexing throughput by creating tiny segments); or design the UI to read the item by id from the source of truth rather than from search.

### Q216. Keeping a search index in sync

| Approach | How | Rank |
| --- | --- | --- |
| **CDC from the database log** | Debezium or equivalent tails the WAL, so the index is driven by committed state | 1 - no dual-write gap, ordered, survives application bugs, catches writes from any source (including manual SQL) |
| **Transactional outbox** | the application writes an event in the same transaction as the row; a relay indexes it | 2 - correct, ordered per aggregate, requires the application to be the only writer (Q116) |
| **Periodic reindex** | scheduled full or incremental rebuild by `updated_at` | 3 - simple and self-healing, but stale by the interval and expensive at scale |
| **Dual write** | the application writes to the database and Elasticsearch in the same request | 4 - broken by construction: no atomicity, so any failure between the two leaves permanent drift |

Whichever you choose, **reconciliation is mandatory**, because every approach is at-least-once and some are lossy: run a periodic comparison of counts and checksums per key range (or per updated-at window) between the source and the index, emit a drift metric, and repair by reindexing the affected range. I also keep the source row's version or `updated_at` **in the indexed document** so the reconciler can detect staleness cheaply and so out-of-order updates can be rejected (index with an external version so an older event cannot overwrite a newer one).

And the operational requirement that people forget: a **full reindex must be a routine, tested procedure** - into a new index behind an alias, then an atomic alias swap - because analyzer or mapping changes force one, and a rebuild you have never rehearsed is not a recovery plan.

### Q217. Relevance

**TF-IDF** scores a document by term frequency times inverse document frequency: rare terms count for more, and repeated terms count for more, with a length normalization. **BM25** (the Lucene default since 5.0) is the same intuition with two corrections that matter: term frequency **saturates** (the 20th occurrence of a word adds almost nothing, where TF-IDF keeps rewarding it), and length normalization is tunable via `b`, with `k1` controlling the saturation curve. In practice BM25 is more robust on documents of varying length and on keyword-stuffed content.

On top of that you have **boosting**: field boosts (title over body), query-time boosts per clause, `function_score` for recency or popularity decay, and `rank_feature` fields for signals such as click-through rate.

But the framing I would give: "the results are wrong" is a **product** problem first. There is no universal correct ranking - the right answer depends on what the user is trying to do, and the only way to know is to define it. So the first steps are to collect judgements (what *should* rank first for these queries), instrument the search (queries with no results, queries with no clicks, position of the clicked result), and establish an offline metric such as NDCG on a labelled set plus an online metric such as click-through at position 1. Only then does tuning boosts mean anything, because otherwise every change is a swap of one anecdote for another. At maturity this becomes learning-to-rank on behavioural data - but the discipline of measuring first is what separates a search that improves from one that is endlessly re-tuned.

### Q218. Star, snowflake, wide flat table

**Star**: a central fact table of measurements with foreign keys to denormalized dimension tables. **Snowflake**: the same, with dimensions further normalized into sub-dimensions. **Wide flat table**: fact and all dimension attributes denormalized into one table, which is what columnar engines and BI extracts often prefer.

Snowflaking is rarely worth it now - it saves storage that compression already saves, and it adds joins - so the real choice is star versus flat.

Dimensional modeling still pays for itself when: **history matters** (slowly changing dimensions are the mechanism for "what was the customer's segment when the order was placed", Q219); **dimensions are shared** across many facts, so conforming them gives consistent definitions across the business - which is really a governance benefit, and the most valuable one; **dimensions change independently** of facts, so a customer rename should not require rewriting a billion fact rows; and when self-service BI tools need a comprehensible model to generate queries against.

The flat table wins when the consumer is a single dashboard or a machine-learning feature set, when the engine's join performance is the bottleneck, or when the data is genuinely event-shaped with no reusable dimensions. My default is a star schema in the warehouse's core layer and flat, purpose-built marts on top - dimensional where governance and history matter, denormalized where speed and simplicity do.

### Q219. Slowly changing dimensions

- **Type 1** - overwrite. History is lost; "what did we think last year" is unanswerable. Fine for corrections of genuine errors.
- **Type 2** - add a new row per change, with `valid_from`, `valid_to`, `is_current` and a **surrogate key** distinct from the business key. History is complete.
- **Type 3** - add a column for the previous value (`current_segment`, `previous_segment`). Cheap, but holds only one step of history.

Type 2 layout:

| customer_sk | customer_id | segment | valid_from | valid_to | is_current |
| --- | --- | --- | --- | --- | --- |
| 5001 | C-123 | SMB | 2024-01-01 | 2025-06-30 | false |
| 7314 | C-123 | Enterprise | 2025-07-01 | 9999-12-31 | true |

The query it enables is the whole point: the fact table stores `customer_sk` - the surrogate key **as of the time of the event** - so joining fact to dimension on the surrogate key automatically gives the attributes that were true when the transaction happened. Revenue by segment for 2024 attributes those orders to SMB, and 2025 orders to Enterprise, with no as-of logic in the query. Joining on the business key instead (`customer_id` plus `is_current`) gives the *current* segment for all history, which is a different and often equally valid question - and being able to say which one the business is asking for is the actual skill.

### Q220. Parquet and ORC

A Parquet file is divided into **row groups** (typically 128 MB - a horizontal slice of rows), each row group into **column chunks** (all values of one column in that slice), and each chunk into **pages** (the unit of compression and encoding). Footers hold the schema and, per row group and per column chunk, **statistics**: min, max, null count, and optionally a Bloom filter and page-level indexes.

That layout gives three savings at once: **column pruning** (read only the chunks for the columns in the query), **predicate pushdown** via the statistics (skip an entire row group whose max is below the filter's lower bound - which is why *sorting the data on the filter column at write time* can improve scan performance by an order of magnitude), and **encoding**: dictionary encoding for low-cardinality strings, run-length and bit-packing for repeated values, delta encoding for sorted integers, then a general codec (Snappy or Zstd) on top.

ORC is structurally equivalent - stripes instead of row groups, with indexes every 10,000 rows and optional Bloom filters - and grew up in the Hive ecosystem, while Parquet grew up in the Spark/Impala one. In practice both are fine and the choice follows the engine; what matters is the physical detail: **row group size** (too small kills the pruning benefit and multiplies metadata; too large wastes IO), **file size** (many small files is the classic performance killer in a lake), and **sort order** within the file.

### Q221. Warehouse versus lakehouse

A **warehouse** (Snowflake, BigQuery, Redshift) owns its storage format and metadata, which is what lets it offer transactions, constraints, fine-grained governance, a query optimizer with real statistics and predictable performance. A **data lake** is files in object storage - cheap, open, engine-agnostic, and with no transactions, no schema enforcement and no reliable listing at scale.

**Table formats** - Iceberg, Delta Lake, Hudi - add the missing layer on top of the files: a **metadata tree** listing exactly which data files constitute the table at each snapshot. That single idea provides ACID commits (a commit is an atomic pointer swap to a new metadata file, so readers never see a partial write), **snapshot isolation and time travel** (query the table as of a timestamp or version), **schema evolution** by field id rather than by column position (so renaming a column does not rewrite data and does not break old files), **hidden partitioning** (the format tracks the partition transform, so queries prune without the user writing a partition predicate - which fixes the Q159 problem for lakes), row-level updates and deletes via delete files, and efficient planning without listing the object store.

The lakehouse claim is therefore: keep the lake's open format and cheap storage, gain most of the warehouse's semantics, and let several engines (Spark, Trino, Flink, Snowflake, Athena) read the same tables. What you still give up relative to a warehouse is peak query performance on small interactive queries, mature fine-grained access control, and operational simplicity - lakehouses need compaction, snapshot expiry and orphan-file cleanup as scheduled jobs, and teams routinely forget until listing costs and small files degrade everything.

### Q222. ETL versus ELT

**ETL** transforms before loading, so the warehouse only ever holds curated data: it was the right design when compute in the warehouse was scarce and expensive. **ELT** loads raw data first and transforms inside the warehouse with SQL: it is the right design when warehouse compute is elastic and cheap, which it now is.

The reasons ELT won: the raw data is preserved, so a transformation bug is fixable by re-running rather than by re-extracting from a source system that may no longer have the data; transformations become SQL in version control (dbt), reviewable and testable by analysts rather than pipeline engineers; the warehouse's optimizer and parallelism beat a hand-rolled transformation tier; and the extraction layer gets much simpler, which is where most pipeline failures live.

Where transformation still belongs **outside** the warehouse: anything that must happen before the data may legally be stored (PII redaction, tokenization, residency filtering); heavy unstructured processing (parsing documents, images, embeddings); streaming transformations that must be applied with low latency; and cost control, where filtering an enormous source before loading is cheaper than loading and discarding.

My default is a layered ELT: a raw/bronze layer that is an immutable copy of the source, a cleansed/silver layer with types, deduplication and conformed keys, and a curated/gold layer of business models - each layer a set of tested SQL models, with the transformation logic owned by the team that owns the meaning of the data.

### Q223. Materialized views

A materialized view stores the computed result of a query. **Full refresh** recomputes it entirely; **incremental refresh** applies only the changes since the last refresh, which requires the engine to track them and restricts the SQL you may use (typically no outer joins, limited aggregates, and change-tracking enabled on the sources).

Staleness is the trade in every case: the view is correct as of its last refresh, so consumers need to know the refresh cadence, and a dashboard showing a materialized aggregate must display "as of" rather than implying it is live.

The **PostgreSQL limitation**: there is no incremental refresh at all. `REFRESH MATERIALIZED VIEW` recomputes the whole thing and takes an `ACCESS EXCLUSIVE` lock, blocking readers for the duration; `REFRESH ... CONCURRENTLY` avoids the lock but requires a unique index on the view, computes the full result **and** diffs it against the existing copy, so it is slower still and needs the space for both.

The ways around it: maintain a summary **table** yourself, updated incrementally by triggers or by a batch job keyed on `updated_at` (more code, far cheaper on large data); refresh into a new table and swap it in with a transactional `ALTER TABLE ... RENAME`, which gives an atomic cutover with no long lock; partition the materialized data by period and refresh only the current partition; or use an extension such as `pg_ivm`. Oracle, SQL Server (indexed views) and Snowflake (dynamic tables) all offer genuine incremental maintenance, and it is a legitimate reason to prefer them for that workload.

### Q224. Reporting on a replica cancels queries `[T]`

The mechanism: WAL replay on a standby needs to remove row versions and truncate pages, but a long-running query on that standby may still need to see them. When replay is blocked by a conflicting query for longer than `max_standby_streaming_delay` (default 30 s), PostgreSQL **cancels the query** - `ERROR: canceling statement due to conflict with recovery`. The conflict can be caused by vacuum cleaning dead tuples on the primary, by a lock (an `ALTER TABLE` replicated from the primary), by a dropped tablespace or by buffer pins. In other words, the primary's ordinary maintenance kills the replica's reports, and the more aggressive vacuum is (because the primary is busy), the more often it happens.

The two fixes, and they are opposites:

1. **`hot_standby_feedback = on`** - the standby tells the primary the oldest snapshot it needs, and the primary's vacuum refrains from removing those row versions. Reports stop being cancelled. The cost lands on the **primary**: dead tuples accumulate for as long as the longest replica query runs, so bloat grows and vacuum falls behind - a long report on the replica now damages the primary (Q93). Use with a `statement_timeout` on the replica so no query can pin the horizon indefinitely.
2. **Raise `max_standby_streaming_delay`** (or set it to -1 to wait indefinitely) - replay pauses instead of cancelling, so the query finishes. The cost lands on the **replica**: replication lag grows for the duration of the report, so any read-your-writes or freshness expectation on that replica breaks (Q143), and the WAL backlog must be retained.

Which to choose depends on whether stale reads or primary bloat is the lesser harm - and the honest third answer is that a dedicated reporting path (a logical replica, a snapshot into a warehouse, or a materialized read model) avoids the trade entirely, which is the Q226 conversation.

### Q225. Streaming versus batch

Batch processes a bounded dataset on a schedule: simple, easy to reason about, trivially re-runnable, and the latency is the interval. Streaming processes an unbounded dataset continuously: latency in seconds, at the cost of a much harder programming model - state must be kept and checkpointed, late data must be handled, and reprocessing history means replaying the stream.

**Exactly-once in a streaming aggregation** does not mean each message is delivered once; it means the **effect on the state and the output is applied once**. Flink and Kafka Streams achieve it with a checkpoint/transaction protocol: the operator state and the input offsets are committed atomically (Flink's distributed snapshots via Chandy-Lamport barriers; Kafka Streams via transactional writes covering the state-store changelog and the offset commit), and the sink must be either transactional or idempotent for the guarantee to extend end to end. The moment the sink is an ordinary REST call or a non-idempotent database insert, the guarantee stops at the framework boundary - which is exactly the point `03-microservices` Q44 makes.

A **watermark** is the framework's assertion about event-time progress: "I believe no event with a timestamp earlier than T will arrive from now on". It is what allows a windowed aggregate to be *closed* and emitted, because event time is unordered in reality. The watermark is a heuristic - usually the maximum observed event time minus an allowed lateness - so it embodies the trade between latency (emit early) and completeness (wait longer). Data arriving after the watermark is **late**, and you choose per pipeline whether to drop it, emit an updated result, or route it to a side output for reconciliation.

My default is batch unless a business decision genuinely depends on sub-minute freshness, because batch's operational cost is a fraction of streaming's - and micro-batching (a few minutes) covers most of what people call real time.

### Q226. "Real-time dashboards" on OLTP data `[A]`

**Establish the actual requirement first.** What decision does the dashboard drive, and how quickly must it change behavior? "Real time" almost always means one of: *sub-second* (an operational monitor - an alert, a fraud signal, a fulfilment queue), *a minute or two* (a business monitor - orders today, error rate, campaign performance), or *this morning* (a management report someone looks at with coffee). The cost difference between those three is an order of magnitude each. I also ask: how many concurrent viewers, how much history does each panel span, how many distinct metrics, is any of it per-customer, and what is the consequence of a number being five minutes stale? And critically: does anyone *act* on it within the freshness window - because if the response takes a day, the freshness is decoration.

**The design, by answer.**

- **This morning**: nightly or hourly batch into a small reporting store (or a materialized view refreshed on a schedule, Q223). Cheapest by far, and it is the honest answer more often than people expect.
- **A minute or two** - the common real case: **CDC from the primary** (logical decoding, Q150) into a store designed for the read shape. For modest volumes, a read replica plus incrementally maintained summary tables; for real volume, stream into a columnar or real-time analytics store (ClickHouse, Druid, Pinot, or the warehouse with a micro-batch) and have the dashboard query pre-aggregated rollups, never raw facts. The rollups are the thing that makes it cheap: a dashboard should read hundreds of rows, not millions.
- **Sub-second**: this is not a dashboard, it is an operational system. Compute the metric in the event stream (Flink or Kafka Streams) and push it to the client over websockets, with the store used only for backfill.

**What I would rule out**: pointing a BI tool at the OLTP primary. It puts unbounded, unpredictable scans on the system that takes orders (Q213), it will eventually cause an incident during a business peak, and every subsequent query optimization has to consider a workload nobody controls. Pointing it at a **read replica** is better and is a legitimate first step for a small system, but it brings the query-cancellation trade of Q224 and it still scales badly.

**How I would sequence it**: start with the replica plus summary tables to prove the metrics are the right ones (most dashboards are rebuilt twice before anyone trusts them), and only build the CDC pipeline once the definitions are stable - because the expensive part is not the pipeline, it is agreeing what "an active customer" means.

*Hook: a real-time dashboard request you converted into a five-minute one, and what it saved.*

---

## 13. The Java data layer against a real database

### Q227. What Hibernate actually issues

- **Lazy `@ManyToOne`**: the owning entity's `SELECT` fetches only the foreign key column; touching the association triggers a second `SELECT ... WHERE id = ?`. Note the trap - a lazy to-one on a **nullable** or non-owning side cannot be proxied without knowing whether the row exists, so Hibernate silently makes it eager unless you enable bytecode enhancement. And accessing `order.getCustomer().getId()` on a proxy does *not* hit the database, because the id is already known; accessing any other field does.
- **`@OneToMany` with `JOIN FETCH`**: one `SELECT` with a `LEFT OUTER JOIN`, returning the parent's columns duplicated once per child row. Hibernate de-duplicates the parent entities in the persistence context, but the *rows* still cross the wire - a parent with 50 children and 30 columns transfers 50 copies of those columns, which is the hidden cost of fetch joins on wide entities.
- **`@BatchSize(size = 25)`**: the first access to any lazy collection triggers one `SELECT ... WHERE parent_id IN (?, ?, ... up to 25)` covering the un-initialized proxies in the persistence context. So N+1 becomes N/25+1 round trips, with no row duplication - which is why batch fetching is often better than a fetch join for collections.

The point to make: these are three different physical strategies for the same object graph, and the right one depends on collection size and how many parents you load, not on a global preference.

### Q228. `JOIN FETCH` with pagination `[T]`

Hibernate cannot apply `LIMIT`/`OFFSET` in SQL, because the join has multiplied rows - limiting to 20 SQL rows might yield three parents, or seven, depending on child counts. So it fetches **the entire result set** and paginates **in memory**, logging `HHH000104: firstResult/maxResults specified with collection fetch; applying in memory`.

On a large table that is a full scan, a full transfer and an OutOfMemoryError waiting for a busy day. It is one of the most damaging silent behaviors in the framework, because it works perfectly in a test with 50 rows.

The correct solution is **two queries**:

1. Page over the **root ids only**, with `LIMIT`/`OFFSET` (or keyset, Q38) applied in SQL:
   `SELECT o.id FROM orders o WHERE ... ORDER BY o.created_at DESC LIMIT 20`
2. Fetch the full graph for exactly those ids:
   `SELECT o FROM Order o LEFT JOIN FETCH o.items WHERE o.id IN :ids ORDER BY o.created_at DESC`

The `ORDER BY` must be repeated in the second query, because `IN` does not preserve order. Spring Data expresses this with a `@Query` returning ids plus an `@EntityGraph` method, and Hibernate 6 offers `@FetchProfile` and `Session.byMultipleIds`. The alternative, when the collection is small, is to drop the fetch join and use `@BatchSize`, which paginates correctly in SQL and issues one extra batched query.

### Q229. `MultipleBagFetchException`

A **bag** is an unordered `List` with no `@OrderColumn` - Hibernate cannot know the index of each element. Fetching two bags in one query produces a Cartesian product between the two collections (10 items x 5 payments = 50 rows), and because neither list has an index, Hibernate cannot tell duplicates caused by the join from genuine duplicate elements. It refuses rather than silently corrupting the collections.

The fixes, in the order I prefer them:

1. **Change the collection type to `Set`.** A `Set` has no positional semantics, so the duplicates from the join collapse correctly. This is the usual answer, and it is nearly always what the model meant. The cost is that the entities need sensible `equals`/`hashCode` (use the business key or the id, never the whole object).
2. **Fetch one collection per query.** Two queries, each fetching one collection for the same root; the persistence context assembles the graph. This also avoids the Cartesian product entirely, which matters as soon as both collections are non-trivial.
3. **Use `@BatchSize`** on both collections and no fetch join at all - three queries total, no row multiplication, and it paginates.

Worth saying out loud: even when the exception is avoided, fetching two collections in one query is usually the wrong plan. 10 x 5 is fine; 200 x 50 is 10,000 rows to build a graph of 250 objects.

### Q230. Dirty checking and flush ordering

At flush, Hibernate compares each managed entity against its loaded snapshot and generates the SQL. It does **not** execute statements in the order your code made the changes; it uses a fixed **action order**: all inserts (in the order the entities were persisted), then updates, then collection deletions, then collection updates/insertions, then entity deletions.

That is why a "delete then insert" on a unique key fails: you remove the row with `email = 'a@b.com'` and add a new one with the same email, and Hibernate executes the **insert first**, hitting the unique constraint even though the sequence you wrote was legal. The same shape causes foreign-key violations when a child is deleted and a replacement inserted.

The remedies: `flush()` explicitly between the two operations to force the order (crude but effective); make the constraint **deferrable** so it is checked at commit (Q59); reuse the existing row (update instead of delete-and-insert), which is usually the better model anyway; or step outside the persistence context for that operation with a JPQL/native bulk statement, remembering that bulk statements bypass the persistence context and require care with stale managed entities.

### Q231. `readOnly = true` still issues an `UPDATE` `[T]`

`@Transactional(readOnly = true)` in Spring sets Hibernate's flush mode to `MANUAL` and marks the JDBC connection read-only - it is a **hint**, not an enforcement (`02-spring` Q64). Mechanisms by which a write still happens:

1. **A nested or subsequent transaction.** `readOnly` applies at the boundary that *started* the transaction. A `REQUIRED` inner method marked read-write joins the outer read-only transaction and keeps its flush mode; conversely a read-only outer with a `REQUIRES_NEW` inner gets a genuinely writable transaction.
2. **An explicit `flush()`** or a JPQL/native `UPDATE`/`DELETE` executed directly - `MANUAL` flush mode stops *automatic* flushing, not deliberate statements.
3. **Hibernate's own writes**: sequence or identity generation, a version increment from an explicit lock, and second-level cache or `@Version` housekeeping. Also `@PostLoad`-style logic that mutates and then gets flushed by a later read-write transaction in the same persistence context.
4. **Entities detached from a read-only transaction and merged in a writable one** later in the request - the change originated in the read-only method but is written elsewhere.
5. **The driver's read-only flag is advisory** in PostgreSQL only if the transaction is actually started as `READ ONLY`; with `LazyConnectionDataSourceProxy` or certain pool configurations the flag may not be applied at all, so nothing stops the write at the database level.

The dependable enforcement is at the **database**: connect the read path with a role that has only `SELECT` privileges, or route it to a replica where writes are physically impossible. That converts a hint into a guarantee.

### Q232. JDBC batching in Hibernate

`hibernate.jdbc.batch_size = 50` tells Hibernate to accumulate `PreparedStatement` parameter sets and send them together. `order_inserts` and `order_updates` sort the pending statements by entity type so that consecutive statements share the same SQL - **without them, batching silently does almost nothing**, because a batch is broken every time the statement text changes, and an interleaved insert/update sequence across two entity types produces batches of one.

`IDENTITY` generation disables insert batching entirely: the database assigns the key during the insert, and JDBC cannot return generated keys for a batch in a way Hibernate can attribute to entities, so it must execute each insert individually to learn the id. This is the single most common reason batching "does not work", and it is a modeling decision made years earlier. Use a `SEQUENCE` with a pooled optimizer (`allocationSize = 50`, `pooled-lo`) instead: ids are allocated in blocks with one round trip per block, and inserts batch freely.

The other requirements: flush and clear the persistence context every batch-size entities in a long loop (otherwise dirty checking becomes quadratic and the heap fills), and remember that batching helps throughput, not latency - and that a batched statement still counts as N rows for locking, WAL and replication.

### Q233. `reWriteBatchedInserts`

By default the PostgreSQL JDBC driver sends a batch as N separate protocol messages in one network flush. That saves the *round trips* but the server still parses and executes N statements, so the win is partial - typically 2-3x.

With `reWriteBatchedInserts=true`, the driver rewrites a batch of identical single-row inserts into **one multi-values statement**: `INSERT INTO t (a,b) VALUES (?,?),(?,?),...`. The server then parses and plans once and executes one statement, which removes per-statement overhead as well as round trips. Typical speedups are **2-3x on top** of ordinary batching, so 5-10x versus unbatched - I would quote it as "a few times faster, measure it" rather than a precise figure.

The caveats: it applies only to plain `INSERT` batches (not updates, and not inserts with `ON CONFLICT` in older driver versions), the rewritten statement is subject to the 65,535-parameter protocol limit so very wide rows cap the effective batch size, and generated-key retrieval interacts badly with it. It is a connection property, so it applies to everything on that pool - which is fine, because it is a no-op when it cannot apply.

### Q234. Fetch size and streaming

`setFetchSize(n)` asks the driver to return rows in chunks of `n` rather than materializing the whole result. In the PostgreSQL driver this switches from the simple query protocol - which buffers the **entire** result set in the client's heap - to using a **server-side cursor** with `Execute` messages for `n` rows at a time.

Three conditions must all hold for a real cursor:

1. **Autocommit must be off.** With autocommit on, the driver cannot keep a cursor open across statements, so it silently ignores the fetch size and buffers everything. This is the one people miss.
2. **The statement must be a forward-only, read-only `ResultSet`** (`TYPE_FORWARD_ONLY`), because a scrollable result cannot be streamed.
3. **`fetchSize > 0`** must be set on the `Statement` before execution.

In JPA/Hibernate that means a transaction (so autocommit is off), `hibernate.jdbc.fetch_size` or a query hint, `Query.stream()` or `ScrollableResults`, plus `entityManager.detach()`/`clear()` every N rows so the persistence context does not accumulate the whole table anyway (`02-spring` Q134). MySQL's driver is different again - it streams only with `Integer.MIN_VALUE` as the fetch size, and holds the connection hostage until the result is fully consumed.

The failure this prevents is the classic one: a nightly job that worked for two years and then OOMs, because the table finally exceeded the heap.

### Q235. Connection pool sizing

The arithmetic, from Little's Law: `concurrency = throughput x latency`. If the application does 2,000 database operations per second and each takes 2 ms of database time, the required concurrency is `2000 x 0.002 = 4` connections. Add headroom for variance and you land at 10, not 100.

The other bound is the server: a database can genuinely execute only as many queries at once as it has cores (plus a factor for IO wait). The PostgreSQL rule of thumb is `connections = ((core_count x 2) + effective_spindle_count)` - so around 20-30 on a 12-core machine, **total across all clients** (`03-microservices` Q193 - the sum of every service's pool must fit).

Why 100 is worse than 20: connections beyond the server's execution capacity do not run in parallel, they **queue inside the database**, where the queue is far more expensive than a queue in the application. Each backend has its own process and memory, each active query competes for `shared_buffers`, spinlocks and IO bandwidth, context switching rises, `work_mem` is allocated per node per connection (Q76), and lock contention grows superlinearly. The measured result is that throughput peaks at a modest pool size and then *declines*, while latency grows without bound - the classic knee curve. A smaller pool also acts as a **bulkhead**: excess load waits in the application where you can see it, time it out and shed it, instead of degrading everyone's queries.

The practical procedure: start from the arithmetic, load-test to find the knee, and set the pool just below it.

### Q236. Connection timeouts at 20 percent database utilization `[T]`

"The pool is exhausted while the database is idle" means connections are being **held** rather than **used**. The diagnosis path:

1. **Confirm where the time goes.** HikariCP exposes `hikaricp_connections_pending`, `acquire` timing and `usage` timing - the mean *usage* time is the key number. If usage is 800 ms while queries take 3 ms, the connection is held for something other than querying.
2. **Look for work inside the transaction that is not database work.** An HTTP call, an S3 upload, a message publish, JSON serialization or a `Thread.sleep` inside a `@Transactional` method holds a connection for its whole duration (`02-spring` Q76, Q212). This is the most common cause by a wide margin.
3. **Check for connections acquired too early.** Spring acquires a connection when the transaction starts, even if the first query comes 200 ms later - `LazyConnectionDataSourceProxy` fixes that (`02-spring` Q65). Read-only paths opening transactions they do not need have the same effect.
4. **Check for leaks.** `leakDetectionThreshold` in Hikari logs stack traces for connections held beyond a limit; a manual `getConnection()` without a finally-block, or a `Stream` from a repository never closed, leaks permanently.
5. **Check for blocking at the database that is not visible as utilization** - lock waits show as idle CPU but held connections. `pg_stat_activity` filtered on `wait_event_type = 'Lock'` answers this in one query, as does a long `idle in transaction` list.
6. **Check the layers between**: a PgBouncer pool smaller than the application's, a proxy connection limit, or DNS/TLS handshake latency on connection creation (which makes `connectionTimeout` fire during a burst if `minimumIdle` is low).

The shape of the answer matters: database utilization measures *work*, and pool exhaustion measures *occupancy*. They diverge whenever a connection is held without working, and that is nearly always the application's fault.

### Q237. The pool timeouts that matter

- **`connectionTimeout`** (default 30 s) - how long a caller waits for a connection from the pool before failing. It should be **short** (1-3 s) so a saturated pool fails fast and sheds load rather than queueing every request thread.
- **`maxLifetime`** (default 30 min) - how long a connection may live before being retired. It must be **shorter than any timeout applied by the infrastructure below** - the database's `idle_session_timeout`, a load balancer's idle TCP timeout (AWS NLB is 350 s), a firewall's connection tracking table, or PgBouncer's `server_lifetime`. If something else kills the connection first, the pool hands out a dead socket and the application sees random `Connection reset` errors. The standard advice is a few minutes less than the shortest upstream limit.
- **`idleTimeout`** (default 10 min) - how long an idle connection above `minimumIdle` survives. Only relevant if `minimumIdle < maximumPoolSize`; I usually set them equal for a fixed-size pool, which gives predictable behavior and no reconnection storms.
- **`validationTimeout`** (default 5 s) - how long the aliveness check may take. Should be well below `connectionTimeout`.

The relationship rule to state: `validationTimeout < connectionTimeout`, and `maxLifetime < (every idle/lifetime limit imposed by the database, the proxy and the network)`. Getting the second one wrong produces intermittent errors that look like a network fault and are actually a configuration mismatch.

### Q238. The timeouts that stop a runaway query

- **`statement_timeout`** (server side, PostgreSQL) - **this is the one that actually stops a runaway query.** The server cancels the statement itself, freeing the backend and its locks. Set it as a default on the application role (`ALTER ROLE app SET statement_timeout = '10s'`), and per-transaction with `SET LOCAL` for the paths that legitimately need longer.
- **`lock_timeout`** (server side) - bounds only the time spent *waiting for a lock*, which is what you want around DDL and background jobs so they never head a lock queue (Q100). It does not bound execution.
- **`idle_in_transaction_session_timeout`** (server side) - kills a session that holds an open transaction without running anything. This is the guard against the Q93 damage, and it should be set aggressively (seconds) on OLTP roles.
- **JDBC `Statement.setQueryTimeout` / Hibernate's `javax.persistence.query.timeout`** - the driver issues a `CANCEL` request on a *separate connection* when the timeout fires. It works, but it depends on the client being alive and able to open a second connection, and it races with the query finishing.
- **The JDBC socket timeout** (`socketTimeout` connection property) - a network-level read timeout. It **does not stop the query**: it abandons the socket, and the server happily continues executing, holding locks, until it finishes. Setting only this is how you end up with a database full of queries nobody is waiting for.

The layering to state: server-side timeouts are authoritative because they act on the process doing the work; client-side timeouts protect the client. You need both, and the client's must be *longer* than the server's so the server's cancellation is what fires first and you get a clean error rather than an abandoned connection.

### Q239. Prepared statement caching and PgBouncer

Three caches. The **driver** caches the parse/describe of a statement per connection (`prepareThreshold`, default 5, then `preparedStatementCacheQueries`), so repeated executions skip parsing and use the extended protocol. The **pool** does not cache statements itself in Hikari (it deliberately delegates to the driver, since a pooled connection is the driver's own). The **server** holds the named prepared statement and, after five executions, may switch to a generic plan (Q72).

PgBouncer in **transaction pooling** mode breaks this: a server connection is assigned to a client only for the duration of a transaction, so the next transaction may land on a different backend where the client's named prepared statement (`S_1`) does not exist - producing `prepared statement "S_1" does not exist`, or worse, colliding with a *different* statement of the same name created by another client.

The modes: **session** pooling preserves everything but gives you almost no pooling benefit (one server connection per client connection). **Transaction** pooling is the useful one. **Statement** pooling forbids multi-statement transactions entirely.

The resolutions: PgBouncer 1.21+ supports **prepared statements in transaction mode** (`max_prepared_statements > 0`), which tracks and replays them per server connection - this is the modern answer. Before that, you disabled server-side prepares in the driver (`prepareThreshold=0`), accepting the parse cost on every execution, which for simple OLTP statements is a few percent and for complex ones is significant. Either way, note the second-order effect: with prepares disabled, every execution is a custom plan, which *fixes* the Q72 generic-plan problem for skewed queries by accident.

### Q240. PgBouncer pooling modes

- **Session** - a server connection is held for the whole client connection. Everything works; you gain only connection *establishment* savings, which is still meaningful for short-lived clients (Lambda) but does nothing for the connection count.
- **Transaction** - a server connection is assigned per transaction. This is where the real benefit lies: 2,000 application connections can share 30 server connections, because most of them are idle between transactions.
- **Statement** - a server connection per statement; multi-statement transactions are rejected outright. Useful only for autocommit-only workloads.

What **transaction pooling forbids** in application code, because these depend on session state that will not follow you to the next transaction:

- Session-level prepared statements (Q239, unless the modern support is enabled).
- `SET`/`RESET` outside a transaction - use `SET LOCAL` inside one instead.
- Session-scoped **advisory locks** (`pg_advisory_lock`) - use the transaction-scoped variant (Q111).
- `LISTEN`/`NOTIFY` (Q117) - the listener's connection is not stable.
- `WITH HOLD` cursors, temporary tables, and any reliance on `currval()` of a sequence.
- Anything that assumes `pg_backend_pid()` or `application_name` is stable.

The practical consequence for a Spring application: put the pooler behind a small Hikari pool per instance, keep everything session-scoped out of the code, and be aware that `statement_timeout` set per session must become a role default or a `SET LOCAL`.

### Q241. Retrying a failed `INSERT` `[T]`

The rule: an error is safe to retry only if you know the server **did not** process the statement. Which errors give you that knowledge:

**Safe** - the server explicitly rejected it and the transaction is dead:

- `40001` serialization failure and `40P01` deadlock detected - the transaction was rolled back by definition (Q103).
- `08001`/`08004` connection could not be established, and `57P03` cannot connect now - nothing was sent.
- A constraint violation is *deterministic*, so retrying is pointless but not dangerous - it will fail again.

**Ambiguous** - the connection died at or after submission and you cannot tell whether the commit happened:

- `08006` connection failure, `08003` connection does not exist, a socket read timeout, `57P01` admin shutdown, and any failure during the **commit** itself. The classic case is the network dropping between the server writing the commit record and the client receiving the acknowledgement - the write succeeded and the client believes it failed.

This is the same "you cannot tell slow from dead" problem as a 504 in `03-microservices` Q34, and no error code will ever resolve it. The only real answer is to make the operation **idempotent** so the ambiguity stops mattering: a client-supplied idempotency key with a unique constraint (Q114), a natural business key with `ON CONFLICT DO NOTHING`, or a deterministic primary key derived from the request. Then the retry either inserts or collides harmlessly, and you read back the result.

The other half is **detection**: before retrying an ambiguous write with no idempotency key, query for the record. That is not free of races, but it converts a certain duplicate into an unlikely one - and if the data matters, build the key.

### Q242. Dropping JPA for jOOQ, Spring Data JDBC or SQL `[A]`

The criteria I would apply to a real codebase:

**Keep JPA** when the domain is genuinely graph-shaped and long-lived - entities with real invariants, aggregates loaded and mutated as objects, optimistic locking, cascading lifecycle - and when the team's productivity on CRUD-heavy screens matters more than SQL control. Dirty checking, the persistence context and the second-level cache are real leverage when you are working with objects rather than result sets.

**Move to jOOQ** when the application's centre of gravity is **queries** rather than an object model: complex reporting, dynamic filters, window functions, CTEs, upserts, database-specific features. jOOQ gives type-safe SQL generated from the schema, so the compiler catches a renamed column, and the SQL you write is the SQL that runs - which removes the entire category of "what did Hibernate do" problems. The cost is no dirty checking, no lazy graphs, and a code-generation step in the build.

**Move to Spring Data JDBC** when the model is aggregate-oriented but simple: no lazy loading, no dirty checking, everything explicit, an aggregate saved as a unit. It suits an event-sourced or DDD-strict service where the implicitness of JPA is a liability rather than a convenience (`02-spring` Q138).

**Plain SQL / `JdbcClient`** for batch jobs, bulk operations, migrations and anything performance-critical.

**The signals I look for in the existing code** to trigger a change: a majority of repositories using `@Query` with native SQL (the ORM is already being bypassed); recurring N+1, `MultipleBagFetchException` and pagination incidents (Q228, Q229); entities with 40 fields and eight relationships that nobody loads together; performance work that consists of fighting the fetch strategy; and a team that cannot predict the SQL a method will issue.

**What I would actually do**: not a rewrite. JPA and jOOQ coexist on the same `DataSource` and the same transaction manager, so the pragmatic path is to keep JPA for the aggregate write model and introduce jOOQ or `JdbcClient` for the read and reporting paths - which is where the pain is, and which gives the team a working comparison before any larger decision.

*Hook: a read path you moved off the ORM, and what it did to latency and to the size of the code.*

---

## 14. Schema evolution and zero-downtime migrations

### Q243. The rule, and the sequence derived from it

The rule: **during a rolling deployment, the old and new versions of the application run simultaneously against a single schema, so the schema must be compatible with both at every instant.**

Everything follows from it. Since you cannot change code and schema atomically, and since you may need to roll the code back, every change must be decomposed into steps that are each backward compatible:

1. **Expand** - add the new structure alongside the old: a nullable new column, a new table, a new index, a new enum value. Deploy this alone; the old code ignores it.
2. **Migrate** - deploy code that **writes both** old and new (dual write), then backfill the historical rows (Q249). At the end of this step both representations are complete and equivalent.
3. **Transition reads** - deploy code that **reads the new** and still writes both. This is the **last safe rollback point**: everything up to here can be reverted by redeploying the previous version, because the old structure is still current.
4. **Contract** - deploy code that no longer references the old structure, then, in a *later* release, drop it.

The two disciplines that make it work in practice: **never combine a schema change and a code change that depends on it in the same deployment**, and **keep the drop at least one release behind** the code that stopped using it, so a rollback never lands on a missing column.

### Q244. PostgreSQL DDL locks, and the fast paths

Most `ALTER TABLE` forms take `ACCESS EXCLUSIVE` (Q96), which conflicts with everything including `SELECT`. But many of them are **metadata-only** and complete in microseconds, so with a short `lock_timeout` they are safe on any size of table:

**`ACCESS EXCLUSIVE` but instant** (catalog update only):

- `ADD COLUMN` with no default, or with a **non-volatile default** (PostgreSQL 11+ stores it as `attmissingval`).
- `DROP COLUMN` (the column is only marked dropped; space is reclaimed by later rewrites).
- `RENAME COLUMN` / `RENAME TABLE`.
- `SET/DROP NOT NULL` where a valid `CHECK` constraint already proves it (PostgreSQL 12+).
- `ADD CONSTRAINT ... NOT VALID` (foreign key or check).
- `SET DEFAULT`, `DROP DEFAULT`, `SET STATISTICS`, comments.
- Widening `varchar(n)` to `varchar(m>n)` or to `text`, and `numeric` precision increases (PostgreSQL 9.2+).

**`ACCESS EXCLUSIVE` and a full table rewrite** (the dangerous ones):

- `ALTER COLUMN TYPE` for anything that changes the on-disk representation.
- `ADD COLUMN` with a **volatile** default.
- `SET NOT NULL` without a proving constraint (a full scan, not a rewrite, but still a long exclusive lock).
- `ADD PRIMARY KEY`, `ADD UNIQUE` (builds the index under the lock - build the index `CONCURRENTLY` first and then `ADD CONSTRAINT ... USING INDEX`).
- `CLUSTER`, `VACUUM FULL`, non-concurrent `REINDEX`.

**Weaker locks**: `CREATE INDEX CONCURRENTLY` and `REINDEX CONCURRENTLY` take `SHARE UPDATE EXCLUSIVE`; `VALIDATE CONSTRAINT` takes `SHARE UPDATE EXCLUSIVE` and scans without blocking writes; `DETACH PARTITION CONCURRENTLY` likewise.

The operating rule: any statement in the second list needs the shadow-column treatment (Q248), and every statement in the first list still needs `lock_timeout` because the *lock acquisition* is the risk, not the work (Q250).

### Q245. `ADD COLUMN ... DEFAULT` `[T]`

Before PostgreSQL 11, adding a column with a default rewrote every row of the table, holding `ACCESS EXCLUSIVE` for the whole rewrite - the canonical migration that took a large table offline. The standard workaround was three steps: add the column nullable, backfill in batches, then `SET DEFAULT`.

From **PostgreSQL 11**, a **non-volatile** default is stored in the catalog as `attmissingval` and applied on read for rows that predate it, so the operation is a metadata change and completes instantly regardless of table size. Existing rows are materialized lazily as they are updated.

The variant that **still rewrites** is a **volatile** default - `DEFAULT random()`, `DEFAULT gen_random_uuid()`, `DEFAULT nextval('seq')`, or a call to any function declared `VOLATILE` - because each row must get a *different* value, so there is nothing to store as a single missing value. `DEFAULT now()` is a subtle case: `now()` is `STABLE`, so it qualifies for the fast path and every existing row gets the *same* timestamp, which is often not what the author intended.

So the rule to state: a constant or `STABLE` default is free; a per-row-varying default is a rewrite, and must be done as add-nullable, backfill in batches, then set the default for new rows.

### Q246. Adding `NOT NULL` without a long lock

`ALTER TABLE ... SET NOT NULL` must prove no null exists, and by itself it does a full table scan under `ACCESS EXCLUSIVE` - minutes of downtime on a large table.

The sequence that avoids it (PostgreSQL 12+):

```sql
-- 1. Add the constraint without validating it: instant, catalog-only.
ALTER TABLE orders ADD CONSTRAINT orders_ref_not_null
  CHECK (customer_ref IS NOT NULL) NOT VALID;

-- 2. Make sure new rows comply (the NOT VALID constraint already enforces this
--    for inserts and updates) and backfill the existing nulls in batches.

-- 3. Validate: takes only SHARE UPDATE EXCLUSIVE, scans without blocking writes.
ALTER TABLE orders VALIDATE CONSTRAINT orders_ref_not_null;

-- 4. Now the fast path applies - the planner uses the validated CHECK as proof,
--    so this is metadata-only.
ALTER TABLE orders ALTER COLUMN customer_ref SET NOT NULL;

-- 5. Optional: drop the now-redundant CHECK.
ALTER TABLE orders DROP CONSTRAINT orders_ref_not_null;
```

The key insight is that `NOT VALID` splits the operation into "enforce for new rows" (instant) and "prove for old rows" (concurrent), which is the same decomposition as expand-contract applied to a constraint. The identical pattern works for foreign keys: `ADD CONSTRAINT ... REFERENCES ... NOT VALID`, then `VALIDATE CONSTRAINT`.

### Q247. Renaming a column across two versions

A rename is **not** a rename - it is an add, a dual write, a backfill, a read switch and a drop. The full sequence:

1. **Release 1 (schema)**: `ALTER TABLE t ADD COLUMN new_name <type>` - instant, nullable, no default (Q245). Nothing reads or writes it.
2. **Release 2 (code)**: the application **writes both** `old_name` and `new_name` on every insert and update, and still **reads `old_name`**. Both versions of the code can run: the old one writes only `old_name`, which is still the read source, so nothing breaks. (A `BEFORE INSERT OR UPDATE` trigger keeping the two in sync is an alternative that avoids needing this release at all, and is what I would use if the write paths are numerous or outside my control.)
3. **Backfill**: batched `UPDATE t SET new_name = old_name WHERE new_name IS NULL AND id BETWEEN ...`, throttled against replication lag (Q249). At the end, verify with a count of mismatches.
4. **Release 3 (code)**: **read `new_name`**, still write both. **This is the last safe rollback point** - `old_name` is still fully populated and correct, so redeploying release 2 works with no data loss.
5. **Release 4 (code)**: stop writing `old_name`. From here a rollback to release 3 would read `new_name` (fine) but release 2 would read a stale `old_name`, so rollback is now bounded to one release.
6. **Release 5 (schema)**: `ALTER TABLE t DROP COLUMN old_name`, plus adding any constraints and indexes on `new_name`, at least one release after nothing writes it.

The reason not to shortcut it with a plain `RENAME` (which is itself instant) is that during the rolling deploy the old pods would reference a column that no longer exists, and every request they serve fails until they are replaced - a partial outage lasting the length of the rollout, and an unrecoverable one if you then need to roll back.

### Q248. Changing a column type on 500 million rows

`ALTER COLUMN TYPE` rewrites the table under `ACCESS EXCLUSIVE`, so on this size it is not an option. The shadow-column approach:

1. **Add the new column** with the target type, nullable, no default (instant).
2. **Add a trigger** to keep it in sync for all new writes:

```sql
CREATE FUNCTION sync_amount() RETURNS trigger AS $$
BEGIN
  NEW.amount_new := NEW.amount_old::numeric(18,4);
  RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER t_sync_amount BEFORE INSERT OR UPDATE ON payments
  FOR EACH ROW EXECUTE FUNCTION sync_amount();
```

The trigger is what makes this safe **regardless of how many application write paths exist**, including manual SQL and other services - which is why I prefer it to dual writes in the application for a type change.

3. **Backfill** in batches with throttling and restartability (Q249), verifying as you go that the converted value round-trips (a mismatch count query, and an explicit decision about rows that cannot convert).
4. **Add the constraints and indexes** on the new column, using `CREATE INDEX CONCURRENTLY` and `NOT VALID` + `VALIDATE` (Q246), so nothing takes a long lock.
5. **Switch reads**, then stop writing the old column, then drop the trigger and the old column - the same release cadence as Q247.

The alternatives worth naming: for a whole-table restructure, `pg_repack` or a logical-replication-based tool (`pgroll`, or a self-managed logical replica with the new schema and a switchover) does the same job with one short cutover, at the cost of double the storage and a more complex operation. And for `varchar(n)` widening or `numeric` precision increases, check first - those are already metadata-only (Q244).

### Q249. Backfilling

The properties a backfill job must have:

- **Batched by key range, not by `OFFSET`.** `WHERE id > :cursor ORDER BY id LIMIT 5000` uses the index and stays constant-cost; `OFFSET` degrades linearly and re-reads work (Q38).
- **One transaction per batch**, so locks are short and dead tuples become vacuumable immediately (Q120). Batch size chosen so a batch takes well under a second - typically 1,000-10,000 rows.
- **Throttled against replication lag.** Between batches, read `pg_stat_replication.replay_lag` (or the LSN difference) and sleep until it is below a threshold. This makes the job self-regulating and prevents it from breaking replica reads. I also throttle on primary load - if `statement_timeout` errors or lock waits rise, back off.
- **Restartable.** The cursor is persisted (a control table row updated in the same transaction as the batch), so a crash resumes rather than restarts. The batch update must be idempotent - `WHERE new_col IS NULL` makes re-running a batch harmless.
- **Observable**: rows processed, rows remaining, current rate, projected completion, and errors, emitted as metrics. A backfill with no ETA is a backfill nobody can plan around.
- **Killable**: a stop flag it checks each batch, and a low `statement_timeout` and `lock_timeout` so it can never become the head of a lock queue.

**Verification of completion** is a separate step, not an assumption: a count of rows still not converted (`WHERE new_col IS NULL`), a sample comparison of old versus new values, and - if the trigger approach was used - a check that no row has diverged (`WHERE new_col IS DISTINCT FROM f(old_col)`). Only when that returns zero, twice, do I proceed to the read switch.

### Q250. A migration behind a long `SELECT` `[T]`

The mechanism is the fair lock queue from Q100: the `ALTER TABLE` requests `ACCESS EXCLUSIVE`, waits behind the running `SELECT`, and every subsequent statement - including trivial `SELECT`s that would not have conflicted with each other - queues behind the `ALTER`. Throughput on that table goes to zero, the connection pool exhausts within seconds, and the application is down while the "migration" has not executed a single byte of work.

The pattern that avoids it:

```sql
SET lock_timeout = '2s';
ALTER TABLE orders ADD COLUMN customer_ref text;
```

If the lock cannot be acquired within two seconds, the statement fails with `55P03 lock_not_available`, the queue drains immediately, and the application is unaffected. The migration tool then **retries with backoff** - typically a loop of 10-20 attempts with a few seconds between - until it catches a moment with no long-running statement. In PostgreSQL a subtransaction or a retry loop in the migration script (or in the tool: Flyway callbacks, or a wrapper that executes the DDL with retries) implements this.

The complementary measures: before starting, query `pg_stat_activity` for statements older than a threshold on the target table and either wait or kill them deliberately; keep `statement_timeout` low on the application role so no query can block DDL for minutes (Q238); schedule DDL away from batch windows; and never wrap several DDL statements in one long transaction, because the locks accumulate and are all held until the end.

### Q251. Migrations in CI/CD

**Who runs them**: a dedicated job in the pipeline, running **before** the application deployment, with a database role that has DDL privileges - not the application's runtime role (Q267). Running them from the application's startup (`spring.flyway.enabled=true`) is convenient for small systems and wrong at scale, for four reasons: the application role then needs DDL privileges permanently; the migration runs inside the pod's startup budget, so a slow migration causes a liveness failure and a crash loop; a rollback of the application does not roll back the schema, but the coupling makes people think it does; and diagnosing a failed migration means reading pod logs rather than a pipeline step.

**N instances starting at once**: Flyway and Liquibase both take a **lock** - Flyway uses `pg_advisory_lock` on PostgreSQL (a row lock on `flyway_schema_history` for other engines), Liquibase uses the `DATABASECHANGELOGLOCK` table. So concurrent starts are safe: one applies, the others wait and then find nothing to do. The failure mode to know is that Liquibase's lock is a **row**, not a real lock, so a crashed instance leaves it set and every subsequent deployment hangs until someone runs `releaseLocks` - which is a memorable 2 a.m. discovery. Flyway's advisory lock is released automatically when the session dies, which is one reason I prefer it on PostgreSQL.

**The rest of the pipeline discipline**: migrations are versioned, immutable once merged (never edit an applied migration - the checksum will fail, and it *should*), reviewed like code with the lock implications called out (Q256), tested against a restored production-sized copy so a rewrite is discovered before production, and applied to every environment through the same job so staging is a genuine rehearsal.

### Q252. Rollback

Which migrations are genuinely reversible: additive, non-destructive ones - `ADD COLUMN`, `CREATE TABLE`, `CREATE INDEX`, adding a nullable field. Their inverse loses nothing.

Which are not: anything that **destroys information**. `DROP COLUMN` cannot be undone by `ADD COLUMN` - the data is gone. A type narrowing that truncated values cannot be widened back. A `DELETE` or a merge of two rows is irreversible. And any migration that has been running in production for ten minutes has new data written under the new schema, which the "down" script does not account for.

Why `down` scripts are a trap: they are almost never tested (nobody runs them in CI against realistic data), they create the *illusion* of a safe rollback so people approve riskier changes, they cannot restore destroyed data, and they are usually wrong because they were written by imagining the inverse rather than by executing it. The one place they earn their keep is local development.

**What I do instead**: make every migration **forward-only and backward-compatible** (Q243), so a rollback of the *application* never requires a rollback of the *schema*. If a schema change turns out to be wrong, the remedy is a new forward migration that corrects it, reviewed like any other. For the destructive step at the end of an expand-contract cycle, I add a deliberate safety margin: the drop happens one or more releases later, so by then the column has been provably unused, and before dropping anything large I take a targeted backup of the column (`CREATE TABLE t_old_col_backup AS SELECT id, old_col FROM t`) so the data is recoverable for a retention period. That is a cheap insurance policy and it has saved me more than once.

### Q253. `gh-ost`, `pt-online-schema-change`, and PostgreSQL

Both MySQL tools solve the same problem - MySQL's `ALTER TABLE` historically locked or blocked - by building a shadow copy:

- **`pt-online-schema-change`** creates a new table with the desired schema, adds **triggers** on the original to mirror every insert/update/delete into it, copies existing rows in chunks, then swaps the tables with an atomic `RENAME`. The triggers add write latency and can interact badly with existing triggers and foreign keys.
- **`gh-ost`** avoids triggers entirely: it copies rows in chunks and applies concurrent changes by **tailing the binlog** as if it were a replica. That decouples the migration from the write path, gives it a throttle it can control (it can pause based on replication lag or load), and makes it interruptible and resumable. It is the better tool for the same reason CDC beats dual writes (Q216).

**The PostgreSQL story is different** because most DDL is already cheap (Q244): adding and dropping columns, renames and constraint additions are metadata-only, and `CREATE INDEX CONCURRENTLY` handles indexes. What remains is table rewrites, and for those the options are `pg_repack` (for compaction and some rewrites, using triggers plus a short swap), the shadow-column pattern (Q248), or the newer generation of tools - **`pgroll`** and **Reshape** - which implement expand-contract by exposing *versioned views* to old and new application versions simultaneously, so the migration and the deployment are decoupled by construction. Logical replication to a new instance with the target schema, followed by a switchover, is the heavyweight option for a full restructure.

### Q254. Multi-tenancy models

| | Shared schema, tenant column | Schema per tenant | Database per tenant |
| --- | --- | --- | --- |
| Migration cost | one migration, instant | N migrations per release (Q255) | N migrations, plus N instances to manage |
| Blast radius | worst - one bad query or migration affects everyone | medium - per-schema failures possible | best - fully isolated |
| Noisy neighbor | worst - shared buffers, locks, connections | shared instance, so still present | isolated (if separate instances) |
| Per-tenant restore | very hard - row-level extraction | possible - restore one schema | trivial |
| Cost at 5,000 tenants | lowest | moderate - catalog bloat, connection and vacuum overhead | prohibitive |
| Isolation guarantee | application/RLS enforced (Q270) | database-enforced by search path | physical |

The practical guidance: **shared schema** is the default for scale (thousands of tenants, self-serve SaaS), with RLS as defense in depth and a tenant column in every index. **Database per tenant** is right when tenants are few, large and contractually isolated (regulated enterprise deals), and it becomes the "silo" tier of a tiered model. **Schema per tenant** occupies an uncomfortable middle - it gives real isolation but PostgreSQL's catalog does not love tens of thousands of schemas, connection pooling gets harder (`search_path` per request), and migrations scale linearly.

The pattern I would actually deploy is the **tiered** one from `03-microservices` Q216: shared schema as the pool, with the option to promote a specific tenant to their own database, and the code written so that placement is a routing lookup rather than a branch.

### Q255. 4,000 tenants at 8 seconds each `[T]`

Serially that is nearly nine hours, during which the fleet is running mixed schema versions - which is fine if the migration is backward compatible (Q243) and fatal if it is not. So the first move is to **guarantee backward compatibility**, because that converts a nine-hour outage into a nine-hour background job.

Then, in order:

1. **Parallelize.** Run K workers migrating different schemas concurrently, bounded by the database's capacity (connections, IO, and lock contention on shared catalog objects). With 16 workers, nine hours becomes about 35 minutes. Catalog contention is the real limit, so ramp K up while watching lock waits.
2. **Make it resumable and idempotent.** A control table recording each tenant's applied version, so a failure at tenant 2,300 resumes rather than restarts, and so a partially applied migration is detectable per tenant.
3. **Attack the 8 seconds.** Is it a table rewrite that could be a metadata change (Q244, Q245)? Is it an index build that could be `CONCURRENTLY` on a small table? Eight seconds per schema on a small tenant usually means the migration is doing something rewrite-shaped that a better formulation would avoid.
4. **Batch by tenant tier** - migrate internal and small tenants first as a canary, then the rest in waves, so a bad migration is caught at tenant 5 rather than tenant 4,000.
5. **Decouple deployment from migration**: the application must tolerate both schema versions, so deploying code and migrating tenants become independent activities with a feature flag deciding when the new path is used per tenant.

And the strategic answer: 4,000 schemas is past the point where schema-per-tenant is comfortable (Q254). If migration time is a recurring operational problem, that is the model telling you it has outgrown its assumptions, and the conversation is whether the largest tenants move to their own databases and the long tail consolidates into a shared schema.

### Q256. Schema change review across 30 teams `[A]`

**Principles**: the owning team decides *what* to change; the platform makes it **impossible to do it dangerously by accident**; review effort is spent only on the changes that can cause an outage. A central approval board for all schema changes becomes a queue, and a queue becomes a workaround.

**The mechanism I would build**, in the order I would build it:

1. **Automated lint in CI, blocking.** A migration linter (Squawk, or a home-grown check) that fails the build on: DDL without `lock_timeout`; a rewrite-inducing `ALTER COLUMN TYPE` or volatile default; `SET NOT NULL` without the `NOT VALID` sequence; `CREATE INDEX` without `CONCURRENTLY`; a `DROP` of a column or table (which requires an explicit annotation and a reference to the release where it stopped being used); adding a `UNIQUE` or `PRIMARY KEY` directly; and a missing index on a new foreign key. This catches perhaps 80 percent of dangerous changes with no human involved, which is what makes the rest of the process affordable.
2. **A risk classification in the PR template**, auto-suggested by the linter: *routine* (additive, metadata-only) merges with normal code review; *elevated* (backfill, index build on a large table, anything touching a table above a size threshold) requires a second reviewer from a rotating pool of database-literate engineers and a written execution plan; *high* (rewrite, drop, cross-team table, multi-tenant fan-out) requires the platform team and a scheduled window.
3. **A rehearsal environment** with a restored production-sized copy, where every elevated and high migration is executed and **timed** before approval. "It took 4 seconds on a copy of production" is worth more than any review comment.
4. **Ownership metadata**: every table has an owning team recorded in a catalog, and a migration touching a table you do not own automatically requests review from the owner. This is where the five-shared-databases problem actually bites, and making the coupling **visible** is half the fix - it creates the pressure to split shared tables that no policy will create.
5. **Runtime guardrails independent of review**: `statement_timeout` and `lock_timeout` defaults on every role, alerting on lock waits and on long-running transactions, and a kill switch runbook. Review catches intent; guardrails catch mistakes.
6. **A feedback loop**: every schema-related incident produces either a new lint rule or a change to the classification. The rule set should grow from real incidents, not from a document written up front.

**What I would explicitly not do**: require a DBA sign-off on every change (a bottleneck and a false sense of safety), maintain a central "data model" document that diverges within a quarter, or block teams from evolving their own tables. The goal is to make the safe path the easy path and the unsafe path loud.

*Hook: a migration standard you introduced across teams, and the incident that prompted it.*

---

## 15. Observability, troubleshooting and capacity

### Q257. The first five minutes

1. **Is it the database or the application?** Look at database CPU, IO and active session count next to application latency. If the database is idle and the application is timing out, it is the pool or the network (Q236), and the next four steps are the wrong tree.
2. **What is running right now?** `pg_stat_activity` ordered by `now() - query_start`, filtered to `state <> 'idle'`. This answers "is one query eating the machine, or are ten thousand normal queries arriving".
3. **Is anything blocked?** `pg_stat_activity` where `wait_event_type = 'Lock'`, joined with `pg_blocking_pids()`. A blocking chain has one root, and killing it resolves the incident in seconds - this step has the highest payoff per second spent.
4. **Is anything idle in transaction?** The same view filtered on that state, ordered by `xact_start`. It explains bloat, blocked DDL and vacuum stalling (Q93).
5. **What changed?** A deployment, a migration, a batch job, a traffic spike, a failover, a statistics refresh. Correlate the start time of the incident with the change log before theorizing.

Then, if none of that answers it, `pg_stat_statements` ordered by `total_exec_time` for the recent window, and the wait-event profile (Q259). The discipline is to establish *where the time is going* before forming a hypothesis, because a database incident has perhaps six root-cause families and this sequence eliminates them in order of frequency.

### Q258. `pg_stat_statements`

It aggregates execution statistics per **normalized query** (constants replaced by placeholders, so the same statement with different parameters shares a `queryid`), per user and per database. The columns I actually read: `calls`, `total_exec_time`, `mean_exec_time`, `stddev_exec_time`, `rows`, and the buffer counters (`shared_blks_hit`, `shared_blks_read`, `temp_blks_written`), plus `total_plan_time` on newer versions.

The important discipline is to **rank by `total_exec_time`, not `mean_exec_time`** - to rank *work*, not queries. A query taking 2 ms called 4 million times an hour consumes far more of the database than a 30-second report run twice, and the 2 ms query is the one where a 30 percent improvement matters. Sorting by mean finds the slow queries; sorting by total finds the expensive workload, and they are usually different lists.

Two more habits: look at `stddev_exec_time` relative to the mean, because a high ratio means the query is sometimes fine and sometimes terrible - parameter-dependent plans (Q72) or lock waits; and take **snapshots** (a scheduled job storing the view with a timestamp, or `pg_stat_monitor`), because the cumulative counters since the last reset tell you nothing about what changed at 14:05. Comparing two snapshots is what turns it from a curiosity into an incident tool.

### Q259. Wait event analysis

PostgreSQL classifies what a backend is waiting on into classes: `LWLock` (internal lightweight locks - buffer mapping, WAL insert), `Lock` (heavyweight relation and row locks), `BufferPin`, `IO` (data file reads and writes, WAL writes), `IPC` (waiting on another process - parallel workers, sync replication), `Timeout`, `Client` (waiting for the application - `ClientRead` means the client is thinking, not the database), and `Extension`.

What each means when it dominates: **`Lock`** is application-level contention - two transactions want the same row or table, so the fix is in the transaction design (Q98, Q107), not in the hardware. **`IO`** means the working set does not fit in memory or storage is too slow - more RAM, better indexes, or faster disks. **`LWLock`** points at internal contention - `WALWrite` under a write-heavy load, `BufferMapping` with a too-small buffer pool, or `LockManager` with very high connection counts. **`BufferPin`** is rare and usually means vacuum waiting on a long-running scan. **`ClientRead`** dominating means the database is waiting for you - an idle-in-transaction problem or a chatty application, and it is a common false alarm in dashboards.

How to sample: PostgreSQL has no built-in history, so you **poll `pg_stat_activity`** every second (or use `pg_wait_sampling`, or a managed service's equivalent - RDS Performance Insights is exactly this) and aggregate the counts. The output is an "active session history" profile: at any moment, N sessions were waiting on X. That profile, plotted over time, tells you what the database was doing during an incident far more directly than any single metric, which is why Oracle and SQL Server DBAs have used wait analysis as the primary method for twenty years.

### Q260. `pg_stat_activity`

The states: `active` (executing), `idle` (connected, no transaction), **`idle in transaction`** (a transaction is open and nothing is running), `idle in transaction (aborted)`, `fastpath function call`, and `disabled`.

`idle in transaction` costs a held snapshot (blocking vacuum globally, Q93), any locks already acquired (blocking DDL and other writers, Q100), and a connection slot. It is the single most damaging state in the view, and `idle in transaction (aborted)` is worse in one respect - the transaction is dead and still holding everything until someone rolls it back.

The queries I keep saved for an incident:

```sql
-- what is running, longest first
SELECT pid, state, now()-xact_start AS xact_age, now()-query_start AS query_age,
       wait_event_type, wait_event, left(query, 120)
FROM   pg_stat_activity
WHERE  state <> 'idle' ORDER BY xact_start;

-- who is blocking whom
SELECT blocked.pid AS blocked_pid, blocked.query AS blocked_query,
       blocking.pid AS blocking_pid, blocking.query AS blocking_query,
       now() - blocked.query_start AS blocked_for
FROM   pg_stat_activity blocked
JOIN   LATERAL unnest(pg_blocking_pids(blocked.pid)) AS b(pid) ON true
JOIN   pg_stat_activity blocking ON blocking.pid = b.pid
WHERE  cardinality(pg_blocking_pids(blocked.pid)) > 0;

-- the oldest transaction in the system (the vacuum horizon)
SELECT pid, state, now()-xact_start AS age, left(query,80)
FROM   pg_stat_activity WHERE xact_start IS NOT NULL ORDER BY xact_start LIMIT 5;
```

plus `pg_cancel_backend(pid)` (cancel the statement) and `pg_terminate_backend(pid)` (kill the session) - and the discipline to record what you killed before you kill it.

### Q261. Ten metrics and their thresholds

| Metric | Alert when |
| --- | --- |
| Connection utilization (`numbackends / max_connections`) | > 80 percent sustained - the pool is misconfigured or leaking |
| Longest transaction age | > 5 minutes on OLTP - protects vacuum and DDL (Q93) |
| Longest lock wait / count of blocked sessions | any session blocked > 30 s |
| Replication lag (seconds, per replica) | > 30 s warning, > 5 min page - and any replica missing entirely |
| Replication slot retained WAL | > 10 GB, or slot inactive > 15 minutes (Q148) |
| `age(relfrozenxid)` max across tables | > 500 million - well before wraparound warnings (Q94) |
| Dead tuple ratio on the top tables, and time since last autovacuum | dead ratio > 20 percent, or no autovacuum in 24 h on a churning table |
| Disk usage - data, WAL, and temp separately | > 75 percent warning, > 85 percent page; WAL growth is the early signal for a stuck slot |
| Cache hit ratio and IO wait | hit ratio dropping *trend*, rather than an absolute threshold |
| Query latency p95/p99 by statement class, plus error rate (deadlocks, serialization failures, timeouts) | any step change versus the previous week |

Two comments I would add. First, **thresholds are less useful than change detection** for most of these - a cache hit ratio of 92 percent may be perfectly healthy, while a drop from 99 to 96 is an incident starting. Second, the top three (connections, transaction age, blocked sessions) catch the overwhelming majority of real incidents, so if the team can only maintain three alerts, those are the three.

### Q262. Mean is flat, users are complaining `[T]`

The mean hides the distribution. What you are missing:

1. **The tail.** p99 and p99.9 can rise by an order of magnitude while the mean moves a few percent, because the mean is dominated by the millions of fast queries. Users experience the tail - and a page making 20 database calls experiences the p99 with roughly 18 percent probability, so the *page's* p50 is close to the *query's* p99.
2. **Aggregation across dissimilar things.** One mean across all queries, all tenants and all endpoints averages a health check with a report. Break it down by statement class, endpoint and tenant; a single large customer having a terrible experience is invisible in the global mean.
3. **Averaging over the wrong window.** A five-minute mean smooths away a 20-second stall that timed out every request in flight. Look at maxima and at the per-second view.
4. **Errors, not latency.** Timeouts, deadlocks and serialization failures **complete quickly** - a query that fails after 100 ms *improves* your mean while breaking the user. Always plot error rate next to latency.
5. **Queueing outside the database.** The database's own view starts when it receives the query; time spent waiting for a connection (Q236) is invisible to it entirely.

What I measure instead: **percentiles by endpoint and by tenant** (p50, p95, p99, max), **error rate by class**, **the end-to-end latency from the application's perspective** including connection acquisition, and **saturation signals** (active sessions, lock waits) which lead latency rather than following it. And for the specific question "who is unhappy", nothing beats a per-tenant p99 table sorted descending.

### Q263. Leading and lagging indicators

**Leading** - these change before users notice, and are what you alert on:

- **Longest transaction age** and count of `idle in transaction` - predicts bloat, blocked DDL and vacuum stalls hours in advance.
- **Dead tuple counts and time since last autovacuum** - predicts the slow-motion degradation of table scans.
- **Transaction age (`relfrozenxid`)** - predicts wraparound weeks in advance, and there is no faster remediation, so early warning is everything.
- **Replication slot retained WAL** and **disk free trend** - predicts a hard outage with a computable time-to-impact.
- **Connection utilization** and **lock wait counts** - predict pool exhaustion.

**Lagging** - these tell you something already went wrong:

- **Cache hit ratio** - it falls *because* the working set grew or bloat spread the data out; by the time it moves, latency has already moved.
- **Replication lag** - by the time it is seconds, stale reads are already being served.
- **Checkpoint frequency** - a symptom of write volume that has already changed.
- **Query latency itself.**

The distinction matters for how you use them: leading indicators get **thresholds and pages**, because you can act before impact; lagging indicators get **dashboards and trend review**, because paging on them means you are always responding to something that already hurt someone. The classic mistake is a monitoring setup made entirely of lagging indicators, which produces alerts that are simultaneously too late and too noisy.

### Q264. Capacity planning

The method: take 12-18 months of history for each dimension, fit the growth, and project with an explicit confidence band - then plan the *action* trigger, not the failure point.

- **Storage**: table and index sizes from `pg_total_relation_size` sampled weekly, decomposed into growth from new rows versus growth from bloat (they need different responses). Project to the point where you hit 70 percent, and note that WAL and backup storage grow with *write* volume, not data volume, so they need their own curve.
- **IOPS and throughput**: from the storage layer's metrics, correlated with transaction rate. The useful derived number is **IO per transaction**, because it stays roughly constant while volume grows - so a forecast of transactions gives a forecast of IOPS, and a change in IO per transaction is a signal that the working set has stopped fitting in memory.
- **Connections**: driven by the number of application instances times pool size, so it is a *deployment* forecast, not a traffic forecast (Q235). It steps rather than curving.
- **CPU**: transactions per second times CPU per transaction, again with the second factor tracked as its own trend.

**What breaks the forecast**: any non-linearity. The working set exceeding RAM (a cliff, not a slope - IO jumps by an order of magnitude in days); a new feature or a new large customer changing the mix; a retention policy nobody implemented, so growth is unbounded by design; **bloat**, which makes storage grow faster than data; and business events - a launch, a migration of another system onto this one, a seasonal peak. Linear extrapolation of a queue-driven metric is also wrong in principle: latency follows a hockey stick as utilization approaches 1, so "we are at 60 percent CPU, we have room for 60 percent more traffic" is false.

So I forecast the resource, but I plan against the **utilization at which behavior changes**, and I re-forecast quarterly rather than treating it as an annual artefact.

### Q265. Load testing a database realistically

What most load tests get wrong, in order of impact:

1. **Data volume and cardinality.** A test database with 100,000 rows has every index in cache and every plan trivially fast. You must test at production scale, or at least at a scale where the working set exceeds RAM, because that is where the behavior changes.
2. **Distribution, not just volume.** Generated data is uniform; real data is Zipfian. One customer with 40 percent of the orders, one product in half the carts, a status column that is 99 percent 'COMPLETE'. Uniform data produces good plans and no hot rows, so the test misses both the bad plan (Q66) and the lock contention (Q107).
3. **Cache state.** Running the same 50 queries repeatedly warms everything into `shared_buffers` and reports latencies you will never see. The test must have a realistic key distribution and a realistic miss rate, and should include a **cold-start** scenario (Q178).
4. **Concurrency shape.** Testing with 10 threads when production has 500 misses lock contention, connection queueing and the throughput knee entirely (Q235). And a constant rate misses the burst behavior that actually breaks things - use open-model load generation (fixed arrival rate) rather than closed-model (fixed thread count), because the closed model self-throttles and hides the failure.
5. **Write mix and its aftermath.** Read-only tests are common because they are easy, and they miss vacuum, bloat, WAL volume, replication lag and checkpoint spikes. A realistic test must run **long enough for autovacuum to matter** - hours, not minutes.
6. **The surrounding system**: the connection pooler, the replica routing, the backup job that runs at 2 a.m., the batch job that competes for IO.

My checklist: a restored copy of production (anonymized, Q273), production-shaped key distributions, an open-model generator at the real read/write mix, a several-hour duration, and measurement of percentiles plus the database's own saturation signals - not just throughput.

### Q266. SLOs for a shared database platform `[A]`

**What I would set SLOs on**, from the consumer's point of view rather than the platform's:

- **Availability**: successful connection and query execution, measured by a synthetic probe per database plus the real error rate. 99.95 percent monthly is a reasonable starting point for a single-region managed platform, and I would state explicitly what a planned failover counts as.
- **Latency**: p99 of a *representative* trivial query (a primary-key lookup) - this measures the platform's health rather than the tenants' query quality, which is the crucial distinction. I would **not** SLO the latency of arbitrary tenant queries, because I do not control them.
- **Durability and recoverability**: RPO and RTO as explicit commitments, verified by a monthly restore drill whose measured time is published (Q153).
- **Change safety**: percentage of schema migrations completing without a lock-wait incident.

**How I keep it from becoming a bottleneck** - the platform enforces *guardrails*, not approvals:

1. **Quotas per service**: connection limits per role, `statement_timeout`, `idle_in_transaction_session_timeout`, and a storage quota with alerting. These are the contract; within them a team can do what it likes.
2. **Self-service with automated gates**: migration linting (Q256), an automated performance report on merge, and a dashboard per service showing its own top queries by total time. Teams get the data to fix their own problems without asking anyone.
3. **A clear split of responsibility, written down**: the platform owns availability, backups, patching, capacity and the guardrails; the *service team* owns its schema, its queries, its indexes and its query latency. Most disputes are about this line, so it must be explicit - including that a service exceeding its quota is throttled rather than allowed to consume the shared budget.
4. **An error budget with teeth**: when the platform's budget is spent, the platform team stops feature work; when a *tenant* consistently causes incidents, they get the choice of remediation or their own instance. That escalation path is what makes a shared platform sustainable, because the alternative - the platform team absorbing everyone's bad queries - does not scale past about five teams.
5. **Noisy-neighbor isolation** where the technology allows it: separate instances per tier, resource groups, or at minimum per-role connection caps, so one team's incident is not thirty teams' incident.

*Hook: an SLO you set for a shared platform, and the first time you had to enforce the error budget.*

---

## 16. Security, compliance and cost

### Q267. Least privilege

The roles I create, and what each may do:

- **Owner / migration role** - owns the schema objects and holds DDL rights. Used only by the migration job in CI/CD (Q251), never by the running application.
- **Application role** - `SELECT`, `INSERT`, `UPDATE`, `DELETE` on the specific tables it needs, `USAGE` on sequences, `EXECUTE` on the functions it calls. **No DDL**, no `TRUNCATE`, no superuser, not the owner of anything.
- **Read-only role** - `SELECT` only, for reporting, dashboards and the read path where you want the guarantee rather than the hint (Q231).
- **Human roles** - individual accounts (or federated logins via IAM authentication) with read-only by default and a separate, audited break-glass role for write access.

The mechanics that make it hold: `REVOKE ALL ON SCHEMA public FROM PUBLIC` and `REVOKE CREATE ON SCHEMA public FROM PUBLIC` (PostgreSQL 15 fixed the default, older versions let any user create objects); `ALTER DEFAULT PRIVILEGES FOR ROLE owner IN SCHEMA app GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_role` so new tables created by a migration are automatically usable without a manual grant - which is the step teams forget, leading to "the migration worked and the app 500s"; grants issued to **group roles** and users granted membership, so access is managed by role rather than by user; and rotation, ideally by using IAM/AD authentication so there is no long-lived password at all.

The reason the application must not have DDL: it turns an SQL injection or a compromised pod into a `DROP TABLE`, and it means a runaway ORM setting (`hibernate.hbm2ddl.auto`) can rewrite production. Both have happened to people I know.

### Q268. SQL injection beyond concatenation

Parameters cannot be used for **identifiers** or **syntax**, which is where injection survives in an ORM codebase:

- **Dynamic `ORDER BY` / column names**: `ORDER BY ?` is not a thing. The safe pattern is an **allow-list map** from an API-facing token to a validated column name and direction, never string interpolation of user input - even "sanitized" input.
- **Dynamic table or schema names** (multi-tenant `search_path` switching): same allow-list rule, plus `quote_ident()` for anything genuinely dynamic.
- **`LIKE` patterns**: the parameter is safe from injection, but `%` and `_` supplied by the user change the query's meaning and can produce a full scan - escape them (`ESCAPE '\'`) and consider length limits.
- **IN-lists**: building `IN (1,2,3)` by string concatenation is the classic. Use an array parameter - `WHERE id = ANY(?)` with a JDBC array - which is also better for plan caching.
- **JPQL/HQL**: `entityManager.createQuery("... WHERE name = '" + name + "'")` is injectable exactly like SQL, and HQL injection can reach beyond the intended entity. Always `setParameter`.
- **Native queries and `@Query(nativeQuery = true)`**: same rules; Spring's SpEL in `@Query` is another injection surface if user input reaches it.
- **JSON path expressions** and full-text `to_tsquery` input, which have their own syntax that user input can break out of - use `plainto_tsquery`/`websearch_to_tsquery` rather than `to_tsquery`.

The defenses that catch what review misses: a static analysis rule banning string concatenation in query construction, a code-review checklist item for any dynamic SQL, the least-privileged role from Q267 so injection cannot escalate, and RLS (Q269) so it cannot cross tenants.

### Q269. Row-level security

RLS attaches **policies** to a table; once `ALTER TABLE t ENABLE ROW LEVEL SECURITY` is set, every query by a non-exempt role has the policy's `USING` expression ANDed into its `WHERE` clause (for reads and for the rows visible to updates and deletes) and the `WITH CHECK` expression applied to rows being written. The typical multi-tenant policy reads a session variable:

```sql
CREATE POLICY tenant_isolation ON orders
  USING (tenant_id = current_setting('app.tenant_id')::uuid)
  WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);
```

with the application executing `SET LOCAL app.tenant_id = ...` at the start of each transaction (`SET LOCAL`, so it cannot leak through a pooled connection - Q240).

**The `BYPASSRLS` risk**: the table **owner** bypasses RLS by default unless you set `FORCE ROW LEVEL SECURITY`, and any role with the `BYPASSRLS` attribute (including superusers) ignores policies entirely. So an application connecting as the schema owner gets *no protection at all* while appearing to be protected - which is the single most common RLS misconfiguration, and an argument for the role separation in Q267.

**Performance**: the policy expression is a predicate on every query, so the tenant column must be indexed and should be the **leading column** of the relevant indexes (Q44). A policy containing a subquery or a function call is evaluated per row unless the planner can hoist it, so keep policies simple and mark helper functions `STABLE`. Policies also constrain the planner - a predicate it cannot push down can turn an index scan into a filter - so measure the important queries with RLS enabled rather than assuming it is free.

### Q270. `WHERE tenant_id = ?` in application code `[T]`

Three realistic failures:

1. **One query forgets it.** A new endpoint, a background job, a report, a data-fix script, an admin screen, a `JOIN` that filters the parent but not the child. It only takes one, and the failure is silent - the query returns *more* rows, not an error - so it surfaces as a customer seeing another customer's data.
2. **The tenant identifier is derived from something the caller controls.** A `tenantId` taken from a request parameter, a JWT claim that is not validated against the authenticated principal, or a header trusted from an internal caller. The query is perfectly written and filters by the *attacker's* chosen tenant.
3. **A path that bypasses the application's query layer entirely**: a native query, an ORM `findAll()`, a raw JDBC report, a CDC pipeline feeding a shared search index with no tenant filter at query time, a cache key that omits the tenant (so tenant B gets tenant A's cached response), or a database restore/export used for debugging.

Defense in depth, in layers:

- **Database-enforced RLS** (Q269) with `FORCE ROW LEVEL SECURITY` and a non-owner application role, so a forgotten predicate returns zero rows rather than everyone's rows. This is the layer that actually saves you.
- **The tenant established once, at the authentication boundary**, from the verified principal, and propagated implicitly (a request-scoped context, plus `SET LOCAL`) so no query author can choose it.
- **A repository base layer** that adds the predicate automatically (Hibernate `@Filter`, a Spring Data specification), so the common path cannot forget.
- **Tenant in every cache key, every index's leading column, every search document, and every message key.**
- **Tests that assert isolation**: an automated test that authenticates as tenant A and attempts every endpoint against tenant B's identifiers, and a lint that flags any repository method without a tenant predicate.

The framing to state: application-level filtering is a *correctness* mechanism, and cross-tenant leakage is a *security* event - so it needs a control that fails closed, which only the database can provide.

### Q271. Encryption at rest, in transit, at the column level

- **In transit (TLS)** protects against network interception and man-in-the-middle. It is table stakes, and the detail that matters is `sslmode`: `require` encrypts but does **not** verify the server, so it does not stop MITM; `verify-full` checks the certificate and hostname and is the only setting that provides the guarantee people assume they have.
- **At rest (disk/volume encryption, TDE)** protects against **physical media** compromise - a stolen disk, a decommissioned drive, a snapshot copied out of the account without the key. It is transparent to queries, costs a few percent CPU, and is usually mandatory for compliance.
- **Column-level encryption** protects the value from anyone with database access - a DBA, a support engineer with a read-only role, an SQL injection, a leaked backup with its key.

**What TDE does not protect against** is the important part, and it is a good interview answer: it protects the *file*, not the *connection or the query*. Anyone who can authenticate to the database - or exploit an injection, or read a memory dump, or obtain a logical `pg_dump` - gets plaintext, because the engine decrypts transparently for every authorized reader. It also does nothing against a compromised application, an over-privileged role, or an insider with legitimate access. So TDE satisfies a compliance control about media, and column encryption is what satisfies a threat model about people.

The layering I would apply: TLS `verify-full` everywhere, volume encryption always (it is nearly free with managed services), and column encryption reserved for the small set of fields where the threat model justifies the cost - card data, government identifiers, health data, credentials.

### Q272. Key management and searchable encryption

Keys must not live where the ciphertext lives. The standard structure is **envelope encryption**: a data encryption key (DEK) encrypts the column values, and the DEK is itself encrypted by a key encryption key (KEK) held in a KMS or HSM. The application fetches and caches the decrypted DEK in memory; the KMS enforces access policy and logs every use; **rotation** of the KEK is cheap (re-encrypt the DEK only), while rotation of the DEK requires re-encrypting the data, so you version the DEK and store the version alongside each value so old and new can coexist.

Then the hard part: **encrypted columns are not searchable**, because a good cipher is randomized, so the same plaintext yields different ciphertext each time. Equality search, uniqueness, range queries, sorting and joins all stop working.

The options and their costs:

- **Deterministic encryption** - the same plaintext always yields the same ciphertext, so equality lookups and uniqueness work. The cost is that it **leaks the equality pattern**: an attacker with the ciphertext sees which rows share a value, and frequency analysis on a low-cardinality column (gender, city, disease code) recovers the plaintext without any key.
- **Blind indexing** - store a keyed HMAC of the normalized plaintext in a separate indexed column for equality lookups, with the actual value randomly encrypted. Same equality leakage in principle, but you control the granularity (truncate the HMAC to create deliberate collisions and reduce leakage), and the encryption itself stays randomized.
- **Order-preserving / order-revealing encryption** enables range queries and leaks the ordering, which is usually enough to reconstruct the data. I would not use it.
- **Client-side field level encryption** (MongoDB CSFLE, AWS DB Encryption SDK) packages the above with proper key handling.

So the honest position: encrypt what needs it, accept that those columns lose query capability, keep a separate searchable projection only where the leakage is acceptable, and push back on "encrypt everything" because it converts a database into a key-value store with extra steps.

### Q273. PII handling

**Classification first**: every column tagged (public, internal, personal, sensitive-personal, financial) in a catalog that lives with the schema - a comment on the column, a YAML file in the repo, or a data catalog tool. Untagged is not "safe", it is "unreviewed", and a lint should fail a migration that adds a column with no classification. This sounds bureaucratic and it is the thing that makes every later control possible, because you cannot mask, retain or delete what you have not identified.

**Lower environments**: production data does not go to a laptop. The pipeline is a restore into a locked-down environment where an **anonymization job** runs before any developer access - deterministic pseudonymization for values that must stay join-able across tables (the same customer id maps to the same fake id everywhere), format-preserving fakes for names, emails and phone numbers so validation still passes, nulling or generalization for free-text fields (which are the worst offenders because PII hides in them), and *deletion* of the columns nobody needs. The alternative, and often the better one, is **synthetic data** generated to match the production distribution (Q265), which has no residual risk at all.

**Tokenization** for the highest-sensitivity fields - card numbers, national identifiers: the real value lives in a separate vault with its own access control and audit trail, and the main database holds only a token. This shrinks the compliance scope dramatically, because the systems holding tokens are out of scope for the standard that governs the real values.

**The controls that keep it honest**: no direct human access to production data by default (queries go through an audited tool that logs who ran what), export and `COPY` privileges restricted and alerted on, and a periodic scan for PII appearing in places it should not - logs, error messages, support tickets, the search index, and lower environments.

### Q274. Auditing

Three mechanisms:

| | Completeness | Performance | Tamper resistance |
| --- | --- | --- | --- |
| **Extension / native audit** (`pgaudit`, Oracle Unified Audit, SQL Server Audit) | high - can capture every statement including reads, DDL and privileged actions | moderate - log volume is the cost, and full statement logging on a hot path is expensive | good if shipped off-host immediately; local files are editable by anyone with host access |
| **Trigger-based audit tables** | only what the triggers cover - DML on audited tables, no reads, and bypassable by `TRUNCATE` or by disabling the trigger | worst - a write per write, inside the transaction, doubling write volume and lock duration | poor - the audit rows live in the same database the actor can access |
| **Log-based capture (CDC)** | complete for data changes (it reads the WAL, so nothing can bypass it) but no reads and no failed attempts | best - asynchronous, no impact on the transaction path | good - the sink is a separate system |

What I actually build depends on what the audit is *for*: **regulatory access logging** ("who read this record") needs statement-level auditing, because CDC cannot see reads; **data lineage and change history** ("what did this record look like last March") is better served by CDC into an append-only store, or by a temporal table design (Q14) which makes history a first-class part of the model; **security forensics** needs both, plus authentication logs.

The properties I insist on regardless of mechanism: the audit trail is written to a **separate system** with different credentials (so compromising the database does not let you edit the evidence), it is **append-only** with retention enforced by the storage rather than by policy, it captures the **application user** and not just the database role (which means propagating the end-user identity, typically via `SET LOCAL application_name` or a session variable), and it is **monitored** - an audit log nobody queries is a compliance artefact, not a control.

### Q275. GDPR erasure against append-only stores `[T]`

The reconciliation is that the regulation requires the data to become **inaccessible and unusable**, not that every byte is physically overwritten everywhere, and it explicitly allows for technical feasibility and for retention required by other legal obligations (tax, anti-money-laundering). That gives four practical mechanisms:

1. **Crypto-shredding.** Encrypt each subject's personal data with a per-subject key; erasure is deleting the key. The ciphertext remains in the event store, the backups and the warehouse, and is permanently unreadable. This is the standard answer for immutable stores and the one I would design for from the start, because retrofitting it is expensive.
2. **Tombstone plus compaction** for log-based systems: publish a deletion event, and rely on the store's compaction (Kafka log compaction with a null value for the key, or a rewrite of the affected partitions in an Iceberg/Delta table) to remove the historical payloads. Requires the personal data to be keyed by subject, which is a modeling decision made years earlier.
3. **Separate the personal data from the event.** Events carry a subject *reference*; the personal attributes live in a mutable profile store that can genuinely be deleted. The event history then remains intact and analytically useful while containing no personal data - this is the cleanest design and the one I would push for.
4. **Retain what the law requires**, minimized and access-restricted, with the retention basis documented. An invoice is not erasable; a marketing profile is.

**Backups** are handled by policy rather than by surgery: you do not restore a backup to delete one person. The accepted approach is a documented, bounded backup retention window (say 35 days) after which the data ages out naturally, plus a **suppression list** applied on any restore so the erased subject is re-erased before the restored system serves traffic. **Warehouses and lakes** are handled by propagating the deletion request through the same pipeline that loaded the data, which requires the subject key to be present and tracked - which comes back to classification (Q273).

The point I would make in an interview: this is a **design-time** problem. A system that stored personal data inline in immutable events, unkeyed and unencrypted, cannot satisfy an erasure request without rewriting history, and no clever runtime trick fixes it.

### Q276. Managed database cost shape

| | RDS PostgreSQL | Aurora PostgreSQL | DynamoDB |
| --- | --- | --- | --- |
| Compute | per instance-hour, whether idle or not | per instance-hour (or ACU-hour for Serverless v2) | none - it is in the request price |
| Storage | provisioned volume, paid for what you allocate | pay for what you *use*, grows automatically | per GB stored |
| IO | included in gp3 up to a baseline; provisioned IOPS extra | **per million IO requests** (unless on I/O-Optimized) | included in request units |
| Requests | none | none | per read/write unit (Q208) |
| Backup | free up to the size of the database, then per GB | same | per GB of continuous backup or on-demand |
| Transfer | cross-AZ and cross-region charged | same, plus cross-region replication | same |

The ones that surprise people: **cross-AZ data transfer** between the application and a database in another AZ, which is invisible in the database bill and can rival it; **Aurora's per-IO charge**, which makes a badly indexed workload (lots of buffer misses) dramatically more expensive than the same workload on RDS with gp3 - and which is why the I/O-Optimized configuration exists once IO is more than about 25 percent of the bill; **backup storage** on a database with high churn, because incremental backups of a bloated, constantly rewritten table are much larger than the database; **snapshot retention** accumulating quietly; **provisioned IOPS** left at a level set during a one-off migration; and **DynamoDB GSIs**, each of which duplicates the write cost of every item it indexes.

### Q277. Right-sizing

**Signals I use**: sustained CPU utilization (below 20-30 percent at peak means over-provisioned, but only if memory is also comfortable), the **cache hit ratio and IO pattern** (the real constraint on a database is usually whether the working set fits in RAM, not CPU), connection count against the instance's limit, IOPS consumed versus provisioned, and the storage allocated versus used. I look at the **peak** of a full business cycle, not the average, and I check whether the peak is driven by a batch job that could move.

**The risk of scaling down** is the cliff: a database is fine at 40 GB of RAM and pathological at 32 GB, because the working set no longer fits and read IO jumps by an order of magnitude in a single step. So a downsize is not a linear bet - it needs the working-set estimate (`pg_buffercache` or simply the size of the hot tables and indexes), a change during a low-traffic window, and a fast rollback path. Instance-class changes also cost a failover, so they are not free even when they are correct.

**The three cheapest wins before changing instance class**:

1. **Delete data.** Retention policies, dropped unused indexes (Q58), archived cold partitions (Q162), and TOASTed blobs moved to object storage. This reduces storage, backup, IO and memory pressure at once, and it is the only intervention that improves performance *and* cost.
2. **Fix the top queries.** The top five by total time are usually 50-80 percent of the load (Q258); halving them is equivalent to halving the instance, and it also reduces the Aurora IO bill directly.
3. **Buy the commitment, not the capacity.** Reserved instances or savings plans on the *current* size give 30-50 percent immediately with no technical risk - and they should be bought only after steps 1 and 2, so you do not reserve capacity you are about to stop needing.

Honourable mentions: moving non-production instances to a schedule (stopped overnight and at weekends is typically a 60 percent saving on those), gp2 to gp3, and switching a spiky, low-average workload to Serverless v2.

### Q278. Retention and archival `[A]`

**Who decides**: not engineering. Retention is a business and legal decision with three inputs - the **legal minimum** (tax, financial and sector regulation), the **legal maximum** (data protection principles say personal data may not be kept longer than necessary, so an indefinite default is itself a violation), and the **business value** of old data. My job is to make the cost visible, propose a default, and get an accountable owner to sign it per data domain. In practice I would drive it as a table: data domain, owner, legal basis, retention period, deletion mechanism, and the date it was last reviewed.

**How to enforce it technically** - policy without a mechanism is a document that ages badly:

- **Partition by time and drop partitions** (Q162). This is the mechanism that makes retention nearly free: a drop is instant, generates no bloat, no WAL burst and no replication lag, where a `DELETE` of the same data is hours of work and a bloated table.
- **A tiering path before deletion**: hot partitions in the database, warm ones detached and exported to Parquet in object storage (queryable by Athena/Trino when someone occasionally needs them), cold ones in an archive storage class, then deleted. Most "we must keep everything" requirements are satisfied by the middle tier at a tenth of the cost.
- **TTL where the store supports it** (DynamoDB, MongoDB, Cassandra, Redis) - noting the caveats about deletion delay and tombstones (Q203, Q210).
- **Automation with alerting**: the job that creates future partitions and drops expired ones runs on a schedule and pages if it fails, because a missing future partition is an outage (Q162) and a missing drop is a silent cost increase.
- **Backups and downstream copies** carry their own retention, and the policy must name them explicitly - otherwise data is "deleted" from the primary and lives for years in snapshots and the warehouse (Q275).

**How retention interacts with partitioning**: they should be designed together. The partition key must be the column the retention rule is expressed in (usually the event or creation timestamp, sometimes a business close date), and the partition granularity should divide the retention period sensibly - monthly partitions for a 7-year retention is 84 partitions, which is manageable; daily partitions for the same period is 2,555, which is not. Where two data domains in one table have different retention periods, that is a signal to split them. And where the retention rule depends on something *mutable* (delete 90 days after the account closes), partitioning by creation time does not help and you need either a periodic archival job keyed on the real predicate or a redesign that makes the retention dimension immutable.

*Hook: a retention policy you introduced, and what it did to storage cost and query performance.*

---

## 17. Data architecture design exercises and leadership

Q279-284 are worked as full CIDER design exercises in [scenario-questions.md](scenario-questions.md), Part B. Read the question, spend five minutes designing out loud, and only then compare.

| Question | Worked as |
| --- | --- |
| Q279 multi-tenant SaaS data layer at 5,000 tenants | S11 |
| Q280 audit and event store, 50k writes/sec, seven-year retention | S12 |
| Q281 global read-heavy product catalogue | S13 |
| Q282 analytics read path off the OLTP primary | S14 |
| Q283 data separation for extracting an orders service | S15 |
| Q284 transactional bookings plus recommendations over the same entities | S16 |

### Q285-290. Story questions

No model answer is scripted for these, and you should be suspicious of any that is - the interviewer is assessing whether *you* have operated a data layer, and a polished generic answer is the clearest possible signal that you have not.

Use **STAR-L** (Situation, Task, Action, Result, **Learning**), defined in [../01-java/README.md](../01-java/README.md). Two or three minutes each. For data stories specifically, the Result must carry a **number** - a latency, a size, a cost, an RTO, a row count, a percentage - because data work is measurable and a story without a measurement reads as second-hand.

The ten stories to prepare, and which of Q285-290 each one serves, are listed in [README.md](README.md) under "Your data story bank". Prepare them written down, then rehearse out loud; the compression from a page to two minutes is where the story becomes good.
