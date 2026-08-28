# Answers

Model answers for [questions.md](questions.md). Numbers match the question numbers exactly.

Every answer follows the four-layer structure from [README.md](README.md): direct answer, mechanism, trade-off, experience hook. The experience hooks are written as placeholders in *italics* - replace them with your own numbers from Nittany Technologies, Verizon India and Sonata Software.

---

## 1. Java language fundamentals

### Q1. `equals()` and `hashCode()` contract

Equal objects must produce equal hash codes. Unequal objects *may* share a hash code (that is a collision, not a bug). `hashCode()` must be consistent across calls as long as the fields used in `equals()` do not change.

Violating it breaks every hash-based collection: `map.put(key, v)` lands in bucket A, and if `hashCode()` later returns a different value, `map.get(key)` looks in bucket B and returns `null` even though the entry exists.

Rules I enforce in review: base both methods on the same immutable subset of fields, prefer `Objects.equals` / `Objects.hash`, and never include mutable or derived fields.

> *Hook: a caching bug caused by an entity whose `hashCode` included a lazily-loaded association.*

### Q2. Mutating a `HashMap` key `[T]`

The entry becomes unreachable but is not removed. The key was placed in the bucket derived from its hash at insertion time. After mutation, `get(key)` computes a new hash, goes to a different bucket, and finds nothing. `containsKey` returns `false`, `remove` fails, yet `size()` still counts the entry and iteration still returns it.

This is a genuine memory leak in long-lived maps. The fix is immutable keys, or keys whose `equals`/`hashCode` use only immutable fields.

### Q3. Integer caching

`Integer.valueOf` caches boxed values in the range -128 to 127 (upper bound tunable via `-XX:AutoBoxCacheMax`). Autoboxing calls `valueOf`, so `127` yields the same cached instance and `==` is `true`. `128` allocates two objects, so `==` compares references and is `false`.

The real lesson: never compare boxed types with `==`. This is the single most common source of intermittent bugs when developers move from `int` to `Integer` in DTOs.

### Q4. `0.1 + 0.2 == 0.3` `[T]`

Prints `false`. IEEE-754 binary floating point cannot represent 0.1 or 0.2 exactly, so the sum is `0.30000000000000004`.

Safe comparison uses a tolerance: `Math.abs(a - b) < 1e-9`. For anything involving money, use `BigDecimal` constructed from a `String` (`new BigDecimal("0.1")`, never `new BigDecimal(0.1)`) and always specify scale and `RoundingMode`.

> *Hook: a billing reconciliation defect where `double` accumulation drifted over millions of rows.*

### Q5. `String` versus `StringBuilder` versus `StringBuffer`

`String` is immutable, `StringBuilder` is mutable and unsynchronized, `StringBuffer` is mutable and synchronized (effectively legacy - the lock is almost never useful because the builder is usually thread-confined).

The compiler already converts simple concatenation into `StringBuilder` (or `invokedynamic` with `StringConcatFactory` since Java 9). What it cannot optimize is concatenation inside a loop, which creates a new builder per iteration and turns O(n) into O(n²).

### Q6. String interning `[T]`

String literals live in the string pool, so `"a" == "a"` is `true`. `new String("a")` forces a fresh heap object, so `==` against the literal is `false`. `intern()` returns the pooled instance, restoring reference equality.

Do not call `intern()` as an optimization in modern code. It moves pressure to a native hash table, and on old JVMs the pool lived in PermGen. Just use `equals()`.

### Q7. Making a class immutable

1. Declare the class `final` (or all constructors private) so behavior cannot be overridden.
2. All fields `private final`.
3. No setters, no mutating methods.
4. **Defensive-copy mutable inputs in the constructor.**
5. **Defensive-copy mutable fields on the way out of getters.** This is the one people forget.

Records handle 1 through 3 automatically but *not* 4 and 5 - a record holding a `List` is still mutable through that list.

### Q8. `final` field holding a `List` `[T]`

`final` means the reference cannot be reassigned; it says nothing about the object's contents. `list.add(x)` still works.

To make it safe: copy on the way in (`List.copyOf(input)`), and return an unmodifiable view or a copy from the getter. `List.copyOf` and `Collections.unmodifiableList` differ - the latter is a *view*, so mutating the original still shows through.

### Q9. Pass by value

Java is always pass by value. For objects, the *reference* is copied by value. So a method can mutate the object your reference points at, but reassigning the parameter inside the method has no effect on the caller.

```java
void f(List<String> l) { l.add("x");        }  // caller sees "x"
void g(List<String> l) { l = new ArrayList<>(); } // caller sees nothing
```

### Q10. Initialization order

Static fields and static blocks run once, in source order, on class initialization - superclass first. Then per instance: superclass instance initializers and constructor, then subclass instance fields and instance blocks in source order, then the subclass constructor body.

### Q11. Overridable method called from a constructor `[T]`

The subclass override runs *before* the subclass fields are initialized, so it sees default values (`null`, `0`, `false`).

```java
class Base { Base() { print(); } void print() {} }
class Child extends Base {
    private String name = "child";
    @Override void print() { System.out.println(name); } // prints null
}
```

Rule: never call an overridable method from a constructor. Make such methods `final` or `private`, or use a builder/factory that fully constructs before invoking behavior.

### Q12. Abstract class versus interface

Interfaces give you multiple inheritance of *type* and, since Java 8, of *behavior* via `default` methods. You still need an abstract class when you need state (instance fields), non-public members, or constructor logic shared by subclasses.

My rule: interface for the contract at the boundary, abstract class only when there is genuinely shared mutable state - otherwise prefer composition.

### Q13. Diamond of default methods `[T]`

The class does not compile. Java forces you to disambiguate explicitly:

```java
class C implements A, B {
    @Override public void hello() { A.super.hello(); }
}
```

Also worth knowing: a class method always beats an interface default, and a more specific interface beats a less specific one ("class wins, then most specific interface, then explicit disambiguation").

### Q14. Overload resolution

Three phases, and the compiler stops at the first that finds a match:

1. Without boxing or varargs (widening primitives allowed).
2. With boxing/unboxing allowed.
3. With varargs allowed.

So `f(int)` beats `f(Integer)` beats `f(int...)` for an `int` argument. Widening wins over boxing - a common surprise.

### Q15. Overload with `null` `[T]`

`f(null)` picks the **most specific** applicable overload. With `f(Object)` and `f(String)`, `String` is more specific, so `f(String)` is chosen. If you add `f(Integer)`, `String` and `Integer` are unrelated, the call becomes ambiguous and compilation fails. Fix by casting: `f((String) null)`.

### Q16. Checked versus unchecked

Checked exceptions must be declared or handled; unchecked (subclasses of `RuntimeException`) need not be.

My team policy: use unchecked exceptions for programming errors and for anything the caller cannot meaningfully recover from, which in a Spring service is nearly everything. Wrap checked exceptions from libraries into domain exceptions at the boundary. Checked exceptions are justified when the caller has a realistic alternative action. Never swallow, never `catch (Exception e) {}`, always preserve the cause.

### Q17. `return` in `finally` `[T]`

The `finally` return wins and **silently discards** the `try` block's return value, and worse, discards any in-flight exception.

```java
int f() { try { return 1; } finally { return 2; } } // returns 2
```

Also note that `try { return x; } finally { x = 99; }` returns the *original* value, because the return value is evaluated and stashed before `finally` runs. Static analysis should flag any `return` or `throw` inside `finally`.

### Q18. `finally` swallowing exceptions `[T]`

Yes. If `finally` completes abruptly - by `return`, `break`, `continue` or throwing - the original exception is discarded entirely. This is how "the error disappeared" bugs happen. It is also why `try-with-resources` records close-time failures as *suppressed* exceptions rather than replacing the primary one.

### Q19. `try-with-resources`

Resources are closed in reverse declaration order, before `catch` and `finally` run. If both the body and `close()` throw, the body's exception is primary and the close exception is attached via `addSuppressed()`, retrievable through `getSuppressed()`. The resource must implement `AutoCloseable`, and since Java 9 you may reference an existing effectively-final variable in the header.

### Q20. `throw`, `throws`, `Error`, `Exception`

`throw` raises an instance; `throws` declares what a method may propagate. `Error` signals JVM-level conditions you should not catch (`OutOfMemoryError`, `StackOverflowError`); `Exception` is recoverable application-level; `RuntimeException` is the unchecked subset.

Catching `Throwable` is nearly always wrong - it swallows `Error` and, in some frameworks, thread-interruption signalling.

### Q21. Type erasure

