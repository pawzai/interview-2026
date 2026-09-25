# Spring Interview Questions

Questions are numbered continuously (`Q1`, `Q2`, ...) so that [answers.md](answers.md) can reference them directly.

Difficulty legend:

- `[C]` Core - you must answer this instantly and correctly.
- `[D]` Deep - expected of a senior engineer, requires mechanism-level detail.
- `[T]` Tricky - designed to catch you out; the obvious answer is usually wrong.
- `[A]` Architect - no single right answer, judged on trade-off reasoning.

Each category opens with an **Assumed known** line pointing at the `01-java` questions this material builds on. If those are shaky, go back before continuing.

---

## 1. Container internals

> Assumed known: `01-java` Q110-114 (dependency injection, bean lifecycle, scopes) and Q118 (proxy types).

1. `[C]` Walk through `AbstractApplicationContext.refresh()` phase by phase. In which phase are AOP proxies created?
2. `[D]` What is a `BeanDefinition` and how does it differ from a bean instance? Who is allowed to modify one?
3. `[T]` `BeanFactoryPostProcessor` versus `BeanPostProcessor` - when does each run, and why does injecting a normal dependency into a `BeanFactoryPostProcessor` produce the "is not eligible for getting processed by all BeanPostProcessors" warning?
4. `[T]` `@Configuration` full mode versus lite mode. What does `proxyBeanMethods = false` actually change, and when is it unsafe?
5. `[D]` How does calling one `@Bean` method from another return the same singleton instead of a new object?
6. `[D]` `FactoryBean<T>` - how does it differ from a `@Bean` factory method, and how do you retrieve the `FactoryBean` itself rather than its product?
7. `[T]` `ObjectProvider` versus `@Lazy` versus `ApplicationContext.getBean()` for deferred lookup. Which do you use and why?
8. `[D]` Explain the three-level singleton cache and how it resolves a circular reference.
9. `[T]` `@Lazy` breaks a constructor injection cycle - what is actually injected, and what are the consequences?
10. `[D]` `@Order`, `Ordered`, `@Priority` and `@DependsOn` - what does each one actually control?
11. `[T]` You inject `List<PaymentHandler>`. In what order do the beans arrive, and how do you make that deterministic?
12. `[C]` `@Primary` versus `@Qualifier` versus bean-name matching - what is the resolution order when several candidates exist?
13. `[D]` How does injection by generic type (`Repository<Order>`) work despite type erasure?
14. `[D]` `ImportSelector` versus `DeferredImportSelector` versus `ImportBeanDefinitionRegistrar` - give a use case for each.
15. `[D]` How does the `@Enable*` annotation pattern work under the hood?
16. `[C]` `InitializingBean`, `@PostConstruct`, `SmartInitializingSingleton` and `SmartLifecycle` - when do you need each?
17. `[T]` Why does a `@PostConstruct` method that calls a `@Transactional` or `@Async` method on itself silently do nothing?
18. `[D]` `ApplicationListener` versus `@EventListener` - ordering, exception behavior, and the built-in context events.
19. `[D]` `@TransactionalEventListener` phases: `BEFORE_COMMIT`, `AFTER_COMMIT`, `AFTER_ROLLBACK`, `AFTER_COMPLETION`. Which would you use to publish to Kafka?
20. `[T]` Application events are synchronous by default. What breaks when you make them asynchronous, and what must you propagate?
21. `[D]` The `Aware` interfaces - which exist, and when is using one legitimate rather than a smell?
22. `[D]` `Environment`, `PropertySource` and `PropertySourcesPlaceholderConfigurer` - how does `${}` resolution actually happen?
23. `[D]` Custom scopes - how do you register one, and what does `SimpleThreadScope` not do that you might expect?
24. `[T]` What does a scoped proxy actually inject into a singleton, and what happens if you call it outside its scope?
25. `[D]` `BeanFactory` versus `ApplicationContext` - is the distinction still meaningful in 2026?
26. `[A]` How would you diagnose "bean X is not eligible for auto-proxying" warnings, and why do they matter?

---

## 2. Configuration, properties and profiles

> Assumed known: `01-java` Q115-116 (auto-configuration, `@Conditional`) and Q126 (configuration precedence).

