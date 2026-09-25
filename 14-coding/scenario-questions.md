# Scenario Questions

Twenty scenarios: ten code-level incidents, six design-and-implement walkthroughs, four leadership-around-code situations. The questions in [questions.md](questions.md) establish that you know the pattern; these establish that you have shipped it, broken it, or made other people better at it.

Work Part A and Part B **out loud** for five to ten minutes before reading the answer. The answers are longer than you should speak; compress each to a two or three minute spoken version.

**Part A** uses **CIDER**: Clarify, Isolate, Decide, Execute, Reflect. Say the clarifying questions even when you then answer them yourself.

**Part B** uses the same spine for a 45–60 minute implement: clarify the API and the invariant, isolate the hard part, decide the structure, execute in a sequence you can defend, reflect on what you would add after the round. Part B maps to Q239 and Q251-Q255.

**Part C** has no scripted answer. Prepare them with real detail using STAR-L, defined in [../01-java/README.md](../01-java/README.md).

---

## Part A - Code-level incidents

### S1. HashMap get is forty microseconds (Q44)

> A payment-lookup map that used to return in tens of nanoseconds is now at 40 µs at p99, on a box that is otherwise idle. The map holds a few hundred thousand keys. CPU is in Java, not in GC. A recent change added a new key type.

**Clarify.** What is the key type, and did `hashCode` / `equals` change? Is the slowness all keys or a subset? Did the map grow, or did the key cardinality stay put while latency moved? Are we looking at `get`, `put`, or `rehash`? Can I take a JFR of the hot method? Is this one tenant's keys?

**Isolate.** Four causes, cheapest first:

1. **Resize on the hot path.** A `put` storm can rehash. JFR / a breakpoint on `resize` tells you in a minute. Unlikely if the map is already at steady size.
2. **The key is mutating** (Q33) so `get` misses and the caller retries. That looks like *wrong answers*, not slow answers, unless the retry is the 40 µs.
3. **GC / safepoint**, already ruled out by "CPU is in Java, idle box", but confirm with a JFR allocation sample.
4. **Hash quality.** A constant or low-entropy `hashCode` puts every key in one bin. Java 8+ treeifies a bin of comparable keys; if the key is *not* `Comparable`, the bin stays a list and `get` is O(n). 200k keys in one list is 40 µs-shaped.

**Decide.** Read the new key's `hashCode`. If it is `return 0` or `return type.ordinal()` on a type with three values, that is the incident. Fix the hash to include the discriminating fields, make the key a `record` of immutables, and if the domain is dense replace the map with an array (Q37).

**Execute.**

1. Confirm with a histogram of `key.hashCode()` on a heap dump or a one-off log: a handful of distinct hashes is the smoking gun.
2. Patch `hashCode`/`equals` together (Q208), add a unit test that 10k distinct keys land in many bins (`HashMap` size versus a walk of table length if you must).
3. Roll forward; do not "tune load factor".
4. Add the assertion you wished you had: a startup canary that inserts N keys and fails if `get` exceeds a microsecond budget in a unit test.

**Reflect.** A `HashMap` is O(1) only if the hash is. The review comment that would have prevented this is "new key type: show me `hashCode`". The production lesson is that a 40 µs `get` is a *design* bug, not a capacity problem.

> Hook: a lookup that died on a key whose hash was the tenant id, and every request for that tenant shared one bin.

### S2. Two-lock cache deadlock (Q232)

> A hand-rolled cache takes a map lock, then a per-entry lock on load. Overnight a deploy added an `invalidateAll` that takes each entry lock and then the map lock to remove. Two threads have been stuck for thirty minutes. The JVM is otherwise healthy.

