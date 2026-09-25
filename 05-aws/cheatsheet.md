# AWS Cheatsheet

Fast revision. Serverless-first: Lambda, API Gateway, EventBridge, Step Functions, DynamoDB and S3 unless another service is named. Assumes [../01-java/cheatsheet.md](../01-java/cheatsheet.md) and [../03-microservices/cheatsheet.md](../03-microservices/cheatsheet.md).

Every number here is a **default at the time of writing**. In an interview, say "the default is X, and it is adjustable" - quoting a figure as immutable is the tell of someone who read it rather than hit it.

---

## The serverless contract

The seven properties every design in this pack is an implementation of:

1. **Compute is billed per millisecond of work**, so idle costs nothing and waste is visible per invocation.
2. **Concurrency is the currency** - `concurrency = arrival_rate x duration`. Every capacity conversation reduces to this identity.
3. **Every quota is per account, per region**, and quotas are shared between unrelated workloads.
4. **Delivery is at-least-once everywhere**, so **idempotency is a precondition, not a refinement**.
5. **Retries exist at every hop**, so the total retry topology must be designed, not inherited.
6. **State lives in a managed store**, never in the execution environment - the environment is a cache, not memory.
7. **The event is the contract**, not the function. Producers publish facts; consumers subscribe.

---

## Accounts and Organizations

| Boundary | What it isolates |
| --- | --- |
| **Account** | Quotas, blast radius, billing, most IAM. The only *hard* boundary. |
| **OU + SCP** | Permission ceiling - SCPs subtract, never grant. |
| **VPC** | Network reachability only. |
| **IAM role** | Identity within an account. |

**Minimum account split**: prod / non-prod / security-tooling / log-archive / shared-services. Split further when quotas collide, blast radius matters, or billing must be attributable.

**SCPs** apply to everything in the account **except the management account** - so never run workloads there. **Effective permission = identity policy ∩ resource policy ∩ SCP ∩ permission boundary ∩ session policy.** An explicit `Deny` anywhere wins.

**Control Tower** = landing zone with guardrails, drift detection and Account Factory. Worth it above ~5 accounts.

---

## Workload identity

| Mechanism | Use |
| --- | --- |
| **Execution role** | Lambda / ECS task / EKS Pod Identity. The only credential a workload should have. |
| **Resource policy** | Cross-account access without a role assumption at the caller. Both sides must allow. |
| **`sts:AssumeRole` chain** | Cross-account work; max chained session 1 hour. |
| **External ID** | Third-party access. Defeats the confused deputy. |
| **OIDC federation** | CI to AWS with no long-lived keys. |
| **Session policy** | Downscope at assume time - the per-tenant isolation lever. |

**IAM users with access keys are a finding**, not a design. If one exists, it needs a migration ticket.

**Cross-account rule of thumb**: same-account access → identity policy alone. Cross-account → identity policy **and** resource policy. KMS is the classic trap: the key policy must also allow it.

---

## VPC, and when Lambda needs one

**A Lambda does not need a VPC** unless it must reach a private resource (RDS, ElastiCache, an on-premises system, a private ALB). VPC-attached functions have **no internet access** without a NAT gateway or VPC endpoint - and that is the surprise that breaks the first deploy.

Since Hyperplane ENIs, VPC attachment costs **~1 s of one-time ENI setup per subnet/security-group combination**, not per cold start. The old "10-second VPC cold start" answer is out of date; say so.

| Egress option | Cost shape |
| --- | --- |
| **NAT gateway** | ~$0.045/h **per AZ** + **~$0.045/GB processed** - the processing charge is what surprises people |
| **Gateway endpoint** (S3, DynamoDB) | **Free**. Always use it. |
| **Interface endpoint / PrivateLink** | ~$0.01/h per AZ per endpoint + ~$0.01/GB |

**Three AZs of NAT ≈ $100/month before a byte moves.** A chatty S3 workload through NAT instead of a gateway endpoint is one of the most common six-figure mistakes.

