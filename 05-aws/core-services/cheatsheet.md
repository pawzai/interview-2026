# AWS Core Services Cheatsheet

Fast revision for the breadth layer. Assumes [../cheatsheet.md](../cheatsheet.md) (serverless) and [../../01-java/cheatsheet.md](../../01-java/cheatsheet.md).

Every number here is a **default at the time of writing**. In an interview, say "the default is X, and it is adjustable" - quoting a figure as immutable is the tell of someone who read it rather than hit it.

**The four habits this pack is drilling**: name the deciding number, say what the service replaced, say when you would refuse it, and describe the operational tail.

---

## Reading an instance name

`m6in.2xlarge` = family `m` / generation `6` / attribute `i` (Intel) + `n` (network optimized) / size `2xlarge`.

| Suffix | Means | | Family | Ratio | For |
| --- | --- | --- | --- | --- | --- |
| `i` / `a` / `g` | Intel / AMD / Graviton | | `t` | Burstable | Dev, low average |
| `n` | Network optimized | | `m` | 1:4 | General, JVM APIs |
| `d` | Local NVMe | | `c` | 1:2 | Compute-bound, transcode |
| `e` | Extra memory/storage | | `r` / `x` / `u` | 1:8+ | Caches, in-memory |
| `z` | High frequency | | `i` / `im` / `d` | Local NVMe | Kafka, Cassandra |
| `flex` | Cheaper, sustained-use limited | | `p` / `g` / `inf` / `trn` | Accelerated | ML, GPU |

**Pick the family from the binding resource** (CPU, memory, disk throughput, network), not from the workload's name.

**T-family credits**: `t3.medium` = 20 percent baseline per vCPU, 24 credits/hour, max 576. `unlimited` mode (default on T3+) bills surplus instead of throttling. **A CPU graph flat at exactly the baseline is a throttle, not idleness.**

---

## Purchasing: three orthogonal decisions

| Instrument | Gives you | Discount | Capacity guarantee? |
| --- | --- | --- | --- |
| **Compute Savings Plan** | $/hr commitment, any family/region/OS, **plus Fargate and Lambda** | ~66% | **No** |
| **EC2 Instance Savings Plan** | $/hr, family+region fixed | ~72% | **No** |
| **Standard RI (regional)** | Specific config, size-flexible in family | ~72% | **No** |
| **Standard RI (zonal)** | Specific config, one AZ | ~72% | **Yes** |
| **On-Demand Capacity Reservation** | Capacity in one AZ, billed as On-Demand | none | **Yes** |
| **Spot** | Interruptible, 2-min notice | ~90% | No |

- **Commitment = billing. Spot = availability. ODCR = capacity.** They compose: ODCR for capacity + Savings Plan on top for price.
- **Commit to the floor** (trailing 60-90 day minimum), not the average. Target ~100% utilization, 70-85% coverage.
- **Sequence**: eliminate → right-size → *then* commit. Committing first locks in the waste.
- **Spot pool = one instance type in one AZ.** 10 types x 3 AZs = 30 pools = survivable. 2 types = not diversified.
- Spot config that works: `OnDemandBaseCapacity` at 30-50% of peak + 10 instance types + `price-capacity-optimized` + Capacity Rebalancing.

**Placement groups**: cluster (one AZ, max network, launch together) / spread (distinct hardware, **max 7 per AZ**) / partition (rack-aware, scales, for HDFS/Cassandra/Kafka). Default = no placement group.

**Tenancy**: a **per-physical-core licence needs a Dedicated Host** - Dedicated Instances are not enough (no host visibility, no affinity, no License Manager).

**Stop / hibernate / terminate**: instance store is **lost on stop**, not just terminate. Auto-assigned public IPv4 **changes on stop/start**.

---

## EBS: the deciding numbers

| Type | Ceiling | Durability | Use |
| --- | --- | --- | --- |
| **gp3** | **16,000 IOPS / 1,000 MB/s**; baseline 3,000 IOPS + 125 MB/s free | 99.8-99.9% | **The default** |
| **io2** | 64,000 IOPS | **99.999%** | >16k IOPS, or five-nines required, or p99 latency variance |
| **io2 Block Express** | 256,000 IOPS / 4,000 MB/s | 99.999% | Extreme; Nitro only |
| **st1** | 500 MB/s, 40 MB/s per TiB baseline | - | **Sequential only** - Kafka, EMR, logs |
| **sc1** | 250 MB/s | - | Cold bulk |

**Thresholds to quote**: move gp3 → io2 at **16,000 IOPS**; io2 → Block Express at **64,000**. HDD types **cannot be boot volumes**, and random I/O destroys them (a 4 KiB random read costs a full 1 MiB of throughput budget).

