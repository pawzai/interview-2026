# Spring Interview Preparation Pack

Deep Spring material for **Principal Engineer / Technical Lead / Solution Architect** interviews: container internals, transactions, MVC and WebFlux, Spring Data, Spring Security, Boot production engineering, Spring Cloud, testing, Spring AI, and the Boot 2 to 3 migration.

---

## Read [01-java](../01-java/README.md) first

This pack is deliberately **not** an introduction to Spring. It assumes you have already worked through the Spring material in the Java pack and starts where that stopped.

| Assumed known, from `01-java` | Where this pack takes it |
| --- | --- |
| Q110-114 DI, injection styles, bean lifecycle, scopes | Category 1 - `refresh()` phases, `BeanDefinition`, post-processor ordering, `@Configuration` lite versus full mode |
| Q115-117 auto-configuration, `@Conditional`, stereotypes | Categories 2 and 10 - writing your own starter, `ConfigData`, configuration metadata |
| Q118-119 JDK versus CGLIB proxies, self-invocation | Category 3 - advice ordering, pointcut expressions, AspectJ weaving, annotation interaction |
| Q120-122 propagation, rollback rules, isolation | Category 4 - `TransactionSynchronizationManager`, programmatic transactions, multiple transaction managers, transaction-bound events |
| Q123-125 `@Async`, circular dependencies | Categories 4 and 8 - context propagation across async, reactive and virtual threads |
| Q126-129 configuration, Actuator, testing, `@MockBean` | Categories 10 and 12 - custom endpoints, observability, context cache mechanics, Testcontainers |
| Q130-131 MVC versus WebFlux, HTTP clients | Categories 5 and 6 - `DispatcherServlet` internals, backpressure, R2DBC, the virtual thread comparison |
| Q132-149 filter chain, JWT, OAuth2 grants, CSRF, method security | Categories 8 and 9 - `AuthorizationManager`, multiple chains, Authorization Server, token relay |
| Q150-164 JPA lifecycle, N+1, locking, Hikari | Category 7 - repository proxy mechanism, projections, Specifications, custom fragments |

Where a question here overlaps, it starts one level deeper. Nothing is restated.

**The answer frameworks are not repeated either.** The four-layer technical answer, CIDER for scenarios and STAR-L for behavioral questions are defined once in [../01-java/README.md](../01-java/README.md). Re-read that section before your first mock.

---

## Files in this pack

| File | Purpose | When to use |
| --- | --- | --- |
| [README.md](README.md) | Prerequisite map, roadmap, what interviewers probe | Read first |
| [questions.md](questions.md) | 313 questions across 21 categories | Daily drilling |
| [answers.md](answers.md) | Mechanism-level model answers | After attempting yourself |
| [scenario-questions.md](scenario-questions.md) | Spring-specific incidents and architecture exercises | Mock practice |
| [cheatsheet.md](cheatsheet.md) | Fast revision reference | Night before, and 30 minutes before |
| [quiz.html](quiz.html) | Interactive flashcard version | Active recall |

### quiz.html

Open it directly in a browser - no server, no internet connection needed. Search covers question and answer text, filter by category, difficulty or your own progress, and mark each question Known or Review with progress saved in the browser. Press `/` to focus search.

Generated from the markdown, so the markdown stays the source of truth. After editing any of the three source files:

```bash
python tools/build-quiz.py 02-spring
```

---

## What interviewers actually probe at this level

Spring questions for a principal role are rarely about annotations. They are about whether you understand the *mechanism* well enough to debug it at 3am and to make platform decisions for other teams.

Four recurring themes:

1. **The proxy boundary.** Most Spring surprises - transactions, async, caching, security - trace back to a call that did not cross a proxy. If you can explain the boundary precisely, half the trick questions collapse into one answer.
2. **What is bound to the thread.** The transaction, the security context, the `EntityManager` and the tracing context are all thread-bound. Every async, reactive or virtual-thread question is really asking whether you know that.
3. **Startup versus runtime.** Auto-configuration, conditional evaluation, proxy creation and AOT processing all happen at startup. Knowing what is decided when explains native image constraints, context caching and most "works locally, fails in production" incidents.
4. **Defaults you should not accept.** `open-in-view`, the default `@Async` executor, unbounded HTTP client pools, `SimpleAsyncTaskExecutor`, exposed Actuator endpoints. Naming a default and why you change it is a strong signal of production experience.

---

## Study roadmap

### Week 1 - Container and configuration

Categories 1 and 2. Draw the `refresh()` sequence from memory and be able to say exactly where proxies are created and where `@ConfigurationProperties` are bound.

### Week 2 - AOP and transactions

Categories 3 and 4. This is the densest trick-question territory in the whole pack. Work every `[T]` question twice.

### Week 3 - Web layer

Categories 5 and 6. Trace one request through `DispatcherServlet` end to end. Form a defensible position on WebFlux versus MVC on virtual threads - you will be asked.

### Week 4 - Data and security

Categories 7, 8 and 9. Be able to draw the filter chain and explain the 6.x `AuthorizationManager` model, since many candidates still describe the pre-6.0 architecture.