**Data transfer**: same-AZ private IP free; **cross-AZ $0.01/GB each way**; cross-region ~$0.02/GB; internet egress ~$0.09/GB; **CloudFront to origin free**.

---

## Edge and entry

| Option | Cost / 1M | Use when |
| --- | --- | --- |
| **HTTP API** | ~$1.00 | Default. JWT auth, proxy integration, lower latency. |
| **REST API** | ~$3.50 | You need request validation, WAF directly, API keys/usage plans, private endpoints, caching. |
| **WebSocket API** | ~$1.00 + connection-minutes | Bidirectional. |
| **ALB** | ~$16-22/month + LCU | Steady high volume; cheaper past ~$X/month crossover. |
| **Function URL** | free | Internal, single function, IAM or no auth. |
| **AppSync** | ~$4 | GraphQL, subscriptions, per-field resolvers. |

**CloudFront in front of everything public**: TLS terminates at the edge, requests travel the AWS backbone, and **origin egress is free** - it often pays for itself on data transfer alone.

**Timeouts**: API Gateway integration timeout is **29 seconds** (now raisable on REST, but assume 29 in an interview and design for it). ALB default idle 60 s. Anything longer must be asynchronous with a job ID.

**Authorizer caching** is the difference between one extra invocation per request and one per five minutes - check the cache key is not the full request.

---

## The Lambda execution model

```
INIT   (up to 10 s; static init, constructor, /tmp, SDK clients)  -- billed since 2023
INVOKE (handler; up to 900 s)
SHUTDOWN (up to 2 s, extensions only)
```

**Cold start = INIT.** `Duration` **excludes** `InitDuration`, so cold starts are invisible on the default dashboard. Always graph `Duration + InitDuration` at p99.

| Concept | Meaning |
| --- | --- |
| **Reserved concurrency** | Both a **floor** (guaranteed) and a **ceiling** (hard cap). Subtracts from the account pool. Free. |
| **Provisioned concurrency** | Pre-initialized environments. Costs even when idle. Kills cold starts. |
| **Account concurrency** | Default **1,000** per region, shared by every function. Adjustable. |
| **Burst rate** | Scales in increments (**1,000/10 s** per function in most regions) - a separate limit from the ceiling. |

**`concurrency = requests_per_second x duration_seconds`.** 500 rps at 200 ms = 100 concurrent. Learn to do this out loud.

**Sync vs async on throttle**: synchronous → **429 to the caller, request lost**. Asynchronous → Lambda retries for **up to 6 hours** with backoff, then DLQ/on-failure destination.

**Memory is the CPU dial**: 1,769 MB ≈ 1 vCPU. More memory often costs *less* because duration falls faster than price rises. Use Lambda Power Tuning; never leave a CPU-bound Java function at 512 MB.

**Java on Lambda**: `INIT` dominated by JVM start plus framework scanning. Fixes in order - **SnapStart** (free, ~10x improvement), avoid classpath scanning (constructor injection, no reflection-heavy DI), **priming** in the init phase, then ahead-of-time (GraalVM native / custom runtime).

**SnapStart traps**: the snapshot is restored many times, so anything initialized once and assumed unique or fresh breaks - **seeded RNG produces identical sequences**, cached credentials expire, open connections are dead. Use CRaC `afterRestore` hooks.

**Limits**: payload **6 MB sync / 256 KB async**; `/tmp` 512 MB (up to 10 GB); ZIP 50 MB zipped / 250 MB unzipped; **container image 10 GB**; env vars 4 KB total; timeout 900 s.

---

## Compute selection

| Choose | When |
| --- | --- |
| **Lambda** | Event-driven, spiky, < 15 min, per-request isolation acceptable, no persistent connections |
| **Fargate** | Long-running, persistent connections, > 15 min, large images, steady load where Lambda's per-request price loses |
| **App Runner** | A container that is a web service and nothing more |
| **EKS** | You have Kubernetes expertise and multi-cloud/portability requirements, or need the ecosystem |
| **EC2** | Licensing, GPUs, custom kernels, or a lift-and-shift |