**gp2 → gp3**: ~20% cheaper, decoupled from size, online. **Watch throughput** - a large gp2 delivers 250 MB/s and gp3's baseline is 125.

**Three independent ceilings** - the volume, the **instance's EBS limits** (`EBSIOBalance%` / `EBSByteBalance%`), and the instance's network. High queue depth with low IOPS usually means the **instance**, not the volume. Compute average I/O size with `VolumeReadBytes / VolumeReadOps`.

**Snapshots**: incremental, crash-consistent (**not** application-consistent), regional, first cross-region copy is full. Restored volumes are **lazily loaded** - slow until hydrated. Fix with Fast Snapshot Restore (expensive), a `fio` pre-warm pass (free, slow), or not restoring at all.

**Multi-Attach (io2)**: up to 16 instances, same AZ, **no coordination** - ext4/XFS will corrupt within minutes. For cluster-aware software only. For shared storage, use EFS.

**Elastic Volumes**: size increases only, ~6-hour cooldown, and **the OS still needs `growpart` + `resize2fs`/`xfs_growfs`**.

---

## File and hybrid storage

| | Use when | Not when |
| --- | --- | --- |
| **EBS** | One instance needs a disk | Sharing |
| **EFS** | Many instances/containers share POSIX files | Many small files (metadata-bound, every op is a network round trip) |
| **S3** | Objects read/written whole | Filesystem semantics required |

**Cost gradient**: S3 ~$0.023/GB, **EFS ~$0.30/GB - roughly 10x.** If the app can use an object API, use S3.

**EFS defaults**: **Elastic throughput + General Purpose**. One **mount target per AZ** or you pay cross-AZ. **Access points** enforce a root directory + POSIX identity - the isolation mechanism. Two permission layers: **IAM (may I mount) and POSIX (may I write)**.

**FSx selection**: Windows apps/SMB/AD → **FSx for Windows**. HPC/ML extreme throughput → **Lustre** (link to S3, lazy-load, delete after the job). Existing NetApp, or NFS+SMB on the same data → **ONTAP**. Low-latency NFS with snapshots → **OpenZFS**. All are provisioned; EFS is serverless.

**Storage Gateway = ongoing access. DataSync = transfer.** Use DataSync for the bulk migration, Storage Gateway for applications still on-premises. Tape Gateway is the strongest single use case (retire physical tape, no backup-software change).

**"We have snapshots" is missing**: consistency, a tested restore, isolation/immutability, and completeness (logs, IaC, secrets, non-EBS data).

**Backup isolation, three threats**: **Vault Lock** (deletion/ransomware) / **cross-account copy** (production account compromise) / **cross-region copy** (regional event). All three, or you have covered one.

---

## Load balancers

| | ALB | NLB | GWLB |
| --- | --- | --- | --- |
| Layer | 7 | 4 | 3 |
| Latency | low ms | **tens of µs** | + a hop |
| Client IP | `X-Forwarded-For` | **Preserved** | n/a |
| Static IP | No | **One per AZ** | n/a |
| Protocols | HTTP/gRPC | TCP/UDP/TLS | GENEVE :6081 |
| WAF | **Yes** | No | No |
| Cross-zone default | **On, free** | **Off, charged** | Off |
| Warming needed | Elastic scaling | **None** | - |

**Decide by**: is it HTTP? → ALB. Then: static IP needed / true client IP at L4 / instantaneous million-rps spike → NLB.

- **Static IP + layer 7** → **Global Accelerator in front of an ALB** (not "switch to NLB"). Or NLB with an `alb` target type.
- **ALB now supports client mTLS** - so mTLS is no longer automatically a reason to leave ALB. Target-side mTLS is.
- **Target types**: `ip` unlocks containers, on-premises and peered VPCs. `alb` composes NLB + ALB properties. **Weighted target groups** = canary/blue-green in the infrastructure, not in code.
- **NLB fails open**: if *every* target is unhealthy, it sends to all of them. And with client IP preservation, **the target's security group must allow the client CIDR, not the NLB** - plus hairpinning from a target back through its own NLB fails.
- **Health checks**: NLB TCP checks only prove the port is open. Use HTTP where the protocol allows.

**The timeout ordering - memorize it:**

```
p99.9 request duration
  < application graceful shutdown
  <= deregistration delay
  <= terminate lifecycle hook timeout
  < 120s (Spot interruption window)

backend keep-alive  >  ALB idle timeout (default 60s)
```

Backend keep-alive shorter than the ALB idle timeout = **intermittent 502s** with `target_status_code` of `-`. nginx defaults to 75s (safe); many app servers default to 20s or less (not).

