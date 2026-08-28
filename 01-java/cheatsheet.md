# Cheatsheet

Fast revision. Read the night before and 30 minutes before the call. Depth lives in [answers.md](answers.md); this file is for recall.

---

## Java version highlights

| Version | What to mention |
| --- | --- |
| 8 | Lambdas, streams, `Optional`, default methods, new date/time API, Metaspace replaces PermGen |
| 9 | Modules (JPMS), `List.of`, private interface methods, `Flow` reactive API |
| 10-11 | `var`, `HttpClient`, `String.strip/repeat/isBlank`, single-file run. **11 is LTS** |
| 14-16 | `switch` expressions, text blocks, records, `instanceof` pattern matching, helpful NPEs |
| 17 | Sealed classes, `RandomGenerator`. **LTS** |
| 21 | **Virtual threads**, pattern matching for `switch`, record patterns, sequenced collections, generational ZGC. **LTS** |
| 24-25 | Most `synchronized` pinning removed, further Loom and ZGC refinement. **25 is LTS** |

Say "we are on 21 with virtual threads for IO-bound fan-out" rather than reciting the list.

---

## Collections: complexity and choice

| Type | get | add | contains | Ordering | Notes |
| --- | --- | --- | --- | --- | --- |
| `ArrayList` | O(1) | O(1)* | O(n) | insertion | * amortized; default choice |
| `LinkedList` | O(n) | O(1)† | O(n) | insertion | † only with a node; avoid |
| `ArrayDeque` | - | O(1)* | O(n) | insertion | beats `LinkedList` and `Stack` |
| `HashMap` | O(1) | O(1) | O(1) | none | treeifies at 8 in a bucket, table >= 64 |
| `LinkedHashMap` | O(1) | O(1) | O(1) | insertion / access | access order gives an LRU |
| `TreeMap` | O(log n) | O(log n) | O(log n) | sorted | red-black tree, navigation methods |
| `ConcurrentHashMap` | O(1) | O(1) | O(1) | none | bucket-level lock, lock-free reads, no nulls |
| `CopyOnWriteArrayList` | O(1) | O(n) | O(n) | insertion | read-dominated only |

`HashMap`: capacity 16, load factor 0.75, resize doubles. Index is `hash & (n-1)`; `hash()` XORs high 16 bits down.

**Traps.** Mutable key = lost entry. `Arrays.asList` is fixed-size and writes through. `List.of` is immutable and NPEs on null. `Collectors.toMap` throws on duplicate keys and on null values.

---

## Tricky one-liners

| Snippet | Result | Why |
| --- | --- | --- |
| `Integer a=127,b=127; a==b` | `true` | `valueOf` cache -128..127 |
| `Integer a=128,b=128; a==b` | `false` | outside cache |
| `0.1+0.2==0.3` | `false` | IEEE-754; use `BigDecimal("0.1")` |
| `try{return 1;}finally{return 2;}` | `2` | finally wins, swallows exceptions |
| `try{return x;}finally{x=99;}` | original `x` | return value stashed first |
| `f(null)` with `f(Object)`/`f(String)` | `f(String)` | most specific wins |
| `new String("a")=="a"` | `false` | new heap object; `intern()` fixes |
| `Optional.of(null)` | NPE | use `ofNullable` |
| `volatile int c; c++` | not atomic | read-modify-write |
| `a.value - b.value` comparator | overflow bug | use `Integer.compare` |
| `new T[10]` | won't compile | erasure; use `Array.newInstance` |
| `Object[] a = new String[1]; a[0]=42;` | `ArrayStoreException` | array covariance is unsound |
| Constructor calls overridable method | subclass field is `null` | subclass fields not yet initialized |
| Stream reused after terminal op | `IllegalStateException` | single-use |

---

## Concurrency

**JMM happens-before**: program order; unlock before lock; volatile write before volatile read; `Thread.start()`; `join()`; final field init before publication.

**`volatile`** = visibility + ordering, **not** atomicity.

**`ThreadPoolExecutor` submission order**: core threads → queue → up to max → rejection handler. *Unbounded queue means max is never reached.*

**Pool sizing**: CPU-bound ≈ cores + 1. IO-bound = `cores × util × (1 + wait/service)`.

