# Coding Interview Questions

Questions are numbered continuously (`Q1`, `Q2`, ...) so that [answers.md](answers.md) can reference them directly.

Difficulty legend:

- `[C]` Core - you must answer this instantly and correctly.
- `[D]` Deep - expected of a senior engineer, requires mechanism-level detail.
- `[T]` Tricky - designed to catch you out; the obvious answer is usually wrong.
- `[A]` Architect - no single right answer, judged on trade-off reasoning.

Each category opens with an **Assumed known** line pointing at the pack that owns the prerequisite depth. [15-mock-interviews](../15-mock-interviews/questions.md) Category 11 owns the coding *round* as behaviour. This pack owns the *substance* you type.

**What this pack is about.** You still write code in a principal loop. The problem is usually easy. The score is on whether the code is correct under the cases the interviewer will supply, whether you chose the structure a reviewer would keep, and whether you can say the complexity and the cost of the alternative in the same breath.

The six design-and-implement questions Q239 and Q251-Q255 are run as full walkthroughs in [scenario-questions.md](scenario-questions.md) Part B. Q267-Q270 have no scripted answer on purpose - they must be your own stories; Part C says how to build them.

---

## 1. How a coding solution is judged, and complexity as a design tool

> Assumed known: [../15-mock-interviews](../15-mock-interviews/questions.md) Q148-Q162 (how the coding round is run) and the four-layer answer in [../01-java/README.md](../01-java/README.md). This category is about what "good code in 45 minutes" actually means.

1. `[C]` What four things is a principal-level coding solution scored on, in order, and why is cleverness not one of them?
2. `[C]` State Big-O for time and extra space, and say what each of O(1), O(log n), O(n), O(n log n), O(n²) and O(2ⁿ) means for n = 10⁵ in a 45-minute round.
3. `[D]` Best, average and worst case. When does quoting only the average case lose you the follow-up, and when is the average the number that matters?
4. `[D]` Amortized versus worst-case. Explain `ArrayList.add` and `HashMap.put` in those terms, and say when you would refuse the amortized story.
5. `[T]` "This is O(n)." The interviewer asks "of what?" What are you expected to name, and what happens if you cannot?
6. `[D]` Time-space trade-off: give three production examples where you spent memory to buy time, and one where you did the opposite.
7. `[D]` What does "in-place" actually mean in Java, and why is swapping inside the input array still not free?
8. `[T]` Two solutions: O(n) time with O(n) space, and O(n log n) time with O(1) extra space. Which do you write first, and what do you say about the other?
9. `[D]` How do you pick a data structure in the first three minutes? Walk the decision: access pattern, uniqueness, order, mutation, concurrency.
10. `[D]` When do you write a brute-force solution on the board first, and when is that a waste of the clock?
11. `[T]` You quote O(n) and the interviewer shows an input that makes it O(n²). What did you miss, and how do you recover?
12. `[D]` Recurrence relations: solve merge sort, binary search and the naive recursive Fibonacci out loud, and say which one you would never ship.
13. `[A]` The interviewer says "production quality". What do you keep, what do you consciously drop, and how do you say that out loud so it is a judgement rather than an excuse?
14. `[A]` Design a 45-minute budget for a medium problem: clarifying, brute force, optimal, tests, complexity. Where do 19-year candidates usually blow it?

---

## 2. Arrays, two pointers, sliding window, prefix sums

> Assumed known: [../01-java](../01-java/questions.md) collections material and `Arrays`/`System.arraycopy`. This category is about the patterns you type, not the language.

15. `[C]` Two-sum in a sorted array. Write the two-pointer solution and state why a hash map is the wrong first move here.
16. `[C]` Reverse an array in place. Write it, and say what changes if the element type is a boxed `Integer`.
17. `[D]` Remove duplicates from a sorted array in place, returning the new length. What does "in place" require you to do with the tail?
18. `[D]` The sliding-window template: when is the window fixed, when is it variable, and what is the loop invariant you state out loud?
19. `[C]` Maximum sum of a subarray of length k. Write the fixed-window version, not the Kadane version.
20. `[T]` Longest substring without repeating characters. Where do candidates off-by-one, and what is the invariant that prevents it?
21. `[D]` Minimum window substring. State the owed-count trick and write the shrink step.
22. `[D]` Kadane's algorithm: maximum subarray sum. Write it, then say what changes for "maximum product" and why that is not the same idea.
23. `[D]` Prefix sums: range sum in O(1) after O(n) preprocess. Write `prefix[i]` as "sum of the first i", and show the off-by-one that interviewers wait for.
24. `[T]` Subarray sum equals k, with negatives allowed. Why does a sliding window fail, and what does the prefix-frequency map actually store?
25. `[D]` Product of array except self, without division. Write the two-pass version and the O(1)-extra-space version, and say what "O(1) extra" is allowed to ignore.
26. `[D]` Dutch national flag: sort an array of 0, 1, 2 in one pass. Write the three-pointer version and name the invariant for each region.
27. `[T]` Rotate an array by k places, in place. Give the reversal method, and the bug when `k > n` or `k` is negative.
28. `[D]` Trapping rain water. Explain the two-pointer height argument, and why a stack solution is the one you mention but do not write first.
29. `[D]` Merge two sorted arrays where the first has unused tail capacity. Write it from the back, and say why from the front is wrong.
30. `[A]` You are given a 10⁸-element stream and must maintain the sum of the last k distinct values. Design the structure and the complexity.