**502 diagnosis**: `target_status_code` = `-` → target never responded (keep-alive race, crash, saturation). Has a value → malformed response. `target_processing_time` = `-1` → connection failure.

**Pre-warming**: not a thing in 2026. Load test the whole path instead - the load balancer is rarely what breaks.

---

## Auto Scaling

| Policy | When | Danger |
| --- | --- | --- |
| **Target tracking** | Default for everything | Metric does not correlate with capacity need |
| **Step** | Asymmetric/non-linear response | Usually means the metric is wrong |
| **Simple** | Effectively never | Cooldown blocks action while it worsens |
| **Scheduled** | Known calendar patterns - raise the **minimum**, not desired | Used instead of dynamic scaling |
| **Predictive** | Ramp faster than boot time; needs ~14 days of **cyclical** history | Unforecastable events; you pay for wrong forecasts |

**Better metrics than CPU**: `RequestCountPerTarget` for a web tier; **backlog per instance** for a queue.

```
backlogPerInstance = ApproximateNumberOfMessagesVisible / InServiceInstances
target = acceptable_latency / processing_time_per_message
```

**Queue depth is a stock, not a flow** - it is not proportional to needed capacity and target tracking on it oscillates. Alarm on `ApproximateAgeOfOldestMessage`; scale on backlog per instance.

**Oscillation - four things to check**: the target value (too near the natural operating point), **instance warm-up** (new instances counted before they serve - the most common cause), cooldown, adjustment size.

**`DefaultInstanceWarmup` replaces cooldowns.** Set it to measured time-to-serving, not time-to-running.

**Health check type**: default is **EC2 only**, which means a crashed application stays "healthy" forever and you silently lose capacity. Any ASG behind a load balancer needs **`HealthCheckType: ELB`** plus a grace period. **Alarm on `HealthyHostCount` diverging from desired capacity.**

**Termination protection (`DisableApiTermination`) does not stop the ASG.** Use **instance scale-in protection** for that.

**Instance refresh vs blue/green**: refresh rolls back by *replacing again* (minutes, mixed state). Blue/green rolls back by shifting weight (seconds, old fleet untouched). Refresh for routine AMI patching **with auto-rollback on an alarm**; blue/green for releases.

**Warm pools**: try these first - bake more into the AMI, predictive scaling, scheduled minimum, or just more headroom.

**Application Auto Scaling** (a different service) scales ECS task count, DynamoDB capacity, Aurora replicas, **Lambda provisioned concurrency**, SageMaker endpoints.

---

## Route 53

**Alias vs CNAME**: alias works **at the zone apex** (CNAME cannot), is **free**, resolves in one lookup, and supports `EvaluateTargetHealth`. Use alias for every AWS target.

| Policy | Use |
| --- | --- |
| Simple | One endpoint |
| **Weighted** | Canary, cross-stack migration, gradual regional shift |
| **Latency** | Multi-region performance |
| **Failover** | Active-passive DR; static S3 error page as secondary |
| **Geolocation** | **Compliance / residency / licensing** (deterministic by country) |
| **Geoproximity** | Traffic management with a **bias** dial (drain, shift, capacity balance) |
| **Multivalue** | Up to 8 healthy records; DNS round-robin **with health checks** |

(**IP-based** is an eighth, routing by client CIDR.)

**Latency routing measures the *resolver's* network latency to the region** - not your application's health, not the user's location, and not capacity. Always pair with health checks.

**Failover timing arithmetic:**

```
detection (interval x threshold: 30s x 3 = 90s default, or 10s x 3 = 30s fast)
+ TTL (60s if you prepared, 300s+ if not)
+ client caching beyond TTL (JVM caches DNS forever unless networkaddress.cache.ttl is set)
+ established connections (unaffected by DNS entirely)
= minutes, never seconds
```

**If you need seconds, use Global Accelerator** (~30s, no DNS involved). **Set `networkaddress.cache.ttl` in every JVM** - it is a one-line fix with an outsized effect.

**Health check types**: endpoint / **calculated** (boolean over children - and the **manual kill-switch** pattern) / **CloudWatch alarm** (for private resources or metric-defined health).

**Cutover TTL strategy**: lower TTL **at least 2x the current TTL in advance**; verify externally; cut over; keep the old endpoint serving; raise TTL only after the old endpoint sees zero traffic for a day.

**Delegation breaks silently** when a hosted zone is deleted and recreated - new NS records, registrar still points at the old ones, console looks perfect. Diagnose with **`dig +trace`**.

---

## CloudFront and the edge

**CloudFront gives you, besides caching**: edge TLS termination, the AWS backbone to origin, WAF/Shield/geo-restriction, edge compute, and **free origin→CloudFront data transfer** (vs ~$0.09/GB to the internet). An uncached API can still be worth it - **if the origin is far from users.** If the origin is near them, it adds a hop and makes things worse.

