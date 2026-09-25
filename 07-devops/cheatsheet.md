# DevOps Cheatsheet

Fast revision. Kubernetes/EKS, GitHub Actions, Argo CD, Terraform, Prometheus/OpenTelemetry unless another tool is named. Assumes [../01-java/cheatsheet.md](../01-java/cheatsheet.md) and [../03-microservices/cheatsheet.md](../03-microservices/cheatsheet.md).

---

## The delivery contract

Everything else in this pack is an implementation of these seven properties:

1. **One immutable artifact per commit**, addressed by **digest**, built once.
2. **Signed**, with **provenance** and an **SBOM** bound to that digest.
3. **Promoted, never rebuilt** - environments differ by injected config only.
4. **Deployed declaratively from git** - running state is a reviewable commit.
5. **Progressively**, with automated analysis and automatic abort.
6. **Emitting a deployment event**: SHA, digest, environment, actor, timestamp.
7. **Rollback available and tested**, with rollback-safety stated per release.

**CI** = everyone merges to mainline daily and a red mainline stops the team. **CD (delivery)** = every passing build is deployable; a property of the *artifact*. **Continuous deployment** = every passing build *is* deployed; a property of the *pipeline*.

**Build once, deploy many.** Rebuilding per environment means production runs a binary that was never tested. `latest` and mutable tags break this silently; use `image@sha256:...`.

---

## DORA, and what the numbers mean

| Metric | Elite | What a bad number tells you |
| --- | --- | --- |
| Deployment frequency | on demand, multiple/day | batch size is large → every other metric degrades |
| Lead time for change | < 1 hour | queueing, not typing; measure commit → production |
| Change failure rate | 0-15 percent | prediction controls failing; add containment |
| MTTR / failed deployment recovery | < 1 hour | rollback is not tested |
| *(add)* Reliability / SLO attainment | - | the four above optimized without this is how you get fast garbage |

**Speed and stability correlate positively.** The trade-off framing is wrong: the same practices (small batches, automation, fast feedback) produce both. Slowing down to be safe usually makes both worse.

**Batch size is the hidden variable.** Weekly releases → bigger batches → more candidate causes per incident → slower MTTR → more fear → less frequent releases.

---

## Pipeline shape and budgets

```
commit → build+unit (5 min, blocking) → package+sign+SBOM+scan (5 min)
       → deploy to test + integration/contract (15 min)
       → promote (digest) → staging → canary prod → 100%
```

| Stage | Budget | If it exceeds |
| --- | --- | --- |
| Pre-merge feedback | **10 min** | developers context-switch; batching resumes |
| Full pipeline to production-ready | 30-40 min | |
| Rollback | **< 5 min** | rollback is theatre |

A green 55-minute pipeline is a **defect**, not a success. Fix order: parallelize → cache → shift slow tests right of the merge gate → shrink the test estate.

**Flaky test policy**: quarantine automatically after N failures, never retry silently in the merge gate, own the quarantine list with a decay date. Retries hide the flake and destroy trust in red.

---

## Git and branching

| Model | Integration frequency | Cost |
| --- | --- | --- |
| **Trunk-based** (+ short-lived branches < 1 day) | continuous | requires flags and expand-contract discipline |
| GitHub flow | days | merge conflicts grow with branch age |
| **GitFlow** | weeks | release branches = batch = the DORA killer |

Branch protection minimum: required checks, required review, **linear history or squash**, no force-push to default, **signed commits**, `CODEOWNERS` for risky paths, and *admins included*.

**Merge queue** exists because "green PR" ≠ "green after merge" - the queue tests the *resulting* mainline, batching optimistically and bisecting on failure.

Monorepo: needs path filtering, affected-target detection, remote cache, `CODEOWNERS`. Polyrepo: needs dependency-bump automation and cross-repo release coordination. Neither is free.

---

## CI mechanics (GitHub Actions)