**Where Lambda is the wrong answer**: sustained high-throughput steady load (the always-on container is cheaper), workloads needing warm caches or connection pools, tasks over 15 minutes, anything needing more than 10 GB memory or GPU, and latency floors where a p99 cold start is unacceptable and provisioned concurrency costs more than a container.

**The crossover** is roughly: if a function is running more than ~40-50 percent of the time, price out Fargate.

---

## The event-driven backbone

| Service | Model | Ordering | Retention | Use |
| --- | --- | --- | --- | --- |
| **SQS Standard** | Queue, at-least-once | None | 14 days max | Buffering, backpressure, work distribution |
| **SQS FIFO** | Queue, exactly-once dedup (5 min) | Per message group | 14 days | Ordering per entity; 300 tps/group (3,000 batched) |
| **SNS** | Pub/sub push | None | None (retry only) | Fanout to a few known subscribers |
| **EventBridge** | Bus, content-based routing | None | Archive + replay | **Domain events; the default** |
| **Kinesis** | Log, shard-ordered | Per partition key | 24 h - 365 d | High-throughput ordered streams, multiple readers, replay |
| **DynamoDB Streams** | Log of item changes | Per partition key | 24 h | Outbox, CDC, projections |
| **MSK** | Kafka | Per partition | Configurable | Existing Kafka estate, log compaction, ecosystem |

**EventBridge vs SNS**: EventBridge for **routing on content** with rules, schema registry, archive/replay and third-party targets - ~$1/M events. SNS for **high-throughput cheap fanout** with lower latency and no filtering complexity. EventBridge's ~0.5 s typical latency and 24-hour retry matter; SNS is faster.

**EventBridge limits**: default **10,000 PutEvents/s** (region-dependent), **5 targets per rule**, 256 KB event size, 300 rules per bus (adjustable). Archive + replay is the recovery tool - and a replay is a **production write**.

**Kinesis**: 1 MB/s or 1,000 records/s **in** per shard; 2 MB/s **out** shared, or **enhanced fan-out** for 2 MB/s per consumer. Hot partition key = one hot shard = the classic lag incident.

**Choose the transport by the question it answers**: "someone should do work" → queue. "this happened" → event bus. "here is an ordered history" → stream.

---

## Event source mappings

| Setting | Why it matters |
| --- | --- |
| `BatchSize` | Cost and throughput. Batch of 1 = 10x the invocations of batch of 10. |
| `MaximumBatchingWindowInSeconds` | Trades latency for fewer invocations. |
| `FunctionResponseTypes: ReportBatchItemFailures` | **Return partial failures** - otherwise one bad record retries the whole batch. |
| `MaximumRetryAttempts` | Streams default **-1 = forever** → a poison record blocks the shard permanently. |
| `MaximumRecordAgeInSeconds` | The other half of the poison-pill defence. |
| `BisectBatchOnFunctionError` | Isolates the bad record instead of dropping the batch. |
| `DestinationConfig.OnFailure` | Where discarded records go. Without it the loss is silent. |
| `MaximumConcurrency` (SQS) | **Backpressure without throttling.** Use this, not reserved concurrency, to protect a downstream. |
| `FilterCriteria` | Filter before invoke - you are not billed for filtered events. |

**Visibility timeout ≥ 6x function timeout** for SQS. Shorter → the message is redelivered while still being processed → concurrent duplicates and a receive count that silently climbs to `maxReceiveCount`.

**Scaling**: SQS pollers add **60 concurrent invocations per minute** up to 1,000 (or `maximumConcurrency`). Kinesis/DynamoDB: **one concurrent invocation per shard**, or per shard x parallelization factor (max 10).

