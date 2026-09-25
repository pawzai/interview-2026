# Coding Cheatsheet

Fast revision. Everything here is expanded in [answers.md](answers.md); question numbers are the index. Read it the night before, and read only the last two sections thirty minutes before.

[15-mock-interviews](../15-mock-interviews/questions.md) Category 11 owns how the *round* is run. This page is what you type.

---

## 1. What the paste is scored on

Correctness under the cases they will supply, structure a reviewer would keep, complexity *of a named variable*, a note the interviewer can write down. Cleverness is not a dimension (Q1).

45-minute budget (Q14): 4 min clarify, 6 sketch, 25 implement, 5 tests, 5 complexity. Time-to-first-correct-loop is the metric.

n = 10⁵: O(n) and O(n log n) live; O(n²) is dead unless the inner bound is tiny. n = 20 is 2ⁿ territory (Q2).

---

## 2. Complexity you must say out loud

| Shape | Time | Extra space | Say it like this |
| --- | --- | --- | --- |
| Two pointers on a sorted array | O(n) | O(1) | of the length |
| Sliding window, each end moves once | O(n) | O(alphabet) | not O(n²) |
| Sort then scan | O(n log n) | O(1) or O(n) | sort is the trick |
| Size-k heap over n | O(n log k) | O(k) | not a max-heap of n |
| Hash get/put | O(1) expected | O(n) | of distinct keys; hash must be honest |
| Binary search / on-answer | O(log range) | O(1) | predicate is monotonic |
| DFS/BFS | O(n + e) | O(n) | mark on enqueue |
| Dijkstra (stale heap) | O((n+e) log n) | O(n) | non-negative only |
| Union-find | inverse-Ackermann | O(n) | "I treat it as O(1) at this n" |
| Backtrack subsets | O(2ⁿ · n) | O(n) | n ≤ 20 |
| 0/1 knapsack 1D | O(n · cap) | O(cap) | inner loop *down* |

Amortized (`ArrayList.add`, `HashMap.put`) is not the SLA (Q4). Hidden O(n²): `List.contains`, `String +` in a loop, `PriorityQueue.remove(Object)`, a hash that collided (Q11, Q73).

---

## 3. Pattern → first move

| If you hear | Write | Not |
| --- | --- | --- |
| Sorted array, pair / range | two pointers (Q15) | a map first |
| Subarray / substring "smallest / longest that" | variable window (Q18, Q20, Q21) | prefix map if negatives (Q24) |
| Range sums, "how many subarrays = k" | prefix + freq map (Q23, Q24) | window |
| Next greater / daily temps | decreasing stack of *indices* (Q78) | nested scan |
| Max of last k | monotonic deque (Q81) | a heap you cannot delete from |
| Merge k lists / chunked sort | heap of heads (Q123) | pairwise merge |
| kth / top-k | size-k heap (Q122) | sort unless n is tiny |
| Stream median | two heaps (Q124) | a sorted list |
| Course order / build order | Kahn (Q138) | DFS without grey (Q139) |
| Cycle, directed | three colours (Q136) | visited-only |
| Components / islands | flood fill (Q140) | unless edges stream in |
| "Can I finish at budget x" | binary search on answer (Q52) | if the predicate is not monotonic |
| Overlapping intervals | sort by start, merge (Q177) | sweep if you need a *count* (Q179) |
| Max non-overlapping | sort by *end* (Q182) | sort by start |
| Subsets / perms / combinations | choose, explore, unchoose (Q150) | nested loops |
| Fewest coins vs number of combinations | loop order (Q168) | the same `dp` |

---

## 4. Java structures under a clock

| Job | Type | Do not |
| --- | --- | --- |
| Stack or queue | `ArrayDeque` (Q211) | `Stack`, `LinkedList` by habit |
| List, random access | `ArrayList` | `LinkedList.get(i)` |
| Uniqueness / seen | `HashSet` / `HashMap` | mutable keys (Q33, S9) |
| Insertion or access order | `LinkedHashMap` (Q35) | expect `containsKey` to count as access |
| Enum keys | `EnumMap` / `EnumSet` (Q210) | `HashSet<MyEnum>` |
| Identity graph clone | `IdentityHashMap` (Q36, Q141) | `HashMap` if `equals` is value-based |
| Sorted keys / multiset | `TreeMap<K, Integer>` (Q127, Q185) | `PriorityQueue.remove` for delete-by-value |
| Min-heap | `PriorityQueue` | `reverseOrder` without thinking about overflow |
| Bounded buffer | `ArrayBlockingQueue` (Q223) | `LinkedBlockingQueue()` (S3) |
| Concurrent map | `ConcurrentHashMap` | null keys/values; `synchronized (map)` |

`List.of` / `Map.of`: unmodifiable, no null (Q203). `record`: no defensive copy (Q204).

---

## 5. Binary search and comparators

