# DevOps Interview Questions

Questions are numbered continuously (`Q1`, `Q2`, ...) so that [answers.md](answers.md) can reference them directly.

Difficulty legend:

- `[C]` Core - you must answer this instantly and correctly.
- `[D]` Deep - expected of a senior engineer, requires mechanism-level detail.
- `[T]` Tricky - designed to catch you out; the obvious answer is usually wrong.
- `[A]` Architect - no single right answer, judged on trade-off reasoning.

Each category opens with an **Assumed known** line pointing at the `01-java`, `02-spring` and `03-microservices` questions this material builds on. If those are shaky, go back before continuing.

The material is anchored on **Kubernetes/EKS, GitHub Actions, Argo CD, Terraform and Prometheus/OpenTelemetry**, with Jenkins, GitLab CI, Helm, Datadog and ECS contrasts called out wherever the mechanism genuinely differs. Name the tool you are describing; interviewers notice when you do.

---

## 1. Delivery pipeline design, versioning and artifacts

> Assumed known: `01-java` Q198 (pipeline stages) and `03-microservices` Q171, Q180 (deployment versus release, independent deployability).

1. `[C]` Define continuous integration, continuous delivery and continuous deployment precisely, and state what each one requires of the team rather than the tooling.
2. `[D]` Design the stage sequence for a Java microservice from commit to production and justify the order. What runs in parallel, what is a gate, and what is advisory?
3. `[T]` Your pipeline is green and takes 55 minutes. What is actually wrong with that, beyond the inconvenience?
4. `[D]` Build once, deploy many: what exactly must be identical across environments, and what is allowed to differ?
5. `[T]` A team rebuilds the artifact per environment "so each one gets the right config". Name three concrete failure modes this produces.
6. `[D]` Artifact versioning schemes - semantic versioning, calendar versioning, commit-SHA tagging. Which do you use for a library, for a service image, and why are they different answers?
7. `[D]` What is an immutable artifact, and how do you enforce immutability in a registry that allows tag overwrites?
8. `[D]` Snapshot versus release artifacts in Maven. What breaks when a snapshot reaches production, and how do you prevent it in the pipeline?
9. `[D]` Artifact promotion: describe promoting a single build through dev, staging and production without rebuilding, including how the registry and the deployment manifest track it.
10. `[D]` Retention and garbage collection for artifacts and images. What policy do you set, and which artifacts must never be deleted?
11. `[D]` Pipeline as code versus pipeline configured in a UI. Beyond reviewability, what does pipeline-as-code actually buy you?
12. `[T]` Explain why "the build works on my machine" is still possible with a containerized build, and what a reproducible build actually requires.
13. `[D]` Fail fast versus complete feedback. How do you order a pipeline so a developer learns the most in the first three minutes?
14. `[D]` Define lead time for change, deployment frequency, change failure rate and MTTR. How do you instrument each from data you already have?
15. `[T]` A team reports a 2 percent change failure rate and daily deploys, but engineers say releases are terrifying. What is the metric missing, and what would you measure instead?
16. `[A]` You inherit three teams with three completely different pipelines. Do you standardize, and how do you sequence it without stopping delivery?

---

## 2. Source control, branching and trunk-based development

> Assumed known: `01-java` Q201 (trunk-based versus GitFlow) and `03-microservices` Q182 (versioning a shared platform library).

17. `[C]` Contrast GitFlow, GitHub Flow and trunk-based development in terms of branch lifetime, merge conflict surface and release cadence.
18. `[D]` What does trunk-based development actually require to be safe? List the preconditions, not the practice.
19. `[T]` A team says "we can't do trunk-based, our features take three weeks". What is the real constraint, and what do you propose?
20. `[D]` Feature branches versus feature flags for incomplete work. Compare the cost of each and give the case where a branch is still correct.
21. `[D]` Merge commit, squash merge and rebase merge. What does each do to bisectability, revert-ability and the blame history?
22. `[D]` `git revert` versus `git reset` versus a forward fix in a shared branch. Which do you use to roll back a bad production change and why?
23. `[D]` How do you find a regression introduced somewhere in the last 300 commits? Describe the mechanism and what makes it fail.
24. `[D]` Monorepo versus polyrepo: compare dependency management, CI cost, atomic cross-service change and release independence.
25. `[T]` A monorepo team runs the full test suite on every commit and CI now takes 90 minutes. Explain the fix in terms of the build graph rather than more machines.
26. `[D]` Branch protection rules that matter: required checks, required reviewers, linear history, signed commits, and who is allowed to bypass. What is your minimum set?
27. `[D]` Conventional commits and automated release notes. What do you get beyond tidy history, and what does it enable in the pipeline?
28. `[D]` Managing shared libraries across services: versioned artifact, git submodule, or copy. Rank them for a 30-service estate.
29. `[T]` A shared library bumps a transitive dependency and eleven services break in production a week later. What was wrong with the process, not the library?
30. `[A]` Make the case for and against a monorepo for a 40-engineer, 25-service Java estate, and state your recommendation with the conditions that would change it.