27. `[D]` The `ConfigData` API introduced in Boot 2.4 replaced `ConfigFileApplicationListener`. What changed about how profile-specific documents are loaded?
28. `[T]` Boot 2.4 forbade `spring.profiles.active` inside a profile-specific document and changed override ordering. What breaks on upgrade and how do you fix it?
29. `[D]` `spring.config.import` - how do you load configuration from AWS Parameter Store, Secrets Manager or Vault, and how do you make an import mandatory?
30. `[D]` Relaxed binding - which property forms all bind to `myApp.connectionTimeout`, and which does the environment variable use?
31. `[C]` `@ConfigurationProperties` versus `@Value` - binding, validation, immutability with constructor binding and records.
32. `[T]` Why does `@Value` fail to bind a YAML list without SpEL, and why does `@Value` inside a `@ConfigurationProperties` class not behave as people expect?
33. `[D]` How do you validate configuration at startup so a misconfigured service fails immediately rather than at first request?
34. `[D]` `@ConfigurationPropertiesBinding` and custom converters - when do you need one?
35. `[D]` Profile groups and `@Profile` expressions. Why are profile-conditional *beans* risky?
36. `[T]` `spring.profiles.active` versus `spring.profiles.include` versus profile groups - what is the precedence, and which is additive?
37. `[D]` What is `spring-configuration-metadata.json` and why must a shared starter generate it?
38. `[D]` `@RefreshScope` - the mechanism, and what it does *not* refresh.
39. `[D]` SpEL - where is it evaluated, what can it reach, and what is the injection risk if user input reaches an expression?
40. `[T]` `${...}` versus `#{...}` - when is each resolved, and can they be nested?
41. `[D]` How do you externalize secrets so they never appear in `/actuator/env`, a heap dump, or a log line?
42. `[A]` How do you manage configuration across 40 services without copy-paste drift?

---

## 3. AOP and proxies

> Assumed known: `01-java` Q118-119 (JDK versus CGLIB, self-invocation).

43. `[D]` Which post-processor creates AOP proxies, how does it find advisors, and at what point in `refresh()` does it run?
44. `[D]` Pointcut designators: `execution`, `within`, `@annotation`, `bean`, `args`, `this`, `target`. Give a realistic expression.
45. `[T]` `this()` versus `target()` in a pointcut - why do they behave differently under a JDK proxy?
46. `[C]` Advice types and the exact order in which they execute around a join point.
47. `[T]` Two aspects match the same method. What determines which wraps which, and what is the default if you say nothing?
48. `[T]` A method annotated with `@Transactional`, `@Async` and `@Cacheable` - what is the actual invocation order, and what goes wrong?
49. `[D]` Where does `@Transactional` sit in the advisor order by default, and when would you change it?
50. `[C]` Self-invocation defeats the proxy. List every Spring annotation this silently disables.
51. `[D]` AspectJ compile-time and load-time weaving - what do they enable that Spring AOP cannot, and what do they cost?
52. `[D]` `@Cacheable`, `@CachePut`, `@CacheEvict` - key generation, `condition` versus `unless`, and `sync = true`.
53. `[T]` `@Cacheable` on a method returning `Optional` or `CompletableFuture` - what is actually stored in the cache?
54. `[T]` Does `@Cacheable` cache a `null` return? Does it cache when the method throws?
55. `[D]` Backing the cache abstraction with Redis - serialization, per-cache TTL, and handling a cache stampede.
56. `[D]` Spring Retry - `@Retryable` and its interaction with transactions and idempotency.
57. `[D]` `@Validated` on a class versus `@Valid` on a parameter - which one is AOP, and which exception does each produce?
58. `[A]` When do you write an aspect rather than a decorator or an explicit call?

---

## 4. Transactions in depth

> Assumed known: `01-java` Q119-122 (self-invocation, propagation, rollback rules, isolation).

59. `[C]` What does `PlatformTransactionManager.getTransaction()` actually do, and how does `TransactionStatus` carry state?
60. `[D]` `TransactionSynchronizationManager` - what is bound to the thread, and how does the `EntityManager` or `Connection` find it?
61. `[D]` `TransactionSynchronization` callbacks - `beforeCommit`, `afterCommit`, `afterCompletion`. Give a real use for each.
62. `[T]` Why can you not reliably write to the database inside `afterCommit`, and what happens if you try?
63. `[D]` `TransactionTemplate` - when is programmatic transaction management genuinely better than declarative?
64. `[T]` `@Transactional(readOnly = true)` - what does it do at the JDBC driver, Hibernate and read-replica routing levels? What does it *not* prevent?
65. `[T]` A transaction is opened but no query runs. What did that cost, and what does `LazyConnectionDataSourceProxy` fix?
66. `[D]` With two `DataSource`s, how does Spring choose the transaction manager, and what fails silently if you get it wrong?
67. `[T]` `ChainedTransactionManager` is deprecated. Why was it dangerous, and what do you do instead?
68. `[D]` JTA and XA - when is it justified in 2026, and what does it cost?
69. `[D]` Transaction timeout - who enforces it, and which operations does it fail to interrupt?
70. `[T]` `UnexpectedRollbackException` - describe the exact sequence of calls that produces it.
71. `[T]` `REQUIRES_NEW` invoked inside a transaction holding a row lock - explain the self-deadlock and how to avoid it.
72. `[D]` `NESTED` propagation and savepoints - which transaction managers support it, and when is it the right answer?
73. `[C]` Rollback rules with a custom exception hierarchy, and when `noRollbackFor` is legitimate.
74. `[T]` You catch an exception inside a transactional method and return normally. When does the transaction still roll back?
75. `[D]` Flush timing and `FlushMode` - why does a query sometimes trigger a flush you did not ask for?
76. `[T]` A `@Transactional` method makes an HTTP call. Why is this a design smell, and what exactly does it cost?
77. `[D]` What does an `@Async` method inherit from the caller's transaction, and what must you do instead?
78. `[D]` Reactive transactions - `ReactiveTransactionManager` and `TransactionalOperator`. Why can the context not be thread-bound here?
79. `[D]` Implementing the transactional outbox in Spring - an events table versus `@TransactionalEventListener`. Which is safe?
80. `[A]` How would you enforce, across a large codebase, that no HTTP call happens inside a transaction?

