# Answers

Model answers for [questions.md](questions.md). Numbers match the question numbers exactly.

Every answer follows the four-layer structure from [../01-java/README.md](../01-java/README.md): direct answer, mechanism, trade-off, experience hook. Code is the shortest Java that would survive a review, not a framework. Q239 and Q251-Q255 are the Part B walkthroughs in [scenario-questions.md](scenario-questions.md). Q267-Q270 have no scripted answer - they are your stories.

---

## 1. How a coding solution is judged, and complexity as a design tool

### Q1. What the coding solution is scored on

Correctness under the cases the interviewer will supply, then structure a reviewer would keep, then complexity you can defend, then communication that produces a written note. Cleverness is not a dimension because a clever trick that breaks on the empty array, or that you cannot explain, is a no-hire artifact.

A principal-level paste looks boring: names that match the domain, one helper, the edge cases in the signature or a comment, and a complexity sentence that names *of what*. The interviewer is deciding "would I let this person merge on week one", not "did they remember the xor trick".

> *Hook: a loop I watched fail a strong senior because the O(n) two-pointer was correct and the narration never named the invariant.*

### Q2. Big-O as a decision tool, not a recitation

O(1) is a hash get or an index. O(log n) is a binary search or a heap operation. O(n) is a single pass. O(n log n) is a sort or n heap operations. O(n²) is a nested scan. O(2ⁿ) or worse is a raw subset or permutation walk.

At n = 10⁵, O(n) and O(n log n) finish; O(n²) is 10¹⁰ operations and you do not write it unless n is tiny or you have a tight inner bound. At n = 20, 2ⁿ is the whole conversation. Always name the variable: O(n) of what - length, edges, alphabet, window.

### Q3. Best, average, worst

Quote worst case unless the algorithm is *designed* around the average (hash tables, randomized quicksort) and you say so. Quoting only the average of quicksort hides the O(n²) pivot failure; quoting only the worst of a hash map hides that the expected `get` is O(1) and that is why you chose it.

The follow-up you lose is "what input makes this bad". Have that input ready: already-sorted for naive quicksort, adversarial hashes for a map, a single huge window for a sliding-window that you implemented as a rescan.

### Q4. Amortized versus worst-case `[D]`

`ArrayList.add` is O(1) amortized: most adds are a store, a resize copies 2ⁿ elements over a sequence of n adds, so the extra cost is O(n) across n adds. `HashMap.put` is the same story plus a rehash. Refuse the amortized story when a single add in a latency-critical path can copy a 10-million-element array - then you pre-size, or you use a structure whose worst case is the SLA.

### Q5. "O(n) of what?" `[T]`

Name the input that grows: characters, edges, distinct keys, window length, number of queries. If two sizes matter, say O(n + m) or O(n · k). Candidates who say "linear" and cannot point at a variable are bluffing, and the interviewer will switch to a two-variable problem on the next question.

### Q6. Time-space trade-offs you have actually made

Spent memory: a prefix-sum array, an LRU, an inverted index. Spent time: streaming a file you could have slurp'd, recomputing a derived value to avoid a stale cache. The interview sentence is "I paid O(n) memory so every query became O(1), and I would not do that if the array did not fit in the heap".

### Q7. What "in-place" means in Java

You mutate the input array or list and allocate only a handful of scalars or a recursion stack you are willing to call extra space. Swapping is not free: you dirty the caller's data, you break other aliases, and you still pay write-barrier and cache-line costs. Say "I will mutate `nums` unless you need it afterwards" before you do it.

### Q8. O(n)/O(n) versus O(n log n)/O(1) `[T]`

Write the O(n) time solution first - correctness and the simpler invariant - and then say "if memory is the constraint I can sort and two-pointer in O(n log n) and O(1) extra, at the cost of destroying order / mutating the input". The interviewer is scoring the *conversation*, not that you picked the textbook optimal on the first line.

### Q9. Picking a structure in three minutes

Access by key → map. Uniqueness → set. Order of insertion → `LinkedHashMap` / list. Order of value → heap or `TreeMap`. Frequent insert/delete at ends → `ArrayDeque`. Need the kth → heap or quickselect. Concurrent writers → `ConcurrentHashMap` or an explicit lock. Say this ladder out loud; it is the note they write.

### Q10. When brute force earns the clock

When the optimal is a named pattern you do not yet see, write the O(n²) so you have a correct oracle and a complexity to beat. Skip it when you already see the two-pointer or the heap and n is 10⁵. A brute-force you cannot finish is a worse artifact than an optimal you narrate and then code.

### Q11. Your O(n) was O(n²) `[T]`

You counted the outer pass and ignored an inner scan, a `contains` on a list, a string `+` in a loop, or a hash that degraded. Recovery: name the hidden loop, give the input that triggers it ("if every window is unique this rescan is n²"), and replace the inner structure. Do not defend the original bound.

### Q12. Recurrences you can solve out loud

Merge sort: T(n) = 2T(n/2) + O(n) → O(n log n). Binary search: T(n) = T(n/2) + O(1) → O(log n). Naive Fibonacci: T(n) = T(n-1) + T(n-2) + O(1) → Θ(φⁿ). You never ship the last one; you ship the O(n) loop or the matrix / closed form. Master theorem is optional; the recursion tree is enough.

### Q13. "Production quality" in 45 minutes `[A]`

Keep: names, a total order on error handling (reject null / empty at the top), complexity, one or two tests. Drop: logging framework, metrics, generics gymnastics, a strategy interface for a single implementation. Say *"I am writing the production shape and omitting the telemetry you would add in the real repo"* so the omission is a judgement.

### Q14. A 45-minute budget `[A]`

Four minutes clarifying and restating; six on a brute-force or a sketch; twenty-five on the optimal plus the helper; five on tests; five on complexity and the follow-up. Nineteen-year candidates blow it by designing a framework for twelve minutes, or by polishing names on a solution that still fails `[]`. Time-to-first-correct-loop is the metric.

---

## 2. Arrays, two pointers, sliding window, prefix sums

### Q15. Two-sum on a sorted array

Two pointers, not a map: the array already is the index.

```java
boolean twoSumSorted(int[] a, int t) {
    int i = 0, j = a.length - 1;
    while (i < j) {
        int s = a[i] + a[j];
        if (s == t) return true;
        if (s < t) i++; else j--;
    }
    return false;
}
```

O(n) time, O(1) extra. A hash map is O(n) extra and throws away the order you were given. Edge: empty, one element, negatives, overflow of `a[i] + a[j]` - use a `long` sum if the values can be `Integer.MIN_VALUE`.

### Q16. Reverse an array in place

```java
void reverse(int[] a) {
    for (int i = 0, j = a.length - 1; i < j; i++, j--) {
        int t = a[i]; a[i] = a[j]; a[j] = t;
    }
}
```

Boxed `Integer[]` is the same swap of *references*; you are not mutating the `Integer` objects. Do not use `Collections.reverse` on `Arrays.asList(intArray)` - that does not compile on an `int[]`.

### Q17. Remove duplicates from a sorted array

Write the next unique at `slow`, scan with `fast`. The tail is garbage; the contract is the new length, not a compacted array you `null` out. Interviewers who want the tail cleared will say so.

```java
int unique(int[] a) {
    if (a.length == 0) return 0;
    int s = 1;
    for (int f = 1; f < a.length; f++)
        if (a[f] != a[s - 1]) a[s++] = a[f];
    return s;
}
```

### Q18. Sliding-window template

Fixed window: add `a[r]`, if `r >= k` drop `a[r - k]`, record. Variable window: grow `r` until the invariant is satisfied (or broken), then shrink `l` while it stays satisfied. The invariant you say out loud is *"the window `[l, r]` is the smallest/largest that still …"*. One `l` and one `r`, both only move forward, so the whole scan is O(n).

### Q19. Maximum sum of a window of length k

```java
int maxSum(int[] a, int k) {
    if (a.length < k) throw new IllegalArgumentException("k");
    int sum = 0, best;
    for (int i = 0; i < k; i++) sum += a[i];
    best = sum;
    for (int i = k; i < a.length; i++) {
        sum += a[i] - a[i - k];
        best = Math.max(best, sum);
    }
    return best;
}
```

This is not Kadane. Kadane is any subarray; this is exactly k. Empty / `k > n` is a precondition, not a clever return.

### Q20. Longest substring without repeating characters `[T]`

Last-seen index, not a set you rebuild. Off-by-one is `r - l` versus `r - l + 1`, and moving `l` to `last[c]` instead of `last[c] + 1`.

```java
int lengthOfLongestSubstring(String s) {
    int[] last = new int[256];
    Arrays.fill(last, -1);
    int best = 0, l = 0;
    for (int r = 0; r < s.length(); r++) {
        char c = s.charAt(r);
        if (last[c] >= l) l = last[c] + 1;
        last[c] = r;
        best = Math.max(best, r - l + 1);
    }
    return best;
}
```

Invariant: `[l, r]` has unique characters. Empty string and all-unique / all-same are the three tests.

### Q21. Minimum window substring

`need` is the count of characters still owed. When you add a useful character, `need--`. When `need == 0` the window is valid; shrink from the left, and each time you evict a useful character `need++`.

```java
String minWindow(String s, String t) {
    int[] owe = new int[128];
    for (int i = 0; i < t.length(); i++) owe[t.charAt(i)]++;
    int need = t.length(), best = Integer.MAX_VALUE, start = 0;
    for (int r = 0, l = 0; r < s.length(); r++) {
        if (owe[s.charAt(r)]-- > 0) need--;
        while (need == 0) {
            if (r - l + 1 < best) { best = r - l + 1; start = l; }
            if (owe[s.charAt(l++)]++ == 0) need++;
        }
    }
    return best == Integer.MAX_VALUE ? "" : s.substring(start, start + best);
}
```

The `> 0` / `== 0` on the owe array is the whole trick: extras are allowed and do not change `need`.

### Q22. Kadane, and why product is different

```java
int maxSubArray(int[] a) {
    int best = a[0], cur = a[0];
    for (int i = 1; i < a.length; i++) {
        cur = Math.max(a[i], cur + a[i]);
        best = Math.max(best, cur);
    }
    return best;
}
```

Maximum *product* must track both min and max because a negative times a min flips sign. That is two running values, not Kadane. Empty array is a spec question; the usual contract is `a.length >= 1`.

### Q23. Prefix sums and the off-by-one

Define `prefix[0] = 0`, `prefix[i] = a[0] + … + a[i-1]`. Range `a[L..=R]` is `prefix[R+1] - prefix[L]`. The interviewer waits for `prefix[R] - prefix[L]` on a 1-based mental model. Inclusive/exclusive is the whole game - say it.

### Q24. Subarray sum equals k, negatives allowed `[T]`

A sliding window assumes you can tell which end to move from the sign of the error. Negatives break monotonicity. Store how many prefixes have seen `sum - k`:

```java
int subarraySum(int[] a, int k) {
    Map<Integer, Integer> freq = new HashMap<>();
    freq.put(0, 1);
    int sum = 0, ans = 0;
    for (int x : a) {
        sum += x;
        ans += freq.getOrDefault(sum - k, 0);
        freq.merge(sum, 1, Integer::sum);
    }
    return ans;
}
```

The map stores *counts of prefix values*, not indices, because the question is "how many", not "is there".

### Q25. Product except self

Two passes: `out[i]` gets the product of the left, then a running right product multiplies on the way back. O(1) extra is allowed to ignore the output array. Zeros: one zero puts zeros everywhere except at that index; two zeros zeros the lot. Do not divide - a zero in the input makes division illegal, which is why the question bans it.

### Q26. Dutch national flag