---

## 3. Hashing, counting and Java `Map`/`Set` idioms

> Assumed known: [../01-java](../01-java/questions.md) Q1-Q2 (`equals`/`hashCode`) and `HashMap` internals. This category is about using those collections under a clock.

31. `[C]` Two-sum in an unsorted array. Write the one-pass `HashMap` and name the "use yourself" trap.
32. `[C]` Group anagrams. What is the key, why is a sorted `char[]` acceptable, and when do you count letters instead?
33. `[T]` You put a mutable key into a `HashSet`, then mutate a field used by `hashCode`. What can you still observe, and what can you not?
34. `[D]` `computeIfAbsent` versus `get` then `put`. Write the frequency-map idiom, and the nested-map idiom that `computeIfAbsent` makes safe.
35. `[D]` `LinkedHashMap` as an insertion-order list and as an access-order LRU. Which methods trigger access order, and which do not?
36. `[T]` `IdentityHashMap` and `EnumMap`. When is each the right tool, and what bug does `IdentityHashMap` hide if you used it by accident?
37. `[D]` Counting sort versus a `HashMap<Integer, Integer>` frequency table. When is the array faster, and when is it a memory bomb?
38. `[D]` First unique character in a stream. Design it, then the "first unique in a string" interview version.
39. `[D]` Longest consecutive sequence in O(n). Why does the "only start from the left edge" trick make the inner loop honest?
40. `[T]` `map.get(key) == null` versus `!map.containsKey(key)`. When are they different, and which one do you write in a frequency map that stores zero?
41. `[D]` Anagram of a substring, permutation-in-string. Write the sliding window over a 26-slot count, and the early-exit condition.
42. `[D]` Design a `Set` of pairs without allocating a wrapper class. What do you do instead, and when is that a mistake?
43. `[D]` Collision behaviour you can actually observe: many keys with the same hash. What happens to `get` in Java 8+, and what do you say if asked to force it?
44. `[A]` A service is seeing `HashMap` get/put at 40 µs instead of 40 ns. Walk the diagnostic: load factor, hash quality, GC, resize, and the rewrite you would actually ship.
45. `[A]` Multiset, bidimap, and "map of lists" keep appearing. When do you pull in Guava or a record, and when do you keep a raw `HashMap`?

---

## 4. Sorting, binary search and binary-search-on-answer

> Assumed known: [../01-java](../01-java/questions.md) `Comparable`/`Comparator` and `Arrays.sort` dual-pivot / TimSort. This category is about search over a sorted domain.

46. `[C]` Write binary search over a sorted `int[]` that returns the index or `-1`. State the loop invariant and the overflow-safe `mid`.
47. `[D]` Lower bound and upper bound. Write both, and say which one `Arrays.binarySearch` is *not*.
48. `[T]` `(lo + hi) / 2` versus `lo + (hi - lo) / 2`. Show the overflow, and say whether it still happens with `int` indices in a normal round.
49. `[D]` Search in a rotated sorted array. How do you decide which half is sorted, and what does a duplicate do to the argument?
50. `[D]` Find the first and last position of a target. Why is this two binary searches, not one plus a scan?
51. `[T]` Binary search on a `double` domain. What is the termination condition if you cannot test equality, and what goes wrong with a fixed iteration count that is too small?
52. `[D]` Binary-search-on-answer: koko eating bananas / capacity to ship packages. What makes a predicate monotonic, and how do you prove it in one sentence?
53. `[D]` Median of two sorted arrays. Sketch the partition approach and the invariant on the left-half count.
54. `[D]` `Arrays.sort` on `int[]` versus `Integer[]` versus `Object[]`. Why are the algorithms different, and when does that change your complexity story?
55. `[T]` A `Comparator` implemented as `return a - b`. Show the overflow, and write the replacement.
56. `[D]` When do you sort as a preprocessing step to make a later linear scan legal? Give three problems where the sort is the whole trick.
57. `[D]` kth largest via sort versus quickselect versus a heap. Give the complexity and the "when I write each" rule.
58. `[T]` `Collections.sort` on a list whose `compare` is inconsistent with `equals`. What can happen, and is it a `TreeSet` problem or a `TimSort` problem?
59. `[A]` You must search a 2 TiB sorted file on disk. Design the search, including what you keep in memory and how you handle a block that does not fit the predicate.
60. `[A]` The interviewer asks you to sort 10⁹ integers in 2 GiB RAM. What algorithm, what radix, and what do you say about Java's `Arrays.sort`?