```java
int mid = lo + (hi - lo) / 2;          // never (lo + hi) / 2   (Q48, S8)
Integer.compare(a, b);                 // never a - b           (Q55, S7)
Arrays.sort(a, Comparator.comparingInt(x -> x[0]));
```

Lower bound: first `i` with `a[i] >= t`. Upper: first `i` with `a[i] > t`. `Arrays.binarySearch` is neither (Q47).

On a double domain: ~100 iterations, not `==` (Q51). On the answer: one sentence of monotonicity or it is not this pattern (Q52).

Inclusive vs exclusive intervals: *ask* (Q181). Rooms-II tie-break: process end before start at the same t (Q179).

---

## 6. Bits, numbers, money

```
-n          == ~n + 1
power of 2  == n > 0 && (n & (n - 1)) == 0     // MIN_VALUE lies (Q193)
drop lowest == n & (n - 1)
get/set/clr == (n >>> k) & 1  /  n | (1<<k)  /  n & ~(1<<k)
```

`Integer.MIN_VALUE` negated is itself. `Math.abs(MIN_VALUE)` returns `MIN_VALUE`. `Math.negateExact` throws (Q189, Q200). `MIN / -1` wraps, does not throw (Q197).

Money: integer minor units or `new BigDecimal("0.1")`, never `double`, never `new BigDecimal(0.1)` (Q196, S4). Compare with `compareTo`, not `equals`.

---

## 7. Concurrency you might have to type

```java
while (n == cap) notFull.await();     // while, not if
notifyAll();                          // one wait-set
// or two Conditions on one ReentrantLock (S11)
```

Ship a pool as `ThreadPoolExecutor(core, max, 60s, ArrayBlockingQueue<>(bound), factory, CallerRuns|Abort)` (Q223). `newCachedThreadPool` is a fork-bomb on a request path (Q224). Unbounded queue ⇒ `max` is a lie (S3).

Virtual threads: still cap the DB (semaphore). `synchronized` around blocking I/O pins (S10, Q225).

Do not `synchronized (Integer)` or interned strings (Q228). Lock order or `tryLock` (Q227, S2).

`thenCompose` is flatMap; `thenApply` on a CF nests (Q221). `join` → `CompletionException`; `get` → checked + clears interrupt (Q222).

---

## 8. Design-and-implement in one screen

| Object | Core | The thing you name |
| --- | --- | --- |
| Bounded queue (S11) | ring + two conditions | interrupt leaves state unchanged |
| LRU (S12) | map + DLL + dummies | `map.size() == listLength` |
| Token bucket (S13) | tokens + lastNanos | *not* distributed |
| KV + TTL (S14) | map + LRU + lazy expire | sample or you leak |
| Snowflake (S15) | ts / worker / seq | clock backwards → refuse |
| Retry (S16) | jitter + budget + predicate | never retry a POST without a key |

API first: null policy, thread-safety sentence, what throws (Q235, Q250). One lock in 45 minutes beats a clever two-lock protocol (S2).

---

## 9. Tests you actually write

Three, after the first green path (Q257): the example in the prompt, one edge (`[]`, `k=0`, `MIN_VALUE`, `""`), one invariant (round-trip, size after evict).

Characterization before a refactor (Q261). `Clock` instead of `Instant.now()` (Q263). `assertArrayEquals`, not `array.equals` (Q215).

---

## 10. Trap list (read this thirty minutes before)

- `(lo + hi) / 2` and `return a - b` (S8, S7).
- Mutable map/set key (S9). `hashCode` of a new key type (S1).
- `get == null` meaning absent on a map that stores null (Q40).
- `Stack` the class; `LinkedList` as a `List` (Q84, Q98).
- `String +` in a loop (Q73). `split(":")` drops trailing empties (Q65).
- Window `r - l` without `+ 1` (S5). Dutch-flag: do not `i++` on a swap with 2 (Q26).
- Sliding window on a sum that can go negative (Q24).
- Directed cycle with a single `visited` (Q139). Dijkstra on a negative edge (Q143).
- Coin-change II loop order counts permutations (Q168).
- `Optional` as a field; `orElse(expensive())` (Q205). Parallel stream into a `HashMap` (S6).
- `newCachedThreadPool`, unbounded `LinkedBlockingQueue` (S3).
- Two locks, opposite order (S2). `synchronized` on a boxed id (Q228).
- Money in `double` (S4). `abs(Integer.MIN_VALUE)` (Q200).
- Virtual threads without a cap on the connection pool (S10).

---

## 11. Sentences that become notes

- "I will mutate `nums` unless you need it afterwards."
- "O(n) of the edges, not the nodes."
- "If x works, x+1 works, so I am searching the budget."
- "This is a node-local limiter; six nodes are 6N."
- "I am writing the production shape and omitting the telemetry."
- "That comment is blocking because it can lose data; the naming one is preference."
