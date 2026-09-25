# Spring Cheatsheet

Fast revision. Assumes the Java-level material in [../01-java/cheatsheet.md](../01-java/cheatsheet.md).

---

## `refresh()` phase order

```
1  prepareRefresh                 flags, required properties
2  obtainFreshBeanFactory         load BeanDefinitions (component scan)
3  prepareBeanFactory             SpEL resolver, Aware processor
4  postProcessBeanFactory         subclass hook (web scopes)
5  invokeBeanFactoryPostProcessors  <- @Configuration parsed, auto-config selected
6  registerBeanPostProcessors       <- auto-proxy creator registered
7  initMessageSource
8  initApplicationEventMulticaster
9  onRefresh                      <- embedded web server created
10 registerListeners
11 finishBeanFactoryInitialization  <- singletons created, AOP PROXIES CREATED
12 finishRefresh                  Lifecycle start, ContextRefreshedEvent
```

**Consequences to recite:** all definitions exist before any instance. `@PostConstruct` runs on the raw target, before the proxy. A `BeanFactoryPostProcessor` that injects a normal bean forces it created at step 5, so it never gets proxied ("not eligible for getting processed by all BeanPostProcessors").

### Three-level singleton cache

`singletonObjects` → `earlySingletonObjects` → `singletonFactories`. The third level exists so the early reference is the **proxy**, not the raw object.

---

## Proxy decision table

| Situation | Proxied? |
| --- | --- |
| External call to a public method on a Spring bean | Yes |
| `this.method()` (self-invocation) | **No** |
| `private`, `final`, `static` method | **No** |
| Called from `@PostConstruct` | **No** (proxy does not exist yet) |
| `final` class with CGLIB | **Fails** |
| Object created with `new` | **No** |

**Everything self-invocation silently breaks:** `@Transactional`, `@Async`, `@Cacheable`/`@CachePut`/`@CacheEvict`, `@PreAuthorize`/`@PostAuthorize`/`@Secured`, `@Retryable`, `@Validated` method validation, `@Timed`/`@Observed`, `@CircuitBreaker`/`@Retry`/`@Bulkhead`, custom aspects.

JDK proxy = interfaces only, `this()` pointcut fails. CGLIB (Boot default) = subclass, needs non-final class and method.

### `@Configuration` full vs lite

| | Full (default) | Lite (`proxyBeanMethods = false`) |
| --- | --- | --- |
| CGLIB subclass | Yes | No |
| `@Bean` calling `@Bean` | Returns singleton | **New unmanaged instance** |
| Startup cost | Higher | Lower (all Boot auto-config uses it) |

---

## Transaction attributes

| Propagation | Existing tx | No tx |
| --- | --- | --- |
| `REQUIRED` (default) | Join | Create |
| `REQUIRES_NEW` | Suspend, create new (2nd connection) | Create |
| `NESTED` | Savepoint | Create |
| `SUPPORTS` | Join | Run without |
| `NOT_SUPPORTED` | Suspend | Run without |
| `MANDATORY` | Join | **Throw** |
| `NEVER` | **Throw** | Run without |

**Rollback:** unchecked + `Error` → rollback. Checked → **commit**. Caught exception → the advisor never sees it → commit.

**`readOnly = true`** does three things: `Connection.setReadOnly` (driver hint), Hibernate `FlushMode.MANUAL` + no dirty-check snapshots, and read-replica routing signal. It does **not** guarantee writes fail.

**`UnexpectedRollbackException`:** inner `REQUIRED` throws → marks `rollbackOnly` → outer catches and continues → outer commit throws.

**Thread-bound:** `TransactionSynchronizationManager` holds the resource map in a `ThreadLocal`. Therefore `@Async`, new threads and reactive chains inherit **nothing**.

