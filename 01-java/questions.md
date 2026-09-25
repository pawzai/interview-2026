# Java Interview Questions

Questions are numbered continuously (`Q1`, `Q2`, ...) so that [answers.md](answers.md) can reference them directly.

Difficulty legend:

- `[C]` Core - you must answer this instantly and correctly.
- `[D]` Deep - expected of a senior engineer, requires mechanism-level detail.
- `[T]` Tricky - designed to catch you out; the obvious answer is usually wrong.
- `[A]` Architect - no single right answer, judged on trade-off reasoning.

Answered in detail in [answers.md](answers.md): every `[T]` question plus the marked core set. Attempt them yourself first.

---

## 1. Java language fundamentals

1. `[C]` Explain the contract between `equals()` and `hashCode()`. What breaks if you violate it?
2. `[T]` A mutable object is used as a `HashMap` key and then mutated. What happens on lookup, and why is the entry still counted in `size()`?
3. `[C]` `==` versus `equals()` for wrapper types. Why does `Integer a = 127, b = 127; a == b` return `true` but the same code with `128` returns `false`?
4. `[T]` What does `System.out.println(0.1 + 0.2 == 0.3)` print, and how do you compare doubles safely?
5. `[C]` Difference between `String`, `StringBuilder` and `StringBuffer`. When does the compiler already optimize concatenation for you?
6. `[T]` Explain string interning. Why is `new String("a") == "a"` false but `new String("a").intern() == "a"` true?
7. `[C]` What makes a class immutable? List all the requirements, including the one most people forget.
8. `[T]` A `final` field holding a `List` - is the object immutable? How do you actually make it safe?
9. `[C]` Pass by value or pass by reference in Java? Justify with an example that surprises people.
10. `[D]` Explain the `static` initialization order: static fields, static blocks, instance fields, instance blocks, constructors, and where inheritance fits.
11. `[T]` What is printed if a subclass constructor calls an overridable method that uses a subclass field? Why?
12. `[C]` Difference between abstract classes and interfaces after Java 8 default methods. When do you still need an abstract class?
13. `[T]` A class implements two interfaces with the same `default` method signature. What happens, and how do you resolve it?
14. `[D]` Explain method overloading resolution: widening versus boxing versus varargs. Which wins?
15. `[T]` What happens when you overload a method with `Object` and `String` parameters and call it with `null`?
16. `[C]` Checked versus unchecked exceptions. What is your team-level policy and why?
17. `[T]` What is returned when a `finally` block contains a `return` statement and the `try` block also returns?
18. `[T]` Can a `finally` block prevent an exception from propagating? Show how, and why it is dangerous.
19. `[D]` Explain `try-with-resources`, suppressed exceptions, and the order of resource closing.
20. `[C]` What is the difference between `throw` and `throws`, and between `Error`, `Exception` and `RuntimeException`?
21. `[D]` Explain generics type erasure. What information survives to runtime, and what does not?
22. `[T]` Why can you not create `new T[10]` in a generic class, and what is the standard workaround?
23. `[D]` Explain PECS. When do you use `? extends T` versus `? super T`?
24. `[T]` `List<String>` cannot be assigned to `List<Object>`, but `String[]` can be assigned to `Object[]`. Explain both, and what runtime exception array covariance causes.
25. `[C]` What are records, and what do they give you for free? What are their limits?
26. `[D]` Sealed classes and interfaces - what problem do they solve, and how do they interact with pattern matching?
27. `[D]` Explain `var`. Where is it useful and where does it hurt readability?
28. `[T]` What does `Optional.of(null)` do? When should `Optional` never be used?
29. `[D]` Explain the difference between shallow copy, deep copy, and why `Cloneable` is considered a broken design.
30. `[D]` What is the purpose of `finalize()`, why is it deprecated, and what replaced it?

---

## 2. Collections and data structures