---

## 5. Strings, parsing and tokenizing

> Assumed known: [../01-java](../01-java/questions.md) `String` immutability, `StringBuilder`, and encoding. This category is about parsing under a clock.

61. `[C]` Reverse words in a sentence. Write it with a `StringBuilder` and without regex, and say why `split(" ")` is a trap.
62. `[C]` Valid palindrome, ignoring non-alphanumeric. Write the two-pointer version on `charAt`, not a filtered copy.
63. `[D]` Longest palindromic substring. Expand-around-centre versus DP: which do you write in 20 minutes, and what is the complexity?
64. `[D]` String-to-integer (`atoi`) with overflow. Write the `long` guard, then the version that never leaves `int`.
65. `[T]` `String.split` with a trailing delimiter, and `split` of `"aaa"` on `"a"`. What do you get, and what should you have used instead?
66. `[D]` Implement `indexOf` / KMP at a sketch level. When is naive O(n·m) acceptable in a round, and when do you mention KMP and stop?
67. `[D]` Valid parentheses is a stack problem. Valid number, valid IP, valid IPv6 are parsers. Write the IP one as a split-and-check, and name the off-by-ones.
68. `[D]` Run-length encode and decode. Write both, and the bomb if the decode allocates from an untrusted length.
69. `[T]` `char` versus code point. Show a surrogate pair that breaks `charAt` / `toCharArray` iteration, and the `codePoints()` fix.
70. `[D]` Minimum window that covers all characters of t. Reuse the owed-count idea from Q21, now on a `String`.
71. `[D]` Implement a simple calculator with `+`, `-` and parentheses. What does the stack store, and how do you handle unary minus?
72. `[D]` Wildcard matching versus regular-expression matching. What is the DP state, and why is `*` in each problem a different animal?
73. `[T]` Concatenating in a loop with `+`. Show the complexity, the bytecode story since Java 9, and the case the compiler still cannot save.
74. `[A]` You must parse a 2 GB CSV on the heap limit of a Lambda. Design the parser: encoding, quoting, and what you never load.
75. `[A]` Design a tokenizer for a tiny expression language that must report line and column on every error. What are the token types and the one state you keep?

---

## 6. Stacks, queues and monotonic structures

> Assumed known: [../01-java](../01-java/questions.md) `ArrayDeque` versus `Stack` versus `LinkedList`. Prefer `ArrayDeque`.

76. `[C]` Valid parentheses. Write it, and name the three failure modes you test.
77. `[C]` Implement a queue with two stacks, and a stack with two queues. Which one do you actually write, and why is the other a curiosity?
78. `[D]` Daily temperatures / next greater element. Write the monotonic decreasing stack, and state the invariant in one sentence.
79. `[D]` Largest rectangle in a histogram. Why do you store indices, not heights, and what do you flush at the end?
80. `[T]` `MinStack` in O(1) getMin. Two-stack versus encoding on one stack: which do you write, and where does the encoding overflow?
81. `[D]` Sliding-window maximum. Write the deque of indices, and the two evictions on each step.
82. `[D]` Evaluate reverse Polish notation. Write it, and the division-truncation rule Java uses that interviewers will probe.
83. `[D]` Asteroid collision. Encode direction as sign, and write the while-condition that candidates get backwards.
84. `[T]` Using `Stack` (the class). Why is it wrong in modern Java, and what exactly is unsynchronized about `ArrayDeque` that you must not forget?
85. `[D]` Decode string (`3[a2[c]]`). Two stacks versus one stack of a small record: write the cleaner one.
86. `[D]` Implement a circular buffer on a fixed `Object[]`. Write `offer`/`poll`/`size` and the full-versus-empty distinction.
87. `[D]` Monotonic queue versus monotonic stack. Give one problem that is illegal for a stack and legal for a deque.
88. `[A]` Design an expression evaluator that will later grow functions and units. What do you implement in 45 minutes, and what do you leave as an interface?
89. `[A]` A producer-consumer on a bounded `ArrayBlockingQueue` is dropping items. Is that a stack/queue question or a concurrency question, and how do you start?

---

## 7. Linked lists, iterators and in-place pointer work

> Assumed known: [../01-java](../01-java/questions.md) references-as-values. Draw boxes and arrows before you type.