```java
void sortColors(int[] a) {
    int l = 0, i = 0, r = a.length - 1;
    while (i <= r) {
        if (a[i] == 0) swap(a, l++, i++);
        else if (a[i] == 2) swap(a, i, r--);   // do not i++
        else i++;
    }
}
```

`[0, l)` is 0s, `[l, i)` is 1s, `(r, n)` is 2s, `[i, r]` is unknown. The `i++` you must not take on a 2 is the bug.

### Q27. Rotate by k `[T]`

`k %= n`, and if `k < 0` add `n`. Reverse all, reverse the first k, reverse the rest. `k > n` without the mod writes off the end or no-ops wrongly. `n == 0` is a guard.

### Q28. Trapping rain water

At `l` and `r`, the water on the smaller side is bounded by that side's running max. Move the smaller side. Stack of indices is the "next greater" reading of the same idea - mention it, write the two-pointer: O(n) time, O(1) extra.

### Q29. Merge into the tail

`A` has capacity `m + n`. Write from the back so you never overwrite an unconsumed value of `A`. From the front you would need a buffer. Three pointers: `i = m-1`, `j = n-1`, `w = m+n-1`.

### Q30. Last k distinct on a 10⁸ stream `[A]`

A `LinkedHashSet` (insertion-order set) plus a running sum: on each value, if already present remove and re-add to refresh order; if size exceeds k, evict the oldest and subtract. O(1) amortized per event, O(k) memory. A heap is the wrong shape - you need recency, not magnitude.

---

## 3. Hashing, counting and Java `Map`/`Set` idioms

### Q31. Two-sum unsorted, one pass

```java
int[] twoSum(int[] a, int t) {
    Map<Integer, Integer> seen = new HashMap<>();
    for (int i = 0; i < a.length; i++) {
        Integer j = seen.get(t - a[i]);
        if (j != null) return new int[] { j, i };
        seen.put(a[i], i);
    }
    throw new IllegalArgumentException("none");
}
```

The "use yourself" trap is putting `a[i]` into the map *before* the lookup when `t == 2 * a[i]`. Put after. Duplicates are legal; the map keeps the latest or the first - either is fine if you look up first.

### Q32. Group anagrams

Key is `char[]` sorted, wrapped as `new String(cs)`, or a 26-int count encoded as a string. Sorted key is O(k log k) per word and is what you write. Count key is O(k) and wins on long words. Do not use `int[]` as a `HashMap` key - it compares by identity.

### Q33. Mutating a `HashSet` key `[T]`

The entry stays in the old bucket. `contains` / `remove` of the mutated object miss; iteration still returns it; `size` is unchanged. It is a leak. Same story as `01-java` Q2 on `HashMap`. Keys must be immutable in the fields that `equals`/`hashCode` read.

### Q34. `computeIfAbsent` idioms

```java
freq.merge(word, 1, Integer::sum);
map.computeIfAbsent(key, k -> new ArrayList<>()).add(value);
```

`get` then `put` of a new list races with yourself on a nested structure and is two lookups. `computeIfAbsent` is one, and it must not recurse into the same map (it is fail-fast on that). Do not use `computeIfAbsent` for a value whose constructor is expensive and can throw after the map has already reserved the key - know the JDK version; modern JDKs only insert on success.

### Q35. `LinkedHashMap` order

Insertion-order is the default. Access-order is `new LinkedHashMap<>(n, 0.75f, true)`. `get`, `getOrDefault`, `put`, `putIfAbsent`, `compute`, `merge` count as access; `containsKey` does **not**. Override `removeEldestEntry` for an LRU (Q243, Q251).

### Q36. `IdentityHashMap` and `EnumMap` `[T]`

`EnumMap` is the default for enum keys - array-backed, no hash, no `null` keys. `IdentityHashMap` uses `==` and `System.identityHashCode`; it is the right tool for an object-identity graph clone (Q141, Q96). Used by accident, two equal `String` keys are two entries and you "lose" updates. It also allows a `null` key.

### Q37. Counting array versus `HashMap` frequency

If the domain is `0..K` and K is ~n or smaller, `int[K+1]` is faster and kinder to the cache. If the domain is `Integer` or the span is 10⁹, the array is a memory bomb and you use a map of *observed* keys. Negative values need an offset or a map; do not silently clip.

### Q38. First unique in a stream

`LinkedHashMap<Char, Boolean>` of "still unique", plus a set of seen-twice. On each char, if new insert; if already unique remove from the map and add to the twice-set; if twice ignore. The first key of the map is the answer. The string version is a 26-count plus a second pass, which you write if the input is static.

### Q39. Longest consecutive sequence

Put everything in a `HashSet`. Start a run only when `x - 1` is *not* in the set, then walk `x+1, x+2, …`. Each number is in at most one walk, so the inner loop is honest O(n). Starting a walk from every x is O(n²) on a single run.

### Q40. `get == null` versus `containsKey` `[T]`

They differ when `null` is a stored value. `HashMap` allows one `null` key and null values; `ConcurrentHashMap` and `Map.of` do not. In a frequency map that can store zero, use `getOrDefault` or `containsKey`. Never use `get == null` to mean "absent" if you ever `put(key, null)`.

### Q41. Permutation in string

A window of `t.length()` over `s`, a 26-count of owed characters, and a `need` of how many slots are still wrong. Slide, adjust the exiting and entering char, succeed when `need == 0`. Early-exit if `s.length() < t.length()`.

### Q42. A set of pairs without a wrapper

Pack two `int`s into a `long` (`((long) a << 32) ^ (b & 0xffffffffL)`) when the domain fits. That is a mistake when `a` already needs 32 bits *and* you wanted a signed pair, or when you will later want three fields - then write a `record Pair(int a, int b)`. Do not use `List.of(a, b)` as a key in a hot path; it allocates.

### Q43. Observable collisions

Java 8+ treeifies a bin of `Comparable` keys at 8 entries (and the table capacity at least 64). `get` degrades from O(1) to O(log bin). You do not try to force this in a round; you say "adversarial hashes plus a bad `hashCode` make bins long, and we once saw get at tens of microseconds on a key whose hash was constant" - that is S1 / Q44.

### Q44. 40 µs HashMap get `[A]`

Diagnostic order: is `hashCode` constant or colliding (S1); is the map being resized on the hot path (pre-size); is the key mutating (Q33); is the pause GC, not the map; is the map actually a `TreeMap` or synchronized wrapper. The rewrite you ship is an identity key, a perfect hash, or a stripped `int[]` + open addressing if the domain is dense. Do not "tune load factor" as the first move.

### Q45. Multiset, bidimap, map-of-lists `[A]`

Keep a raw `HashMap` plus `merge` / `computeIfAbsent` until the third call site wants the same structure. Then a `record` and two small methods, or Guava `Multimap` / `BiMap` if the project already has it. Pulling Guava for one `HashMultiset` in an interview is a smell; saying "I would" is not.

---

## 4. Sorting, binary search and binary-search-on-answer

### Q46. Binary search, invariant and safe mid

```java
int indexOf(int[] a, int t) {
    int lo = 0, hi = a.length - 1;
    while (lo <= hi) {
        int mid = lo + (hi - lo) / 2;
        if (a[mid] == t) return mid;
        if (a[mid] < t) lo = mid + 1;
        else hi = mid - 1;
    }
    return -1;
}
```

Invariant: if `t` is present it is in `a[lo..=hi]`. Empty array returns -1. Duplicates: this returns *a* hit, not the first (Q50).

### Q47. Lower and upper bound

Lower bound: first index `i` with `a[i] >= t` (or `n`). Upper bound: first `i` with `a[i] > t`. `Arrays.binarySearch` returns *an* index of an exact hit, or `-(insertionPoint) - 1`. It is neither bound. Write the loop with `hi = n` and `lo < hi`, assigning `hi = mid` or `lo = mid + 1`.

### Q48. Mid overflow `[T]`

`lo + hi` overflows a signed `int` when both are large (the classic `Integer.MAX_VALUE` pair). `lo + (hi - lo) / 2` does not, because `hi - lo` fits if they are valid indices. In a *normal* `int[]` the last index is `Integer.MAX_VALUE - 1` at theoretical max, so `lo + hi` can still overflow. Write the safe form by habit. This is S8.

### Q49. Rotated sorted array

One half of `[lo, hi]` is always sorted (no duplicates). If `a[lo] <= a[mid]`, the left is sorted; ask whether `t` lies in `[a[lo], a[mid])`. Duplicates (`a[lo] == a[mid] == a[hi]`) make that test lie - you can only shrink `hi--` and the worst case becomes O(n). Say that before you are asked.

### Q50. First and last position

Two bound searches, not a hit plus a linear scan: the scan is O(n) on an all-equal array, which is the case they will feed you. Lower bound of `t` and lower bound of `t+1` (or upper bound of `t`) minus one. Missing target: lower bound is out of range or not equal.

### Q51. Binary search on doubles `[T]`

Terminate on a domain width (`hi - lo > 1e-9`) *or* a fixed iteration count (~100 is enough for IEEE doubles). A too-small iteration count leaves a wrong integer answer after you floor. A too-tight epsilon on a huge domain never finishes. Prefer a fixed 80–100 iterations and say so.

### Q52. Binary search on the answer