**`@TransactionalEventListener` phases:** `BEFORE_COMMIT` (write outbox row here) · `AFTER_COMMIT` (publish to Kafka here) · `AFTER_ROLLBACK` · `AFTER_COMPLETION`. A DB write in `AFTER_COMMIT` is **silently lost** unless `REQUIRES_NEW`. Does not fire at all with no transaction unless `fallbackExecution = true`.

---

## MVC request flow

```
Filters (Security ~order -100)
  → DispatcherServlet
    → HandlerMapping     (RequestMappingInfo → HandlerMethod)
    → interceptor preHandle
    → HandlerAdapter     (argument resolvers → invoke → return value handlers)
    → interceptor postHandle
    → HandlerExceptionResolver  ← @ControllerAdvice lives HERE
    → interceptor afterCompletion
```

A **filter** cannot know the handler (mapping happens inside the dispatcher) and an exception thrown in a filter **bypasses `@ControllerAdvice`** → goes to `/error`.

| Concern | Use |
| --- | --- |
| Raw bytes, all requests incl. static/error | `Filter` |
| Needs the resolved `HandlerMethod` | `HandlerInterceptor` |
| Cross-cutting on domain objects | AOP |
| Error mapping | `@ControllerAdvice` + `ProblemDetail` |

**Validation exceptions:** `@Valid` on `@RequestBody` → `MethodArgumentNotValidException` (handled → 400). `@Validated` on a class → `ConstraintViolationException` (**unhandled → 500**, add a handler).

**Async MVC:** `Callable` (executor) · `DeferredResult` (any thread) · `WebAsyncTask` · `StreamingResponseBody` · `SseEmitter`. `SecurityContext` propagates; **MDC does not**.

**Removed in Spring 6:** path extension content negotiation, suffix pattern matching, trailing-slash matching.

---

## Reactive quick reference

| Operator | Effect |
| --- | --- |
| `subscribeOn` | Where the **source** runs; position irrelevant, first wins |
| `publishOn` | Everything **downstream** of it |
| `flatMap` | Concurrent, interleaved, **default concurrency 256** - always bound it |
| `concatMap` | Sequential, ordered |
| `flatMapSequential` | Concurrent, ordered output |
| `onErrorContinue` | **Trap** - breaks the operator contract; use `onErrorResume` inside the inner publisher |

**Schedulers:** `parallel` (CPU) · `boundedElastic` (wrap blocking) · `single` · `immediate`. Never block `reactor-http-nio-*`.

**Context:** `ThreadLocal` fails; use Reactor `Context` (`contextWrite`/`deferContextual`). `SecurityContextHolder` → `ReactiveSecurityContextHolder`. BlockHound in tests catches blocking on the loop.

**Symptom of one blocking call:** all routes slow, CPU idle.

---

## Spring Data

| Return type | Cost |
| --- | --- |
| `List` | All rows |
| `Page` | Query + **extra COUNT** |
| `Slice` | `pageSize + 1` rows, no count |
| `Stream` | Cursor - needs open tx **and** close **and** fetch size **and** periodic `clear()` |

**Projections:** closed interface → narrow SQL. **Open** interface (`@Value` SpEL) or **nested** → loads full entity. DTO constructor projection → narrow, preferred.

**`@Modifying`** → always `clearAutomatically = true, flushAutomatically = true`.

**`save()` with an assigned ID** issues a SELECT (`isNew` is ID-null based → `merge`). Fix with `Persistable`, `@Version` or `@CreatedDate`.

**`@EntityGraph` + `Pageable` on a collection** → in-memory pagination (`HHH000104`).

**Native query + user sort column** → SQL injection. Use an allowlist map.

---

## Spring Security 6

```java
@Bean @Order(1) SecurityFilterChain api(HttpSecurity http) throws Exception {
    return http.securityMatcher("/api/**")
        .authorizeHttpRequests(a -> a
            .requestMatchers("/api/public/**").permitAll()
            .anyRequest().authenticated())
        .oauth2ResourceServer(o -> o.jwt(withDefaults()))
        .sessionManagement(s -> s.sessionCreationPolicy(STATELESS))
        .csrf(CsrfConfigurer::disable)
        .build();
}
```