**Rejection policies**: `Abort` (default), `CallerRuns` (backpressure - the useful one), `Discard`, `DiscardOldest`.

**Synchronizers**: `CountDownLatch` one-shot; `CyclicBarrier` reusable; `Semaphore` permits; `Phaser` dynamic.

**Virtual threads**: one per task, never pool them; `synchronized` pins (use `ReentrantLock`); limit downstream concurrency with a `Semaphore`; `ScopedValue` replaces `ThreadLocal`.

**`CompletableFuture`**: `thenApply` runs on the completing thread, `thenApplyAsync` on the pool. `thenCompose` = flatMap. `join()` throws `CompletionException`, `get()` throws `ExecutionException`.

**Deadlock detection**: `jcmd <pid> Thread.print` - the JVM names the cycle. Prevent with lock ordering and `tryLock(timeout)`.

---

## JVM

**Memory**: heap (young: Eden + 2 survivors, old) | metaspace (native) | thread stacks (~1MB each) | code cache | direct buffers.

**Collectors**: Serial (tiny) · Parallel (throughput) · G1 (default, pause target) · ZGC (sub-ms, large heaps) · Shenandoah.

**OOM causes**: heap space (leak) · GC overhead limit (late-stage leak) · metaspace (classloader leak) · direct buffer (NIO) · unable to create native thread (thread leak, not heap).

**Container memory** = heap + metaspace + code cache + stacks + direct + GC + native. Set `-XX:MaxRAMPercentage=70`, not `-Xmx` at 95 percent.

**Production flags**: `-XX:MaxRAMPercentage=70 -XX:+UseG1GC -XX:+HeapDumpOnOutOfMemoryError -XX:+ExitOnOutOfMemoryError -Xlog:gc*:file=... -XX:NativeMemoryTracking=summary`, `-Xms == -Xmx`.

**Tools**: `jcmd` (dumps, NMT) · `jstack` · JFR (always-on) · async-profiler (flame graphs) · Eclipse MAT (heap analysis) · JMH (benchmarks).

**Reference types**: strong · soft (memory pressure) · weak (next GC, `WeakHashMap`) · phantom (`Cleaner`).

---

## Streams

`filter map flatMap distinct sorted peek limit skip` are lazy. `collect reduce forEach count anyMatch findFirst min max` are terminal.

`Collectors`: `toList toSet toMap(k,v,merge) groupingBy(f, downstream) partitioningBy joining counting summingInt averagingDouble mapping teeing`.

**Parallel** only when: large N, cheap even splitting (array/`ArrayList`/range), stateless and associative, CPU-bound. Uses the shared common pool - never for IO, never in a request handler.

---

## Spring

**Bean lifecycle**: instantiate → inject → `*Aware` → `BeanPostProcessor.before` → `@PostConstruct` → `afterPropertiesSet` → init-method → **`BeanPostProcessor.after` (proxy created here)** → in use → `@PreDestroy` → destroy.

**Proxy rules**: JDK proxy if interfaces, else CGLIB (Boot defaults to CGLIB). No `final` classes or methods. **Self-invocation bypasses the proxy** - kills `@Transactional`, `@Async`, `@Cacheable`, `@PreAuthorize` on internal calls.

**`@Transactional`**:

- Rolls back on unchecked only. **Checked exceptions commit.** Use `rollbackFor = Exception.class`.
- Propagation: `REQUIRED` (default) · `REQUIRES_NEW` (suspends, second connection) · `NESTED` (savepoint, JDBC only) · `MANDATORY` (guard) · `SUPPORTS` · `NEVER` · `NOT_SUPPORTED`.
- Isolation: `READ_COMMITTED` (Postgres default) · `REPEATABLE_READ` (MySQL default) · `SERIALIZABLE`.
- Anomalies: dirty read → non-repeatable read → phantom read.

**Auto-configuration**: `@EnableAutoConfiguration` → `AutoConfigurationImportSelector` → `META-INF/spring/...AutoConfiguration.imports` → `@Conditional` filtering. Override with your own bean (`@ConditionalOnMissingBean` backs off). Debug with `--debug`.

**Config precedence** (high to low): command line → `SPRING_APPLICATION_JSON` → env vars → external profile yml → internal profile yml → external yml → internal yml → defaults.