**Idempotency** = a conditional write on a business key with a TTL. `PutItem` with `attribute_not_exists(pk)`, or Powertools' idempotency utility. Without it, at-least-once delivery is a correctness bug waiting for a retry.

**Alarm on `IteratorAge` (streams) and `ApproximateAgeOfOldestMessage` (queues)** - not on depth. Age tells you the drain rate is insufficient; depth does not.

---

## Step Functions

| | Standard | Express |
| --- | --- | --- |
| Duration | 1 year | 5 minutes |
| Pricing | **per state transition (~$25/M)** | per invocation + GB-s (~10-100x cheaper at volume) |
| Execution semantics | exactly-once | at-least-once (async) |
| History | full, in the console, 90 days | CloudWatch Logs only |
| Use | business processes, sagas, human steps, anything you must audit | high-volume short orchestration, stream processing |

**Standard's cost is transitions, so the cost lever is step count** - and at high volume Standard frequently dominates the whole bill. Nested Express inside Standard is the standard optimization.

**Direct SDK integrations** remove Lambdas for pure API calls - fewer functions, fewer cold starts, but the retry and error mapping moves into ASL.

**`.sync` integrations** (Textract, Batch, ECS, Glue, a nested state machine) wait for completion without a poller. **`.waitForTaskToken`** is the callback pattern - human approval, third-party webhook - with a heartbeat and a timeout, always.

**Distributed Map**: up to 10,000 concurrent child executions over S3 objects or a manifest; cap `MaxConcurrency` or it becomes the account-wide concurrency incident.

**Deterministic execution names** (`order-{orderId}`) make duplicate starts impossible - a free idempotency mechanism for Standard.

**Sagas**: `Catch` on each step routing to compensating states in reverse order. Compensation must be idempotent, and there must be a terminal manual-intervention state that is alarmed.

**Workflow vs code**: use a state machine when the process is long-running, has human steps, needs compensation, needs an audit trail, or must be queryable. Use code when it is a fast sequence of calls in one transaction boundary - a state machine for three sequential calls is cost and latency for nothing.

---

## Data for serverless

**DynamoDB**

- **Item 400 KB**; partition **3,000 RCU / 1,000 WCU**; **query result page 1 MB**; `BatchGetItem` 100 items / 16 MB; `TransactWriteItems` **100 items, 2x cost**; scan is a full-table read.
- **Single-table design**: generic `PK`/`SK`, entity prefixes (`ORDER#123`), overloaded GSIs, item collections for locality. Justified by access-pattern locality, not by fashion - if the entities are unrelated, separate tables are clearer.
- **On-demand vs provisioned**: on-demand for unpredictable or spiky (scales to **2x previous peak** instantly, more with warming); provisioned + auto-scaling for steady, predictable load at ~1/7 the per-request price. Auto-scaling reacts in **minutes** - it does not save you from a spike.
- **Hot partition**: identified with Contributor Insights. Fixed by write sharding, a better key, or caching. Adaptive capacity helps but is not a licence to ignore key design.
- **GSI**: eventually consistent, **its own capacity** - a throttled GSI throttles the base table's writes. LSI: strongly consistent, same partition key, must exist at creation, 10 GB per collection.
- **Streams** for outbox, projections and CDC. `NEW_AND_OLD_IMAGES` to make the event self-contained.
- **TTL** is eventual (up to 48 h) and free; it emits a stream record.

**Relational under serverless**

- Each execution environment is its own process with its own pool → **connections = concurrency x pool size**. 600 concurrent x pool of 10 = 6,000 connections. Aurora's `max_connections` is in the hundreds.
- **Pool size 1-2 per environment.** A Lambda serves one request at a time.
- **RDS Proxy** decouples connection count from concurrency and holds the pool across cold starts. Watch `DatabaseConnectionsCurrentlySessionPinned` - session-level `SET` statements defeat multiplexing.
- **Aurora Serverless v2** scales in 0.5 ACU steps, minimum 0 (with a resume delay) - good for spiky relational; still needs a proxy under Lambda.
- **Data API** removes connections entirely; higher per-call latency, HTTP semantics.