**Chain dispatch:** first matching chain wins, and **only** it runs. A chain with no `securityMatcher` matches everything - put it last or later chains are dead.

**5 → 6 changes that fail at RUNTIME (not compile):**

| Change | Symptom |
| --- | --- |
| `SecurityContextHolderFilter` only reads | Custom filter auth lost next request - call `saveContext` |
| `AuthorizationFilter` applies to `ERROR`/`FORWARD` | Error pages 403 / redirect loops |
| CSRF `XorCsrfTokenRequestAttributeHandler` + deferred token | SPA CSRF failures |
| `requestMatchers` MVC-aware matching | Rules match differently - can widen access |

Compile-time: `WebSecurityConfigurerAdapter` → `SecurityFilterChain` bean · `authorizeRequests` → `authorizeHttpRequests` · `antMatchers`/`mvcMatchers` → `requestMatchers` · `@EnableGlobalMethodSecurity` → `@EnableMethodSecurity` (prePost on by default) · `AccessDecisionManager`/voters → `AuthorizationManager`.

**Context propagation:** `@Async` → `DelegatingSecurityContextAsyncTaskExecutor` or a `TaskDecorator` that sets **and clears in `finally`**. Never `MODE_INHERITABLETHREADLOCAL` with a pool (wrong-user attribution).

**`StrictHttpFirewall`** rejects `%2F`, `%2E`, `;`, `\`, `//`, non-printable → bare 400. Fix the URL design, not the firewall.

---

## OAuth2 / OIDC

| Config | Role |
| --- | --- |
| `oauth2ResourceServer` | My API validates incoming tokens |
| `oauth2Login` | My app authenticates users via an IdP (OIDC RP) |
| `oauth2Client` | My app gets tokens to call other APIs |

**Default JWT validation:** signature, `exp`/`nbf`, `iss`. **Audience is NOT validated by default** - add `JwtClaimValidator<>("aud", ...)`. Treat as mandatory.

**Authorities:** default converter reads `scope`/`scp` → prefix **`SCOPE_`**. So `hasRole('ADMIN')` fails - Keycloak puts roles in `realm_access.roles`, Cognito in `cognito:groups`. Write a `JwtAuthenticationConverter`.

**Token works in Postman, 401 in service:** audience → issuer trailing slash → authority mapping (403 not 401) → clock skew → header stripped by gateway.

**Multi-issuer:** `JwtIssuerAuthenticationManagerResolver.fromTrustedIssuers(...)` - the trusted list must be explicit or it is an auth bypass.

---

## Boot production defaults to change

```yaml
server.shutdown: graceful
spring.lifecycle.timeout-per-shutdown-phase: 30s

spring.datasource.hikari:
  maximum-pool-size: 15          # a concurrency limit, not a throughput dial
  minimum-idle: 15
  connection-timeout: 3000
  max-lifetime: 570000           # SHORTER than DB / LB / NAT idle timeout
  leak-detection-threshold: 20000

spring.task.execution.pool: {core-size: 8, max-size: 32, queue-capacity: 100}
spring.threads.virtual.enabled: true     # Boot 3.2+ / Java 21

management.endpoints.web.exposure.include: health,info,prometheus   # never "*"
management.endpoint.health.probes.enabled: true
management.endpoint.health.show-details: when-authorized
management.endpoint.env.show-values: never
management.server.port: 9090
```

**Liveness** = no dependencies at all. **Readiness** = only hard dependencies (own DB). Putting a downstream in either turns a blip into a fleet-wide outage.

**Graceful shutdown does not cover:** Kafka/SQS listeners, `@Scheduled`, async executors, or LB deregistration - add a `preStop` sleep of 5-10s.