**The three policies**: **cache policy** = what is in the cache key (fragments the cache). **Origin request policy** = what the origin sees but does not fragment the cache. **Response headers policy** = what CloudFront adds to responses.

**Cache key**: the most common mistake is forwarding all query strings/headers/cookies - the cache appears to work while caching one object per user. Strip `utm_*`, `fbclid`; normalize `User-Agent` with a CloudFront Function; never key on `Authorization` for public content.

**Hit rate diagnosis order**: cache policy → **origin `Cache-Control` headers** (`curl -I` the origin, 30 seconds) → TTLs → long-tail request distribution (may be legitimate - use Origin Shield) → cache-busting URLs → `Vary` → methods/status codes. Use `x-edge-result-type` in the access logs.

**Versioned filenames beat invalidations**: instant, self-consistent, free rollback, `max-age=31536000`. Invalidate only the HTML entry point.

**Signed cookies for video** (hundreds of HLS segments), **signed URLs for single files** and non-cookie clients.

**Functions vs Lambda@Edge**: CloudFront Functions = all ~400+ edges, **viewer triggers only, no network access**, sub-ms, ~1/6 the price. Lambda@Edge = 13 regional edge caches, **origin triggers too, full SDK/network**, ms. Start with Functions.

**OAC over OAI** (OAI cannot serve SSE-KMS objects). **The bucket policy must condition on `AWS:SourceArn` of your distribution** - without it, any CloudFront distribution in the world can read the bucket.

**Global Accelerator vs CloudFront**: GA is L3/4, **two static anycast IPs**, no caching, ~30s health-check failover, **works for UDP and non-HTTP**, traffic dials per endpoint group. They compose.

**Origin failover covers GET/HEAD/OPTIONS only, per-request, no circuit state.** It is not a multi-region API failover mechanism.

---

## VPC at scale

**SG vs NACL**: ENI vs subnet; **stateful vs stateless**; allow-only vs allow+deny; all-rules vs ordered-first-match. SGs can reference other SGs. NACLs need the **ephemeral port range** for return traffic. Use NACLs only for an explicit deny or a guardrail an app team cannot undo.

**Peering vs Transit Gateway**: peering is **non-transitive**, needs **non-overlapping CIDRs**, and is `n(n-1)/2` - unmanageable past 5-10 VPCs. TGW replaced full-mesh peering and the transit-VPC appliance pattern.

**TGW costs**: **~$0.05/attachment/hour (~$36/month)** + **~$0.02/GB processed.**

Design consequences: **gateway endpoints for S3 and DynamoDB in every VPC** (free, and they remove that traffic from both NAT at $0.045/GB and TGW at $0.02/GB); **co-locate chatty services** in one VPC; **peer directly** for a small number of very high-volume pairs.

**TGW segmentation**: **association** = what an attachment can see; **propagation** = who can reach it. Prod associated to `prod-rt`, propagating into `prod-rt` + `shared-rt`; same for non-prod; shared services propagates into both. Prod has no route to non-prod, and an app team cannot change it.

**VPN**: two tunnels per connection, **~1.25 Gbps per tunnel, no aggregation**. Exceed it with **multiple VPN connections + ECMP over TGW**, or Direct Connect. **Always use BGP.**

**Direct Connect**: dedicated (1/10/100 Gbps, **weeks to months** lead time) vs hosted (50 Mbps-25 Gbps, **days**). VIF types: **private** (one VPC) / **public** (AWS public endpoints over DX) / **transit** (DX Gateway → TGWs, multi-VPC, multi-region - **the scalable pattern**). Start on VPN, order DX in parallel.

**Resiliency models**: dev-and-test (2 connections, 1 location) / **high resiliency** (1 per location, 2 locations) / **maximum** (2 per location, 2 locations). **Test with the BGP failover feature.** The hidden SPOF is usually the same fibre path, the same carrier, or one router on your side.

**Endpoints**: gateway (S3/DynamoDB only, **free**, route table entry) vs interface/PrivateLink (ENI, ~$0.01/hr/AZ + ~$0.01/GB). **Endpoint policies are the exfiltration control.**

**PrivateLink beats peering for a service provider**: exposes one endpoint not a network, **unidirectional**, **CIDR overlap irrelevant**, no provider-side work per consumer.

**Overlapping CIDRs after a merger**, ranked: re-address one side (correct, expensive - secondary CIDRs enable a phased move) / **PrivateLink per service** (fast, best for "next quarter") / NAT between them (works, horrible, needs an end date) / route only non-overlapping subnets / via on-premises.