31. `[C]` Internal working of `HashMap`: buckets, hashing, collision handling, resize threshold.
32. `[D]` When and why does `HashMap` treeify a bucket, and what requirement does treeification place on the key?
33. `[T]` What happens if you use `HashMap` concurrently from multiple threads? What was the classic infinite-loop bug and is it still present?
34. `[D]` `ConcurrentHashMap` internals: how does it achieve concurrency without a global lock, and how does `size()` behave?
35. `[C]` `ArrayList` versus `LinkedList` - and why is `LinkedList` almost always the wrong choice in practice?
36. `[D]` Explain fail-fast versus fail-safe iterators and `ConcurrentModificationException`.
37. `[T]` You remove an element from a list inside an enhanced for loop and no exception is thrown. Explain when that is possible.
38. `[C]` `HashSet` versus `TreeSet` versus `LinkedHashSet` - complexity and ordering guarantees.
39. `[D]` `Comparable` versus `Comparator`. What is the contract, and what breaks if the comparison is inconsistent with equals?
40. `[T]` A `Comparator` returns `a.value - b.value` for ints. What is the bug?
41. `[D]` How do you choose between `ConcurrentHashMap`, `Collections.synchronizedMap` and `Hashtable`?
42. `[D]` Explain `BlockingQueue` implementations and where each fits in a producer-consumer design.
43. `[D]` `CopyOnWriteArrayList` - how it works and the exact workload where it wins.
44. `[C]` What is the time complexity of `contains()` on `ArrayList`, `HashSet` and `TreeSet`?
45. `[T]` Why does `Arrays.asList()` throw `UnsupportedOperationException` on `add()` but allow `set()`?
46. `[T]` `List.of(...)` versus `Arrays.asList(...)` versus `new ArrayList<>()` - three different null and mutability behaviors. Name them.

---

## 3. Streams, lambdas and functional Java

47. `[C]` Intermediate versus terminal operations. Why is a stream without a terminal operation a no-op?
48. `[D]` Explain lazy evaluation and short-circuiting in streams with an example.
49. `[T]` What happens if you reuse a stream after a terminal operation?
50. `[D]` `map` versus `flatMap`. Give a real use case for `flatMap` beyond flattening lists.
51. `[T]` `Collectors.toMap` with duplicate keys - what happens, and how do you fix it?
52. `[D]` When do parallel streams actually help, and what are the three conditions that must hold?
53. `[T]` Why is using a parallel stream inside a servlet request handler often a bad idea? Which pool does it use?
54. `[D]` Explain `reduce` versus `collect`. Why is `collect` preferred for mutable accumulation?
55. `[T]` What is wrong with using a stateful lambda in `map()` on a parallel stream?
56. `[D]` `Collectors.groupingBy` with a downstream collector - write one for counting and one for averaging.
57. `[C]` What is a functional interface? Name the core ones in `java.util.function`.
58. `[D]` Method references: four kinds. Give an example of each.
59. `[T]` Effectively final - why must lambdas capture effectively final variables, and what is the underlying reason?
60. `[D]` How do you handle checked exceptions inside lambdas cleanly?

---

## 4. Concurrency and multithreading

61. `[C]` Thread lifecycle states in Java. What is the difference between `WAITING` and `TIMED_WAITING`?
62. `[D]` Explain the Java Memory Model: happens-before, visibility, reordering.
63. `[C]` `volatile` - what it guarantees and what it does not.
64. `[T]` Is `volatile int count; count++` thread-safe? Explain precisely why not.
65. `[D]` `synchronized` versus `ReentrantLock`. What does `ReentrantLock` give you that `synchronized` cannot?
66. `[D]` Explain `ReadWriteLock` and `StampedLock`, and when optimistic reads pay off.
67. `[C]` `wait()`, `notify()`, `notifyAll()` - why must they be called inside a synchronized block?
68. `[T]` Why must `wait()` always be called in a loop rather than an `if`?
69. `[D]` Explain the executor framework: core pool size, max pool size, queue, rejection policy, and how they interact.
70. `[T]` You configure a `ThreadPoolExecutor` with core 10, max 100 and an unbounded `LinkedBlockingQueue`. Why will the pool never grow beyond 10?
71. `[D]` How do you size a thread pool for CPU-bound versus IO-bound work?
72. `[D]` `CompletableFuture`: composition, exception handling, and which executor the callbacks run on.
73. `[T]` Difference between `thenApply` and `thenApplyAsync`, and why it matters for thread starvation.
74. `[D]` Explain deadlock, livelock, starvation. How do you detect deadlock in production?
75. `[D]` `CountDownLatch` versus `CyclicBarrier` versus `Semaphore` versus `Phaser`.
76. `[D]` What are atomic classes and how does CAS work? What is the ABA problem?
77. `[T]` Why does `LongAdder` outperform `AtomicLong` under high contention?
78. `[D]` `ThreadLocal` - use cases, and the memory leak risk in application servers and thread pools.
79. `[A]` Virtual threads (Project Loom): what changes, what does not, and which of your existing patterns become anti-patterns?
80. `[T]` Why does `synchronized` pin a virtual thread, and what should you use instead?
81. `[D]` Explain the double-checked locking idiom and why it requires `volatile`.
82. `[D]` How do you implement a thread-safe singleton? Compare four approaches.
83. `[A]` How do you make a legacy non-thread-safe class safe without rewriting it?
84. `[A]` Structured concurrency with `StructuredTaskScope` - what does it fix that `CompletableFuture` fan-out does not?
85. `[A]` You switch a Spring Boot service to virtual threads. Where does the bottleneck move, and what do you have to bound?
86. `[D]` How do you propagate MDC, `SecurityContext` and tenant identity across an executor boundary, and what changes with virtual threads?
87. `[D]` What is false sharing, and when is `@Contended` the right answer?
88. `[D]` How do you find lock contention in a running production JVM, as opposed to guessing from the code?

