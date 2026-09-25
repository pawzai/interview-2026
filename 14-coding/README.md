# Coding Pack

The **substance** pack for a Principal Engineer / Technical Lead / Solution Architect coding round: algorithm and data-structure patterns in Java, complexity as a design tool, concurrency you can type, and the in-process objects (LRU, limiter, queue, KV, id generator, retry) that a 45–60 minute "design and implement" actually is.

You still write code in a principal loop. The problem is usually easy. The score is on whether the code is correct under the cases the interviewer will supply, whether you chose the structure a reviewer would keep, and whether you can say the complexity and the cost of the alternative in the same breath.

---

## What this pack owns, and what it does not

| | Owned here (`14-coding`) | Owned elsewhere |
| --- | --- | --- |
| How the coding *round* is run | - | [../15-mock-interviews](../15-mock-interviews/questions.md) Q148-Q162: narration, being stuck, when to volunteer complexity |
| How a *review* round is run | What you comment on (Category 18) | [../15-mock-interviews](../15-mock-interviews/questions.md) Q163-Q175: tone, selection, the author in the room |
| Language semantics | Java API fluency under a clock (Category 15) | [../01-java](../01-java/questions.md): `equals`/`hashCode`, JMM, collections internals |
| High-level design | In-process objects (Category 17) | [../04-system-design](../04-system-design/questions.md): the distributed version of the same objects |
| Concurrency theory | The code you type (Category 16) | [../01-java](../01-java/questions.md): happens-before, executors, virtual threads as mechanisms |

**The answer frameworks are not repeated.** The four-layer technical answer, CIDER for scenarios and STAR-L for behavioural questions are defined once in [../01-java/README.md](../01-java/README.md).

---

## Files in this pack

| File | Purpose | When to use |
| --- | --- | --- |
| [README.md](README.md) | Scope, what interviewers probe, the roadmap | Read first |
| [questions.md](questions.md) | 270 questions across 18 categories | Daily drilling |
| [answers.md](answers.md) | Mechanism-level model answers with compact Java | After attempting yourself |
| [scenario-questions.md](scenario-questions.md) | Ten incidents, six implement walkthroughs, four stories | Mock practice |
| [cheatsheet.md](cheatsheet.md) | Patterns, complexity table, trap list | Night before, and 30 minutes before |
| [quiz.html](quiz.html) | Interactive flashcard version | Active recall |

Q239 and Q251-Q255 have no answer in `answers.md` on purpose - they are the Part B walkthroughs. Q267-Q270 have no scripted answer on purpose - they are your stories; Part C says how to build them.

### quiz.html

Open it directly in a browser - no server, no internet connection. Search covers question and answer text, filter by category, difficulty or your own progress, and mark each question Known or Review with progress saved in the browser. Press `/` to focus search.

Generated from the markdown, so the markdown stays the source of truth:

```bash
python tools/build-quiz.py 14-coding
```

---

## What interviewers actually probe at this level

The problem is a pretext. Six recurring signals:

1. **The invariant, said out loud.** "The window `[l, r]` has unique characters" is a note. A silent two-pointer that happens to work is not. Interviewers write down the sentence, not the loop.
2. **Complexity of a named variable.** "O(n)" without "of the edges" is a bluff, and the next problem will have two sizes (Q5). Hidden inner scans (`contains` on a list, `+` on a `String`) are how an O(n) becomes an O(n²) on the follow-up (Q11).
3. **Java, not pseudocode.** `ArrayDeque` not `Stack`. `Integer.compare` not `a - b`. `lo + (hi - lo) / 2`. A `record` as a key whose fields you then mutate. These are not style nits; they are the bugs in Part A.
4. **The structure you would keep.** A 45-minute paste that looks like a framework is a miss (Q13). A 45-minute paste with no names, no guard and no complexity sentence is also a miss. The target is boring production code.
5. **Concurrency as a contract, not a keyword.** `synchronized` on a boxed `Integer`, an unbounded queue, two locks in opposite order, virtual threads without a semaphore in front of a 20-connection pool - these fail loops that the algorithm did not.
6. **A test that would have caught it.** Three tests, after the first green path: happy, edge, invariant (Q257). Candidates who TDD-theatre twelve tests on an empty method, and candidates who write none, both lose the same dimension.

---

## Study roadmap

### Week 1 - Judging, arrays, hashing, search

Categories 1 to 4. Be able to state the 45-minute budget, write two-pointer / window / prefix without looking, and write overflow-safe binary search plus `Integer.compare` from muscle memory.

### Week 2 - Strings, stacks, lists, trees

Categories 5 to 8. Work every `[T]`. Be able to reverse a list, detect a cycle entrance, validate a BST with running bounds, and write a 26-array trie.

### Week 3 - Heaps, graphs, backtracking, DP

Categories 9 to 12. Merge-k, stream median, Kahn, union-find, the backtracking template, and the coin-change loop-order trap. This is the week the 10⁵-versus-20 rule has to become automatic.

### Week 4 - Intervals, bits, Java API

Categories 13 to 15. Sweep-line events and the inclusive/exclusive question. Money not in `double`. The ten Java rules you would enforce (Q217).

### Week 5 - Concurrency and design-and-implement

Categories 16 and 17. Type Q219 and a `ThreadPoolExecutor` constructor without looking. Then run S11-S16 timed, out loud, with a compiler if you have one. The six objects should become a shape, not a memory.

### Week 6 - Review, incidents and stories

Category 18, then only [scenario-questions.md](scenario-questions.md). Part A out loud with CIDER. Part C as STAR-L at two minutes and at six. Hand the *round mechanics* to [../15-mock-interviews](../15-mock-interviews/README.md) Category 11.

---

## Self-check before the interview

- [ ] I can write two-pointer, variable window, prefix-sum, monotonic stack and size-k heap without a template open.
- [ ] I write `lo + (hi - lo) / 2` and `Integer.compare` by habit.
- [ ] I can say "O(n) of what" and name the input that makes my bound a lie.
- [ ] I pick `ArrayDeque`, not `Stack` or `LinkedList`, unless I can say why.
- [ ] I can detect a directed cycle (grey) and an undirected one (parent or union-find), and I do not mix the two.
- [ ] I can write Kahn, union-find, and a `CompletableFuture` compose on a whiteboard.
- [ ] I can implement LRU, a token bucket, a bounded queue and a snowflake id, and name the invariant of each before I type.
- [ ] I can ship a `ThreadPoolExecutor` with a bound and a rejection policy, and I can explain why `newCachedThreadPool` is not that.
- [ ] I never put money in a `double`, and I know what `Math.abs(Integer.MIN_VALUE)` returns.
- [ ] I write three tests: happy, edge, invariant.
- [ ] I have a story for landing a review standard, for a refactor that broke production, and for coaching someone through a coding round.