**Startup sequence to recite:** `preStop` sleep → readiness fails → traffic drains → `SIGTERM` → requests + listeners finish → context close.

---

## Observability

| Meter | Use |
| --- | --- |
| `Counter` | Monotonic events |
| `Timer` | Latency |
| `Gauge` | Sampled value (**weak reference** - keep the source alive) |
| `DistributionSummary` | Non-time distributions |
| `LongTaskTimer` | In-progress long work |

**`publishPercentiles` cannot be aggregated across instances.** Use `publishPercentileHistogram` and let Prometheus compute quantiles.

**Cardinality:** every tag combination = one time series. Never tag with user ID, order ID or raw URI. `http.server.requests` uses the **matched pattern** for exactly this reason. High-cardinality data belongs in traces and logs.

**`@Observed`** → one recording produces metric + span. `lowCardinalityKeyValues` → tags + attributes; `highCardinalityKeyValues` → attributes only.

**Boot 3:** Sleuth is gone → **Micrometer Tracing**; propagation default changed B3 → **W3C `traceparent`**.

---

## Startup and packaging

| Option | Gain | Cost |
| --- | --- | --- |
| `BufferingApplicationStartup` + `/actuator/startup` | Diagnosis | None |
| Lazy init | Fast start | **Hides failures until runtime** - dev/test only |
| CDS (Boot 3.3) | ~30-40% off startup | Training run in the build |
| CRaC | Milliseconds, JIT warm | Resources must be re-established on restore |
| AOT | Faster start, less memory | **Conditions evaluated at BUILD time** - profiles fixed |
| Native image | Instant start, low memory | Reflection hints, 5-10 min builds, must run full suite natively |

---

## Test slices

| Slice | Loads | Excludes |
| --- | --- | --- |
| `@WebMvcTest` | Controllers, advice, filters, security | Services, repos, **your `@Configuration`** |
| `@DataJpaTest` | Entities, repos, tx + rollback | Web, services |
| `@JsonTest` | Jackson + `JacksonTester` | Everything else |
| `@RestClientTest` | `MockRestServiceServer` | Web layer |
| `@WebFluxTest` | Reactive web, `WebTestClient` | Services, repos |

**Context cache key** = config classes + profiles + properties + initializers + customizers (`@MockBean`, `@DynamicPropertySource`, web environment) + parent. Any difference = a new application started.

**`@Transactional` tests hide:** commit-time constraints, flush timing, `LazyInitializationException`, locking and concurrency, and `AFTER_COMMIT` listeners never firing.

**`@WebMvcTest` does not load your `SecurityConfig`** → `@Import` it, or the test verifies Spring's defaults.

`@MockBean` → **`@MockitoBean`** (Spring 6.2). Prefer plain Mockito with constructor injection.

---

## Spring Cloud

| Component | Verdict on Kubernetes |
| --- | --- |
| Eureka | Skip - Services + DNS |
| Config Server | Usually skip - ConfigMaps / Parameter Store |
| LoadBalancer | Skip unless zone affinity |
| Bus | Skip - rolling restart |
| Gateway | Keep if you need app-aware routing |
| Resilience4j | Keep - app-level, platform cannot see it |
| Stream / spring-kafka | Keep |
| Kubernetes Config | Usually skip - mount the ConfigMap, `spring.config.import: configtree:` |
| Kubernetes Discovery | Skip - Service DNS. Keep only for gRPC / HTTP2 or zone-aware routing |

**Resilience4j aspect order (outermost first):** `Retry → CircuitBreaker → RateLimiter → TimeLimiter → Bulkhead → method`. Retry must be outside the transaction advisor.

**Kafka:** `concurrency` ≤ partitions · disable auto-commit · `ErrorHandlingDeserializer` (poison messages) · `DefaultErrorHandler` + `DeadLetterPublishingRecoverer` · `@RetryableTopic` so retries do not block the partition · `addNotRetryableExceptions`.