| Concept | Note |
| --- | --- |
| Hosted runners | zero ops, no VPC access, per-minute cost, cold cache |
| Self-hosted **ephemeral** (ARC) | VPC access, control, warm cache; **never reuse a runner across untrusted jobs** |
| `pull_request` vs **`pull_request_target`** | the latter runs *your* code with *secrets* against a fork's PR - the classic RCE |
| `GITHUB_TOKEN` | scope it `permissions: read-all` by default, elevate per job |
| Reusable workflow vs composite action | workflow = whole jobs + secrets inheritance; action = steps inside one job |
| Concurrency group | `cancel-in-progress` for PRs, **never** for production deploys |
| Cache key | content hash of the lockfile, with `restore-keys` fallback; a cache is a *hint*, never a correctness dependency |

**Pin third-party actions to a commit SHA**, not a tag. A tag is mutable and the supply-chain compromise is exactly that.

**Never trust the cache for correctness.** A poisoned cache is a supply-chain attack; scope caches by branch and never share a writable cache between PR and default branch.

---

## Supply chain

| Artefact | Answers |
| --- | --- |
| **SBOM** (SPDX/CycloneDX) | what is in this image |
| **Provenance** (in-toto/SLSA) | who built it, from what source, on what builder |
| **Signature** (Sigstore/cosign) | this digest came from us and is unmodified |
| **VEX** | this CVE is present but not exploitable here, and why |

SLSA levels ≈ L1 provenance exists → L2 signed by a hosted builder → **L3 non-falsifiable provenance from an isolated builder** (this is the meaningful bar) → L4 hermetic + two-party review.

**Sign the digest, not the tag.** Verify at **admission**, not only in the pipeline - otherwise the check is advisory.

Dependency defences: lockfiles committed, **exclusive routing** for internal namespaces (kills dependency confusion), no unpinned floating versions, no install-time scripts in CI where avoidable, and an internal proxy with quarantine on new versions.

Scanner noise: severity alone is useless. Prioritize by **reachability + exploitability (KEV/EPSS) + exposure**. A critical in an unreachable code path outranks nothing.

---

## Containers and the JVM

```dockerfile
# layer order = cache hit rate: least-changing first
FROM eclipse-temurin:21-jdk AS build   # deps layer, then source layer
FROM gcr.io/distroless/java21-debian12  # no shell, no package manager
USER 65532:65532
```

| Base | Trade |
| --- | --- |
| `-jre` slim | familiar, has a shell, larger CVE surface |
| **distroless** | small surface, **no shell** - `kubectl exec` debugging dies; use ephemeral debug containers |
| Alpine + JDK | musl; historically a JVM performance/compat risk - verify, do not assume |

JVM in a container, non-negotiable:

- The JVM is **container-aware** since 10/8u191 - it reads cgroup limits. Do not hardcode heap.
- `-XX:MaxRAMPercentage=75` (not `-Xmx`), leaving room for **metaspace, thread stacks, code cache, direct buffers** - the heap is not the footprint. `OOMKilled` with plenty of free heap = off-heap.
- **CPU limits cause CFS throttling**: the JVM sizes GC and pool threads from `availableProcessors()`, then gets throttled at the 100 ms quota boundary. Symptom is p99 latency spikes with average CPU well under the limit.
- **Set requests always; think hard before setting CPU limits.** Memory limits yes (memory is incompressible); CPU limits usually no.
- Layer the fat JAR (`--layers`) so dependencies cache separately from application classes.

---

## Kubernetes, condensed

**Reconciliation, not orchestration.** Every controller watches desired state and drives actual towards it, forever. This is why deleting a pod does not "work" and why drift self-heals.

| Object | Use |
| --- | --- |
| Deployment | stateless, interchangeable replicas |
| StatefulSet | stable identity + per-pod volume; ordered rollout; **PVCs survive deletion** |
| DaemonSet | one per node (agents, CNI, log shippers) |
| Job/CronJob | batch; set `concurrencyPolicy`, `startingDeadlineSeconds`, `backoffLimit`, `ttlSecondsAfterFinished` |

### Probes - the highest-yield table in the pack

| Probe | Failure action | Use for |
| --- | --- | --- |
| **startup** | kills after threshold, *suspends the other two* | slow-starting JVMs. Its absence causes the classic restart loop |
| **readiness** | removes from **Endpoints** (no traffic) | dependency checks, warm-up, load shedding |
| **liveness** | **kills the container** | *only* unrecoverable states (deadlock). Cheap, dedicated, generous timeout |

**Never put a dependency check in liveness.** Database slow → every pod fails liveness → whole fleet restarts → you turned a degradation into an outage.