**Flow logs cannot tell you**: what was in the traffic (use Traffic Mirroring), or **which rule** rejected it (use **Reachability Analyzer**). Not logged at all: DNS to the `.2` resolver, DHCP, IMDS, Windows activation. Send them to **S3 + Athena**, not CloudWatch Logs at $0.50/GB.

**Network Firewall's unique capability is domain-name egress filtering** - a security group only knows IPs. Check VPC endpoints with endpoint policies first.

**VPC DNS**: both `enableDnsSupport` **and** `enableDnsHostnames` are needed for interface endpoint private DNS - without them the endpoint resolves publicly and quietly routes via NAT. The `.2` resolver has a **1,024 packets/second per ENI** limit.

**Resolver endpoints**: **inbound** = on-premises resolves AWS names. **Outbound** = AWS resolves on-premises names. Share rules with RAM.

**Centralized egress** saves hourly NAT charges (120 gateways ≈ $3,800/month → 3) but **adds TGW per-GB on top of NAT per-GB**. Do the arithmetic, and do the endpoint work first.

---

## RDS and Aurora

| | Multi-AZ instance | Multi-AZ DB cluster | Aurora |
| --- | --- | --- | --- |
| Standby readable | **No** | **Yes (2)** | Yes (up to 15) |
| Replication | Synchronous | Semi-synchronous | Shared storage |
| Failover | **60-120s** | **<35s** | **<30s** |
| AZs | 2 | 3 | 3 |

**Multi-AZ is not read scaling and not zero downtime.** RPO 0, RTO 1-2 minutes, **all connections dropped**, in-flight transactions lost. The endpoint's **DNS record changes** - so a JVM caching DNS never recovers.

**Read replicas**: asynchronous, lag is variable, **no read-after-write guarantee**. **Promotion is irreversible and loses whatever lag existed** - so `ReplicaLag` is a DR-readiness metric, not just a performance one.

**Aurora storage**: **6 copies across 3 AZs**, 4/6 write quorum, 3/6 read quorum, **ships redo log records not pages**. Survives an AZ + one copy. Self-healing. Storage auto-scales to 128 TiB. Continuous backup to S3, PITR to the second, fast cloning.

**Aurora endpoints**: cluster (writes, follows failover) / reader (load-balances, **new connections only**) / custom (a named subset) / instance (**diagnostics only - never in an application**, because it breaks permanently on failover).

**Failover tiers 0-15**: lowest tier wins, largest instance breaks ties. **Put the writer-sized replica at tier 0** so a small reporting replica is not promoted into the writer role.

**Aurora Serverless v2**: 0.5 ACU increments, in-place, no dropped connections. **The minimum ACU is the real decision** - too low means a cold buffer cache. Wrong for steady predictable load (a reserved provisioned instance is far cheaper).

**Aurora Global Database**: storage-level replication, **sub-second lag**, planned switchover is lossless, unplanned RPO is seconds / RTO under a minute. **A headless secondary is pilot-light DR at storage cost.**

**Backups**: automated backups **die with the instance** (unless retained backups are enabled); **manual snapshots survive**. Deleting an instance without a final snapshot is usually unrecoverable - **AWS support cannot restore it**. Prevention: `deletion_protection`, an SCP on `rds:DeleteDBInstance`, and AWS Backup in a separate account.

**Blue/Green** automates the staging copy, replication, safety checks and the **endpoint-name swap** (under a minute). It does **not** roll back after switchover - writes to green are not replicated back.

**Parameter changes that "did nothing"**: **static parameters need a reboot** (`pending-reboot` status). Also: still on the default group; wrong level (cluster vs instance) on Aurora; a formula value; session-level overrides. **Check the running value** (`pg_settings.pending_restart`, `SHOW VARIABLES`), not the console.

**RDS Proxy** beyond serverless: absorbs container-fleet connection storms and deploy churn, and **holds connections across failover** (60-120s → seconds). Watch **`DatabaseConnectionsCurrentlySessionPinned`** - session state (`SET`, temp tables, some prepared statements) pins connections and defeats pooling entirely.

**"Why is the DB slow right now"** = **Performance Insights** (AAS by **wait event** and **top SQL**). CloudWatch tells you CPU is high; Enhanced Monitoring tells you which OS process; only PI names the query. **7-day retention is free - enable it everywhere.**

**End of standard support** → **Extended Support billed per vCPU-hour, escalating**, then a forced upgrade. Version currency is a budget item.

---

## Caching and analytics

**Redis vs Memcached**: Memcached is genuinely **multi-threaded** and simpler to scale for a pure cache; Redis has data structures, replication, failover and persistence. Default to Redis (or **Valkey**, cheaper). **MemoryDB** is durable Redis (synchronous multi-AZ log) - it collapses "cache + database" into one system.