---

## 3. CI mechanics - runners, caching, matrices and monorepo pipelines

> Assumed known: `01-java` Q198 (pipeline stages) and `03-microservices` Q183 (how many pre-production environments you actually need).

31. `[C]` Walk through what happens when a GitHub Actions workflow triggers: event, workflow, job, step, runner. Where does isolation begin and end?
32. `[D]` GitHub-hosted versus self-hosted runners. Compare cost, security posture, network access and cold-start, and say when you would run self-hosted.
33. `[T]` A self-hosted runner is reused between jobs. Name four ways this leaks state or credentials, and what you do about it.
34. `[D]` Ephemeral runners on Kubernetes (Actions Runner Controller) - how does autoscaling work, and what is the trade-off against a warm pool?
35. `[D]` Caching in CI: what should be cached for a Maven build, a Gradle build and a Docker build, and what is the correct cache key for each?
36. `[T]` A dependency cache makes the build faster but occasionally produces a wrong result. Give three mechanisms by which a cache can poison a build.
37. `[D]` Gradle build cache versus dependency cache versus the Gradle daemon. Which one gives the biggest win on a warm CI runner, and why?
38. `[D]` Matrix builds: what do you actually parallelize across, and when does a matrix cost more than it saves?
39. `[D]` Test parallelization and flaky tests. How do you detect a flaky test automatically, and what is your policy when you find one?
40. `[T]` Quarantining flaky tests reduced the failure rate to zero. Why is that a warning sign, and what do you put in place?
41. `[D]` Change detection in a monorepo: how do you compute the affected set correctly, including transitive dependencies and shared config?
42. `[T]` A path-filter-based monorepo pipeline skipped the test that would have caught the bug. What is wrong with path filters, and what replaces them?
43. `[D]` Where do you enforce code quality gates - coverage, static analysis, dependency policy - and what do you do when the gate blocks an urgent fix?
44. `[D]` Reusable workflows and composite actions in GitHub Actions. How do you version a shared workflow across 30 repositories without breaking them all at once?
45. `[D]` Concurrency control: describe the mechanism you use to stop two deployments of the same service racing, and the failure mode if you get it wrong.
46. `[D]` Pipeline observability: what do you instrument about the pipeline itself, and which signal tells you a pipeline is degrading before developers complain?
47. `[A]` CI cost has tripled year on year. Walk through how you would attribute the spend and what you would change first.

---

## 4. Build and dependency supply chain

> Assumed known: `03-microservices` Q169 (SBOM, signed images, admission control, a CVE in a base image used by 40 services).

48. `[C]` What is a software bill of materials, what formats exist, and at which pipeline stage should it be generated?
49. `[D]` SBOM generated from source versus generated from the built image. What does each one miss?
50. `[D]` Dependency confusion and typosquatting attacks. Explain the mechanism and the registry configuration that prevents them.
51. `[T]` Your build pulls from Maven Central through a proxy. An attacker publishes a higher version of an internal artifact ID publicly. What happens, and what setting decides it?
52. `[D]` Lock files and reproducible dependency resolution in Maven and Gradle. What does each ecosystem actually guarantee?
53. `[D]` Transitive dependency conflict resolution: Maven's nearest-wins versus Gradle's highest-wins. Which surprises people, and how do you diagnose the resolved graph?
54. `[D]` Vulnerability scanning: SCA versus SAST versus DAST versus container scanning. What does each catch that the others cannot?
55. `[T]` A scanner reports 240 critical CVEs in your base image. How do you triage this without either ignoring it or stopping delivery?
56. `[D]` Reachability analysis and the VEX document. Why does "vulnerable dependency present" not mean "exploitable", and how do you record that decision?
57. `[D]` Automated dependency updates (Dependabot, Renovate). Design the policy: what auto-merges, what needs review, and what is batched?
58. `[D]` Artifact signing with Sigstore/cosign: what is signed, where is the signature stored, and what does keyless signing actually attest?
59. `[D]` SLSA build levels. What does each level require of the build platform, and which level is realistically achievable on hosted CI?
60. `[D]` Provenance attestation: what does an in-toto attestation contain, and how does the deployment side verify it?
61. `[T]` You verify image signatures at deploy time. Explain the gap that still exists between the signed image and the running container.
62. `[D]` Internal artifact repository (Nexus, Artifactory, CodeArtifact): what problems does it solve beyond caching, and what new single point of failure does it introduce?
63. `[A]` Design a supply chain security posture for a regulated Java estate. State what you would implement in the first quarter and what you would defer.