**Exactly-once across Kafka and a database is not achievable.** Design for at-least-once + an inbox table in the same transaction. `@Transactional` on `@KafkaListener` is a **database** transaction only.

**`@Scheduled` runs on every instance** → ShedLock (`lockAtMostFor` > worst-case runtime), leader election, or an external scheduler.

**Config reload on Kubernetes:** default is **off**. `refresh` (rebind `@ConfigurationProperties`) < `restart_context` < `shutdown`. A ConfigMap edit is an untracked change applied to every pod at once with no rollout and no rollback → change it in Git, checksum-annotate the pod template, get a rolling update.

---

## Web protocols beyond REST

**STOMP:** handshake is HTTP (filters, cookies, security apply) → after upgrade **nothing is HTTP**. Simple broker = in-memory map, **per JVM**.

**Scale-out:** sticky sessions do **not** help - the *publisher* is on the wrong instance. Fix = `enableStompBrokerRelay` (RabbitMQ / ActiveMQ), or a Redis/Kafka side channel you now own.

**Per-user push:** `convertAndSendToUser(user, "/queue/x", p)` → rewrites to a session-unique destination; client subscribes to `/user/queue/x`.

**Auth:** handshake (cookie/session) *or* `CONNECT` frame in a `ChannelInterceptor` (bearer tokens - browsers cannot set handshake headers). **The connection outlives the token.** Authorize per *destination*, not per URL.

| | WebSocket | SSE | Long polling |
| --- | --- | --- | --- |
| Direction | Both ways | Server → client | Request/response |
| Reconnect | You build it | Built in, `Last-Event-ID` | Natural |
| Proxies | Needs `Upgrade` end to end | Disable buffering + heartbeat | Fine |

Default to **SSE** unless the client genuinely pushes. Watch the LB idle timeout (60s on an ALB).

**CORS:** `http.cors(withDefaults())` + a `CorsConfigurationSource` bean - Security runs **before** `DispatcherServlet`, and a preflight `OPTIONS` carries no credentials → 401 before MVC's CORS ever runs. `allowCredentials(true)` + `allowedOrigins("*")` throws → use `allowedOriginPatterns`. Never set CORS in both the gateway and the app (duplicate headers are rejected).

---

## Messaging endpoints

**JMS:** `JmsTemplate` opens **connection + session + producer per call** → `CachingConnectionFactory` (`sessionCacheSize` > concurrency). Not in front of an XA factory.

**What actually redelivers:** `sessionTransacted=true` (local JMS tx) or `AUTO_ACKNOWLEDGE`. `@Transactional` alone is the **database** only. JMS tx + DB tx = best-efforts 1PC, not atomicity.

**AMQP defaults to change:** `publisher-confirm-type: correlated` (broker took it) · `publisher-returns: true` + `mandatory` (it was routed - catches routing-key typos) · `default-requeue-rejected: false` (true = hot loop on a poison message).

**Neither confirms nor returns catch** a consumer-side failure, or a producer crash between DB commit and publish → outbox.

**Retry placement:** in-process interceptor = short transient only (holds the consumer thread) · immediate requeue = hot loop · **delay queue** (TTL queue with DLX back to the exchange) = the one that scales. Always terminate at a DLQ with an alert and a redrive runbook.

**`__TypeId__` puts the producer's FQCN on the wire.** Map logical IDs (`order.created.v1`) with `DefaultJackson2JavaTypeMapper`, or force the type on the consumer. Kafka: `spring.json.trusted.packages` is an allow-list, never `*`.

**Declaration ownership:** consumer owns its queue + binding; exchanges are infrastructure. Mismatched redeclaration = `PRECONDITION_FAILED`, channel down.

**Spring Integration** earns its place for protocol adapters (SFTP, mail, TCP, MQTT) and stateful EIPs (aggregator, resequencer, claim check). One source → transform → one sink does **not** need it.

---

## Spring Batch