**Scopes**: singleton · prototype (Spring does not destroy these) · request · session. Singleton→prototype needs `ObjectProvider` or `@Lookup`.

**Testing**: unit (no context) → slices (`@WebMvcTest`, `@DataJpaTest`) → `@SpringBootTest` + Testcontainers → contract tests. `@MockBean` changes the context cache key and slows the suite.

---

## Spring Security filter chain (order)

`SecurityContextHolderFilter` → `HeaderWriter` → `Cors` → `Csrf` → `Logout` → **authentication filters (`UsernamePassword`, `BearerToken`, OAuth2, custom JWT)** → `RequestCacheAware` → `Anonymous` → `SessionManagement` → **`ExceptionTranslation` (401/403)** → **`AuthorizationFilter` (decision)**.

`AuthenticationManager` → `ProviderManager` → `AuthenticationProvider` → `UserDetailsService` + `PasswordEncoder` → `SecurityContextHolder` (ThreadLocal).

**Auth quick table**

| Topic | Answer |
| --- | --- |
| Session vs JWT | Sessions revocable, JWT stateless-but-unrevocable |
| Revoke a JWT | Short TTL + refresh, denylist, token version claim, key rotation |
| Access token TTL | 5-15 min; refresh rotated with reuse detection |
| Grants in 2026 | Auth Code + PKCE, Client Credentials, Device. Implicit and ROPC are dead |
| OIDC adds | `id_token`, `/userinfo`, discovery, JWKS |
| PKCE prevents | Authorization code interception |
| JWT storage | Not `localStorage` (XSS). HttpOnly+Secure+SameSite cookie, access token in memory |
| CSRF needed when | Credentials sent automatically (cookies, Basic). Not for bearer headers |
| CORS is | A browser control, not authorization. Configure before auth filters |
| Password hash | Argon2id preferred, BCrypt cost 10-12 acceptable; tune to ~250-500ms |
| `hasRole('X')` | Prepends `ROLE_`; `hasAuthority('X')` does not |

**OWASP Top 10**: Broken Access Control · Cryptographic Failures · Injection · Insecure Design · Security Misconfiguration · Vulnerable Components · Auth Failures · Integrity Failures · Logging Failures · SSRF.

---

## JPA and SQL

**Lifecycle**: transient → managed (dirty checking auto-flushes) → detached (`LazyInitializationException`) → removed.

**N+1 fixes**: `JOIN FETCH` (breaks pagination on collections) · `@EntityGraph` · `@BatchSize` / `default_batch_fetch_size` (best general default) · two-query ID fetch · DTO projection (best for reads).

**Do not** fix lazy loading with `EAGER` or `open-in-view` - turn `open-in-view` off.

**Locking**: optimistic `@Version` (default choice, handle `OptimisticLockException` with retry) · pessimistic `@Lock(PESSIMISTIC_WRITE)` with a lock timeout.

**Owning side** of `@OneToMany`/`@ManyToOne` is the side with the FK (`@ManyToOne`). Always write `addChild`/`removeChild` helpers.

**`merge` returns the managed copy** - the passed instance stays detached.

**Pagination**: keyset/seek (`WHERE (created_at,id) < (?,?) ORDER BY ... LIMIT n`), not `OFFSET`.

**Indexes**: leftmost prefix rule on `(a,b,c)`; equality → range → sort order; a function on the column kills the index; every index costs writes.

**HikariCP**: `(cores × 2) + spindles` ≈ 10-20 per instance. Alert on `hikaricp_connections_pending`. `maxLifetime` < any upstream idle timeout.

**Zero-downtime migration**: expand → backfill in batches → dual-write → switch reads → contract. Additive only per release. `CREATE INDEX CONCURRENTLY`, constraints `NOT VALID` then validate, set `lock_timeout`.

---

## Distributed systems

**CAP**: during a partition, choose C or A. **PACELC**: else, choose Latency or Consistency - the trade-off you live with daily.

**Outbox**: solves the dual-write. Write the event in the same local transaction, relay by polling or CDC (Debezium). Gives at-least-once, so consumers need an **inbox** / dedup.

**Saga**: choreography (2-3 steps, no coordinator) vs orchestration (more steps, observable). Compensations are semantic. Steps must be idempotent.