**The metastable loop**: load ↑ → probe served by a saturated pool → timeout → kill → cold restart → its traffic redistributes → more kills. Fix by relaxing/removing liveness *first*, then adding capacity.

### QoS and eviction

| Class | Condition | Evicted |
| --- | --- | --- |
| **Guaranteed** | requests == limits, all containers, cpu+mem | last |
| **Burstable** | requests < limits | by usage-over-request |
| **BestEffort** | nothing set | **first** |

Scheduling uses **requests**; enforcement uses **limits**. Over-requesting wastes money invisibly; under-requesting gets you evicted.

`OOMKilled` = the container exceeded its memory **limit** (cgroup, kernel kill, exit 137). Node-pressure eviction = the *node* ran out and the kubelet chose a victim. Different problems.

### Graceful shutdown - the ordering that causes "deploys drop requests"

Endpoint removal and `SIGTERM` are **concurrent, not ordered**. The proxy on some node may still send traffic after the process starts shutting down.

```yaml
lifecycle:
  preStop:
    exec: { command: ["sleep", "10"] }   # absorb the propagation race
terminationGracePeriodSeconds: 60        # > preStop + longest in-flight request
```

Plus: application handles `SIGTERM` → fails readiness → drains in-flight → exits. PID 1 must actually receive signals (no shell wrapper, or use an init).

### Rollout knobs

`maxSurge` / `maxUnavailable`: `maxUnavailable: 0` = never dips below capacity, needs headroom. `minReadySeconds` prevents a fast rollout from racing past a crash that appears after 20 seconds. `progressDeadlineSeconds` marks the rollout failed - **it does not roll back**.

---

## Networking, storage, cluster ops

Service types: ClusterIP → NodePort → LoadBalancer; **Ingress/Gateway API** for L7. Gateway API splits the roles: infra team owns `GatewayClass`/`Gateway`, app teams own `HTTPRoute`.

**Headless Service** (`clusterIP: None`) returns pod IPs - required for StatefulSet peer discovery and client-side load balancing over long-lived connections (gRPC).

**gRPC/HTTP2 through a L4 Service is broken by design**: one long-lived connection pins to one pod, so new pods get no traffic. Fix with client-side LB + headless, or a L7 proxy/mesh.

NetworkPolicy: **default-deny per namespace, then allow**. Without a policy everything can reach everything. Policies are additive; there is no deny rule.

CNI on EKS: the VPC CNI gives pods **real VPC IPs** (great for security groups and observability, constrains IP planning and pods-per-node by ENI limits). Prefix delegation raises density.

Storage: **`reclaimPolicy: Delete` on a production StorageClass is a data-loss incident waiting for a namespace delete.** Use `Retain`. `volumeBindingMode: WaitForFirstConsumer` avoids provisioning a volume in a zone the pod cannot schedule into.

Drain stalls, in order of likelihood: **unsatisfiable PDB** (`minAvailable: 1` on 1 replica = blocks forever) → replacement pod cannot schedule (capacity/affinity/topology) → StatefulSet volume detach → bare pod with no controller → long grace period.

Upgrades: control plane first, then nodes; **kubelet may be up to 3 minor versions behind the API server, never ahead**. A mixed-version cluster is a supported steady state - do not rush it to meet a window.

Autoscaling layers: **HPA** (replicas) / **VPA** (requests - do not run with HPA on the same metric) / **Cluster Autoscaler or Karpenter** (nodes). Karpenter provisions right-sized nodes directly from pending pod shape instead of scaling fixed node groups.

---

## Config and secrets

**Config that differs per environment is injected; everything else is in the image.** A ConfigMap change does *not* restart pods - either mount as a volume and watch, or (better) checksum the config into the pod template annotation so a change rolls the Deployment.

| Approach | Note |
| --- | --- |
| **External Secrets Operator** | store of record stays in Vault/ASM; syncs to a Secret; rotation propagates |
| **Sealed Secrets** | encrypted in git, cluster-specific key; simple, no external store, painful rotation |
| **SOPS** | encrypted files in git, KMS-backed; good for GitOps, still git-resident |
| **CSI Secrets Store** | mounted directly, never a Kubernetes Secret object |
| Kubernetes Secret alone | **base64 is not encryption**; enable encryption at rest + RBAC or it is a ConfigMap with a warning label |

