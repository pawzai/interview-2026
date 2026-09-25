# Scenario Questions

Spring-specific production incidents, architecture exercises and leadership situations.

Every scenario uses **CIDER**, defined in [../01-java/README.md](../01-java/README.md):

- **Clarify** - what you ask before answering. Never diagnose or design in silence.
- **Isolate** - narrow the failure domain or the core requirement.
- **Decide** - commit to an approach and name the trade-off.
- **Execute** - the concrete steps.
- **Reflect** - what you monitor, prevent, or would do differently.

Read the scenario, answer out loud for five minutes, then compare. The model responses are longer than you should speak - use them as the map, not the script.

---

## Part A - Production incidents

### S1. Works locally, fails to start in production

> The service runs fine on every developer machine and in the CI pipeline. Deployed to production it fails to start with `NoSuchBeanDefinitionException` for a bean that clearly exists in the code.

**Clarify.** Which profiles are active in each environment? Did this ever work in production, or is it a first deployment? Is the artifact identical, or built separately per environment? Is AOT or a native image involved? What does the startup log say *before* the failure - specifically, does the auto-configuration report differ?

**Isolate.** "Exists in the code but not in the context" means the bean was conditionally excluded, not missing. The candidates, in order of likelihood:

1. **Profile-conditional bean.** The bean is `@Profile("dev")` or its configuration class is, and production runs a different profile. This is the most common cause and the reason I keep business behavior out of profiles (`answers.md` Q35).
2. **`@ConditionalOnProperty`** where the property is set locally (in `application.yml` committed to the repo) but comes from Parameter Store in production, and the import failed or the key differs.
3. **`@ConditionalOnClass`** where a dependency is `provided` or `optional` in the production build, or excluded by the packaging.
4. **Auto-configuration ordering** differing because of classpath order in the built artifact versus the IDE (Q184).
5. **AOT processing** - conditions were evaluated at *build* time with the build environment's profile, so a profile-conditional bean was never registered at all (Q196).
6. Component scanning missing a package because the artifact is packaged differently - a repackaged jar, a shaded dependency, or a module boundary.

**Decide.** Do not guess. The auto-configuration report tells you *why* a condition did not match, and comparing it between environments answers this definitively in minutes.

**Execute.**

1. Start the failing environment with `--debug` (or `logging.level.org.springframework.boot.autoconfigure=DEBUG`) and read the **negative matches** section for the bean in question. It states the condition that failed.
2. Diff the effective configuration: `/actuator/env` and `/actuator/configprops` between a working environment and production. Active profiles are at the top and are frequently the answer on their own.
3. Confirm the artifact is byte-identical across environments. If it is not, that is the finding - build once, promote the same artifact.
4. Fix the specific cause, then remove the class of problem: move the conditional from a *bean* to a *value* where possible, and make required configuration fail fast with validation (Q33).

**Reflect.** The systemic issue is that production was the first place this configuration combination ran. I would add a pipeline stage that starts the application with the **production profile** against stubbed infrastructure and asserts the context loads - a `@SpringBootTest` with the production profile active and external dependencies mocked. It catches this entire class of failure in CI for a few seconds of build time. I would also treat "different configuration per environment" as a risk to minimize rather than a feature to use.

> *Hook: a deployment failure caused by environment-specific wiring, and the pipeline gate you added afterwards.*

---

### S2. Half the operation was saved

> Customers report orders appearing with no payment record. The code clearly wraps both writes in a `@Transactional` method, and the developer insists it is correct.

**Clarify.** Show me the call path - is the transactional method called from within the same class? What exception type is thrown on the failure path? Is anything catching it? Is there more than one `DataSource`? Is the method `public`? Is the failing write happening in an event listener or an async method?

**Isolate.** "Transactional but partially committed" has a small set of causes, and they are all in the Spring pack:

1. **Self-invocation** - the method is called via `this`, so no proxy, no transaction at all (`answers.md` Q50). The most common.
2. **Checked exception** - Spring commits on checked exceptions by default, so a declared `IOException` from a downstream leaves the partial write committed (`01-java` Q121).
3. **Caught exception** - the code catches and logs, so the advisor never sees it and commits (Q74).
4. **`private`, `final` or `static`** method - the proxy cannot intercept it.
5. **Wrong transaction manager** - with two data sources, a plain `@Transactional` binds the `@Primary` manager, so writes to the second data source run in auto-commit with no rollback (Q66).
6. **Called from `@PostConstruct`** or another pre-proxy context (Q17).
7. The second write is in an **`@Async` method or an `AFTER_COMMIT` listener**, so it was never in the transaction to begin with (Q62, Q77).

**Decide.** This is verifiable rather than arguable. I would prove which one it is before changing code, because the fixes differ and "add `rollbackFor`" applied to a self-invocation problem changes nothing while appearing to.

**Execute.**

1. Turn on `logging.level.org.springframework.transaction.interceptor=TRACE` in a test or staging environment. It logs every transaction begin, commit and rollback with the method name. If there is no "Getting transaction for..." line, the proxy was never involved - that is causes 1, 4 or 6, immediately.
2. Reproduce with a **non-transactional** integration test (Q228) that forces the failure and asserts *both* rows are absent. A `@Transactional` test would have hidden this in the first place, which is likely why it shipped.
3. Apply the specific fix - extract to a separate bean for self-invocation; standardize on unchecked domain exceptions; remove the catch; qualify the transaction manager.
4. Audit for the same pattern elsewhere: a search for `@Transactional` on non-public methods, and an ArchUnit rule for internal calls to annotated methods (Q50).

**Reflect.** The deeper issue is that a silently non-transactional method is indistinguishable from a working one until data is wrong. Prevention: the ArchUnit rules, a non-transactional integration test for every multi-write use case, and a data-integrity check that runs continuously - a reconciliation query alerting on orders without payments. That last one is what turns "customers told us" into "we knew first", and at principal level that is the part worth emphasizing.