90. `[C]` Reverse a singly linked list, iteratively and recursively. Which do you write first, and why does the recursive one use O(n) space?
91. `[C]` Detect a cycle. Floyd's algorithm: prove in two sentences that the pointers meet if a cycle exists.
92. `[D]` Find the cycle entrance, not just its existence. Why does resetting one pointer to the head work?
93. `[D]` Merge two sorted lists. Write it with a dummy head, and say why dummy heads are not a crutch.
94. `[D]` Remove the nth node from the end in one pass. The two-pointer gap, and the dummy you need when the head is removed.
95. `[T]` Reverse nodes in k-group. What do you do with the remainder, and where do candidates lose the previous group's tail?
96. `[D]` Copy a list with random pointers. The weave-in-place method versus the `IdentityHashMap`. Which do you write, and what does the weave assume?
97. `[D]` Add two numbers stored as reversed lists, then as forward lists. What extra structure does the forward case need?
98. `[T]` `LinkedList` (the Java class) as a `List` and as a `Deque`. When is it the right structure, and when is it a cache-miss machine you should not have chosen?
99. `[D]` Flatten a multilevel doubly linked list. Recursion versus an explicit stack: which one matches the "child before next" rule without a second pass?
100. `[D]` Palindrome linked list. Reverse the second half in place, compare, restore. Why restore, and what do you say if they say not to?
101. `[D]` LRU as a HashMap plus doubly linked list. Write the node, the move-to-front, and the eviction. (Full design is Q251.)
102. `[T]` Iterating a list while deleting. `Iterator.remove` versus `list.remove(i)` on an `ArrayList` versus a `LinkedList`. Which one is O(n²), and which one throws?
103. `[A]` You must splice 10⁶ nodes from one list into another under a lock. What do you store in the node to make splice O(1), and what do you give up?
104. `[A]` Design an LRU that must also support O(1) delete-by-key and O(1) peek-oldest. Is the Java `LinkedHashMap` enough, and when is it not?

---

## 8. Trees, BSTs and tries

> Assumed known: [../01-java](../01-java/questions.md) recursion and the heap as an array. This is binary trees, BSTs and prefix trees.

105. `[C]` Inorder, preorder, postorder: recursive and iterative. Which traversal produces a BST in sorted order?
106. `[C]` Maximum depth and whether a tree is height-balanced. Write the combined DFS that returns both so you do not walk twice.
107. `[D]` Lowest common ancestor in a binary tree, then in a BST. Why is the BST version not a search for both values independently?
108. `[D]` Serialize and deserialize a binary tree. What delimiter and null marker do you pick, and why is inorder alone not enough?
109. `[D]` Validate a BST. The wrong check (`left < root < right` on children only) and the correct running-bound check.
110. `[T]` A BST iterator that must be O(1) amortized `next` and O(h) memory. Write the stack invariant.
111. `[D]` Invert a binary tree, flatten to a linked list, and connect next-right pointers. What is the shared pattern?
112. `[D]` Path sum, path sum II, and maximum path sum (the hard one). What does the helper return in each, and why is the hard one not "the sum of the path you are on"?
113. `[D]` Construct a tree from preorder and inorder. The hashmap from value to inorder index, and the shrinking range.
114. `[T]` Morris traversal. What pointer do you temporarily rewrite, and why would you never do this in production code you review?
115. `[D]` Implement a trie: `insert`, `search`, `startsWith`. Array of 26 versus `HashMap<Character, Node>`, and when the map wins.
116. `[D]` Word search II (board + dictionary). Trie plus DFS with a visited flag, and the trick of deleting a found word from the trie.
117. `[D]` kth smallest in a BST. Inorder and stop, versus an augmented node that stores subtree size. When do you mention the augmentation?
118. `[T]` Deleting a node in a BST. The three cases, and which successor you take when both children exist.
119. `[A]` Design a file-path autocomplete. Trie versus a sorted list plus binary search: the memory, the update, and the query you optimize.
120. `[A]` A 50-million-key prefix store with Unicode. Do you ship a trie? What do you ship instead, and what do you call the index?

---

## 9. Heaps, top-K and streaming order statistics

> Assumed known: [../01-java](../01-java/questions.md) `PriorityQueue` as a binary heap. Default is a min-heap.

121. `[C]` `PriorityQueue` default ordering, `Comparator.reverseOrder()`, and why `poll` of an empty queue returns `null` rather than throwing.
122. `[C]` kth largest in an array. Write the size-k min-heap, and state why a max-heap of n is the worse default.
123. `[D]` Merge k sorted lists. Heap of (value, list index, element index): the tuple you store, and the complexity.
124. `[D]` Find median from a data stream. Two heaps, the invariant on their sizes, and which heap holds the extra element.
125. `[T]` `PriorityQueue` is not thread-safe and not a bounded buffer. What do you use for each of those jobs instead?
126. `[D]` Top-K frequent elements. Heap versus bucket sort on frequency: when is the bucket O(n), and when is it a memory bomb?
127. `[D]` Sliding-window median. Why a heap pair is awkward in Java (no delete-by-value), and the `TreeMap` as a sorted multiset workaround.
128. `[D]` Reorganize string / task scheduler. What does the heap store, and what is the cooldown slot doing?
129. `[T]` Building a heap in O(n) versus n times `offer` in O(n log n). How does `new PriorityQueue(collection)` do it, and when do you care?
130. `[D]` K closest points to origin. Heap of size k versus quickselect on squared distance. Which do you write, and when is squared distance mandatory?
131. `[D]` Merge k sorted iterators that are too large to materialize. What do you store in the heap, and how do you not leak the iterators?
132. `[A]` Design a running top-K over a 24-hour sliding window of events. Heap, count-min, or a time-bucketed map - pick and defend.
133. `[A]` A "priority queue" in production that must support O(1) peek, O(log n) insert, and O(log n) delete-by-id. What do you add to the heap?