**Idempotency**: client-generated key, unique constraint in the same transaction as the effect, store and replay the response, validate the payload hash.

**Kafka**: ordering per partition only · consumers ≤ partitions · `acks=all` + `min.insync.replicas=2` · disable auto-commit · **increasing partitions breaks key ordering** · exactly-once only within Kafka.

**SQS**: visibility timeout must exceed processing time · FIFO group ID is the parallelism unit · DLQ after `maxReceiveCount`, alert on it.

**Resilience order**: `Retry(CircuitBreaker(RateLimiter(TimeLimiter(Bulkhead(call)))))`. Retry needs backoff + jitter + idempotency.

**Caching**: cache-aside (default) · read-through · write-through · write-behind. Stampede fixes: single-flight lock, TTL jitter, early refresh.

**Rate limiting**: token bucket (bursty, default) · leaky bucket (smooth) · sliding window counter. Return 429 + `Retry-After`. Decide fail-open vs fail-closed.

**Status codes**: 201+Location · 202 async · 204 delete · 400 syntax · 401 unauthenticated · 403 unauthorized · 404 hide existence · 409 conflict · 422 semantic · 429 + `Retry-After` · 503 + `Retry-After`. Errors as RFC 9457 `problem+json`.

---

## AWS

**Compute**: Lambda (spiky, event-driven, <15 min) · ECS Fargate (default for services) · EKS (need the ecosystem) · EC2 (special hardware or licensing).

**Lambda Java cold starts**: SnapStart · reduce framework (or GraalVM native) · init work in the init phase · provisioned concurrency.

**Messaging**: SQS (work queue) · SNS (fan-out) · EventBridge (routing rules, replay, schema registry) · Kinesis/MSK (ordered, replayable streams).

**Data**: RDS (familiar) · Aurora (fast failover, 15 replicas, serverless v2) · DynamoDB (KV at scale - wrong when access patterns are unknown or you need joins/aggregations).

**DynamoDB**: ~3000 RCU / 1000 WCU per partition · hot partition from low-cardinality keys → shard the key · GSI (different PK, eventually consistent, throttling affects base writes) vs LSI (same PK, created with table, 10 GB item collection limit).

**IAM**: identity and resource policies are additive **within** an account; **across accounts both must allow**. Explicit deny always wins. SCPs restrict, never grant. Workload credentials: instance profile · ECS task role (≠ execution role) · EKS IRSA / Pod Identity · Lambda execution role. No static keys.

**VPC**: public (LB, NAT) / private (compute) / isolated (data). NAT is billed per hour **and** per GB - gateway endpoints for S3 and DynamoDB are free. SGs stateful and referenceable; NACLs stateless.

**Secrets**: Secrets Manager (rotation) · Parameter Store SecureString (cheap) · never in the image or repo.

**Scaling**: target tracking by default. **CPU is usually the wrong metric for Java services** - scale on request concurrency, queue depth, or `ApproximateAgeOfOldestMessage`. Out fast, in slow. Health-check grace > JVM warm-up.

**Well-Architected pillars**: operational excellence · security · reliability · performance efficiency · cost optimization · sustainability.

---

## DevOps

**Pipeline**: commit (build, unit, static analysis) → security (deps, secrets, SBOM, image scan) → integration (Testcontainers, contract tests) → package (multi-stage, layered, signed, SHA tag) → staging + smoke → canary → production. **Build once, promote the same artifact.**

**Deployments**: rolling (needs two-version compatibility) · blue-green (instant rollback, double cost, all-or-nothing) · canary (best risk profile, needs per-version metrics and automated analysis).

**Rolling + schema**: additive only; nullable or defaulted new columns; never rename or drop in the same release; migrations backward compatible so rollback works.

**Docker for Java**: multi-stage · layered JAR · distroless or JRE-alpine · `jlink` · non-root · pin by digest · optimize layer churn before size.

**Container memory**: RSS = heap + metaspace + code cache + stacks + direct + native. Use `MaxRAMPercentage`, cap direct and metaspace, set memory request = limit.

**Probes**: startup (gates the others during JVM boot) · liveness (dumb, dependency-free, restarts) · readiness (removes from LB, checks dependencies). **Never put a database check in liveness** - one blip restarts the fleet.