---

## 5. Spring MVC internals

> Assumed known: `01-java` Q130-131 (MVC versus WebFlux, HTTP clients) and Q167 (REST design).

81. `[C]` Trace a request through `DispatcherServlet`. Which components run, in which order?
82. `[D]` `HandlerMapping` and `HandlerAdapter` - how is a `@RequestMapping` method matched and then invoked?
83. `[D]` `HandlerMethodArgumentResolver` - name three built-ins and describe when you would write your own.
84. `[D]` How is an `HttpMessageConverter` selected, and what is the correct way to customize Jackson in Boot?
85. `[T]` Why does `@RequestBody` binding to an abstract type or interface fail, and how do you handle polymorphic JSON without opening a deserialization hole?
86. `[D]` Content negotiation - `Accept` header, path extension and request parameter. What changed in recent Boot versions and why?
87. `[C]` `Filter` versus `HandlerInterceptor` versus `@ControllerAdvice` versus AOP - order of execution and what each can see.
88. `[T]` Why can a servlet `Filter` not know which handler method will run, and what runs before Spring Security in the chain?
89. `[D]` `@ControllerAdvice` - how are `@ExceptionHandler` methods resolved when several match, and what does `ResponseEntityExceptionHandler` give you?
90. `[D]` `ProblemDetail` and RFC 9457 support in Spring 6 - how do you adopt it consistently across a service?
91. `[T]` Why does an exception thrown inside a `Filter` bypass `@ControllerAdvice`, and how do you handle it?
92. `[D]` `@Valid` versus `@Validated`, validation groups, and the difference between `MethodArgumentNotValidException` and `ConstraintViolationException`.
93. `[D]` `WebMvcConfigurer` versus `@EnableWebMvc` - why does the latter disable Boot's MVC auto-configuration?
94. `[D]` Async MVC - `Callable`, `DeferredResult`, `WebAsyncTask` and `StreamingResponseBody`. Which thread serves which phase?
95. `[T]` During async MVC dispatch, what happens to the `SecurityContext`, the MDC and request-scoped beans?
96. `[D]` `SseEmitter` - timeouts, error handling, and how you capacity-plan for open connections.
97. `[D]` `RestClient` versus `WebClient` versus `RestTemplate` in Spring 6.1, and declarative `@HttpExchange` clients.
98. `[D]` HTTP caching - `ETag`, `ShallowEtagHeaderFilter` and `Cache-Control`. What does the shallow filter save and what does it not?
99. `[D]` Multipart handling, size limits, and streaming a large upload without buffering it in memory.
100. `[D]` How does a 404 for an unmapped URL differ from an exception thrown inside a handler, and how do you handle both consistently?
101. `[T]` Tomcat thread pool sizing versus virtual threads in Boot 3.2+ - what actually changes, and what stays exactly the same?
102. `[A]` How do you version and evolve a REST API in Spring without forking controllers for every version?

---

## 6. Reactive Spring and WebFlux

> Assumed known: `01-java` Q130 (MVC versus WebFlux) and Q79 (virtual threads).

103. `[C]` `Mono` and `Flux` - cold versus hot publishers, and what "nothing happens until you subscribe" means in practice.
104. `[T]` You call a `WebClient` method and never subscribe. What happens, and how do you catch this in review?
105. `[D]` Backpressure - what `request(n)` means, and what `onBackpressureBuffer`, `Drop` and `Latest` each do.
106. `[D]` Schedulers - `parallel`, `boundedElastic`, `single`, `immediate`. What belongs on each?
107. `[T]` `publishOn` versus `subscribeOn` - where in the chain does each take effect?
108. `[T]` One blocking call inside a WebFlux handler - describe exactly what happens and how you detect it in CI.
109. `[D]` Reactor `Context` - why does `ThreadLocal` fail, and how do MDC and the security context propagate?
110. `[D]` `flatMap` versus `concatMap` versus `flatMapSequential` - ordering and concurrency differences.
111. `[T]` Why does `flatMap` with default concurrency overwhelm a downstream service, and how do you bound it?
112. `[D]` Error handling - `onErrorResume`, `onErrorReturn`, `onErrorContinue` and `retryWhen` with backoff. Which is a trap?
113. `[D]` `WebClient` configuration - connection pool sizing, timeouts, and what `PrematureCloseException` usually means.
114. `[D]` R2DBC versus JDBC - what you gain and what you give up.
115. `[D]` Reactive transactions with `TransactionalOperator` - how does the boundary differ from the servlet model?
116. `[D]` Testing with `StepVerifier` and `VirtualTimeScheduler`.
117. `[D]` `WebFilter` and reactive Spring Security - how does the chain differ from the servlet filter chain?
118. `[T]` Why does `SecurityContextHolder` return nothing in a WebFlux handler, and what do you use instead?
119. `[A]` WebFlux versus MVC on virtual threads in 2026 - what do you recommend, and what conditions change your answer?
120. `[A]` You inherit a WebFlux service the team cannot debug or maintain. What do you do?