---

### S3. Audit records attributed to the wrong user

> The audit table shows actions attributed to users who did not perform them. It is intermittent, it only affects records written by a background process, and it is a compliance finding.

**Clarify.** Which code path writes those rows - async, scheduled, or a message listener? How is the actor determined - `SecurityContextHolder`, `AuditorAware`, or an explicit parameter? What executor is used? Is `MODE_INHERITABLETHREADLOCAL` configured anywhere? When did it start?

**Isolate.** Attribution to the *wrong* user, rather than to no user, is the key detail. A missing context produces null or "anonymous"; a *wrong* one means a context was inherited or left behind on a **pooled thread**.

The two mechanisms:

1. **`MODE_INHERITABLETHREADLOCAL`** with a thread pool. The context is inherited at thread *creation*, so each pooled thread permanently carries whichever user happened to trigger its creation, and every subsequent task on that thread is attributed to them (Q151). This is a privilege and compliance bug, not a cosmetic one.
2. **A `TaskDecorator` that sets the context but does not clear it** in a `finally`. The context persists on the pooled thread after the task completes and is used by the next unrelated task (Q152).

Either way, `AuditorAware` reads `SecurityContextHolder`, gets a stale authentication, and writes a plausible-looking but wrong username - which is worse than a null, because nobody notices.

**Decide.** Treat this as a security incident, not a bug: the audit trail is unreliable for an unknown period, and that has to be communicated to whoever owns the compliance obligation. Fix the mechanism, then determine the blast radius.

**Execute.**

1. **Contain.** Fix the propagation: use `DelegatingSecurityContextAsyncTaskExecutor` or a decorator that both sets *and clears* in a `finally`, and remove `MODE_INHERITABLETHREADLOCAL`.
2. For background work with no real user, make `AuditorAware` return an explicit **system principal** (`system:order-reconciler`) rather than falling back to whatever is on the thread (Q132). Ambient identity for system work is the design flaw underneath this.
3. **Assess the blast radius** - identify affected rows by correlating audit timestamps against the background job schedule, and quantify the period. Report it honestly.
4. Prefer **explicit identity** for the long term: the background job takes the acting user as a parameter or reads it from the record it is processing, rather than reading ambient state. That removes the entire class of failure.

**Reflect.** Two preventions. A test that runs work on a pooled executor twice with different users and asserts no leakage - simple, and it would have caught this. And a broader principle I would apply across the estate: anything security-relevant should be **passed explicitly** rather than read from ambient thread state, because ambient state and thread reuse interact badly and always will.

---

### S4. One new feature exhausted the connection pool

> A release added product enrichment from a third-party API to the order detail endpoint. Within an hour, every endpoint in the service was timing out - including ones that touch neither orders nor the third party.

**Clarify.** Is the enrichment call inside a `@Transactional` method? What timeouts are configured on the HTTP client? What is `hikaricp_connections_pending` doing? Did the third-party API slow down, or is it responding normally?

**Isolate.** Total service failure from one endpoint's new dependency is the signature of a **shared resource being held**. Two candidates, and here they compound:

1. **The HTTP call is inside the transaction** (Q76, Q212). Each in-flight enrichment holds a database connection for the duration of the remote call. With a pool of 15 and a 2-second response time, the pool is fully consumed by about 8 concurrent requests, and every other endpoint queues behind them.
2. **No timeout on the client**, so a degraded third party holds connections indefinitely rather than failing.

The give-away is that unrelated endpoints fail: that only happens through a shared pool. `connections_pending` climbing while database CPU is idle confirms it.

**Decide.** Mitigate immediately, then fix structurally. Rolling back is the fastest mitigation and I would do that first unless the feature is business-critical, because the fix requires a code change.

**Execute (mitigate).**

1. Roll back, or disable the enrichment via its feature flag if one exists. Confirm `connections_pending` returns to zero.
2. If neither is possible, deploy an aggressive read timeout as a stopgap - it converts an unbounded hold into a bounded one.

**Execute (fix).**

1. **Move the call outside the transaction.** Fetch enrichment first, then open a short transaction for any persistence - or, better, do not persist at all and treat enrichment as a read-time concern.
2. **Explicit connect and read timeouts** derived from the provider's SLA, always shorter than the transaction timeout.
3. **Circuit breaker with a fallback** that returns the order *without* enrichment - the dependency is non-critical, so degradation is the correct behavior (`01-java` Q181).
4. **Bulkhead** so enrichment can consume at most N concurrent slots and cannot starve the rest of the service.
5. `LazyConnectionDataSourceProxy` as a net (Q65).

**Reflect.** The review process let a network call into a transaction, so I would add the ArchUnit rule from Q80 - report-only first, then enforcing - plus a runtime interceptor that flags an HTTP call with an active transaction. I would also add a dashboard panel per downstream showing latency, error rate and breaker state, and an alert on `connections_pending`, because that metric would have paged us before customers noticed. Finally, a fault-injection test in staging that adds five seconds of latency to the third party and asserts the rest of the service still serves - untested fallbacks are the ones that fail.

---

### S5. Users randomly logged out after the Boot 3 upgrade

> After upgrading from Boot 2.7 to 3.2, users report being logged out unpredictably. Login succeeds, then a later request bounces them back to the login page. It does not reproduce reliably in testing.

**Clarify.** Is there a **custom authentication filter**? Is the session stored in memory, or in Redis via Spring Session? Is this a multi-instance deployment? Does it happen on the very next request, or after some time? Was Spring Security upgraded from 5 to 6 as part of this?