---

## 5. Containers and image engineering

> Assumed known: `01-java` Q202-203 (Docker image optimization for Java, why the container used more memory than `-Xmx`).

64. `[C]` What is a container, in kernel terms? Name the primitives and state what a container is not.
65. `[D]` Namespaces and cgroups: which namespace provides which isolation, and what does cgroup v2 change over v1 for memory and CPU?
66. `[D]` OCI image format: manifest, config, layers, digest. What exactly does a tag point to, and why is the digest the only safe reference?
67. `[D]` Layer caching in a Dockerfile: give the ordering rules, and show the layout for a Maven-built Spring Boot application.
68. `[T]` Adding a single line to `pom.xml` invalidates the whole build cache and the image takes eight minutes. Explain the mechanism and the fix.
69. `[D]` Multi-stage builds: what belongs in each stage, and how do you keep the build tooling out of the final image?
70. `[D]` Spring Boot layered JARs and `layertools`. What layers does it produce, and what does that do to registry push size on a typical code change?
71. `[D]` Base image selection: full JDK, JRE, Alpine, distroless, scratch. Compare attack surface, debuggability and the glibc/musl issue for the JVM.
72. `[T]` A service works on Debian and crashes with a `SIGSEGV` on Alpine. What is the most likely cause, and what else changes on musl?
73. `[D]` JVM ergonomics in a container: what does the JVM read to size the heap, and what happens if you set `-Xmx` equal to the container memory limit?
74. `[D]` `MaxRAMPercentage`, `InitialRAMPercentage` and container awareness. What is your default, and how do you account for non-heap memory?
75. `[T]` A pod is OOMKilled but the JVM heap graph shows 40 percent usage. Walk through where the memory actually went.
76. `[D]` CPU limits and the JVM: how does CFS throttling interact with the garbage collector and thread pool sizing? What is `availableProcessors` reporting?
77. `[D]` Image size reduction techniques ranked by actual impact. Where does the real weight in a Java image come from?
78. `[D]` Class Data Sharing, AppCDS and Class Data Sharing archives in an image. What startup improvement should you expect, and what invalidates the archive?
79. `[D]` GraalVM native image for a Spring Boot service: what do you gain, what do you lose, and what breaks at build time?
80. `[A]` A team wants to move from JVM containers to native images across the estate to cut cold-start cost. Evaluate the proposal.

---

## 6. Kubernetes core - scheduler, controllers, probes and resources

> Assumed known: `01-java` Q204-205 (probes, requests versus limits) and `03-microservices` Q116-118 (health checks, what a readiness check must not do, graceful shutdown ordering).

81. `[C]` Describe the control plane components and what each one is responsible for. What happens to running workloads if the API server goes down?
82. `[D]` The reconciliation loop: explain declarative desired state, the controller pattern, and why Kubernetes is level-triggered rather than edge-triggered.
83. `[D]` Walk through everything that happens between `kubectl apply` of a Deployment and a container running on a node.
84. `[D]` Deployment, ReplicaSet and Pod: which controller owns which decision, and what does a rolling update actually create and delete?
85. `[D]` `maxSurge` and `maxUnavailable`: give the arithmetic for a 10-replica Deployment, and the setting you use for a service that must not lose capacity.
86. `[T]` A rolling update completes successfully and the service is broken. Name three ways Kubernetes reports success on a broken rollout.
87. `[D]` Readiness, liveness and startup probes: state precisely what each one does when it fails, and the failure you cause by conflating readiness and liveness.
88. `[T]` A liveness probe on a slow-starting JVM service causes a restart loop under load. Explain the feedback loop and give two fixes.
89. `[D]` Pod lifecycle and graceful shutdown: describe the exact sequence from `DELETE` to container exit, including endpoint removal, `preStop` and `terminationGracePeriodSeconds`.
90. `[T]` A pod is terminated and clients see connection resets despite a graceful shutdown handler. Explain the race and how you close it.
91. `[D]` Requests versus limits, and the three QoS classes. Which one gets evicted first, and what does that mean for a Java service?
92. `[T]` Setting a CPU limit made p99 latency worse while CPU utilization dropped. Explain what happened.
93. `[D]` Do you set CPU limits? Give your position, the mechanism behind it, and the case where you would change it.
94. `[D]` Node pressure eviction versus OOMKill versus preemption. Which is the kubelet, which is the kernel, and how do you tell from the pod status?
95. `[D]` StatefulSet versus Deployment: what guarantees does a StatefulSet add, and what does it cost during a rolling update?
96. `[D]` DaemonSet, Job and CronJob. What are the concurrency and failure-handling settings you must set on a CronJob, and what is the default trap?
97. `[D]` Pod scheduling controls: node selectors, affinity, anti-affinity, taints and tolerations, topology spread constraints. Which do you reach for to survive an AZ loss?
98. `[T]` A pod is `Pending` and the cluster has plenty of free CPU. List the causes, in the order you would check them.
99. `[A]` A team asks whether they should run on Kubernetes at all for six low-traffic services. Give your reasoning and the alternatives.