---

## 7. Spring Data in depth

> Assumed known: `01-java` Q150-161 (JPA lifecycle, N+1, lazy loading, locking, pagination, Hikari).

121. `[C]` How does a repository *interface* become a working bean? Which proxy and which factory are involved?
122. `[C]` Query derivation from method names - the parsing rules, and where the approach breaks down.
123. `[T]` A finder returning `Optional`, `Stream`, `Page`, `Slice` or `List` - what changes in the SQL issued and in the transaction required?
124. `[D]` Projections - interface-based, class/DTO-based, dynamic and nested. Which actually narrow the SQL?
125. `[T]` Why can an interface projection with a nested projection still load the full entity graph?
126. `[D]` `Specification` and the Criteria API - composing dynamic queries without string building.
127. `[D]` Querydsl versus Specifications versus a hand-written `@Query`. How do you choose?
128. `[T]` `@Modifying` - why do you need `clearAutomatically` and `flushAutomatically`, and what stale state appears without them?
129. `[D]` `@Query` with JPQL versus native SQL - pagination, sorting and when you must supply a `countQuery`.
130. `[T]` Sorting a native query by a user-supplied column name - what is the risk and what is the correct handling?
131. `[D]` Custom repository fragments - composing behavior without an abstract base class.
132. `[D]` Auditing - `@CreatedBy`, `@LastModifiedDate` and `AuditorAware`. How does it behave for async or system-initiated writes?
133. `[D]` Optimistic locking through Spring Data - handling `OptimisticLockingFailureException` and retrying safely.
134. `[D]` Streaming a large result set with `Stream<T>` - what does it require from the transaction, the connection and the fetch size?
135. `[T]` Why does returning `Page` cost an extra query, and when should you use `Slice` or keyset pagination instead?
136. `[D]` `@EntityGraph` on a repository method - how does it interact with pagination and with `JOIN FETCH`?
137. `[D]` Configuring two data sources - two `EntityManagerFactory` beans, `@EnableJpaRepositories` and the transaction manager wiring.
138. `[D]` Spring Data JDBC versus JPA - the aggregate model, no lazy loading, no dirty checking. When is it the better choice?
139. `[D]` `JdbcClient` and `JdbcTemplate` - when do you drop down to them, and how do you batch efficiently?
140. `[D]` Spring Data Redis - template configuration, serializer choice, and using Redis as a cache versus as a store of record.
141. `[T]` Why does `save()` on a new entity with an assigned (non-generated) ID issue a `SELECT` first, and how do you avoid it?
142. `[A]` How do you stop a repository layer from growing into 200 bespoke query methods?

---

## 8. Spring Security architecture

> Assumed known: `01-java` Q132-134, Q141-143 (filter chain, authentication components, CSRF, CORS, method security basics).

143. `[C]` The `SecurityFilterChain` bean DSL - how are multiple chains selected and ordered?
144. `[T]` You define two chains and the first has no `securityMatcher`. What happens to the second, and why?
145. `[D]` `AuthorizationManager` - the Spring Security 6 authorization model. What did it replace, and why?
146. `[D]` `authorizeHttpRequests` versus the removed `authorizeRequests` - what changed semantically, not just in name?
147. `[D]` A custom `AuthenticationProvider` versus a custom filter - which do you write for which problem?
148. `[D]` `SecurityContextRepository` and the Spring Security 6 change that requires explicit saving.
149. `[T]` After upgrading to Security 6, authentication succeeds but the user is anonymous on the next request. What is the cause?
150. `[D]` Session fixation protection strategies and session concurrency control.
151. `[D]` `SecurityContextHolder` strategies - thread-local, inheritable thread-local and global. When would you change the default?
152. `[T]` The security context is lost inside an `@Async` method. Why, and what are the fixes?
153. `[T]` How does security context propagation differ between a `ThreadPoolTaskExecutor` and virtual threads?
154. `[D]` `@EnableMethodSecurity` in 6.x - what changed from `@EnableGlobalMethodSecurity`, and how does `@AuthenticationPrincipal` resolve?
155. `[D]` Adding custom SpEL functions to `@PreAuthorize` via a `MethodSecurityExpressionHandler`.
156. `[T]` Does `@PreAuthorize` work on a method returning a `Stream` or a reactive type? What about `@PostAuthorize`?
157. `[D]` Domain object security and ACLs - when is that machinery justified over a simple tenant predicate?
158. `[D]` Security headers in the DSL - HSTS, CSP, frame options, referrer policy. Which do you always set?
159. `[D]` CSRF for a single-page application - `CookieCsrfTokenRepository` and the BREACH protection handler.
160. `[T]` After upgrading to Security 6, CSRF fails for a SPA. Explain the deferred token loading issue and the fix.
161. `[D]` `StrictHttpFirewall` and `RequestRejectedException` - why do legitimate-looking URLs get rejected?
162. `[D]` Securing Actuator - a separate filter chain, a management port, and what you expose to whom.
163. `[D]` Testing security - `@WithMockUser`, a custom `@WithSecurityContext`, and `SecurityMockMvcRequestPostProcessors`.
164. `[T]` Why might a `@WebMvcTest` pass authorization checks that fail in production, or skip them entirely?
165. `[D]` Password encoder upgrades in place - `DelegatingPasswordEncoder` and `UserDetailsPasswordService`.
166. `[A]` How do you roll out a breaking security change across 40 services without an outage?