---

## 10. Graphs: traversal, topological order, shortest paths, union-find

> Assumed known: [../03-microservices](../03-microservices/questions.md) for distributed graphs of services; this category is the in-memory graph you code.

134. `[C]` Represent a graph in Java: adjacency list as `List<List<Integer>>` versus `Map<Integer, List<Integer>>`. When do you need the map?
135. `[C]` BFS and DFS. Write both on an adjacency list, and say which one finds unweighted shortest paths.
136. `[D]` Detect a cycle in a directed graph. The three-colour (or recursion-stack) method, and why a visited-only set is not enough.
137. `[D]` Detect a cycle in an undirected graph. Union-find versus DFS with parent. Which do you write, and why is the parent needed?
138. `[D]` Topological sort: Kahn's algorithm and DFS-finish-time. Write Kahn, and say what a remaining in-degree tells you.
139. `[T]` Course schedule with a cycle. The interviewer says "just DFS". What extra state do you need so a cross-edge is not a cycle?
140. `[D]` Number of islands / connected components. Flood fill, and the union-find version. When is union-find the one you want?
141. `[D]` Clone a graph. The `HashMap<Node, Node>` from original to clone, and the BFS that fills neighbours after the clone exists.
142. `[D]` Dijkstra with `PriorityQueue`. The "stale heap entry" pattern in Java (no decrease-key), and why a visited-on-settle is enough for non-negative weights.
143. `[T]` Bellman-Ford and a negative cycle. When must you mention it, and what happens if you run Dijkstra on a negative edge?
144. `[D]` Union-find with path compression and union-by-rank. Write `find` and `union`, and the inverse-Ackermann claim you should not oversell.
145. `[D]` Word ladder. The implicit graph, bidirectional BFS, and why the neighbour generation is the real cost.
146. `[D]` Alien dictionary. The graph of letter-order constraints, and the invalid-input cases (cycle, prefix contradiction).
147. `[T]` BFS on a grid with a visited `boolean[][]` versus mutating the grid. When is mutation acceptable in a round, and when is it a bug?
148. `[A]` A dependency graph of 20k build targets. Design the incremental rebuild: what you store, what you invalidate, and the cycle report.
149. `[A]` Shortest path in a time-dependent graph (edge weight = function of departure time). What algorithm still works, and what do you discretize?

---

## 11. Recursion, backtracking and divide-and-conquer

> Assumed known: [../01-java](../01-java/questions.md) call stack, tail-call (Java does not have it), and `StackOverflowError`.

150. `[C]` The backtracking template: choose, explore, unchoose. Write it for subsets, and name what you copy into the result.
151. `[C]` Permutations of a distinct array. The used-array versus in-place swap. Which do you write, and why is the swap version easier to get wrong?
152. `[D]` Combination sum, with and without reuse. The sort-and-skip, and the index you pass to forbid reuse of earlier elements.
153. `[D]` N-Queens. The three bit-sets or boolean arrays you keep (col, diag, anti-diag), and why a board scan on each place is the slow version.
154. `[T]` Generating parentheses. The two counts you thread, and the pruning that makes it not "all strings of length 2n".
155. `[D]` Word search I (one word on a board). DFS with a visited cell, and the early `false` that candidates forget to unmark.
156. `[D]` Sudoku solver. Why is this the canonical "if it returns true, stop" backtrack, and what do you try first to make it finish?
157. `[D]` Merge sort and quicksort as divide-and-conquer. Write the merge, and the quicksort partition you would defend in a review.
158. `[T]` Recursion that is secretly O(n) stack on a linked list or a skewed tree. When do you rewrite to iterative, and what do you say if you do not have time?
159. `[D]` Letter combinations of a phone number. The mapping, and why this is backtracking rather than a nested loop you unroll.
160. `[D]` Restore IP addresses. Four integers, leading-zero rule, and the 255 cap. Write the prune.
161. `[A]` A regex-like matcher you must extend later with backreferences. What do you implement now (NFA? backtrack? DP?), and what do you refuse?
162. `[A]` Recursion over a user-supplied depth (an org chart, a bill of materials). How do you bound the stack, and what is the iterative alternative?

---

## 12. Dynamic programming and greedy

> Assumed known: Category 11 for the recursive shape. DP is recursion plus a cache plus a definition of state.