**Isolate.** Security 5 to 6 replaced `SecurityContextPersistenceFilter` (which saved the context automatically at the end of each request) with `SecurityContextHolderFilter`, which **only reads**. Saving is now the authenticating component's responsibility (Q148).

The built-in filters were updated. A **custom** filter that sets `SecurityContextHolder` and nothing else now persists the authentication for that single request only - so login works and the next request is anonymous (Q149).

"Not reliably reproducible" usually means either a multi-instance deployment where behavior depends on which instance serves the follow-up request, or that the reproduction path in testing happened to use the standard login rather than the custom filter.

**Decide.** Confirm the mechanism before changing anything, because "users get logged out" has several plausible causes (session replication, cookie configuration, load balancer affinity) and fixing the wrong one wastes a day during a live incident.

**Execute.**

1. **Confirm**: after a successful login, inspect whether the `SecurityContext` is actually in the session (`/actuator/sessions` with Spring Session, or a debug log on the repository). If the session exists but holds no context, that is the answer.
2. **Fix** the custom filter to save explicitly:

```java
SecurityContext context = SecurityContextHolder.createEmptyContext();
context.setAuthentication(authentication);
SecurityContextHolder.setContext(context);
securityContextRepository.saveContext(context, request, response);
```

3. **Audit every custom filter and every custom authentication path** in the codebase for the same omission - there is usually more than one, and the others fail less visibly.
4. Check the adjacent Security 6 runtime changes at the same time (Q253): `AuthorizationFilter` now applying to `ERROR` dispatches, CSRF deferred tokens breaking SPA clients, and `requestMatchers` matching semantics.

**Reflect.** The lesson for the next upgrade is that **security changes that fail at runtime need runtime verification**. I would build an authorization test matrix - representative endpoint × role × expected status - and run it before and after any security upgrade, diffing the results. Reading a migration guide is necessary and not sufficient. I would also make the canary deployment mandatory for framework upgrades, with authentication success rate as an explicit promotion gate, so the blast radius of the next one is 5 percent of users for ten minutes rather than everyone for a day.

---

### S6. Every route through the gateway got slow

> Spring Cloud Gateway p99 latency went from 20ms to 4 seconds across all routes after a release. CPU on the gateway pods is under 15 percent. The backing services show normal latency.

**Clarify.** What was in the release? Are all routes affected equally, or is one worse? What is the event loop thread count, and are those threads busy? Any new global filter?

**Isolate.** Latency across **all** routes with **idle CPU** is the definitive signature of **event loop starvation** (Q208). The gateway has a handful of Netty threads for the entire process; if something blocks one, every request routed through it waits, regardless of destination.

The usual cause is a new global filter doing blocking work: a JDBC lookup for an API key, a synchronous `RestTemplate` call to an authorization service, a blocking Redis client, or reading a file per request. It can also be a blocking call inside a `KeyResolver` for rate limiting.

The low CPU is what rules out the alternatives - a genuine capacity problem, a GC problem or a CPU-bound filter would all show high CPU.

**Decide.** Roll back first. This is a total-service degradation with a known recent change, and diagnosis can happen afterwards on a non-production instance.

**Execute.**

1. **Roll back**, confirm recovery.
2. **Confirm the mechanism** on a staging instance: a thread dump showing `reactor-http-nio-*` threads inside a JDBC or socket read is conclusive. `BlockHound` in the gateway's test suite would have failed the build.
3. **Fix the filter**: return a `Mono` and use `WebClient` for lookups; use a reactive Redis client; cache locally with Caffeine so the hot path has no I/O at all; and if a blocking library is genuinely unavoidable, `publishOn(Schedulers.boundedElastic())` explicitly as a bridge.
4. Re-deploy behind a canary with latency as the promotion gate.

**Reflect.** A gateway is the highest-blast-radius component in the estate - a single careless filter degrades every service behind it. So I would treat it differently from an ordinary application: **BlockHound in the test suite as a hard gate**, a documented rule that no blocking API may be used in gateway code, review by someone who understands the reactive model, and an alert on event loop utilization specifically rather than CPU. I would also question whether the authorization lookup belonged in the gateway at all - filters that need application state are often a sign the concern is in the wrong layer.

---

### S7. The test suite now takes 40 minutes

> CI has degraded from 8 minutes to 40 over about a year. Developers have stopped running tests locally and are batching changes, and the change failure rate is rising.

**Clarify.** How many tests, and what is the split between unit, slice and `@SpringBootTest`? How much of the 40 minutes is *test execution* versus context startup and container startup? Has the application grown, or just the test count?

**Isolate.** In a Spring codebase, a suite that grows super-linearly is almost always **application context startups**, not test execution. Each distinct `MergedContextConfiguration` starts a whole application (Q221), and the count grows silently as people add `@MockBean` combinations and inline properties.

Secondary contributors: `@SpringBootTest` used where a unit test would do, a Testcontainer started per class, and `@DirtiesContext` evicting the cache.

**Decide.** Measure before optimizing. `logging.level.org.springframework.test.context.cache=DEBUG` reports cache size, hits and misses - that single number usually reframes the problem immediately, and I have seen suites creating 40+ contexts where 3 would do.

**Execute.**

1. **Count the contexts** and identify the annotations creating them (Q222). Consolidate `@MockBean` sets into a shared `@TestConfiguration` imported everywhere, so the cache key repeats.
2. **Move tests down the pyramid.** Audit the `@SpringBootTest` classes; most are testing logic that needs no container. Converting them to plain Mockito tests turns seconds into milliseconds each, and this is usually the largest single win.
3. **Share containers** - a singleton container for the whole suite rather than per class, plus reuse enabled locally (Q227).
4. **Remove `@DirtiesContext`** by fixing the state leakage it was papering over.
5. **Parallelize** once shared state is eliminated - which also improves test quality (Q234).
6. **Split the pipeline** - fast tests on every commit, slower integration tests on merge, so developer feedback is minutes.

