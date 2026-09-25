# Answers

Model answers for [questions.md](questions.md). Numbers match the question numbers exactly.

Answers follow the four-layer structure defined in [../01-java/README.md](../01-java/README.md): direct answer, mechanism, trade-off, experience hook. Hooks are written as *italic placeholders* - replace them with real detail from Verizon India and Sonata Software.

Q258-262 are worked as full design exercises in [scenario-questions.md](scenario-questions.md). Q308-313 are story questions with no scripted answer.

---

## 1. Container internals

### Q1. The `refresh()` sequence

`AbstractApplicationContext.refresh()` runs a fixed template of twelve steps:

1. `prepareRefresh` - start time, active flag, validate required properties.
2. `obtainFreshBeanFactory` - create the `BeanFactory` and load `BeanDefinition`s (component scanning happens here for annotation contexts).
3. `prepareBeanFactory` - register the expression resolver, `ApplicationContextAwareProcessor`, resolvable dependencies such as `ApplicationContext` itself.
4. `postProcessBeanFactory` - subclass hook (this is where the web contexts register scopes).
5. **`invokeBeanFactoryPostProcessors`** - `BeanDefinitionRegistryPostProcessor`s run first, and this is where `ConfigurationClassPostProcessor` parses `@Configuration`, `@Import`, `@ComponentScan` and auto-configuration, then `BeanFactoryPostProcessor`s such as property placeholder resolution.
6. `registerBeanPostProcessors` - instantiate and register all `BeanPostProcessor`s, including `AnnotationAwareAspectJAutoProxyCreator`.
7. `initMessageSource`, 8. `initApplicationEventMulticaster`, 9. `onRefresh` (the embedded web server is created here), 10. `registerListeners`.
11. **`finishBeanFactoryInitialization`** - instantiate all remaining non-lazy singletons. **AOP proxies are created here**, in `postProcessAfterInitialization` of the auto-proxy creator.
12. `finishRefresh` - `LifecycleProcessor` start, publish `ContextRefreshedEvent`.

The takeaway that answers a dozen other questions: bean *definitions* are all known before any bean is *instantiated*, and proxying happens after initialization, which is why `@PostConstruct` runs on the raw target.

### Q2. `BeanDefinition`

A `BeanDefinition` is the metadata describing how to create a bean - class name, scope, lazy flag, constructor arguments, property values, factory method, init and destroy methods, autowire mode, primary and role flags. It is not an instance; instances are created later from the definition.

`BeanDefinitionRegistryPostProcessor` can add or remove definitions; `BeanFactoryPostProcessor` can modify existing ones. After step 5 the registry is effectively frozen. This is the extension point behind auto-configuration, Spring Data repositories and mapper scanning - all of them register definitions programmatically rather than being component-scanned.

### Q3. `BeanFactoryPostProcessor` versus `BeanPostProcessor` `[T]`

`BeanFactoryPostProcessor` operates on *definitions* before any singleton is created (step 5). `BeanPostProcessor` operates on *instances*, wrapping each bean before and after initialization (step 11).

The warning appears because a `BeanFactoryPostProcessor` must itself be instantiated in step 5 - before `registerBeanPostProcessors` in step 6. If it injects a normal bean, that bean is force-created early, missing every `BeanPostProcessor` that has not been registered yet. Practically, the bean never gets its AOP proxy, so `@Transactional` on it silently does nothing.

Fix: make the post-processor `static` when declared as a `@Bean` method, depend only on `Environment` or `BeanFactory`, and look dependencies up lazily rather than injecting them.

### Q4. Full versus lite `@Configuration` `[T]`

In **full mode** (`proxyBeanMethods = true`, the default), `ConfigurationClassPostProcessor` enhances the class with a CGLIB subclass whose `BeanMethodInterceptor` routes every `@Bean` method call through the container. In **lite mode** (`proxyBeanMethods = false`, or `@Bean` methods on a plain `@Component`), no subclass is created and `@Bean` methods are ordinary Java methods.

`proxyBeanMethods = false` saves a CGLIB class and some startup time, which is why every Boot auto-configuration class uses it. It is **unsafe when one `@Bean` method calls another** - you get a new, unmanaged instance each time, with no proxying, no lifecycle callbacks and no singleton guarantee. The safe pattern in lite mode is to take the dependency as a method parameter instead:

```java
@Bean OrderService orderService(OrderRepository repo) { return new OrderService(repo); }
```

### Q5. Inter-bean method calls

In full mode the CGLIB interceptor checks whether the container is currently creating that bean. If not, it delegates to `beanFactory.getBean(name)` and returns the existing singleton rather than executing the method body. That is why `@Bean` methods look like plain calls but respect scope.

It also means a `@Configuration` class cannot be `final` and its `@Bean` methods cannot be `private` or `final` - the same CGLIB constraints as any Spring proxy.

### Q6. `FactoryBean<T>`

A `FactoryBean<T>` is a bean whose job is to produce another object; the container publishes `getObject()` as the bean, not the factory. It exists for complex or conditional construction, and for integration points where the target type is only known at runtime - `SqlSessionFactoryBean`, `LocalContainerEntityManagerFactoryBean` and `ProxyFactoryBean` are all examples.

Prefix the name with `&` to get the factory itself: `context.getBean("&entityManagerFactory")`.

A `@Bean` method is simpler and type-safe, so in application code prefer it. `FactoryBean` earns its place when you need the container to know the produced type before creating it (via `getObjectType()`), which matters for autowiring by type during early resolution.

### Q7. Deferred lookup `[T]`

`ObjectProvider<T>` is the right answer in almost all cases: it is type-safe, supports optional (`getIfAvailable`), unique (`getIfUnique`), streaming and ordered access, and defers resolution to call time without a proxy. It is the modern replacement for both `@Lazy` tricks and container lookups.

`@Lazy` injects a proxy that resolves on first method call - useful to break a cycle, but the indirection is invisible at the call site. `ApplicationContext.getBean()` couples your code to the container and is untestable without Spring; it is acceptable only in infrastructure code.

### Q8. The three-level singleton cache

`DefaultSingletonBeanRegistry` holds three maps: `singletonObjects` (fully initialized), `earlySingletonObjects` (instantiated but not fully populated) and `singletonFactories` (`ObjectFactory` references able to produce an early reference).

Creating A: an entry goes into `singletonFactories` immediately after instantiation but before population. A populates and needs B; B is created, needs A, finds the factory, obtains the early reference, completes, and A then finishes. The third level exists specifically so that if A must be proxied, the factory returns the *proxy* rather than the raw instance, keeping references consistent.

### Q9. `@Lazy` on a cycle `[T]`

The injected object is a proxy, not the bean. Nothing is resolved until the first method call, which breaks the construction cycle.

Consequences: the real bean's creation failure surfaces at first use rather than at startup, losing fail-fast; the proxy adds a level of indirection to every call; and if the target is `final` or has no interface, CGLIB constraints apply. It works, but a cycle is nearly always a missing third collaborator, so I treat `@Lazy` as a temporary stabilizer rather than the fix.

### Q10. Ordering annotations

- `@Order` / `Ordered` - orders beans *in a collection* (injected `List`, aspect precedence, filter order, `ApplicationListener` order). Lower value wins.
- `@Priority` - JSR-250 equivalent, and unlike `@Order` it also participates in single-bean autowire candidate selection when several match.
- `@DependsOn` - forces *creation order*, not collection order. Used when a bean has an initialization side effect another bean relies on.

None of them affects the order in which `@Bean` methods are declared, which the container treats as an implementation detail.

### Q11. Injected `List` ordering `[T]`

You get them in `@Order` order if annotated; otherwise in an order derived from registration - component scanning order, which depends on classpath and filesystem traversal. It is stable enough to be relied on accidentally and unstable enough to break when you change build tooling or JAR ordering.

Make it explicit: annotate each handler with `@Order`, or inject a `Map<String, Handler>` and select by key, or sort at the injection point with `Comparator.comparingInt(Handler::priority)` so ordering is a property of your domain rather than of the container.

### Q12. Autowire resolution order

1. Match by type. If exactly one candidate, done.
2. If several, a `@Primary` candidate wins.
3. Otherwise `@Priority` (lowest value) wins.
4. Otherwise a `@Qualifier` on the injection point is matched against qualifiers or bean names.
5. Otherwise the field or parameter *name* is matched against bean names.
6. Otherwise `NoUniqueBeanDefinitionException`.

Step 5 is the one that surprises people: renaming a constructor parameter can change which bean is injected. That is a strong argument for explicit `@Qualifier` on any type with multiple implementations.

### Q13. Generic type injection

Erasure removes the type argument from *values*, but not from the declaration site. Spring reads generic information from the class metadata via `ResolvableType`, which walks the declared supertypes and field or parameter signatures, so `OrderRepository implements Repository<Order>` is matchable against `Repository<Order>`.

This is what makes `List<Handler<OrderEvent>>` injection resolve to only the handlers for that event type - genuinely useful for typed dispatch, and it is the same mechanism behind `ParameterizedTypeReference`.

### Q14. Import mechanisms

- `ImportSelector` - returns configuration class names to register, evaluated during configuration parsing. Use for "include these configurations based on an annotation attribute".
- `DeferredImportSelector` - the same but deferred until all other configuration classes are processed, so user beans exist and `@ConditionalOnMissingBean` can back off correctly. **This is what auto-configuration uses**, which is precisely why your beans always win over Boot's.
- `ImportBeanDefinitionRegistrar` - registers `BeanDefinition`s programmatically. Use when the beans are derived from scanning or from metadata rather than being statically declared - Spring Data repositories, Feign clients and MyBatis mappers all use it.

### Q15. The `@Enable*` pattern

`@Enable*` is a meta-annotation carrying an `@Import` of either a `@Configuration` class, an `ImportSelector` or an `ImportBeanDefinitionRegistrar`, plus attributes that the imported component reads from the annotation metadata.

`@EnableTransactionManagement` imports a selector that chooses proxy-based or AspectJ-based configuration from the `mode` attribute, and registers the advisor and auto-proxy creator. Understanding this makes the whole "how does the annotation do anything" question trivial: the annotation is just metadata, the imported class does the work.

### Q16. Initialization callbacks

- `@PostConstruct` - per-bean, after dependency injection. The default choice.
- `InitializingBean.afterPropertiesSet` - identical timing, but couples you to Spring. Avoid in application code.
- `SmartInitializingSingleton.afterSingletonsInstantiated` - runs once after *all* singletons exist. Use when you must inspect or wire up other beans.
- `SmartLifecycle` - `start`/`stop` with a phase, tied to context lifecycle rather than bean creation. Use for anything that opens a resource or consumes traffic: message listeners, schedulers, background pollers. It gives you ordered startup and, importantly, ordered *shutdown* with `stop(Runnable)` for graceful draining.

The rule I apply: bean setup goes in `@PostConstruct`, but anything that starts consuming work goes in `SmartLifecycle` so it can be stopped cleanly.

### Q17. `@PostConstruct` self-invocation `[T]`

Two separate reasons, and naming both is the strong answer. First, `@PostConstruct` runs during initialization, *before* `postProcessAfterInitialization` creates the proxy - so at that moment the proxy does not yet exist. Second, even after startup, calling `this.method()` never crosses the proxy.

So a `@PostConstruct` that calls a `@Transactional` method runs without a transaction, and one that calls `@Async` runs synchronously on the startup thread - which can also deadlock startup if it waits on something the context has not started yet.

Fix: move the work to an `ApplicationRunner`, an `@EventListener(ApplicationReadyEvent.class)`, or `SmartLifecycle`, all of which run after the context is fully initialized and go through the proxy.

### Q18. `ApplicationListener` versus `@EventListener`

`@EventListener` is the annotation-driven form, resolved by `EventListenerMethodProcessor`; it supports a SpEL `condition`, multiple event types, and returning a value that is published as a further event. `ApplicationListener<T>` is the interface form, and is the only one that works for events published *before* the annotation processor runs - which is why Boot's own early listeners implement the interface.

Both are synchronous by default and share the publishing thread, so a listener throwing an exception propagates to the publisher and, inside a transaction, rolls it back. Order with `@Order`.

Built-in events worth naming: `ApplicationStartingEvent`, `ApplicationEnvironmentPreparedEvent`, `ContextRefreshedEvent`, `ApplicationReadyEvent` (the correct hook for "start doing work"), `ContextClosedEvent`.

### Q19. `@TransactionalEventListener` phases

The listener is bound to a transaction synchronization rather than firing immediately.

- `BEFORE_COMMIT` - still inside the transaction; a write here is part of the same commit. This is where an outbox row can be written.
- `AFTER_COMMIT` (default) - the data is durable. **This is where you publish to Kafka or send an email**, because you must not tell the world about something that might roll back.
- `AFTER_ROLLBACK` and `AFTER_COMPLETION` - compensation and cleanup.

The important caveat: if no transaction is active, the listener does not fire at all unless you set `fallbackExecution = true`. That silently breaks tests and non-transactional call paths.

### Q20. Async application events `[T]`

Making the multicaster async (set a `TaskExecutor` on `SimpleApplicationEventMulticaster`, or annotate listeners `@Async`) changes four things: the publisher no longer sees listener exceptions, so failures vanish unless you register an error handler; the listener no longer participates in the publisher's transaction, so `@TransactionalEventListener` semantics change; `ThreadLocal` state - security context, MDC, tenant, tracing - is not propagated; and ordering guarantees are gone.

Propagate context with a `TaskDecorator` on the executor that copies the `SecurityContext`, MDC and Micrometer observation scope. And be honest about what you have built: an async in-memory listener with no durability is not a message queue, so if the work must survive a crash it belongs in an outbox.

### Q21. `Aware` interfaces

`BeanNameAware`, `BeanFactoryAware`, `ApplicationContextAware`, `EnvironmentAware`, `ResourceLoaderAware`, `ApplicationEventPublisherAware`, `MessageSourceAware`. They are callbacks that hand a bean a piece of container infrastructure during initialization.

In application code they are a smell - they couple your class to Spring and make it untestable without a context. They are legitimate in *infrastructure* code: a custom `BeanPostProcessor` or `Scope` implementation genuinely needs the `BeanFactory`, and `ApplicationEventPublisherAware` is occasionally cleaner than injecting the publisher. For everything else, inject what you need.

### Q22. Placeholder resolution

`Environment` holds an ordered `MutablePropertySources` list; resolution walks it and the first source containing the key wins - that ordering *is* the configuration precedence rule.

`PropertySourcesPlaceholderConfigurer` is a `BeanFactoryPostProcessor` that visits every bean definition and resolves `${...}` in its property values and constructor arguments *before instantiation*. Because it is a `BeanFactoryPostProcessor`, it must be declared `static` when defined as a `@Bean` method, or it will be created too early and pull other beans with it.

`@Value` on a field is resolved later, by `AutowiredAnnotationBeanPostProcessor` at injection time, using the same `Environment`.

### Q23. Custom scopes

Implement `org.springframework.beans.factory.config.Scope` (`get`, `remove`, `registerDestructionCallback`) and register it with `beanFactory.registerScope("tenant", new TenantScope())` from a `BeanFactoryPostProcessor`, then use `@Scope("tenant")`.

`SimpleThreadScope` is the built-in thread scope, and the trap is that **it does not call destruction callbacks** - it has no way to know a thread is finished, so `@PreDestroy` never runs and anything holding a resource leaks in a pooled thread. Real thread-bound state should use `RequestScope` in a web app, or an explicit context object you manage.

### Q24. Scoped proxies `[T]`

`@Scope(value = "request", proxyMode = TARGET_CLASS)` injects a CGLIB proxy into the singleton. Every method call on it resolves the *current* request's instance from the scope and delegates. Without the proxy, the singleton would capture one request's bean forever.

Called outside its scope, you get `BeanCreationException: Scope 'request' is not active for the current thread` - which is exactly what happens on an `@Async` thread, in a `@Scheduled` job, or in a Kafka listener, since none of those has a bound request. That is one of the most common "works in the controller, fails in the background job" bugs.

### Q25. `BeanFactory` versus `ApplicationContext`

`BeanFactory` is the bare DI container. `ApplicationContext` extends it with event publication, message source and internationalization, resource loading, `Environment`, automatic registration of `BeanPostProcessor`s and `BeanFactoryPostProcessor`s, and eager singleton instantiation.

In 2026 the distinction is mostly historical - you always use an `ApplicationContext`. It remains worth knowing because it explains the layering (`ApplicationContext` *has a* `BeanFactory`, obtained in step 2 of refresh) and because `BeanFactory` is still the type you interact with in infrastructure extension points.

### Q26. Auto-proxying warnings `[A]`

The warning "is not eligible for getting processed by all BeanPostProcessors" means a bean was instantiated during step 5 or 6, before the post-processor registry was complete. The consequence is silent: that bean never receives its AOP proxy, so `@Transactional`, `@Async`, `@Cacheable`, metrics and security on it do nothing at all.

Diagnosis: read the warning carefully - it names the bean and often the post-processor that caused early instantiation. The usual culprits are a non-static `@Bean` `BeanFactoryPostProcessor`, a `BeanPostProcessor` that injects application beans, and `@Autowired` on infrastructure configuration such as a `DataSource` used by a post-processor.

Fixes: declare post-processors `static`, inject `ObjectProvider` and resolve lazily, or take `BeanFactory` and look up on demand. I treat these warnings as build-failing, because a silently non-transactional service is far worse than a startup error.

> *Hook: a service where metrics and transactions were silently absent because of an eagerly created post-processor.*

---

## 2. Configuration, properties and profiles

### Q27. The `ConfigData` API

Boot 2.4 replaced `ConfigFileApplicationListener` with a `ConfigDataLocationResolver` / `ConfigDataLoader` SPI. The visible change is that configuration is now loaded in a **strict, document-order** model: files are processed in the order they are declared, and later documents override earlier ones, including profile-specific documents.

Under the old model profile-specific files were layered on afterwards regardless of position. Under the new one, `application-prod.yml` overrides `application.yml` because it is processed later, but a profile document *within* a file only overrides documents above it. The SPI is also the extension point that lets `spring.config.import` pull configuration from Vault, Consul or AWS.

### Q28. Boot 2.4 configuration upgrade `[T]`

Three specific breakages:

1. `spring.profiles.active` is **not allowed** inside a profile-specific document or a document that itself is profile-activated - it throws `InactiveConfigDataAccessException`. Profile activation must happen in the top-level document, or use profile *groups*.
2. `spring.profiles` was replaced by `spring.config.activate.on-profile`.
3. Override ordering changed, so a value you expected to win may now lose depending on document order.

The escape hatch is `spring.config.use-legacy-processing=true`, which was removed in Boot 2.6 - so it buys you one release to migrate, no more. My approach is to write a test that asserts the effective value of the twenty properties that actually matter per profile, then upgrade; guessing from documentation does not survive contact with a real configuration tree.

### Q29. `spring.config.import`

It declaratively imports additional configuration sources at the right point in the precedence chain, rather than bolting them on in a listener:

```yaml
spring:
  config:
    import:
      - "aws-parameterstore:/prod/orders/"
      - "aws-secretsmanager:/prod/orders/db"
      - "optional:file:/etc/orders/override.yml"
```

Without the `optional:` prefix a missing source **fails startup**, which is exactly what you want for a mandatory secret store - the alternative is a service that starts with empty credentials and fails at first request. Imports are processed after the importing document, so the imported values override it.

### Q30. Relaxed binding

For `myApp.connectionTimeout`, all of these bind: `myApp.connectionTimeout`, `my-app.connection-timeout`, `my_app.connection_timeout`, `MYAPP_CONNECTIONTIMEOUT`.

Environment variables must use the **upper-case underscore** form (`MYAPP_CONNECTIONTIMEOUT`), because that is the only form many shells and orchestrators permit. Kebab-case is the recommended canonical form in properties files, and it is what you should write in documentation.

Relaxed binding applies to `@ConfigurationProperties` only - **`@Value` does exact matching**, which is one more reason to prefer type-safe binding.

### Q31. `@ConfigurationProperties` versus `@Value`

`@ConfigurationProperties` gives you relaxed binding, nested objects, `List` and `Map` binding, JSR-303 validation with `@Validated`, IDE metadata, and constructor binding for immutability:

```java
@ConfigurationProperties("orders.http")
@Validated
record OrdersHttpProperties(@NotNull URI baseUrl, @DurationUnit(SECONDS) Duration timeout) {}
```

Records and constructor binding mean the object is immutable and cannot be half-configured. Register with `@EnableConfigurationProperties` or `@ConfigurationPropertiesScan`.

`@Value` is appropriate only for a single scalar, or when you genuinely need SpEL. It offers no validation, no relaxed binding and no metadata.

### Q32. `@Value` limitations `[T]`

`@Value("${my.list}")` on a `List<String>` fails because `@Value` performs simple placeholder substitution followed by a conversion - a YAML list is stored as indexed keys (`my.list[0]`, `my.list[1]`), not as a single comma-joined value. You must either use a comma-separated property with `@Value("${my.list}") List<String>` (which works only because of the `String` to collection converter), or use SpEL `#{'${my.list}'.split(',')}`, or - correctly - use `@ConfigurationProperties`, which binds indexed keys natively.

Mixing `@Value` into a `@ConfigurationProperties` class is worse: with constructor binding the `@Value` is ignored entirely, and with setter binding it creates two competing binding mechanisms on one object, so the value depends on which ran last. Keep the two mechanisms in separate classes.

### Q33. Fail-fast configuration validation

Annotate the properties class `@Validated` and put JSR-303 constraints on the fields. Binding failures then throw at context startup with a precise report naming the property, the invalid value and the constraint.

For rules that constraints cannot express, add a `@PostConstruct` validation method, or implement `Validator` and register it as `configurationPropertiesValidator`. For cross-cutting checks - "if `feature.x` is enabled then `feature.x.endpoint` must be set" - I prefer an `ApplicationRunner` that throws, because the message can be domain-specific.

The principle is worth stating: a service should refuse to start rather than start misconfigured. A crash loop is visible in thirty seconds; a service silently pointing at the wrong queue is discovered by a customer.

### Q34. Custom converters

Binding uses a `Converter` registry. To bind a custom type - a `Money`, a `Duration` in a non-standard format, a comma-separated set of enums - register a `Converter<String, T>` annotated `@ConfigurationPropertiesBinding`:

```java
@Component
@ConfigurationPropertiesBinding
class StringToMoneyConverter implements Converter<String, Money> { ... }
```

The annotation is required; without it the converter is registered for MVC binding but not for configuration binding, which is a confusing failure because the same converter works elsewhere.

### Q35. Profiles

`@Profile` supports expressions: `@Profile("prod & !legacy")`. Profile *groups* let one profile activate several: `spring.profiles.group.prod=prod,metrics,secure`.

Profile-conditional **beans** are risky because they create code paths that no test exercises. If `prod` has a different implementation than `dev`, then your test suite verifies the `dev` behavior and production runs code that was never integration-tested - and the divergence is invisible in code review.

My rule: profiles select *configuration values* and infrastructure adapters (a real S3 client versus LocalStack), never business logic. Where behavior must differ, use a feature flag that can be toggled in any environment, so both branches are testable.

### Q36. Profile activation precedence `[T]`

`spring.profiles.active` **replaces** the active set - the highest-precedence property source that defines it wins outright, so setting it on the command line discards what is in `application.yml`. `spring.profiles.include` is **additive** and unconditionally adds profiles regardless of what is active. Profile groups expand a profile into several when it is activated.

The trap is combining them: `include` cannot be used to conditionally add, and defining `active` in multiple sources does not merge - people expect union semantics and get replacement. Since Boot 2.4, `include` in a profile-specific document is also restricted. When it gets complicated, groups are the maintainable answer.

### Q37. Configuration metadata

`spring-configuration-metadata.json` describes your properties - name, type, description, default, deprecation - and is what gives IDE auto-completion and validation. It is generated at build time by adding `spring-boot-configuration-processor` as an annotation processor.

For a shared starter it is not cosmetic: it is the documentation, and it is the mechanism for deprecating a property gracefully (`@DeprecatedConfigurationProperty` with a replacement) so forty consuming teams see a warning in their IDE rather than discovering the change at runtime. I treat missing metadata in a platform starter as a defect.

### Q38. `@RefreshScope`

A `@RefreshScope` bean is a scoped proxy over a bean stored in a refreshable scope. On `/actuator/refresh` or a Config Server bus event, the cached instance is discarded; the next method call recreates it with the new `Environment` values.

Its limits are what matter: it only affects beans in that scope, so a value injected into a *singleton* is not refreshed; `@ConfigurationProperties` beans are rebound but objects constructed *from* them at startup are not; and infrastructure already built with the old value - a connection pool, a `WebClient` with a base URL, a Kafka consumer - keeps the old configuration. Recreating a `DataSource` at runtime is also genuinely risky.

So it works for simple behavioral flags and thresholds. For anything structural I prefer a restart or a rolling deployment, because a partially refreshed application is harder to reason about than a restarted one.

### Q39. SpEL

SpEL is evaluated by the container at bean creation for `@Value("#{...}")`, and at invocation time for `@PreAuthorize`, `@Cacheable(key)`, `@EventListener(condition)` and similar. It can read bean properties, call methods, index collections, and reference other beans by name (`@beanName`), which makes it powerful and dangerous.

The injection risk is real: SpEL can invoke arbitrary methods including `T(java.lang.Runtime).getRuntime().exec(...)`. **Never build a SpEL expression from user input** - that is remote code execution, and it has been the mechanism behind several high-profile Spring CVEs. Expressions must be static strings in code; user data may only arrive as *parameters* referenced by the expression (`#userId`), never as expression text.

### Q40. `${}` versus `#{}` `[T]`

`${...}` is a property placeholder, resolved by `PropertySourcesPlaceholderConfigurer` against the `Environment`. `#{...}` is SpEL, evaluated by the expression parser against the bean factory.

Placeholders are resolved **first**, so nesting works in one direction only: `#{'${app.list}'.split(',')}` is valid because the placeholder is substituted into the expression before parsing. The reverse - a SpEL result used as a property key - does not work.

Practical guidance: use `${}` for configuration, and reach for `#{}` only when you need computation. Most `#{}` usage in application code is better expressed as a `@ConfigurationProperties` field with a typed converter.

### Q41. Keeping secrets out of the process

Layered, because any single control leaks eventually:

- Load from Secrets Manager or Parameter Store via `spring.config.import`, with the workload assuming an IAM role - no static credentials anywhere.
- Never put secrets in `@ConfigurationProperties` objects that Actuator can serialize; Boot sanitizes keys matching `password`, `secret`, `key`, `token` and URIs with credentials, but it sanitizes by **key name**, so a field called `connectionString` or `dsn` containing a password is printed in full.
- Set `management.endpoint.env.show-values=never` and `management.endpoint.configprops.show-values=never` (Boot 3), and keep `/env`, `/configprops` and `/heapdump` off the exposed set entirely.
- Wrap secret values in a holder type whose `toString()` returns `****`, so an accidental log statement or exception message cannot leak them.
- For the highest sensitivity, fetch at use time with a short cache rather than binding at startup, so the value is not resident for the process lifetime and rotation takes effect without a restart.

Plus the basics: secret scanning in CI and pre-commit, and treating any secret that reaches git history as compromised.

### Q42. Configuration across 40 services `[A]`

I separate three kinds of configuration, because conflating them is what creates drift:

1. **Platform defaults** - timeouts, connection pool sizing, logging format, metrics tags, security headers. These belong in a shared starter with sensible defaults and `@ConditionalOnMissingBean` back-off, so a team gets them by adding one dependency and can override any of them. Versioned and released like any library.
2. **Environment configuration** - endpoints, credentials, capacity. These come from the deployment mechanism: Parameter Store or Secrets Manager per environment, injected via `spring.config.import`, defined in the same Terraform that creates the resource being pointed at. That way the URL and the thing it points to cannot drift apart.
3. **Service-specific configuration** - genuinely local, lives in the repository as `@ConfigurationProperties` with validation.

Then enforcement: a startup check that fails if a required platform property is missing, metadata so overrides are discoverable, and a periodic report of which services are on which starter version. What I explicitly avoid is a central Config Server as the runtime source of truth on Kubernetes - it adds a hard startup dependency and a new outage mode for a problem the platform already solves.

> *Hook: the shared starter you built or adopted, and the drift it eliminated.*

---

## 3. AOP and proxies

### Q43. Proxy creation