**Best of all: no secret.** IRSA / Workload Identity / OIDC federation removes the credential entirely - nothing to rotate, nothing to leak.

Feature flags: the **cold-start default** is the one that matters. If the flag service is unreachable at boot, what does the SDK return? Decide it deliberately, cache last-known-good, and treat the flag service as a tier-1 dependency. Flags are code with no review, no tests and no rollback unless you build them - so they need expiry dates and an owner.

---

## Release strategies

| Strategy | Traffic | Cost | Rollback | Good for |
| --- | --- | --- | --- | --- |
| Rolling | gradual by pod | 1x + surge | re-roll (minutes) | default |
| **Blue/green** | instant switch | **2x** | instant | fast rollback, hard cutover; migrations are the catch |
| **Canary** | 1→5→25→50→100 | ~1.1x | shift weight back | statistically detectable change |
| Shadow/mirror | 0 percent real | 2x compute | n/a | validating without risk; **beware duplicate side effects** |
| Feature flag | per user/request | 1x | flip | product experiments, decoupling deploy from release |

**Deploy ≠ release.** Deploy = the artifact is running. Release = users see it. Everything good follows from separating them.

Canary analysis must compare against a **concurrent baseline** (the stable version *right now*), not against yesterday - otherwise every diurnal pattern reads as a regression. Watch error rate, latency percentiles, saturation, and at least one business metric. Automate the **abort**.

**Rollback safety is a property of the release, and the pipeline should know it.** A release that writes a new data format or runs a non-additive migration is *not* rollback-safe; automatic rollback must be disabled and the only path is forward.

**Expand-contract** for every schema and format change:
1. **Expand** - add the new nullable column/field; deploy code that writes both, reads old.
2. **Migrate** - backfill in batches.
3. **Switch** - read new.
4. **Contract** - stop writing old, then drop, *after* a deliberate delay.

Each step is independently deployable and revertible. The delay before contract is the rollback window.

---

## GitOps and Argo CD

**Pull, not push.** The cluster reconciles itself from git: no CI credentials into the cluster, drift self-heals, the running state is a reviewable commit, and recovery is "point a new cluster at the repo".

| Term | Meaning |
| --- | --- |
| `Synced` | live objects match git |
| `Healthy` | resources report ready by their health check |
| **Neither means "the service works"** | that is what the canary and the SLO are for |

- **Separate the app repo from the manifest repo** - otherwise every deploy is a commit to source and the audit trail is noise.
- **Promotion = an automated PR changing one image digest.** The merge is the authorization event, and it is your change record.
- **`selfHeal: true`** reverts manual `kubectl` changes - which is the point, and also why break-glass needs a defined path (disable auto-sync, or commit).
- **`prune: true`** deletes what git no longer declares - powerful and dangerous; combine with `Retain` PVs and prune protection on stateful resources.
- **ApplicationSet** generates Applications from a directory/cluster/list generator - this is how "add a service" becomes "add a directory".
- **One Argo CD per production cluster**, not one hub controlling production - blast radius and credential concentration.
- **`ignoreDifferences`** for fields mutated by other controllers (HPA replicas, injected sidecars, cloud-assigned annotations); otherwise you fight a permanent diff.

Argo Rollouts (or Flagger) supplies the progressive delivery Argo CD lacks: `Rollout` replaces `Deployment`, `AnalysisTemplate` defines the metric queries and thresholds, and failure aborts automatically.

**Undetected non-deployment is the GitOps failure mode.** Alert on any Application not `Synced`+`Healthy` for 15 minutes, and make CI wait on the reconciliation result - "merged" is not "deployed".

---

## Terraform

| Concept | Note |
| --- | --- |
| **State** | the map from configuration to real resource IDs. Its loss ≈ orphaning your estate |
| Backend | S3 + versioning + encryption + DynamoDB (or S3 native) locking |
| `plan` | a *proposal against the state as it was* - re-plan at apply time or use a saved plan |
| **Blast radius** | one state per environment per bounded component; a monolithic state = 40-minute applies and total risk |
| `import` / `moved` | adopt existing resources / rename without destroy-recreate |
| `terraform_remote_state` vs data source | remote state couples you to another component's internals; prefer published outputs or data lookups |
| `create_before_destroy` | avoids downtime on replacements; needs unique names |
| `prevent_destroy` | on databases and anything with data. Cheap insurance |
| `-target` | a **break-glass** tool; routine use means your state is badly split |