Generics are compile-time only. After erasure, `List<String>` and `List<Integer>` are both `List`; the compiler inserts casts and bridge methods. What survives: generic signatures in class metadata (readable reflectively via `getGenericSuperclass`, which is how Jackson `TypeReference` and Spring's `ParameterizedTypeReference` work). What does not survive: the runtime type of a *value*, so no `instanceof List<String>`, no `new T[]`, no overloads differing only by type parameter.

### Q22. `new T[10]` `[T]`

At runtime `T` is erased to `Object`, so the array would be an `Object[]` masquerading as `T[]`, and any store would need a check the JVM cannot perform. The standard workaround:

```java
@SuppressWarnings("unchecked")
T[] arr = (T[]) new Object[10];         // internal use only
T[] arr = (T[]) Array.newInstance(clazz, 10); // when caller supplies Class<T>
```

Best answer: use `List<T>` and avoid generic arrays entirely.

### Q23. PECS

Producer Extends, Consumer Super. `? extends T` when you only read (`List<? extends Number>` - you can get `Number`, you cannot add). `? super T` when you only write (`List<? super Integer>` - you can add `Integer`, reads give `Object`). Use an exact `T` when you do both.

Signature that shows you understand it: `void copy(List<? super T> dst, List<? extends T> src)`.

### Q24. Array covariance versus generic invariance `[T]`

Arrays are covariant: `String[]` *is a* `Object[]`. That is unsound and the JVM patches it at runtime with `ArrayStoreException`:

```java
Object[] a = new String[1];
a[0] = 42; // compiles, throws ArrayStoreException
```

Generics are invariant precisely to move that error to compile time. `List<String>` is not a `List<Object>`, because if it were you could insert an `Integer` and the erased runtime could not stop you.

### Q25. Records

A record generates a canonical constructor, private final fields, accessors (`name()` not `getName()`), and `equals`/`hashCode`/`toString` from all components. They are implicitly final and cannot extend a class.

Limits: shallow immutability only, no JavaBean naming (so some older frameworks need config), and no easy partial-update - though a compact constructor lets you validate and normalize. Ideal for DTOs, value objects, and as sealed-interface implementations.

### Q26. Sealed types

`sealed interface Shape permits Circle, Square` restricts who may implement it. This gives the compiler a closed set, which makes `switch` pattern matching *exhaustive* - no `default` branch needed, and adding a new subtype breaks compilation everywhere it must be handled. That is exactly what you want for domain modelling: algebraic data types in Java, with the compiler enforcing completeness.

### Q27. `var`

Local variable type inference, compile-time only, still statically typed. Good when the right-hand side already names the type (`var repo = new CustomerRepository()`) or when the type is unpronounceable (nested generics, stream intermediates). Bad when it hides the type from the reader (`var result = service.process()`), and unusable for fields, parameters, or `null` initializers.

### Q28. `Optional.of(null)` `[T]`

Throws `NullPointerException` immediately. Use `Optional.ofNullable` when the value may be null.

`Optional` is designed as a *return type* for "no result is normal". Do not use it for fields (not serializable, adds an allocation per instance), parameters (the caller then has to build one), or collection elements (an empty collection already expresses absence). And never call `get()` without `isPresent()` - use `orElseThrow`, `orElseGet` or `map`.

### Q29. Cloning

`Object.clone()` is a shallow field-by-field copy, so nested mutable objects are shared. `Cloneable` is a marker interface that does not even declare `clone()`, the contract is documented rather than enforced, and it interacts badly with `final` fields and inheritance.

Preferred alternatives: a copy constructor, a static factory, a builder `toBuilder()`, or - best - make the object immutable so copying is unnecessary.

### Q30. `finalize()`

Deprecated for removal because it is non-deterministic (may never run), can resurrect objects, delays collection by an extra GC cycle, and exceptions in it are ignored. Replaced by `try-with-resources`/`AutoCloseable` for deterministic cleanup, and `java.lang.ref.Cleaner` for a safety-net that runs on a dedicated thread without resurrection risk.

---

## 2. Collections and data structures

### Q31. `HashMap` internals

An array of buckets, sized to a power of two. `hash(key)` spreads the key's `hashCode` by XOR-ing its high 16 bits into the low bits (because the index is `hash & (n-1)`, which otherwise ignores high bits). Collisions form a linked list, converting to a red-black tree at 8 entries in a bucket when the table is at least 64 slots, and back to a list at 6. Default capacity 16, load factor 0.75, resize doubles capacity and rehashes. Java 8+ splits a bucket's entries into "stay" and "move by oldCapacity" without recomputing hashes.

Pre-size when you know the count: `new HashMap<>(expected / 0.75f + 1)`.

### Q32. Treeification

Once a bucket exceeds `TREEIFY_THRESHOLD` (8) and the table has at least 64 buckets, the list becomes a red-black tree, turning worst-case lookup from O(n) to O(log n). This was a hardening measure against hash-collision denial-of-service attacks.

It requires ordering: the tree compares by hash, then by `Comparable` if the key implements it, and otherwise falls back to a tie-break on class name and `System.identityHashCode`. So keys that are `Comparable` degrade more gracefully.

### Q33. Concurrent `HashMap` misuse `[T]`

Undefined behavior: lost updates, entries visible to one thread and not another, corrupted size. The classic Java 7 bug was an infinite loop in `get()` because concurrent resize reversed a bucket's linked list and created a cycle, pinning a CPU core at 100 percent.

Java 8 changed resize to preserve order, so the infinite loop is gone - but the map is still not thread-safe: lost updates and infinite loops during treeification remain possible. Use `ConcurrentHashMap`.

> *Hook: a production CPU spike traced to a shared non-concurrent map in a cache layer.*

### Q34. `ConcurrentHashMap`

Java 8 dropped segment locking. Now it locks the *first node of a bucket* with `synchronized` and uses CAS for empty-bucket insertion, so contention only occurs between threads touching the same bucket. Reads are lock-free (`volatile` node fields). Resize is cooperative: writing threads help transfer buckets.

`size()` is an approximation derived from a striped counter (`LongAdder`-style) and is not a consistent snapshot; iterators are weakly consistent - they never throw `ConcurrentModificationException` but may or may not reflect concurrent writes. Null keys and values are forbidden, precisely so `get()` returning `null` unambiguously means "absent".

Also: `computeIfAbsent` holds the bucket lock, so the mapping function must not update the same map - that deadlocks.

### Q35. `ArrayList` versus `LinkedList`

`ArrayList` is a contiguous array: O(1) indexed access, amortized O(1) append, O(n) middle insert due to `System.arraycopy` - which is extremely fast, being a vectorized memory move.

`LinkedList` gives O(1) insertion *only if you already hold the node*, which via the `List` API you never do, since reaching position n costs O(n) traversal. Add poor cache locality and 40 bytes of overhead per element, and `ArrayList` wins in practice almost always. `LinkedList` is defensible only as a `Deque`, and `ArrayDeque` beats it there too.

### Q36. Fail-fast versus fail-safe

Fail-fast iterators (`ArrayList`, `HashMap`) track a `modCount`; structural modification during iteration makes the next `next()` throw `ConcurrentModificationException`. It is a bug-detection heuristic, explicitly not a guarantee.

Fail-safe (`CopyOnWriteArrayList`, `ConcurrentHashMap`) iterate a snapshot or are weakly consistent, so no exception but possibly stale data.

Safe removal during iteration: `iterator.remove()`, or `removeIf()`.

### Q37. Removing in a for-each without an exception `[T]`

The check happens in `next()`, not `remove()`. If you remove the **second-to-last** element, `hasNext()` compares `cursor != size`, which now accidentally matches, the loop exits early and `next()` is never called again - so no exception and one element silently skipped. That is worse than the exception.

Same trap applies when iterating a concurrent collection, or when the modification happens on a different structure than the one being iterated.

### Q38. Set implementations

`HashSet`: O(1) average, no order, backed by `HashMap`. `LinkedHashSet`: O(1), insertion order preserved via a doubly-linked list. `TreeSet`: O(log n), sorted by `Comparable`/`Comparator`, backed by a red-black tree, and gives you navigation (`floor`, `ceiling`, `subSet`).

### Q39. `Comparable` versus `Comparator`

`Comparable` is the natural ordering defined on the type; `Comparator` is an external, swappable ordering. The contract requires antisymmetry, transitivity, and consistency - and `TimSort` will actively throw `IllegalArgumentException: Comparison method violates its general contract!` if you break transitivity.

Inconsistency with `equals` is legal but surprising: a `TreeSet` deduplicates using `compareTo`, so two objects that are unequal but compare as 0 will silently collapse into one element.

### Q40. `a.value - b.value` `[T]`

Integer overflow. If `a.value = Integer.MAX_VALUE` and `b.value = -1`, the subtraction wraps to a negative number and the comparator reports the wrong order, which then corrupts sorting and `TreeMap` structure.

Use `Integer.compare(a.value, b.value)` or `Comparator.comparingInt(X::getValue)`.

### Q41. Choosing a concurrent map

`ConcurrentHashMap` for essentially all new code: fine-grained locking, lock-free reads, atomic `compute`/`merge`/`putIfAbsent`. `Collections.synchronizedMap` wraps every method in one lock, so it serializes all access and still requires manual synchronization around iteration. `Hashtable` is legacy - same global lock plus no-null semantics.

Caveat: `ConcurrentHashMap` makes individual operations atomic, not sequences of them. Check-then-act still needs `compute` or an explicit lock.

### Q42. `BlockingQueue`

`ArrayBlockingQueue` is bounded and array-backed with a single lock - predictable memory, natural backpressure. `LinkedBlockingQueue` has separate put/take locks so higher throughput, but is unbounded by default which is how you get an `OutOfMemoryError` instead of backpressure - always pass a capacity. `SynchronousQueue` has zero capacity and hands off directly (what `newCachedThreadPool` uses). `PriorityBlockingQueue` is unbounded and ordered. `DelayQueue` releases elements only after their delay expires - useful for scheduled retries.

### Q43. `CopyOnWriteArrayList`

Every mutation copies the whole backing array under a lock; reads are completely lock-free and iterate an immutable snapshot. Cost is O(n) per write plus garbage.

Wins only when reads massively outnumber writes and the collection is small: listener/observer registries, cached configuration, security filter chains. It is a disaster for anything write-heavy.

### Q44. `contains()` complexity

`ArrayList` O(n), `HashSet` O(1) average and O(log n) worst case after treeification, `TreeSet` O(log n). The classic performance fix in code review is a `List.contains` inside a loop, turning O(n²) into O(n) by switching to a `HashSet`.

### Q45. `Arrays.asList()` `[T]`

It returns a fixed-size *view backed by the original array*, not an `ArrayList` (it is the private `Arrays$ArrayList`). `set()` writes through to the array so it is supported; `add`/`remove` would change the length, which an array cannot do, hence `UnsupportedOperationException`.

Extra trap: `Arrays.asList(intArray)` with a primitive array gives you a single-element `List<int[]>`.

### Q46. Three list factories `[T]`

- `new ArrayList<>()` - fully mutable, allows nulls and duplicates.
- `Arrays.asList(...)` - fixed size, `set` allowed, allows nulls, writes through to the array.
- `List.of(...)` - fully immutable, **throws `NullPointerException` on null elements**, and its iteration order is stable but `Set.of`/`Map.of` deliberately randomize iteration order per JVM run to stop you depending on it.

---

## 3. Streams, lambdas and functional Java

### Q47. Intermediate versus terminal

Intermediate operations (`map`, `filter`, `sorted`) return a stream and are lazy - they only build a pipeline. Nothing executes until a terminal operation (`collect`, `forEach`, `reduce`, `findFirst`) pulls elements through. So a pipeline with no terminal operation does literally nothing, which is a real bug when someone calls `list.stream().map(this::save)` and expects side effects.

### Q48. Laziness and short-circuiting

Elements are pushed through the whole pipeline one at a time, not stage by stage. `list.stream().filter(...).map(...).findFirst()` stops at the first match instead of mapping everything. Short-circuiting operations: `findFirst`, `findAny`, `anyMatch`, `allMatch`, `noneMatch`, `limit`. This is what makes infinite streams (`Stream.iterate(...).limit(n)`) usable.

### Q49. Reusing a stream `[T]`

`IllegalStateException: stream has already been operated upon or closed`. A stream is single-use. If you need two passes, either re-create it from the source, or use a `Supplier<Stream<T>>`, or collect once and iterate the collection.

### Q50. `map` versus `flatMap`

`map` is 1-to-1, `flatMap` is 1-to-many and flattens one level. Beyond flattening nested collections, the important use is unwrapping containers: `Optional.flatMap` to chain lookups that each may be empty, and `CompletableFuture.thenCompose` (the same concept) to avoid `Future<Future<T>>`. Also `stream.flatMap(line -> Arrays.stream(line.split(" ")))` for tokenizing.

### Q51. `Collectors.toMap` duplicate keys `[T]`

Throws `IllegalStateException: Duplicate key`. Supply a merge function:

```java
.collect(Collectors.toMap(User::getId, u -> u, (a, b) -> b));
```

Second trap: the two-argument `toMap` throws `NullPointerException` if a *value* is null (unlike `HashMap`), because it uses `map.merge` internally. If values may be null, use `groupingBy` or collect manually.

### Q52. When parallel streams help

Three conditions, all required: the data set is large enough that per-element work dominates fork/join overhead (rule of thumb, N × cost > ~100 microseconds), the source splits cheaply and evenly (arrays, `ArrayList`, `IntStream.range` - not `LinkedList`, `Iterator`-based sources, or `BufferedReader.lines`), and the operations are stateless, associative and side-effect free.

Also, the terminal operation must not be a cheap merge that gets swamped by combining cost - `collect(toList())` on a parallel stream is often slower than sequential.

### Q53. Parallel streams in a request handler `[T]`

They use the shared `ForkJoinPool.commonPool`, sized to `availableProcessors - 1` for the entire JVM. One slow parallel stream - especially one doing blocking IO - starves every other parallel stream in the process, and in a container the processor count may be misdetected.

If you must, submit the stream inside your own `ForkJoinPool` (`pool.submit(() -> stream.parallel()...).get()`), or better, use an `ExecutorService` or virtual threads for IO-bound fan-out. Parallel streams are for CPU-bound work, never for IO.

### Q54. `reduce` versus `collect`

`reduce` is for immutable accumulation with an associative function returning a new value each time; `collect` is a mutable reduction with a supplier, accumulator and combiner, so it reuses containers.

Doing string concatenation with `reduce` is O(n²) because each step allocates a new `String`; `Collectors.joining()` uses one `StringBuilder`. The general rule: if the accumulator is a container, use `collect`.

### Q55. Stateful lambda in a parallel stream `[T]`

Results become non-deterministic and possibly corrupt. The stream contract requires the mapper to be stateless; with a shared mutable variable you get a data race, and even with an `AtomicInteger` the *order* of invocation is unspecified, so an index-assigning lambda produces different results per run. Restructure to carry state in the element, or collect to an ordered result and post-process.

### Q56. `groupingBy` with downstream

```java
Map<Dept, Long> counts =
    emps.stream().collect(groupingBy(Employee::dept, counting()));

Map<Dept, Double> avgSalary =
    emps.stream().collect(groupingBy(Employee::dept, averagingDouble(Employee::salary)));
```

Worth knowing the other downstreams: `mapping`, `filtering`, `reducing`, `teeing`, and the three-argument form that lets you choose `TreeMap::new` for a sorted result.

### Q57. Functional interfaces

An interface with exactly one abstract method; `@FunctionalInterface` makes the compiler enforce it. `default` and `static` methods do not count, nor do public `Object` methods like `equals`.

Core set: `Function<T,R>`, `BiFunction`, `Supplier<T>`, `Consumer<T>`, `BiConsumer`, `Predicate<T>`, `BiPredicate`, `UnaryOperator<T>`, `BinaryOperator<T>`, plus the primitive specializations (`IntFunction`, `ToIntFunction`, `IntPredicate`) that exist purely to avoid boxing.

### Q58. Method references

1. Static: `Integer::parseInt`
2. Bound instance: `System.out::println`
3. Unbound instance of an arbitrary object: `String::toLowerCase`
4. Constructor: `ArrayList::new`

The subtle one is 3 - the receiver becomes the first parameter, so `String::compareTo` is a `BiFunction<String,String,Integer>`.

### Q59. Effectively final `[T]`

A lambda captures the *value* of a local variable, not the variable itself, because locals live on the stack of a frame that may have exited by the time the lambda runs. Allowing mutation would create two divergent copies with no defined semantics - and would be a data race if the lambda runs on another thread.

Instance and static fields are captured by reference (via `this`), so they *can* be mutated - which is exactly why an inner-class lambda can accidentally leak or race on enclosing state. Workaround when you truly need a mutable counter: an `AtomicInteger` or a one-element array, though usually that means you should be using `reduce` or `collect`.

### Q60. Checked exceptions in lambdas

Standard functional interfaces do not declare checked exceptions, so you must either handle inline (which is noisy), or define your own throwing interface and a wrapper:

```java
@FunctionalInterface interface ThrowingFunction<T,R,E extends Exception> { R apply(T t) throws E; }

static <T,R> Function<T,R> unchecked(ThrowingFunction<T,R,Exception> f) {
    return t -> { try { return f.apply(t); } catch (Exception e) { throw new UncheckedException(e); } };
}
```

Practical stance: at the boundary, wrap into a domain `RuntimeException` with the cause preserved. Never `catch (Exception e) { return null; }` inside a `map`.

---

## 4. Concurrency and multithreading

### Q61. Thread states

`NEW`, `RUNNABLE` (includes running and ready, and confusingly also blocked on IO), `BLOCKED` (waiting for a monitor lock), `WAITING` (`wait()`, `join()`, `park()` with no timeout), `TIMED_WAITING` (same with a timeout, plus `sleep`), `TERMINATED`.

In a thread dump: many `BLOCKED` threads point at lock contention; many `WAITING` on a pool queue is normal idling; many `RUNNABLE` inside socket reads means a slow downstream, not CPU load.

### Q62. Java Memory Model

The JMM defines when a write by one thread becomes visible to another. Without synchronization, the compiler, JIT and CPU may reorder and cache freely, so there is no visibility guarantee at all.

`happens-before` is the ordering relation: program order within a thread; monitor unlock happens-before subsequent lock of the same monitor; a `volatile` write happens-before every subsequent read of that field; `Thread.start()` happens-before anything in that thread; anything in a thread happens-before another thread's successful `join()`; `final` field initialization happens-before publication of a properly constructed object.

### Q63. `volatile`

Guarantees: visibility (reads always see the latest write, no caching in registers) and ordering (a memory barrier prevents reordering across the access, so writes made *before* the volatile write are visible to a thread that reads it).

Does not guarantee: atomicity of compound operations. It is right for a `stop` flag or a safely-published immutable reference; it is wrong for counters.

### Q64. `volatile` increment `[T]`

Not thread-safe. `count++` is read-modify-write: three separate bytecode steps. Two threads can both read 5, both write 6, and one increment is lost. `volatile` fixes visibility of each individual read and write but cannot make the triple atomic.

Fixes: `AtomicInteger.incrementAndGet()` (CAS), `LongAdder` under high contention, or a lock.

### Q65. `synchronized` versus `ReentrantLock`

Both are reentrant and mutually exclusive. `synchronized` is simpler, JVM-managed, releases automatically on exception, and benefits from biased/thin lock optimizations.

`ReentrantLock` adds: `tryLock()` with and without timeout (essential for deadlock avoidance), interruptible acquisition, an optional fair ordering policy, multiple `Condition` objects on one lock, and the ability to lock and unlock in different scopes. Cost is that you must `unlock()` in a `finally`. And on virtual threads, `ReentrantLock` does not pin the carrier thread while `synchronized` does.

### Q66. `ReadWriteLock` and `StampedLock`

`ReentrantReadWriteLock` lets concurrent readers share, while writers are exclusive. It only pays off when reads greatly outnumber writes and critical sections are long enough to amortize the higher bookkeeping cost; under write pressure it can be slower than a plain lock, and readers can starve writers without the fair policy.

`StampedLock` adds an optimistic read: take a stamp, read fields, then `validate(stamp)` - if a writer intervened, fall back to a real read lock. It is faster but not reentrant and not directly usable with `Condition`, so it is easy to misuse.

### Q67. `wait`/`notify` inside `synchronized`

Because they operate on the object's monitor, and the JVM throws `IllegalMonitorStateException` otherwise. Deeper reason: without holding the lock there is a lost-wakeup race - the condition could change and `notify` could fire between your condition check and your `wait()`, and you would sleep forever. Holding the monitor makes check-and-wait atomic.

Prefer `notifyAll()` unless you can prove all waiters are interchangeable, because `notify()` may wake a thread waiting on a different condition and lose the signal.

### Q68. `wait()` in a loop `[T]`

Three reasons: spurious wakeups are permitted by the specification; `notifyAll` wakes every waiter, but only one may proceed; and another thread may consume the condition between your wakeup and your reacquiring the lock. So the condition must be rechecked:

```java
synchronized (lock) {
    while (!condition) { lock.wait(); }
    // proceed
}
```

### Q69. Executor framework

Submission logic in order: if fewer than `corePoolSize` threads exist, create a new thread even if others are idle; else try to enqueue; if the queue is full, create threads up to `maxPoolSize`; if that fails too, apply the `RejectedExecutionHandler` (`AbortPolicy` default, plus `CallerRunsPolicy`, `DiscardPolicy`, `DiscardOldestPolicy`).

`CallerRunsPolicy` is the underrated one: it applies backpressure by making the submitting thread do the work, which throttles the producer instead of dropping requests.

### Q70. Pool never grows past core `[T]`

An unbounded queue never becomes full, and `maxPoolSize` is only consulted when enqueueing fails. So `maxPoolSize` is dead configuration, and the queue grows until you run out of heap - a latency problem that turns into an `OutOfMemoryError`.

Fix: use a bounded queue sized deliberately, plus a rejection policy. This is exactly why `Executors.newFixedThreadPool` is discouraged and you should construct `ThreadPoolExecutor` directly.

### Q71. Pool sizing

CPU-bound: threads ≈ number of cores (plus one to cover occasional page faults). More threads just add context switching.

IO-bound: `threads = cores × targetUtilization × (1 + waitTime / serviceTime)`. So a task waiting 90ms and computing 10ms can justify roughly 10 threads per core.

In practice I derive the number from Little's Law against the target throughput and observed latency, then bound it by what the downstream can absorb - the thread pool is also a concurrency limit protecting the database or the upstream API. With virtual threads the sizing question moves from "how many threads" to "how many concurrent calls will the downstream tolerate", enforced by a semaphore.

### Q72. `CompletableFuture`

Composition: `thenApply` (transform), `thenCompose` (flatMap, avoids nesting), `thenCombine` (join two independent futures), `allOf`/`anyOf` (fan-in).

Exceptions: `exceptionally` (recover), `handle` (see both result and error), `whenComplete` (observe without changing). An exception inside a stage skips subsequent `thenApply` stages and propagates to the first handler, and `join()` wraps it in `CompletionException` while `get()` wraps it in `ExecutionException`.

Executor: without an explicit executor, async stages run on the common `ForkJoinPool`, and non-async stages run on whichever thread completed the previous stage - which may be a Netty IO thread or the caller. Always pass an explicit executor for anything blocking.

### Q73. `thenApply` versus `thenApplyAsync` `[T]`

`thenApply` runs on the thread that completed the previous stage (or the calling thread if it was already complete). `thenApplyAsync` submits to the common pool or an executor you supply.

It matters because a heavy `thenApply` hijacks the completing thread. If that thread belongs to your HTTP client's IO pool, you stall all other connections on that pool - a classic cause of "everything got slow when one endpoint got slow".

### Q74. Deadlock, livelock, starvation

Deadlock: two threads each hold a lock the other needs, and nobody moves. Requires mutual exclusion, hold-and-wait, no preemption, circular wait - break any one. My standard prevention is global lock ordering plus `tryLock` with timeout.

Livelock: threads keep changing state in response to each other and make no progress (two retry loops backing off in lockstep). Fix with randomized backoff.

Starvation: a thread never gets scheduled or never wins the lock - fix with fair locks or priority separation.

Detection in production: take a thread dump (`jstack`, `jcmd <pid> Thread.print`); the JVM explicitly prints "Found one Java-level deadlock" with the cycle. `ThreadMXBean.findDeadlockedThreads()` can also be exposed as a health check.

### Q75. Synchronizers

`CountDownLatch`: one-shot gate, wait for N events; cannot be reset. `CyclicBarrier`: N threads wait for each other, reusable, supports a barrier action. `Semaphore`: permits limiting concurrency - my usual tool for capping calls to a fragile downstream. `Phaser`: dynamic party registration across multiple phases, for when the participant count changes at runtime.

### Q76. Atomics, CAS and ABA

Atomic classes wrap a `volatile` value and use `compareAndSet`, which maps to a single CPU instruction (`lock cmpxchg`). The pattern is a retry loop: read, compute, CAS, repeat if it failed. Lock-free, so no context switching, but it burns CPU under heavy contention.

ABA: a thread reads A, another changes it to B and back to A, and the CAS succeeds although the state changed meaningfully - dangerous in lock-free stacks where the node was recycled. Solved with `AtomicStampedReference` (value plus version counter).

### Q77. `LongAdder` versus `AtomicLong` `[T]`

`AtomicLong` has all threads CAS-ing the same cache line, so under contention you get cache-line ping-pong and repeated CAS failures. `LongAdder` keeps an array of cells, one per contending thread (padded to avoid false sharing), so each thread updates its own cell without conflict; `sum()` adds the cells.

Trade-off: `sum()` is not atomic and is more expensive, so `LongAdder` is right for write-heavy counters read occasionally - metrics - and wrong when you need an exact `getAndIncrement` value, such as ID generation.

### Q78. `ThreadLocal`

Per-thread storage, implemented as a map *on the Thread object* keyed by weak references to the `ThreadLocal`. Uses: `SecurityContextHolder`, transaction/EntityManager binding, MDC for correlation IDs, non-thread-safe formatters.

Leak risk: in a thread pool, threads live forever, so a value never removed stays reachable through the thread and can pin an entire classloader in an application server. The key is weakly referenced but the *value* is not. Always `remove()` in a `finally`, and be aware that with virtual threads the per-thread copy is cheap in creation but expensive in aggregate - `ScopedValue` is the modern replacement.

### Q79. Virtual threads

Lightweight threads scheduled by the JVM onto a small pool of carrier threads. A blocking call unmounts the virtual thread instead of blocking an OS thread, so thread-per-request becomes viable at hundreds of thousands of concurrent requests.

What changes: pooling virtual threads is pointless - create one per task (`Executors.newVirtualThreadPerTaskExecutor()`); reactive code written *purely* to avoid blocking loses much of its justification; `ThreadLocal` becomes expensive at scale.

What does not change: you still need to limit concurrency against downstreams (use a `Semaphore`, since the pool no longer does it for you), CPU-bound work still needs a bounded pool, and none of this makes shared mutable state safe.

### Q80. Pinning `[T]`

Inside a `synchronized` block the JVM cannot unmount the virtual thread because the monitor is tied to the OS thread's stack frame, so it pins the carrier thread. Enough pinned carriers and throughput collapses back to platform-thread limits. (JDK 24 removed most pinning under `synchronized`, but library code you do not control may still be on an older baseline.)

Guidance: replace `synchronized` around blocking calls with `ReentrantLock`, which parks correctly. Diagnose with `-Djdk.tracePinnedThreads=full`.

### Q81. Double-checked locking

```java
private volatile Singleton instance;
public Singleton get() {
    if (instance == null) {
        synchronized (this) {
            if (instance == null) instance = new Singleton();
        }
    }
    return instance;
}
```

`volatile` is mandatory. Without it, the JIT may reorder allocation and constructor execution so another thread sees a non-null reference to a partially constructed object. `volatile` inserts the barrier that forbids that reordering.

### Q82. Thread-safe singleton

1. Eager static field - simplest, thread-safe by class initialization, but no laziness.
2. Holder idiom - `private static class Holder { static final Singleton INSTANCE = new Singleton(); }`; lazy and lock-free, relying on JVM class-initialization guarantees. My default.
3. Double-checked locking with `volatile` - only when you need a parameterized or resettable instance.
4. Enum singleton - serialization and reflection safe, Joshua Bloch's recommendation, though awkward if it needs dependencies.

In Spring the honest answer is: use a singleton-scoped bean and let the container manage it, so it stays testable.

### Q83. Making a legacy class thread-safe

Options in the order I would consider them: confine it to one thread (`ThreadLocal` or a single-threaded executor owning the instance); make each use create its own instance if construction is cheap; wrap it in a thread-safe facade that holds a private lock around every method (client-side locking); or copy-on-write the state if reads dominate.

The wrapper is usually the right first move because it is provable and reversible - and I would add a concurrency test with `jcstress` or a hammer test before declaring it safe.

---

## 5. JVM internals, memory and performance

### Q84. Memory areas

Heap (shared, GC-managed, holds objects, split into young and old). Metaspace (native memory, class metadata; replaced PermGen in Java 8 and grows until `MaxMetaspaceSize`). Per-thread stacks (frames, locals, ~1MB default - `StackOverflowError` lives here). Code cache (JIT-compiled native code; if it fills, the JVM reverts to interpretation and performance quietly halves). Direct/native memory for NIO buffers, outside the heap and invisible to `-Xmx`.

### Q85. Generational collection

Objects are allocated in Eden. A minor GC copies survivors to a survivor space; each surviving collection increments the object's age; at the tenuring threshold it is promoted to the old generation. Objects too large for Eden are allocated directly in old (humongous allocations in G1). The weak generational hypothesis - most objects die young - is why this is fast: collection cost is proportional to *live* data, not garbage.

Premature promotion (survivor space too small) is a common cause of frequent full GCs.

### Q86. Choosing a collector

- **Serial**: single-threaded, tiny heaps, containers with one core.
- **Parallel**: throughput-optimized, long pauses acceptable - batch jobs.
- **G1** (default since Java 9): region-based, pause-target driven (`-XX:MaxGCPauseMillis`), good default for heaps from a few GB up to tens of GB.
- **ZGC**: sub-millisecond pauses, concurrent, scales to terabytes; costs some throughput and more memory. Generational ZGC (JDK 21+) removed most of that throughput penalty.
- **Shenandoah**: similar low-pause goal, concurrent compaction, common on OpenJDK/RedHat builds.

My decision rule: start with G1; move to ZGC when p99 latency is dominated by GC pauses and the heap is large; use Parallel when throughput matters more than tail latency.

### Q87. Stop-the-world in G1

Long pauses usually come from: humongous allocations (objects over half a region) fragmenting old space; a mixed-collection set that is too large; reference processing (many weak/soft references or finalizers); or an evacuation failure ("to-space exhausted") where G1 cannot find space for survivors and degrades to a full GC.

Fixes: increase heap or region size, reduce allocation rate, raise `InitiatingHeapOccupancyPercent` headroom, and eliminate the allocation hot spot found in the allocation profile.

### Q88. Container OOM-kill with healthy heap `[T]`

The container limit covers *all* JVM memory, and heap is only part of it. The rest: metaspace, code cache, thread stacks (1MB × thread count - 500 threads is 500MB), direct byte buffers used by Netty and NIO, GC structures, JIT and compiler arenas, and native allocations from libraries such as compression or crypto.

Diagnosis: enable Native Memory Tracking (`-XX:NativeMemoryTracking=summary` then `jcmd <pid> VM.native_memory summary`). Fixes: set `-XX:MaxDirectMemorySize`, cap thread counts, set `MaxMetaspaceSize`, and size the heap as roughly 50-70 percent of the container limit rather than 90 percent (or use `-XX:MaxRAMPercentage`).

> *Hook: a Kubernetes service being killed every few hours until direct buffers were capped.*

### Q89. `OutOfMemoryError` variants

- **Java heap space**: genuine leak or under-sized heap. Take a heap dump.
- **GC overhead limit exceeded**: over 98 percent of time in GC recovering under 2 percent of heap - a leak in its late stage.
- **Metaspace**: classloader leak, typically repeated redeployment or dynamic proxy/CGLIB class generation.
- **Direct buffer memory**: unreleased NIO buffers, usually a Netty or file-channel path.
- **Unable to create new native thread**: thread leak or an OS/cgroup thread limit, not a heap problem at all.
- **Requested array size exceeds VM limit**: an array over ~2^31 elements, usually an unbounded query result.

### Q90. Finding a leak in production

1. Confirm from metrics: old-gen occupancy after full GC trending upward over days.
2. Capture a heap dump at low traffic (`jcmd <pid> GC.heap_dump`) - accept the pause, or take it from a canary instance.
3. Analyze with Eclipse MAT: Leak Suspects report, then dominator tree, then the shortest path to GC root of the biggest retained set.
4. Correlate to code: the usual culprits are unbounded caches, `ThreadLocal` in pooled threads, static collections, listeners never deregistered, and `ClassLoader` retention.
5. Reproduce in a load test, fix, and add a guard - a bounded cache with eviction plus an alert on old-gen growth.

For continuous visibility I keep Java Flight Recorder running with a low-overhead profile and use async-profiler for allocation flame graphs.

### Q91. Reference types

Strong: normal; never collected while reachable. Soft: collected only under memory pressure - suitable for a memory-sensitive cache, though in practice a bounded Caffeine cache is more predictable. Weak: collected at the next GC once weakly reachable - used for canonicalizing maps and `WeakHashMap` keys, and by `ThreadLocal` for its keys. Phantom: never returns the referent, enqueued after finalization - used with `Cleaner` for deterministic native-resource cleanup, e.g. freeing direct buffers.

### Q92. JIT

The JVM interprets first, profiles hot paths, then compiles. Tiered compilation goes through C1 (fast compilation, light optimization, gathers profile data) into C2 (aggressive optimization) for the hottest methods.

Optimizations that matter: inlining (the enabler for everything else - and why very large methods are never optimized well), loop unrolling, escape analysis, dead code elimination, and speculative optimization based on the observed profile, e.g. monomorphic call sites turned into direct calls.

Deoptimization happens when a speculation is invalidated - a new subclass is loaded, or an "impossible" branch is taken - and the method falls back to the interpreter and is recompiled. This is why performance can change after hours of uptime, and why the first minutes after deployment are slow.

### Q93. Naive microbenchmarks `[T]`

They measure the wrong thing: no JIT warm-up so you time the interpreter, dead code elimination removes the computation whose result you ignore, constant folding precomputes it, GC and other JVM activity add noise, and `currentTimeMillis` has coarse resolution.

Use JMH: it handles warm-up iterations, forks a fresh JVM per run, provides `Blackhole` to consume results, and reports distributions rather than a single number. And treat any microbenchmark as suggestive only - the real judge is a production-shaped load test.

### Q94. Escape analysis

The JIT proves an object never escapes the method (never stored to a field, never returned, never passed to an unanalyzable call). It can then apply scalar replacement - split the object into its fields held in registers, so no allocation at all - and lock elision, removing synchronization on a thread-confined object.

This is why "avoid allocation" advice is often wrong for short-lived local objects, and why a small wrapper or `Optional` in a hot loop frequently costs nothing after warm-up.

### Q95. Reading a thread dump

Take three dumps, ten seconds apart, so you can distinguish a stuck thread from a busy one.

Look for, in order: the JVM's own deadlock report at the bottom; threads in `BLOCKED` state and the lock address they wait on, then find the owner ("locked <0x...>"); repeated identical stacks across dumps (stuck); many threads in the same downstream call (a slow dependency); the pool queue depth implied by idle versus busy worker counts; and GC threads or the finalizer thread being busy.

Correlate with CPU: `top -H -p <pid>`, convert the offending thread ID to hex, and find it in the dump by `nid=`.

### Q96. Production JVM flags

`-XX:MaxRAMPercentage=70` (container-aware sizing instead of a fixed `-Xmx`), `-XX:+UseG1GC` or `-XX:+UseZGC -XX:+ZGenerational`, `-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/dumps`, `-XX:+ExitOnOutOfMemoryError` for containers so the orchestrator restarts a poisoned process, GC logging with rotation (`-Xlog:gc*:file=...:time,uptime:filecount=5,filesize=20M`), `-XX:NativeMemoryTracking=summary`, JFR enabled with a low-overhead profile, and `-XX:+UseStringDeduplication` when string-heavy.

Equally important: setting `-Xms` equal to `-Xmx` in containers to avoid heap resizing pauses.

### Q97. p50 20ms, p99 3s `[A]`

The gap means something intermittent, not something slow. My checklist:

1. **GC pauses** - correlate p99 spikes with GC logs. A 3s pause suggests full GC or evacuation failure.
2. **Lock contention or pool queueing** - queueing time is the classic bimodal signature; measure time-in-queue separately from time-in-service.
3. **Connection pool exhaustion** - HikariPool wait time, HTTP client pool saturation.
4. **A slow dependency's own tail**, amplified because one request fans out to N calls (tail amplification: with N=10, p99 of a dependency becomes roughly p90 of your request).
5. **Cold paths** - cache misses, JIT deoptimization, DNS lookups, TLS handshakes, lazy initialization.
6. **Noisy neighbours / CPU throttling** - in Kubernetes, `container_cpu_cfs_throttled_seconds` is the first metric I check.

I would attach distributed tracing filtered to slow traces, and compare the span breakdown of a p99 trace against a p50 trace. That usually answers it in one look.

---

## 6. Design patterns and clean code

### Q98. SOLID in practice

- **SRP**: an `OrderService` that also formats emails and writes CSV changes for three unrelated reasons. Split by *reason to change*, not by "one method per class".
- **OCP**: a `switch` over payment types recompiled for every new type; replace with a `PaymentHandler` interface and let Spring inject `List<PaymentHandler>`, selecting by `supports(type)`.
- **LSP**: `Square extends Rectangle` breaks callers that set width and height independently. The test is behavioral: can I substitute the subtype without the caller knowing?
- **ISP**: a fat `UserService` interface forcing test doubles to stub ten unused methods; split into role interfaces.
- **DIP**: the service layer importing `JdbcTemplate` directly; depend on a repository interface owned by the domain, implemented in the infrastructure layer.

### Q99. Strategy versus Template Method versus State

Strategy: interchangeable algorithms selected by the client, composed at runtime. Template Method: fixed algorithm skeleton in a base class with subclass hooks - inheritance-based, so more rigid. State: the object's behavior changes because *its own* state changed, and states know about transitions.

I prefer Strategy by default because composition beats inheritance for testing; Template Method is fine when the skeleton is genuinely invariant (Spring's `JdbcTemplate` is the canonical example).

### Q100. Builder

Beyond the telescoping-constructor problem, the real value is: enforcing invariants in `build()` so no invalid object ever exists, supporting optional parameters without a combinatorial constructor explosion, producing immutable objects, and giving readable call sites where boolean or same-typed parameters would otherwise be positionally ambiguous. With records, a compact constructor plus a generated builder (Lombok `@Builder`) covers most cases.

### Q101. Factory versus DI

A DI container is a factory, so constructor-arg factories have largely been absorbed. Factories still earn their place when the choice is *data-driven at runtime* (create a handler based on a message type), when construction is genuinely complex, or when you must decouple from a third-party API. In Spring the idiomatic form is injecting a `Map<String, Handler>` (bean name to bean) or a `List<Handler>` with a `supports()` predicate.

### Q102. Decorator versus Proxy

Structurally identical - both implement the same interface and wrap an instance. The difference is intent and lifecycle: a Decorator *adds behavior* and is stacked by the client, who chooses the composition; a Proxy *controls access* to a subject it usually creates or manages, adding lazy loading, remoting, caching or security without the client knowing.

Spring AOP is proxy-based; a `BufferedInputStream` wrapping a `FileInputStream` is a decorator.

### Q103. Observer versus event bus versus broker

In-process `Observer` / Spring `ApplicationEvent`: synchronous by default, same transaction and same JVM, no durability - good for decoupling within a module. An in-process event bus adds async dispatch but still dies with the process. A message broker (Kafka, SQS) adds durability, cross-process delivery, replay and backpressure, at the cost of eventual consistency and operational complexity.

The boundary rule: if losing the event on a crash is unacceptable, it must cross a broker with an outbox, not an in-memory listener.

### Q104. Singleton as anti-pattern `[T]`

The classic static-holder Singleton hides its dependency (callers reach for it globally rather than declaring it), makes testing hard because you cannot substitute it, introduces global mutable state, and can leak across classloaders.

Spring's singleton scope is a different thing: one instance per container, but injected explicitly, so it stays substitutable and testable. The pattern is fine; the `static getInstance()` implementation is what causes the pain.

### Q105. Resilience patterns

**Retry** handles transient faults - must be paired with exponential backoff plus jitter, a bounded attempt count, and idempotency, or it becomes a self-inflicted denial of service. **Circuit breaker** stops calling a failing dependency (closed → open after a failure threshold → half-open trial), converting slow failures into fast ones. **Bulkhead** isolates resources per dependency, so one slow downstream cannot consume the whole thread or connection pool.

Composition order in Resilience4j matters: `Retry(CircuitBreaker(RateLimiter(TimeLimiter(Bulkhead(call)))))` - retry outermost so it observes the breaker, timeout inside so each attempt is bounded. And always define a fallback: cached data, degraded response, or a queued write.

### Q106. Inheritance versus composition `[A]`

I ask: is this a true "is-a" that satisfies Liskov for every current *and future* caller, or am I reusing code? If it is reuse, compose. Inheritance couples you to the parent's implementation details, breaks encapsulation (the fragile base class problem), and consumes your one superclass slot.

I permit inheritance for stable, shallow hierarchies designed for extension and documented as such, and for sealed hierarchies modelling a closed set of variants.

### Q107. Clean code at team scale `[A]`

Definition: code a competent engineer unfamiliar with it can change safely in an afternoon. That means clear naming, small units with one reason to change, explicit boundaries, and tests that document intent.

Enforcement without being a bottleneck: automate everything mechanical (Spotless/Checkstyle, SonarQube quality gate on new code only, mutation testing on core modules, architecture tests with ArchUnit so layering violations fail the build), write a short set of team conventions with the *rationale*, and reserve human review for design and risk. I also rotate who runs design review so the standard is not attached to me personally.

### Q108. Hexagonal architecture

The domain sits in the centre and defines *ports* (interfaces) for what it needs; adapters implement them for HTTP, JPA, Kafka, S3. Dependencies point inward only.

Testing payoff: domain logic is testable with plain JUnit and in-memory adapters, no Spring context, so the fast test tier covers the important logic in milliseconds; integration tests (Testcontainers) then verify only the adapters. The cost is more interfaces and indirection, so I apply it to the core domain modules, not to a CRUD service.

### Q109. DDD and service boundaries

An **aggregate** is a consistency boundary - one transaction, one aggregate, referenced from outside only by identity. A **bounded context** is a linguistic and model boundary; the same word means different things in two contexts ("customer" in billing versus in support), and forcing one shared model is the root of most distributed monoliths.

Mapping to microservices: a service should own one or a few bounded contexts and their data exclusively. If two services need the same table, the boundary is wrong. Context maps (shared kernel, customer-supplier, anti-corruption layer) are how I document and negotiate the integration - and the anti-corruption layer is what I insist on when integrating a legacy system.

---

## 7. Spring Framework and Spring Boot

### Q110. Dependency injection

DI inverts control of dependency construction so a class declares what it needs and the container supplies it, enabling substitution in tests and decoupling from concrete implementations.

Constructor injection is my default: dependencies are explicit, the object is fully initialized and can be `final`, it works without Spring in a unit test, and an over-long constructor is a visible SRP warning. Setter injection only for genuinely optional dependencies. Field injection I do not allow.

### Q111. Why field injection is discouraged `[T]`

The field cannot be `final`, so the object is mutable and not thread-safe by construction; you cannot instantiate the class in a plain unit test without reflection; the dependency list is hidden, so a class with twelve dependencies looks fine; and circular dependencies get silently resolved instead of failing fast.

Since Spring 4.3, a single-constructor class does not even need `@Autowired`, so constructor injection is no more verbose.

### Q112. Bean lifecycle

Instantiate → populate dependencies → `BeanNameAware`/`BeanFactoryAware`/`ApplicationContextAware` → `BeanPostProcessor.postProcessBeforeInitialization` → `@PostConstruct` → `InitializingBean.afterPropertiesSet` → custom `init-method` → `BeanPostProcessor.postProcessAfterInitialization` (this is where AOP proxies are created) → bean in use → `@PreDestroy` → `DisposableBean.destroy` → custom destroy method.

The key insight for interviews: proxies are created in the *after-initialization* post-processor, which is why `@PostConstruct` code runs on the raw target and self-invocation there is never proxied.

### Q113. Bean scopes

`singleton` (one per container, default), `prototype` (new instance per lookup; Spring does *not* manage its destruction, so `@PreDestroy` never runs), plus web scopes `request`, `session`, `application`, `websocket`.

Singletons must be stateless, or thread-safe, because one instance serves all concurrent requests. The most common production bug I see is an instance field on a `@Service` used as per-request state.

### Q114. Singleton depending on prototype `[T]`

The dependency is injected once, at singleton creation, so the same prototype instance is reused forever - the prototype scope is effectively lost.

Two fixes: inject an `ObjectProvider<T>` (or `Provider<T>`) and call `getObject()` per use - my preference, since it is explicit and testable; or use `@Lookup` method injection / `@Scope(proxyMode = TARGET_CLASS)`, which puts a proxy in place that resolves a new instance per call.

### Q115. Auto-configuration

`@SpringBootApplication` includes `@EnableAutoConfiguration`, which imports `AutoConfigurationImportSelector`. That reads candidate configuration class names from `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` (the `spring.factories` mechanism before Boot 2.7) on every jar in the classpath, filters them by `@Conditional` annotations, orders them with `@AutoConfigureBefore`/`After`, and registers the survivors.

The conditions are why it feels magical: `@ConditionalOnClass(DataSource.class)` plus `@ConditionalOnMissingBean(DataSource.class)` means "configure a DataSource only if the driver is present and the user has not defined one". Run with `--debug` to get the auto-configuration report showing matched and unmatched conditions - that is the answer to "why is this bean not being created".

### Q116. `@Conditional` and overriding

`@ConditionalOnMissingBean` is the back-off hook: define your own bean of that type and the auto-configured one steps aside. Ordering matters, so user configuration must be processed first - which it is, because auto-configuration is always registered last.

Others I use: `@ConditionalOnProperty` (feature flags at wiring level), `@ConditionalOnClass`/`OnMissingClass`, `@ConditionalOnWebApplication`, `@Profile`, and custom `Condition` implementations. To disable one outright: `@SpringBootApplication(exclude = DataSourceAutoConfiguration.class)` or `spring.autoconfigure.exclude`.

### Q117. Stereotype annotations

All are `@Component` meta-annotated, so scanning treats them identically. The functional differences are: `@Repository` adds exception translation (`PersistenceExceptionTranslationPostProcessor` converts vendor `SQLException`s into Spring's `DataAccessException` hierarchy), and `@Controller`/`@RestController` are detected by Spring MVC's handler mapping; `@RestController` also implies `@ResponseBody`.

`@Service` carries no behavior at all - it is documentation of intent, and useful for AOP pointcuts by annotation.

### Q118. Spring AOP proxies

Spring AOP is proxy-based and method-level only (not field access, not constructors). If the bean implements at least one interface, Spring uses JDK dynamic proxies by default; otherwise it uses CGLIB subclassing. Boot sets `spring.aop.proxy-target-class=true` by default, so CGLIB is generally used.

Consequences worth naming: CGLIB cannot proxy `final` classes or `final` methods, and it needs a usable constructor; JDK proxies only expose interface methods, so injecting by concrete class fails. For call-level interception (private methods, self-calls, constructors) you need AspectJ weaving instead.

### Q119. `@Transactional` self-invocation `[T]`

The annotation is implemented by a proxy that starts a transaction before delegating to the target. A self-call (`this.doWork()`) goes straight to the target instance and never touches the proxy, so no transaction. Same for `private`, `final` and `static` methods - the proxy cannot intercept them. And `@Transactional` on a method called from `@PostConstruct` runs before the proxy exists.

Two fixes: move the transactional method into a separate bean and inject it (my preference - it makes the boundary explicit); or self-inject / use `AopContext.currentProxy()` with `@EnableAspectJAutoProxy(exposeProxy = true)`, which works but hides the mechanism. Third option for the determined: AspectJ load-time weaving.

> *Hook: partial writes in a batch retry path caused exactly by this.*

### Q120. Propagation

`REQUIRED` (default) joins an existing transaction or starts one. `REQUIRES_NEW` suspends the current one and runs independently - the right choice for audit logging or a failure record that must survive the caller's rollback. `NESTED` uses a JDBC savepoint, so an inner rollback does not kill the outer transaction (JDBC only, not JTA). `SUPPORTS` joins if present, otherwise runs non-transactionally. `MANDATORY` throws if there is no transaction - a good guard on internal helpers. `NEVER` and `NOT_SUPPORTED` are the inverses.

The trap with `REQUIRES_NEW`: it holds two connections simultaneously, so under load it can exhaust the pool and even self-deadlock if the inner transaction waits on a row the outer one locked.

### Q121. Rollback rules `[T]`

By default Spring rolls back only on unchecked exceptions (`RuntimeException`) and `Error`. A **checked exception commits the transaction**, which surprises everyone - a `throw new IOException()` from your service leaves the partial write committed.

Fix with `@Transactional(rollbackFor = Exception.class)`, or standardize on unchecked domain exceptions. Second trap: catching an exception inside the transactional method means Spring never sees it and the transaction commits; and if a nested transaction already marked the transaction rollback-only, you get `UnexpectedRollbackException` at commit time.

### Q122. Isolation levels

`READ_UNCOMMITTED` allows dirty reads. `READ_COMMITTED` prevents dirty reads (PostgreSQL and Oracle default). `REPEATABLE_READ` also prevents non-repeatable reads (MySQL InnoDB default; and InnoDB's gap locks prevent most phantoms too). `SERIALIZABLE` prevents phantoms, at the cost of heavy locking or serialization failures you must retry.

Practical stance: keep `READ_COMMITTED` and solve the specific anomaly with optimistic locking (`@Version`) or an explicit `SELECT ... FOR UPDATE`, rather than raising the isolation level globally and paying for it everywhere.

### Q123. `@Async`

Backed by the same proxy mechanism, so the same self-invocation rule applies: an internal call runs synchronously. The method must return `void`, `Future`, or `CompletableFuture` - anything else and the return value is meaningless.

Configure your own executor; the default `SimpleAsyncTaskExecutor` (pre-Boot 3.2 behavior) creates a new thread per call and does not pool, which is unusable in production. Also note that exceptions from `void` async methods vanish unless you register an `AsyncUncaughtExceptionHandler`, and that `SecurityContext` and MDC do not propagate unless you configure a `TaskDecorator` (or set `DelegatingSecurityContextAsyncTaskExecutor`).

### Q124. `@Async` plus `@Transactional` `[T]`

Two proxies stack, and the transaction is bound to a thread via `ThreadLocal`. The async method runs on a different thread, so it does not inherit the caller's transaction - it starts its own, or none. Consequences: entities passed as arguments are detached in the new thread (`LazyInitializationException`), the caller's transaction may commit or roll back independently, and the async work can read pre-commit state.

Correct pattern: commit first, then trigger async work - ideally via `@TransactionalEventListener(phase = AFTER_COMMIT)` - and pass IDs rather than entities so the async method reloads within its own transaction.

### Q125. Circular dependencies

With field or setter injection Spring resolves cycles using the early-reference cache in `DefaultSingletonBeanRegistry` (the three-level cache), exposing a partially constructed bean. With constructor injection it cannot - neither bean can be created first - so it throws `BeanCurrentlyInCreationException`. Since Boot 2.6 circular references are disallowed by default.

`@Lazy` on one side works by injecting a proxy, and it is a legitimate escape hatch, but a cycle almost always signals a missing third component or a misplaced responsibility. I treat it as a design bug and extract the shared behavior.

### Q126. Configuration

Precedence, highest first: command-line args, `SPRING_APPLICATION_JSON`, OS environment variables, `application-{profile}.yml` outside the jar, then inside, `application.yml` outside then inside, `@PropertySource`, defaults. Config Data imports (`spring.config.import`) let you pull in AWS Parameter Store or Vault.

`@ConfigurationProperties` over `@Value` for anything non-trivial: type-safe binding, relaxed naming, JSR-303 validation with `@Validated`, nested objects, list and map binding, and IDE metadata. `@Value` is fine for a single value and required for SpEL.

Profiles: keep them for environment shape (`dev`, `prod`), not for business logic, and avoid profile-conditional beans that change behavior in ways tests never exercise.

### Q127. Actuator

Expose `/health` (with `liveness` and `readiness` groups for Kubernetes), `/info`, `/metrics` and `/prometheus`. Guard `/env`, `/configprops`, `/heapdump`, `/threaddump`, `/loggers` and `/mappings` behind authentication, because they leak configuration and secrets.

My production setup: put actuator on a separate management port not exposed by the ingress, require an authenticated role for anything beyond health, set `management.endpoint.health.show-details=when-authorized`, and write custom `HealthIndicator`s only for dependencies whose failure should actually take the instance out of rotation - a common mistake is failing readiness because a non-critical downstream is down, which turns a partial outage into a total one.

### Q128. Testing strategy

Pyramid: a large base of plain JUnit + Mockito unit tests with no Spring context (milliseconds); a middle tier of slice tests (`@WebMvcTest`, `@DataJpaTest`, `@JsonTest`, `@RestClientTest`) that load only the relevant part; a thin top of `@SpringBootTest` integration tests against Testcontainers for real Postgres/Kafka/LocalStack; and contract tests (Spring Cloud Contract or Pact) at service boundaries so consumer expectations are verified without a full end-to-end environment.

I also insist on `@DirtiesContext` being rare, on deterministic time via an injected `Clock`, and on no `Thread.sleep` in tests - use Awaitility.

### Q129. `@MockBean` and context caching `[T]`

Spring caches application contexts across test classes keyed by their configuration. `@MockBean` changes that key, so every distinct combination of mocks creates and starts a *new* context - which for a large app can be several seconds each and dominates suite runtime.

Mitigations: group mocks into a shared test configuration so the key is reused, prefer constructor injection with plain Mockito in unit tests, use slice tests, and inspect `spring.test.context.cache.maxSize` and the context-cache statistics logging to see how many contexts you are creating. Spring Framework 6.2 `@MockitoBean` behaves the same way regarding the cache key.

### Q130. MVC versus WebFlux `[A]`

WebFlux earns its place when you have very high concurrency with mostly IO-bound work and a fully reactive downstream stack (R2DBC, reactive Mongo, reactive HTTP client), or when you need streaming/backpressure semantics such as SSE fan-out to many clients.

Costs are real: a steep learning curve, painful debugging (no meaningful stack traces), `ThreadLocal` no longer works so security context and MDC need `Context` propagation, one blocking call anywhere poisons the event loop, and a much smaller pool of engineers who can maintain it.

In 2026 my default answer is: with virtual threads, Spring MVC gives you most of WebFlux's concurrency benefit with none of the cognitive cost, so I choose MVC + virtual threads unless I specifically need streaming or backpressure.

### Q131. HTTP clients

`RestTemplate` is in maintenance mode - synchronous, still supported, still everywhere in legacy code. `WebClient` is the reactive, non-blocking client and works fine in a blocking app via `.block()`, though that wastes its advantage. The JDK `HttpClient` (Java 11+) is a solid dependency-free option with HTTP/2 support.

In 2026 I use Spring's `RestClient` for synchronous calls - it has WebClient's fluent API with blocking semantics - and declarative HTTP interfaces (`@HttpExchange`) for typed clients. Whatever the choice, the things that actually matter are: explicit connect and read timeouts, a bounded connection pool, retry with backoff, a circuit breaker, and request/response logging with correlation IDs.

---

## 8. Spring Security, authentication and authorization

### Q132. The filter chain

A single `DelegatingFilterProxy` registered in the servlet container delegates to `FilterChainProxy`, which selects the first matching `SecurityFilterChain`. Typical order:

1. `DisableEncodeUrlFilter`, `WebAsyncManagerIntegrationFilter`
2. `SecurityContextHolderFilter` - loads the `SecurityContext` for the request and clears it afterwards
3. `HeaderWriterFilter` - security headers
4. `CorsFilter`
5. `CsrfFilter`
6. `LogoutFilter`
7. **Authentication filters** - `UsernamePasswordAuthenticationFilter`, `BearerTokenAuthenticationFilter`, OAuth2 filters, and your custom JWT filter
8. `RequestCacheAwareFilter`, `SecurityContextHolderAwareRequestFilter`
9. `AnonymousAuthenticationFilter` - assigns an anonymous token so downstream never sees null
10. `SessionManagementFilter`
11. `ExceptionTranslationFilter` - converts `AuthenticationException` to a 401 entry point and `AccessDeniedException` to 403
12. `AuthorizationFilter` - the final authorization decision

Authentication happens in step 7; authorization in step 12. `ExceptionTranslationFilter` sits *above* the authorization filter precisely so it can catch its exceptions.

### Q133. Authentication components

The filter builds an unauthenticated `Authentication` token and passes it to `AuthenticationManager` (usually `ProviderManager`), which walks a list of `AuthenticationProvider`s asking `supports(tokenType)`. `DaoAuthenticationProvider` loads the user through `UserDetailsService`, verifies the password with `PasswordEncoder`, and returns a fully populated `Authentication` with authorities. The filter stores it in `SecurityContextHolder`, which is `ThreadLocal`-backed (hence the propagation problem on async threads), and the `SecurityContextRepository` persists it for session-based flows.

### Q134. Sessions versus JWT

Sessions: server-side state, instantly revocable, opaque to the client, small cookie; cost is sticky sessions or a shared store (Redis via Spring Session), which is a scaling and availability concern but a solved one.

JWT: self-contained, stateless, verifiable without a lookup, good for cross-service and cross-domain; cost is that you cannot revoke before expiry, the payload is readable by anyone holding it, claims go stale (a role revoked at 10:00 still works until the token expires), and tokens grow with claims.

My default for a first-party web app is sessions with Redis - the "stateless is simpler" argument usually evaporates once you add a revocation list. JWTs I use for service-to-service and for genuinely federated scenarios, with short lifetimes.

### Q135. Revoking a JWT `[T]`

You cannot un-issue it, so every option is a compromise:

1. **Short access-token lifetime** (5-15 minutes) plus refresh tokens - revoke at the refresh step. This is the standard answer and usually sufficient; you accept a bounded window of stale authorization.
2. **Denylist** of revoked JTIs in Redis, checked per request - correct, but reintroduces the state you removed, though the store is far smaller than a session store and can expire entries at token expiry.
3. **Token version claim** compared against a per-user counter - one cheap lookup, invalidates all of a user's tokens at once, good for "log out everywhere" and password change.
4. **Key rotation** to revoke everything at once - a blunt emergency instrument.

The honest interview answer is to name the trade-off explicitly: stateless authentication and immediate revocation are fundamentally in tension; pick which one the requirement actually needs.

### Q136. Access and refresh tokens

Access token: short-lived (5-15 min), sent on every request, carries claims. Refresh token: long-lived (days to weeks), used only against the token endpoint, stored server-side or at minimum tracked.

Storage: for browsers, a refresh token in an `HttpOnly`, `Secure`, `SameSite=Strict` cookie scoped to the token endpoint; access token in memory. For mobile, the platform keystore.

Rotation: issue a new refresh token on every use and invalidate the previous one. Reuse detection - if an already-used refresh token is presented, the token family has leaked, so revoke the whole family and force re-authentication. That is what turns rotation from cosmetic into a real defense.

### Q137. Grant types in 2026

Recommended: **Authorization Code + PKCE** for all interactive clients including SPAs and mobile, and **Client Credentials** for machine-to-machine. **Device Code** for input-constrained devices.

Deprecated by the OAuth 2.1 / Security BCP direction: **Implicit** (tokens in the URL fragment, no refresh, leaks through history and referrers) and **Resource Owner Password Credentials** (the client handles the user's password, defeats federation and MFA). Both should be treated as unavailable in a new design.

### Q138. OAuth2 versus OIDC

OAuth2 is an *authorization* framework: it gets a client a token to access a resource. It says nothing about who the user is - using an access token to infer identity is the classic mistake.

OIDC is an identity layer on top: it adds the `id_token` (a signed JWT with standard claims: `sub`, `iss`, `aud`, `exp`, `nonce`), the `/userinfo` endpoint, standard scopes (`openid`, `profile`, `email`), and discovery via `/.well-known/openid-configuration` with a JWKS endpoint for key rotation. If you need to know *who* the user is, you need OIDC.

### Q139. PKCE

Proof Key for Code Exchange. The client generates a random `code_verifier`, sends `code_challenge = SHA256(verifier)` with the authorization request, and must present the original verifier when exchanging the code for tokens.

It prevents authorization code interception: on mobile, a malicious app registering the same custom URL scheme could steal the code; in a browser, the code can leak through logs, referrers or history. Without PKCE, whoever holds the code can redeem it (public clients have no secret). With PKCE, the code is useless without the verifier. It is now recommended for confidential clients too.

### Q140. JWT in `localStorage` `[T]`

`localStorage` is readable by any JavaScript on the origin, so a single XSS - including one in a third-party dependency - exfiltrates the token, and the attacker then holds a valid credential until it expires, off your machine and beyond your reach.

Alternative: an `HttpOnly`, `Secure`, `SameSite` cookie, which JavaScript cannot read. That reintroduces CSRF exposure, so pair it with `SameSite=Lax/Strict` and a CSRF token for state-changing requests. The pragmatic pattern is: refresh token in an `HttpOnly` cookie, access token held in a JavaScript closure in memory only (lost on refresh, re-obtained silently). And none of this substitutes for eliminating the XSS: a strict Content Security Policy and output encoding are the primary control.

### Q141. CSRF

The attacker makes the victim's browser send an authenticated request to your site using credentials the browser attaches *automatically*. That is the key condition - it applies to cookies and HTTP Basic, not to an `Authorization: Bearer` header that JavaScript must add deliberately.

So a purely token-based API can disable CSRF. You must keep it on when: any authentication relies on cookies, you serve server-rendered forms, or you use a hybrid (cookie-stored JWT) - that last case is a very common oversight, where teams disable CSRF "because we use JWT" while storing the JWT in a cookie.

Defenses: synchronizer token or double-submit cookie (Spring's `CookieCsrfTokenRepository`), plus `SameSite` cookies as defense in depth.

### Q142. CORS

CORS is a *browser* enforcement mechanism that relaxes the same-origin policy. A non-simple request triggers a preflight `OPTIONS` carrying `Origin`, `Access-Control-Request-Method` and headers, and the server replies with the allowed set.

Two things to say in an interview: CORS is not authorization - it does not protect your API, since curl and server-side clients ignore it entirely; and `allowedOrigins("*")` combined with `allowCredentials(true)` is rejected by the spec and by Spring, which is a signal that wildcarding credentials is unsafe.

Configure it once, in Spring Security's `cors()` backed by a `CorsConfigurationSource`, not with scattered `@CrossOrigin` annotations - and note the CORS filter must run before authentication so preflights are not rejected with a 401.

### Q143. Method security

Enable with `@EnableMethodSecurity`. `@PreAuthorize` evaluates before invocation and takes SpEL: `@PreAuthorize("hasRole('ADMIN') or #userId == authentication.principal.id")`. `@PostAuthorize` runs after and can inspect the return value (`returnObject.ownerId == authentication.name`) - useful, but the method has already executed, so any side effect has happened. `@Secured` and JSR-250 `@RolesAllowed` are role-only and less expressive. `@PreFilter`/`@PostFilter` filter collections, which is elegant but do not use `@PostFilter` on a large result set - filter in the query instead.

Note it is AOP-based, so the same self-invocation limitation applies, and remember `hasRole('ADMIN')` implicitly prepends `ROLE_` while `hasAuthority('ADMIN')` does not - a frequent source of "why is my rule not matching".

### Q144. Multi-tenant authorization

Layered, because a single control will eventually be bypassed:

1. Tenant identity comes from the *authenticated token*, never from a request parameter or header the client controls.
2. Resolve it once in a filter into a request-scoped context, and propagate it explicitly (not via a raw `ThreadLocal` on async paths).
3. Enforce at the data layer, not in each service method: a Hibernate `@Filter` or a `@Where` clause applied globally, or Postgres row-level security keyed on a session variable - so a developer who forgets the `WHERE tenant_id = ?` still cannot leak.
4. Include the tenant in every cache key, every queue message and every log line.
5. Test it: an automated test suite that authenticates as tenant A and asserts 404 (not 403 - do not confirm existence) on every tenant B resource.

The strongest isolation is separate schemas or databases per tenant; it costs migration complexity and connection pool pressure, but for regulated data it is often the only defensible answer.

### Q145. Password hashing

Use a memory-hard, deliberately slow algorithm with a per-password salt. **Argon2id** is the current recommendation (OWASP: 19 MiB memory, 2 iterations, 1 degree of parallelism as a baseline). **BCrypt** remains acceptable with a work factor of 10-12 and is what Spring's `DelegatingPasswordEncoder` defaults to; note its 72-byte input truncation. **PBKDF2** when FIPS compliance forces it, at 600k+ iterations for SHA-256.

Choose the cost by measuring: tune so hashing takes roughly 250-500ms on production hardware, then re-evaluate annually. Use `DelegatingPasswordEncoder` so the stored hash carries its algorithm prefix (`{bcrypt}`, `{argon2}`) and you can upgrade in place on successful login.

### Q146. OWASP Top 10 with Java mitigations

1. **Broken Access Control** - deny by default, enforce server-side per resource, never trust client-supplied IDs; test for IDOR.
2. **Cryptographic Failures** - TLS everywhere, AES-GCM, no MD5/SHA-1 for passwords, no hardcoded keys, use KMS.
3. **Injection** - parameterized queries and JPA parameter binding; validate and allowlist; encode output to stop XSS.
4. **Insecure Design** - threat modelling, abuse cases, rate limits designed in rather than bolted on.
5. **Security Misconfiguration** - actuator endpoints locked down, stack traces off, default credentials removed, security headers set.
6. **Vulnerable Components** - OWASP Dependency-Check or Snyk in CI, an SBOM, and a policy for patching (Log4Shell is the reference lesson).
7. **Identification and Authentication Failures** - MFA, no credential stuffing tolerance, secure session handling, account lockout with backoff.
8. **Software and Data Integrity Failures** - signed artifacts, verified base images, no unsafe Java deserialization of untrusted input (use JSON with type restrictions).
9. **Logging and Monitoring Failures** - log authentication events and authorization denials, never log secrets or tokens, alert on anomalies.
10. **SSRF** - allowlist outbound destinations, block link-local `169.254.169.254`, use IMDSv2, resolve and validate the IP after redirects.

### Q147. SQL injection in JPA `[T]`

Prepared statements protect *parameter values*, not query structure. Injection still occurs through:

- Concatenated JPQL or native queries: `em.createQuery("... WHERE name = '" + name + "'")`.
- Dynamic `ORDER BY` or column names built from user input - these cannot be bound as parameters, so they must be validated against an allowlist.
- `LIKE` patterns concatenated without escaping wildcard characters.
- Spring Data `@Query` with SpEL that interpolates user input, or `nativeQuery = true` with string building.
- Dynamic table names in multi-tenant schema switching.

Rule: every user-controlled value is a bound parameter; every user-controlled *identifier* is checked against a fixed allowlist. Add static analysis to catch concatenation into query strings.

### Q148. Secrets in Spring Boot on AWS

No secrets in `application.yml`, environment variables in a manifest, or the container image. Use AWS Secrets Manager (supports rotation, encrypted with KMS) or Parameter Store SecureString for lower-cost cases, loaded via `spring.config.import=aws-secretsmanager:` from Spring Cloud AWS, with the task or pod assuming an IAM role (IRSA on EKS, task role on ECS) so there are no static credentials anywhere.

For databases, prefer IAM authentication or Secrets Manager-managed rotation with a short-lived credential. Add: least-privilege IAM per service, secret scanning in CI (gitleaks) and a pre-commit hook, audit access via CloudTrail, and a documented rotation runbook. If a secret ever reaches git history, treat it as compromised and rotate - removing the commit is not remediation.

### Q149. Zero-trust service-to-service `[A]`

Assume the network is hostile; every call is authenticated and authorized regardless of origin.

Mechanism: mutual TLS with short-lived, automatically rotated certificates (SPIFFE/SPIRE identities, or a service mesh like Istio/Linkerd issuing them), so each workload has a cryptographic identity rather than an IP-based trust assumption. Layer authorization on top: mesh authorization policies for coarse "who may call whom", plus token-based (OAuth2 client credentials with audience-restricted, short-lived tokens) for fine-grained scopes at the application layer. Propagate the *end user* identity separately from the service identity - a token exchange so the downstream can enforce user-level rules without re-authenticating.

Supporting practices: no long-lived credentials, deny-by-default policies as code and reviewed, full audit of allow/deny decisions, and continuous verification rather than a one-time perimeter check. The cost is real operational complexity, so I introduce it where the blast radius justifies it - starting with the services holding regulated data.

---

## 9. Databases, JPA and persistence

### Q150. Entity lifecycle

**Transient**: new, no identity, not tracked. **Managed**: attached to a persistence context; changes are auto-flushed at commit through dirty checking (which is why calling a setter without any `save()` still writes). **Detached**: has identity but the context is closed; lazy loads fail; `merge()` reattaches a copy. **Removed**: scheduled for deletion at flush.

The dirty-checking behavior is the one that catches people: modifying a managed entity inside a transaction persists whether or not you intended it.

### Q151. N+1 selects `[T]`

One query fetches N parents, then accessing a lazy association fires one query per parent - N+1 round trips. It is invisible in a small dev dataset and lethal in production.

Fixes and their drawbacks:

1. **`JOIN FETCH`** in JPQL - one query, but it multiplies rows for collections (a cartesian product with two collections), and **pagination with `JOIN FETCH` on a collection makes Hibernate fetch everything into memory and paginate in Java** - it warns `HHH000104`.
2. **`@EntityGraph`** - declarative and reusable on Spring Data repository methods, same cartesian caveat.
3. **`@BatchSize(size = 25)`** or `hibernate.default_batch_fetch_size` - turns N+1 into N/25+1 queries with an `IN` clause; no cartesian product, works with pagination. My usual default.
4. **Two-query approach**: fetch IDs with pagination, then fetch entities with a fetch join on those IDs.
5. **DTO projection** with a constructor expression or Spring Data interface projection - fetch exactly what you need and skip the entity graph entirely; my preference for read-heavy endpoints.

Detection: enable `hibernate.generate_statistics`, assert query counts in integration tests, and use datasource-proxy or Hypersistence Utils to fail a test when the count exceeds a threshold. That is how you keep it from coming back.

### Q152. `LazyInitializationException` `[T]`

Lazy associations are proxies that need an open session. Once the transaction ends and the session closes, touching the proxy throws.

The wrong fixes: switching to `EAGER` (now you over-fetch on every query, everywhere), or enabling `spring.jpa.open-in-view` (Boot's default, and it keeps a database connection held for the full request including view rendering, so it hides N+1 problems in the serialization layer and exhausts the pool under load - I turn it off explicitly and fix what breaks).

The right fixes: fetch what you need inside the transaction using a fetch join or entity graph; or map to a DTO inside the transactional boundary so nothing lazy escapes; or use `Hibernate.initialize()` deliberately where a conditional load is genuinely needed.

### Q153. Caching levels

First-level cache is the persistence context - per transaction, mandatory, gives you identity guarantees within a session. Second-level is shared across sessions per `SessionFactory` (Ehcache, Hazelcast, Infinispan), plus an optional query cache.

Dangers: stale data when anything writes to the database outside Hibernate (bulk updates, another service, a DBA script); cache invalidation across a cluster requiring distributed invalidation; the query cache being notoriously easy to make slower than no cache because any write to a table invalidates all its cached queries.

I enable the second-level cache only for genuinely read-mostly reference data, and I prefer an explicit application cache (Caffeine or Redis) over the entity cache, because the invalidation rules are then visible rather than implicit.

### Q154. Locking

**Optimistic**: a `@Version` column; on update Hibernate adds `WHERE version = ?` and throws `OptimisticLockException` if zero rows changed. No locks held, so it scales; the caller must handle the conflict, usually by reloading and retrying. Default choice for user-facing edits.

**Pessimistic**: `SELECT ... FOR UPDATE` via `@Lock(LockModeType.PESSIMISTIC_WRITE)` or `PESSIMISTIC_READ`. Holds a row lock for the transaction's duration, so it serializes contenders and risks deadlocks and lock-wait timeouts. Justified for short critical sections with high contention where retrying is expensive - inventory decrement, seat reservation.

Always set a lock timeout (`jakarta.persistence.lock.timeout`) with pessimistic locks so a stuck transaction does not cascade.

### Q155. Bidirectional `@OneToMany`

The **`@ManyToOne` side owns the relationship** because it holds the foreign key. `mappedBy` on the `@OneToMany` side declares it as the inverse, non-owning side.

If you add a child to the parent's collection but never set `child.setParent(parent)`, nothing is persisted - the owning side was never modified. Always write helper methods:

```java
public void addItem(Item item) { items.add(item); item.setOrder(this); }
public void removeItem(Item item) { items.remove(item); item.setOrder(null); }
```

Also: use `Set` with a stable `equals`/`hashCode` (based on a business key, not the generated ID, which is null before persist), and avoid `@OneToMany` without `mappedBy`, which creates a surprise join table.

### Q156. `CascadeType.REMOVE` on a large collection `[T]`

Hibernate must load every child entity to apply lifecycle callbacks and fire an individual `DELETE` per row - so deleting a parent with 100,000 children loads 100,000 objects into the persistence context and issues 100,000 statements. Memory and transaction duration both explode, and it silently gets worse as data grows.

Alternatives: a bulk `DELETE FROM child WHERE parent_id = ?` (then clear the persistence context, because bulk operations bypass it), a database-level `ON DELETE CASCADE` foreign key, or soft delete plus an asynchronous purge job. Also note `orphanRemoval = true` has the same characteristics.

### Q157. `save`, `saveAndFlush`, `persist`, `merge`

`persist` makes a *new* entity managed and throws if it already has an identifier that exists. `merge` copies the state of a detached instance into a managed copy and **returns that copy** - the instance you passed in remains detached, which is the classic "my changes disappeared" bug.

Spring Data's `save` delegates to `persist` when `isNew()` is true and `merge` otherwise. `saveAndFlush` additionally forces the SQL to be issued immediately rather than at commit - useful when you need a generated value or want a constraint violation to surface at a known point, but it forfeits batching.

### Q158. Efficient pagination

`OFFSET n` makes the database scan and discard n rows, so page 10,000 is slow and cost grows linearly with depth. Worse, with concurrent inserts, rows shift between pages so users see duplicates or gaps.

Use **keyset (seek) pagination**: `WHERE (created_at, id) < (:lastCreatedAt, :lastId) ORDER BY created_at DESC, id DESC LIMIT 20`, with a matching composite index. Constant cost at any depth and stable under concurrent writes. The trade-off is no random access to "page 500", which is almost never a real requirement - infinite scroll and "next" links fit naturally.

Also avoid `COUNT(*)` on every page request; use an estimated count or `Slice` instead of `Page` in Spring Data.

### Q159. Indexing

Composite index column order follows the **leftmost prefix rule**: an index on `(a, b, c)` serves predicates on `a`, `a,b`, and `a,b,c` - not on `b` alone. Order by equality predicates first, then range, then the sort column. A **covering index** includes every column the query touches (via `INCLUDE` in Postgres) so the plan is index-only, skipping the heap fetch.

Reasons an index is ignored: a function or implicit cast on the indexed column (`WHERE lower(email) = ?` needs a functional index), leading wildcard `LIKE '%x'`, low selectivity where a sequential scan is genuinely cheaper, stale statistics, or type mismatch between parameter and column. Also remember every index slows writes and consumes memory, so unused indexes should be dropped - `pg_stat_user_indexes` tells you which.

### Q160. Execution plans

`EXPLAIN (ANALYZE, BUFFERS)` in Postgres gives estimated *and* actual rows plus IO. What I look at: a large divergence between estimated and actual rows (stale statistics or a correlation the planner cannot see), sequential scans on large tables in a selective query, nested loops with a high inner row count, sorts spilling to disk (`external merge Disk:`), and high `shared read` versus `shared hit` indicating cache misses.

Actions in order: fix the query shape, add or reorder an index, `ANALYZE` to refresh statistics, increase `work_mem` for a sort, or restructure into a materialized view if the aggregate is genuinely expensive and slightly stale data is acceptable.

### Q161. HikariCP sizing

The pool is a concurrency limit, not a performance dial. A larger pool means more concurrent queries competing for the same finite CPUs and disks, and past the saturation point throughput flattens while latency rises - plus you risk exhausting the database's own `max_connections` across all instances.

HikariCP's own guidance: `connections = ((core_count × 2) + effective_spindle_count)` as a starting point, which for a typical cloud database lands around 10-20 per instance. Then multiply by instance count and check it against the database limit, reserving headroom for admin connections and using a proxy such as RDS Proxy or PgBouncer when you have many instances or Lambda.

Set `connectionTimeout` (fail fast rather than pile up), `maxLifetime` shorter than any database or load-balancer idle timeout, `leakDetectionThreshold` in non-production, and alert on `hikaricp_connections_pending` - queueing there is the single best early warning of database trouble.

### Q162. SQL versus NoSQL `[A]`

I start from access patterns, not from the data. Questions: what are the top five queries by volume; do we need multi-entity transactions; is the schema stable or genuinely heterogeneous; what is the read/write ratio and the growth curve; what consistency does the business actually require?

Relational is my default because ACID transactions, joins, ad-hoc querying and mature tooling cover most business systems, and Postgres handles JSON, full text and even vectors well enough to defer a second store. I reach for NoSQL when there is a specific, dominant pattern: key-value lookups at extreme scale and predictable single-digit-millisecond latency (DynamoDB), document storage where the aggregate is always read whole, time-series or append-only event data, or a graph traversal that is genuinely recursive.

The failure mode I have seen most often is choosing a document store for relational data and then reimplementing joins in application code - so I ask "what query becomes impossible if we choose this?" before committing.

### Q163. Zero-downtime migrations

Rules, all following from the fact that old and new code run simultaneously during a rollout:

1. **Expand and contract.** Add the new column nullable, backfill in batches, dual-write from the application, switch reads, then drop the old column in a later release.
2. **Never** rename or drop in the same deployment that changes the code.
3. Additive only within a deployment; destructive changes only after the previous version is fully retired.
4. Migrations must be backward compatible with the previous application version, because rollback must remain possible.
5. Avoid long-running locks: create indexes `CONCURRENTLY`, add constraints as `NOT VALID` then validate separately, batch backfills with a bounded transaction size and a sleep between batches.
6. Set a `lock_timeout` on migrations so a blocked DDL fails instead of queuing every query behind it.

Flyway with versioned, immutable, checksum-verified scripts run as a separate pipeline step or init container - not on application startup in a multi-instance deployment, where several instances race (or use Flyway's lock and accept the startup delay).

### Q164. Changing a column type on 500M rows `[A]`

Never `ALTER TABLE ... ALTER COLUMN TYPE` directly - it rewrites the whole table under an exclusive lock.

The expand-contract shadow-column approach:

1. Add `amount_new` of the target type, nullable, with a low-lock `ALTER` (adding a nullable column without a default is metadata-only in modern Postgres).
2. Deploy application code that **dual-writes** both columns, reading from the old one.
3. Backfill in batches - 10,000 rows per transaction, keyed on the primary key, throttled and monitored for replication lag, resumable via a progress table.
4. Add a constraint or trigger to guarantee consistency, and run a verification query comparing the two columns.
5. Deploy code that reads from `amount_new` while still writing both. Bake for a release.
6. Stop writing the old column; drop it in a later release, then rename if cosmetics matter (a rename is also a separate expand-contract cycle, or just live with the name).

Throughout: feature-flag the read switch so rollback is instant, run the backfill off-peak, and rehearse the entire sequence on a production-sized copy first. If a rewrite is unavoidable, consider a logical-replication cut-over to a new table instead.

> *Hook: a large-table type migration executed with zero downtime, quoting the row count and the backfill duration.*

---

## 10. Microservices, APIs and distributed systems

### Q165. Service boundaries `[A]`

I derive boundaries from bounded contexts and from the *rate and reason of change*, not from nouns or from team structure alone (though Conway's Law means team structure will win if I ignore it, so I align them deliberately).

Signals a boundary is wrong: two services always deploy together; a change to one feature touches three repositories; services share a database or a table; chatty synchronous call chains where one request fans out through four hops; a service that is only ever called by one other service; distributed transactions appearing in the design; and a shared "common" library that every service must upgrade in lockstep.

My practical approach is to start with a modular monolith with enforced module boundaries (ArchUnit, package-private APIs), let the seams prove themselves under real change, and extract a service only when there is a concrete driver: independent scaling, independent deployment cadence, different reliability requirement, or team autonomy.

### Q166. Monolith versus microservices in 2026 `[A]`

I recommend staying monolithic when the team is under roughly 20-30 engineers, the domain is not yet stable, deployment frequency is not the bottleneck, and the organization lacks the platform maturity - CI/CD, observability, on-call, infrastructure as code - to operate a distributed system.

The costs people underestimate: every in-process call becomes a network call that can fail, be slow, or be duplicated; local transactions become sagas; debugging requires distributed tracing; testing requires contract tests; and the operational surface multiplies. You trade a code-complexity problem for an operations-complexity problem, and only the second one wakes you at 3am.

What I actually advocate is a modular monolith with clean internal boundaries and an independent deployment path, extracting services where there is a measured need. That preserves the option value without paying the premium up front.

### Q167. REST, idempotency and status codes

Richardson maturity: level 0 (single endpoint, RPC over HTTP), 1 (resources), 2 (HTTP verbs and status codes - where most real APIs sit and where I stop unless there is a reason), 3 (HATEOAS, rarely worth it for internal APIs).

Idempotency by method: `GET`, `PUT`, `DELETE` and `HEAD` are idempotent by specification; `POST` is not, which is why creation endpoints need an `Idempotency-Key` header. `PUT` replaces the whole resource; `PATCH` is a partial update and is not idempotent unless you define it to be (JSON Merge Patch usually is; JSON Patch with `add` to an array is not).

Status codes: 200 with a body, 201 with a `Location` header for creation, 202 for accepted-but-async, 204 for a successful delete or empty response, 400 for malformed syntax, 401 unauthenticated versus 403 unauthorized, 404 for missing (and deliberately for "exists but you may not see it", to avoid leaking existence), 409 for conflict such as an optimistic-lock failure, 412 for a failed precondition, 422 for semantically invalid input, 429 with `Retry-After`, 503 with `Retry-After` for shedding load. Errors should follow RFC 9457 `application/problem+json` so clients can parse them uniformly.

### Q168. Versioning

Options: URI path (`/v1/orders`) - visible, cacheable, trivially routable, and my default for public APIs despite purist objections; custom header or `Accept` media type versioning - cleaner URLs but harder to test and to route at the edge; query parameter - avoid.

The more important half is the policy: version only on *breaking* changes, and make additive changes non-breaking by having clients tolerate unknown fields (Postel's law, enforced in the client library). Publish a deprecation policy with a fixed support window, emit `Deprecation` and `Sunset` headers (RFC 8594), instrument per-version usage so you know exactly who is left, contact those consumers directly, and only then retire. Never run more than two major versions - the maintenance cost is what actually kills you, so the discipline is aggressive retirement, not clever versioning.

### Q169. CAP and PACELC

CAP: during a network **partition**, you must choose between consistency and availability. The common misstatement is "pick two of three" - partition tolerance is not optional in a distributed system, so the real choice is CP or AP, and only while partitioned.

PACELC is more useful because it describes the other 99.9 percent of the time: **if Partitioned, choose Availability or Consistency; Else, choose Latency or Consistency.** Synchronous replication across regions costs latency on every write even when the network is healthy; that is the trade-off you actually live with daily. DynamoDB with eventually consistent reads is PA/EL; a single-leader RDBMS with synchronous replicas is PC/EC; Cassandra is tunable per query.

Framing it this way in an interview signals you have operated these systems rather than read about them.

### Q170. Explaining eventual consistency

To a product owner I do not use the term. I say: "When you change this, the update is guaranteed, but it may take up to a few seconds to appear on that other screen. What should the user see during that window?" That converts an architecture property into a product decision they can actually make.

Making it acceptable in the UI: read-your-own-writes for the acting user (route their reads to the leader, or optimistically render their own change), explicit pending states rather than silently stale data, and a bounded, monitored staleness window with an SLO ("99.9 percent of updates visible within 2 seconds"). Where the business genuinely cannot tolerate it - money movement, inventory at the point of sale - I keep that specific operation strongly consistent rather than arguing.

### Q171. Sagas

A long-lived business transaction split into local transactions, each with a compensating action, because a distributed two-phase commit is not viable across services.

**Choreography**: each service reacts to events. No central coordinator, loose coupling, good for 2-3 steps. Beyond that nobody can tell you what the flow is or where it is stuck, and cyclic event dependencies creep in.

**Orchestration**: a coordinator (a state machine, Temporal, Step Functions, or a Camunda-style engine) drives the steps. Explicit, observable, testable, easy to add timeouts and retries; cost is a component that must itself be highly available and can accrete business logic.

I use orchestration for anything with more than three steps or with money involved, because operability matters more than coupling purity. Either way the hard parts are the same: compensations are semantic, not rollbacks (you refund, you do not un-charge), steps must be idempotent because retries are certain, and you need to handle the semantic lock problem - data is visible in an intermediate state, so model it explicitly (`PENDING`, `RESERVED`) rather than pretending it is atomic.

### Q172. Transactional outbox `[T]`

The problem is the dual-write: you cannot atomically commit to your database *and* publish to a broker. If you save then publish and the process dies in between, the state changed but nobody was told. If you publish then save and the save fails, you have announced something that never happened. Wrapping both in a distributed transaction (XA) is slow, poorly supported, and puts a broker outage in your write path.

The outbox writes the event **into a table in the same local transaction** as the state change - one atomic commit. A separate process then relays rows to the broker: either polling the table, or tailing the write-ahead log with change data capture (Debezium), which is lower latency and does not load the database with polling.

This gives at-least-once delivery, never zero, so consumers must be idempotent. The inverse pattern on the consumer side is the inbox: record processed message IDs in the same transaction as the effect, so redelivery is a no-op.

### Q173. Idempotent payment API

The client generates an `Idempotency-Key` (a UUID) per logical operation and resends the same key on every retry.

Server side: insert the key into a table with a unique constraint **inside the same transaction** as the payment. If the insert succeeds, process and store the response body and status against the key. If it violates the constraint, the request is a retry - return the stored response. If the stored record is still in-flight, return 409 or block briefly, so two concurrent retries cannot both proceed. Scope the key to the client and validate that the request payload hash matches the original, otherwise a client reusing a key with different content gets a 422 rather than a silently wrong result.

Also: give keys a defined retention (24 hours is typical) documented to clients, make downstream calls to the payment processor carry their own idempotency key, and use a state machine on the payment record (`INITIATED → AUTHORIZED → CAPTURED`) with transitions guarded so a duplicate cannot double-capture.

> *Hook: a payments or ordering flow where duplicate submissions were eliminated.*

### Q174. Exactly-once

End-to-end exactly-once *delivery* is impossible in an asynchronous system with failures - the classic two-generals result. What is achievable is exactly-once **processing**, by combining at-least-once delivery with idempotent or transactional effects.

What Kafka actually gives you: an idempotent producer (a producer ID and sequence number let the broker deduplicate retries within a session, so no duplicates on the log), and transactions that atomically write to multiple partitions *and* commit consumer offsets, giving exactly-once semantics for the read-process-write pattern **within Kafka** (`processing.guarantee=exactly_once_v2`). The moment your side effect leaves Kafka - an HTTP call, a database write in another system - you are back to needing idempotency on your side.

So my answer is always: design consumers to be idempotent, use a dedup key or an inbox table, and treat Kafka transactions as an optimization for Kafka-to-Kafka pipelines rather than a general guarantee.

### Q175. Kafka fundamentals

A topic is split into **partitions**, which are the unit of parallelism and of ordering - ordering is guaranteed *within* a partition only, and the partition is chosen by `hash(key) % partitions`, so keying by entity ID gives per-entity ordering.

A **consumer group** distributes partitions among members; one partition is consumed by at most one member of a group, so consumer parallelism is capped by partition count. **Rebalancing** happens on membership change and, with the eager protocol, stops the world for the group; cooperative incremental rebalancing (the default now) only moves the affected partitions. Static group membership plus a tuned `session.timeout.ms` avoids rebalances caused by long processing pauses; `max.poll.interval.ms` exceeded is the classic cause of a consumer being kicked out mid-batch.

**Offsets** are consumer-controlled. Auto-commit gives at-most-once or at-least-once depending on timing, both accidentally; I disable it and commit after processing, accepting at-least-once and making the handler idempotent. Durability comes from `acks=all` plus `min.insync.replicas=2` on a replication factor of 3 - `acks=1` will lose data on a leader failure.

### Q176. Increasing partitions `[T]`

Ordering breaks for existing keys. The partition is `hash(key) % partitionCount`, so changing the count remaps keys: messages for key K written before the change sit in partition 3, and new ones go to partition 7. Two consumers now process that key's history and its future concurrently, with no ordering relationship between them.

Also: partitions can only be increased, never decreased, and log-compacted topics can end up with two live records for the same key in different partitions.

Mitigations: over-provision partitions at topic creation (they are cheap up to a point); or create a new topic with the new partition count and migrate consumers with a controlled cut-over; or use a custom partitioner with consistent hashing if you must scale live. In practice, plan capacity up front - this is one of the few Kafka decisions that is genuinely hard to undo.

### Q177. Trace context propagation

W3C Trace Context (`traceparent` / `tracestate` headers) carries the trace ID, span ID and sampling flag. On synchronous HTTP calls, instrumentation copies it automatically.

Async boundaries are where it breaks, because the context lives in a `ThreadLocal` that the new thread does not inherit. Handling: for executors, wrap with a context-propagating decorator (Micrometer's `ContextSnapshot`, Spring's `TaskDecorator`, or OpenTelemetry's `Context.taskWrapping`) - a plain `ThreadPoolTaskExecutor` will lose it. For messaging, inject the context into the message headers on publish and extract it on consume, linking the consumer span to the producer span as a *link* rather than a parent when the work is batched. For reactive code, propagate through Reactor's `Context` rather than `ThreadLocal`. For scheduled and batch jobs, start a fresh root trace with a meaningful attribute.

Then make it useful: put the trace ID in the MDC so every log line carries it, return it in an error response header so support can jump from a customer complaint straight to the trace, and sample tail-based on errors and latency so you keep the traces that matter.

### Q178. Discovery, load balancing and mesh

**Server-side**: clients call a stable endpoint (ALB, Kubernetes Service) that distributes traffic. Simple, language-agnostic, one more network hop, and the balancer has no view of application-level health beyond a probe.

**Client-side**: the client fetches the instance list from a registry (Eureka, Consul) and chooses itself, so it can do zone-aware routing, least-outstanding-requests balancing, and immediate ejection of a failing host. Cost is a smart client per language and a registry to operate.

**Service mesh** (Istio, Linkerd): moves that logic into a sidecar or ambient proxy, so it is language-agnostic again, and adds mTLS, retries, timeouts, circuit breaking, traffic shifting and consistent telemetry as configuration rather than code. Cost is real: a control plane to run, per-request latency and memory overhead, and a new failure domain that your on-call must understand.

My position: on Kubernetes, start with Services plus client-side resilience libraries; adopt a mesh when you need mTLS everywhere, uniform traffic policy across polyglot services, or progressive delivery - not because it is fashionable.

### Q179. Rate limiting

**Token bucket**: tokens refill at a fixed rate up to a capacity; allows bursts up to the bucket size. My default, and what most cloud gateways implement. **Leaky bucket**: outflow is strictly constant, smoothing traffic entirely - good for protecting a downstream with a hard throughput limit. **Fixed window**: trivial but allows a 2x burst across the window boundary. **Sliding window log** is exact but stores every timestamp; **sliding window counter** interpolates between two fixed windows and is the usual compromise.

Where to enforce: at the edge (API Gateway, WAF, ingress) for coarse per-client protection and to keep abusive traffic off your compute; in the application for per-tenant or per-endpoint business rules that need identity context; and at the client with a concurrency limiter or semaphore to protect the downstream. Distributed enforcement needs shared state - Redis with an atomic Lua script, or a token-bucket library like Bucket4j - and you must decide the failure mode: fail-open (availability) or fail-closed (protection) when Redis is unreachable.

Always return `429` with `Retry-After` and `X-RateLimit-*` headers, and rate limit by authenticated identity rather than IP where possible, since NAT makes IP a poor key.

### Q180. Caching strategies

**Cache-aside** (lazy loading): the application checks the cache, loads from the source on a miss, and populates. Most common, resilient to cache failure, but the first request per key is slow and it is easy to get inconsistent under concurrent writes. **Read-through**: the cache itself loads on miss, so the loading logic lives in one place. **Write-through**: write to cache and store synchronously - consistent, higher write latency. **Write-behind**: write to cache and flush asynchronously - fastest writes, risk of data loss and much harder recovery; I use it only for tolerable data such as counters.

Invalidation: prefer a short TTL plus explicit invalidation on write; version the cache key (include an entity version or a schema version in the key) so a deploy or a schema change does not serve stale shapes; and for multi-instance local caches, publish invalidation events rather than hoping TTLs align.

**Stampede** (many concurrent misses on the same hot key hitting the database at once) is the failure I actually plan for: use a per-key lock or single-flight so one loader populates while others wait, add jitter to TTLs so keys do not expire in lockstep, and consider probabilistic early refresh so a hot key is refreshed just before it expires. Caffeine's `AsyncLoadingCache` gives you single-flight for free locally; Redis needs an explicit lock.

### Q181. Graceful degradation `[A]`

The principle is that a partial outage should cause a partial loss of function, not a total one. So I classify every dependency as critical or non-critical up front - if the recommendations service is down, the product page must still render.

Mechanisms: a circuit breaker with an explicit fallback (cached value, default, empty section, or a queued write for a deferrable action); timeouts everywhere, always shorter than the caller's own deadline, with a deadline budget propagated through the call chain; bulkheads so a slow dependency cannot exhaust shared threads or connections; feature flags to disable an expensive or failing feature without a deploy; load shedding at the edge, dropping the lowest-priority traffic first; and serving stale-but-usable cached data with an explicit indication rather than an error.

Then I verify it: chaos experiments and failure injection in staging, plus a game day where we actually turn a dependency off and confirm the degraded behavior is what the product owner agreed to. Untested fallbacks are the ones that fail, usually because the fallback path itself calls the same dead dependency.

---

## 11. AWS and cloud architecture

### Q182. Compute decision framework

My sequence of questions: what is the traffic shape, what is the required startup latency, how long does a unit of work run, what does the team already operate well, and what is the cost at expected scale?

- **Lambda** for event-driven, spiky or low-volume workloads, and for glue. Under 15 minutes, stateless, tolerant of cold starts (or worth paying for provisioned or SnapStart). Cheapest at low and bursty volume, expensive at sustained high throughput.
- **ECS on Fargate** for standard long-running services. No cluster to manage, per-task isolation, straightforward IAM and networking. My default for a team that wants containers without Kubernetes.
- **EKS** when you need the Kubernetes ecosystem: complex multi-service topology, a service mesh, operators, portability across clouds, or an existing platform team. The cost is that you now run a platform.
- **EC2** for specialized needs: licensing, GPUs, very high sustained throughput where reserved instances win, or software that cannot be containerized.

I also state the reversibility: containerized services can move between Fargate and EKS with limited effort, while a deeply Lambda-native design is harder to unwind - so for an uncertain workload I bias toward containers.

### Q183. Lambda cold starts in Java `[T]`

Causes, in order of impact: JVM startup, classpath scanning and reflection in Spring or Jakarta EE frameworks, static initialization, and the JIT running interpreted until warm. A Spring Boot Lambda can take 5-10 seconds cold; the same logic in plain Java takes a few hundred milliseconds.

Four things that actually work:

1. **SnapStart** - Lambda snapshots the initialized JVM after `init` and restores from it, cutting cold starts by an order of magnitude. Requires care with anything captured in the snapshot: random seeds, cached credentials, open connections, and unique IDs - use the runtime hooks (`Resource::beforeCheckpoint` / `afterRestore`) to re-initialize them.
2. **Reduce the framework**. Use a plain handler, or Micronaut/Quarkus with build-time dependency injection, or Spring Cloud Function with AOT and a GraalVM native image. Removing reflection is where the win is.
3. **Do work in the init phase** - the 10-second init window is billed differently and is already outside the request path, so construct clients (`DynamoDbClient`, connection pools) as static fields and prime one call.
4. **Provisioned concurrency** for predictable latency-sensitive endpoints - it works, it costs money, and it means you are paying for idle, which is often the signal that this workload belonged on Fargate.

Also: trim the deployment package, use tiered compilation stop-at-level-1 (`-XX:TieredStopAtLevel=1 -XX:+TieredCompilation`) for short-lived invocations, and avoid VPC-attached Lambdas unless needed (Hyperplane ENIs removed most of that penalty, but the dependency remains).

### Q184. Messaging service selection

- **SQS** - point-to-point work queue, one consumer group, durable, with retries, visibility timeout and DLQ. Default for decoupling a producer from a worker.
- **SNS** - pub/sub fan-out to multiple subscribers, push-based, with message filtering by attribute. Typically SNS to several SQS queues, which gives fan-out plus per-consumer buffering and retry - the "fan-out pattern".
- **EventBridge** - an event bus with content-based routing rules, schema registry, SaaS and AWS-service sources, archive and replay, and scheduling. My choice for domain events across many services because the routing is declarative and consumers can be added without touching the producer. Higher latency and lower throughput ceiling than SNS.
- **Kinesis / MSK** - ordered, replayable streams with multiple independent consumers reading at their own position, and per-shard ordering. For analytics pipelines, change streams, and anything needing replay of a large window or strict ordering by key.

The distinguishing question I ask is: does the consumer need to *replay* history, and does order matter? Yes to either points at Kinesis or Kafka; otherwise SQS or EventBridge.

### Q185. SQS standard versus FIFO

**Standard**: nearly unlimited throughput, at-least-once delivery, best-effort ordering. **FIFO**: strict ordering within a message group ID, exactly-once *processing* via a 5-minute deduplication window, and throughput limited to 300 messages/second per group (3,000 with batching, and much higher with high-throughput mode enabled, which relaxes the deduplication scope).

Traps worth naming: the message group ID is the parallelism unit, so using a constant group ID serializes your entire queue; a single poisoned message blocks its whole group until it is moved to the DLQ; and **visibility timeout** must exceed your maximum processing time, or the message reappears and is processed twice while the first attempt is still running - the most common SQS bug there is. Extend it with a heartbeat (`ChangeMessageVisibility`) for long tasks, and always make the consumer idempotent even on FIFO, because "exactly once" only holds within the dedup window.

### Q186. Dead letter queues

A message lands in the DLQ after `maxReceiveCount` failed receives - which includes crashes and visibility-timeout expiries, not just explicit failures. That is the point: it stops a poison message from blocking the queue forever and from being retried infinitely at cost.

Operationally I treat a DLQ as an alertable condition, never a dumping ground: a CloudWatch alarm on `ApproximateNumberOfMessagesVisible > 0`, with the message retention set long enough (14 days) to investigate. Before replaying I want to know *why* it failed, because replaying a poison message just refills the DLQ.

Safe reprocessing: fix the cause first, then use the SQS DLQ redrive feature (or a controlled consumer) to move messages back at a throttled rate, ensure the handler is idempotent because some messages may have partially succeeded, and keep a record of what was redriven and when. For messages that can never succeed, archive them to S3 with the failure reason rather than deleting silently.

### Q187. RDS, Aurora, DynamoDB

**RDS**: managed conventional engines. Predictable, familiar, cheapest for modest workloads; failover to a standby takes 60-120 seconds; read scaling via read replicas with replication lag.

**Aurora**: a distributed storage layer under Postgres/MySQL compatibility - six copies across three AZs, faster failover (typically under 30 seconds), up to 15 low-lag read replicas, and storage that grows automatically. Aurora Serverless v2 scales capacity in fine-grained increments, which is genuinely useful for variable load. Costs more per hour, plus IO charges on the standard configuration.

**DynamoDB**: single-digit-millisecond key-value and document access at any scale, no capacity planning with on-demand mode, and no operational database to tune.

DynamoDB is the wrong choice when access patterns are unknown or will change, when you need ad-hoc queries, joins, aggregations or reporting, when items are large or transactions span many entities, or when the team lacks single-table-design experience - the schema is a function of your queries, so getting the queries wrong means a migration, not an index. I have seen more failures from choosing DynamoDB for a relational domain than from any other AWS decision.

### Q188. DynamoDB key design

The partition key determines physical distribution: its hash selects a partition, each of which sustains roughly 3,000 read and 1,000 write units per second. A **hot partition** comes from low-cardinality or skewed keys - a status field, a date, a single popular tenant. Fixes: choose a high-cardinality key, add a write-sharding suffix (`key#0..N`) and scatter-gather on read, or split the hot entity out. Adaptive capacity absorbs mild skew automatically but not a sustained hotspot.

The sort key enables range queries and the composite-key patterns behind single-table design, where several entity types share a table using generic `PK`/`SK` attributes and overloaded GSIs.

**GSI**: different partition and sort key, its own provisioned capacity, eventually consistent only, and unlimited size - throttling on a GSI throttles writes to the base table, which surprises people. **LSI**: same partition key with an alternate sort key, must be created with the table, supports strongly consistent reads, and constrains the item collection to 10 GB. I use GSIs almost exclusively, and project only the attributes needed to keep them small.

### Q189. IAM and workload credentials

**Users** hold long-lived credentials and should exist only for genuine break-glass or legacy cases - human access belongs in IAM Identity Center with federated, short-lived sessions. **Roles** are assumed and produce temporary credentials, which is what every workload should use. **Policies** are the permission documents attached to either.

How workloads get credentials: an **EC2 instance** uses the instance profile via IMDSv2. An **ECS task** uses a task role, retrieved from a link-local credential endpoint - distinct from the *execution* role, which only lets the agent pull images and write logs; conflating the two is a common misconfiguration. An **EKS pod** uses IRSA - the pod's service account is annotated with a role ARN, the projected service account token is exchanged with STS via OIDC federation, and the SDK picks it up through the web-identity provider chain. EKS Pod Identity is the newer, simpler alternative that avoids per-cluster OIDC trust configuration. A **Lambda** uses its execution role.

The point I make in interviews: no static access keys anywhere in the estate, permissions scoped per workload rather than per environment, and `aws:SourceArn`/`aws:PrincipalOrgID` conditions on trust policies to prevent the confused-deputy problem.

### Q190. Identity versus resource policies `[T]`

Both are evaluated. Within a single account, access is granted if **either** an identity policy or the resource policy allows it, and there is no explicit deny - they are additive. **Across accounts, both must allow**: the caller's identity policy in account A, and the bucket policy in account B. That asymmetry is the answer most candidates miss.

Full evaluation order: an explicit `Deny` anywhere wins; then organization SCPs must allow (they only restrict, never grant); then permission boundaries and session policies cap the maximum; then the union of identity and resource policies must contain an `Allow`.

Practical use: resource policies are how you grant cross-account access without the other account creating a role, how you enforce `aws:SecureTransport` and encryption conditions on a bucket regardless of who calls, and how you restrict a KMS key. Identity policies are how you manage per-workload least privilege at scale.

### Q191. VPC design

Standard shape: a VPC per environment, spread over at least three availability zones, with public subnets holding only load balancers and NAT gateways, private subnets for application compute, and isolated subnets with no outbound route for databases.

Cost note worth raising unprompted: NAT gateways are billed hourly *and* per gigabyte processed, and they are a frequent surprise line item. **VPC endpoints** remove that for AWS service traffic - gateway endpoints for S3 and DynamoDB are free and should always be present; interface endpoints (PrivateLink) for ECR, Secrets Manager, KMS, CloudWatch and so on cost per hour but usually less than the NAT data charges they replace, and they keep traffic off the public internet.

**Security groups** are stateful, instance-level, allow-only, and can reference other security groups - which is how I express "the app tier may reach the database tier" without hardcoding CIDRs. **NACLs** are stateless, subnet-level, ordered, and support explicit deny - I use them only for coarse subnet-level blocks, because stateless rules require matching ephemeral port ranges and are easy to get wrong.

### Q192. Secrets management

**Secrets Manager** for anything requiring rotation or cross-account sharing: native rotation with Lambda for RDS credentials, resource policies, and KMS encryption. Roughly $0.40 per secret per month plus API calls, which matters only if you have thousands.

**Parameter Store SecureString** for configuration and lower-sensitivity secrets: free at standard tier, integrates with the same SDK patterns, no built-in rotation.

**Environment variables** are acceptable only as the delivery mechanism when injected at runtime from one of the above (ECS `secrets` block, EKS External Secrets Operator) - never as the storage. They still leak into task definitions, `docker inspect`, crash dumps and logs, so for the highest-sensitivity values I fetch at runtime with caching instead.

Around all of it: least-privilege IAM per secret, CloudTrail auditing of `GetSecretValue`, automatic rotation with a tested rollback, secret scanning in CI and pre-commit, and IAM database authentication where available so there is no password to manage at all.

### Q193. S3 cost reduction

First, measure: S3 Storage Lens and an inventory report tell you what you actually have - I have never seen this analysis fail to find something surprising.

Levers, roughly in order of return: enable **Intelligent-Tiering** as the default for unpredictable access, which automates the standard-to-infrequent transitions for a small monitoring fee; add **lifecycle policies** to move known-cold data to Glacier Instant Retrieval, Flexible Retrieval or Deep Archive, and to expire genuinely temporary data; enable a rule to **abort incomplete multipart uploads** after 7 days, which is invisible storage almost everyone is paying for; expire **noncurrent versions** on versioned buckets, another common silent cost; compress and consolidate small objects, since per-request costs and minimum billable sizes dominate for tiny files; and check **cross-region replication and data transfer** charges, which are often larger than the storage line itself.

Then verify with Cost Explorer that the change landed, and put a budget alarm on the bucket's cost allocation tag so it does not drift back.

### Q194. Auto-scaling

**Target tracking** keeps a metric at a set point and manages the scaling policy for you - simple, and my default. **Step scaling** applies different adjustments per alarm threshold, useful when you need a large jump under severe load. **Scheduled scaling** for known patterns such as a business-hours workload or a batch window. **Predictive scaling** where the pattern is regular and warm-up time is long.

Scaling on CPU is often wrong because CPU is rarely the constraint for a Java service - the queue is. A service waiting on a database or an external API sits at 20 percent CPU while latency climbs, so CPU-based scaling never fires. Better signals: request concurrency or `ALBRequestCountPerTarget`, queue depth or age of the oldest message for workers (with target tracking on `ApproximateAgeOfOldestMessage`, which directly maps to the user-visible SLO), and p99 latency as a guard.

The other half is getting the dynamics right: scale out fast and in slowly, set the health-check grace period longer than JVM warm-up or you will kill instances mid-start, keep a floor of instances for AZ resilience, and confirm the downstream can absorb the scaled-out fleet - auto-scaling into a fixed-size connection pool just moves the failure.

### Q195. Multi-region active-active `[A]`

Shape: Route 53 latency or geolocation routing (with health checks and failover records) into regional stacks, each self-sufficient - ALB, compute, cache and data - with global data replication underneath and CloudFront in front for static and cacheable content.

The three hardest problems:

1. **Data consistency and write conflicts.** Two regions accepting writes for the same entity will conflict. Options: partition ownership so each entity has a home region and writes are routed there (my preference - it keeps reasoning simple); or accept a last-writer-wins / CRDT model with DynamoDB Global Tables and design the domain so conflicts are commutative; or keep a single write region with regional read replicas, which is really active-passive for writes and is what most "active-active" systems actually are. Be honest about which one you are proposing.
2. **Failover correctness.** Health checks must detect partial failure, not just a dead endpoint; DNS TTLs and client-side caching delay cut-over; and the surviving region must have capacity headroom for the full load, which means paying for roughly 2x capacity or accepting degraded service. Split-brain during a partition needs a defined resolution.
3. **Operational reality.** Deploying two regions with schema changes in flight, keeping configuration and secrets in sync, replicating identity and session state, regional service and feature parity, data residency and compliance constraints, and the cost of cross-region transfer. Plus testing: an untested failover is not a failover, so regular region-evacuation game days are non-negotiable.

I would also ask what the requirement actually is. If it is disaster recovery with a 15-minute RTO, warm standby is far cheaper and simpler than active-active; active-active earns its cost when you need low latency for globally distributed users or a genuinely zero-RTO regulatory commitment.

### Q196. A 40 percent bill increase `[A]`

1. **Scope it.** Cost Explorer grouped by service, then by usage type, comparing month over month and daily - a step change points at a deployment or a configuration change; a ramp points at growth or a leak. AWS Cost Anomaly Detection usually flags it first if configured.
2. **Localize it.** Group by linked account, then by tag (which requires the tagging discipline to already exist - if it does not, that is the first remediation). Correlate the start date against the deployment and infrastructure change log.
3. **Check the usual suspects.** Data transfer, especially cross-AZ and NAT gateway processing; a change from gateway to public routing; CloudWatch Logs ingestion after someone enabled debug logging; untagged or orphaned resources - unattached EBS volumes, old snapshots, idle load balancers, forgotten dev environments; a Savings Plan or Reserved Instance term expiring; an autoscaling floor raised; S3 versioning without lifecycle rules; a runaway Lambda retry loop or a recursive trigger.
4. **Fix and prevent.** Remediate the specific cause, then add guardrails: budgets with alerts per account and per team, anomaly detection, a tagging policy enforced by SCP or Config rule, cost visibility surfaced to the owning teams, and a right-sizing review cadence. Commit to Savings Plans only for the baseline you are confident in.

The framing I use with leadership is cost per unit of business value - cost per request or per tenant - because absolute spend rising alongside traffic is not a problem, and that distinction is what turns the conversation from panic into engineering.

### Q197. Well-Architected in practice

The six pillars are operational excellence, security, reliability, performance efficiency, cost optimization, and sustainability.

How I actually use it: not as a checklist recited to a customer, but as a structured review at design time and then annually, with the questions turned into concrete findings that get an owner, a severity and a date. The value is that it forces the conversations teams avoid - what is the RTO and RPO and have we tested them; who can access production data and how is it audited; what happens when this AZ fails; what does this cost per transaction and is that acceptable.

I run it as a workshop with the team rather than an audit done to them, prioritize the findings against risk rather than fixing everything, and track them in the normal backlog so they compete honestly with feature work. The output people remember is usually the reliability gap nobody had written down.

---

## 12. DevOps, CI/CD and observability

### Q198. Pipeline for a Java microservice

Stages, with the guiding principle that anything that can fail should fail as early and as cheaply as possible:

1. **Commit stage** (target: under 10 minutes) - compile, unit tests, static analysis (SpotBugs, Checkstyle/Spotless, SonarQube quality gate on new code), and a fast fail on formatting so review never discusses it.
2. **Security stage** - dependency vulnerability scan (OWASP Dependency-Check, Snyk or Trivy), secret scanning, SBOM generation, and container image scanning after build. Fail on new critical findings, warn on pre-existing, so the gate does not become noise everyone bypasses.
3. **Integration stage** - Testcontainers-backed tests against a real Postgres, Kafka and LocalStack; contract tests verifying both consumer and provider sides.
4. **Package** - a reproducible, multi-stage Docker build with layered JARs, signed (cosign) and pushed to ECR with an immutable tag derived from the commit SHA. Never `latest`.
5. **Deploy to staging** - via GitOps (Argo CD) or the pipeline, then smoke tests and a short performance check against a baseline so a regression is caught before production.
6. **Deploy to production** - progressive delivery: canary to a small traffic slice with automated analysis of error rate and latency, then a staged rollout, with automatic rollback on SLO violation.
7. **Post-deploy** - deployment markers on dashboards, automated verification, and a change record.

Cross-cutting: trunk-based development with short-lived branches, the same artifact promoted through every environment (build once), environment differences only in configuration, database migrations as a separate backward-compatible step, and everything in version control including the pipeline itself.

### Q199. Deployment strategies

**Rolling**: replace instances in batches. Cheap, no extra infrastructure, and the default in Kubernetes. Requires that two versions coexist safely - both in the API contract and in the database schema.

**Blue-green**: stand up a full parallel environment and switch traffic at the load balancer. Instant cut-over and instant rollback; costs double infrastructure during the window, and the switch is all-or-nothing, so a bad release hits 100 percent of users at once. Also needs a plan for in-flight sessions and for shared state such as the database, which is the part that makes blue-green much less clean in practice than in diagrams.

**Canary**: route a small percentage to the new version, watch metrics, and progress or roll back. The best risk/cost profile and my default for anything user-facing. Requires per-version metrics, a defined analysis window and automated promotion (Argo Rollouts, Flagger) - a manual canary that nobody watches is just a slow rolling deploy.

What each requires from the application, which is the real answer: backward and forward compatible APIs and events, backward compatible schema changes, statelessness or externalized session state, graceful shutdown honouring SIGTERM with connection draining, idempotent startup, and readiness probes that are honest about when the instance can serve.

### Q200. Rolling deployments and the schema `[T]`

Old and new code run against the **same database at the same time**, so the schema must be compatible with both versions simultaneously. That single fact generates all the rules:

- Only additive changes in a deploy: new columns must be nullable or have a default, because the old code's `INSERT` does not mention them.
- Never rename or drop a column in the same release that stops using it - old instances still reference it. Drop it one release later.
- No changes that alter the meaning of an existing column.
- New tables and columns first, code that uses them second.
- Migrations must be backward compatible with the previous version, because rollback must remain possible without a data restore - and rollback is the whole point of the strategy.
- Avoid long-lived locks; use `CREATE INDEX CONCURRENTLY` and `NOT VALID` constraints so the migration does not block traffic.

The same reasoning applies to message schemas - a consumer running old code must tolerate events produced by new code, which is why I require schema-registry compatibility checks in CI.

### Q201. Branching for a 30-engineer team

I recommend **trunk-based development**: short-lived branches merged to main within a day or two, everything behind feature flags, main always releasable, and continuous integration in the literal sense.

Why not GitFlow at that size: long-lived `develop` and `release` branches produce large, painful merges; the divergence between branches means integration problems are discovered late; and the release train adds latency without adding safety. GitFlow made sense for versioned, shipped software with multiple supported versions - which is a real case, and I would use it for a distributed library or an on-premises product.

What makes trunk-based work in practice, and what I would put in place first: a fast and trustworthy pipeline (if CI takes 40 minutes or is flaky, people batch changes and the model collapses), feature flags with a discipline for removing them, pull requests small enough to review in 20 minutes, branch protection with required checks, and pair or ensemble programming for the riskiest changes. The branching model is downstream of test quality, so I would fix the pipeline before arguing about branches.

### Q202. Docker image optimization for Java

- **Multi-stage build**: compile with the JDK, run on a JRE or a `jlink`-trimmed runtime, so build tooling and source never ship.
- **Layered JARs**: Spring Boot's layered mode splits dependencies, spring-boot-loader, snapshot dependencies and application classes into separate layers, so a code change re-pushes a few hundred kilobytes instead of the whole fat JAR. Use `bootBuildImage`/buildpacks or an explicit `layertools extract`.
- **Small base image**: `eclipse-temurin:21-jre-alpine` or, better, a **distroless** base - no shell, no package manager, minimal CVE surface. Debugging becomes harder, which is the trade-off; an ephemeral debug container solves it on Kubernetes.
- **`jlink`** a custom runtime containing only the modules you use, typically halving the JRE size.
- Order Dockerfile instructions from least to most frequently changing so the layer cache is effective, and use a `.dockerignore`.
- Run as a **non-root user**, set a read-only root filesystem, and pin base images by digest.
- Consider **CDS/AppCDS** (or a GraalVM native image where startup dominates) to cut startup time, which matters more than image size for scaling responsiveness.

Worth saying explicitly: image size mostly affects pull time on a cold node, so I optimize layer *churn* first and absolute size second.

### Q203. Container memory exceeding `-Xmx` `[T]`

Because `-Xmx` bounds only the Java heap, and the process needs much more: metaspace, the JIT code cache and compiler arenas, per-thread stacks at ~1 MB each, direct byte buffers (Netty, NIO), GC internal structures, and native allocations from libraries. Total RSS can easily be heap plus 400 MB to 1 GB.

A second cause on older JVMs: the container was not detected, so the JVM sized the heap and GC threads from the *host's* memory and CPU count. Java 10+ is container-aware by default (`UseContainerSupport`), but ancient base images still get this wrong.

Fixes: size the heap as a percentage of the limit (`-XX:MaxRAMPercentage=70`) rather than a fixed value; cap the other regions explicitly (`-XX:MaxMetaspaceSize`, `-XX:MaxDirectMemorySize`, `-XX:ReservedCodeCacheSize`); bound thread counts, since a thread leak shows up as native memory, not heap; measure real usage with Native Memory Tracking rather than guessing; and set `-XX:+ExitOnOutOfMemoryError` so a poisoned process is restarted rather than limping.

Then set the Kubernetes memory *request equal to the limit* for a Guaranteed QoS class, so the pod is not evicted under node pressure, and alert on RSS approaching the limit rather than waiting for the OOM kill.

### Q204. Probes

**Liveness**: is the process irrecoverably broken? Failure restarts the container. Keep it dumb and dependency-free - a check that the process responds. **Readiness**: can this instance serve traffic right now? Failure removes it from the Service endpoints without restarting it, so it is the right place for "dependencies are warming up" or "I am shedding load". **Startup**: gates the other two during a slow boot, which is exactly the Java case - a JVM taking 60 seconds to start would otherwise be killed by liveness before it ever became ready.

What breaks when you conflate them: putting a database check in *liveness* means a database blip restarts every pod in the fleet simultaneously, turning a recoverable dependency outage into a full outage with a thundering-herd reconnect. Using liveness without a startup probe means slow-starting JVMs restart forever in a crash loop. Making readiness depend on a non-critical downstream removes all instances from service when that downstream degrades, when the correct behavior was to degrade gracefully.

Spring Boot maps this well: `/actuator/health/liveness` and `/actuator/health/readiness` with `management.endpoint.health.probes.enabled=true`, and readiness automatically flips to `OUT_OF_SERVICE` during graceful shutdown so in-flight requests drain.

### Q205. Requests, limits and the JVM

**Requests** drive scheduling and guarantee a share; **limits** cap usage. For memory the limit is a hard kill - exceed it and the kernel OOM-kills the container, with no grace. For CPU the limit is enforced by CFS quota: the process is *throttled*, not killed, meaning it is descheduled until the next 100 ms period.

That throttling is what hurts a JVM. GC threads, JIT compiler threads and application threads all compete inside the quota, so a limit of 1 CPU on a JVM that sized its GC parallelism from the node's 64 cores produces severe throttling and latency spikes with the CPU graph sitting well below the limit - which is why `container_cpu_cfs_throttled_seconds` is the metric I check before `container_cpu_usage`. Startup suffers most, because JIT compilation is CPU-hungry precisely when the quota is tightest.

My defaults: set memory request equal to limit (Guaranteed QoS, no eviction surprise); set a CPU request that reflects steady-state need and consider omitting the CPU limit for latency-sensitive services (a widely used practice, since requests already provide fair sharing), or set it generously if policy requires one; and pin `-XX:ActiveProcessorCount` when the JVM's detection does not match the quota.

### Q206. Terraform, CloudFormation, CDK

**Terraform**: multi-cloud, mature module ecosystem, HCL is declarative and readable, and the plan output is the best change-preview of the three. State is the operational burden - remote backend with locking (S3 plus DynamoDB), and state is sensitive because it contains secrets in plaintext.

**CloudFormation**: AWS-native, no state file to manage (AWS tracks it), automatic rollback on failure, and StackSets for multi-account. Slower to support new services than it once was, and YAML at scale becomes unwieldy.

**CDK**: real programming languages compiling to CloudFormation, so you get loops, types, abstraction and unit tests, plus high-level constructs that encode good defaults. The risk is that the generated resources are hidden behind constructs, and an upgrade can produce a surprising diff - `cdk diff` discipline is essential.

My choice depends on context: AWS-only with a strong developer culture, CDK; multi-cloud or a platform team standardizing across providers, Terraform. Either way the practices matter more than the tool - modules with versioned releases, no manual console changes, drift detection running on a schedule (`terraform plan` in CI, or CloudFormation drift detection), policy as code (OPA/Sentinel, cfn-guard) in the pipeline, and separate state per environment. **Drift** is the failure I plan for explicitly: someone will click in the console during an incident, so detection plus a documented reconciliation path is part of the design, not an afterthought.

### Q207. Default instrumentation

Every service gets, without anyone asking:

- **Metrics** via Micrometer to Prometheus: the RED signals per endpoint (rate, errors, duration as a histogram so quantiles are computable, never a pre-aggregated average), plus JVM metrics (heap, GC pause and frequency, thread counts, class loading), connection pool metrics (Hikari active/idle/pending), HTTP client metrics per downstream, cache hit ratio, and queue depth and consumer lag for anything asynchronous. Business metrics too - orders placed, payments failed - because those detect problems the technical metrics miss.
- **Logs**: structured JSON, one event per line, with the trace ID, span ID, tenant and user ID in the MDC, at a sane level (INFO for business events, DEBUG off in production), and never containing secrets, tokens or PII. Sampled or rate-limited for high-volume paths, because log ingestion is often the largest observability cost line.
- **Traces**: OpenTelemetry auto-instrumentation with a Java agent, with manual spans around meaningful business operations and significant attributes (tenant, entity ID, result). Tail-based sampling so all errors and slow requests are kept while routine traffic is sampled down.
- **Correlation**: the same trace ID flows through logs, traces and error reports, and is returned to the client in a response header so a support ticket leads straight to the evidence.

Then the outputs: a standard dashboard template per service (RED plus saturation), alerts derived from SLOs rather than from thresholds someone guessed, and a runbook link on every alert.

### Q208. SLI, SLO and error budgets

An **SLI** is a measured ratio of good events to valid events - request success rate, or the fraction of requests served under 300 ms. An **SLO** is the target for that SLI over a window, for example 99.9 percent over 28 rolling days. The **error budget** is the remaining allowance: 99.9 percent over 28 days permits about 40 minutes of failure.

How I actually use the budget, which is the part interviewers are testing: it converts reliability from an argument into a number both engineering and product accept in advance. Budget healthy means we can ship faster, take more deployment risk, and run chaos experiments. Budget more than half consumed means we tighten canary criteria and prioritize reliability work. Budget exhausted means a feature freeze on that service until it is back within target, and the remediation work goes to the top of the backlog - agreed with the product owner *before* the incident, not negotiated during it.

Practical requirements: alert on **burn rate**, not on individual failures - a fast burn (2 percent of budget in an hour) pages, a slow burn opens a ticket - which is what eliminates most alert noise. Choose SLIs from the user's perspective, measured at the edge where the user experiences them. Keep the number of SLOs small; three meaningful ones beat twenty nobody trusts. And set the target from what the business actually needs, because every additional nine multiplies cost - most internal services do not need four.

### Q209. Good alerts

A good alert is **symptom-based, actionable, urgent and attributable**: it fires on something a user is experiencing, a human must do something about it now, and there is a documented action. If the answer to "what do I do when this fires?" is "look at it and probably nothing", it should not page.

Concretely, every alert I approve has: a clear title naming the affected service and user impact, a link to a runbook with diagnosis steps, a dashboard link, the right severity (page versus ticket versus dashboard-only), and an owner.

How I eliminate fatigue: alert on SLO burn rate rather than on causes, so one alert covers many failure modes instead of ten cause-based alerts firing together; delete alerts that have never led to action, which is usually a large fraction; group and deduplicate related alerts into a single incident; use `for` durations so transient blips self-resolve; suppress downstream alerts when an upstream dependency is already alerting; and review every page in the weekly operational review, asking whether it was actionable - anything that was not gets fixed or removed that week.

The cultural point I make: alert fatigue is not an inconvenience, it is a reliability risk, because the page that matters gets ignored alongside the ones that do not. Tracking pages per on-call shift as a metric, with a target, is what actually drives it down.

### Q210. Blameless postmortems `[A]`

The premise is that people act rationally given the information and incentives available to them at the time, so "human error" is the *start* of the investigation, not its conclusion. If an engineer could take down production with one command, the system permitted it - that is the finding.

How I run one: within a few days while memory is fresh; a facilitator who was not the responder; a timeline built from evidence (logs, traces, chat, deploy records) rather than recollection; and a structure covering impact in user terms, detection (how long, and did monitoring or a customer find it), response, resolution, and contributing factors - plural, because single root causes are usually a simplification. I explicitly include what went *well*, and I ask counterfactual-free questions ("what information did you have?") rather than "why didn't you...".

What makes it still useful in six months: quantified impact, so the cost is comparable across incidents; a clear narrative someone outside the team can follow; and a small number of specific, owned, dated action items entered in the normal backlog - two real fixes that ship beat fifteen that do not. I also track the aggregate: recurring themes across postmortems are what justify platform investment, and a postmortem action-item completion rate is a metric I report to leadership.

The failure mode to name: a postmortem process that produces documents nobody reads and actions nobody completes is theatre, and it burns the team's willingness to be honest the next time.

---

## 13. AI engineering with Java

### Q211. LLM integration architecture

I treat the model as an unreliable, expensive, non-deterministic external dependency, and the architecture follows from that.

Shape: a dedicated module behind a domain interface (`AnswerGenerator`, not `OpenAiClient`) so the provider is swappable and testable; a gateway layer handling authentication, retries with backoff, timeouts, circuit breaking and provider fallback; prompt templates versioned in source control and rendered server-side, never assembled from raw user input; structured output enforced via JSON schema / tool-calling and validated against a DTO before anything downstream sees it; streaming to the client over SSE for perceived latency; a semantic or exact-match cache for repeated queries; and full observability - token counts, cost, latency, model version and prompt version on every call, with the prompt and response sampled for evaluation.

Around it: rate limits per tenant, a budget cap that degrades rather than fails, and a kill switch feature flag. Spring AI or LangChain4j gives the client abstraction, chat memory and tool calling so I do not write that plumbing myself.

The point I would make: the model call is 10 percent of the work; the other 90 percent is the retrieval, validation, cost control and evaluation around it.

### Q212. RAG and its failure modes

RAG retrieves relevant documents from a knowledge base and puts them in the prompt as grounding, so the model answers from your data rather than from its parameters - which fixes staleness, enables citations, and avoids fine-tuning for factual updates.

The failure modes of a naive implementation, which is what the question is really asking:

- **Retrieval misses.** Pure vector similarity fails on exact terms, product codes, acronyms and negation. Fix with hybrid search (BM25 plus vectors, fused with reciprocal rank fusion) and a reranker.
- **Bad chunking.** Fixed-size splits cut tables and sentences in half and strip context. Fix with structure-aware chunking, overlap, and attaching document and section metadata to each chunk - or contextual retrieval, where each chunk is prefixed with a short summary of its place in the document.
- **Retrieved-but-not-used, or worse, wrong-and-used.** Relevant context ranked low is ignored, and irrelevant context actively misleads. Fix by reranking, limiting to the top few chunks, and prompting the model to say it does not know.
- **No grounding enforcement.** The model blends retrieved facts with its own priors. Require citations to chunk IDs and verify them programmatically; reject answers whose claims are not supported.
- **Stale or unpermissioned index.** Documents change and access control does not carry into the vector store - a genuine data-leak risk in a multi-tenant system. Filter by tenant and ACL *at query time*, not after retrieval.
- **No evaluation.** Without a measured retrieval hit rate and answer-faithfulness score, every prompt change is a guess.

### Q213. Embeddings and vector search

An embedding maps text to a dense vector where semantic similarity is geometric proximity. Similarity is almost always **cosine** (magnitude-invariant, and equivalent to dot product on normalized vectors); Euclidean is used occasionally, and the choice must match how the model was trained.

**Chunking** is the decision that most affects quality: 200-500 tokens with 10-20 percent overlap as a starting point, split on semantic boundaries (headings, paragraphs) rather than character counts, keeping tables and code blocks intact, and storing rich metadata (source, section, date, tenant, ACL) for filtering. Small chunks retrieve precisely but lack context - the small-to-big pattern retrieves small chunks and passes their larger parent to the model.

**Hybrid search** matters because dense vectors alone lose exact-match capability: run BM25 and vector search in parallel and fuse the rankings (RRF), then rerank the top 50 down to the top 5 with a cross-encoder. That combination consistently outperforms either alone.

**Store choice**: pgvector when Postgres is already there and the corpus is moderate - one system to operate, and metadata filtering with real SQL, which is a bigger advantage than people expect; OpenSearch when you also need lexical search and already run it; a dedicated store (Pinecone, Qdrant, Weaviate) at large scale or when you need advanced filtering and sharding. Index type is an ANN accuracy/latency trade-off: HNSW for low latency at higher memory, IVFFlat for lower memory at some recall cost.

Operational details worth naming: embeddings must be regenerated when you change the model, so plan for a re-index; normalize vectors once at write time; and store the embedding model version alongside the vector so a mixed index is detectable.

### Q214. Controlling LLM cost and latency

Cost first, because it is the one that surprises finance:

- **Right-size the model per task.** Routing simple classification and extraction to a small model and reserving the frontier model for genuinely hard generation typically cuts spend by most of the bill.
- **Cache aggressively.** Exact-match caching for repeated queries, semantic caching for near-duplicates, and provider-side prompt caching for long stable system prompts and retrieved context.
- **Control tokens.** Trim retrieved context to what is needed, cap conversation history with summarization rather than unbounded accumulation, and constrain `max_tokens`.
- **Batch** offline work through batch APIs at a large discount.
- **Budget guardrails.** Per-tenant and per-feature quotas, a hard monthly cap, and a documented degradation path when it is hit.

Latency:

- **Stream** the response so time-to-first-token is what the user perceives.
- **Parallelize** retrieval and any independent calls; overlap embedding with other work.
- **Shorten the critical path** - fewer chained model calls; an agent that makes six sequential calls is six times the latency and the failure surface.
- **Set aggressive timeouts** with a fallback to a smaller model or a cached answer, rather than letting the user wait 30 seconds.

Measurement underpins all of it: tokens in, tokens out, cost and latency tagged by feature, tenant, model and prompt version, on a dashboard the team sees weekly. You cannot control what you have not attributed.

### Q215. Prompt injection

Instructions and data share one channel, so any text the model reads can attempt to redirect it - and unlike SQL injection there is no parameterization that reliably separates them. **Direct** injection is a user typing "ignore your instructions"; **indirect** is the dangerous one, where the payload is planted in a document, web page, email or code comment that your retrieval or browsing tool later ingests.

Against a tool-using agent the impact is not a rude reply, it is action: exfiltrating data through a tool call, sending an email, modifying a record, or chaining to another system with the agent's credentials.

Defense is layered, because no single control holds:

- **Treat all model output as untrusted input.** Never pass it to `eval`, a shell, or an unparameterized query.
- **Constrain the tools, not the prompt.** Least privilege per tool, allowlisted operations, parameter validation and schema enforcement, and no tool that can do irreversible or high-value damage without a human approval step.
- **Isolate untrusted content** in a clearly delimited section with instructions that content there is data, never instructions - helpful, not sufficient.
- **Separate privilege levels**: a planner model that sees only trusted input decides actions, while a second model handles untrusted content and cannot invoke tools (the dual-LLM pattern).
- **Egress control**: block the agent from making arbitrary outbound requests, since rendering an image URL is a classic exfiltration channel.
- **Detection and limits**: input/output filtering, anomaly detection on tool usage, rate limits, and full audit logging of every tool invocation.

The honest framing for an interview: prompt injection is not solved, so I design assuming it will succeed occasionally and limit the blast radius accordingly.

### Q216. Evaluating an AI feature

Non-determinism means the usual assert-equals test does not apply, so I build a layered evaluation instead of pretending the problem away.

- **A golden dataset** of a few hundred realistic cases with expected outcomes, drawn from real usage and from known failure cases, version-controlled and grown every time production surfaces a new failure.
- **Deterministic assertions wherever possible**: schema validity, required fields present, citations resolving to real chunks, no PII in output, latency and cost within bounds, refusal on out-of-scope input. A surprising share of real regressions are caught here.
- **Component metrics** rather than only end-to-end: for RAG, retrieval recall@k and precision, then answer faithfulness (is every claim supported by the retrieved context) and answer relevance. Isolating retrieval from generation is what makes failures diagnosable.
- **LLM-as-judge** for subjective quality, with a rubric, a stronger model than the one under test, pairwise comparison rather than absolute scoring, and periodic calibration against human labels so I know the judge's agreement rate. I treat it as a noisy signal, not truth.
- **Human review** on a sampled slice, especially for anything customer-facing or regulated.
- **In production**: online metrics - thumbs up/down, task completion, escalation to a human, edit distance on accepted suggestions - plus A/B tests for meaningful changes, and shadow evaluation of a candidate model against live traffic.

Then the discipline: run the suite in CI on every prompt, model or retrieval change (prompts are code and belong in version control), pin model versions and treat a provider's model update as a change requiring re-evaluation, and define release criteria as thresholds rather than vibes. Report a distribution and a confidence interval, not a single score.

### Q217. Streaming responses

**SSE** is the right default for LLM output: one-directional server-to-client, plain HTTP so it traverses proxies and load balancers, automatic browser reconnection with `Last-Event-ID`, and trivial in Spring (`SseEmitter` in MVC, or `Flux<ServerSentEvent>` in WebFlux). **WebSocket** only when you genuinely need bidirectional low-latency messaging - interrupting generation mid-stream, collaborative sessions, voice. **WebFlux** is an implementation choice underneath either, valuable because a long-held stream ties up a thread in MVC - though with virtual threads that objection largely disappears, so I would not adopt WebFlux for this reason alone in 2026.

The operational concerns are where experience shows:

- **Timeouts and buffering** in every intermediary - ALB idle timeout, Nginx `proxy_buffering off` and `X-Accel-Buffering: no`, CloudFront - or the client sees nothing until the response completes, which is the single most common streaming bug.
- **Connection budget**: each stream holds a connection for its lifetime, so capacity planning is by concurrent streams, not requests per second.
- **Cancellation**: detect client disconnect and abort the upstream model call, or you keep paying for tokens nobody will read.
- **Errors mid-stream**: the HTTP status was already sent as 200, so failures must be delivered as an error event the client understands, and partial output must be handled.
- **Heartbeats** to keep idle connections alive, graceful shutdown that drains streams, and sticky-free design so any instance can serve.
- Content moderation and validation become harder because you are emitting before you have the whole answer - buffer a window, or accept the risk and be able to retract.

### Q218. Spring AI versus LangChain4j versus building it

Both give the same core value: a provider-agnostic chat and embedding client, structured output binding to Java types, tool/function calling, chat memory, document loaders and splitters, vector store abstractions over pgvector/OpenSearch/Qdrant, and RAG plumbing. Spring AI fits naturally into Boot's auto-configuration, observability and testing story, which is decisive when the rest of the stack is Spring; LangChain4j is framework-agnostic and has moved faster on some agent features.

What I would take from them: the client abstraction, retry and observability wiring, structured output, and the document/embedding pipeline - reimplementing those is undifferentiated work.

What I would build myself regardless: prompt management and versioning (they are business logic and deserve first-class treatment, review and evaluation), the evaluation harness, cost attribution and budget enforcement, the retrieval strategy including hybrid search and reranking tuned to my corpus, guardrails and tenant isolation, and caching policy. Those are where the quality of the product actually lives.

The caveat I would state: these libraries move quickly and their abstractions are still settling, so I keep them behind my own domain interface rather than letting their types spread through the codebase - the same discipline I would apply to any fast-moving dependency.

### Q219. PII and compliance with third-party models `[A]`

I start from the data, not the model: classify what is being sent, and establish the legal basis and residency requirements before choosing a provider.

Controls I would put in place:

- **Minimize.** Send only the fields the task requires; strip identifiers that add nothing. Most prompts contain far more context than the task needs.
- **Redact or tokenize** PII before it leaves the boundary, substituting stable placeholders and re-hydrating the response on the way back, so the provider never sees the real values. Automated detection (Comprehend PII, Presidio) plus deterministic rules, with the residual-risk caveat that detection is imperfect.
- **Contract and configuration**: a DPA with the provider, zero-retention / no-training-on-our-data settings enabled and verified, an enterprise tier where that is contractual rather than a checkbox, and regional endpoints or a self-hosted/Bedrock deployment inside our own account when residency demands it.
- **Keep regulated data in-boundary.** For health, payment or similarly regulated data, a model running in our VPC (Bedrock with a VPC endpoint, or a self-hosted open-weight model) is often the only defensible answer, and the quality gap in 2026 is small enough that this is a real option rather than a concession.
- **Audit and governance**: log what categories of data were sent, by whom, for what purpose; retention and deletion policies covering prompts and outputs (which are themselves personal data if they contain PII); DPIA where required; and consent or notice to users that AI processing occurs.
- **Guard the output too**: PII can leak *out* of a model, and a response echoing another tenant's retrieved content is a breach - so tenant-scoped retrieval and output scanning both matter.

The framing I would give leadership: this is a data-governance decision with a technical implementation, so legal, security and engineering agree the boundary once, and I encode it as a policy the platform enforces rather than a rule each team remembers.

### Q220. Pushing back on a poor-fit AI feature `[A]`

I do not open with "no". I try to understand the outcome they actually want, because the request is usually a proposed *solution* to a real problem, and the problem is often legitimate even when the solution is not.

Then I make the trade-off visible rather than argue from authority: what accuracy is achievable and what happens on the failure cases; what the cost per interaction is at expected volume; the latency the user will experience; the compliance and data exposure implications; and what the maintenance burden looks like when the model provider deprecates a version. Alongside that I propose an alternative that reaches the same outcome - frequently a deterministic rule, a search improvement, or a much smaller model scoped to a narrower task.

If it is still contested, I propose a **time-boxed spike with agreed success criteria** on real data. That converts an opinion contest into evidence, and it is honest: I have been wrong about what models can do, and a two-week evaluation costs far less than a year of maintaining something that does not work. I also insist on defining the failure mode up front - what the user sees when the model is wrong - because a feature that cannot degrade acceptably should not ship regardless of its average quality.

And if the decision goes against me after that, I commit to it and instrument it heavily so we find out quickly. Disagreeing and committing, with measurement attached, is more useful than being right in a retrospective.

---

## 14. System design

The system design questions in [questions.md](questions.md) (Q221-Q230) are worked as full scenarios in [scenario-questions.md](scenario-questions.md), with clarifying questions, capacity estimates, component choices and failure analysis for each.

Universal structure to apply to any of them:

1. **Requirements** - functional, then non-functional (scale, latency, availability, consistency, durability, retention, compliance). Ask before designing; the interviewer is deliberately vague.
2. **Capacity estimates** - QPS at peak, read/write ratio, storage growth per year, bandwidth. Round aggressively and state your assumptions out loud.
3. **API design** - the two or three endpoints that matter, with their contracts.
4. **Data model** - entities, access patterns, then the store choice justified by those patterns.
5. **High-level architecture** - draw it, keep it to 6-8 boxes, then walk one write path and one read path end to end.
6. **Deep dive** - go deep where the interviewer steers, or pick the genuinely hard part yourself.
7. **Scale and bottlenecks** - what breaks first at 10x, and the specific mitigation.
8. **Failure modes** - what happens when each component dies; where the data is at risk.
9. **Operations** - metrics, alerts, deployment, cost.
10. **Trade-offs** - state what you consciously chose not to do, and under what condition you would change it.

At principal level, steps 7 through 10 are what distinguish the answer. Most candidates draw the boxes; few explain what happens when a box fails, what it costs, and how they would know it was broken.