---

## 7. Kubernetes networking, storage and cluster operations

> Assumed known: `03-microservices` Q121-136 (discovery, load balancing, gateway, service mesh) and `01-java` Q194 (auto-scaling and why CPU is often the wrong signal).

100. `[C]` Explain the Kubernetes networking model and its flat requirement. What must a CNI plugin provide?
101. `[D]` How does a `ClusterIP` Service actually route traffic? Contrast kube-proxy in iptables mode with IPVS and eBPF-based dataplanes.
102. `[D]` Service, Endpoints and EndpointSlice. Why was EndpointSlice introduced, and what breaks at scale without it?
103. `[T]` A pod is removed from a Service but keeps receiving traffic for several seconds. Explain the full propagation path and every place it can lag.
104. `[D]` Headless services and DNS: when do you need one, and what does the DNS response look like?
105. `[D]` CoreDNS at scale: `ndots`, search domains, and why a single external lookup can cost five DNS queries. What do you configure?
106. `[D]` Ingress versus Gateway API versus a service mesh. What problem does each solve, and what is the migration reason to move from Ingress to Gateway API?
107. `[D]` NetworkPolicy: default-deny, ingress versus egress, and what NetworkPolicy cannot express. What enforces it?
108. `[D]` Service mesh data plane: what does the sidecar actually intercept, and what latency and resource overhead should you budget? What does ambient/sidecarless change?
109. `[D]` mTLS in a mesh: where do the certificates come from, what is the rotation period, and what happens during a control plane outage?
110. `[D]` PersistentVolume, PersistentVolumeClaim, StorageClass and dynamic provisioning. What do `ReadWriteOnce` and `ReadWriteMany` mean in practice on a cloud provider?
111. `[T]` A StatefulSet pod is stuck in `ContainerCreating` after a node failure. Explain the volume attachment mechanism that causes this and how long it takes to clear.
112. `[D]` Cluster autoscaler versus Karpenter versus a fixed node group. Compare provisioning latency, bin-packing and cost behavior.
113. `[D]` Horizontal Pod Autoscaler: what metric do you scale on for a JVM service, what is the stabilization window for, and why is CPU often the wrong signal?
114. `[T]` HPA and cluster autoscaler are both enabled and the service still drops requests during a traffic spike. Walk through the timing chain.
115. `[D]` Vertical Pod Autoscaler and KEDA. When do you use each, and what conflicts with HPA?
116. `[D]` Cluster upgrades: describe a zero-downtime EKS control plane and node group upgrade, including PodDisruptionBudgets and what makes a drain hang.
117. `[A]` Design the cluster topology for a 60-service estate across three environments. One cluster or many, and how do you carve namespaces, node pools and blast radius?

---

## 8. Configuration and secrets management

> Assumed known: `02-spring` Q27-42 (the `ConfigData` API, `spring.config.import`, relaxed binding, keeping secrets out of `/actuator/env`) and `03-microservices` Q184-185 (where configuration belongs, the config change that caused a bigger outage than any code change).

118. `[C]` The twelve-factor config principle: what belongs in config, what belongs in the artifact, and where is the boundary genuinely ambiguous?
119. `[D]` ConfigMap versus Secret in Kubernetes. What is the actual difference, and what does "Secrets are not encrypted" mean concretely?
120. `[D]` Environment variables versus mounted files for configuration. Compare update behavior, leakage risk and application support.
121. `[T]` You update a ConfigMap and the application does not pick up the change. Explain both mechanisms - env var and volume mount - and the propagation delay.
122. `[D]` Configuration hot reload versus rolling restart. Which do you default to, and what makes hot reload dangerous?
123. `[D]` Secret storage options: sealed secrets, External Secrets Operator, CSI Secrets Store driver, Vault agent injection. Compare where the secret lives at rest and in the pod.
124. `[D]` Secrets encryption at rest in etcd: KMS provider, envelope encryption, and what an etcd backup contains without it.
125. `[D]` Secret rotation without downtime: describe the sequence for a database credential used by 12 running pods.
126. `[T]` A secret was committed to git six months ago and has since been removed from the branch. What is your response, in order?
127. `[D]` Dynamic secrets from Vault versus static rotated secrets. What does short-lived credential issuance actually change about the blast radius?
128. `[D]` Workload identity: IRSA on EKS, and how a pod gets AWS credentials without a stored key. Walk through the token exchange.
129. `[D]` Configuration drift between environments. How do you detect it, and what structure prevents "it works in staging" as a class of problem?
130. `[D]` Feature flags as configuration: where does the flag state live, what is the failure mode when the flag service is unreachable, and what is your default?
131. `[A]` Design the configuration and secrets strategy for a 25-service estate spanning EKS and a legacy VM fleet.