**Reflect.** I would frame this to leadership as a **delivery** problem, not a hygiene one: a 40-minute suite changes behavior, and the batching it causes is what is driving the change failure rate. That connects the work to a metric they already care about.

Prevention: a build-time budget - the fast suite fails if it exceeds five minutes - so the cost is visible at the moment it is introduced rather than a year later. And context count reported in the build output, so an added context is a visible event in a pull request.

---

### S8. The native image works until it does not

> A service was migrated to a GraalVM native image for faster startup. It passed all tests and ran fine for two weeks, then failed in production on a monthly reporting endpoint with `ClassNotFoundException`.

**Clarify.** Was the reporting path exercised by the test suite that ran against the *native* binary, or only against the JVM? What does that path do differently - reflection, a template engine, dynamic proxies, resource loading, serialization? Which library raised the error?

**Isolate.** GraalVM's closed-world assumption means anything reachable only through reflection, dynamic proxies, resource patterns or serialization must be registered at build time (Q197). Spring's AOT engine generates hints for framework usage, but not for a library doing its own reflection, nor for your own dynamic behavior.

A monthly path is exactly where this hides: it was never executed in the native binary, in tests or in the first two weeks of production. This is not a Spring bug, it is the fundamental risk of native images - **your test coverage of the native binary is your safety net, and it was not there**.

**Decide.** Mitigate first: the JVM artifact of the same code works. Then decide whether native is worth keeping for this service at all, which is the more valuable conversation.

**Execute.**

1. **Fail over to the JVM build** for the affected service to restore the function immediately.
2. **Register the hints** for the failing path:

```java
class ReportingHints implements RuntimeHintsRegistrar {
    public void registerHints(RuntimeHints hints, ClassLoader cl) {
        hints.reflection().registerType(ReportRow.class, MemberCategory.INVOKE_DECLARED_CONSTRUCTORS,
                                        MemberCategory.DECLARED_FIELDS);
        hints.resources().registerPattern("reports/*.jrxml");
    }
}
```

3. **Close the coverage gap** - the entire test suite must run against the native binary in CI (`nativeTest`), not just against the JVM. That is slow, and it is the price of the deployment model.
4. Use the **GraalVM tracing agent** on a full run of the application exercising every path, to generate hint configuration for anything missed.

**Reflect.** The strategic reflection matters more than the fix. I would ask what native was bought for: if the goal was startup time on a long-running service, **CDS or CRaC** delivers most of the benefit with none of this risk (Q198), and I would move back. Native earns its complexity for scale-to-zero and short-lived workloads, where the startup difference is the whole product requirement.

I would also state the general principle: any deployment model where a code path can fail only in production **requires** that production's exact artifact be fully exercised in CI. If we are unwilling to pay for that, we should not use the model.

---

### S9. Duplicate processing after every deployment

> A Kafka consumer creates duplicate records every time the service is deployed. The team's proposed fix is to add a database uniqueness check before every insert.

**Clarify.** What is the acknowledgment mode, and is auto-commit enabled? How long does processing take per message, and what are `max.poll.interval.ms` and `session.timeout.ms`? Does processing include an external call? Is the handler idempotent today? Are the duplicates exactly at rebalance time?

**Isolate.** Duplicates concentrated at deployment means **rebalancing**. During a rolling deployment, consumers leave and join, partitions are reassigned, and any message processed but whose offset was not yet committed is redelivered to the new owner.

That is not a bug - Kafka is at-least-once, and the guarantee cannot be tightened (Q216). The real problem is that the handler is **not idempotent**, which means every rebalance, every retry, every network blip and every restart produces duplicates. Deployments just made it visible and regular.

Contributing factors to check: acknowledgment after processing versus auto-commit on poll; processing time exceeding `max.poll.interval.ms`, which causes the consumer to be evicted *mid-batch* and guarantees redelivery; and shutdown that does not drain and commit (Q189).

**Decide.** The proposed fix - a check-then-insert - is a race condition, not a solution: two concurrent consumers both check, both find nothing, both insert. I would push back on that specifically, because it is the kind of fix that appears to work in testing and fails under the exact conditions it was meant to handle.

**Execute.**

1. **Make the handler idempotent properly**: a unique constraint on the business key, or an **inbox table** recording processed message IDs written in the *same database transaction* as the effect, so redelivery is a no-op enforced by the database rather than by application logic.
2. **Order the commits** - database transaction first, offset commit after - so duplicates are the failure mode rather than loss.
3. **Disable auto-commit** and acknowledge explicitly after successful processing.
4. **Fix graceful shutdown** so the listener container stops accepting, finishes the in-flight message and commits before exit (Q189), which removes most deployment-time redelivery.
5. **Check `max.poll.interval.ms`** against the p99 processing time, and reduce `max.poll.records` so a batch always completes within it.

**Reflect.** The teaching point is that at-least-once is the default everywhere - Kafka, SQS, HTTP retries, user double-clicks - so **idempotency is a design requirement, not a Kafka-specific workaround**. I would audit the other consumers for the same gap, add it to the service template and the review checklist, and add a test that deliberately redelivers a message and asserts a single effect. That test is cheap and it permanently encodes the requirement.

---

### S10. The metrics platform fell over

> After a release, the shared Prometheus instance became unresponsive and metrics were lost for every team, not just yours. The platform team traced it to your service.

**Clarify.** What metrics did the release add or change? Are any tagged with an identifier - user, order, tenant, session? Did any endpoint start receiving unmatched URLs? What is the series count for the service before and after?