**Caching**: **DAX** for DynamoDB (microsecond reads, write-through, in-VPC, item/query cache) versus **ElastiCache** for general-purpose. Both put a VPC in the path of your function - decide whether that is worth it.

---

## S3 as an architectural tier

- **3,500 PUT / 5,500 GET per second per prefix**, and prefixes partition automatically - the old "randomize your key prefix" advice is obsolete but still asked about.
- **Strong read-after-write consistency** for all operations since 2020.
- **Multipart** above ~100 MB; **required** above 5 GB. Always add a lifecycle rule to **abort incomplete multipart uploads** - otherwise you pay for invisible parts forever.

| Class | Use | Gotcha |
| --- | --- | --- |
| Standard | Hot | - |
| Intelligent-Tiering | Unknown access pattern | Small monitoring fee per object; **the safe default** |
| Standard-IA | Known infrequent | 30-day minimum, 128 KB minimum, retrieval fee |
| One Zone-IA | Regenerable | Single AZ |
| Glacier Instant | Archive with instant access | 90-day minimum |
| Glacier Flexible | Archive, minutes-hours | 90-day minimum |
| Deep Archive | Compliance, 12 h | 180-day minimum |

**Transitions cost money per object** - for millions of small objects, lifecycle transitions can cost more than the storage saved. Do the arithmetic.

**Events**: S3 → EventBridge (preferred; filtering, multiple targets) or direct to Lambda/SQS/SNS. **Never write into the bucket that triggers you** - that is the recursive-invocation bill. Separate buckets or scoped prefixes, and rely on `RecursiveInvocationsDropped` as a safety net, not a design.

**Presigned URLs** move bytes out of your compute path entirely - the function signs, the client transfers. Use **presigned POST** with a policy for uploads to constrain size and content type.

**Object Lock** (Compliance mode) is what makes a retention obligation defensible; put the bucket in a separate account with an SCP.

---

## Observability

- **CloudWatch metrics**: standard 1-minute, detailed/custom to 1 second. Custom metrics via the API are ~$0.30/metric/month and cost adds up fast; **EMF** (embedded metric format) emits metrics from a log line at zero API cost - use it.
- **Logs**: ~$0.50/GB ingested, ~$0.03/GB stored. **Set a retention period on every log group** - the default is "never expire", and forgotten log groups are one of the most common silent costs.
- **Logs Insights** is charged per **GB scanned**, so retention and structure control query cost.
- **Structured JSON logging always**, with the **correlation ID and trace ID on every line**. Powertools for Java gives logger, tracer, metrics and idempotency in one dependency - use it rather than hand-rolling.
- **X-Ray** for the distributed trace; **sample** (default 1 req/s plus 5 percent). ADOT if you need OpenTelemetry and vendor portability.
- **Lambda Insights** for memory and CPU per invocation; **Contributor Insights** for hot keys.
- **The four metrics for every function**: `Errors`, `Throttles`, `Duration` **p99 including `InitDuration`**, and `ConcurrentExecutions`. For every async consumer, add the **age** metric.

**Telemetry cost is often 10-30 percent of a serverless bill.** Sample traces, set retention, use EMF, and log at INFO not DEBUG in production.

---

## Reliability, quotas and failure modes

| Where | Default | Note |
| --- | --- | --- |
| Lambda concurrency | 1,000/region | Shared, adjustable |
| Lambda burst | 1,000 per 10 s | Separate limit |
| API Gateway | 10,000 rps, 5,000 burst | Per account per region |
| Step Functions | 2,000 executions/s start (Standard) | Transitions also limited |
| DynamoDB | 40,000 RCU/WCU per table (on-demand default) | Adjustable |
| SQS | Effectively unlimited standard; FIFO 300 tps/group | |
| KMS | ~10,000-50,000 req/s by region and key type | The forgotten one in a failover |