---

## 5. JVM internals, memory and performance

89. `[C]` Describe the JVM memory areas: heap, metaspace, stack, code cache, direct buffers.
90. `[D]` Young generation, old generation, and how objects are promoted.
91. `[D]` Compare Serial, Parallel, G1, ZGC and Shenandoah. How do you choose?
92. `[D]` What is a stop-the-world pause and what causes long ones in G1?
93. `[T]` Your heap usage is fine but the container keeps getting OOM-killed. Where is the memory going?
94. `[D]` `OutOfMemoryError` variants: heap space, GC overhead limit, metaspace, direct buffer, unable to create native thread. Cause of each.
95. `[D]` How do you find a memory leak in production? Walk through your exact tooling.
96. `[D]` Strong, soft, weak and phantom references. Give a real use case for each.
97. `[D]` What does the JIT compiler do? Explain tiered compilation, inlining and deoptimization.
98. `[T]` Why do microbenchmarks written with `System.currentTimeMillis()` give misleading results, and what do you use instead?
99. `[D]` What is escape analysis and scalar replacement?
100. `[D]` How do you read a thread dump? What are you looking for first?
101. `[D]` Key JVM flags you actually set in production and why.
102. `[A]` A service has p50 of 20ms and p99 of 3s. How do you find the cause?
103. `[D]` Walk through a `-Xlog:gc*` log. What do you read off it, and what do "to-space exhausted" and "Humongous" lines tell you?
104. `[T]` Why can a 32GB heap hold *less* live data than a 31GB heap?
105. `[D]` How does a direct byte buffer leak happen, and how do you find one in a Netty-based service?
106. `[D]` How do you prove a metaspace problem is a classloader leak rather than an under-sized metaspace?
107. `[A]` A container was OOMKilled. How do you get a heap dump out of a process the kernel already killed?
108. `[T]` Memory climbs and GC runs constantly, but every full GC returns to the same floor. Is this a leak, and what do you fix?

---

## 6. Design patterns and clean code

109. `[C]` Explain SOLID with a concrete Java example of a violation and its fix for each principle.
110. `[D]` Strategy versus Template Method versus State - how do you choose?
111. `[D]` Builder pattern - when do you need it beyond many constructor parameters?
112. `[D]` Factory versus Abstract Factory versus dependency injection. Has DI made factories obsolete?
113. `[D]` Decorator versus Proxy - both wrap. What is the intent difference?
114. `[D]` Observer pattern versus an event bus versus a message broker. Where is the boundary?
115. `[T]` Why is the Singleton pattern often called an anti-pattern in modern Spring applications?
116. `[D]` Explain the Circuit Breaker, Bulkhead and Retry patterns, and how they compose.
117. `[A]` How do you decide between inheritance and composition in a real design review?
118. `[A]` What is your definition of clean code at a team level, and how do you enforce it without becoming a bottleneck?
119. `[D]` Explain hexagonal / ports-and-adapters architecture and what it buys you in testing.
120. `[D]` Domain-Driven Design: aggregates, bounded contexts, and how they map to microservice boundaries.