**Cluster mode**: enable it from the start if growth is plausible. Converting later means fixing every multi-key operation (`CROSSSLOT`) under pressure. **Hash tags** `{user:123}` force keys into one slot.

**Cache collapse - four mechanisms:**

1. **Thundering herd** - jitter TTLs, single-flight lock, probabilistic early refresh.
2. **Eviction cascade** - `Evictions` climbing, hit rate falling under load.
3. **Single-thread saturation** - **`EngineCPUUtilization` at 100% while `CPUUtilization` looks fine**. Slow log; eliminate O(N) commands; shard.
4. **Hot key** - no amount of sharding helps.

A bigger node fixes only #2. **Test with a cold cache at production concurrency.**

**Athena cost = bytes scanned (~$5/TB).** Parquet (10-30x) x compression (3-5x) x partitioning (up to 1000x) x selecting only needed columns. 1 TB of JSON = $5; the same as partitioned Parquet with a date predicate = fractions of a cent. **"Athena is expensive" means "the lake is badly laid out".**

**Athena vs Redshift**: Athena when query frequency is low/unpredictable, data is already in S3, consumers are few. Redshift for many concurrent users on modelled data. **Concurrency scaling** fixes "dashboards are slow at 9am" (queue wait, not execution time - check which dominates). **RA3 separates compute from storage**; distribution and sort keys dominate performance.

**Firehose vs Data Streams**: need **multiple independent consumers or replay** → Streams. Just delivering to S3 as partitioned Parquet → Firehose (managed, format conversion, dynamic partitioning, **60s minimum buffer**). Common answer: Streams as the log, Firehose as one consumer.

**Purpose-built stores**: DocumentDB (MongoDB compat) / Neptune (graph traversal) / Keyspaces (Cassandra compat) / Timestream (time-series). **Default to DynamoDB for known key access and Aurora PostgreSQL for everything else** - Postgres extensions (`JSONB`, PostGIS, `pgvector`) cover a lot. **Every extra store is a permanent operational cost.**

**OpenSearch liabilities**: shard count fixed at index creation; **JVM heap capped ~32 GB**; mapping explosion from dynamic JSON; always running. Use UltraWarm/cold tiers and ISM policies, or ask whether CloudWatch Logs Insights or Athena would do.

---

## Containers

**ECS/EKS are orchestrators; Fargate is a capacity provider under either.** "ECS vs Fargate" is not a comparison.

**ECS on EC2 vs Fargate**: EC2 wins at **high steady packing efficiency** (bin-packing, Spot, Savings Plans); Fargate wins below that once operational time is counted. **Daemon containers are the sharpest difference** - an agent costs once per *instance* on EC2 and once per *task* on Fargate, which can double the bill. Fargate pulls the image fresh per task, so large images hurt.

**Cluster auto scaling** uses **`CapacityProviderReservation`** (task placement demand), **not CPU** - a node at 20% CPU can still have no room for a 4-vCPU task. Enable **managed termination protection** or scale-in kills running tasks.

**Fargate cannot pull the image** - four causes: no path to ECR (needs `ecr.api`, `ecr.dkr` **and the S3 gateway endpoint** for layers) / **execution role** not task role, missing ECR permissions / missing `assignPublicIp` or a bad route / image, tag, cross-account policy, or **arm64-vs-x86 mismatch**. Read `stoppedReason`: timeout = network, `AccessDenied` = permissions, `manifest unknown` = the image.

**EKS: AWS manages only the control plane** - roughly 20% of the work. Upgrades, add-ons, networking, RBAC, policy and observability are yours.

**VPC CNI IP exhaustion**: pods get real VPC IPs, and each node **pre-allocates a warm pool**. Symptom: nodes join but schedule nothing, `failed to assign an IP address`. Fixes in order: **secondary VPC CIDR (`100.64.0.0/10`) with new node subnets** / **prefix delegation** (`/28` per ENI) / tune `WARM_IP_TARGET` / IPv6. **Alarm on available IPs per subnet.**

**Pod Identity over IRSA** for new clusters - no OIDC provider, no per-cluster trust policy.

**ECR at scale**: lifecycle policies (untagged expire in 7 days), **tag immutability** on prod, enhanced scanning (continuous, not just on push), **cross-region replication**, a shared artifacts account with repository policies conditioned on `aws:PrincipalOrgID`, and **deploy by digest**.

**Batch** = long-running, retryable, resource-hungry jobs. **Spot is natural** because retry is built into the job model; queue mapped to a Spot compute environment first, On-Demand second.