---

## 9. Deployment and release strategies

> Assumed known: `03-microservices` Q171-186 (deployment versus release, canary analysis, feature flag taxonomy, expand-migrate-contract, independent deployability).

132. `[C]` Contrast recreate, rolling, blue/green and canary deployments in terms of capacity requirement, rollback speed and risk exposure.
133. `[D]` Separate deploy from release. What does that mean mechanically, and what does it change about the risk of a Friday deploy?
134. `[D]` Blue/green on Kubernetes: describe the implementation, the cutover mechanism, and what you do about in-flight requests, database state and caches.
135. `[T]` A blue/green cutover succeeded and rollback failed. Give three reasons rollback is not simply the reverse of the cutover.
136. `[D]` Canary analysis: what signals do you compare, over what window, and how do you avoid promoting on a statistically meaningless sample?
137. `[D]` Argo Rollouts or Flagger: describe the controller's state machine and how it interacts with the mesh or ingress for traffic weighting.
138. `[T]` A canary at 5 percent traffic shows a healthy error rate, then breaks at 100 percent. Name four reasons a canary can pass and the full rollout still fail.
139. `[D]` Progressive delivery by cohort rather than by traffic percentage. When is that the correct choice, and what does it require of the router?
140. `[D]` Feature flags: short-lived release flags versus long-lived operational flags versus experiment flags. What is your lifecycle policy for each?
141. `[T]` A team has 340 feature flags and nobody knows which are safe to remove. How did this happen, and how do you dig out?
142. `[D]` Database migrations in a zero-downtime deploy: the expand-contract sequence, and what makes a migration non-rollbackable.
143. `[T]` A rollback of the application succeeded, but the schema migration had already run. What is your position on rolling back migrations, and what does that imply for how you write them?
144. `[D]` Backward and forward compatibility of API and message contracts during a rolling deploy. What must be true for the two versions to coexist?
145. `[D]` Deployment windows, change freezes and approval gates. Which of these actually reduce risk, and which mostly move it?
146. `[D]` Automated rollback: what triggers it, how fast can it be, and what is the danger of a fully automatic rollback?
147. `[D]` Rollback for a stateful service or one with a consumer group offset. What is different, and what do you plan in advance?
148. `[A]` A business unit demands a two-week manual UAT gate before every production release. Make the case for change and describe the transition you would actually run.

---

## 10. GitOps and Argo CD

> Assumed known: Category 9 above, and `03-microservices` Q180, Q183 (independent deployability, environment strategy).

149. `[C]` Define GitOps by its properties, not its tools. What does it change compared to a pipeline that runs `kubectl apply`?
150. `[D]` Push-based versus pull-based deployment. What security property does pull-based buy you, and what does it cost operationally?
151. `[D]` Argo CD architecture: application controller, repo server, API server. Where does reconciliation happen and what does it compare?
152. `[D]` Sync waves, hooks and the health assessment. How does Argo CD decide an Application is `Healthy` rather than just `Synced`?
153. `[T]` An Argo CD Application shows `Synced` and `Healthy` while the service is returning 500s. What does Argo CD actually know, and what does it not?
154. `[D]` Drift detection and self-heal. When would you deliberately leave self-heal off?
155. `[T]` An operator mutates a resource that Argo CD manages, producing a permanent sync loop. Explain the mechanism and the three ways to resolve it.
156. `[D]` Repository structure for GitOps: one repo or many, and how do you separate application source from deployment manifests? What does each choice do to the review flow?
157. `[D]` Environment promotion in GitOps without copy-pasted YAML. Compare Kustomize overlays, Helm values hierarchies and Argo CD ApplicationSets.
158. `[D]` Helm versus Kustomize: templating versus patching. What does each get wrong, and can you defensibly use both?
159. `[D]` Image updates in GitOps: how does a new image tag reach the manifest repository, and what does the write-back create that you must plan for?
160. `[D]` Secrets in a GitOps repository. Give two workable approaches and state exactly what is stored in git in each.
161. `[D]` Multi-cluster Argo CD: hub-and-spoke versus per-cluster instances. Compare blast radius, credential handling and scale limits.
162. `[A]` A team wants GitOps but has a compliance requirement for a human approval gate on production. Design a flow that satisfies both.

---

## 11. Infrastructure as Code and Terraform