---

## 9. OAuth2, OIDC and Authorization Server

> Assumed known: `01-java` Q135-140 (JWT revocation, refresh tokens, grant types, OIDC, PKCE, token storage).

167. `[D]` Configuring a resource server with `issuer-uri` - what does Spring fetch at startup, and which validations does it perform by default?
168. `[C]` JWT validation - signature, issuer, audience and expiry. How do you add a custom validator?
169. `[T]` Where do JWT claims become granted authorities, and why does `hasRole('ADMIN')` fail out of the box with a Keycloak or Cognito token?
170. `[D]` Opaque token introspection versus local JWT validation - when do you choose introspection, and what must you cache?
171. `[D]` `OAuth2AuthorizedClientManager` - how do you make an authenticated machine-to-machine call with client credentials?
172. `[D]` Token relay through a gateway - propagating the user's token versus performing a token exchange.
173. `[D]` `oauth2Login` versus `oauth2ResourceServer` versus `oauth2Client` - three different roles in one framework.
174. `[D]` Spring Authorization Server - when do you run your own rather than using Keycloak, Cognito or Okta?
175. `[D]` JWKS and key rotation - what is cached, for how long, and what happens during a rotation?
176. `[D]` Customizing token claims in Spring Authorization Server, and why you keep tokens small.
177. `[T]` Refresh token rotation and reuse detection - what does the framework give you, and what must you implement?
178. `[D]` A multi-tenant resource server accepting tokens from several issuers - `JwtIssuerAuthenticationManagerResolver`.
179. `[D]` OIDC logout - `OidcClientInitiatedLogoutSuccessHandler`, and what back-channel logout solves.
180. `[D]` Propagating the authenticated principal across async, reactive and messaging boundaries.
181. `[T]` A token works in Postman but the service returns 401 with no useful detail. How do you diagnose it?
182. `[A]` Design authentication for a system with a web SPA, a mobile app, partner APIs and internal service-to-service calls.

---

## 10. Spring Boot production engineering

> Assumed known: `01-java` Q115-116 (auto-configuration), Q127 (Actuator), Q203-207 (containers, probes, observability).

183. `[C]` Write an auto-configuration and a starter - which files, which conditions, what ordering, and what metadata?
184. `[T]` Why must your auto-configuration back off with `@ConditionalOnMissingBean`, and why does evaluation order matter so much?
185. `[D]` `AutoConfiguration.imports` versus `spring.factories` - what changed in Boot 2.7 and 3, and why?
186. `[D]` A custom Actuator endpoint - `@Endpoint`, `@ReadOperation`, exposure and securing it.
187. `[D]` Custom `HealthIndicator` and health groups for Kubernetes liveness and readiness probes.
188. `[T]` Which dependency failures belong in readiness and which do not? Describe the outage caused by getting this wrong.
189. `[D]` Graceful shutdown - what `server.shutdown=graceful` covers, the lifecycle timeout, and what else must drain.
190. `[C]` Micrometer meter types - `Counter`, `Timer`, `Gauge`, `DistributionSummary`. When do you need percentiles versus a histogram?
191. `[T]` Why does tagging a metric with a user ID, order ID or raw URL path take down your metrics backend?
192. `[D]` The Micrometer Observation API and `@Observed` - what does it unify?
193. `[D]` Micrometer Tracing - propagation, sampling and baggage. What replaced Spring Cloud Sleuth?
194. `[D]` `BufferingApplicationStartup` - how do you find what makes startup slow?
195. `[D]` `spring.main.lazy-initialization` - what it buys you and what it hides.
196. `[D]` Spring AOT processing - what happens at build time, and what dynamic behavior can no longer work?
197. `[T]` GraalVM native image - which Spring features break, and how do you register reflection hints?
198. `[D]` Class Data Sharing and Project CRaC - startup improvements short of a native image.
199. `[D]` Layered jars, buildpacks and `bootBuildImage` - how do you optimize a Spring image?
200. `[D]` Boot's `TaskExecutor` auto-configuration - what changed in 3.2 with virtual threads, and how should `@Async` be configured now?
201. `[D]` Structured JSON logging in Boot 3.4, externalized logging configuration, and correlation IDs.
202. `[T]` Why can `/actuator/env` and `/actuator/configprops` still leak secrets despite sanitization, and what do you do about it?
203. `[D]` Boot's `DataSource` and HikariCP auto-configuration - which defaults must you override in production?
204. `[A]` How do you build a platform starter that 40 teams depend on without becoming their bottleneck?

