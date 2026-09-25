# Answers

Model answers for [questions.md](questions.md). Numbers match the question numbers exactly and are **local to this pack** - references to the serverless pack are written as "serverless pack Q68" and point at [../answers.md](../answers.md).

Answers follow the four-layer structure defined in [../../01-java/README.md](../../01-java/README.md): direct answer, mechanism, trade-off, experience hook. Hooks are written as *italic placeholders* - replace them with real detail from Verizon India and Sonata Software.

Every figure here is a **default at the time of writing**. Say "the default is X, and it is adjustable" rather than quoting a number as immutable. Q215-220 are worked as full exercises in [scenario-questions.md](scenario-questions.md).

---

## 1. EC2: instances, purchasing and placement

### Q1. Reading an instance type name

`m6i.2xlarge` decomposes as **family `m`** (general purpose, balanced CPU to memory at roughly 1:4), **generation `6`**, **attribute `i`** (Intel), **size `2xlarge`** (8 vCPU, 32 GiB).

The suffix letters are the part people fumble:

| Suffix | Meaning |
| --- | --- |
| `i` / `a` / `g` | Intel / AMD / Graviton (ARM) |
| `n` | Network optimized - higher bandwidth |
| `d` | Local NVMe instance store attached |
| `e` | Extra memory or extra storage |
| `z` | High frequency cores |
| `flex` | Sustained-usage-limited, cheaper for bursty workloads |

So `m6in.2xlarge` is Intel with enhanced networking, and `m6gd.2xlarge` is Graviton with local NVMe. Sizes double linearly - `2xlarge` is twice a `xlarge` in both vCPU and memory - which makes capacity arithmetic easy and is why "we need 12 vCPU" usually becomes a `4xlarge` with headroom rather than an exact fit.

The practical value of knowing this is that you can reason about an unfamiliar type from its name, and you can spot the cheap win: the same generation on `a` or `g` is typically 10-20 percent cheaper for the same nominal size.

*Hook: an instance family change you made purely from reading the naming, and the saving or performance change it produced.*

### Q2. The instance families and what they are for

| Family | Ratio / specialization | Typical members |
| --- | --- | --- |
| **General purpose** | ~1:4 vCPU to GiB | `m`, `t` (burstable), `mac` |
| **Compute optimized** | ~1:2 | `c` |
| **Memory optimized** | ~1:8 or higher | `r`, `x`, `u` (high memory), `z` |
| **Storage optimized** | Local NVMe, high IOPS | `i`, `d`, `im`, `h` |
| **Accelerated** | GPU, Inferentia, Trainium, FPGA | `p`, `g`, `inf`, `trn`, `f` |

Mapping the four workloads:

- **A Spring Boot API** - `m` family. The JVM wants memory for heap plus metaspace and the workload is mixed, so a balanced ratio is right. `c` is a common mistake here: you end up memory-constrained and buying vCPU you do not use.
- **An in-memory cache** - `r` family, or `x` if the dataset is very large. The whole point is GiB per rupee, and cache workloads are rarely CPU-bound.
- **A video transcoder** - `c` family, or `g` if the codec has GPU acceleration. Transcoding is the archetypal compute-bound job, and a GPU can change the economics by an order of magnitude for supported codecs.
- **A Kafka broker** - `i` or `im` family for local NVMe, or `r` with EBS if you need the durability semantics of network storage. Kafka is throughput and disk bound, and the sequential-write pattern suits instance store well - provided you accept that broker replacement means resynchronizing from replicas.

The senior framing: **you pick the family from the binding resource, not from the workload's name.** Measure which of CPU, memory, disk throughput or network is saturating first, then choose the family whose ratio matches.

*Hook: a workload you moved between families after measuring, and what the binding resource turned out to be.*

### Q3. What Nitro changed

Nitro moved virtualization off the main CPU and onto dedicated hardware cards: networking, EBS, local storage, and the security/monitoring functions all run on Nitro cards, with a minimal KVM-based hypervisor left on the host.

What that means to you as an architect, in order of practical importance:

1. **Nearly bare-metal performance.** The hypervisor tax largely disappeared, so instance performance is more predictable and consistent - which is what makes capacity planning tractable at all.
2. **Higher network and EBS throughput**, and they became separately provisioned. Instance network bandwidth and EBS bandwidth are now distinct ceilings you can hit independently, which is the source of a whole class of "the volume is not the bottleneck" confusion (Q26).
3. **Enclaves and always-on encryption.** EBS encryption at no performance cost, and Nitro Enclaves for isolated processing of sensitive data.
4. **Faster instance launches and live-update capability**, which is why maintenance events became rarer.
5. **Bare metal instances became possible** - the `.metal` sizes exist because the virtualization is on the card, so AWS can simply not virtualize.

The architectural consequence worth saying out loud: **on Nitro, "it must be slow because it is virtualized" stopped being a valid hypothesis.** If a workload underperforms against on-premises hardware on a Nitro instance, the cause is almost always storage configuration, network placement, or an instance-size ceiling - not the hypervisor.

*Hook: a performance comparison against on-premises hardware where the actual difference turned out to be storage or network configuration.*

### Q4. The T-family credit model

Burstable instances give you a **baseline** fraction of a vCPU continuously, and bank the unused portion as **CPU credits**. One credit is one vCPU-minute at 100 percent. When you exceed the baseline you spend credits; when you are below it you accrue them, up to a cap of roughly 24 hours' worth.

The numbers that matter: `t3.medium` has a **20 percent baseline** per vCPU and earns 24 credits per hour, with a maximum balance of 576. `t3.micro` is 10 percent. The baseline is *per vCPU*, so a two-vCPU `t3.medium` at 20 percent baseline is 0.4 vCPU of sustained compute.

**When credits run out**, the behaviour depends on the mode:

- **Standard mode**: the instance is throttled hard to the baseline. This is the cliff.
- **Unlimited mode** (the default on T3 and later): the instance keeps bursting and you are billed for **surplus credits** at a fixed rate per vCPU-hour. No throttling, but a bill that can quietly exceed the equivalent `m` instance.

The trade-off is the whole point: T instances are dramatically cheaper *if the workload's average is genuinely below the baseline*. They are a trap for anything with a sustained load, because standard mode degrades and unlimited mode costs more than the right-sized `m` while also being unpredictable. **The rule I would state: T family for development, low-traffic internal tools and genuinely spiky low-average workloads; never for a production service with a steady floor.**

*Hook: a burstable instance you moved off, and whether the trigger was throttling or the surplus-credit bill.*

### Q5. The three-week `t3.medium` cliff

The instance accrued credits from launch, ran above its baseline for three weeks spending them down, exhausted the balance, and is now **throttled to its 20 percent baseline in standard mode**. CPU shows "20 percent" because 20 percent is now the ceiling, not because the application only wants 20 percent - the metric is reporting the throttle, not the demand.

This is the single most misread graph in AWS. A flat line at exactly the baseline is not a healthy, idle instance; it is a hard-limited one. The confirming metrics are **`CPUCreditBalance` at zero** and **`CPUSurplusCreditBalance`** or `CPUCreditUsage` behaviour, and if you have them, run-queue length inside the instance showing work waiting.

"Three weeks" is the tell: it is exactly the shape of a credit balance draining slowly. A genuine load increase produces a step change, not a slow decline followed by a cliff.

The two fixes:

1. **Switch to unlimited mode** - immediate, no restart, keeps the instance responsive. This buys time but converts a performance problem into a cost problem, so it is a mitigation and not a resolution.
2. **Move to a non-burstable instance** - `m6i.large` or equivalent, sized from the *actual* demand you can now measure (which you could not see while it was throttled). This is the real fix.

*Hook: a credit-exhaustion incident, how long it took to diagnose, and what the graph looked like.*

### Q6. The purchasing options

| Option | Commitment | Discount | Workload shape |
| --- | --- | --- | --- |
| **On-Demand** | None | Baseline | Unpredictable, short-lived, or the first 3 months of anything new |
| **Savings Plans** | 1 or 3 years of $/hour spend | Up to ~72 percent | Any steady baseline; flexible across instance family and even across Lambda/Fargate |
| **Reserved Instances** | 1 or 3 years of specific capacity | Up to ~72 percent | Steady and specific; needed for capacity reservation semantics |
| **Spot** | None, but interruptible with 2 minutes' notice | Up to ~90 percent | Fault-tolerant, stateless, batch, flexible on timing |
| **Dedicated Hosts** | Optional | Premium price | Licensing tied to physical sockets or cores, compliance isolation |
| **Capacity Reservations** | None (billed as On-Demand) | No discount | You need the capacity to *exist* in a specific AZ |

The framing that gets you credit: **these are three orthogonal decisions, not one list.** Commitment (Savings Plan or RI) is a *billing* construct. Spot is an *availability* construct. Capacity Reservations are a *capacity* construct. You can - and often should - buy a Savings Plan that applies to instances running in a Capacity Reservation, and separately run your batch tier on Spot.

The standard shape for a mature estate: **cover the measured floor with a Compute Savings Plan, run the variable middle On-Demand, and run everything interruptible on Spot.**

*Hook: the commitment mix you chose for an estate, and how you sized the floor.*

### Q7. Reserved Instances versus Savings Plans

**Savings Plans commit you to a dollar amount per hour** for one or three years. **Reserved Instances commit you to a specific instance configuration** - family, size (within a normalization factor), region or AZ, platform.

| | Compute Savings Plan | EC2 Instance Savings Plan | Standard RI |
| --- | --- | --- | --- |
| Flexibility | Any region, family, OS, tenancy; **also Fargate and Lambda** | Family and region fixed; size and OS flexible | Family, region, OS fixed |
| Discount | Up to ~66 percent | Up to ~72 percent | Up to ~72 percent |
| Capacity reservation | No | No | Only zonal RIs |
| Sellable | No | No | Standard RIs, on the Marketplace |

For a mixed fleet today I would buy a **Compute Savings Plan** covering the floor, for three reasons. The flexibility means an instance family migration - to Graviton, say - does not strand the commitment, which matters because you almost certainly *will* re-platform something in three years. It covers Fargate and Lambda, so a workload that moves to containers or serverless stays covered. And it removes the operational overhead of RI management, which in practice is where most organizations quietly lose the discount they thought they bought.

The counter-argument, stated honestly: **EC2 Instance Savings Plans give a few more percentage points** if you are confident about the family, and **zonal RIs are the only commitment that also reserves capacity**. If you need capacity assurance in a specific AZ, no Savings Plan will give it to you.

The sizing rule matters more than the choice: **commit to the floor, not the average.** Look at the minimum hourly spend over the trailing 60-90 days, commit to that, and top up quarterly. Over-committing is a three-year mistake.

*Hook: a commitment purchase you sized, the coverage and utilization you achieved, and whether you got it wrong in either direction.*

### Q8. Standard versus Convertible, regional versus zonal, and capacity

**Standard RIs**: the deepest discount, and you can change the AZ, the instance size within the family, and the network type - but not the family, OS or tenancy. Sellable on the Reserved Instance Marketplace.

**Convertible RIs**: a smaller discount, but you can exchange them for a different family, OS or tenancy, provided the new reservation is of equal or greater value. Not sellable.

**Regional scope**: the discount applies across all AZs in the region and gets *instance size flexibility* within the family. No capacity guarantee.

**Zonal scope**: pinned to one AZ, no size flexibility, **and it reserves capacity in that AZ**.

So the answer to the capacity question: **only zonal RIs and On-Demand Capacity Reservations guarantee capacity.** Regional RIs, all Savings Plans and Convertible RIs are purely billing constructs - they will happily give you a discount on an instance you cannot launch.

This matters in exactly two situations, and they are worth naming because most people never hit them: **a large-scale failover into a second region or AZ**, where everyone else is failing over at the same time and capacity is genuinely contended; and **a scheduled event with a known large spike**. In both cases the correct instrument is an **On-Demand Capacity Reservation** - it reserves capacity, it is billed whether or not you use it, and a Savings Plan can be applied on top to reduce that bill. That combination - ODCR for capacity plus Savings Plan for price - is the answer that shows you have actually needed it.

*Hook: a failover or launch where capacity availability, not price, was the constraint.*

### Q9. How Spot actually works

Spot gives you spare EC2 capacity at a steep discount, reclaimed when AWS needs it back. The mechanics:

- **Pricing** is set by long-term supply and demand per instance type per AZ, and moves gradually - the old "bidding" model is gone. You pay the current Spot price, up to an optional maximum.
- **Interruption notice** is a **two-minute warning** delivered through instance metadata and an EventBridge event. There is also a **rebalance recommendation** signal that fires *earlier*, when the instance is at elevated risk, which is the more useful of the two because two minutes is not much.
- **Allocation strategies** decide which pools you draw from. `capacity-optimized` picks the pools with the deepest spare capacity and is the right default; `price-capacity-optimized` balances the two and is generally what I would actually use; `lowest-price` optimizes for cost and gets you interrupted constantly; `diversified` spreads across pools.
- **Capacity Rebalancing** on an ASG proactively launches a replacement when the rebalance recommendation arrives, rather than waiting for the two-minute notice.

The single most important design input is **pool diversity**. A Spot "pool" is one instance type in one AZ. If your fleet can use 10 instance types across 3 AZs, that is 30 pools and an interruption is a minor event; if it can use one type in one AZ, an interruption is an outage. This is why "we run on Spot" and "we run on Spot safely" are different statements, and the difference is a mixed instances policy with a long type list.

*Hook: a Spot fleet you ran, its interruption rate, and how many pools it drew from.*

### Q10. Spot for the whole stateless web tier

The instinct is defensible - the tier is stateless, so interruption should be survivable - but three things bite:

1. **Correlated interruption.** Spot capacity is reclaimed per pool, and if the fleet is one or two instance types, a single capacity event can take a large fraction of the fleet within minutes. Stateless does not save you from having no capacity. *Fix: a mixed instances policy with 10+ instance types across all AZs and `price-capacity-optimized` allocation, plus an **On-Demand base capacity** so the fleet can never go to zero.*
2. **In-flight requests die.** Two minutes is enough to drain gracefully, but only if something is listening. Without handling, the instance vanishes mid-request and users see errors. *Fix: consume the interruption notice and the rebalance recommendation, deregister from the target group, and let the deregistration delay drain connections - and make sure the deregistration delay is shorter than two minutes (Q59).*
3. **Replacement is not instantaneous.** A new instance must launch, boot, warm up the JVM and pass health checks - which for a Java service is often several minutes. During that window the remaining fleet absorbs the load, and if it was sized without headroom, you get a cascading overload. *Fix: headroom in the ASG, a warm pool or a pre-baked AMI to cut boot time, and Capacity Rebalancing so replacement starts before the interruption.*

The honest summary I would give: **Spot for a customer-facing tier is viable and I have done it, but it costs engineering effort, and the correct configuration is "On-Demand base plus Spot on top", not "100 percent Spot".** A common landing point is 30-50 percent On-Demand base with the elastic portion on Spot - most of the saving, with a floor that cannot disappear.

*Hook: a Spot configuration for a customer-facing tier, the base percentage you chose, and what a real capacity event did to it.*

### Q11. Placement groups

| Type | Guarantee | Use |
| --- | --- | --- |
| **Cluster** | Instances packed onto the same high-bisection-bandwidth network segment, single AZ | HPC, tightly coupled compute, low-latency node-to-node - anything needing 10s of microseconds and full network throughput |
| **Spread** | Each instance on **distinct underlying hardware**, max 7 per AZ per group | A small set of critical instances that must not share a failure domain - a three-node quorum, a pair of domain controllers |
| **Partition** | Instances divided into partitions, each on a separate rack; you can see which partition an instance is in | Large distributed data systems that are rack-aware - HDFS, Cassandra, Kafka |

The trade-offs are what interviewers want. **Cluster** maximizes network performance and *concentrates* failure risk in one AZ and often one rack, and it can fail to launch if capacity in the group's segment is insufficient - so launch all instances in one request. **Spread** maximizes hardware independence but caps you at 7 instances per AZ, which surprises people who try to use it for a general fleet. **Partition** is the one that scales, and it is the right answer for a data tier because the topology is *exposed* - your application can place replicas in different partitions deliberately.

The thing worth adding: for most workloads the answer is **no placement group at all**. Default placement already spreads across hardware, and adding a cluster group to a web tier gains nothing while adding a launch constraint.

*Hook: a workload where placement genuinely mattered, and how you verified it did.*

### Q12. Tenancy and licensing

**Default (shared) tenancy**: your instance shares hardware with other customers. **Dedicated Instances**: your instances run on hardware dedicated to your account, but you have no visibility or control over which physical host, and instances may move between hosts on stop/start. **Dedicated Hosts**: you get a specific physical server, with visibility of its sockets, cores and host ID, and control over instance placement on it.

**For a BYOL licence tied to physical sockets or cores - the classic Oracle, Windows Server or SQL Server case - you need a Dedicated Host.** Dedicated Instances are not enough, and this is the distinction the question is really testing. The licence terms require you to demonstrate and control the physical core count you are running on; only Dedicated Hosts expose that, support **affinity** (an instance returns to the same host after a stop/start), and integrate with **License Manager** for tracking. Dedicated Instances give you hardware isolation for *compliance* purposes but no host visibility, so you cannot satisfy a per-core licence audit with them.

The cost trade-off is steep: Dedicated Hosts are billed per host, not per instance, so you pay for the whole machine whether you fill it or not. That makes bin-packing your own workloads onto the host an actual design activity, and it is often the reason a "move to AWS" business case for a licensed workload comes out negative unless you also migrate off the licence.

*Hook: a licensed workload you placed on AWS, the tenancy you chose, and whether the licence or the infrastructure dominated the cost.*

### Q13. Golden AMIs, user data and configuration management

Three points on a spectrum from "bake everything" to "configure everything at boot":

- **Golden AMI**: the OS, runtime, agents and often the application are baked into the image. Boot time is minutes-to-seconds, the result is deterministic, and the artifact is immutable and testable. The cost is an AMI pipeline, a proliferation of images, and a patching cadence you must actually run.
- **User data at boot**: a minimal base AMI plus a script that installs and configures. Flexible and simple to start, but boot is slow, it depends on external repositories being available, and it is non-deterministic - the same script on two days produces two different machines.
- **Configuration management** (Ansible, Chef, or Systems Manager State Manager): converges the machine to a described state, at boot and continuously.

The mature pattern is a **layered bake**: a hardened base AMI produced centrally on a monthly cadence with OS patches and agents (CloudWatch, SSM, security tooling), then an application AMI built per release on top of it in CI with EC2 Image Builder, then **user data only for instance-specific configuration** - environment, region, cluster identity - injected at boot. Configuration management is used for drift detection and emergency fleet-wide changes, not for provisioning.

The principle underneath is the same one from `07-devops`: **immutable infrastructure**. Anything configured at boot is a thing that can differ between two instances in the same ASG, and every such thing is a future incident where one instance behaves differently and nobody knows why.

*Hook: an AMI pipeline you built or inherited, the bake-versus-boot split you chose, and the incident that set it.*

### Q14. User data, cloud-init and Systems Manager

**User data** is a blob you attach to the instance; **cloud-init** is the agent inside the AMI that reads it from the metadata service and executes it, on Linux; on Windows, EC2Launch v2 plays the same role. So user data is the delivery mechanism and cloud-init is the executor - and they are frequently conflated. **Systems Manager** is a different thing entirely: an agent with a persistent control-plane connection that can run commands at any time, not only at boot.

Key behaviours to know: user data runs **as root**, **once by default on first boot** (not on every reboot, unless you configure `cloud-init` to do so or use a `MIME` multipart with the right directive), and it runs **late in boot but before the instance is marked healthy** - which means a slow user-data script delays your ASG's health check and interacts badly with warm-up settings.

**Debugging a silently failing user-data script** - the sequence I would actually run:

1. **`/var/log/cloud-init-output.log`** on the instance. This has the stdout and stderr of the script and answers the question 90 percent of the time. On Windows, the EC2Launch log under `C:\ProgramData\Amazon\EC2Launch\log`.
2. **`/var/log/cloud-init.log`** for the cloud-init framework itself - useful when the script did not run at all rather than ran and failed.
3. **Check the shebang.** A script without `#!/bin/bash` on the first line is not executed as a script. This is the most common cause of "it did nothing".
4. **Check it is not being skipped as a re-run** - if the AMI was baked *from* an instance that already ran cloud-init, the instance-id check can cause it to be skipped.
5. **Check network dependencies** - a script that curls a repository from a private subnet with no NAT hangs and times out, and the failure is silent because nothing checks the exit code.

The last point generalizes: **user data does not fail the instance.** A non-zero exit code is not surfaced anywhere, the instance boots healthy, and the fleet runs with half the configuration missing. Any serious use of user data ends with a step that signals success explicitly - `cfn-signal`, a lifecycle hook completion, or a health check that actually tests the configured thing.

*Hook: a user-data failure that ran silently in production, and the signal you added afterwards.*

### Q15. The instance metadata service

IMDS is the link-local endpoint at `169.254.169.254` that gives an instance information about itself - instance ID, AZ, network configuration, user data - and, critically, **the temporary credentials of its attached IAM role**. Architecturally it is the mechanism that makes role-based access work on EC2 at all: it is why an EC2 instance never needs an access key on disk.

**IMDSv2 makes it session-oriented**: the caller must first `PUT` to `/latest/api/token` to obtain a token, then present that token as a header on every subsequent request. The `PUT` requirement and a default response hop limit of 1 are what matter, because together they defeat the attack that made IMDSv1 dangerous - a **server-side request forgery** in an application, where an attacker gets your app to fetch `169.254.169.254/latest/meta-data/iam/security-credentials/` and returns the role's credentials to them. A simple GET-based SSRF cannot perform the PUT or set the header, and the hop limit stops a container or proxy relaying it.

What changes when you enforce it: you must **audit for SDK and tooling versions** old enough to only speak v1, check that containers on the instance either have a hop limit of 2 or use task roles instead, and use the `MetadataNoToken` CloudWatch metric to find v1 callers before you flip the switch. The enforcement itself is an instance-level setting you can also mandate account-wide.

The forensic detail is in [11-security](../../11-security/questions.md); the architectural point here is that **IMDS is the credential distribution mechanism for EC2, and hop limit plus v2 enforcement is a design decision you make per instance profile, not a security afterthought.**

*Hook: an IMDSv2 rollout you drove, and what you found still speaking v1.*

### Q16. Moving a Java fleet to Graviton

The promise is roughly **20 percent better price-performance** for typical Java workloads, sometimes considerably more, because the JVM abstracts the architecture and OpenJDK on ARM64 is mature.

The actual work:

1. **Inventory native dependencies.** Pure Java is portable; anything with a native component is not. The usual suspects: `netty-tcnative`, Snappy and LZ4 compression bindings, `sqlite-jdbc`, image libraries, Lombok is fine but bytecode-manipulation agents may not be, and anything with a bundled `.so`.
2. **Container images.** Every base image and every layer must have an ARM64 variant, and the build must produce a multi-architecture manifest. This is usually the largest chunk of work in a container estate.
3. **The build pipeline.** You need ARM64 builders, or cross-compilation and ARM64 test runners. Testing on x86 and deploying on ARM is not acceptable.
4. **Agents and sidecars** - APM agents, security agents, log shippers - each needs an ARM64 build, and vendor support here is the most common blocker.
5. **Performance validation**, because the gain is workload-dependent. Verify under production-like load rather than trusting the headline number.

The migration approach: **run both architectures side by side in the same ASG or target group** using a mixed instances policy, compare latency and error rate at equal traffic, then shift the weight. That makes it reversible and turns the promise into a measurement.

What I would promise: **"a 15-20 percent compute cost reduction on the services that migrate cleanly, with a proportion - typically 10-30 percent of services - that will not move because of a dependency"**. Promising a fleet-wide 20 percent is how this project acquires a bad reputation in month three.

*Hook: a Graviton migration, the percentage of services that moved cleanly, and the measured saving.*

### Q17. Stop, hibernate and terminate

| | Stop | Hibernate | Terminate |
| --- | --- | --- | --- |
| **Root EBS volume** | Preserved | Preserved | Deleted if `DeleteOnTermination` is true (the default for the root volume) |
| **Attached EBS volumes** | Preserved | Preserved | Preserved unless flagged |
| **Instance store** | **Lost** | **Lost** | Lost |
| **RAM contents** | Lost | **Written to the root EBS volume and restored** | Lost |
| **Private IP** | Retained | Retained | Released |
| **Public IP (auto-assigned)** | **Released** - you get a new one on start | Released | Released |
| **Elastic IP** | Retained (and, when associated, not charged... but charged while the instance is stopped) | Retained | Disassociated |
| **Billing** | No instance charge; you still pay for EBS and Elastic IPs | Same, plus the larger root volume for the RAM image | Nothing |

The two facts that catch people: **the auto-assigned public IPv4 address changes across a stop/start**, which breaks anything that hardcoded it - the reason Elastic IPs or DNS exist. And **instance store data does not survive a stop**, not just a terminate, because a stopped instance may start on entirely different hardware. That second one has caused real data loss for people who treated instance store as a disk.

**Hibernate** requires the root volume to be encrypted and large enough to hold RAM, is limited to certain instance families and sizes, and has a maximum hibernation period. It is genuinely useful for expensive-to-warm workloads - a JVM with a large loaded cache, a development machine with an IDE and toolchain - and rarely worth it otherwise.

*Hook: a case where instance-store or public-IP behaviour on stop caused an incident.*

### Q18. Right-sizing 200 instances in a month

The trap is to open Compute Optimizer, take its recommendations and apply them - which produces a fast saving and a slow incident, because the recommendations are based on CPU and memory metrics that may not include memory at all unless the agent is installed.

My sequence:

**Week 1 - instrument and classify.** Install the CloudWatch agent everywhere so **memory and disk are actually visible** (the hypervisor cannot see them, Q212). Tag every instance with owner, environment and application, chasing down the unowned ones - and expect 10-20 percent of the fleet to have no clear owner, which is itself a finding. Pull 30-90 days of history where it exists.

**Week 2 - take the free wins.** These need no risk assessment: **instances that are simply stopped or idle** (under 5 percent CPU and near-zero network for 30 days) get flagged for deletion after owner confirmation; **non-production gets a shutdown schedule** (Q213), typically a 60-70 percent saving on that portion; **unattached EBS volumes and old snapshots** get cleaned up; **gp2 volumes move to gp3** (Q20), which is a saving with no performance risk.

**Week 3 - right-size the safe majority.** Downsize instances with clear evidence: p99 CPU and memory both well under the target across a full business cycle including month-end. Move in **one size step at a time**, in non-production first, and change nothing else in the same window. Generation upgrades - `m5` to `m6i` - are usually both cheaper and faster, and are the lowest-risk change of all.

**Week 4 - commit and institutionalize.** With the fleet reduced, size a **Compute Savings Plan against the new floor** - doing this before right-sizing would lock in the waste, which is the sequencing mistake to call out explicitly. Then set up the ongoing loop: monthly Compute Optimizer review, tagging enforced in IaC, and a right-sizing check in the deployment path so new services start correctly.

**What I would not do**: touch anything with a licence tied to core count without checking the licence first, right-size a database instance from CPU alone (memory and buffer cache are the constraint, Q147), or make changes during a month-end or peak period. And I would track **reliability metrics before and after** so the saving is not quietly purchased with stability.

*Hook: a right-sizing programme, the percentage saved, and what you refused to touch.*

---

## 2. EBS, instance store and block storage economics

### Q19. The volume types

| Type | Media | Performance | Designed for |
| --- | --- | --- | --- |
| **gp3** | SSD | 3,000 IOPS and 125 MB/s baseline, independently provisionable to 16,000 IOPS and 1,000 MB/s | The default for everything - boot volumes, most databases, general workloads |
| **gp2** | SSD | 3 IOPS per GiB, burst to 3,000 | Legacy. Migrate to gp3. |
| **io2 / io2 Block Express** | SSD | Up to 64,000 IOPS (256,000 Block Express), sub-millisecond, 99.999 percent durability | Latency-sensitive, IOPS-hungry, business-critical databases |
| **io1** | SSD | Up to 64,000 IOPS, 99.9 percent durability | Legacy; io2 is the same price with better durability |
| **st1** | HDD | Throughput-optimized, up to 500 MB/s, baseline scales with size | Big sequential reads - log processing, data warehouse, Kafka, EMR |
| **sc1** | HDD | Cold, up to 250 MB/s | Infrequently accessed, cost-optimized bulk |

The one-line rule: **gp3 unless you have a specific reason.** The reasons are: more than 16,000 IOPS or sub-millisecond consistency (io2), the five-nines durability requirement (io2), sustained large sequential throughput at low cost per GB (st1), or genuinely cold bulk (sc1).

The trap to name: **HDD volumes cannot be boot volumes**, and their performance is defined in throughput, not IOPS - so a small random-read workload on st1 performs catastrophically, because every random read spends the throughput budget of a full 1 MiB block.

*Hook: a volume type choice you made against the default, and the number that justified it.*

### Q20. gp2 versus gp3

**gp2 coupled performance to size**: 3 IOPS per GiB, with a burst bucket to 3,000 IOPS for small volumes. To get 9,000 IOPS you had to provision a 3,000 GiB volume whether you needed the space or not - so people bought capacity to buy performance.

**gp3 decoupled them.** Every volume gets 3,000 IOPS and 125 MB/s **regardless of size**, and you provision additional IOPS (to 16,000) and throughput (to 1,000 MB/s) independently, each priced separately.

Why gp3 is almost always the right migration:

1. **It is roughly 20 percent cheaper per GB** than gp2.
2. **Small volumes get 3,000 IOPS as a baseline**, where gp2 gave a 100 GiB volume only 300 IOPS with a burst bucket that could be exhausted.
3. **You stop over-provisioning capacity to buy IOPS**, which is where the large savings are - the 3,000 GiB volume for 9,000 IOPS becomes a 500 GiB gp3 with 9,000 provisioned IOPS at a fraction of the cost.
4. **The change is online**, with no downtime and no snapshot round trip.

The one case to check before a blanket migration: **a very large gp2 volume relying on the 3 IOPS/GiB scaling above 16,000 IOPS**. A 16 TiB gp2 delivers 16,000 IOPS by size alone, and gp3's ceiling is also 16,000 - so that migrates fine, but anything that needed more was on io1/io2 anyway. The genuine edge case is throughput: gp2 above ~334 GiB delivers 250 MB/s, and gp3's baseline is 125 MB/s, so **a large gp2 volume can lose throughput on migration unless you explicitly provision it**. That is the detail worth knowing, because a naive fleet-wide migration has caused exactly that regression.

*Hook: a gp2 to gp3 migration, the saving, and whether you had to provision throughput to match.*

### Q21. gp3, io2 and io2 Block Express - the deciding numbers

The thresholds, in the order you hit them:

- **Above 16,000 IOPS or 1,000 MB/s** - gp3's ceiling - you must move to io2. This is the hard boundary and the number to quote.
- **Above 64,000 IOPS**, or above 1,000 MB/s sustained on io2, you need **io2 Block Express**, which reaches 256,000 IOPS and 4,000 MB/s and requires a Nitro instance.
- **Durability**: gp3 and io1 are 99.8-99.9 percent annual durability; **io2 and Block Express are 99.999 percent**, a hundred-fold improvement. For a single-instance database where volume loss is a restore-from-backup event, that difference is a real availability input, and it is the reason to choose io2 even below 16,000 IOPS.
- **Latency consistency**: io2 offers sub-millisecond latency with much tighter variance. If your p99 database latency matters more than your median, this is the argument.

The trade-off is cost, and it is not small: **provisioned IOPS on io2 are billed per IOPS per month**, so 32,000 IOPS costs meaningfully more than the volume itself. A 500 GiB io2 with 32,000 IOPS can cost several times the equivalent gp3.

The practical decision rule: **start on gp3 with provisioned IOPS. Move to io2 when you hit 16,000 IOPS, when the five-nines durability is a stated requirement, or when p99 latency variance is the problem you are solving.** And before doing any of that, check whether the real fix is a query, an index or a cache - buying IOPS to compensate for a missing index is the most expensive way to solve that problem.

*Hook: a volume you moved to io2, the metric that justified it, and the cost delta.*

### Q22. st1 and sc1

Both are HDD-backed and **defined by throughput, not IOPS**. st1 (Throughput Optimized) delivers a baseline of 40 MB/s per TiB with a burst to 250 MB/s per TiB, capped at 500 MB/s per volume. sc1 (Cold) is 12 MB/s per TiB baseline, bursting to 80, capped at 250 MB/s.

They are good at **large sequential I/O at a low cost per GB** - roughly half the price of gp3 for st1 and less for sc1. The workloads: Kafka log segments, HDFS and EMR data nodes, log processing, data warehouse scans, big-file media storage, and backup staging.

**What destroys their performance is random I/O.** An HDD volume's throughput budget is consumed in 1 MiB units, so a 4 KiB random read costs the same budget as a 1 MiB sequential read - you lose 99.6 percent of your throughput to seek amplification. A database with a random access pattern on st1 performs so badly that people assume the volume is broken.

Two more constraints worth naming: **neither can be a boot volume**, and **performance scales with size**, so a small st1 is slow in absolute terms - a 500 GiB st1 has only a 20 MB/s baseline, which is often worse than the gp3 it replaced. The saving only materializes at scale.

*Hook: a workload where you chose HDD-backed storage, and how you confirmed the access pattern was sequential.*

### Q23. Low IOPS, high queue depth

The volume is not the bottleneck in the way the graph suggests. A **queue depth consistently above ~30 with IOPS below the provisioned limit means requests are waiting somewhere other than the volume's IOPS budget**. Four candidates, in the order I would check:

1. **The instance's EBS bandwidth ceiling.** Every instance size has a maximum EBS throughput and IOPS, separate from what the volume can deliver (Q26). An `m6i.large` cannot drive a 16,000 IOPS volume no matter how it is provisioned. Check `EBSIOBalance%` and `EBSByteBalance%` - if they are draining, the instance is the limit.
2. **The throughput ceiling rather than the IOPS ceiling.** If the workload uses large blocks, you hit MB/s before IOPS. 3,000 IOPS at 256 KiB per operation is 768 MB/s, far beyond gp3's baseline 125 MB/s. `VolumeWriteBytes / VolumeWriteOps` gives you the average I/O size and usually settles it immediately.
3. **Latency, not throughput.** High queue depth with low IOPS and high `VolumeQueueLength` alongside elevated await times inside the instance suggests each operation is slow - which for gp3 usually means you are being throttled at the burst boundary, or the workload is synchronous with `fsync` per write and is latency-bound rather than throughput-bound.
4. **A single-threaded application.** Queue depth is a *measure of concurrency*, so if it is high while IOPS are low, and none of the above hold, the storage layer is being asked for deep concurrency that it is serving slowly - and the answer might be io2 for latency, not more IOPS.

The diagnostic sequence is: **compute average I/O size, compare against both the volume limits and the instance limits, and check the instance's EBS burst balance metrics.** That distinguishes all four within a few minutes, and the answer is very often number 1 - the instance, not the volume.

*Hook: a storage performance investigation where the instance size, not the volume, was the constraint.*

### Q24. Burst buckets on gp2 and the gp3 equivalent

**gp2** allocates 3 IOPS per GiB as a baseline and gives volumes under 1,000 GiB a **burst bucket** filled at the baseline rate, holding up to 5.4 million I/O credits, spendable at up to 3,000 IOPS. A 100 GiB volume therefore has a 300 IOPS baseline but can sustain 3,000 IOPS until the bucket empties - roughly 30 minutes of continuous burst. The metric is **`BurstBalance`**, and when it reaches zero, performance drops to the baseline hard. Volumes at or above 1,000 GiB have a baseline of 3,000+ and no bucket.

This produces exactly the T-instance pattern (Q5): fine in testing, fine for weeks, then a cliff - and the same misdiagnosis, because the IOPS graph flattens at the baseline and looks like reduced demand.

**On gp3 the bucket is gone** - the 3,000 IOPS baseline is sustained indefinitely, which is the main operational improvement. The equivalent trap is different and worth naming: **gp3's baseline throughput is 125 MB/s regardless of size**, and it is a hard ceiling rather than a bucket. A workload doing large sequential I/O will hit 125 MB/s while showing IOPS far below 3,000, and because there is no burst balance metric to drain, there is no warning graph at all - just a flat throughput line. The fix is to provision throughput explicitly, and the lesson is to **alarm on throughput as well as IOPS**.

The other surviving bucket is at the **instance** level: `EBSIOBalance%` and `EBSByteBalance%` on smaller instance types, which burst and drain exactly like gp2 did.

*Hook: a burst-balance exhaustion you diagnosed, on either the volume or the instance.*

### Q25. Instance store versus EBS

**Instance store** is physically attached NVMe on the host. It offers the highest possible IOPS and throughput - millions of IOPS on `i` family instances - at the lowest latency, and it is **included in the instance price**. **EBS** is network-attached, durable, snapshot-able, detachable, and priced separately per GB and per provisioned IOPS.

The decisive property is durability: **instance store data is lost on stop, on hibernate, on termination, and on any underlying hardware failure.** Not just on terminate - on stop, because the restarted instance is a different physical machine. There is no snapshot, no backup, no recovery.

So the operational consequence, which is the real answer: **choosing instance store means your architecture must treat every node as disposable and must be able to rebuild a node's data from elsewhere.** That is fine and correct for: a Kafka broker or Cassandra node that resynchronizes from replicas, a search index that can be rebuilt from the source of truth, a cache, scratch space for a batch job, or a database read replica. It is a data-loss incident waiting to happen for anything that is the only copy.

The economics are genuinely attractive at the high end - an `i4i` instance's local NVMe versus the equivalent provisioned io2 is a large multiple in cost - which is why data-intensive systems use it. The engineering price is the rebuild path, and if you cannot describe that path in one sentence, use EBS.

*Hook: a system where you used instance store, and what the node-rebuild path was.*

### Q26. EBS-optimized, and finding the real ceiling

"EBS-optimized" originally meant dedicated bandwidth between the instance and EBS rather than sharing the general network path. **On all current-generation Nitro instances it is enabled by default and cannot be disabled** - so the term now mostly describes a property rather than a choice.

What remains, and what the question is really about, is that there are **three independent ceilings** and any of them can be the binding one:

1. **The volume's limits** - provisioned IOPS and throughput on gp3/io2, or size-derived limits on gp2/st1.
2. **The instance's EBS limits** - a maximum EBS IOPS and MB/s per instance size, published in the instance type table. This is frequently much lower than what the volume can do: a small instance may cap at 3,600 IOPS and 143 MB/s regardless of the volume attached.
3. **The instance's network limits** - separate again, and relevant when the workload is simultaneously driving network and storage.

Finding which is binding:

- Compare `VolumeReadOps + VolumeWriteOps` and `VolumeReadBytes + VolumeWriteBytes` against the **volume's** provisioned figures.
- Check **`EBSIOBalance%` and `EBSByteBalance%`** on the instance. These exist on burstable-EBS instance sizes and draining toward zero is a definitive signal that the *instance* is the limit.
- Compare the totals across **all volumes on the instance** against the instance's published EBS maximum - a common miss is that three volumes each within their own limits collectively exceed the instance's.
- Inside the OS, `iostat -x` gives await and utilization, which distinguishes "slow operations" from "too many operations".

The rule to state: **provision the volume to the workload, then verify the instance can actually drive it.** Buying 16,000 IOPS for an instance that can consume 3,600 is a pure waste, and it is a common one.

*Hook: a case where the instance's EBS ceiling, not the volume, was the limit, and how you found it.*

### Q27. Snapshots

EBS snapshots are **incremental block-level backups stored in S3** (in AWS-managed buckets you do not see). The first snapshot copies all written blocks; each subsequent snapshot stores only blocks changed since the previous one, with unchanged blocks referenced rather than copied.

The behaviour that surprises people is **deletion**. Because snapshots share blocks, deleting a snapshot does not necessarily free its apparent size - only blocks not referenced by any other snapshot are removed. So deleting the "big" first snapshot frees almost nothing if later snapshots depend on those blocks, and **every snapshot remains independently restorable** regardless of what you delete. You can never break a chain by deleting a middle snapshot, which is the reassuring half of the same mechanism.

Other mechanics worth knowing: snapshots are **crash-consistent, not application-consistent** - for a database you need to quiesce, flush, or use a mechanism that does (Q45); they are **regional**, so a snapshot does not protect you from a regional event until copied; and **copying cross-region transfers the data and is billed for the transfer and the new storage**, with the first copy in a new region being a **full** copy, not incremental. Subsequent copies of later snapshots to that region are incremental against what is already there.

Cost: snapshots are billed per GB-month of *changed* blocks, plus the transfer for cross-region copies. The usual waste is orphaned snapshots from deleted volumes accumulating for years, which is why lifecycle policies via **Data Lifecycle Manager** or AWS Backup should be mandatory rather than optional.

*Hook: a snapshot strategy you set up, and what your retention and cross-region policy was.*

### Q28. Fast Snapshot Restore

A volume created from a snapshot is **lazily loaded**: blocks are fetched from S3 on first access, so the first read of any block pays a large latency penalty and the volume performs badly until it is fully hydrated (Q29). **Fast Snapshot Restore pre-provisions the snapshot in specific AZs so that volumes created from it are fully initialized immediately** - full performance from the first I/O.

Pricing is the deciding factor: FSR is billed **per snapshot per AZ per hour** while enabled, at a rate that is far from trivial, and there is a limit on how many snapshots you can have FSR-enabled per region. It is also rate-limited in how quickly it can create initialized volumes.

So it is worth it when: **you restore from the same snapshot repeatedly and quickly** - a golden data volume for test environments, a scale-out event where new instances hydrate a large dataset from a base snapshot, or a DR plan whose RTO does not tolerate the hydration period. It is not worth it for routine backup snapshots that you hope never to restore, which is most of them.

The alternatives to mention: **pre-warm the volume yourself** by reading every block (`fio` or `dd`) after creation - slow but free; or **avoid the pattern entirely** by baking data into an AMI, using a shared filesystem, or having the node fetch data from S3 in parallel, which for large datasets is often faster than either option.

*Hook: a restore-time requirement that made FSR or an alternative necessary, and what you measured.*

### Q29. The slow first hour after a restore

**Lazy loading.** The volume is available immediately, but its blocks still live in S3. The first access to any block triggers a fetch from S3, which is orders of magnitude slower than an EBS read - so the volume performs at a fraction of its provisioned capability until the working set is hydrated. Once a block has been read once, it is on the volume and performs normally, which is why the problem resolves on its own and why it looks so mysterious: the same benchmark run twice gives completely different numbers.

The three ways to avoid it:

1. **Fast Snapshot Restore** (Q28) - pre-initializes the snapshot in the AZ so restored volumes are hot from the first I/O. Fast and expensive.
2. **Pre-warm by reading every block** before putting the volume into service - `sudo fio --filename=/dev/nvme1n1 --rw=read --bs=1M --iodepth=32 --ioengine=libaio --direct=1 --name=warm` or a simple `dd` pass. Free, but takes time proportional to volume size and consumes the throughput budget while it runs. Correct for a planned restore where you control the schedule.
3. **Do not restore from a snapshot at all** - replicate the data instead (a database read replica promoted, a filesystem synchronized in advance), or design the node to fetch its data from S3 in parallel at startup, which for large datasets is often faster than serial hydration.

The reason this matters beyond the annoyance: **a DR plan whose RTO was measured on a warm volume is wrong.** If you tested restore by creating a volume and running a quick check, you measured the availability of the volume, not the performance of the service - and in a real recovery you will discover the difference under load.

*Hook: a restore whose measured RTO was invalidated by hydration, and how you re-tested it.*

### Q30. EBS encryption

Encryption is at rest on the volume, on snapshots created from it, and **in transit between the instance and the volume**, using AES-256 with a KMS key. On Nitro instances there is no measurable performance cost, which removes the historical reason to skip it.

The mechanics: a **data key** is generated by KMS, encrypted under your CMK, and stored with the volume; the Nitro card holds the plaintext data key and performs the encryption, so the guest OS is not involved and the key never enters instance memory. **Account-level default encryption** can be enabled per region, after which every new volume and snapshot is encrypted with your chosen default key - and this is the setting to turn on everywhere, because it converts encryption from a per-resource decision into a property of the account.

The rules that constrain designs:

- **You cannot encrypt an existing unencrypted volume in place.** The path is snapshot → copy the snapshot with encryption enabled → create a volume from the encrypted copy. That means downtime or a replica swap, which is why default encryption at account creation matters so much.
- **You cannot decrypt an encrypted volume**, and you cannot change its key in place - the same copy dance applies.
- **AMIs inherit encryption**, so an encrypted golden AMI can only launch instances with encrypted volumes.

**Copying an encrypted snapshot to another account** is the part with the most failure modes: the snapshot must be encrypted with a **customer-managed key** (the AWS-managed `aws/ebs` key cannot be shared), the key policy must grant the target account use of the key, the snapshot must be explicitly shared with that account, and the target account must **copy the snapshot and re-encrypt it with its own key** before it can create a volume it fully controls. Every step of that chain produces an unhelpful `AccessDenied` when missed, and the usual culprit is the KMS key policy rather than the snapshot permission.

*Hook: an encryption retrofit or a cross-account snapshot share, and which permission was missing.*

### Q31. io2 Multi-Attach

Multi-Attach lets a single io1 or io2 volume be attached to **up to 16 Nitro instances in the same AZ simultaneously**, each with full read and write access.

What it is **not** is a shared filesystem. Every instance sees the raw block device, and there is **no coordination whatsoever** between them - no locking, no cache coherence, no arbitration. If two instances mount a standard filesystem like ext4 or XFS read-write on the same volume, they will each cache metadata independently and corrupt the filesystem within minutes. That failure is fast, total, and the classic misuse.

It exists for **cluster-aware applications that provide their own coordination**: a clustered filesystem (GFS2, OCFS2), Oracle RAC with ASM, or a custom application implementing its own distributed locking. Those systems expect shared block storage and handle the coherence themselves.

Constraints to know: **same AZ only** (so it is not an availability mechanism), io1/io2 only, Nitro instances only, no support for boot volumes, and **I/O fencing is your problem** - a partitioned node that still has the volume attached can still write to it.

The answer to "we need shared storage": **use EFS** (Q34). Multi-Attach is the right answer only when a specific piece of clustering software demands raw shared block devices, and that is a narrow set.

*Hook: a shared-storage requirement, and whether the answer was EFS, Multi-Attach or a redesign.*

### Q32. Modifying a volume online

Elastic Volumes let you change **size (increase only), volume type, and provisioned IOPS or throughput** without detaching the volume or stopping the instance. The volume enters an `optimizing` state during which it remains fully usable, though performance may be between the old and new levels.

The constraints:

- **Size can only increase**, never decrease. Shrinking requires creating a smaller volume and copying data at the filesystem level - so over-provisioning a volume is an effectively permanent decision, which is an argument for starting small and growing.
- There is a **cooldown of at least six hours** (sometimes longer) between modifications to the same volume, which matters if you are iterating on IOPS during an incident.
- Some type transitions have constraints, and moving to or from an HDD type has size implications.

**And the OS still has to do its part**, which is the half people forget: expanding the volume does not expand the partition or the filesystem. On Linux the sequence is `lsblk` to confirm the new size, `growpart /dev/nvme0n1 1` to extend the partition, then `resize2fs` (ext4) or `xfs_growfs` (XFS) to extend the filesystem. On Windows it is Disk Management or `diskpart extend`. Until you do that, `df` shows the old size and nothing has actually changed from the application's point of view - which produces the "I resized the volume and the disk is still full" support ticket.

*Hook: an online volume modification you performed under pressure, and whether the filesystem step was part of the runbook.*

### Q33. Storage for a 20 TB PostgreSQL on EC2

**What I would measure first**, before choosing anything - because the answer is entirely determined by it:

- **The I/O profile**: read versus write ratio, average I/O size, random versus sequential. From `pg_stat_*` views and `iostat -x`.
- **The current bottleneck**: is p99 query latency dominated by I/O wait, or by CPU, locks, or a missing index? A surprising proportion of "we need faster disks" turns out to be one unindexed query.
- **IOPS at peak**, not average, and the queue depth alongside it (Q23).
- **The buffer cache hit ratio.** If it is low, the cheapest performance fix is more RAM, not more IOPS - a memory-optimized instance can eliminate the I/O rather than accelerating it.
- **Whether the instance is the ceiling** (Q26).

**Then the decision.** Assuming the measurement confirms a genuine I/O constraint:

| Option | When |
| --- | --- |
| **gp3 with provisioned IOPS and throughput** | The default. 20 TB across several volumes, provisioned to the measured peak. Cheapest, and sufficient up to 16,000 IOPS per volume. |
| **Multiple gp3 volumes striped (LVM/RAID 0)** | Needs more than 16,000 IOPS or 1,000 MB/s but not io2 latency. Aggregate the limits - but check the *instance* ceiling first, and accept that striping multiplies the failure probability. |
| **io2 Block Express** | Sub-millisecond consistency is the requirement, or you need above 64,000 IOPS, or the 99.999 percent durability is a stated requirement. Significantly more expensive. |
| **`i4i` with instance store** | Extreme IOPS at low cost - but only if there is a replica and a rebuild path, since the data is lost on stop (Q25). For a primary with a streaming standby, this is legitimate and often overlooked. |

**And the question I would actually ask**: why is this on EC2? A 20 TB PostgreSQL being hand-tuned for I/O is a strong candidate for **Aurora**, where the storage layer is a distributed service that removes this entire class of decision, or at minimum **RDS**, where the volume management is managed. If the answer is a Postgres extension Aurora does not support, or a licensing or compliance constraint, that is a real reason - but "we have always run it ourselves" is not, and raising it is the difference between answering the question and doing the job.

*Hook: a database storage decision where measurement changed the answer you expected to give.*

---

## 3. File and hybrid storage: EFS, FSx, Storage Gateway, Backup

### Q34. EFS, EBS and S3 in one sentence each

- **EBS** is a **block device attached to one instance** (or a few, with Multi-Attach). Use it when something needs a disk: a boot volume, a database's data directory, anything expecting POSIX block semantics with single-writer ownership.
- **EFS** is a **managed NFS filesystem accessible from many instances, containers and functions simultaneously**, across AZs, growing elastically. Use it when multiple compute nodes must read and write the same files with POSIX semantics.
- **S3** is an **object store addressed over HTTP**, with effectively unlimited capacity, eleven nines of durability, and no filesystem semantics. Use it for anything that is a whole object read and written as a unit: media, backups, data lake files, static assets, logs.

The decision rule that follows: **if the application can be changed to use an object API, use S3** - it is an order of magnitude cheaper, infinitely scalable and operationally free. EFS exists for the cases where it cannot: legacy applications expecting a filesystem, shared configuration or content across a fleet, CMS uploads, home directories, and container workloads needing shared state.

The cost gradient is the part to say out loud: S3 Standard is around $0.023/GB-month, EFS Standard is roughly $0.30, and EFS is also charged for throughput in some modes. **EFS is roughly ten times the price of S3**, which is why "just use EFS, it's easier" is a decision with a bill attached.

*Hook: a case where you moved a workload from EFS to S3 (or refused to), and the reason.*

### Q35. EFS throughput and performance modes

**Throughput modes:**

| Mode | Behaviour |
| --- | --- |
| **Elastic** | Scales throughput automatically with demand, pay per GB transferred. The default and the right answer for almost everything. |
| **Provisioned** | You specify MB/s independent of stored data, billed for it whether used or not. For steady, predictable, high throughput where Elastic's per-request pricing is worse. |
| **Bursting** | Legacy model: throughput scales with the amount of data stored (50 KB/s per GB) with a burst credit bucket. |

**Performance modes:** **General Purpose** (lowest latency, capped at around 35,000 read IOPS) and **Max I/O** (higher aggregate throughput, at the cost of higher per-operation latency). Max I/O is largely superseded - with Elastic throughput, General Purpose handles far more than it used to, and the latency penalty of Max I/O hurts almost every real workload.

**Default choice: Elastic throughput with General Purpose performance mode.** It removes the two classic EFS failures - running out of burst credits (the `BurstCreditBalance` cliff, exactly the gp2 and T-instance pattern again) and paying for provisioned throughput nobody uses.

The reason to deviate: **Provisioned throughput when you have a sustained high-throughput workload**, because Elastic's per-GB-transferred charge can exceed a flat provisioned rate at volume. That is an arithmetic question, and the crossover is worth computing rather than guessing.

*Hook: an EFS throughput mode decision, and whether burst credits ever caught you.*

### Q36. EFS with many small files

EFS is NFS over the network, so **every file operation is a network round trip** - typically low single-digit milliseconds against a local EBS volume's tens of microseconds. For large sequential I/O this is irrelevant because throughput dominates. For **many small files it is everything**, because the workload becomes metadata-bound: `open`, `stat`, `read`, `close` for a 2 KB file is four round trips to move two kilobytes.

This is why a build that takes 2 minutes on EBS takes 40 minutes on EFS, and why `node_modules`, Maven repositories, Git working directories and image thumbnail trees are the canonical EFS disaster stories. The throughput graph looks fine - you are nowhere near the limit - because the constraint is **operations and latency, not bandwidth**.

What I would change, in order of preference:

1. **Move the small-file workload off EFS.** Build artifacts, dependency caches and scratch space belong on the instance's local EBS or instance store. If the point of EFS was sharing, share the *result* (a tarball in S3), not the working directory.
2. **Batch the access pattern** - read one archive instead of ten thousand files, which is what tarballs, JARs and container image layers all exist to do.
3. **Cache locally.** Copy the read-mostly tree to local disk at startup and read from there.
4. **Increase concurrency.** EFS scales throughput with parallelism, so a single-threaded traversal is the worst possible pattern; parallel workers help substantially if the workload allows it.
5. **Mount tuning** - larger `rsize`/`wsize`, and the EFS mount helper with TLS - is worth doing but is a marginal gain against a metadata-bound workload, and I would say so rather than presenting it as the fix.

*Hook: a small-file performance problem on a network filesystem, and where you moved the workload.*

### Q37. EFS storage classes, lifecycle and One Zone

Classes: **Standard**, **Infrequent Access (IA)**, **Archive**, and the **One Zone** variants of each. Lifecycle management moves files between them automatically based on access age - typically Standard to IA after 30 days, Archive after 90 - and **Intelligent-Tiering** moves them back to Standard on access.

The economics are steep: IA is roughly a tenth of Standard's storage price, Archive less again. **But IA and Archive charge per-GB retrieval**, so a file that transitions to IA and is then read repeatedly costs more than leaving it in Standard. The failure mode is a workload with a long tail of occasionally-read files - lifecycle moves them to IA, an analytics job scans everything monthly, and the retrieval charges dwarf the storage saving. Intelligent-Tiering exists to fix exactly this, and it is the safer default.

**The One Zone failure mode people forget** is not that it is less durable - it is still 11 nines *within* the AZ. It is that **an AZ outage makes the filesystem unavailable, and an AZ loss destroys it.** More subtly: One Zone means all your compute must be in that AZ to avoid cross-AZ data charges and latency, which **couples your compute placement to your storage placement** and quietly undermines the multi-AZ design of everything above it. A Multi-AZ ASG mounting a One Zone filesystem has instances in two AZs paying cross-AZ charges and losing service entirely when one AZ fails.

One Zone is right for: development and test, and derived data that can be regenerated. It is wrong for anything a production service depends on being available.

*Hook: a lifecycle policy whose retrieval costs surprised you, or a One Zone choice you made deliberately.*

### Q38. Access points, POSIX permissions and mount targets

**Mount targets** are the ENIs through which instances reach the filesystem. You create **one per AZ** you have compute in, each in a subnet with a security group. Traffic from an instance goes to the mount target **in its own AZ** if one exists - and if it does not, it crosses AZs, paying cross-AZ data transfer and adding latency. So the rule is: **a mount target in every AZ where you run compute**, which for a three-AZ ASG means three.

**Access points** are application-specific entry points into the filesystem. Each enforces:

- A **root directory** - the client sees this as `/`, so it cannot traverse to other parts of the filesystem. This is the isolation mechanism for multi-tenant or multi-application use of one filesystem.
- A **POSIX identity** (UID, GID, secondary groups) that overrides whatever the client claims, so file ownership is enforced by EFS rather than trusted from the instance.

That combination is what makes access points important architecturally: **without them, any instance that can reach the mount target can read the whole filesystem as whatever UID it likes.** With them, plus an IAM policy scoped to the access point, you get real per-application isolation on a shared filesystem - which is how you avoid running a filesystem per service.

The permissions model is a two-layer thing that catches people: **IAM controls whether you may mount and connect; POSIX permissions control what you may do once mounted.** A correct IAM policy with wrong POSIX ownership gives you a successful mount and permission denied on every write, which is exactly the symptom in Q47.

*Hook: an EFS access point or POSIX ownership problem in a container environment, and how you resolved it.*

### Q39. The FSx family

| Service | Protocol | Exists for |
| --- | --- | --- |
| **FSx for Windows File Server** | SMB, with Active Directory integration, DFS, shadow copies | Windows workloads needing a real Windows file share - user home directories, .NET applications, SQL Server file shares, anything expecting NTFS ACLs |
| **FSx for Lustre** | Lustre (POSIX) | HPC and ML - hundreds of GB/s, sub-millisecond latency, and native S3 integration. Genomics, seismic processing, training data |
| **FSx for NetApp ONTAP** | NFS, SMB, **and iSCSI** simultaneously | Lift-and-shift of a NetApp estate; multi-protocol access; you want ONTAP's snapshots, cloning, dedup and SnapMirror |
| **FSx for OpenZFS** | NFS | Linux workloads wanting ZFS semantics - snapshots, clones, compression - with low latency; a general-purpose NFS alternative to EFS with better latency |

The selection logic in one line each: **Windows applications → FSx for Windows. HPC or ML training at extreme throughput → Lustre. You already run NetApp, or you need NFS and SMB on the same data → ONTAP. You want low-latency NFS with snapshots and EFS is too slow or too expensive → OpenZFS.**

The trade-off against EFS is worth stating: **EFS is serverless - no capacity planning, no throughput sizing, multi-AZ by default. Every FSx variant is provisioned** - you choose capacity and throughput and manage them, and most deployments are single-AZ by default with Multi-AZ as a more expensive option. You take on operational work in exchange for protocol support or performance that EFS cannot provide. If neither of those is the reason, use EFS.

*Hook: an FSx deployment you chose over EFS, and the specific requirement that forced it.*

### Q40. FSx for Lustre linked to S3

The linkage makes an S3 bucket (or prefix) appear as a **POSIX directory tree in the Lustre filesystem**. On creation, Lustre imports the bucket's *metadata* - so files appear immediately with the right names and sizes - and the **object contents are loaded lazily on first read**, or eagerly if you preload. Writes can be exported back to S3, either explicitly through a data repository task or automatically with the newer data repository associations.

The pattern this enables is the standard HPC and ML training loop:

1. Data lives permanently in **S3**, which is cheap, durable and the organization's data lake.
2. When a job runs, spin up a **Lustre filesystem linked to the relevant prefix** - creation takes minutes.
3. The compute cluster gets a POSIX filesystem with **hundreds of GB/s of aggregate throughput** and sub-millisecond latency, which is what training and simulation workloads need and what S3's object API cannot provide.
4. Results are **exported back to S3**.
5. **Delete the filesystem.** You pay for Lustre only for the duration of the job.

That last step is the whole economic argument: Lustre is expensive per GB-month, S3 is not, and the linkage makes Lustre an ephemeral accelerator over durable storage rather than a place data lives. A team that leaves a large persistent Lustre filesystem running is paying for a cache they use a few hours a week.

The trade-off: **the lazy load means the first epoch of a training run is slow** while data hydrates - the same shape as EBS snapshot hydration (Q29) - so preloading matters when the job is short relative to the data size. And the S3 linkage is not a live two-way sync; changes on either side need an explicit task to reconcile, and treating it as a mirror leads to lost work.

*Hook: an HPC or ML data pipeline where the storage tier was the bottleneck, and what you moved it to.*

### Q41. Storage Gateway modes

A hybrid appliance - a VM, a hardware appliance, or an EC2 instance - that presents on-premises-friendly protocols locally and stores the data in AWS, with a local cache for hot data.

| Mode | Presents locally | Stores in | Real use |
| --- | --- | --- | --- |
| **S3 File Gateway** | NFS or SMB | S3 objects, one file per object | An application writes files to a share; they land in S3 as objects that a data pipeline can read. The bridge between a file-based legacy application and a data lake. |
| **FSx File Gateway** | SMB | FSx for Windows | Low-latency local access to an FSx for Windows filesystem from a branch office. |
| **Volume Gateway** | **iSCSI block volumes** | EBS snapshots in S3 | Backing up on-premises block storage to AWS, or presenting cloud-backed volumes to servers that need block devices. Cached mode keeps hot data local; stored mode keeps all data local and asynchronously backs it up. |
| **Tape Gateway** | **A virtual tape library (VTL)** | S3 and Glacier | Replacing a physical tape library without changing the backup software. NetBackup or Veeam thinks it is writing tapes; the tapes are objects in Glacier. |

Three genuinely real uses: **Tape Gateway is the strongest** - it eliminates physical tape handling and off-site storage with no change to the backup software, and the business case writes itself. **S3 File Gateway** is the standard way to get a legacy application's file output into a data lake without touching the application. **Volume Gateway in cached mode** extends on-premises storage capacity without buying an array.

The caveat to state: Storage Gateway is a **hybrid** tool, and its value ends when the workload moves to AWS. Deploying it for a workload already in AWS is almost always the wrong answer - use the native service directly.

*Hook: a hybrid storage integration you built, and whether the gateway was a migration step or a permanent fixture.*

### Q42. Storage Gateway versus DataSync

They look similar and solve different problems:

- **DataSync is a transfer service.** It moves data from A to B - on-premises NFS/SMB/HDFS/object storage to S3, EFS or FSx, or between AWS storage services - on a schedule or on demand, with validation, encryption, incremental transfer and bandwidth throttling. It is a **migration and replication** tool with a defined start and end per task.
- **Storage Gateway is an access service.** It presents an ongoing protocol endpoint that on-premises systems read and write through, continuously, with AWS as the backing store. There is no "job"; it is a permanent part of the data path.

The distinction in one line: **DataSync copies data; Storage Gateway serves it.**

When you use both, which is common in a migration: **DataSync performs the bulk initial transfer** - it is far faster, parallel, validated and purpose-built for moving terabytes - and then **Storage Gateway provides ongoing access** for the applications that have not yet moved and still expect a local share. Trying to do the bulk migration through a File Gateway is slow and painful; trying to give a legacy application ongoing NFS access through DataSync is impossible.

The third option that belongs in the comparison: **for a one-off transfer where the network is the constraint, neither - use Snowball** (Q188).

*Hook: a data migration where you used both tools, and how you split the work between them.*

### Q43. AWS Backup

A centralized backup service that orchestrates backups **across services** - EBS, EC2 instances, RDS and Aurora, DynamoDB, EFS, FSx, S3, Storage Gateway volumes, DocumentDB, Neptune, Redshift, and VMware workloads.

What it centralizes that per-service backups do not:

1. **One policy for everything.** A single backup plan applies to resources across services, rather than snapshot lifecycle rules on EBS, automated backups on RDS, PITR on DynamoDB, and a cron job for the rest - each configured differently and each capable of being forgotten.
2. **Compliance reporting.** A single view of what is protected, what is not, and whether the policy was met. This is the thing auditors ask for and the thing per-service backups cannot produce.
3. **Cross-account and cross-region copy** as a policy attribute rather than a bespoke automation.
4. **Immutability** through Vault Lock (Q44).
5. **Resource selection by tag**, so a new resource with the right tag is protected automatically - which is what makes coverage complete rather than aspirational.

The object model: a **backup plan** contains rules (schedule, retention, lifecycle to cold storage, copy actions); a **backup selection** decides which resources the plan covers, by tag or ARN; a **backup vault** holds the recovery points and is the encryption and access-control boundary.

The trade-offs, honestly: AWS Backup's per-service capability is sometimes **behind the native service** - RDS PITR through Backup is more limited than RDS's own, and restores can be slower or less granular. And warm storage in a vault is billed on top of the underlying snapshot cost in some cases. The usual landing point is **AWS Backup as the governance and compliance layer for the whole estate**, with native mechanisms retained where they are genuinely better and explicitly documented as exceptions.

*Hook: a backup consolidation you ran, and what you discovered was unprotected.*

### Q44. Vault Lock, cross-account and cross-region copy

Three controls, three distinct threat models - and naming them separately is the answer:

**Vault Lock** makes recovery points **immutable** - a WORM control. In **governance mode** it can be removed by a privileged principal; in **compliance mode** it cannot be removed by anyone, including the root user, once the cooling-off period expires. The threat model is **an attacker (or an insider, or a mistake) deleting the backups before or during the attack**, which is exactly what ransomware operators do first. Encryption does not help here and neither does replication - only immutability does.

**Cross-account copy** puts a copy in an account with a **different set of credentials and a different trust boundary**. The threat model is **compromise of the production account**: an attacker with full administrative access to production cannot reach the backups, because they are governed by a different account's IAM and typically an SCP that prevents deletion. This is the single highest-value backup control most organizations do not have.

**Cross-region copy** protects against **a regional event** - the availability threat, not the security one. It is also, in practice, a data-residency question you must check before enabling.

The combination worth recommending: **backups written to a vault in a separate, tightly locked backup account, in a second region, with Vault Lock in compliance mode and a retention period matching the obligation.** That covers the accidental deletion, the malicious insider, the compromised production account and the regional outage - and each of those is a different failure that a single mechanism does not address.

*Hook: a backup isolation design you drove, and the threat that motivated it.*

### Q45. "We have snapshots, so we have backups"

Four things that claim is missing:

1. **Consistency.** An EBS snapshot is **crash-consistent, not application-consistent**. For a running database it captures whatever was on disk at that instant, including a partially written transaction. Recovery may work through crash recovery - or may not. A real backup either quiesces the application, uses the database's own mechanism, or uses a pre/post script to flush and freeze the filesystem.
2. **A tested restore.** A backup you have not restored is a hypothesis. The number of organizations that discover at recovery time that the snapshot is missing a volume, or that nobody knows the encryption key, or that the restored instance cannot start because a dependent configuration was never captured, is not small. **Backups are validated by restoring them, on a schedule, with the time measured** - and that measured time is your actual RTO (Q46).
3. **Isolation and immutability.** Snapshots in the same account can be deleted by the same credentials that manage the resources. A compromise or a mistaken automation deletes the resource and its backups together (Q44).
4. **Completeness and retention policy.** Snapshots typically cover volumes, not: the database's transaction logs for point-in-time recovery, the configuration and IaC needed to rebuild the surrounding infrastructure, secrets and keys, and anything living outside EBS - S3 buckets, DynamoDB tables, parameter values. A "backup" that restores a disk into a world that no longer exists is not a recovery capability.

The sentence that lands: **"snapshots are a component of a backup strategy; the strategy is the retention policy, the isolation, the consistency mechanism and the tested restore."**

*Hook: a restore that failed or surprised you, and what you changed about the backup design.*

### Q46. Deriving RTO and RPO, and proving them

**RPO** - how much data you can lose - is determined by **backup frequency and replication lag**. Hourly snapshots is a one-hour RPO at best; continuous replication or transaction log shipping gives minutes or seconds. **RTO** - how long recovery takes - is the sum of every step in the actual recovery path, and it is almost always dominated by steps nobody counted.

The honest RTO calculation for a database restore:

```
detect + decide + provision infrastructure + restore data
  + hydrate/warm (Q29) + apply logs + validate + cut traffic over + DNS propagation
```

Teams quote the "restore data" number and call it the RTO. In practice detection and decision alone are often 15-30 minutes, and DNS TTL adds more (Q88). This is why measured RTOs are routinely 3-5 times the stated target.

**Proving rather than asserting** - the practices that turn the number into a fact:

- **Scheduled restore tests**, quarterly at minimum, into an isolated environment, with the wall-clock time recorded as the official RTO. Automate them so the cost of running one is near zero, because a manual test happens once and never again.
- **Automated validation** of the restored data - row counts, checksums, a smoke test of the application against it - so "the restore completed" is distinguished from "the data is correct".
- **A game day** that runs the full path including the human steps, because the technical restore is rarely the slow part.
- **Track the measured number in the same place as the target**, so the gap is visible to the people who set the target.

The framing to use with a business stakeholder: **"our tested RTO is four hours; the target is one; closing that gap costs X."** That converts an aspiration into a funded decision, which is the job.

*Hook: a restore test whose measured time differed from the documented RTO, and what you did with the number.*

### Q47. EFS with ECS and EKS

**ECS**: you declare an EFS volume in the task definition, optionally with an access point and IAM authorization, and mount it into the container. Fargate supports EFS natively - which is notable because Fargate has no persistent local storage, so EFS is the mechanism for shared or persistent state. **EKS**: the **EFS CSI driver** provides a StorageClass; you can provision access points dynamically per PersistentVolumeClaim, and unlike EBS, an EFS volume supports `ReadWriteMany` so pods across nodes and AZs share it.

The two things that commonly go wrong:

1. **Permissions - and it is almost always this.** There are two independent layers (Q38): **IAM** (can this task role mount and connect to the filesystem or access point?) and **POSIX** (can this UID write to this directory?). The classic symptom is a successful mount and `Permission denied` on the first write, because the container runs as a non-root UID that does not own the directory. The fix is an **access point with an enforced POSIX identity** matching the container's user, which also removes the need for the container to run as root. On EKS add a third layer: the CSI driver's own service account needs an IRSA or Pod Identity role, and its absence produces a mount failure that looks like a network problem.
2. **Networking.** The mount target's **security group must allow NFS (TCP 2049) from the task or node security group**, there must be a mount target **in every AZ where tasks run** (or you silently pay cross-AZ charges and latency, Q38), and a Fargate task in a private subnet needs the route to reach it. A missing mount target in one AZ produces the maddening symptom of tasks that work or fail depending on where they are scheduled.

The third thing, which is not a failure but a design mistake: **using EFS for something that should not be shared.** Container logs, caches and scratch space on EFS give you the small-file performance problem of Q36 plus a shared failure domain. EFS is for state that genuinely must be shared.

*Hook: an EFS-in-containers problem you debugged, and which of the two layers it turned out to be.*

### Q48. Storage for a media company

**Clarify first**: how many concurrent editors and what resolution - 4K ProRes streams need hundreds of MB/s *per editor*? Are editors on-premises, in AWS on workstations, or remote? What is the retrieval expectation on the archive - an hour, a day, or instant? Is there a compliance retention obligation or just a business one? What is the annual ingest volume, because that determines whether the archive is 100 TB or 10 PB?

**The three tiers, each with a different answer:**

**Ingest.** Media lands in **S3** via multipart upload, with **Transfer Acceleration** if contributors are geographically distant (Q191), or a **Snowball** for bulk backlog. S3 is the landing zone and the permanent source of truth for originals - it is cheap, durable, and event-driven so ingest can trigger a processing pipeline. Originals go to Standard briefly, then lifecycle down. Proxy/preview generation happens on ingest via an event-driven pipeline, because editors should work with proxies, not originals.

**Editing.** This is the tier that decides the architecture, because collaborative 4K editing is a **shared-filesystem, high-throughput, low-latency** problem that S3 cannot serve directly.

- **FSx for Windows File Server** if the editors are on Premiere or Avid on Windows workstations, which is the common case - SMB is what the tooling expects, and AD integration handles the user model.
- **FSx for Lustre** if the workload is rendering or transcoding at extreme aggregate throughput rather than interactive editing, linked to the S3 bucket so working sets hydrate on demand and results export back (Q40).
- **FSx for NetApp ONTAP** if they have an existing NetApp estate on-premises and want SnapMirror-based hybrid workflows - a genuine lift-and-shift accelerator.
- **Not EFS**: NFS latency and the cost at this scale make it the wrong tool for interactive 4K.

Pair this with **workstations in AWS** (EC2 with GPU, accessed over DCV or a partner protocol) if editors are remote - because moving 4K over the internet to a local workstation is a worse problem than moving pixels.

**Archive.** **S3 lifecycle** down the class ladder based on the retrieval expectation, and this is where the retrieval question I asked earlier pays off:

| Retrieval need | Class |
| --- | --- |
| Occasionally, immediately (a client calls asking for last year's footage) | **Glacier Instant Retrieval** |
| Planned, hours acceptable | Glacier Flexible Retrieval |
| Effectively never, compliance only | Deep Archive |

For a media company, **Glacier Instant Retrieval is usually the right archive tier** despite costing more than Deep Archive, because "we can get it in twelve hours" loses business and the price difference across a decade rarely justifies it. Add **Object Lock** if there is a legal retention obligation, and **Intelligent-Tiering** for the middle band where access is genuinely unpredictable.

**The cross-cutting decisions**: a metadata catalogue in DynamoDB or a MAM product so nobody has to `LIST` a bucket with tens of millions of objects; **transitions cost money per object**, so lifecycle rules on millions of small proxy files need arithmetic before they are enabled; and **egress is the hidden line item** - delivering to clients should go through CloudFront, not direct from S3.

*Hook: a media or large-file storage design, the tier that dominated the cost, and the retrieval assumption you had to challenge.*

---

## 4. Load balancing: ALB, NLB, GWLB

### Q49. The load balancer family in one line each

- **Application Load Balancer** - layer 7, HTTP/HTTPS/gRPC. Routes on content (host, path, header, method, query, source IP), terminates TLS, integrates with WAF and Cognito, targets can be instances, IPs, Lambda functions or another ALB.
- **Network Load Balancer** - layer 4, TCP/UDP/TLS. Extreme throughput, ultra-low latency, **static IP per AZ**, preserves the client source IP, handles millions of requests per second with no pre-warming.
- **Gateway Load Balancer** - layer 3. Deploys and scales **third-party virtual network appliances** (firewalls, IDS/IPS, deep packet inspection) transparently, using GENEVE encapsulation on port 6081.
- **Classic Load Balancer** - the previous generation, layer 4 and 7. Legacy only; there is no reason to create one today, and its presence in an estate is a migration item.

The one-line selection rule: **ALB for HTTP applications, NLB for non-HTTP protocols or when you need static IPs or extreme scale, GWLB when you are inserting a security appliance into the traffic path.**

*Hook: a load balancer migration you ran - Classic to ALB, or ALB to NLB - and what forced it.*

### Q50. ALB versus NLB - the real differences

| | ALB | NLB |
| --- | --- | --- |
| **Layer** | 7 (HTTP/HTTPS/gRPC) | 4 (TCP/UDP/TLS) |
| **Routing** | Content-based: host, path, header, query, method, source IP | Flow-based hash on the 5-tuple |
| **Latency added** | Low milliseconds | Tens of microseconds |
| **Client IP** | In `X-Forwarded-For`; the target sees the ALB's IP | **Preserved** by default for instance targets |
| **Addressing** | DNS name, IPs change | **One static IP per AZ**, and Elastic IPs can be assigned |
| **TLS** | Terminates, SNI, ACM, and can re-encrypt | Terminates TLS, or passes TCP straight through |
| **Protocols** | HTTP only | Anything over TCP or UDP - databases, MQTT, syslog, game protocols |
| **Scaling** | Scales, but very large sudden spikes benefit from ramping | Handles millions of rps instantly, no warming |
| **Targets** | Instance, IP, Lambda, ALB | Instance, IP, ALB |
| **WAF** | Yes | No |

**What actually drives the decision, most often**: whether the protocol is HTTP. If it is, ALB, because content-based routing and WAF are worth far more than the microseconds of latency. If it is not - a database proxy, MQTT, a custom TCP protocol, UDP - the decision is made for you.

**The three secondary drivers**, in the order they come up in real designs: a **partner or firewall needs a static IP to allowlist** (NLB, or Global Accelerator in front of an ALB); the backend needs to see the **true client IP at the TCP layer** rather than trusting a header (NLB); or the traffic profile is **extreme and spiky** (NLB). Everything else is usually secondary to "is it HTTP".

*Hook: a case where you chose NLB over ALB, and which of these drivers decided it.*

### Q51. ALB plus mTLS, static IP and a million rps

Take the three requirements separately, because they have different answers and the naive response - "switch to NLB" - is wrong on the first one.

**Mutual TLS to the backend.** ALB now supports **mTLS for client authentication** (verify mode with a trust store, or passthrough mode where the client certificate is forwarded to the target in headers), so mTLS *from clients* is no longer a reason to abandon ALB. If the requirement is mTLS **from the ALB to the target**, ALB re-encrypts to the target but does not present a client certificate - so that specific requirement does mean either NLB with TCP passthrough (letting the target terminate mTLS itself) or a mesh handling mTLS inside the network. **I would clarify which of the two is meant, because it changes the answer completely** - and that clarification is the most valuable thing to say here.

**A static IP for a partner allowlist.** Do not switch to NLB for this. **Put Global Accelerator in front of the ALB**: it provides two static anycast IPs, keeps all of the ALB's layer-7 capability, and improves global latency as a bonus (Q109). The alternative pattern - an NLB in front of the ALB - also works and is cheaper, and is worth mentioning as the option when you do not need Global Accelerator's routing.

**One million requests per second.** ALB does scale to this, but it scales *elastically*, so a step function to that volume can outrun it while an NLB absorbs it instantly. The question to ask is **what the arrival shape is**: a million rps reached over ten minutes is fine on ALB; a million rps arriving in five seconds is not. If it is genuinely instant, NLB or Global Accelerator in front is the answer.

**The synthesis**: `Global Accelerator (static IPs) → ALB (mTLS client auth, content routing, WAF) → targets`, with NLB only if the mTLS requirement turns out to be target-side or the traffic shape is truly instantaneous. **The interviewer is testing whether you accept the framing or decompose it**, and the decomposition is the answer.

*Hook: a requirement set that looked like it forced a load balancer change, and how you satisfied it without one.*

### Q52. Target groups and target types

A **target group** is a routing destination with its own protocol, port, health check configuration and attributes. Load balancer listeners have rules that forward to target groups; the target group owns the targets and their health.

| Type | What it enables |
| --- | --- |
| **`instance`** | Register EC2 instance IDs; traffic goes to the instance's primary IP on the target port. Simple, and **preserves the client IP on NLB**. Cannot reach targets outside the VPC. |
| **`ip`** | Register IP addresses directly - which unlocks **containers with awsvpc networking (ECS/EKS pods), on-premises targets over Direct Connect or VPN, and peered VPCs**. The dominant type in a container estate. |
| **`lambda`** | ALB invokes a Lambda function as the target. Lets you put serverless behind an ALB path rule instead of API Gateway - useful when most of the application is containers and one path is a function. |
| **`alb`** | An NLB forwards to an ALB. The pattern behind "static IP plus layer-7 routing" (Q51) and PrivateLink-fronted services, since PrivateLink requires an NLB. |

The design points that follow: **`ip` targets are what make ECS and EKS work**, because each task or pod has its own ENI and registering instance IDs would be meaningless. **`alb` as a target type is the composition primitive** that lets you get NLB properties (static IP, PrivateLink compatibility) and ALB properties (content routing, WAF) at once. And **weighted target groups** on an ALB - two groups behind one rule with a percentage split - is the mechanism for blue/green and canary at the load balancer, which is how you avoid building traffic shifting in application code (Q57).

*Hook: a target type choice that unlocked something - on-premises targets, containers, or a composition pattern.*

### Q53. Health checks on ALB versus NLB

**ALB** health checks are HTTP(S): a path, an expected status code range, interval, timeout, and healthy/unhealthy thresholds. They test the application. **NLB** health checks can be TCP (does the port accept a connection), HTTP or HTTPS. A TCP check tests only that something is listening - which is much weaker, and the default trap.

The differences that matter operationally:

- **Semantics.** An ALB check on `/health` that queries dependencies tells you the application works. An NLB TCP check tells you the socket is open, which a completely broken application will happily satisfy. **If you use NLB, use an HTTP health check where the protocol allows it.**
- **Failure behaviour.** NLB checks are more aggressive by default and NLB does **not** have the same connection-draining semantics for existing flows - an unhealthy TCP target has its flows terminated rather than gracefully completed.
- **All targets unhealthy.** ALB returns 503. **NLB, if every target in a target group is unhealthy, sends traffic to all of them anyway** - "fail open" - on the theory that a broken health check should not black-hole the service. This surprises people and is worth knowing, because it means an NLB service can look healthy while every target is failing.
- **Cross-zone interaction.** With cross-zone disabled on an NLB (the default), a zone whose targets are all unhealthy still receives its share of DNS-directed traffic unless the zonal health check removes the zone's IP from DNS.

The general rule for both: **the health check must exercise the real request path.** A handler that returns 200 unconditionally is decoration - the failure mode from the parent pack's rollout scenario. But do not go too far the other way: a health check that verifies every downstream dependency turns a downstream blip into a full fleet ejection. The balance is **check the things this instance owns; report degraded dependencies through metrics, not through the health check.**

*Hook: a health check that was either too shallow or too deep, and the incident that revealed it.*

### Q54. Healthy targets, 502s

A 502 from an ALB means the target returned something the ALB could not interpret as a valid HTTP response, or closed the connection unexpectedly. Health checks pass because the health path is cheap and the failing path is not. Five distinct causes:

1. **Keep-alive timeout mismatch.** The backend's idle timeout is shorter than the ALB's (default 60 s), so the backend closes a pooled connection just as the ALB sends a request on it. This is **the single most common cause** and produces intermittent, low-rate, unreproducible 502s. Fix: backend keep-alive strictly greater than the ALB idle timeout (Q64).
2. **The application crashed or the request timed out mid-response.** An OOM kill, an unhandled exception after headers were sent, or a request exceeding the target's own timeout leaves a truncated response. Correlates with backend errors and restarts.
3. **A malformed or oversized response.** Headers exceeding the ALB's limits, duplicate or invalid header names, a bad `Content-Length`, or a non-HTTP response on an HTTP listener. Deterministic - the same request always fails.
4. **TLS mismatch on the target group.** The target group is configured for HTTPS and the target speaks HTTP, or vice versa, or the cipher/protocol negotiation fails. Usually total rather than intermittent, and appears immediately after a configuration change.
5. **The target is saturated** - the accept queue is full, the thread pool is exhausted, or GC pause exceeds the ALB's timeout - so connections are refused or reset while the cheap health endpoint still answers.

**The diagnostic that separates them quickly**: ALB **access logs** contain `elb_status_code`, `target_status_code` and the three timing fields. If `target_status_code` is `-`, the target never produced a response (causes 1, 2, 5). If it has a value, the target responded and the ALB rejected it (cause 3). `target_processing_time` of `-1` points at a connection failure (cause 4). Then correlate the 502 timestamps with backend restarts and GC logs.

*Hook: a 502 investigation, and which of these it turned out to be.*

### Q55. Cross-zone load balancing

Without cross-zone, each load balancer node distributes only to targets **in its own AZ**. DNS hands clients roughly equal traffic per AZ, so if AZ-a has 2 targets and AZ-b has 8, each AZ-a target receives four times the load. With cross-zone enabled, every node distributes across **all** targets in all AZs, evening it out.

The defaults are the part to remember:

| | Default | Charged for cross-AZ traffic? |
| --- | --- | --- |
| **ALB** | **On**, and cannot be disabled at the load balancer level (can be turned off per target group) | **No** - cross-zone traffic on ALB is free |
| **NLB** | **Off** | **Yes** - standard cross-AZ data transfer charges apply |
| **GWLB** | Off | Yes |

So on ALB it is free and on by default; on NLB you are opting in to **$0.01/GB each way** for the traffic that crosses zones. For a high-throughput NLB moving hundreds of TB, that is a real number and the reason the default is off.

**When turning it off hurts you**: whenever target counts are uneven across AZs - which happens constantly with ASG scaling activity, an AZ with capacity constraints, spot interruptions concentrated in one pool, or simply a target count that does not divide evenly by three. It also hurts during a **partial AZ failure**: the surviving targets in a degraded AZ absorb the full DNS share for that zone rather than being backed up by the other zones. The mitigation if you keep it off is to ensure balanced target counts per AZ and to rely on zonal health checks removing an AZ from DNS entirely.

The rule I would give: **leave it on for ALB (you have no choice and it is free); on NLB, enable it unless the cross-AZ bill is material and your target counts are provably balanced.**

*Hook: an imbalance caused by cross-zone settings, or a cross-AZ bill you traced to an NLB.*

### Q56. Sticky sessions

**ALB stickiness** uses a cookie: either the load-balancer-generated `AWSALB` (duration-based, you set the lifetime) or an **application-based cookie** where your app sets a cookie the ALB honours. The ALB reads the cookie and routes to the same target. **NLB stickiness** is at layer 4 - source IP affinity, since there are no cookies to read - configured per target group.

What stickiness breaks, which is the real content of the answer:

1. **Even load distribution.** Long-lived sessions pin users to targets, so a newly scaled-out instance receives only new sessions and the old instances stay hot. After a scaling event the fleet can be badly unbalanced for as long as sessions live.
2. **Graceful scale-in and deploys.** Terminating a target drops its sessions. With stickiness, that means those users lose their state, not merely their connection - so every deployment becomes user-visible unless sessions are externalized anyway.
3. **The failure blast radius.** An instance failure logs out its whole cohort rather than causing a retried request.
4. **NLB's source-IP affinity specifically** behaves badly behind a corporate NAT or a mobile carrier, where thousands of users share a source IP and all land on one target.

The position to take: **stickiness is a workaround for server-side session state, and the correct fix is to externalize the session** - into ElastiCache/Redis, DynamoDB, or a signed token held by the client. Then any target can serve any request, scaling and deploys are invisible, and you delete a category of problems. I would use stickiness deliberately in two cases: **a legacy application that cannot be changed**, and **a genuine performance optimization** where a local cache makes affinity valuable and losing it is merely slower, not incorrect.

*Hook: a session-state externalization you drove, and what it unlocked operationally.*

### Q57. ALB routing rules and weighted target groups

Listener rules evaluate in priority order and match on **host header, path, HTTP header, HTTP method, query string, and source IP**, with actions of forward, redirect, fixed response, authenticate (Cognito or OIDC), or forward to **weighted target groups**.

What you can build with these that people usually build in code:

- **Path-based routing to different services** - `/api/orders/*` to one target group, `/api/pricing/*` to another. This is an API gateway function done at the load balancer, and it removes a routing service from the architecture.
- **HTTP-to-HTTPS redirect** as a listener rule, rather than an application filter that every service must implement identically.
- **Maintenance pages and fixed responses** without an origin - a fixed 503 with a JSON body during a planned outage, configured in seconds.
- **Authentication at the edge** - the ALB can require an OIDC or Cognito login before the request reaches the target, which means unauthenticated traffic never touches the application.
- **Blue/green and canary via weighted target groups** - two groups behind one rule with a 95/5 split, shifted progressively. This is the important one: **traffic shifting belongs in the infrastructure, not in application code**, and building it with weights plus CloudWatch alarms plus automated rollback gets you progressive delivery without a mesh.
- **Header-based routing for testing** - route requests with `X-Version: canary` to the new target group, so testers opt in deterministically while public traffic stays on stable.

The limits worth knowing so you do not over-invest: rules per listener are capped (100 by default, adjustable), conditions per rule are limited, and there is **no percentage-based routing at the rule level other than target group weights**, no request rewriting beyond redirects, and no response transformation. When you need more than that, you have outgrown the ALB and want API Gateway or a mesh - and knowing where that line is matters more than knowing the feature list.

*Hook: routing or traffic-shifting logic you moved out of application code into the load balancer.*

### Q58. TLS on a load balancer

**Termination** at the ALB or NLB is the default: the load balancer holds the certificate (usually from **ACM**, which handles renewal automatically and is free for use with AWS services), decrypts, and forwards to the target. **SNI** lets one listener serve **many certificates** - up to 25 per listener by default, plus a default certificate - selecting by the hostname the client requested, which is how a multi-tenant service serves customer domains from one ALB.

**End-to-end encryption** means the load balancer re-encrypts to the target over a second TLS connection. The trade-offs:

**In favour of re-encrypting:** compliance regimes frequently require encryption in transit *everywhere*, not just at the edge; it protects against anything with visibility into the VPC network path; and for regulated data it is usually simpler to satisfy the auditor than to argue that the VPC is trusted.

**Against:** it costs CPU on both ends (though on Nitro this is modest); it doubles the certificate management problem, because the **ALB does not validate the target's certificate** - it accepts self-signed certificates and does not check the hostname, so the protection is against passive observation rather than active man-in-the-middle, and pretending otherwise is a common overstatement; and it complicates debugging.

The pragmatic position: **terminate at the edge with ACM, and re-encrypt to the target when a compliance requirement or a genuinely untrusted network segment demands it.** Note that AWS encrypts inter-AZ traffic at the physical layer within a region, which is often sufficient for the "data in transit" control - and knowing that is what lets you have an informed conversation with an auditor rather than reflexively enabling everything.

For NLB there is a third option worth naming: **TCP passthrough**, where the load balancer does not terminate at all and the target handles TLS. That is what you use for mTLS terminated at the application (Q51) or for protocols the load balancer does not understand.

*Hook: a TLS termination decision driven by compliance, and what you actually had to demonstrate.*

### Q59. Deregistration delay and slow start

**Deregistration delay** (connection draining, default **300 seconds**) is how long the load balancer keeps sending *existing* in-flight requests to a target after it has been deregistered, while sending no new ones. It exists so that removing a target - a deploy, a scale-in, a manual replacement - does not kill requests in progress.

**Slow start** (off by default) ramps traffic to a *newly registered* target linearly over a configured period, instead of giving it a full share immediately. It exists for targets that need to warm up: a JVM that needs JIT compilation, a connection pool that needs to fill, a local cache that needs to populate.

**What breaks when deregistration delay is shorter than your longest request**: those requests are cut off mid-flight. The client sees a connection reset or a 502, and the damage depends on the operation - a truncated GET is an annoyance, a truncated payment POST is a support case and possibly a double charge on retry. Every deployment and every scale-in event then produces a small number of errors, which teams often accept as background noise for months without realizing it is configuration.

So the rule: **deregistration delay must exceed your p99.9 request duration**, and it should be set from measurement rather than left at the default. The default of 300 seconds is *too long* for most HTTP services and slows every deploy; 30-60 seconds is typical for a normal API. But for a service with long-running requests - a report generator, a file upload, a streaming endpoint - it must be longer.

The interaction to name: **deregistration delay must be shorter than the Spot interruption window (two minutes) if you run on Spot** (Q10), and it must be shorter than the ASG lifecycle hook's timeout, or the instance is terminated while the load balancer is still draining it. Those three numbers - request duration, deregistration delay, lifecycle hook timeout - have to be ordered correctly, and they usually are not.

*Hook: a deploy or scale-in that produced errors, and the timeout ordering you fixed.*

### Q60. NLB, client IP preservation and proxy protocol

NLB **preserves the client source IP by default for instance and IP targets** - the target sees the real client address in the packet, because NLB operates at layer 4 without rewriting the source. This is one of the main reasons to choose NLB: applications that need the client IP for geolocation, rate limiting or logging get it without parsing headers.

**Proxy protocol v2** is for the case where preservation is *not* available or not sufficient: when the NLB terminates TLS, when targets are behind a PrivateLink endpoint, or when the target is registered by IP in a way that loses the original address. It prepends a binary header to the TCP connection carrying the source and destination addresses, plus TLS metadata - and **the target application must be able to parse it**, which nginx, HAProxy, Envoy and most proxies can, but a plain application server generally cannot without configuration. Enabling it on the target group while the target does not expect it corrupts the first bytes of every connection, which manifests as immediate protocol errors.

**The surprising security group interaction**, which is the part of this question that catches people: because the client IP is preserved, **the target's security group must allow traffic from the client's IP range, not from the NLB.** With an ALB you allow the ALB's security group and you are done; with an NLB preserving client IPs, allowing only the VPC CIDR results in every external connection being dropped. Worse, **NLB itself has no security group** in its classic form (security groups for NLB are now supported but must be explicitly enabled and are not retrofittable to existing NLBs), so historically the target's security group was the only enforcement point and it had to be open to the world for a public NLB - which is a genuine security consideration, not a footnote.

The corollary people miss: with client IP preservation on, **an instance cannot reach the NLB in front of itself** (hairpinning fails), which breaks service-to-service calls that route through the same load balancer.

*Hook: an NLB security group or hairpinning problem, and how long it took to identify.*

### Q61. Gateway Load Balancer

GWLB solves a problem the other two cannot: **transparently inserting third-party network appliances - firewalls, IDS/IPS, DPI - into the traffic path, with elastic scaling and health checking, without changing routing on every VPC.**

Before it, inserting a firewall appliance meant building your own high-availability pair with failover scripts, or routing everything through a single choke point, and scaling was manual. GWLB makes a fleet of appliances behave like a single, scalable, self-healing service.

**How it works**: GWLB operates at **layer 3**. Traffic is directed to a **Gateway Load Balancer Endpoint** (a VPC endpoint) via route table entries, GWLB encapsulates the original packet in **GENEVE (port 6081)** and forwards it to an appliance in the target fleet, the appliance inspects and returns it, and GWLB decapsulates and forwards it on to its original destination. **GENEVE's role is to preserve the original packet completely** - source, destination, everything - so the appliance sees traffic exactly as it was sent and the flow is transparent to both endpoints. GWLB also maintains **flow stickiness** using a 5-tuple hash, so both directions of a connection reach the same appliance, which stateful firewalls require.

The typical deployment is a **centralized inspection VPC** (Q130): spoke VPCs route egress or east-west traffic through Transit Gateway to an inspection VPC, where GWLB endpoints hand traffic to the appliance fleet.

The trade-offs: **latency** from the extra hop and the encapsulation; **cost**, which is the GWLB hourly and per-GB charge plus the endpoint charges plus the appliance licences plus the Transit Gateway data processing - this stacks up quickly; and **an availability dependency** on the appliance fleet for traffic that previously flowed directly. And the honest question to ask before recommending it: whether **AWS Network Firewall** (Q126) does what you need, since it is managed and removes the appliance operational burden entirely. GWLB is the right answer chiefly when the organization has standardized on a specific vendor's appliance and its rule set, which is a real and common constraint.

*Hook: a network inspection requirement, and whether you used a managed service or an appliance fleet.*

### Q62. Load balancer metrics and what they tell you

The metrics I would alarm on, per target group where possible:

| Metric | Why |
| --- | --- |
| `HTTPCode_ELB_5XX_Count` | The load balancer itself failed - no healthy targets, or 502/503/504 generated by the ALB |
| `HTTPCode_Target_5XX_Count` | The application failed. Separating these two is the first diagnostic split |
| `TargetResponseTime` (p99, not average) | The user-facing latency signal |
| `UnHealthyHostCount` | Alarm below a threshold of healthy hosts, not on any unhealthy host |
| `RejectedConnectionCount` | The ALB hit a connection limit - a capacity signal |
| `TargetConnectionErrorCount` | The ALB could not connect to the target at all |
| `ActiveConnectionCount` / `NewConnectionCount` | The ratio indicates keep-alive effectiveness |
| `ConsumedLCUs` | Cost and capacity |
| `ProcessedBytes` | Traffic and cost |

**Rising `TargetResponseTime` with flat `RequestCount`** is the diagnostic in the question, and it is a valuable one: **the load is unchanged, so the slowdown is not caused by traffic.** That excludes an entire class of hypotheses and points at something in or below the target:

- a **downstream dependency** slowing - a database, a cache, a third-party API;
- **resource exhaustion inside the target** that is time-dependent rather than load-dependent - a memory leak growing GC pause time, a connection pool leaking, a thread pool filling, a disk filling;
- a **change** - a deploy, a feature flag, a configuration value, a data volume crossing a threshold that made a query fall off an index;
- **fewer healthy targets** carrying the same traffic - so check `HealthyHostCount` alongside it, because flat total `RequestCount` with half the targets means each target's load doubled.

The order I would check: healthy host count first (cheapest to rule out), then correlate with deploy events, then downstream latency, then the target's own resource metrics. The absence of a `RequestCount` change is what makes this fast - without it you would be chasing load.

*Hook: a latency investigation where the flat request count was the clue that redirected you.*

### Q63. Pre-warming in 2026

**You do not.** Pre-warming was a Classic Load Balancer practice: you raised a support ticket before a launch and AWS provisioned capacity ahead of your spike, because CLB scaled slowly.

What replaced it:

- **NLB requires no warming at all.** It handles millions of requests per second from the first second, which is why it is the answer for a genuinely instantaneous spike (Q51).
- **ALB scales automatically and much faster than CLB**, and for the overwhelming majority of launches it simply keeps up. Where there is doubt, you **load test with a realistic arrival shape** rather than requesting warming - the test both validates the scaling and finds the other bottlenecks, which are almost always the real problem.
- For **exceptional, known events** - a ticket on-sale, a product launch with a hard start time and a step function to enormous volume - the modern conversation with AWS is through your account team about **service quotas and capacity planning across the whole stack**, not a load balancer pre-warm request.

The answer that shows judgement, though, is redirecting the concern: **the load balancer is rarely the thing that fails during a launch.** The real constraints are downstream - target capacity and ASG scaling speed, database connections, Lambda concurrency, third-party rate limits, and quotas nobody checked (the parent pack's failover scenario). So my answer to the request is: "the ALB will be fine; let us load test the whole path at the expected shape and find what actually breaks." That is a more useful thing to spend the week before a launch on.

*Hook: a launch you prepared for, what you load tested, and what the actual bottleneck turned out to be.*

### Q64. Idle timeout versus backend keep-alive

The **ALB idle timeout** (default 60 seconds) is how long the ALB holds a connection with no data flowing before closing it, on both the client side and the target side. The **backend's keep-alive timeout** is how long the target holds an idle connection open.

**The backend's keep-alive must be strictly larger than the ALB's idle timeout.** A margin of a few seconds is not enough; make it comfortably larger - if the ALB is 60, set the backend to 65-75.

When it is the wrong way round, you get the race that causes Q54's intermittent 502s: the ALB has a pooled connection it believes is usable, the backend's timer expires first and it sends a FIN, and the ALB dispatches a request into a connection that is closing. The request is lost. It is intermittent, load-dependent, unreproducible in testing, and generates a small constant error rate that teams live with for months.

The specific numbers worth carrying: **nginx `keepalive_timeout` defaults to 75 seconds** (safe against a 60-second ALB); **many application servers default to much less** - older Tomcat and various embedded servers default to 20 seconds or even 5, and Go's `http.Server` has no keep-alive timeout by default but its `IdleTimeout` falls back to `ReadTimeout`. Spring Boot with embedded Tomcat is a common offender because `server.tomcat.keep-alive-timeout` is easy to leave unset while `connection-timeout` is set to something short.

The other direction matters too: **raising the ALB idle timeout above the backend's capability** does not help, and **long idle timeouts consume connection slots** on both sides. For WebSockets or streaming you raise the ALB timeout deliberately (up to 4000 seconds) and must then raise the backend's to match.

*Hook: an intermittent 502 or connection-reset problem traced to a timeout ordering.*

### Q65. Internal service-to-service load balancing for 40 services

**Clarify first**: are these all in one VPC and one account, or spread across accounts? Is the traffic HTTP/gRPC or mixed? Do you need mTLS between services, and is that a compliance requirement or an aspiration? What is the team's operational maturity - is there a platform team who can run a mesh? And what problem is actually being solved - is this a greenfield decision, or is something failing today?

**The four options, honestly:**

| Option | Cost at 40 services | Gives you | Costs you |
| --- | --- | --- | --- |
| **Internal ALB per service** | ~$16-22/month each plus LCUs = **$700-1,000/month base** | Simplicity, per-service health checks, path routing, familiar | Cost, 40 things to manage, an extra hop's latency, no mTLS or fine-grained policy |
| **One shared internal ALB, host or path rules** | One ALB | Cheap, central | A shared failure domain, rule limits (100 default), coupled deployment of routing config, a central team in every change |
| **Cloud Map (DNS service discovery)** | Near zero | No proxy hop at all - clients resolve and connect directly; cheapest and lowest latency | Client-side load balancing quality depends on the client's DNS caching; no health-based ejection beyond DNS; no retries, circuit breaking or mTLS |
| **Service mesh (App Mesh, Istio, or ECS Service Connect)** | Sidecar CPU/memory per task | mTLS everywhere, retries, circuit breaking, per-service traffic policy, uniform telemetry | Real operational complexity, a control plane to run, sidecar resource overhead, a new failure mode, and a skills requirement |

**My answer, and the reasoning**: at 40 services I would start with **ECS Service Connect** (or Cloud Map if not on ECS) as the default, and add internal ALBs only for the services that genuinely need layer-7 routing or are entry points from outside the mesh.

The reasoning is that Service Connect gives most of the mesh benefits - service discovery, client-side load balancing with health awareness, retries, and uniform metrics - **without running a mesh control plane**, and it is managed. Forty internal ALBs is roughly $10,000 a year to solve a problem that does not need a proxy. A full mesh is the right answer at a larger scale or when mTLS between services is a hard compliance requirement, but recommending Istio to an organization without a platform team is how you get an outage caused by the thing that was supposed to improve reliability.

**What would change my answer**: a stated mTLS-everywhere requirement (mesh), heavy use of gRPC with sophisticated load balancing needs (mesh or Service Connect, not DNS), services spread across many accounts and VPCs (PrivateLink or Transit Gateway becomes part of the answer), or an existing Kubernetes estate with a mesh already running (use it).

*Hook: a service-to-service communication decision at scale, what you chose, and whether you later regretted the complexity in either direction.*

---

## 5. Auto Scaling and capacity management

### Q66. The Auto Scaling group

An ASG maintains a fleet of EC2 instances across one or more AZs, replacing unhealthy ones and adjusting the count in response to policy. Its components: a **launch template** (what to launch), **subnets across AZs** (where), **min / max / desired capacity** (how many), **health check configuration** (what "working" means), **target group attachments** (where traffic comes from), and **scaling policies** (when to change the count).

The three capacity numbers do different jobs and are frequently misunderstood:

- **Desired** is the current target. Scaling policies change it; so do you, manually. It is a *state*, not a setting - which is why setting desired in Terraform and then autoscaling causes perpetual drift, and why you usually exclude it with `ignore_changes`.
- **Minimum** is a **floor the ASG will never go below**, including for scale-in and including after failures. It is your availability guarantee: min of 2 across 2 AZs is what makes an AZ loss survivable.
- **Maximum** is a **ceiling and a cost/blast-radius control**. It is also the most common cause of "why did it not scale" - a traffic event hits max and the ASG stops, silently, with no alarm unless you added one.

The behaviour worth naming: the ASG also does **AZ rebalancing** on its own, terminating and launching instances to even out distribution, which surprises people who see unexplained instance churn. And **min is enforced even against health-check failures** - if instances keep failing, the ASG keeps launching replacements, which is how a bad AMI produces an infinite launch loop.

*Hook: an ASG whose max or min was the cause of an incident, in either direction.*

### Q67. Launch templates versus launch configurations

**Launch configurations are legacy and immutable** - you cannot modify one, so every change means creating a new configuration and updating the ASG, and they do not support newer features (T-unlimited mode, mixed instance policies, multiple network interfaces, dedicated hosts, capacity reservations, metadata options for IMDSv2). AWS has ended support for creating new ones.

**Launch templates are versioned.** Every change creates a new version; the ASG references a specific version, `$Latest`, or `$Default`.

Why versioning matters operationally, which is the real content:

1. **Rollback is a version pointer change.** A bad AMI or user-data change is reverted by pointing the ASG at the previous version and triggering an instance refresh - no reconstruction of the old configuration from memory.
2. **The `$Latest` versus pinned choice is a real decision.** `$Latest` means any template edit immediately affects new launches - including a scale-out event at 3am picking up a half-finished change. **Pinning to a specific version** and updating deliberately is the safer pattern, and it is what makes deployments explicit rather than ambient.
3. **Audit.** Version history shows what changed and when, which during an incident answers "did anything change" without archaeology.
4. **Mixed instances policies require templates**, so any Spot strategy (Q77) depends on them.

The practical guidance: **pin the ASG to a version number, manage versions from IaC, and use instance refresh to roll changes out** - that combination gives you an immutable, reviewable, revertible fleet configuration.

*Hook: a launch template version rollback, or an incident caused by `$Latest`.*

### Q68. The scaling policy types

| Policy | Mechanism | Right when | Dangerous when |
| --- | --- | --- | --- |
| **Target tracking** | You name a metric and a target value; AWS manages the CloudWatch alarms and the arithmetic to hold it | **The default for almost everything.** CPU at 50 percent, requests per target, custom backlog-per-instance | The metric does not actually correlate with capacity need - tracking CPU on an I/O-bound service scales the wrong dimension |
| **Step scaling** | Alarm thresholds map to specific capacity adjustments, with larger steps for larger breaches | You need **asymmetric or non-linear** response - add 10 instances if the breach is severe, 2 if mild | You are hand-tuning what target tracking would do better; step policies are frequently a sign of fighting the wrong metric |
| **Simple scaling** | One alarm, one adjustment, then a cooldown before anything else happens | Effectively never - superseded | Any spiky workload: the cooldown blocks further action while the situation worsens |
| **Scheduled** | Change min/max/desired at a time | **Known, calendar-driven patterns**: business hours, a nightly batch window, a marketing send, Black Friday | Used *instead of* dynamic scaling - the schedule is always wrong on the day the pattern changes |

**The combination is the real answer**: scheduled scaling to raise the *minimum* ahead of a known event, plus target tracking to handle actual demand within that envelope. Scheduled scaling should adjust the floor, not the desired count, so dynamic scaling is not fighting it.

The metric choice matters more than the policy choice. **CPU is the default and often the wrong signal** - a service bound by downstream latency, connection pool, or memory does not show CPU pressure until it is far too late. `RequestCountPerTarget` on the ALB is usually a better tracking metric for a web tier, and a **backlog-per-instance** custom metric is the right one for a queue consumer (Q79).

*Hook: a scaling policy where the metric, not the policy type, was the problem.*

### Q69. Predictive scaling

Predictive scaling uses machine learning over your historical CloudWatch data to **forecast load and scale ahead of it**, rather than reacting after the metric moves. It generates an hourly forecast for the next 48 hours and provisions capacity in advance.

What it needs: **at least 24 hours of history to start and about 14 days to be useful**, and - crucially - a **recurring, cyclical pattern**. It works by finding periodicity; a workload with no daily or weekly rhythm gives it nothing to learn.

When it beats reactive scaling: whenever **the ramp is faster than your instances can boot**. Reactive scaling is always late by the sum of the metric period, the alarm evaluation, the launch time and the warm-up - typically 3-8 minutes for a JVM on EC2. A workload that goes from 20 percent to 100 percent in five minutes every morning at 09:00 will be under-provisioned for the whole ramp every single day, no matter how well the target tracking is tuned. Predictive scaling has the capacity in place before the traffic arrives.

The right configuration: **predictive scaling for the baseline forecast, target tracking underneath for the deviations.** Run it in **forecast-only mode first** for a couple of weeks and compare the forecast against reality before letting it act - that is the step people skip, and it costs nothing.

The limits to state: it will not predict an unforecastable event (a marketing email, a news story, a competitor's outage), so it never replaces reactive scaling; and it **provisions capacity you pay for whether the forecast was right or not**, so a wrong forecast is a cost event.

*Hook: a workload with a sharp daily ramp, and how you got capacity in place ahead of it.*

### Q70. ASG oscillation

Scaling out then in every few minutes means **the act of scaling changes the metric enough to reverse the decision** - a classic control loop with too much gain and too little damping. The four settings I would look at:

1. **The target value and the metric itself.** A target that sits near the natural operating point causes constant crossing. If CPU idles at 48 percent and the target is 50, the group oscillates forever. Widen the gap, or - more often the real fix - **choose a metric that is proportional to load rather than noisy**: `RequestCountPerTarget` instead of CPU.
2. **Instance warm-up** (`EstimatedInstanceWarmup`, or the default instance warmup on the ASG). If a new instance is counted in the metric average *before* it is actually serving - while the JVM warms - it drags the average down, triggering a scale-in, which then removes capacity that was about to be needed. **This is the most common cause**, and setting warm-up to the true time-to-useful (not time-to-running) fixes it.
3. **Cooldown**, for simple and step scaling: too short and the group acts again before the previous action's effect is visible. Target tracking largely handles this itself, which is another argument for it.
4. **The scaling adjustment size.** Steps that are too large overshoot and force a correction; a group of 4 that scales by 4 will always oscillate. Percentage-based adjustments with a sensible minimum behave better across fleet sizes.

**The fifth thing, which is not a setting**: target tracking is deliberately asymmetric - it scales out aggressively and scales in conservatively - so persistent oscillation usually means one of the above is fighting that design rather than the algorithm being wrong.

The diagnostic: plot the metric against the scaling activity timeline. If the metric moves *because of* the scaling action rather than before it, it is a feedback loop (causes 1, 2, 4). If the metric is genuinely oscillating on its own, the workload is bursty and the answer is a longer metric period or a smoother metric.

*Hook: a scaling oscillation you diagnosed, and which setting fixed it.*

### Q71. Cooldown, warm-up and instance refresh

Three different mechanisms that are constantly confused:

- **Cooldown** is a *pause after a scaling activity* during which further **simple scaling** actions are suppressed. It applies to simple scaling and, in a limited way, to manual changes; it does **not** apply to target tracking or step scaling in the way people assume.
- **Instance warm-up** is *how long a newly launched instance is excluded from the group's aggregated metrics*. It applies to target tracking and step scaling and is the modern, correct control. The instance is in service and receiving traffic; it is simply not counted toward the metric until it has had time to become representative.
- **Instance refresh** is not a scaling control at all - it is a **rolling replacement operation** for rolling out a new launch template version or AMI (Q76).

**The modern replacement for cooldowns is `DefaultInstanceWarmup` on the ASG**, a single setting that applies warm-up consistently to scaling policies, lifecycle hooks and health checks. AWS's guidance is to set it and stop configuring per-policy cooldowns and warm-ups, which is the answer to give: **cooldowns are legacy; warm-up is the control that matters, and it should be set to the true time from launch to serving-at-full-capability.**

The value to use is measured, not guessed: from the instance launch event to the point where its latency and CPU match an established instance. For a Spring Boot service that is often 2-4 minutes, and the default of 300 seconds is coincidentally close - but on a service that starts in 20 seconds, leaving it at 300 makes scaling sluggish for no reason.

*Hook: a warm-up value you measured rather than guessed, and what it changed.*

### Q72. Lifecycle hooks

A lifecycle hook pauses an instance in a **wait state** during launch (`Pending:Wait`) or termination (`Terminating:Wait`) until you either complete the action or the timeout expires, giving you a window to do work while the ASG holds.

**On launch** - real uses: register the instance with an external system (a configuration store, a monitoring platform, a licence server); pull application state or warm a large local cache before it takes traffic; run a validation step and **abandon** the instance if it fails, so a broken instance never serves. The last one is genuinely valuable and underused: `CONTINUE` or `ABANDON` is a decision you get to make.

**On terminate** - the important ones: **flush local state** (upload logs and metrics, drain an in-memory buffer, complete in-flight batch work); **deregister from external systems**; and **graceful shutdown for long-running work** that outlasts the load balancer's deregistration delay - a worker processing a 10-minute job needs the instance kept alive to finish it, which no other mechanism provides.

**If the heartbeat expires**: the ASG performs the **default result**, which you configure as `CONTINUE` or `ABANDON`. The default default is `ABANDON`, which on launch terminates the instance and on terminate proceeds with termination. The important operational consequence: **a hook whose completion signal is never sent silently stalls every scaling action until the timeout**, so an ASG with a 1-hour hook timeout and broken automation takes an hour to add each instance during an incident. You extend the wait with `RecordLifecycleActionHeartbeat` for work that legitimately takes longer, and you **alarm on instances sitting in a wait state**, because that failure is otherwise invisible.

The modern alternative worth naming: for termination-time work, **EventBridge on the lifecycle event plus a Lambda or SSM Automation** is cleaner than a script on the instance signalling itself, because it still works when the instance is the thing that is broken.

*Hook: a lifecycle hook you used for graceful drain, and what happened the first time it timed out.*

### Q73. Termination policies

By default the ASG chooses which instance to terminate using: the **AZ with the most instances** first, then within it, the instance using the **oldest launch template or configuration**, then the one **closest to the next billing hour** (a vestige of hourly billing), then random.

You can set the policy explicitly - `OldestInstance`, `NewestInstance`, `OldestLaunchTemplate`, `OldestLaunchConfiguration`, `ClosestToNextInstanceHour`, `AllocationStrategy` (for Spot pool optimization), `Default`, or a **custom termination policy backed by a Lambda function** for genuinely complex cases.

**Protecting a specific instance** - three distinct mechanisms, and knowing which to use is the point:

1. **Instance scale-in protection** - the ASG-level flag that excludes an instance from scale-in events. This is the right tool for "this instance is processing a long job". Set it programmatically when work starts, clear it when work ends.
2. **Termination protection** (`DisableApiTermination`) - an EC2-level flag that blocks the terminate API. It does **not** stop the ASG from terminating the instance, which is the trap: people set it and are surprised. It protects against a manual mistake, not against the ASG.
3. **A lifecycle hook** (Q72) - does not prevent termination but delays it while work completes, which is the right mechanism when the work is bounded.

The design principle to state: **needing to protect a specific instance is usually a smell.** It means the instance holds state or work that is not recoverable elsewhere, and the durable fix is to move that work into a queue or make it resumable. Scale-in protection is the correct tactical tool and a signal to look at the architecture.

*Hook: an instance whose termination caused work loss, and whether you fixed it with protection or with a redesign.*

### Q74. Warm pools

A warm pool is a pool of **pre-initialized instances held in `Stopped`, `Running` or `Hibernated` state** outside the ASG's in-service capacity, so a scale-out event promotes an already-booted instance in seconds instead of launching one from scratch in minutes.

The problem it solves is **long instance initialization** - a large AMI, a slow bootstrap, a JVM that needs to warm, an application that must load gigabytes of data at startup. When time-to-serving is 8 minutes, reactive scaling cannot respond to a 3-minute traffic ramp at all.

What it costs: **stopped instances still incur EBS storage charges** for their root and data volumes (and hibernated ones a larger volume for the RAM image), and `Running` warm pool instances cost full price. There is also real complexity - warm pool instances need their own lifecycle hooks for the `Warmed:Pending:Wait` state, and the reuse-on-scale-in behaviour needs thought.

**The alternative you should try first**, and this is the part that shows judgement:

1. **Make startup faster.** Bake more into the AMI instead of installing at boot (Q13); most 8-minute boots are 7 minutes of `yum install` and application download. This is usually the correct fix and it makes everything better, not just scaling.
2. **Predictive scaling** (Q69) if the pattern is cyclical - it provisions ahead of the demand curve with normal instances and no warm pool complexity.
3. **Scheduled minimum increases** for known events.
4. **Simply run more headroom.** For a fleet of moderate size, keeping two extra instances running is often cheaper than the operational complexity of a warm pool, and always simpler.
5. **Reconsider the platform** - a workload needing warm pools to scale is telling you something about its startup design.

Warm pools are the right answer when initialization is genuinely irreducible - loading a large model or dataset - and the traffic is genuinely unpredictable so prediction does not help.

*Hook: a slow-starting fleet, and whether you fixed the start time or added a warm pool.*

### Q75. ASG health check types

- **EC2 health checks** (the default) consider an instance healthy if its **EC2 status checks** pass - the instance is running and reachable at the hypervisor level. This says nothing whatsoever about your application.
- **ELB health checks** additionally mark an instance unhealthy if it fails the **target group's health check**, which does test the application.
- **Custom health checks** let an external system call `SetInstanceHealth` to mark instances unhealthy - for a health signal only your application knows about.

**What the wrong choice lets you run for weeks**: with EC2-only health checks, **an instance whose application has crashed, deadlocked, run out of heap, or lost its database connection stays "healthy" indefinitely**, because the operating system is running perfectly. The ASG will never replace it. The load balancer stops sending it traffic (its own health check fails), so you lose that instance's capacity silently, permanently, and without an ASG event. Repeat across a few instances over a few weeks and you are running at half capacity with a green ASG - which is discovered during the next traffic peak.

The default being EC2-only is the trap, and **any ASG behind a load balancer should have `HealthCheckType: ELB`** with a `HealthCheckGracePeriod` long enough to cover application startup (otherwise the ASG kills instances during their normal boot, producing exactly the infinite launch loop the grace period exists to prevent).

The alarm that catches this class of problem regardless: **compare `HealthyHostCount` on the target group against the ASG's desired capacity** and alert on divergence. That single alarm catches the silent capacity loss no matter which health check mechanism failed.

*Hook: a capacity loss that went unnoticed because instances were "healthy", and the alarm you added.*

### Q76. Instance refresh versus blue/green for an AMI rollout

**Instance refresh** replaces instances **in place within the same ASG**, in batches, respecting a minimum healthy percentage and an instance warm-up between batches. It can be configured with **checkpoints** (pause at 20 percent, wait, continue) and **auto-rollback** on a CloudWatch alarm.

**Blue/green with a second ASG** stands up an entirely new ASG on the new AMI, attaches it to the target group (or to a second target group behind a weighted rule), shifts traffic, and deletes the old one.

| | Instance refresh | Blue/green ASG |
| --- | --- | --- |
| Rollback speed | Minutes - it must launch replacements on the old version again | **Seconds** - shift the weight back; the old fleet is still running |
| Rollback certainty | Rolls forward to the old version; a partial refresh leaves a mixed fleet | The old fleet is untouched and known-good |
| Cost during rollout | ~One batch of extra capacity | **Double capacity** for the duration |
| Complexity | One API call, native to the ASG | Orchestration, two ASGs, traffic shifting |
| Traffic control | Coarse - it is instance replacement, not traffic shifting | Fine - weighted target groups allow 1 percent canaries |

**On rollback, which is what the question asks**: blue/green is decisively better. Instance refresh's auto-rollback still has to *replace instances again*, so if the refresh is 60 percent complete you are 5-10 minutes from full recovery and running mixed versions throughout. With blue/green, the old fleet never stopped running, so recovery is a weight change measured in seconds and there is never a mixed state serving traffic ambiguously.

**What I would actually use**: instance refresh for routine, low-risk changes - a monthly patched base AMI, an agent version - where its simplicity wins and a few minutes of rollback is acceptable. Blue/green for application releases, where you want a real canary, sub-minute rollback, and the ability to compare two versions side by side under identical traffic. And I would always configure instance refresh with **auto-rollback on an alarm** rather than leaving it to a human watching a dashboard.

*Hook: an AMI or application rollout on EC2, the mechanism you used, and how long a rollback actually took.*

### Q77. Mixed instances policy

A mixed instances policy lets one ASG launch **multiple instance types across On-Demand and Spot**, with:

- **`OnDemandBaseCapacity`** - an absolute number of instances always On-Demand. This is your floor.
- **`OnDemandPercentageAboveBaseCapacity`** - the split for everything above the base.
- **`SpotAllocationStrategy`** - `price-capacity-optimized` (the right default), `capacity-optimized`, `lowest-price`, or `diversified`.
- **`Overrides`** - the list of acceptable instance types, optionally weighted so a `4xlarge` counts as 4 units.
- **Capacity Rebalancing** - launch a replacement when the rebalance recommendation arrives, before the two-minute notice.

**Configuring it to survive a Spot capacity event** - the specific answers:

1. **`OnDemandBaseCapacity` at a level that can serve your minimum acceptable traffic**, typically 30-50 percent of normal peak. This is the single most important setting: it makes "all Spot reclaimed simultaneously" a degradation rather than an outage.
2. **Ten or more instance types in the overrides**, spanning families and sizes - `m6i`, `m6a`, `m5`, `m5a`, `m5n`, `c6i`, `r6i` and their sizes. Combined with three AZs, that is 30+ pools (Q9), and correlated reclamation across all of them is vanishingly unlikely.
3. **`price-capacity-optimized`** allocation, which weights toward pools with deep capacity rather than the absolute cheapest - the cheapest pool is cheapest because it is about to be reclaimed.
4. **Capacity Rebalancing on**, so replacement starts at the rebalance signal rather than the two-minute notice.
5. **Instance weighting** if your types differ in size, so capacity is measured in units of work rather than instance count.
6. **Test it** - use the Spot interruption simulation in FIS to actually reclaim instances and watch what happens.

The trap to name: **a mixed instances policy with two instance types is not diversified**, and it gives false confidence. The whole mechanism depends on pool count.

*Hook: a Spot fleet configuration, the On-Demand base you chose, and what a real capacity event did.*

### Q78. Scale-in drops requests

The chain: the ASG selects an instance to terminate → it begins termination → the load balancer deregisters it → **but the instance is shut down before in-flight requests complete**, or before the load balancer has finished draining. The client sees a reset.

The specific mechanisms, and there are usually two or three at once:

1. **Deregistration delay shorter than the longest request** (Q59), so the load balancer stops waiting and the instance is terminated mid-request.
2. **No lifecycle hook on terminate**, so the ASG proceeds straight to shutdown once deregistration completes - and the two are not coordinated the way people assume.
3. **The application does not handle `SIGTERM`.** The instance gets a shutdown signal, the process dies immediately, and any request in flight dies with it. A Spring Boot service needs graceful shutdown enabled (`server.shutdown=graceful` with a `spring.lifecycle.timeout-per-shutdown-phase`) - it is not the default in every configuration.
4. **Long-lived connections**: WebSockets, SSE, gRPC streams and long-polling requests do not "complete" within any reasonable drain window, so the drain expires with connections still open.
5. **Keep-alive connections from the load balancer** being closed abruptly rather than after the current request.

The fix, as an ordered chain that must be internally consistent:

```
application graceful shutdown period
  <= deregistration delay
  <= lifecycle hook timeout
  <  Spot interruption window (if applicable)
```

Concretely: measure p99.9 request duration, set graceful shutdown a little above it, set deregistration delay above that, add a terminate lifecycle hook with a timeout above that, and make the application handle `SIGTERM` by refusing new work while finishing current work. Then **test it** by terminating an instance under load and watching for a single error - because every one of these settings can look correct and still be wrong by one link.

*Hook: a scale-in or deployment that dropped requests, and which link in the chain was broken.*

### Q79. Scaling on a queue

**Queue depth is the wrong target metric because it is not proportional to the capacity you need** - it is a stock, not a flow. A depth of 10,000 tells you nothing about how many consumers you need without also knowing the arrival rate and the per-message processing time. Worse, target tracking on raw depth is unstable: as consumers drain the queue the depth falls, capacity is removed, the depth climbs again. And a target value of "1,000 messages" is meaningless as the fleet changes size - it means something different with 2 consumers than with 40.

**The right metric is backlog per instance**, sometimes called acceptable backlog per capacity unit:

```
backlogPerInstance = ApproximateNumberOfMessagesVisible / InServiceInstances
target = (acceptable latency) / (average processing time per message)
```

So if a message takes 0.1 seconds to process and you want a message to wait no more than 30 seconds, the target backlog per instance is 300. You publish `backlogPerInstance` as a custom CloudWatch metric on a schedule (a Lambda on a 1-minute EventBridge rule) and target-track it.

That metric is **proportional to the capacity deficit**, dimensionally correct, stable as the fleet scales, and directly derived from a latency SLO - which is why it works where depth does not.

Two refinements worth mentioning: **`ApproximateAgeOfOldestMessage` is the better *alarm*** even when backlog-per-instance is the better *scaling metric*, because age is the direct expression of "we are not keeping up" (the parent pack's DLQ scenario). And in a serverless consumer, this whole question is replaced by the event source mapping's own scaling with `maximumConcurrency` as the control - which is worth saying, because it is the argument for moving the consumer off EC2 entirely.

*Hook: a queue-driven scaling configuration, the target you calculated, and how you derived it from a latency requirement.*

### Q80. EC2 Auto Scaling versus Application Auto Scaling

**EC2 Auto Scaling** manages ASGs of EC2 instances - that is its entire scope. **Application Auto Scaling** is a separate, generic service that scales the capacity dimension of *other* AWS resources using the same policy types (target tracking, step, scheduled).

What Application Auto Scaling scales, and this list is the answer:

- **ECS services** (task count) - the container equivalent of an ASG
- **DynamoDB** provisioned read and write capacity, on tables and GSIs
- **Aurora replicas** (the reader count)
- **Lambda provisioned concurrency**
- **EMR instance groups, AppStream fleets, SageMaker endpoint variants, Comprehend, Keyspaces, MSK storage, ElastiCache**, and others

**Where it matters in a serverless estate** - three places that come up constantly:

1. **Lambda provisioned concurrency** scaled on a schedule or on the `ProvisionedConcurrencyUtilization` metric, so you pay for pre-warmed environments during business hours and not overnight. This is the mechanism behind "scheduled provisioned concurrency" in the parent pack's Black Friday plan.
2. **DynamoDB provisioned capacity auto-scaling**, which is the thing that reacts in *minutes* and therefore does not save you from a spike - the reason on-demand exists (parent pack Q154).
3. **ECS service scaling**, which is how a Fargate service responds to load at all.

The conceptual point worth making: **"auto scaling" on AWS is not one feature**, and knowing that DynamoDB, Lambda concurrency and ECS tasks are all scaled by the same underlying service with the same policy semantics lets you reason about them uniformly - including the shared limitation that target tracking is reactive and bounded by how fast the underlying resource can actually change.

*Hook: an Application Auto Scaling configuration - provisioned concurrency, DynamoDB or ECS - and what its reaction time meant for you.*

### Q81. Capacity plan for a 20x seasonal peak

**Clarify first**: is 20x the peak *instantaneous* rate or the daily volume? How sharp is the ramp - does it arrive over an hour or at midnight on a countdown? What is the revenue cost of one minute of unavailability, since that sets the budget? Which downstream systems - payment providers, third-party APIs, the database - have their own limits? And what happened last year?

**What I buy.** The four-day peak does not justify a commitment, so: the **existing steady-state floor stays on Savings Plans**, and the peak capacity is **On-Demand**. The critical purchase is **On-Demand Capacity Reservations for the peak window in each AZ** (Q8) - because during a genuine industry-wide peak, On-Demand capacity in a popular instance type is not guaranteed, and discovering that at 09:00 on the day is unrecoverable. ODCRs are billed whether used or not, and a Savings Plan can apply on top; the cost of four days of reserved capacity is trivial against the risk. I would **not** put the peak tier on Spot, because everyone else wants the same capacity at the same time.

**What I pre-scale.**

- **Raise the ASG minimum on a schedule** ahead of the ramp - not the desired count, so target tracking still works above it (Q68). Stage it: 2x the day before, 8x the night before, full capacity two hours ahead.
- **Predictive scaling is not useful here** - there is no cyclical history for a once-a-year event - so this is explicitly scheduled plus reactive, and saying that shows you know when the ML option does not apply.
- **Pre-scale everything downstream, not just the web tier**: database instance size or Aurora replicas, ElastiCache nodes, DynamoDB to on-demand or pre-warmed provisioned capacity, connection pool sizes, and any Lambda provisioned concurrency in the path.
- **Raise service quotas weeks in advance** - Lambda concurrency, API Gateway throttles, SES, and anything else with a per-account limit. This has lead time and is the most commonly missed item.
- **Increase the ASG maximum**, which is the single most likely silent failure (Q66), and alarm on approaching it.

**What I test**, which is where the real value is:

1. **A load test at 20x with the correct arrival shape**, against a production-like environment, at least three weeks out so there is time to fix what it finds.
2. **A scaling-speed test**: how long from traffic arriving to capacity serving? If that is 8 minutes and the ramp is 3, no policy tuning will save it and I need a warm pool or a pre-scaled floor.
3. **A dependency test** - the payment provider's rate limit, the third-party APIs, and the database's connection ceiling. The web tier is rarely what breaks.
4. **A game day** with a failure injected during peak load: an AZ loss, a database failover, a dependency timing out.
5. **A load-shedding plan**, tested: which endpoints get throttled first, and who is authorized to pull the lever without a meeting.

**And the operational preparation**: a dashboard showing the handful of numbers that matter, staffing agreed, a change freeze from a week before, and a documented rollback for every change made in the run-up.

*Hook: a seasonal peak you prepared for, what the load test found, and what actually broke on the day.*

---

## 6. Route 53 and DNS architecture

### Q82. Record types and TTL

The ones you actually use: **A** and **AAAA** (IPv4/IPv6 addresses, and the basis of Route 53 **alias** records), **CNAME** (an alias to another name, never at the zone apex), **MX** (mail), **TXT** (verification, SPF, DKIM, DMARC), **NS** and **SOA** (delegation and zone metadata, created with the zone), **SRV** (service location, used by some protocols and AD), **CAA** (which CAs may issue certificates for the domain), and **PTR** for reverse lookups.

**TTL is the operational control**, and it is worth being precise about what it does: it tells resolvers how long they may cache the answer. Its consequences:

- **A low TTL (60 seconds) means fast change propagation** - essential before a migration or a failover - at the cost of more queries, which on Route 53 means slightly more money and slightly higher latency for cache misses.
- **A high TTL (24 hours) means cheap, fast resolution** but a change takes a day to be universally visible.
- **TTL is a hint, not a guarantee.** This is the part that matters in an incident (Q88): some resolvers ignore it, some clamp it to their own minimum, corporate resolvers cache aggressively, and **Java's JVM historically caches DNS forever** unless `networkaddress.cache.ttl` is set - a genuine and frequent cause of "we failed over and the Java service kept calling the old endpoint".
- **Alias records to AWS resources have TTLs managed by Route 53** and are generally the right choice for AWS targets.

The practical guidance: **60 seconds for anything that might need to move**, 300 for normal service records, longer only for genuinely static things like MX and TXT. The cost difference is negligible and the optionality is worth a great deal.

*Hook: a change whose propagation was slower than the TTL suggested, and what was caching it.*

### Q83. Alias versus CNAME

| | Alias | CNAME |
| --- | --- | --- |
| **At the zone apex** (`example.com`) | **Works** | **Not allowed** by the DNS specification |
| **Cost** | **Free** for queries to AWS resources | Billed per query |
| **Resolution** | Route 53 resolves it internally and returns the A/AAAA records directly - one lookup | The client receives the CNAME and must perform a second lookup |
| **Target** | AWS resources only: ELB, CloudFront, S3 website, API Gateway, another record in the same zone, Global Accelerator, VPC endpoints | Any DNS name |
| **Health checks** | Can evaluate the target's health automatically | No |

**The apex is what decides it.** DNS forbids a CNAME coexisting with other records at a name, and the apex must have SOA and NS records - so `example.com` can never be a CNAME. Before alias records this forced people into ugly workarounds (an EC2 instance running a redirect, or hardcoding load balancer IPs, which change). **Alias records at the apex are the reason `example.com` can point at an ALB at all**, and that is the answer to give.

The other two matter as well: **free queries** is not nothing at scale, and **one fewer round trip** is a real latency saving on every cold resolution. Plus `EvaluateTargetHealth`, which lets an alias to an ELB automatically become unhealthy when the ELB has no healthy targets - a failover mechanism you get for free.

The rule: **use alias whenever the target is an AWS resource; use CNAME only for external targets and non-apex names.**

*Hook: an apex-domain problem, or a query-cost or latency saving from switching to alias.*

### Q84. The seven routing policies

| Policy | Behaviour | Production use |
| --- | --- | --- |
| **Simple** | One record, one or more values, returned in random order | A single endpoint - an internal service, a static site |
| **Weighted** | Values returned in proportion to assigned weights | Canary releases, blue/green migration, gradual traffic shift between regions or providers |
| **Latency-based** | Returns the region with the lowest measured network latency for the resolver | A multi-region active-active application - send users to their fastest region |
| **Failover** | Primary until its health check fails, then secondary | Active-passive DR; a static S3 "we are down" page as the secondary |
| **Geolocation** | Routes by the *user's* location (continent, country, or US state) | Data residency and compliance (EU users to EU infrastructure), content licensing, language-localized sites |
| **Geoproximity** | Routes by geographic distance between user and resource, with an adjustable **bias** to expand or shrink a resource's region | Shifting traffic between data centres by geography, including partial shifts during a migration |
| **Multivalue answer** | Up to eight healthy records returned at random, **with health checks** | Poor man's load balancing for endpoints not behind a load balancer; improving availability of a simple record set |

**IP-based routing** is an eighth policy worth knowing (route by the client's CIDR block, for ISP-specific routing), and interviewers occasionally count it.

The distinction to be crisp about: **latency-based routes by measured network performance; geolocation routes by where the user is; geoproximity routes by distance with a bias dial.** They are frequently conflated, and the compliance case (geolocation) versus the performance case (latency) is the difference that matters most.

*Hook: a routing policy you used for something other than its obvious purpose.*

### Q85. Latency-based routing

Route 53 maintains a continuously updated table of **network latency between AWS regions and the internet's resolver locations**, built from AWS's own measurements. When a query arrives, Route 53 identifies the resolver's location and returns the record for the region with the lowest measured latency **to that resolver**.

**What it does not measure**, which is the substance of the question:

1. **Your application's latency.** It measures network latency to the *region*, not the health, load or response time of your service in it. A region whose application is degraded but reachable will still win the latency comparison and receive traffic. **Latency-based routing must be combined with health checks** or it will happily route users to a broken region faster than to a working one.
2. **The user's latency - it measures the resolver's.** If a user in Chennai is configured to use a resolver in Singapore, or a corporate VPN sends DNS to a central resolver in London, Route 53 sees the resolver's location. **EDNS Client Subnet** mitigates this when the resolver supports it (Google and Cloudflare do; many corporate resolvers do not), but the mismatch is real and is why some users get routed "wrong".
3. **Current network conditions in a fine-grained way.** The table is updated over time, not per-query, so it does not respond to a transient network event.
4. **Anything about capacity.** A small region and a large region are equal as far as latency routing is concerned, so a latency-routed failover can send more traffic to a region than it can serve - which is the parent pack's failover scenario in a different disguise.

The practical composition: **latency-based routing plus health checks plus a capacity plan for the receiving region**, and Global Accelerator as the alternative when you want routing decisions made on the network path rather than by DNS (Q109).

*Hook: a latency-routing surprise where users were routed to an unexpected region, and the cause.*

### Q86. Geolocation, geoproximity and bias

**Geolocation** routes by the user's *political* location - continent, country, or US state - matched against the resolver's IP. It answers "where is this user, legally?" You configure explicit mappings (EU → Frankfurt, IN → Mumbai) plus a **default record** for anywhere unmatched, and forgetting that default is the classic mistake: unmatched users get no answer at all.

**Geoproximity** routes by *physical distance* between the user and the resource, with resources placed at AWS regions or arbitrary latitude/longitude coordinates. The distinguishing feature is **bias**, a value from -99 to +99 that **expands or shrinks the geographic area a resource serves**. A bias of +50 on your Mumbai endpoint pulls in users who would otherwise have gone to Singapore.

What bias is actually for, which is the interesting part:

- **Gradual traffic shifting by geography** - during a migration to a new region, increase its bias progressively and watch traffic move region by region rather than all at once.
- **Capacity balancing** - shrink the area served by a region that is capacity-constrained, expand a region with headroom.
- **Cost management** - pull traffic toward a cheaper region where the latency difference is tolerable.
- **Draining a region** before maintenance, by setting a large negative bias.

Geoproximity requires **traffic flow** (the visual policy editor), which carries an additional charge - a practical consideration worth knowing.

**Choosing between them**: geolocation for **compliance and content** requirements, where the answer must be deterministic by country and "close enough" is not acceptable. Geoproximity for **operational traffic management**, where you want a dial. And latency-based (Q85) when the goal is purely performance and you do not care which region a user lands in.

*Hook: a data residency or traffic-shifting requirement solved with geolocation or geoproximity.*

### Q87. Failover routing and health checks

A failover record set has a **primary** and a **secondary**, each associated with a health check (or, for alias records, `EvaluateTargetHealth`). Route 53 returns the primary while it is healthy and the secondary otherwise.

**What happens from the moment the primary starts failing**, step by step - and the point of walking through it is that every step adds delay:

1. **Health checkers detect the failure.** Route 53 uses a globally distributed set of checkers; a check is configured with an **interval** (30 seconds standard, or 10 seconds fast) and a **failure threshold** (default 3). So detection takes `interval x threshold` - **90 seconds by default**, 30 seconds if you configure fast checks with a threshold of 3. A health check is considered failed only when more than 18 percent of checkers agree, which prevents a single network path problem from causing a false failover.
2. **Route 53 stops returning the primary** and begins returning the secondary. This propagates to Route 53's edge locations quickly - seconds.
3. **Resolvers still hold cached answers** for up to the record's TTL. A 300-second TTL means five more minutes of clients being handed the dead primary.
4. **Clients cache too**, often beyond the TTL - browsers, connection pools, and the JVM (Q82).
5. **Existing connections are unaffected entirely.** DNS failover does nothing about a client holding an open TCP connection to the failed endpoint; that client fails until it reconnects.

So the realistic end-to-end failover time is **detection (90 s) + TTL (60-300 s) + client behaviour**, giving several minutes at best - which is why the answer to "how fast is DNS failover" is "minutes, not seconds", and why Global Accelerator exists for anything needing faster (Q109).

The configuration that minimizes it: **fast health checks (10 s) with a threshold of 2-3, a TTL of 60 seconds, alias records with `EvaluateTargetHealth` where possible, and application-level retry with connection re-resolution.**

*Hook: a DNS failover you executed or drilled, and the measured end-to-end time.*

### Q88. Failover took 20 minutes

The three contributing mechanisms, and they compound:

1. **Detection lag.** Standard health checks at a 30-second interval with a failure threshold of 3 take **90 seconds minimum** to declare failure - and if the endpoint was failing intermittently rather than cleanly, the checkers may have oscillated for several minutes before crossing the threshold consistently. A health check pointed at a shallow endpoint (a static 200) may not have detected the failure at all until someone triggered it manually, which is often the real story behind a 20-minute number.
2. **TTL, and caching beyond it.** If the record's TTL was 300 seconds, that is five minutes of resolvers legitimately serving the old answer. But the bigger contributor is caching that **ignores TTL**: corporate and ISP resolvers with their own minimum caching, the **JVM's `networkaddress.cache.ttl` defaulting to cache-forever** under some security manager configurations, connection pools that resolved once at startup and never again, and browsers with their own DNS cache. A Java client fleet that resolved the endpoint at boot will *never* move until restarted, which alone explains a long tail.
3. **Established connections and connection pools.** DNS changes affect *new* resolutions only. Every client with an open connection, or a connection pool holding sockets to the old endpoint, continues to fail until those connections are torn down and re-established - and a pool configured to retry the same host, or with a long `keepAliveDuration`, will hold on.

**A fourth, which is often the true answer and worth raising**: the failover was *tested* in a way that did not reproduce these conditions - a test that flipped the record manually and confirmed `dig` returned the new value measures step 2 in isolation and none of the rest.

The fixes, in order of value: **TTL to 60 seconds** on anything failoverable; **fast health checks** against a meaningful endpoint; **set `networkaddress.cache.ttl` explicitly** in every JVM (this is a one-line fix with an outsized effect); **configure connection pools to expire and re-resolve**; and for anything needing sub-minute failover, **use Global Accelerator or a load balancer rather than DNS**, because DNS is structurally incapable of it. Finally, **drill the whole path with real clients**, not with `dig`.

*Hook: a failover whose measured time exceeded the design, and which layer of caching was responsible.*

### Q89. The three health check types

1. **Endpoint health checks** - Route 53's global checkers make requests to an IP or domain over HTTP, HTTPS or TCP, optionally with **string matching** on the response body. This is the basic building block.
2. **Calculated health checks** - combine the results of other health checks with boolean logic ("healthy if at least 2 of these 3 children are healthy"). 
3. **CloudWatch alarm health checks** - the health check's state is driven by a CloudWatch alarm.

**When you need the second and third**, which is the real question:

**Calculated health checks** are needed when the health of a *service* is not the health of a single endpoint. Concrete cases: a region is healthy only if the web tier **and** the database replica **and** a critical dependency are healthy - three child checks combined with AND. Or the inverse: a **parent check that is a manual kill switch**, where you combine the real check with a dummy check you can flip, giving operators a way to force a failover without touching the records. That kill-switch pattern is genuinely valuable during an incident and is the answer that stands out.

**CloudWatch alarm health checks** are needed when **health is not externally observable over HTTP**. The cases: a private resource with no public endpoint for Route 53's checkers to reach - which is common and is the primary driver; health defined by a metric rather than a probe (error rate above 5 percent, queue age above 10 minutes, replication lag above a threshold); or a composite business signal. This is how you make DNS failover respond to "the application is returning errors" rather than "the port is open".

The caveat on CloudWatch-based checks: they inherit the alarm's evaluation period, so a 5-minute alarm adds 5 minutes to detection (Q87). And a health check based on an alarm that goes to `INSUFFICIENT_DATA` behaves according to the setting you choose - which needs to be deliberate, because the default may fail your service over when a metric simply stops reporting.

*Hook: a health check that needed to be calculated or metric-driven, and what it let you detect.*

### Q90. Weighted routing for canary and migration

Weighted records return values in proportion to their weights (a weight of 10 against 90 sends roughly 10 percent), with a weight of 0 disabling a record entirely. It is genuinely good at: **shifting traffic between endpoints that share nothing** - a different region, a different account, a different cloud provider, an old and a new stack - which no load balancer can do because they are not behind a common one. That is the case it exists for, and it is how most large migrations are actually executed.

**Its two real limitations compared with a load balancer:**

1. **The distribution is over resolutions, not requests, and it is approximate.** Weights are applied per DNS query, and one resolution serves an unknown number of requests - a client resolves once and reuses the connection for thousands of requests, and a large corporate resolver's single query affects thousands of users. So a 1 percent weight does not give you 1 percent of traffic; it gives you roughly 1 percent of *resolutions*, with high variance and a long tail of stickiness. A load balancer's weighted target groups split actual requests, precisely.
2. **Rollback is slow and incomplete.** Setting the weight to 0 stops new resolutions but does nothing about cached DNS or established connections (Q88), so a bad canary continues receiving traffic for minutes after you pull it. With a load balancer, a weight change takes effect on the next request. **For a canary, that difference is the whole point** - the value of a canary is that you can abort it instantly.

The third limitation worth adding: **no per-request control.** You cannot route by header, cookie or user ID, so you cannot do sticky canaries or opt-in testing.

The guidance: **weighted DNS for coarse, slow, cross-stack shifts** measured in hours or days - a region migration, a provider change. **Weighted target groups or a mesh for canaries** measured in minutes with automatic rollback. Using DNS for a 5-minute canary is a mistake that shows up when you need to abort.

*Hook: a migration you executed with weighted DNS, the shift schedule, and how you handled the rollback lag.*

### Q91. Multivalue answer versus simple with multiple values

A **simple** record with multiple values returns **all** of them, in random order, and Route 53 does not care whether any of them work. If one of four IPs is dead, a quarter of clients get a dead address until someone edits the record.

**Multivalue answer** returns **up to eight healthy records, chosen at random**, with **health checks attached to each**. The addition is health awareness: an unhealthy value is simply not returned.

So the answer to "what does the former add" is: **health checking, and therefore automatic removal of failed endpoints from the answer set.** Plus a degree of client-side load distribution, since different resolvers get different subsets.

Where it is genuinely useful: endpoints that are **not behind a load balancer** - a small fleet of instances serving a protocol a load balancer does not handle, geographically distributed endpoints, or a set of NLBs in different regions. It is a lightweight availability improvement for cases where a load balancer is unavailable or unjustified.

Where it is not a substitute for a load balancer, which is the trade-off to state: **it has no connection-level intelligence** - no least-connections, no request-level health, no draining, and the same DNS caching problems as everything else (Q88), so a failed endpoint's removal still takes TTL plus client behaviour to take effect. Clients also vary in whether they try a second address when the first fails.

The one-liner: **multivalue is DNS-level round-robin with health checks; use it when there is no load balancer, not instead of one.**

*Hook: a case where multivalue answer routing was the right tool, and what you would have used otherwise.*

### Q92. Private hosted zones and split-horizon DNS

A **private hosted zone** is associated with one or more VPCs and resolves **only for queries originating inside those VPCs**, through the VPC's `.2` resolver. The same domain name can exist as both a public hosted zone and a private hosted zone.

**Split-horizon** is exactly that overlap: `api.example.com` resolves to a private ALB's internal address inside the VPC and to a public CloudFront distribution from the internet. When both a private and a public zone match, **the private zone wins for queries from an associated VPC** - and the most-specific zone wins if several private zones could match.

Why you would do this:

- **Internal traffic stays internal.** Service-to-service calls resolve to a private address and never leave the VPC - no NAT charges, no internet path, lower latency, and it works when the internet gateway does not.
- **One hostname across environments.** The same configuration value works in every environment because the name resolves differently per VPC, which removes a whole class of environment-specific config.
- **Internal-only names** that must not appear in public DNS at all.

The mechanics and gotchas: the VPC must have **`enableDnsSupport` and `enableDnsHostnames`** on (Q128); associating a zone with VPCs in **other accounts** requires an authorization step from the zone owner and an association from the VPC owner, done via CLI or API; and **on-premises systems cannot resolve a private zone** without a Route 53 Resolver inbound endpoint (Q93). That last one is the most common surprise in a hybrid estate.

The trap worth naming: **split-horizon makes debugging harder**, because "what does this name resolve to" now depends on where you ask. Anyone diagnosing a connectivity problem must know which zone they are hitting, and I would document it prominently rather than treating it as obvious.

*Hook: a split-horizon design you implemented, and a debugging session it complicated.*

### Q93. Route 53 Resolver endpoints and hybrid DNS

The VPC's `.2` resolver handles DNS inside a VPC but is unreachable from outside it. **Resolver endpoints** bridge that gap in each direction:

**Inbound endpoint** - **on-premises resolves AWS names.** You create an inbound endpoint (ENIs with IP addresses in your VPC subnets), and configure your on-premises DNS servers to **forward** queries for `aws.internal.example.com` to those IPs. The flow: on-prem client → on-prem DNS server → conditional forwarder → inbound endpoint IPs (over Direct Connect or VPN) → Route 53 Resolver → private hosted zone → answer returns the private IP.

**Outbound endpoint** - **AWS resolves on-premises names.** You create an outbound endpoint and attach **resolver rules** that say "queries for `corp.example.com` should be forwarded to these on-premises DNS server IPs". The flow: EC2 instance → VPC `.2` resolver → matching resolver rule → outbound endpoint ENI → on-premises DNS server (over Direct Connect or VPN) → answer.

Both directions:

```
on-prem client -> on-prem DNS -> [conditional forwarder] -> INBOUND endpoint -> R53 Resolver -> PHZ
EC2 instance   -> .2 resolver -> [resolver rule]         -> OUTBOUND endpoint -> on-prem DNS
```

The design details that matter: create endpoints in **at least two AZs** for availability, since these are ENIs and an AZ failure takes one out; **share resolver rules across accounts with AWS RAM** so forty accounts do not each need their own configuration - this is the pattern that makes it manageable at scale; and watch the **queries-per-second limit per endpoint IP**, which a busy estate can reach.

The alternative worth mentioning: **running your own DNS forwarders on EC2** was the pre-Resolver pattern and still appears in older estates. It works, and it is one more thing to patch and keep highly available - Resolver endpoints exist to delete it.

*Hook: a hybrid DNS integration you built, and which direction caused more trouble.*

### Q94. DNSSEC on Route 53

DNSSEC cryptographically signs DNS records so a resolver can verify that an answer genuinely came from the zone's owner and was not modified in transit. It protects against **DNS spoofing and cache poisoning** - an attacker injecting a forged answer that sends your users to their server. It does **not** provide confidentiality (queries are still in plaintext - that is DoH/DoT), and it does not protect against a compromise of your account or registrar.

On Route 53 you enable signing on a public hosted zone, Route 53 manages the zone-signing key, you create a **key-signing key backed by a KMS asymmetric key** (which must be in `us-east-1`), and you then establish the **chain of trust by adding a DS record at the parent zone**, through your registrar.

**The operational risk, and it is significant**: DNSSEC failures are **hard failures**. If a validating resolver cannot verify a signature, it returns SERVFAIL rather than falling back to an unsigned answer - so **your domain becomes entirely unresolvable** for those users. The specific ways this happens:

- **Expired signatures.** Route 53 handles rotation, but if something interrupts it, signatures expire and the zone goes dark on a timer.
- **KMS key problems.** Deleting, disabling, or breaking the key policy of the KSK's KMS key breaks signing. A key deletion is a domain outage with a scheduled date.
- **A broken chain of trust** - a DS record at the parent that does not match, most commonly after a key rotation done in the wrong order, or during a registrar transfer.
- **Key rollover mistakes**, which require a specific sequence with waiting periods for TTLs.

And the recovery is slow: fixing a DS record requires the registrar and then parent-zone TTL propagation, which can be hours during which the domain does not resolve at all.

**The honest recommendation**: enable DNSSEC when there is a **compliance or government requirement** (it is mandated in several sectors), and be deliberate about the operational commitment - monitoring for signature expiry, a documented rollover procedure, and protection on the KMS key. For most commercial applications the threat DNSSEC addresses is better mitigated by HTTPS with certificate validation and HSTS, and the availability risk of getting it wrong exceeds the spoofing risk it removes. That is a defensible position to state, provided you can articulate both sides.

*Hook: a DNSSEC implementation or a decision not to, and the reasoning you gave.*

### Q95. Registration, delegation and NS records

**Registration** is your relationship with the registrar (Route 53 Domains, or a third party) - it establishes that you own the name and, critically, records **which nameservers are authoritative** for it. **Delegation** is the parent zone (`.com`) pointing at those nameservers via **NS records**. The authoritative zone then serves the actual records.

Creating a Route 53 public hosted zone gives you **four assigned nameservers**, and the domain only resolves once the registrar's nameserver setting matches them.

**The most common way delegation gets silently broken**: someone **deletes and recreates the hosted zone**. Route 53 assigns a *different* set of four nameservers to the new zone, but the registrar still points at the old ones. The zone looks perfect in the console - every record is there, correct - and the domain does not resolve, because the world is asking nameservers that no longer host it. Teams lose hours to this because the evidence they look at (the records in the console) is fine, and the broken thing is one level up and invisible from there.

Two close relatives, both worth mentioning:

- **NS records inside the zone not matching the registrar's**, after a manual edit of the apex NS record set - which people do while "cleaning up" and which breaks resolution for resolvers that follow the zone's own NS records.
- **Subdomain delegation done in only one place**: creating a hosted zone for `dev.example.com` but never adding the NS record for it in the parent `example.com` zone. The child zone is authoritative and nobody is told to ask it.

The diagnostic that finds all of these in one command: **`dig +trace example.com`**, which walks the delegation from the root and shows exactly where the chain diverges - and comparing the registrar's nameserver list against the hosted zone's assigned NS record set. I would add that a delegation check belongs in the runbook for anything that touches a hosted zone, precisely because the failure is invisible from inside the console.

*Hook: a DNS outage caused by a delegation problem, and how long it took to look one level up.*

### Q96. TTL strategy around a cutover

The strategy has four phases, and the timing is driven by the *current* TTL, not the new one - which is the subtlety.

**Two weeks before (or at least 2x the current TTL before):** identify every record involved and **lower its TTL to 60 seconds**. This must happen far enough in advance that all cached copies of the *old, long* TTL have expired - if the current TTL is 24 hours, resolvers may hold that answer, with its 24-hour lifetime, for another day. So the lead time must exceed the existing TTL. Lowering it the morning of the cutover accomplishes nothing.

**The days before:** verify the low TTL is actually in effect by querying from several external resolvers, not just from your own machine. Confirm no dependency has hardcoded the IP, and check the JVM DNS cache settings on every Java client (Q88) - because a 60-second TTL is irrelevant to a client that cached at boot.

**At cutover:** change the record. With a 60-second TTL, the bulk of traffic moves within a couple of minutes, with a tail from non-compliant resolvers and long-lived connections. **Have the old endpoint continue serving** throughout - do not decommission it, because the tail is real and you want it to succeed rather than error. Monitor traffic at *both* endpoints, and use the old endpoint's residual traffic as the signal for when the migration is genuinely complete.

**After, once traffic at the old endpoint is zero and has stayed zero for a day:** raise the TTL back to 300 seconds or more, and only then decommission the old endpoint.

**Two additions that make the difference between a plan and a good plan**: keep a **rollback ready** - the old record value written down, the old endpoint warm, and the TTL still low so reverting is as fast as the change was. And consider whether DNS is the right cutover mechanism at all: **shifting weights at a load balancer or with weighted records** gives a gradual, observable, instantly-revertible migration, where a single DNS change is a step function with a slow tail (Q90).

*Hook: a cutover where the TTL preparation mattered, or one where it was skipped.*

### Q97. DNS for two-region active-active with hybrid and partner consumers

**Clarify first**: is the application genuinely active-active, or active-passive being described optimistically - because DNS cannot fix a single-writer database? What failover time is required? Are the on-premises consumers inside the corporate network with their own resolvers? Does the partner need a static IP or a fixed hostname? Are there data residency rules that constrain which users may reach which region?

**The design**, layered by consumer type, because they have genuinely different needs:

**Public users** - `api.example.com` as a **latency-based record set with health checks**, one record per regional endpoint, using **alias records to each region's ALB or CloudFront distribution with `EvaluateTargetHealth`**. Latency routing sends users to their nearest healthy region; the health checks remove a failed region automatically (Q85). TTL at 60 seconds.

Where residency rules exist, **geolocation takes precedence over latency**: EU users pinned to the EU region regardless of measured latency, with latency-based routing applied only within the unconstrained population. Route 53's rule ordering handles this through traffic flow, and getting the precedence right - compliance first, performance second - is the design decision to state.

**On-premises consumers** - a **private hosted zone** for `api.internal.example.com` resolving to the private regional endpoints, with an **inbound Resolver endpoint** so corporate DNS can forward to it (Q93). Traffic then flows over Direct Connect rather than the internet. Internal consumers get **failover or weighted routing** rather than latency-based, because latency measurement from a corporate resolver is meaningless (Q85) - a fixed primary with health-checked failover is more predictable, and predictability is what internal consumers want.

**The partner** - if they need a **static IP** to allowlist, DNS cannot provide it and I would use **Global Accelerator** in front of both regions: two static anycast IPs, health-checked failover in **seconds rather than minutes**, and no dependency on the partner's DNS behaviour (Q109). This is the part of the design where DNS is the wrong tool and saying so is the point. If they do not need a static IP, a **dedicated hostname** (`partner-api.example.com`) with failover routing gives you the ability to move or throttle them independently of public traffic - which is worth having.

**Cross-cutting:**

- **A separate health check per region checking a deep endpoint**, combined with **calculated health checks** so a region is only healthy if its application *and* its data layer are (Q89), plus a manual kill-switch child check for operator-forced failover.
- **Capacity**: latency routing will send all traffic to the surviving region on failure, so each region must be able to serve everything - and the quota parity check from the parent pack applies.
- **60-second TTLs** everywhere, and **explicit JVM DNS cache settings** on every internal Java client, because that single misconfiguration invalidates the whole design (Q88).
- **Documented, drilled failover** with the measured end-to-end time, not the theoretical one.

**The honest caveat to state**: DNS-based multi-region failover takes minutes. If the requirement is seconds, the answer is Global Accelerator for everyone, not just the partner - and if the requirement is zero data loss with a single writer, DNS is not the problem to solve.

*Hook: a multi-region DNS design, and the consumer type that needed a different mechanism from the rest.*

---

## 7. CloudFront and the global edge

### Q98. What CloudFront gives you beyond caching

1. **TLS termination at the edge.** The handshake completes at a nearby edge location rather than at your origin, removing several round trips from every new connection. For a user in India hitting a `us-east-1` origin, that alone can be 300-500 ms saved on connection setup - which is why CloudFront helps even with caching disabled (Q108).
2. **The AWS backbone.** From the edge to your origin, traffic travels AWS's private network with persistent, optimized connections rather than the public internet. Lower latency, far less jitter, and no dependency on the quality of intermediate transit providers.
3. **Security enforcement at the edge**: WAF, Shield Standard (always on, free) and Shield Advanced, geo-restriction, signed URLs and cookies, and origin access control that makes an S3 bucket reachable *only* through the distribution.
4. **Origin protection and offload.** Requests absorbed at the edge never reach your origin, which is a capacity and cost benefit as much as a latency one - and origin shield adds a second consolidation layer (Q111).
5. **Compute at the edge** - CloudFront Functions and Lambda@Edge - for header manipulation, redirects, A/B assignment and authorization without an origin round trip (Q106).
6. **Free data transfer from origin to CloudFront**, which is a real line item: origin egress to the internet is ~$0.09/GB, and to CloudFront it is zero.

The framing that gets credit: **CloudFront is a global network entry point that happens to cache**, not a cache that happens to be global. Most of the value for a dynamic API comes from items 1, 2, 3 and 6, none of which involve caching anything.

*Hook: a CloudFront deployment where the benefit was TLS termination, backbone routing or egress cost rather than cache hits.*

### Q99. Origins, origin groups and failover

An **origin** is where CloudFront fetches content - S3, an ALB, an EC2 instance, API Gateway, a Lambda function URL, or any HTTP server anywhere including outside AWS. A distribution can have many origins, selected by **cache behaviour** (path pattern).

An **origin group** pairs a primary and a secondary origin for automatic failover.

**What triggers failover**: CloudFront retries against the secondary when the primary returns one of the **specific status codes you configure** (from 400, 403, 404, 416, 500, 502, 503, 504) or when the connection **times out or cannot be established**. Failover applies to **GET, HEAD and OPTIONS** requests only.

**What it does not cover**, which is the substance of the question:

- **It is per-request, not a health check.** There is no continuous probing and no circuit state - every request pays the primary's failure and timeout before trying the secondary. A hard-down origin with a 10-second connection timeout means every user waits 10 seconds and then succeeds. CloudFront does not learn.
- **POST, PUT, DELETE and PATCH do not fail over.** Any write request to a failed primary simply fails - which for an API means origin groups protect your reads and nothing else.
- **A 200 response containing an error does not trigger it.** An origin returning `200 OK` with an error body is healthy as far as CloudFront is concerned.
- **Only the status codes you listed trigger it**, and the default set is narrower than people assume.

So origin failover is a **static-content resilience feature**, and treating it as a multi-region failover mechanism for an API is a mistake. For that you want **Route 53 health-checked failover** or **Global Accelerator** in front, with CloudFront pointed at the resulting endpoint - and knowing where that line falls is the answer.

*Hook: an origin failover configuration, and what it did or did not cover during a real origin failure.*

### Q100. Origin Access Control versus Origin Access Identity

Both make an S3 bucket reachable **only through CloudFront** rather than directly, so the bucket stays private and all access passes through the distribution's controls.

**OAI** was the original mechanism: a special CloudFront principal you reference in the bucket policy. **OAC** replaced it and is the correct choice for anything new, because OAI has real gaps:

| | OAI | OAC |
| --- | --- | --- |
| SSE-KMS encrypted objects | **Not supported** | Supported |
| Dynamic requests (POST, PUT) to S3 | No | Yes |
| All AWS regions | Older regions only in practice | All |
| Signing | SigV4 with limitations | **SigV4, short-lived credentials** |
| Granularity | Per-identity | Per-origin, with more control |

The SSE-KMS gap is the one that forces the migration most often - you cannot serve KMS-encrypted objects through an OAI at all.

**The bucket policy with OAC** grants `s3:GetObject` to the `cloudfront.amazonaws.com` service principal, **conditioned on the source ARN of the specific distribution**:

```json
{
  "Effect": "Allow",
  "Principal": { "Service": "cloudfront.amazonaws.com" },
  "Action": "s3:GetObject",
  "Resource": "arn:aws:s3:::my-bucket/*",
  "Condition": {
    "StringEquals": {
      "AWS:SourceArn": "arn:aws:cloudfront::111122223333:distribution/E1ABCDEF"
    }
  }
}
```

**That condition is the entire security control** - without it you have granted every CloudFront distribution in the world read access to your bucket, and someone can point their own distribution at it. It is the most important line in the policy and the easiest to omit.

Two related points: **block all public access on the bucket** as well, so the policy is not the only thing standing between you and exposure; and for a **static website endpoint** (with index documents and redirect rules) OAC does not apply, because that endpoint is public by nature - you use a custom origin with a secret header instead, which is a meaningfully weaker control and worth stating.

*Hook: an OAI to OAC migration, or an S3 origin exposure you found and closed.*

### Q101. The three policy types

They were split apart from the old "forward these to the origin" settings because **one setting was being asked to do two contradictory jobs**: deciding what varies the cache, and deciding what the origin receives. Those are genuinely different questions, and conflating them was the source of most CloudFront cache problems.

- **Cache policy** - what goes into the **cache key** (which headers, cookies and query strings make this a different cached object), plus TTL settings and compression. Everything here **fragments the cache**.
- **Origin request policy** - what is **forwarded to the origin** but does *not* affect the cache key. This is how the origin sees a header it needs for logging or logic without every distinct value creating a separate cached object.
- **Response headers policy** - headers CloudFront **adds to the response** to the client: CORS, HSTS, `X-Frame-Options`, CSP, `Cache-Control` overrides, and custom headers. Managed centrally rather than implemented in every origin application.

The example that makes the split obvious: you want the origin to see `User-Agent` for analytics, but you do **not** want a separate cache entry per user agent string - which would give you a near-zero hit rate. Old settings could not express that. Now: `User-Agent` in the origin request policy, absent from the cache policy. Similarly, `Authorization` usually belongs in the origin request policy and never in the cache key unless responses genuinely differ per user.

AWS provides **managed policies** (`CachingOptimized`, `CachingDisabled`, `AllViewerExceptHostHeader`, `CORS-S3Origin`) that cover most cases, and starting from those rather than hand-rolling is the practical advice.

*Hook: a cache policy change that fixed a hit-rate or origin-load problem.*

### Q102. Cache key design

The cache key determines what counts as "the same object". Every element you add **multiplies the number of cached variants**, so the design goal is: **include exactly what changes the response, and nothing else.**

**Should be in the key**: the path (always), query strings that genuinely select content (`?productId=`, `?page=`), a header or cookie that selects a genuinely different response (`Accept-Language` where you serve localized content, a `device-type` header from a CloudFront Function normalizing user agents), and `Accept-Encoding` when serving compressed variants.

**Should not**: tracking and campaign query strings (`utm_source`, `fbclid`, `gclid`), session cookies, `User-Agent` in raw form, `Authorization` for public content, timestamps or cache-busting parameters that vary per request, and anything a client can set arbitrarily.

**The single most common mistake is forwarding all query strings, all headers and all cookies** - which was the old default and is still what people configure "to be safe". The consequence: every distinct combination of tracking parameters, every session cookie, every user agent string creates its own cache entry. A page shared on social media with different `utm` parameters caches separately per share, and the hit rate collapses to near zero while the origin serves everything. **The cache appears to be working - the metrics show objects cached - and it is caching one object per user.**

The corollary and the second-order mistake: **forwarding a cookie in the cache key makes the cache effectively per-user**, which for a site that sets any analytics cookie means no shared caching at all.

The right approach: **start from `CachingOptimized`, add only what you can justify**, and use a CloudFront Function to **normalize** inputs before they reach the key - strip tracking parameters, bucket user agents into `mobile`/`desktop`, round a value into a small set. Normalization is what turns a high-cardinality input into a usable cache dimension.

*Hook: a cache key you fixed, and what the hit rate did.*

### Q103. Twenty percent hit ratio on a static site

A diagnostic sequence, cheapest first:

1. **Look at the cache policy.** Are all query strings, headers or cookies being forwarded into the key (Q102)? This is the cause more often than everything else combined. Check the actual policy attached to the behaviour serving the traffic, not the distribution's default.
2. **Check what the origin is sending.** A `Cache-Control: no-cache`, `no-store`, `private`, or `max-age=0` header from the origin overrides your intentions, and application frameworks add these by default constantly - Spring Boot, Express and Django all send restrictive cache headers unless told otherwise. Also check for `Set-Cookie` on static responses, which suppresses caching. Fetch an asset directly from the origin with `curl -I` and read the headers; this takes thirty seconds and is frequently the whole answer.
3. **Check the TTLs.** A short `max-age` or a low default TTL means objects expire before they are reused. Compare the TTL against the actual request interval per object.
4. **Look at the request distribution.** In the access logs, count requests per URI. If you have a very long tail of rarely-requested unique objects, a low hit rate may be **correct and unavoidable** - each edge location caches independently, so an object requested once per day at each of 400 edges will never hit. This is where **Origin Shield** helps (Q111), and it is also the case where the answer is "the metric is fine, the workload is like that".
5. **Check for cache-busting in the URLs** - a build that appends a unique hash per deploy is correct, but one that appends a timestamp per request is not.
6. **Check the `Vary` header.** `Vary: *` or `Vary: User-Agent` from the origin fragments the cache regardless of your cache policy.
7. **Check the HTTP methods and status codes.** CloudFront does not cache POST, and by default caches only a limited set of error codes - a site returning many 404s or 302s may be counted as misses.

The most valuable single artefact is the **CloudFront access log with the `x-edge-result-type` field**, which distinguishes `Hit`, `Miss`, `RefreshHit`, `LimitExceeded` and `Error` - and grouping misses by URI and by the fields in the cache key usually names the cause in one query.

*Hook: a cache hit rate investigation, and which of these it turned out to be.*

### Q104. Invalidations versus versioned objects

**Invalidation** tells CloudFront to remove objects from all edge caches. **Versioned object names** means every deploy publishes new filenames (`app.a3f9c2.js`) so new content is fetched at a new URL and old content simply ages out.

**Versioned names are the correct default**, and the reasons are worth listing because they are not only about cost:

1. **It is instant and deterministic.** The HTML references the new filename, so the moment the HTML is served, every client gets the new asset. An invalidation takes minutes to complete across all edges and there is a window where behaviour is inconsistent.
2. **No partial-deploy state.** With invalidation, some edges have the new CSS and the old JS for a period. With versioning, a client gets a self-consistent set.
3. **Rollback is free** - the old files still exist at their old URLs.
4. **You can set `max-age` to a year** on the assets, which maximizes both edge and browser caching.
5. **Cost.** The first 1,000 invalidation paths per month are free; beyond that each path is billed. A team deploying ten times a day with a wildcard invalidation is not bankrupted, but a pipeline that invalidates thousands of individual paths per deploy is a real line item.

The pattern: **long-lived, versioned, immutable assets, and a short-TTL (or no-cache) HTML entry point** that references them. Only the small HTML file needs to be fresh.

**When invalidation is still right**: the HTML entry point itself after a deploy, an emergency content correction (a legal or security issue in published content), and content that genuinely cannot be renamed. Use a small number of **wildcard paths** (`/index.html`, `/*`) rather than thousands of explicit ones, since a wildcard counts as one path.

*Hook: a deployment pipeline where you moved from invalidation to versioned assets, or the invalidation bill that prompted it.*

### Q105. Signed URLs versus signed cookies

Both restrict access to content to users your application has authorized, using a policy signed with a private key whose public half is registered in CloudFront as a **key group** (the modern mechanism; the older trusted-signer model used root account keys and should not be used).

The policy can constrain: an **expiry time**, an optional **start time**, an optional **source IP range**, and the **resource path** (a specific object, or a wildcard for a custom policy).

| | Signed URL | Signed cookie |
| --- | --- | --- |
| Scope | **One object** (or a wildcard with a custom policy) | **Many objects** matching a path pattern |
| Where the credential lives | In the URL itself | In a `Set-Cookie` on the client |
| Shareable/leakable | Yes - the URL contains the grant, so it can be pasted anywhere until expiry | Less so - cookies are not copied when a link is shared |
| Works when the client cannot set cookies | Yes (native apps, download managers, `<img>` from another origin) | No |
| Appears in logs and referrers | Yes | No |

**For a video library, signed cookies.** The reason is HLS or DASH streaming: a single video is **hundreds or thousands of segment files** plus a manifest, all fetched by the player. Signing every segment URL individually is impractical - the manifest would have to be rewritten per user per session, and segment URLs expire mid-playback. A signed cookie with a path-based custom policy (`/videos/movie-123/*`) and a sensible expiry authorizes the whole session with one grant, and the player fetches segments normally.

**Signed URLs are right** for a single-file download (a PDF, an installer, an export), for clients that cannot hold cookies, and for a short-lived one-time link sent by email.

The point worth adding: for S3 origins specifically, **S3 presigned URLs are a different mechanism** that bypasses CloudFront's controls - if content must go through CloudFront, use CloudFront signing, not S3 presigning, or clients will find and use the direct S3 path.

*Hook: a content protection scheme you built, and why you chose URLs or cookies.*

### Q106. CloudFront Functions versus Lambda@Edge

| | CloudFront Functions | Lambda@Edge |
| --- | --- | --- |
| **Where it runs** | All ~400+ edge locations | Regional edge caches (13 locations) |
| **Triggers** | Viewer request, viewer response **only** | Viewer request/response **and origin request/response** |
| **Runtime and limits** | JavaScript (ECMAScript 5.1-ish), **sub-millisecond**, 2 MB memory, 10 KB code, **no network access, no filesystem** | Node.js or Python, up to **5 s** (viewer) / **30 s** (origin), up to 10 GB memory, **full network and AWS SDK access** |
| **Cost** | ~1/6th the price, and it is very cheap | Standard Lambda pricing plus per-request |

**The four differences in one line**: location (every edge versus regional), trigger points (viewer only versus origin too), capability (no network versus full SDK), and cost/latency (sub-millisecond and cheap versus milliseconds and not).

**Only CloudFront Functions can**: run at the true edge on **every** request at effectively zero latency cost - so anything on the hot path of all traffic, executed hundreds of thousands of times per second, where a millisecond matters. The canonical uses: **URL rewrites and redirects, header manipulation, cache-key normalization** (Q102), simple token validation, and A/B test cohort assignment via a cookie.

**Only Lambda@Edge can**: **make network calls** - so anything requiring a lookup against DynamoDB, a call to an authorization service, fetching from a different origin, or reading a secret. Plus anything at the **origin request/response** triggers, which is where you do dynamic origin selection, request signing, or response transformation that should be cached. And anything needing a real runtime - image resizing, complex body manipulation.

The decision rule: **start with CloudFront Functions; move to Lambda@Edge only when you need network access, an origin-side trigger, or more than the tiny runtime allows.** And before either, ask whether the logic belongs at the edge at all - a lot of Lambda@Edge exists because it was easier than changing the origin, and it is harder to deploy, version, debug and roll back than ordinary application code.

*Hook: edge logic you implemented, which service you used, and whether you later moved it.*

### Q107. WAF attachment points and the Shield line

**WAF attaches to**: CloudFront distributions, Application Load Balancers, API Gateway REST APIs, AppSync, Cognito user pools, App Runner, and Verified Access. Notably **not** to NLB (it is layer 4) and not to Lambda function URLs directly.

**Where to attach it matters**: a WAF on CloudFront is a **global** web ACL (created in `us-east-1`) and filters at the edge, so malicious traffic is dropped before it reaches your region - cheaper and faster. A WAF on the ALB is **regional** and filters after the traffic has already arrived. **If you have CloudFront, put the WAF there**, and use the ALB's security group or a secret header to ensure nobody bypasses CloudFront to reach the ALB directly - because a WAF you can route around is decorative.

**The Shield line:**

- **Shield Standard** is **free and always on** for all AWS customers. It provides automatic protection against common layer 3 and 4 attacks - SYN floods, UDP reflection, amplification - with detection and inline mitigation at the edge. For the majority of workloads, especially those behind CloudFront, this is genuinely sufficient.
- **Shield Advanced** is a paid subscription (a substantial monthly commitment plus data charges, on a 1-year term) and adds: **the DDoS Response Team** on call during an attack, **cost protection** (credits for scaling charges incurred during a documented attack), **enhanced detection** with attack diagnostics and near-real-time visibility, **application-layer (L7) protection** with automatic WAF rule creation, **health-based detection** integrated with Route 53, protection for Elastic IPs and Global Accelerator, and a **WAF fee waiver** for protected resources.

**The honest positioning**: Shield Advanced is bought for three reasons - **a genuine, targeted threat profile** (gaming, gambling, political, financial, or a company that has already been attacked), a **compliance or contractual requirement**, or **the cost protection and the DRT relationship as insurance**. It is not a technical necessity for most workloads behind CloudFront, and the monthly commitment is significant enough that recommending it reflexively is poor advice. The question to ask is "have we been attacked, and what did it cost us" - if the answer is no, Shield Standard plus a well-configured WAF with rate-based rules is the proportionate answer.

*Hook: a DDoS event or a Shield Advanced decision, and how you justified it either way.*

### Q108. CloudFront for dynamic and API traffic with caching off

You are buying four things, none of which is caching:

1. **TLS termination at the edge.** The handshake - DNS, TCP, TLS - completes tens of milliseconds from the user instead of hundreds. On a new connection this is the single biggest component of time-to-first-byte for a distant user, and CloudFront keeps a **warm, persistent connection** from the edge to your origin, so the request itself skips connection setup entirely.
2. **The AWS backbone** from edge to origin, instead of the public internet. Lower latency, and far lower **variance** - jitter and packet loss on international transit is what makes p99 latency terrible for distant users, and the backbone largely removes it.
3. **Security at the edge**: WAF, Shield, geo-restriction, and the ability to keep the origin private.
4. **Free origin egress.** Data from your origin to CloudFront costs nothing; from the origin to the internet it is ~$0.09/GB. For an API returning meaningful payloads at volume, **CloudFront can be cheaper than not using it** even after its own request and transfer charges.

**Is it worth it?** For an API with **geographically distributed users**, decisively yes - I have seen 30-50 percent p99 improvements for distant users with caching disabled entirely. For an API whose users are **in the same region as the origin**, largely no: the edge is barely closer than the origin, and you have added a hop, a cost and a component. That is the honest boundary, and it is also the mechanism behind Q110.

Two refinements: use the **`CachingDisabled`** managed cache policy with **`AllViewerExceptHostHeader`** as the origin request policy so headers and cookies reach the origin correctly; and **cache selectively rather than not at all** - even a 5-second TTL on a hot read endpoint, or caching `OPTIONS` preflight responses, produces real origin offload on an "uncacheable" API.

*Hook: an API you fronted with CloudFront, the latency change by geography, and whether the cost went up or down.*

### Q109. Global Accelerator versus CloudFront

**CloudFront is a CDN**: it terminates HTTP(S) at the edge, caches content, runs edge functions, and applies WAF. It is content-aware and HTTP-only.

**Global Accelerator is a network-layer accelerator**: it gives you **two static anycast IP addresses** advertised from AWS edge locations worldwide, and routes traffic over the AWS backbone to your endpoints (ALB, NLB, EC2, Elastic IP) in one or more regions. It does not cache, does not understand HTTP, and does not terminate TLS.

| | CloudFront | Global Accelerator |
| --- | --- | --- |
| Layer | 7 (HTTP/HTTPS) | **3/4 (TCP and UDP)** |
| Caching | Yes | No |
| Static IPs | No | **Yes, two anycast IPs** |
| Failover speed | Origin group, per-request | **Health-check-based, ~30 seconds, no DNS involved** |
| Traffic dials / weights | No | Yes, per-endpoint-group |
| Non-HTTP protocols | No | **Yes - UDP, gaming, VoIP, MQTT, IoT** |

**When you specifically need Global Accelerator:**

1. **Static IPs are required** - a partner or corporate firewall allowlist, or a client that hardcodes addresses (Q51).
2. **The protocol is not HTTP** - UDP-based gaming, VoIP, MQTT, custom TCP protocols. CloudFront cannot carry these at all.
3. **Fast, deterministic regional failover** - health-checked failover in around 30 seconds with **no DNS dependency whatsoever**, which sidesteps every caching problem in Q88. For an active-active service with a strict RTO, this is the reason.
4. **Fine-grained traffic control across regions** - traffic dials let you shift a percentage away from a region for a migration or a drain, which DNS weights do imprecisely (Q90).

The two are **complementary, not alternatives**, and the strong answer says so: a common architecture is CloudFront for the cacheable web and static tier, and Global Accelerator for the API or non-HTTP tier needing static IPs and fast failover. You can even place Global Accelerator behind CloudFront as the origin.

*Hook: a case where Global Accelerator was the right answer, and which of the four drivers decided it.*

### Q110. CloudFront made the API slower

Three mechanisms, and usually the first:

1. **The origin is in the same region as the users, so the edge is not closer.** A user in Mumbai hitting an origin in `ap-south-1` was already 10 ms away. Now the request goes user → Mumbai edge → origin, which adds a hop, an extra TLS termination and a small amount of processing, for no distance saved. **CloudFront helps when the origin is far from users; it costs when the origin is close** (Q108). This is the answer for a "main market" regression specifically, because the main market is usually where the origin was placed.
2. **Cache misses cost more than no cache.** On a miss, CloudFront must go to the origin *and* has already spent time at the edge - so an uncacheable API with a poorly configured cache key (Q102) pays the miss penalty on every request while getting no hits. If the origin also has to be revalidated, it is worse.
3. **Connection reuse to the origin was lost or is inefficient.** If the distribution is configured with a low origin keep-alive timeout, or the origin closes connections aggressively, each request re-establishes a connection from the edge - discarding the main advantage. Similarly, **routing to a distant regional edge cache** on the way to the origin adds a hop rather than removing one.

The fourth, worth checking because it is easy to miss: **an edge function on the viewer-request trigger** adding latency to every request, particularly a Lambda@Edge function which runs at a regional edge cache rather than the true edge and can add tens of milliseconds.

**The diagnostic**: compare p50 and p99 **by geography**, from real user monitoring, before and after. The expected pattern is distant users improving substantially and local users regressing slightly. If that is what you see, the answer may be to **keep CloudFront and accept the local regression** because the global picture is better - or to serve the main market directly and route others through the edge. If *everyone* regressed, look at the cache configuration and the edge functions.

*Hook: a CloudFront rollout with a mixed latency result by geography, and how you decided whether to keep it.*

### Q111. Price classes, regional edge caches and Origin Shield

**Price classes** limit which edge locations serve your distribution. `PriceClass_All` uses everything; `PriceClass_200` excludes the most expensive (South America, and some of Australia/New Zealand); `PriceClass_100` restricts to North America and Europe. Restricting the class **lowers your per-GB cost** because expensive regions are billed at a higher rate - but users in excluded regions are served from a **more distant** edge, so latency for them gets worse. It is a direct cost-for-latency trade, and the right choice depends entirely on where your users are. For a business with no customers in South America, `PriceClass_200` is free money; applied to a global consumer app it is a self-inflicted latency problem.

**Regional edge caches** sit between the ~400+ edge locations and your origin: a smaller number (roughly 13) of larger caches. An object evicted from a small edge cache may still be present in the regional cache, so the request is served from there rather than the origin. They are **automatic, free, and require no configuration** - and they exist because individual edge caches are small and evict aggressively. They do **not** apply to dynamic content or to S3 origins in all cases.

**Origin Shield** is an *additional, opt-in* caching layer in a **single region you designate**, which all edge and regional caches consult before going to the origin. What it changes:

1. **Origin load collapses.** Instead of up to 13 regional caches each requesting an object on a miss, one request reaches the origin. For a high-cardinality catalogue or a live event, this can be an order-of-magnitude reduction in origin requests.
2. **Cache hit ratio improves** for a long-tail workload, because requests from around the world consolidate into one cache rather than fragmenting (Q103, cause 4).
3. **It costs extra** - Origin Shield requests are billed - and it **adds a hop** for requests that miss everywhere, so it slightly increases latency on a full miss.

Place Origin Shield **in the region closest to your origin**. Use it when the origin is expensive or fragile, when the content has a long tail, or during live events. Skip it for a small set of hot objects that stay cached everywhere anyway.

*Hook: an Origin Shield or price class decision, and the measured effect on origin load or cost.*

### Q112. Standard logs versus real-time logs

**Standard logs** (access logs) are delivered to S3, with all fields, on a **delay of minutes to an hour**, batched into files. They are cheap - you pay only for S3 storage and the delivery - and they are complete.

**Real-time logs** are delivered to **Kinesis Data Streams within seconds**, with a configurable field set and a configurable **sampling rate**, and you pay per log line delivered plus the Kinesis costs.

**Enable standard logs by default, always.** They cost almost nothing, and they are the artefact you need for the investigations in Q103 and Q54 - cache hit analysis by URI, error breakdowns, `x-edge-result-type` distribution, top talkers, and traffic analysis. Query them with Athena over a partitioned S3 prefix and the whole capability costs a few dollars a month. Not having them is the common regret during an incident, because you cannot retroactively generate them.

**Real-time logs cost meaningfully more** - per-line charges plus a Kinesis stream plus whatever consumes it - so enable them when you need seconds-level visibility: **during an active attack or incident**, for **real-time security detection** feeding a WAF rule or a SIEM, for a **live event** where you must see the traffic shape as it happens, or for **immediate alerting on error rates** at the edge. The sampling rate is the cost control - 1 percent real-time sampling is often enough for anomaly detection at a fraction of the price.

The pattern I would recommend: **standard logs on, always, to a lifecycle-managed S3 prefix with Athena over them; real-time logs configured but disabled, ready to enable within a minute when something is happening.** Having the configuration ready and dormant is the operational detail that matters, because setting it up during an incident is too slow.

*Hook: an investigation that depended on CloudFront access logs, or a case where they were not enabled.*

### Q113. Edge design for a global SaaS

**Clarify first**: what is the traffic split between the three workloads, and which dominates the bill? Is the video on-demand or live, and is it DRM-protected? Are there data residency requirements for EU customers - which would constrain not just where data is stored but which edge and origin serves them? Is the API's payload cacheable at all, or is everything per-user? Do customers use custom domains, and how many?

**The design, one behaviour per workload on a single distribution** (or separate distributions if the teams and release cycles are separate, which is often the better organizational answer):

**Static console** - `/*.js`, `/*.css`, `/assets/*`, `/index.html`

- Origin: **S3 with OAC** (Q100), block public access, versioned object names (Q104).
- Assets: `Cache-Control: public, max-age=31536000, immutable`, cache policy `CachingOptimized`, no cookies or query strings in the key.
- `index.html`: short TTL or `no-cache`, invalidated on deploy - the only invalidation in the pipeline.
- **Compression on** (Brotli and gzip) - for a JavaScript-heavy console this is one of the largest wins available and costs nothing.
- A **response headers policy** applying HSTS, CSP, `X-Content-Type-Options` and the CORS configuration centrally rather than in the application.

**JSON API** - `/api/*`

- Origin: **ALB or API Gateway**, in the primary region; with two regions, **Global Accelerator or Route 53 latency routing in front of the origins** rather than relying on CloudFront origin groups, which do not fail over writes (Q99).
- Cache policy: **`CachingDisabled`** by default, with origin request policy `AllViewerExceptHostHeader`. Then **selectively cache** the genuinely public read endpoints - a product catalogue, reference data, feature flags - with a short TTL. Even 10 seconds on a hot endpoint is meaningful offload.
- **WAF attached here** with managed rule groups plus **rate-based rules per IP**, since this is the attack surface.
- The value here is items 1, 2 and 4 of Q98 - edge TLS, backbone, free origin egress - not caching, and I would say so explicitly when justifying it.
- A **CloudFront Function** on viewer request to normalize or reject malformed requests cheaply before they consume anything.

**Video** - `/media/*`

- Origin: **S3 (or MediaPackage for live)**, HLS/DASH segments with long TTLs since segments are immutable.
- **Signed cookies** with a path-scoped policy for the session (Q105) - not signed URLs, because of the segment count.
- **Origin Shield** in the origin's region (Q111): video has a long tail and high per-object volume, and consolidating misses protects both the origin and the bill.
- This will dominate data transfer, so it dominates the cost conversation.

**Cross-cutting decisions:**

- **Regions and residency**: origins in `eu-central-1` (or `eu-west-1`) and `us-east-1` with `ap-south-1` if India volume justifies it. If EU data residency is a requirement, **the EU customers' API and data must be served from the EU origin** - which is a Route 53 geolocation decision (Q86) at the origin selection layer, not something CloudFront solves, and CloudFront's edge caching of personal data becomes a question the legal team must answer.
- **Price class**: `PriceClass_All`, given customers in three continents including India - restricting it would directly harm one of the three named markets.
- **Custom customer domains**: SNI with ACM certificates, or CloudFront's SaaS Manager pattern for many domains; note the certificate limit per distribution and plan for it if the customer count is large.
- **Logging**: standard logs to S3 with Athena, real-time logs configured and dormant (Q112).
- **Cost watch**: video data transfer first, then API requests, then function invocations. Set a per-workload cost view from the start, because "CloudFront is expensive" is not actionable and "video egress is 80 percent of CloudFront" is.

*Hook: a multi-workload edge design, the behaviour split you chose, and which workload dominated the bill.*

---

## 8. VPC at scale: peering, Transit Gateway, hybrid connectivity

### Q114. Security groups versus network ACLs

| | Security group | Network ACL |
| --- | --- | --- |
| **Attaches to** | ENIs (instances, tasks, endpoints) | **Subnets** |
| **State** | **Stateful** - a permitted outbound flow's response is automatically allowed | **Stateless** - you must write both directions explicitly |
| **Rules** | **Allow only** - there is no deny | **Allow and deny**, evaluated in numbered order, first match wins |
| **Evaluation** | All rules evaluated; any match permits | Ordered; lowest matching rule number decides |

Two consequences worth adding: security groups can **reference other security groups** as a source, which is the mechanism that makes a real design possible (`app-sg` allows 8080 from `alb-sg`, and it keeps working as instances come and go); and because NACLs are stateless, you must allow the **ephemeral port range** (1024-65535) for return traffic, which is the single most common NACL mistake.

**When the NACL is the right tool** - and the answer is "rarely, but specifically":

1. **You need an explicit deny.** Security groups cannot express "block this IP". Blocking a specific abusive address or CIDR at the subnet boundary is the classic use, and it is genuinely useful during an incident as a fast, coarse control.
2. **A subnet-wide guardrail that an application team cannot undo.** Security groups are typically managed by the workload team; NACLs are managed by the network team. A NACL denying egress to the internet from a database subnet is a control that survives someone editing a security group.
3. **Defence in depth for a highly sensitive subnet**, where a second independent enforcement layer is a compliance requirement.

**Default position**: security groups do the work, NACLs stay at their default allow-all, because stateless rules with ephemeral ports are error-prone and produce failures that are hard to diagnose - the packet leaves and the response is silently dropped, with nothing in any log to say why. Adding NACL rules should be a deliberate decision with a named reason.

*Hook: a NACL you added deliberately, or a connectivity failure caused by a stateless rule.*

### Q115. VPC peering

Peering creates a direct network connection between two VPCs, in the same or different accounts and regions. Traffic uses private IPs, stays on the AWS backbone, and there is **no bandwidth bottleneck or single point of failure** - it is not a gateway appliance, it is a routing construct.

**The limits and properties that shape designs:**

- **It is not transitive.** If A peers with B and B peers with C, A cannot reach C. There is no routing through an intermediary VPC, and this is the fundamental constraint.
- **CIDRs must not overlap.** Peering cannot be created at all between VPCs with overlapping address space, and there is no NAT option within peering.
- **You must update route tables on both sides**, plus security groups. Creating the peering connection alone does nothing.
- **Security group references work across peering** within the same region, which is useful and often forgotten.
- **Quotas**: 125 active peering connections per VPC by default, and route table entries are also capped.
- **Cross-region peering** works but charges cross-region data transfer, and does not support some features (like security group references).

**The scaling problem is the point**: full-mesh peering requires `n(n-1)/2` connections. For 10 VPCs that is 45 connections and 45 sets of route table entries to maintain; for 40 VPCs it is 780. It becomes unmanageable somewhere between 5 and 10 VPCs, and that is exactly the threshold where **Transit Gateway** becomes the answer (Q116).

**CIDR overlap** leaves you with genuinely bad options (Q129): re-address one side, or put a NAT layer between them - typically a PrivateLink endpoint service or a proxy fleet, which changes the connectivity model from "network" to "service". Neither is cheap, which is why **CIDR planning is the one networking decision that is effectively unrecoverable** and why it belongs in the landing zone design on day one.

**Peering remains the right answer** for a small number of stable, high-throughput connections - two VPCs exchanging a lot of data, where TGW's per-GB processing charge would be significant and the mesh is trivially small.

*Hook: a peering mesh you outgrew, or a CIDR overlap you had to work around.*

### Q116. Transit Gateway

TGW is a **regional network hub**: VPCs, VPN connections, Direct Connect gateways and other TGWs attach to it, and it routes between them. It replaced two things - **full-mesh VPC peering** (Q115), with its `n²` growth and non-transitivity, and the **transit VPC** pattern, where you ran your own router appliances on EC2 in a hub VPC and managed their scaling, patching and availability yourself.

The replacement was worth it because TGW is **managed, transitive, and scales to thousands of attachments** with no appliance to operate.

**How it works:**

- **Attachments** connect a resource to the TGW. A **VPC attachment** creates an ENI in one subnet **per AZ** you select - and you should select every AZ where you have workloads, because traffic to a TGW without an attachment in the local AZ crosses AZs (paying transfer and adding latency), and an AZ without an attachment loses connectivity if the others fail.
- **TGW route tables** are the segmentation mechanism, and this is where the power is. Each attachment is **associated** with exactly one route table (which decides *how that attachment routes outward*) and can **propagate** its routes into any number of route tables (which decides *who can reach it*). That association/propagation split is what lets you build isolation (Q118).
- The VPC's own route tables must also point the relevant CIDRs at the TGW - **both layers must be right**, and forgetting the VPC-side route is the most common "TGW is not working" cause.

**What TGW does not do**: it does not solve CIDR overlap, it does not inspect traffic (you route to an inspection VPC for that, Q130), it is **regional** (cross-region requires TGW peering), and it is **not free** (Q117).

*Hook: a migration from peering mesh or transit VPC to TGW, and what it simplified.*

### Q117. Transit Gateway pricing and its consequence

Two charges: **per attachment per hour** (roughly $0.05, so about **$36/month per attachment**) and **per GB of data processed** (roughly **$0.02/GB**).

Both matter, and the second is the one that shapes architecture. Note that the per-GB charge is **levied on data processed**, and for VPC-to-VPC traffic through the TGW you pay it while **also** potentially paying cross-AZ charges - so a chatty east-west workload routed through a TGW can be surprisingly expensive. A terabyte a day of inter-service traffic is roughly $600/month in TGW processing alone.

**The design consequences:**

1. **Do not route traffic through the TGW that does not need to be there.** The biggest offender is **S3 and DynamoDB traffic**: routing it through TGW to a centralized egress VPC, or worse through a NAT gateway as well, costs $0.02/GB (TGW) plus $0.045/GB (NAT) when a **gateway endpoint in the local VPC is free**. Gateway endpoints in every VPC should be a landing zone default, and this alone is often the largest network cost saving available.
2. **Keep chatty services in the same VPC.** If two services exchange large volumes, co-locating them avoids the charge entirely. This pushes toward fewer, larger VPCs with subnet-level separation, rather than a VPC per service - which is the opposite of what a naive "isolate everything" instinct suggests, and worth stating as a deliberate trade-off.
3. **Attachment count has a floor cost.** Forty VPC attachments is ~$1,450/month before any data moves. That is an argument against creating a VPC per small workload.
4. **Peering is cheaper for a small number of high-volume links** - peering has no hourly or processing charge, only standard data transfer - so a pair of VPCs exchanging petabytes should be peered directly even in a TGW estate. A hybrid of TGW for general connectivity plus direct peering for the heavy pairs is a legitimate and cost-aware design.

*Hook: a network cost you traced to TGW or NAT processing, and the endpoint or topology change that fixed it.*

### Q118. Segmenting production from non-production with TGW route tables

The mechanism is the **association / propagation** split (Q116). Association determines what an attachment can *see*; propagation determines who can *reach* an attachment.

The layout for prod, non-prod and shared egress:

**Three TGW route tables**: `prod-rt`, `nonprod-rt`, `shared-rt`.

| Attachment | Associated with | Propagates into |
| --- | --- | --- |
| Prod VPCs | `prod-rt` | `prod-rt`, `shared-rt` |
| Non-prod VPCs | `nonprod-rt` | `nonprod-rt`, `shared-rt` |
| Shared services VPC (egress, DNS, tooling) | `shared-rt` | `prod-rt`, `nonprod-rt` |

The result:

- A **prod VPC** uses `prod-rt`, which contains routes to other prod VPCs and to shared services. It has **no route to any non-prod CIDR** - the isolation is at the routing layer, not a firewall rule someone can edit.
- A **non-prod VPC** likewise sees non-prod plus shared, and cannot reach prod.
- **Shared services** uses `shared-rt`, which has routes to everything, so egress and DNS work for both environments.
- Adding a new prod VPC is one association and one propagation; the isolation is automatic and cannot be forgotten.

Refinements worth mentioning: add a **default route (`0.0.0.0/0`) pointing at the inspection or egress VPC attachment** in both `prod-rt` and `nonprod-rt` for centralized internet egress (Q130); use **blackhole routes** to explicitly drop traffic to CIDRs that should never be reachable; and **disable route propagation and use static routes** where you want the topology to be explicit and reviewable rather than emergent - which for a security boundary is often the better choice, since propagation makes reachability depend on an attachment's configuration rather than on a deliberate decision.

The point to make: **this is network segmentation expressed as routing, which means an application team cannot undo it** - unlike a security group. That is why it is the right layer for an environment boundary.

*Hook: a TGW segmentation design, and a case where the routing boundary caught something a security group would not have.*

### Q119. Site-to-Site VPN

An IPsec tunnel between your on-premises customer gateway device and AWS. AWS provisions **two tunnels to two separate endpoints in different AZs** for every VPN connection - and both should be configured on your device, because using only one is the single most common resilience mistake.

**BGP versus static**: with **BGP (dynamic routing)** the two sides exchange routes automatically, so adding a VPC CIDR or an on-premises subnet propagates without a change on the other side, and **failover between tunnels is automatic and fast**. With **static routing** you configure routes manually on both sides and failover depends on the device's dead peer detection and your configuration. **Always use BGP if the device supports it** - the operational difference is large, and static routing in a growing estate becomes a source of outages when someone adds a subnet and forgets a route.

**The throughput ceiling is ~1.25 Gbps per tunnel**, and critically, **a single VPN connection does not aggregate its two tunnels** - the second is for failover, not bandwidth. So one VPN connection is effectively a 1.25 Gbps link.

**How you exceed it:**

1. **Multiple VPN connections with ECMP over Transit Gateway.** TGW supports equal-cost multi-path across VPN attachments, so `n` connections give roughly `n x 1.25 Gbps` of aggregate throughput. This is the standard answer and it requires TGW (a Virtual Private Gateway does not support ECMP).
2. **Direct Connect** (Q120), which is the real answer above a couple of gigabits - 1, 10 or 100 Gbps ports, with lower and far more consistent latency.
3. **Accelerated Site-to-Site VPN**, which routes the tunnel over Global Accelerator's anycast network to the nearest edge, improving consistency and often throughput for distant sites - though the per-tunnel ceiling remains.

The other limits worth knowing: VPN throughput also depends on your **customer gateway device's** IPsec performance, which is frequently the actual bottleneck; and **per-flow throughput is lower than aggregate**, so a single large TCP transfer will not reach 1.25 Gbps regardless.

*Hook: a VPN throughput ceiling you hit, and whether you scaled out tunnels or moved to Direct Connect.*

### Q120. Direct Connect

A dedicated physical connection between your network and AWS at a Direct Connect location, bypassing the public internet entirely.

**Dedicated versus hosted:**

- **Dedicated connection**: a physical 1, 10 or 100 Gbps port allocated to you, ordered through AWS, with a cross-connect arranged at the colocation facility. You can create multiple VIFs on it. **Lead time is typically weeks to months** - port allocation, the LOA-CFA, the cross-connect, and your carrier's circuit.
- **Hosted connection**: purchased from an **AWS Direct Connect Partner** who already has capacity at the location. Available in smaller increments (50 Mbps up to 25 Gbps), provisioned in **days rather than months**, and generally the right answer for anything below 1 Gbps or when speed of delivery matters. A hosted connection supports **one VIF** (hosted VIFs are a related but distinct product).

**The lead time is the operationally important fact**: Direct Connect cannot be part of a plan that needs connectivity next week. The standard pattern is **start with a VPN for immediate connectivity and order Direct Connect in parallel**, cutting over when it arrives and keeping the VPN as backup (Q121). Saying this unprompted signals you have actually run the process.

**The three VIF types:**

| VIF | Reaches | Use |
| --- | --- | --- |
| **Private VIF** | One VPC's private IPs, via a Virtual Private Gateway | Direct connectivity to a single VPC |
| **Public VIF** | **AWS public service endpoints** - S3, DynamoDB, public APIs - over the DX link rather than the internet, using public IPs | Large data transfer to S3, or reaching public endpoints without internet egress |
| **Transit VIF** | A **Direct Connect Gateway attached to Transit Gateways**, reaching many VPCs across accounts and regions | **The scalable pattern** - one DX connection serving an entire multi-VPC, multi-region estate |

**Transit VIF plus DX Gateway plus TGW is the design to describe** for an enterprise, because private VIFs bind to individual VPCs and do not scale past a handful. And the DX Gateway is **global** - a connection in one region can reach TGWs in others, which is what makes a single DX estate serve a multi-region footprint.

*Hook: a Direct Connect procurement, the lead time you experienced, and what you ran in the meantime.*

### Q121. Resilient hybrid connectivity

**AWS's own resiliency model** defines named levels, and quoting them is worth doing because it gives the business a vocabulary:

| Model | Configuration | For |
| --- | --- | --- |
| **Development and test** | Separate connections at a **single** DX location, terminating on separate devices | Non-critical workloads; survives a device failure, not a location failure |
| **High resiliency** | One connection at **each of two** DX locations | Critical workloads; survives a location or carrier failure |
| **Maximum resiliency** | **Two connections at each of two** DX locations, on separate devices, ideally separate carriers | Workloads that cannot tolerate an outage |

AWS provides a **resiliency toolkit** that configures these and, importantly, a **failover test feature** that lets you disable BGP sessions to prove the failover works - which is the part most organizations never do.

**Where VPN fits as a backup**: a Site-to-Site VPN over the internet as a standby path for the DX link. It is cheap, provisioned in minutes, and independent of the DX carrier - so it covers the failure mode a second DX at the same location does not. The mechanics matter:

- Both paths run **BGP**, and you make DX preferred using **AS path prepending** or **local preference** on your side, and BGP attributes AWS honours on theirs. When DX drops, BGP converges to the VPN automatically.
- **The VPN's bandwidth is a fraction of the DX's** (1.25 Gbps per tunnel versus 10 Gbps), so failover is a **capacity degradation, not a transparent event**. You must know which workloads matter when only the VPN is available, and ideally have a way to shed the rest. Saying this is what separates a real answer from a diagram.
- Test the failover deliberately, on a schedule, and measure both convergence time and the throughput you actually get.

**The most common gap**, which Q122 asks about directly, is that all this redundancy runs through one physical path somewhere.

*Hook: a hybrid connectivity design, its resiliency level, and whether you ever tested the failover.*

### Q122. Two Direct Connects, still one point of failure

The usual answer: **both connections terminate at the same Direct Connect location**, or run over **the same physical fibre path or the same carrier**, so a single backhoe, building event or carrier outage takes both. Redundant ports on redundant AWS devices are worthless if the fibre between your data centre and the facility is a single conduit - and organizations buy "two circuits" from one carrier who provisions them over the same path without ever mentioning it.

The other places the single point hides, and a good answer lists several because the question is really "how thoroughly do you think about this":

1. **The same customer router on your side.** Two circuits into one device means the device is the SPOF. Maximum resiliency requires separate devices at your end too, which is the half people forget because they only look at the AWS side.
2. **The same carrier, even at two locations** - a carrier-wide routing or BGP event affects both.
3. **The same colocation facility power or cross-connect infrastructure**, even with two providers.
4. **A single Direct Connect Gateway or single VIF** - the physical layer is redundant and the logical layer is not.
5. **BGP configuration** that does not actually fail over: no BFD (bidirectional forwarding detection), so convergence takes minutes; or route filtering that drops the backup path's routes.
6. **The same building entrance** for both fibres - two diverse routes that converge in the last 50 metres.

**How to find it**: demand the **circuit path documentation from the carriers** and verify diversity end to end, including the entrance facility; use **different carriers** for the two paths, not just different circuits; and **test by actually disabling a BGP session** with the resiliency toolkit rather than reasoning about it. The test is the only thing that turns an assumption into a fact, and it is routinely skipped because it feels risky - which is precisely the reason to do it in a planned window rather than discovering the answer during an incident.

*Hook: a redundancy design where you found a shared dependency, and how you found it.*

### Q123. Gateway endpoints, interface endpoints and PrivateLink

**Gateway endpoints** exist for **S3 and DynamoDB only**. They are a **route table entry** pointing a prefix list at the endpoint - no ENI, no IP address, and **completely free**. Traffic to S3 from within the VPC leaves via the endpoint instead of the internet gateway or NAT.

**Interface endpoints (AWS PrivateLink)** create an **ENI with a private IP in your subnet** for a service, and DNS resolves the service's public name to that private IP. They work for most AWS services and for third-party or your own services. They are billed **per endpoint per AZ per hour (~$0.01) plus per GB processed (~$0.01)**.

**Endpoint policies** are resource policies on the endpoint restricting what can be done through it - for example, allowing access only to your own account's buckets. This is the **data exfiltration control**: without it, an instance with S3 access can write to *any* S3 bucket in the world including an attacker's, and the gateway endpoint helpfully provides a private path to do it. An endpoint policy limiting `s3:*` to `aws:PrincipalOrgID` or a bucket list closes that, and it belongs in the landing zone baseline.

**The cost point that matters most** (Q117): **always create gateway endpoints for S3 and DynamoDB in every VPC.** They are free, they remove that traffic from NAT gateways ($0.045/GB) and Transit Gateways ($0.02/GB), and forgetting them is one of the most common large, silent network costs.

**How PrivateLink reaches a service in another VPC**: the provider puts their service behind a **Network Load Balancer** and creates an **endpoint service**; the consumer creates an interface endpoint targeting it. Traffic flows consumer ENI → AWS network → provider's NLB, **one-directionally**, with no route table changes, no CIDR coordination, and **no requirement that the CIDRs do not overlap** - which is the property that makes it uniquely useful (Q124, Q129).

*Hook: an endpoint policy you wrote, or a NAT bill fixed by adding gateway endpoints.*

### Q124. PrivateLink versus peering for a service provider

| | VPC peering | PrivateLink |
| --- | --- | --- |
| Exposes | **The whole VPC network** to the peer, subject to routing and security groups | **One service endpoint**, nothing else |
| CIDR overlap | **Prohibited** | **Irrelevant** - no routing between the networks |
| Direction | Bidirectional network reachability | **Unidirectional** - consumer to provider only |
| Scale | `n²` connections, route table changes per peer | One endpoint service, `n` consumer endpoints, **no provider-side change per consumer** |
| Consumer's view | A network route | A DNS name resolving to an ENI in their own VPC |
| Cost | Data transfer only | Hourly per endpoint per AZ, plus per GB |

**Why a SaaS vendor prefers PrivateLink**, and the reasons compound:

1. **CIDR independence.** A vendor with a thousand customers cannot require that none of them use `10.0.0.0/16`. Peering would be impossible at that scale for this reason alone; PrivateLink does not route, so overlap is a non-issue.
2. **Minimal exposure.** Peering gives the customer a route into the vendor's VPC - the blast radius of a misconfigured security group is the whole network. PrivateLink exposes exactly one NLB and nothing else, in one direction. For a multi-tenant provider, offering network-level reachability to every customer is not acceptable.
3. **No per-customer provider work.** The vendor creates one endpoint service and adds principals to its allowlist. Each customer creates their own endpoint. There is no route table to update, no coordination call, and onboarding is self-service.
4. **The customer's traffic never touches the internet**, which is usually the customer's actual requirement and the reason they asked.
5. **The consumer controls their own side** - their subnet, their security group, their DNS - so it fits their network model rather than imposing the vendor's.

**Peering remains right** for a small number of trusted, high-volume, bidirectional connections within one organization - a shared services VPC exchanging heavy traffic with a workload VPC, where the per-GB PrivateLink charge would be material and mutual reachability is desired.

*Hook: a service exposure decision - PrivateLink, peering or public API - and what drove it.*

### Q125. VPC Flow Logs

Flow logs capture **metadata about IP traffic** at the VPC, subnet or ENI level, delivered to CloudWatch Logs, S3 or Kinesis Firehose.

The fields that matter: **source and destination address and port, protocol, packets, bytes, start and end time, the action (`ACCEPT` or `REJECT`), and `log-status`**. In the extended format you can also capture **`flow-direction`, `traffic-path`, `pkt-srcaddr`/`pkt-dstaddr`** (the original addresses before NAT translation - essential when a NAT gateway is in the path), **`tcp-flags`**, `az-id`, `subnet-id`, `instance-id` and `vpc-id`. Choosing the extended format with the fields you need is a decision worth making deliberately at creation, because you cannot retroactively enrich existing logs.

What they are good for: proving whether traffic reached an ENI, finding what a security group is rejecting, mapping actual traffic patterns before a migration, identifying the top talkers behind a data transfer bill, and detecting connections to unexpected destinations.

**Two questions flow logs categorically cannot answer:**

1. **What was in the traffic.** They are metadata only - no payload, no headers above layer 4, no HTTP method, path, status code or hostname. "Which URL was called" and "was the data exfiltrated sensitive" are unanswerable. For that you need application logs, ALB access logs, or a packet capture via **VPC Traffic Mirroring**, which is the tool for the job and worth naming as the alternative.
2. **Why traffic was rejected.** A `REJECT` record tells you a security group or NACL dropped the packet - **but not which one, and not which rule**. You are left inferring from the topology. (**VPC Reachability Analyzer** is the tool that does answer this, by statically evaluating the path configuration, and mentioning it is a strong signal.)

Two further blind spots worth knowing: certain traffic is **not logged at all** - traffic to and from the Amazon DNS server, DHCP, instance metadata (`169.254.169.254`), Windows licence activation, and traffic to the reserved VPC router address. And flow logs are **aggregated over an interval** (1 or 10 minutes), so they are not a per-packet record and short-lived flows can be summarized in ways that hide detail.

Finally, the cost: flow logs at full fidelity on a busy VPC generate enormous volume, and **CloudWatch Logs ingestion at ~$0.50/GB** makes them one of the classic surprise bills. Send them to **S3 in Parquet with Athena** for analysis rather than CloudWatch, unless you need real-time alerting.

*Hook: an investigation where flow logs answered the question, and one where you needed something else.*

### Q126. Network Firewall versus the alternatives

| Control | Layer | Scope | Strengths | Limits |
| --- | --- | --- | --- | --- |
| **Security group** | 4 (stateful) | ENI | Simple, stateful, references other SGs, no cost | Allow-only, no deny, no layer-7, no logging of allowed traffic |
| **NACL** | 3/4 (stateless) | Subnet | Explicit deny, subnet-wide guardrail, free | Stateless, error-prone, no layer-7, no logging |
| **AWS Network Firewall** | 3-7 (stateful) | VPC, via firewall endpoints in dedicated subnets | **Managed**, Suricata-compatible IPS rules, **domain-name filtering**, TLS inspection, deep packet inspection, full logging | Cost (hourly per endpoint plus per GB), added latency and a hop, another thing in the path |
| **Third-party appliance behind GWLB** | 3-7 | Wherever you route it | **Vendor rule sets and expertise you already have**, unified policy with on-premises, advanced features | You operate it: licensing, patching, scaling, HA, plus GWLB and appliance costs |

**Where each belongs:**

- **Security groups do the everyday work.** Every workload, every ENI. This is the primary control and the one that should express your intended architecture.
- **NACLs for a small number of deliberate subnet guardrails** (Q114) - an explicit deny, or a boundary an application team should not be able to undo.
- **Network Firewall for egress filtering and inspection**, and specifically for the capability the other two lack entirely: **filtering by domain name**. "This subnet may reach `*.amazonaws.com` and `repo.corp.example.com` and nothing else" is not expressible in a security group (which knows only IPs, and IPs for SaaS endpoints change constantly), and it is the single most valuable **data exfiltration control** in a regulated environment. Deploy it in a **centralized inspection VPC** (Q130) rather than per-VPC, for cost and manageability.
- **Third-party appliance behind GWLB** when the organization has **standardized on a vendor's rule set** - a Palo Alto or Fortinet policy that must be identical on-premises and in AWS, with a security team trained on it. That consistency is a legitimate and common reason, and it is usually the *only* good reason, because you are taking on operational burden that Network Firewall removes.

**The ordering to state**: start with security groups; add Network Firewall when you need egress domain filtering, IPS, or logged inspection; reach for an appliance only when a specific vendor capability or policy-consistency requirement demands it. And check first whether the requirement is really satisfied by **VPC endpoints with endpoint policies** (Q123), which achieve a lot of the exfiltration control at zero cost.

*Hook: an egress filtering requirement, and which of these you used.*

### Q127. IPv6 in a VPC

What changes:

- **Addressing.** You associate an IPv6 CIDR with the VPC - either **AWS-provided (a fixed `/56`)** or your own via BYOIP - and each subnet gets a **`/64`**. The sizes are fixed, so there is no subnetting arithmetic and effectively no address exhaustion, which is the main reason to adopt it (Q174's EKS IP exhaustion problem, for instance, largely disappears).
- **IPv6 addresses are globally routable by default.** There is no concept of a private IPv6 range in the AWS model equivalent to RFC 1918 - so "it has an IPv6 address" means "it is addressable from the internet if routing and security allow". This is the conceptual shift that catches people, and it means **security groups and NACLs must have explicit IPv6 rules** - an IPv4 rule does not cover IPv6, and a security group that allows `0.0.0.0/0` but not `::/0` will silently behave differently for the two protocols.
- **No NAT.** NAT gateways are IPv4-only and there is no IPv6 NAT, because address scarcity was the reason NAT existed.
- **Routing**: instances with IPv6 route to the internet gateway directly.

**An egress-only internet gateway** is the IPv6 equivalent of a NAT gateway's *security* property, not its translation property: it allows **outbound-initiated IPv6 traffic and blocks inbound-initiated** connections, statefully. Since IPv6 addresses are globally routable, this is how you give a private subnet outbound internet access without making its instances reachable. It is **free**, unlike a NAT gateway - which is a genuine cost argument for IPv6 in egress-heavy workloads.

**Dual-stack migration**, in practice: enable IPv6 alongside IPv4 (dual-stack) rather than attempting IPv6-only; add IPv6 CIDRs to VPC and subnets; add IPv6 rules to every security group and NACL; add an egress-only IGW for private subnets; enable IPv6 on load balancers (dual-stack ALB) and add AAAA records; and **verify every dependency** - some AWS services, many third-party APIs, and plenty of on-premises systems remain IPv4-only, which is what usually prevents going IPv6-only.

The honest framing: **most estates adopt IPv6 because they ran out of RFC 1918 space or need it for a specific workload (EKS at scale, or public-facing services with IPv6 requirements), not because it is better.** Dual-stack doubles the rule surface and the debugging surface, and that cost is real.

*Hook: an IPv6 adoption, what forced it, and what broke.*

### Q128. DNS inside a VPC

**`enableDnsSupport`** (on by default) enables the **Amazon-provided DNS resolver at the VPC's base address plus two** - `169.254.169.253` or `10.0.0.2` for a `10.0.0.0/16` VPC. With it off, no DNS resolution happens through AWS at all, and private hosted zones, VPC endpoint DNS and public name resolution all fail.

**`enableDnsHostnames`** (off by default for a manually created VPC, on for the default VPC) controls whether instances get **public DNS hostnames** assigned. Both must be on for private hosted zones to resolve and for **interface endpoints' private DNS** to work - and that combination is the cause of a very common failure: an interface endpoint created with private DNS enabled, in a VPC with `enableDnsHostnames` off, where the service's name still resolves to the public IP and traffic goes out through the NAT gateway. It *works*, which is why nobody notices, and it silently costs money and defeats the point of the endpoint.

**The `.2` resolver** handles: public DNS, private hosted zones associated with the VPC, VPC endpoint private DNS, and internal `ec2.internal` / `compute.internal` names. It is reachable only from within the VPC and has a **hard limit of 1,024 packets per second per ENI**, which is a real constraint for a busy service doing frequent lookups - and it manifests as intermittent resolution failures under load, which is a genuinely hard thing to diagnose. The fixes are caching (a local resolver like `dnsmasq` or Node's DNS cache) and, for containers, `ndots` tuning.

**Private hosted zone resolution across accounts** requires the zone to be **associated with each VPC** that needs it. Cross-account association is a two-step process: the zone owner creates an authorization (`create-vpc-association-authorization`), then the VPC owner performs the association - and this can only be done via CLI or API, not the console, which surprises people. At scale, the manageable patterns are **AWS RAM-shared Route 53 Resolver rules** (Q93) or associating a central zone with many VPCs programmatically.

*Hook: a DNS resolution problem in a VPC - endpoint private DNS, cross-account association, or the resolver packet limit.*

### Q129. Overlapping CIDRs after a merger

Both use `10.0.0.0/16`, and peering and Transit Gateway both **require non-overlapping address space** - so neither is available. The options, ranked honestly:

**1. Re-address one side. The correct answer, and the expensive one.** Renumber one company's VPCs into a non-overlapping range. This is the only option that leaves you with a clean, routable, permanently maintainable network. The cost is real: every hardcoded IP, firewall rule, allowlist, monitoring configuration and on-premises route must change, and it usually means rebuilding VPCs since a VPC's primary CIDR cannot be changed (though **secondary CIDRs can be added**, which enables a phased migration - add a non-overlapping secondary range, move workloads into new subnets in it, then decommission the old subnets). **If the estate is small or the timeline is long, do this.**

**2. PrivateLink for service-to-service access.** Since PrivateLink does not route between networks, **overlap is irrelevant** (Q124). Each side exposes the specific services the other needs behind an NLB, and consumers create endpoints. This is the **best answer for "next quarter"** in most cases: it is fast, requires no renumbering, exposes only what is intended, and scales. Its limit is that it is service-by-service and unidirectional - it does not give you general network reachability, so it fails for things needing bidirectional or protocol-diverse connectivity.

**3. NAT between the two networks.** A NAT layer (a firewall appliance, or an EC2-based NAT with 1:1 static translations) presents each side to the other under non-overlapping "translated" addresses. It works, and it is genuinely horrible to operate: DNS must be manipulated to hand out translated addresses, troubleshooting becomes an exercise in address archaeology, and every new workload needs a mapping. **Legitimate as a bridge with a documented end date**, dangerous as a permanent state - and I would insist on the end date being funded.

**4. Route only the non-overlapping parts.** If the overlap is partial - both use `10.0.0.0/16` but only `10.0.1.0/24` and `10.0.2.0/24` are actually in use on each side, and those do not collide - you can peer and route the specific non-overlapping subnets. Fragile (any new subnet can break it) but occasionally a pragmatic quick win.

**5. Go via on-premises**, if both connect to a corporate network that already NATs. Inherits whatever the enterprise already does.

**My recommendation in the room**: PrivateLink for the immediate integration needs so the business is unblocked next quarter, running in parallel with a funded re-addressing programme for one side. And the wider lesson to state: **this is why CIDR allocation is a landing zone decision made once, with a large reserved range, before the first VPC exists** (parent pack Q33).

*Hook: a CIDR conflict you resolved, which option you took, and whether the temporary solution became permanent.*

### Q130. Centralized egress and inspection VPCs

**Centralized egress**: instead of a NAT gateway in every VPC, spoke VPCs route `0.0.0.0/0` to a Transit Gateway, which routes to an **egress VPC** containing the NAT gateways and internet gateway.

**Centralized inspection**: the same shape, but traffic passes through an inspection layer - AWS Network Firewall endpoints, or a third-party appliance fleet behind a Gateway Load Balancer (Q61) - before egress, and optionally for east-west traffic between spokes.

**What they buy:**

1. **Fewer NAT gateways.** Forty VPCs with three AZs each is 120 NAT gateways at ~$32/month each - about **$3,800/month in hourly charges alone** - versus three in a central egress VPC. This is usually the headline saving.
2. **A single egress point** for a **fixed set of public IPs** that partners and third parties can allowlist, which is otherwise very hard to provide.
3. **One place to enforce and log egress policy** - domain filtering, IPS, full traffic logging - rather than replicating it per VPC or trusting each team.
4. **A consistent security posture** that does not depend on every account's baseline being correct.

**What they cost:**

1. **Transit Gateway data processing at ~$0.02/GB, on top of NAT's ~$0.045/GB** (Q117) - so centralized egress makes each gigabyte *more* expensive while making the hourly charges far cheaper. **The break-even depends on your traffic volume**, and for a high-egress estate centralization can cost more overall. This is the arithmetic to do rather than assume, and it is the most common mistake in these designs.
2. **Latency** - an extra hop through TGW, and another through the inspection layer.
3. **A shared failure domain.** The egress VPC is now a dependency for every workload's internet access. It must be multi-AZ, and it becomes a change-control-sensitive component.
4. **Operational complexity** - appliance capacity planning, route table management, and asymmetric routing problems that are genuinely hard to debug.

**The rule that resolves most of it**: **always put gateway endpoints for S3 and DynamoDB in the spoke VPCs** (Q123) so that traffic never reaches the TGW or the NAT at all. In many estates the majority of "internet" traffic is S3, and this single change alters the cost calculation completely - often to the point where centralized egress becomes clearly worthwhile because the remaining volume is small.

*Hook: a centralized egress design, the arithmetic you did, and whether it saved money.*

### Q131. Network design for 40 accounts, 4 regions, plus on-premises

**Clarify first**: what is the traffic pattern - mostly north-south to the internet, or heavy east-west between accounts? Is there a compliance requirement that traffic be inspected or that it never traverse the internet? What are the four regions for - latency, residency, or DR? What on-premises bandwidth is needed, and is there an existing Direct Connect? And how much of the estate is serverless, since that changes how much VPC there is to connect at all?

**The design:**

**Address plan.** One large reserved range for AWS overall - a `/8` from RFC 1918 if available, otherwise a large `/12`. Divide it **per region first** (each region gets a contiguous `/12` or `/14`), then per account/VPC within the region, with a fixed VPC size (a `/20` or `/21` is generous for most workloads). Reserve at least as much space as you have allocated, for the second wave nobody predicted. **This is the decision that cannot be undone** (Q129), and I would spend real time on it and write it down.

**Per region: a Transit Gateway as the hub.** All VPCs in the region attach to it, with attachments in every AZ where workloads run. TGWs in different regions are **peered** (or connected via a Cloud WAN core network - worth mentioning as the modern alternative for exactly this scale).

**Segmentation via TGW route tables** (Q118): prod, non-prod, shared services, and inspection. Prod cannot route to non-prod at all; both reach shared services; the default route goes to the inspection/egress VPC.

**A shared services VPC per region**, containing: **centralized egress with NAT and Network Firewall** (Q130), **Route 53 Resolver inbound and outbound endpoints** with rules shared via RAM (Q93), and shared tooling. Plus **gateway endpoints for S3 and DynamoDB in every spoke VPC**, and **centralized interface endpoints** in the shared VPC with private DNS shared across accounts where per-VPC endpoints would be too expensive.

**On-premises connectivity**: **Direct Connect at two locations** (high resiliency, Q121) into a **Direct Connect Gateway**, with **transit VIFs to the TGWs** in the primary regions - the DX Gateway is global, so one DX estate serves all four regions. **Site-to-Site VPN over the internet as the backup path**, with BGP preferring DX and a documented understanding that failover is a capacity degradation.

**Cross-account sharing**: use **AWS RAM** to share TGW attachments, Resolver rules and (optionally) subnets from a network account, so the network team owns the topology and workload accounts consume it without being able to change it. **Centralizing VPCs via shared subnets is worth considering** for smaller workloads - it reduces VPC and attachment count materially, which is a direct cost saving (Q117).

**Governance**: the whole topology in IaC in a network account, CIDR allocation from an IPAM (AWS IPAM does this well and prevents the overlap problem structurally), and SCPs preventing workload accounts from creating internet gateways or their own VPCs outside the managed pattern.

**The trade-offs I would name out loud**: this is a **hub-and-spoke design that centralizes cost and creates a shared dependency** - the network account becomes critical infrastructure with its own availability requirements and change process. It is the right shape at 40 accounts, and it would be over-engineered at 5. And the per-GB charges (TGW plus NAT plus inspection) mean **the design's running cost scales with traffic**, so the gateway endpoints and the co-location of chatty services are not optimizations - they are part of the design.

*Hook: a multi-account network topology you designed or inherited, and the constraint that shaped it most.*

---

## 9. RDS and Aurora operations

### Q132. RDS, Aurora and self-managed

| | Self-managed on EC2 | RDS | Aurora |
| --- | --- | --- | --- |
| **You manage** | OS, patching, engine install, backups, replication, failover, HA, storage | Parameter tuning, schema, queries, sizing | Same as RDS, minus storage sizing |
| **AWS manages** | Nothing above the hypervisor | OS, engine patching, backups, Multi-AZ failover, storage scaling | All of that plus a distributed storage layer |
| **You give up** | - | Superuser, OS access, arbitrary extensions, custom replication topologies, some engine versions | Additionally: engine version choice is narrower, some extensions unsupported, engine-specific internals differ |
| **You gain** | Total control | Operational time back, tested failover, PITR | Six-way replicated storage, fast replicas, faster failover, storage auto-scaling to 128 TiB |

**Going EC2 → RDS**, you give up: **superuser/`SUPER` privileges** (which breaks tooling expecting them), **OS-level access** (no shell, so no `perf`, no custom agents, no filesystem-level backup tools), **arbitrary extensions and plugins** (only those on RDS's supported list), **file-based operations** (`LOAD DATA INFILE` from local disk, `COPY FROM` a local path), and **custom replication topologies** (a chain of replicas, or replication to a non-AWS target, except via DMS). You also accept AWS's maintenance windows and version support lifecycle.

**Going RDS → Aurora**, you additionally give up: **direct control of storage** (which is the point - it is a distributed service), **some engine versions and extensions**, and **exact engine behaviour** in edge cases, since Aurora reimplements the storage layer. You gain the six-copy storage (Q137), sub-10-second failover, up to 15 fast replicas, and a genuinely different scaling model.

**The framing worth giving**: each step trades control for operational time, and the honest question is whether you were actually using the control. Most teams running PostgreSQL on EC2 are not using `SUPER`, custom replication or OS access for anything - they are carrying the operational burden for capabilities they never exercise. **The legitimate reasons to stay self-managed** are: an extension RDS does not support, a version RDS does not offer, a licensing arrangement, or a genuinely custom replication topology - and those should be stated specifically rather than assumed.

*Hook: a migration up or down this ladder, and the capability that was actually at stake.*

### Q133. RDS Multi-AZ instance deployment

A **synchronously replicated standby in a second AZ**, using block-level replication (or the engine's native mechanism for SQL Server). The standby is **not readable and not usable for anything** - it exists solely to take over.

**The failover mechanism**: RDS monitors the primary; on failure - instance failure, AZ failure, storage failure, or an operator-initiated reboot-with-failover, or a maintenance event - it promotes the standby and **updates the DNS CNAME of the endpoint** to point at the new instance. Applications reconnect using the same endpoint name.

The numbers to know: **failover typically takes 60-120 seconds**, dominated by detection, promotion and DNS propagation. It is **not** instant.

The consequences that matter operationally:

- **All connections are dropped.** Every open connection to the old primary is severed; the application must reconnect. A connection pool that does not handle this gracefully - or a JVM caching DNS (Q88) - will keep failing after the database is healthy again. **The most common post-failover incident is not the database; it is the application's DNS cache.**
- **In-flight transactions are lost** and must be retried. Synchronous replication guarantees committed data, not in-flight work.
- **Synchronous replication has a write latency cost** - every commit waits for the standby to acknowledge. Cross-AZ round trip is a small number of milliseconds, but for a write-heavy workload it is measurable, and it is the price of the durability guarantee.
- **RPO is zero, RTO is one to two minutes.**

*Hook: an RDS failover you experienced, the measured time, and whether the application reconnected cleanly.*

### Q134. Multi-AZ DB cluster versus Multi-AZ instance

The **Multi-AZ DB cluster** (available for MySQL and PostgreSQL) is a **three-instance** deployment: one writer and **two readable standbys** across three AZs, using **semi-synchronous** replication - a commit is acknowledged when at least one standby confirms, rather than waiting for both.

What the cluster form changes:

1. **The standbys are readable.** You get two reader endpoints instead of a dead standby, so the HA investment also delivers read capacity. In the instance deployment you were paying for a machine that served no traffic.
2. **Failover is much faster - typically under 35 seconds** rather than 60-120, because the standbys are already running, connected and current.
3. **Write latency is often *better*, not worse**, which surprises people: semi-synchronous commit to the faster of two standbys beats synchronous commit to a single one, and the cluster uses faster local storage.
4. **Three AZs instead of two**, so it survives an AZ failure with HA still intact.
5. **It costs more** - three instances rather than two.

**Choosing between them**: the DB cluster where you want faster failover and can use the read capacity; the instance deployment where cost matters more and one to two minutes of failover is acceptable. And **Aurora** where you want both plus the storage architecture (Q137) - which for PostgreSQL and MySQL is often the better answer than either, making the Multi-AZ DB cluster a somewhat narrow middle option worth knowing about but rarely the conclusion.

*Hook: a Multi-AZ topology choice, and whether failover time or read capacity drove it.*

### Q135. Correcting both halves of the Multi-AZ claim

**"Multi-AZ gives us read scaling"** - wrong for the classic Multi-AZ *instance* deployment. The standby is **not readable**; it accepts no connections and serves no queries. It is a warm spare. Read scaling comes from **read replicas**, which are a completely different feature with different semantics (asynchronous, lag, separate endpoints). The confusion is common enough to be a reliable interview filter, and the two are frequently deployed together precisely because they solve different problems: Multi-AZ is availability, read replicas are scale.

The nuance to add rather than omit: the **Multi-AZ DB cluster** form (Q134) *does* have readable standbys, so the statement is true for that specific deployment type - and being precise about which one you mean is the mark of someone who has used both.

**"Multi-AZ gives us zero-downtime failover"** - also wrong. Failover takes **60-120 seconds** for an instance deployment (under 35 for a DB cluster), during which the database is unavailable. And more importantly:

- **Every connection is dropped.** Applications must reconnect, and in-flight transactions are lost and must be retried.
- **The endpoint's DNS record changes**, so anything caching DNS beyond the TTL continues to fail after the database has recovered (Q88, Q133).
- The application's own recovery - connection pool re-establishment, JVM DNS cache, circuit breaker state - frequently takes longer than the database's.

**The accurate statement**: "Multi-AZ gives us an RPO of zero and an RTO of roughly one to two minutes, with all connections dropped. Whether that is zero *user-visible* downtime depends entirely on whether our application retries and re-resolves properly - and we should test that." That reframing, from a database property to an end-to-end property, is the answer.

*Hook: a failover where the application's recovery, not the database's, was the long pole.*

### Q136. Read replicas

**Mechanism**: for RDS, replicas use the **engine's native asynchronous replication** - MySQL binlog replication, PostgreSQL streaming replication. The primary does not wait for the replica, so a commit on the primary is not guaranteed to be on the replica.

**Lag** is therefore inherent and variable, driven by: replica instance size relative to the primary, write volume on the primary, long-running queries on the replica blocking apply (particularly in PostgreSQL, where a long read can conflict with replay), network, and single-threaded apply on some engines. Monitor **`ReplicaLag`**, and know that under a bulk write it can grow to minutes.

The correctness consequence is the one that matters: **read-after-write is not guaranteed.** A user submits a form and immediately reads back stale data. The mitigations - route reads-after-writes to the primary, use a session token to pin recent writers to the primary for a period, or design the UI to use the value it just submitted - are application-level decisions, and pretending replicas are transparent is how this bug reaches production.

**Cross-region replicas** add: significantly higher and more variable lag, **cross-region data transfer charges** on every replicated byte, and use as a DR mechanism as well as a read-scaling one.

**Promotion** makes a replica a standalone primary. Key facts: it is **irreversible** - the replica leaves the replication topology permanently and cannot rejoin; it takes a few minutes; **replication stops at whatever point it had reached**, so any lag at promotion time is **data loss**; and the promoted instance keeps its own endpoint, so the application must be repointed. Promotion is the DR mechanism for a cross-region replica, and its RPO is exactly the lag at the moment of failure - which is why you monitor lag as a DR readiness metric, not just a performance one.

*Hook: a replica lag problem, and whether the fix was routing, sizing or the query.*

### Q137. Aurora's storage architecture

Aurora separates compute from storage. The storage layer is a **distributed, self-healing, log-structured service** spanning three AZs, keeping **six copies of the data - two per AZ** - in 10 GB segments.

Writes work differently from a traditional database: Aurora **ships redo log records, not data pages**, to the storage layer. A write is acknowledged when **four of six copies** acknowledge (a quorum), and reads require three of six. The storage nodes materialize pages from the log asynchronously.

**What that buys over RDS:**

1. **Durability.** It tolerates the **loss of an entire AZ plus one additional copy** without data loss, and loss of two copies without losing write availability. RDS Multi-AZ has two copies.
2. **Self-healing.** Segments are continuously scanned and repaired; a failed disk or node is re-replicated automatically without operator involvement.
3. **Much lower write amplification.** A traditional MySQL Multi-AZ write sends the data page, the double-write buffer, the binlog and the redo log across the network to the standby. Aurora sends only log records. This is where the "up to 5x MySQL throughput" claim comes from and it is largely real for write-heavy workloads.
4. **Fast replicas.** Replicas read from the **same shared storage** rather than replaying a log, so replica lag is typically **tens of milliseconds** rather than seconds, and adding a replica does not add write load to the primary (Q138).
5. **Storage auto-scales** in 10 GB increments up to 128 TiB, with no provisioning, no volume management and no "the disk is full" incident.
6. **Fast failover**, because a promoted replica already has the data - there is nothing to catch up.
7. **Backups are continuous to S3** with no performance impact, and **PITR to the second** within the retention window.
8. **Fast database cloning** - a copy-on-write clone of a multi-terabyte database in minutes, which is transformative for test environments.

The trade-off to name: **you cannot touch the storage layer**, engine version and extension support is narrower than RDS, and Aurora costs more per instance-hour plus an I/O charge (unless on the I/O-optimized configuration, which is worth evaluating for I/O-heavy workloads).

*Hook: an Aurora migration, and which of these properties actually mattered in practice.*

### Q138. Aurora replicas versus RDS read replicas, and failover tiers

**RDS read replicas** are separate instances with **their own copy of the data**, kept current by asynchronous engine-level replication. Adding one adds replication load to the primary, lag is seconds and variable, and promotion is irreversible.

**Aurora replicas** read from the **same shared storage volume** as the writer. Consequences:

- **Lag is typically 10-20 milliseconds**, because there is no data to ship - only cache invalidation.
- **Adding a replica adds almost no load to the writer.**
- **Up to 15 replicas** versus 5 (or 15 for some RDS engines) - and they can be added or removed in minutes.
- **A replica is automatically promoted on writer failure**, typically in under 30 seconds, and it is not a separate database afterwards - it becomes the cluster's writer, and the old writer rejoins as a replica.
- **Replicas can auto-scale** (via Application Auto Scaling, Q80).

**Failover tiers** (0-15) determine the promotion order: Aurora promotes the **available replica with the lowest tier number**; among equal tiers it picks the one **largest in size** (to avoid promoting an undersized instance). The practical uses:

- Put the replica that is **sized like the writer** at **tier 0**, so a failover does not promote a small reporting replica into the writer role and immediately overload it. This is the most valuable use and the one people miss.
- Put replicas dedicated to **reporting or analytics** at a **high tier** so they are chosen last.
- Use tiers to make failover **deterministic** in a multi-AZ replica set, so you know which AZ you will land in.

The related detail: **Aurora's reader endpoint load-balances across replicas** but only on new connections, so a long-lived connection pool distributes poorly - a known wart that is worth designing around with connection recycling or RDS Proxy.

*Hook: an Aurora failover where the promoted instance's size or tier mattered.*

### Q139. Aurora endpoints

| Endpoint | Points at | Use |
| --- | --- | --- |
| **Cluster (writer)** | The current **writer**, always - it follows failover automatically | All writes, and any read needing read-after-write consistency |
| **Reader** | Load-balances across **all available replicas** (new connections only) | General read traffic |
| **Custom** | A subset of instances you define, by name or by criteria | Segregating workloads - a reporting endpoint hitting only the large analytics replicas |
| **Instance** | One specific instance | Diagnostics and administration. **Not for applications.** |

**What the application should use**: the **cluster endpoint for writes** and the **reader endpoint for reads**, with the application aware of which it is issuing. Most JDBC drivers and the AWS JDBC wrapper support read/write splitting; doing it explicitly in the data layer is clearer.

**What breaks if you pick wrong**, which is the substance:

- **Using an instance endpoint in the application** is the worst mistake. When that instance fails or is replaced during a failover or maintenance, the application is pointed at something that no longer exists or is now a replica accepting no writes - and there is no automatic recovery. **This is a real and common outage cause**, usually introduced during debugging and never reverted.
- **Sending writes to the reader endpoint** produces read-only errors, immediately and obviously - the benign failure.
- **Sending all reads to the cluster endpoint** works correctly but wastes the replicas entirely, so you are paying for read capacity you do not use. Common, invisible, and usually discovered during a cost review.
- **Assuming the reader endpoint distributes evenly** - it balances per connection, so a pool of 50 long-lived connections established at startup may land unevenly and stay that way (Q138).
- **Reading from the reader immediately after a write** and expecting to see it - the lag is small but not zero.

*Hook: an endpoint misconfiguration and what it cost, or a read/write split you implemented.*

### Q140. Aurora Serverless v2

Aurora Serverless v2 scales an instance's capacity **in place, in 0.5 ACU increments** (an ACU being roughly 2 GiB of memory with corresponding CPU and network), from a configured minimum to a maximum, **in seconds and without dropping connections**. This is the key difference from v1, which paused and resumed with disruptive scaling points and was largely unusable for production.

**The minimum ACU trade-off** is the central design decision. A low minimum (0.5 ACU) is cheap when idle but means: less memory for the buffer cache, so **cold performance is poor** after an idle period and queries that were fast become slow while the cache refills; and scaling up from a very low floor takes longer to reach high capacity. A higher minimum keeps the cache warm and response predictable, at a continuous cost. **The minimum should be set from the buffer cache the workload actually needs**, not from the cheapest number - and this is the tuning that determines whether Serverless v2 feels good or terrible.

A minimum of **0 ACU** is now possible, pausing after a period of inactivity, with a resume delay on the next connection - genuinely useful for development and intermittent workloads, and unacceptable for anything latency-sensitive.

**When it is the wrong choice:**

1. **Steady, predictable load.** Serverless v2 is priced at a premium per ACU-hour against provisioned instances. At constant utilization you pay more for scaling you never use - and a reserved provisioned instance is dramatically cheaper.
2. **Very large, constant workloads** where you would simply size an instance and be done.
3. **When cost predictability matters more than elasticity** - a variable bill is a genuine problem for some organizations.

**When it is right**: spiky or unpredictable load, development and test environments (huge savings), multi-tenant SaaS where per-tenant databases idle most of the time, new workloads whose capacity you cannot yet predict, and the reader tier of a cluster where read load varies more than write load - **mixing provisioned writer with serverless readers is a legitimate and underused pattern**.

*Hook: a Serverless v2 deployment, the minimum ACU you chose, and how you arrived at it.*

### Q141. Aurora Global Database

One Aurora cluster designated primary in one region, with up to five **read-only secondary regions**. Replication happens **at the storage layer**, using a dedicated infrastructure that ships log records directly - not the database engine's replication.

**RPO and RTO:**

- **Typical replication lag is under one second**, often a few hundred milliseconds, and it does not consume writer CPU because it happens below the engine.
- **Managed planned failover** (switchover) is **lossless** - it coordinates with the primary, drains, and promotes cleanly. RPO zero.
- **Unplanned failover** ("detach and promote") has an **RPO of whatever was in flight**, typically seconds of data, and an **RTO of under a minute** for the promotion itself - plus your application's time to repoint, which is the part people forget to count.

**A headless secondary** is a secondary region with the **storage volume replicated but no database instances running**. It exists to give you **DR at storage cost only** - you are paying for replicated storage and the replication, not for idle compute. On a disaster, you launch instances into the existing volume and promote, which takes longer than a warm secondary (minutes to provision instances) but costs a fraction. It is the **pilot light pattern** expressed natively, and it is the right default for a DR-only secondary region where a few extra minutes of RTO is acceptable.

The trade-offs to state: secondaries are **read-only** - Global Database does not give you multi-region writes (write forwarding exists, which forwards writes from a secondary to the primary, but that is a latency convenience, not active-active); cross-region **replicated data transfer is charged**; and the failover is a **cluster-level, one-way operation** whose reversal is another failover, so drilling it needs planning.

*Hook: a Global Database deployment, whether you ran headless, and whether you ever failed over.*

### Q142. Backups, PITR and what deletion destroys

**Automated backups**: RDS takes a daily snapshot during the backup window and **continuously ships transaction logs to S3**, which together enable **point-in-time recovery to any second** within the retention period (0-35 days, default 7). Retention of 0 **disables backups entirely** - a genuinely dangerous setting that exists and that people set in "temporary" environments that become permanent.

**Manual snapshots** are user-initiated, full, and **retained until you explicitly delete them** - independent of any retention window.

**Cross-region**: automated backups can be replicated to another region (an explicit feature), and manual snapshots can be copied. Copies of encrypted snapshots need the KMS considerations from Q30.

**What is deleted when you delete the instance** - the crucial distinction:

- **Automated backups are deleted** with the instance (after a short grace period in some configurations, and RDS now offers *retained* automated backups which survive deletion if configured - worth knowing, and not the default assumption to rely on). **Point-in-time recovery dies with the instance.**
- **Manual snapshots survive.** They are independent objects.
- The **final snapshot** option at deletion time creates a manual snapshot - which is why unchecking it is so consequential (Q143).

**Aurora differs**: backups are continuous to S3 by design, PITR is to the second within the retention window, and there is no backup window or performance impact. Aurora also has **backtrack** (MySQL-compatible only) which rewinds the cluster in place, in seconds, without a restore - excellent for recovering from a bad migration or a mistaken `DELETE`, and limited to a configured window.

The operational rule: **automated backups are for operational recovery; manual snapshots or AWS Backup with a separate account are for the things that must survive the resource** (Q44). Relying on automated backups alone means an accidental instance deletion destroys the resource and its recovery path simultaneously.

*Hook: a restore you performed, and whether it was from PITR or a snapshot.*

### Q143. The deleted instance with no final snapshot

**What you can recover:**

1. **A manual snapshot, if one exists.** These survive instance deletion. Check first, including in other regions.
2. **Retained automated backups**, if the feature was enabled - RDS can retain automated backups after deletion, and if so you have PITR up to the deletion time. This is the best case and worth checking immediately.
3. **An AWS Backup recovery point**, if the instance was covered by a backup plan (Q43) - which is exactly why a centralized backup plan matters more than per-resource settings.
4. **A read replica**, if one existed - it is a separate instance and is *not* deleted with the primary (though it is promoted or becomes standalone). This has saved people.
5. **A cross-region snapshot copy**, if the estate replicated them.
6. **Aurora specifically**: the cluster and the instances are separate objects - deleting an instance does not delete the cluster or its storage, so an Aurora "instance deletion" is often fully recoverable, and this distinction is worth knowing.

**What you cannot do:**

- **There is no undelete.** Once the deletion completes and automated backups are purged, the data is gone.
- **AWS support cannot recover it.** This is worth saying plainly, because the instinct is to open a P1 and hope. They can confirm what exists; they cannot resurrect deleted storage.
- **Point-in-time recovery is not available** without retained automated backups, because the transaction logs went with the instance.

**The immediate actions**, in order: **stop anyone from doing anything else destructive**; check every recovery source above, including other regions and accounts; check CloudTrail for the deletion event to establish exactly when and by whom, and whether a final snapshot was in fact created under a generated name; and check whether any downstream system - a data warehouse, an ETL target, an analytics replica, a nightly export - holds a usable copy. That last one is the unglamorous save in a real incident.

**The postmortem controls**: **`deletion_protection` on every production database** (it blocks the delete API outright, and it is one attribute); an **SCP denying `rds:DeleteDBInstance`** in production accounts except to a break-glass role; **AWS Backup with a vault in a separate account** so backups do not share the resource's fate (Q44); and **retained automated backups** enabled. Deletion protection alone would have prevented this and costs nothing, which is what makes the incident a governance finding rather than a human one.

*Hook: a destructive action that was or was not recoverable, and the guardrail you added.*

### Q144. RDS Blue/Green Deployments

It creates a **complete staging copy** of your production database (the green environment) - the instance, its replicas, and its configuration - kept **in sync with production via logical replication**. You make changes to green (a major version upgrade, a schema change, a parameter change), test them, and then **switch over**.

**What it automates**, which is the substantial part: provisioning the green environment, establishing and monitoring replication, running switchover **safety checks** (replication lag must be near zero, no long-running transactions, no unsupported activity), and then performing the switchover itself - which **stops writes on blue, waits for green to catch up completely, renames the endpoints so green takes blue's names, and resumes**. Typically **under a minute**, with no application configuration change because the endpoint names move.

**What it does not do:**

- **It is not zero-downtime.** There is a brief write outage during switchover - short, but real, and connections are affected.
- **It does not test your application.** It ensures the database is consistent; whether your queries still work on the new version is your problem, and the whole point of having green available beforehand.
- **It does not roll back after switchover.** The old blue environment is retained (renamed) so you can go back manually, but there is no automated reversal, and **writes that landed on green after switchover are not replicated back**. So rollback after any real traffic means data loss or reconciliation - the same problem as any database cutover (parent pack's migration scenario), and the reason to validate thoroughly before switching.
- **It has engine and feature restrictions** - not all engines, versions and configurations are supported, and some features (certain replication setups, some parameter changes) block it.

**The switchover itself** is: stop new writes on blue → let green's replication drain to zero → verify → **swap the endpoint names** → allow writes on green. The endpoint rename is the clever part, because it means the application's connection string never changes.

The honest positioning: **it is a significant improvement over the previous approach** (manual replica, manual promotion, manual endpoint changes) for major version upgrades in particular, and it removes most of the risk from a task that used to be a weekend project. It is not magic, and the testing on green is still where the work is.

*Hook: a major version upgrade you performed, with or without blue/green, and how long the write outage was.*

### Q145. Parameter groups and the change that did nothing

A **parameter group** is a named set of engine configuration values applied to an instance or cluster (Aurora has both cluster-level and instance-level parameter groups, which is itself a source of confusion). An **option group** is different: it enables optional engine *features* - Oracle TDE and OEM, SQL Server auditing, MySQL memcached plugin - rather than tuning values.

**The default parameter group cannot be modified.** You must create a custom one and associate it, which is a step people miss - they edit "the parameters" in the console, find nothing is editable, and copy values somewhere unhelpful.

**Static versus dynamic** is the answer to "why did nothing happen":

- **Dynamic parameters** take effect **immediately** (or on the next connection) once applied.
- **Static parameters require a reboot** of the instance. Changing one puts the instance into `pending-reboot` status - and **the change is not in effect until you reboot**. The parameter group shows the new value, the console shows it applied, and the engine is still running the old one.

That is the mechanism behind "I changed it and nothing happened": the parameter was static, the status said `pending-reboot`, and nobody rebooted. `max_connections`, `shared_buffers` and most memory-related parameters are static.

**The other reasons a change appears to do nothing:**

1. **The instance was never associated with the custom group** - it is still on the default.
2. **For Aurora, the parameter is at the wrong level** - some parameters only take effect in the *cluster* parameter group, others only at the *instance* level, and setting one in the wrong place is silently ignored.
3. **The value is a formula referencing `DBInstanceClassMemory`**, and the effective value is not what you typed.
4. **The engine caps or ignores it** - setting a value beyond the engine's allowed range clamps it silently.
5. **Session-level overrides** in the application (`SET` statements, or a connection pool configuring the session) override the server default per connection.

**The check**: query the engine for the *running* value (`SHOW VARIABLES` in MySQL, `SHOW <param>` or `pg_settings` in PostgreSQL) rather than trusting the console. `pg_settings` even has a `pending_restart` column that answers this directly.

*Hook: a parameter change that silently did nothing, and how long before someone checked the running value.*

### Q146. RDS Proxy beyond serverless

RDS Proxy is a managed connection pool sitting between the application and the database, multiplexing many client connections onto a smaller number of database connections.

**For a container fleet**, the connection storm problem is the same shape as the serverless one and just as real: 200 Fargate tasks each with a pool of 10 is 2,000 connections against an instance whose `max_connections` is in the hundreds. The proxy decouples the two - the tasks connect to the proxy freely, and the proxy maintains a bounded pool to the database. It also **absorbs deployment churn**: a rolling deploy that replaces 200 tasks creates 200 new pools' worth of connections against the database simultaneously, and the proxy flattens that entirely.

**For failover, which is the underappreciated benefit**: the proxy **holds client connections open during a database failover**, detects the new writer, and reconnects on the client's behalf. The application's connections are preserved rather than dropped, so **failover time as experienced by the application drops from 60-120 seconds to a few seconds** - and, critically, it eliminates the Q133/Q135 problem where the application's DNS cache and pool recovery are the long pole. For an estate where the application layer reconnects badly, RDS Proxy is often a faster fix than fixing every application.

It also provides **IAM authentication** and **secret rotation via Secrets Manager** without application changes.

**The costs and caveats**: it is priced **per vCPU of the database instance per hour**, which is not trivial; it **adds a network hop** and roughly a millisecond of latency; and the crucial operational metric is **`DatabaseConnectionsCurrentlySessionPinned`** - **session-level state defeats multiplexing**. Prepared statements in some modes, temporary tables, `SET` statements, advisory locks and explicit transactions cause the proxy to *pin* a client connection to a database connection for its lifetime, at which point you get no pooling benefit at all while still paying for the proxy. Many ORMs and connection pool libraries issue session-level `SET` statements at connection time by default, so **checking the pinning metric after deployment is mandatory**, and a proxy with high pinning is a proxy doing nothing.

*Hook: an RDS Proxy deployment, and whether the driver was connection count or failover behaviour.*

### Q147. Enhanced Monitoring, Performance Insights and CloudWatch

- **CloudWatch metrics** come from the **hypervisor** at 1-minute granularity: CPU, connections, IOPS, throughput, free storage, freeable memory, replica lag. Good for trends, alarms and capacity. They tell you *that* something is wrong.
- **Enhanced Monitoring** installs an agent on the instance and reports **OS-level metrics at up to 1-second granularity** to CloudWatch Logs: **per-process CPU and memory**, load average, detailed memory breakdown, per-device disk metrics, and the process list. It sees things the hypervisor cannot - crucially, **memory as the OS sees it** rather than as the hypervisor guesses, and which processes are consuming what.
- **Performance Insights** is a **database-aware** view: it samples the engine's active sessions and presents load as **Average Active Sessions**, broken down by **wait event, SQL statement, host and user**, against a "max vCPU" line that shows whether you are saturated.

**"Why is the database slow right now" is answered by Performance Insights**, and it is not close. It is the only one of the three that connects load to **specific SQL statements and specific wait events**. The workflow is: look at AAS against the vCPU line to see if you are saturated; look at the **wait event breakdown** to see *what* sessions are waiting on - CPU, `io/table/sql/handler` (disk reads), `lock`, `IO:DataFileRead`, `LWLock` - which names the category of problem; then look at the **top SQL** contributing to that wait. Within a minute you have "this query, waiting on this resource, is 70 percent of the load".

CloudWatch tells you CPU is at 95 percent. Enhanced Monitoring tells you which OS process is using it. **Only Performance Insights tells you which query and why**, which is what you actually need.

The practical guidance: **enable Performance Insights on every production database** - the 7-day retention tier is free, which removes the only objection - and enable Enhanced Monitoring at 60 seconds as standard, dropping to 1-5 seconds during an investigation since the CloudWatch Logs ingestion cost at 1 second is significant.

*Hook: a database performance investigation where Performance Insights named the query, and what the wait event was.*

### Q148. Maintenance windows and version upgrades

**The maintenance window** is a weekly 30-minute period during which AWS applies OS and engine patching and other maintenance. Some maintenance is **deferrable** (you can postpone it), some is **required** with a deadline, and some is applied immediately for critical security issues.

**Minor version upgrades** (12.7 → 12.9) are backward compatible and can be applied **automatically** if `auto_minor_version_upgrade` is enabled - which I would leave **on for non-production and consider carefully for production**, since automatic patching during a maintenance window means an unplanned restart at a time you did not choose. The safer production pattern is auto-upgrade off, with a deliberate quarterly patching cadence you control.

**Major version upgrades** (12 → 15) are never automatic. They can break compatibility, they require testing, and the mechanism is either an in-place upgrade (with downtime proportional to the database size) or **blue/green** (Q144), which is now the recommended path.

**Both involve downtime**: minor upgrades are typically a restart (a minute or two, plus failover time if Multi-AZ - and note that with Multi-AZ, AWS patches the standby first then fails over, which is faster but *does* trigger a failover, so your application must handle it).

**End of standard support** is the part with real consequences. When a major version reaches end of standard support, AWS moves the instance to **RDS Extended Support**, which is **charged per vCPU per hour at a rate that escalates over time** and can easily exceed the instance cost itself. If you take no action for long enough, **AWS will forcibly upgrade the instance** to a supported version at a scheduled date. So the practical position is: **an unsupported version is a cost and a scheduled outage you do not control**, and version currency is a budget item, not a technical preference. Track the version lifecycle calendar and plan upgrades a quarter ahead of the deadline.

*Hook: a version upgrade you planned, the downtime, and whether extended support charges featured in the business case.*

### Q149. Migrating 5 TB of Oracle with a four-hour outage window

**Clarify first**: how much of the schema is Oracle-specific - PL/SQL packages, triggers, materialized views, Advanced Queuing, Spatial, partitioning, database links? Is there a business driver to leave Oracle (licence cost) or is the goal simply to be on AWS? What is the write rate, since that determines CDC feasibility? Are there downstream systems reading the database directly? Is four hours a hard limit, and does it include validation and rollback time - because if it does, the usable window is closer to two.

**The options:**

| Option | Outage | Effort | When |
| --- | --- | --- | --- |
| **RDS for Oracle** (lift) | Minutes to hours | Low | Heavy PL/SQL, tight deadline, licence not the driver. BYOL or licence-included. |
| **Aurora PostgreSQL** via SCT + DMS | Minutes with CDC | **High** - conversion, testing, application changes | Licence cost is the driver and there is time |
| **RDS PostgreSQL** via SCT + DMS | Minutes with CDC | High | Same, without Aurora's premium |
| **Oracle on EC2** | Depends | Medium | An Oracle feature RDS does not support, or you need OS access |
| **Native tooling** (Data Guard, RMAN, Data Pump) into EC2 or RDS | Varies | Medium | The DBA team already knows it; often the fastest path with least surprise |

**The decision criteria**, in the order I would apply them:

1. **Run the AWS Schema Conversion Tool assessment first**, before deciding anything. It produces a report of what converts automatically and what needs manual work, quantified in hours. **This is a days-long exercise that de-risks a quarters-long programme**, and skipping it is the most common cause of a migration that overruns. If SCT reports 95 percent automatic conversion, PostgreSQL is realistic; if it reports thousands of hours of PL/SQL rewriting, it is a separate project.
2. **Separate the platform move from the engine change.** Doing both at once doubles the risk. If the deadline is tight, **lift to RDS for Oracle now and convert to PostgreSQL later** as a funded, separate piece of work. That is frequently the right answer and it is the one people are reluctant to say because it sounds unambitious.
3. **The four-hour window is comfortable for a CDC-based cutover and tight for a dump-and-load.** 5 TB via Data Pump or a DMS full load will not reliably complete, validate and be ready for traffic in four hours. So the mechanism should be **full load in advance plus continuous CDC running for days or weeks**, with the cutover being: quiesce writes → let CDC lag reach zero → validate → repoint → resume. That is minutes, not hours, and it turns the four-hour window into a comfortable one.

**The plan I would propose**, assuming the SCT assessment is favourable:

1. **SCT assessment** and a decision on target engine, funded up front.
2. **Schema conversion** and application remediation, tested against a converted copy.
3. **DMS full load** into the target, followed by **continuous CDC** running for at least two weeks, with **DMS data validation** plus application-level reconciliation queries running throughout.
4. **Dress rehearsal** of the cutover in a lower environment, timed.
5. **Cutover**: freeze writes, drain CDC to zero, validate, repoint, resume, monitor.
6. **Rollback readiness**: **reverse CDC configured before cutover** so the Oracle database keeps receiving changes and fail-back is a connection string change. This is the single most important preparation and the one most often skipped.
7. Keep Oracle running and in sync for a defined period after cutover before decommissioning.

**What I would refuse**: doing the engine conversion and the platform move in the same cutover, decommissioning Oracle on day one, and committing to a date before the SCT assessment exists.

*Hook: a database migration you ran, whether you converted the engine, and what the actual cutover duration was.*

---

## 10. Caching, analytics and purpose-built data services

### Q150. Redis versus Memcached on ElastiCache

**Redis** has data structures (lists, sets, sorted sets, hashes, streams, bitmaps, HyperLogLog), persistence, replication and failover, transactions, Lua scripting, pub/sub, and cluster mode for sharding. **Memcached** is a pure key-value cache: strings only, no persistence, no replication, multi-threaded.

**When Memcached still wins**, honestly - and the list is short but real:

1. **It is genuinely multi-threaded.** Redis (in its classic form) executes commands on a single thread, so a single Redis node is limited by one core for command processing. Memcached scales across all cores on the node, so for a **pure, high-throughput, simple key-value cache on a large instance**, Memcached can deliver more operations per second per node. (Note that ElastiCache for Redis has enhanced I/O and Valkey/Redis 7 improve on this, which narrows the gap.)
2. **Simplicity of horizontal scaling for a pure cache.** You add nodes and the client-side consistent hashing distributes keys. No cluster mode, no slot management, no failover semantics to reason about.
3. **Lower memory overhead per key** for simple string values.
4. **You genuinely do not need any of Redis's features** and value having less to operate and reason about.

**Everything else favours Redis**, and in practice Redis is the default: replication and automatic failover (Memcached has none - a lost node is lost data with no HA at all), persistence, the data structures that let you implement rate limiters, leaderboards, session stores, queues and locks without a second system, backup and restore, and encryption in transit and at rest.

**The honest summary**: I would choose Redis unless the workload is a pure cache where losing a node's data is completely acceptable and per-node throughput is the binding constraint. And I would note that **Valkey** (the open-source fork, now offered on ElastiCache at lower cost) is increasingly the default choice over Redis for new deployments on licensing and price grounds.

*Hook: a caching layer you built, which engine, and whether the choice was ever revisited.*

### Q151. Redis cluster mode enabled versus disabled

**Cluster mode disabled**: a single shard - one primary and up to five read replicas. All data fits on one node's memory. Scaling means a **bigger node** (vertical) or **more replicas** (read scaling only).

**Cluster mode enabled**: data is **sharded across up to 500 node groups**, each with its own primary and replicas, using **16,384 hash slots** distributed across shards. Writes scale horizontally; the dataset can far exceed one node's memory.

**What changes for the client**, which is the operationally important part:

- The client must be **cluster-aware**. It discovers the topology, computes the hash slot for each key (CRC16 mod 16384), and connects to the right shard. A non-cluster client simply fails with `MOVED` redirections.
- **Multi-key operations only work within a single slot.** `MGET`, `MSET`, transactions, Lua scripts touching multiple keys, and set operations all require the keys to be in the same slot - otherwise you get `CROSSSLOT` errors. **This is the change that breaks existing applications**, and it is discovered at runtime rather than at deploy time.
- **Hash tags** (`user:{123}:profile` and `user:{123}:settings`) force related keys into the same slot by hashing only the braced portion. Designing these up front is what makes cluster mode workable.
- **Resharding is online** but moves slots between nodes, with brief redirections during the move.

**Choosing**: cluster mode disabled while the dataset fits comfortably in one node with headroom (and note that ElastiCache nodes go up to hundreds of gigabytes, so this covers a great deal), and cluster mode enabled when you need **write throughput beyond one node**, a dataset larger than one node, or you want the ability to scale horizontally without a maintenance event.

**The advice worth giving**: **enable cluster mode from the start even with a single shard** if there is any prospect of growth, because migrating a live application from non-cluster to cluster mode means fixing every multi-key operation under pressure. The cost of starting cluster-aware is a slightly more capable client library; the cost of converting later is an application project.

*Hook: a Redis scaling decision, and whether multi-key operations forced a redesign.*

### Q152. ElastiCache Serverless versus node-based

**Serverless** removes capacity planning: you create a cache, get a single endpoint, and it scales storage and compute automatically based on usage. Billed per **GB-hour of data stored** and per **ElastiCache Processing Unit (ECPU)** consumed. It is multi-AZ by default, patches itself, and reaches usable capacity in about a minute.

**Node-based** means you choose instance types, shard count, replica count, AZ placement, and manage scaling, patching windows and failover configuration yourself.

**What you pay for and give up:**

*Serverless gains*: no capacity planning, instant provisioning, automatic scaling for spiky workloads, no over-provisioning for peak, no maintenance windows, and a dramatically lower operational burden. For a workload that is idle much of the time - development, an internal tool, a new service with unknown load - it is far cheaper because you are not paying for a running node.

*Serverless costs*: **the unit economics are worse at steady high load.** A predictable, constantly-busy cache is cheaper on reserved node-based instances, often substantially. You also give up: **fine-grained control** over node types and placement, some **configuration parameters**, the ability to reason precisely about which node holds what, and there are **feature gaps** at any given time that need checking against your requirements.

**The decision rule**: **serverless for variable, unpredictable or low-average workloads, and for anything where operational simplicity is worth a premium; node-based with reserved instances for steady, high, predictable load.** The same shape as Aurora Serverless v2 (Q140), and the same trap - people adopt serverless for a workload that turns out to be constant and then wonder why it costs more.

The practical approach: **start serverless for a new workload**, measure the actual pattern for a month, and move to node-based if the utilization curve turns out to be flat. That gets you the right answer with evidence rather than a guess.

*Hook: a serverless-versus-provisioned decision for a cache or database, and what the measured utilization curve showed.*

### Q153. Caching patterns and their AWS-specific costs

**Lazy loading (cache-aside)**: the application checks the cache; on a miss it reads the database and populates the cache. *AWS-specific costs*: every miss is a full round trip - application to ElastiCache (a fraction of a millisecond in-AZ, more cross-AZ), then to the database, then back to the cache. **Cross-AZ traffic is charged at $0.01/GB each way**, so a cache in a different AZ from the application pays both latency and money on every operation - which is why node placement and AZ-aware clients matter. The bigger risk is the **thundering herd** on a cold cache or a mass eviction: every request misses simultaneously and the database receives the full load, which is Q154.

**Write-through**: every write updates the cache and the database. *Costs*: write latency now includes both systems, and you cache data that may never be read, consuming memory (and therefore node size, and therefore money) for nothing. On ElastiCache Serverless you pay per GB-hour stored, so **caching unread data has a direct, itemized cost** that node-based deployments hide inside the instance price.

**TTL-based expiry**: everything gets a TTL and refreshes on expiry. *Costs*: **synchronized expiry** is the danger - if a batch of keys is written at the same moment with the same TTL, they all expire together and produce a coordinated stampede. **Jitter the TTL** (base plus a random component) as a matter of routine.

**The AWS-specific considerations that cut across all three:**

- **Cross-AZ charges and latency** make placement a real design input. Use an AZ-aware client where possible.
- **Eviction policy** (`maxmemory-policy`) matters: `allkeys-lru` for a pure cache, `volatile-lru` when the cache also holds data you cannot afford to lose, and `noeviction` if writes must fail rather than silently discard - and choosing wrong turns a cache into a data-loss mechanism.
- **The `Evictions` and `CacheMisses` metrics** together tell you whether the cache is undersized, and `SwapUsage` above zero on a node is a red flag.
- **The failover behaviour**: a node failure loses its data unless you have replicas, and the reconnect storm afterwards is itself a load event.

**The pattern I would default to**: cache-aside with jittered TTLs, plus write-through only for data that is expensive to compute and certain to be read.

*Hook: a caching pattern you implemented, and whether the cost surprise was memory, cross-AZ transfer or a stampede.*

### Q154. The cache that collapses at peak

Three distinct mechanisms, and they look similar from outside:

1. **Thundering herd / cache stampede.** A popular key expires (or is evicted) and hundreds of concurrent requests all miss simultaneously, all query the database, all recompute the same value, and all write it back. The database is hit with a burst it never sees in testing because in testing there is not enough concurrency for the requests to overlap. **The fix**: a **lock or single-flight** so only one request recomputes while others wait or serve stale; **probabilistic early expiration** (refresh before expiry with increasing probability); and **jittered TTLs** so keys do not expire in lockstep.
2. **Memory pressure and eviction cascade.** At peak the working set exceeds the node's memory, the eviction policy starts discarding entries, the hit rate falls, more requests go to the database, response times rise, more requests are in flight simultaneously, and more data is cached - which evicts more. It is a metastable failure: the eviction is now causing the load. **The signals**: `Evictions` climbing, `DatabaseMemoryUsagePercentage` near 100, `CacheHitRate` falling under load rather than rising. **The fix**: size for peak working set with headroom, review what is being cached, set a sane eviction policy, and consider whether large objects belong in the cache at all.
3. **Connection exhaustion or single-thread saturation.** Redis processes commands on one thread; at peak, either the **connection count** hits the limit (`CurrConnections` against `maxclients`), or the **CPU on the single command thread** saturates (`EngineCPUUtilization` at 100 percent while overall `CPUUtilization` looks fine - **this distinction is the diagnostic**), or a **slow command** (`KEYS`, a large `SMEMBERS`, an unbounded `LRANGE`, an expensive Lua script) blocks the thread and every other client queues behind it. **The fix**: check `EngineCPUUtilization` specifically, find slow commands with the slow log, eliminate O(N) commands on large collections, shard with cluster mode to get more command threads, and pool connections properly.

**A fourth worth mentioning**: a **hot key** - one key receiving a disproportionate share of traffic - saturates a single shard regardless of how many shards you have, and no amount of scaling helps. The fix is client-side caching of that key or key splitting.

**Why testing missed it**: all four require **concurrency and data volume** that test environments do not have. A load test with a warm cache and a small dataset exercises none of these. The test that finds them is a load test **with a cold cache**, at production data volume, at production concurrency.

*Hook: a cache collapse you diagnosed, which mechanism it was, and how you reproduced it afterwards.*

### Q155. MemoryDB versus ElastiCache for Redis

**ElastiCache for Redis is a cache**: data lives in memory, replication is asynchronous, and a failover can lose recently written data. Its durability options (RDB snapshots, AOF) reduce but do not eliminate the window. It is designed on the assumption that the source of truth is elsewhere.

**MemoryDB is a durable database with Redis compatibility**: every write is **synchronously committed to a multi-AZ transaction log** before being acknowledged. It offers **microsecond reads and single-digit millisecond writes**, with 11 nines of durability and no data loss on failover.

The trade-off is exactly what you would expect: **MemoryDB's writes are slower** (single-digit milliseconds versus microseconds) because they wait for the distributed log, and it **costs more per GB**.

**What it lets you delete from your architecture** - the interesting part:

The classic pattern is **Redis as a cache in front of DynamoDB or Aurora**, which means: two systems to operate, a cache-invalidation problem, a consistency window, code implementing the cache-aside pattern everywhere, and a cold-cache failure mode. **MemoryDB collapses that into one system** - it is both the fast access layer and the durable store. For a workload whose data model is naturally Redis-shaped (leaderboards, session state, real-time feeds, geospatial queries, rate limiting at scale) and whose entire dataset fits in memory, this removes a whole tier and the class of bugs that comes with it.

**When it is not the answer**: when the dataset is too large to hold in memory economically (memory is expensive per GB compared with DynamoDB or S3), when the access pattern is genuinely relational or analytical, or when write latency of microseconds is required. And the cost comparison must be done honestly: MemoryDB holding a large dataset entirely in memory can be far more expensive than DynamoDB plus a small cache, so the "one system" simplification has a price.

*Hook: a case where you considered collapsing a cache and a database into one system, and what decided it.*

### Q156. What Redshift is for, and when it is wrong

Redshift is a **columnar, massively parallel processing data warehouse** for **analytical queries over large volumes of structured data** - aggregations, joins and scans across billions of rows, with results in seconds. Columnar storage means a query touching 3 of 200 columns reads only those 3; MPP means the work is distributed across compute nodes; and compression on columnar data is dramatic.

**Three cases where it is the wrong answer:**

1. **As an operational or transactional database.** Redshift is optimized for large scans, not for single-row lookups or high-frequency small writes. A point query by primary key that a relational database answers in a millisecond takes Redshift far longer, and row-level `INSERT`/`UPDATE`/`DELETE` at OLTP rates is pathological - it is designed for bulk loads. **Using Redshift behind an application API is a classic and expensive mistake.**
2. **When the data volume is small or the query frequency is low.** A cluster running continuously for a few hundred gigabytes queried occasionally is expensive compared with **Athena over Parquet in S3**, which has no cluster to run and charges per query. The crossover is roughly: if the warehouse is not busy most of the day, Athena or Redshift Serverless is cheaper.
3. **For unstructured, semi-structured-heavy, or highly variable schemas** - deeply nested JSON, log search, free-text queries. OpenSearch or Athena over a data lake handles these better, and forcing them into a warehouse schema is work with no payoff.

A fourth worth adding: **as a real-time store**. Redshift is a batch-oriented system; streaming ingestion exists (Kinesis/MSK streaming ingestion) but sub-second freshness across the estate is not what it is for.

**The correct positioning**: Redshift for a **curated, high-concurrency, business-critical warehouse** where many analysts and BI dashboards query the same modelled data repeatedly - which is where its performance and its cost model both make sense.

*Hook: a Redshift deployment that was right, or one you replaced with Athena.*

### Q157. Redshift architecture

**The leader node** receives client connections, parses and optimizes queries, generates compiled code, distributes work to compute nodes, and aggregates their results. It stores no user data and runs no user query segments.

**Compute nodes** hold data in **slices** (a portion of memory and disk per node) and execute the query segments in parallel. Node count and type determine capacity and throughput.

**RA3 with managed storage** is the architectural change worth understanding. Older node types (DS2, DC2) coupled compute and storage - to store more data you bought more nodes even if you did not need the compute. **RA3 separates them**: data lives in **S3-backed managed storage**, with a large local SSD cache on each node holding the hot working set. You size the cluster for the compute you need and pay separately for the storage you use, and they scale independently. That decoupling is what makes elasticity - concurrency scaling, pause/resume, cross-cluster data sharing - possible at all.

**Redshift Spectrum** queries data **directly in S3** without loading it, using the Glue Data Catalog for schema, and executes the S3 scan on a separate fleet of Spectrum nodes. Its purpose is the **warehouse plus data lake** pattern: keep hot, curated, frequently-joined data in Redshift's managed storage, and leave the cold historical bulk in S3 as Parquet, queryable in the same SQL statement with a join between them. It is billed per **TB scanned**, so partitioning and columnar formats matter exactly as they do for Athena (Q159).

Two more concepts that always come up alongside: **distribution style** (`KEY`, `EVEN`, `ALL`, `AUTO`) determines how rows are spread across slices and is the single biggest determinant of join performance - a bad distribution key causes data to be redistributed across the network on every join; and **sort keys** determine physical ordering and enable zone-map pruning, which is how Redshift skips reading blocks entirely.

*Hook: a Redshift performance problem traced to distribution or sort keys.*

### Q158. Serverless, concurrency scaling and WLM

- **Redshift Serverless** removes the cluster: you specify a base capacity in **RPUs** and it scales automatically, charging per RPU-second **only while queries run**. Ideal for intermittent or unpredictable analytics, development, and workloads with long idle periods.
- **Concurrency scaling** adds **transient clusters** automatically when queries queue on a provisioned cluster, routing the overflow to them. You accrue one hour of free concurrency-scaling credit per day per cluster, which covers most bursts; beyond that it is billed per second.
- **Workload management (WLM)** allocates memory and concurrency across **query queues**, routing queries by user group or query group. **Automatic WLM** (the recommendation) lets Redshift manage this with query priorities; manual WLM lets you define queues explicitly. **Short Query Acceleration** routes small queries past long-running ones.

**"Our dashboards are slow at 9am" is solved by concurrency scaling**, and the reasoning matters: the symptom is a **burst of concurrent queries queuing** - every analyst and every scheduled dashboard refresh arriving at the start of the business day - against a cluster sized for the average. The queries themselves are not slow; they are **waiting**. Concurrency scaling detects the queueing and offloads it to transient capacity, which is precisely the mechanism for a predictable, bounded, daily burst - and the free daily credits often make it cost nothing.

Why not the others: **WLM redistributes** the existing capacity, which helps you prioritize but cannot create throughput that is not there - it would let dashboards jump ahead of ETL, which is a valid partial mitigation and worth doing alongside. **Serverless** would solve it too, but it is a migration of the whole warehouse rather than a setting, and it changes the cost model entirely.

The diagnostic to state: check whether **queue wait time** or **execution time** dominates, using `STL_WLM_QUERY` or the console's workload breakdown. Queue wait means concurrency; execution time means the query, the distribution keys, or the cluster size - and that distinction is what tells you which lever to pull.

*Hook: a warehouse concurrency problem, and whether the fix was capacity, prioritization or query tuning.*

### Q159. Athena versus Redshift, and Athena's cost model

**Athena** is serverless Presto/Trino over data in S3: no infrastructure, no loading, pay **per TB scanned** (~$5/TB). **Redshift** is a provisioned (or serverless) warehouse with data loaded, modelled and optimized.

**Athena wins when:**

- **Query frequency is low or unpredictable.** No cluster running means no cost when nobody is querying. A warehouse queried twice a day cannot justify a cluster.
- **Data is already in S3 in a data lake**, and you want to query it without an ETL pipeline to load it.
- **Ad-hoc and exploratory analysis**, one-off investigations, log analysis, or querying data you do not yet know is valuable.
- **The consumers are few**, since Athena has concurrency limits and no result caching across users in the way a warehouse does.

**Redshift wins when**: many concurrent users, repeated queries over the same modelled data, complex joins across large curated tables, sub-second dashboard requirements, and workloads where the per-query cost of scanning would exceed a cluster's fixed cost.

**How partitioning, format and compression change Athena's cost by an order of magnitude** - because the bill is *entirely* a function of bytes scanned:

1. **Columnar format.** Converting CSV or JSON to **Parquet or ORC** means a query touching 3 of 50 columns reads only those columns. That alone is commonly a **10-30x reduction**, and it is the single highest-value change.
2. **Compression.** Parquet with Snappy or ZSTD reduces bytes further - typically another 3-5x over uncompressed - and Athena charges for compressed bytes scanned.
3. **Partitioning.** Partitioning by date (`s3://bucket/table/year=2026/month=09/day=01/`) means a query with a date predicate scans one day instead of three years - a **1000x reduction** for a typical "yesterday" query. Use **partition projection** to avoid the metadata overhead of millions of partitions.
4. **File size.** Many tiny files is slow and inefficient; **compact to 128 MB - 1 GB files**. This affects performance more than cost, but it matters.
5. **`SELECT` only the columns you need** - `SELECT *` defeats columnar storage entirely, and is the most common user error.

The concrete example worth quoting: **1 TB of JSON scanned costs $5; the same data as partitioned Parquet, with a query touching one day and four columns, might scan 200 MB and cost a tenth of a cent.** That is the difference between an unusable and a trivial bill, and it is why "Athena is expensive" almost always means "the data lake is badly laid out".

*Hook: an Athena cost reduction from format or partitioning, and the factor you achieved.*

### Q160. Glue and when to use EMR instead

**Glue crawlers** scan data in S3 (or JDBC sources), infer schema and partitions, and populate the **Glue Data Catalog** - a Hive-compatible metastore that Athena, Redshift Spectrum, EMR and Glue jobs all share. It is the connective tissue of a data lake: one schema definition, consumed by every engine.

**Glue ETL jobs** run serverless Spark (or Python shell, or Ray) with a managed environment, billed per **DPU-hour** with a one-minute minimum. Glue Studio provides a visual editor; DynamicFrames add schema flexibility over Spark DataFrames.

**When to use EMR instead:**

1. **You need control over the cluster** - specific Spark, Hadoop or Hive versions, custom configurations, specific instance types, GPU nodes, or tuning that Glue does not expose.
2. **The ecosystem beyond Spark** - Hive, HBase, Presto, Flink, Trino, Hudi/Iceberg at a version Glue does not offer, or a machine learning library requiring a particular environment.
3. **Cost at sustained scale.** Glue is priced for convenience; for **long-running, large, continuous workloads**, EMR on Spot instances (or EMR on EKS) is substantially cheaper. The crossover comes surprisingly quickly for daily multi-hour jobs.
4. **Long-running or interactive workloads** - a persistent cluster with notebooks attached, where Glue's job model is a poor fit.
5. **Lift-and-shift of an existing Hadoop estate**, where matching the on-premises stack matters.

**Glue wins for**: event-driven and scheduled ETL, moderate data volumes, teams without Spark operational expertise, and anything where not managing a cluster is worth the premium. **The Data Catalog you should use regardless** - even with EMR - because it is the shared metadata layer, and running a separate Hive metastore is work with no benefit.

**Worth adding**: for simple transformations, neither may be needed. **Athena CTAS statements** can do a great deal of ETL declaratively, and for streaming, **Firehose with dynamic partitioning** handles the common "land it as partitioned Parquet" case without any Spark at all. Reaching for Spark when SQL would do is a common over-engineering pattern.

*Hook: a Glue-versus-EMR decision, and whether cost or control drove it.*

### Q161. Lake Formation

Lake Formation adds **fine-grained access control over the data lake**, centrally managed and enforced consistently across Athena, Redshift Spectrum, EMR, Glue and QuickSight.

**What it adds over bucket policies and IAM:**

1. **Table, column, row and cell-level permissions.** IAM and bucket policies operate on **prefixes and objects** - you can grant access to `s3://lake/sales/` but not to "the sales table excluding the `salary` column" or "only rows where `region = 'EU'`". Lake Formation grants permissions on **catalog objects** with column filters and row-level filter expressions.
2. **A single grant model across engines.** The same permission applies whether the user queries through Athena, Spectrum or EMR, rather than being reimplemented per engine.
3. **Tag-based access control (LF-Tags)**, which is what makes it scale: tag tables and columns (`classification=pii`, `domain=finance`), grant permissions on tags rather than on resources, and new tables inherit the policy automatically. This is the mechanism that turns hundreds of grants into a handful.
4. **Cross-account data sharing** through the catalog, without copying data or writing bucket policies per consumer - the foundation of a data mesh.
5. **Centralized audit** of data access decisions.

**When it is worth the complexity**: when you have **multiple consumer teams with genuinely different entitlements** over shared data, when there is **regulated data (PII, financial, health) requiring column or row-level control**, when **cross-account sharing** is needed, or when a compliance regime requires demonstrable, auditable, centralized access governance. In other words: a real, multi-tenant, governed data lake.

**When it is not**: a single team's data lake where everyone has the same access. Lake Formation introduces a permission layer that must be correct for anything to work, and the classic failure mode is **the hybrid state** - some access via IAM, some via Lake Formation, with permissions that appear correct and queries that fail confusingly. Adopting it is a decision to route *all* lake access through it, and doing it halfway is worse than not at all. That is the trade-off to name.

*Hook: a data governance requirement that justified Lake Formation, or a case where you decided IAM was sufficient.*

### Q162. Kinesis Data Streams versus Firehose for analytics ingestion

| | Data Streams | Firehose |
| --- | --- | --- |
| **Model** | A durable, replayable **log** you read from | A **delivery pipeline** to a destination |
| **Consumers** | Many, independent, each with their own position | One configured destination |
| **Retention** | 24 hours to 365 days - **replayable** | None; buffered and delivered |
| **Latency** | ~200 ms, real-time | **Buffered - 60 seconds minimum** (or by size), typically minutes |
| **Ordering** | Per partition key | Not guaranteed |
| **Management** | Shards (or on-demand), scaling, consumer position | **Fully managed, no capacity to size** |
| **Transformation** | Your consumer code | Built-in Lambda transform, format conversion to Parquet/ORC, dynamic partitioning |
| **Destinations** | Anything you write | S3, Redshift, OpenSearch, Splunk, HTTP endpoints |

**What decides it:**

1. **Do you need more than one independent consumer, or replay?** If yes, **Data Streams** - that is the defining capability. Analytics plus a real-time alerting consumer plus a future consumer you have not built yet, all reading independently from their own position, is only possible with a log.
2. **Is sub-second latency required?** Firehose's minimum buffer is 60 seconds, so anything real-time needs Data Streams.
3. **Is the destination simply "S3 as partitioned Parquet"?** Then **Firehose**, and it is not close - it does buffering, compression, **format conversion to Parquet using the Glue schema**, and **dynamic partitioning** with no code. Building that on Data Streams means writing and operating a consumer that does the same thing worse.
4. **Do you want to manage capacity?** Firehose has none to manage.

**The pattern that resolves most real cases**: **Data Streams as the ingestion log, with Firehose as one of its consumers** delivering to S3 in Parquet for the analytics tier, while other consumers read the same stream for real-time needs. You get replay, multiple consumers and a managed path to the lake. The cost is two services instead of one, and it is usually worth it.

**Firehose alone** is right when the only destination is the lake or the warehouse and there is genuinely no second consumer - a very common and perfectly good case that people over-engineer.

*Hook: an ingestion pipeline you built, and whether you needed the log or just the delivery.*

### Q163. OpenSearch Service

**Genuinely good for**: full-text search with relevance ranking, log analytics and observability at scale (the ELK use case), aggregations over semi-structured data with sub-second response, geospatial queries, and increasingly **vector search** for semantic retrieval. Its strength is a rich query DSL over high-cardinality, semi-structured data with fast aggregations - which no other AWS service does as well.

**What makes it an operational liability:**

1. **Cluster sizing is genuinely hard and unforgiving.** Shard count is fixed at index creation; too few and you cannot parallelize or scale, too many and the cluster spends its time on shard overhead. The rule of thumb is 10-50 GB per shard, and getting it wrong requires a reindex.
2. **JVM heap pressure is the dominant failure mode.** Heap is capped around 32 GB regardless of instance size, and field data, aggregations on high-cardinality fields and mapping explosion consume it. A cluster under heap pressure degrades, then circuit-breaks, then becomes unresponsive - and the recovery involves rolling restarts that take hours on a large cluster.
3. **Mapping explosion.** Dynamic mapping on logs with variable JSON keys creates thousands of fields, blows up the cluster state, and is very hard to undo.
4. **It is always running and always costing.** A cluster sized for peak ingest runs 24/7. Log analytics clusters routinely become one of the largest line items in an estate, and the data has a short useful life.
5. **Upgrades and node replacements are slow** at scale, and a red cluster during business hours is a bad day.
6. **It is not a database.** No transactions, no joins, eventual consistency, and using it as a primary store leads to the reindex-from-source problem when something goes wrong.

**The mitigations to name**: **UltraWarm and cold storage tiers** for older indices (dramatically cheaper), **Index State Management** policies to roll over and delete automatically, **OpenSearch Serverless** for workloads that do not justify cluster management, explicit mappings rather than dynamic, and being honest about whether **CloudWatch Logs Insights or Athena over S3** would serve the actual query pattern at a fraction of the cost - which for "we occasionally search logs from last week" it usually would.

*Hook: an OpenSearch cluster you operated, the failure mode you hit, and what you would do differently.*

### Q164. Purpose-built database selection

| Service | Access pattern it exists for | Try this first |
| --- | --- | --- |
| **DocumentDB** | MongoDB-compatible document workloads - flexible schemas, nested documents, MongoDB drivers and an existing MongoDB codebase | **DynamoDB** if the access patterns are known and key-based; PostgreSQL with `JSONB` if you want documents plus relational |
| **Neptune** | **Graph traversal** - "friends of friends", fraud rings, recommendations, knowledge graphs, lineage. Queries that would be many self-joins in SQL | **PostgreSQL with recursive CTEs** for shallow traversals; only move to a graph database when traversal depth and pattern-matching are the core workload |
| **Keyspaces** | Cassandra-compatible wide-column - existing Cassandra applications, CQL, very high write throughput with a known partition model | **DynamoDB**, which serves the same shape of workload natively and is better integrated. Keyspaces exists chiefly for compatibility |
| **Timestream** | **Time-series at scale** - IoT telemetry, metrics, sensor data - with time-based retention tiering and time-series functions (interpolation, smoothing, gap filling) | **CloudWatch** if it is operational metrics; **DynamoDB with a time-based key** for moderate volumes; **S3 plus Athena** for analytical time-series that need no real-time query |

**The framing that matters more than the table**: each of these exists because a specific access pattern is expensive or awkward on a general-purpose store. The right question is **"is this access pattern the core of the workload, or an edge of it?"** A social application whose *primary* operation is multi-hop traversal needs Neptune; an application that occasionally needs a two-hop lookup does not, and adding a graph database for it means a second data store, a second consistency problem, a second operational burden and a second thing on call.

**The default I would state**: **DynamoDB for known key-based access patterns, PostgreSQL (Aurora) for everything relational or where the pattern is not yet known** - and Postgres's extensions (`JSONB`, PostGIS, `pgvector`, `ltree`, TimescaleDB where available) cover a remarkable amount of what these specialized services offer, with one system to operate. Reach for a purpose-built store when you have **measured** that the general-purpose one cannot serve the pattern, and can say which query and what the numbers were.

The reason to be disciplined here: **every additional data store is a permanent operational and cognitive cost** - backup, monitoring, upgrades, expertise, an on-call rotation that must understand it - and that cost is paid forever while the benefit is often a single feature.

*Hook: a purpose-built database you adopted or declined, and the measurement behind the decision.*

### Q165. QuickSight, and central lake versus data mesh

**QuickSight** is AWS's managed BI service: dashboards, visualizations, and **SPICE**, its in-memory engine that caches datasets for fast queries without re-hitting the source. Its distinguishing features are **per-user or per-session pricing** (rather than per-server, which makes embedded analytics for many external users economical), native integration with Athena, Redshift, RDS and S3, **row-level security** integrating with Lake Formation, and embedding into applications. Q gives natural-language querying.

It fits as **the consumption layer** over whatever the storage and query layer is. It is not a warehouse and not a transformation tool - people who try to do modelling in QuickSight end up with unmaintainable dataset definitions, and the modelling belongs in dbt, Glue or the warehouse.

**Central lake versus data mesh at 200 engineers:**

**Central lake**: one platform team owns ingestion, storage, modelling and governance. *Strengths*: consistency, a single source of truth, one set of standards, easier governance and compliance, no duplication. *Weaknesses*: the central team becomes a **bottleneck** - every new dataset and every schema change queues behind them; they lack domain knowledge about the data they are modelling; and domain teams disown data quality because they do not own the pipeline.

**Data mesh**: domain teams own their data as a **product** - they publish it with a schema, an SLA, documentation and quality guarantees - and a central platform team provides the self-service infrastructure (catalog, storage, access control, standards) rather than the pipelines. *Strengths*: scales with the organization, puts ownership where the domain knowledge is, removes the bottleneck. *Weaknesses*: requires **real platform maturity** and genuine organizational commitment; inconsistent quality if standards are not enforced by the platform; duplication; and it is a **socio-technical change**, not a tooling choice - which is why most "data mesh" projects fail.

**My position at 200 engineers**: the organization is at roughly the size where a purely central model starts to break, so the answer is **a federated model with a strong central platform**: the platform team owns the catalog (Glue plus Lake Formation), the access control model, the storage standards (Parquet, partitioning conventions, Iceberg tables), the ingestion patterns and the cost visibility; **domain teams own their own datasets and pipelines** within those standards. Governance is enforced by the platform's defaults rather than by review.

And the caveat worth stating: **do not adopt data mesh as a way to avoid building a platform.** The most common failure is declaring a mesh, devolving responsibility to teams with no shared infrastructure, and ending up with forty incompatible data stores and no catalogue. The platform investment comes first.

*Hook: a data platform ownership model you worked in, and where the bottleneck or the inconsistency showed up.*

### Q166. Analytics on top of a live OLTP estate

**Clarify first**: what freshness does the analytics actually need - real-time, hourly, or overnight is fine? What is the query pattern - fixed dashboards, ad-hoc exploration, or ML feature extraction? How many source databases, and what engines? Is there PII requiring masking or access control? What is the current pain - is analytics slow, or is it slowing the OLTP systems? And what is the data volume and growth rate?

The constraint "without changing the transactional systems or degrading them" is the whole design, and it rules out the two things people do first: **querying the production database directly** (degrades it), and **asking application teams to publish events** (changes them).

**The design:**

```
OLTP (RDS/Aurora, live)
  |
  |-- DMS with CDC (read from the replica, not the primary)
  |      or Aurora zero-ETL to Redshift, where available
  v
S3 raw zone (Parquet, partitioned by date)   <- landing, immutable, append-only
  |
  |-- Glue / Athena CTAS / dbt
  v
S3 curated zone (Iceberg tables, conformed model, SCD where needed)
  |
  +--> Athena           (ad-hoc, exploration)
  +--> Redshift Spectrum/Serverless  (dashboards, high concurrency)
  +--> QuickSight       (consumption)
  Glue Data Catalog + Lake Formation across all of it
```

**The decisions and why:**

- **CDC via DMS, reading from a read replica, not the primary.** This is the key move for "without degrading them": DMS full load plus ongoing CDC captures changes from the transaction log with minimal overhead, and pointing it at a **dedicated read replica** isolates even that from the primary. No schema change, no application change, no query load on production.
- **Aurora zero-ETL to Redshift** where the source is Aurora and the target is Redshift - it removes the DMS pipeline entirely and delivers near-real-time replication managed by AWS. Worth checking availability for the specific engine version, and it is the answer that shows current knowledge.
- **Land raw first, immutably.** The raw zone is an append-only record of what the source said, partitioned by ingest date. Everything downstream is derived and rebuildable, which means a modelling mistake is a reprocess rather than a data loss.
- **Iceberg (or Hudi) for the curated zone**, because CDC produces updates and deletes, and a plain Parquet lake handles those badly. Iceberg gives you upserts, time travel and schema evolution, and it is what makes a CDC-fed lake maintainable.
- **Athena as the default query engine, Redshift only if concurrency demands it** (Q159). Start with Athena; the cost model favours it until you have many concurrent users.
- **Lake Formation for column and row-level control** over PII (Q161), since the analytics audience is wider than the OLTP audience and that is where the governance risk lives.

**Guarding against degradation, explicitly**: CDC from a replica; monitor **replica lag** as a first-class metric and alarm on it, since DMS CDC can increase it; throttle DMS during peak windows if needed; and **never** allow analytical queries against the production endpoints - enforce it with security groups and separate credentials, not with a policy document.

**What I would flag to the business**: analytics built on CDC of an OLTP schema **inherits that schema**, including its normalization, its cryptic column names and its lack of history. It works, and it is the right first step, but the long-term answer is domain teams publishing modelled data products (Q165). CDC is the pragmatic bridge that gets value now without touching the transactional systems - and saying that it is a bridge, not the destination, is the honest part.

*Hook: an analytics platform you built over live systems, how you avoided degrading them, and the freshness you delivered.*

---

## 11. Containers, platforms and edge compute

### Q167. The compute platforms in one line each

- **ECS** - AWS's own container orchestrator. Simple object model, deep AWS integration, no control plane to run or upgrade. For teams that want containers without Kubernetes.
- **EKS** - managed Kubernetes. The full ecosystem and portability, and the full operational surface. For teams with Kubernetes expertise or a multi-cloud/portability requirement.
- **Fargate** - a **launch type**, not an orchestrator: serverless compute for ECS tasks or EKS pods, with no instances to manage. For teams that do not want to run nodes.
- **App Runner** - give it a container image or a source repository and get a scaling HTTPS service with a URL. For a single web service where you want nothing else.
- **Elastic Beanstalk** - upload an application, get an ASG, load balancer and deployment tooling managed for you. The 2010s PaaS; still functional, largely superseded.
- **Lightsail** - fixed-price VPS with bundled compute, storage and transfer, and a simplified console. For small, simple, predictable workloads and for people who find the AWS console overwhelming.

The distinction that matters and that people blur: **ECS and EKS are orchestrators; Fargate is a capacity provider underneath either of them.** "ECS versus Fargate" is not a coherent comparison, and being precise about it is a small but reliable signal.

*Hook: a platform selection you made, and the constraint that decided it.*

### Q168. The ECS object model

- **Task definition** - the immutable, versioned blueprint: container images, CPU and memory (at the task level and optionally per container), environment variables and secrets, IAM **task role** and **execution role**, networking mode, volumes, logging configuration, and health checks. Analogous to a pod spec.
- **Task** - a running instantiation of a task definition. One or more containers scheduled together on the same host, sharing a network namespace in `awsvpc` mode.
- **Cluster** - a logical grouping of tasks and (for EC2 launch type) container instances. Mostly a namespace and a capacity boundary.
- **Service** - maintains a **desired count** of tasks from a task definition.

**What a service adds over a task**, which is the substance:

1. **Desired count maintenance** - if a task dies, the service replaces it. A standalone task that exits is simply gone.
2. **Load balancer integration** - the service registers and deregisters tasks with a target group automatically as they come and go, including the deregistration delay handling (Q59).
3. **Rolling deployments** with `minimumHealthyPercent` and `maximumPercent` controlling how many tasks may be stopped and started at once, plus **deployment circuit breaker** with automatic rollback on failure.
4. **Service auto scaling** via Application Auto Scaling (Q80).
5. **Service discovery** via Cloud Map or Service Connect (Q171).
6. **Placement strategies and constraints** (spread across AZs, binpack, per-instance) for EC2 launch type.

So: **run a standalone task for a batch job or a one-off; run a service for anything long-lived that must stay up and receive traffic.** The scheduled-task and standalone-task path (via EventBridge Scheduler) is the right one for cron-style work, and using a service with a desired count of 1 for a batch job is a common mistake that produces a restart loop when the job completes successfully.

*Hook: an ECS deployment configuration - circuit breaker, healthy percent - that mattered during a bad release.*

### Q169. ECS on EC2 versus Fargate

| | ECS on EC2 | Fargate |
| --- | --- | --- |
| **You manage** | The instances: AMI, patching, scaling, capacity | Nothing |
| **Pricing** | Per instance-hour, regardless of task packing | **Per task vCPU and GB-second** |
| **Density** | You can **bin-pack many small tasks** onto one instance and pay for the instance | Each task is billed for its own reservation; **no bin-packing benefit** |
| **Daemon containers** | Supported - one log/metrics/security agent per *instance* | **Not supported** - a sidecar per *task* instead |
| **GPU / special hardware** | Yes | Limited |
| **Image pull time** | Cached on the instance after the first pull - **fast subsequent starts** | **Pulled fresh for every task** (though Fargate has improved caching) - slower cold starts, and it matters for large images |
| **Task size limits** | Up to the instance size | Bounded (up to 16 vCPU / 120 GB) |
| **Ephemeral storage** | Instance disk, configurable | 20 GB default, up to 200 GB |
| **Spot** | Spot instances via capacity providers | Fargate Spot |

**The real trade-offs:**

- **Cost is not one-directional.** Fargate's per-task pricing is higher per unit of compute, so a **densely packed, steadily-utilized** fleet is cheaper on EC2 - and can be much cheaper with Spot and Savings Plans. But a fleet at 30 percent utilization is cheaper on Fargate, because you stop paying for the idle 70 percent. **The crossover is utilization**, and the honest way to answer is to compute it rather than assert a preference.
- **The operational cost of EC2 is real and often understated**: AMI pipeline, patching cadence, cluster auto scaling configuration, draining instances during scale-in, and capacity mismatch (a task that will not fit on any instance). That is engineering time, and for a small team it usually exceeds the compute saving.
- **Daemon containers are the sharpest functional difference.** An organization running Datadog, Splunk or a security agent as a daemonset pays once per instance on EC2 and **once per task on Fargate** - which for many small tasks can double the bill and is the single most common Fargate cost surprise.
- **Large images hurt on Fargate** because the pull is on the critical path of every task start.

**My default**: **Fargate**, and move to EC2 when a measured cost analysis at real utilization justifies it, or when you need GPUs, daemon containers, or task sizes beyond Fargate's limits. Starting on EC2 "because it is cheaper" without doing the arithmetic including operational time is the common error.

*Hook: an EC2-versus-Fargate cost analysis you ran, and what the utilization turned out to be.*

### Q170. Capacity providers and cluster auto scaling

A **capacity provider** connects an ECS cluster to a source of capacity: an **Auto Scaling group** (for EC2) or **`FARGATE` / `FARGATE_SPOT`**. A **capacity provider strategy** on a service or task distributes tasks across providers with a **base** (a minimum number of tasks on this provider) and a **weight** (the ratio above the base) - which is the mechanism for "always at least 2 tasks on regular Fargate, then 80 percent of the rest on Fargate Spot".

**How the ASG knows to add an instance for a pending task** - this is **Managed Scaling**, and the mechanism is worth explaining precisely because "the ASG scales on CPU" is the wrong answer:

1. ECS computes a metric called **`CapacityProviderReservation`**, published to CloudWatch. It is, roughly, `(instances needed to run all current and pending tasks) / (instances currently running) x 100`.
2. If there are pending tasks that do not fit on the existing instances, the "needed" figure exceeds the "running" figure, so the metric goes above 100.
3. A **target tracking policy** on the ASG targets this metric at a **target capacity** you set (say 100, meaning "run exactly enough instances", or 90, meaning "keep 10 percent spare so a new task can start immediately").
4. The ASG scales out until the reservation returns to target.

So the scaling signal is **task placement demand, not resource utilization** - which is the important conceptual point, because CPU-based scaling of a container host fleet is always wrong: an instance can be at 20 percent CPU and still have no room for a task that requests 4 vCPU.

**Managed termination protection** is the companion setting: it prevents the ASG from terminating an instance that still has non-daemon tasks running, so scale-in drains properly instead of killing work. **Enable it** - without it, cluster auto scaling and ECS fight each other, and the symptom is tasks being killed during quiet periods.

The practical guidance: set **target capacity slightly below 100** (90-95) if task start latency matters, accepting some idle capacity as the price of fast placement.

*Hook: a cluster auto scaling configuration, and whether tasks ever sat pending for want of capacity.*

### Q171. Service discovery for ECS

| Option | Mechanism | Best for |
| --- | --- | --- |
| **Cloud Map (ECS Service Discovery)** | Registers task IPs into a Route 53 private hosted zone; clients resolve `service.namespace` by DNS | Simple, no proxy hop, works with any protocol. **DNS caching and no health-aware load balancing** are the weaknesses |
| **Internal ALB** | Tasks register in a target group; clients call the ALB's DNS name | HTTP services needing path routing, TLS termination, or an entry point from outside. Costs ~$16-22/month each and adds a hop |
| **ECS Service Connect** | An **Envoy sidecar** injected per task, with ECS managing the configuration; clients call a logical name and the sidecar handles discovery, load balancing, retries and telemetry | **The modern default for service-to-service inside ECS** |

**Which and why**: **Service Connect** for east-west traffic between ECS services, for the reasons in Q65 - it gives client-side load balancing that is health-aware, automatic retries, per-connection metrics without instrumenting the application, and **no per-service load balancer cost** - while being managed by ECS rather than requiring a mesh control plane you operate. Its limitation is that it is ECS-only, so it does not help if half the estate is on EKS or EC2.

**Cloud Map** where you need plain DNS - a non-HTTP protocol, a client that cannot use a sidecar, or integration with something outside ECS. The caveat to state is **DNS caching**: a client that resolves once and holds the address will keep calling a task that no longer exists, which is the same failure as Q88 in miniature, and it is why DNS-based discovery for containers (which churn constantly) is weaker than it looks.

**Internal ALB** where the service is an **entry point** - traffic arriving from outside the cluster, from another VPC, or from a client that needs a stable HTTP endpoint with TLS. Also where you need layer-7 routing that Service Connect does not do.

The composite answer for a real estate: **Service Connect for internal service-to-service, one ALB at the edge for ingress**, and Cloud Map only for the protocol exceptions.

*Hook: a service discovery mechanism you chose in a container estate, and its failure mode.*

### Q172. Fargate task cannot pull the image

Four causes, and the diagnostic is largely about *where* the task is and *which* role is involved:

1. **No network path to ECR.** A task in a **private subnet with no NAT gateway and no VPC endpoints** cannot reach ECR. This is the most common cause. ECR needs **three** endpoints: `com.amazonaws.<region>.ecr.api`, `com.amazonaws.<region>.ecr.dkr`, **and an S3 gateway endpoint** - because image layers are stored in S3 and people configure the first two and miss the third. The symptom is a pull that starts and then times out on layers, which is confusingly different from an outright failure.
2. **The wrong role, or a role without permission.** Image pulling is done by the **execution role** (`ecsTaskExecutionRole`), not the **task role** - a distinction that trips people constantly. It needs `ecr:GetAuthorizationToken`, `ecr:BatchCheckLayerAvailability`, `ecr:GetDownloadUrlForLayer`, `ecr:BatchGetImage`, and `logs:CreateLogStream`/`PutLogEvents` for the log driver. Granting the permission to the task role instead produces exactly this failure.
3. **A missing `assignPublicIp`, or subnet routing.** A task in a **public subnet without `assignPublicIp: ENABLED`** has no route to the internet at all, because Fargate tasks have no public IP unless asked. Similarly, a private subnet whose route table does not point at the NAT gateway.
4. **The image or tag does not exist where you think.** A **cross-account or cross-region** ECR reference without a repository policy permitting the pulling account; a tag that was overwritten or deleted; an architecture mismatch (**an arm64 image on an x86 task**, which is increasingly common with Apple Silicon build machines and produces a confusing error); or a **private registry** (Docker Hub) hitting the anonymous rate limit, which needs credentials in Secrets Manager referenced by `repositoryCredentials`.

**The diagnostic sequence**: read the **stopped task's `stoppedReason`**, which usually names the category directly; check whether the failure is a **timeout** (network - causes 1, 3) or **`AccessDenied`/`unauthorized`** (permissions - cause 2) or **`manifest unknown`/`not found`** (cause 4). That single distinction separates all four in seconds, and it is in the task's own metadata rather than in any log - which is why people miss it and go looking in CloudWatch for logs that were never created, because the container never started.

*Hook: an image pull failure you debugged, and which of these it was.*

### Q173. EKS: what AWS manages and what you do

**AWS manages**: the **control plane** - the API server, etcd, the scheduler and the controller manager - across three AZs, with automatic scaling, patching and backups of etcd. You never see or touch these instances. You pay a flat hourly charge per cluster for it.

**You manage**: everything else. The **worker nodes** (or their absence, with Fargate), the **Kubernetes objects**, **cluster upgrades** (AWS provides new versions; applying them to the control plane and then to the nodes and add-ons is your job, on AWS's support timeline), **networking configuration**, **add-on lifecycle**, **RBAC and its mapping to IAM**, and all the observability, security and policy tooling that a Kubernetes estate needs.

**Managed node groups**: EC2 instances that EKS provisions and manages within an ASG, with EKS handling the bootstrap, the AMI selection (EKS-optimized AMIs), graceful **draining during upgrades and scale-in**, and node health monitoring. You still choose instance types and sizes, and you still trigger upgrades. The alternative - **self-managed nodes** - gives full control of the AMI and bootstrap, and hands you the drain and upgrade logic. **Karpenter** is increasingly the answer instead of node groups: it provisions right-sized nodes just-in-time based on pending pods, which is materially better for both cost and bin-packing, and mentioning it signals current knowledge.

**Fargate profiles**: rules matching namespace and labels; matching pods run on Fargate with no node at all. Good for isolation and for bursty workloads, with real constraints: **no daemonsets** (so per-node logging and security agents do not work - a sidecar per pod instead, the Q169 problem again), no privileged containers, no GPUs, one pod per "node", and slower pod start.

**Add-ons**: EKS-managed versions of the components a cluster needs - **VPC CNI, CoreDNS, kube-proxy**, EBS and EFS CSI drivers, Pod Identity agent. Managing them as EKS add-ons rather than raw manifests means AWS handles version compatibility with the control plane, which removes a real class of upgrade pain.

**The honest summary**: EKS removes control-plane operations, which is perhaps 20 percent of the work of running Kubernetes. **The other 80 percent - upgrades, networking, add-ons, RBAC, policy, observability, cost - is still yours**, and underestimating that is why "we chose EKS to reduce operational burden" often disappoints.

*Hook: an EKS upgrade or add-on compatibility problem, and what it cost in time.*

### Q174. EKS networking and IP exhaustion

**The VPC CNI gives every pod a real VPC IP address** from the subnet, via secondary IPs on the node's ENIs. This is the defining property of EKS networking: pods are first-class VPC citizens, reachable directly, with security groups applicable to them, and no overlay or NAT between pods and other AWS resources. It is why EKS integrates so cleanly with ALBs, security groups and VPC flow logs.

**The cost is IP consumption.** Each instance type supports a fixed number of ENIs with a fixed number of IPs each, so **the maximum pods per node is a function of instance type**, and by default the CNI **pre-allocates a whole ENI's worth of IPs** to keep pod start fast (the "warm pool"). A modest node can hold 50-100 IPs whether or not it is running that many pods.

**You exhaust the subnet** when: the cluster grows, nodes multiply, each node reserves a block of IPs, and the `/24` subnets someone created early on run out. The symptom is pods stuck in `ContainerCreating` with a `failed to assign an IP address` error, and **nodes that join the cluster but cannot schedule anything**. It happens suddenly, at scale, usually during a rollout when pod count temporarily doubles.

**The options, in the order I would consider them:**

1. **Add secondary CIDRs to the VPC** (`100.64.0.0/10` from the shared address space is the standard choice, since it does not consume RFC 1918) and create new subnets for nodes in it. **The most common and least disruptive fix** - it does not renumber anything, and pods get IPs from the new range while nodes stay where they are.
2. **Prefix delegation.** Configure the CNI to assign **`/28` prefixes** rather than individual IPs to ENIs. This dramatically increases pods per node and reduces API churn - but it allocates in blocks, so it can *worsen* fragmentation on a nearly-full subnet. It is the right default for a new cluster.
3. **Tune the warm pool** - `WARM_IP_TARGET` and `MINIMUM_IP_TARGET` - to reduce over-allocation. Reduces waste at the cost of slower pod starts when scaling.
4. **IPv6 for the cluster** (Q127), which eliminates the problem structurally - pods get IPv6 addresses from an effectively unlimited space. The right long-term answer, and it requires the whole estate to cope with IPv6.
5. **A different CNI** (Calico with an overlay) - pods get non-VPC addresses, so the subnet is irrelevant. You lose the direct VPC integration, security groups per pod, and the simplicity, which is usually too high a price.

**Pod Identity and IRSA**: the two mechanisms for giving a pod an IAM role. **IRSA** uses an OIDC provider on the cluster and a service account annotation, with a trust policy referencing the OIDC issuer - powerful, and fiddly to set up per cluster. **EKS Pod Identity** is the newer mechanism: an agent add-on plus an association between a service account and a role, with **no OIDC provider and no trust policy per cluster**, which makes it far easier to manage across many clusters and is the one to use for new work.

*Hook: an IP exhaustion event on EKS, and which mitigation you applied.*

### Q175. ECR at multi-account scale

**Lifecycle policies** are non-negotiable: rules that expire images by age or count (keep the last 20 tagged with `prod-*`, expire untagged images after 7 days). Without them, every build's image accumulates forever and the repository becomes a real storage line item - and the untagged-image accumulation from overwritten tags is the largest part of it.

**Image scanning**: **basic scanning** (on push, against the CVE database) is free and should always be on. **Enhanced scanning** uses Amazon Inspector, scans continuously as new CVEs are published rather than only at push time, and covers OS and language packages. The continuous part is the important difference: an image that was clean when pushed and is now vulnerable is the normal case, and only enhanced scanning tells you. Wire the findings to EventBridge so a critical CVE in a running image raises a ticket automatically rather than sitting in a console.

**The cross-account strategy for a multi-account estate** - the pattern:

- **One shared "artifacts" or "shared-services" account owns the ECR repositories.** Builds push there from CI; workload accounts pull from there. This gives one place for scanning, lifecycle, immutability and audit, and it means production is not pulling from an account where developers can push.
- **Repository policies** grant `ecr:BatchGetImage`, `ecr:GetDownloadUrlForLayer` and `ecr:BatchCheckLayerAvailability` to the workload accounts (ideally conditioned on `aws:PrincipalOrgID` rather than listing accounts).
- **`ecr:GetAuthorizationToken`** must be granted in the *pulling* account's execution role - it is an account-level action, not a repository one, and forgetting it is the classic cross-account pull failure (Q172).
- **Tag immutability on** for production repositories, so a tag can never be repointed at different content. This closes a genuine supply-chain gap and costs nothing.
- **Deploy by digest, not by tag** (`image@sha256:...`), which makes the deployed artifact unambiguous.

**Cross-region**: **ECR replication rules** copy images to other regions automatically on push. Essential for multi-region deployments and for DR, because a region that cannot pull its images cannot recover - and pulling cross-region at scale is slow and incurs data transfer. Replication should be configured as part of the landing zone, not remembered at failover time.

*Hook: an ECR strategy across accounts, or a cross-account pull failure you debugged.*

### Q176. AWS Batch

Batch is a managed **job scheduler and capacity manager for batch computing**: you submit jobs, it provisions compute, runs them, and scales the capacity down when the queue is empty. It exists for workloads that are computational, finite, and tolerant of latency - simulations, genomics, rendering, financial risk calculations, large ETL, image and video processing.

**The object model:**

- **Job definition** - the blueprint: container image, vCPU and memory, IAM role, retry strategy, timeout, environment.
- **Job queue** - where jobs wait. Queues have a **priority** and are mapped to one or more compute environments **in order of preference**.
- **Compute environment** - the capacity: **managed** (Batch provisions EC2 or Fargate for you, within your instance-type and vCPU limits) or **unmanaged** (you provide the ECS cluster). Managed environments specify allocation strategy, instance types, min/max/desired vCPUs, and whether to use **On-Demand or Spot**.

**How this relates to Spot** - the important part, and the reason Batch exists rather than a plain ASG:

A compute environment can be `SPOT` with a **bid percentage** and an allocation strategy (`SPOT_CAPACITY_OPTIMIZED` or `SPOT_PRICE_CAPACITY_OPTIMIZED`). Because Batch jobs are **retryable by definition** and Batch has a **built-in retry strategy** (including retry on specific exit codes and on Spot interruption), Spot interruption becomes a scheduling event rather than a failure - the job is simply re-queued and re-run. That is what makes Batch the natural home for Spot: the workload's fault tolerance is a property of the job model rather than something you engineer.

The standard pattern is **a queue mapped to a Spot compute environment first and an On-Demand environment second**, so jobs run on Spot when capacity exists and fall back to On-Demand when it does not - giving you 70-90 percent savings with a bounded worst case.

**Batch versus the alternatives**: Step Functions distributed map for orchestrating many small serverless tasks; ECS scheduled tasks for simple periodic jobs; EMR for Spark specifically. **Batch is right when jobs are long-running, resource-hungry, have dependencies between them (array jobs and job dependencies), and need capacity managed across a fleet** - which is where Lambda's 15-minute limit and Step Functions' orchestration model both stop being enough.

*Hook: a batch workload you ran on AWS, whether on Spot, and what the saving and interruption rate were.*

### Q177. Elastic Beanstalk in 2026

**When it is still right:**

1. **A small team with a conventional web application and no platform engineering capacity.** Beanstalk gives you an ASG, a load balancer, health monitoring, rolling deployments, log aggregation and a rollback mechanism, from a `.jar` or a `.zip`, with no IaC to write. For a team of three shipping a Spring Boot application, that is genuine value.
2. **An existing Beanstalk estate that works.** Migrating a functioning application off it for architectural purity is rarely a good use of a quarter.
3. **Rapid prototyping or an internal tool** where the goal is to be running today.
4. **Organizations that need a paved road and have no platform team** - Beanstalk *is* a paved road, and a bad paved road beats no paved road.

**What it hides that eventually hurts:**

1. **The resources it creates are yours to inherit.** Beanstalk generates an ASG, security groups, a load balancer and IAM roles with its own conventions. The moment you need something it does not expose - a specific ALB rule, a custom health check, a particular scaling behaviour - you are editing generated resources, and Beanstalk may revert them on the next deploy. **The abstraction leaks precisely when you have outgrown it.**
2. **Configuration is in `.ebextensions` and platform hooks**, which is a bespoke, poorly-documented, order-dependent mechanism that nobody else in the industry knows. It is IaC without the tooling, review or testing.
3. **Platform versions age**, and upgrading a platform branch that has reached end of support is disruptive; teams discover this when their Java or Node version is deprecated.
4. **It obscures what is actually running**, so when something breaks, the team debugging it has never seen the underlying resources and does not know where to look.
5. **Deployment models** (all-at-once, rolling, rolling with additional batch, immutable, blue/green via swap) are limited compared with what ECS or a proper pipeline offers, and the defaults are not the safe ones.

**My position**: Beanstalk is a reasonable answer for a small team's simple web application and a poor answer for anything that will grow. For new work I would default to **App Runner** (simpler, more modern, container-native) or **ECS on Fargate with a shared IaC construct** (more work up front, no ceiling). The deciding question is whether there will be a platform capability in a year - if yes, start where you are going.

*Hook: a Beanstalk application you inherited or migrated, and what forced the change.*

### Q178. Lightsail

**The honest positioning**: Lightsail is AWS's answer to DigitalOcean and Linode - a **fixed monthly price** bundling an instance, SSD storage and a data transfer allowance, with a **simplified console** that hides the rest of AWS. It offers instances, managed databases, load balancers, object storage, containers and static IPs, all with the same bundled-price model.

**What it is genuinely good for**: a small predictable workload where **cost certainty matters more than elasticity** - a WordPress site, a small internal tool, a personal project, a development box, a customer-facing site for a small business. The pricing is genuinely simpler and often cheaper than the equivalent EC2 plus EBS plus data transfer, and the console does not require understanding VPCs, security groups and IAM. For a developer who wants a server for $5 a month, it works.

**What it is not**: it is deliberately limited. No Auto Scaling groups, minimal IAM integration, no CloudFormation support to speak of, a restricted instance range with no modern families, limited networking (a managed VPC you do not control), and none of the services a real architecture uses. **The moment you need a second AZ, a real load balancer, IAM roles, or integration with the rest of AWS, you have outgrown it.**

**The migration path off it**: Lightsail instances can be **exported as EC2 snapshots** and launched as EC2 instances, and Lightsail has **VPC peering** with a single region's default VPC, which allows a hybrid period. But the export is a lift of the instance, not of the architecture - you get an EC2 instance and then have to build the VPC, security groups, ASG, load balancer and IAM around it, which is the work you avoided by choosing Lightsail. In practice, migrating off Lightsail is a rebuild with a data copy.

**The advice I would give**: use Lightsail deliberately for things that will stay small, and **do not use it for anything a business will depend on growing**, because the migration cost is paid at exactly the moment you are busiest. For a company already on AWS, the simplification it offers is not worth the ceiling.

*Hook: a Lightsail deployment, or a migration off it, and what the trigger was.*

### Q179. Outposts, Local Zones and Wavelength

All three extend AWS infrastructure beyond the standard region, and each exists for a different **physical constraint**:

**Outposts** - AWS-owned and operated racks (or 1U/2U servers) installed **in your own data centre**, running the same AWS APIs and services locally, managed from the region. **The constraint that makes it the only option: data must physically remain on your premises**, for regulatory, contractual or sovereignty reasons; or an application has a hard dependency on **single-digit-millisecond latency to on-premises systems** (a factory floor control system, a trading system co-located with an exchange, a hospital's imaging equipment). Also: an environment with genuinely unreliable connectivity to the region that must keep operating regardless.

**Local Zones** - AWS-operated infrastructure in **metropolitan areas** far from the parent region, offering a subset of services (EC2, EBS, some load balancing and databases) with a low-latency link back. **The constraint: you need single-digit-millisecond latency to end users in a specific city** that is far from the nearest region. The canonical uses are real-time gaming, live video production, remote virtual workstations for media and engineering, and AR/VR - workloads where 30 ms versus 8 ms is the difference between usable and not. Note that CloudFront already solves this for cacheable content, so **Local Zones are specifically for latency-sensitive *compute*, not delivery**.

**Wavelength** - AWS compute embedded **inside telecom carriers' 5G networks**, at the edge of the mobile network. **The constraint: ultra-low latency to mobile devices specifically**, without traffic traversing the internet - it stays within the carrier's network. Connected vehicles, industrial IoT over 5G, mobile AR, real-time video analytics from mobile cameras.

**The distinguishing question for each**: *Outposts* - must the data stay in my building? *Local Zones* - are my users in a city with no nearby region and do they need low-latency compute? *Wavelength* - are my users on mobile networks and is the last-mile latency the problem?

**The caveat worth stating**: all three carry a substantial cost and complexity premium, offer a **subset of services**, and create a hybrid operational model. Outposts in particular is a capacity commitment with a multi-year term and physical installation. They are the right answer to a genuine physical constraint and the wrong answer to a preference - and the most valuable thing to do when someone proposes one is to establish which constraint is actually in play, because frequently the answer is CloudFront, a closer region, or nothing.

*Hook: an edge or on-premises constraint you evaluated, and whether it justified one of these.*

### Q180. Image Builder and AMI hygiene

**EC2 Image Builder** is a managed pipeline for building, testing and distributing AMIs and container images. Its object model: **components** (reusable build and test steps), an **image recipe** (a base image plus an ordered list of components), an **infrastructure configuration** (how the build instance runs), a **distribution configuration** (which regions and accounts receive the image, and how it is tagged and shared), and a **pipeline** that ties them together on a schedule or a trigger.

**What a good AMI lifecycle looks like:**

1. **A base image built centrally, on a schedule** - monthly, or on a critical CVE. Starts from the latest AWS-provided AMI (referenced by SSM parameter so it always resolves to current), applies OS patches, installs the standard agents (SSM, CloudWatch, security tooling), applies CIS hardening, and configures logging.
2. **Automated testing in the pipeline.** Image Builder runs test components against the built image before it is distributed - verify the agents are running, the hardening is applied, the image boots, a validation script passes. **An untested AMI distributed to production is the mechanism behind the infinite launch loop in Q66.**
3. **Application images built on top of the base** in CI per release, so the application AMI inherits the current patched base rather than diverging.
4. **Distribution and sharing** to every region and account that needs it, with the AMI ID published to an **SSM Parameter Store parameter** (`/ami/base/al2023/latest`). Launch templates reference the parameter, not a hardcoded ID - which is what makes rollout a matter of updating one parameter.
5. **Rollout via instance refresh or blue/green** (Q76), progressively, with automatic rollback.
6. **Deprecation and cleanup**: mark old AMIs deprecated, and delete AMIs and their snapshots after a retention period. **Orphaned AMI snapshots are one of the most common silent EBS costs** in a mature estate, and Image Builder does not clean up by default.
7. **Compliance measurement**: a Config rule or a scheduled query reporting **what percentage of running instances are on a current AMI**, so "we patch monthly" is a number rather than an intention.

**Systems Manager's role alongside it**: **Patch Manager** for instances that are long-lived and cannot be replaced (Q199), **Inventory** to know what is actually running, and **State Manager** for drift. The two approaches are complementary - Image Builder for immutable replacement, SSM for the fleet you cannot replace - and a mature estate uses immutable replacement as the default and SSM as the exception.

*Hook: an AMI pipeline you built, the patch cadence, and how you measured compliance.*

### Q181. A six-person team wanting Kubernetes

**My response, and I would give it in this order:**

First, **ask why**, genuinely and without leading. The answers separate into two groups. Good reasons: a specific capability they need (a Kubernetes operator for a piece of software they run, a genuine multi-cloud requirement, a customer contractually requiring on-premises deployment of the same artifacts). Weak reasons: "it is the standard", "it will help us hire", "we will need it eventually", "our containers should be orchestrated properly". The weak reasons are the common ones, and they are usually a proxy for a real problem - deployments are painful, or the current platform is limiting - which is worth surfacing because the real problem may have a much cheaper solution.

Second, **state the cost honestly**. A production Kubernetes estate requires: cluster upgrades every few months on AWS's support timeline, add-on version compatibility management, networking and IP planning (Q174), RBAC and IAM mapping, ingress controllers, secrets management, policy enforcement, observability tooling, cost allocation, and enough expertise that someone can debug it at 3am. **That is comfortably a full-time role**, which for a six-person team is 17 percent of the engineering capacity, permanently, spent on infrastructure rather than product. And the failure mode is not that it does not work - it is that it works until the day it does not, and the person who set it up has left.

Third, **offer the alternative that addresses the underlying need**: **ECS on Fargate** gives them containers, rolling deployments with automatic rollback, service discovery, auto scaling and load balancer integration, with **no control plane, no node management and no upgrade treadmill**. For the overwhelming majority of what a six-person team needs, it is equivalent in capability and a fraction of the operational cost. **App Runner** if it is a single web service.

**The conditions under which I would agree:**

1. They have a **hard technical requirement** only Kubernetes meets - a specific operator, a vendor product shipped as Helm charts, or a genuine portability requirement with a named customer behind it.
2. The team **already has real Kubernetes operational experience** - not exposure, but having run it in production and been on call for it - and that is more than one person.
3. They are on a **trajectory** where the estate will be large enough within a year that the fixed cost amortizes, and the growth is funded.
4. They will adopt it with **managed everything** - EKS with Karpenter, managed add-ons, a managed ingress, and a deliberate decision not to run their own control-plane-adjacent components.

And I would say the thing that matters most: **this decision is reversible in one direction only.** Moving from ECS to EKS later is a manageable project; moving off Kubernetes once it is embedded is not. So the burden of proof sits with adoption, not with declining.

*Hook: a platform decision you argued against or for, and how the team's size and skills featured in it.*

### Q182. Platform for 25 Java services, team of 12, no platform engineers

**Clarify first**: are the services already containerized? What is the deployment frequency now and what does the team want it to be? Is there a compliance requirement affecting isolation or on-premises deployment? What is the traffic shape - steady, spiky, or mostly idle? Are any of the services stateful or long-running beyond a request? And is anyone on the team experienced with any of the candidate platforms?

**My answer: ECS on Fargate, with a shared CDK construct library, and a small number of services on Lambda where the shape fits.** The reasoning, with the team-shaped part front and centre:

**The team-shaped argument, which is the decisive one.** Twelve engineers and no platform engineers means **the platform must have close to zero operational surface**, because every hour spent on it is an hour not spent on 25 services. Fargate has no nodes to patch, no cluster to upgrade, no capacity to plan, and no control plane to understand. EKS would consume roughly one full-time engineer - 8 percent of the team - permanently, and there is nobody to be that person. That is not a marginal consideration; it is the whole decision. Any platform requiring dedicated ownership is disqualified by the constraint given.

**Why not the alternatives:**

- **EKS**: the operational cost above, plus the knowledge concentration risk. Twenty-five services is not large enough for the ecosystem benefits to outweigh it.
- **EC2 with ASGs**: AMI pipeline, patching, capacity, scaling configuration - more operational work than Fargate for less capability.
- **Elastic Beanstalk**: viable, and I would rule it out because 25 services means 25 Beanstalk environments with `.ebextensions` configuration that will diverge, and the abstraction leaks exactly when the team is least able to absorb it (Q177).
- **All Lambda**: right for some of the 25, wrong as a blanket answer - Java cold starts, the 15-minute limit, and connection pooling to a relational database (parent pack Q161) make it a poor fit for steady-state request-serving Java services.
- **App Runner**: genuinely tempting for its simplicity, and it constrains you to a single web service shape with less control over networking and scaling. Worth using for the simplest few if it fits.

**The design:**

```
CDK construct library (one repo, owned collectively)
  -> per service: ECR repo, ECS Fargate service, target group + ALB rule,
     log group with retention, alarms, IAM task role, autoscaling policy
Shared ALB with host/path rules   (not 25 ALBs - Q65)
ECS Service Connect for east-west traffic
Aurora PostgreSQL (shared cluster, schema per service, or a few clusters by domain)
Secrets Manager + Parameter Store, injected by the task definition
GitHub Actions -> OIDC -> build, push to ECR, update service; rolling deploy
     with circuit breaker and automatic rollback
CloudWatch Container Insights + structured JSON logs + X-Ray
```

**The single most important artefact is the shared construct library.** With no platform team, the way you avoid 25 divergent configurations is to make the paved road a dependency rather than a document: one `JavaService` construct that emits the service, its alarms, its log retention, its scaling policy and its IAM role, so a new service is 15 lines and every service is consistent by default. That is the thing I would build in week one, and it is what a platform team would otherwise provide.

**What I would revisit and when**: if the estate reaches 60+ services or the team grows past 30 with a dedicated platform function, EKS becomes defensible. If a specific service needs GPUs or very high steady utilization, move that one to EC2 or EKS rather than the whole estate. And if cost analysis at real utilization shows Fargate is materially more expensive than a packed EC2 fleet (Q169), that is a calculation to redo annually rather than a decision to make now.

*Hook: a platform decision constrained by team size rather than by technology, and how it held up.*

---

## 12. Migration and data transfer

### Q183. The 7 Rs

| R | What it means | Example |
| --- | --- | --- |
| **Retire** | Turn it off. Nobody uses it | The reporting server three people log into annually; typically 10-20 percent of a discovered estate |
| **Retain** | Leave it where it is, for now | A mainframe integration, or a system being replaced next year anyway |
| **Rehost** | Lift and shift, unchanged | 200 VMs moved with MGN onto EC2, same OS, same configuration |
| **Relocate** | Move the hypervisor-level container without changing the VMs | VMware workloads to VMware Cloud on AWS |
| **Repurchase** | Replace with a SaaS product | Self-hosted Jira or Confluence to Atlassian Cloud; a home-grown CRM to Salesforce |
| **Replatform** | Lift and *tinker* - keep the application, change a managed component | Self-managed PostgreSQL on a VM becomes RDS; Tomcat on a VM becomes a container on Fargate |
| **Refactor** | Rewrite for the cloud | A monolith decomposed into services; a batch job rewritten as Step Functions plus Lambda |

**The judgement, which is what is actually being tested**: cost and value rise steeply from left to right, and **most estates should be mostly rehost and replatform**. Refactoring everything is how a migration programme misses its date by a year; rehosting everything is how you arrive on AWS with the same problems and a higher bill.

**The sequencing I would argue for**: **retire aggressively first** (it is free value and shrinks everything downstream), **rehost or relocate the bulk** to meet the deadline, **replatform where the change is cheap and the payoff is immediate** (databases to RDS, load balancers to ALB, file shares to FSx - these remove operational work without touching application code), and **refactor only what the business case justifies afterwards**, once the workload is on AWS and you can measure it.

The sentence worth having ready: **"the migration deadline is met by rehosting; the value is realized by replatforming and refactoring afterwards"** - which is how you reconcile a data-centre exit date with the desire to modernize, and it is the conversation that most migration programmes get wrong in one direction or the other.

*Hook: a migration where you chose rehost over refactor (or the reverse), and whether the follow-up modernization actually happened.*

### Q184. Migration Hub and Application Discovery Service

**Application Discovery Service** collects data about the on-premises estate - server inventory, specifications, utilization, running processes, and **network connections between servers**. Two modes: an **agentless collector** (a VM appliance reading from vCenter, good for coverage and quick to deploy) and an **agent** installed per server (deeper data, including process-level and connection-level detail). **Migration Hub** aggregates this, lets you group servers into **applications**, and then tracks migration progress across the tools (MGN, DMS) in one place.

**What a real assessment phase produces:**

1. **A complete inventory**, which is almost never what the CMDB says. Discovery routinely finds 20-40 percent more servers than the organization believed it had, and a set nobody can identify an owner for.
2. **A dependency map** - which servers talk to which, on which ports, at what volume. **This is the single most valuable output**, because it determines what must move together (Q193). Without it, wave planning is guesswork and the first cutover breaks something nobody knew was connected.
3. **Right-sizing data.** Actual CPU, memory and disk utilization over weeks, which is what turns "we have 300 servers of this spec" into an accurate EC2 sizing and an accurate cost estimate. On-premises servers are habitually over-provisioned, and this is where a large part of the business case comes from.
4. **A retire list** - servers with no network traffic and no logins, which is free value (Q183).
5. **A defensible TCO model** built on measured utilization rather than nameplate specifications.

**Why teams skip it**: it takes 4-8 weeks of data collection before it yields anything, and it feels like delay when there is a deadline; installing agents across a production estate requires change approvals and cooperation from teams with no stake in the migration; and there is often a belief that the existing CMDB or a spreadsheet is sufficient.

**What skipping it costs**: sizing based on nameplate specs, so the AWS bill comes in far above the business case; wave plans that break because of undiscovered dependencies; servers migrated that should have been retired; and a discovery process that happens anyway, one outage at a time, during cutover. **The assessment is the cheapest phase of the programme and the one that most determines whether the rest of it works** - and arguing for it against schedule pressure is a thing worth being able to do.

*Hook: a discovery phase you ran or inherited, and what it found that nobody expected.*

### Q185. Application Migration Service

MGN is AWS's lift-and-shift service. It works by **continuous block-level replication**:

1. **An agent is installed on each source server** (physical, virtual, or in another cloud), with no reboot required.
2. The agent replicates the server's disks **continuously** to a **staging area** in your AWS account - low-cost EBS volumes attached to lightweight replication servers. The initial sync copies everything; after that it ships only changed blocks, so the ongoing bandwidth is modest.
3. The staging area stays **continuously current**, typically seconds behind the source. This is the important property: you can leave it replicating for weeks while you prepare.
4. **Test instances** can be launched at any time from a point-in-time snapshot of the staging volumes, **without disrupting replication or the source**. You launch, test, throw it away, and repeat as often as you like.
5. At cutover, MGN **converts the machine for AWS** - injecting drivers, adjusting the bootloader, network configuration and licensing activation - and launches the production instance.

**The cutover sequence**: verify replication lag is near zero → stop the application on the source (this is the outage window) → wait for the final blocks to replicate → launch the cutover instance → validate → repoint DNS or the load balancer → resume traffic. **The window is minutes**, because everything except the last few seconds of data was already there.

**What matters operationally:**

- **Test, repeatedly, before cutover.** The ability to launch a test instance without disrupting anything is MGN's best feature and the most under-used. A workload should be launch-tested several times before its cutover.
- **The launch template** (instance type, subnet, security groups, IAM role) is configured per source server, and this is where right-sizing from the discovery data (Q184) is applied - migrating a 32-core on-premises server that runs at 5 percent to a 32-core EC2 instance is how a migration blows its budget.
- **Rollback** is: keep the source server intact and switch back. MGN does not replicate *back*, so any data written on AWS after cutover is lost on rollback - which is why the source must be kept and why the validation window matters.
- **Post-launch actions** can run automation on the migrated instance - installing the SSM agent, joining a domain, applying configuration.

*Hook: an MGN migration, how many test launches you did, and what the cutover window actually was.*

### Q186. DMS, CDC and SCT

**DMS** moves data between databases. Its two phases:

- **Full load**: bulk copy of existing data, table by table, in parallel.
- **CDC (change data capture)**: reads the source's transaction log (binlog, WAL, redo log) and applies ongoing changes to the target continuously. This is what enables a near-zero-downtime cutover: run full load plus CDC for weeks, then cut over when lag is zero.

**Homogeneous** (Oracle to Oracle, PostgreSQL to PostgreSQL) is largely mechanical - the schema transfers as-is and DMS is a data-movement tool. **Heterogeneous** (Oracle to PostgreSQL, SQL Server to Aurora) requires the schema and code to be converted first, and that is where the work is.

**The Schema Conversion Tool** (now largely integrated into DMS as DMS Schema Conversion) handles that: it connects to the source, converts tables, indexes, views, stored procedures, functions and triggers to the target dialect, and produces an **assessment report** classifying every object as automatically converted, or requiring manual work with an estimated effort. **The assessment report is the artefact that should gate the migration decision** (Q149) - it is the difference between "we will move to PostgreSQL" as an aspiration and as a plan with a number attached.

**What DMS does and does not do**, which is the part people get wrong:

- **DMS migrates data, not schema.** It will create rudimentary target tables if they do not exist, but with inferred types and **no indexes, no constraints, no foreign keys, no sequences, no triggers**. The schema must be created properly first, by SCT or by hand.
- It does **not** convert application code, and the application's SQL is usually where the remaining work lives.
- **CDC has requirements on the source** - supplemental logging on Oracle, `binlog_format=ROW` on MySQL, logical replication and a replication slot on PostgreSQL. Enabling these often requires a source restart, which needs planning.
- **Some data types and LOBs are handled specially** - LOB mode settings (limited, full, inline) have real performance and correctness consequences, and getting them wrong truncates data silently (Q187).

**The operational shape**: a replication instance sized for the workload, tasks per group of tables, **CloudWatch monitoring of `CDCLatencySource` and `CDCLatencyTarget`**, and **DMS data validation** enabled so row-level comparison runs continuously rather than being a manual check at the end.

*Hook: a DMS migration you ran, homogeneous or heterogeneous, and where the effort actually went.*

### Q187. DMS reports success and the data is wrong

Four causes, each with the check that would have caught it:

1. **LOB handling truncated data.** DMS's default **limited LOB mode** truncates any LOB larger than the configured `LobMaxSize` - **silently**, with no error and no warning in the task log. A `CLOB` column with a 40 KB document is cut to 32 KB and the task reports success. *Caught by*: enabling **full LOB mode** (slower) or setting `LobMaxSize` above the true maximum, and by **validating maximum column lengths** between source and target rather than only row counts.
2. **Data type mapping differences.** Heterogeneous migrations convert types, and the conversions are not always lossless: Oracle `NUMBER` without precision to PostgreSQL, `DATE` semantics differing between engines (Oracle `DATE` includes a time component, others do not), timezone handling, `CHAR` padding, unsigned integers, and floating-point precision. The data arrives, it is the wrong value. *Caught by*: reviewing the SCT type mapping report and **checksum or aggregate comparison** on numeric and date columns, not row counts.
3. **CDC missed or misapplied changes.** Transactions in flight when the full load snapshot was taken; a source without the required supplemental logging so updates arrive without full row context; DDL changes during migration that CDC does not replicate; or a task restarted from the wrong position. Often manifests as a small number of rows differing. *Caught by*: **DMS data validation** running continuously, and monitoring for validation failures rather than only task state.
4. **Constraints, sequences and triggers not migrated.** DMS moves rows. If sequences were not reset to the correct next value, the first insert on the target collides or starts from 1. If triggers exist on the target during load, they fire and **generate duplicate derived data**. If foreign keys were disabled for the load and never re-enabled, referential integrity was never enforced. *Caught by*: a **post-migration checklist** verifying sequences, constraints, indexes and triggers, and comparing object counts between source and target.

**The meta-answer, and the one that matters most**: **"DMS reports success" means the task ran, not that the data is correct.** Task state is a liveness signal. Correctness requires **DMS data validation enabled from the start**, plus **application-level reconciliation** - row counts per table, aggregate sums on key numeric columns, checksums on samples, and business-level assertions ("total outstanding balance matches"). Those run continuously through the CDC period, not once at the end, so a divergence is caught days before cutover rather than discovered by a customer.

*Hook: a data migration discrepancy you found, how you found it, and whether validation was running.*

### Q188. Snowball and the arithmetic

**The calculation is the answer**, and it should be done out loud:

```
transfer time = data volume / usable bandwidth
usable bandwidth ~= 50-70 percent of the link's nominal rate
```

At **1 Gbps** with 60 percent utilization you get roughly **6.5 TB per day**. At **10 Gbps**, about **65 TB per day**. At **100 Mbps**, about **650 GB per day**.

So:

| Data | 100 Mbps | 1 Gbps | 10 Gbps |
| --- | --- | --- | --- |
| 10 TB | 15 days | ~1.5 days | 4 hours |
| 100 TB | 5 months | 15 days | ~1.5 days |
| 1 PB | 4 years | 5 months | 15 days |

**A Snowball Edge holds ~80 TB usable and takes about a week end to end** - order, ship, load, ship back, ingest. Snowmobile (a truck) moves up to 100 PB.

**The decision rule**: if the network transfer takes materially longer than a week per 80 TB, ship disks. Concretely, **below ~10 TB use the network; 10-100 TB do the arithmetic against your actual bandwidth; above 100 TB on anything less than 10 Gbps, ship.**

**Three factors that are usually decisive and are not in the arithmetic:**

1. **You cannot use the whole link.** The WAN is also carrying production traffic, so you get a fraction of it, and saturating the link during business hours is not acceptable. This alone often halves the effective bandwidth.
2. **The data keeps changing.** A five-month transfer of a live dataset means the source has changed substantially by the time it completes, so you need CDC or a delta pass anyway - and at some point the delta grows faster than you can transfer it, which makes network transfer impossible regardless of patience.
3. **Cost.** Transferring 500 TB over Direct Connect has a data transfer cost; a Snowball has a flat device and shipping fee. At volume the device is cheaper as well as faster.

**The hybrid pattern worth naming**: **Snowball for the bulk historical data, network with DataSync or DMS CDC for the delta and the ongoing sync.** That is how large migrations are actually done - ship the 500 TB baseline, then keep the last few days current over the wire until cutover.

*Hook: a bulk data transfer where you did this arithmetic, and which way it came out.*

### Q189. DataSync versus the alternatives

| Tool | What it is | Choose when |
| --- | --- | --- |
| **DataSync** | A managed **transfer service** with an agent (on-premises) or agentless (AWS to AWS). Parallel, multi-threaded, incremental, with **checksum validation**, bandwidth throttling, scheduling and filtering | **Bulk and recurring transfers** between NFS, SMB, HDFS, object storage, S3, EFS and FSx |
| **S3 CLI / SDK** | Scripts you write and run | Small, one-off transfers; when you need custom logic; when the source is already S3-API-native |
| **Storage Gateway** | An **ongoing access** protocol endpoint backed by AWS storage | On-premises applications need continuous file or block access to cloud-backed storage (Q41) |
| **Transfer Family** | Managed **SFTP/FTPS/FTP/AS2 endpoints** in front of S3 or EFS | **External parties** push or pull files using standard protocols you do not control |

**What decides between them:**

1. **Is this a transfer or an access pattern?** A transfer has a beginning and an end (DataSync, CLI); an access pattern is continuous (Storage Gateway, Transfer Family). This single question resolves most confusion.
2. **Who initiates?** If **you** initiate, DataSync. If a **third party** initiates using a protocol they already use, Transfer Family.
3. **Scale and validation.** DataSync's advantages over a script are real and worth listing: **10x or more faster** through parallelism and a purpose-built protocol, **automatic checksum verification** of every file transferred, **incremental sync** that compares metadata rather than re-copying, resumption after failure, built-in scheduling, filtering and bandwidth throttling, and CloudWatch metrics. A `aws s3 sync` script gives you none of that reliably, and the validation is the part that matters for a migration you must be able to defend.
4. **Source and destination types.** DataSync handles NFS, SMB and HDFS sources natively - the CLI does not.

**When the CLI is genuinely fine**: a few gigabytes, a one-off, from a machine that already has credentials, where you will verify the result manually.

**The combination in a migration** (Q42): **DataSync for the bulk initial transfer and recurring sync; Storage Gateway for applications that need ongoing access during the transition; Transfer Family for external partners; Snowball if the arithmetic says so** (Q188). These are not competitors - a real migration uses three of the four.

*Hook: a data transfer where you chose DataSync over a script, and what the validation or speed difference was.*

### Q190. AWS Transfer Family

A **managed SFTP, FTPS, FTP and AS2 endpoint** in front of S3 or EFS. Users connect with a standard client using SSH keys or passwords; files land as S3 objects. It handles the protocol, the endpoint availability, the user directory mapping, and integration with IAM for per-user access scoping. Identity can be **service-managed** (keys stored in the service), or delegated to **Active Directory** or a **custom identity provider via Lambda or API Gateway** - the last being how you integrate an existing customer database.

**When it is the right answer**: you have **external parties - customers, partners, banks, suppliers - who exchange files over SFTP** and will not change. This is enormously common in finance, insurance, healthcare, retail supply chains and payroll, where SFTP is the integration contract and has been for twenty years. Transfer Family lets you retire the SFTP servers you have been patching for a decade, put the files directly into S3 where an event-driven pipeline can process them, and get IAM-scoped per-partner access with CloudWatch logging and CloudTrail auditing.

It is **not** the answer for your own applications moving data - use the S3 API - or for bulk migration (use DataSync). Choosing it because "we need to get files into S3" without an external protocol constraint is over-engineering.

**What is surprising about the cost model**: it is billed **per protocol per hour that the endpoint is enabled** - roughly **$0.30/hour, so about $216 per month per protocol, whether or not a single file is transferred** - plus a per-GB charge for data uploaded and downloaded. Enabling SFTP, FTPS and FTP on one server is three times the hourly charge. **The fixed cost is the surprise**: an endpoint provisioned for a partner who sends one file a week costs the same as one handling terabytes, and a team that spins up separate endpoints per partner or per environment discovers a four-figure monthly bill for something they think of as "just SFTP".

The mitigations: **consolidate onto one endpoint** with per-user home directory mappings and IAM scoping rather than an endpoint per partner; enable only the protocols actually required; and use the newer **public endpoint type** rather than a VPC endpoint with an Elastic IP unless the network isolation is needed, since that adds cost. And for a genuinely low-volume, low-partner-count case, honestly compare it against running an SFTP container on Fargate - which is more work and may be an order of magnitude cheaper.

*Hook: an SFTP integration you migrated to Transfer Family, and whether the fixed cost was a factor.*

### Q191. Accelerating a slow upload from Mumbai to `us-east-1`

**First, diagnose which of the three problems it is**, because they have different fixes:

- **Latency-bound (long fat network)**: a single TCP stream over a ~200 ms round trip cannot fill the pipe, because throughput is bounded by `window size / RTT`. The link is fast, one stream is slow.
- **Bandwidth-bound**: the link itself is saturated.
- **Loss-bound**: packet loss on the international path collapses TCP throughput, and this is common on public transit between India and the US.

**What each option does:**

1. **Multipart upload with parallelism** - the first thing to try, and frequently sufficient. Splitting the object and uploading parts **concurrently** works around the single-stream window limit entirely. Tuning `max_concurrent_requests` and `multipart_chunksize` in the AWS CLI, or using `s5cmd`, commonly gives a **5-10x improvement for free**. **Anyone proposing Transfer Acceleration before doing this is skipping the cheap fix.**
2. **S3 Transfer Acceleration** - the upload goes to the **nearest CloudFront edge** (Mumbai) and then travels the **AWS backbone** to the bucket in `us-east-1`. This addresses the loss and jitter of public transit, which is usually the real problem on this route. Charged **per GB at a premium**, and AWS provides a speed comparison tool that tells you whether it actually helps for your route - **use it, because it does not always**, and paying for acceleration that delivers nothing is a real outcome.
3. **CloudFront upload** (a distribution with PUT/POST allowed to an S3 origin) - similar mechanism to Transfer Acceleration, entering the AWS network at the edge, with more control and different pricing. Worth comparing.

**Which actually helps here**: for **Mumbai to `us-east-1` specifically**, the distance means both the latency and the public-transit quality are in play, so the answer is usually **multipart parallelism first (large win, free), then Transfer Acceleration if the measurement shows the backbone helps**. Both, together, is the realistic answer.

**But the question I would ask first**: **why is the bucket in `us-east-1`?** If the data is produced in Mumbai and consumed in Mumbai, the bucket should be in `ap-south-1` - and the transfer problem disappears entirely. If it must be centralized, consider **uploading to `ap-south-1` and using S3 Cross-Region Replication** to move it, which is asynchronous, managed, and takes the transfer off the user's critical path. **Fixing the topology beats accelerating a bad topology**, and that reframing is the answer that distinguishes a senior response.

*Hook: an upload performance problem, whether parallelism or acceleration fixed it, and whether you questioned the destination.*

### Q192. Cutover planning

**What must exist before you flip**, as a checklist - and the value is in insisting on all of it:

1. **A tested rollback path, built before the forward step.** For a database, that means **reverse replication configured and verified in advance**, so the old system continues receiving changes and fail-back is a connection-string change rather than a restore. This is the single most important item and the one most often skipped, because it is work for an outcome you hope not to need (parent pack's migration scenario).
2. **A rollback decision point with a named owner and a deadline.** "If we are not serving traffic successfully by 04:00, we roll back" - decided in advance, in writing, because at 03:45 in the middle of a cutover nobody is capable of making that judgement cleanly.
3. **DNS TTLs already lowered**, at least twice the previous TTL in advance (Q96), and verified from external resolvers.
4. **Replication lag at zero and monitored**, with a dashboard showing it in real time during the cutover.
5. **A validated dress rehearsal** - the entire cutover performed in a lower environment, timed, with the runbook followed literally by the person who will run it on the night. The rehearsal is what turns a 40-step runbook into an accurate one.
6. **A change freeze** on both sides, starting days before, so nothing is deployed into the middle of it.
7. **Data reconciliation queries** ready to run, with expected results known, so "is the data correct" is answered in minutes rather than debated (Q187).
8. **The old system kept intact and running** - not decommissioned, not repurposed - for a defined period (I would say a month past cutover, through at least one month-end).
9. **Comms**: who is on the call, who decides, who tells the business, and what the customer-facing message is if it goes badly.
10. **A validation checklist** covering the business functions, not just the technical health - someone logging in and completing a real transaction.

**The freeze window** deserves its own mention: it must cover **both** the source and the target, including infrastructure changes, and it should extend past the cutover until the system is confirmed stable. Cutovers are broken by an unrelated deploy more often than by the cutover itself.

**And the sequence at the moment of cutover**: quiesce writes → drain replication to zero → validate → repoint → smoke test → open to traffic → monitor → declare success or roll back at the decision point. Writing it down at that granularity, with a time estimate per step, is what makes the four-hour window measurable rather than hopeful.

*Hook: a cutover you ran, whether you used the rollback path, and what the rehearsal changed.*

### Q193. Migration waves and dependency mapping

**Waves** are groups of servers or applications migrated together in one cutover event. **The dependency map from discovery (Q184) determines their composition**, because anything that communicates with low latency or high volume must move together or be prepared to communicate across the WAN.

**How I would sequence 300 servers:**

1. **Retire first.** Discovery will identify servers with no traffic and no logins. Removing 15 percent of the estate before planning anything is the cheapest win available.
2. **Group by application, not by server.** A wave should be a **complete application and its tightly-coupled dependencies** - the web tier, the app tier, its database, its cache, its batch jobs. Splitting an application across waves means it runs across the WAN during the gap, which is where the latency surprises live.
3. **Order by risk and learning, ascending.** **Wave 1 is a low-risk, low-dependency, non-critical application with an engaged team** - a proving ground for the tooling, the network, the runbook and the organization's ability to execute a cutover at all. It should be something whose failure is embarrassing rather than damaging. Then progressively more critical applications as the process matures.
4. **Then order by dependency direction**: applications that others depend on tend to move earlier (or their dependents must tolerate the WAN hop), and shared services - directory, DNS, monitoring, file shares, the shared database - are either moved first or explicitly kept on-premises with connectivity for the duration.
5. **Keep waves small enough to execute and validate in a single window** - typically 5-20 servers, or one application. Large waves fail because there is no time to validate before the window closes.
6. **Leave the hardest for last but not too last** - the mainframe integration or the licence-encumbered database should not be wave 1, and it also should not be discovered in the final month.

**What makes a wave fail:**

- **An undiscovered dependency.** Something reaches the migrated application over a port nobody documented, or the application calls a hardcoded IP address of a server left behind. **This is the most common cause**, and it is a direct consequence of a weak discovery phase.
- **Latency across the split.** An application chatting with a database left on-premises across a 30 ms link, when it was designed for 0.5 ms and makes 200 sequential queries per page. The application "works" and is unusably slow - which is the failure mode that most damages confidence in the programme.
- **Shared infrastructure** nobody assigned to a wave: a licence server, an NTP source, a certificate authority, a legacy authentication system.
- **No rollback** for the wave, so a problem becomes a crisis rather than a retreat.
- **Insufficient validation time** in the window, so problems are discovered by users on Monday.

**The practice that catches most of it**: for each wave, **run the application on AWS against the on-premises dependencies first** (the stage-1 parallel run from the parent pack's migration scenario), which surfaces latency and connectivity problems while rollback is a DNS weight rather than a restore.

*Hook: a migration wave that failed or nearly failed, and which of these causes it was.*

### Q194. The TCO comparison that says AWS is more expensive

Five things it probably left out, **on both sides** - and the "both sides" framing is the point, because these comparisons are usually biased in both directions at once.

**Missing from the on-premises side (making it look cheaper than it is):**

1. **The full cost of the facility and the hardware refresh cycle.** Power, cooling, floor space, physical security, and the **capital refresh every 3-5 years** amortized properly. Many comparisons count only the depreciated book value of servers already owned, which prices the past rather than the future.
2. **Labour.** The people who rack, patch, monitor, back up, and are on call for hardware. Often several full-time roles that are not attributed to the workload because they are "already there".
3. **Software licensing that changes with the platform** - hypervisor licences, backup software licensed per socket, monitoring agents, and the enterprise agreements that expire during the period.
4. **Over-provisioning.** On-premises capacity is bought for peak plus a safety margin plus growth headroom, so utilization is routinely 10-20 percent. **The comparison should be against actual utilization, not nameplate** (Q184) - and this is frequently the largest single distortion.
5. **The cost of not being elastic** - the projects delayed waiting for hardware, the capacity bought for a peak that never came, and the DR capability that does not exist because a second data centre was unaffordable. Hard to quantify, real, and worth naming even if you cannot put a number on it.

**Missing or wrong on the AWS side (making it look more expensive than it will be):**

1. **Commitments.** Comparing on-demand list prices against owned hardware is not a fair comparison. **Savings Plans and Reserved Instances at 1 or 3 years take 40-70 percent off**, and a migrated steady-state estate is exactly the profile they exist for.
2. **Right-sizing.** The comparison usually assumes a 1:1 mapping of on-premises specs to instance sizes. With real utilization data, the AWS estate is materially smaller (Q184).
3. **Non-production shutdown.** Development and test running only during business hours is a 60-70 percent saving on that portion, which is typically 30-40 percent of the estate. Impossible on-premises.
4. **Replatforming savings**, deliberately excluded from a lift-and-shift comparison but real over the period - managed databases removing DBA time, S3 replacing a storage array, serverless removing servers entirely.
5. **Data transfer and support tier**, which are usually *under*-estimated - so this one cuts the other way, and mentioning it is what makes the answer credible rather than a sales pitch.

**How I would handle the conversation**: I would not argue that the number is wrong. I would **ask what assumptions it uses for utilization, commitment and lifecycle**, rebuild it with those explicit, and present a range with the assumptions visible. And I would say plainly that **for a pure lift-and-shift of an over-provisioned, fully-depreciated estate, AWS genuinely can be more expensive** - the business case for migration in that situation is agility, DR, elasticity and the exit from a facility, not raw cost. **Pretending otherwise is how programmes lose credibility in year two**, and being the person who says it is worth more than winning the argument.

*Hook: a TCO comparison you built or challenged, and which assumption changed the answer.*

### Q195. VMware Cloud on AWS and hybrid holding patterns

VMware Cloud on AWS (and the equivalent hybrid offerings) runs the **VMware stack - vSphere, vSAN, NSX - on dedicated bare-metal EC2 hosts**, managed as a service. Your VMs move with **vMotion or HCX, without conversion**, keeping their IP addresses, their tooling and their operational model, while gaining low-latency access to native AWS services from the same VPC.

**When it is a legitimate strategy:**

1. **A hard deadline that a conversion-based migration cannot meet.** A data-centre lease expiring in nine months with 300 VMs and no migration experience (Q196) is the archetype: relocating VMs wholesale is measured in weeks, where rehosting each one with MGN plus testing is measured in months. **It converts a deadline problem into a modernization problem you can solve later**, and that is a real and defensible engineering trade.
2. **Heavy dependence on VMware-specific capability** - NSX network policies, vSAN features, a VMware-integrated backup and DR product, or third-party appliances that only ship as OVAs.
3. **DR to the cloud** without rebuilding the DR runbook - VMware SRM continues to work.
4. **Bursting or temporary capacity** without buying hardware.
5. **An operations team whose entire skill set is VMware**, where the retraining timeline is longer than the migration timeline. This is an organizational constraint and a legitimate one.

**When it is an expensive delay** - and this is the more common case:

- **It is expensive.** Dedicated bare-metal hosts with a minimum cluster size, plus VMware licensing, means the running cost is frequently **higher than the equivalent native AWS estate and sometimes higher than the on-premises estate**. It is not a cost-reduction play and should never be sold as one.
- **You get none of the operational benefits of cloud-native.** You still patch guest operating systems, still manage VMs, still size capacity. The managed-service savings that justify migration do not materialize.
- **It becomes permanent.** The plan is always "relocate now, modernize later". Without a **funded, scheduled modernization programme with named owners**, later never arrives, and the organization is paying a premium indefinitely for the privilege of not having changed anything.

**How I would frame it**: legitimate as a **bridge with a funded exit plan and a date**, where the date is in the same budget cycle and someone's objectives depend on it. Without that, it is a way of spending more money to postpone a decision - and I would say so explicitly when it is proposed, because the honest conversation is easier before the contract than after.

*Hook: a hybrid holding pattern you used or declined, and whether the modernization actually followed.*

### Q196. Nine months, 300 VMs, a mainframe, no experience

**Clarify first**: is the lease genuinely immovable, or is a short extension purchasable - because a three-month extension is often far cheaper than the risk it removes, and asking is free. What does the mainframe actually do, and who owns it? What is the budget and can we hire or bring in a partner? What is the tolerance for downtime per application? And is there an existing VMware estate, because that changes the fastest path substantially.

**The shape of the plan:**

**Months 1-2: foundation and discovery, in parallel.**

- **Discovery from day one** (Q184) - agents deployed, dependency mapping running, because it takes weeks to produce useful data and everything else depends on it. This is the critical path and starting it late is the most common fatal mistake.
- **Landing zone**: accounts, network, Direct Connect **ordered immediately** (Q120 - the lead time is months and this is the second critical path), with VPN for immediate connectivity.
- **Bring in help.** With no migration experience in the team and nine months, an AWS partner with a migration practice is not optional. I would say this early and plainly rather than discovering it in month five.
- **Decide the strategy per workload** from the 7 Rs (Q183), with a strong bias to **retire and rehost**.

**Month 2: the strategic decision, and it is the important one.**

If there is a VMware estate, **seriously evaluate VMware Cloud on AWS or a relocate-based approach for the bulk** (Q195). Relocating 300 VMs is achievable in nine months with a modest team; rehosting and testing 300 VMs individually with MGN is not, unless the applications are simple and the team is large. **I would make this call explicitly, with the cost premium quantified and a funded modernization programme attached with dates.** The alternative - attempting per-VM rehosting and running out of time in month seven - is the failure mode I am designing against.

If there is no VMware estate, **MGN-based rehosting in waves** (Q185, Q193) with aggressive retirement and a partner providing scale.

**Months 3-8: wave execution.**

- **Wave 1 in month 3**: a low-risk application, to prove the tooling, the network, the runbook and the organization (Q193).
- Then waves every 1-2 weeks, increasing in size and criticality as the process matures. **Front-load the schedule** - aim to complete migration by month 7, leaving two months of buffer, because something will slip and a plan with no buffer against a lease expiry is not a plan.
- **Continuous discovery validation** - each wave's dependency assumptions verified before its cutover.

**The mainframe: address it in month 1 and probably retain it.** Mainframe migration is a multi-year programme (refactor with Blu Age or Micro Focus, replatform, or replace), and it will not happen in nine months. **The realistic answer is to keep the mainframe where it is** - in a colocation facility if the lease is the constraint, or with the vendor - and **connect to it over Direct Connect**, migrating the applications around it. That is the pragmatic call, and making it early prevents it from consuming attention that the other 300 VMs need. **AWS Mainframe Modernization** is the eventual path, as a separate funded programme.

**Months 8-9: buffer, stabilization, decommission.** Run through a month-end on AWS before decommissioning anything. Keep the on-premises environment until the lease genuinely ends.

**What I would insist on**: the discovery phase not being cut; a partner engaged; the Direct Connect ordered in week one; **buffer in the schedule**; and the modernization programme funded *now* if we take a relocate-based path, because otherwise the temporary becomes permanent (Q195).

**What I would tell the sponsor**: the deadline is achievable with a rehost/relocate strategy and a partner; it is not achievable if we try to modernize during the migration; and the mainframe is out of scope for this programme. Being clear about all three in month one is what makes the rest possible.

*Hook: a deadline-driven migration you ran, what you deliberately did not modernize, and whether the follow-up happened.*

---

## 13. Operations, governance and cost tooling

### Q197. The Systems Manager capabilities worth knowing

| Capability | What it replaces |
| --- | --- |
| **Session Manager** | Bastion hosts, SSH keys, inbound port 22 |
| **Patch Manager** | A patching cron job, or manual patching, or WSUS |
| **Run Command** | SSH-in-a-loop scripts, Ansible ad-hoc commands |
| **State Manager** | Configuration drift management, a Puppet/Chef agent |
| **Automation** | Runbooks in a wiki that a human follows at 3am |
| **Parameter Store** | Configuration files, environment variables baked into AMIs |
| **Inventory** | A CMDB that is out of date |
| **Compliance** | A spreadsheet of patch status |
| **Fleet Manager** | RDP jump boxes and console access |
| **Maintenance Windows** | Ad-hoc change scheduling |
| **Application Manager / OpsCenter** | Scattered operational context and ticket queues |

**The mechanism underneath all of it** is worth stating because it is what makes the value proposition work: the **SSM Agent** (pre-installed on current AWS AMIs) makes an **outbound** connection to the Systems Manager endpoints. Nothing connects inbound to the instance. That single design choice is what allows managing instances in private subnets with no bastion, no inbound rules, and no SSH keys - and it is why Systems Manager is a **security** improvement as much as an operational one.

**The prerequisites people miss**: the instance needs the agent running, an **instance profile with `AmazonSSMManagedInstanceCore`**, and **network access to the SSM endpoints** - which for a private subnet means either a NAT gateway or **three interface endpoints** (`ssm`, `ssmmessages`, `ec2messages`). "Session Manager does not work" is almost always one of those three.

The ones I would prioritize in a new estate: **Session Manager** (delete the bastions), **Patch Manager** with a baseline and a compliance report, **Parameter Store** for configuration, and **Automation runbooks** for the operations that currently live in someone's shell history.

*Hook: a Systems Manager capability you rolled out, and what it let you decommission.*

### Q198. Session Manager versus bastions and SSH keys

**Session Manager** provides a browser or CLI shell to an instance through the SSM agent's **outbound** connection, authenticated and authorized by **IAM**, with the whole session **logged to CloudWatch Logs or S3**.

**What it changes about network design** - this is the substance:

1. **No inbound ports at all.** Instances need **no port 22 open, from anywhere, including from a bastion.** Security groups for managed instances can have an empty inbound ruleset, which is a genuinely different posture.
2. **No bastion hosts.** The bastion - an internet-facing instance that must be patched, monitored, hardened, made highly available, and which is a standing attack target - simply disappears. So do the security groups, the Elastic IPs and the operational burden around it.
3. **No SSH key management.** No key distribution, no rotation, no offboarding problem, no keys on laptops, no shared `.pem` file in a password manager. **Access is revoked by changing an IAM policy**, immediately and centrally.
4. **Private subnets become fully manageable**, which removes the pressure to place instances in public subnets "so we can reach them".
5. **Access is auditable per identity.** CloudTrail records who started a session against which instance; the session log records **every command typed and its output**. With SSH through a bastion, you know someone connected to the bastion - what they did afterwards is not attributable.

**The controls it enables** that were not previously practical: **IAM policies scoped by instance tag** (this team may connect to instances tagged `team=payments` only), **session preferences enforcing logging and encryption**, **`ssm:StartSession` requiring MFA** via a policy condition, port forwarding for database access without exposing the database, and **breaking-glass access that is loggable and revocable**.

**The honest caveats**: it needs the agent, the instance profile and endpoint connectivity (Q197); the shell experience is slightly different from SSH; and **file transfer is awkward** (SCP works via a proxy configuration, but it is not seamless). Neither is a reason to keep bastions.

The position I would take: **an internet-facing bastion host in 2026 is a finding**, and Session Manager plus VPC endpoints is the replacement, with the added benefit that the audit trail satisfies a control most organizations were failing anyway.

*Hook: a bastion estate you decommissioned, and what the security or audit driver was.*

### Q199. Patch Manager

The object model: a **patch baseline** defines which patches are approved (by classification, severity, product, and an **auto-approval delay** - "approve critical security patches 7 days after release"), plus explicit approve and reject lists. **Patch groups** are a tag (`Patch Group`) on instances that associates them with a baseline. A **maintenance window** defines when patching runs, against which targets, with what concurrency and error thresholds.

**How you patch a fleet without an outage:**

1. **Rings, staged over time.** A `dev` patch group with a 0-day auto-approval delay, `staging` at 3 days, `production` at 7-14 days. Patches soak in lower environments before reaching production, and a bad patch is caught by someone whose downtime does not matter.
2. **Concurrency and error thresholds in the maintenance window.** `MaxConcurrency: 25%` and `MaxErrors: 1` means a quarter of the fleet patches at a time and the whole operation **stops on the first failure** rather than proceeding to break everything. This is the single most important safety setting.
3. **Use the load balancer.** For instances behind a target group, the maintenance window task should **deregister the instance, patch, verify, re-register** - which is what turns "patching with a reboot" into a rolling operation with no user impact. This is done with an Automation runbook rather than a plain Run Command, and it is the difference between a real patching process and a hopeful one.
4. **`Scan` before `Install`.** Run scan-only against the fleet first to see what *would* be applied and how many instances are affected, so the change is known rather than discovered.
5. **Reboot control**: `RebootOption: NoReboot` for patches that do not need one, with reboots batched into a separate window.

**The alternative that is often better**: for anything in an Auto Scaling group, **do not patch in place at all - replace the AMI** (Q180) and roll the fleet with an instance refresh or blue/green (Q76). Immutable replacement is more reliable than in-place patching, produces a known-good artifact, and is testable before deployment. **Patch Manager is for the instances you cannot replace** - long-lived stateful servers, legacy applications, on-premises servers registered as managed instances - and framing it that way is the mature position.

**And measure it**: Patch Manager's **compliance reporting** gives you the percentage of the fleet compliant with its baseline. That number, reported monthly, is what turns patching from an activity into a control.

*Hook: a patching process you built, and whether it was in-place or AMI replacement.*

### Q200. Run Command, State Manager and Automation

- **Run Command** executes a document (a script or a predefined action) **once, now**, against a set of targets selected by instance ID, tag or resource group. **Imperative and ad-hoc.**
- **State Manager** **continuously enforces a desired state** by applying an association on a schedule - every 30 minutes, daily - and reporting compliance. **Declarative and recurring.**
- **Automation** runs a **multi-step workflow** that can span AWS services, not just instances - with branching, approvals, error handling and inputs. **Orchestration.**

**A real use for each:**

**Run Command**: an incident. A vulnerability is announced, and you need to know which of 400 instances has the affected package version - one command, targeted by tag, results aggregated, answer in two minutes. Or: restart a service across a fleet, collect a diagnostic bundle, rotate a credential file. The defining characteristic is that it is a **one-off action taken deliberately by a human**, and it replaces SSH-in-a-loop with something audited and IAM-controlled.

**State Manager**: ensuring the CloudWatch agent is installed and running with the correct configuration on every instance, forever. An instance that drifts - because someone stopped the agent, or an AMI was built without it - is corrected on the next association run and reported as non-compliant in the meantime. Also: enforcing an ntp configuration, keeping the SSM agent updated, applying a security baseline. The defining characteristic is **drift correction without human involvement**.

**Automation**: an operational runbook. "Patch an instance behind a load balancer" is a workflow - deregister from the target group, wait for connections to drain, snapshot the volume, apply patches, reboot, verify the health check, re-register, and roll back if verification fails. That spans EC2, ELB and SSM, has branching and error handling, and is exactly what a human follows from a wiki page at 3am and gets wrong. **Automation turns the wiki page into an executable, testable, auditable artifact** - and can be triggered by an EventBridge rule so it runs without a human at all (Q211).

**The progression worth naming**: teams start with Run Command because it is the closest thing to what they did before, and the value comes from moving upward - **the operations you run repeatedly should become State Manager associations or Automation runbooks**, and the measure of an operations practice is what fraction of its actions are still ad-hoc.

*Hook: a manual runbook you converted into an Automation document, and what it prevented.*

### Q201. Parameter Store versus Secrets Manager

| | Parameter Store | Secrets Manager |
| --- | --- | --- |
| **Cost** | **Standard parameters free**; advanced ~$0.05/parameter/month; higher-throughput tier charged per API call | **~$0.40 per secret per month**, plus ~$0.05 per 10,000 API calls |
| **Rotation** | **None built in** - you build it with Lambda and EventBridge | **Built in**, with managed rotation templates for RDS, Redshift, DocumentDB, and custom Lambda rotation |
| **Size** | 4 KB standard, 8 KB advanced | 64 KB |
| **Throughput** | 40 TPS default (higher throughput tier available, charged) | Higher, and charged per call |
| **Cross-account / replication** | Limited | **Resource policies and multi-region replication** built in |
| **Versioning** | Yes, with labels | Yes, with staging labels (`AWSCURRENT`, `AWSPENDING`) |
| **Hierarchy** | **Path-based (`/app/prod/db/host`) with `GetParametersByPath`** | Flat names by convention |
| **Encryption** | Optional (`SecureString` with KMS) | Always |
| **Direct database integration** | No | Yes - RDS/Aurora can manage the credential |

**The honest comparison**: Secrets Manager's genuine differentiators are **built-in rotation** and **cross-account/multi-region replication**. Everything else, Parameter Store does adequately and for free.

So the rule I would give: **Parameter Store for configuration and for secrets you do not rotate automatically; Secrets Manager for credentials that must rotate - database passwords above all - and for secrets shared across accounts or regions.**

The cost difference matters at scale in a way people underestimate: **400 secrets in Secrets Manager is ~$160/month**; the same in Parameter Store standard tier is **free**. For an estate with per-service, per-environment secrets, that is a real number, and it is why "just use Secrets Manager for everything" is a defensible default only until you count them.

**The operational points that apply to both**, and that matter more than the choice: **fetch at initialization and cache** - never per request, because the throughput limits and the per-call charges are both real (parent pack Q192); use **path hierarchies** in Parameter Store so `GetParametersByPath` retrieves an application's whole configuration in one call; and **never put a secret in an environment variable in plaintext** in a task definition or Lambda configuration - reference the secret ARN so the value is resolved at runtime and never appears in the resource definition or in CloudTrail.

*Hook: a configuration and secrets strategy you set, and whether cost or rotation drove the split.*

### Q202. AWS Config

Config records the **configuration state of your resources over time** and evaluates them against **rules**. Its components: a **configuration recorder** capturing resource state and every change; a **delivery channel** writing to S3; **rules** (AWS-managed or custom Lambda/Guard) that evaluate resources as compliant or not, triggered by configuration change or periodically; **conformance packs** bundling rules and remediation as a deployable unit, deployable across an organization; and **remediation actions** via SSM Automation, manual or automatic.

**The question Config answers that CloudTrail cannot**, and this is the crux:

**CloudTrail records API calls - events, actions, "who did what, when".** It is an audit log of activity. **Config records resource state - "what does this resource look like now, what did it look like on 3 March, and is it compliant?"**

So the questions only Config answers:

- **"Which resources are non-compliant with this policy, right now?"** CloudTrail can tell you that someone called `AuthorizeSecurityGroupIngress`; it cannot tell you which of your 3,000 security groups currently allow 0.0.0.0/0 on port 22 without you replaying and reconstructing every event ever.
- **"What did this resource look like before the incident?"** Config keeps a timeline of configuration items, so you can see the state at any past moment and **diff two points in time**.
- **"What is related to this resource?"** Config maintains a relationship graph - which ENIs, volumes and security groups belong to this instance.
- **"Was this ever compliant?"** Compliance history over time, which is what an auditor asks for.
- **Resources created outside of API calls you captured**, or state that drifted without a recorded event.

The complementary framing: **CloudTrail is the verb, Config is the noun.** An investigation typically uses both - Config to find what changed and when, CloudTrail to find who did it.

**The cost model** is the sting, and it is Q203: Config charges **per configuration item recorded** (each change to each resource) plus **per rule evaluation**. Both scale with change rate, not with resource count.

*Hook: an investigation or audit where Config's state history was the thing that answered the question.*

### Q203. The Config bill exceeding the resources it monitors

**How it happens** - the mechanism is that Config bills per **configuration item** (roughly $0.003 each) and per **rule evaluation**, and both are driven by **change frequency**:

1. **Recording all resource types, including the noisy ones.** The worst offenders are resources that change constantly: **ENIs and their attachments** in a container estate (every Fargate task creates and destroys one), **EC2 instances** in an aggressively scaling ASG, **security group rule changes** from automation, **S3 object-level configuration**, and Lambda function versions. A cluster running thousands of short-lived tasks per day generates tens of thousands of configuration items daily from ENIs alone - and each one costs money while telling you nothing you want to know.
2. **Recording global resources in every region.** IAM resources are global, and if the recorder in all 20+ enabled regions records them, you pay **20 times** for the same items. This is a default-configuration mistake that is pure waste.
3. **Periodic rules evaluating frequently across a large estate** - a rule evaluating every hour across 10,000 resources is 240,000 evaluations a day.
4. **Config enabled in every region by Control Tower or a landing zone**, including regions with nothing in them, where the recorder still runs and still records the global resources.
5. **Conformance packs deployed organization-wide** without reviewing which rules are actually needed, each adding evaluations across every account.

**What I would change:**

1. **Exclude the high-churn resource types** you do not need history for - `AWS::EC2::NetworkInterface` is almost always the biggest single win in a container estate. Config supports an exclusion list, and this one change routinely cuts the bill by more than half.
2. **Record global resources in one region only** (`includeGlobalResourceTypes` on a single recorder). Free saving, no loss of coverage.
3. **Switch to recording only on change with a daily snapshot** rather than continuous, where the resource type permits, and review whether **periodic rule frequency** needs to be hourly rather than daily.
4. **Turn off Config in regions you do not use** - and pair that with an SCP denying resource creation in those regions, so the absence of monitoring is not a gap.
5. **Review the rule set**: remove rules nobody acts on. A rule generating findings that are never remediated is a cost with no benefit, and conformance packs are full of them.
6. **Consider the alternative for some checks**: **Security Hub controls, or an EventBridge rule on the specific API call**, can answer a targeted question far more cheaply than a Config rule evaluating continuously.

**The framing to give**: Config's cost is **proportional to change, not to size**, which is counter-intuitive and is why the bill surprises people - the most dynamic, modern, well-automated parts of the estate generate the most cost. Tuning the recorder is a one-hour exercise that frequently saves five figures a year.

*Hook: a Config cost you reduced, and which resource type dominated it.*

### Q204. CloudFormation for a 40-account baseline

- **Change sets** - a preview of what an update will do before it does it: which resources are added, modified, or **replaced** (the important one, since a replacement destroys and recreates). Essential in a pipeline: generate the change set, review or gate on it, then execute.
- **Drift detection** - compares the live resources against the template, reporting what has been changed out of band. Useful for finding manual console changes; it detects drift but does not correct it, and it does not cover every property of every resource type.
- **Nested stacks** - stacks as resources inside a parent stack, for decomposing a large template and reusing components. They introduce coupling: a nested stack update goes through the parent, and failures are harder to diagnose. **Cross-stack references via exports also create hard coupling** - an exported value cannot be changed while another stack imports it, which can deadlock you - so SSM Parameter Store lookups are usually the better cross-stack mechanism (parent pack Q245).
- **StackSets** - deploy a stack to **many accounts and regions from one operation**, with automatic deployment to new accounts via **service-managed permissions with AWS Organizations**, plus deployment ordering, concurrency control and failure tolerance.

**For a 40-account baseline, StackSets is the answer**, and specifically **service-managed StackSets targeting organizational units**. The reasoning: the requirement is "every account, including accounts that do not exist yet, must have this baseline" - and StackSets with OU targeting and **automatic deployment enabled** satisfies exactly that. A new account created in the `workloads` OU receives the baseline automatically, with no pipeline step and nothing for anyone to remember. That property - **new accounts are compliant by construction** - is what makes it right at this scale.

The baseline it would deploy: CloudTrail configuration, Config recorder and rules, GuardDuty enablement, the standard IAM roles (deployment role, read-only role, break-glass), VPC endpoints, log group retention defaults, and budget alarms.

The operational details that matter: use **delegated administration** so the management account is not doing the deployments; set **failure tolerance and max concurrent accounts** deliberately (rolling out a broken baseline to 40 accounts simultaneously is a bad afternoon); and note that **StackSet updates are slow** across many accounts, so the baseline should change rarely and be tested in a small OU first.

The honest caveat: **Control Tower already does much of this** (Q214), so on a Control Tower landing zone, StackSets is for the things Control Tower's controls do not cover - and knowing where that boundary is prevents building a parallel system.

*Hook: a multi-account baseline you deployed, and how new accounts inherited it.*

### Q205. CloudFormation, CDK or Terraform for an operations team that does not write application code

**The honest answer is that the team's skills and the surrounding ecosystem decide it, not the tools' feature sets** - and for an operations team specifically, that pushes away from CDK.

| | Suits this team when |
| --- | --- |
| **CloudFormation (YAML)** | They want declarative, AWS-native, no toolchain, no build step, no language runtime. Reads like configuration. StackSets for multi-account. The cost is verbosity and weak abstraction. |
| **CDK** | Someone on the team genuinely writes TypeScript or Python **and will maintain it**. Gives real abstraction, testing and reuse - and **it is a software project**, with dependencies, upgrades, a build step, and synthesized output that must be understood when something goes wrong. |
| **Terraform** | They need **multi-cloud or non-AWS providers** (Datadog, GitHub, Cloudflare, VMware, Okta), or the organization already uses it. Better plan output, a more mature module ecosystem, and no CloudFormation to debug underneath. The cost is **state management** as your problem. |

**What actually decides it:**

1. **What can this team maintain in two years?** An operations team without a programming practice will write CDK by copying examples, will not write tests, and will eventually be unable to upgrade the CDK version or debug a synthesis failure. **CDK's abstraction is a liability without the engineering practice around it** - and this is the specific point the question is probing.
2. **What else do they manage?** If the estate includes SaaS configuration, DNS at an external provider, or another cloud, **Terraform** is decisively better because one tool covers everything. This is frequently the deciding factor for an operations team, whose scope is broader than one cloud.
3. **What does the rest of the organization use?** Diverging costs more than the tool difference is worth.
4. **Multi-account rollout.** StackSets (CloudFormation) is genuinely excellent at this; Terraform needs external orchestration.

**My recommendation for this specific team**: **Terraform if their scope extends beyond AWS or the organization already uses it; CloudFormation with StackSets if the scope is purely AWS multi-account baselines.** I would **not** recommend CDK to a team that does not write application code, even though it is the technically richest option - because the failure mode is not that it works badly, it is that in eighteen months nobody can change it.

The deeper point: **choose the tool the team can still operate when the person who introduced it has left.** Deferring the detail to `07-devops` for state management and pipeline mechanics, the selection criterion at this level is maintainability by the actual team, not capability.

*Hook: an IaC tool choice made for team-capability reasons, and whether it held up.*

### Q206. Service Catalog

Service Catalog lets a central team publish **approved, pre-configured products** (CloudFormation templates or Terraform configurations) organized into **portfolios**, which are shared with accounts and constrained by **launch constraints** (the product is provisioned using a role the *catalog* specifies, not the user's), **template constraints** (limiting parameter values - only these instance types, only these regions) and **tag options**.

**The pattern it enables**: a developer with no permission to create an RDS instance directly can **launch an approved "PostgreSQL database" product**, choosing from a constrained set of sizes, and receive a database that is encrypted, backed up, in the right subnet, tagged correctly and compliant - because the template says so and the launch constraint means their own permissions are irrelevant. **You grant the ability to create *correct* resources without granting the ability to create resources.** That inversion is genuinely valuable, and it is the strongest argument for it.

**Why most implementations fail:**

1. **The catalog goes stale.** Products are built once, in a project, and not maintained. Within a year the templates use old instance types, missing features and outdated defaults, and teams route around them. **A catalog needs a product owner and a release cadence**, and organizations fund the build but not the maintenance.
2. **It is too restrictive.** The parameters exposed do not cover real needs, so teams request exceptions, exceptions become the norm, and the catalog serves the simple cases nobody needed help with.
3. **It is imposed as a control rather than offered as a convenience.** If launching from the catalog is slower or less capable than a ticket, or than the team's own Terraform, adoption depends on enforcement - and enforced platforms decay (the parent pack's leadership scenario).
4. **The console-centric workflow does not fit engineering teams** who work in pipelines and IaC. A product launched by clicking in a console is not in anyone's repository, which conflicts directly with how mature teams work - **and this is the most common structural reason it fails in an engineering organization**.
5. **It duplicates a construct library.** If teams already consume a shared CDK or Terraform module library, that *is* the paved road, and Service Catalog adds a second, worse one.

**Where it genuinely works**: organizations with a **large population of non-engineering or low-engineering consumers** - data scientists needing a SageMaker environment, analysts needing a database, business units needing a standard application stack - where self-service through a console is the right interface and IaC is not. Also for **regulated environments** where the audit requirement is that resources were provisioned from an approved template.

**Where I would use a module library instead**: an engineering organization that already works in code. The paved road should be a dependency in their repository, not a portal.

*Hook: a self-service provisioning mechanism you built, and whether it was a catalog or a module library.*

### Q207. Trusted Advisor

Trusted Advisor runs checks across five categories - **cost optimization, performance, security, fault tolerance, and service limits** - and reports findings with recommended actions. The **service limits (quota utilization) checks** and a subset of security checks are available on all support plans; **the full check set requires Business or Enterprise support**.

**The checks that matter:**

- **Service quota utilization** - the most valuable, because it warns before you hit a limit (the parent pack's failover scenario), and it is available at every support tier.
- **Idle and underutilized resources** - stopped instances with attached volumes, idle load balancers, unassociated Elastic IPs, low-utilization instances, unattached EBS volumes.
- **Reserved Instance and Savings Plan recommendations** and expiring commitments.
- **Security group rules open to 0.0.0.0/0** on sensitive ports, public S3 buckets, root account MFA, exposed access keys.
- **Fault tolerance**: single-AZ resources, ASGs without multi-AZ, RDS without Multi-AZ, missing backups.

**Its structural limits, which is the substance of the question:**

1. **It has no context.** It reports that an instance is underutilized; it does not know it is a DR standby, a licence server, or a batch host that runs hard once a month. **Every recommendation requires human judgement**, and a team that acts on them mechanically will break things - which is the fastest way to make people ignore the tool.
2. **It is a fixed check set.** You cannot express organization-specific policy. It is a generic best-practice checklist, not a governance mechanism - for that you need **Config rules** (Q202) or **Security Hub**.
3. **The thresholds are not tunable** for most checks, so an "underutilized" instance is judged against AWS's definition, not yours.
4. **The cost recommendations are shallow.** It finds idle resources and commitment opportunities; it does not do architectural cost analysis - it will not tell you that the NAT gateway processing charge is your largest line item or that a gateway endpoint would eliminate it. **Compute Optimizer** (Q208) and **Cost Explorer** do deeper work.
5. **The full check set is gated behind a paid support plan**, which for a smaller organization means the useful version is not available.
6. **It is a snapshot, not a trend.** No history, weak alerting, and findings that reappear until acted upon with no workflow.

**How I would use it**: as a **periodic sanity sweep**, reviewed monthly, with the **service limits checks wired to alerts** (via the Trusted Advisor EventBridge events) because that one is genuinely operational. Not as the cost programme, not as the security programme, and not as anything anyone is measured against.

*Hook: a Trusted Advisor finding that was genuinely useful, and one you correctly ignored.*

### Q208. Compute Optimizer

Compute Optimizer analyses **CloudWatch metrics history** with machine learning to recommend right-sizing for EC2 instances, Auto Scaling groups, EBS volumes, Lambda functions, ECS services on Fargate, RDS instances and commercial software licences. It classifies resources as **under-provisioned, over-provisioned, optimized or none**, with specific recommended alternatives and projected savings and performance risk.

**What it needs**: **at least 30 hours of metrics** (and meaningfully more for good recommendations), and crucially - **memory metrics require the CloudWatch agent**. Without it, the hypervisor provides CPU, network and disk, but **not memory**, so recommendations are made on CPU alone. That is the single most important caveat: **a memory-bound Java workload looks over-provisioned on CPU, and following the recommendation causes OOM kills.** Enabling **enhanced infrastructure metrics** (a paid feature) extends the lookback from 14 days to 3 months, which materially improves quality.

**What it recommends well**: consistently over-provisioned instances in steady workloads, generation upgrades (`m5` to `m6i`, which are usually cheaper *and* faster), gp2-to-gp3 volume migrations, Lambda memory tuning (genuinely good - it does the cost/duration curve for you), and Graviton migration opportunities.

**What it systematically misses:**

1. **Memory, without the agent** - as above, and this is the big one.
2. **Business context and cyclicality.** A 14-day lookback over a quiet fortnight misses month-end, quarter-end, Black Friday and the annual batch run. Right-sizing on that basis is a future incident with a delayed fuse.
3. **Headroom requirements.** It optimizes toward utilization, not toward the burst capacity a latency-sensitive service needs. A service sized to handle a failover of its AZ peers looks over-provisioned by design.
4. **Licensing constraints.** Downsizing an instance with a per-core licence may save nothing, or the licence may forbid the target type.
5. **Application-level constraints** - a JVM heap sized for the instance, a connection pool sized for the vCPU count, an application with a hard-coded thread count.
6. **Anything that is not a resource metric** - a queue consumer sized for latency rather than utilization, a DR standby, a warm spare.

**How to use it responsibly**: install the CloudWatch agent everywhere **first**, enable enhanced infrastructure metrics, then treat recommendations as **candidates requiring owner confirmation**, applied **one size step at a time, in non-production first**, and never during a peak period. And track reliability metrics before and after (Q259 in the parent pack), because a right-sizing programme that quietly degrades p99 latency has not saved money.

*Hook: a Compute Optimizer recommendation you followed, and one you rejected with a reason.*

### Q209. Cost Explorer, CUR, Budgets and Cost Anomaly Detection

| Tool | The question it answers |
| --- | --- |
| **Cost Explorer** | **"Where is the money going, and how has that changed?"** Interactive analysis by service, account, tag, usage type, over time, with forecasting and RI/SP recommendations. The first place to look. |
| **Cost and Usage Report (CUR)** | **"Give me every line item so I can build my own analysis."** Hourly or daily, resource-level, delivered to S3 in Parquet, queryable with Athena. The only source detailed enough for per-tenant allocation, chargeback, or joining cost to your own usage metrics. |
| **Budgets** | **"Tell me when spend exceeds a threshold I set."** Cost, usage, RI/SP utilization and coverage budgets, with alerts and optional automated actions (apply an SCP, stop instances). Threshold-based and forward-looking via forecast alerts. |
| **Cost Anomaly Detection** | **"Tell me when spend deviates from its own pattern, without me setting a threshold."** ML-based per-service or per-account monitors that learn the normal shape and alert on statistically significant deviations. |

**The distinction that matters most is Budgets versus Anomaly Detection**, because they are often conflated: a **budget is a threshold you chose** - useful for governance ("this team gets $10,000 a month") and useless for catching a problem below the threshold. **Anomaly detection has no threshold** - it catches a service that jumped 400 percent while the total remained under budget, which is exactly the recursion-loop scenario in the parent pack. **You need both**, and organizations typically have only budgets.

**What I would set up as a baseline:**

- **Cost Explorer** available to engineering teams, not just finance. Most cost problems are fixed by the person who caused them, if they can see them.
- **CUR into S3 with Athena and a Glue catalog**, because every serious cost question eventually needs line-item data, and setting it up retroactively means waiting a month for history.
- **Budgets per team or per account**, with alerts at 80 and 100 percent of both actual and **forecast** - the forecast alert is the one that gives you time to act.
- **Cost Anomaly Detection with a monitor per service and per linked account**, alerting to the **engineering** channel rather than to finance, with a low threshold. Detection should be hours, not the monthly invoice.

*Hook: a cost surprise, which of these tools caught it, and how long it took.*

### Q210. Savings Plans and RIs at the organization level

**Sharing**: by default, **discounts are shared across the whole organization** - a Savings Plan or RI purchased in one account applies to matching usage in any account under the same management account, with the discount applied to whichever eligible usage maximizes the benefit. **RI and Savings Plans discount sharing can be turned off per account**, which you would do for an account whose costs must be strictly ring-fenced (a subsidiary, a customer-dedicated account, a chargeback boundary).

The practical implication: **buy commitments centrally, in the management account or a dedicated billing account**, and let them float across the organization. Buying per-team means stranded commitments when a team's workload changes, and it wastes the flexibility that is the whole point.

**My commitment strategy for a growing estate:**

1. **Cover the floor, not the average, and not the peak.** Look at the trailing 60-90 days of hourly on-demand-equivalent spend and commit to a level below the **minimum**, so the commitment is always fully utilized. **Utilization must be ~100 percent**; coverage is the number you grow.
2. **Ladder the commitments.** Do not buy one large three-year plan. Buy in tranches quarterly, so expiries are staggered and you are never renegotiating the whole estate at once - and so a workload change affects one tranche rather than everything.
3. **Prefer Compute Savings Plans** (Q7) for flexibility across family, region, and Fargate and Lambda. In a *growing* estate, re-platforming is likely, and a commitment that survives a move to Graviton or containers is worth the few percentage points it costs.
4. **One-year over three-year while growing**, mostly. Three-year terms give a deeper discount and lock in architectural assumptions for a very long time. A reasonable split is a three-year commitment on the genuinely stable core (a database tier, a steady baseline) and one-year on everything else.
5. **Review monthly**: **coverage** (what fraction of eligible spend is discounted - target 70-85 percent, not 100, because the last slice is the most volatile) and **utilization** (target ~100 percent). Both are Budgets metrics, so alert on them.
6. **Never commit ahead of a known change** - a migration, a re-platform, a shutdown. And check the roadmap before every purchase, which means talking to engineering rather than working from the billing console.

**The failure mode to name**: an organization that buys a large three-year commitment, then completes a modernization that halves compute usage, and spends two years paying for capacity it does not use. **The commitment should follow the architecture, not constrain it** - and if a commitment is preventing a good architectural decision, that is a sunk cost, not a reason.

*Hook: a commitment portfolio you managed, the coverage and utilization you targeted, and a commitment you regretted.*

### Q211. Health Dashboard and Personal Health events

The **AWS Health Dashboard** has two parts: the **public status page** (broad service status, historically slow to update and coarse) and **your account's Health Dashboard**, which shows events **specific to your resources** - the far more useful one.

**Personal Health events** cover three categories: **issues** (an AWS-side problem affecting your resources - a degraded service in your region), **scheduled changes** (an EC2 instance requiring a reboot for maintenance, an RDS certificate rotation, a Lambda runtime deprecation, an EBS volume on degraded hardware), and **account notifications**. Crucially, they carry **affected resource identifiers** - the specific instance IDs, not just "some customers may be affected".

**Turning them into automated action rather than an email nobody reads** - which is the question, and the answer is the **AWS Health API and EventBridge**:

Health events are published to **EventBridge**, so they are programmable:

```
Health event -> EventBridge rule -> action
```

Concrete automations worth building:

- **`AWS_EC2_INSTANCE_RETIREMENT_SCHEDULED`** → a Lambda or SSM Automation that checks whether the instance is in an ASG. If it is, **terminate it and let the ASG replace it** at a time you choose, well before the forced retirement. This turns a scheduled outage into a non-event, automatically, and it is the single highest-value one.
- **`AWS_EBS_VOLUME_LOST` / degraded volume** → page immediately, and trigger a snapshot-based recovery runbook.
- **`AWS_RDS_*` maintenance or certificate rotation** → create a ticket with the affected instance and the deadline, assigned to the owning team via resource tags.
- **Service degradation in a region** → post to the incident channel automatically with the affected resources, so the on-call engineer's first question ("is it us or is it AWS?") is answered before they ask it. **This is worth a great deal at 3am.**
- **Lambda runtime or engine version deprecation** → open a tracking issue with the deadline, so version currency (Q148) is managed rather than discovered.

**Organizational view** is the enabling feature at scale: enabling **AWS Health organizational view** aggregates events from every account into the management account, so one EventBridge rule set covers 40 accounts rather than 40 configurations.

**The principle**: Health events are **the only signal that tells you about a problem AWS knows about and you do not**, and they arrive with resource-level precision. Leaving them in email is discarding the highest-signal, lowest-noise operational feed available - and wiring them to EventBridge is a day's work with a permanent payoff.

*Hook: an AWS Health event you automated a response to, or one you missed because it went to email.*

### Q212. CloudWatch for an EC2 estate

**What the hypervisor gives you for free**: CPU utilization, network in/out, disk read/write on the instance store, EBS metrics, and status checks. **What it cannot see** is the answer to the question:

**Memory utilization and disk space used** are invisible from outside the instance. The hypervisor knows how much memory it *allocated*, not how much the guest OS is *using*, and it has no idea what a filesystem's utilization is. **These are the two metrics that most often matter** - "the instance ran out of memory" and "the disk filled" are two of the most common causes of instance failure, and neither is visible without the agent. Also invisible: per-process resource use, swap, filesystem inode usage, TCP connection state counts, and anything from inside the application.

**The CloudWatch agent** collects these and ships them as custom metrics, plus it handles **log collection** from files on disk (application logs, system logs, IIS logs), and can collect **StatsD and collectd** metrics from applications. Installing it everywhere, via State Manager (Q200) so it self-heals, is a baseline requirement - and it is a prerequisite for Compute Optimizer being useful (Q208).

**The rest of the toolkit:**

- **Custom metrics** cost ~$0.30 per metric per month, and **a metric is a unique combination of name and dimensions** - so publishing a metric with an instance-ID dimension across 500 instances is 500 metrics. This is how custom-metric bills get out of hand, and the mitigation is aggregating dimensions carefully or using **EMF** (parent pack Q189) to derive metrics from logs.
- **Log groups**: **set a retention period on every one.** The default is never-expire, and forgotten log groups accumulating at $0.03/GB-month forever is one of the most common silent costs in any estate. This should be enforced by a Config rule with auto-remediation.
- **Metric filters** extract metrics from log content - counting `ERROR` lines, extracting a latency value from a log message - which is how you alarm on things the application does not publish as a metric.
- **Composite alarms** combine multiple alarms with boolean logic, and their real value is **noise reduction**: alarm only when the error rate is high **and** the deployment is not in progress; or a single "service unhealthy" alarm that pages, with the twenty component alarms feeding it silently. This directly addresses the alert-storm problem, and it is under-used.
- **Alarms on `INSUFFICIENT_DATA`** deserve a deliberate decision - a metric that stops reporting because the instance died should usually be treated as a failure, not ignored.

*Hook: a metric you could only get from the agent, and the incident that made you install it.*

### Q213. Automating non-production shutdown

**The mechanisms**, from simplest to most capable:

1. **AWS Instance Scheduler** - the AWS-published solution: a CloudFormation stack with a Lambda, DynamoDB and EventBridge, driving start/stop by a **tag on the resource** (`Schedule: office-hours`). Handles EC2 and RDS, multiple time zones, cross-account and cross-region. **The right default** because it is maintained, tag-driven and handles the edge cases.
2. **EventBridge Scheduler plus a Lambda or SSM Automation** - a cron rule invoking `StopInstances` and `StartInstances` on tagged resources. Simple, transparent, and about 50 lines. Good when the requirement is simple and you want to own it.
3. **Auto Scaling scheduled actions** for ASGs - set min/max/desired to 0 at 19:00 and back at 07:00. The cleanest mechanism for anything already in an ASG, and it composes correctly with dynamic scaling.
4. **RDS**: instances can be **stopped for a maximum of 7 days**, after which AWS starts them automatically - a real constraint that catches people over holidays. **Aurora Serverless v2 scaling to zero** (Q140) is the better answer for non-production databases.
5. **ECS/EKS**: scale services to zero replicas rather than stopping nodes, or scale the node group.

**What always breaks the first time:**

1. **Something was running that mattered.** A nightly batch job, an overnight integration test suite, a scheduled data refresh, or a colleague in another time zone. **The first shutdown reveals dependencies nobody documented** - and the fix is an opt-out tag plus a warning period before enforcement, not an argument.
2. **Things do not come back cleanly.** Services that do not start on boot, applications that fail because a dependency started in the wrong order, databases whose connections all fail for a period, and instances whose **public IPs changed** (Q17) breaking anything that hardcoded them. Start-up is less tested than shutdown.
3. **The stop is not a real saving.** A stopped EC2 instance still bills for **EBS volumes and Elastic IPs**, so the saving is compute only - typically 60-70 percent of the instance cost, not 100. And **RDS stopped instances still bill for storage and backups**. Presenting the saving as the full resource cost is a credibility error.
4. **Tag coverage is incomplete**, so half the estate keeps running and the saving is half what was promised. Tag enforcement is the prerequisite.
5. **Nobody can override it.** An engineer working late, or a demo on a Saturday, finds their environment shut down with no way to start it - so they disable the whole schedule. **A self-service override** (a tag change, a chatbot command, a "keep alive until" tag) is what makes it survive contact with the team.

**How I would roll it out**: tag-driven with an **opt-out** rather than opt-in (opt-in gets 20 percent coverage), a **two-week warning period** with notifications and no action, a **self-service override**, and a **published saving** afterwards so the team sees the result. Expect **60-70 percent off the non-production compute bill**, which for an estate where non-production is 30-40 percent of spend is a large, low-risk win.

*Hook: a shutdown schedule you implemented, the saving, and what broke the first week.*

### Q214. Governance baseline for 3 to 40 accounts

**Clarify first**: what is driving the growth - team autonomy, compliance separation, acquisitions? Is there a compliance regime (PCI, HIPAA, SOC 2) with specific control requirements? Who will own this - is anyone dedicated, or is it a side responsibility? What is the tolerance for slowing teams down? And what already exists in the three accounts, because retrofitting is harder than building.

**The constraint that shapes everything: no dedicated platform team.** So the design principle is **"automated and inherited, not reviewed and enforced"** - anything requiring a human in the path will not survive, and anything a new account does not get automatically will be missing.

**The baseline:**

**1. Control Tower as the foundation.** With no platform team, hand-rolling a landing zone is the wrong call. Control Tower gives Organizations, a security and log-archive account, CloudTrail and Config aggregation, a guardrail set, and **Account Factory** so a new account arrives compliant. It has opinions and some inflexibility, and **that is a feature here** - it substitutes for the platform team's judgement.

**2. An OU structure that expresses the policy boundaries**, not the org chart: `Security`, `Infrastructure`, `Workloads/Prod`, `Workloads/NonProd`, `Sandbox`, `Suspended`. SCPs attach to OUs, so the structure *is* the policy model.

**3. SCPs - a small set, high value**, because over-restrictive SCPs generate escalations nobody has time to handle:
- Deny disabling CloudTrail, Config, GuardDuty.
- Deny leaving the organization, and deny modifying the Control Tower roles.
- **Deny all regions except the two or three you use** - which shrinks the attack surface, the Config bill (Q203) and the monitoring burden in one line.
- Deny root user actions.
- In production OUs: deny deleting backups, and deny `rds:DeleteDBInstance` outside a break-glass role (Q143).

**4. Identity through IAM Identity Center**, with permission sets mapped to groups in the existing identity provider. **No IAM users anywhere.** Federation for humans, OIDC for CI. This is the single highest-value control and it is a day's work.

**5. Centralized logging and detection** in the log-archive and security accounts: CloudTrail organization trail to an immutable, Object-Locked S3 bucket; Config aggregated; GuardDuty and Security Hub enabled organization-wide with delegated administration. Configured once at the organization level, so new accounts are covered automatically.

**6. Cost visibility from day one** (Q209): CUR into S3, Cost Explorer available to teams, budgets per account with forecast alerts, Cost Anomaly Detection per account, and **mandatory tags enforced in IaC** rather than by policy - plus Cost Categories mapping accounts to teams.

**7. A baseline deployed by StackSets** (Q204) with automatic deployment to new accounts: log group retention defaults, VPC endpoints, the standard roles, budget alarms, and the Config rules that matter.

**8. Network foundation** (Q131), scaled to the size: a CIDR plan with IPAM from the start - because that is the unrecoverable decision (Q129) - and Transit Gateway when the VPC count justifies it, not before.

**9. A paved road for the teams**: a shared IaC module library and a reference pipeline, so the easy path is the compliant path.

**The sequencing over the year**, since it cannot all be done at once: Control Tower, OUs, Identity Center and centralized logging in the first month (these are prerequisites and get harder later); cost visibility and tagging in month two; the StackSet baseline and SCPs in months two to three; the network foundation as the VPC count grows; and the module library iteratively as teams ask for things.

**What I would tell leadership**: this needs **an owner with allocated time** - perhaps 30-50 percent of one engineer - even if not a full team, and without that the baseline decays and the fortieth account will not look like the fourth. **Governance that nobody owns is governance that expires.** And I would set one measurable outcome: **the percentage of accounts that are compliant with the baseline without manual intervention**, reported monthly.

*Hook: a governance baseline you built during rapid account growth, and what you had to retrofit later.*

---

## 14. Service-selection exercises

Q215-220 are worked in full in [scenario-questions.md](scenario-questions.md) as exercises S11-S16. Attempt each out loud for fifteen minutes before reading the model answer.

The pattern each one is testing is the same: **establish the constraints before naming a service, name the deciding number rather than a preference, and say what you would give up.** A list of services is not an answer; a decision with a stated trade-off is.