> Assumed known: `01-java` Q206 (Terraform versus CloudFormation versus CDK, state management and drift) and `03-microservices` Q183 (environment strategy).

163. `[C]` Declarative versus imperative infrastructure. What does a desired-state tool give you that a provisioning script does not?
164. `[D]` Terraform state: what is in it, why is it required, and what breaks if two runs use it concurrently?
165. `[D]` Remote state with locking on S3 and DynamoDB. Describe the lock mechanism and what you do when a lock is stuck.
166. `[T]` State drifted because someone changed a resource in the console. Walk through your options, including what `terraform import` and `-refresh-only` actually do.
167. `[D]` State file blast radius: how do you split state, and what is the trade-off between one big state and one state per component?
168. `[D]` `count` versus `for_each`. Why does removing an item from the middle of a `count` list destroy resources, and what does `for_each` change?
169. `[T]` A refactor that only renamed modules produced a plan destroying 40 resources. Explain the mechanism and both remedies.
170. `[D]` Module design: what makes a Terraform module reusable, what should never be hardcoded, and how do you version and consume modules across teams?
171. `[D]` Terraform workspaces versus directory-per-environment. Which do you use for prod isolation and why?
172. `[D]` Data sources and remote state outputs for cross-stack references. What coupling does each create, and what is the alternative?
173. `[D]` `terraform plan` in CI: how do you review a plan safely, where do you store it, and what makes an apply diverge from the reviewed plan?
174. `[D]` Provider version pinning and the dependency lock file. What breaks in six months if you do not pin?
175. `[D]` Policy as code: OPA/Rego, Sentinel, Checkov. Where in the pipeline does the policy check belong, and what do you do about existing violations?
176. `[T]` A Terraform apply timed out mid-way. Describe the state of the world and your recovery procedure.
177. `[D]` Terraform versus CloudFormation/CDK versus Pulumi versus Crossplane. What genuinely distinguishes them, beyond language preference?
178. `[D]` Managing Kubernetes resources: Terraform's Kubernetes provider versus GitOps. Where do you draw the line between the two?
179. `[D]` Testing infrastructure code: what is actually testable, and what does a plan-time test catch that an apply-time test does not?
180. `[A]` You inherit 4,000 lines of Terraform in one root module with no tests and manual applies from laptops. Sequence the first 90 days.

---

## 12. Observability - metrics, logs, traces and SLOs

> Assumed known: `01-java` Q207-208 (what you instrument by default, SLI/SLO/error budget) and `03-microservices` Q137-154 (OpenTelemetry, trace context, sampling, cardinality, burn-rate alerting, observability cost).

181. `[C]` Monitoring versus observability. Give a definition that is operationally useful rather than a slogan.
182. `[D]` The three signals plus profiles and events. For a given latency incident, state which signal you reach for at each step.
183. `[D]` Prometheus data model: metric name, labels, samples. What is a time series, and what does cardinality actually cost in memory and query time?
184. `[T]` Someone adds a `user_id` label to a metric. Walk through exactly what happens to Prometheus over the next hour.
185. `[D]` Counter, gauge, histogram and summary. When is a summary wrong, and why can you not average percentiles?
186. `[D]` Histogram buckets: how do you choose them, what does `histogram_quantile` actually compute, and what error does it carry? What do native histograms change?
187. `[D]` Pull versus push scraping. What does the pull model give you operationally, and how do you handle short-lived jobs and serverless?
188. `[D]` Prometheus at scale: federation, remote write, Thanos and Mimir. What problem does each solve, and in what order do you hit them?
189. `[D]` Recording rules and query cost. When do you materialize a query, and what is the trap with recording rules over a rate?
190. `[T]` `rate()` over a counter that resets, and a `rate()` window shorter than the scrape interval. What does Prometheus return in each case?
191. `[D]` Structured logging: what fields are mandatory in every log line, and what should never be logged?
192. `[D]` Log levels in production, sampling, and the cost curve. How do you get debug detail for one request without turning on debug globally?
193. `[T]` A log pipeline drops lines under load and nobody notices for weeks. What do you instrument to catch this?
194. `[D]` OpenTelemetry: SDK, API, Collector, and the semantic conventions. What does the Collector do that an agent in the process cannot?
195. `[D]` Trace context propagation across HTTP, messaging and a thread pool. Where does context usually get lost in a Java service?
196. `[D]` Head-based versus tail-based sampling. What does tail-based buy you, what does it cost, and where does it run?
197. `[D]` Exemplars and correlating a metric spike to a specific trace. What is required end to end for this to work?
198. `[D]` Define SLI, SLO, SLA and error budget. Write a good availability SLI for a request-driven service and say why the naive one is wrong.
199. `[T]` A service reports 99.99 percent availability and users are complaining. Give four reasons the number can be true and useless.
200. `[A]` Design the observability strategy for a 40-service estate with a fixed budget. What do you keep, what do you sample, and what do you drop?