**Isolate.** This is **cardinality explosion** (Q191). Each unique tag combination is a separate time series with its own storage and index entry. A tag carrying a user ID, an order ID or a raw URL path produces one series per value, and a million users means a million series per metric.

The two specific Spring mechanisms:

1. A custom metric tagged with a high-cardinality value - the most common, and usually well-intentioned ("we wanted to see per-customer latency").
2. **`http.server.requests` with an unmatched URI.** Spring tags with the *matched pattern* (`/orders/{id}`) precisely to bound cardinality. A new endpoint that bypasses pattern matching - a custom filter recording the raw URI, or requests hitting no handler - produces one series per distinct path.

The fact that it affected other teams is the important part: this is a **shared-platform incident**, and my service caused an outage for people who had no involvement.

**Decide.** Stop the bleeding immediately by removing the offending metric, then treat the platform's lack of a guardrail as a finding to raise constructively rather than defensively.

**Execute.**

1. **Roll back or hotfix** to remove the high-cardinality tag. Coordinate with the platform team on cleaning up the existing series.
2. **Re-implement the requirement correctly**: the underlying need - per-customer visibility - belongs in **traces and logs**, which are designed for high-cardinality data, or in a low-cardinality bucketing (customer *tier*, not customer *ID*).
3. Set `management.metrics.web.server.max-uri-tags` as a bound, and verify no filter records raw URIs.
4. Add a **cardinality check in CI** - a test that exercises the metrics endpoint and asserts the series count per meter stays under a threshold.

**Reflect.** Two levels. Within my team: metrics get reviewed for cardinality the same way a database index gets reviewed, and the `@Observed` low/high cardinality distinction (Q192) is used deliberately because it encodes the right practice in the API.

At the platform level, I would raise - collaboratively - that a single tenant should not be able to take down shared observability. Per-service series limits and ingestion quotas are the standard defense, and offering to help implement them is a better response than apologizing. That framing, taking responsibility while also improving the system that permitted it, is what is being assessed here.

---

## Part B - Architecture and design

### S11. Module structure and shared platform for a 30-engineer estate (Q258)

**Clarify.** How many services exist today and how are they deployed? Is there a platform team, or would this be a shared responsibility? What is the current pain - inconsistency, slow onboarding, upgrade paralysis, incident response? Are teams aligned to domains or to layers? What is the deployment platform?

That last question matters because it determines what the platform *should not* build (Q220).

**The shape I would propose.**

**Service internals** - a standard, documented layout so any engineer can navigate any service:

```
com.acme.orders
  ├─ api          # controllers, DTOs, exception handling
  ├─ domain       # entities, value objects, domain services, ports
  ├─ application  # use cases, transaction boundaries
  ├─ infrastructure # JPA adapters, clients, messaging
  └─ config       # Spring configuration
```

Packages rather than Maven modules for most services, enforced with ArchUnit (Q233); multi-module (Q250) only where the domain is complex enough to justify it.

**Shared platform** as several thin, independently versioned starters rather than one monolith (Q204):

- `acme-observability-starter` - Micrometer configuration, standard tags, tracing, structured logging, correlation IDs.
- `acme-security-starter` - resource server configuration, authority mapping, standard filter chains, security headers.
- `acme-web-starter` - `ProblemDetail` error handling, Jackson configuration, standard filters.
- `acme-resilience-starter` - Resilience4j defaults, client timeouts, connection pool sizing.
- `acme-testing-starter` - Testcontainers configuration, ArchUnit rule sets, test fixtures.

Every bean `@ConditionalOnMissingBean`, every feature `@ConditionalOnProperty` with a default, full configuration metadata, and a canary consumer always on the latest version.

**What I deliberately would not build**: a service discovery layer, a config server, or anything Kubernetes already provides.

**Governance.** A lightweight architecture forum with rotating membership rather than an architecture board; ADRs in each repository for local decisions and a central one for cross-cutting; inner-source contribution to the starters with a review SLA; and a service template (a `cookiecutter` or Backstage scaffold) that produces a deployable, observable, secured service in minutes - which is how standards actually spread, because the standard path is the easy path.

**Trade-offs to state.** This is a real investment - roughly one to two engineers' ongoing capacity for the starters and the template. At 30 engineers that is defensible if it saves each team the same work; below about 15 engineers it is not, and copy-paste with good documentation is genuinely the right answer. I would also set a measure - time from repository creation to production deployment, and incident count attributable to missing platform concerns - so the investment is accountable.

---

### S12. A modular monolith that can be split later (Q259)

**Clarify.** What is driving the eventual split - scaling, team autonomy, deployment cadence, or a belief that microservices are the destination? (If nobody can answer, the right recommendation may be to stay monolithic permanently, and saying so is the senior answer.) How many teams? Is the domain understood, or still being discovered?

**The design.** The goal is that extracting a module later is a **transport change, not a redesign**.

**Module boundaries from bounded contexts**, one top-level package each, verified by Spring Modulith (Q247):

```java
@Test void modulesAreValid() { ApplicationModules.of(Application.class).verify(); }
```

**Four rules that make extraction cheap:**

1. **No cross-module calls except through a published API.** Each module exposes an interface in its root package; everything else is internal and Modulith enforces it. When the module becomes a service, that interface becomes the client.
2. **Communicate by events, not by calls, wherever the interaction is not a query.** `@ApplicationModuleListener` with the event publication registry (Q248) gives at-least-once delivery inside the process, so listeners are already idempotent and already asynchronous - exactly what they must be across a network. Switching to Kafka later changes the publisher, not the logic.
3. **No shared database tables between modules.** Each module owns its tables, prefixed by module name, and never joins across a boundary - it asks the other module's API. This is the constraint teams most want to break and the one that actually determines whether extraction is possible, because a shared table cannot be split without a migration.
4. **No shared entities.** Modules exchange DTOs, not JPA entities, so a schema change in one does not ripple.