**Clarify.** Can I take a thread dump? What are the two stacks holding? Is this the first time `invalidateAll` ran in production (a nightly job)? Is there a third lock (the load's remote client)? How many threads - two, or a pile-up behind them?

**Isolate.** Thread dump is the whole incident. You expect:

- Thread A: `cacheMap.lock` → waiting on `entry.lock` (in `get` / load).
- Thread B: `entry.lock` → waiting on `cacheMap.lock` (in `invalidateAll`).

That is Q227 in production: opposite order. A third lock on the remote load would be a bonus, not required.

**Decide.** Do not "add a timeout and retry" as the fix; that hides the inversion. Replace the two-lock protocol with `ConcurrentHashMap.compute` (per-key serialization, no outer lock) or with Caffeine. If you must keep two locks, one global order, documented, and `invalidateAll` follows it.

**Execute.**

1. Thread dump, paste the two stacks into the ticket, declare a deadlock, bounce the node if it is still wedged.
2. Feature-flag `invalidateAll` off so the remaining nodes stay up.
3. Rewrite: `compute` for load, `keySet` snapshot for invalidate, no nested locks.
4. A regression test that runs `get` and `invalidateAll` in a tight race for ten seconds with a timeout - the old code deadlocks, the new one does not.

**Reflect.** The deploy was a lock-order change, not a cache-feature change. Two locks is a protocol; it belongs in the review of *both* methods. S2 is why Q232 is an `[A]`.

> Hook: a cache invalidation that only ran at 02:00, so the deadlock waited for the first night.

### S3. Unbounded queue filled the heap (Q233)

> A worker pool's old-gen filled in twelve minutes after a downstream outage. Heap dump: millions of `Runnable`s sitting in a `LinkedBlockingQueue`. The pool's `maximumPoolSize` is 32. The submitter is an HTTP thread.

**Clarify.** Which executor factory? What is the queue type and capacity? What is the rejected-execution policy? Did the downstream timeout, or did it hang past the HTTP timeout? How many tasks were *supposed* to be in flight?

**Isolate.** `new LinkedBlockingQueue<>()` has capacity `Integer.MAX_VALUE`. Combined with a `ThreadPoolExecutor`, `maximumPoolSize` is never reached because new threads are only created when the *queue* is full. Tasks pile in the queue; the 32 workers sit on the hung downstream; the heap is the queue. This is Q223 / Q224 / Q233 on one board.

**Decide.** Bound the queue to a number you can defend (seconds of work × workers), pick an observable rejection policy (`Abort` or `CallerRuns`), and make the HTTP layer fail the request when submit fails. Do not raise the heap.

**Execute.**

1. Shed load: refuse new submits, drain what you can, bounce if the heap is already dying.
2. Replace the queue with `ArrayBlockingQueue<>(bound)`, policy `AbortPolicy` or `CallerRunsPolicy`.
3. Metric: queue depth, reject count, and a page on reject.
4. The downstream gets a timeout that is *shorter* than the HTTP timeout, so workers return.

**Reflect.** An unbounded queue is an unbounded heap. `maximumPoolSize` on an unbounded queue is documentation, not a limit. The review comment is one sentence: "show me the bound and the reject path".

> Hook: a "temporary" `newCachedThreadPool` that became the payment worker and OOM'd a region.

### S4. Rounding bug in money arithmetic (Q196)

> A nightly reconciliation is off by a few rupees on a few thousand invoices, never more than a rupee each, always after a tax line that uses a percentage. The service has been in production for a year. A new tax rate of 0.1% shipped yesterday.

**Clarify.** What type is the amount - `double`, `float`, `BigDecimal`, integer cents? How is the percentage applied? Which `RoundingMode`, and is it the same on every line? Can I reproduce on a single invoice? Is the drift always the same sign?

**Isolate.** `0.1` percent in a `double`, or `new BigDecimal(0.1)`, reproduces IEEE error (Q196). A year of *nice* rates (5%, 18%) hid it; 0.1% is the first rate that cannot be represented. Alternative: `BigDecimal.equals` comparing scale-2 to scale-4 and taking the wrong branch. Alternative: `HALF_UP` on one side and `HALF_EVEN` on the other.

**Decide.** Integer minor units or `BigDecimal` constructed from `String` / integer, one `RoundingMode` for the product, one scale at the money boundary. The tax line is `amount.multiply(rate).setScale(2, mode)`.

**Execute.**

1. Reproduce with the failing invoice in a unit test that currently fails (Q201).
2. Fix the type; do not "add 0.005 and hope".
3. Re-run last night's file; publish the delta; decide with finance whether you correct issued invoices.
4. A static-analysis / review rule: no `double` in the `money` package, no `new BigDecimal(double)`.

**Reflect.** The incident waited for a rate that is not a dyadic rational. A million-add loop in CI would have caught the `double` path in a minute. Q200 (`abs(MIN_VALUE)`) is the sibling you mention if they ask "what else about numeric types".

> Hook: a tax change to 0.1% that made a year-old `double` visible as rupees.

### S5. Off-by-one that only fails on the boundary (Q20)

> A "longest unique-character window" helper is used to size a buffer. It passed 40 unit tests. Production data of a 1-character string and a string of all the same character both allocate a 0-length buffer and throw. Mixed strings are fine.

**Clarify.** What is the exact function and the documented contract for `""`, `"a"`, `"aaaa"`? Is the return `r - l` or `r - l + 1`? Is `l` moved to `last[c]` or `last[c] + 1`? Can I see the tests that passed?

**Isolate.** The classic Q20 bug: `best = r - l` (a fencepost) or `l = last[c]` (the previous occurrence stays *inside* the window). All-unique of length 1 and all-same are the two cases a random-string test never hits. The 40 tests were long mixed fixtures.

**Decide.** Fix the invariant: `[l, r]` inclusive, unique, `best = r - l + 1`, and `l = last[c] + 1` when `last[c] >= l`. Add the two cases plus `""`.

**Execute.**

1. Characterization of current (wrong) output on `"a"` and `"aaaa"` so the ticket has a number.
2. Fix, add the three tests, run the production allocator against them.
3. Hunt every other window in the same file for `r - l` without the `+ 1`.

**Reflect.** Boundary tests are not polish; they are the tests that find off-by-ones. A property test ("window never contains a duplicate, length is maximal") would have failed on `"a"` immediately.

> Hook: a buffer sized by a window helper that returned 0 for every one-character tenant id.

### S6. A stream mutates shared state (Q207)

> A pairing session "cleaned up" a loop into a parallel stream that increments a `HashMap` frequency table in `forEach`. Unit tests pass. Production, under load, shows lost counts and the occasional `ConcurrentModificationException` in a log that nobody pages on.

**Clarify.** Is the stream `parallel()`? Is the map a `HashMap` or a `ConcurrentHashMap`? Is anything else iterating the map while the stream runs? Did the tests run with `parallel` disabled (single-core CI)? What is the downstream reader?

**Isolate.** A `HashMap` is not a concurrent structure. `parallel().forEach(k -> map.merge(k, 1, Integer::sum))` is a data race; `merge` on `HashMap` is not atomic across threads. CME is a concurrent structural modification during a resize. Tests passed because CI ran sequential or never collided.

**Decide.** Sequential stream or, better, a loop (Q206). If you meant parallel, `Collectors.groupingByConcurrent` / `toConcurrentMap`, or a `LongAdder` per key. Do not "synchronize the `forEach`".

**Execute.**

1. Revert to the loop on the same night; it is the safe diff.
2. A test that uses a 16-thread pool and a small key set until the old code loses counts; the new code does not.
3. Review note: parallel streams are banned on shared mutable state. Q207 is now a wiki example.

**Reflect.** `toList()` on the *output* does not snapshot the *source* and does not make a side-effecting `forEach` safe. Parallel is a concurrency decision, not a style one.

> Hook: a "Java 8 cleanup" that lost one in a thousand increments and only on the large box.

### S7. Comparator subtraction overflow (Q55)

> A sort of account ids started throwing `IllegalArgumentException: Comparison method violates its general contract` after a migration imported ids near `Integer.MIN_VALUE`. The comparator is `return a.id - b.id`. It has been in the codebase for eight years.

**Clarify.** Are the ids signed 32-bit? Did the imported file actually contain `MIN_VALUE` / very large positives? Is this `Arrays.sort` on objects (TimSort) or a `TreeSet`? Does the same comparator serve as `equals`?

**Isolate.** `a - b` overflows (Q55, Q186). TimSort notices a contract break and throws; a naive n² sort would have silently misordered. Eight years of ids in `0..1e8` never overflowed. The migration did.

**Decide.** `Integer.compare(a.id, b.id)` or `Comparator.comparingInt(Account::id)`. If ids are really unsigned 32-bit, `Integer.compareUnsigned`. Do not catch the IAE and "sort differently".

**Execute.**

1. Patch the comparator; add a test `compare(MIN_VALUE, MAX_VALUE) < 0`.
2. Hunt `return a - b` in the same module (it travels in packs).
3. Re-run the import.

**Reflect.** A comparator that is "obvious" for eight years is still wrong. The contract is mathematical, not cultural. ErrorProne / a custom check for `compare` methods that subtract is the permanent fix.

> Hook: a data import that first exercised `MIN_VALUE` and took down a nightly sort.

### S8. Binary-search mid overflow (Q48)

> A search over a memory-mapped `int[]` of more than a billion elements returns wrong indices on the upper half, never throws. The probe is `int mid = (lo + hi) / 2`. Tests used arrays of a few thousand.

**Clarify.** What is `a.length`? Are `lo` and `hi` both in the upper two billion? Is the array a real `int[]` (max length `Integer.MAX_VALUE - n`) or a long-indexed structure being squeezed into `int`? Can I print `lo`, `hi`, `mid` on a failing probe?

**Isolate.** `lo + hi` overflows a signed `int` and becomes negative; `/ 2` is a negative `mid`; the search then does something depending on how you index (Q48). Small tests never add two large indices. If this is a `long`-addressed file (Q59) stuffed into `int` mid, that is the same family.

**Decide.** `mid = lo + (hi - lo) / 2`, or do the arithmetic in `long` and cast. Add a test where `lo` and `hi` are both `> Integer.MAX_VALUE / 2`.

**Execute.**

1. Fix the mid. This is a one-line change and a one-line test.
2. Grep the repo for `(lo + hi) / 2` and `(left + right) >> 1`.
3. If the structure is a 2 TiB file, stop pretending the index is `int` (Q59).

**Reflect.** Overflow-safe mid is a habit, not an optimization. The test you add is more valuable than the fix; the next person will copy the first binary search they see.

> Hook: a search that "worked in staging" because staging held 40 million rows, not 1.1 billion.

### S9. Mutating a HashSet key (Q33)

> A `Set<Session>` is the membership of an in-memory room. After a "harmless" `session.setLastSeen(now)` the room sometimes cannot `remove` the session on disconnect. `size()` grows for the life of the process. Heap dump shows sessions that no client holds.

**Clarify.** Does `Session.hashCode` / `equals` include `lastSeen`? Is the set a `HashSet`? Is `lastSeen` updated while the object is in the set? Can I `contains` the same reference after the update?

**Isolate.** Q33: the entry sits in the old bucket. `remove(session)` hashes to a new bucket and misses. Iteration still sees it; `size` grows. This is a leak, not a disconnect bug.

**Decide.** Keys are immutable in the fields that `equals`/`hashCode` read. `lastSeen` does not belong in the identity. Use a `record SessionId` as the key, or remove-then-add if you truly must rehash (you do not).

**Execute.**

1. Confirm: `System.identityHashCode` of a "stuck" session versus `hashCode()` before and after `setLastSeen`.
2. Drop `lastSeen` from `equals`/`hashCode`; add a test that mutates and still `remove`s.
3. Walk other in-set mutations (`setStatus`, `setName`).

**Reflect.** A mutable key is a memory leak with a long fuse. The review rule is the same as `01-java` Q2: if it is a map or set key, it is a `record` of immutables.

> Hook: a chat room whose `HashSet` retained every session that had ever updated a timestamp.

### S10. Virtual threads pinned on a synchronized JDBC wrapper (Q225)

> A migration from a 200-thread pool to virtual threads *increased* tail latency and the platform thread count stayed near 200. Thread dump: hundreds of virtual threads in `RUNNING` inside `synchronized (this)` of a connection wrapper, and a matching set of carrier threads stuck with them. The DB pool is size 20.

**Clarify.** Are the virtual threads blocking in `synchronized` or in JNI? What is the DB pool size? Is there a semaphore in front of it? What was the old pool size, and what was it *for* (CPU or waiting)? Can I see a JFR "VirtualThreadPinned" event?

**Isolate.** Two stacked problems. Pinning (Q225): `synchronized` around a blocking JDBC call keeps the carrier. Pool mismatch (Q234): 100k virtual threads stampede 20 connections; the old 200-thread pool *was* the concurrency cap and nobody replaced it with a semaphore.

**Decide.** Put a `Semaphore(20)` (or the pool's own checkout) in front of JDBC. Replace the `synchronized` wrapper with a `ReentrantLock` if the critical section still blocks, or shrink the `synchronized` so it does not include the I/O. Do not "add more platform threads".

**Execute.**

1. Roll back the migration if production is on fire; this is a behaviour change, not a flag-flip.
2. Semaphore + pin hunt; JFR `VirtualThreadPinned` as a CI canary on the request path.
3. Re-ship with the cap; measure p99 and carrier-thread count *before* celebrating.

**Reflect.** Virtual threads delete the pool that existed to park waiters. They do not delete the pool that exists to protect a 20-connection database. Pinning is a separate, smaller, real bug. Measure first (Q234).

> Hook: a virtual-thread cutover that kept 200 carriers busy because the JDBC wrapper still used `synchronized`.

---

## Part B - Design and implement

### S11. Bounded blocking queue (Q239)

> Forty-five minutes. Production quality. Multiple producers, multiple consumers. Capacity N. `put` blocks when full, `take` blocks when empty, `offer` / `poll` with timeout. The interviewer will ask about interrupt policy and a single wait-set.

**Clarify.** Capacity is an argument, `> 0`. Nulls: reject (`Objects.requireNonNull`) - that is the `ArrayBlockingQueue` contract. Interrupt: `put`/`take` throw `InterruptedException` and leave the structure unchanged. Fairness: not required unless they ask; say "unfair, I can switch to a fair lock". Timeout units: `TimeUnit`.

**Isolate.** The hard part is not the ring (Q86). It is two conditions (not-full, not-empty) on one lock, and not using `notify` on a shared wait-set so a producer wakes a producer. Interrupt and timeout must not drop an item or double-take.

**Decide.** `ReentrantLock` + `notFull` + `notEmpty` `Condition`s, a circular `Object[]`, a count. `notifyAll` on a single monitor is correct and simpler if time is short; two conditions is the production shape. State the invariant: `0 <= n <= cap`, `n == 0` iff empty, `n == cap` iff full.

**Execute.**

```java
final class BoundedQueue<T> {
    private final Object[] a;
    private int h, t, n;
    private final ReentrantLock lock = new ReentrantLock();
    private final Condition notEmpty = lock.newCondition();
    private final Condition notFull = lock.newCondition();

    BoundedQueue(int cap) {
        if (cap <= 0) throw new IllegalArgumentException("cap");
        a = new Object[cap];
    }

    void put(T x) throws InterruptedException {
        Objects.requireNonNull(x);
        lock.lockInterruptibly();
        try {
            while (n == a.length) notFull.await();
            a[t] = x; t = (t + 1) % a.length; n++;
            notEmpty.signal();
        } finally { lock.unlock(); }
    }

    @SuppressWarnings("unchecked")
    T take() throws InterruptedException {
        lock.lockInterruptibly();
        try {
            while (n == 0) notEmpty.await();
            T x = (T) a[h]; a[h] = null; h = (h + 1) % a.length; n--;
            notFull.signal();
            return x;
        } finally { lock.unlock(); }
    }
}
```

`offer`/`poll` use `awaitNanos`. Tests: one producer one consumer; N producers N consumers on `cap=1`; interrupt during `put` when full; reject null. Complexity: O(1) per op.

**Reflect.** A single `synchronized` + `notifyAll` (Q219) is a legal 20-minute version; say what you would add (two conditions, fairness, `drainTo`). Do not write a linked list - the bound is the point. After the round: JFR, a metric on wait time, and a poison-pill story for shutdown.

> Hook: the queue you wished S3 had been.

### S12. LRU cache (Q251)

> Sixty minutes. `get` / `put` in O(1), capacity N, optional TTL, a thread-safety contract you will defend. They will ask why you did not use `LinkedHashMap`.

**Clarify.** Capacity 0: legal (every `put` evicts immediately) or rejected - pick and say. Null keys / values: reject. `get` of missing: `null` or `Optional` - pick `null` to match `Map`, or `Optional` if this is a new API (Q250). TTL: lazy on access plus a sample, unless they want a janitor. Concurrency: one lock for the round; "I would use Caffeine in the repo".

**Isolate.** The structure is Q101 / Q243: map + doubly linked list + dummy ends. The hard parts are `put` on an existing key (update + move, no evict unless size exceeded), `get` that does not leak a node, and the size invariant after every path. `LinkedHashMap` *is* enough for single-thread LRU (Q104); you write the list because they want to see `moveToFront` and because TTL / weighted size / concurrency will not fit in `removeEldestEntry`.

**Decide.** `record` is the wrong node (it is mutable). A static inner `Node` with `prev`/`next`. One `ReentrantLock`. Invariant: `map.size() == listLength`, head is newest, tail is oldest.

**Execute.** Write, in this order, so each step is testable: node + dummies; `moveToFront`; `evictTail`; `get`; `put`; lock wrapper; then TTL field if time. Tests: evict oldest; `put` existing does not grow; `get` refreshes; capacity 1; capacity 0 if you allowed it.

**Reflect.** The follow-up ladder: LFU (Q244), weighted entries, `computeIfAbsent` without double load (Q226), distributed LRU (that is `04-system-design`, refuse to fake it). Weaknesses you name: one lock, lazy TTL, no metrics.

> Hook: an auth-token cache whose `LinkedHashMap` was "good enough" until TTL and a second writer showed up.

### S13. Rate limiter (Q252)

> Sixty minutes, production quality. Per-key limit of N events per window W, in one process, then "what changes when this is six nodes". They will ask token bucket versus sliding window.

**Clarify.** Per-key or global? Allow a burst of N at window start (token bucket, Q241) or "no more than N in any W" (sliding log / sliding window, Q242)? Fail-open or fail-closed when the clock jumps? Return type: boolean, or a `Result(allowed, retryAfter)`? Key cardinality?

**Isolate.** The in-process object is small. The hard part is the clock (`nanoTime` versus wall), the memory of per-key state (a map that must evict stale keys), and the honest distributed sentence: this limiter is *not* global.

**Decide.** For "API quota, one node": token bucket, `ConcurrentHashMap<Key, Bucket>`, lazy refill, a sample eviction of idle keys. For "compliance, any W": sliding window counter (two buckets) or a log (Q242). Distributed: Redis `INCR` + `PEXPIRE`, or a token-bucket in Redis, and accept ±1 window of error; or a central service. Do not "put a HashMap in Redis".

**Execute.** Write `tryAcquire(key, n)` with Q241's refill. Document: not distributed, not fair, clock is monotonic. Tests: N+1st fails; refill after W; a key you never see again does not leak if you sample. Then say the six-node story in one minute: local limiter is a *protection of the node*, not a *quota*; quota lives in Redis or at the edge (API Gateway, Q in `05-aws`).

**Reflect.** A limiter that is correct on one box and silent on six is how outages get 6× the allowed traffic. Name that before they ask. Weakness: key-map leak, and `nanoTime` overflowing in 292 years (you may joke once).

> Hook: a node-local limiter that "held" in staging (one box) and vanished behind an autoscaling group.

### S14. In-memory key-value store with TTL (Q253)

> Sixty minutes. `put(k, v, ttl)`, `get`, `delete`, capacity eviction, a concurrency contract. They will ask lazy versus eager expire.

**Clarify.** Null policy. TTL of 0 / negative: reject or treat as delete. Capacity: entry count or bytes? Overwrite: reset TTL or keep? `get` of expired: miss, and drop the entry.

**Isolate.** Two indexes (Q246): `HashMap<K, Node>` for O(1) get, and a recency structure for eviction (LRU list) plus an expiry structure if eager (`DelayQueue` or `TreeMap<exp, K>`). Lazy expire is one index and a check on access; the leak is unread expired keys.

**Decide.** Lazy + sample (on each `put`, inspect 5 random entries) + LRU for capacity. One lock, or `ConcurrentHashMap` plus a lock on the LRU list (that is the two-lock trap of S2 - prefer one lock in 60 minutes). Invariant: every live entry is in both the map and the LRU list; expired is in neither after a `get`.

**Execute.** Reuse S12's list. Add `expNanos` on the node. `get`: if expired, delete, return miss. `put`: overwrite path resets TTL and moves to front; then evict while `size > cap` or the tail is expired. Tests: expire-on-get; unread expired does not live forever *if* a later `put` samples it; capacity still holds under a flood of short-TTL keys.

**Reflect.** Eager expire needs a thread you now have to shut down - say so if they want it. Distributed KV is Redis / DynamoDB and a different pack. Weakness: sampling is probabilistic; a key that is never touched and never sampled sits until capacity evicts it (LRU saves you if the list still contains it).

> Hook: a session store that "expired" on paper and grew until an LRU was added.

### S15. Process-local ID generator, later sharded (Q254)

> Forty-five to sixty minutes. Unique 64-bit ids, roughly ordered by time, one process today, many tomorrow. They will rewind the clock and ask what you emit.

**Clarify.** Uniqueness is the invariant; monotonicity is best-effort. IDs may leak (they are not secrets). Worker id: an int you are *given*, not `random`. Clock: wall clock, with a policy on backwards steps. Rate: ids per millisecond you must support (4096 is the 12-bit default).

**Isolate.** Snowflake (Q245) is the shape. The hard parts are: sequence overflow in a millisecond (wait or steal from the next ms), clock going backwards (throw, wait, or use a logical clock), and the later shard (worker-id bits must already exist).

**Decide.** Layout you write on the board: 1 unused + 41 timestamp + 10 worker + 12 sequence, epoch you pick and *document*. `nextId` is `synchronized` (or an `AtomicLong` of the last id if you are careful). Clock backwards by less than X ms: wait; more: throw. Do not emit.

**Execute.** Write `nextId`, the wait-for-next-ms helper, and a test that two ids in the same ms differ in the sequence bits. Test that a one-second rewind throws (or waits - you picked). Show how a second process with a different worker id cannot collide *if* worker ids are unique. The "later sharded" sentence: worker bits *are* the shard; a coordinator (or instance index) assigns them; you do not hash the payload into the id.

**Reflect.** Weaknesses: 41 bits of ms is ~69 years from the epoch; 10 bits is 1024 workers; a duplicate worker id is a silent uniqueness bug - that assignment is an ops problem you name. UUID v7 is the alternative if you do not need 64 bits.

> Hook: an order-id scheme that collided after a leap-second because two boxes issued from a rewound clock.

### S16. Retry library with backoff, idempotency and a budget (Q255)

> Sixty minutes. A library 40 teams will import (Q250). `call` with retry-on predicate, jittered exponential backoff, a deadline, and an idempotency key the caller can pass through. They will ask what you never retry.

**Clarify.** What is retried: `IOException` and 408/429/5xx, not 4xx, not `IllegalArgumentException`. Deadline: wall budget, not "N attempts" alone. Idempotency: the library *transports* a key the caller minted; it does not mint one for a POST it does not understand. Thread: the caller’s thread sleeps (simple) or scheduled executor (non-blocking) - pick and document.

**Isolate.** The loop is Q238. The library problem is the API: what is generic, what is wrapped, what is logged, what is cancelled, and how a team cannot forget the predicate. The budget is a `Deadline` object, not a magic `maxAttempts=3` that ignores a 30-second sleep.

**Decide.**

```java
public final class Retry {
    public static <T> T call(Callable<T> c, RetryPolicy p) throws Exception { /* Q238 + deadline */ }
}
public final class RetryPolicy {
    final Predicate<Exception> retryOn;
    final int maxAttempts;
    final Duration budget, base, cap;
    final boolean jitter;
}
```

Defaults: retry on `IOException` and a small set of status wrappers; 3 attempts; 2s budget; jitter on. `IdempotencyKey` is a header argument, not something `Retry` invents. Never retry a non-idempotent request unless the key is present - if it is absent, one attempt.

**Execute.** Write the policy object first (that is the API review). Then the loop with `System.nanoTime()` against the budget. Tests: succeeds first time (zero sleeps); always-fail respects budget; 400 is not retried; interrupt stops the loop. Document thread-safety: policy is immutable, `call` is stateless.

**Reflect.** Weaknesses: sleeping on the caller thread; no retry-after parsing yet; a bad default predicate will 3× a POST. The follow-up you volunteer: `Retry-After`, and a metric on attempts. This is the library form of S3's "do not lose work silently" - here, do not *duplicate* work silently.

> Hook: a retry helper that turned a 500 into three orders because the POST had no idempotency key.

---

## Part C - Leadership around code

No model answer is scripted. Use STAR-L. Two minutes and six minutes. A number in the Situation and a number of the same kind in the Result. A named person who disagreed. A Learning that is a rule you have used since.

### S17. Landing a review standard across teams you do not manage (Q267)

You wrote Q266's ten-line standard. Six teams, none of them yours, had six different definitions of "blocking". How did you get to one definition without a title that said they had to listen? Who resisted, what did you drop, what became the default in the template, and what changed in the revert rate or the time-to-merge?

### S18. A senior peer's blocking comment is wrong (Q268)

They are senior to you, or on a panel later. The comment would have broken the invariant, or it was a preference labelled blocking. What did you say, in what channel, who did you bring in, and what happened to the relationship? The Learning is a rule about *how* you disagree in a review, not "I was right".

### S19. A refactor you shipped broke production (Q269)

Characterization tests you skipped, a characterization you trusted that did not pin the thing that broke, or a rename that moved a bug. Numbers: error rate, minutes to detect, minutes to revert, what the suite looks like now. The Learning is a rule you have applied on a later refactor.

### S20. Growing someone who could not pass a coding round (Q270)

A named engineer, a baseline (failed a loop, or could not finish Q76 in twenty minutes), what you changed in *their week* (not a pep talk), and a result that is theirs (they passed, they now run the pairing, they shipped the limiter). The Learning is a rule about how you coach code, and a case of using it with someone else.

---