---

## 13. Alerting, on-call and incident response

> Assumed known: `01-java` Q209-210 (what a good alert looks like, blameless postmortems) and `03-microservices` Q150-151 (error budget arithmetic, green dashboards during an outage), plus Category 12 above.

201. `[C]` What makes a good alert? Give the criteria, and the test you apply before adding one.
202. `[D]` Symptom-based versus cause-based alerting. Give the small set of symptom alerts you would put on any request-driven service.
203. `[D]` The four golden signals and the RED and USE methods. When does each apply, and how do they overlap?
204. `[D]` Multi-window multi-burn-rate alerting on an error budget. Give the windows and thresholds, and explain what each window catches.
205. `[T]` An alert fires every night at 02:00 and is always resolved by 02:10. What is the correct response, and what is the wrong one?
206. `[D]` Alert fatigue: how do you measure it, and what is your policy for an alert that has never once required action?
207. `[D]` Alertmanager grouping, inhibition, silencing and routing. Design the rules that turn a cluster-wide failure into one page rather than 200.
208. `[D]` Paging versus ticketing versus dashboard-only. What is your rule for which severity goes where, and who decides?
209. `[D]` On-call rotation design: size, handover, follow-the-sun, and compensation. What makes a rotation sustainable at 19 people versus 5?
210. `[D]` Incident command: the roles, who declares an incident, and why the person fixing it should not be the one communicating.
211. `[D]` Severity definitions. Write SEV1 to SEV3 in terms a non-engineer can apply at 03:00.
212. `[T]` During an incident, two engineers apply conflicting fixes simultaneously. What process failure allowed this, and what prevents it?
213. `[D]` Blameless postmortems: what makes them work, what makes them theater, and how do you track the actions to completion?
214. `[D]` Runbooks: what belongs in one, what makes them rot, and how do you keep them accurate?
215. `[A]` Your team has a 4 am page three nights a week and morale is collapsing. What do you do in the first two weeks, and what in the first quarter?

---

## 14. Reliability engineering - capacity, chaos, backup and DR

> Assumed known: `03-microservices` Q101-120 (timeouts, retries, circuit breakers, metastable failure, chaos engineering, error budget policy) and `01-java` Q195 (multi-region active-active).

216. `[C]` Availability targets: translate 99.9, 99.95 and 99.99 percent into error budget minutes per month, and state what each implies operationally.
217. `[D]` How do dependency availabilities compose? Compute the availability of a service with five sequential dependencies at 99.9 percent each, and say what changes it.
218. `[D]` Capacity planning: how do you size a service from a traffic forecast, and what headroom do you keep for failover?
219. `[D]` Load testing: smoke, load, stress, soak and spike. What does a soak test catch in a JVM service that a load test never will?
220. `[T]` A load test passed at 3x expected traffic and the service fell over at 1.2x in production. Give five reasons the test lied.
221. `[D]` Performance testing in the pipeline: what can you assert automatically without a flaky gate?
222. `[D]` Chaos engineering: the steady-state hypothesis, blast radius control, and what you must have in place before your first experiment.
223. `[D]` Game days and failure injection. What failures do you inject first for a Kubernetes-hosted estate, and what do you expect to learn?
224. `[D]` Define RPO and RTO, and explain how each one drives a different part of the architecture.
225. `[T]` Backups have run successfully every night for two years. Why is that not evidence of anything, and what is?
226. `[D]` Backup strategy for a Kubernetes estate: what is actually stateful, and what does a cluster backup (Velero, etcd snapshot) include and exclude?
227. `[D]` DR patterns: backup-restore, pilot light, warm standby, active-active. Give the cost and RTO of each and how you choose.
228. `[D]` Multi-region failover: what makes it hard beyond replication? Cover DNS, state, quorum and the decision to fail over.
229. `[T]` A failover drill worked, and the real failover failed. Name four asymmetries between a drill and a real event.
230. `[D]` Graceful degradation: what does a service do when a non-critical dependency is down, and how do you make that the default rather than an afterthought?
231. `[A]` The business asks for 99.99 percent availability. Walk through the conversation, the cost implications and what you would actually commit to.

---

## 15. Pipeline and runtime security

> Assumed known: `02-spring` Categories 8-9 (filter chain, JWT, OAuth2), `03-microservices` Q155-170 (service-to-service authentication, workload identity, secrets distribution, supply chain) and Category 4 above.