**What stays monolithic deliberately**: one deployment, one database instance (with schema separation), one transaction manager. That is the benefit - local transactions, no distributed tracing required to debug, and refactoring boundaries is a compile-time operation while the domain is still being learned.

**The extraction path** when a driver appears: move the module to its own deployment behind the same interface, switch the internal event publication to a broker, split the schema (which is safe because nothing joined across it), and cut traffic over with the two coexisting.

**Trade-offs.** The rules feel like unnecessary ceremony while everything is in one process, and teams will push back - the shared-table rule especially. The honest framing is that this is **option value**: a modest, ongoing discipline that keeps a decision open. If we are certain we will never split, we should drop the rules and admit it rather than paying for an option we will not exercise.

---

### S13. Multi-tenancy end to end (Q260)

**Clarify.** How many tenants and what is the size distribution - a long tail plus a few enterprise customers changes the answer entirely. What are the compliance and data residency requirements? Does any tenant need dedicated infrastructure contractually? Is per-tenant customization required? What is the pricing model, since it determines whether per-tenant cost attribution matters?

**Isolation model.** I would propose a **tiered** approach, which is where most mature SaaS converges: a shared database with a tenant discriminator for the long tail, and a dedicated database for enterprise and regulated tenants. That matches cost to willingness to pay and gives an answer to "we need our own database" that does not require re-architecture.

**The Spring implementation, layer by layer:**

**Tenant resolution** - from the authenticated token only, never a header or parameter the client controls:

```java
String tenant = jwt.getClaimAsString("tenant");   // authoritative
```

Resolved once in a filter into a request-scoped holder, and propagated explicitly to async and messaging paths with a `TaskDecorator` (Q95) - ambient state that silently disappears on a background thread is how cross-tenant leaks happen.

**Data isolation, enforced at the lowest layer** so a developer who forgets a predicate cannot leak:

- Shared schema: PostgreSQL **row-level security** with the tenant set as a session variable on connection checkout, or a Hibernate `@Filter` enabled globally. RLS is stronger because it is enforced by the database regardless of the code path, including ad-hoc queries.
- Dedicated database: an `AbstractRoutingDataSource` keyed on the tenant, with a connection pool per tenant - which is the operational constraint, since pools multiply.

**Everything else must carry the tenant**: cache keys (a tenant-prefixed key generator, or a leak on first cache hit), queue messages, log lines, metrics tags (as a *low-cardinality* tag only if tenant count is bounded - see Q191), S3 prefixes, and vector store filters if there is an AI feature (Q241).

**Noisy neighbours**: per-tenant rate limits, bounded concurrency per tenant so one cannot consume the pool, statement timeouts so an expensive query cannot saturate the database, and separate queues or priority lanes for large tenants.

**Operations**: automated onboarding and offboarding including complete deletion (GDPR has a deadline), per-tenant metrics without which noisy-neighbour incidents are undiagnosable, and a migration strategy across thousands of tenants with per-tenant progress tracking rather than one script.

**Verification.** This is a security control, so it gets tested like one: an automated suite authenticating as tenant A and asserting **404** (not 403 - do not confirm existence) on every tenant B resource, run in CI. And a periodic scan for queries lacking a tenant predicate.

**Trade-offs to state.** Shared schema is cheapest and densest with the highest blast radius from a single bug; database-per-tenant is the strongest isolation, easiest per-tenant restore and residency story, and the heaviest operationally. The tiered model costs the complexity of supporting both, and I would be explicit that this is a deliberate purchase rather than an accident.

---

### S14. An idempotent, observable Kafka consumer (Q261)

**Clarify.** What is the message volume and the ordering requirement - global, per key, or none? What is the effect of processing - a database write, an external call, or both? What is the acceptable end-to-end latency? What should happen to a message that can never succeed? Is replay of history a requirement?

**The design.**

**Consumption.** `@KafkaListener` with `concurrency` set to the partition count for this instance count, auto-commit **disabled**, and manual acknowledgment after successful processing (Q215). `ErrorHandlingDeserializer` wrapping the value deserializer, so a poison message becomes a handled failure rather than an infinite crash loop.

**Idempotency** - the core requirement, because delivery is at-least-once and no configuration changes that (Q216):

```java
@Transactional
public void handle(OrderEvent event) {
    if (!inbox.recordIfNew(event.messageId())) return;   // unique constraint
    orderService.apply(event);
}
```

The inbox insert and the business effect commit in **one local transaction**, so a redelivery is a no-op enforced by the database rather than by a check-then-act race. The inbox table gets a retention policy, since it grows forever otherwise.

**Ordering.** Key by aggregate ID so all events for one entity land on one partition and are processed in order. If throughput requires more parallelism than partitions allow, dispatch within the consumer to a bounded worker pool **keyed by the message key**, preserving per-entity order while scaling.

**Error handling, by class of failure:**

- **Transient** (downstream timeout) - `DefaultErrorHandler` with exponential backoff, or better `@RetryableTopic` so retries move to delay topics and do not block the partition.
- **Permanent** (validation failure, unknown schema) - `addNotRetryableExceptions` so it goes straight to the DLT rather than retrying ten times.
- **DLT** - alerted on, never silently accumulating, with the failure reason in headers and a documented, throttled replay path (`01-java` Q186).

**External calls.** Outside the database transaction, with a circuit breaker, and an idempotency key propagated so the downstream can deduplicate too.

**Observability** - the "fully observable" half of the question:

- **Consumer lag and lag growth rate** as the primary alert - lag alone tells you there is a problem, the rate tells you before it is one.
- Per-message processing time as a `Timer`, so the bottleneck is visible without an incident.
- Trace context extracted from message headers and continued, so a trace spans producer and consumer (`01-java` Q177).
- Counters for processed, deduplicated, retried and dead-lettered - the deduplication counter is the one that proves idempotency is actually working.
- DLT depth alert, rebalance rate, and structured logs carrying message ID, key, partition, offset and trace ID.