### Week 5 - Production engineering

Categories 10, 11 and 12. Actuator, observability, native images, Spring Cloud, and the test pyramid that actually runs fast.

### Week 6 - Modern and mock

Categories 13 and 14, then work only from [scenario-questions.md](scenario-questions.md).

### Week 7 - Breadth across the rest of the portfolio

Categories 15 to 20. These are the parts of Spring that a Java-and-Spring role assumes you have met even when they are not the centre of the job: web protocols beyond REST, the messaging endpoints, Spring Batch, the non-relational stores, Spring on Kubernetes, and the Spring AI platform surface including MCP. Batch and messaging are the two most likely to appear unannounced, because most enterprises run both.

---

## Coverage map

Where each part of the Spring portfolio is covered. `01-java` holds the first pass, this pack holds the depth, and a few topics deliberately live in the pack that owns the wider subject.

| Component | Where |
| --- | --- |
| Core / IoC, Context, Beans | Category 1, plus `01-java` Q110-114 |
| SpEL | Q39, Q40 |
| AOP - aspect, advice, pointcut, join point, weaving, proxies | Category 3, plus `01-java` Q118-119 |
| Validation - `@Valid`, `@Validated`, groups | Q57, Q92 |
| Spring MVC | Category 5 |
| Spring WebFlux | Category 6 |
| REST, `ProblemDetail`, API versioning | Q90, Q97, Q102 |
| WebSocket / STOMP | Category 15 (Q263-267) |
| HATEOAS | Q268, Q269 |
| CORS | Q270, plus `01-java` Q141-143 |
| Spring JDBC - `JdbcClient`, `JdbcTemplate` | Q139 |
| Spring Data JPA | Category 7 |
| Spring Data JDBC | Q138 |
| Spring Data Redis | Q140, Q297 |
| Spring Data MongoDB | Q291-293 |
| Spring Data Elasticsearch | Q294, Q295 |
| Transaction management | Category 4 |
| Spring Boot, starters, auto-configuration | Category 10, plus `01-java` Q115-117 |
| Actuator, Micrometer, tracing | Q186-193, Q201, Q202 |
| DevTools and the dev loop | Q302 |
| Spring Security, method security | Category 8 |
| OAuth2 client, resource server, JWT, Authorization Server | Category 9 |
| Spring Kafka | Q214-216, and `03-microservices` category 3 |
| Spring AMQP / RabbitMQ | Q274-277, and `03-microservices` category 15 |
| Spring JMS | Q271-273, Q280 |
| Spring Integration | Q278, and `03-microservices` Q244 |
| Spring Web Services / SOAP | Q279, and `03-microservices` Q246 |
| Spring Cloud Config, Gateway, OpenFeign, LoadBalancer, Stream | Category 11 |
| Circuit Breaker / Resilience4j | Q210 |
| Spring Cloud Kubernetes | Q298-301 |
| Spring Batch - job, step, chunk, tasklet, reader/processor/writer | Category 17 |
| `@Scheduled`, `TaskExecutor`, `@Async` | Q77, Q200, Q217, Q301 |
| Testing - slices, `MockMvc`, `WebTestClient`, Testcontainers | Category 12 |
| Observability - Actuator, Micrometer, OpenTelemetry, structured logging | Q190-193, Q201, and `07-devops` |
| Spring AI - `ChatClient`, advisors, RAG, tools, structured output, memory | Category 13 |
| Spring AI - `ChatModel`, `EmbeddingModel`, ETL, MCP | Category 20 |

Deliberately out of scope here: broker topology, delivery semantics and estate-level integration patterns live in [`03-microservices`](../03-microservices/questions.md) categories 3 and 15; Prometheus, Grafana and cluster operations live in [`07-devops`](../07-devops/README.md); model behavior and evaluation live in [`08-genai`](../08-genai/README.md).

---

## Your Spring story bank

Prepare these with real detail from Verizon India and Sonata Software. Generic answers are transparent at 19 years of experience.

1. A Spring application you tuned for startup or memory, with before and after numbers.
2. A transaction bug that reached production, and the mechanism behind it.
3. A security requirement you implemented that was more than "add Spring Security".
4. A Boot 2 to 3 (or Java 8 to 17+) migration you planned and executed.
5. A shared starter or platform library you built for other teams, and how you versioned it.
6. A test suite you made fast, with the runtime before and after.
7. A Spring Cloud or microservice integration where you chose *not* to add a component.
8. An AI feature built on Spring, with its cost and evaluation controls.

---

## Self-check before the interview

- [ ] I can draw the `ApplicationContext` refresh sequence and name where AOP proxies are created.
- [ ] I can explain why `@Transactional`, `@Async`, `@Cacheable` and `@PreAuthorize` all fail the same way, in one sentence.
- [ ] I can describe the Spring Security 6 authorization architecture without using `AccessDecisionVoter`.
- [ ] I have a defensible position on WebFlux versus virtual threads.
- [ ] I can name three Spring Boot defaults I always change and why.