```
Job ── JobInstance (name + identifying params) ── JobExecution (one attempt)
        └── StepExecution ── ExecutionContext (reader position, restart state)
```

**Transaction boundary = the chunk.** read × N (in memory) → process each → **write(list) once** → update step counters → commit. That single batched write is where the speed comes from.

| Failure at item 7 of chunk 2 | |
| --- | --- |
| Chunk 1 | Committed, counters advanced |
| Chunk 2 | Fully rolled back |
| Restart | Reader resumes from `ExecutionContext` **only if it is an `ItemStream`** |

**Fault tolerance:** a skippable exception → rollback → **re-read the chunk item by item** to find the culprit → processors must be side-effect free, writers must be idempotent.

**Why writers must be idempotent even though chunks are transactional:** non-restartable reader · the skip scan · commit-then-crash · file/HTTP/message effects are not in the transaction. Upsert, deterministic keys, temp-file-then-rename, outbox.

**Readers:** cursor = snapshot-consistent, single-threaded, holds a connection · paging = restartable and partitionable, **needs a unique immutable sort key** (non-unique sort = rows duplicated or skipped) · keyset beats `OFFSET`.

**Scaling:** parallel flows (safe) < local partitioning (**the default** - own reader and `ExecutionContext` per partition) < remote partitioning (metadata only) < remote chunking (ships items; only when processing ≫ reading). Multi-threaded step breaks restartability.

**`JobInstanceAlreadyCompleteException`** = this instance already succeeded → add an identifying parameter, mark one non-identifying, `allowStartIfComplete` on idempotent steps, or `RunIdIncrementer` (which throws away duplicate-run protection).

**Batch 5:** `@EnableBatchProcessing` no longer needed and **switches Boot's auto-config off** · no `JobBuilderFactory`/`StepBuilderFactory` → `new JobBuilder(name, jobRepository)` · typed `JobParameters` · Jakarta · schema changed, `initialize-schema: never` in production.

**Run as a Kubernetes `Job`** - own limits, own restart policy, visible failure, no leaked state. Wire the exit code: `System.exit(SpringApplication.exit(ctx, ...))`.

**Test:** `@SpringBatchTest` + `JobLauncherTestUtils.launchJob/launchStep`. Two tests that matter: **restart mid-way**, and **run twice, assert identical end state**.

---

## Non-relational Spring Data

**Mongo:** `MongoTemplate` for aggregation, bulk ops, `findAndModify`, partial `$set`/`$inc` (a repository `save()` rewrites the whole document and loses concurrent field updates). Aggregation: `$match` first and indexed, 100 MB per stage without `allowDiskUse`.

**Embed vs reference:** embed if owned, read together and **bounded**. Unbounded array → relocation on every update, multi-key index blowup, 16 MB hard wall. Fixes: subset pattern, bucket pattern. "A few" without a stated upper bound = reference.

**Mongo transactions** need a replica set (never standalone - the classic works-in-Testcontainers failure), 60s default limit. Prefer single-document atomicity + outbox. Frequent multi-document ACID = the data is relational.

**Elasticsearch is not a source of record:** near-real-time (refresh gap), no multi-document transactions, mappings are immutable. Write to the DB → outbox/CDC → indexer → ES. Rebuildable index makes a mapping change routine.

**Zero-downtime reindex:** always read/write through an **alias** → build `v2` → backfill + catch up → atomic alias swap → keep `v1` for rollback.

**Two stores in one app:** separate packages, store-specific base interfaces, explicit `@EnableJpaRepositories(basePackages=)` / `@EnableMongoRepositories(basePackages=)`. Otherwise both scanners claim the interface. `@Transactional` spans **one** manager.

**Redis repositories:** `@RedisHash` + `@TimeToLive`; phantom copy + keyspace notifications (`notify-keyspace-events Ex`) clean up `@Indexed` secondary index sets - not enabled = leaked index entries.