**Lifecycle.** Graceful shutdown that finishes the in-flight message and commits the offset before exit (Q189), so a deployment does not manufacture redeliveries.

**Trade-offs.** The inbox adds a write per message and a table to maintain; at very high volume a bounded deduplication cache in Redis with a TTL is a cheaper approximation, trading a small correctness window for throughput. I would name that as the scaling path rather than building it up front.

---

### S15. Boot 2.7 to Boot 3 across 40 services (Q262)

**Clarify.** What is the current spread - all on 2.7, or a range back to 2.3? Are all on Java 17 already? Is there a shared BOM or platform starter? How many teams, and what is their capacity? Is anything forcing the timeline - a CVE, an end-of-support date, a dependency requiring Boot 3? What third-party and internal libraries are shared?

**Decide the approach.** Not 40 parallel migrations, and not one big-bang. A **pathfinder then wave** model, because the first migration discovers the problems and every subsequent one should be cheaper.

**Execute.**

**Phase 0 - Prepare (2-3 weeks).**

- Get every service to **Java 17 and Boot 2.7.x latest** first. Two migrations at once makes failures unattributable.
- Fix all deprecation warnings on 2.7 - most Boot 3 breakages are things 2.7 already warned about.
- **Inventory the dependencies** across all 40 services and identify which lack Jakarta-compatible versions (Q252). This is the long pole and it is external to you, so it must start first. Anything with no upgrade path needs a decision - replace, fork, or isolate.
- Upgrade the internal shared libraries to publish Jakarta-compatible artifacts, and to ship both `spring.factories` and `AutoConfiguration.imports` during the transition (Q185).

**Phase 1 - Pathfinder (2-3 weeks).** One real but non-critical service, migrated by the platform team *with* the owning team. Produce:

- A migration runbook with the actual issues encountered, not the generic guide.
- An OpenRewrite recipe covering the mechanical changes.
- A documented Security 5 to 6 change list for the estate's common patterns (Q253).
- A realistic effort estimate per service, sized by category.

**Phase 2 - Waves.** Group services by similarity and risk, simplest and lowest-risk first. Each wave: automated pull request from the recipe, team review, the **authorization test matrix** run before and after (Q253), canary deployment with authentication success rate and error rate as promotion gates, then full rollout. Wave retrospectives feed back into the runbook.

**Phase 3 - Long tail.** The services with genuinely blocked dependencies. These need individual decisions and executive visibility, because they are the ones that stall indefinitely.

**Risk controls throughout.** Every service independently deployable and rollback-able; nothing else changing during the migration (no feature work in the same release); `spring-boot-properties-migrator` in each service for one release to surface configuration changes (Q254); and a canary period per wave rather than per service.

**Reporting.** A single dashboard of services by version, updated automatically, with a target date. Visible progress is what keeps a months-long migration from stalling once the initial energy fades.

**The framing for leadership.** Not "we need to upgrade the framework", but: the current version loses support on a date, after which security patches stop; the cost of doing this deliberately over one quarter is X, and the cost of doing it under CVE pressure later is several times that plus unplanned outage risk. Attach the date and the number - that is what turns it from an engineering preference into a decision they can make.

---

## Part C - Leadership and platform ownership

Answer with STAR-L in two to three minutes. The model responses give the shape and the judgement being assessed; fill them with real events from Verizon India and Sonata Software.

### S16. The team wants WebFlux for a new service

> A well-regarded senior engineer proposes building a new service on WebFlux. The rest of the team has no reactive experience. You think it is the wrong choice.

**What is being assessed:** whether you can disagree technically without shutting down a strong engineer, and whether your position is reasoned or reflexive.

**Approach.** I would start by understanding what they are optimizing for, because there is often a real requirement underneath - they may know something about the expected concurrency, or a streaming requirement, that I do not.

Then I would make it a **criteria** discussion rather than a preference one: what concurrency do we actually expect, is the downstream stack reactive, do we need backpressure or streaming semantics, what is the team's ability to debug it at 3am, and what does it cost us if the author leaves. Writing those down usually resolves it, because in most cases the concurrency target is comfortably met by MVC on virtual threads (`answers.md` Q119) and the reactive stack is buying complexity rather than capacity.

If they still disagree, I would look for the smallest reversible test - build one endpoint both ways and measure, or agree that the reactive approach is right *if* a specific condition holds, and check it. Turning an opinion contest into evidence is nearly always available and it preserves the relationship.

And if I am overruled, or if the criteria genuinely favour reactive, I would commit and then insist on the things that make it survivable: BlockHound in CI, context propagation configured, `StepVerifier` tests, and at least two other engineers brought up to competence so it is not one person's service.

**Learning to state.** Early in my career I would have argued the technology. What I have learned is that the durable question is not which is better but which we can *operate*, and framing it that way usually produces agreement rather than a winner.

### S17. Two teams have built two different shared starters

> You discover that two teams have independently built overlapping platform starters. Both are in use, both are maintained, and each team believes theirs is better.

**Approach.** First, resist the instinct to pick one immediately - the duplication is a symptom of an organizational gap (no shared ownership, no visibility), and choosing a winner without addressing that guarantees a third starter next year.

I would get both teams in a room to compare against **consumer needs** rather than against each other: which concerns does each cover, what do consuming teams actually use, what is the quality of the metadata and tests, and what would migration cost in each direction. Very often the answer is that each is better at different things, which turns a competition into a merge.