---

## 11. Spring Cloud and microservices

> Assumed known: `01-java` Q165-181 (service boundaries, saga, outbox, Kafka, resilience, rate limiting).

205. `[D]` Spring Cloud Config Server - refresh, encryption, and why many teams moved to ConfigMaps or Parameter Store instead.
206. `[D]` `@RefreshScope` - the proxy mechanism, and which beans it cannot refresh.
207. `[D]` Spring Cloud Gateway - route predicates, filters and global filters. Why is it built on WebFlux?
208. `[T]` Why must you never make a blocking call inside a Gateway filter, and what is the symptom when someone does?
209. `[D]` Gateway rate limiting with Redis - the token bucket parameters and writing a `KeyResolver`.
210. `[C]` Resilience4j with Spring Boot - `@CircuitBreaker`, `@Retry`, `@Bulkhead`, and the aspect ordering between them.
211. `[D]` OpenFeign - declarative clients, error decoding, and integration with Resilience4j and tracing.
212. `[T]` A Feign call made from inside a `@Transactional` method - what is the failure mode under load?
213. `[D]` Spring Cloud LoadBalancer after Ribbon - client-side balancing, instance health and caching.
214. `[D]` Spring Cloud Stream - binders, the functional programming model, error channels and DLQ configuration.
215. `[D]` Spring for Apache Kafka - `@KafkaListener`, container concurrency, acknowledgment modes, `DefaultErrorHandler` and retry topics.
216. `[T]` A `@KafkaListener` method annotated `@Transactional` - which transaction is that, and how do you actually get atomicity with the database?
217. `[D]` `@Scheduled` runs on every instance. Compare ShedLock, a database lock and leader election.
218. `[D]` Spring Cloud AWS - `spring.config.import` for Parameter Store and Secrets Manager, and SQS listeners.
219. `[D]` Spring Cloud Contract - the producer and consumer sides, and where it fits relative to integration tests.
220. `[A]` Which Spring Cloud components would you deliberately not adopt when running on Kubernetes, and why?

---

## 12. Testing Spring applications

> Assumed known: `01-java` Q128-129 (test pyramid, `@MockBean` and context caching).

221. `[D]` The test context cache - what forms the cache key, and how do you keep the number of contexts small?
222. `[T]` Which annotations silently create a new application context, and how do you measure how many your suite creates?
223. `[C]` The test slice catalogue - which slice for which layer, and what each one deliberately does not load.
224. `[D]` `@TestConfiguration` versus `@Configuration` in tests, and when you need `@Import`.
225. `[D]` `@MockBean` versus `@MockitoBean` (Spring 6.2) versus plain constructor-injected Mockito.
226. `[D]` `@DynamicPropertySource` versus `@TestPropertySource` versus an `ApplicationContextInitializer`.
227. `[D]` Testcontainers with `@ServiceConnection` (Boot 3.1) and container reuse - how much boilerplate does it remove?
228. `[T]` Why do `@Transactional` tests pass while production fails? List the specific things such a test cannot see.
229. `[D]` `MockMvc` versus `WebTestClient` versus `TestRestTemplate` versus `@SpringBootTest(webEnvironment = RANDOM_PORT)`.
230. `[T]` Which classes of bug does `MockMvc` structurally fail to catch?
231. `[D]` Testing scheduled jobs, async methods and eventual behavior without `Thread.sleep`.
232. `[D]` Testing Kafka or SQS consumers - embedded broker, Testcontainers, or a contract? Which and when?
233. `[D]` ArchUnit for enforcing layering, package boundaries and Spring conventions.
234. `[D]` Causes of flaky tests specific to Spring, and how you eliminate each.
235. `[D]` A `@SpringBootTest` suite takes 25 minutes. Walk through how you get it under ten.
236. `[A]` Define the test strategy you would mandate for a new Spring service.

---

## 13. Spring AI

> Assumed known: `01-java` Q211-220 (LLM architecture, RAG, embeddings, cost, prompt injection, evaluation).

237. `[C]` The `ChatClient` fluent API - system and user messages, options, and where prompts should actually live.
238. `[D]` Advisors - what problem do they solve, and which are built in?
239. `[D]` Structured output with `entity()` - how does it work, and what happens when the model returns invalid JSON?
240. `[D]` Tool calling in Spring AI - registration, execution and the security boundary you must enforce.
241. `[D]` The `VectorStore` abstraction, document readers, splitters and metadata filters.
242. `[D]` `QuestionAnswerAdvisor` and RAG wiring - what does it give you, and what must you still build yourself?
243. `[D]` Chat memory options - and why unbounded conversation history is a cost defect, not a feature.
244. `[D]` Observability and cost attribution for AI calls in a Spring service.
245. `[T]` How do you test and evaluate a Spring AI feature when the output is non-deterministic?
246. `[A]` Would you adopt Spring AI or wrap the provider SDK behind your own interface? Justify it.