**Outposts** (data must stay in your building) / **Local Zones** (low-latency *compute* in a far city) / **Wavelength** (mobile 5G edge). All carry a large premium and a service subset - establish the physical constraint first.

---

## Migration

**The 7 Rs**: Retire / Retain / Rehost / Relocate / Repurchase / Replatform / Refactor. **The deadline is met by rehosting; the value is realized by replatforming and refactoring afterwards.**

**Discovery produces**: a real inventory (usually 20-40% more servers than believed), **the dependency map** (the most valuable output), right-sizing data, a retire list, and a defensible TCO. It takes 4-8 weeks and it is the critical path - **start it in week one.**

**MGN**: agent-based **continuous block replication** to a staging area; **test launches without disrupting replication**; cutover = stop the app, drain, launch, validate, repoint. **Minutes of downtime.** Rollback = keep the source; MGN does not replicate back.

**DMS**: full load + **CDC from the transaction log**. It migrates **data, not schema** - no indexes, constraints, sequences or triggers. **SCT's assessment report should gate the migration decision.**

**DMS says success, data is wrong - four causes**: **limited LOB mode truncates silently** / type mapping differences (Oracle `NUMBER`, `DATE` semantics, timezones) / CDC gaps (missing supplemental logging, DDL, restart position) / sequences, constraints and triggers not handled. **Task state is liveness, not correctness** - run DMS data validation plus application-level reconciliation continuously.

**Snowball arithmetic** (assume ~60% usable bandwidth):

| | 100 Mbps | 1 Gbps | 10 Gbps |
| --- | --- | --- | --- |
| 10 TB | 15 days | ~1.5 days | 4 hrs |
| 100 TB | 5 months | 15 days | ~1.5 days |
| 1 PB | 4 years | 5 months | 15 days |

A Snowball Edge holds ~80 TB and takes about a week end to end. **Below 10 TB use the network; above 100 TB on <10 Gbps, ship.** And remember the link is shared with production, and the data keeps changing. **Hybrid: Snowball for the baseline, CDC for the delta.**

**DataSync copies; Storage Gateway serves; Transfer Family is for external parties.** DataSync over a script: ~10x faster, **checksum validation**, incremental, resumable, scheduled.

**Transfer Family cost surprise**: **~$0.30/hour per protocol (~$216/month) whether or not a file moves.** Consolidate onto one endpoint with per-user mappings.

**Slow upload from far away**: **multipart with parallelism first** (5-10x, free), then measure whether **Transfer Acceleration** helps on that route. **Then ask why the bucket is not in the local region.**

**Before you cut over**: a **tested rollback with reverse replication configured in advance**, a rollback decision point with a named owner and a deadline, TTLs already lowered, replication lag at zero, a timed dress rehearsal, a change freeze on both sides, reconciliation queries ready, and the old system kept intact for a month.

**Waves**: group by **application plus tightly-coupled dependencies**, order by risk ascending, keep them small enough to validate in one window. **A chatty app split from its database across a WAN is the classic failure** - 200 sequential queries x 25 ms = 5 seconds. Nothing errors; everything is slow.

**TCO comparisons miss**, on-premises: facility, refresh cycle, labour, licensing, and **over-provisioning (10-20% utilization)**. On AWS: **commitments, right-sizing, non-production shutdown**, and replatforming savings. For a lift-and-shift of a depreciated, over-provisioned estate, AWS genuinely can cost more - **say so**.

---

## Operations and governance

**Systems Manager works because the agent connects *outbound***. Prerequisites when it does not work: the agent, `AmazonSSMManagedInstanceCore` on the instance profile, and network access (NAT or the **`ssm`, `ssmmessages`, `ec2messages`** endpoints).

**Session Manager deletes bastions, SSH keys and inbound port 22.** Access is IAM (revoke by policy), scoped by instance tag, with **every command logged**. An internet-facing bastion in 2026 is a finding.

**Run Command** = one-off now. **State Manager** = continuous drift correction. **Automation** = multi-step, multi-service runbook (and EventBridge can trigger it). Move operations upward from the first to the third.

**Patch Manager**: baselines + patch groups + maintenance windows, with **rings** (dev 0 days, staging 3, prod 7-14), **`MaxConcurrency` and `MaxErrors: 1`**, and load-balancer deregister/patch/verify/re-register via Automation. **For anything in an ASG, replace the AMI instead** - Patch Manager is for what you cannot replace.

**Parameter Store vs Secrets Manager**: Secrets Manager's real differentiators are **built-in rotation** and **cross-account/multi-region replication**. Otherwise Parameter Store is free (standard tier) - 400 secrets is ~$160/month vs $0. **Fetch at init and cache**, never per request.