**Drift** = reality diverged from state (a console change, another controller, a cloud-side default). Detect with scheduled `plan` and alert on non-empty; decide per case whether to codify or revert.

**Never store secrets in Terraform outputs or variables you can avoid** - state is plaintext, including passwords a provider returns.

Module discipline: modules encode *your* opinions, not the provider's surface. A module that passes through every argument is a worse version of the resource. Version them, use them, do not build a DSL.

Policy as code (OPA/Conftest/Sentinel/Checkov) runs on the **plan JSON**, so it evaluates the actual proposed change. Highest-value rules: fail on any unexpected `destroy`, require tags, forbid public ingress `0.0.0.0/0` on sensitive ports, require encryption.

Stalled state recovery: confirm nothing is running → `force-unlock` → snapshot state → `import` orphans one at a time, re-planning after each → **never apply a plan containing unexpected destroys**.

---

## Observability

**Three signals, one identity.** Metrics (cheap, aggregate, alert on these) / logs (expensive, detailed, the *why*) / traces (relationships and latency attribution). Bind them with **trace ID in every log line** and **exemplars** on histograms.

**Cardinality is the cost function.** Series count = the product of every label's distinct values. Never label with: user ID, request ID, email, raw URL path, session ID, full error message.

```
http_requests_total{route,method,status}   # route TEMPLATED: /orders/{id}
                                           # NOT /orders/12345
```

One bad label can multiply a metric by a million and take down the metrics backend - which takes down alerting during the incident it caused. **Per-tenant limits are the containment control.**

Prometheus: pull-based, service discovery, `rate()` before aggregation (`sum(rate(x[5m]))`, never `rate(sum(...))`), histograms not summaries when you need to aggregate percentiles across pods. Long-term/HA needs Thanos or Mimir. Push only via the Pushgateway for batch jobs, and it is a trap for everything else.

**Percentiles do not average, and cannot be averaged across instances.** Compute them from histogram buckets. Your bucket boundaries decide your resolution - choose them around your SLO threshold.

OpenTelemetry: **API/SDK/Collector**, one instrumentation for all three signals, vendor-neutral. The **Collector** (agent DaemonSet + gateway tier) is where you enrich, redact, filter and **tail-sample** - and therefore where you control cost. Head sampling is cheap and drops the rare error; **tail sampling keeps every error and slow trace** at the price of buffering.

Retention tiers: high-resolution for hours, downsampled for months, and don't put debug logs in the expensive index.

### SLOs

**SLI** = a ratio of good events to valid events, measured **where the user is** (edge/client), not at the component. **SLO** = the target. **Error budget** = `1 - SLO`, and the whole point is that it makes reliability a *budget to spend*, not a value to maximize.

99.9 percent over 28 days ≈ **40 minutes** of budget. 99.99 ≈ 4 minutes - which means a single bad deploy exhausts it, so do not promise it without the engineering to back it.

**Multi-window multi-burn-rate alerting** is the only alerting on this list that is worth memorizing:

| Burn rate | Long window | Short window | Budget consumed | Action |
| --- | --- | --- | --- | --- |
| 14.4x | 1 h | 5 m | 2 percent | **page** |
| 6x | 6 h | 30 m | 5 percent | **page** |
| 3x | 1 d | 2 h | 10 percent | ticket |
| 1x | 3 d | 6 h | 10 percent | ticket |

The short window prevents alerting on an already-resolved burn; the long window prevents alerting on noise.

---

## Alerting and on-call

**Page on symptoms, ticket on causes.** "Checkout error rate exceeds budget burn" pages; "node memory at 85 percent" does not.

Every page must be: **urgent, actionable, and about a real user impact**. If any of the three fails, it is a ticket or a dashboard.

Target: **< 2 pages per shift**. Above that, the fix is the alerting, not the engineer. Track alert **actionability** (what fraction resulted in action) and delete the rest quarterly.