---

## 14. Architecture, modularity and migration

> Assumed known: `01-java` Q108-109 (hexagonal, DDD) and Q165-166 (service boundaries, monolith versus microservices).

247. `[D]` Spring Modulith - what does it enforce, and how does it verify module boundaries at build time?
248. `[D]` Modulith application events and the event publication registry - how does this relate to the transactional outbox?
249. `[D]` Hexagonal architecture with Spring - where do annotations belong, and how do you keep the domain framework-free?
250. `[D]` A multi-module Maven or Gradle layout for a Spring service - what belongs in each module?
251. `[C]` Boot 2 to Boot 3 migration - give the full checklist in order.
252. `[T]` The Jakarta namespace migration - which third-party libraries break, and how do you find them before runtime?
253. `[T]` Spring Security 5 to 6 - which breaking changes fail at runtime rather than at compile time?
254. `[D]` Property renames and removed configuration between Boot 2 and 3 - how do you catch them automatically?
255. `[D]` Dependency management - the Boot BOM, and how to override a managed version safely.
256. `[D]` Upgrade cadence and support windows - how do you plan Spring upgrades as ongoing work rather than a project?
257. `[D]` Versioning and deprecating a shared starter used by many teams.
258. `[A]` Design the module structure and shared platform for a new 30-engineer Spring estate.
259. `[A]` Design a modular monolith in Spring that can be split into services later without a rewrite.
260. `[A]` Design multi-tenancy in a Spring Boot application end to end.
261. `[A]` Design an idempotent, fully observable Kafka consumer service in Spring.
262. `[A]` Plan a Boot 2.7 to Boot 3 migration across 40 services.

---

## 15. Web protocols beyond REST

> Assumed known: `01-java` Q130-131 (MVC versus WebFlux, HTTP clients) and Q96 above (`SseEmitter`).

263. `[C]` STOMP over WebSocket in Spring - what does the handshake look like, and what does the simple broker actually do?
264. `[D]` `@MessageMapping`, `@SendTo` and `SimpMessagingTemplate` - how does a message reach one specific user rather than everyone?
265. `[T]` Your WebSocket application works on one instance and breaks on three. Explain why, and what a broker relay changes.
266. `[D]` Authenticating a WebSocket connection - at the HTTP handshake or per STOMP frame? What is available in each case?
267. `[T]` WebSocket versus SSE versus long polling - which do you choose, and what does a load balancer, proxy or corporate firewall do to each?
268. `[D]` Spring HATEOAS - `RepresentationModel`, `EntityModel`, `Link` and the HAL media type. What does an assembler give you?
269. `[A]` When does hypermedia genuinely earn its cost, and why do most REST APIs stop at level 2 of the Richardson model?
270. `[T]` CORS in Spring - `@CrossOrigin`, `CorsConfigurationSource`, `WebMvcConfigurer` and the gateway. Why must Spring Security know about CORS, and what breaks a preflight request?

---

## 16. Messaging endpoints in Spring

> Assumed known: `01-java` Q174-176 (Kafka fundamentals) and Q214-216 above (Spring Cloud Stream, `@KafkaListener`). Broker topology and estate-level integration are in [`03-microservices`](../03-microservices/questions.md) category 15.

271. `[C]` `JmsTemplate` and `@JmsListener` - what does `DefaultMessageListenerContainer` do per message, and how does `concurrency` behave?
272. `[T]` A plain `JmsTemplate` send is far slower than expected. What is it doing on every call, and what does `CachingConnectionFactory` fix?
273. `[D]` `sessionTransacted`, client acknowledge and `@Transactional` on a JMS listener - which of these actually redelivers a failed message?
274. `[D]` Spring AMQP - `RabbitTemplate`, `@RabbitListener`, and how exchanges, queues and bindings get declared. Who should own the declarations?
275. `[T]` Publisher confirms versus publisher returns in RabbitMQ - what does each detect, and which failure does neither catch?
276. `[D]` RabbitMQ acknowledgment modes in Spring AMQP, `DLX` configuration, and retry with `RetryInterceptorBuilder`. Where does the retry actually happen?
277. `[T]` `MessageConverter` and the `__TypeId__` header - why does a producer refactor break consumers, and how do you version a message payload safely?
278. `[D]` Spring Integration - channels, endpoints, the `IntegrationFlow` DSL and the poller. What problem does it solve that plain code does not?
279. `[D]` Spring Web Services - contract-first with `@Endpoint` and `@PayloadRoot`, WSDL generation, and where WS-Security fits. When is SOAP still the right answer in 2026?
280. `[T]` A listener annotated `@Transactional` consumes a message and writes to a database. Which transaction is that, what can still be lost, and what do you do instead?

---

## 17. Spring Batch