**Quotas are per account per region** - which is why a standby region at defaults fails under real traffic. Check parity with ARC readiness checks or a scheduled Service Quotas diff.

**Retry topology**: count the layers. SDK (3 attempts) x Lambda async (2 retries) x event source mapping x the caller's own retry = a **multiplicative amplification** that turns a slow downstream into a self-inflicted DDoS. Design retries at exactly one layer per hop, with **exponential backoff and jitter** and a **budget** (retries capped as a fraction of requests).

**Timeout budget**: each hop's timeout must be strictly less than its caller's remaining budget. API Gateway 29 s → Lambda 25 s → downstream 5 s with 2 retries. A Lambda timeout longer than its caller's is wasted money on a response nobody will read.

**Circuit breakers** matter more in serverless because there is no shared process state - keep the breaker state in DynamoDB or accept per-environment breakers.

| DR pattern | RTO | RPO | Cost |
| --- | --- | --- | --- |
| Backup & restore | hours | hours | lowest |
| Pilot light | 10s of min | minutes | low - **usually right for serverless** |
| Warm standby | minutes | seconds | medium |
| Active-active | ~0 | ~0 | highest, plus permanent complexity |

**A DR plan that has not been tested at full traffic has not been tested.**

---

## Multi-region

- **DynamoDB global tables**: multi-active, **last-writer-wins** on the item, replication lag typically < 1 s. LWW silently discards a concurrent write - if the data has business meaning (a balance, an inventory count), you need a conflict strategy, not a resolution policy.
- **Route 53**: latency, geolocation, weighted, failover routing; health checks. **Client DNS caching means failover is not instant** - budget for TTL plus resolver behaviour. **Global Accelerator** for anycast IPs and sub-minute failover without DNS.
- **Aurora Global Database**: sub-second replication, **single writer**, managed unplanned failover in ~1 minute with potential data loss; planned switchover is lossless.
- **S3 CRR/SRR**: asynchronous; **RTC** gives a 15-minute SLA at a price.
- **Route 53 ARC**: routing controls with a 5-region data plane, for a failover that works when the console does not.
- **Active-active is a correctness problem, not an infrastructure problem.** Idempotency, conflict resolution, request routing stickiness, and a release process that must now deploy safely to two live regions.
- **Data residency**: region choice, replication scope, and where logs and backups land - people forget the logs.

---

## IaC and delivery

| Tool | Strength | Weakness |
| --- | --- | --- |
| **CDK** | Real language, constructs, testable, great for serverless | CloudFormation underneath (limits, slow rollback, drift) |
| **SAM** | Simple, fast local invoke, serverless-focused | Limited beyond serverless |
| **Terraform** | Multi-cloud, mature state model, wide provider set | Verbose for serverless; state management is your problem |

**Stack boundaries by rate of change and blast radius**: network/foundation (rarely changes), stateful (databases, buckets - never delete), stateless application (deploys many times a day). Cross-stack references are a coupling: prefer SSM Parameter Store lookups over `Fn::ImportValue`, which locks the exporting stack.

**Deployment**: publish a **version**, shift an **alias** with `CodeDeploy` weighted traffic (`Canary10Percent5Minutes`), alarms on the alias for automatic rollback. Pre-traffic and post-traffic hooks for verification.

**In-flight executions**: a Step Functions execution continues on the state machine definition it started with; a Lambda version change mid-execution means later steps run new code against earlier state. Version the state machine or make steps compatible.

**Config**: environment variables for static config; **Parameter Store / Secrets Manager fetched in `INIT` and cached** in the environment; AppConfig for dynamic flags with validation and rollback. Never call Secrets Manager per invocation - it is a latency, cost and throttle problem.

---

## Cost engineering

**Lambda**: `$0.0000166667 per GB-s` + `$0.20 per 1M requests`.

```
1M invocations x 500 ms x 1024 MB
= 1M x 0.5 s x 1 GB = 500,000 GB-s
= 500,000 x 0.0000166667 = $8.33  + $0.20 requests  = $8.53
```