---

## 7. Spring Framework and Spring Boot

121. `[C]` What problem does dependency injection solve? Constructor versus field versus setter injection.
122. `[T]` Why is field injection discouraged even though it is the most concise?
123. `[D]` Explain the Spring bean lifecycle, including `BeanPostProcessor` and `@PostConstruct`.
124. `[D]` Bean scopes: singleton, prototype, request, session. What happens when a singleton depends on a prototype?
125. `[T]` A singleton bean injects a prototype bean. Why does it get the same instance every time, and what are the two fixes?
126. `[D]` How does Spring Boot auto-configuration work end to end?
127. `[D]` `@Conditional` family: `@ConditionalOnMissingBean`, `@ConditionalOnProperty`, ordering. How do you override an auto-configuration?
128. `[C]` `@Component` versus `@Service` versus `@Repository` versus `@Controller` - is there any functional difference?
129. `[D]` How does Spring AOP work? JDK dynamic proxies versus CGLIB, and when each is used.
130. `[T]` `@Transactional` on a private method, or called from within the same class, does nothing. Explain why and give two fixes.
131. `[D]` Transaction propagation levels: `REQUIRED`, `REQUIRES_NEW`, `NESTED`, `SUPPORTS`, `MANDATORY`. Give a real use case for `REQUIRES_NEW`.
132. `[T]` `@Transactional(rollbackFor = ...)` - by default which exceptions roll back a transaction and which silently commit?
133. `[D]` Isolation levels and the anomalies they prevent: dirty read, non-repeatable read, phantom read.
134. `[D]` `@Async` - how it works, why the caller must not be in the same class, and how you configure the executor.
135. `[T]` Why does `@Async` combined with `@Transactional` on the same method behave unexpectedly?
136. `[D]` Circular dependencies in Spring: how they are resolved, why constructor injection fails, and why you should fix the design instead.
137. `[D]` Spring profiles, externalized configuration precedence, and `@ConfigurationProperties` versus `@Value`.
138. `[D]` Spring Boot Actuator: which endpoints do you expose in production and how do you secure them?
139. `[D]` How do you write tests in Spring Boot: `@SpringBootTest` versus slice tests versus plain unit tests. What is your pyramid?
140. `[T]` Why does `@MockBean` slow down your test suite, and how do you avoid context reloading?
141. `[A]` Spring MVC versus WebFlux. When would you actually choose reactive, and what is the cost?
142. `[D]` How does `RestTemplate` differ from `WebClient` and from the Java 11 `HttpClient`? What are you using in 2026?

---

## 8. Spring Security, authentication and authorization

143. `[C]` Walk through the Spring Security filter chain in order. Where does authentication actually happen?
144. `[D]` `AuthenticationManager`, `AuthenticationProvider`, `UserDetailsService`, `SecurityContextHolder` - how do they connect?
145. `[D]` Session-based authentication versus JWT. What are the real trade-offs, including revocation?
146. `[T]` How do you invalidate a stateless JWT before it expires? Discuss all realistic options.
147. `[D]` Access token versus refresh token: lifetimes, storage, rotation, and reuse detection.
148. `[D]` OAuth2 grant types in 2026: which are still recommended and which are deprecated, and why?
149. `[D]` OAuth2 versus OIDC. What exactly does OIDC add?
150. `[D]` Explain PKCE and the attack it prevents.
151. `[T]` Why is storing a JWT in `localStorage` risky, and what is the recommended alternative?
152. `[D]` CSRF: what it is, why it does not apply to a stateless bearer-token API, and when you must still enable it.
153. `[D]` CORS: preflight requests, why disabling it is not a security fix, and where to configure it correctly.
154. `[D]` Method-level security: `@PreAuthorize`, `@PostAuthorize`, `@Secured`, and SpEL expressions.
155. `[D]` How do you implement multi-tenant authorization without leaking data between tenants?
156. `[D]` Password storage: BCrypt versus Argon2 versus PBKDF2. What work factor do you choose and why?
157. `[D]` OWASP Top 10 - name them and give a Java-specific mitigation for each.
158. `[T]` How does SQL injection still happen in a JPA application, despite prepared statements?
159. `[D]` How do you secure secrets in a Spring Boot application deployed on AWS?
160. `[A]` How do you implement zero-trust service-to-service authentication in a microservice estate?