`AnnotationAwareAspectJAutoProxyCreator` is a `SmartInstantiationAwareBeanPostProcessor` registered by `@EnableAspectJAutoProxy` (or by Boot's AOP auto-configuration). During `postProcessAfterInitialization` - step 11 of refresh - it collects all `Advisor` beans plus `@Aspect` classes, asks each whether its pointcut matches the bean's class, and if any match it wraps the bean in a proxy built by `ProxyFactory`.

Everything else follows from that single fact: proxies are per-bean, created after initialization, and the container hands the *proxy* to whoever injects the bean, while the target's own `this` reference still points at the raw object.

### Q44. Pointcut designators

- `execution(* com.acme.service.*Service.*(..))` - the general-purpose one, matching method signatures.
- `within(com.acme.service..*)` - all joinpoints inside a type or package. Cheaper to evaluate.
- `@annotation(com.acme.Audited)` - methods carrying an annotation. My most-used designator, because it makes the aspect opt-in and visible at the call site.
- `@within` / `@target` - types carrying an annotation.
- `bean(*Repository)` - Spring-specific, matches by bean name.
- `args(String, ..)` - argument runtime types; `this()` and `target()` match the proxy and target types.

A realistic combination: `@annotation(audited) && within(com.acme..*)` with the annotation bound as a parameter so the advice can read its attributes.

### Q45. `this()` versus `target()` `[T]`

`this()` matches when the **proxy** is an instance of the given type; `target()` matches when the **target object** is.

Under CGLIB the proxy is a subclass of the target, so both match. Under a JDK dynamic proxy the object implements only the interfaces - it is *not* an instance of the implementation class - so `this(OrderServiceImpl)` fails to match while `target(OrderServiceImpl)` succeeds.

Practical rule: use `target()` when you mean the implementation type, and be aware that a pointcut which works under Boot's CGLIB default can break if something forces JDK proxying.

### Q46. Advice order

Around a single join point, for one aspect: `@Around` (before the proceed) → `@Before` → **method** → `@AfterReturning` or `@AfterThrowing` → `@After` → `@Around` (after the proceed).

`@After` is a finally block - it runs on both paths. `@Around` must call `proceed()` and return its result; forgetting to return it silently makes methods return `null`, which is a memorable production bug.

With multiple aspects the highest-precedence aspect wraps the others entirely, so its `@Before` runs first and its `@After` runs last - the standard nesting model.

### Q47. Multiple aspects `[T]`

Precedence comes from `@Order` or `Ordered` on the **aspect class** (lower value = higher precedence = outermost). Two advice methods *within the same aspect* on the same join point have **undefined** relative order - the specification does not guarantee it, and it has changed between versions. If you need a defined order, put them in separate aspects.

Without `@Order`, ordering is undefined and depends on bean registration. That is fine until an aspect that logs and an aspect that opens a transaction produce log lines outside the transaction, or a security aspect runs after an auditing aspect that has already recorded the action as permitted. Always order aspects that interact.

### Q48. `@Transactional` + `@Async` + `@Cacheable` `[T]`

Each is implemented by its own advisor with a defined order: `@Async` is `Ordered.LOWEST_PRECEDENCE`, `@Transactional` and `@Cacheable` are also `LOWEST_PRECEDENCE` by default but the async advisor is registered such that async typically wraps the others.

The practical answer is that **you should never stack all three**, because the semantics are incoherent:

- `@Async` returns immediately, so `@Cacheable` caches a `CompletableFuture`, not a value (before Spring 6.1 it cached the future object itself, which meant subsequent callers shared one in-flight computation - sometimes desirable, usually surprising).
- The transaction begins on the async thread, not the caller's, so the caller's transaction neither includes nor waits for it.
- If the async method fails, the caller has already returned success.

The clean design is one annotation per method and explicit composition: a cached, transactional method, called by a thin `@Async` wrapper in a different bean - which also solves the self-invocation problem.

### Q49. `@Transactional` advisor order

`AbstractTransactionManagementConfiguration` registers the transaction advisor at `Ordered.LOWEST_PRECEDENCE`, so it is the **innermost** advice by default - closest to your method, with other aspects wrapping it.

You change it when an aspect must run *inside* the transaction (an auditing aspect that writes a row must be inside, or its write is not part of the commit) or *outside* it (a retry aspect must be outside, or it retries within an already rollback-marked transaction and every attempt fails). Set `@EnableTransactionManagement(order = ...)` or order the other aspects explicitly. Getting retry and transaction ordering backwards is a classic, and it produces `UnexpectedRollbackException` under load.

### Q50. Everything self-invocation breaks `[T]`

Any annotation implemented by a Spring AOP proxy stops working on an internal call: `@Transactional`, `@Async`, `@Cacheable` / `@CachePut` / `@CacheEvict`, `@PreAuthorize` / `@PostAuthorize` / `@Secured`, `@Retryable` / `@Recover`, `@Validated` method validation, `@Timed` and `@Observed`, `@CircuitBreaker` / `@RateLimiter` / `@Bulkhead`, and any custom aspect you write.

It also fails for `private`, `final` and `static` methods, and for calls made before the proxy exists (`@PostConstruct`).

Detection: an ArchUnit rule or a Sonar rule flagging internal calls to annotated methods, because this is not something code review reliably catches. The fix is almost always to extract the annotated method into a collaborating bean, which usually improves the design anyway.

### Q51. AspectJ weaving

Spring AOP is proxy-based: method execution join points only, on Spring beans only, and never on self-invocation. AspectJ weaves bytecode - at compile time (CTW) or class load time (LTW, `-javaagent:aspectjweaver.jar` plus `@EnableLoadTimeWeaving`) - and can therefore advise private methods, constructors, field access, static methods, self-invocation, and objects Spring does not manage.

The cost is significant: a build or launch dependency, harder debugging because the code you read is not the code that runs, slower builds, and behavior that surprises anyone who has not been told weaving is enabled. Native image and AOT support is also weaker.

I have used LTW exactly where proxying could not work - domain objects instantiated with `new` needing injection (`@Configurable`). For everything else the proxy limitation is a design signal, not an obstacle to route around.

### Q52. The cache annotations

`@Cacheable` checks then stores; `@CachePut` always executes and stores; `@CacheEvict` removes (with `allEntries` and `beforeInvocation` options).

Keys come from `SimpleKeyGenerator` (all parameters combined) unless you supply `key` as SpEL - and you nearly always should, because the default silently changes when someone adds a parameter. `condition` is evaluated **before** invocation on the arguments; `unless` is evaluated **after**, so it can reference `#result`.

`sync = true` makes concurrent callers for the same key wait for one computation instead of all recomputing. It only works on `@Cacheable`, cannot be combined with `unless` or multiple caches, and is supported only by cache implementations that provide atomic get-with-loader - Caffeine yes, plain Redis no.

### Q53. Caching `Optional` and `CompletableFuture` `[T]`

Spring unwraps `Optional` and stores the **contained value**, returning a fresh `Optional` on a hit. So the cache holds `Customer`, not `Optional<Customer>` - which is what you want, and it means an empty `Optional` is cached as `null`.

`CompletableFuture` was historically cached **as the future object**, meaning every hit returned the same completed future - usually harmless, occasionally a leak, and definitely surprising if the future was still pending. Spring Framework 6.1 added first-class support for `CompletableFuture` and reactive return types, unwrapping the value on completion. If you are on an older baseline, do not put `@Cacheable` on an async method - cache the synchronous method it delegates to.

### Q54. Nulls and exceptions in `@Cacheable` `[T]`

`null` **is** cached by default, and that is deliberate - it prevents repeated lookups for missing keys (a cheap defense against cache-penetration). Suppress it with `unless = "#result == null"`. Redis is the exception: `RedisCacheConfiguration.disableCachingNullValues()` makes a null throw instead, so behavior differs by cache provider - worth knowing when a service behaves differently after moving from Caffeine to Redis.

An exception caches **nothing** and propagates. So a method failing intermittently produces no negative caching, and every caller hits the failing downstream - which is why `@Cacheable` is not a substitute for a circuit breaker.

### Q55. Redis-backed caching

Three things to get right:

- **Serialization.** The default JDK serialization is unreadable, fragile across class changes, and a deserialization risk. Configure `GenericJackson2JsonRedisSerializer` or a typed serializer, and version the cached payload so a deployment that changes the DTO shape does not read garbage - I include a schema version in the cache name.
- **TTL per cache.** `RedisCacheManagerBuilder.withCacheConfiguration(name, config.entryTtl(...))`. A single global TTL is always wrong for some cache.
- **Stampede.** Redis has no atomic loader, so `sync = true` does not protect you; N instances all miss and all hit the database. Mitigate with jittered TTLs, a short local Caffeine tier in front of Redis (which also cuts network calls dramatically), and a distributed lock or probabilistic early refresh for genuinely hot keys.

Also decide the failure mode explicitly: if Redis is down, `@Cacheable` throws by default and takes your service with it. Register a `CacheErrorHandler` that logs and falls through to the method, so a cache outage degrades performance rather than availability.

### Q56. Spring Retry

`@Retryable(retryFor = ..., maxAttempts = 3, backoff = @Backoff(delay = 200, multiplier = 2, random = true))` with `@Recover` for the fallback, enabled by `@EnableRetry`. It is proxy-based, so the usual self-invocation rule applies.

Two interactions matter. **Transactions**: if retry is *inside* the transaction advisor, every attempt runs in the same already-marked-rollback-only transaction and all fail - retry must be the outer advice, which means retrying at a boundary that starts a fresh transaction per attempt. **Idempotency**: retrying a non-idempotent operation duplicates work; if the first attempt partially succeeded before failing, the retry compounds it.

So my rule is: retry only idempotent operations, only at a boundary that resets state, only on transient exception types (never on validation failures), and always with jittered backoff and a bounded attempt count. For anything cross-service I prefer Resilience4j so the retry composes with a circuit breaker.

### Q57. `@Validated` versus `@Valid`

`@Valid` on a controller parameter is handled by Spring MVC's argument resolver during binding, and a failure produces `MethodArgumentNotValidException`, which `ResponseEntityExceptionHandler` maps to a 400.

`@Validated` on a **class** activates `MethodValidationPostProcessor`, an AOP proxy that validates method parameters and return values on any Spring bean - services, not just controllers. A failure produces `ConstraintViolationException`, which nothing handles by default, so it surfaces as a 500 unless you add an `@ExceptionHandler`. That mismatch is the trap.

`@Validated` also carries validation **groups**, which `@Valid` cannot: `@Validated(OnCreate.class)`. Spring 6.1 improved method validation so that constraints on controller method parameters produce `HandlerMethodValidationException` instead, which is handled properly - worth knowing on a modern baseline.

### Q58. Aspect versus decorator `[A]`

I use an aspect when the concern is genuinely cross-cutting - it applies to many types, is not part of their contract, and the alternative is the same three lines repeated everywhere. Auditing, metrics, tracing and security fit.

I use a decorator or an explicit call when the behavior is part of the domain, when it applies to one or two types, or when the reader needs to see it at the call site. A caching decorator around one repository is clearer than an aspect matching a pointcut declared in a different package.

The deciding question is debuggability: an aspect makes behavior invisible in the code you are reading, and a team unfamiliar with it will lose hours. So I require any aspect to be opt-in via an annotation rather than matched by package or naming convention - `@Audited` on the method tells the next reader something happens here, while `execution(* com.acme.service..*(..))` does not.

---

## 4. Transactions in depth

### Q59. `PlatformTransactionManager`

`getTransaction(definition)` asks the manager whether a transaction is already bound to the thread; if so it applies the propagation rule (join, suspend, nest, or throw), otherwise it starts a new one - acquiring a `Connection`, setting auto-commit false and applying isolation and timeout - and binds the resource to `TransactionSynchronizationManager`.

It returns a `TransactionStatus` carrying whether the transaction is new, whether a savepoint exists, the suspended resources of an outer transaction, and the rollback-only flag. `commit(status)` either really commits (if new) or, for a participating transaction, does nothing except propagate the rollback-only flag upward. `rollback(status)` either rolls back or marks the outer transaction rollback-only.

That "participating transactions do not really commit" behavior is the mechanism behind `UnexpectedRollbackException`.

### Q60. `TransactionSynchronizationManager`

It is a set of `ThreadLocal`s holding: a **resource map** (keyed by `DataSource` or `EntityManagerFactory`, valued with the bound `ConnectionHolder` or `EntityManagerHolder`), a list of **synchronizations**, and flags for the current transaction name, isolation, read-only status and active state.

`DataSourceUtils.getConnection(dataSource)` and `EntityManagerFactoryUtils.doGetTransactionalEntityManager(...)` consult that map, which is precisely how `JdbcTemplate` and a JPA repository end up on the *same* connection inside one `@Transactional` method without either knowing about the other.

It is also why everything transaction-related is thread-bound, and therefore why `@Async`, reactive chains and manually spawned threads do not inherit a transaction.

### Q61. `TransactionSynchronization`

Register one with `TransactionSynchronizationManager.registerSynchronization(...)`. Callbacks:

- `beforeCommit(readOnly)` - still inside the transaction; a write here joins the commit. Used for last-moment validation or writing an outbox row.
- `beforeCompletion()` - before commit or rollback; resource cleanup.
- `afterCommit()` - the data is durable; publish events, send notifications, invalidate caches.
- `afterCompletion(status)` - always runs; unbind and clean up thread state such as MDC or a tenant context.

`@TransactionalEventListener` is a thin, declarative wrapper over exactly this, and knowing that is a good signal in an interview.

### Q62. Writing in `afterCommit` `[T]`

By the time `afterCommit` runs the transaction has committed but the synchronization is still active and the resources are still bound. A repository call there joins that completed transaction: it executes against the bound connection but **nothing will commit it**, so the write is silently lost (or throws, depending on the resource state).

It also happens outside any rollback protection - if the code throws, the original transaction is already durable, so you get a partially applied operation with an exception surfacing to nobody useful.

Correct approach: annotate the listener `@Transactional(propagation = REQUIRES_NEW)` so it runs in a genuinely new transaction, and accept that this is a second, independent commit which may fail on its own - meaning the operation is now eventually consistent and needs retry or reconciliation. If you need atomicity, the write belongs in `BEFORE_COMMIT` instead.

### Q63. `TransactionTemplate`

Programmatic transactions are better when the boundary is not a whole method: a long method where only a small section must be transactional, a loop that commits per batch, a boundary that depends on runtime conditions, or code inside a lambda or callback where an annotation cannot reach.

```java
transactionTemplate.execute(status -> {
    repository.saveAll(batch);
    return null;
});
```

It also makes the transaction boundary *visible*, which for tricky code is a genuine readability win over an annotation whose semantics depend on the proxy. And it sidesteps self-invocation entirely, which occasionally makes it the pragmatic fix in legacy code.

The cost is verbosity and the ease of accidentally holding the transaction open around non-database work - the same sin as a fat `@Transactional`, just harder to spot with a linter.

### Q64. `readOnly = true` `[T]`

It does three different things at three levels, and the answer people miss is that it is a *hint*, not an enforcement:

1. **JDBC**: `Connection.setReadOnly(true)`, which some drivers pass to the server (PostgreSQL sets the transaction read-only and will actually reject writes; MySQL may ignore it).
2. **Hibernate**: sets `FlushMode.MANUAL` and skips taking dirty-checking snapshots of loaded entities. This is the real performance win - on a query loading thousands of entities it meaningfully cuts memory and CPU, because no snapshot copy is retained.
3. **Routing**: an `AbstractRoutingDataSource` can read `TransactionSynchronizationManager.isCurrentTransactionReadOnly()` to send the transaction to a read replica. This is the most common production use.

What it does **not** do: guarantee a write fails. On a driver that ignores the flag, a manual `flush()` or a native query will happily write. So treat it as an optimization and a routing signal, not as a safety control.

### Q65. Transactions without queries `[T]`

Opening a transaction acquires a connection from Hikari immediately and holds it until commit - even if the method never executes a statement, and even if it then spends 400ms calling an HTTP API. With a pool of 20 and a hundred concurrent requests, you exhaust the pool with connections doing nothing.

`LazyConnectionDataSourceProxy` wraps the real `DataSource` and returns a proxy `Connection` that defers acquisition until the first *statement*. The transaction still starts logically; the physical connection is only taken when needed. It also makes read-write routing work correctly, since the routing decision can be deferred until the read-only flag is known.

The caveat: it hides the problem rather than fixing it. A `@Transactional` method making network calls is still wrong. I use the proxy as a safety net and still enforce the boundary rule.

> *Hook: a connection pool exhaustion incident where transactions spanned an external call.*

### Q66. Multiple data sources

With more than one `DataSource`, Boot's auto-configuration backs off and you must declare everything explicitly: two `DataSource` beans (one `@Primary`), two `LocalContainerEntityManagerFactoryBean`s with distinct `persistenceUnit` names and entity packages, two `PlatformTransactionManager`s, and `@EnableJpaRepositories(basePackages, entityManagerFactoryRef, transactionManagerRef)` per package.

Spring picks the transaction manager by the `transactionManager` attribute on `@Transactional`, falling back to the `@Primary` one. **That fallback is the silent failure**: a method touching the secondary database with a plain `@Transactional` runs under the primary manager, so it gets a transaction on the wrong data source - the secondary operations run in auto-commit, with no rollback and no atomicity, and nothing warns you.

Mitigations: name the qualifier on every `@Transactional` in a multi-data-source application, keep repositories for each data source in strictly separate packages, and add an ArchUnit rule enforcing it. And say the important thing: two data sources in one transaction is not atomic without XA, so design for idempotency and reconciliation instead.

### Q67. `ChainedTransactionManager` `[T]`

It was deprecated (and removed) because it promises something it cannot deliver. It commits the managers in sequence: if manager A commits and manager B then fails, A is already durable and cannot be undone. It is best-effort one-phase commit dressed up as a distributed transaction, so it fails exactly when you need it - under partial failure - and leaves inconsistent state with no record of it.

What to do instead: pick a **single** transactional resource as the source of truth and make everything else eventually consistent from it. The transactional outbox is the canonical pattern - write the state change and the event in one local transaction, relay the event afterwards, and make consumers idempotent. If two databases genuinely must agree atomically, that is either a JTA case or, more often, a signal that the boundary is drawn in the wrong place.

### Q68. JTA and XA

XA gives real two-phase commit across resources via a transaction manager (Atomikos, Narayana, or a Jakarta EE server). It is justified almost nowhere in 2026: it requires XA-capable resources, adds latency for the prepare phase, introduces in-doubt transactions that need manual resolution after a coordinator crash, and the coordinator itself becomes a stateful single point of failure that must be highly available and have durable storage.

I would consider it only for a legacy integration where the alternative is genuinely unacceptable and the resources are both XA-capable and co-located. Otherwise: outbox, idempotency, sagas and reconciliation - which are more code but fail in ways you can observe and recover from.

### Q69. Transaction timeout

`@Transactional(timeout = 5)` sets a deadline on the `TransactionStatus`. Enforcement is cooperative: Spring passes the remaining time to each statement as a JDBC query timeout where the resource supports it, and checks the deadline when a new statement is issued. Hibernate applies it per query.

What it does **not** interrupt: an already-running statement in a driver that ignores query timeout, a network call inside the method, `Thread.sleep`, or in-memory computation. So a method that hangs on an HTTP call will blow through its transaction timeout entirely - the connection stays held and the timeout fires only when the next statement runs.

For that reason I set database-side guards too (PostgreSQL `statement_timeout` and `idle_in_transaction_session_timeout`), because those are enforced by the server regardless of what the application does.

### Q70. `UnexpectedRollbackException` `[T]`

The exact sequence:

1. Outer method `@Transactional` starts a real transaction.
2. Inner method `@Transactional` (default `REQUIRED`) **participates** - no new transaction.
3. The inner method throws a runtime exception. Its transaction advisor calls `rollback`, which - because it is only participating - cannot roll back; it sets `rollbackOnly = true` on the shared transaction.
4. The outer method **catches** the exception and continues normally, believing it handled the failure.
5. The outer advisor calls `commit`, the manager sees `rollbackOnly`, rolls back and throws `UnexpectedRollbackException: Transaction rolled back because it has been marked as rollback-only`.

The lesson is that catching an exception does not undo the rollback marking. Fixes: do not catch and swallow across a transactional boundary; or make the inner method `REQUIRES_NEW` so its failure is genuinely isolated; or check `TransactionAspectSupport.currentTransactionStatus().isRollbackOnly()` before proceeding. The first is usually the right design.

### Q71. `REQUIRES_NEW` self-deadlock `[T]`

The outer transaction updates row X and holds a write lock. It then calls a `REQUIRES_NEW` method, which **suspends** the outer transaction (the lock is still held - suspension does not release locks) and takes a *second* connection from the pool. If that inner transaction touches row X, it waits for a lock held by a transaction that cannot proceed until the inner one finishes. Deadlock, resolved only by the lock timeout.

The second failure mode is pool exhaustion: every `REQUIRES_NEW` nesting level holds an extra connection simultaneously, so under load a pool of 20 supports only 10 concurrent requests.

Avoidance: never touch the same rows across the nesting; keep `REQUIRES_NEW` for genuinely independent writes such as audit records; always configure a lock timeout so a deadlock fails fast; and size the pool for the maximum nesting depth.

### Q72. `NESTED` propagation

`NESTED` uses a JDBC **savepoint** inside the existing transaction. An inner failure rolls back to the savepoint, leaving the outer transaction alive and able to commit the rest. There is one physical transaction and one connection, unlike `REQUIRES_NEW`.

Supported by `DataSourceTransactionManager` (and `JpaTransactionManager` with a JDBC-based dialect and `nestedTransactionAllowed = true`); **not** supported by JTA.

It fits "process a batch, skip the items that fail" where you want the successful items committed together and do not want the connection cost of `REQUIRES_NEW`. In practice I use it rarely, because savepoint behavior with a JPA persistence context is subtle - the entity state is not rolled back with the savepoint, so you must clear the persistence context yourself or you continue with entities that no longer reflect the database.

### Q73. Rollback rules

Default: rollback on `RuntimeException` and `Error`, commit on checked exceptions. With a custom hierarchy, the cleanest approach is a single unchecked base (`DomainException extends RuntimeException`) so everything rolls back by default, and then `noRollbackFor` for the specific cases where it should not.

`noRollbackFor` is legitimate when the exception is a *business outcome* rather than a failure - `InsufficientFundsException` where you still want to persist the attempted-transaction audit row, or a validation exception thrown after you have deliberately recorded the rejection. Say clearly that this is a deliberate design choice, because the reviewer's default assumption is that it is a mistake.

Rules are matched by the *deepest* (most specific) match on the exception class hierarchy, and `rollbackFor` on a nested method does not affect the outer transaction's own rules.

### Q74. Catching inside a transactional method `[T]`

If you catch the exception, the *transaction advisor never sees it*, so it does not mark rollback. The transaction commits with whatever was written before the exception - a partial write, which is usually the bug.

It still rolls back in two cases: if the exception escaped a **nested** `@Transactional` call that already set `rollbackOnly` (giving `UnexpectedRollbackException` at commit as in Q70), or if the underlying resource itself invalidated the transaction (a constraint violation in PostgreSQL aborts the transaction, and every subsequent statement fails with "current transaction is aborted").

That last one is worth naming because it surprises people: on PostgreSQL you cannot catch a constraint violation and continue using the same transaction. You need a savepoint, or a separate transaction, or you must check before writing.

### Q75. Flush timing

Hibernate's default `FlushMode.AUTO` flushes before a query whose result could be affected by pending changes, and at commit. This means a `findBy...` call can trigger inserts and updates you did not expect at that point - and therefore constraint violations surface at a surprising line, inside a query rather than at the save.

`saveAndFlush` forces it immediately, which you want when you need a generated ID for subsequent work, when you want a constraint violation at a controlled point, or before a native query that bypasses the persistence context and would otherwise not see your pending changes.

Manual flush costs you batching - Hibernate batches statements until flush, so flushing per entity in a loop turns one batch into N round trips. That trade-off is the answer to "why is my bulk insert slow".

### Q76. HTTP calls inside a transaction `[T]`

The cost is concrete: the database connection is held for the entire duration of the network call. A 500ms API call inside a transaction means each request occupies a pooled connection for 500ms doing nothing, so a 20-connection pool caps you at 40 requests per second regardless of database capacity. When the remote service slows to 5 seconds, the pool is exhausted and *every* endpoint fails - a total outage caused by one slow third party.

It is also semantically wrong: the HTTP call cannot be rolled back, so if the transaction later fails you have performed an irreversible external action with no record of it.

The correct shape: do the external call outside the transaction, then open a short transaction to persist the result; or write an outbox row transactionally and perform the call asynchronously afterwards with retry and idempotency. Enforce it with an ArchUnit rule (Q80) - review will not catch it reliably.

### Q77. `@Async` and transactions

The `@Async` method runs on a different thread, and the transaction is thread-bound, so it inherits **nothing**: no transaction, no persistence context, no `EntityManager`, and by default no security context or MDC.

Consequences: entities passed as arguments are detached, so touching a lazy association throws `LazyInitializationException`; the async work can start before the caller commits and therefore read stale or non-existent data; and if the caller rolls back, the async work has already happened.

The correct pattern: pass **identifiers, not entities**; trigger the async work from `@TransactionalEventListener(phase = AFTER_COMMIT)` so it cannot run for a rolled-back transaction; and annotate the async method itself `@Transactional` so it opens its own transaction and reloads what it needs.

### Q78. Reactive transactions

`ReactiveTransactionManager` (with R2DBC) binds the transactional resource to the **Reactor `Context`** rather than to a `ThreadLocal`, because a reactive chain hops threads freely and no thread owns the request.

`@Transactional` does work on reactive return types - Spring subscribes with the transactional context attached - but only if the whole chain is reactive; any blocking call or thread handoff outside Reactor's control breaks the association. `TransactionalOperator` gives explicit control:

```java
return orderRepository.save(order)
    .then(auditRepository.save(entry))
    .as(transactionalOperator::transactional);
```

The mental model to state: in the servlet world the transaction follows the *thread*; in the reactive world it follows the *subscription*. Every difference follows from that.

### Q79. Outbox in Spring

Two implementations, and only one is safe by default.

**Events table**: write the domain change and an `outbox` row in the same `@Transactional` method. One local commit, fully atomic. A separate relay - a poller, or Debezium tailing the WAL - publishes and marks rows sent. This is the correct default.

**`@TransactionalEventListener`**: `AFTER_COMMIT` publishing to Kafka is *not* an outbox - if the process dies between commit and publish, the event is lost forever. It is acceptable only when losing the event is tolerable. `BEFORE_COMMIT` writing an outbox row *is* safe, because it is inside the transaction.

Spring Modulith's event publication registry is a supported middle ground: it persists incomplete event publications in the same transaction and republishes them on restart, giving at-least-once delivery without you writing the relay (Q248).

Whichever you choose, consumers must be idempotent, because all of these are at-least-once.

### Q80. Enforcing no HTTP in transactions `[A]`

Layered, because one control is never enough across a large codebase:

1. **ArchUnit rule in CI** - the primary control. Assert that no method annotated `@Transactional` calls a type in your HTTP client packages, transitively where practical. It fails the build with a precise message and a link to the rationale.
2. **A runtime guard** - a custom `Interceptor` on the `RestClient`/`WebClient` that checks `TransactionSynchronizationManager.isActualTransactionActive()` and, in non-production, throws; in production, records a metric and logs at WARN with the stack trace. This catches the dynamic paths static analysis misses.
3. **`LazyConnectionDataSourceProxy`** as a safety net so the damage is bounded while violations are being cleaned up.
4. **Alerting** on transaction duration percentiles and on Hikari `connections_pending`, so a new violation is visible operationally.

Then the rollout matters as much as the rule: turn the ArchUnit rule on in report-only mode, fix the existing violations with the owning teams, and only then fail the build. Introducing a build-breaking rule against a codebase with 200 existing violations is how platform teams lose credibility.

---

## 5. Spring MVC internals

### Q81. The `DispatcherServlet` flow

1. Servlet filters run (including the Spring Security filter chain).
2. `DispatcherServlet.doDispatch` begins. Multipart resolution if applicable.
3. `getHandler()` walks the `HandlerMapping` list, returning a `HandlerExecutionChain` (handler plus matching interceptors).
4. `getHandlerAdapter()` finds an adapter that supports the handler.
5. Interceptor `preHandle` methods run in order; returning false stops the chain.
6. `handle()` - the adapter resolves arguments, invokes the method, and handles the return value.
7. Interceptor `postHandle` (skipped if an exception was thrown).
8. `processDispatchResult` - render the view, or for `@ResponseBody` the return value was already written by the return-value handler.
9. On exception, the `HandlerExceptionResolver` chain runs - this is where `@ExceptionHandler` methods are found.
10. Interceptor `afterCompletion` always runs.

The detail that matters: everything from step 2 onward is inside the servlet, so an exception thrown in a *filter* never reaches step 9.

### Q82. `HandlerMapping` and `HandlerAdapter`

`RequestMappingHandlerMapping` builds a map of `RequestMappingInfo` (path patterns, methods, params, headers, consumes, produces) to `HandlerMethod` at startup by scanning `@Controller` beans. At request time it matches and, when several patterns match, sorts them by specificity - exact over `{var}` over `**`.

`RequestMappingHandlerAdapter` then does the real work: resolves each argument through the `HandlerMethodArgumentResolver` chain, invokes the method reflectively, and passes the return value through the `HandlerMethodReturnValueHandler` chain (which is where `@ResponseBody` triggers message conversion).

Separating the two is what allows different handler kinds - `@RequestMapping` methods, `HttpRequestHandler`, functional routes - to coexist behind one dispatcher.

### Q83. Argument resolvers

Built-ins include `RequestParamMethodArgumentResolver`, `PathVariableMethodArgumentResolver`, `RequestResponseBodyMethodProcessor` (`@RequestBody`), `ModelAttributeMethodProcessor`, `ServletRequestMethodArgumentResolver`, and `AuthenticationPrincipalArgumentResolver` from Spring Security.

Write your own when a value is derived from the request in a way every controller would otherwise repeat - a resolved tenant, a parsed pagination or filter object, a decoded cursor. It removes a line from fifty controllers and makes the concept a type.

```java
class TenantArgumentResolver implements HandlerMethodArgumentResolver {
    public boolean supportsParameter(MethodParameter p) { return p.getParameterType() == TenantId.class; }
    public Object resolveArgument(...) { return TenantId.of(webRequest.getHeader("X-Tenant")); }
}
```

Register through `WebMvcConfigurer.addArgumentResolvers`. Important caveat: resolve identity from the authenticated principal, not a header, or you have built an authorization bypass.

### Q84. Message converters

Selection is by requested media type and parameter or return type: for a response, the return value handler matches the `Accept` header against each converter's supported media types and `canWrite(type, mediaType)`, taking the first match. Order matters, and the first compatible converter wins.

Customizing Jackson **correctly** in Boot means using `Jackson2ObjectMapperBuilderCustomizer` or the `spring.jackson.*` properties, so Boot's carefully assembled `ObjectMapper` - with its modules for JSR-310, `Optional`, parameter names and Kotlin - is preserved:

```java
@Bean Jackson2ObjectMapperBuilderCustomizer json() {
    return b -> b.failOnUnknownProperties(false).serializationInclusion(NON_NULL);
}
```

Defining your own `ObjectMapper` bean replaces Boot's entirely and quietly loses those modules - which typically shows up as `LocalDateTime` serializing as an object of fields instead of ISO-8601. Overriding `configureMessageConverters` (rather than `extendMessageConverters`) has the same effect on the converter list.

### Q85. Polymorphic `@RequestBody` `[T]`

Jackson cannot instantiate an abstract type or interface without being told which concrete class to use, so it throws `InvalidDefinitionException: cannot construct instance`.

The dangerous fix is `@JsonTypeInfo(use = Id.CLASS)`, which lets the *payload* name any class on the classpath - that is a deserialization gadget vulnerability, the same class of bug behind many Java RCEs. `enableDefaultTyping` is the same mistake with a different name.

The safe fix is an explicit, closed registry of permitted subtypes:

```java
@JsonTypeInfo(use = Id.NAME, property = "type")
@JsonSubTypes({ @Type(value = CardPayment.class, name = "card"),
                @Type(value = BankPayment.class, name = "bank") })
sealed interface PaymentRequest permits CardPayment, BankPayment {}
```

Pairing it with a `sealed` interface means the compiler enforces exhaustive handling too. And a validation rule to state: never accept type information the client fully controls.

### Q86. Content negotiation

`ContentNegotiationManager` resolves the requested media type from, in order: a request parameter (`format=json`, disabled by default), then the `Accept` header. **Path extension matching (`/orders.json`) was deprecated in Boot 2.6 and removed in Spring 6** - along with suffix pattern matching for request mappings.

That removal matters because it was a security problem as much as a design one: extension-based negotiation made it possible to bypass path-based security rules (`/admin` protected, `/admin.json` not), and it made every path with a dot ambiguous.

The modern position: negotiate on `Accept` only, register additional converters for other formats, and version through headers or the path rather than the extension.

### Q87. Filters, interceptors, advice and AOP

Execution order for a request:

1. **Servlet `Filter`** - outermost, sees the raw `HttpServletRequest`, can wrap request and response, runs for *every* request including static resources and errors. Spring Security lives here.
2. **`HandlerInterceptor`** - inside `DispatcherServlet`, knows the resolved `HandlerMethod` (so it can read annotations on it), runs only for mapped requests.
3. **`@ControllerAdvice`** - `@InitBinder` and `@ModelAttribute` before the method, `@ExceptionHandler` after a failure.
4. **AOP advice** on the controller or service - innermost, sees method arguments as objects.

Choose by what you need: raw bytes or unconditional coverage means a filter; handler metadata means an interceptor; domain objects and reusable behavior mean AOP.

### Q88. What a filter cannot see `[T]`

A filter runs before `DispatcherServlet`, and handler mapping happens *inside* the dispatcher - so at filter time no handler has been resolved and the filter cannot know which controller method will run or read its annotations. It can only match on the URL, which is fragile because URL patterns and handler mappings can disagree (path variables, matrix parameters, encoding).

What runs before Spring Security: anything with a lower filter order registered in the servlet container. Boot registers `OrderedCharacterEncodingFilter` (order -2147483648), `OrderedFormContentFilter`, and the tracing/metrics filters; Spring Security's `springSecurityFilterChain` sits at `-100` by default (`SecurityProperties.DEFAULT_FILTER_ORDER`). Anything you register with a lower order sees unauthenticated requests - which is fine for request logging and a serious bug for anything that trusts the principal.

### Q89. `@ControllerAdvice` resolution

`ExceptionHandlerExceptionResolver` looks first for an `@ExceptionHandler` in the **controller itself**, then in applicable `@ControllerAdvice` beans. Within a set of candidates, the handler whose declared exception type is the **closest match in the class hierarchy** wins - not declaration order.

Multiple advice classes are ordered by `@Order`, and `@ControllerAdvice` can be scoped by `basePackages`, `assignableTypes` or `annotations`, which is how you give a subset of controllers different error handling.

`ResponseEntityExceptionHandler` is a base class handling the standard Spring MVC exceptions (`MethodArgumentNotValidException`, `HttpMessageNotReadableException`, `NoHandlerFoundException` and about twenty others) and, since Spring 6, mapping them to `ProblemDetail`. Extend it rather than reimplementing that list, and override `handleExceptionInternal` to add correlation IDs uniformly.

### Q90. `ProblemDetail` and RFC 9457

Spring 6 added `ProblemDetail` (`type`, `title`, `status`, `detail`, `instance`, plus extensions) and `ErrorResponse`, producing `application/problem+json`. Enable Spring's built-in mapping with `spring.mvc.problemdetails.enabled=true`.

Adopting it consistently means more than turning it on:

- Extend `ResponseEntityExceptionHandler` so framework exceptions and your domain exceptions produce the same shape.
- Define a stable `type` URI per error class - this is the machine-readable contract, so it must be documented and versioned, not a random URL.
- Add extensions for what clients actually need: a correlation ID, field-level violations, and a retry hint.
- **Never** put internal details in `detail` - it goes to the client. Log the stack trace with the correlation ID and return only what is safe.

The value is that every service and every client handles errors identically, which matters far more in a 40-service estate than in one application.

### Q91. Exceptions in filters `[T]`

`@ControllerAdvice` is invoked by `ExceptionHandlerExceptionResolver` **inside** `DispatcherServlet`. A filter that throws does so before or after the dispatcher, so the exception propagates to the servlet container, which performs an error dispatch to the configured error page - in Boot, `/error`, handled by `BasicErrorController`. The result is Boot's generic error body rather than your `ProblemDetail`, which is why "our error format is consistent" quietly stops being true for authentication failures.

Handling it: catch inside the filter and write the response yourself using the same `ProblemDetail` serialization; or, for Spring Security specifically, configure `authenticationEntryPoint` and `accessDeniedHandler` in the DSL, which is the supported hook for 401 and 403 bodies. For a truly uniform format I also customize `ErrorAttributes` or replace `BasicErrorController`, so even container-level errors match.

### Q92. Validation exceptions

- `@Valid` / `@Validated` on an `@RequestBody` parameter → `MethodArgumentNotValidException` (a `BindException` subclass) → handled by `ResponseEntityExceptionHandler` → 400.
- Constraints directly on controller method parameters (`@RequestParam @Min(1) int page`) with `@Validated` on the class → `ConstraintViolationException` pre-6.1, or `HandlerMethodValidationException` in Spring 6.1+ → the older form is **unhandled by default**, giving a 500.
- `@Validated` on a service class → `ConstraintViolationException` → unhandled → 500.

Groups let one object be validated differently per operation: `@Validated(OnCreate.class)` on the controller method, with `@Null(groups = OnCreate.class) @NotNull(groups = OnUpdate.class) Long id` on the DTO.

The practical takeaway is to add an explicit handler for `ConstraintViolationException` mapping it to 400 with field details, because the default behavior misrepresents a client error as a server error - which also skews your error-rate SLO.

### Q93. `WebMvcConfigurer` versus `@EnableWebMvc`

`WebMvcAutoConfiguration` is annotated `@ConditionalOnMissingBean(WebMvcConfigurationSupport.class)`. `@EnableWebMvc` imports `DelegatingWebMvcConfiguration`, which **is** a `WebMvcConfigurationSupport` - so adding it makes Boot's entire MVC auto-configuration back off.

You lose: the configured message converters and Jackson setup, static resource handling, the error page mapping, content negotiation defaults, `WebMvcProperties` binding, and locale/formatter configuration. The symptom is usually "my JSON dates changed" or "static resources 404" immediately after someone added the annotation to enable one interceptor.

The correct approach in Boot is to implement `WebMvcConfigurer` **without** `@EnableWebMvc` - your callbacks are added to the auto-configured setup. Use `@EnableWebMvc` only when you deliberately want full manual control.

### Q94. Async MVC

- **`Callable<T>`** - the container thread returns immediately; the `Callable` runs on the configured `AsyncTaskExecutor`; the result triggers an async dispatch back onto a container thread to complete the response.
- **`DeferredResult<T>`** - no executor involved. You hold the object and complete it from any thread later (a message arrival, a callback, another service's response). This is the right tool for long-polling and for bridging a callback API.
- **`WebAsyncTask<T>`** - a `Callable` plus a per-request timeout and executor.
- **`StreamingResponseBody`** - write directly to the `OutputStream` on an async thread; for large downloads without buffering.
- **`SseEmitter`** - a specialized long-lived response for server-sent events.

The key insight is that the servlet container thread is released during the async phase and a *different* container thread performs the final dispatch. That is what makes context propagation (Q95) an issue.

### Q95. Context during async dispatch `[T]`

- **`SecurityContext`** - propagated, because `WebAsyncManagerIntegrationFilter` registers a `SecurityContextCallableProcessingInterceptor`. This works for `Callable` and `WebAsyncTask`; for a thread *you* spawn or a `DeferredResult` completed from your own executor, it is not.
- **MDC** - **not** propagated. Logging on the async thread loses the correlation ID unless you copy the MDC yourself, typically with a `TaskDecorator` on the async executor.
- **Request-scoped beans** - the request stays open through the async phase, so they remain available on the dispatch thread, but on an arbitrary executor thread there is no bound request and access throws (Q24) unless `RequestContextHolder` is propagated.
- **Micrometer observation / trace context** - needs the context-propagation library and a decorator.

So my standard setup is a single `TaskDecorator` that copies security context, MDC and the observation scope, applied to every executor in the application - and a test that asserts a correlation ID appears in a log line written from an async path.

### Q96. `SseEmitter`

Construct with an explicit timeout (`new SseEmitter(TIMEOUT)`) rather than relying on `spring.mvc.async.request-timeout`; on timeout the emitter completes and `onTimeout` fires. Always register `onCompletion`, `onTimeout` and `onError` callbacks to remove the emitter from whatever registry holds it, or you leak emitters for disconnected clients - the most common SSE bug.

Sending to a dead client throws on the *next* send, which is how you detect disconnection; there is no push notification of it.

Capacity planning is by **concurrent open connections**, not requests per second: each emitter holds a socket, and with a servlet container each also holds an async context. Virtual threads help, but the socket and the per-connection memory remain. Also disable response buffering in every intermediary or the client sees nothing until completion (Nginx `proxy_buffering off`, `X-Accel-Buffering: no`, and an ALB idle timeout longer than the emitter timeout).

### Q97. HTTP clients in Spring 6.1+

- **`RestClient`** (Spring 6.1) - the modern synchronous client with WebClient's fluent API. My default for blocking code.
- **`WebClient`** - reactive and non-blocking; still the right choice in WebFlux or for streaming.
- **`RestTemplate`** - maintenance mode; still supported, still everywhere in legacy code, no new features.
- **`@HttpExchange`** declarative interfaces - define the contract as an interface and let Spring generate the implementation over any of the above:

```java
@HttpExchange("/customers")
interface CustomerClient {
    @GetExchange("/{id}") Customer byId(@PathVariable String id);
}
```

This is my preferred shape: the contract is a type, it is trivially mockable in tests, and the transport is configured once.

Whatever the choice, the things that actually matter are the same: explicit connect and read timeouts, a bounded connection pool, retry with backoff and jitter, a circuit breaker, and propagation of the trace context.

### Q98. HTTP caching

`ETag` lets a client revalidate with `If-None-Match` and receive a 304 with no body. `ShallowEtagHeaderFilter` computes an MD5 over the **already-rendered** response, so it saves *bandwidth* but not server work - the controller ran, the database was queried, the JSON was serialized. It also buffers the whole response in memory, which is harmful for large or streaming responses.

Real savings need a "deep" ETag: derive a version from data you can obtain cheaply - an entity `@Version`, a `last_modified` column, or a content hash stored alongside - and use `ServletWebRequest.checkNotModified(version)` early in the controller, returning before doing the expensive work.

For `Cache-Control`, the useful defaults are `no-store` for anything user-specific, `max-age` plus `private` for personalized-but-cacheable data, and `public, max-age, stale-while-revalidate` for shared reference data at the CDN.

### Q99. Multipart and large uploads

Limits are `spring.servlet.multipart.max-file-size` and `max-request-size`; exceeding them throws `MaxUploadSizeExceededException`, which you should handle explicitly to return a 413 rather than a 500. Set `file-size-threshold` so files above it spill to disk instead of the heap.

For genuinely large uploads, do not accept a `MultipartFile` at all - it materializes the file (memory or temp disk) before your method runs. Instead consume the raw stream (`request.getInputStream()`, or a `Part` obtained via the Servlet API) and pipe it straight to its destination, so memory stays constant regardless of file size.

The pattern I prefer for cloud deployments is to bypass the application entirely: issue a **pre-signed S3 URL** so the client uploads directly to storage and only notifies your service afterwards. It removes the bandwidth, the memory pressure, the timeout risk and the request-duration problem in one move.

### Q100. 404 versus handler exceptions

An unmapped URL does not produce an exception by default - `DispatcherServlet` simply sends a 404 through the container, which error-dispatches to `/error` and `BasicErrorController`. Setting `spring.mvc.throw-exception-if-no-handler-found=true` (and, before Boot 3, disabling static resource mapping) makes it throw `NoHandlerFoundException` instead, which `@ControllerAdvice` can handle. In Boot 3 this is the default behavior for the API case.

An exception inside a handler goes through the `HandlerExceptionResolver` chain and reaches your `@ExceptionHandler`.

To make both consistent I do two things: enable the throw-on-no-handler behavior so 404s reach my advice, and customize `ErrorAttributes` (or replace `BasicErrorController`) so anything that still reaches `/error` - filter exceptions, container errors - is rendered as the same `ProblemDetail`. Otherwise a client sees three different error shapes from one service.

### Q101. Tomcat threads versus virtual threads `[T]`

With `spring.threads.virtual.enabled=true` on Boot 3.2+ and Java 21, Tomcat uses a virtual thread executor: each request gets its own virtual thread, blocking unmounts rather than occupying a platform thread, and `server.tomcat.threads.max` stops being the concurrency ceiling.

What **changes**: you can serve far more concurrent blocking requests with the same hardware; thread-pool tuning largely disappears; thread dumps look different and existing pool-saturation alerts stop firing.

What **does not change** - and this is the part interviewers are testing:

- The **downstream** is still finite. Removing your own bottleneck just moves the load to the database or the third-party API, so you now need an explicit `Semaphore`, bulkhead or connection-pool limit where the thread pool used to provide accidental backpressure.
- Connection pools are still sized as before; more concurrent requests means more contention for the same 20 connections.
- CPU-bound work still needs a bounded pool.
- `synchronized` blocks around blocking calls pin the carrier thread on older JDK baselines - use `ReentrantLock`.
- `ThreadLocal` still works but per-thread copies multiply at high concurrency.

So the honest summary: virtual threads remove a limit, they do not add capacity, and the first thing to do after enabling them is to add the limit back where it belongs.

### Q102. API versioning in Spring `[A]`

The mechanism is the easy part - URI path versioning (`/v1/orders`) is what I default to for public APIs because it is visible, cacheable and routable at the edge; header or media-type versioning is cleaner in theory and harder to test and route.

What actually keeps it maintainable is refusing to fork controllers. Concretely:

- Version only on **breaking** changes; make everything else additive and require clients to ignore unknown fields.
- Keep **one** controller and one service; version the **DTOs** and map between them. A `V1OrderResponse` mapper over the current domain model is far cheaper to maintain than two controller trees that drift.
- Where behavior genuinely differs, isolate it in a strategy selected by version, not duplicated through the stack.
- Never let a version reach the domain layer - versions are a transport concern.

Then the lifecycle: publish a deprecation policy, emit `Deprecation` and `Sunset` headers, instrument usage **per version and per consumer** so you know exactly who remains, contact them directly, and retire aggressively. Running more than two versions is what actually kills you, so the discipline is retirement, not clever routing.

---

## 6. Reactive Spring and WebFlux

### Q103. Cold versus hot

A **cold** publisher generates its data per subscriber - each subscription to a `WebClient` `Mono` issues its own HTTP request. A **hot** publisher emits regardless of subscribers, and late subscribers miss earlier values (`Sinks.many().multicast()`, `share()`).

"Nothing happens until you subscribe" means the operator chain is only an assembly-time description; no work occurs until `subscribe()` walks it. Practically: returning the `Mono` from a controller means Spring subscribes; calling an operator chain and ignoring the result does nothing at all; and the same `Mono` subscribed twice performs the work twice, which is why `cache()` exists.

### Q104. Forgetting to subscribe `[T]`

Nothing happens. No request is sent, no exception is thrown, and no log line appears - the method returns and the chain is garbage collected. This is the single most common WebFlux bug, and it is silent, which is what makes it dangerous: a fire-and-forget audit call that was never made.

Catching it: the IDE and SpotBugs flag ignored return values of `@CheckReturnValue`-style types; a code review rule that every `Mono`/`Flux` must be returned, subscribed or explicitly `.subscribe()`d with a comment; and BlockHound-style enforcement will not help here, so it must be static analysis. In practice, requiring that reactive types are always *returned* up to the framework - never terminated inside a service - removes most of the risk.

### Q105. Backpressure

The `Subscription` carries `request(n)`: the subscriber tells the publisher how many elements it can accept, so a fast producer cannot overwhelm a slow consumer. Operators propagate this upstream, which is why an unbounded source such as a network stream can be consumed safely.

When the source cannot be slowed - a hot sensor stream, a WebSocket - the strategies are: `onBackpressureBuffer` (buffer, with a bound and an overflow strategy, or you have moved the failure to an `OutOfMemoryError`), `onBackpressureDrop` (discard new items - right for live telemetry), `onBackpressureLatest` (keep only the newest - right for a UI showing current state), and `onBackpressureError` (fail fast).

The choice is a product decision, not a technical one: which data are you allowed to lose? That framing is what interviewers want.

### Q106. Schedulers

- `Schedulers.parallel()` - a fixed pool sized to CPU count, for **CPU-bound** work. Never block here.
- `Schedulers.boundedElastic()` - an elastic pool with a cap (10× CPUs by default) and a queue, explicitly intended for **wrapping blocking calls** you cannot avoid, such as JDBC or a legacy library.
- `Schedulers.single()` - one reusable thread, for work that must be serialized.
- `Schedulers.immediate()` - runs on the calling thread; a no-op scheduler used to opt out.

The event loop threads (`reactor-http-nio-*`) belong to Netty and must never block. `boundedElastic` exists so that a necessary blocking call degrades throughput rather than deadlocking the loop - but it is a bridge, not a strategy: if most of your work is blocking, you have written a thread-per-request application with much worse ergonomics, and MVC on virtual threads is the better answer.

### Q107. `publishOn` versus `subscribeOn` `[T]`

`subscribeOn` affects the **subscription and the source**, and its position in the chain is irrelevant - the first one wins, and it determines where the data-producing work starts.

`publishOn` affects everything **downstream of it**, switching the thread for subsequent operators. Multiple `publishOn` calls each take effect from their position.

```java
Mono.fromCallable(this::blockingCall)   // runs on boundedElastic
    .subscribeOn(Schedulers.boundedElastic())
    .map(this::transform)               // still boundedElastic
    .publishOn(Schedulers.parallel())
    .map(this::cpuWork)                 // now parallel
```

The rule I state: `subscribeOn` for where the work *starts*, `publishOn` for where the work *continues*. Most confusion comes from expecting `subscribeOn` to behave positionally.

### Q108. One blocking call in WebFlux `[T]`

The Netty event loop has one thread per core (typically 2-8 for the whole application). A blocking call occupies one of them for its duration, so with four loop threads, four concurrent slow calls stall **every request in the application**, including health checks and requests that never touch that code. Throughput collapses to a level far worse than a thread-per-request server, because there is no pool to absorb it.

Detection in CI is the actionable part: **BlockHound** instruments the JVM to throw when a blocking call happens on a non-blocking thread. Add it as a test dependency and install it in the test bootstrap, and a blocking JDBC call in a reactive path fails the build with a stack trace pointing at the exact line.

Runtime detection: `reactor.blockhound` in staging, plus alerting on event-loop thread saturation and on a latency profile where p50 and p99 rise together across unrelated endpoints - the signature of a starved loop.

### Q109. Reactor `Context`

`ThreadLocal` fails because a reactive chain hops threads between operators; the value set at subscription time is not visible in a `map` running on another scheduler.

Reactor's `Context` is an immutable key-value map attached to the **subscription** and propagated **upstream** (written with `contextWrite`, read with `deferContextual` or `Mono.deferContextual`). Because it travels with the subscription rather than the thread, it survives every thread switch.

Spring Security uses this for `ReactiveSecurityContextHolder`, which is just a well-known context key. For MDC and tracing, the Micrometer **context-propagation** library bridges `ThreadLocal` and Reactor `Context` automatically when enabled (`Hooks.enableAutomaticContextPropagation()`), which is what makes correlation IDs appear in logs without manual plumbing - and it is the first thing to check when they do not.

### Q110. `flatMap` versus `concatMap` versus `flatMapSequential`

- `flatMap` - subscribes to inner publishers **eagerly and concurrently**; results are interleaved in completion order. Fastest, no ordering.
- `concatMap` - subscribes to each inner publisher only after the previous completes. Ordered, **sequential**, so latency is the sum.
- `flatMapSequential` - subscribes eagerly and concurrently like `flatMap`, but **buffers to emit in source order**. Concurrency with ordering, at the cost of holding completed results while waiting for earlier ones.

Choose by whether order matters and whether the downstream can tolerate concurrency. For calling an external API per element where order is irrelevant, `flatMap` with a concurrency bound; where the API must be called in order (a sequence of state transitions), `concatMap`.

### Q111. Unbounded `flatMap` `[T]`

`flatMap` defaults to a concurrency of `Queues.SMALL_BUFFER_SIZE` - **256** in-flight inner subscriptions. So a `Flux` of 10,000 IDs fires 256 simultaneous HTTP calls at the downstream, which for a service sized for 20 concurrent requests is an accidental denial of service - and it looks like *their* outage, not yours.

Bound it explicitly: `flatMap(this::call, 8)`. I treat the two-argument form as mandatory in review; the default is almost never the right number, and it is invisible.

Also bound the client itself: the `WebClient` connection pool (`ConnectionProvider.builder().maxConnections(n).pendingAcquireMaxCount(m)`) provides a second limit, so a missed `flatMap` bound degrades into queueing rather than overload. And prefer `limitRate` on the source when the constraint is throughput rather than concurrency.

### Q112. Error handling operators

- `onErrorReturn(fallback)` - a static fallback value.
- `onErrorResume(e -> alternative)` - a fallback publisher; the general-purpose recovery operator.
- `onErrorMap` - translate to a domain exception, preserving the cause.
- `retryWhen(Retry.backoff(3, ofMillis(200)).jitter(0.5).filter(this::isTransient))` - the correct retry form: bounded, exponential, jittered, and filtered to transient errors.

**`onErrorContinue` is the trap.** It does not behave like the others: it reaches *upstream* into operators that support it and makes them drop the offending element and continue, which violates the normal error-terminates-the-sequence contract. It works inconsistently depending on which operators are in the chain, it is invisible to the operator that actually failed, and it interacts badly with `flatMap`. Reactor's own documentation discourages it. The correct way to skip bad elements is to handle the error *inside* the inner publisher: `flatMap(x -> process(x).onErrorResume(e -> Mono.empty()))`, which is explicit and local.

### Q113. `WebClient` configuration

The defaults are not production-ready. What I always set:

```java
ConnectionProvider provider = ConnectionProvider.builder("api")
    .maxConnections(50).pendingAcquireTimeout(ofSeconds(2))
    .maxIdleTime(ofSeconds(20)).maxLifeTime(ofMinutes(5)).build();

HttpClient http = HttpClient.create(provider)
    .option(CONNECT_TIMEOUT_MILLIS, 2000)
    .responseTimeout(ofSeconds(5));
```

`maxIdleTime` **must be shorter than the server's or load balancer's idle timeout**. `PrematureCloseException` (or "Connection prematurely closed BEFORE response") almost always means exactly that: the client reused a pooled connection that the far side had already closed, a race you cannot retry your way out of reliably. The fix is the idle-time setting, not a retry.

Also: `responseTimeout` bounds the whole response, while `CONNECT_TIMEOUT_MILLIS` bounds only connection establishment - you need both. And enable metrics on the connection provider so pool saturation is visible before it becomes latency.

### Q114. R2DBC versus JDBC

R2DBC is a non-blocking database API, so a query does not occupy a thread while waiting. You gain the ability to keep the reactive stack pure end to end, and higher connection efficiency under very high concurrency.

You give up a great deal: **no JPA** - no dirty checking, no lazy loading, no entity graph, no first-level cache; Spring Data R2DBC is closer to Spring Data JDBC in capability. No JDBC-based tooling, fewer mature drivers, different and less familiar transaction semantics, and a much smaller pool of engineers who can debug it.

My position: R2DBC is justified when you are already fully reactive for a good reason and the database is a genuine bottleneck at very high concurrency. For most services in 2026, JDBC on virtual threads gives you the throughput benefit with the entire mature ecosystem intact.

### Q115. Reactive transaction boundaries

The boundary is the **subscription**, not the thread (Q78). `TransactionalOperator` makes it explicit:

```java
Mono<Order> result = orderRepository.save(order)
    .flatMap(saved -> auditRepository.save(auditFor(saved)).thenReturn(saved))
    .as(transactionalOperator::transactional);
```

Everything within that subscription shares the transaction via the Reactor `Context`. Consequences: work spawned onto a separate subscription (a `subscribe()` inside the chain, a fire-and-forget) is **not** in the transaction; and mixing blocking JDBC into a reactive transaction does not work at all, since the two bind their resources differently.

`@Transactional` on a method returning `Mono`/`Flux` works with a `ReactiveTransactionManager`, but I prefer the operator form here because the boundary is visible - in reactive code, invisible boundaries are much harder to reason about than in imperative code.

### Q116. `StepVerifier`

```java
StepVerifier.create(service.findOrders(customerId))
    .expectNextMatches(o -> o.status() == CONFIRMED)
    .expectNextCount(2)
    .verifyComplete();
```

It subscribes, asserts the sequence of signals, and fails if the sequence differs. `expectError(Type.class)`, `expectSubscription`, `thenRequest(n)` for backpressure assertions, and `verify(Duration)` for a timeout.

`StepVerifier.withVirtualTime(() -> flux)` replaces the scheduler with a `VirtualTimeScheduler`, so `thenAwait(Duration.ofHours(1))` completes instantly. That is what makes retry-with-backoff, timeout and interval logic testable - otherwise the test either sleeps for real or is not written at all. The supplier form is required because the publisher must be assembled *after* the virtual scheduler is installed, which is a common mistake.

### Q117. `WebFilter` and reactive security

`WebFilter` is the reactive analogue of a servlet `Filter`, but it returns `Mono<Void>` and composes through `chain.filter(exchange)` rather than a blocking call. The security chain is `WebFilterChainProxy` with `SecurityWebFilterChain` beans, configured through `ServerHttpSecurity` instead of `HttpSecurity`.

The structural difference: everything is non-blocking, so a filter that needs to load a user must return a `Mono` rather than block, and the security context lives in the Reactor `Context` rather than a `ThreadLocal`. `@EnableWebFluxSecurity` replaces `@EnableWebSecurity`, and `@EnableReactiveMethodSecurity` handles method security - with the limitation that it only supports reactive return types.

### Q118. Reactive security context `[T]`

`SecurityContextHolder` is `ThreadLocal`-backed, and no thread owns a reactive request, so it returns nothing (or worse, another request's context in a pooled thread - which is why relying on it here is a security bug, not just a nuisance).

Use `ReactiveSecurityContextHolder.getContext()`, which reads from the Reactor `Context`:

```java
return ReactiveSecurityContextHolder.getContext()
    .map(SecurityContext::getAuthentication)
    .flatMap(auth -> service.forUser(auth.getName()));
```

Or simply accept `@AuthenticationPrincipal` as a controller parameter, which is resolved for you. In tests, `@WithMockUser` works if you add `WebTestClientConfigurer` `mockUser()`, since the context must be written into the subscription rather than a thread.

### Q119. WebFlux versus MVC on virtual threads `[A]`

My recommendation in 2026 is **MVC with virtual threads by default**, and WebFlux only for specific, nameable reasons.

The reasoning: virtual threads deliver the concurrency benefit that was WebFlux's main selling point, while preserving imperative code, usable stack traces, `ThreadLocal`-based tooling, JDBC and JPA, step debugging, and a hiring pool that can maintain it. The cognitive cost of reactive code is real and it is paid by every engineer who touches the codebase for years.

Conditions that change my answer:

- **Streaming and backpressure semantics** - server-sent events to many clients, or consuming a fast upstream where you must signal "slow down". Virtual threads give concurrency but not backpressure.
- **A fully reactive stack already in place** with reactive drivers and a team fluent in it - rewriting to MVC is not automatically an improvement.
- **Very high connection counts with minimal per-request work** - an API gateway or proxy, where event-loop efficiency genuinely wins. Spring Cloud Gateway is reactive for exactly this reason.
- **Composition-heavy orchestration** - fanning out to many services with fine-grained concurrency and timeout control, where the operator model is genuinely more expressive than imperative code.

What I would not accept as a reason: "it is faster" without a measurement, or "it is more modern".

### Q120. Inheriting an unmaintainable WebFlux service `[A]`

I would not rewrite it first. A rewrite of a working system by a team that does not understand it produces a differently broken system, later.

My sequence:

1. **Stabilize and measure.** Add BlockHound in tests, checkpoint/`onOperatorDebug` or `ReactorDebugAgent` so stack traces are usable, proper context propagation so logs correlate, and metrics on the event loop and connection pools. Most "unmaintainable" reactive services are actually "undebuggable" ones, and this alone changes the situation.
2. **Find the real problem.** Is it genuinely the paradigm, or is it unbounded `flatMap`, blocking calls on the loop, `onErrorContinue`, and no tests? Those are fixable defects, not architectural ones.
3. **Build the team's capability** deliberately - a short internal guide covering the ten operators they actually use, pairing on changes, and `StepVerifier` tests so changes are safe.
4. **Then decide.** If after that the service is still a drag - typically when it is mostly blocking work wrapped in `boundedElastic`, which is the honest signal that reactive bought nothing - I would migrate incrementally: MVC with virtual threads, endpoint by endpoint behind the same contract, with the two coexisting during the transition. Never a big bang.

The judgement being assessed is whether you can separate "I dislike this" from "this is costing us", and whether you can make that case with evidence.

---

## 7. Spring Data in depth

### Q121. From interface to bean

`RepositoryBeanDefinitionRegistrarSupport` (an `ImportBeanDefinitionRegistrar`, activated by `@EnableJpaRepositories` or Boot's auto-configuration) scans for interfaces extending `Repository` and registers a `JpaRepositoryFactoryBean` definition for each.

At creation, the factory builds a **JDK dynamic proxy** implementing your interface. Its interceptor chain resolves each call in order: is it a method of the base `SimpleJpaRepository` implementation, a method from a custom fragment, or a *derived* or `@Query` method to be executed by a `RepositoryQuery`? Derived queries are parsed at **startup**, which is why a typo in a method name fails at boot rather than at first call - a genuinely valuable property worth mentioning.

### Q122. Query derivation

`PartTree` parses the method name after a subject keyword (`find`, `read`, `get`, `query`, `count`, `exists`, `delete`) and `By`, splitting the predicate on `And`/`Or`, then matching property paths against the entity graph, with keywords such as `Between`, `LessThan`, `Like`, `IgnoreCase`, `OrderBy`.

Where it breaks down: ambiguous property paths (`findByUserAddressZip` could be `user.addressZip` or `user.address.zip` - resolved by underscore, `findByUser_Address_Zip`); anything needing a join condition, an aggregate, a subquery or a projection; and method names that grow past readability - `findByStatusAndCreatedAtBetweenAndCustomerTypeInOrderByCreatedAtDesc` is a signal to switch to `@Query` or a `Specification`.

My guidance to teams: derivation for one or two predicates, `@Query` for anything fixed and complex, `Specification` or Querydsl for anything dynamic.

### Q123. Return types `[T]`

- `Optional<T>` / `T` - expects at most one row; more than one throws `IncorrectResultSizeDataAccessException`.
- `List<T>` - all rows materialized.
- `Page<T>` - the query plus a **separate `COUNT` query**.
- `Slice<T>` - fetches `pageSize + 1` rows to determine `hasNext`; no count query.
- `Stream<T>` - a cursor-based, lazily materialized result. **Requires an open transaction and must be closed** (try-with-resources), or you leak the connection.
- `Mono`/`Flux` - only with a reactive module.

So the return type changes both the SQL issued and the transactional requirements of the caller, which is not obvious from the method signature. `Stream` and `Page` are the two that surprise people - the first because it needs a transaction the caller may not have, the second because of the hidden count.

### Q124. Projections

- **Interface (closed)** projection - getters matching entity properties. Spring Data generates a query selecting **only those columns**, so it is genuinely narrow. This is the efficient one.
- **Interface (open)** projection - any getter annotated `@Value("#{target.x + target.y}")`. Because the SpEL can reach anything, Spring Data **loads the full entity** and evaluates against it. No SQL narrowing at all.
- **Class/DTO** projection - a class (or record) whose constructor parameters match property names. Also produces a narrow query, and my preferred form because it is a real type with no proxy.
- **Dynamic** projection - `<T> List<T> findByStatus(Status s, Class<T> type)`, letting the caller choose the shape from one method.

The distinction between closed and open interface projections is exactly the kind of detail that separates a candidate who has read the documentation from one who has profiled the SQL.

### Q125. Nested projections `[T]`

A nested projection (`interface OrderView { CustomerView getCustomer(); }`) cannot be satisfied by a flat column selection, so Spring Data falls back to loading the **full root entity** and then wrapping the association in a projection proxy. The association is loaded according to its fetch strategy - which for a lazy `@ManyToOne` means an extra query per row, reproducing N+1 exactly where you thought you had optimized it.

The same happens with any open projection, because the SpEL expression could reference anything.

The reliable fix is a **DTO projection with a constructor expression** naming the exact columns across the join:

```java
@Query("select new com.acme.OrderView(o.id, c.name) from Order o join o.customer c")
List<OrderView> findViews();
```

One query, exactly the columns needed, no proxies. The general lesson: verify projections by looking at the generated SQL, because the type signature tells you nothing about it.

### Q126. `Specification`

`Specification<T>` wraps a JPA Criteria predicate and composes with `and`, `or` and `not`, which is how you build a dynamic query without concatenating strings:

```java
static Specification<Order> hasStatus(Status s) {
    return (root, query, cb) -> s == null ? null : cb.equal(root.get("status"), s);
}
repository.findAll(hasStatus(status).and(createdAfter(from)), pageable);
```

Returning `null` for an absent filter makes optional criteria compose cleanly. Strengths: type-safe-ish, dynamic, works with `Pageable` and `Page`, and it is injection-proof because values are bound as parameters.

Weaknesses: the Criteria API is verbose and reads poorly, `root.get("status")` is a stringly-typed reference that refactoring will not catch (use the generated JPA metamodel `Order_.status` to fix that), and complex joins with fetch semantics interact awkwardly with the count query used for `Page`.

### Q127. Specifications versus Querydsl versus `@Query`

- **`@Query`** - a fixed query. Most readable, easiest to review and to hand to a DBA, and easily verified with `EXPLAIN`. My default when the query does not vary.
- **`Specification`** - dynamic criteria, no extra dependency or build step. My default for search endpoints with optional filters.
- **Querydsl** - a generated, fully type-safe DSL (`QOrder.order.status.eq(...)`) that is far more readable than Criteria and survives refactoring. Better ergonomics, at the cost of an annotation processor, generated sources, and a build step that can complicate IDE setup and native builds.

I choose Querydsl when there is a large amount of dynamic query construction and the team will invest in it; Specifications when it is a handful of endpoints; `@Query` for everything else. The failure mode to avoid is using all three in one codebase, which is common and makes the data layer unreadable.

### Q128. `@Modifying` `[T]`

A `@Modifying` query executes DML **directly against the database**, bypassing the persistence context entirely. Hibernate does not know what it changed.

That creates two problems, and each flag fixes one:

- `flushAutomatically = true` - flushes pending changes **before** the query, so your in-memory modifications are not overwritten or ignored by the bulk statement.
- `clearAutomatically = true` - clears the persistence context **after**, so subsequently loaded entities are not served from the first-level cache with stale, pre-update state.

Without them, code that runs `updateStatusToArchived()` and then reads the entity gets the *old* status back from the persistence context and silently writes it again on flush. Both flags are recommended, and a `@Modifying` query requires an active transaction.

### Q129. `@Query`: JPQL versus native

JPQL is portable, validated at startup against the entity model, and integrates with the persistence context. Native SQL gives you database-specific features (window functions, CTEs, `ON CONFLICT`, full-text) at the cost of portability and startup validation.

For pagination with a native query you must supply a `countQuery`, because Spring Data cannot derive it reliably by string manipulation:

```java
@Query(value = "select * from orders where status = :s",
       countQuery = "select count(*) from orders where status = :s",
       nativeQuery = true)
Page<Order> findByStatus(@Param("s") String status, Pageable pageable);
```

Sorting with `Pageable` works for JPQL but **not** for native queries with dynamic `Sort` - Spring Data cannot safely inject an ORDER BY into arbitrary SQL, and attempting it is where Q130 comes from.

### Q130. Sorting a native query by user input `[T]`

Column names cannot be bound as parameters, so a user-supplied sort column has to be concatenated into the SQL - which is **SQL injection**, in an application where everyone assumed JPA made that impossible.

`Sort.by(userInput)` with a native query either fails or, if you build the string yourself, injects. `JpaSort.unsafe("...")` exists precisely to make the danger explicit in the code.

The correct handling is an **allowlist**: map an external sort key to a known column, and reject anything else.

```java
private static final Map<String, String> SORTABLE =
    Map.of("created", "created_at", "amount", "total_amount");
String column = SORTABLE.get(request.sort());
if (column == null) throw new BadSortException(request.sort());
```

Same rule for dynamic table names in schema-per-tenant setups. The general principle worth stating: every user-controlled *value* is a bound parameter; every user-controlled *identifier* is validated against a fixed allowlist.

### Q131. Custom fragments

Define an interface and an implementation named with the `Impl` suffix, then have your repository extend both:

```java
interface OrderRepositoryCustom { List<OrderSummary> search(SearchCriteria c); }
class OrderRepositoryCustomImpl implements OrderRepositoryCustom { @PersistenceContext EntityManager em; ... }
interface OrderRepository extends JpaRepository<Order, Long>, OrderRepositoryCustom {}
```

Spring Data detects the `Impl` by naming convention and adds it to the proxy's interceptor chain.

This is better than an abstract base class because fragments **compose** - several fragments can be mixed into one repository, and a fragment can be shared across repositories (a `SoftDeleteFragment` reused everywhere). It also keeps the hand-written `EntityManager` code in one clearly-marked place instead of leaking a second repository type into the service layer.

### Q132. Auditing

Enable with `@EnableJpaAuditing` and `@EntityListeners(AuditingEntityListener.class)`; then `@CreatedDate`, `@LastModifiedDate`, `@CreatedBy` and `@LastModifiedBy` are populated on persist and update. The user comes from an `AuditorAware<String>` bean, which normally reads `SecurityContextHolder`.

The interesting part is what happens when there is no user: an `@Async` method, a `@Scheduled` job, a Kafka consumer or a Flyway-triggered migration all have an empty security context, so `AuditorAware` must return a meaningful system identity rather than `Optional.empty()` (which leaves the column null and destroys the audit trail's value).

```java
return Optional.of(SecurityContextHolder.getContext())
    .map(SecurityContext::getAuthentication).filter(Authentication::isAuthenticated)
    .map(Authentication::getName).or(() -> Optional.of("system:" + applicationName));
```

Also worth stating: JPA auditing records *who last touched the row*, not a history. If you need "what changed and when" for compliance, that is Hibernate Envers or an explicit audit table (see `01-java` Q225), not these four annotations.

### Q133. Optimistic locking through Spring Data

Add `@Version` to the entity; Hibernate appends `WHERE version = ?` to updates and throws `ObjectOptimisticLockingFailureException` (Spring's `OptimisticLockingFailureException` hierarchy) when zero rows are affected.

Handling it correctly means **reload, re-apply, retry** - not retrying the same detached entity, which will fail identically forever. The retry must therefore wrap a boundary that starts a fresh transaction *and* re-reads:

```java
@Retryable(retryFor = OptimisticLockingFailureException.class,
           maxAttempts = 3, backoff = @Backoff(delay = 50, random = true))
@Transactional
public void adjustStock(Long id, int delta) {
    Product p = repository.findById(id).orElseThrow();  // fresh read each attempt
    p.adjust(delta);
}
```

The retry aspect must be **outside** the transaction aspect (Q49), or every attempt joins the same doomed transaction. For a genuinely hot row, retries will thrash and pessimistic locking or an atomic `UPDATE ... SET qty = qty - ?` is the better answer.

### Q134. Streaming large results

```java
@Transactional(readOnly = true)
public void export(Consumer<Order> sink) {
    try (Stream<Order> stream = repository.streamAllByStatus(ACTIVE)) {
        stream.forEach(sink);
    }
}
```

Requirements, all of which are easy to get wrong: an **open transaction** for the whole consumption (the cursor lives on the connection); an explicit **close** (try-with-resources) or the connection leaks; a **fetch size** hint so the driver does not materialize everything anyway (`@QueryHints(@QueryHint(name = HINT_FETCH_SIZE, value = "500"))`, and on MySQL the fetch size must be `Integer.MIN_VALUE`); and periodic `entityManager.clear()`, because otherwise every streamed entity stays in the persistence context and you reproduce the `OutOfMemoryError` you were trying to avoid.

That last point is the one candidates miss - streaming fixes the JDBC buffer, not the first-level cache.

### Q135. `Page` versus `Slice` `[T]`

`Page` needs the total element count to compute `getTotalPages()`, so it issues a second `COUNT` query. On a large filtered table that count can cost more than the page itself, and it is executed on **every** page request.

`Slice` only fetches `pageSize + 1` rows to determine whether a next page exists - no count query. It gives you "next" and "previous" but not "page 47 of 912".

Use `Slice` for infinite scroll and any "next" navigation, which is most modern UIs. Use `Page` only when the UI genuinely renders a total, and consider an approximate count (`reltuples` in Postgres) or a cached count if it does.

Beyond a few thousand pages, neither is right: `OFFSET` makes the database scan and discard, so cost grows with depth. That is when you move to keyset pagination (`01-java` Q158), which Spring Data supports directly with `ScrollPosition` and `Window<T>` on modern versions.

### Q136. `@EntityGraph`

`@EntityGraph(attributePaths = {"customer", "items"})` on a repository method turns lazy associations into a single fetch join for that query, declaratively and without writing JPQL. It is the cleanest fix for N+1 on a specific access path.

Its interactions are the same as `JOIN FETCH` because it *is* a fetch join underneath: fetching a **collection** with `Pageable` causes Hibernate to fetch all rows and paginate **in memory** (the `HHH000104` warning), and fetching two collections produces a cartesian product. Fetching `@ManyToOne` associations with pagination is safe.

So my rule is: entity graphs for to-one associations freely; for collections, either avoid pagination, or use `@BatchSize`/`default_batch_fetch_size`, or split into two queries (page the IDs, then fetch with the graph).

### Q137. Two data sources

Beyond the transaction manager selection issue (Q66), the wiring itself must be explicit:

```java
@Configuration
@EnableJpaRepositories(basePackages = "com.acme.orders.repo",
    entityManagerFactoryRef = "ordersEmf", transactionManagerRef = "ordersTx")
class OrdersDataConfig {
    @Bean @Primary @ConfigurationProperties("spring.datasource.orders")
    DataSource ordersDataSource() { return DataSourceBuilder.create().build(); }
    @Bean LocalContainerEntityManagerFactoryBean ordersEmf(...) { ... packages("com.acme.orders.domain") ... }
    @Bean PlatformTransactionManager ordersTx(@Qualifier("ordersEmf") EntityManagerFactory emf) { ... }
}
```

Non-obvious requirements: entity packages must not overlap, or entities are managed by both units; one `DataSource` must be `@Primary` or Boot's other auto-configurations (Flyway, Actuator health, Batch) fail to resolve; each needs its own Flyway or Liquibase configuration; and Hikari metrics must be tagged per pool or you cannot tell which one is saturated.

I would also ask whether two data sources are warranted at all - it is frequently a service boundary drawn in the wrong place.

### Q138. Spring Data JDBC versus JPA

Spring Data JDBC implements a strict **DDD aggregate** model: an aggregate root and everything reachable from it is loaded and saved as a unit. There is no lazy loading, no dirty checking, no first-level cache, no session, and no proxies. Saving a root deletes and re-inserts its child collections by default.

That simplicity is the point. You always know what SQL runs, there is no `LazyInitializationException`, no N+1 by accident, no detached-entity confusion, and the mental model fits in one page - which matters more on a team than the feature list.

I choose it when aggregates are small and well-bounded, when the team has been repeatedly burned by JPA's implicit behavior, or when the domain model is genuinely aggregate-shaped. I choose JPA when there is a large existing model, complex object graphs, or a need for the second-level cache and lazy loading. What I would not do is mix both against the same tables.

### Q139. `JdbcClient` and `JdbcTemplate`

`JdbcClient` (Spring 6.1) is the modern fluent wrapper - named parameters, typed mapping, `Optional` results, all in one readable call:

```java
List<OrderRow> rows = jdbcClient.sql("select id, total from orders where status = :s")
    .param("s", status).query(OrderRow.class).list();
```

I drop to it when JPA is the wrong tool rather than a broken one: bulk operations, reporting queries with database-specific SQL, `INSERT ... ON CONFLICT`, window functions, or a hot path where entity overhead is measurable.

For batching, `JdbcTemplate.batchUpdate` with a `BatchPreparedStatementSetter`, chunked (typically 500-1000 rows per batch) so a single transaction does not grow unbounded. With JPA, batching requires `hibernate.jdbc.batch_size`, ordered inserts and updates, and a periodic `flush()` plus `clear()` - all easy to get wrong, which is why bulk work often belongs in JDBC anyway.

### Q140. Spring Data Redis

Configure `RedisTemplate` deliberately: the default `JdkSerializationRedisSerializer` produces unreadable, class-coupled binary that breaks on any class change and is a deserialization risk. Use `StringRedisSerializer` for keys and a JSON serializer for values, and use `StringRedisTemplate` where values are strings.

**Cache versus store of record** is the design question. As a *cache*, everything must tolerate loss: every key has a TTL, the data is reconstructible from the source, and a Redis outage degrades latency rather than correctness (Q55). As a *store*, you must think about persistence (RDB/AOF), failover behavior, whether cluster mode splits your keys, and what happens to data in a failover - Redis is not a database with the durability guarantees people assume.

The recurring mistake I look for is a session store or a distributed lock built on a Redis configured as a cache with eviction enabled, so keys silently disappear under memory pressure and correctness quietly breaks. Also worth naming: `KEYS` in production is a stop-the-world scan - use `SCAN`.

### Q141. `save()` on an assigned ID `[T]`

`SimpleJpaRepository.save()` calls `entityInformation.isNew(entity)`. The default implementation checks whether the **ID is null**. With a generated ID, a new entity has a null ID, so `persist()` is called. With an **assigned** ID (a UUID or business key you set yourself), the ID is never null, so Spring Data assumes it is detached and calls `merge()` - and `merge()` must first `SELECT` to see whether the row exists.

So every insert costs an extra round trip, and at scale that doubles your write latency.

Fixes, in order of preference:

1. Implement `Persistable<ID>` and control `isNew()` yourself, typically with a transient `@Transient boolean isNew = true` reset in `@PostPersist`/`@PostLoad`.
2. Add `@Version`; Spring Data's `JpaMetamodelEntityInformation` then uses a null version as the new-entity signal.
3. Add `@CreatedDate` with auditing, which is used similarly.
4. Call `entityManager.persist()` directly in a custom fragment when you know it is new.

The same reasoning explains the equivalent behavior in Spring Data JDBC, where `isNew` is also ID-based.

### Q142. Preventing repository sprawl `[A]`

Two hundred bespoke finders is a symptom, not the disease. The causes are usually that every screen gets its own query method, that the repository is treated as a general-purpose query API by every caller, and that nobody owns the data layer.

What I do about it:

- **Separate reads from writes.** The repository serves the aggregate for *writes*; read-heavy screens get purpose-built query objects returning DTOs, often with `JdbcClient` or a dedicated query service. That single split removes most of the sprawl, because the pressure came from read shapes.
- **Push variability into parameters, not method names.** One `Specification`-based `search(criteria, pageable)` replaces thirty `findByAAndBAndC` variants.
- **Own the aggregate boundary.** If a repository has finders for every field, the aggregate is probably too large or is being used as a database gateway rather than a domain concept.
- **Review the data layer as a design artifact**, not as incidental plumbing - I would put a named owner on it and include SQL review in the definition of done for new query methods.
- **Instrument it.** Query-count assertions in tests and per-query metrics make the cost of a careless finder visible, which changes behavior more than a guideline does.

Realistically I would not clean up all 200 at once; I would freeze growth with the review rule, then consolidate the top twenty by call volume.

---

## 8. Spring Security architecture

### Q143. Multiple `SecurityFilterChain` beans

Each `SecurityFilterChain` bean is registered with `FilterChainProxy`, which holds them **in order** and dispatches a request to the **first chain whose `securityMatcher` matches** - and only that chain. Chains are ordered by `@Order` on the bean method.

```java
@Bean @Order(1) SecurityFilterChain actuator(HttpSecurity http) throws Exception {
    return http.securityMatcher("/actuator/**")
        .authorizeHttpRequests(a -> a.anyRequest().hasRole("OPS"))
        .httpBasic(withDefaults()).build();
}

@Bean @Order(2) SecurityFilterChain api(HttpSecurity http) throws Exception {
    return http.securityMatcher("/api/**")
        .authorizeHttpRequests(a -> a.anyRequest().authenticated())
        .oauth2ResourceServer(o -> o.jwt(withDefaults()))
        .csrf(CsrfConfigurer::disable).sessionManagement(s -> s.sessionCreationPolicy(STATELESS)).build();
}
```

This is how you give the API bearer-token authentication and the admin UI form login in one application, with genuinely independent configuration.

### Q144. A chain with no matcher `[T]`

A chain without `securityMatcher` matches **every** request. Since dispatch stops at the first match, a matcher-less chain ordered before another makes the later one **completely unreachable** - and there is no error, no warning, and no startup failure. The application simply enforces rules you did not intend.

The symptom is usually "our API chain is being ignored and everything is redirecting to the login page", because the catch-all UI chain was declared first.

Rules I apply: always give every chain an explicit `@Order` and an explicit `securityMatcher`, except for exactly one deliberate catch-all which is ordered **last**. And test it - a parameterized test asserting the expected status for a representative URL per chain catches this immediately, whereas reading the configuration does not.

### Q145. `AuthorizationManager`

Spring Security 6 replaced the `AccessDecisionManager` / `AccessDecisionVoter` / `ConfigAttribute` model with a single functional interface:

```java
AuthorizationDecision check(Supplier<Authentication> authentication, T object);
```

The differences that matter: the `Authentication` is a **`Supplier`**, so it is only resolved if a rule actually needs it (a cheap `permitAll` no longer forces session lookup); the model is composable with `AuthorizationManagers.allOf`/`anyOf` rather than a voter-consensus strategy; it is used uniformly for web requests, method security and messaging, where previously each had its own mechanism; and it returns a decision object that can carry detail rather than an int vote.

A custom rule is now just a lambda or a small class, which makes tenant or ownership checks far easier to express than writing a voter did.

### Q146. `authorizeHttpRequests` versus `authorizeRequests`

`authorizeRequests` used the old `FilterSecurityInterceptor` and voter model, and was removed in Spring Security 6. `authorizeHttpRequests` uses `AuthorizationFilter` and `AuthorizationManager`.

Semantic changes, not just a rename:

- **`AuthorizationFilter` runs later in the chain** than `FilterSecurityInterceptor` did, and by default it applies to **all dispatcher types** including `ERROR` and `FORWARD`. That means the `/error` dispatch is now authorized too - a common upgrade surprise where errors turn into 403s or redirect loops.
- Matcher methods changed: `antMatchers`, `mvcMatchers` and `regexMatchers` were unified into **`requestMatchers`**, which selects an appropriate matcher implementation automatically and, importantly, uses MVC-aware matching when Spring MVC is present - which closes the path-matching mismatch that used to allow security bypasses.
- Authentication is lazily resolved, as above.

### Q147. Custom `AuthenticationProvider` versus custom filter

Write an **`AuthenticationProvider`** when the credentials arrive through an existing mechanism and only the *verification* differs - validating against an LDAP directory, a legacy password store, or an extra factor. You implement `authenticate()` and `supports()`, and slot it into `ProviderManager`; everything else in the chain is unchanged.

Write a **filter** when the credentials arrive in a *new way* that no existing filter knows how to extract - a custom header, a signed request, an mTLS certificate attribute, an API key. The filter's job is to extract the credential, build an unauthenticated `Authentication` token, hand it to the `AuthenticationManager`, and store the result.

The mistake I look for is a filter that does both extraction *and* verification, bypassing `AuthenticationManager` entirely. That works, and then it silently skips the event publishing, the credential erasure, the provider chain and the standard failure handling - so behavior diverges from the rest of the application in ways nobody documents.

### Q148. `SecurityContextRepository` and explicit saving

In Spring Security 5, `SecurityContextPersistenceFilter` automatically *saved* the context to the `HttpSession` at the end of the request. In 6, that filter was replaced by `SecurityContextHolderFilter`, which **only reads** - saving is now the responsibility of whatever authenticates.

The built-in authentication filters do it correctly. **Custom filters do not**, unless you added it:

```java
SecurityContext context = SecurityContextHolder.createEmptyContext();
context.setAuthentication(authentication);
SecurityContextHolder.setContext(context);
securityContextRepository.saveContext(context, request, response);   // now required
```

The rationale for the change is performance and correctness: the old filter had to inspect the context on every request to decide whether to save, which caused unnecessary session writes and made session replication expensive.

### Q149. Authentication lost after upgrade `[T]`

This is Q148 in its symptom form: a custom authentication filter sets the `SecurityContextHolder` but never calls `saveContext`. Under Security 5 the persistence filter saved it implicitly; under 6 nothing does, so the context exists for that request only and the next request is anonymous.

It is a particularly nasty upgrade bug because the failing request *succeeds* - login works, and the failure appears on the following request, so it looks like a session or cookie problem rather than a code problem.

Fixes: call `saveContext` explicitly (and construct a new context rather than mutating the existing one, which the API now warns about); or set `securityContextRepository` on the DSL and let the framework's filters handle it; or for a stateless API, confirm you actually want `NullSecurityContextRepository` and the behavior is correct as-is.

### Q150. Session fixation and concurrency

**Session fixation**: an attacker sets a known session ID before login and reuses it afterwards. Spring's default strategy is `changeSessionId()` (Servlet 3.1+), which keeps the session attributes but issues a new ID at authentication. `migrateSession` copies to a brand-new session; `newSession` starts empty; `none` disables protection and should never be used.

**Concurrency control** limits simultaneous sessions per principal:

```java
http.sessionManagement(s -> s
    .sessionFixation(f -> f.changeSessionId())
    .maximumSessions(1).maxSessionsPreventsLogin(false));
```

`maxSessionsPreventsLogin(false)` expires the oldest session; `true` rejects the new login. The operational catch is that this requires a `SessionRegistry`, and in a multi-instance deployment an in-memory registry only sees one instance's sessions - so you need Spring Session with Redis for it to mean anything. Teams frequently enable it, test it locally, and ship something that does nothing in production.

### Q151. `SecurityContextHolder` strategies

- `MODE_THREADLOCAL` (default) - per-thread, cleared at the end of each request.
- `MODE_INHERITABLETHREADLOCAL` - child threads inherit the context. Tempting for async, but dangerous with **pooled** threads: the inheritance happens at thread *creation*, so a pooled thread keeps whichever context it inherited first and later tasks silently run as the wrong user. That is a privilege-escalation bug, not just a nuisance.
- `MODE_GLOBAL` - one context for the whole JVM. Only for standalone single-user applications.

I change the default essentially never. For async propagation the correct tools are `DelegatingSecurityContextAsyncTaskExecutor`, `DelegatingSecurityContextRunnable`, or a `TaskDecorator` - all of which copy the context per *task* rather than per thread, which is the semantics you actually want.

### Q152. Security context in `@Async` `[T]`

The context is thread-bound and `@Async` runs on a different thread, so the method sees an anonymous (or null) authentication and any `@PreAuthorize` on it fails or behaves as unauthenticated.

Three fixes:

1. **Wrap the executor** - `new DelegatingSecurityContextAsyncTaskExecutor(delegate)`, or set the strategy on the `ThreadPoolTaskExecutor` via a `TaskDecorator` that copies the context and clears it in a `finally`. This is the general answer and it should be applied to every executor in the application, alongside MDC and observation propagation.
2. **Pass the identity explicitly** - the async method takes the user ID as a parameter rather than reading ambient state. Often the better design, because it makes the dependency visible.
3. **Re-authenticate as a system principal** if the work genuinely is system work, so audit records are honest about who did it.

The `finally` clear is not optional: leaving a context on a pooled thread means the next unrelated task inherits it.

### Q153. Pooled threads versus virtual threads `[T]`

The propagation mechanism is identical - both are platform-level threads from the JVM's perspective and neither inherits a `ThreadLocal` by default, so you need the same decorator either way.

What differs is the **risk profile**. A pooled thread is *reused*, so a context left behind leaks into the next task and can run someone else's work as the wrong user. A virtual thread is created per task and discarded, so there is nothing to leak into - the failure mode disappears, though you still must *set* the context if the work needs it.

The other difference is scale: virtual threads make `ThreadLocal` copies per-task rather than per-pool-thread, so at 100,000 concurrent tasks the memory cost of copying a security context is real. `ScopedValue` is the forward-looking answer, and Spring Security is moving toward it.

So the summary: same fix, but pooled threads need the `finally` clear for *correctness*, while virtual threads need it only for hygiene.

### Q154. `@EnableMethodSecurity`

It replaced `@EnableGlobalMethodSecurity`, with three notable changes: `prePostEnabled` is **true by default** (so `@PreAuthorize` works with just the annotation); it uses `AuthorizationManager` throughout rather than the voter model; and it supports meta-annotations and generic type resolution properly, so you can define `@IsAdmin` as a composed annotation and use it everywhere.

`@AuthenticationPrincipal` is resolved by an argument resolver and can navigate into the principal (`@AuthenticationPrincipal(expression = "claims['tenant']")`), or be used on a custom principal type directly.

Enable `securedEnabled` or `jsr250Enabled` only if you actually use `@Secured` or `@RolesAllowed`; leaving several models active in one codebase produces inconsistent rules that no one can audit.

### Q155. Custom SpEL in `@PreAuthorize`

Extend the expression handler to add domain-aware functions:

```java
@Component("orders")
class OrderSecurity {
    public boolean canEdit(Long orderId, Authentication auth) { ... }
}
```

then `@PreAuthorize("@orders.canEdit(#id, authentication)")` - referencing a bean by name is the simplest extension point and needs no custom handler at all. For deeper integration, register a `MethodSecurityExpressionHandler` with a custom `MethodSecurityExpressionOperations` subclass exposing new root-level functions (`isTenantMember(#id)`).

I prefer the bean-reference form: the logic is a normal Spring bean, so it is unit-testable, debuggable and refactorable, while a custom root object hides logic inside a security-framework extension that few engineers will ever read. Keep the expression itself trivial - a complex SpEL expression is untestable business logic in a string.

### Q156. `@PreAuthorize` on streams and reactive types `[T]`

`@PreAuthorize` works on any method regardless of return type, because it evaluates **before** invocation - so it is safe on `Stream` and reactive returns, provided the security context is available at call time (which for reactive means using `@EnableReactiveMethodSecurity` and the Reactor `Context`).

`@PostAuthorize` and `@PostFilter` are the problem. They need the *result*, and for a `Stream` or a `Flux` the result is a lazy pipeline, not the data - so `@PostFilter` on a `Stream` either does not filter, or forces materialization, defeating the purpose. `@PostAuthorize` on a `Mono` also cannot inspect the eventual value without subscribing.

`@EnableReactiveMethodSecurity` supports `@PreAuthorize` and `@PostAuthorize` on reactive returns, but **not** `@PreFilter`/`@PostFilter`. The practical guidance is unchanged either way: filter in the query, not after it - post-filtering a large result set is both a security-by-luck pattern and a performance defect.

### Q157. ACLs versus a tenant predicate

Spring Security ACLs give per-object, per-principal permissions with inheritance, stored in four dedicated tables and consulted per object. That is genuinely necessary for a document management or collaboration product where any user can be granted rights on any individual object.

For nearly everything else - multi-tenant SaaS, ownership checks, role-based access to a resource type - it is enormous overkill: four extra tables, a cache to keep coherent, a query per object, and machinery few engineers understand.

The alternative is to make authorization part of the **query**: `WHERE tenant_id = :tenant AND (owner_id = :user OR :user IN (SELECT ...))`, enforced at the data layer with row-level security or a Hibernate filter so it cannot be forgotten (`01-java` Q144). That is faster, simpler and provably applied.

I would adopt ACLs only when per-object grants are a first-class product feature, and even then I would evaluate a purpose-built permissions table against the framework's schema first.

### Q158. Security headers

Spring Security sets several by default: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Cache-Control: no-cache, no-store`, and `Strict-Transport-Security` on HTTPS requests.

What I always configure explicitly:

```java
http.headers(h -> h
    .httpStrictTransportSecurity(s -> s.maxAgeInSeconds(31536000).includeSubDomains(true))
    .contentSecurityPolicy(c -> c.policyDirectives("default-src 'self'; frame-ancestors 'none'"))
    .referrerPolicy(r -> r.policy(STRICT_ORIGIN_WHEN_CROSS_ORIGIN)));
```

**CSP is the one that matters most** and the one nobody sets, because it requires knowing what your pages load - and it is the primary defense that makes an XSS non-exploitable, which is what actually protects a token in a cookie (`01-java` Q140). Roll it out with `Content-Security-Policy-Report-Only` first, collect violation reports, then enforce.

For a pure JSON API most of these are irrelevant, but they cost nothing and protect against a browser being pointed at your API directly.

### Q159. CSRF for a SPA

The SPA pattern is the **double-submit cookie**: the server writes a readable cookie, JavaScript reads it and echoes it in a header.

```java
http.csrf(c -> c
    .csrfTokenRepository(CookieCsrfTokenRepository.withHttpOnlyFalse())
    .csrfTokenRequestHandler(new SpaCsrfTokenRequestHandler()));
```

`withHttpOnlyFalse()` is required so the SPA can read it - which is safe here because the token's purpose is to prove the request came from your origin, not to be a secret from your own page.

In Security 6, `XorCsrfTokenRequestAttributeHandler` became the default: it XORs the token with a random mask per response, so the encoded value differs each time. This is **BREACH** protection - without it, a compression side-channel can extract a stable token from an HTTPS response. The consequence is that the value in the cookie and the value expected in the header are encoded differently, which is where Q160 comes from.

### Q160. CSRF breaking after the Security 6 upgrade `[T]`

Two changes combine. First, the default `XorCsrfTokenRequestAttributeHandler` means the token must be **resolved through the handler** rather than compared raw. Second, `CsrfToken` loading became **deferred** for performance - the token is only generated when something actually accesses it, so if nothing reads it during the request, the cookie is never written and the SPA has no token to send.

The standard fix is a handler that opts the *header* comparison back to the plain value while keeping XOR for rendering, plus a filter that forces the token to be resolved:

```java
final class SpaCsrfTokenRequestHandler extends CsrfTokenRequestAttributeHandler {
    private final CsrfTokenRequestHandler xor = new XorCsrfTokenRequestAttributeHandler();
    @Override public void handle(HttpServletRequest req, HttpServletResponse res, Supplier<CsrfToken> token) {
        xor.handle(req, res, token);
        req.getAttribute(CsrfToken.class.getName());   // force deferred token to render
    }
    @Override public String resolveCsrfTokenValue(HttpServletRequest req, CsrfToken token) {
        return StringUtils.hasText(req.getHeader(token.getHeaderName()))
            ? super.resolveCsrfTokenValue(req, token)     // raw value from header
            : xor.resolveCsrfTokenValue(req, token);      // XOR value from form
    }
}
```

This exact scenario is documented in the Spring Security migration guide, and being able to explain *why* rather than just pasting the class is the differentiator.

### Q161. `StrictHttpFirewall`

`StrictHttpFirewall` is enabled by default and rejects requests before they reach any filter, throwing `RequestRejectedException` - which produces a bare 400 with no useful message, so it is often misdiagnosed as a routing or gateway problem.

It rejects: URL-encoded slashes (`%2F`, `%5C`), encoded percent signs, semicolons (path parameters), non-printable ASCII, backslashes, double slashes, and non-normalized paths.

The reason is that these are the classic **path traversal and authorization bypass** vectors: if the firewall allowed `%2f`, a rule protecting `/admin/**` could be bypassed by a path that the servlet container normalizes differently than the security matcher does.

If a legitimate URL is rejected - typically an ID containing a semicolon or an encoded slash - the correct fix is to change the URL design (put the value in a query parameter or encode it base64url), not to relax the firewall. If you must relax it, do so for exactly one character with a documented rationale, and never disable it wholesale.

### Q162. Securing Actuator

Three layers, and I use all of them:

1. **A separate management port** (`management.server.port=9090`) that the ingress or load balancer does not expose. This alone prevents internet reachability, and it is the highest-value control.
2. **A dedicated `SecurityFilterChain`** ordered first with `securityMatcher(EndpointRequest.toAnyEndpoint())`, permitting only `health` and `info` unauthenticated and requiring a role for the rest:

```java
http.securityMatcher(EndpointRequest.toAnyEndpoint())
    .authorizeHttpRequests(a -> a
        .requestMatchers(EndpointRequest.to("health", "info")).permitAll()
        .anyRequest().hasRole("OPS"));
```

3. **Minimal exposure** - `management.endpoints.web.exposure.include` listing only what is needed, never `*`. `/env`, `/configprops`, `/heapdump`, `/threaddump`, `/loggers` and `/shutdown` are the ones that leak or allow mutation.

Also: `management.endpoint.health.show-details=when-authorized` so an unauthenticated probe gets `UP` without a map of your dependencies, and health *groups* so liveness and readiness expose only what each needs (Q187).

### Q163. Testing security

- `@WithMockUser(roles = "ADMIN")` - the simplest case; note it prefixes `ROLE_` for `roles` but not for `authorities`.
- `@WithUserDetails("alice")` - loads through your real `UserDetailsService`, so it exercises actual user data.
- A custom `@WithSecurityContext` annotation with a `SecurityContextFactory` - the right approach for a custom principal type, a JWT with specific claims, or a tenant-scoped user. Worth building once per codebase.
- Request post-processors for per-request control: `mockMvc.perform(get("/api/x").with(jwt().jwt(j -> j.claim("scope", "read"))))`, plus `user()`, `csrf()` and `anonymous()`.

For a resource server, `jwt()` is the important one because it bypasses the need for a real token or issuer while still exercising your authority-mapping logic - which is where the bugs are.

### Q164. `@WebMvcTest` and security `[T]`

`@WebMvcTest` auto-configures Spring Security, but it only scans web-layer components - `@Controller`, `@ControllerAdvice`, `WebMvcConfigurer`, filters. Your `SecurityFilterChain` lives in a `@Configuration` class, which is **not** picked up. So the test runs against Spring Security's *default* configuration (everything authenticated, HTTP Basic) rather than yours, and assertions about your rules are meaningless - they pass for the wrong reason, or fail confusingly.

Fix: `@WebMvcTest(controllers = X.class) @Import(SecurityConfig.class)` so the real chain is used.

The second trap is method security: `@PreAuthorize` on a *service* never runs in a `@WebMvcTest`, because the service is a `@MockBean`. Method-level rules need their own focused test with a real bean and `@EnableMethodSecurity`.

The general point worth making: slice tests give speed by omitting things, and you must know exactly what was omitted or you will trust a green test that verifies nothing.

### Q165. In-place password encoder upgrades

`DelegatingPasswordEncoder` (the default from `PasswordEncoderFactories.createDelegatingPasswordEncoder()`) stores the algorithm as a prefix: `{bcrypt}$2a$10$...`. Matching dispatches on the prefix, so several algorithms coexist in one table.

To *upgrade* existing hashes, implement `UserDetailsPasswordService`:

```java
public UserDetails updatePassword(UserDetails user, String newHash) {
    repository.updatePassword(user.getUsername(), newHash);
    return withNewPassword(user, newHash);
}
```

`DaoAuthenticationProvider` calls it automatically when `passwordEncoder.upgradeEncoding(oldHash)` returns true - which happens when the stored algorithm or work factor is weaker than the current default. So users are migrated **transparently on successful login**, because that is the only moment the plaintext is available.

Users who never log in keep old hashes, so the migration needs an end date after which those accounts are forced through a reset. Stating that shows you have actually run the migration rather than read about it.

### Q166. Rolling out a security change across 40 services `[A]`

The mechanism depends on the change, but the *process* is what is being assessed.

1. **Establish the blast radius.** Which services, which callers, which of them are outside my control (partners, mobile apps with long release cycles). Mobile is usually the constraint that dictates the timeline.
2. **Make it dual-mode first.** The change must accept both old and new for a period - accept both token formats, both header names, both cookie configurations. A security change that flips atomically across 40 services cannot be rolled back and will cause an outage.
3. **Ship it disabled**, behind a flag, in the shared starter. Deploy widely with no behavior change.
4. **Enable in one low-risk service**, verify with real traffic and with the metrics that prove it (authentication success rate, 401/403 rate by client, token format distribution).
5. **Instrument the old path** so you can see exactly who is still using it, per client. This is what lets you make the retirement decision on evidence rather than on a deadline.
6. **Expand in waves**, most-instrumented first, with an explicit rollback per wave.
7. **Retire the old path** only when the metric is zero, and after contacting the remaining callers directly.

Two things I would insist on: a **security exception process** for teams that genuinely cannot meet the timeline, so they escalate rather than hide; and a real deadline with executive support, because security migrations without a forcing function run forever.

> *Hook: a security or authentication migration you drove across many services - the sequencing and the evidence you used to retire the old path.*

---

## 9. OAuth2, OIDC and Authorization Server

### Q167. Resource server with `issuer-uri`

```yaml
spring.security.oauth2.resourceserver.jwt.issuer-uri: https://idp.example.com/realms/acme
```

At startup Spring fetches `{issuer}/.well-known/openid-configuration` (or the OAuth2 equivalent), reads the `jwks_uri`, and builds a `JwtDecoder` (`NimbusJwtDecoder`) with a caching key source.

Default validations: **signature** against the JWKS keys, **`exp`** and **`nbf`** with a small clock skew, and **`iss`** matching the configured issuer. Notably, **audience is not validated by default** - which is a real security gap, because a token minted for a different service in the same realm will be accepted. That is Q168.

The startup fetch also means the application **fails to start if the IdP is unreachable**, which is a hard dependency worth knowing about. Use `jwk-set-uri` instead to skip discovery, and consider a readiness dependency rather than a startup one.

### Q168. Custom JWT validators

```java
@Bean
JwtDecoder jwtDecoder(OAuth2ResourceServerProperties props) {
    NimbusJwtDecoder decoder = JwtDecoders.fromIssuerLocation(props.getJwt().getIssuerUri());
    decoder.setJwtValidator(new DelegatingOAuth2TokenValidator<>(
        JwtValidators.createDefaultWithIssuer(issuer),
        new JwtClaimValidator<List<String>>("aud", a -> a != null && a.contains("orders-api")),
        new JwtClaimValidator<String>("azp", "trusted-client")));
    return decoder;
}
```

**Audience validation should be considered mandatory**, not optional: without it, any token from the same issuer - including one issued to a low-privilege client, or to a completely different service - is accepted by your API. This is a genuine privilege-escalation path in a shared-IdP estate, and it is the single most common resource server misconfiguration.

Other validators worth adding: a maximum token lifetime, required scopes for the service, and a `tid`/tenant claim check.

### Q169. Claims to authorities `[T]`

`JwtAuthenticationConverter` uses `JwtGrantedAuthoritiesConverter`, which by default reads the **`scope`** or **`scp`** claim and prefixes each value with **`SCOPE_`**. So a token with `scope: "orders.read"` produces the authority `SCOPE_orders.read`.

`hasRole('ADMIN')` checks for `ROLE_ADMIN`, which no standard OIDC token contains - and Keycloak puts roles in `realm_access.roles`, Cognito in `cognito:groups`, Entra ID in `roles`. None of these is read by default, which is why authorization "silently does nothing" until configured.

```java
@Bean JwtAuthenticationConverter converter() {
    JwtAuthenticationConverter c = new JwtAuthenticationConverter();
    c.setJwtGrantedAuthoritiesConverter(jwt -> {
        Map<String, Object> realm = jwt.getClaim("realm_access");
        List<String> roles = realm == null ? List.of() : (List<String>) realm.get("roles");
        return roles.stream().map(r -> new SimpleGrantedAuthority("ROLE_" + r)).toList();
    });
    return c;
}
```

Design guidance: use `hasAuthority('SCOPE_...')` for API scopes (what the *client* may do) and roles for user permissions (what the *user* may do), and do not conflate them - they answer different questions.

### Q170. Introspection versus local validation

**Local JWT validation** is a signature check with no network call, so it is fast and has no runtime dependency on the IdP - but the token is valid until it expires and cannot be revoked (`01-java` Q135), and any claim staleness is unbounded.

**Opaque token introspection** (`spring.security.oauth2.resourceserver.opaquetoken.*`) calls the IdP's introspection endpoint per request, so revocation is immediate and claims are always current. The costs are a network round trip on every request, a hard runtime dependency on the IdP, and load on it proportional to your traffic.

You must cache to make introspection viable - a short TTL (30-60 seconds) keyed on a hash of the token, which is a deliberate trade of revocation latency for throughput. Say that number out loud: "we accept up to 60 seconds of stale authorization" is an architectural decision, not an implementation detail.

I choose introspection when tokens are opaque by policy, when immediate revocation is a requirement (financial or admin operations), or when the token would otherwise carry sensitive claims. JWT otherwise.

### Q171. `OAuth2AuthorizedClientManager`

For machine-to-machine calls, register a client with the `client_credentials` grant and let Spring manage token acquisition, caching and refresh:

```java
@Bean OAuth2AuthorizedClientManager manager(ClientRegistrationRepository reg,
                                            OAuth2AuthorizedClientService svc) {
    var provider = OAuth2AuthorizedClientProviderBuilder.builder()
        .clientCredentials().refreshToken().build();
    var manager = new AuthorizedClientServiceOAuth2AuthorizedClientManager(reg, svc);
    manager.setAuthorizedClientProvider(provider);
    return manager;
}

WebClient client = WebClient.builder()
    .apply(new ServletOAuth2AuthorizedClientExchangeFilterFunction(manager)
        .oauth2Configuration()).build();
// then: .attributes(clientRegistrationId("inventory-api"))
```

The value is that token lifecycle - fetch, cache, refresh before expiry, retry on 401 - is handled for you, which is code teams otherwise write badly and repeatedly. `AuthorizedClientServiceOAuth2AuthorizedClientManager` is the variant for non-request contexts such as scheduled jobs, where there is no `HttpServletRequest` to bind to.

### Q172. Token relay versus exchange

**Relay** forwards the caller's access token unchanged to the downstream. Simple, and the downstream sees the original user - but it means every service in the chain holds a token valid for *all* the audiences in it, so a compromise anywhere grants access everywhere. It also fails cleanly only if the token's audience includes each downstream.

**Token exchange** (RFC 8693) trades the incoming token for a new one scoped to the specific downstream, with a narrower audience and scope, optionally preserving the user identity through the `act` (actor) claim. That gives least privilege per hop and an auditable delegation chain.

Relay is acceptable within a single trust boundary where all services are equally trusted and the audience is correct. Exchange is what I would use crossing a trust boundary, calling a partner, or where a downstream should not be able to impersonate the user elsewhere.

In Spring Cloud Gateway, `TokenRelay` is a one-line filter; exchange requires an IdP that supports RFC 8693 and an explicit call, which is the practical reason relay is more common than it should be.

### Q173. The three OAuth2 roles

- **`oauth2ResourceServer`** - my API *validates* incoming tokens. This is what a backend service almost always needs.
- **`oauth2Login`** - my application *authenticates users* via an external IdP, receiving an ID token and establishing a session. This is a server-rendered web application acting as an OIDC relying party.
- **`oauth2Client`** - my application *obtains tokens to call other APIs*, either on a user's behalf (authorization code) or as itself (client credentials).

They are independent and often combined: a BFF uses `oauth2Login` for the user session and `oauth2Client` to call downstream APIs; a pure API uses only `oauth2ResourceServer`.

Candidates frequently conflate `oauth2Login` and `oauth2ResourceServer` and try to configure both for a stateless API, which produces confusing redirect-to-login behavior on a JSON endpoint. Naming the three roles cleanly is a quick credibility signal.

### Q174. Running Spring Authorization Server

Use a managed IdP (Keycloak, Cognito, Okta, Entra) by default. They provide user management, MFA, federation, social login, admin UIs, password policies, account recovery, compliance certifications and a security team - all of which you would otherwise build and maintain.

I would run Spring Authorization Server when: the authorization server must be deeply embedded in the product's domain model (issuing tokens with complex, application-specific claims computed from your data); there is a hard data-residency or air-gap requirement; the licensing cost of a commercial IdP at your user count is prohibitive; or you need a lightweight, purpose-built issuer for internal service-to-service tokens only, with no human users.

The point to make explicitly: it is a **framework for building an authorization server**, not a product. It has no user store, no admin console, no MFA and no account recovery - you build those. That is a multi-year ownership commitment for a security-critical component, and it should be a deliberate decision, not a default.

### Q175. JWKS and key rotation

`NimbusJwtDecoder` fetches the JWKS from `jwk-set-uri` and caches it (5 minutes by default, with the cache keyed by key ID). When a token arrives with an unknown `kid`, the decoder refreshes the JWKS, which is what makes rotation transparent.

A correct rotation publishes the new key **before** signing with it, so validators can fetch it in advance, and keeps the old key published until every token signed with it has expired. If an IdP rotates and removes in one step, every in-flight token fails validation - a brief total outage.

Operational concerns: the JWKS endpoint becomes a runtime dependency, so cache it and make failure graceful rather than fatal; a JWKS refresh storm across many instances after a rotation can rate-limit you at the IdP; and clock skew between issuer and validator causes spurious `exp`/`nbf` failures, so allow a small skew and keep NTP working.

### Q176. Customizing tokens

```java
@Bean OAuth2TokenCustomizer<JwtEncodingContext> tokenCustomizer() {
    return context -> {
        if (context.getTokenType() == OAuth2TokenType.ACCESS_TOKEN) {
            context.getClaims().claim("tenant", lookupTenant(context.getPrincipal()));
        }
    };
}
```

Keep tokens **small**, and be able to say why: they are sent on every request, so size is latency and bandwidth on the hot path; they often live in headers with proxy size limits (8KB is a common ceiling, and exceeding it produces a confusing 431 or a silently dropped header); and every claim is readable by anyone holding the token, so a claim is a disclosure decision.

The specific anti-pattern is putting a user's full permission list in the token. It grows unboundedly, it goes stale the moment permissions change, and it leaks your authorization model to the client. Put a stable identity and a tenant in the token, and resolve fine-grained permissions server-side where they can be current.

### Q177. Refresh token rotation `[T]`

Spring Authorization Server rotates refresh tokens by default - each use issues a new refresh token and invalidates the previous one (configurable with `reuseRefreshTokens(false)`).

What it does **not** give you is **reuse detection with family revocation**, which is the part that actually provides security. Rotation alone means a stolen token works until the legitimate client next refreshes; detection means that when an *already-used* token is presented, you conclude the family has leaked and revoke the entire chain, forcing re-authentication.

Implementing it requires tracking a token family identifier and the used-token history, and deciding the response: revoke the family, log a security event, and ideally notify the user. You also have to handle the benign false positive - a client that retried a refresh after a network timeout legitimately presents the same token twice - usually with a short grace window where the immediately-previous token is accepted once.

Naming both the gap and the false-positive handling is what separates a real implementation from a documentation summary.

### Q178. Multi-issuer resource server

```java
@Bean JwtIssuerAuthenticationManagerResolver resolver() {
    return JwtIssuerAuthenticationManagerResolver.fromTrustedIssuers(
        "https://idp.example.com/realms/tenant-a",
        "https://idp.example.com/realms/tenant-b");
}
http.oauth2ResourceServer(o -> o.authenticationManagerResolver(resolver));
```

It reads the `iss` claim (without validating the signature yet), selects or lazily builds the `AuthenticationManager` for that issuer, and delegates. Each issuer gets its own decoder and JWKS cache.

The critical constraint is the **trusted issuer list**. A resolver that accepts any issuer from the token and fetches its JWKS is a complete authentication bypass - an attacker stands up their own IdP, signs a token claiming to be an admin, and your service dutifully fetches their public key and validates it. The trusted list must be explicit and configured, never derived from the token.

For tenant-per-issuer setups, also map the issuer to a tenant identity in the authentication and enforce it in the data layer, so a valid token for tenant A cannot read tenant B's data.

### Q179. OIDC logout

Local logout clears your session; it does **not** end the session at the IdP, so the next login silently succeeds without prompting and the user believes they logged out when they did not. That is the gap.

`OidcClientInitiatedLogoutSuccessHandler` redirects to the IdP's `end_session_endpoint` with the `id_token_hint` and a `post_logout_redirect_uri`, ending both sessions:

```java
var handler = new OidcClientInitiatedLogoutSuccessHandler(clientRegistrationRepository);
handler.setPostLogoutRedirectUri("{baseUrl}/logged-out");
http.logout(l -> l.logoutSuccessHandler(handler));
```

**Back-channel logout** solves the other direction: the user logs out at the IdP (or an admin terminates the session) and the IdP calls each relying party's logout endpoint directly, so applications can invalidate their sessions without the user's browser being involved. Spring Security supports it via `oidcLogout()` with a session registry. It matters in an SSO estate where "log out everywhere" is a real requirement - and it needs a shared session store to work across instances.

### Q180. Propagating the principal

- **Synchronous HTTP** - the exchange filter function attaches the token automatically (Q171), or you propagate the incoming one for relay.
- **`@Async` / executors** - a `TaskDecorator` copying the `SecurityContext` (Q152).
- **Reactive** - the Reactor `Context` via `ReactiveSecurityContextHolder` (Q118).
- **Messaging** - there is no ambient context, so the identity must be carried **in the message**. Put a signed token or a verifiable claim in a header, or - better for durability - record the acting principal as part of the message payload, because a token will have expired by the time a delayed or replayed message is processed.

That last point is the one worth emphasizing: propagating a *token* into a queue is a common mistake, because tokens are short-lived and messages are not. For asynchronous work, record **who requested it** as data and re-derive authority at processing time, or execute as an explicit system principal with the original requester recorded for audit.

### Q181. Token works in Postman, fails in the service `[T]`

Diagnose in this order, because the causes are ranked by frequency:

1. **Audience.** Postman does not validate `aud`; your service does (if configured). Decode the token at jwt.io and compare `aud` with what the service expects.
2. **Issuer mismatch.** A trailing slash difference between the `iss` claim and `issuer-uri` fails an exact string comparison. This one wastes hours.
3. **Authority mapping** (Q169). Authentication succeeded and *authorization* failed - a 403, not a 401, though a misconfigured entry point can render it as 401.
4. **Clock skew.** The service's clock is ahead, so a fresh token is `nbf`-invalid.
5. **The token is not reaching the service** - a gateway stripping the `Authorization` header, or a proxy dropping it on redirect.
6. **Scope or resource** - the token was issued for a different resource server.

To stop it being guesswork, log the specific failure: `OAuth2AuthenticationException` carries an `OAuth2Error` with a description, and returning it in the `WWW-Authenticate` header (as the spec intends) tells the caller *why* without leaking anything sensitive. Set `logging.level.org.springframework.security=DEBUG` in a non-production environment and the decoder tells you exactly which validator rejected it.

### Q182. Authentication for a mixed estate `[A]`

**Clarify first**: who are the users (employees, consumers, partners), is there an existing IdP, what regulatory constraints apply, what is the mobile release cadence, and do partners need per-tenant isolation?

The shape I would propose:

- **One IdP** as the single identity authority, with the user store, MFA and federation. Not one per channel.
- **Web SPA** - authorization code with PKCE, and I would push for the **BFF pattern**: tokens held server-side, the browser gets only an `HttpOnly` session cookie. That removes token-in-browser storage entirely, which is the highest-value decision here (`01-java` Q140). If a pure SPA is mandated, then PKCE with the access token in memory and the refresh token in an `HttpOnly`, `SameSite` cookie scoped to the token endpoint.
- **Mobile** - authorization code with PKCE, refresh token in the platform keystore, rotation with reuse detection. Mobile's slow release cycle means the token contract must be versioned and backward compatible for a long window.
- **Partner APIs** - client credentials with per-partner clients, audience-restricted short-lived tokens, per-partner rate limits, and mTLS where the partner supports it. Certificate-bound tokens (RFC 8705) if the data justifies it.
- **Service-to-service** - workload identity (SPIFFE, IRSA) plus mTLS in the mesh for *service* identity, and audience-scoped client credentials for *application* authorization. Propagate the end-user identity separately via token exchange (Q172) so downstream services can enforce user-level rules.

Cross-cutting: short access token lifetimes, a documented revocation story per channel, one authorization model expressed the same way everywhere, and a central audit of authentication and authorization decisions. I would also state what I am deliberately not doing - no ROPC, no implicit, no long-lived API keys - and the migration path for anything that exists today.

---

## 10. Spring Boot production engineering

### Q183. Writing a starter

Two modules by convention: `acme-spring-boot-autoconfigure` (the code and conditions) and `acme-spring-boot-starter` (a dependency aggregator with no code).

```java
@AutoConfiguration(after = DataSourceAutoConfiguration.class)
@ConditionalOnClass(AcmeClient.class)
@EnableConfigurationProperties(AcmeProperties.class)
public class AcmeAutoConfiguration {
    @Bean @ConditionalOnMissingBean
    AcmeClient acmeClient(AcmeProperties props) { return new AcmeClient(props.url()); }
}
```

Registered in `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` (one class name per line).

The things that make it good rather than merely working: `@ConditionalOnMissingBean` on every bean so consumers can override; `@ConditionalOnProperty` with `matchIfMissing` for opt-in features; explicit `after`/`before` ordering; the configuration processor for metadata (Q37); documented and validated properties; and a test using `ApplicationContextRunner` that asserts both the configured and backed-off cases:

```java
new ApplicationContextRunner()
    .withConfiguration(AutoConfigurations.of(AcmeAutoConfiguration.class))
    .withUserConfiguration(CustomClientConfig.class)
    .run(ctx -> assertThat(ctx).getBean(AcmeClient.class).isSameAs(ctx.getBean("myClient")));
```

Never put `@ComponentScan` in a starter - it scans the *consumer's* packages and causes bewildering conflicts.

### Q184. Back-off and ordering `[T]`

`@ConditionalOnMissingBean` only sees beans that are **already registered** when the condition is evaluated. Auto-configurations are processed by a `DeferredImportSelector`, so they run **after** all user configuration - which is exactly why a user bean always wins.

But *between* auto-configurations, order matters entirely. If configuration A defines a `DataSource` conditionally on none existing, and configuration B does the same, whichever is evaluated first wins and the other backs off. Without explicit `@AutoConfiguration(after = ...)` or `@AutoConfigureOrder`, the order is derived from the imports file and is not something to rely on.

The failure is silent and environment-dependent: it works locally and a different classpath ordering in the deployed artifact produces a different bean. Diagnosis is the `--debug` auto-configuration report, which lists positive and negative matches with the reason - that report is the single most useful tool for "why is this bean not what I expect".

### Q185. `AutoConfiguration.imports`

Before Boot 2.7, auto-configurations were listed under the `EnableAutoConfiguration` key in `META-INF/spring.factories`. Boot 2.7 introduced `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` - a plain newline-delimited list - and Boot 3 **removed** the `spring.factories` support for this key entirely.

Reasons for the change: `spring.factories` was a single overloaded file serving many unrelated purposes, it was slow to parse (every JAR, every key), and it gave no structure for ordering. The new file is purpose-specific, cheaper to read, and works better with AOT processing, which needs to resolve the auto-configuration set at build time.

The practical consequence is that a library published for Boot 2.6 silently contributes **nothing** on Boot 3 - no error, the beans just do not appear. That is one of the more confusing Boot 3 migration failures (Q252), and the fix is to ship both files during the transition.

### Q186. Custom Actuator endpoint

```java
@Component
@Endpoint(id = "cache-stats")
class CacheStatsEndpoint {
    @ReadOperation Map<String, CacheStats> all() { ... }
    @ReadOperation CacheStats one(@Selector String name) { ... }
    @WriteOperation void evict(@Selector String name) { ... }
    @DeleteOperation void clear() { ... }
}
```

`@Endpoint` is technology-agnostic; `@WebEndpoint` and `@JmxEndpoint` restrict exposure. `@Selector` binds a path segment.

Two things to get right: it must be added to `management.endpoints.web.exposure.include` to be reachable at all, and any `@WriteOperation` or `@DeleteOperation` is a **mutating production operation**, so it needs authorization (Q162) and audit logging. An endpoint that clears a cache or changes a log level is an attack surface, and I have seen `/actuator/loggers` used to enable DEBUG logging on a production service by someone who should not have had access.

### Q187. Health indicators and groups

```java
@Component
class PaymentGatewayHealthIndicator implements HealthIndicator {
    public Health health() {
        return gateway.ping() ? Health.up().build()
                              : Health.down().withDetail("endpoint", url).build();
    }
}
```

```yaml
management.endpoint.health.group.readiness.include: readinessState,db
management.endpoint.health.group.liveness.include: livenessState
management.endpoint.health.probes.enabled: true
```

Boot exposes `/actuator/health/liveness` and `/actuator/health/readiness`, and integrates with `ApplicationAvailability` so readiness automatically reports `OUT_OF_SERVICE` during startup and graceful shutdown - which is what makes zero-downtime rolling deployments work without custom code.

The design rule: a custom indicator is only worth writing if its failure should change how the platform treats the instance. Otherwise it is a metric, not a health check.

### Q188. What belongs in readiness `[T]`

**Readiness** should contain only dependencies without which this instance cannot serve *any* useful traffic - typically its own database. **Liveness** should contain almost nothing: it answers "is this process broken beyond recovery", and its failure causes a restart.

The outage pattern: someone adds a downstream API or a third-party service to readiness (or worse, to liveness). That dependency has a blip. **Every instance simultaneously** reports not-ready, Kubernetes removes them all from the Service endpoints, and a partial degradation - where most endpoints would still have worked - becomes a total outage. If it was in liveness, the whole fleet restarts at once, and the cold-start stampede then overwhelms the dependency as it recovers, turning a two-minute blip into a twenty-minute incident.

So: liveness must be dependency-free; readiness contains only hard dependencies; everything else is a metric with an alert, and the application degrades gracefully (`01-java` Q181). Boot makes this easy to get wrong because `@ConditionalOnEnabledHealthIndicator` auto-registers indicators for anything on the classpath - Redis, Kafka, Mongo, every downstream with a starter - and they all land in the default health group. Curating that list explicitly is a required production step.

### Q189. Graceful shutdown

`server.shutdown=graceful` plus `spring.lifecycle.timeout-per-shutdown-phase=30s`. On `SIGTERM`, the web server stops accepting new connections and waits for in-flight requests to complete before the context closes.

What it does **not** cover, and must be handled separately:

- **Message consumers** - Kafka listener containers, SQS pollers, and `@Scheduled` tasks. These are `SmartLifecycle` beans; make sure they stop in the right phase, finish the in-flight message and commit the offset.
- **Async executors** - set `setWaitForTasksToCompleteOnShutdown(true)` and an await timeout, or queued tasks are dropped.
- **Load balancer deregistration** - the crucial one. Kubernetes sends `SIGTERM` and removes the endpoint *concurrently*, and endpoint propagation to every kube-proxy takes time. So the pod must keep serving for a few seconds after `SIGTERM` or it will reject requests that were already routed to it. A `preStop` sleep of 5-10 seconds is the standard fix, and it must be shorter than `terminationGracePeriodSeconds`.

The full sequence to state: `preStop` sleep → readiness fails → traffic drains → `SIGTERM` → graceful shutdown of listeners and requests → context close → exit.

### Q190. Micrometer meter types

- **`Counter`** - monotonically increasing. Rate is computed at query time; never expose a "rate" yourself.
- **`Timer`** - duration plus count. Records latency distributions.
- **`Gauge`** - a sampled instantaneous value (queue depth, pool size). Micrometer holds a **weak reference** to the source object, so a gauge on a local variable is garbage collected and reports NaN - a classic bug.
- **`DistributionSummary`** - distributions of non-time values (payload size, batch size).
- **`LongTaskTimer`** - for in-progress long-running work, which a normal `Timer` cannot show until it finishes.

**Percentiles versus histograms** is the question that separates people who have run these systems: `publishPercentiles` computes quantiles *in the application*, so they **cannot be aggregated** across instances - averaging p99s from ten pods is statistically meaningless. `publishPercentileHistogram` exports bucket counts, which Prometheus aggregates correctly with `histogram_quantile`. For any multi-instance service, use histograms, and accept the higher series count.

### Q191. High-cardinality tags `[T]`

Every unique combination of tag values creates a **separate time series**, stored and indexed independently. Tagging with a user ID gives you one series per user; with a raw URL path containing IDs, one per resource. A million users means a million series per metric, which exhausts memory in Prometheus, blows past the cardinality limits of a managed backend, and costs a fortune in a per-series-priced service. It typically takes the metrics system down for *everyone*, not just your service - so it is a shared-platform incident.

The specific Spring trap: `http.server.requests` is tagged with `uri`, and if you use a path *without* a template - or write a custom tag from `request.getRequestURI()` - you get one series per ID. Spring uses the **matched pattern** (`/orders/{id}`) precisely to avoid this, which is why `uri` is `UNKNOWN` for unmatched requests rather than the raw path.

Guardrails: keep tag values to bounded, low-cardinality sets (status, method, outcome, endpoint template); put high-cardinality identifiers in **traces and logs**, which are designed for it; set `management.metrics.web.server.max-uri-tags`; and review new metrics for cardinality the same way you review a database index.

### Q192. The Observation API

`@Observed` and the `ObservationRegistry` unify what used to be three separate instrumentations: you record an observation **once**, and registered handlers produce a metric (a `Timer`), a trace span, and optionally a log entry from the same event.

```java
@Observed(name = "order.process", contextualName = "process-order",
          lowCardinalityKeyValues = {"channel", "web"})
public Order process(OrderRequest request) { ... }
```

The key/value distinction maps exactly onto Q191: **low cardinality** values become metric tags *and* span attributes; **high cardinality** values become span attributes only. That single design decision encodes the right practice into the API.

The practical benefit is consistency - metric names and span names agree, so a latency spike on a dashboard leads directly to the matching traces. It is proxy-based, so the usual self-invocation rule applies (Q50).

### Q193. Micrometer Tracing

Micrometer Tracing replaced **Spring Cloud Sleuth** in Boot 3; Sleuth is not available for Boot 3, which is a real migration item. It is a facade over a tracer - OpenTelemetry or Brave - with bridges chosen by dependency.

- **Propagation**: W3C `traceparent` by default (Sleuth used B3), which is a wire-format change to coordinate across services during migration.
- **Sampling**: `management.tracing.sampling.probability`. Head-based by default; tail-based sampling (keeping all errors and slow traces) happens in the collector, not the application, and is what you actually want in production.
- **Baggage**: key-value data propagated across the whole trace (`management.tracing.baggage.remote-fields`), optionally copied into MDC so it appears in logs. Useful for tenant or request-type, but every baggage field is on every hop's wire format, so keep it minimal.

Instrumentation is automatic for MVC, WebFlux, `RestClient`/`WebClient`, JDBC, Kafka and scheduled tasks; the gap is always custom async boundaries, which need context propagation configured (Q95).

### Q194. Diagnosing slow startup

```java
public static void main(String[] args) {
    SpringApplication app = new SpringApplication(Application.class);
    app.setApplicationStartup(new BufferingApplicationStartup(4096));
    app.run(args);
}
```

Then `/actuator/startup` returns the recorded step timings - bean instantiation, auto-configuration evaluation, post-processing - which turns "startup is slow" into a ranked list.

Common findings and their fixes: heavy classpath scanning (narrow `@ComponentScan`, or use explicit imports); auto-configurations evaluating conditions against a huge classpath (exclude what you do not use); eager connection pool initialization and Flyway migrations at startup (move migrations to a separate step); JPA `EntityManagerFactory` building for hundreds of entities; a blocking network call in `@PostConstruct` - often the real culprit, and one that turns an IdP or config-server blip into a failed deployment.

Startup time matters more than it used to: it dictates how fast you can scale out, how quickly a rolling deployment completes, and how long a crash loop takes to recover.

### Q195. Lazy initialization

`spring.main.lazy-initialization=true` defers bean creation until first use. Startup gets dramatically faster, which is genuinely useful for **local development** and for tests.

What it hides is the problem: configuration errors, missing beans and bad wiring no longer fail at startup - they fail on the first request that touches them, in production, at 3am. It converts a deployment-time failure into a runtime failure, which is exactly the wrong direction. It also shifts the cost to the first request of each path, so latency is unpredictable after every deployment and the "warm" state is only reached gradually.

So: yes for development and tests, no for production. If production startup is slow, fix the cause found in Q194 rather than deferring it. `@Lazy` on specific expensive beans is a reasonable targeted compromise.

### Q196. Spring AOT

AOT processing runs at **build time** and generates Java source: bean definitions as explicit registration code, proxy classes, and reflection/resource/serialization hints. At runtime the application skips configuration class parsing, condition evaluation and most reflection, which cuts startup time and memory even on the JVM - and it is a prerequisite for native images.

What can no longer work, because the bean set is fixed at build time:

- **Conditions are evaluated at build time**, so `@Profile` and `@ConditionalOnProperty` are resolved with the *build-time* environment. A profile that changes which beans exist must be active during the build, and a property-conditional bean cannot be toggled at deploy time.
- Beans registered dynamically at runtime, and `BeanFactoryPostProcessor`s that alter definitions based on runtime state.
- Unregistered reflection, dynamic proxies, and classpath scanning for classes not known at build time.

The practical consequence to name: **profile-conditional beans and AOT are fundamentally in tension**, which is another argument for profiles selecting values rather than beans (Q35).

### Q197. Native image constraints `[T]`

GraalVM's closed-world assumption means everything reachable must be known at build time. What breaks: unregistered reflection, dynamic proxies, JNI, dynamic class loading, resource loading by pattern, serialization, and some bytecode-generating libraries. CGLIB proxies are replaced at build time, which is why `@Configuration(proxyBeanMethods = false)` matters more here.

Spring's AOT engine generates most hints automatically for framework usage. Yours are declared explicitly:

```java
@Configuration
@ImportRuntimeHints(AcmeHints.class)
class AcmeConfig {}

class AcmeHints implements RuntimeHintsRegistrar {
    public void registerHints(RuntimeHints hints, ClassLoader cl) {
        hints.reflection().registerType(LegacyDto.class, MemberCategory.INVOKE_DECLARED_CONSTRUCTORS,
                                        MemberCategory.DECLARED_FIELDS);
        hints.resources().registerPattern("templates/*.ftl");
    }
}
```

Or `@RegisterReflectionForBinding(LegacyDto.class)` for the common serialization case.

The honest operational assessment: build times of five to ten minutes, a debugging experience unlike the JVM, less mature profiling, and failures that appear only in the native binary. It is worth it for genuinely short-lived or scale-to-zero workloads (Lambda, CLI tools). For a long-running service, CDS or CRaC (Q198) usually gives enough of the startup benefit at a fraction of the complexity - and saying that is a stronger answer than enthusiasm for native.

### Q198. CDS and CRaC

**Class Data Sharing** (first-class support in Boot 3.3) dumps the loaded class metadata to an archive that subsequent JVMs memory-map instead of re-parsing. A training run produces the archive, which ships in the image. Typical improvement is 30-40 percent off startup, with no code changes, no framework restrictions and full JVM behavior retained. This is the highest value-to-effort option and my default recommendation.

**Project CRaC** (Coordinated Restore at Checkpoint) snapshots a **running, warmed-up** JVM and restores from it in tens of milliseconds - so you skip class loading, context refresh *and* JIT warm-up. Spring supports the lifecycle callbacks (`spring.context.checkpoint=onRefresh`, or a full checkpoint after warm-up).

The catch with CRaC is the same as with Lambda SnapStart: anything captured in the snapshot must be re-established on restore - open connections, cached credentials, random seeds, timers, and anything that assumed a unique process identity. Beans implement `org.crac.Resource` with `beforeCheckpoint`/`afterRestore` hooks.

The decision framework: CDS first (free), CRaC when startup latency is genuinely business-critical, native image only when you need both instant start and minimal memory and can accept the build and debugging cost.

### Q199. Images and layers

- **Layered jars** (`spring-boot-maven-plugin` layered mode) separate dependencies, spring-boot-loader, snapshot dependencies and application classes. Since dependencies change rarely and application code changes every build, only a small layer is rebuilt and re-pushed - the practical win is push and pull time, not image size.
- **Buildpacks** via `bootBuildImage` produce an optimized image with no Dockerfile: correct layering, a suitable JRE, memory calculation for the container, and an SBOM. It also handles CDS and native builds through configuration. My default for teams that do not want to own a Dockerfile.
- **A hand-written multi-stage Dockerfile** when you need control: a specific base image, distroless, extra tooling, or corporate scanning requirements.

Regardless of approach: run as non-root, pin the base image by digest, use `.dockerignore`, order instructions least-to-most volatile, and set `-XX:MaxRAMPercentage` rather than a fixed heap (`01-java` Q203).

### Q200. `TaskExecutor` and virtual threads

Historically, `@Async` with no configured executor fell back to `SimpleAsyncTaskExecutor`, which creates a **new platform thread per call** with no pooling and no bound - unusable in production and the cause of many thread-exhaustion incidents.

Boot auto-configures an `applicationTaskExecutor` (a `ThreadPoolTaskExecutor`) which `@Async` uses, configurable via `spring.task.execution.*`. **In Boot 3.2+ with `spring.threads.virtual.enabled=true`**, that becomes a `SimpleAsyncTaskExecutor` backed by **virtual** threads - where unbounded thread creation is the intended model rather than a bug.

What I configure explicitly either way:

```yaml
spring.task.execution.pool.core-size: 8
spring.task.execution.pool.max-size: 32
spring.task.execution.pool.queue-capacity: 100
spring.task.execution.shutdown.await-termination: true
spring.task.execution.shutdown.await-termination-period: 30s
```

Plus a `TaskDecorator` for context propagation (Q95), and a separate named executor per workload so one slow task type cannot starve another - the bulkhead principle applied inside the process. With virtual threads, the pool bound disappears and must be replaced by an explicit `Semaphore` where the downstream needs protection (Q101).

### Q201. Structured logging

Boot 3.4 added built-in structured logging: `logging.structured.format.console=ecs` (or `logstash`, `gelf`) emits JSON directly, removing the Logback encoder dependency and XML that every team previously copied between projects.

What makes logs actually useful in production:

- **JSON, one event per line**, so the collector does not need multiline stitching - which is what breaks stack traces in most log pipelines.
- **Correlation** - trace and span IDs in the MDC, populated automatically by Micrometer Tracing, plus tenant and user identifiers. Add them with `logging.structured.ecs.service.*` and MDC.
- **Discipline about volume** - log ingestion is frequently the largest observability cost line. INFO for business events, DEBUG off, sampling or rate limiting on hot paths.
- **Never log secrets, tokens or PII**, enforced with a Logback converter or a scanner in CI, because a token in a log is a credential in a system with different access controls.

I also return the trace ID in an error response header, so a support ticket leads directly to the logs and traces.

### Q202. Actuator secret leakage `[T]`

Boot sanitizes values whose **key** matches patterns like `password`, `secret`, `key`, `token`, `credentials`, and URIs containing credentials. Sanitization is therefore **name-based**, and the leaks come from everything it cannot recognize:

- A property named `connectionString`, `dsn`, `sasl.jaas.config` or `webhookUrl` containing an embedded password.
- A nested object in `@ConfigurationProperties` whose fields have innocuous names.
- The value appearing under a *different* endpoint - `/heapdump` contains every string in memory, and `/threaddump` can contain arguments.
- `/configprops` showing bound objects, and `/env` showing every property source.

Handling: set `management.endpoint.env.show-values=never` and `management.endpoint.configprops.show-values=never` (Boot 3 defaults to `NEVER`, but verify on your version); do not expose those endpoints at all in production; register a `SanitizingFunction` for your own naming conventions; and treat `/heapdump` as equivalent to production shell access.

The structural fix is to keep secrets out of the `Environment` in the first place (Q41) - fetch at use time, wrap in a redacting holder type, and never bind a raw secret into a properties object.

### Q203. `DataSource` and Hikari defaults

Boot's defaults are development defaults. In production I always set:

```yaml
spring.datasource.hikari:
  maximum-pool-size: 15            # derived, not guessed - see 01-java Q161
  minimum-idle: 15                 # equal to max: avoid churn under spiky load
  connection-timeout: 3000         # fail fast rather than queue forever
  max-lifetime: 570000             # shorter than DB/LB idle timeout (e.g. 600s)
  idle-timeout: 300000
  leak-detection-threshold: 20000  # non-production, or generous in production
  validation-timeout: 2000
```

The reasoning that matters: `maximum-pool-size` is a **concurrency limit**, not a throughput dial - bigger is slower past saturation, and it must be multiplied by instance count against the database's `max_connections`. `max-lifetime` must be shorter than any idle timeout on the database, proxy or NAT gateway, or you get intermittent "connection reset" errors that are nearly impossible to reproduce. `connection-timeout` decides whether a database slowdown becomes a fast failure or a pile-up.

I also always enable Hikari metrics and alert on `hikaricp_connections_pending`, which is the earliest reliable warning of database trouble.

### Q204. A platform starter without becoming a bottleneck `[A]`

The failure mode is a platform team that owns a starter every service must use, cannot keep up with requests, and becomes the thing everyone routes around. Avoiding it is mostly about defaults and governance rather than code.

Principles I apply:

- **Defaults, not mandates.** Every bean is `@ConditionalOnMissingBean` and every feature is `@ConditionalOnProperty` with a sensible default, so a team can override any decision locally without a pull request to my repository. The starter is opinionated but never a straitjacket.
- **Thin and composable.** Several small starters (observability, security, resilience, messaging) rather than one monolith, so a team adopts what it needs.
- **No `@ComponentScan`, no surprise beans**, and no transitive dependency choices that constrain consumers - the fastest way to be resented is to force a library version.
- **Inner source.** Consumers can raise pull requests, with clear contribution docs and a review SLA. My team owns quality, not authorship.
- **Versioning discipline** - semantic versioning, a documented support window for the previous major, deprecation via configuration metadata (Q37) so warnings appear in the IDE, and migration notes with each release.
- **Automated adoption** - a bot raising the upgrade pull request against every consuming repository, with the pipeline proving it, so upgrading is a review rather than a project.
- **Measure the right thing** - not adoption count, but whether the starter reduces incidents and time-to-first-deploy. If teams are working around it, that is my defect to fix.

> *Hook: a platform library you owned - the adoption approach, and how you handled a breaking change.*

---

## 11. Spring Cloud and microservices

### Q205. Config Server

Config Server serves configuration from a Git (or Vault) backend, with per-application and per-profile resolution, encryption support (`{cipher}`), and refresh via `/actuator/refresh` or Spring Cloud Bus.

Why many teams moved away on Kubernetes: it adds a **hard startup dependency** - if Config Server is down, nothing starts, so it must be as available as everything that depends on it; it duplicates what the platform already provides through ConfigMaps, Secrets, Parameter Store and Secrets Manager; and it introduces a second, parallel place where configuration lives, which is exactly the drift problem it was meant to solve. Runtime refresh also proves less useful in practice than it sounds (Q206), since immutable deployments are the safer model anyway.

I would still use it when running outside Kubernetes, when configuration genuinely must be versioned in Git with review and audit, or in a large estate that needs one configuration model across heterogeneous platforms. Otherwise `spring.config.import` against the platform's own store is simpler and has fewer failure modes.

### Q206. `@RefreshScope`

Covered mechanically in Q38. In the Spring Cloud context, the additional points are that `/actuator/refresh` rebinds the `Environment` and publishes `RefreshScopeRefreshedEvent`, and Spring Cloud Bus can broadcast that across the estate over a message broker.

What it cannot refresh: `@Value` in singletons, anything constructed at startup from a property (connection pools, clients with fixed base URLs, Kafka consumers), `@ConfigurationProperties`-derived objects created eagerly, and log levels (which have their own Actuator endpoint).

My practical position: bus-wide refresh across dozens of services is a distributed state change with no transactionality - some services refresh, some fail, and you cannot tell which configuration is live where. For anything that matters I prefer a rolling restart, which is observable, versioned and rollback-able. Refresh is fine for a threshold or a feature toggle, and a feature flag service does that job better.

### Q207. Spring Cloud Gateway

Routes are matched by **predicates** (path, host, method, header, query, weight, time) and modified by **filters** (rewrite path, add or remove headers, circuit breaker, retry, rate limiter, token relay). Global filters apply to every route.

It is built on **WebFlux and Netty** because a gateway is the archetypal case for an event loop: thousands of concurrent connections doing almost no CPU work, just forwarding bytes. A thread-per-connection gateway would need an enormous thread count for the same concurrency.

Worth knowing on a modern baseline: `spring-cloud-gateway-server-mvc` provides a servlet-based gateway that works with virtual threads, for teams that want the routing model without the reactive stack. That is a reasonable choice now, though the reactive version remains the more mature and better-performing option at high connection counts.

### Q208. Blocking in a Gateway filter `[T]`

The gateway has a handful of event loop threads for the entire process. A blocking call in a filter - a JDBC lookup for an API key, a synchronous HTTP call to an authorization service, a blocking cache client - occupies one of them for the whole duration.

The symptom is distinctive and worth naming: **latency rises for every route, not just the one with the filter**, throughput collapses non-linearly under load, and the gateway appears to hang while CPU sits near idle. Because it affects unrelated traffic, it is usually misdiagnosed as a network or downstream problem, and the gateway is the last place anyone looks.

Correct approaches: return a `Mono` and use `WebClient` for any lookup; use a reactive Redis client for shared state; cache locally with Caffeine so the common path has no I/O; and if a blocking library is unavoidable, `publishOn(Schedulers.boundedElastic())` to move it off the loop - explicitly, as a bridge. Enforce it with BlockHound in the gateway's test suite (Q108), because this is exactly the codebase where one careless filter is catastrophic.

### Q209. Gateway rate limiting

```yaml
filters:
  - name: RequestRateLimiter
    args:
      redis-rate-limiter.replenishRate: 100      # sustained requests/second
      redis-rate-limiter.burstCapacity: 200      # bucket size - the burst allowance
      redis-rate-limiter.requestedTokens: 1
      key-resolver: "#{@principalKeyResolver}"
```

It is a token bucket implemented as an atomic Redis Lua script, so counting is correct across all gateway instances. `replenishRate` is the sustained rate, `burstCapacity` the bucket depth - setting them equal disallows bursts entirely, which is usually too strict for real clients.

The `KeyResolver` decides *what* is limited, and this is the important design choice:

```java
@Bean KeyResolver principalKeyResolver() {
    return exchange -> exchange.getPrincipal().map(Principal::getName)
        .defaultIfEmpty("anonymous");
}
```

Limiting by IP is a poor default because NAT and mobile carriers put thousands of users behind one address - you either block legitimate users or set the limit uselessly high. Limit by authenticated identity or API key where possible, and fall back to IP only for unauthenticated endpoints.

Also decide the Redis failure mode explicitly: fail-open preserves availability, fail-closed preserves protection, and the gateway defaults to denying when it cannot reach Redis.

### Q210. Resilience4j aspect ordering

Spring Boot's Resilience4j integration applies aspects in a defined order, outermost first: **Retry → CircuitBreaker → RateLimiter → TimeLimiter → Bulkhead → your method**. It is configurable per aspect (`resilience4j.retry.retryAspectOrder` and equivalents).

That default order is correct, and being able to justify it matters more than reciting it:

- **Retry outermost** so each attempt is observed by the circuit breaker and each gets a fresh timeout. If retry were innermost, three retries would happen inside one timeout and the breaker would see one long failure instead of three.
- **Circuit breaker above the rate limiter** so an open circuit fails immediately without consuming a permit.
- **TimeLimiter inside** so each individual attempt is bounded.
- **Bulkhead closest to the call** so it limits actual concurrent invocations.

The failure I look for is retry configured *inside* a transaction (Q49) or a retry with no jitter, both of which turn a downstream blip into a synchronized retry storm. And always define the fallback: `@CircuitBreaker(name = "inventory", fallbackMethod = "cachedInventory")` - a breaker without a fallback just converts a slow failure into a fast one, which helps you but not the user.

### Q211. OpenFeign

```java
@FeignClient(name = "inventory", configuration = InventoryConfig.class)
interface InventoryClient {
    @GetMapping("/items/{sku}") Item byId(@PathVariable String sku);
}
```

It generates the HTTP client from the interface, integrating with Spring Cloud LoadBalancer for service discovery, Resilience4j for circuit breaking, and Micrometer for tracing and metrics.

Things to configure that are not defaults: an `ErrorDecoder` mapping status codes to domain exceptions (the default throws a generic `FeignException` that loses the response body); explicit connect and read timeouts; a `RequestInterceptor` for token propagation; and a real HTTP client implementation (Apache HttpClient 5 or OkHttp) with a bounded connection pool, since the default `HttpURLConnection` has no pooling.

Worth stating: Spring's own `@HttpExchange` interfaces (Q97) now cover most of what Feign provided, without an extra dependency, and are the better choice for new code. Feign remains sensible in an estate already standardized on it.

### Q212. Feign inside a transaction `[T]`

This is Q76 with a specific mechanism. The database connection is held for the whole HTTP call, so response time of the remote service directly consumes connection pool capacity: a 200ms call with a pool of 15 caps you at 75 requests per second on that path, and when the remote service degrades to 5 seconds you hold every connection and the *entire application* fails - including endpoints that never call inventory.

Feign makes it worse than a raw client in two ways: the call site looks like a local method invocation, so it does not read like I/O; and its default timeouts are generous (or, with some configurations, effectively unbounded), so a hung downstream holds the connection indefinitely.

The fix is structural: move the call outside the transaction, or persist an intent and perform the call asynchronously. Then the defensive layers - explicit Feign timeouts shorter than any transaction timeout, a circuit breaker, `LazyConnectionDataSourceProxy` as a net, and the ArchUnit rule from Q80.

### Q213. Spring Cloud LoadBalancer

It replaced Netflix Ribbon, which is end-of-life. A `ServiceInstanceListSupplier` provides instances from the discovery client, and a `ReactorLoadBalancer` selects one - round-robin by default, with random available.

The useful capabilities are in the supplier decorators, and they are opt-in: health-check filtering (`health-check` supplier, which pings instances rather than trusting the registry), zone preference (`zone-preference`, which keeps traffic in-AZ and cuts both latency and cross-AZ data transfer cost), instance caching (on by default, so registry lookups are not per-request), and retry on a different instance.

On Kubernetes I would generally not use it: the Service abstraction already load balances, and adding client-side balancing means two mechanisms to reason about. It earns its place outside Kubernetes, or when you specifically need zone affinity or client-side health checks that the platform does not provide.

### Q214. Spring Cloud Stream

It abstracts messaging behind the functional model - a `Supplier`, `Function` or `Consumer` bean is bound to a destination by a **binder** (Kafka, RabbitMQ, Kinesis, SQS):

```java
@Bean Consumer<OrderEvent> processOrder() { return event -> service.handle(event); }
```

```yaml
spring.cloud.stream.bindings.processOrder-in-0:
  destination: orders
  group: order-processor
  consumer.max-attempts: 3
```

Error handling: retries happen in-process by default, then the message goes to a DLQ if enabled (`spring.cloud.stream.kafka.bindings.*.consumer.enableDlq`). You can also subscribe to the per-binding error channel for custom handling.

The trade-off is honest to state: the abstraction buys you binder portability and less boilerplate, but it hides broker semantics that you eventually need - partition assignment, offset management, exactly-once configuration, consumer lag. Teams that adopt Stream to avoid learning Kafka find themselves debugging Kafka through an abstraction layer. I use it where messaging is simple and uniform, and the native `spring-kafka` API where the broker's semantics matter.

### Q215. Spring for Apache Kafka

```java
@KafkaListener(topics = "orders", groupId = "order-processor", concurrency = "3")
public void handle(ConsumerRecord<String, OrderEvent> record, Acknowledgment ack) { ... }
```

- **`concurrency`** creates that many consumer threads in the container, capped usefully by the partition count (`01-java` Q175) - more consumers than partitions leaves some idle.
- **Acknowledgment modes**: `BATCH` (default), `RECORD`, or `MANUAL`/`MANUAL_IMMEDIATE` with an injected `Acknowledgment`. I disable auto-commit and acknowledge after successful processing, accepting at-least-once.
- **`DefaultErrorHandler`** with a `FixedBackOff` or `ExponentialBackOff` retries in-process, then invokes a recoverer - typically `DeadLetterPublishingRecoverer` sending to `<topic>.DLT`. Classify exceptions with `addNotRetryableExceptions` so a deserialization or validation failure goes straight to the DLT instead of retrying 10 times.
- **Non-blocking retries** (`@RetryableTopic`) move retries to separate delay topics, so a slow-to-succeed message does not block its partition - important, because in-process retry with backoff stalls every subsequent message in that partition.
- **`ErrorHandlingDeserializer`** wraps your deserializer so a poison message becomes a handled failure rather than an infinite consumer crash loop, which is otherwise a genuinely painful outage.

### Q216. `@KafkaListener` with `@Transactional` `[T]`

The annotation opens a **database** transaction. It does not make the Kafka consumption transactional, and it certainly does not make the two atomic.

What actually happens: the message is consumed, the database transaction commits, and then the offset is committed separately. If the process dies between them, the message is redelivered and the database work happens twice. If you commit the offset first and the database fails, the message is lost.

Options:

- **Kafka transactions** (`KafkaTransactionManager`, `spring.kafka.producer.transaction-id-prefix`) give exactly-once *within Kafka* for consume-process-produce, atomically committing produced records and consumer offsets. They do **not** extend to your database.
- **`ChainedKafkaTransactionManager`** was the old attempt to span both and is deprecated for the same reason as Q67 - it is best-effort, not atomic.
- **The correct answer**: accept at-least-once delivery and make the handler **idempotent** - an inbox table recording processed message IDs in the *same* database transaction as the effect, so a redelivery is a no-op. Order the operations so the database commit happens before the offset commit, making duplicates the failure mode rather than loss.

Stating "exactly-once across Kafka and a database is not achievable; I design for idempotency instead" is the answer being looked for.

### Q217. Scheduling in a cluster

`@Scheduled` runs on **every instance**, so a nightly job on six pods runs six times. Options:

- **ShedLock** - a lock row in a database or Redis, acquired for the duration with a minimum and maximum hold time. Minimal infrastructure, works with the existing `@Scheduled` annotation (`@SchedulerLock(name = "...", lockAtMostFor = "10m")`), and is my default. `lockAtMostFor` must exceed the worst-case runtime, or a second instance starts while the first is still running.
- **A database advisory lock** - the same idea implemented directly; fine, but you end up writing ShedLock.
- **Leader election** (Spring Integration's `LeaderInitiator`, or Kubernetes leases) - one instance is leader and runs all scheduled work. Better when there are many jobs and you want them co-located, but adds a leadership protocol to reason about.
- **An external scheduler** - a Kubernetes `CronJob`, EventBridge Scheduler, or a workflow engine, invoking an endpoint or running a separate task. This is what I prefer for anything important, because the schedule becomes visible infrastructure with its own observability, retries and alerting, rather than being hidden inside an application.

Whatever the mechanism, the job must be **idempotent** - locks fail, leaders change, and schedulers retry.

### Q218. Spring Cloud AWS

Configuration import gives you Parameter Store and Secrets Manager as first-class property sources (Q29), resolved before the context starts and participating in normal precedence.

SQS listening is annotation-driven:

```java
@SqsListener(value = "orders-queue", maxConcurrentMessages = "10")
public void handle(OrderMessage message, Acknowledgement ack) { ... }
```

with acknowledgement modes (`ON_SUCCESS` by default), batch listeners, and visibility-timeout extension for long-running work - which is the setting people forget, causing the message to be redelivered while still being processed (`01-java` Q185).

It also provides S3 (including a `Resource` implementation so `s3://bucket/key` works with `ResourceLoader`), SNS, DynamoDB and CloudWatch metric export. Credentials come from the default provider chain, so IRSA or the ECS task role works with no configuration - which is the point.

The thing to verify per project: Spring Cloud AWS 3.x is a substantial rewrite on AWS SDK v2 with a different group ID and different property names, so the migration from 2.x is not a version bump.

### Q219. Spring Cloud Contract

The **producer** defines contracts (Groovy, YAML or Java DSL) describing request and response pairs. The build generates tests that run against the real producer, so the contract is verified to match the implementation, and publishes a **stub JAR** to the artifact repository. The **consumer** uses `@AutoConfigureStubRunner` to run against those stubs instead of a mock it wrote itself.

The value is that it closes the gap that unit tests with hand-written mocks leave open: your mock says the API returns `orderId`, the API actually returns `id`, both test suites are green, and integration fails. With contracts, the stub the consumer uses is generated from a contract the producer's tests prove.

Where it fits: at service boundaries, replacing the need for a full end-to-end environment for API compatibility. It does not replace integration tests for your own database and messaging, and it is not free - contracts must be maintained, and the workflow (consumer-driven or producer-driven) needs an agreed process or teams argue about who owns the contract.

I would introduce it where two teams integrate and breakages are recurring, not across every service by default.

### Q220. What not to adopt on Kubernetes `[A]`

The general principle: do not run a second implementation of something the platform already provides, because you then own two systems that can disagree.

- **Eureka / service discovery** - Kubernetes Services and DNS do this, with the platform's own health awareness. Running Eureka adds a registry to operate and a second source of truth about instance health.
- **Spring Cloud Config Server** - ConfigMaps, Secrets and Parameter Store cover it (Q205), without a hard startup dependency on a service you must keep as available as everything else.
- **Client-side load balancing** - the Service handles it; add it only for zone affinity or client health checks the platform lacks (Q213).
- **Spring Cloud Bus** - a message broker for configuration refresh is a lot of machinery for something a rolling restart does more safely.
- **Hystrix** - end-of-life; use Resilience4j.

What I **would** adopt: Resilience4j (application-level concerns the platform cannot see), Spring Cloud Stream or `spring-kafka` (messaging is genuinely application logic), Spring Cloud Gateway if I need application-aware routing beyond an ingress, Spring Cloud AWS for cloud service integration, and Contract for boundary testing.

The nuance I would add: if you also run outside Kubernetes, or need portability across environments, the calculus changes - and a service mesh overlaps with several of these too, so the honest answer is to pick one layer for each concern and be consistent about it.

---

## 12. Testing Spring applications

### Q221. The context cache key

`MergedContextConfiguration` is the key, comprising: the configuration classes and locations, the active profiles, the property sources (`@TestPropertySource`, inline properties), the context initializers, the `ContextCustomizer`s (which is where `@MockBean`, `@DynamicPropertySource` and web environment settings contribute), the parent context, and the `ContextLoader`.

Any difference produces a **new context**, each costing full startup time and heap. A suite with 40 distinct combinations starts 40 applications, which is where the "why does our build take 25 minutes" answer lives.

Keeping the count low: define a small number of standard test configurations and reuse them; put shared mocks in one `@TestConfiguration` imported everywhere rather than per-class `@MockBean` combinations; avoid per-class inline properties; and use `@DirtiesContext` almost never - it evicts the context and forces a rebuild for everything after it.

Measure it: enable `logging.level.org.springframework.test.context.cache=DEBUG` and the framework logs cache size, hit and miss counts. That number is the metric to drive down.

### Q222. Silent context creation `[T]`

The ones that create a new cache key, often unintentionally:

- `@MockBean` / `@SpyBean` - **each distinct set** of mocked types is a different key. Two test classes mocking different services get two contexts.
- `@TestPropertySource` and `@SpringBootTest(properties = ...)` - any difference in inline properties.
- `@ActiveProfiles` - different profile sets.
- `@DynamicPropertySource` - contributes a customizer.
- `webEnvironment` - `MOCK`, `RANDOM_PORT` and `DEFINED_PORT` are all distinct.
- `@ContextConfiguration` with different classes, and different slice annotations.
- `@DirtiesContext` - evicts, so the next test rebuilds.

Finding out how many you create: the cache logging above, or a `TestExecutionListener` that counts contexts. I have also had success simply sorting the build log by context startup lines - it is usually obvious which annotation combination is duplicated across dozens of classes.

The practical fix that gives the biggest win is consolidating `@MockBean` usage, because it is the most common and least obvious contributor.

### Q223. Slice tests

| Slice | Loads | Notably excludes |
| --- | --- | --- |
| `@WebMvcTest` | Controllers, advice, filters, converters, security | Services, repositories, `@Configuration` classes |
| `@DataJpaTest` | Entities, repositories, embedded/configured DB, transactional + rollback | Web layer, services |
| `@JdbcTest` / `@DataJdbcTest` | `JdbcTemplate`, `DataSource` | JPA |
| `@JsonTest` | Jackson configuration, `JacksonTester` | Everything else |
| `@RestClientTest` | `RestTemplateBuilder`/`RestClient` plus `MockRestServiceServer` | Web layer |
| `@DataRedisTest`, `@DataMongoTest` | The relevant data module | Others |
| `@WebFluxTest` | Reactive web layer, `WebTestClient` | Services, repositories |

The critical property is that each slice **excludes your `@Configuration` classes**, so anything you configured yourself - security rules, custom converters, message converters, argument resolvers - is absent unless explicitly `@Import`ed. That is what makes slices fast and what makes them lie if you do not know it (Q164, Q230).

### Q224. `@TestConfiguration` versus `@Configuration`

A static nested `@Configuration` class inside a test **replaces** the application's configuration for that test. A `@TestConfiguration` is **additive** - it supplements the primary configuration rather than replacing it, and it is not picked up by component scanning of the main application, so it cannot accidentally leak into production wiring.

`@TestConfiguration` is what you want in almost every case: overriding one bean with a stub, adding a fixed `Clock`, or registering a test-only `RestClient` pointed at a mock server. Combine with `@Import(MyTestConfig.class)` to apply it to specific test classes, which also keeps the context cache key stable if you import the same configuration everywhere.

### Q225. `@MockBean`, `@MockitoBean` and plain Mockito

`@MockBean` (Boot) replaced a bean in the context with a Mockito mock; **`@MockitoBean` (Spring Framework 6.2)** is the successor, moving the capability into the core framework, and `@MockBean` is deprecated from Boot 3.4. Both behave the same way for the context cache (Q222).

Plain Mockito with constructor injection needs no context at all:

```java
var service = new OrderService(mockRepository, mockGateway);
```

This runs in milliseconds, has no cache implications, and is what the vast majority of tests should use. It is also an argument for constructor injection (`01-java` Q111).

My guidance: default to plain Mockito unit tests; use `@MockitoBean` only when you genuinely need the Spring context *and* must stub a collaborator - typically in a `@WebMvcTest` where the controller's service dependency must exist. And group those stubs so the cache key repeats.

### Q226. Test property mechanisms

- **`@TestPropertySource(properties = ...)`** - static values known at compile time. Highest precedence among test property sources.
- **`@DynamicPropertySource`** - a static method registering values computed at runtime, evaluated **before** the context starts. This is what makes Testcontainers work, because the port is only known after the container starts:

```java
@DynamicPropertySource
static void props(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", postgres::getJdbcUrl);
}
```

Values are `Supplier`s, so they are resolved lazily at the right moment.

- **`ApplicationContextInitializer`** - the most flexible, adding a whole `PropertySource` programmatically; used when you need conditional logic or many values.

Since Boot 3.1, `@ServiceConnection` (Q227) removes most `@DynamicPropertySource` usage for supported containers.

### Q227. Testcontainers with `@ServiceConnection`

```java
@SpringBootTest
@Testcontainers
class OrderIntegrationTest {
    @Container @ServiceConnection
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16");
}
```

`@ServiceConnection` (Boot 3.1) derives *all* the connection properties from the container - URL, username, password, driver - via a `ConnectionDetails` bean, replacing the `@DynamicPropertySource` block entirely. Supported for Postgres, MySQL, Redis, Kafka, MongoDB, RabbitMQ, Elasticsearch, LocalStack and more.

`static` containers are started once per class and shared; **reuse** (`.withReuse(true)` plus `testcontainers.reuse.enable=true` in `~/.testcontainers.properties`) keeps them running between *runs*, which transforms the local development loop - the container starts once a day rather than once a build.

Boot 3.1 also added `@TestConfiguration` container beans plus `SpringApplication.from(...).with(TestContainersConfig.class)` so you can **run the application locally** against the same containers, which removes a whole class of "works in tests, not locally" friction.

### Q228. What `@Transactional` tests hide `[T]`

A `@Transactional` test rolls back at the end and, crucially, runs the test method and the application code in **one transaction on one thread**. That hides:

- **Commit-time failures** - deferred constraints, database triggers, and anything that only fires on commit. The test never commits.
- **Flush-timing bugs** - the test and the code share a persistence context, so an entity you saved is visible without a flush; in production, with separate transactions, it may not be.
- **`LazyInitializationException`** - the session stays open for the whole test, so lazy loading always works. Production closes it at the transaction boundary and throws.
- **Isolation and locking behavior** - there is only one transaction, so you cannot observe concurrent access, deadlocks or optimistic lock failures.
- **Auto-generated values and identity semantics** that differ between `persist` and `merge` paths.
- **`@TransactionalEventListener(AFTER_COMMIT)`** - never fires, so the entire asynchronous half of your logic is untested (Q19).

So `@Transactional` tests are fine for repository-level query verification. Anything asserting behavior across a transaction boundary needs a **non-transactional** test with explicit cleanup - `@Transactional(propagation = NOT_SUPPORTED)` or a truncate between tests - and that is where the real bugs are found.

### Q229. The four web test styles

- **`MockMvc`** - no server, no network; the `DispatcherServlet` is invoked directly with a mock request. Fastest, and the right default for controller logic.
- **`WebTestClient`** - fluent and reactive; works both against a mock server (`@WebFluxTest`, or bound to `MockMvc`) and a real port. Better assertions than `MockMvc` even for servlet applications.
- **`TestRestTemplate`** - a real HTTP client against a real port; blocking, with error handling suited to testing (it does not throw on 4xx/5xx).
- **`@SpringBootTest(webEnvironment = RANDOM_PORT)`** - starts the real embedded server, so the full stack including the actual servlet container, filters and serialization is exercised.

My layering: `MockMvc` or `WebTestClient` on a slice for controller behavior, and a small number of `RANDOM_PORT` tests for the paths where the real stack matters - authentication, content negotiation, error handling, and anything that has broken in production before.

### Q230. What `MockMvc` cannot catch `[T]`

Because there is no server and no network:

- **Servlet container behavior** - actual request parsing, URL decoding, header size limits, chunked encoding, HTTP/2 specifics.
- **Filters not registered in the test** - `MockMvc` only applies filters you add (or, with `@AutoConfigureMockMvc`, the Spring Security chain); container-registered filters and their ordering are not exercised.
- **Real serialization over the wire** - `MockMvc` uses the configured converters, but connection-level issues, compression, and streaming behavior are invisible.
- **Async completion semantics** - `asyncDispatch` must be invoked manually, so a bug in the async lifecycle is easy to miss.
- **Anything configuration-dependent that the slice omitted** (Q164) - security rules, custom converters, error handling.
- **Response buffering and SSE** behavior, which depend on the real container.

The mitigation is not to abandon `MockMvc` - it is fast and appropriate - but to have a thin layer of real-port tests covering exactly these areas, and to know which category a given bug would fall into when deciding where to test.

### Q231. Testing async and scheduled behavior

Never `Thread.sleep`. Use **Awaitility**:

```java
await().atMost(5, SECONDS).untilAsserted(() ->
    verify(notificationService).send(argThat(n -> n.orderId().equals(id))));
```

It polls until the assertion passes or the timeout expires, so the test is fast when things work and gives a clear failure when they do not.

For **scheduled** methods, do not wait for the schedule at all: extract the work into a method and test that directly, and separately assert the cron expression with a unit test on `CronExpression.parse(...).next(...)`. Testing that Spring's scheduler works is testing the framework.

For `@Async`, either use Awaitility as above, or in tests replace the executor with a synchronous one so behavior is deterministic:

```java
@TestConfiguration
static class SyncExecutorConfig {
    @Bean TaskExecutor applicationTaskExecutor() { return new SyncTaskExecutor(); }
}
```

Also inject a fixed `Clock` everywhere rather than using `Instant.now()`, so time-dependent logic is deterministic - that single practice eliminates a large share of flaky tests.

### Q232. Testing message consumers

- **Testcontainers with a real broker** - highest fidelity, and my default for the consumer's own integration test. It exercises real serialization, partitioning, offset commits and error handling. Slower, but with container reuse the cost is acceptable.
- **`@EmbeddedKafka`** - an in-JVM broker, faster to start than a container but less faithful (different version, different configuration surface) and historically a source of flakiness. I now prefer Testcontainers.
- **Contract tests** (Q219) - verify the *message schema* between producer and consumer without either running the other. This is the right tool for compatibility, not for behavior.
- **Unit tests on the handler** - the listener method should delegate to a plain service, and that service gets ordinary unit tests. Most of the logic should be testable this way.

The layering I recommend: handler logic in unit tests, one Testcontainers test per consumer covering deserialization, retry and DLQ behavior (the parts that only break in integration), and contract tests at the team boundary.

### Q233. ArchUnit

```java
@ArchTest static final ArchRule domainIsFrameworkFree =
    noClasses().that().resideInAPackage("..domain..")
        .should().dependOnClassesThat().resideInAnyPackage("org.springframework..");

@ArchTest static final ArchRule noHttpInTransaction =
    noMethods().that().areAnnotatedWith(Transactional.class)
        .should().callMethodWhere(target(owner(assignableTo(RestClient.class))));
```

Rules I put in place on most Spring codebases: layering (controllers must not touch repositories directly), the domain package must not depend on Spring or JPA (Q249), no field injection, no `@Transactional` on private or non-public methods (Q50), no HTTP calls inside transactions (Q80), no `System.out`, and naming conventions.

The value is that it enforces the decisions that code review keeps re-litigating, with a message explaining *why*. Introduce rules in report-only mode against an existing codebase, fix, then enforce - a build-breaking rule with 200 pre-existing violations gets disabled rather than obeyed (Q80).

### Q234. Spring-specific flakiness

Causes I look for, roughly in order of frequency:

- **Shared mutable state across tests** - a singleton bean holding state, a static cache, a `@MockBean` whose stubbing leaks because reset behavior was assumed. Contexts are cached and *shared*, so a test that mutates a bean affects later tests in a non-deterministic order.
- **Test ordering dependence** - tests passing individually and failing in a suite. Random ordering in CI surfaces this deliberately.
- **Time** - `Instant.now()`, timezone differences between the developer machine and CI, and daylight-saving boundaries. Inject a `Clock`.
- **Async without Awaitility** - a sleep that is long enough locally and not on a loaded CI agent.
- **Random ports and container startup races**, and tests assuming a container is ready when the port is open.
- **Database state** - tests relying on data from another test, or an identity sequence that is not reset.
- **`@DirtiesContext` interacting with parallel execution**.

The systemic fixes: randomize order, run tests in parallel deliberately to expose shared state, ban `Thread.sleep` with a lint rule, inject `Clock`, and treat a flaky test as a build-blocking defect rather than something to re-run. A quarantine with an expiry date works better than a permanent `@Disabled`.

### Q235. From 25 minutes to under ten `[D]`

Measure first - which tests, and where the time goes between context startup and test execution.

1. **Count the contexts** (Q221). This is usually the single largest win: consolidating `@MockBean` combinations and standardizing on a few configurations can remove tens of context startups.
2. **Move tests down the pyramid.** Most `@SpringBootTest` classes are testing logic that needs no context. Converting them to plain Mockito tests turns seconds into milliseconds each.
3. **Container reuse and shared containers** (Q227) - a static container per class, or a singleton container pattern shared across the whole suite, rather than one per class.
4. **Parallel execution** - JUnit 5 `junit.jupiter.execution.parallel.enabled`, which requires the isolation work from Q234 and is therefore also a quality improvement.
5. **Remove `@DirtiesContext`** wherever the underlying state issue can be fixed properly.
6. **Split the suite** - fast tests on every commit, slower integration tests on merge, so developer feedback is minutes even if total runtime is not.
7. **Build-level wins** - Gradle build cache and test result caching so unchanged modules do not re-run.

And a point worth making: a 25-minute suite changes team behavior - people batch changes and stop running tests locally - so this is a delivery problem, not just a cost one.

### Q236. Test strategy for a new service `[A]`

What I would mandate, with the reasoning attached because a strategy nobody believes in is not followed:

- **A pyramid, weighted heavily to unit tests** on domain logic with no Spring context. Constructor injection makes this possible, which is why it is a standard.
- **Slice tests** for the web and persistence layers, with explicit `@Import` of the real configuration so they test what production runs (Q164).
- **A small number of integration tests** with Testcontainers covering the paths that only break in integration: transactions across a boundary, serialization, security, messaging retry and DLQ.
- **Contract tests** at every team boundary (Q219).
- **ArchUnit rules** encoding the architectural decisions (Q233).
- **No `@Transactional` on tests asserting cross-boundary behavior** (Q228).
- **An injected `Clock`, Awaitility instead of sleeps, and randomized test order** as non-negotiables.
- **A target on the fast suite** - under five minutes for the commit stage, treated as a real requirement with a named owner.

What I would deliberately *not* mandate: a coverage percentage. It produces assertion-free tests and measures the wrong thing. I would measure **change failure rate** and **mutation score** on core modules instead, and review test quality in code review the same way as production code.

---

## 13. Spring AI

### Q237. `ChatClient`

```java
String answer = chatClient.prompt()
    .system("You are a support assistant. Answer only from the provided context.")
    .user(u -> u.text("Summarize order {id}").param("id", orderId))
    .options(ChatOptions.builder().temperature(0.2).build())
    .call().content();
```

It is a fluent facade over the provider-specific `ChatModel`, with `call()` for blocking and `stream()` for a `Flux<String>`. Default system prompts and advisors can be set on the builder so every call in a service shares them.

**Where prompts should live** is the more interesting half of the question. Not inline string literals scattered through services: prompts are business logic that changes independently of code, needs review, versioning and evaluation. I keep them as versioned resources (`PromptTemplate` loaded from `classpath:/prompts/order-summary.st`), reference the version in telemetry so a quality change can be attributed to a prompt change, and run them through the evaluation suite in CI (Q245).

### Q238. Advisors

Advisors are the interceptor chain for a chat call - the same idea as a `HandlerInterceptor` or a servlet filter, applied to prompts and responses. They let you inject retrieved context, manage memory, log, or post-process without every call site repeating the logic.

Built-in ones worth naming: `QuestionAnswerAdvisor` (RAG - retrieves from a `VectorStore` and injects into the prompt), `MessageChatMemoryAdvisor` and `PromptChatMemoryAdvisor` (conversation history), `SimpleLoggerAdvisor`, and `SafeGuardAdvisor` for basic content filtering.

Custom advisors are where the production concerns go: PII redaction before the call and after the response, token budget enforcement, tenant-scoped retrieval filters, cost attribution, and caching. That is the right layer for them - centralized, testable, and applied consistently rather than depending on each developer remembering.

### Q239. Structured output

```java
record OrderSummary(String status, BigDecimal total, List<String> issues) {}

OrderSummary summary = chatClient.prompt()
    .user("Summarize this order: " + json)
    .call().entity(OrderSummary.class);
```

`entity()` uses a `StructuredOutputConverter` that generates a JSON schema from the target type, appends format instructions to the prompt, and parses the response. With providers supporting native structured output or tool calling, the schema is enforced by the model rather than requested in prose, which is considerably more reliable.

**When the model returns invalid JSON**, the converter throws a parse exception. The defensive design that matters:

- Prefer providers and modes with **native** JSON schema enforcement over prompt-based instructions.
- **Retry once** with the parse error fed back, which recovers most cases.
- **Validate the parsed object** with JSR-303 - schema-valid does not mean semantically valid, and a hallucinated enum value or a negative total will parse fine.
- **Have a defined fallback** - degrade to unstructured text, or fail the feature cleanly, rather than propagating a partially-parsed object.

Treat the model as an untrusted input source, because that is exactly what it is.

### Q240. Tool calling

```java
@Bean
@Description("Look up the current status of an order by its ID")
Function<OrderRequest, OrderStatus> orderStatus(OrderService service) {
    return req -> service.status(req.orderId());
}
```

or `@Tool`-annotated methods registered with `.tools(myToolBean)`. Spring AI generates the JSON schema from the types, sends the tool definitions with the prompt, and when the model requests a call, executes it and feeds the result back for the next turn.

**The security boundary is the critical part**, and it is the whole of Q215 in the Java pack made concrete. The model decides which tool to call and with what arguments, and that decision can be influenced by injected content in a retrieved document. Therefore:

- Tools run with the **application's** authority, not the model's judgement - authorize every tool invocation against the *end user's* permissions, exactly as you would an API call.
- Validate arguments as untrusted input; never interpolate them into SQL, shell commands or URLs.
- Scope tools narrowly and read-only by default; anything irreversible or high-value requires explicit human confirmation.
- Bound the number of tool-calling turns, or a loop will happily consume your budget.
- Audit every invocation with arguments and results.

A tool that takes a raw query string and executes it is the AI-era equivalent of SQL injection.

### Q241. Vector stores and ingestion

`VectorStore` abstracts pgvector, Redis, OpenSearch, Qdrant, Pinecone, Chroma and others behind `add(List<Document>)` and `similaritySearch(SearchRequest)`. The ETL pipeline is `DocumentReader` (PDF, HTML, JSON, Tika) → `DocumentTransformer` (`TokenTextSplitter`, metadata enrichers) → `DocumentWriter`.

**Metadata filters** are the feature that matters most in production:

```java
vectorStore.similaritySearch(SearchRequest.query(question)
    .withTopK(5).withSimilarityThreshold(0.7)
    .withFilterExpression("tenant == '" + tenantId + "' && status == 'published'"));
```

That filter is a **security control** in a multi-tenant system, not a relevance tweak - it must be applied as a pre-filter derived from the authenticated principal, never from user input, and never applied after retrieval (`01-java` Q212). I would test it the same way I test tenant isolation in the database: authenticate as tenant A and assert nothing from tenant B is ever retrievable.

Also store the **embedding model version** with each vector, so a model change is detectable and triggers a controlled re-index rather than a silently mixed index.

### Q242. `QuestionAnswerAdvisor` and RAG

```java
chatClient.prompt().user(question)
    .advisors(new QuestionAnswerAdvisor(vectorStore, SearchRequest.defaults().withTopK(5)))
    .call().content();
```

It embeds the question, searches the store, injects the results into the prompt with a default template, and returns the retrieved documents in the response context for citation.

What it gives you is the *plumbing*. What you still have to build is everything that determines quality (`01-java` Q212):

- **Hybrid retrieval** - lexical plus vector with rank fusion. Pure vector search fails on exact terms, codes and negation.
- **Reranking** with a cross-encoder over the fused candidates, usually the largest single quality gain.
- **Chunking strategy** tuned to your corpus, with structure awareness and metadata.
- **Grounding enforcement** - requiring citations and verifying they resolve, rather than trusting the model not to blend in its own priors.
- **Tenant and ACL filtering** at query time.
- **Evaluation** (Q245) - without measured retrieval hit rate and faithfulness, every change is a guess.

So the honest framing: the advisor is 10 percent of a production RAG system, and the remaining 90 percent is retrieval quality, safety and measurement.

### Q243. Chat memory

Spring AI provides `ChatMemory` implementations - in-memory, JDBC, Cassandra, Neo4j - wired through `MessageChatMemoryAdvisor` (sends prior messages) or `PromptChatMemoryAdvisor` (summarizes into the system prompt), with `MessageWindowChatMemory` bounding by message count.

Unbounded history is a **cost defect** with a compounding shape, and being able to explain that is the point: every turn resends the entire conversation, so token usage grows quadratically with conversation length. A 50-turn conversation does not cost 50 units, it costs roughly 1,275. It also eventually exceeds the context window and fails outright, and long contexts degrade answer quality as relevant detail is diluted.

Controls: a hard window (last N turns), summarization of older turns into a compact form, a per-conversation token budget with a defined behavior when exceeded, provider-side prompt caching for the stable prefix, and a retention policy - conversation history is user data with privacy and deletion obligations, and storing it forever is both a cost and a compliance decision.

### Q244. Observability and cost

Spring AI integrates with Micrometer Observations, producing spans and metrics for model calls, embeddings, vector store operations and tool invocations, including token counts.

What I record on every call: prompt tokens, completion tokens, total cost derived from the model's pricing, latency and time-to-first-token for streaming, model name and version, prompt version, tenant, feature, and outcome including whether a retry or fallback occurred.

Then the dimensions matter more than the totals - cost must be attributable **per feature and per tenant**, or you cannot answer "which feature is expensive" or "is this customer profitable", and those are the questions that arrive within a month of launch. I put it on a dashboard the team sees weekly and set a budget alert per feature, because AI cost grows quietly with usage rather than announcing itself.

Also: sample prompts and responses into a store for evaluation and debugging, with PII handling applied, since you cannot improve what you cannot inspect - but sample rather than log everything, because prompts and responses are both large and sensitive.

### Q245. Testing and evaluating `[T]`

Deterministic assertions are unit tests; quality is an evaluation suite. Both are needed.

**In the test suite** (deterministic, runs in CI): mock the `ChatModel` and assert your own logic - that the prompt was assembled correctly, that retrieval filters included the tenant, that a malformed response is handled, that the token budget is enforced, that tool arguments are validated. Most of the code around the model is ordinary logic and should be tested as such.

**In the evaluation suite** (non-deterministic, also runs in CI on prompt or model changes):

- A **golden dataset** of realistic cases, grown from real failures.
- **Deterministic checks first** - schema validity, citations resolving to real chunks, no PII in output, cost and latency within bounds, correct refusal on out-of-scope input. A surprising share of regressions are caught here.
- **Component metrics** - retrieval recall@k separately from answer faithfulness and relevance, because isolating them is what makes failures diagnosable.
- **LLM-as-judge** with a rubric, a stronger judge model, pairwise comparison rather than absolute scoring, and periodic calibration against human labels.
- **Thresholds as release criteria**, reported with a confidence interval rather than a single number.

Spring AI provides `RelevancyEvaluator` and `FactCheckingEvaluator` as starting points. The discipline that matters is treating prompts as versioned code and re-running evaluation on every prompt, model or retrieval change - including when the provider silently updates a model, which is why model versions should be pinned.

### Q246. Spring AI or the raw SDK `[A]`

I would use Spring AI, but keep it behind my own domain interface.

What it genuinely gives me: a provider-agnostic client so switching or A/B-testing models is a configuration change; structured output binding to Java types; tool calling with schema generation; the document ETL and `VectorStore` abstraction; and - the underrated one - native integration with Boot's auto-configuration, Micrometer observability and testing support, which is otherwise a meaningful amount of plumbing per project.

What I would still own: prompt management and versioning, the evaluation harness, cost attribution and budget enforcement, retrieval strategy including hybrid search and reranking, guardrails and tenant isolation. Those determine product quality and are not commodity infrastructure.

The reason for the wrapper interface is that Spring AI is young and its abstractions are still settling - the advisor and memory APIs have changed across recent versions. Letting its types spread through the codebase means a library upgrade becomes a refactor of every service. A thin `AnswerGenerator` interface in the domain, implemented in the infrastructure layer, costs almost nothing and contains that risk - the same discipline I would apply to any fast-moving dependency.

I would not write directly against a provider SDK, because that guarantees a rewrite the first time you change or add a model provider, which in this space is a matter of months.

---

## 14. Architecture, modularity and migration

### Q247. Spring Modulith

Modulith treats each top-level package under the application root as a **module**, with its direct package being the public API and sub-packages internal by default. It verifies at build time:

```java
@Test void verifyModularity() {
    ApplicationModules.of(Application.class).verify();
}
```

This fails if a module reaches into another module's internal package, if there are cyclic dependencies between modules, or if a module accesses an undeclared dependency. `@ApplicationModule(allowedDependencies = "order")` makes the permitted edges explicit.

It also generates documentation - PlantUML component diagrams and module canvases - from the code, which is the only architecture documentation that stays current. And `@ApplicationModuleTest` bootstraps a single module in isolation, which is a genuinely useful middle tier between unit and full integration tests.

The value over ArchUnit is that the rules are derived from package structure rather than written out, so they are harder to get wrong and cheaper to adopt.

### Q248. Modulith events and the outbox

Modules communicate through application events rather than direct calls, which is what keeps the dependency graph acyclic. The problem is that a plain in-memory event is lost if the process dies after commit (Q79).

The **event publication registry** solves this: Modulith persists an `event_publication` row for each `@ApplicationModuleListener` in the *same transaction* as the business change, and marks it complete when the listener succeeds. Incomplete publications are republished on restart (`spring.modulith.republish-outstanding-events-on-restart`), and are queryable and resubmittable at runtime.

So it is an **outbox for in-process events**, giving at-least-once delivery within the application - which means listeners must still be idempotent. `@ApplicationModuleListener` is a composed annotation combining `@Async`, `@Transactional(propagation = REQUIRES_NEW)` and `@TransactionalEventListener(AFTER_COMMIT)`, which is exactly the correct combination from Q19 and Q62 packaged so people stop getting it wrong.

The strategic point: this makes a modular monolith's internal communication semantically similar to messaging, so extracting a module into a service later means changing the transport rather than the design (Q259).

### Q249. Hexagonal with Spring

The domain package contains entities, value objects, domain services and **port interfaces**, with no Spring, JPA or Jackson annotations. Adapters in the infrastructure layer implement the ports and carry all the framework annotations - `@Repository` on a JPA adapter, `@RestController` on a web adapter.

Keeping the domain clean in practice:

- **Separate persistence models from domain models**, with explicit mappers. This is the part teams resist because it is more code, and it is what actually delivers the independence - a shared entity annotated with both JPA and Jackson couples your database schema to your API contract permanently.
- **Enforce it with a test** (Q233) rather than a guideline: `noClasses().that().resideInAPackage("..domain..").should().dependOnClassesThat().resideInAnyPackage("org.springframework..", "jakarta.persistence..")`.
- Wire ports to adapters in an infrastructure `@Configuration` class, so the domain never sees the container.

The honest trade-off: this is worth it for a genuinely complex domain with long-lived business rules, and it is over-engineering for a CRUD service. I apply it to core domain modules and let peripheral modules be straightforward Spring applications - and I would say that explicitly rather than presenting it as universally correct.

### Q250. Multi-module layout

```
order-service/
  order-domain/           # pure Java: entities, value objects, ports. No Spring.
  order-application/      # use cases, orchestration, transaction boundaries
  order-infrastructure/   # JPA adapters, HTTP clients, messaging, config
  order-api/              # DTOs and contracts shared with clients (published)
  order-bootstrap/        # @SpringBootApplication, wiring, application.yml
```

The value is that the **build enforces the dependency direction** - `order-domain` has no Spring dependency on its classpath, so a violation is a compile error rather than an architecture test failure. That is stronger enforcement than any rule.

The costs are real and worth naming: more build configuration, slower IDE indexing, more friction for a small change, and a temptation to create modules that mirror layers rather than meaningful boundaries. For a small service, packages plus ArchUnit give most of the benefit at a fraction of the cost.

I would use this layout when the domain is complex, when the API module is genuinely published to other teams, or when I need to guarantee the domain stays framework-free over years.

### Q251. Boot 2 to Boot 3 checklist

In order:

1. **Get to Boot 2.7 and Java 17 first**, on the latest 2.7.x patch. Never do two migrations at once.
2. **Fix all deprecation warnings on 2.7** - most Boot 3 breakages are things 2.7 already warned about.
3. **Jakarta EE namespace** - `javax.*` to `jakarta.*` for persistence, servlet, validation, annotation. Mostly mechanical, but third-party libraries must have Jakarta-compatible versions (Q252).
4. **Upgrade third-party dependencies** to Jakarta-compatible releases *before* the Boot upgrade where possible.
5. **Spring Security 5 to 6** - the largest behavioral change (Q253).
6. **Configuration property changes** - many renames and removals (Q254).
7. **Auto-configuration registration** - `spring.factories` to `AutoConfiguration.imports` for any internal starters (Q185).
8. **Observability** - Sleuth is gone; migrate to Micrometer Tracing, including the B3 to W3C propagation change (Q193).
9. **Hibernate 5 to 6** - changed defaults for identifier generation and naming strategies, and some HQL behavior changes. This causes subtle data-layer issues and deserves its own test pass.
10. **Trailing slash matching removed** in Spring 6 - `/orders` and `/orders/` are no longer equivalent, which silently breaks clients.
11. Run the **OpenRewrite** Boot 3 recipe to automate the mechanical parts, then review the diff carefully.
12. Test, deploy to a canary, and watch authentication and error rates specifically.

The sequencing point matters: each step should be independently deployable, so a problem is attributable.

### Q252. Finding Jakarta breakages `[T]`

The failure is at **runtime**, as `NoClassDefFoundError` or `ClassNotFoundException` for a `javax.*` class, often from a code path that only executes occasionally - which is why it escapes a green build.

Libraries commonly affected: older Hibernate Validator, JAXB and SOAP clients, Quartz, older Jackson modules for JAXB, PDF and reporting libraries, servlet-based third-party filters, older Testcontainers and WireMock, and any internal shared library not yet republished.

How to find them systematically rather than by discovery in production:

- Use the **OpenRewrite** `UpgradeSpringBoot_3_0` recipe, which handles the mechanical rename and flags what it cannot.
- **Scan the dependency tree for `javax.*` imports** in compiled artifacts - a build-time check that fails if any dependency still references the removed namespace. This is the highest-value control.
- Check the `jdeps`-style analysis or use the Spring Boot migrator tooling.
- Raise a **runtime canary**: deploy to a canary with a synthetic test hitting the less-travelled code paths, especially file export, reporting, scheduled jobs and SOAP integrations - the areas that unit tests cover least.

The general lesson to state: a compile-clean Jakarta migration is not a working one, because the failures live in transitive dependencies and rarely-executed paths.

### Q253. Security 5 to 6 runtime breakages `[T]`

The compile-time changes are the easy half - `WebSecurityConfigurerAdapter` removed in favour of `SecurityFilterChain` beans, `authorizeRequests` to `authorizeHttpRequests`, `antMatchers` to `requestMatchers`, and the lambda DSL becoming mandatory. Those fail the build, which is the good case.

The ones that fail at **runtime** are the dangerous ones:

- **Explicit `SecurityContextRepository` saving** (Q148-149) - custom authentication filters silently stop persisting authentication.
- **`AuthorizationFilter` applies to all dispatcher types**, including `ERROR` and `FORWARD` (Q146), so error pages start returning 403 or looping.
- **CSRF deferred tokens and BREACH protection** (Q160) - SPA clients break.
- **`requestMatchers` uses MVC-aware matching** when MVC is present, so a rule that previously matched on a raw path may now match differently - this can either open or close access unexpectedly.
- **Path matching changes in Spring 6** - trailing slash matching removed, `PathPatternParser` as the default - which affects security rules that relied on the old behavior.
- **Default `RequestCache` behavior** and redirect handling changes affecting post-login navigation.

Given several of these can *widen* access rather than break visibly, my migration includes an automated authorization test matrix - every representative endpoint × every role × expected status - executed before and after, with the results diffed. Reading the configuration is not sufficient assurance for a security change.

### Q254. Finding configuration changes

Add `spring-boot-properties-migrator` as a runtime dependency for one release:

```xml
<dependency>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-properties-migrator</artifactId>
  <scope>runtime</scope>
</dependency>
```

At startup it reports renamed properties (and temporarily maps them) and errors on removed ones, using the metadata Boot ships. That converts a silent behavior change into a startup log you can act on - and it is the single most useful upgrade tool most teams do not know about. **Remove it after migrating**, since it is a startup cost and a crutch.

Beyond that: strict configuration validation so unknown properties are noticed (a mistyped or obsolete property is silently ignored by default, which is how a security setting quietly stops applying), a test asserting the effective values of the properties that matter, and a diff of `/actuator/configprops` between the old and new versions in a non-production environment - which catches defaults that changed even when your property did not.

### Q255. Dependency management

`spring-boot-dependencies` is a BOM pinning consistent versions for hundreds of libraries; the parent POM or Gradle plugin applies it. That consistency is most of the value Boot provides - the versions are tested together.

To override safely:

```xml
<properties>
  <postgresql.version>42.7.3</postgresql.version>
</properties>
```

Use the **property the BOM defines** rather than declaring an explicit `<version>` on the dependency, so all related artifacts move together. Overriding one artifact of a multi-module library while the BOM pins the rest produces a mixed-version classpath and `NoSuchMethodError` at runtime.

Rules I apply: override only with a documented reason (a CVE fix or a required feature), record it with a comment and an expiry, revisit at every Boot upgrade to remove overrides the BOM has caught up with, and never override Spring Framework or Security versions independently of Boot - those are tested as a set and mismatching them is how you get subtle, hard-to-diagnose failures.

### Q256. Upgrade cadence

Spring Boot minor releases arrive roughly every six months with about 12 months of OSS support (13 months for the last minor of a major), and Java LTS every two years. Falling behind is not a neutral choice: it compounds, and it eventually forces a large, risky, unbudgeted migration under CVE pressure - which is the situation most teams are actually in when they ask this question.

What I put in place:

- **Patch versions automatically** - Renovate or Dependabot raising pull requests, merged by CI without human debate. This is where most CVE fixes are.
- **Minor versions on a schedule** - a planned upgrade within one quarter of release, treated as normal work with an owner, not a project needing a business case.
- **A supported-version policy** with a stated floor, so "we are on an unsupported version" is a visible, escalating compliance issue rather than an engineering preference.
- **Capacity reserved** - a standing allocation for maintenance, because upgrades that compete with features always lose.
- **Automation to reduce cost** - a platform BOM so 40 services change one version property, OpenRewrite recipes for mechanical changes, and a canary service that upgrades first and documents the surprises for everyone else.

The argument I make to leadership is in their terms: staying current is a series of small, predictable costs; falling behind converts that into one large, unpredictable one, usually triggered by a vulnerability with a deadline attached.

### Q257. Versioning a shared starter

- **Semantic versioning**, honestly applied - a changed default is a breaking change even if it compiles, because behavior is the contract.
- **A support window** for the previous major, published up front, so teams can plan.
- **Deprecate before removing** - keep the old property working, mark it with `@DeprecatedConfigurationProperty` and a replacement so the warning appears in the IDE (Q37), and log a warning at startup. Remove only in the next major, after the window.
- **Migration notes with every release**, and an OpenRewrite recipe for anything mechanical.
- **Feature flags for behavior changes** - ship the new behavior disabled, let teams opt in, make it the default in the next major, remove the flag after that. That is three releases for one change, and it is what makes a 40-team upgrade non-events rather than incidents.
- **A canary consumer** - one service (ideally owned by the platform team) always on the latest version, so problems surface before wide adoption.
- **Automated upgrade pull requests** to every consumer with CI proving them, so upgrading is a review rather than a task.

The judgement point: the cost of a breaking change is not the code change, it is 40 teams × coordination × their release schedules. That reframing usually reveals that the change is not worth making, or that it should be additive - and being willing to carry a deprecated path for a year is what makes a platform trustworthy.

---

## 15. Web protocols beyond REST

### Q263. STOMP over WebSocket

WebSocket gives you a bidirectional byte pipe and nothing else - no routing, no addressing, no acknowledgment. STOMP is a small text protocol layered on top that adds `CONNECT`, `SUBSCRIBE`, `SEND` and destinations, which is what lets Spring apply its usual programming model to messages.

The sequence: the client issues an HTTP `GET` with `Upgrade: websocket`; a `HandshakeInterceptor` can inspect and copy attributes from the HTTP request into the WebSocket session; the handshake completes and the connection switches protocols. From then on nothing is HTTP - no filters, no `HttpServletRequest`, no per-request security.

```java
@Configuration @EnableWebSocketMessageBroker
class WsConfig implements WebSocketMessageBrokerConfigurer {
  public void registerStompEndpoints(StompEndpointRegistry r) {
    r.addEndpoint("/ws").setAllowedOrigins("https://app.example.com");
  }
  public void configureMessageBroker(MessageBrokerRegistry r) {
    r.setApplicationDestinationPrefixes("/app");   // routed to @MessageMapping
    r.enableSimpleBroker("/topic", "/queue");      // in-memory broker
  }
}
```

The **simple broker** is an in-memory subscription registry with a scheduled heartbeat thread. It keeps a map of destination to sessions and writes messages out. It does not persist, does not acknowledge, does not survive a restart, and does not know about other instances - which is Q265.

### Q264. `@MessageMapping` and user destinations

`@MessageMapping("/chat/{room}")` handles an inbound frame on an application destination; `@SendTo("/topic/room/{room}")` publishes the return value to a broadcast destination. Both run on the `clientInboundChannel` executor, not a servlet thread.

For a single user, the mechanism is the **user destination**. `SimpMessagingTemplate.convertAndSendToUser("alice", "/queue/alerts", payload)` rewrites the destination to a session-unique one (`/queue/alerts-user<sessionId>`) that only that user's session is subscribed to; the client subscribes to the plain `/user/queue/alerts`. `@SendToUser` does the same for a return value. The identity comes from `Principal` on the message, which is whatever the handshake established.

```java
simpMessagingTemplate.convertAndSendToUser(order.getOwner(), "/queue/orders", event);
```

`SimpMessagingTemplate` is also how a normal REST controller, a Kafka listener or a scheduled job pushes to a connected client - which is usually the real requirement, not chat.

### Q265. Scaling WebSocket across instances `[T]`

The simple broker's subscription registry is **local to the JVM**. With three instances behind a load balancer, Alice is connected to instance 1 and the event that concerns her is produced on instance 3, which has no idea she exists. The message is silently dropped - no error, which is why this reaches production.

Three fixes, in increasing order of correctness:

1. **Sticky sessions** - does not help at all. It keeps a client pinned, but the *publisher* is still on the wrong instance.
2. **A shared broker relay** - `enableStompBrokerRelay("/topic", "/queue")` pointing at RabbitMQ or ActiveMQ with the STOMP plugin. Spring stops being the broker and becomes a proxy; subscriptions and messages live in the broker, so any instance can publish to any client. This is the supported answer, and it also gives you persistence and flow control.
3. **A pub/sub side channel** - publish to Redis or Kafka and have every instance re-broadcast locally. Cheaper to run, but you have written a broker with no acknowledgment or backpressure, and every instance now processes every message.

Related capacity point: each connection holds a socket, buffers and a session for its whole lifetime. `setSendTimeLimit` and `setSendBufferSizeLimit` matter, because one slow client otherwise consumes heap until the connection is force-closed.

### Q266. Authenticating a WebSocket

Two places, and the distinction matters.

**At the handshake** the request is still HTTP, so the security filter chain, cookies and the `SecurityContext` all apply. Securing `/ws` in `authorizeHttpRequests` and copying the authenticated `Principal` into the session is the simplest correct approach for a browser client with a session cookie.

**Per STOMP frame** is required when the credential is a bearer token, because browsers cannot set headers on the WebSocket handshake. The client sends the token in the `CONNECT` frame and you authenticate in a `ChannelInterceptor`:

```java
@Override public void configureClientInboundChannel(ChannelRegistration reg) {
  reg.interceptors(new ChannelInterceptor() {
    public Message<?> preSend(Message<?> msg, MessageChannel ch) {
      var acc = StompHeaderAccessor.wrap(msg);
      if (StompCommand.CONNECT.equals(acc.getCommand())) {
        acc.setUser(jwtAuthenticate(acc.getFirstNativeHeader("Authorization")));
      }
      return msg;
    }
  });
}
```

Two things people get wrong. First, **the connection outlives the token** - a 15-minute JWT on a connection open for six hours is authenticated by something long expired, so you need a re-authentication frame or a server-side expiry that closes the socket. Second, authorization is *per destination*, not per URL: `@PreAuthorize` on the `@MessageMapping` method, or `AuthorizationManager`-based message security, because subscribing to `/topic/admin` is an access decision no HTTP rule will ever see.

### Q267. WebSocket, SSE and polling `[T]`

| | WebSocket | SSE | Long polling |
| --- | --- | --- | --- |
| Direction | Bidirectional | Server to client | Request/response |
| Transport | Upgrade, not HTTP after | Plain HTTP streaming | Plain HTTP |
| Reconnect | You implement it | Built into `EventSource`, with `Last-Event-ID` | Natural |
| Proxy friendliness | Needs `Upgrade` support end to end | Works everywhere | Works everywhere |
| Server cost | Connection + session | Connection | Connection churn |

My default is **SSE for server-push, WebSocket only when the client genuinely pushes too** - dashboards, notifications, progress and streamed LLM tokens are all one-directional, and SSE gets automatic reconnect with event replay for free.

What the infrastructure does to each is the part candidates miss. Layer-7 proxies, corporate middleboxes and some API gateways strip the `Upgrade` header or fail to route it, so WebSocket fails in exactly the enterprise networks you cannot test from. Buffering proxies break SSE unless you disable buffering and send a periodic comment heartbeat, otherwise nothing arrives until the buffer fills. Idle timeouts on the load balancer (60 seconds on an AWS ALB by default) close both unless a heartbeat keeps them warm. And with HTTP/1.1 the browser's six-connections-per-origin limit makes SSE tabs starve the rest of the page - HTTP/2 removes that.

### Q268. Spring HATEOAS

`RepresentationModel` is the base carrying a `Links` collection; `EntityModel<T>` wraps a payload with links; `CollectionModel<T>` wraps many; `PagedModel` adds pagination links. `WebMvcLinkBuilder.linkTo(methodOn(...))` builds URIs from the controller mapping rather than string concatenation, so a path change does not silently produce broken links.

```java
EntityModel.of(order,
    linkTo(methodOn(OrderController.class).one(order.getId())).withSelfRel(),
    linkTo(methodOn(OrderController.class).cancel(order.getId())).withRel("cancel"));
```

A `RepresentationModelAssembler` moves that out of the controller into one testable place per resource, which matters because the value of hypermedia is consistency - links added ad hoc in handlers drift immediately. The default media type is HAL (`application/hal+json`); HAL-FORMS additionally describes the *inputs* an affordance needs, which is what makes a generic client possible.

The genuinely useful pattern is **state-dependent affordances**: include the `cancel` link only when the order is actually cancellable. The client stops encoding your state machine.

### Q269. When hypermedia earns its cost `[A]`

It earns its cost when the *client is not yours and cannot be redeployed with you*: long-lived partner integrations, public APIs with many independent consumers, or a generic UI driven by the API's own description. In those cases, moving the state machine into the response is what lets you change flow without a coordinated release, and HAL-FORMS lets a client render actions it was never coded for.

It does not earn its cost in the common case: a single-page application and a mobile app, both written by the same organization, released alongside the API. The client already knows the URIs and the state machine, so the links are payload nobody reads, and every one of them costs a link builder, a test and bytes on the wire.

Why most APIs stop at Richardson level 2: the benefit only materializes if clients actually follow links instead of templating URLs, and almost none do - the moment one client hardcodes `/orders/{id}/cancel`, you have all the cost and none of the freedom. I would rather invest in an OpenAPI contract, consumer-driven contract tests and a clear versioning policy, which solve the real coupling problem for internal clients. The position to state in an interview is not "HATEOAS is bad" but "hypermedia is a coupling trade, and I only pay for it where I cannot coordinate releases".

### Q270. CORS in Spring `[T]`

CORS is enforced by the browser, not the server; your job is to send headers that authorize a cross-origin read. The preflight is an `OPTIONS` request the browser sends before any non-simple request (custom headers, `PUT`, `DELETE`, JSON content type), and it carries no credentials.

The three configuration points:

- `@CrossOrigin` on a controller or method - fine for a demo, terrible at scale because policy ends up scattered.
- `WebMvcConfigurer.addCorsMappings` - central for MVC, but only applies to handler-mapped requests.
- A `CorsConfigurationSource` bean plus `http.cors(withDefaults())` - the one I use, because it is the only one Spring Security sees.

**Spring Security must know about CORS because its filter chain runs before the `DispatcherServlet`.** A preflight `OPTIONS` carries no `Authorization` header and no cookie, so an authenticated rule rejects it with 401 before MVC's CORS handling ever runs - and the browser reports a generic "CORS error" that sends people to change MVC config that was already correct. `http.cors()` installs `CorsFilter` early in the chain, which answers the preflight and short-circuits it.

Other things that break a preflight: `allowCredentials(true)` combined with `allowedOrigins("*")` is illegal and throws at startup (use `allowedOriginPatterns`); a header the client sends but `allowedHeaders` omits; a missing `exposedHeaders` so the client can read the response but not the header it needs; `maxAge` left at the default so every request is preflighted twice; and a gateway that adds its own CORS headers, producing duplicate `Access-Control-Allow-Origin` values which browsers reject. Decide in exactly one place - gateway or application, never both.

---

## 16. Messaging endpoints in Spring

### Q271. `JmsTemplate` and `@JmsListener`

`@JmsListener` is backed by a `DefaultMessageListenerContainer`, which runs its own threads outside the container's request infrastructure. Each thread loops: take a connection and session from the pool, call `consumer.receive(receiveTimeout)`, and if a message arrives invoke the listener, then acknowledge or commit. If nothing arrives, the loop repeats - so the container is polling the broker, not being pushed to.

`concurrency = "3-10"` sets minimum and maximum consumers, and `DefaultMessageListenerContainer` scales up only after `idleConsumerLimit` and `maxMessagesPerTask` thresholds are met, so ramp-up is deliberately slow. Two consequences worth stating: **more consumers than queue partitions or than the database pool can serve is a self-inflicted outage**, and for a topic (rather than a queue) concurrency above 1 duplicates delivery unless the subscription is shared.

`JmsTemplate` is the send side and is synchronous by design: `convertAndSend` creates a session and producer, sends, and closes them.

### Q272. Why `JmsTemplate` is slow `[T]`

By default `JmsTemplate` creates a **connection, session and producer per call, and closes them afterwards**. On a real broker each connection is a TCP connect plus an authentication handshake, which is tens of milliseconds. Sending 1000 messages costs 1000 handshakes, and the throughput you measure is the broker's connection rate, not its message rate.

The Spring model deliberately does no caching itself so it can participate in a JTA transaction, where the connection must come from the transaction-aware factory. `CachingConnectionFactory` fixes the common non-JTA case by caching the connection and a configurable number of sessions and producers per session:

```java
@Bean ConnectionFactory connectionFactory(ConnectionFactory target) {
  var f = new CachingConnectionFactory(target);
  f.setSessionCacheSize(10);
  return f;
}
```

Order-of-magnitude improvement for one bean. Caveats: `setSessionCacheSize` must exceed your concurrency or threads contend; do not put a caching factory in front of a JTA-managed XA factory; and on a listener container the container already manages its own sessions, so the caching factory is for the *send* side.

### Q273. Which acknowledgment actually redelivers

The question is where the "I processed this" decision lives.

- **`sessionTransacted = true`** - a local JMS transaction. The message is delivered, the listener runs, and the session commits on normal return or rolls back on exception, which puts the message back for redelivery. This is what makes JMS redelivery work.
- **`AUTO_ACKNOWLEDGE`** (the default) - the container acknowledges after a successful listener call, so an exception does trigger redelivery, but there is no transaction, so nothing is grouped.
- **`CLIENT_ACKNOWLEDGE`** - you call `message.acknowledge()`, and it acknowledges every message delivered on that session so far, not just this one. Rarely what people intend.
- **`@Transactional` alone** - a *database* transaction. It rolls back the database write; it says nothing about the message. Without `sessionTransacted`, the message was already acknowledged and is gone.

The combination people reach for is `sessionTransacted = true` plus `@Transactional`, with the JMS transaction outside the database one. That is a best-efforts 1-phase commit, not atomicity: if the database commits and the JMS commit then fails, the message is redelivered and the work happens twice. So the real answer is the same as everywhere else in this pack - **make the handler idempotent** (an inbox table keyed by message ID in the same database transaction), and configure a redelivery limit and a DLQ so a poison message cannot loop forever.

### Q274. Spring AMQP and declaration ownership

`RabbitTemplate` sends and `@RabbitListener` consumes, with `SimpleMessageListenerContainer` (thread per consumer, `prefetch` messages in flight) or `DirectMessageListenerContainer` (dispatches on the client library's threads, cheaper for many queues). Declaring topology is a separate concern: `Queue`, `TopicExchange` and `Binding` beans are picked up by `RabbitAdmin` and declared on connect, and `@RabbitListener(bindings = @QueueBinding(...))` does the same inline.

The ownership question is the real one, and my answer is that **the consumer owns its queue and its binding, and nobody owns the exchange in application code**. A producer that declares queues knows its consumers, which is exactly the coupling messaging was supposed to remove. Exchanges are shared infrastructure and belong in the same declarative infrastructure code as the cluster itself (Terraform, or the operator), because a rogue application declaring an exchange with different durability or arguments fails on mismatch - `PRECONDITION_FAILED` - and takes the channel down with it.

In production I also set `spring.rabbitmq.dynamic=false` for services that must not create topology, so a configuration typo fails loudly instead of quietly creating an unrouted queue that fills the disk.

### Q275. Confirms versus returns `[T]`

They answer different questions and both are off by default.

- **Publisher confirms** answer "did the *broker* take responsibility for this message?" The broker acks after routing (and after persisting, for a durable queue). This catches broker unavailability, disk alarms and connection loss.
- **Publisher returns** answer "was this message routed to at least one queue?" If a mandatory message matches no binding, the broker returns it. Without this, a typo in the routing key is a silently discarded message - the publish succeeds, the confirm is positive, and the message never existed.

```yaml
spring.rabbitmq.publisher-confirm-type: correlated
spring.rabbitmq.publisher-returns: true
spring.rabbitmq.template.mandatory: true
```

The failure **neither catches** is the consumer's: the message was routed and persisted, and then the consumer rejected it, dead-lettered it, or processed it wrongly. A confirm is a broker receipt, not an end-to-end delivery guarantee. It also does not survive the producer crashing between the database commit and the publish - which is the outbox pattern's entire reason for existing (Q79).

### Q276. Acknowledgment, DLX and where retry happens

`AcknowledgeMode.AUTO` (Spring's default, and confusingly *not* the AMQP auto-ack) acknowledges after the listener returns and rejects on exception. `MANUAL` gives you the `Channel` and delivery tag. `NONE` is fire-and-forget with no redelivery.

Dead-lettering is broker-side: the queue is declared with `x-dead-letter-exchange`, and a message that is rejected with `requeue=false`, expires, or overflows the queue length is republished there with an `x-death` header recording why and how many times.

Retry can happen in three places, and choosing wrongly is the classic mistake:

1. **In-process, via `RetryInterceptorBuilder`** on the listener container - a stateless interceptor retries with backoff *on the consumer thread*, holding the message unacknowledged. Cheap and correct for a transient blip of a few hundred milliseconds. With a long backoff it blocks a consumer thread and, at prefetch scale, stalls the queue.
2. **Broker-side requeue** - `requeue=true` puts the message back at the head immediately, so a permanently failing message becomes a hot loop that saturates the consumer. Almost never right without a delay.
3. **A delay queue** - dead-letter to a queue with a TTL and no consumer, whose own DLX points back at the original exchange. Delay without holding a consumer thread, which is the pattern that scales.

The rule I apply: retry in process only for short, transient faults; use a delayed retry queue for anything longer; and always terminate at a real DLQ with an alert and a documented redrive procedure. `spring.rabbitmq.listener.simple.default-requeue-rejected: false` is a default I always change, because leaving it true is how a single bad message consumes a cluster.

### Q277. `__TypeId__` and payload versioning `[T]`

`Jackson2JsonMessageConverter` writes the fully qualified producer class name into the `__TypeId__` header, and the consumer's converter uses it to pick a target class. That means **the fully qualified class name of the producer is part of your wire contract**. Rename the package, move the class to a shared library, or split the service, and consumers fail deserialization with `ClassNotFoundException` for a change that touched no logic.

Fixes, in order of preference:

1. **Map types explicitly** with `DefaultJackson2JavaTypeMapper` and an ID-to-class map, so the wire carries a stable logical name (`order.created.v1`) and each side maps it to whatever class it likes.
2. **Force the target type** on the consumer (`setDefaultType` with `TypePrecedence.INFERRED`, or the `@RabbitListener` parameter type), ignoring the header entirely.
3. Never accept an arbitrary class name from the wire - deserializing to a producer-chosen type is a gadget-chain risk, the same category as the polymorphic JSON problem in Q85. Kafka's `spring.json.trusted.packages` exists for exactly this reason and should be an allow-list, never `*`.

For versioning the payload itself: additive-only changes with a tolerant reader (unknown fields ignored, new fields optional with defaults), a version field in the envelope, and a new logical type ID when a change is genuinely breaking so old and new can be consumed side by side during the transition.

### Q278. Spring Integration

Spring Integration is an implementation of the enterprise integration patterns: `MessageChannel`s connect endpoints, and endpoints are transformers, filters, routers, splitters, aggregators and service activators. The `IntegrationFlow` DSL wires them:

```java
@Bean IntegrationFlow fileFlow(JdbcTemplate jdbc) {
  return IntegrationFlow.from(Files.inboundAdapter(new File("/in")),
                              c -> c.poller(Pollers.fixedDelay(5000).maxMessagesPerPoll(10)))
      .transform(Transformers.fileToString())
      .split(s -> s.delimiters("\n"))
      .filter((String line) -> !line.isBlank())
      .handle(m -> jdbc.update("insert into staging(line) values (?)", m.getPayload()))
      .get();
}
```

What it gives you over plain code: **channel adapters for protocols you would otherwise write by hand** (file, FTP, SFTP, mail, TCP, MQTT, JDBC polling), and stateful patterns that are genuinely hard to get right - an aggregator with correlation, release and group timeout, a resequencer, a claim check, and a poller with transaction and error-channel semantics. Errors go to a dedicated error channel rather than being thrown into a caller that does not exist.

When it is justified: multi-protocol integration work, or a flow that needs those stateful patterns. When it is not: a straight "consume from Kafka, transform, write to database" pipeline, where the DSL adds an abstraction the on-call engineer has to learn and a stack trace nobody can read. My honest position is that Spring Integration is excellent at what it was designed for and routinely over-applied - and if the flow is one source, one transform and one sink, `@KafkaListener` and a service method is the maintainable choice.

### Q279. Spring Web Services and SOAP

Spring-WS is deliberately **contract-first**: you write the XSD, generate the JAXB classes at build time (`jaxb2-maven-plugin`), and the WSDL is generated from the schema by `DefaultWsdl11Definition`. Endpoints are `@Endpoint` classes with `@PayloadRoot(namespace, localPart)` methods that receive and return JAXB objects; `MessageDispatcherServlet` routes by payload root rather than by URL.

`XwsSecurityInterceptor` or `Wss4jSecurityInterceptor` handles WS-Security - signing, encryption, timestamps and username tokens applied at the *message* level rather than the transport level.

When SOAP is still right in 2026: when the counterparty dictates it, which is the honest answer for banking, insurance, telecom provisioning and government interfaces; when you need message-level signatures that survive intermediaries, where TLS terminating at a gateway is not sufficient for non-repudiation; and when WS-* features such as reliable messaging or `WS-AtomicTransaction` are contractual. What it genuinely offers is a machine-readable, strongly typed, enforceable contract - the thing REST needed OpenAPI to approximate.

For new internal services I would not choose it. The pattern I have used is an anti-corruption layer: one adapter service speaking SOAP outward and events or REST inward, so the XML and the WS-Security keystore management stay in one place rather than spreading through the estate.

### Q280. `@Transactional` on a listener `[T]`

It is a **database transaction only**. The message broker knows nothing about it. So the sequence is: the container delivers the message, the database transaction commits, and the container then acknowledges. Two gaps follow.

If the process dies **after the database commit and before the acknowledgment**, the message is redelivered and you process it again - a duplicate. If the transaction rolls back after an effect the database cannot undo (an email sent, an HTTP call made, a second message published), redelivery repeats that effect.

There is no fix inside the annotation. What actually works:

- **Consume idempotently.** An inbox table with the message ID as the primary key, inserted inside the same transaction as the business write. A duplicate hits the unique constraint and the handler exits successfully. This turns at-least-once delivery into effectively-once processing, and it is the only part of the problem you can fully solve.
- **Publish through an outbox.** Never publish inside the transaction: write the event to an outbox table in the same commit and let a relay publish it (Q79). Otherwise a commit-then-crash loses the event, or a publish-then-rollback invents one.
- **Do not do non-transactional work inside the transaction** - the HTTP call and the email belong after commit, driven by the outbox or `@TransactionalEventListener(AFTER_COMMIT)`.

For Kafka specifically, `@Transactional` on a `@KafkaListener` does not join a Kafka transaction unless a `KafkaTransactionManager` is in play, and even then exactly-once applies only to Kafka-to-Kafka flows, not to Kafka-plus-database (Q216).

---

## 17. Spring Batch

### Q281. The Spring Batch domain model

A **`Job`** is the unit of work; a **`Step`** is a phase of it; a `Job` has ordered steps with conditional flow. **`JobLauncher`** starts a job with `JobParameters`. **`JobRepository`** persists state - and everything restartable in Spring Batch follows from the fact that this state is in a database, not in memory.

The metadata tables:

| Table | Holds |
| --- | --- |
| `BATCH_JOB_INSTANCE` | One row per job name + identifying parameters |
| `BATCH_JOB_EXECUTION` | One row per attempt at an instance, with status and exit code |
| `BATCH_JOB_EXECUTION_PARAMS` | The parameters of that attempt |
| `BATCH_JOB_EXECUTION_CONTEXT` | Serialized job-level `ExecutionContext` |
| `BATCH_STEP_EXECUTION` | Per step: read, write, commit, skip and rollback counts |
| `BATCH_STEP_EXECUTION_CONTEXT` | Serialized step-level `ExecutionContext`, including reader position |

Two distinctions interviewers probe. **`JobInstance` versus `JobExecution`**: the instance is "the payroll run for 2026-08", the execution is one attempt at it; re-running after a failure creates a new execution against the same instance, which is what makes restart meaningful. And the repository is written to *transactionally alongside your chunk*, which is why it must live in a real database - the `Map`-based repository is for tests only, since restart is exactly the feature it cannot provide.

### Q282. Chunk versus `Tasklet`

A **`Tasklet`** is a single `execute()` method called repeatedly until it returns `FINISHED`, each call in its own transaction. Use it for operations that are not item-oriented: run a stored procedure, move a file, truncate a staging table, call a service.

**Chunk-oriented** processing is read-process-write in batches:

```java
new StepBuilder("importStep", jobRepository)
    .<InputRow, Customer>chunk(500, transactionManager)
    .reader(reader()).processor(processor()).writer(writer())
    .faultTolerant().skipLimit(20).skip(ParseException.class)
    .build();
```

The transaction boundary is **the chunk, not the item**. Spring Batch opens a transaction, calls `read()` `chunkSize` times (accumulating in memory), calls `process()` on each, calls `write()` **once with the whole list**, updates the step execution counters in the same transaction, and commits. That single-call writer is the reason batch is fast - one `JDBC` batch insert per 500 rows rather than 500 round trips.

Choosing the chunk size is a real trade-off: larger means fewer commits and better throughput, but a bigger rollback on failure, more heap held, and longer locks. I start at 100-1000 and tune against the actual write cost.

### Q283. What survives a mid-chunk failure `[T]`

With a chunk size of 100 and a failure at item 7 of the second chunk: **the first chunk is committed** (items 1-100 are in the database and `BATCH_STEP_EXECUTION.write_count` says 100, in the same transaction). The second chunk rolls back entirely - items 101-107 are not written, and the counters do not advance. The step execution is marked `FAILED` and the `ExecutionContext` retains the position saved at the last successful commit.

On restart with the same `JobParameters`, Spring Batch finds the existing `JobInstance`, creates a new `JobExecution`, and the reader **restores itself from the `ExecutionContext`**. How well depends entirely on the reader: `ItemStream` readers such as `FlatFileItemReader` and the paging readers save a row or page count in `update()` and skip forward on `open()`. A cursor reader re-executes its query and skips `n` rows, which is correct only if the underlying data has not changed. A custom reader that does not implement `ItemStream` restarts **from the beginning** and reprocesses the first 100 items - which is Q288's point about idempotent writers.

If the step is fault-tolerant, there is a further subtlety: on a skippable exception Spring Batch rolls back and **re-reads the chunk one item at a time** to identify the offending item, so `process()` can be called more than once for the same item. Processors must therefore be side-effect free.

### Q284. Reader choices at scale

| Reader | Mechanism | Breaks when |
| --- | --- | --- |
| `JdbcCursorItemReader` | One `ResultSet` streamed with a fetch size | The connection is held for the whole step; long transactions, replica conflicts, and no safe restart if the data changes |
| `JdbcPagingItemReader` | A new sorted, keyed query per page | Requires a stable unique sort key; `OFFSET` deepening if the implementation is naive, and rows shifting between pages |
| `JpaPagingItemReader` | Same, through the `EntityManager` | Persistence-context growth; the reader clears it per page, which detaches entities the processor may still expect |
| `RepositoryItemReader` | Calls a Spring Data method with `Pageable` | Convenient, same paging caveats, and easy to accidentally hide an N+1 |
| `FlatFileItemReader` | Buffered line reader with a `LineMapper` | Cheap and restartable by line count; a mid-file change invalidates the position |
| `SynchronizedItemStreamReader` wrapper | Serializes reads | Needed to use a non-thread-safe reader in a multi-threaded step, and it becomes the bottleneck |

The rules I apply: **cursor for a snapshot-consistent single-threaded pass over a stable table; paging for anything long-running, multi-threaded or restartable**. Paging must sort by a unique, immutable key - sort by a non-unique column and rows appear twice or not at all across pages, which is a data bug no test catches. And keyset paging (`WHERE id > :last ORDER BY id`) beats `OFFSET` once the table is large.

### Q285. Restartability and parameter identity

`JobParameters` are the identity of a `JobInstance`. Spring Batch computes the instance from the job name plus the **identifying** parameters, and enforces that one instance runs to `COMPLETED` at most once. That is a feature: it prevents the same month's payroll being run twice.

So `JobInstanceAlreadyCompleteException` on re-run means exactly that - this work already succeeded. Options:

- Add a genuinely identifying parameter (`runDate=2026-08-01`), which is the correct model for periodic jobs.
- Mark a parameter non-identifying (`new JobParameter<>(value, String.class, false)`), so it is recorded but does not affect identity.
- `allowStartIfComplete(true)` on a step, which lets that step re-run within a restarted job even though it previously succeeded - right for idempotent setup or cleanup steps, wrong for the step that writes the ledger.
- A `RunIdIncrementer`, which appends an incrementing `run.id` so every launch is a new instance - convenient, but it discards the duplicate-run protection, so I only use it for genuinely idempotent jobs.

Restart also has limits: a step is restartable only up to `startLimit` (default `Integer.MAX_VALUE`), an execution stuck in `STARTED` after a hard kill must be marked `ABANDONED` or `FAILED` before restart, and a job whose reader is not an `ItemStream` restarts from zero.

### Q286. Skip, retry and stateful writers `[T]`

Three fault-tolerance mechanisms interact:

- **Retry** re-attempts an item on a listed exception. Because the chunk transaction has already rolled back, retry means **the whole chunk is replayed**, item by item.
- **Skip** logs the failing item and continues, up to `skipLimit`. Reaching the limit fails the step.
- **`noRollback`** declares an exception that should not roll back the chunk at all.

The failure mode with a stateful `ItemWriter` is this: a skippable exception during write causes Spring Batch to roll back and reprocess the chunk one item at a time to find the culprit. A writer that holds internal state - an open file handle with a partially written buffer, an accumulated running total, a `StringBuilder`, an external HTTP client that has already sent - has **already applied the effects of the first pass**, and the database rollback does not undo it. The scan then applies them again. You get duplicated file lines, doubled totals, or duplicate downstream calls, and the counts in `BATCH_STEP_EXECUTION` look perfectly healthy.

The rules: writers must be stateless and idempotent (Q288), processors must be side-effect free because they may be invoked repeatedly for the same item, anything that must happen exactly once belongs in a `ChunkListener` or `StepExecutionListener` that is aware of rollback, and a `SkipListener` should record every skipped item somewhere durable - a skip limit of 100 with no record of *what* was skipped is silent data loss.

### Q287. Scaling a batch job

Four models, in increasing order of complexity:

1. **Multi-threaded step** - one step, a `TaskExecutor`, many threads sharing one reader and writer. Simple, but it requires thread-safe components, breaks reader restartability (the saved position is meaningless when threads interleave), and destroys ordering. Safe mainly with a `SynchronizedItemStreamReader` and `saveState(false)`.
2. **Parallel flows** - independent steps running concurrently in a split. Trivially safe because nothing is shared; only useful when the work genuinely decomposes into different steps.
3. **Local partitioning** - a `Partitioner` divides the input into ranges (customer IDs 1-1000, 1001-2000), and each partition gets its **own step execution, own reader and own `ExecutionContext`**. This is the one I reach for: full restartability per partition, no shared state, and scaling is a matter of the grid size and the executor. It needs a partitionable key with a reasonably even distribution.
4. **Remote partitioning / remote chunking** - the same, distributed over messaging. Remote partitioning sends only partition metadata (workers read their own data, so it scales the reader too); remote chunking sends the *items* to workers, so the manager's reader remains the bottleneck and the network carries the payload. Remote chunking is only worth it when processing is far more expensive than reading.

Reader safety is the deciding constraint: paging readers partition cleanly, cursor readers do not; anything relying on a saved position is incompatible with a shared multi-threaded step.

### Q288. Why writers must be idempotent `[T]`

Because "transactional" bounds the **database** work in one chunk, and it does not bound anything else, nor does it prevent the chunk from running twice.

Four routes to a repeated write, none of which the chunk transaction addresses:

1. **Restart with a non-restartable reader** - the position was never saved, so the step re-reads from the start and rewrites everything already committed.
2. **The skip scan** - a fault-tolerant chunk that fails is re-read item by item, so items in that chunk pass through the writer more than once.
3. **The commit-then-crash window** - the database commits and the process dies before the job repository records it, or the step execution is left `STARTED` and later restarted from an earlier checkpoint.
4. **Non-database effects** - files, HTTP calls, messages and emails are not in the transaction at all, so a rollback leaves them and a replay repeats them.

Practically that means: upsert rather than insert (`ON CONFLICT DO UPDATE`, `MERGE`), use a natural or deterministic business key rather than a generated one, write files to a temporary path and rename atomically at step completion, and route messages through an outbox so the publish is part of the same commit. The test I actually run is "execute the job twice against the same input and assert the end state is identical" - if that fails, the job is not production-ready regardless of what the counters say.

### Q289. Spring Batch 5

The changes that matter on upgrade:

- **`@EnableBatchProcessing` is no longer required** - Boot 3 auto-configures the infrastructure when `spring-boot-starter-batch` is present. Worse, *adding* it now **switches the auto-configuration off** (it backs off via `@ConditionalOnMissingBean`), which is the opposite of the Batch 4 behavior and produces confusing failures on upgrade. Remove it unless you deliberately want manual control.
- **`JobBuilderFactory` and `StepBuilderFactory` are gone.** Use `new JobBuilder(name, jobRepository)` and `new StepBuilder(name, jobRepository)`, passing the `JobRepository` and, for chunk steps, the `PlatformTransactionManager` explicitly. This is mechanical but touches every job configuration class.
- **`JobParameters` are typed and generic** - `new JobParameter<>(value, String.class, true)`, with the boolean controlling whether the parameter is identifying. The default `JobParametersConverter` changed format, so the command-line syntax gained a type: `runDate(java.time.LocalDate)=2026-08-01`.
- **Jakarta namespace and Java 17 baseline**, in line with the rest of Boot 3.
- **The metadata schema changed** - new columns and sequence handling. In production, run the DDL upgrade script explicitly rather than relying on `spring.batch.jdbc.initialize-schema`, which I set to `never` outside of tests anyway.
- `JobLauncherApplicationRunner` replaced `JobLauncherCommandLineRunner`, and `spring.batch.job.name` replaced `spring.batch.job.names`.

### Q290. Kubernetes `Job` versus a long-lived service `[A]`

I default to a **Kubernetes `Job` or `CronJob` running the Boot application with `spring.batch.job.enabled=true`**, and a `spring.batch.job.name` selecting which job to run. The reasons are operational rather than architectural: the batch workload gets its own resource requests and limits, so a 4 GB sort does not evict the request-serving pods; it gets its own restart policy and backoff; failure is visible as a failed `Job` object rather than a log line inside a healthy service; and the pod exits, so nothing leaks between runs. Scheduling comes from the cluster, which removes the "runs on every instance" problem in Q217 entirely.

The exit code has to be wired correctly or Kubernetes thinks a failed job succeeded: `System.exit(SpringApplication.exit(context, ...))`, with Boot's `ExitCodeGenerator` mapping the `JobExecution` status. This is the detail most teams miss.

I keep batch inside a long-lived service only when the job is small, frequent and needs the service's warm caches or in-memory state, or when the platform has no job scheduler. Then it is `@Scheduled` plus ShedLock plus a bounded executor, and I accept that a heavy job competes with request traffic.

Testing is the same in both cases:

```java
@SpringBootTest @SpringBatchTest
class ImportJobTest {
  @Autowired JobLauncherTestUtils utils;
  @Test void skipsBadRowsAndCommits() throws Exception {
    var params = new JobParametersBuilder().addString("input", "classpath:rows.csv").toJobParameters();
    JobExecution exec = utils.launchJob(params);
    assertThat(exec.getExitStatus()).isEqualTo(ExitStatus.COMPLETED);
    assertThat(exec.getStepExecutions().iterator().next().getSkipCount()).isEqualTo(2);
  }
}
```

`launchStep` tests one step in isolation, `JobRepositoryTestUtils` clears metadata between tests, and the tests I insist on are the restart test (fail mid-way, relaunch, assert the end state) and the double-run idempotency test from Q288.

---

## 18. Non-relational Spring Data and multi-store

### Q291. `MongoTemplate` versus repositories

Repositories give derived queries, `@Query` with a JSON filter, paging and the same proxy mechanism as JPA (Q121). `MongoTemplate` is the lower-level API with the full command surface, and both share the same `MappingMongoConverter`, so entities map identically - mixing them is normal, not a smell.

Aggregation is the clearest case for the template, because a pipeline is not expressible as a derived query:

```java
Aggregation agg = Aggregation.newAggregation(
    Aggregation.match(Criteria.where("status").is("SHIPPED").and("createdAt").gte(from)),
    Aggregation.group("customerId").sum("total").as("revenue").count().as("orders"),
    Aggregation.sort(Sort.Direction.DESC, "revenue"),
    Aggregation.limit(20));
List<CustomerRevenue> top = mongoTemplate
    .aggregate(agg, "orders", CustomerRevenue.class).getMappedResults();
```

Other template-only work: bulk operations, `findAndModify` for atomic read-modify-write, partial updates with `Update.inc`/`set` (a repository `save()` rewrites the whole document, which loses concurrent field updates), and `$` positional array updates. `@Aggregation` on a repository method covers simple pipelines if you prefer to keep everything in the interface.

The practical caution: aggregation runs in the server with a 100 MB per-stage memory limit unless `allowDiskUse` is set, and `$match` must come first and hit an index or you have written a collection scan with extra steps.

### Q292. Embed or reference `[T]`

Embed when the child is owned by the parent, read with it, and bounded - order lines, an address, a settings object. Reference when the child is shared, queried independently, or unbounded.

What forces the decision is the **16 MB document limit combined with the fact that Mongo rewrites and re-indexes the whole document on update**. An unbounded embedded array - audit entries, comments, events - is the classic modelling failure. Symptoms in order: documents outgrow their allocation so every update relocates them; index entries multiply because a multi-key index has one entry per array element; reads fetch megabytes to display ten items; the working set stops fitting in RAM and latency collapses; and finally writes fail outright at 16 MB, with the data now unmigratable in place.

The remedies are the **subset pattern** (embed the last 20, keep the full history in its own collection) and the **bucket pattern** (one document per customer per day holding up to N events). Both preserve the read that motivated embedding without an unbounded array.

I also treat "we will just embed it, it is only a few" as needing a stated upper bound. If nobody can state one, it is a reference.

### Q293. Mongo transactions

`MongoTransactionManager` makes `@Transactional` work with Mongo, and it plugs into the same abstraction as JDBC (Q59) - `TransactionSynchronizationManager` binds the `ClientSession` to the thread, and the template picks it up.

What the deployment must provide: **a replica set or sharded cluster with the WiredTiger engine**. A standalone `mongod` cannot do transactions, which is the classic "works in the test container, fails in the developer's local Mongo" report. Multi-document transactions have a default 60-second limit, hold snapshots that pressure the cache, and on a sharded cluster are considerably more expensive.

What to do instead most of the time: **model so you do not need one**. Mongo already gives single-document atomicity, so an aggregate that is one document needs no transaction - which is the same aggregate-boundary reasoning as Spring Data JDBC (Q138). Where an operation genuinely spans documents, `findAndModify` for atomic state transitions, an outbox document for downstream effects, and idempotent retries cover most cases. If your domain needs frequent multi-document ACID guarantees, that is evidence the data is relational and the store choice deserves revisiting - a more useful thing to say in an interview than reciting the configuration.

### Q294. Elasticsearch and zero-downtime reindex

`ElasticsearchOperations` (and the repository abstraction over it) handles CRUD, criteria and native queries; `IndexOperations` manages mappings and aliases. Mappings should be **explicit** - dynamic mapping infers a type from the first document it sees, and a field that arrives as `"12"` before it arrives as `12` is now permanently a `keyword`. Since a mapping cannot be changed in place, a mapping change is a reindex.

The alias pattern makes that non-disruptive:

1. Applications only ever read and write through an alias, `orders`, never a concrete index.
2. Create `orders-v2` with the new mapping.
3. Backfill it - `_reindex` from `orders-v1`, or replay from the source of record, which is better because it also fixes anything the old index got wrong.
4. Dual-write, or capture the changes since the backfill started, so `v2` catches up.
5. Atomically swap the alias in a single actions call - remove from `v1`, add to `v2`. Readers never see a window with no index.
6. Keep `v1` for a rollback window, then delete it.

Sizing details worth knowing: shard count is fixed at creation, refresh interval controls the near-real-time visibility gap (raise it during a bulk load, then restore it), and `BulkOptions` with a few thousand documents per request beats per-document indexing by an order of magnitude.

### Q295. Why Elasticsearch is not a source of record `[T]`

Its guarantees are wrong for the job. Indexing is **near-real-time, not immediate** - a document is invisible until the next refresh (one second by default), so a read-after-write is not guaranteed. There are no multi-document transactions and no foreign keys. Mappings cannot change, so schema evolution means a reindex. Historically the replication model could lose acknowledged writes under partition, and while that improved substantially, the design point is search availability, not durability. And a corrupted index or a mistaken mapping has no `mongodump` equivalent that reconstructs your business data.

The correct write path is **write to the system of record, then project into the index**:

```
service -> PostgreSQL (source of record) -> outbox table
        -> relay / CDC -> event stream -> indexer -> Elasticsearch (behind an alias)
```

Properties this gives you: the index is **rebuildable at any time** from the database (which is what makes a mapping change routine rather than an incident), the write path is not coupled to search availability, and search-side failures degrade a feature instead of failing the transaction. Never dual-write from the application to both, since that has no atomicity and drifts silently.

The consequence to design for is lag: the UI must tolerate a just-created item not yet appearing in search, which is the read-your-own-writes problem, usually solved by reading the item itself from the database on the detail page rather than from the index.

### Q296. Two stores in one application `[T]`

Spring Data's repository scanners are per-store, and each one is greedy. With `OrderRepository extends JpaRepository` and `AuditRepository extends MongoRepository` in the same package, **both** scanners try to claim both interfaces. Depending on version and ordering you get either a startup failure - along the lines of "no property found" or an inability to determine the module - or the quieter disaster where an interface is bound to the wrong store and queries go somewhere unexpected.

Spring Data uses strict, then relaxed, then finally ambiguous resolution: strict mode only claims an interface if the repository type is store-specific, or the domain type carries a store-specific annotation (`@Document` versus `@Entity`), or the package is exclusively configured for one store. Multiple stores means you must be explicit:

```java
@Configuration
@EnableJpaRepositories(basePackages = "com.acme.orders.jpa",
                       entityManagerFactoryRef = "orderEmf",
                       transactionManagerRef = "orderTx")
@EnableMongoRepositories(basePackages = "com.acme.audit.mongo")
class PersistenceConfig { }
```

The conventions I enforce: **separate packages per store, never mixed**; store-specific base interfaces (`JpaRepository`, not `CrudRepository`) so strict resolution succeeds; entities annotated for exactly one store; and explicit `basePackages` on every `@Enable*Repositories`. Transactions do not span the two - `@Transactional` picks one manager (Q66), and the other store's write is outside it, so the same idempotency and outbox reasoning applies.

### Q297. Redis repositories, Spring Session and Security

`@RedisHash("session")` with `CrudRepository` maps an object to a Redis hash and gives you repository semantics over Redis. The mechanics people get wrong:

- **Expiry is per object**, via `@TimeToLive` or the `timeToLive` attribute, and Redis expires the hash. Spring Data additionally maintains a **phantom copy** with a slightly longer TTL plus keyspace-notification listeners, so it can clean up secondary indexes when the primary key expires. Keyspace notifications must be enabled on the server (`notify-keyspace-events Ex`) or indexes leak entries pointing at keys that no longer exist.
- **Secondary indexes** come from `@Indexed` and are implemented as Redis sets that Spring Data maintains on write. They are not free, they are not transactional with the primary write, and they are the main reason a Redis repository is more expensive than a plain `RedisTemplate` call.

Cache versus store of record is the framing (Q140): as a repository you are treating Redis as a store, so you must answer what happens when it restarts without persistence, or fails over and loses the tail of the replication stream. Fine for sessions and ephemeral state; not fine for anything you cannot regenerate.

**Spring Session with Redis** (`@EnableRedisHttpSession`) replaces the container's `HttpSession` with a Redis-backed one via `SessionRepositoryFilter`, which must be ordered **before** the Spring Security filter chain so that `HttpSessionSecurityContextRepository` reads and writes the shared session (Q148). Boot orders it correctly by default; hand-registering the filter is how people break it. What you gain is stateless application instances - no sticky sessions, no session loss on deploy - plus centralized invalidation and concurrency control. What you pay is a Redis round trip on every request that touches the session, and a hard dependency: Redis down means nobody is logged in. Keep the session small (an ID and authorities, not a shopping cart), set an idle timeout, and use `flushMode` deliberately.

---

## 19. Spring Cloud Kubernetes and the development loop

### Q298. ConfigMaps and Secrets as a `PropertySource`

`spring-cloud-starter-kubernetes-client-config` registers a `PropertySource` during bootstrap (or via `spring.config.import: kubernetes:` in the `ConfigData` model, Q27) that reads a ConfigMap named after `spring.application.name` in the pod's namespace and contributes its entries to the `Environment`. Keys can be flat (`key: value` pairs become properties directly) or a whole `application.yaml` entry that is parsed as YAML. Secrets work the same way, base64-decoded, and are disabled by default because reading them requires broader RBAC.

The pod needs a `Role` granting `get`, `list` and `watch` on `configmaps` (and `secrets` if enabled), bound to its service account:

```yaml
rules:
  - apiGroups: [""]
    resources: ["configmaps", "secrets"]
    verbs: ["get", "list", "watch"]
```

The point I make when this comes up in design review: this is one of two ways to get a ConfigMap into an application, and the other one - mounting it as a volume or projecting it into environment variables - needs **no permissions, no library and no API dependency**, and Boot reads a mounted file natively through `spring.config.import: configtree:/etc/config/`. I only take the API-based route when I actively want dynamic reload; otherwise the mount is strictly simpler and does not give the pod read access to the namespace's secrets.

### Q299. Reload modes `[T]`

`spring.cloud.kubernetes.reload` has two detection modes and three strategies.

Detection: `polling` re-reads the ConfigMap on an interval (works everywhere, costs API calls); `event` watches the Kubernetes API for changes (immediate, but needs `watch` permission and a resilient reconnect, and a watch that silently dies stops all updates with no symptom).

Strategies, in increasing order of blast radius:

- `refresh` - fires `RefreshEvent`, rebinding `@ConfigurationProperties` and clearing `@RefreshScope` beans (Q38, Q206). Cheap, but only affects things that are actually refreshable.
- `restart_context` - closes and restarts the application context in place. Everything is rebuilt; connections are re-established; it takes real time and the pod stays `Ready` while doing it.
- `shutdown` - exits the process and lets Kubernetes restart the pod, which is a full rolling restart if the ConfigMap is shared.

In production I default to **reload disabled**. The reasons are the ones that matter at 3am: a ConfigMap edit becomes an untracked, un-reviewed change that takes effect immediately across every pod simultaneously, with no rollout, no canary and no `kubectl rollout undo`. Pods that started at different times can hold different configurations, so behavior depends on pod age - the worst kind of bug to reproduce. Only a subset of state actually re-reads, so you get a half-applied configuration (a changed pool size that the existing `DataSource` ignores, for instance). And an operator editing a ConfigMap does not expect to restart a fleet, which `shutdown` does.

What I do instead: treat configuration as a deployment. Change the ConfigMap in Git, add a checksum annotation to the pod template so the change triggers a normal rolling update, and get a progressive rollout with health gating and a rollback path for free. I enable `refresh` only for a narrow, explicitly refreshable set - feature flags and log levels - and even those are better served by a purpose-built flag system.

### Q300. `DiscoveryClient` versus Service DNS

`spring-cloud-kubernetes-discovery` implements `DiscoveryClient` against the Kubernetes API, listing `Services` and `Endpoints` so `@LoadBalanced RestTemplate`, WebClient and OpenFeign can resolve `http://order-service/...` client-side and Spring Cloud LoadBalancer can pick an instance.

Plain Service DNS gives you the same name resolution with no library: `http://order-service.namespace.svc.cluster.local`. kube-proxy load-balances at layer 4 and the platform manages endpoint health.

What the API-based client gains you: individual pod IPs rather than one virtual IP, so client-side algorithms such as zone affinity, least-connections or weighted routing become possible; access to service and pod metadata for routing decisions; and for HTTP/2 or gRPC, avoiding the well-known problem that layer-4 balancing pins a long-lived connection to one pod and never rebalances.

What it costs: RBAC to list services and endpoints across namespaces (a meaningful widening of what a compromised pod can see), a hard runtime dependency on the API server from every application pod, API server load that scales with your fleet, and a second source of truth for health that can disagree with the platform's.

My default is **Service DNS**, consistent with Q220: on Kubernetes the platform already does discovery, and re-implementing it in the application is the classic Spring Cloud over-adoption. I make an exception for gRPC or long-lived HTTP/2 connections, or where zone-aware routing has a measurable cost benefit - and then I would look hard at whether a service mesh solves it outside the application first.

### Q301. Leader election versus ShedLock

They solve overlapping problems with different failure modes.

**ShedLock** is a mutual-exclusion lock on a *job execution*, stored in a database, Redis or Mongo. Every instance still runs its scheduler; the first to acquire the lock executes and the rest skip. `lockAtMostFor` must exceed the worst-case runtime, because that is the safety valve if the holder dies without releasing. Failure modes: if the job runs longer than `lockAtMostFor`, a second instance starts while the first is still working - concurrent execution, which is exactly what you were preventing. Clock skew across instances affects the window. And the lock store becomes a dependency of your scheduling.

**Leader election** (Spring Cloud Kubernetes, or Integration's `LockRegistryLeaderInitiator`) elects one instance as leader for a *period*, via a `ConfigMap` or `Lease` object; the leader runs all leader-scoped work and others stay idle. Failure modes: a leader partitioned from the API server may still believe it is leader while a new one is elected - two leaders briefly, unless the work is fenced by a token. Failover takes as long as the lease duration, so a scheduled job can be missed entirely during a handover, not merely delayed. And leadership is coarse-grained: one leader takes *all* the leader work, which concentrates load.

How I choose: **ShedLock for periodic jobs**, because the granularity is per job and a missed run is simply the next tick; **leader election for continuous singleton work** such as an outbox relay or a queue poller that must run somewhere at all times. And the strongest answer for a Kubernetes estate is often neither - a `CronJob` (Q290) moves the concern to the platform, which already solves it.

Whichever you choose, the job itself must tolerate double execution. Every one of these mechanisms has a split-brain window; the lock reduces the probability, and idempotency is what makes it safe.

### Q302. DevTools `[T]`

`spring-boot-devtools` runs the application under **two classloaders**: a base loader holding unchanging jars from third-party dependencies, and a restart loader holding your classes. When the file watcher sees a recompiled class it throws away only the restart loader and re-creates the context, so restart is far faster than a JVM start because the dependency jars are never re-read. It also disables template and static-resource caching, enables `LiveReload`, and sets a batch of "development-time" properties including verbose condition evaluation.

It must never reach production for three separate reasons, and the first two are security issues, not conveniences:

1. **The remote debug tunnel** (`spring.devtools.remote.secret`) exposes an endpoint that accepts class bytes and loads them. That is remote code execution with a shared-secret gate.
2. **Development defaults are unsafe defaults** - caching disabled, more verbose error output, condition reports and configuration on the wire.
3. **Restart is not a deployment model.** Two classloaders means `instanceof` and identity comparisons can fail across the boundary, static caches behave oddly, and memory grows over restarts.

Boot defends against this: DevTools is disabled automatically when the application is started from a fully packaged jar, and the Maven and Gradle plugins mark it `optional`/`developmentOnly` so it does not propagate transitively. Those defaults are easy to defeat by declaring the dependency in `compile` scope, so I also fail the build if it appears in the production dependency tree.

What replaced it as the better loop in Boot 3.1+: **Docker Compose support** (`spring-boot-docker-compose`) starts the `compose.yaml` next to your project when the app starts and wires the connection details in automatically, and **`@ServiceConnection` with Testcontainers at development time** does the same from a `TestApplication` main class launched via `bootTestRun`. Both remove the real friction, which was never restart speed - it was standing up a database, Kafka and Redis that match production. Combined with a modern JVM's class-data sharing and a fast context, plain restart is usually good enough, and IDE-driven hot swap covers method-body edits without any of DevTools' risk.

---

## 20. Spring AI platform surface and MCP

### Q303. `ChatModel`, `EmbeddingModel` and `ImageModel`

The layering is deliberate. `ChatModel` is the **portable, low-level port**: `call(Prompt) -> ChatResponse`, plus `stream(Prompt) -> Flux<ChatResponse>`. It knows about messages, options, token usage and finish reasons, and each provider ships one implementation. `EmbeddingModel` is the same idea for vectors (`embed(Document)`, batching, dimensions), and `ImageModel`, `TranscriptionModel` and `ModerationModel` fill out the other modalities.

`ChatClient` is the **fluent application-facing API built on top of `ChatModel`**, and it is where advisors, prompt templates, structured output conversion, tool callbacks and chat memory live (Q237-243). Most application code should use it.

When I go direct to the model:

- Building infrastructure rather than a feature - a custom advisor, an evaluator, or a batch pipeline where the advisor chain is overhead.
- Bulk embedding, where I want explicit batch control and to observe token usage per batch. `VectorStore` calls `EmbeddingModel` for me, but a backfill of a million documents needs rate limiting and checkpointing that belongs in my code.
- Testing, where a stub `ChatModel` is the cleanest seam - it is a one-method interface, so no mocking framework is needed.

The rule I apply in code review: features depend on `ChatClient`, platform code depends on `ChatModel`, and nothing outside a configuration class depends on a provider type.

### Q304. Where portability breaks `[T]`

The interface is portable; the behavior is not. Swapping the starter compiles and then behaves differently, which is worse than failing.

Where it breaks:

- **`ChatOptions` is the leak.** The common interface covers temperature, max tokens, top-p and stop sequences. Everything that differentiates a provider is in the provider-specific subtype - `OpenAiChatOptions` for response format, seed, logit bias, reasoning effort and parallel tool calls; `AnthropicChatOptions` for thinking budget and top-k; Bedrock and Vertex for their own guardrail and safety-filter settings. The moment you set one, your configuration is provider-specific even though your code still says `ChatClient`.
- **Prompts are not portable.** System-message handling differs (Anthropic treats it as a distinct parameter, some models want instructions in the user turn), and a prompt tuned on one model regresses on another. This is the largest practical cost and it never shows up in a compile.
- **Tool calling differs** in schema strictness, parallel call support and how a refusal is signalled.
- **Structured output** - some providers offer a native JSON or schema mode, and Spring AI's converter falls back to instructing the model and parsing, which has a materially different failure rate.
- **Multimodal, token accounting, rate-limit semantics, error taxonomies and finish reasons** all vary, and retry and cost logic depend on all of them.

So my position is that Spring AI's portability is real at the **structural** layer - one programming model, one observability story, one set of abstractions for tools, memory and vector stores - and mostly illusory at the behavioral layer. That is still worth a great deal: switching providers becomes a re-evaluation exercise rather than a rewrite. But I plan for it explicitly - provider-specific options isolated in configuration classes, an evaluation suite that is run against any candidate model before a switch, and a documented primary and fallback rather than a vague claim that we can change any time.

### Q305. The document ETL pipeline and reindexing

The pipeline is three roles. **Readers** produce `Document`s (`PagePdfDocumentReader`, `TikaDocumentReader`, `JsonReader`, `MarkdownDocumentReader`). **Transformers** reshape them - `TokenTextSplitter` for chunking, `KeywordMetadataEnricher` and `SummaryMetadataEnricher` for adding retrievable metadata, plus your own for cleaning. **Writers** persist - `VectorStore.add()` embeds and stores, or `FileDocumentWriter` for inspection.

```java
var docs = new TikaDocumentReader(resource).read();
var chunks = new TokenTextSplitter(800, 350, 5, 10000, true).apply(docs);
chunks.forEach(d -> d.getMetadata().putAll(Map.of("source", name, "version", "v3")));
vectorStore.add(chunks);
```

Two things determine retrieval quality far more than the model does: **chunk size and overlap**, and **the metadata you attach**, because metadata filters are what make multi-tenant or permission-scoped retrieval possible at all.

Reindexing without a gap uses the same alias reasoning as Q294, but vector stores rarely have aliases, so the version lives in metadata or in the collection name:

1. Write new chunks with `version: v3` in their metadata alongside the existing `v2`.
2. Keep the retrieval filter pinned to `v2` while the backfill runs, so users never see a half-populated corpus.
3. Evaluate `v3` against a fixed question set - the same retrieval quality metrics you would use for any change.
4. Flip the filter to `v3` in configuration, which is instant and reversible.
5. Delete `v2` after a soak period.

Alternatively, index into a second collection and switch the `VectorStore` bean's target. Either way the principles are the same: **the vector store is a derived index, never the source of record** (same as Q295), the source documents and their checksums live somewhere you can re-run from, and a re-embedding must be assumed whenever the embedding model or its version changes - vectors from different models are not comparable, so a model upgrade is always a full reindex.

### Q306. MCP in Spring AI

Model Context Protocol standardizes how a model-facing application discovers and calls external capabilities. It has three primitives - **tools** (callable functions), **resources** (readable context) and **prompts** (reusable templates) - carried over JSON-RPC.

Spring AI ships both sides. `spring-ai-starter-mcp-client` auto-configures clients from properties and exposes their tools through `ToolCallbackProvider`, so they enter the same tool-calling path as in-process tools (Q240):

```java
ChatClient.builder(chatModel)
    .defaultToolCallbacks(mcpToolCallbackProvider)
    .build();
```

`spring-ai-starter-mcp-server-webmvc` (or the WebFlux variant) turns your own `@Tool`-annotated beans into an MCP server other applications can consume.

Transports: **stdio**, where the client launches the server as a child process and speaks over its pipes - suitable for local, desktop and CLI use, and a poor fit for a multi-instance Kubernetes deployment; and **HTTP with Server-Sent Events** (with the newer streamable-HTTP transport superseding the original SSE pairing), which is what you use for a networked server. In a Spring service I use HTTP transports exclusively - stdio means every pod spawns and supervises child processes, with no independent scaling, health checking or authentication story.

Discovery is at runtime: on connect the client calls `tools/list` and receives names, descriptions and JSON schemas, which are converted into `ToolCallback`s and advertised to the model. That is the power and the risk - **the tool surface is defined by a remote party and can change without your release**. Clients cache the listing and support change notifications, so a server can add tools to a running client.

### Q307. MCP servers versus in-process tools `[A]`

I decide on ownership and blast radius, not on novelty.

**In-process `@Tool` methods** for anything that is core to this service: reading its own database, calling its own domain logic, invoking a service it already depends on. The call is a method call, the security context is right there, the latency is microseconds, it is trivially testable, and there is no new deployable. This covers most of what a typical enterprise AI feature needs, and it is where I start.

**An MCP server** when at least one of these holds: the capability is owned by another team and should evolve on their release cycle; it is reused by several AI applications and duplicating the tool definitions would guarantee drift; it is a third-party integration where somebody already publishes a server; or it needs a different runtime, language or scaling profile. The value is a versioned, discoverable capability boundary - the same argument as extracting a service, and it deserves the same scepticism.

The security boundary differs sharply, and this is the part interviewers are actually testing:

- **In-process**, the tool runs with the application's full authority. The discipline is that the tool method enforces authorization itself - `@PreAuthorize` on the tool, the tenant taken from the `SecurityContext` and never from a model-supplied argument, and every parameter validated. **Treat tool arguments as untrusted user input**, because a prompt-injected document can choose them.
- **With MCP**, you additionally have a network boundary and a third party. Every model-facing risk above still applies, plus: the server must authenticate the caller (OAuth2 client credentials, not a shared token in a config file) and enforce its own authorization rather than trusting the client; the client must pin which servers it will connect to, with no dynamic registration from model output; tool descriptions arriving from a remote server are **text that reaches the model's context**, so a malicious or compromised server can inject instructions - a genuinely new attack surface with no in-process equivalent; and a changed tool schema can silently alter behavior between deployments, so I pin versions and diff the tool listing in CI.

My default: build in-process, extract to MCP when a second consumer appears, and never connect to a third-party MCP server that has not been reviewed - with human confirmation required for any tool that writes, spends or sends.

---

Q258-262 are worked as full design exercises in [scenario-questions.md](scenario-questions.md), which also covers the production incidents and leadership scenarios. Q308-313 are story questions - use STAR-L and your own experience.