163. `[C]` The three questions you ask before writing DP: what is the state, what is the recurrence, what is the base? Apply them to climbing stairs.
164. `[C]` 0/1 knapsack versus unbounded knapsack. The loop-order difference, and why reversing the inner loop matters on a 1D array.
165. `[D]` Longest increasing subsequence. O(n²) DP you write first, then the patience-sorting O(n log n) you mention.
166. `[D]` Longest common subsequence and edit distance. Write the 2D table and the rolling-row space optimization.
167. `[D]` House robber, house robber II (circle), and the tree version. What changes in the state?
168. `[T]` Coin change (fewest coins) versus coin change II (number of combinations). The loop order that accidentally counts permutations.
169. `[D]` Unique paths with obstacles. Why is this DP and not BFS, and when would BFS be the right reading of the same grid?
170. `[D]` Palindrome partition / longest palindromic subsequence. Which table do you fill first, and in which direction?
171. `[D]` Greedy: interval scheduling (max number of non-overlapping), Huffman, and Dijkstra. What is the matroid-shaped argument you actually say?
172. `[T]` Jump game (reach the end) versus jump game II (min jumps). Why is the first a greedy scan and the second a BFS-on-the-array?
173. `[D]` Kadane again, now as DP: `dp[i] = max(a[i], dp[i-1] + a[i])`. When do you keep the array, and when do you keep one variable?
174. `[D]` Decode ways (`11106`). The silent base cases, and the zero that zeros the whole suffix.
175. `[A]` A DP whose naive state is too big (subset of 40 items, or a 10⁴ × 10⁴ grid). What do you drop, meet-in-the-middle, or discretize?
176. `[A]` The interviewer wants a greedy proof. How do you structure "exchange argument" in two minutes so it is a proof and not a vibe?

---

## 13. Intervals, scheduling and sweep lines

> Assumed known: Category 4 (sort as a preprocess) and Category 6 (scan with a stack or heap).

177. `[C]` Merge overlapping intervals. Sort by start, and the one comparison that decides merge versus append.
178. `[C]` Insert an interval into a sorted list. The three-pass (before, overlapping, after) that avoids a full sort.
179. `[D]` Meeting rooms II: minimum number of rooms. Heap of end times versus a sweep of +1/−1 events.
180. `[D]` Can attend all meetings. Sort by start or by end? Which comparison, and why is this not meeting-rooms II?
181. `[T]` Overlapping inclusive versus exclusive endpoints. `[1,2]` and `[2,3]`: do they overlap? What do you ask before you write?
182. `[D]` Non-overlapping intervals you must remove to make the rest non-overlapping. Why sort by end, not by start?
183. `[D]` Sweep line: skyline, car pooling, meeting-rooms. What is an "event", how do you break ties, and what does the active set hold?
184. `[D]` Interval intersection of two sorted lists. Two pointers, and the `max(start) / min(end)` test.
185. `[D]` My calendar I/II/III. `TreeMap` as a sweep, and the booking-III running sum.
186. `[T]` Sorting intervals with `a[0] - b[0]`. The overflow, and the `Integer.compare` fix (same family as Q55).
187. `[A]` A calendar of 10⁷ bookings, queries of "is this range free" and "book if free". What index, and what do you give up on delete?
188. `[A]` Staff a 24/7 rota from interval-availability. This is not meeting-rooms. What extra constraints do you elicit, and which algorithm remains?

---

## 14. Bit manipulation, numeric correctness and overflow

> Assumed known: [../01-java](../01-java/questions.md) Q3-Q4 (caching, floating point) and two's complement.

189. `[C]` Two's complement: why `-n` is `~n + 1`, and what `Integer.MIN_VALUE` does under unary minus.
190. `[C]` Get, set, clear, toggle the k-th bit. Write the four one-liners, and say whether k is 0-based from the right.
191. `[D]` Single number (every element twice, one once). XOR fold, and the two-single-numbers follow-up that needs a discriminating bit.
192. `[D]` Number of 1 bits, and `n & (n - 1)` to drop the lowest set bit. Brian Kernighan versus `Integer.bitCount`.
193. `[T]` `n & (n - 1) == 0` as a power-of-two test. Why must you also reject `n <= 0`, and what does it do to `Integer.MIN_VALUE`?
194. `[D]` Reverse bits of a 32-bit int. The loop, and the "swap halves, then quarters" parallel method you mention.
195. `[D]` Sum of two integers without `+`. XOR and carry, and why a `while` is needed.
196. `[T]` Money in `double`. Show the exact failure, `new BigDecimal(0.1)` as the second failure, and the constructor you actually use.
197. `[D]` Integer division that must truncate toward zero, and the `Integer.MIN_VALUE / -1` overflow that Java... does what with?
198. `[D]` Fast exponentiation (`modPow`). Write the binary-exponent loop, and the overflow-safe modular multiply you need on large moduli.
199. `[D]` UTF-8 validation as a bit problem. Leading-ones count, and the continuation-byte mask.
200. `[T]` `Math.abs(Integer.MIN_VALUE)` and `Math.negateExact`. What returns, what throws, and which one do you want in a money path?
201. `[A]` A billing service adding millions of currency amounts per hour. Design the numeric type, the rounding rule, and the one test that would have caught Q196.
202. `[A]` Packed bitsets for 10⁸ flags. `BitSet` versus `long[]`, cardinality, and when a roaring bitmap is the actual answer.