---

## 9. Databases, JPA and persistence

161. `[C]` JPA entity lifecycle states: transient, managed, detached, removed.
162. `[T]` Explain the N+1 select problem. Show three different fixes and the drawback of each.
163. `[T]` `FetchType.EAGER` versus `LAZY` - why does `LAZY` throw `LazyInitializationException` and what are the correct fixes (not `open-in-view`)?
164. `[D]` First-level versus second-level cache. When is the second-level cache dangerous?
165. `[D]` Optimistic versus pessimistic locking. How do you implement each in JPA?
166. `[D]` `@OneToMany` bidirectional mapping - who owns the relationship and what happens if you set only one side?
167. `[T]` Why should you not use `CascadeType.REMOVE` with a large collection?
168. `[D]` `save()` versus `saveAndFlush()` versus `persist()` versus `merge()`.
169. `[D]` How do you paginate efficiently over millions of rows? Why does `OFFSET` degrade?
170. `[D]` Database indexing: composite index column order, covering indexes, and why an index can be ignored.
171. `[D]` How do you read an execution plan and act on it?
172. `[D]` Connection pooling with HikariCP: how do you size the pool, and why is bigger not better?
173. `[A]` SQL versus NoSQL for a given workload - walk through your decision process.
174. `[D]` Database migrations with Flyway or Liquibase in a zero-downtime deployment. What are the rules?
175. `[A]` How do you change a column type on a 500 million row table with no downtime?

---

## 10. Microservices, APIs and distributed systems

176. `[A]` How do you decide microservice boundaries? What signals tell you a boundary is wrong?
177. `[A]` Monolith versus microservices in 2026 - when do you recommend staying monolithic?
178. `[D]` REST maturity levels, idempotency, and correct status code usage for each operation.
179. `[D]` API versioning strategies. Which do you use and how do you deprecate?
180. `[D]` Explain the CAP theorem accurately, and then explain why PACELC is more useful.
181. `[D]` Eventual consistency: how do you explain it to a product owner, and how do you make it acceptable to users?
182. `[D]` Saga pattern: choreography versus orchestration, and how compensation works.
183. `[T]` Why is the transactional outbox pattern needed, and what exactly does it fix that a "save then publish" cannot?
184. `[D]` How do you guarantee idempotency for a payment API consumed with retries?
185. `[D]` Exactly-once delivery - is it possible? Explain what Kafka actually gives you.
186. `[D]` Kafka: partitions, consumer groups, rebalancing, offset management, ordering guarantees.
187. `[T]` What happens to ordering when you increase Kafka partitions on an existing topic?
188. `[D]` Distributed tracing: how does context propagate across async boundaries?
189. `[D]` Service discovery, client-side versus server-side load balancing, and where a service mesh fits.
190. `[D]` Rate limiting algorithms: token bucket, leaky bucket, sliding window. Where do you enforce them?
191. `[D]` Caching strategies: cache-aside, read-through, write-through, write-behind. How do you handle invalidation and stampede?
192. `[A]` How do you design for graceful degradation when a downstream dependency is down?

---

## 11. AWS and cloud architecture

193. `[D]` ECS Fargate versus EKS versus Lambda versus EC2 - your decision framework.
194. `[T]` Lambda cold starts in Java: what causes them and which four techniques actually reduce them?
195. `[D]` SQS versus SNS versus EventBridge versus Kinesis - pick one per use case and justify.
196. `[D]` SQS standard versus FIFO: throughput, ordering, deduplication, and visibility timeout traps.
197. `[D]` Dead letter queues: when does a message land there and how do you reprocess safely?
198. `[D]` RDS versus Aurora versus DynamoDB. When is DynamoDB the wrong choice?
199. `[D]` DynamoDB partition key design, hot partitions, GSI versus LSI.
200. `[D]` IAM roles versus users versus policies. How does an EKS pod or ECS task get credentials?
201. `[T]` What is the difference between an IAM resource policy and an identity policy when both apply to an S3 request?
202. `[D]` VPC design: public/private subnets, NAT gateway cost, VPC endpoints, security groups versus NACLs.
203. `[D]` How do you manage secrets: Secrets Manager versus Parameter Store versus environment variables?
204. `[D]` S3 storage classes, lifecycle policies, and how you would cut storage cost by half.
205. `[D]` Auto-scaling: target tracking versus step scaling, and why scaling on CPU is often wrong.
206. `[A]` Design a multi-region active-active deployment. What are the three hardest problems?
207. `[A]` Your AWS bill jumped 40 percent this month. Walk through your investigation.
208. `[D]` Well-Architected Framework pillars - how do you apply them in a real review?