232. `[C]` Shift-left security: what does it actually mean in pipeline terms, and what is the failure mode of taking it too literally?
233. `[D]` Secret scanning: pre-commit, server-side and historical scanning. What does each catch, and why do you need all three?
234. `[D]` OIDC federation from GitHub Actions to AWS. Walk through the token exchange and explain why this is better than a stored access key.
235. `[T]` A workflow with OIDC access to production is triggered by `pull_request_target`. Explain the vulnerability precisely.
236. `[D]` Least privilege for a CI pipeline: what permissions does a deploy job actually need, and how do you scope them per environment?
237. `[D]` Third-party GitHub Actions: what is the risk, and what is your policy for pinning, vetting and allow-listing?
238. `[D]` Container image scanning in the pipeline versus in the registry versus at admission. What does each stage catch that the others miss?
239. `[D]` Admission control: validating versus mutating webhooks, and Pod Security Admission versus OPA Gatekeeper versus Kyverno. What do you enforce by default?
240. `[D]` Pod security: `runAsNonRoot`, read-only root filesystem, dropped capabilities, seccomp profiles. Which of these break a typical Java service, and how do you fix it?
241. `[T]` A container runs as root inside the pod. What can it actually do, and what changes if `hostPID` or a `hostPath` mount is present?
242. `[D]` Kubernetes RBAC: Role versus ClusterRole, and the specific verbs that are equivalent to cluster admin. What do you never grant?
243. `[D]` Runtime security: what does eBPF-based detection (Falco, Tetragon) see that image scanning cannot?
244. `[D]` Audit logging in Kubernetes and in the CI system. What do you retain, and what question must the log be able to answer?
245. `[T]` An attacker compromises a build agent. Enumerate what they now have access to, and which controls limit the damage.
246. `[D]` Compliance as code: how do you produce evidence for an auditor from the pipeline rather than a spreadsheet?
247. `[D]` Separation of duties in an automated pipeline. How do you satisfy the control when a machine performs the deploy?
248. `[A]` Design the security controls for a pipeline handling regulated data, from commit to running pod, and state which controls you would fight to keep if asked to cut half.

---

## 16. Cost, FinOps and platform efficiency

> Assumed known: `01-java` Q196 (the AWS bill that jumped 40 percent) and Category 7 above (autoscaling and node provisioning).

249. `[C]` Where does cloud spend actually go in a Kubernetes estate? Give the usual ranking and the item teams consistently forget.
250. `[D]` Cost attribution without chargeback theater: how do you attribute shared cluster cost to teams, and what is the unit you report?
251. `[D]` Requests versus actual usage: how do you measure the gap, and what is a realistic target utilization for a production node pool?
252. `[T]` A team reduced pod CPU requests to cut cost and latency got worse. Explain the two mechanisms at play.
253. `[D]` Spot and Graviton for stateless workloads: what is required in the application and in the cluster to use them safely?
254. `[D]` Reserved capacity, savings plans and on-demand. How do you decide the commitment level with an uncertain roadmap?
255. `[D]` Right-sizing a JVM service: what data do you need, and how do you avoid the trap of sizing on average utilization?
256. `[D]` Data transfer and observability costs. Why do these grow super-linearly with service count, and what do you do about it?
257. `[D]` Non-production spend: what do you shut down, what do you shrink, and what must stay production-shaped?
258. `[T]` Cost dropped 30 percent after an optimization and incident rate doubled. What was likely traded away?
259. `[D]` Efficiency as an SLO: how would you set a cost-per-request target and make it visible without turning it into a stick?
260. `[A]` The CFO asks for a 25 percent cloud cost reduction in two quarters. Build the plan and say what you would refuse to cut.

---

## 17. Platform engineering, design exercises and leadership

> Assumed known: everything above, plus `03-microservices` Category 15 (leadership and organizational) and `04-system-design` Category 15 (design walkthroughs).

261. `[A]` Design a complete CI/CD platform for a 200-engineer, 60-service Java organization, from commit to production, covering build, artifacts, deployment, rollback and observability.
262. `[A]` Design a zero-downtime migration of 25 services from EC2 with Jenkins-and-Ansible deploys onto EKS with GitOps, without a big-bang cutover.
263. `[A]` Design the observability and SLO platform for that estate: what is standardized, what is per-team, and how do you drive adoption without a mandate?
264. `[A]` Design a multi-region active-active deployment and its release process. What breaks about your normal pipeline when there are two live regions?
265. `[A]` Design an internal developer platform: what is the paved road, what is the escape hatch, and how do you know the platform is working?
266. Tell me about a production incident you led. What was the failure, what did you do, and what changed permanently afterwards.
267. Describe a delivery process you changed across teams you did not own. How did you get adoption?
268. Tell me about a time you reduced deployment risk with a measurable result.
269. Describe a technical decision on infrastructure or tooling that you got wrong. How did you find out, and what did you do?
270. How do you decide between building platform capability in-house and buying it? Give a real decision you made and what you would do differently.