The predicate `feasible(x)` is "can I finish / ship / eat at budget x". It is monotonic: if x works, x+1 works. Search the budget. Prove monotonicity in one sentence: *"more capacity can only make the same packing easier"*. If that sentence is false, it is not this pattern (Q24's negatives).

### Q53. Median of two sorted arrays

Partition both arrays so the left half has `(n+m+1)/2` elements and `maxLeft <= minRight` across the cut. Binary-search the cut on the shorter array. Odd total → max of lefts; even → average of max-left and min-right. You do not merge. O(log min(n, m)).

### Q54. `Arrays.sort` dual path

`int[]` (and other primitives) use dual-pivot quicksort, not stable, O(n log n) typical. `Object[]` / boxed uses TimSort, stable, O(n log n) worst, exploits runs. `Integer[]` pays boxing and TimSort. Your complexity story changes when you promised stability or when you sorted a primitive to dodge comparators.

### Q55. `return a - b` `[T]`

`Integer.MIN_VALUE - 1` (or `a = MIN_VALUE, b = 1`) overflows and flips the sign, so the comparator lies and TimSort can throw `IllegalArgumentException: Comparison method violates its general contract`. Write `Integer.compare(a, b)` or `Comparator.comparingInt`. Same family as Q186.

### Q56. Sort as the trick

Three problems: merge intervals (Q177), two-sum closest, and "meeting rooms" (Q180). The sort makes a linear scan legal because any violation of the invariant would have appeared earlier. Say *"I sort so that the candidate I now consider is the only one I need"*.

### Q57. kth largest: sort, heap, quickselect

Sort: O(n log n), simple, mutates. Size-k min-heap: O(n log k), the default you write (Q122). Quickselect: average O(n), worst O(n²) unless you randomize or median-of-medians, mutates, not stable. Write the heap unless they ban extra memory or n is huge and k ~ n/2, then quickselect and say the worst case.

### Q58. Comparator inconsistent with `equals` `[T]`

`TreeSet` / `TreeMap` will treat two `equals`-equal elements as distinct if `compare` says otherwise (or drop one if `compare` says 0 but `equals` is false - it uses compare only). TimSort may throw if the contract (antisymmetry, transitivity) is broken. In a review: `compare == 0` iff `equals`.

### Q59. Binary search a 2 TiB file `[A]`

Keep a small index of block starts (or trust a known record size). Probe the midpoint *block*, read one record, decide left/right. Memory holds one block plus the index. If a block contains a run that straddles the predicate, scan that block linearly. This is not `mmap` of 2 TiB on a 16 GiB heap.

### Q60. Sort 10⁹ ints in 2 GiB `[A]`

2 GiB is 2³¹ bytes ≈ 0.5 × 10⁹ ints, so you cannot hold the data. External sort: chunk, `Arrays.sort` each chunk to disk, k-way merge with a heap (Q123). Radix sort of 32-bit keys is attractive *per chunk*. `Arrays.sort` on the whole thing is not an option; say that and move to the merge.

---

## 5. Strings, parsing and tokenizing

### Q61. Reverse words

Trim, scan tokens by skipping spaces, push into a list or a deque, join with a single space. `split(" ")` keeps empty strings for double spaces and is the trap; `split("\\s+")` is acceptable if you then filter. `StringBuilder` and an index walk is what you write when they ban regex.

### Q62. Valid palindrome

```java
boolean isPalindrome(String s) {
    int i = 0, j = s.length() - 1;
    while (i < j) {
        while (i < j && !Character.isLetterOrDigit(s.charAt(i))) i++;
        while (i < j && !Character.isLetterOrDigit(s.charAt(j))) j--;
        if (Character.toLowerCase(s.charAt(i++)) != Character.toLowerCase(s.charAt(j--)))
            return false;
    }
    return true;
}
```

No filtered copy. Empty and punctuation-only are `true`.

### Q63. Longest palindromic substring

Expand around 2n-1 centres (odd and even). O(n²) time, O(1) extra, twenty minutes. DP `dp[i][j] = s[i]==s[j] && dp[i+1][j-1]` is O(n²) space and slower to type. Manacher is O(n) and you mention it only if they ask; you do not write it under a clock.

### Q64. atoi with overflow

Sign, skip leading spaces, accumulate in a `long`, clamp to `[Integer.MIN_VALUE, Integer.MAX_VALUE]`. The never-leave-`int` version checks `if (acc > MAX/10 || acc == MAX/10 && digit > MAX%10)` *before* multiplying. Trailing junk is ignored or rejected - ask. `+` / `-` only at the start.

### Q65. `String.split` traps `[T]`

`"a:b:".split(":")` is `["a","b"]` - trailing empties dropped. `"a:b:".split(":", -1)` keeps them. `"aaa".split("a")` is `[]` (or a pile of empties depending on limit). For tokenization, prefer an index scan or `split(regex, -1)` when empties are data. `StringTokenizer` is legacy.

### Q66. `indexOf` / KMP

Naive is O(n·m) and acceptable when m is tiny or they asked for `indexOf` behaviour. Mention KMP (prefix table, O(n+m)) or Rabin-Karp and stop - writing KMP correctly takes the rest of the round. The production answer is `String.indexOf` / `Pattern`, not your KMP.

### Q67. Valid IP

`split("\\.", -1)` - the `-1` keeps empties so `"1.1.1."` fails. Four parts, each 0-255, no leading zero unless the part is `"0"`. IPv6: eight hex groups, `::` once. Off-by-ones: empty part, nine groups, hex out of range. Do not use `InetAddress` in a round unless they permit library calls; it does DNS.

### Q68. Run-length encode / decode

Encode: count runs, append `c` + count (or count + `c` - agree the format). Decode: parse the integer and `append(String.valueOf(c).repeat(n))`. The bomb is `repeat(untrusted)` on a 2 GB claim - cap the decoded length and fail closed. This is a security review comment (pack `11`).

### Q69. `char` versus code point `[T]`

A supplementary character is two `char`s (surrogate pair). `charAt` / `toCharArray` / `s.length()` are UTF-16 units. `s.codePoints()` / `offsetByCodePoints` iterate characters. `"👍".length()` is 2. In a round, ask whether the input is BMP; most toy problems are.

### Q70. Minimum window covering t

Same owed-count as Q21. On a `String` you still use `charAt` and a 128- or 256-array if the problem is ASCII; a `HashMap<Character, Integer>` if it is Unicode. Do not copy-paste Q21 without saying the alphabet.

### Q71. Calculator with parentheses

One stack of integers and signs (or a stack of `(acc, sign)` frames). On `(` push the frame and reset; on `)` pop and combine. Unary minus is a sign on the next number, not a binary operator - treat `+`/`-` as "apply the pending sign to the number you just finished". No `*`/`/` in this version; those need precedence or a second stack.

### Q72. Wildcard versus regex matching

Wildcard (`?` = one, `*` = any sequence): DP `dp[i][j]` on prefixes, `*` can eat zero or more. Regex (`.` = one, `*` = *zero or more of the previous*): the `*` binds to the previous token, so the state must look at `p[j-1]`. They are not the same `*`. Write the 2D boolean table; mention that a greedy backtrack also works and can explode.

### Q73. `+` in a loop `[T]`

Each `s = s + chunk` copies the growing prefix: O(n²). Since Java 9, *compile-time* concatenation is `invokedynamic` / `StringConcatFactory`; a loop still allocates a new `String` per iteration unless you wrote a `StringBuilder`. The compiler cannot save the loop. This is S-adjacent to any "build a string" problem.

### Q74. 2 GB CSV on a Lambda heap `[A]`

Do not load the file. Stream lines (or a proper quoted-CSV state machine that can hold at most one record), decode with the declared charset, never `Files.readString`. Quoted fields can contain newlines - a `readLine` parser is wrong for real CSV. Cap record size. Off-heap / pipe to the next stage. Heap limit is the design constraint, not an afterthought.

### Q75. Tokenizer with line and column `[A]`

Token types: number, ident, string, operator, lparen, rparen, eof. State is `(i, line, col)` and the current token. On every consume, if `'\n'` then `line++, col=1` else `col++`. Errors throw a `ParseException(line, col, msg)` - never just `"bad token"`. Leave expression parsing as a recursive-descent interface so Q71 / Q88 can sit on top.

---

## 6. Stacks, queues and monotonic structures

### Q76. Valid parentheses

```java
boolean valid(String s) {
    ArrayDeque<Character> st = new ArrayDeque<>();
    for (int i = 0; i < s.length(); i++) {
        char c = s.charAt(i);
        if (c == '(' || c == '[' || c == '{') st.push(c);
        else if (st.isEmpty() || !match(st.pop(), c)) return false;
    }
    return st.isEmpty();
}
```

Three failures: leftover opens, a close on empty, a mismatched pair. `ArrayDeque`, not `Stack`.

### Q77. Queue with two stacks

Inbound stack for `enqueue`, outbound for `dequeue`. Amortized O(1): each element moves at most once. The two-queue stack is O(n) per push or per pop and is a curiosity - write it only if they ask. State the amortized story (Q4) out loud.

### Q78. Next greater / daily temperatures

Scan left to right, keep a *decreasing* stack of indices. When `a[i]` is greater than `a[st.peek()]`, pop and record `i - idx` (or `a[i]`). Invariant: stack heights are strictly decreasing, so the first greater to the right is the first that fails that.

### Q79. Largest rectangle in a histogram

Stack of increasing indices. On a descent, the popped bar's right bound is `i` and its left bound is the new peek. Area = `height[pop] * (i - peek - 1)`. Flush with a sentinel height 0 at the end so the tail pops. You store indices because you need the width.

### Q80. MinStack `[T]`

Two stacks: values, and running mins (push a min when `x <= min`, pop it when `x == min`). Encoding `2*x - min` on one stack overflows `int` when x is `MIN_VALUE`. Write two stacks, or a stack of a `record Node(int val, int min)`. Do not use `Stack`.

### Q81. Sliding-window maximum

`ArrayDeque<Integer>` of indices, decreasing values. On each `r`: evict from the back while `a[r] >= a[back]`; evict from the front while `front <= r-k`; the front is the max. O(n): each index is pushed and popped once.

### Q82. Reverse Polish

```java
int evalRPN(String[] tok) {
    ArrayDeque<Integer> st = new ArrayDeque<>();
    for (String t : tok) {
        switch (t) {
            case "+" -> st.push(st.pop() + st.pop());
            case "-" -> { int b = st.pop(), a = st.pop(); st.push(a - b); }
            case "*" -> st.push(st.pop() * st.pop());
            case "/" -> { int b = st.pop(), a = st.pop(); st.push(a / b); }
            default -> st.push(Integer.parseInt(t));
        }
    }
    return st.pop();
}
```

Java `/` truncates toward zero. Order on `-` and `/` is the bug. Overflow of `int` multiply is usually ignored in the toy problem; say so.

### Q83. Asteroid collision

Positive flies right, negative left. A collision is `top > 0 && x < 0`. While that holds, compare `top` and `-x`: equal → pop and drop x; top smaller → pop and keep going; top larger → drop x. The while condition candidates reverse is "same direction" versus "towards each other".

### Q84. Do not use `Stack` `[T]`

`java.util.Stack` extends `Vector`, is synchronized on every call, and exposes the `Vector` API (`get(i)`), so it is not a stack. `ArrayDeque` is unsynchronized: it is *not* a concurrent queue. For many producers use `ArrayBlockingQueue` / `ConcurrentLinkedQueue` (Q89, Q125).

### Q85. Decode `3[a2[c]]`

A stack of `(string-so-far, multiplier)` frames. On `[` push and reset; on `]` pop, repeat the current string, append to the popped string. Cleaner than two parallel stacks. `repeat` on an untrusted multiplier is Q68 again - cap it.

### Q86. Circular buffer

```java
final class Ring<T> {
    private final Object[] a;
    private int h, t, n;
    Ring(int cap) { a = new Object[cap]; }
    boolean offer(T x) {
        if (n == a.length) return false;
        a[t] = x; t = (t + 1) % a.length; n++; return true;
    }
    @SuppressWarnings("unchecked")
    T poll() {
        if (n == 0) return null;
        T x = (T) a[h]; a[h] = null; h = (h + 1) % a.length; n--; return x;
    }
    int size() { return n; }
}
```

Count `n` distinguishes full from empty. Nulling on poll avoids leaks. This is the sequential core of Q239.

### Q87. Monotonic queue versus stack

A stack only sees the *next* (or previous) greater/smaller. A deque can drop from the front as the window moves, so it can answer "max of the last k" (Q81). That problem is illegal for a single stack because the max may leave the window while a smaller candidate remains.

### Q88. Expression evaluator that will grow `[A]`

45 minutes: tokenizer (Q75) + recursive descent for `expr → term ± term`, `term → number | (expr)`. Leave `call()` / units as an interface and a `Map<String, Function>`. Do not write a shunting-yard *and* an AST *and* a visitor. The extension hook is the parser method you can override, not a framework.

### Q89. Drops on `ArrayBlockingQueue` `[A]`

Start as a concurrency / backpressure question, not a stack question. `offer` returns false on full; `add` throws; `put` blocks. "Dropping" means someone used `offer` without a retry or used `DiscardPolicy` on a pool (Q223, S3). First question: which method, and is the consumer dead.

---

## 7. Linked lists, iterators and in-place pointer work

### Q90. Reverse a list

Iterative first: three pointers, O(1) extra.

```java
ListNode reverse(ListNode h) {
    ListNode prev = null;
    while (h != null) {
        ListNode n = h.next;
        h.next = prev;
        prev = h;
        h = n;
    }
    return prev;
}
```

Recursive `reverse(h.next)` then `h.next.next = h; h.next = null` uses O(n) stack. You write iterative unless they ask. Empty and single-node are identity.

### Q91. Cycle detection, Floyd

`slow` +1, `fast` +2. If they meet, a cycle exists. Proof: once both are in the cycle of length C, the gap of `fast - slow` grows by 1 each step modulo C and therefore hits 0. If there is no cycle, `fast` hits null. Do not dereference `fast.next` without a null check.

### Q92. Cycle entrance

After they meet, put one pointer back at the head; both walk +1. They meet at the entrance. Algebra: head-to-entrance A, meet-point M inside the cycle, `A + M = kC`, so walking A from the meet lands on the entrance. You do not need C.

### Q93. Merge two sorted lists

Dummy head, tail crawls. Dummy is not a crutch: it deletes the "first node is special" branch that produces null bugs. O(n+m) time, O(1) extra (iterative). Recursion is O(n+m) stack - refuse it on long lists.

### Q94. Remove nth from end, one pass

Dummy → head. `fast` walks n+1 steps (because of dummy), then `slow` and `fast` walk together. `slow.next = slow.next.next`. Dummy is mandatory when n equals the length (head removed). n larger than the list is a spec question - throw or no-op.

### Q95. Reverse in k-groups `[T]`

Count k nodes ahead; if fewer, leave the remainder. Reverse that run (Q90), stitch `prevTail.next` to the new head, and set `prevTail` to the run's old head (now the tail). Candidates lose the previous tail and orphan the rest of the list. Draw it.

### Q96. Copy list with random pointers

`IdentityHashMap<Node, Node>` from original to clone is the one you write: first pass clone nodes, second pass wire `next` and `random`. Weave-in-place (`orig.next = clone`, then split) is O(1) extra and assumes you may mutate the source list temporarily - ask. Do not use `HashMap` on a node that did not implement `hashCode` by identity; default is identity, but a value-based `equals` would break it. `IdentityHashMap` is the honest type (Q36).

### Q97. Add two numbers as lists

Reversed: dummy, carry, walk both. Forward: reverse both, add, reverse the result - or a stack each, then build the result from the LSD. The extra structure is the stack (or the reverse). Do not recurse on 10⁴-digit numbers.

### Q98. `java.util.LinkedList` `[T]`

Right as a `Deque` when you need mid-list splice *and* you already have the `ListIterator`. Wrong as a `List` you index: `get(i)` is O(n), and each node is a cache-miss. An `ArrayList` or `ArrayDeque` is the default. In a review, `new LinkedList<>()` without a splice is a comment.

### Q99. Flatten multilevel doubly linked list

DFS: for each node, if `child` exists, splice the flattened child between `node` and `node.next`, then continue. Recursion matches "child before next". An explicit stack of the saved `next` does the same without a second pass. Clear `child` after splice. Null `next` on the inner tail is the bug.

### Q100. Palindrome list

Slow/fast to mid, reverse second half, compare, reverse back. Restore because the caller did not give you the list. If they say not to restore, say you still would in production and skip it on the clock. Odd length: skip the middle node. O(n) time, O(1) extra.

### Q101. LRU skeleton

`Map<K, Node>` plus a doubly linked list, dummy head and tail. `get` moves the node to front; `put` on a live key updates and moves; eviction removes `tail.prev`. Full production walkthrough is Q251 / S12. Here you write the node and `moveToFront` correctly.

### Q102. Iterate and delete `[T]`

`Iterator.remove` is the legal way. `list.remove(i)` on an `ArrayList` is O(n) per delete (shift) so a filter loop is O(n²), and you must `i--` or walk backwards. `list.remove(i)` while using a for-each throws `ConcurrentModificationException`. `LinkedList.remove(i)` is O(n) to find plus O(1) unlink - still O(n²) for many deletes. Prefer `removeIf` or an iterator.

### Q103. O(1) splice of 10⁶ nodes `[A]`

You need the node itself, not an index: a real doubly linked list (or an intrusive list) so splice is pointer rewrites. You give up array locality and O(1) random access. Under a lock, do not walk 10⁶ nodes to find the cut; the caller must hand you the endpoints. `java.util.LinkedList` does not expose nodes, so you cannot O(1)-splice it from the outside.

### Q104. LRU with delete-by-key and peek-oldest `[A]`

`LinkedHashMap` in access-order plus `removeEldestEntry` is enough for get/put/evict. `remove(key)` is O(1). Peek-oldest without evicting is `iterator().next()` - that is O(1) at the head of a linked map and does *not* count as access if you use the entry iterator carefully; `get` of that key would refresh it. It is *not* enough when you need weighted size, TTL (Q246), or concurrency - then you write Q251 or use Caffeine.

---

## 8. Trees, BSTs and tries

### Q105. Traversals

Inorder of a BST is sorted order. Recursive is three lines; iterative inorder is a stack of the left spine, then pop/visit/go right. Preorder is visit then children; postorder is the one you get wrong iteratively - two stacks or a "last visited" pointer. Name which you are writing before you type.

### Q106. Depth and balanced in one walk

```java
int height(TreeNode n) {                 // -1 => unbalanced
    if (n == null) return 0;
    int L = height(n.left);  if (L < 0) return -1;
    int R = height(n.right); if (R < 0) return -1;
    if (Math.abs(L - R) > 1) return -1;
    return 1 + Math.max(L, R);
}
```

A separate `depth` plus a separate `balanced` is two walks. Interviewers notice.

### Q107. LCA

Binary tree: recurse; if both sides return non-null, `root` is the LCA; otherwise propagate the non-null. You are allowed to assume both nodes exist, or you must say you do. BST: walk from the root until `root` is between `p` and `q` (or equals one). Two independent searches plus a path compare also works and is worse.

### Q108. Serialize / deserialize

Preorder with a `#` (or `X`) null marker and commas. Inorder alone cannot distinguish structure. Level-order also works and matches LeetCode 297. Split on the delimiter you picked; `split(",", -1)` if you allow empties. Do not use Java serialization.

### Q109. Validate a BST

`left < root < right` on *children only* accepts a left-subtree node that is larger than the root. Thread a running `(lo, hi)` exclusive bound. Watch duplicates: the usual contract is strictly increasing; ask. `long` bounds avoid `Integer.MIN_VALUE` sentinels that reject a legal min-value node.

### Q110. BST iterator `[T]`

Stack holds the path to the next node: constructor pushes the left spine. `next` pops, then pushes the left spine of the popped node's right. Amortized O(1): each node is pushed and popped once. Memory O(h). `hasNext` is `!stack.isEmpty()`.

### Q111. Invert, flatten, next-right

All three are "rewire children, recurse (or BFS)". Invert is swap. Flatten (to a right-linked list) is postorder-ish: flatten right, flatten left, hang the old right off the left tail. Next-right is BFS, or the O(1)-space walk using the `next` you already set on the level above. Shared pattern: process a node, then the child pointers you still own.

### Q112. Path sums

Path-sum I: remaining target, return boolean. Path-sum II: same plus a mutable path you add/remove, copy into the result on a leaf hit. Maximum path sum: the helper returns the best *downward* gain from this node (or 0 if negative); the answer is a global max of `leftGain + node + rightGain`. The hard one is not "the path you are currently on".

### Q113. Build from preorder and inorder

Preorder head is the root. A map `value → inorder index` splits the inorder range into left and right in O(1). Recurse with a shrinking preorder index (or a pair of bounds). Duplicates break the map - the problem usually promises unique values. O(n).

### Q114. Morris traversal `[T]`

You temporarily set `predecessor.right = current` to thread the tree, then undo it. O(1) extra, O(n) time, mutates the tree while you walk. Never in production: a concurrent reader sees a cycle, an exception mid-walk leaves the thread in place, and the trick is unreadable. Mention it; do not propose it in a review.

### Q115. Trie

```java
final class Trie {
    static class N { final N[] c = new N[26]; boolean end; }
    private final N root = new N();
    void insert(String w) {
        N n = root;
        for (int i = 0; i < w.length(); i++) {
            int k = w.charAt(i) - 'a';
            if (n.c[k] == null) n.c[k] = new N();
            n = n.c[k];
        }
        n.end = true;
    }
    boolean search(String w) { N n = walk(w); return n != null && n.end; }
    boolean startsWith(String p) { return walk(p) != null; }
    private N walk(String w) { /* same loop, return null on miss */ }
}
```

`HashMap<Character, N>` wins on sparse / Unicode (Q120). Array of 26 wins on lowercase interview problems.

### Q116. Word search II

Insert the dictionary into a trie. DFS from every cell, walking the trie, marking the board visited. On `node.end`, add the word and set `end = false` (or delete the edge) so you do not report it twice. Prune empty trie branches. This is Q155 plus a trie, not 200 separate searches.

### Q117. kth smallest in a BST

Inorder and stop at k - O(h + k), simple. Augment each node with subtree size and jump - O(h) per query, O(n) extra, the structure you mention if they ask for many queries. Do not write the augmentation under a clock for one query.

### Q118. BST delete `[T]`

Leaf: unlink. One child: replace with the child. Two children: take the inorder successor (min of right), copy its value, delete the successor (which has no left child). The predecessor is symmetric. Losing the successor's right subtree is the bug. Parent pointers versus returning the new subtree root - return the root.

### Q119. File-path autocomplete `[A]`

If the set is static and queries dominate, a sorted list plus binary search on the prefix (lower bound of `prefix`, upper bound of `prefix + "\uffff"`) is simple and cache-friendly. If you insert and query equally, a trie (or a radix / PATRICIA tree) wins. Memory of a 26-way trie on paths is the reason you do not ship Q115 unmodified.

### Q120. 50 million Unicode prefixes `[A]`

A 26-array trie is the wrong machine. You ship a compressed trie (radix tree), an FM-index / suffix array if the set is static, or a search engine inverted-prefix (n-grams, finite-state transducer - what Lucene's automaton does). Call it an index, not "a HashMap of prefixes". Memory per edge is the design number you put on the board.

---

## 9. Heaps, top-K and streaming order statistics

### Q121. `PriorityQueue` basics

Default is a min-heap of natural order. Max-heap: `new PriorityQueue<>(Comparator.reverseOrder())` or `comparingInt(x -> -x)` only if you are sure `-x` cannot overflow (Q55). `poll`/`peek` on empty return `null`; `remove()` / `element()` throw. Not thread-safe (Q125).

### Q122. kth largest, size-k min-heap

```java
int findKthLargest(int[] a, int k) {
    PriorityQueue<Integer> pq = new PriorityQueue<>(k);
    for (int x : a) {
        pq.offer(x);
        if (pq.size() > k) pq.poll();
    }
    return pq.peek();
}
```

A max-heap of n is O(n) memory and O(n log n) to drain; you only needed k. Boxing is the Java tax - say it, do not write a raw `int` heap unless they ask.

### Q123. Merge k sorted lists

Heap of a `record Item(int val, int list, int idx)` (or the node itself). Seed with the head of each list; on pop, offer the next of that list. O(N log k) for N total elements. Null lists are skipped at seed. This is also the k-way merge of Q60.

### Q124. Median of a stream

Max-heap `lo` (left half), min-heap `hi` (right half). Invariant: `lo.size() == hi.size()` or `lo` has one extra; every value in `lo` ≤ every value in `hi`. Offer into `lo`, then move `lo.peek` to `hi` if order broke, then rebalance sizes. Median is `lo.peek` or the average of the two peeks. Integers: say whether you truncate the average.

### Q125. `PriorityQueue` is not those other things `[T]`

Not thread-safe: `PriorityBlockingQueue` or a lock. Not a bounded buffer: `ArrayBlockingQueue` (blocking, bounded) or a `PriorityBlockingQueue` *with* an external semaphore if you need priority *and* a bound. Using `PriorityQueue` as a work queue across threads is a CME / lost-wakeup waiting to happen.

### Q126. Top-K frequent

Count in a `HashMap`, then a size-k min-heap of entries, or bucket-sort: `List<Integer>[]` indexed by frequency (0..n). Bucket is O(n) when the frequency range is n; it is a memory bomb if you allocate `new List[maxValue]` on the *value* not the frequency. Heap is the default you write.

### Q127. Sliding-window median

Java's `PriorityQueue` cannot delete an arbitrary value in O(log n) - `remove(Object)` is O(n). Workarounds: lazy deletion (a `HashMap` of stale counts, skip on peek) or a `TreeMap<Integer, Integer>` multiset for each half. Write the `TreeMap` pair unless they let you lazy-delete. This is why Q124 does not drop straight into a window.

### Q128. Reorganize string / task scheduler

Heap of `(count, char)` (max-heap). Pop, place, decrement, park the just-used char for `cooldown` steps in a small queue, then return it to the heap. Task scheduler is the same with idle slots: `max(tasks.length, (maxCount-1)*(n+1) + nMax)`. Write the formula if they want the count; write the heap if they want the schedule.

### Q129. Heapify in O(n) `[T]`

`new PriorityQueue<>(collection)` calls `heapify`, Floyd's method, O(n). n times `offer` is O(n log n). You care when n is large and the collection already exists. `PriorityQueue(int capacity)` does **not** heapify an implicit array - it is just a size hint.

### Q130. K closest points

Size-k max-heap of squared distance, or quickselect (Q57) on `x*x + y*y`. Squared distance is mandatory so you do not take `sqrt` or compare doubles. Overflow: `x*x` on `int` can overflow - use `long`. Write the heap.

### Q131. Merge k huge iterators

Heap of a small cursor: the iterator and its current value. `hasNext` is `!heap.isEmpty()`. Close / do not leak: if the iterators are I/O, the merge object is `AutoCloseable` and closes all. Do not `Collectors.toList` first - that was the whole point.

### Q132. Running top-K over 24 hours `[A]`

Exact: time-bucketed maps (e.g. 24 hourly `HashMap`s of key→count) plus a heap on query, or a `TreeMap<timestamp, key>` you evict. Approximate: count-min sketch + a heap of candidates (what stream-processing libraries do). Heap-only of events does not expire cheaply. Pick buckets if they want exact; sketch if they want 10⁷ events/s.

### Q133. Heap plus delete-by-id `[A]`

`Map<Id, Node>` pointing into a binary heap (or a `TreeMap` of `(priority, id)`). Delete-by-id: look up, swap with last, `sift`. Or: lazy delete, skip stale ids on peek (Q127). Java's `PriorityQueue` does not give you the index, so you write the heap or you lazy-delete. Peek is O(1), insert/delete O(log n).

---

## 10. Graphs: traversal, topological order, shortest paths, union-find

### Q134. Graph representation

`List<List<Integer>>` when nodes are `0..n-1`. `Map<Integer, List<Integer>>` when they are sparse ids, strings, or not numbered. Weighted: `record Edge(int to, int w)`. Do not use an n×n `int[][]` at n = 10⁵. Say directed versus undirected (store both ways) before you type.

### Q135. BFS and DFS

BFS: `ArrayDeque`, mark visited *on enqueue* (or you get exponential re-expansion). Unweighted shortest path is BFS, not DFS. DFS: recursion or an explicit stack; visited on entry. Both are O(n + e). Grid: four (or eight) deltas, bounds check, then the same.

### Q136. Directed cycle

Three colours: white / grey (on the stack) / black (done). A grey neighbour is a back-edge, hence a cycle. A visited-only set cannot tell a back-edge from a cross-edge to a finished subgraph. Recursion-stack set is the same as grey.

### Q137. Undirected cycle

DFS with a `parent` argument: a visited neighbour that is not the parent is a cycle. Union-find: for each edge, if `find(u)==find(v)` it is a cycle, else `union`. You write union-find when you already need components (Q140); DFS when you already have the adjacency list and a single question.

### Q138. Topological sort, Kahn

In-degree array, queue of zeros, pop and decrement neighbours. A remaining positive in-degree means a cycle (and a partial order you cannot finish). DFS-finish-time is the other writing: push on exit, reverse the list. Kahn is the one you write because the leftover degrees *are* the cycle report.

### Q139. Course schedule, "just DFS" `[T]`

You need the grey state (Q136). A single `visited` will treat a node reachable by two legal paths as a cycle, or miss a cycle that goes through a "visited" node still on the stack. The interviewer who says "just DFS" is waiting for that sentence.

### Q140. Islands / components

Flood fill (DFS/BFS) from each unvisited `1`, count starts. Union-find on the `1` cells, union with right and down only to avoid double work, count roots. Union-find wins when edges arrive as a stream (dynamic connectivity) or you already have it; flood fill wins on a grid under a clock.

### Q141. Clone a graph

```java
Node clone(Node n) {
    if (n == null) return null;
    Map<Node, Node> copy = new IdentityHashMap<>();
    ArrayDeque<Node> q = new ArrayDeque<>();
    copy.put(n, new Node(n.val)); q.add(n);
    while (!q.isEmpty()) {
        Node u = q.poll();
        for (Node v : u.neighbors) {
            if (!copy.containsKey(v)) {
                copy.put(v, new Node(v.val));
                q.add(v);
            }
            copy.get(u).neighbors.add(copy.get(v));
        }
    }
    return copy.get(n);
}
```

Create the clone *before* you walk its neighbours. `IdentityHashMap` because node equality is identity (Q36, Q96).

### Q142. Dijkstra in Java

`PriorityQueue` of `(dist, node)`. No decrease-key: offer a new entry, ignore stale ones when `d > best[u]` on pop. Mark settled on pop, not on first sight (unlike unweighted BFS). Non-negative weights only. O((n+e) log n) with the stale-entry tax.

### Q143. Bellman-Ford and negatives `[T]`

Relax all edges n-1 times; one more success means a negative cycle reachable from the source. Mention it when weights can be negative or when "arbitrage" is the story. Dijkstra on a negative edge is *wrong*, not just slower - it can settle a node before a cheaper path exists. Do not "fix" Dijkstra with negatives.

### Q144. Union-find

```java
int find(int x) { return p[x] == x ? x : (p[x] = find(p[x])); }
boolean union(int a, int b) {
    int ra = find(a), rb = find(b);
    if (ra == rb) return false;
    if (r[ra] < r[rb]) { int t = ra; ra = rb; rb = t; }
    p[rb] = ra;
    if (r[ra] == r[rb]) r[ra]++;
    return true;
}
```

Path compression + union-by-rank is inverse-Ackermann, "effectively O(1)" - do not say O(1) as a theorem, say "I treat it as O(1) for this n".

### Q145. Word ladder

Implicit graph: words are nodes, an edge if they differ by one character. Neighbour generation is the cost: either mutate each position through `a-z` and test a `HashSet` (26·L), or pre-bucket on a wildcard key. Bidirectional BFS halves the depth. Begin/end not in the list is a guard.

### Q146. Alien dictionary

Compare consecutive words, find the first differing character, add that directed edge. Prefix contradiction: a longer word before its prefix (`apple` then `app`). Then Kahn (Q138); a leftover degree is a cycle, hence invalid. Multiple valid orders: any one, or `""` if they want "the" order and it is not unique - ask.

### Q147. Mutating the grid as visited `[T]`

Acceptable in a round when the problem gives you the grid and does not need it afterwards; say you are mutating. A bug when the caller reuses the grid, when `-1` is already a cell value, or when you must restore (some backtracking). Prefer a `visited[][]` unless they ask for O(1) extra.

### Q148. 20k-target incremental rebuild `[A]`

Store the DAG and the reverse DAG (dependents). On a change, BFS/DFS the dependents, mark dirty, Kahn-build only that subgraph. Cycle report is Q138 leftovers, as a list of names, not a boolean. Persist hashes of inputs so "changed" is content, not timestamps. This is `make` / Bazel, not LeetCode course-schedule.

### Q149. Time-dependent shortest path `[A]`

If waiting is allowed and the cost of departing at t is monotonic, Dijkstra still works with state `(node, time)` and edge weight `w(t_depart)`. You discretize time (seconds, minutes) or you keep time continuous and evaluate `w` as a function. State explosion is the design problem: bucket time, or bound the horizon. Plain Dijkstra-on-nodes is wrong because the cost of `u→v` is not a constant.

---

## 11. Recursion, backtracking and divide-and-conquer

### Q150. Subsets template

```java
void dfs(int i, List<Integer> path, List<List<Integer>> out, int[] a) {
    if (i == a.length) { out.add(new ArrayList<>(path)); return; }
    path.add(a[i]); dfs(i + 1, path, out, a); path.remove(path.size() - 1);
    dfs(i + 1, path, out, a);
}
```

Copy `path` into `out` - the live list will change. Choose / explore / unchoose is the sentence you say. O(2ⁿ · n) for n ≤ 20.

### Q151. Permutations

Used-array is the one you write: scan 0..n-1, skip used, mark, recurse, unmark. In-place swap (`swap(i, j)` for `j >= i`, recurse `i+1`, swap back) is shorter and easier to get wrong on duplicates. Duplicates: sort and skip a value that equals the previous and the previous was *not* used (or the swap family with a set at this depth).

### Q152. Combination sum

Reuse allowed: recurse `i` (same index) after pushing `a[i]`. Reuse forbidden: recurse `i+1`. Sort and skip duplicates at the same depth (`if (i>start && a[i]==a[i-1]) continue`). The index you pass *is* the rule; a `used[]` is the other writing of the same thing.

### Q153. N-Queens

`col[n]`, `diag[2n]`, `anti[2n]` (or three bitsets). Place row by row. A board scan per place is O(n) extra per attempt and is the slow version you mention only to reject. n=9 is the usual limit; bitsets make n=14 solvable.

### Q154. Generate parentheses `[T]`

Thread `(open, close)` used so far. Place `(` if `open < n`; place `)` if `close < open`. That prune *is* the algorithm: you never generate the illegal strings. 2n nested loops over `()()`… is the version that then needs a validator.

### Q155. Word search I

DFS from each starting cell, consume one character, mark, recurse four ways, unmark. The early `false` candidates forget to unmark is a leak into the next start. Bound: if the remaining word is longer than remaining cells, stop. This is not Q116.

### Q156. Sudoku solver

Find the emptiest cell (fewest candidates) first - that is the "make it finish" trick. For each candidate, place, recurse, undo; if a recursive call returns true, return true immediately. The `if (dfs()) return true` is the canonical "search, do not enumerate all".

### Q157. Merge sort and quicksort

Merge: two pointers into a buffer, O(n) extra, stable if you take left-on-tie. Quicksort: Hoare or Lomuto partition, no extra array, not stable, worst O(n²) on a sorted input if the pivot is `a[hi]` - randomize or take median-of-three. In a review you defend merge for stability and guaranteed bounds, quicksort for cache and in-place.

### Q158. Hidden O(n) stack `[T]`

A linked-list recursion or a skewed BST is n frames. Rewrite to iterative (Q90, Q110) when n is 10⁴+ or the JVM stack is the default 1 MB. If you do not have time, say *"this is O(n) stack; I would iterate before merge"* and leave it. Silence is the red flag.

### Q159. Phone letter combinations

Mapping `2→abc` … `9→wxyz`. Backtracking because the depth is the digits and the branching is 3–4; a nest of loops does not extend to 12 digits. Same template as Q150. Empty input → empty list, not a list of `""` - ask, LeetCode wants empty.

### Q160. Restore IP

At most four parts, each 0-255, no leading zero unless `"0"`. Prune when remaining chars cannot fill remaining parts (`left > 3*parts` or `left < parts`). Build with a `StringBuilder` or a list you join. `"25525511135"` has two answers; `"0000"` has one (`0.0.0.0`).

### Q161. Matcher that must grow backreferences `[A]`

Now: DP or NFA for the Q72 subset (`a`, `.`, `*`). Refuse backreferences in the same 45 minutes - they make the language non-regular; you need a backtracking engine with a capture map, and that is a library (Java `Pattern`) not an interview function. Say the extension point: an AST node for `Group` you do not implement today.

### Q162. User-supplied depth `[A]`

Bound the recursion (a `depth > MAX` throw), or rewrite to an explicit `ArrayDeque` so the heap holds the stack and you can cap memory. Org charts and BOMs are data, not trusted to be balanced. The iterative alternative is a stack of `(node, state)` so you can resume after a child. `StackOverflowError` is not an acceptable product behaviour.

---

## 12. Dynamic programming and greedy

### Q163. Three questions, climbing stairs

State: `ways(i)` = ways to reach step i. Recurrence: `ways(i) = ways(i-1) + ways(i-2)`. Base: `ways(0)=1`, `ways(1)=1`. Then it is Fibonacci, O(n) time, O(1) space with two variables. If you cannot say the three sentences you do not start a table.

### Q164. 0/1 versus unbounded knapsack

0/1: each item once - inner loop on capacity **downward** so you do not reuse `dp[c-w]` from this item. Unbounded: inner loop **upward** so you do reuse. That loop-order sentence is the whole distinction on a 1D array. 2D is obvious (`item × capacity`) and safer to write if you have the space.

### Q165. Longest increasing subsequence

O(n²): `dp[i] = 1 + max(dp[j] for j < i if a[j] < a[i])`. Write that first. Patience sorting: `tails[len]` is the smallest tail of any LIS of that length, binary-search each a[i], O(n log n). Mention the second; reconstruct the sequence from a `prev[]` if they ask.

### Q166. LCS and edit distance

`dp[i][j]` on prefixes. LCS: equal → `1 + dp[i-1][j-1]`, else max of skip. Edit: equal → copy diagonal; else `1 + min(insert, delete, replace)`. Rolling two rows (or one) drops space to O(min(n,m)). You cannot then reconstruct the alignment without more storage - say so.

### Q167. House robber family

Linear: `dp[i] = max(dp[i-1], dp[i-2] + a[i])`. Circle: max of "drop first" and "drop last". Tree: return `(rob_this, skip_this)` from each node; `rob_this = node + skip(left) + skip(right)`, `skip_this = max(left) + max(right)`. The state is "did I take the current node".

### Q168. Coin change versus coin change II `[T]`

Fewest coins: `dp[v] = min(dp[v], dp[v-c] + 1)`, any loop order of coins works for *min*. Number of *combinations*: outer loop coins, inner value upward - that way `{1,2}` is one combination. Outer value, inner coins counts permutations. This is the trap. Amount 0 is 1 combination and 0 coins.

### Q169. Unique paths with obstacles

`dp[i][j] +=` from above and left, zeroed on obstacles, `dp[0][0] = 1` if start is free. BFS would also count paths if you *sum* incoming, but BFS-as-shortest-path is the wrong reading: every path has the same length. Use BFS when the question is reachability or shortest *cost* on a graph; use this DP when the question is "how many".

### Q170. Palindrome DP

First fill `isPal[i][j]` by increasing length (`j-i`). Longest palindromic subsequence is LCS(s, reverse(s)), or `dp[i][j] = 2+dp[i+1][j-1]` when ends match. Palindrome partition uses `isPal` plus a 1D cut DP. Direction: length-up, or i downward, so `i+1,j-1` is already known.

### Q171. Greedy you can defend

Interval scheduling: sort by *end*, take if it starts after the last take - exchange argument (Q176). Huffman: two lightest, repeat, optimal prefix codes. Dijkstra: settle the closest unsettled, needs non-negative weights (Q142). The sentence is *"any better solution could swap this choice without getting worse"*, not "it looks greedy".

### Q172. Jump game versus jump game II `[T]`

I: scan, maintain `reach = max(reach, i+a[i])`, fail if `i > reach`. Greedy, O(n). II: min jumps is BFS on the array - the current jump's window, the farthest you can see, increment jumps when the window ends. A second greedy (farthest each jump) is that BFS in other clothes. Do not DP II in O(n²) unless n is tiny.

### Q173. Kadane as DP

`dp[i] = max(a[i], dp[i-1] + a[i])` is "best subarray *ending at i*". Keep one variable unless they want the subarray bounds, in which case you also store start indices. The array is for the lecture; the variable is for the paste.

### Q174. Decode ways

`dp[i]` = ways to decode the suffix (or prefix) starting at i. A `'0'` cannot start a code; `10` and `20` are legal, `30` is not. `11106` dies at `06`. Base: `dp[n] = 1`. Walk from the back so the 1- and 2-digit decisions are already computed. Empty string is 0 or 1 - LeetCode 0; say it.

### Q175. State too big `[A]`

40 items subset: meet-in-the-middle, 2²⁰ per half. 10⁴×10⁴ grid: drop a dimension (rolling row), or this is not DP (greedy / formula / sampling). Discretize values if only order matters (coordinate compression). The first move is "what can I forget", not a bigger machine.

### Q176. Exchange argument in two minutes `[A]`

State the greedy choice. Take an optimal solution that does *not* contain it. Show you can swap the greedy item in and the objective does not get worse, so there exists an optimal that *does* contain it. Repeat. If you cannot name the swap, you do not have a proof - you have a hope, and you say so.

---

## 13. Intervals, scheduling and sweep lines

### Q177. Merge overlapping intervals

Sort by start. Walk: if `cur.start <= last.end`, `last.end = max(last.end, cur.end)`; else append a new interval. Inclusive endpoints: `<=` is the merge (Q181). O(n log n) sort, O(n) extra for the output. Empty input is an empty list, not `null`.

### Q178. Insert an interval

One pass, no re-sort if the list is already sorted: emit everything that ends before the new start; merge everything that overlaps the new interval; emit the rest. Three regions, three loops or one loop with a state. O(n). If the list is *not* sorted, you are in Q177.

### Q179. Meeting rooms II

Sweep: for each interval push `(start, +1)` and `(end, -1)`, sort by time, **end before start** on a tie so a meeting that ends at t frees the room for one that starts at t. The running sum's max is the room count. Heap version: sort by start, min-heap of end times, pop if `heap.peek() <= start`, then push; heap size is rooms. Same answer.

### Q180. Can attend all

Sort by start (or by end). Adjacent pair: `a[i-1].end > a[i].start` is a clash. This is *not* rooms II - you only need a boolean. Sort-by-end is the greedy for "max number you can attend" (Q182), a different question. Ask which one they meant.

### Q181. Inclusive versus exclusive `[T]`

Ask. Calendar systems usually treat `[1,2)` and `[2,3)` as non-overlapping (Q179 tie-break). Closed intervals `[1,2]` and `[2,3]` overlap at 2. Writing `<=` versus `<` is the whole bug. Put the question in the first thirty seconds.

### Q182. Erase minimum to make non-overlapping

Sort by *end*. Take a interval if it starts at or after the last taken end; otherwise erase it. Sorting by start fails: a long early interval blocks many short later ones and you would keep the wrong one. This is Q171's interval scheduling, inverted ("erasures = n - taken").

### Q183. Sweep line as a pattern

An event is `(time, delta, tieBreak)`. Sort. Active set is a counter (rooms, car pooling) or a tree of buildings (skyline). Tie-break: process removals before additions at the same x when that matches the closed/open rule (Q181); skyline is its own (higher first on start, lower first on end). If you cannot name the event, it is not yet a sweep.

### Q184. Intersection of two sorted interval lists

Two pointers. `lo = max(a.start, b.start)`, `hi = min(a.end, b.end)`; if `lo < hi` (or `<=`, Q181) emit. Advance the interval that ends first. O(n+m). Do not build a sweep of 2(n+m) events unless the lists are unsorted.

### Q185. My calendar I / II / III

`TreeMap<Integer, Integer>` of delta at each time (the sweep stored as a map). I: reject if any existing interval overlaps - `floorKey` / `ceilingKey`. II: same map, running sum must not exceed 2 after a trial add; roll back if it does. III: the max running sum is k. `TreeMap` is the structure; a list plus linear scan is the n-small version.

### Q186. `a[0] - b[0]` on intervals `[T]`

Same overflow as Q55. `Integer.MIN_VALUE` starts exist in toy data less often than in production timestamps-as-ints, but TimSort will still throw if the comparator lies. `Arrays.sort(a, Comparator.comparingInt(x -> x[0]))`.

### Q187. 10⁷ bookings, range-free query `[A]`

A segment tree or fenwick on compressed coordinates, or an interval tree / implicit treap of free ranges. You give up cheap arbitrary deletes if you only store a bitmap of booked slots; you give up O(1) book if you store a balanced tree of free intervals (then book is split, O(log n)). 10⁷ means O(n) per query is dead. This is not `TreeMap` of 10⁷ keys on a 256 MB heap without thinking about constants.

### Q188. Staffing a rota `[A]`

Elicit: coverage required per slot, max shift length, rest rules, skills, fairness across people. The remaining algorithm is usually a sweep of demand plus a greedy or min-cost flow, not meeting-rooms. If they wanted meeting-rooms they would have given you intervals and a boolean. Say what you are *not* solving.

---

## 14. Bit manipulation, numeric correctness and overflow

### Q189. Two's complement

`-n` is `~n + 1`. `Integer.MIN_VALUE` has no positive counterpart in 32 bits: `-MIN_VALUE == MIN_VALUE`, and `Math.abs(MIN_VALUE)` returns the same negative (Q200). That is why a `negate` in a money path is `negateExact` or a `long`.

### Q190. Four bit one-liners

`get = (n >>> k) & 1`, `set = n | (1 << k)`, `clear = n & ~(1 << k)`, `toggle = n ^ (1 << k)`. k is 0-based from the right. `1 << k` for k=31 is `MIN_VALUE`; use `1L << k` if you then store in a `long`. `>>>` on get so a sign bit does not smear.

### Q191. Single number, XOR

XOR is associative, commutative, and `x^x==0`, so a fold of "everything twice, one once" is the one. Two singles: XOR all, take a set bit of the result (they differ there), partition the array by that bit, XOR each part. Do not sort.

### Q192. Popcount

`Integer.bitCount(n)` is the production call. Brian Kernighan: `for (; n != 0; n &= n - 1) c++;` is O(popcount). You write the loop if they banned the intrinsic. `n & (n-1)` drops the lowest set bit - that identity is also Q193.

### Q193. Power of two `[T]`

`n > 0 && (n & (n - 1)) == 0`. `n <= 0` must be rejected: `0 & -1 == 0`, and `MIN_VALUE` is `1 << 31` so `MIN_VALUE & (MIN_VALUE - 1) == 0` as well. Both would otherwise look like powers of two.

### Q194. Reverse bits

Loop 32 times: `out = (out << 1) | (n & 1); n >>>= 1`. Parallel: swap 16-bit halves, then 8, 4, 2, 1 with masks - mention, do not debug it under a clock. `Integer.reverse` exists; say so after you write the loop.

### Q195. Add without `+`

```java
int add(int a, int b) {
    while (b != 0) {
        int carry = (a & b) << 1;
        a = a ^ b;
        b = carry;
    }
    return a;
}
```

XOR is the sum without carry; `a & b` shifted is the carry. A single XOR is not enough when carry generates carry. Overflow wraps, same as Java `+`.

### Q196. Money in `double` `[T]`

`0.1 + 0.2 != 0.3`. `new BigDecimal(0.1)` *reproduces the double*, it does not fix it. Use `new BigDecimal("0.1")` or `BigDecimal.valueOf` on a long of minor units. This is S4 / Q201. `double` is legal for a *scientific* value you will never compare for equality.

### Q197. Integer division and `MIN / -1`

Java `/` on ints truncates toward zero. `Integer.MIN_VALUE / -1` overflows 32-bit two's complement; Java *returns* `MIN_VALUE` and does not throw. `Math.negateExact(Integer.MIN_VALUE)` throws. Know which one you are on in a money or index path.

### Q198. Fast exponentiation

```java
long modPow(long a, long e, long m) {
    long r = 1 % m;
    for (a %= m; e > 0; e >>= 1, a = a * a % m)
        if ((e & 1) != 0) r = r * a % m;
    return r;
}
```

If `m` is near 2⁶³, `a * a` overflows `long` - use `Math.multiplyExact` into a `BigInteger`, or a modular multiply. `e < 0` is a spec question (modular inverse, only if gcd(a,m)=1).

### Q199. UTF-8 validation

Count leading ones of the first byte: 0 → ASCII, 2/3/4 → that many total bytes; 1 or >4 is illegal. Each continuation is `10xxxxxx`. Overlong encodings and surrogates are invalid in the real spec; mention them if they want production, skip if they want the LeetCode bitmask.

### Q200. `abs(MIN_VALUE)` `[T]`

`Math.abs(Integer.MIN_VALUE)` returns `Integer.MIN_VALUE`. `Math.negateExact` / `absExact` (Java 17) throw `ArithmeticException`. Money path: `absExact` or promote to `long` first. Silent wrap is how a debit becomes a debit.

### Q201. Billing numerics `[A]`

Store integer minor units (`long` cents) or `BigDecimal` with a fixed scale and an explicit `RoundingMode` (usually `HALF_EVEN` for money, and the *same* mode everywhere). The test that catches Q196 is `assertEquals(0, new BigDecimal("0.1").add(new BigDecimal("0.2")).compareTo(new BigDecimal("0.3")))` plus a million-add loop that would drift in `double`. Never `equals` on `BigDecimal` without `compareTo` (scale differs). Incident: S4.

### Q202. 10⁸ flags `[A]`

`BitSet` is the JDK default: `set`/`get`/`cardinality`/`nextSetBit`. `long[]` is the same idea with more control. 10⁸ bits is 12.5 MB - fine. Roaring (or a sparse bitset) wins when the set bits are clustered or very sparse and you union them a lot. Do not `boolean[100_000_000]` - that is 100 MB plus headers, and a review comment.

---

## 15. Java API fluency under time pressure

### Q203. `List.of` / `Map.of`

Unmodifiable, no `null` (NPE on `of` and on later `list.add`). `Map.of` caps at 10 entries; `Map.ofEntries` does not. `new ArrayList<>(List.of(a, b))` is the mutable copy you want when you will add. `Arrays.asList` is fixed-size (set ok, add throws) and reflects array writes.

### Q204. `record` as DTO and key

Generates ctor, accessors, `equals`/`hashCode`/`toString`. Does **not** defensive-copy: a `record R(List<String> xs)` is mutable through `xs`. As a map key, the components you hash must not change (Q33). Compact ctor is where validation goes.

### Q205. `Optional`

Return type for "maybe". Never a field, never a parameter, never `Optional<T>` in a collection. `orElse(expensive())` always evaluates the argument; `orElseGet` is lazy. `get` without `isPresent` is a review comment; use `orElseThrow`. Do not `optional != null`.

### Q206. Streams under a clock

Write a stream for a map/filter/collect that fits on three lines. Write a loop for anything with an early return, a running pair of values, checked exceptions (Q212), or a performance bound you must name. `reduce` that is really a `max` / `sum` should be `max` / `mapToInt.sum`. Interviewers read a 15-line stream as avoidance.

### Q207. Stream over a mutating list `[T]`

Non-concurrent streams are fail-fast on structural mutation: `ConcurrentModificationException`, or worse, a silent miss. `toList()` (unmodifiable copy of the *output*) does not snapshot the *source*. Another thread mutating the source is a data race, not a stream feature. Concurrent source: `CopyOnWriteArrayList` or a snapshot.

### Q208. `equals` / `hashCode` / `compareTo`

`record` does the first two. A class: `Objects.equals` / `Objects.hash` on the same immutable fields. `compareTo` must be consistent with `equals` (Q58): `compare == 0` iff `equals`. Do not include mutable or derived fields. Do not use `==` on boxed values (Q3 of `01-java`).

### Q209. Comparator nulls `[T]`

`Comparator.comparing(Foo::getName)` NPEs when `getName()` is null, *inside* `comparing`, not at sort start. `comparing(Foo::getName, nullsFirst(naturalOrder()))` is the fix. `nullsFirst` on the *outer* comparator handles null *elements*; that is a different null.

### Q210. `EnumSet` / `EnumMap`

Bit-vector / array, no hash, no boxing of the key. Default in a review whenever the key is an enum. `HashSet<MyEnum>` is a smell unless the set is transient and tiny. `EnumSet.noneOf` / `allOf` / `complementOf` are the constructors; there is no public ctor.

### Q211. Deque / list rule

Stack or queue: `ArrayDeque`. Random access or append-only list: `ArrayList`. `LinkedList` only for mid-list splice when you already hold an iterator (Q98). That is the one-line rule. `Stack` and `Vector` are historical.

### Q212. Checked exceptions in `map`

Production: a small private helper that wraps in an unchecked domain exception, or `map` to a result type. Refuse sneaky-throw utilities and `e -> { throw new RuntimeException(e); }` as a habit - they erase the type the caller needed. In a 45-minute round, a loop with a `try` is cleaner than a stream you have to apologize for.

### Q213. Three special maps `[T]`

`IdentityHashMap`: identity keys, graph clone (Q141). `WeakHashMap`: keys GC-able; values are *strong* - a value pointing back at its key pins it. `ConcurrentHashMap`: concurrent writers, no `null` keys or values, aggregates are weakly consistent. One sentence each is enough; the weak-key gotcha is the follow-up.

### Q214. Formatting

Logs: `String.formatted` or a text block, never `NumberFormat` on a hot path (it is mutable and not thread-safe). Money: `BigDecimal.setScale(2, rounding)` then `toPlainString`, or a `DecimalFormat` *cloned per use* / `NumberFormat.getInstance` carefully. Do not `double` format a currency (Q196).

### Q215. Array `equals`

`==` is identity. `array.equals` is identity (`Object.equals`) - a famous trap. `Arrays.equals` is shallow; `Arrays.deepEquals` for nested arrays. In a test: `assertArrayEquals`. This is the stream-adjacent "I thought I compared contents" bug.

### Q216. Twenty minutes in their codebase `[A]`

Introduce: text blocks for the SQL/JSON you already touched, `var` on the obvious local, a `record` for the tuple you were about to write a class for, `switch` expressions if one is mid-edit. Leave: a virtual-thread migration, a stream rewrite of a working loop, `Optional` wrapping of every return. The diff should look like you were there to solve *their* ticket.

### Q217. Ten rules you would enforce `[A]`

No `null` in new APIs (`Optional` return or a zero value). Collections: Q211. Exceptions: wrap at the boundary, never swallow. Streams: Q206. Concurrency: no `synchronized` on a public type, no `newCachedThreadPool` (Q224), document the thread-safety of every public type. `equals`/`hashCode` together. Money not in `double`. No `Stack`. Tests do not read `now()` (Q263). Reviews label blocking versus preference (Q266).

---

## 16. Concurrency coding exercises

### Q218. Three counters

`synchronized` on a private final lock: simple, exclusive. `AtomicInteger`: CAS, the default for a single counter. `LongAdder`: striped, the default under high contention on a hot increment (metrics). Ship `LongAdder` for rates; `AtomicInteger` for a size you also `get`; synchronized for a compound invariant a single atomic cannot hold.

### Q219. `wait` / `notify` bounded buffer

```java
synchronized void put(T x) throws InterruptedException {
    while (n == a.length) wait();
    a[t++ % a.length] = x; n++;
    notifyAll();
}
synchronized T take() throws InterruptedException {
    while (n == 0) wait();
    @SuppressWarnings("unchecked") T x = (T) a[h++ % a.length];
    n--; notifyAll();
    return x;
}
```

`while`, not `if` - spurious wake and multiple waiters. `notifyAll` is the safe default because `put` and `take` share one wait-set; two conditions want two locks or a `Condition` each (Q239). Restore interrupt on catch if you swallow.

### Q220. Latch versus one-shot future

`CountDownLatch` is a one-shot gate: `countDown` / `await`. `CompletableFuture` is a one-shot *value*: `complete` / `join`, plus a pipeline (Q221). The future is cleaner when the waiter needs the result or a composition; the latch is cleaner when N workers must all finish and there is no value. Neither resets - that is `CyclicBarrier` / `Phaser`.

### Q221. `CompletableFuture` compose

```java
cfA.thenCompose(a -> callB(a))          // flatMap: B returns a CF
  .thenCombine(cfC, this::merge)
  .exceptionally(ex -> fallback)
  .handle((v, ex) -> ex == null ? v : fallback);
```

`thenApply` is map; `thenCompose` is flatMap - using apply when B returns a CF nests the futures. Default executor is `ForkJoinPool.commonPool()` (or the completing thread for some stages); a named pool is what you ship. `thenApplyAsync` if you mean it.

### Q222. `join` / `get` / `orTimeout` `[T]`

`get` throws checked `ExecutionException` / `InterruptedException` and *clears* the interrupt flag - restore it. `join` throws unchecked `CompletionException` and does not deal in interrupts the same way. `orTimeout` completes *the receiver* exceptionally with `TimeoutException` and does not cancel the work unless you also `cancel`. Know which one you are wrapping.

### Q223. `ThreadPoolExecutor` you would ship

```java
new ThreadPoolExecutor(
    core, max, 60, TimeUnit.SECONDS,
    new ArrayBlockingQueue<>(bound),
    namedFactory,
    new ThreadPoolExecutor.CallerRunsPolicy());
```

`CallerRuns` is backpressure onto the submitter. `Abort` is a metric plus a 429. `Discard` / `DiscardOldest` lose work - say so if you pick them (S3). Unbounded queue + `max` is a lie: `max` is never reached (Q233).

### Q224. `newCachedThreadPool` `[T]`

`SynchronousQueue`, `max = Integer.MAX_VALUE`: every submit with no idle thread creates a thread. A burst creates tens of thousands; idle threads die after 60s, not immediately. On a request path this is an accidental fork-bomb. Write Q223. Cached is acceptable for a short-lived CLI, not a service.

### Q225. Virtual threads

`Thread.startVirtualThread` / `Executors.newVirtualThreadPerTaskExecutor` for blocking I/O. You still need a semaphore (or a bounded pool of *something*) when the other side cannot take 100k concurrent calls - a DB pool of 20, an API quota. Pinning: a virtual thread inside `synchronized` or a JNI call cannot unmount; prefer `ReentrantLock` in new code if the critical section blocks. Measure, do not assume.

### Q226. Thread-safe cache with TTL

Naive: `ConcurrentHashMap<K, record E(V v, long exp)>`, `get` checks `now < exp`. Races still there: two loads of the same missing key (thundering herd), and expired entries you never evict (leak) unless a janitor or `compute` on access. Caffeine does both. Write the naive, name the two races, do not pretend it is Caffeine.

### Q227. Lock ordering

Always acquire locks in a global order (e.g. `System.identityHashCode`, with a third lock on a hash collision). `tryLock` + backoff is the alternative when you cannot order (S2). Document the order in one comment. Dining philosophers is this problem in costume.

### Q228. `synchronized (boxed)` `[T]`

`Integer.valueOf` caches -128..127, so `synchronized (id)` on a small id is a *global* lock shared with every other tenant who used that id. Interned strings are the same accident. Lock on a private `final Object lock = new Object()` you own, or on the domain object whose monitor is documented.

### Q229. 10k fan-out, capped

```java
Semaphore cap = new Semaphore(64);
List<CompletableFuture<V>> all = ids.stream()
    .map(id -> CompletableFuture.supplyAsync(() -> {
        cap.acquireUninterruptibly();
        try { return call(id); } finally { cap.release(); }
    }, pool)).toList();
CompletableFuture.allOf(all.toArray(CompletableFuture[]::new)).join();
```

Cap *inside* the task so the pool queue does not hold 10k started permits. `allOf` then join; a timeout on the `allOf` (Q222) is the production wrapper.

### Q230. Happens-before you can use

Unlock of M happens-before a later lock of M: the bounded buffer (Q219) is correct *because of this*, not because of `volatile n`. Volatile write happens-before a subsequent read of that field. `Thread.start` happens-before the first action in the thread; the last action happens-before `join` returns. `CF.complete` happens-before dependents. One line of code each is the answer; a JMM lecture is not.

### Q231. Worker pool for a 100× burst `[A]`

Bounded queue (Q223), `CallerRuns` or a shed that returns 429 with a retry-after, a metric on queue depth and reject count, and a heap-based kill switch. Losing tasks silently (`Discard`) is not absorbing. OOM is the unbounded-queue failure (S3 / Q233). Virtual threads still need a bound on the *downstream*.

### Q232. Two-lock cache deadlock `[A]`

Reproduce: thread 1 holds the map lock, waits for entry lock; thread 2 holds that entry, waits for the map lock. Whiteboard the two stacks. Replace with one lock, or with `ConcurrentHashMap.compute` (per-key serialization, no outer lock), or with Caffeine. Never take locks in opposite orders (Q227). Incident: S2.

### Q233. Unbounded queue filled the heap `[A]`

Replacement: `ArrayBlockingQueue` of a size you can defend (seconds of work, not days), a rejection policy you can observe, and a producer that *backs off*. The story is backpressure, not a bigger heap. `LinkedBlockingQueue()` has capacity `Integer.MAX_VALUE`. Incident: S3.

### Q234. Migrate a 200-thread pool to virtual threads `[A]`

Measure first: is the pool blocking on I/O (yes → virtual) or burning CPU (no → keep a sized pool)? Delete the pool that exists only to park waiters. Keep a semaphore in front of the JDBC pool and any rate-limited client (Q225). Keep the timeout. Pinning and thread-local caches (inherited `ThreadLocal` of a 200-slot thing) are what you hunt in week one.

---

## 17. Design and implement

### Q235. What "design and implement" scores

API (names, what throws, what is thread-safe), invariants (capacity, TTL, uniqueness) stated before code, concurrency chosen on purpose, and one test that would fail if the invariant slipped. A LeetCode problem scores a function. This scores a type someone else will import. Write the signature and the invariant in the first five minutes.

### Q236. Parking lot / deck of cards

Types carry rules: `Spot` holds a `Vehicle` of a matching `Size`; `Deck` deals from a `List<Card>` and does not expose `remove(i)` to callers. Refuse a `ParkingLotManagerServiceImpl` that also bills, opens the gate and sends email. 45 minutes: the objects and one happy-path method, not a framework.

### Q237. In-process event bus

`Map<Class<?>, List<Handler>>`, `subscribe` / `publish`. Sync handlers run on the publisher's thread - a slow one stalls everyone; isolate with a per-subscriber queue or an executor, and a rejection policy (Q223). Exceptions in a handler must not abort the others. Weak refs if you do not own unsubscription. This is not Kafka; say so.

### Q238. Retry with jittered backoff

```java
<T> T retry(Callable<T> c, Predicate<Exception> retryOn, int max, long baseMs) {
    ThreadLocalRandom rnd = ThreadLocalRandom.current();
    for (int i = 0; ; i++) {
        try { return c.call(); }
        catch (Exception e) {
            if (i == max || !retryOn.test(e)) sneak(e);
            long cap = baseMs << Math.min(i, 16);
            Thread.sleep(cap / 2 + rnd.nextLong(cap / 2 + 1));
        }
    }
}
```

Never retry a non-idempotent POST without an idempotency key, and never retry a 4xx that will not change. Full library is Q255 / S16. Jitter is not optional - synchronized retries are a thundering herd.

### Q240. Thread-safe ring of last N

`synchronized` on a Q86 ring, or a `synchronizedList` you do not want. Many writers, one reader: a single lock on `offer` plus a snapshot `toArray` for the reader is enough at modest N. For high ingest, a disruptor / many-to-one queue and a draining reader. Do not hand out the live array.

### Q241. Token bucket, one process

Fields: `capacity`, `refillPerSec`, `tokens` (double or long micros), `lastNanos`. `tryAcquire(n)`: refill `min(capacity, tokens + (now-last)*rate)`, then grant if `tokens >= n`. Clock: `nanoTime`, not `currentTimeMillis` (it jumps). Not distributed - say it (Q252 is the production one).

### Q242. Sliding-window log limiter

Store timestamps of accepted events in a deque; evict `< now - W`; accept if `size < limit`. More accurate than a bucket at the window edge; more memory (one long per event). Pick the bucket when you need cheap `tryAcquire` and a little burstiness is fine; the log when compliance said "no more than N in any W".

### Q243. LRU `get`/`put` O(1)

`HashMap<K, Node>` + doubly linked list, dummy ends, `moveToFront`, evict `tail.prev`. Lock: one `synchronized` for the toy; a `ReentrantLock` you document for the library. Full production (capacity 0, null policy, concurrency, metrics) is Q251 / S12. Here the invariant is "map size == list length".

### Q244. LFU versus LRU

LFU needs frequency → a map of freq to a linked list of nodes, plus the key map; min-freq is a counter you bump when a list empties. LFU is the wrong default when traffic is a scan (a one-time pass evicts the working set) or when recency *is* the signal. LRU is the default you write; LFU when a known hot set is stable.

### Q245. Snowflake, one process

`id = (ts - epoch) << 22 | (worker << 12) | seq`. 41 bits time, 10 worker, 12 sequence is the usual split - say yours. Same-millisecond: `seq++`; overflow: wait for the next millisecond. Clock went backwards: refuse to issue (throw) or wait; do not emit a duplicate. Worker id is an argument, not `random`.

### Q246. KV with TTL and size eviction

Two indexes: `HashMap<K, Node>` and a recency list (LRU) or a `TreeMap<exp, K>` for eager expire. Lazy expire: check on `get`/`put`, plus a sample on each write so the map cannot fill with dead keys. Eager: a delay queue / janitor. Lazy is what you write in 45 minutes; name the leak if you skip the sample.

### Q247. Service locator `[T]`

Implement a constructor-injected object, or a small factory with an interface. Say *"I will not add a global `Services.get()`; it makes tests lie and hides the graph"*. If they insist on the sketch, write it as a `Map<Class<?>, Object>` and then say what you would delete before merge. Do not lecture for five minutes.

### Q248. Flatten nested list iterator

Stack of `Iterator<NestedInteger>`. `hasNext` advances until the top is an integer (or the stack is empty): while top is a list, push its iterator; while top is exhausted, pop. `next` calls `hasNext`, then returns `stack.peek().next().getInteger()`. The bug is doing the advance in `next` only, so a trailing empty list lies.

### Q249. Range module

`TreeMap<Integer, Integer>` of start → end, disjoint and coalesced. `add`: find overlapping via `floorKey`, merge, delete covered keys, insert the union. `remove` splits. `query`: `floorKey` and `end >= right`. O(k log n) per op for k overlaps. This is Q185's cousin with explicit remove.

### Q250. Library API for 40 teams `[A]`

Document thread-safety ("this type is immutable" / "one thread"). Nullability: `package-info` + `@Nullable`, no silent NPE. Compatibility: no removing methods, no widening throws, no changing `equals`. Javadoc carries the invariant (capacity, TTL units, what `null` means). A preview package is allowed; a breaking v2 in week three is not. Q217 is the style; this is the contract.

---

## 18. Clean code, refactoring, review and testing

### Q256. What you keep in 45 minutes

Keep: names that match the problem, a helper for a second use, a guard on null/empty, the complexity sentence. Drop: a logging facade, a strategy interface, generics that take five minutes, comments that restate the line. Say the drop out loud (Q13). Mock Q153 is the same list from the *round* side.

### Q257. Tests in a live round

Three, after the first green path, not before you have a loop: one happy example from the prompt, one edge (`[]`, `null`, `k=0`, `MIN_VALUE`), one invariant (round-trip, `size` vs eviction, "result is sorted"). Write them as `assert` or a `main`. TDD theatre of twelve tests on an empty method wastes the clock.

### Q258. Three katas on twenty lines

Extract method: the inner loop that had a name in your mouth. Parameter object: the four booleans that travel together become a `record`. Replace type code: `int kind` plus a switch becomes a small type with behaviour. Do them one at a time, tests green in between (Q261). Do not rename everything first.

### Q259. 200-line method, three flags

Split on the flags first: three methods, not one method with a clearer name. Do not rename while the behaviour is still wrong - you will rename the bug. Characterization test (Q261) on the whole method, then extract. Live, you narrate *"I am isolating the `isRetry` path so I can see it"*.

### Q260. Optional field, null return, empty catch `[T]`

First: the empty catch - that is a production incident. Then the null return versus `Optional` inconsistency: pick one for *this* type and say which. Leave the `Optional` field if the clock is short and it is not on the path you were asked to change; put it on the list. Ordering is judgement; a tour of every smell is a failed review (mock Q172).

### Q261. Characterization tests

Pin *observable* behaviour: outputs, thrown types, order if it is part of the contract, not internal call counts. A test of a function you are about to delete should live on the façade you are keeping. Gold-plating is asserting on log lines and private state. Golden files are fine when the output is a blob; name them as characterization, not as spec.

### Q262. Mutation versus coverage

100% lines can miss `x + 1` versus `x` if no assertion read the value. A useful mutation: flip a condition, off-by-one a bound, drop a `break`, replace `&&` with `||`. If the suite stays green, the suite is the bug. You do not run PIT in a 45-minute round; you *name* one mutation you would apply to this method.

### Q263. Flaky tests

`Instant.now()`: inject a `Clock`. HashMap order: assert as a set, or use `LinkedHashMap` if order is the contract. Shared statics: isolate with a new classloader or (better) do not use them. Real I/O: a fake or a temp dir you delete. The fix is determinism, not a retry rule. A `@RepeatedTest` that "usually passes" is not a fix.

### Q264. Security bug in pairing `[T]`

Name it, label it blocking, estimate blast radius in one sentence, offer to park a failing test, and *return to the ticket they asked you to do* unless they steer. A 20-minute lecture on OWASP is a failed pairing even when you are right. Mock Q169 is the architecture-review version of the same muscle.

### Q265. What a principal comments on

API shape (will 40 teams have to live with this name), failure modes (what does this do when the dependency is slow), and the cost of the happy path (an extra allocation on 10 kRPS, a sync call inside a virtual thread that pins). Seniors find the NPE. Principals find the design that will still be wrong when the NPE is gone.

### Q266. A ten-line review standard `[A]`

Blocking: correctness, security, data loss, unbounded resource, a missing test on the invariant. Non-blocking: naming, a simpler structure, a missed library call. Question: "did you consider X" - not a demand. Preference: style the linter should have owned. Every comment labelled. No "nit:" that is actually blocking. How you *land* this across teams is Q267 / S17.

---