---

## 15. Java API fluency under time pressure

> Assumed known: [../01-java](../01-java/questions.md) language and collections chapters. This is what a reviewer reads in the first twenty seconds of your paste.

203. `[C]` `List.of` / `Map.of` are unmodifiable and reject `null`. What throws, and when do you still want `new ArrayList<>(List.of(...))`?
204. `[C]` `record` as a DTO and as a map key. What is generated, and what is *not* (defensive copies)?
205. `[D]` `Optional`: when you return it, when you never use it as a field or a parameter, and the `orElse` versus `orElseGet` trap.
206. `[D]` Streams: `filter`/`map`/`flatMap`/`collect`, and a reduce you should have written as a loop. When is a stream the wrong tool in a timed round?
207. `[T]` A stream over a shared `ArrayList` that another thread mutates. What happens, and what does `toList()` (Java 16) not make safe?
208. `[D]` `equals`/`hashCode`/`compareTo` consistency. Write a `record`-based key, then the class-based version with `Objects.equals` / `Objects.hash`.
209. `[T]` `Comparator` chains with `nullsFirst`, and `comparing` on a field that can be null. Which call throws, and where?
210. `[D]` `EnumSet` / `EnumMap` versus `HashSet` of enums. Why is the bit-vector version the default in a review?
211. `[D]` `ArrayDeque` versus `LinkedList` versus `ArrayList` for a stack and for a queue. Give the one-line rule you apply in every round.
212. `[D]` Checked exceptions inside a `map` lambda. What do you actually write (helper, sneak, wrap), and what do you refuse in production?
213. `[T]` `IdentityHashMap`, `WeakHashMap`, `ConcurrentHashMap`. One sentence each on when you reach for them, and the `WeakHashMap` gotcha on keys.
214. `[D]` `String.formatted`, text blocks, and `NumberFormat` versus `DecimalFormat` versus `BigDecimal.setScale`. Which one for logs, which one for money?
215. `[D]` `equals` on arrays: `==`, `array.equals`, `Arrays.equals`, `Arrays.deepEquals`. Write the one-liner you want in a test.
216. `[A]` You have 20 minutes of a pairing session on their codebase. Which Java 17+ features do you introduce, and which do you leave alone because the diff would lie?
217. `[A]` Style guide in 15 minutes: nullability, collections, exceptions, streams, concurrency. Write the ten rules you would actually enforce.

---

## 16. Concurrency coding exercises

> Assumed known: [../01-java](../01-java/questions.md) memory model, `synchronized`, `volatile`, executors, virtual threads. This category is the code you type, not the JMM lecture.

218. `[C]` Write a thread-safe counter three ways: `synchronized`, `AtomicInteger`, and `LongAdder`. When is each the one you ship?
219. `[C]` `wait`/`notify` on a bounded buffer. Write `put`/`take` with `while` (not `if`), and say why `notifyAll` is the safe default.
220. `[D]` Implement a latch and a one-shot gate with `CountDownLatch` versus `CompletableFuture`. When is the future the cleaner API?
221. `[D]` `CompletableFuture` pipeline: `thenApply`, `thenCompose`, `thenCombine`, `exceptionally`, `handle`. Write a two-call compose and name the pool it runs on.
222. `[T]` `join` versus `get` versus `orTimeout`. Which one wraps in `CompletionException`, which throws checked, and what does `join` do to the interrupt flag?
223. `[D]` Bounded thread pool: `ThreadPoolExecutor` parameters. Write a constructor you would ship, and the `CallerRuns` versus `Abort` versus `Discard` choice.
224. `[T]` `Executors.newCachedThreadPool()` in a request path. What grows, what does not shrink fast enough, and what do you write instead?
225. `[D]` Virtual threads: when you just `Thread.startVirtualThread`, when you still need a semaphore, and what pins a virtual thread.
226. `[D]` Thread-safe cache with TTL. `ConcurrentHashMap` plus a timestamp, versus Caffeine. Write the naive version and name the two races it still has.
227. `[D]` Dining philosophers / lock ordering. Write the ordered-lock acquire, and the tryLock-with-backoff alternative.
228. `[T]` `synchronized` on a boxed `Integer` or on `intern()`ed strings. Why is that a cross-tenant deadlock, and what do you lock on instead?
229. `[D]` A `CompletableFuture` fan-out of 10k calls with a concurrency cap. Write the semaphore-wrapped supply, and the `allOf` join.
230. `[D]` Happens-before you can actually use: unlock/lock, volatile write/read, thread start/join, `CF` completion. Give one code example each.
231. `[A]` Design a worker pool that absorbs a 100× burst without losing tasks and without OOMing. Queue bound, rejection, shedding, and the metric.
232. `[A]` A two-lock cache (map lock + per-entry lock) deadlocks in production. How do you reproduce it on a whiteboard, and what do you replace?
233. `[A]` Unbounded `LinkedBlockingQueue` in a thread pool filled the heap. Design the replacement and the backpressure story. (Incident: S3.)
234. `[A]` You must migrate a 200-thread pool to virtual threads. What do you keep, what do you delete, and what do you measure first?