The outcome I would drive is a single starter with **joint ownership** and both authors as maintainers, rather than one team's absorbed into the other's - because the goal is that both teams stay invested, and because the engineer whose code is discarded is the one most likely to build the next duplicate.

Then the structural fix: a visible place where shared components are registered, an inner-source model so the answer to "this does not do what I need" is a pull request rather than a fork, and a lightweight forum where someone announcing "I am about to build X" gets told it exists.

**Learning.** Duplication like this is almost always a communication failure that surfaced as a technical one, and treating it purely technically leaves the cause intact.

### S18. A senior engineer resists the upgrade cadence

> You introduce a policy that services must stay within one minor version of current Spring Boot. A respected engineer argues loudly that this is churn for its own sake and is taking time from features.

**Approach.** I would take the objection seriously, because it is partly right: if upgrades are painful and manual, the policy *is* imposing a real cost, and the correct response is to reduce the cost rather than to insist on the discipline.

So I would separate the two questions. On the *why*: the argument is not novelty, it is that support windows end, that CVE patches only land on supported versions, and that deferred upgrades compound into a large unplanned migration under deadline pressure - which is exactly what a Boot 2 to 3 migration looks like when left too long (S15). I would bring the numbers: our current version's end-of-support date, and an estimate of the two paths.

On the *how*: automated dependency pull requests, a shared BOM so 40 services change one property, OpenRewrite recipes, and a canary service that upgrades first and documents the surprises. If upgrading is a ten-minute review rather than a two-day task, the objection largely evaporates - and if it does not, that tells me the automation is not good enough yet.

I would also give the objection somewhere to go: a stated exception process, so a team with a genuine blocker escalates rather than quietly ignoring the policy.

**Learning.** Resistance to a policy is usually accurate information about the policy's cost. The engineers who push back hardest are often the ones who have felt that cost most directly, and treating them as obstacles rather than as data loses you both the information and the person.

### S19. Your platform library caused a production incident

> A change to the shared observability starter caused a memory leak that took down three services during a peak period. You own the library.

**Approach.** Own it immediately and publicly - in the incident channel, in the postmortem, and with the affected teams. Platform ownership means the blast radius of your mistakes is other people's outages, and how you handle the first one determines whether teams ever trust your library again.

Concretely: mitigate first (yank the version, publish a fixed release, help each affected team deploy), then a blameless postmortem that I run but do not facilitate, so it is not my own investigation of myself.

The findings I would expect to be about *my process*, not the specific bug: the library had no canary consumer, so a change reached three production services simultaneously; there was no load or soak test in the library's own pipeline; and the release notes did not flag it as behavioral. Those are all fixable, and they are more useful than "we will be more careful".

I would then go further than required - offering the affected teams a way to pin versions and a documented rollback path - because the trust cost of a platform incident is higher than the technical cost, and rebuilding it is the actual work.

**Learning.** A shared library is a distributed system with a coordinated deployment I do not control. Once I started treating releases with the same care as a production deployment - canary, soak, staged rollout, explicit rollback - the class of incident stopped.

### S20. Standardizing 40 services you do not own

> Leadership asks you to bring 40 services onto consistent Spring, security and observability standards. You have no authority over the teams that own them.

**Approach.** Authority is not what makes this work anyway, so I would not spend time asking for it. What works is making the standard path the **easiest** path.

My sequence: start by finding out what the teams actually struggle with, because a standard that solves their problem is adopted and one that solves mine is resisted. Usually it is observability during incidents, security review turnaround, and time to get a new service to production.

Then build the thing that helps: a service template that produces a fully wired service in minutes, starters that are genuinely optional and override-friendly (`answers.md` Q204), and automated upgrade pull requests so adoption is a review rather than a project. Pick two or three willing teams first and make them successful publicly - voluntary adoption by respected teams does more than a mandate.

Where a mandate is genuinely required - security controls, supported versions - I would get it stated by leadership with a real deadline and an exception process, and I would be specific that it is a small list. A platform team that mandates twenty things is ignored; one that mandates three and helps with the rest is followed.

And I would measure adoption and *outcomes* - incident count, time to first deploy - not compliance, because if teams are working around the standard, that is my defect.

**Learning.** Influence without authority is mostly about reducing someone else's cost. Every time I have tried to lead with the standard rather than with the help, it has taken twice as long.

### S21. Justifying a framework upgrade to a non-technical executive

> The CFO asks why engineering wants to spend a quarter on "upgrading something that already works".

**Approach.** It is a fair question and the technical framing is the wrong one. I would translate it into risk and cost, with numbers and dates.

The three points I would make: our current version stops receiving security patches on a specific date, after which any vulnerability is unpatched and that is a compliance and customer-trust exposure, not just an engineering one. Doing this deliberately over one quarter costs a known amount and can be scheduled around delivery commitments. Doing it later, under a vulnerability with a disclosure deadline, costs several times that plus unplanned outage risk and the opportunity cost of dropping whatever we were doing.

I would also be honest about the benefits I am *not* claiming - it will not make the product faster or add features - because overselling it damages credibility for the next conversation. And I would offer the middle option if there is one: a reduced scope covering the highest-risk services this quarter and the rest next, so it is a choice rather than an ultimatum.

**Learning.** Early on I made these arguments in terms of technical debt, which is a metaphor executives have learned to discount. Framing it as a dated, quantified risk with options attached changed the response entirely - and it is also more honest, because it forces me to actually know the date and the number.

---

## Practice protocol

1. Set a five-minute timer and answer out loud, recording yourself.
2. Write your **clarifying questions before** reading the model answer - this is the habit most senior candidates lack, and it is the most visible signal in an interview.
3. Compare, and note only what you missed. Keep a running gap list.
4. Re-attempt anything you missed a week later.

Target: two incidents and one design per day for two weeks, then a full mock covering one of each in 60 minutes.