> Assumed known: Q217 above (`@Scheduled` across instances) and Q77 (transactions and `@Async`).

281. `[C]` `Job`, `Step`, `JobLauncher`, `JobRepository` and `JobExecution` - how do the pieces fit, and what do the metadata tables store?
282. `[D]` Chunk-oriented processing versus a `Tasklet` - when do you use each, and what is the transaction boundary in a chunk-oriented step?
283. `[T]` A chunk fails on item 7 of 100. What has been committed, what is rolled back, and what does the reader do on restart?
284. `[D]` `ItemReader` choices - `JdbcCursorItemReader` versus `JdbcPagingItemReader` versus a JPA reader. What breaks each one at scale?
285. `[D]` Restartability - `ExecutionContext`, `JobParameters` identity, and `allowStartIfComplete`. Why does re-running a job with the same parameters fail?
286. `[T]` Skip, retry and `noRollback` policies interact. Describe the failure mode of a skip policy combined with a stateful `ItemWriter`.
287. `[D]` Scaling a batch job - multi-threaded step, partitioning, remote chunking and parallel flows. Which are safe with which readers?
288. `[T]` Why must an `ItemWriter` be idempotent even though each chunk is transactional?
289. `[D]` Spring Batch 5 changes - `@EnableBatchProcessing` no longer required, builder APIs requiring a `JobRepository`, and typed `JobParameters`.
290. `[A]` Running batch as a Kubernetes `Job` versus inside a long-lived Boot service - which do you choose, and how do you test either with `JobLauncherTestUtils`?

---

## 18. Non-relational Spring Data and multi-store

> Assumed known: Q121-142 above (Spring Data internals, Redis) and `06-database` for the engine-level material.

291. `[C]` Spring Data MongoDB - `MongoTemplate` versus repositories, and how do you run an aggregation pipeline that a derived query cannot express?
292. `[T]` Embedding versus referencing a Mongo document - what forces the decision, and what breaks when the embedded array grows unbounded?
293. `[D]` Mongo transactions in Spring - what does `MongoTransactionManager` require from the deployment, and what should you do instead most of the time?
294. `[D]` Spring Data Elasticsearch - `ElasticsearchOperations`, index mappings, and reindexing behind an alias with no downtime.
295. `[T]` Why is Elasticsearch a poor source of record, and what is the correct write path when it is your search tier?
296. `[T]` Two stores in one application - JPA and Mongo repositories in the same package. What goes wrong, and how does `@EnableJpaRepositories(basePackages = ...)` fix it?
297. `[D]` `@RedisHash` and Redis repositories versus using Redis as a cache - key expiry semantics, secondary indexes, and Spring Session with Spring Security.

---

## 19. Spring Cloud Kubernetes and the development loop

> Assumed known: Q205-206, Q220 above (Config Server, `@RefreshScope`, what to skip on Kubernetes) and `07-devops` for cluster operations.

298. `[C]` Spring Cloud Kubernetes - how do ConfigMaps and Secrets become a `PropertySource`, and what RBAC does the pod need?
299. `[T]` Config reload modes - `polling` versus `event`, `refresh` versus `restart_context` versus `shutdown`. Which would you enable in production, and why is automatic reload risky?
300. `[D]` `DiscoveryClient` backed by the Kubernetes API versus plain Service DNS - what do you gain, and what does it cost you in permissions and coupling?
301. `[D]` Leader election with Spring Cloud Kubernetes versus ShedLock for `@Scheduled` work. Which failure modes differ?
302. `[T]` Spring Boot DevTools - what does the restart classloader actually do, why must it never reach production, and what replaced it as the better dev loop in Boot 3.1+?

---

## 20. Spring AI platform surface and MCP

> Assumed known: Q237-246 above (`ChatClient`, advisors, RAG, tool calling) and `08-genai` for model behavior.

303. `[C]` `ChatModel`, `EmbeddingModel` and `ImageModel` underneath `ChatClient` - what belongs at each layer, and when do you call the model directly?
304. `[T]` Spring AI claims portability across providers. Where does that break, and what does provider-specific `ChatOptions` do to your abstraction?
305. `[D]` The document ETL pipeline - readers, transformers and writers into a `VectorStore`. How do you reindex without a gap in retrieval?
306. `[D]` Model Context Protocol in Spring AI - client and server starters, the transports, and how tools get discovered at runtime.
307. `[A]` MCP servers versus in-process tool calling - which do you choose for which capability, and what is the security boundary you must enforce for each?

---

## 21. Leadership and platform ownership

These have no model answer on purpose - they must be your own stories from Verizon India and Sonata Software. Use STAR-L and quantify the result.

308. Tell me about a Spring platform decision you made that other teams had to live with.
309. Describe a production incident whose root cause turned out to be a Spring mechanism.
310. How do you keep 40 services on a consistent Spring and Java version?
311. Tell me about a time you removed a framework or component rather than adding one.
312. How do you introduce a major Spring upgrade without stalling feature delivery?
313. Which widely used Spring practice do you consider harmful, and how do you argue against it?