**CloudTrail is the verb; Config is the noun.** Only Config answers "which resources are non-compliant right now", "what did this look like before", and "what is related to this".

**Config cost is proportional to change, not size.** The fixes: **exclude `AWS::EC2::NetworkInterface`** (the biggest win in a container estate), **record global resources in one region only**, reduce periodic rule frequency, disable in unused regions (plus an SCP), and delete rules nobody acts on.

**StackSets with service-managed permissions and OU targeting** is the multi-account baseline mechanism - new accounts become compliant automatically.

**IaC choice for an operations team**: Terraform if scope extends beyond AWS; CloudFormation + StackSets if it is purely AWS multi-account. **Not CDK without a programming practice** - the failure mode is that nobody can change it in eighteen months.

**Trusted Advisor's limits**: no context (every recommendation needs judgement), a fixed check set, untunable thresholds, shallow cost analysis, most checks gated behind Business/Enterprise support. **The service-quota checks are the genuinely operational ones** - wire them to alerts.

**Compute Optimizer needs the CloudWatch agent for memory.** Without it, recommendations are CPU-only and a memory-bound JVM looks over-provisioned. It also misses cyclicality (14-day lookback), headroom requirements, licensing and DR standbys.

| Cost tool | Question |
| --- | --- |
| **Cost Explorer** | Where is the money going? |
| **CUR + Athena** | Line-item detail, chargeback, per-tenant |
| **Budgets** | Have we crossed **a threshold I set**? |
| **Cost Anomaly Detection** | Has spend deviated from **its own pattern**? |

You need the last two **both** - a service jumping 400% while staying under budget is exactly what anomaly detection catches.

**Health events → EventBridge → action.** The highest-value automation: `AWS_EC2_INSTANCE_RETIREMENT_SCHEDULED` → terminate an ASG member early on your schedule. Also: regional degradation → post to the incident channel automatically, so "is it us or AWS?" is answered before it is asked. Enable **organizational view**.

**CloudWatch agent gives you what the hypervisor cannot: memory and disk space** - the two most common causes of instance failure. **Set retention on every log group** (default is forever). **Composite alarms** for noise reduction. A **metric is a unique name + dimension combination**, so an instance-ID dimension across 500 instances is 500 metrics.

**Non-production shutdown**: 60-70% off that portion. Use tag-driven **opt-out** with a self-service override and a warning period. **RDS instances can only be stopped for 7 days.** Stopped instances still bill for EBS and Elastic IPs - the saving is compute only.

**Governance for rapid account growth**: Control Tower, an OU structure that expresses policy boundaries, a **small** high-value SCP set (including **region restriction**, which also cuts the Config bill), **IAM Identity Center with no IAM users**, organization-wide CloudTrail/Config/GuardDuty/Security Hub, cost visibility from day one, a StackSet baseline, and **IPAM before the first VPC**. Measure: **the percentage of accounts compliant without manual intervention.**

---

## Numbers worth quoting

| Thing | Number |
| --- | --- |
| gp3 baseline / ceiling | 3,000 IOPS + 125 MB/s / **16,000 IOPS + 1,000 MB/s** |
| io2 / Block Express ceiling | 64,000 / 256,000 IOPS |
| io2 durability | **99.999%** vs 99.8-99.9% |
| Spread placement group | **max 7 instances per AZ** |
| `t3.medium` baseline | 20% per vCPU |
| ALB idle timeout default | **60s** (backend keep-alive must exceed it) |
| Deregistration delay default | 300s (usually too long; set from p99.9) |
| Spot interruption notice | **2 minutes** (rebalance recommendation is earlier) |
| VPN tunnel throughput | **~1.25 Gbps, no aggregation** |
| TGW | ~$36/attachment/month + **$0.02/GB** |
| NAT gateway | ~$32/month + **$0.045/GB** |
| Cross-AZ transfer | $0.01/GB each way |
| Internet egress vs to CloudFront | ~$0.09/GB vs **$0** |
| Athena | **~$5 per TB scanned** |
| CloudWatch Logs ingestion | ~$0.50/GB |
| Multi-AZ instance failover | **60-120s** (DB cluster <35s, Aurora <30s) |
| RDS stopped maximum | **7 days**, then auto-start |
| Route 53 health check | 30s x 3 = 90s default; 10s fast |
| VPC `.2` resolver | 1,024 packets/s per ENI |
| EFS vs S3 storage | ~$0.30 vs ~$0.023 per GB-month |
| Transfer Family | ~$216/month **per protocol**, idle |
| Snowball Edge | ~80 TB, ~1 week round trip |
| Savings Plan targets | ~100% utilization, **70-85% coverage** |
| Non-production shutdown saving | **60-70%** of that portion |