---

## 12. DevOps, CI/CD and observability

209. `[D]` Describe your ideal CI/CD pipeline for a Java microservice, stage by stage.
210. `[D]` Blue-green versus canary versus rolling deployment. What does each require from the application?
211. `[T]` What must be true about your database schema for a rolling deployment to be safe?
212. `[D]` Trunk-based development versus GitFlow. What do you recommend for a 30-engineer team?
213. `[D]` Docker image optimization for Java: layers, JLink, distroless, multi-stage builds.
214. `[T]` Why did your Java container use far more memory than `-Xmx`, and how do you fix it?
215. `[D]` Kubernetes: readiness versus liveness versus startup probes. What breaks if you conflate them?
216. `[D]` Requests versus limits, and what happens to a JVM when it hits a CPU limit.
217. `[D]` Terraform versus CloudFormation versus CDK. State management and drift.
218. `[D]` Observability: metrics, logs, traces. What do you instrument by default in every service?
219. `[D]` SLI, SLO, error budget - how do you actually use an error budget to make decisions?
220. `[D]` What does a good alert look like? How do you eliminate alert fatigue?
221. `[A]` How do you run a blameless postmortem, and what makes one useful six months later?

---

## 13. AI engineering with Java

222. `[D]` How do you integrate an LLM into a Spring Boot service? Describe the architecture.
223. `[D]` What is RAG, and what are the failure modes of a naive implementation?
224. `[D]` Embeddings and vector databases: chunking strategy, similarity metrics, and hybrid search.
225. `[D]` How do you control LLM cost and latency in production?
226. `[D]` Prompt injection: how does it work against a tool-using agent, and how do you defend?
227. `[D]` How do you evaluate an AI feature? What does your regression suite look like when outputs are non-deterministic?
228. `[D]` Streaming responses in Spring: SSE versus WebSocket versus WebFlux. What are the operational concerns?
229. `[D]` Spring AI or LangChain4j - what do they give you and what would you build yourself?
230. `[A]` How do you handle PII and compliance when sending data to a third-party model provider?
231. `[A]` A stakeholder wants an AI feature that you believe is a poor fit. How do you handle it?

---

## 14. System design

232. `[A]` Design a URL shortener handling 100 million redirects per day.
233. `[A]` Design a payment processing system with strict consistency and auditability.
234. `[A]` Design a notification service supporting email, SMS and push with retries and rate limits.
235. `[A]` Design a rate limiter usable across 200 service instances.
236. `[A]` Design an audit log that is tamper-evident and queryable over five years of data.
237. `[A]` Design a real-time dashboard consuming a 100k events/second stream.
238. `[A]` Design the migration of a 10-year-old monolith to services without a big bang.
239. `[A]` Design a document search feature combining keyword and semantic search.
240. `[A]` Design a multi-tenant SaaS platform, covering data isolation and noisy neighbours.
241. `[A]` Design a feature flag and experimentation platform.

---

## 15. Leadership, behavioral and .NET-to-Java positioning

242. Walk me through your 19-year career in four minutes.
243. Why are you leaving Sonata Software now?
244. You moved from .NET to Java in the middle of your career. Why, and what did you learn from doing both?
245. What is the most complex system you have personally architected?
246. Tell me about a production incident you owned end to end.
247. Describe a time you were technically wrong and someone junior corrected you.
248. How do you handle a disagreement with an architect or a principal peer?
249. How do you mentor engineers who are stronger than you in a specific area?
250. Tell me about a time you had to say no to a business stakeholder.
251. How do you balance technical debt against feature delivery? Give a concrete example.
252. Describe a decision you made that turned out to be wrong. What did it cost and what changed after?
253. How do you keep learning at 19 years of experience without chasing every trend?
254. What would you do in your first 90 days here?
255. How do you evaluate whether to adopt a new technology?
256. What questions do you have for us?