---

## 17. Design and implement

> Assumed known: [../04-system-design](../04-system-design/questions.md) for the distributed version of these objects. This category is the in-process object you code in 45-60 minutes.

235. `[C]` What does "design and implement" score that a LeetCode problem does not: API, invariants, concurrency, and the test you write first?
236. `[D]` Object-model a parking lot or a deck of cards so the types carry the rules. What do you refuse to put on a god class?
237. `[D]` Implement an in-memory pub/sub event bus with sync and async handlers, and say how you contain a slow subscriber.
238. `[D]` Implement retry with jittered exponential backoff and a retry-on predicate. Write the loop, and the one thing you never retry.
239. `[A]` Design and implement a bounded blocking queue with a waiting-producer / waiting-consumer contract. Production quality, 45 minutes. (S11)
240. `[D]` Implement a circular log / ring buffer of the last N events, thread-safe for many writers and one reader.
241. `[D]` Implement a token-bucket rate limiter for a single process. The fields, the refill, and the `tryAcquire(n)`.
242. `[D]` Implement a sliding-window log rate limiter, and say when you would pick it over the token bucket.
243. `[D]` Implement an LRU cache (`get`/`put` in O(1)). The map plus doubly linked list, and the lock story. Full walkthrough is Q251.
244. `[D]` LFU versus LRU. What extra structure does LFU need, and when is LFU the wrong default?
245. `[D]` Implement a snowflake-style ID generator for one process. Timestamp, worker id, sequence, and the clock-went-backwards case.
246. `[D]` Implement a tiny in-memory KV with TTL and size eviction. The two indexes, and the lazy-versus-eager expire choice.
247. `[T]` A singleton "service locator" the interviewer sketches. What do you implement instead, and how do you say it without lecturing?
248. `[D]` Implement an iterator over a nested list of integers (flatten). The stack of iterators, and the `hasNext` that actually advances.
249. `[D]` Implement a range module / interval set with `add`, `query`, `remove`. `TreeMap` keyed by start.
250. `[A]` Design the API for a library that will be used by 40 teams. Compatibility, nullability, thread-safety contract, and what you put in the Javadoc.
251. `[A]` Design and implement an LRU cache, production quality, 60 minutes. (S12)
252. `[A]` Design and implement a rate limiter, 60 minutes, production quality expected. (S13)
253. `[A]` Design and implement an in-memory key-value store with TTL, 60 minutes. (S14)
254. `[A]` Design and implement a process-local ID generator that will later be sharded. (S15)
255. `[A]` Design and implement retry with backoff, idempotency keys, and a budget, as a library. (S16)

---

## 18. Clean code, refactoring, review and testing

> Assumed known: [../15-mock-interviews](../15-mock-interviews/questions.md) Q163-Q175 (how a review *round* is run). This category is what you say about the code in front of you.

256. `[C]` In a 45-minute round, what naming, structure and error handling do you keep, and what do you consciously drop? (See also mock Q153.)
257. `[C]` What tests do you write in a live coding round, how many, and when? Happy path, one edge, one invariant.
258. `[D]` Refactoring kata: extract method, introduce parameter object, replace type code with class. Show each on a 20-line example.
259. `[D]` A 200-line method with three boolean flags. How do you split it live, and what do you not rename while you are still wrong?
260. `[T]` The code uses `Optional` as a field, `null` as a return, and `catch (Exception e) {}`. What do you say first, and what do you leave?
261. `[D]` Characterization tests before a refactor. What do you pin, and how do you avoid gold-plating the test of a function you are about to delete?
262. `[D]` Mutation testing versus coverage. Why is 100% line coverage compatible with a useless suite, and what mutation would you apply to this method?
263. `[D]` Flaky test: time, order, shared statics, and real I/O. Write the fix for a test that calls `Instant.now()` and one that depends on `HashMap` order.
264. `[T]` You find a security bug in the pairing codebase. How do you raise it without turning the next 20 minutes into a lecture? (See mock Q169.)
265. `[D]` What a principal-level reviewer comments on that a strong senior misses: API shape, failure modes, and the cost of the happy path.
266. `[A]` Write a ten-line code-review standard you could paste into a team wiki, covering blocking versus preference.
267. `[A]` You need this standard adopted by six teams you do not manage. How did you land it? (Your story. S17)
268. `[A]` A senior peer's review-blocking comment is wrong, and they are on the panel. How did you handle a real case? (Your story. S18)
269. `[A]` You shipped a refactor that broke production. Tell it with numbers. (Your story. S19)
270. `[A]` You grew someone who could not pass a coding round into someone who now runs them. (Your story. S20)

---