**CPU limits**: CFS throttling, not killing. Check `container_cpu_cfs_throttled_seconds`. Consider no CPU limit for latency-sensitive services; pin `ActiveProcessorCount` if detection is wrong.

**Observability defaults**: RED metrics as histograms · JVM, pool and queue metrics · structured JSON logs with trace ID in MDC · OTel traces with tail-based sampling · trace ID returned to the client.

**SLO**: 99.9% over 28 days ≈ 40 minutes of budget. **Alert on burn rate**, not raw errors. Fast burn pages, slow burn tickets. Budget exhausted → reliability work takes priority, agreed in advance.

---

## AI engineering

**RAG pipeline**: ingest → chunk (200-500 tokens, overlap, structure-aware, metadata) → embed → store → **hybrid retrieve (BM25 + vector, fused with RRF)** → **rerank (cross-encoder)** → prompt with citations → validate → stream.

**RAG failure modes**: retrieval miss on exact terms · bad chunking · irrelevant context used anyway · no grounding enforcement · stale or unpermissioned index · no evaluation.

**Similarity**: cosine (normalized dot product). **Index**: HNSW (fast, more memory) vs IVFFlat (less memory, lower recall).

**Cost control**: right-size the model per task · exact + semantic + provider prompt caching · trim context and cap history · batch API · per-tenant budget with graceful degradation. **Attribute cost by feature, tenant, model and prompt version.**

**Latency**: stream (time-to-first-token) · parallelize retrieval · shorten the chain · timeout with fallback to a smaller model.

**Prompt injection**: direct and **indirect** (planted in retrieved documents). Defenses: treat model output as untrusted, least-privilege tools with schema validation, human approval for irreversible actions, dual-LLM separation, egress control, audit every tool call. Not solved - limit blast radius.

**Evaluation**: golden dataset · deterministic assertions (schema, citations resolve, no PII, cost/latency bounds) · component metrics (retrieval recall@k, then faithfulness and relevance) · LLM-as-judge with pairwise comparison and human calibration · online metrics and A/B. Run in CI; prompts are versioned code; pin model versions.

**PII**: minimize → redact/tokenize → zero-retention contract → in-VPC model (Bedrock) for regulated data → audit and retention policy → scan the output too.

---

## System design template

1. Requirements: functional, then scale / latency / availability / consistency / retention / compliance
2. Estimates: peak QPS, read:write ratio, storage per year, bandwidth (round hard, say assumptions)
3. API: the two or three endpoints that matter
4. Data model and access patterns → store choice justified by them
5. Architecture: 6-8 boxes, then walk one write path and one read path
6. Deep dive where steered
7. **What breaks first at 10x, and the mitigation**
8. **Failure modes per component**
9. **Operations: metrics, alerts, deployment, cost**
10. **Trade-offs and what you deliberately did not build**

Steps 7-10 are where principal candidates separate from senior ones.

---

## Numbers worth knowing

| Operation | Time |
| --- | --- |
| L1 cache reference | 1 ns |
| Branch mispredict | 5 ns |
| Main memory reference | 100 ns |
| Mutex lock/unlock | 25 ns |
| Compress 1 KB | 2 µs |
| SSD random read | 150 µs |
| Read 1 MB from memory | 20 µs |
| Read 1 MB from SSD | 1 ms |
| Round trip within a datacenter | 500 µs |
| Read 1 MB from disk | 20 ms |
| Round trip California to Netherlands | 150 ms |

**Availability**: 99% = 3.65 days/year · 99.9% = 8.8 hours · 99.99% = 53 minutes · 99.999% = 5 minutes.

**Rules of thumb**: 1M requests/day ≈ 12 QPS · assume peak = 2-5× average · one modern instance handles a few thousand simple QPS · one Postgres instance handles low thousands of simple queries/second.

---

## Final 30 minutes

- Filter chain order, bean lifecycle, `ThreadPoolExecutor` submission order.
- The five `@Transactional` traps: self-invocation, private, checked exceptions, caught exceptions, `REQUIRES_NEW` connection use.
- Three numbers from your own experience: scale, latency improvement, cost saved.
- Five questions for the interviewer - about the team's biggest technical risk, on-call reality, how decisions get made, what success looks like in a year, and why the role is open.
- One sentence positioning nineteen years and two ecosystems as an asset.