**Spring Session:** `SessionRepositoryFilter` must run **before** the security chain (Boot orders it; hand-registering breaks it). Buys stateless instances; costs a Redis round trip per request and "Redis down = nobody logged in". Keep the session tiny.

---

## DevTools

Two classloaders (base jars + restart loader for your classes) → fast restart. **Never in production:** the remote tunnel (`spring.devtools.remote.secret`) loads class bytes over the wire = RCE; caching disabled; two loaders break `instanceof` and identity. Boot disables it from a packaged jar and marks it `developmentOnly` - fail the build if it appears in the production tree.

**Better dev loop (3.1+):** `spring-boot-docker-compose` and `@ServiceConnection` + Testcontainers at development time. The friction was never restart speed, it was standing up the dependencies.

---

## Spring AI and MCP

```
ChatClient   ← advisors, prompt templates, entity(), tool callbacks, memory   (features)
   ↓
ChatModel / EmbeddingModel / ImageModel   ← portable port, call + stream       (platform code)
```

Go direct to the model for: custom advisors, bulk embedding with rate limiting, and test stubs (one-method interface, no mock needed).

**Portability breaks at:** provider-specific `ChatOptions` (response format, seed, thinking budget, guardrails), **prompts** (a prompt tuned on one model regresses on another), tool-schema strictness, native JSON mode vs instruct-and-parse, token accounting and error taxonomies. Structural portability is real; behavioral portability is not - keep an evaluation suite and run it before any switch.

**ETL:** reader → `TokenTextSplitter` → metadata enrichment → `VectorStore.add()`. Chunk size/overlap and metadata drive retrieval quality more than the model does. **Reindex** by writing `version: v3` alongside `v2`, keeping the filter on `v2`, evaluating, then flipping the filter. A new embedding model always means a full reindex - vectors from different models are not comparable.

**MCP:** tools + resources + prompts over JSON-RPC. `spring-ai-starter-mcp-client` → `ToolCallbackProvider` → same tool-calling path. Transports: **stdio** (child process - local/CLI only, never a multi-pod deployment) and **HTTP/SSE** (streamable HTTP). `tools/list` at connect, so **the tool surface is defined by a remote party and can change without your release** - pin versions, diff the listing in CI.

**In-process tool vs MCP server:** start in-process (method call, security context present, trivially testable); extract to MCP when a second consumer appears or another team owns it. Security: tool arguments are **untrusted input** (a prompt-injected document chooses them) - tenant from `SecurityContext`, never from an argument; and a remote server's tool *descriptions* reach the model's context, which is an injection surface with no in-process equivalent.

---

## Boot 2 → 3 migration order

1. Java 17 + Boot 2.7.x latest, fix all deprecation warnings
2. Inventory dependencies for Jakarta compatibility (**the long pole**)
3. `javax.*` → `jakarta.*`
4. Spring Security 5 → 6 (runtime failures - test matrix required)
5. Property renames → `spring-boot-properties-migrator` for one release
6. `spring.factories` → `AutoConfiguration.imports` (silently contributes nothing otherwise)
7. Sleuth → Micrometer Tracing (B3 → W3C)
8. Hibernate 5 → 6 (ID generation and naming strategy defaults)
9. Trailing-slash matching removed

Automate with **OpenRewrite**, then review the diff.

---

## Answer-shaping reminders

- Name the **mechanism**, not just the behavior. "Self-invocation does not cross the proxy" beats "you need a separate bean".
- Every Spring surprise reduces to one of: **the proxy boundary**, **what is bound to the thread**, or **startup versus runtime**.
- State the **default you change and why** - `open-in-view`, `SimpleAsyncTaskExecutor`, Actuator exposure, Hikari `max-lifetime`.
- For every design answer: clarify first, then name the trade-off you accepted and what would change your mind.
- Attach a **number** wherever you can - pool size, timeout, p99, series count, startup seconds.