Alert storm control: **grouping** (by alertname+cluster+service), **inhibition** (a node-down alert suppresses its pods' alerts), and **severity routing**. A tier-1 SLO alert must route where it cannot be suppressed by infrastructure noise.

Incident roles: **Incident Commander** (decides, does not debug), **Ops/subject lead** (the only one making changes), **Comms**, **Scribe**. The IC's first three acts: declare severity, assign roles, state that all changes go through one person.

Severity is defined by **customer impact and required response**, not by how alarming the graph looks. Write the definitions before you need them.

**First five minutes**:
1. Is it real, and what is the customer impact?
2. **What changed?** - deploy, flag, config, migration, infrastructure change, traffic. Correlated change log first.
3. Stop the bleeding: roll back, flip the flag, shed load, add capacity. Restoration precedes diagnosis.
4. Is rollback *safe*? (migration/format = no)
5. Communicate before you are asked.

Postmortems: **blameless**, because the alternative buys you fewer reports rather than fewer errors. Action items need an owner, a date and a priority, or the document is a diary. **Human error is a starting point, never a root cause** - the question is why the system permitted it.

---

## Reliability

**Availability arithmetic**: 99.9 = 43 m/month, 99.99 = 4.3 m/month. Serial dependencies **multiply** (five 99.9 components in series ≈ 99.5). Redundancy only helps if failures are independent - and shared control planes, shared config and shared deploys make them correlated.

**RTO** = how long to recover. **RPO** = how much data you can lose. Both are business decisions; the architecture follows from them, and cost is roughly exponential in both.

| Pattern | RTO | Cost |
| --- | --- | --- |
| Backup/restore | hours-days | lowest |
| Pilot light | tens of minutes | low |
| Warm standby | minutes | medium |
| Active-active | ~zero | **> 2x**, plus a permanent design tax on every feature |

**A backup that has never been restored is not a backup.** Test restores on a schedule, measure the restore *time*, and verify the data. Backups must be immutable and out of the blast radius of the credentials that could delete them (ransomware and a bad script look identical).

Chaos engineering is a **hypothesis test in production with a blast-radius limit and an abort condition**, not "break things". Start in staging, start small, and stop when the hypothesis fails.

**Load testing must be against production-shaped data and topology** or it validates nothing. Test the failure modes: dependency slow (not down), partial degradation, cold cache, and recovery from saturation.

Metastable failure: the system stays broken after the trigger is removed because the *recovery work itself* sustains the load (retry storms, probe kill loops, thundering-herd cache fills). Defences: **jittered exponential backoff, retry budgets, circuit breakers, load shedding, request hedging with caution**.

Multi-region breaks your release process: canaries become regional, versions differ across regions for hours, migrations must be compatible with two versions in two regions, rollback gains a region dimension, and **the pipeline itself must survive losing a region** or you cannot deploy the fix.

---

## Security

**Shift left *and* shift right.** Pipeline checks (SAST, dependency, IaC, secrets, image scan) plus runtime enforcement (admission, policy, network, runtime detection). Pipeline checks are advisory unless enforced at admission.

| Gate | Fails the build on |
| --- | --- |
| Secret scanning + **push protection** | any credential, server-side, before it lands |
| Dependency scan | reachable + exploitable + exposed, not "critical" |
| IaC policy (plan JSON) | unexpected destroy, public ingress, missing encryption, missing tags |
| Image scan | fixable criticals in the final image layers |
| Signature/provenance verify | at **admission**, not just at build |

**OIDC federation kills the long-lived cloud key.** GitHub Actions requests a short-lived OIDC token; the cloud trusts the issuer and exchanges it for a role. **Pin the trust policy's `sub` claim** to `repo:org/name:environment:production` - a trust policy matching `repo:org/*` is a hole big enough to drive any repository through.

Pod-level: `runAsNonRoot`, `readOnlyRootFilesystem`, drop **all** capabilities, `allowPrivilegeEscalation: false`, seccomp `RuntimeDefault`. Enforce with **Pod Security Admission** (`restricted`) plus Kyverno/Gatekeeper for what PSA cannot express.

Admission control: validating (reject) and mutating (modify) webhooks. **`failurePolicy: Fail` means an unavailable webhook blocks all deployments** - including the deployment that would fix the webhook. Scope it with namespace selectors and exclude system namespaces.

Least privilege for humans: **no standing production write access**. Time-bounded, approved, audited break-glass instead. "The engineer deleted a namespace" is answered by "why did they have delete permission at 2 pm on a Tuesday".

Leaked credential response: **deactivate first, investigate second**. Then scope the permissions, hunt CloudTrail over the full exposure window for recon/persistence/exfiltration patterns, and only then clean up the repository - which is cleanup, not remediation.

---

## Cost

**Cost per unit of business value**, not total spend. Total spend rising while cost-per-transaction falls is a success, and you need the second number to say so.

Attribution first: **mandatory ownership tags** enforced by policy, per-team showback, anomaly detection by service, daily granularity. Without attribution every cost conversation is a guess.

| Lever | Typical yield |
| --- | --- |
| Right-size requests to actual usage (VPA recommendations) | large - most clusters request 2-3x what they use |
| Non-production off outside working hours | ~60-70 percent of non-prod |
| **Spot/Karpenter** for interruptible workloads | 60-90 percent of that compute |
| Savings Plans / Reserved on the stable baseline | 30-50 percent, **buy last**, after right-sizing |
| Observability pipeline filtering and sampling | often the fastest-growing line, and the least-owned |
| Delete orphans: volumes, snapshots, IPs, load balancers, old images | free money, recurring |

**Right-size before you commit.** Buying a reservation for waste locks in the waste for three years.

Kubernetes-specific waste: bin-packing failure from oversized requests, a DaemonSet's cost multiplied by node count, idle node headroom, cross-AZ traffic between pods (topology-aware routing), and **NAT gateway processing charges** for image pulls and telemetry egress (use VPC endpoints and a registry pull-through cache).

Spot safely: diversify across instance types and AZs, handle the 2-minute interruption notice, run PDBs, and never put the control-plane-critical or single-replica stateful workload on it.

---

## Platform engineering

**Standardize the contract, not the implementation.** Enforce at the boundary (signed artifact, deployment event, policy compliance); let teams reach it however they like.

The paved road must be **strictly easier than not using it**, or adoption fails and the mandate that follows produces malicious compliance.

**Escape hatches must exist, be composable layer by layer, and never require permission.** Requiring approval to deviate recreates the ticket queue you built the platform to remove.

The **anti-metric** that tells the truth: platform team ticket volume and queue time. Rising means self-service is not working, however good the portal looks.

Measure: time to first production deploy for a new service; paved-road adoption among *new* services; DORA per team; developer time spent on non-product work; escape-hatch usage by reason (this is your roadmap); time to apply an estate-wide change (this is your leverage).

Run it as a **product team** - roadmap, users, support SLO, changelog, and its own availability treated as tier-1 because a platform outage blocks every team.

---

## Numbers worth quoting

| | |
| --- | --- |
| Pre-merge feedback budget | **10 minutes**; above that, developers batch |
| Rollback budget | **< 5 minutes**, and it must be tested |
| Pages per on-call shift | **< 2**; above that, fix the alerting |
| 99.9 percent over 28 days | ~**40 minutes** of error budget |
| 99.99 percent over 28 days | ~4 minutes - one bad deploy |
| Burn-rate page thresholds | **14.4x/1h** and **6x/6h**, each with a short window |
| CFS quota period | **100 ms** - the throttling granularity behind p99 spikes |
| JVM heap in a container | `MaxRAMPercentage=75`, never a hardcoded `-Xmx` |
| Kubelet version skew | up to **3 minor** behind the API server, never ahead |
| Default `terminationGracePeriodSeconds` | 30 - usually too short; `preStop` sleep ~10 s |
| Deployment `progressDeadlineSeconds` | marks failure; **does not roll back** |
| Cluster request utilization | most clusters request **2-3x** actual usage |
| Spot discount | 60-90 percent; 2-minute interruption notice |
| Reserved/Savings Plan discount | 30-50 percent - buy **after** right-sizing |
| Serial availability | five 99.9 components in series ≈ **99.5** |
| Canary steps | 1 → 5 → 25 → 50 → 100, with automated abort at each |
| SLSA level that matters | **L3** - non-falsifiable provenance from an isolated builder |
| Action pinning | **commit SHA**, not tag; tags are mutable |