**Memory tuning is often free money**: doubling memory that halves duration costs the same but returns faster; more CPU frequently makes it *cheaper*. **Graviton (arm64) is ~20 percent cheaper** per GB-s for the same work.

| Service | Rough unit price |
| --- | --- |
| Lambda | $0.20/M requests + $0.0000166667/GB-s |
| HTTP API | $1.00/M |
| REST API | $3.50/M |
| EventBridge | $1.00/M custom events |
| SQS | $0.40/M requests (batching cuts this 10x) |
| Step Functions Standard | $25/M state transitions |
| Step Functions Express | $1.00/M + duration-GB |
| DynamoDB on-demand | ~$1.25/M writes, ~$0.25/M reads |
| DynamoDB provisioned | ~1/7 of on-demand at steady load |
| S3 Standard | ~$0.023/GB/month |
| CloudWatch Logs | ~$0.50/GB ingest |
| NAT gateway | ~$0.045/h + $0.045/GB |

**The usual dominant lines, in the order you should check them**: NAT gateway data processing, CloudWatch Logs ingestion, Step Functions Standard transitions, cross-AZ data transfer, idle provisioned concurrency, and un-lifecycled S3.

**Commitments**: Compute Savings Plans cover Lambda, Fargate and EC2 - size to the measured **floor**, not the average. Reserved capacity for DynamoDB provisioned. Never commit to a workload you are about to re-architect.

**Unit cost is the only metric that survives growth**: cost per order, per tenant, per document. Absolute spend rising while unit cost falls is a healthy business.

**Never cut**: multi-AZ, backups, the DR capability, security controls, or the observability you need during an incident. Say this out loud when given a cost target.

---

## Well-Architected, condensed

Six pillars: **Operational excellence, Security, Reliability, Performance efficiency, Cost optimization, Sustainability**.

The framework is a **question set, not a scorecard**. A review's value is in three things: the accurate architecture diagram, the three risks that matter stated in business terms, and **the trade-offs you recommend accepting**. A review that lists thirty findings and no accepted risks is a checklist, not engineering judgement.

The highest-signal review questions are not in the framework: *show me your last three incidents*, *show me the dashboard you open during an incident*, *what are you afraid of*, and *who is the only person who understands X*.

---

## Numbers worth quoting

| Thing | Number |
| --- | --- |
| Lambda account concurrency (default) | 1,000/region |
| Lambda burst | 1,000 per 10 s |
| Lambda timeout / `INIT` limit | 900 s / 10 s |
| Lambda payload sync / async | 6 MB / 256 KB |
| Lambda memory → 1 vCPU | 1,769 MB |
| Lambda async retries / retry window | 2 / 6 hours |
| API Gateway integration timeout | 29 s |
| DynamoDB item / partition | 400 KB / 3,000 RCU, 1,000 WCU |
| DynamoDB query page / transaction | 1 MB / 100 items |
| DynamoDB on-demand instant scale | 2x previous peak |
| Kinesis shard in / out | 1 MB/s, 1,000 rec/s / 2 MB/s shared |
| SQS retention / FIFO throughput | 14 days / 300 tps per group |
| SQS visibility timeout rule | ≥ 6x function timeout |
| S3 per prefix | 3,500 PUT / 5,500 GET per second |
| S3 multipart threshold / required | ~100 MB / 5 GB |
| Step Functions Standard / Express | 1 year / 5 minutes |
| Cross-AZ data transfer | $0.01/GB each way |
| Internet egress | ~$0.09/GB |
| CloudFront → origin | free |
| Graviton saving | ~20 percent |
| 99.9 / 99.95 / 99.99 per month | 43.8 min / 21.9 min / 4.4 min |

**The identity to have on instant recall**: `concurrency = arrival_rate x duration`. Most Lambda capacity, cost and throttling questions are that equation asked sideways.
