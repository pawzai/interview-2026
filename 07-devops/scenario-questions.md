# Scenario Questions

Delivery and production incidents, platform design exercises and leadership situations.

Every scenario uses **CIDER**, defined in [../01-java/README.md](../01-java/README.md):

- **Clarify** - what you ask before answering. Never diagnose or design in silence.
- **Isolate** - narrow the failure domain or the core requirement.
- **Decide** - commit to an approach and name the trade-off.
- **Execute** - the concrete steps.
- **Reflect** - what you monitor, prevent, or would do differently.

Read the scenario, answer out loud for five minutes, then compare. The model responses are longer than you should speak - use them as the map, not the script. References like (Q87) point at [answers.md](answers.md).

---

## Part A - Production incidents

### S1. The rollout said success and the service is down

> A routine deploy of the orders service completed at 14:02. Argo CD shows `Synced` and `Healthy`. The Deployment shows 12 of 12 replicas updated and available. Customer support says checkout has been failing since 14:03. The team is looking at you.

**Clarify.** What is the error - 5xx from the service, or a downstream failure? Is it all requests or a subset? What exactly was in the release: code only, or config, schema or a dependency bump? Did anything else deploy in that window? What does the readiness probe actually check? Do we have the previous image digest?

**Isolate.** Kubernetes and Argo CD both report success against their own criteria, and neither criterion is "the service works" (Q86, Q153). Argo CD knows the live objects match git; the Deployment knows the pods pass their readiness probes. So the failure is in the gap between "the process is running" and "the service is correct". Three families:

1. **The readiness probe is not measuring anything meaningful** - a probe on a static endpoint that returns 200 whatever the state of the application.
2. **The configuration is wrong but syntactically valid** - a ConfigMap pointing at the wrong endpoint, a missing secret key, a flag defaulted the wrong way. Argo CD deploys it faithfully and reports success.
3. **The change is correct in isolation and wrong in context** - a contract break with a caller, a migration that has not run, a downstream that does not speak the new version.

**Decide.** Restore service first, diagnose second. The fastest restoration is redeploying the previous image digest, which exists, is verified, and takes one rollout (Q22). I do that before understanding the cause, unless the release included a migration - in which case I check that first, because rollback may be unsafe (Q143).

**Execute.**

1. Confirm the impact and declare a SEV (Q211), appoint an IC, and announce that I am the only one making changes (Q212).
2. Check whether the release included a schema migration or a data-format change. If yes, rollback is off the table and I go to a forward fix or a flag.
3. If not: `kubectl rollout undo` or revert the promotion commit in the GitOps repository, and watch the error rate.
4. While that rolls: pull a failing request's trace and its logs by trace ID (Q182). That usually names the cause within a minute.
5. Verify recovery on the customer-facing signal, not on pod status.
6. Then diagnose properly with the pressure off.

**Reflect.** Three systemic fixes. **The readiness probe must exercise the real request path**, or it is decoration. **The rollout must be gated on service-level signals** - a canary controller comparing error rate and latency against a concurrent baseline, with automatic abort (Q136, Q137), so a broken release never reaches 100 percent. And **the deployment must emit an event correlated to the SHA**, so the first question at 14:03 is answered by a dashboard rather than by asking around.

> *Hook: a rollout that reported success while the service was broken, and the gate you added.*

---

### S2. The liveness probe is killing the fleet

> Traffic rose 40 percent above normal at 10:15. By 10:22 the service is effectively down. Pods are restarting continuously - restart counts in the hundreds. CPU on the nodes is high but not saturated. Removing load would fix it, but the traffic is real customers.

**Clarify.** What is the restart reason - `OOMKilled`, or liveness probe failure? What does the liveness probe hit, with what timeout and failure threshold? Is there a startup probe? What are the resource requests and limits? Is CFS throttling non-zero? When did the restarts begin relative to the traffic rise?

**Isolate.** Restart reason `Unhealthy` with a liveness probe failure, plus a traffic trigger, is the feedback loop of Q88:

Load rises → the probe endpoint is served by the same saturated thread pool → the probe exceeds its 1-second timeout three times → kubelet kills the container → the pod restarts cold, with no JIT, no warm connection pool, and start-up CPU cost → its traffic redistributes to the remaining pods, pushing them into the same state → more kills. It is metastable: the restarts are now generating the pressure, so the original spike is no longer the cause.

If the reason is `OOMKilled` instead, this is Q75 and a different investigation - but the shape of the collapse is the same.

**Decide.** I break the loop first and fix the cause afterwards. The fastest way to break it is to stop the killing, which means changing the liveness probe - and I can do that without a code change.

**Execute.**

1. **Immediately relax or disable the liveness probe** on the Deployment - raise `timeoutSeconds` to 10 and `failureThreshold` to 6, or remove it entirely for the duration. A pod that is slow is better than a pod that is dead. This is a break-glass change, so I disable Argo CD self-heal or make it through git with an expedited path, and I announce it (Q154, Q212).
2. **Add capacity**, manually, now - scale the replica count up rather than waiting for the HPA, which is too slow for this (Q114).
3. **Shed load if it is still not recovering** - rate-limit at the gateway to protect what capacity exists, and let the service serve a subset successfully rather than nothing.
4. Watch for stabilization: restarts stop, latency falls, error rate recovers.
5. Then diagnose the underlying saturation: throttling metrics, GC pause time, thread pool queueing, downstream latency.

**Reflect.** The permanent fixes, in order: a **startup probe** so a slow start can never trip liveness (Q88); a **liveness probe on a dedicated cheap endpoint** that answers "is this JVM deadlocked" and nothing else; a **readiness probe** that can shed the pod from the load balancer without killing it; correct sizing and probably **no CPU limit** (Q92, Q93); and **load shedding** in the application so saturation degrades rather than collapses. In the postmortem I would also flag that the probe configuration was never tested under load - a game day injecting a traffic spike (Q223) would have found this.

> *Hook: a probe configuration that caused an outage, and what you changed.*

---

### S3. Alert storm at 03:00

> A node pool loses six nodes at 03:04. Between 03:04 and 03:09 the on-call engineer receives 214 pages. They acknowledge, silence everything, and go back to sleep. At 07:30 you discover a tier-1 service has been degraded since 03:06.

**Clarify.** What actually happened to the nodes - spot reclaim, an AZ event, an autoscaler action, a bad AMI rollout? What were the 214 pages - which rules, how many distinct? Which alert covered the tier-1 degradation, and was it in the silenced set? What is the current state of the service?

**Isolate.** Two failures, and it is important to name them separately.

1. **The infrastructure event.** Six nodes lost simultaneously is a correlated failure - spot reclaim of an under-diversified pool (Q253), a single-AZ event, or an autoscaler misjudgement. This is the trigger.
2. **The alerting failure, which is the real incident.** 214 pages for one event means alerts are **per-pod and per-instance with no grouping and no inhibition** (Q207). The engineer did the only rational thing available and silenced them, and in doing so silenced the one alert that mattered. The system converted a recoverable infrastructure event into four hours of undetected customer impact.

The tier-1 degradation was invisible because it was one signal in 214, and because there was no severity or routing distinction between "a pod restarted" and "a customer-facing service is failing".

**Decide.** Restore the tier-1 service now, then treat the alerting configuration as the incident that needs fixing - because the infrastructure event will happen again and next time the response must be one page.

**Execute.**

1. Assess and restore the degraded service: capacity, replica distribution, whether pods rescheduled and are healthy.
2. Clear the silences deliberately, one group at a time, so you can see what is genuinely still firing.
3. Confirm the node pool state and whether capacity has been replaced.
4. Then, same day: implement grouping by `alertname, cluster, service`, inhibition rules so `NodeNotReady` suppresses pod-level alerts on that node, and a severity split so only symptom-level alerts page (Q202, Q207).
5. Introduce a **SLO burn-rate alert** for the tier-1 service that pages independently of infrastructure alerts and cannot be suppressed by them (Q204).

**Reflect.** The postmortem action is not "tell people not to silence alerts". It is that **silencing was the correct action given the tooling**, and the system must make it unnecessary. Concretely: a hard target of fewer than two pages per shift (Q206), pages only on symptoms, inhibition following the dependency hierarchy, and a rule that a tier-1 SLO alert routes to a separate, non-suppressible channel. I would also fix the node pool's diversification so the trigger is less likely.

> *Hook: an alert storm you were on the receiving end of, and the routing you rewrote afterwards.*

---

### S4. Half the fleet is on the new version and rollback made it worse

> A canary reached 50 percent and analysis showed elevated errors, so the controller aborted and shifted traffic back to the stable version. Errors did not fall - they rose. The service is now worse than it was during the canary.

**Clarify.** What errors, from which version's pods? Did the release include a migration, a message format change, or a change to shared state - a cache, a queue, a distributed lock? Are the old pods actually healthy, or did the abort scale up pods that never became ready? Is a downstream service involved? What does the error look like in a trace?

**Isolate.** Rollback made it worse, which means the new version left behind state the old version cannot handle (Q135). The candidates, in order:

1. **Data written in the new format.** The canary wrote rows, cache entries or messages with a new shape - a new enum value, a changed serialization version. The old code reads them and throws. Errors rise on rollback because *all* traffic is now on code that cannot read the new data.
2. **A migration ran.** Even an additive one can break old code if a constraint tightened or a default changed.
3. **Shared coordination state.** A consumer group offset advanced, a leader election key changed, a distributed lock's format changed.
4. **Capacity.** The abort scaled the stable ReplicaSet back up from a reduced count, and the new pods are cold - so the errors are start-up and saturation errors, not correctness errors. This one is benign and self-resolving, and it is worth ruling out first because it looks identical for the first two minutes.

**Decide.** I need to know within two minutes whether this is case 4 (wait) or cases 1-3 (roll forward). The discriminator is the error itself: a deserialization or constraint error names the cause; a timeout or connection error suggests capacity. If it is 1-3, **rollback is not available and the only path is forward** - either re-promoting the new version, or shipping a fix that makes the old version tolerant.

**Execute.**

1. Pull one failing request's trace and log line. Read the actual exception. This is thirty seconds and it decides everything.
2. If capacity: confirm stable pods are becoming ready, add replicas, wait, and communicate that recovery is in progress.
3. If format or state: **re-promote the new version to 100 percent**. It is the version that can read its own data, and the elevated error rate it produced is likely smaller than the error rate the old version is producing now. Say out loud that we are rolling *forward* into a version we know is imperfect, and why.
4. Then fix the original canary failure with a targeted change, under the same canary process.
5. If neither works, assess whether the new-format data can be repaired or quarantined.

**Reflect.** The systemic failure is that a release which was not rollback-safe was deployed as if it were. The fixes: **expand-contract for every format and schema change** (Q142), with a rule that a release may not both write a new format and be the first release to read it; **the pipeline should know whether a release is rollback-safe** and disable automatic rollback when it is not (Q146); and **the rollback path must be tested in staging** as part of the release, not assumed.

> *Hook: a rollback that was unavailable, and how you found out.*

---

### S5. Terraform state is corrupted mid-apply

> A production apply was running in CI when the job hit its 30-minute timeout and was killed. The state lock is still held. The next plan proposes to create 14 resources that a colleague says already exist, and to destroy 3 that are in use.

**Clarify.** Is any apply still running anywhere - a retry, someone's laptop? What is the lock's age and holder? Is the S3 bucket versioned? What was in the change - was it a create-only change or did it include replacements? Do we know which resources completed? Is production currently healthy?

**Isolate.** This is Q176. State is written per-resource, so it reflects everything that completed. The 14 "create" proposals are almost certainly **orphans** - resources whose cloud API call succeeded but whose state write did not, or that were created after the last state persist. The 3 "destroy" proposals are more alarming and need separate explanation: either they were genuinely removed from the configuration in this change, or the state is stale in a way that makes Terraform think they are unmanaged.

The critical judgement: **do not apply this plan.** A plan that destroys three in-use resources is the incident, not the recovery.

**Decide.** Recover state to match reality before applying anything. Import the orphans one at a time, verify after each, and investigate the destroys separately. Nothing is applied until the plan matches intent exactly.

**Execute.**

1. **Confirm no apply is running** - check the CI job, check for any other runner, check CloudTrail for recent API activity from the Terraform role.
2. `terraform force-unlock <ID>` with the ID from the error (Q165).
3. **Verify state integrity**: check the S3 object version history, confirm the serial number, and take a copy of the current state before touching it.
4. **Verify each of the 14 in the cloud console/API.** Anything that exists gets `terraform import`; anything that does not is a genuine create. Re-plan after each import so you can see the plan shrinking - if it does not shrink as expected, stop.
5. **Investigate the 3 destroys separately.** Read the git diff for this change: were they removed from configuration deliberately? If not, this is a configuration or module-address problem (Q169) and needs `moved` blocks, not a destroy.
6. Only when the plan matches intent - and specifically has zero unexpected destroys - apply it.
7. Communicate throughout; this is a change-management incident even if nothing is customer-facing yet.

**Reflect.** Prevention, in order of value: **CI apply timeouts longer than any realistic apply**, with signal trapping so the lock is released on cancellation; **a required check that fails any plan containing a destroy** without an explicit approval label (Q169) - which alone would have stopped the dangerous half of this; **smaller state files** so applies are short and blast radius is bounded (Q167); and **an alert on locks older than an hour**. I would also add that this incident is an argument for reading plans rather than auto-approving them.

> *Hook: a Terraform recovery you performed, and how long it took.*

---

### S6. The cloud bill jumped 60 percent in one week

> Finance flags that last week's spend is 60 percent above the four-week average. Nothing obvious was launched. Engineering says nothing changed. You have a meeting in two hours.

**Clarify.** Which day did it start, and was it a step change or a ramp? Is it one account, one region, one service? Is it compute, data transfer, storage, or a managed service? Did traffic grow? Was there a deployment, an autoscaler change, an instance family change, or a new environment created?

**Isolate.** A step change with no launch narrows it quickly. Split the bill by service and by usage type first - that is fifteen minutes in Cost Explorer and it usually names the category. The recurring causes:

1. **A node count explosion** - a workload with a huge resource request that will not schedule, driving the autoscaler to add nodes indefinitely; or an HPA scaling on a broken metric; or a node group whose instance type changed.
2. **Data transfer**, especially NAT gateway processing - a new dependency pulling images or telemetry through NAT, or a change that moved traffic cross-AZ (Q256).
3. **Observability** - a cardinality explosion (Q184) or a log-level change multiplying ingestion volume. This is frequently billed to a different account and missed.
4. **Storage** - a snapshot schedule change, orphaned volumes, or a retention setting.
5. **A managed service resized** - an RDS instance upgraded, a cluster scaled.
6. **Something legitimate** - a launch, a marketing campaign, a customer onboarded. Growth is not waste, and confusing the two is how you cut something you need.
7. **An incident**: crash-looping pods burning compute, retries amplifying traffic, or a runaway job.

**Decide.** I do not guess in the meeting. I bring the attribution - which service, which usage type, which day - and either the cause or the next step to find it. Attribution first, remediation second.

**Execute.**

1. Cost Explorer grouped by service, then by usage type, then by tag, daily granularity. Identify the specific line that moved.
2. Correlate the start time against the change log: deployments, Terraform applies, config changes, flag flips (Q182). Most step changes have a change behind them within an hour.
3. For compute: node count over time, pending pod count, HPA target and replica history, and whether any workload's requests changed.
4. For transfer: NAT gateway processed bytes, cross-AZ transfer, and whether a VPC endpoint went missing.
5. Remediate the identified cause; if it is legitimate growth, say so clearly and move the conversation to cost per unit (Q250).
6. Bring to the meeting: the number, the cause, the fix, the timeline, and whether it is recurring.

**Reflect.** The reason this was a surprise is the missing controls: **anomaly detection on daily spend by service**, **mandatory ownership tags** so attribution takes minutes rather than hours, **per-team showback** so a team sees their own trend, and **a budget alert per environment**. I would also note that "nothing changed" is never true and that a change log correlated with the cost timeline should be the first tool, not the last.

> *Hook: a cost spike you investigated, and what it actually turned out to be.*

---

### S7. Deploys have been silently failing for two weeks

> A developer asks why their fix from two weeks ago is not in production. Investigation shows the deployment pipeline has been reporting success while Argo CD has been failing to sync since a change to the manifest repository. Eleven services are running fortnight-old code.

**Clarify.** What is the sync error? What changed in the manifest repository two weeks ago? Is it all eleven services or a subset with something in common? Was anything deployed successfully in that window? Are any of the undeployed changes security fixes? Did anyone acknowledge an Argo CD alert?

**Isolate.** Two separate failures again, and the second is the serious one.

1. **The sync failure** - a rendering error (an invalid Kustomize patch, a Helm value type change), an RBAC change, an admission policy rejecting the manifests, or a CRD version removed by a cluster upgrade. One cause, eleven applications, so it is something shared: a base manifest, a common chart version, or a cluster-level change.
2. **The detection failure.** The pipeline reported success because its job ended at "commit merged" - it never observed the deployment outcome (Q150). And Argo CD's `OutOfSync`/`Failed` state was either not alerted on, or the alert went somewhere nobody reads. Two weeks of undetected non-deployment is a monitoring gap, not a GitOps gap.

**Decide.** Fix the sync, then close the feedback loop, then assess the risk of the fortnight of undeployed changes - which may include security patches and which will now all land at once.

**Execute.**

1. Read the Argo CD application condition and the controller logs. The error is usually explicit.
2. Fix the shared cause - correct the manifest, restore the permission, adjust the policy.
3. **Do not let eleven services deploy a fortnight of accumulated change simultaneously.** Sequence them: sync one, verify, then the next, prioritizing by risk. A batched two-week release is exactly the risk profile of Q3, and it deserves canary treatment.
4. Review what is in each backlog of changes - specifically for migrations, contract changes and security fixes that may now interact.
5. Same day: add an **alert on any Argo CD application not Synced or not Healthy for more than 15 minutes**, routed to the owning team.
6. Add the deployment-result feedback to CI: the pipeline waits on and reports the reconciliation outcome, so "merged" is not mistaken for "deployed".

**Reflect.** The systemic issues are that **the deployment had no end-to-end success signal** and that **deployment freshness was not monitored**. Beyond the alert, I would add a "time since last successful sync" metric per application with an SLO, and a **deployment lead-time metric** (Q14) - a service whose lead time silently went from two hours to two weeks would have shown up on that chart in days. I would also ask why nobody noticed for two weeks, because that usually points at low deployment frequency being normalized.

> *Hook: a silent pipeline failure you found, and how long it had been running.*

---

### S8. Certificate expiry took out service-to-service traffic

> At 02:14 every service in the cluster starts failing to call every other service. TLS handshake errors. No deployment, no config change. The mesh control plane is running. Nothing in the cluster is unhealthy according to Kubernetes.

**Clarify.** What is the exact TLS error - unknown CA, expired certificate, or hostname mismatch? Is it all services or a subset? Is north-south traffic (through the ingress) also affected, or only east-west? When did the mesh control plane last restart? What is the root CA's expiry date? Is this a cluster the mesh was installed on more than a year ago?

**Isolate.** Simultaneous, cluster-wide, no change, at an arbitrary hour: that is a **time-based expiry**, not a change-induced failure. The candidates:

1. **The mesh root or intermediate CA expired.** Workload certificates rotate every 24 hours and are healthy; the **root** has a multi-year lifetime and nobody set a reminder. Every workload certificate now chains to an expired root, so every mTLS handshake fails at once (Q109).
2. **A trust bundle was not updated** after a root rotation - services cached the old bundle and the new certificates do not validate (`03-microservices` Q160).
3. **An ingress or upstream certificate** expired, if the failure is north-south rather than east-west.
4. **cert-manager stopped renewing** some weeks ago - a rate limit, an ACME failure, an RBAC change - and this is the first certificate to actually run out. The failure is today; the cause is a month old.

Kubernetes reports everything healthy because pods are running and readiness probes usually do not perform an mTLS call to a peer.

**Decide.** Restore trust as fast as possible. If it is the root CA, the immediate options are to issue a new root and distribute it (slow, correct) or to **temporarily set the mesh's mTLS mode to permissive** so plaintext is accepted (fast, and a deliberate, time-boxed reduction in security posture). For a total outage I would take the permissive path with an explicit decision record and a deadline, while the correct fix is prepared.

**Execute.**

1. Confirm the diagnosis: inspect a workload certificate's chain and the root's `notAfter` (`istioctl proc-status`, or `openssl` against the mounted cert).
2. Declare SEV1, appoint an IC, and communicate.
3. If root expiry: issue a new root (or intermediate from the organization PKI), distribute the trust bundle to every namespace, and restart the control plane so new workload certificates chain correctly. Workloads pick up new certificates on rotation, so restarts may be needed to accelerate it.
4. If the outage cannot be resolved in minutes, switch mTLS to permissive as a deliberate mitigation, restore service, and revert once trust is repaired.
5. Verify recovery on a real request path, not on pod status.

**Reflect.** This is an entirely preventable class of incident and the prevention is boring: **alert on certificate expiry with a long lead** - 30 days for workload and intermediate certificates, 90 days for roots - with the check performed against the *actual served certificate*, not against a config file. Add cert-manager's renewal failure metrics to alerting. Add a **synthetic probe that performs a real mTLS call between two services** and alerts on failure, because that is the only check that would have caught cases 2 and 4 early. And record every root and intermediate expiry as a calendared, owned event.

> *Hook: an expiry incident, and the alert lead time you settled on.*

---

### S9. A leaked credential in a public repository

> A security researcher emails: an AWS access key belonging to your organization is in a public GitHub repository, committed nine days ago by an engineer pushing a personal side project that included a copied config file.

**Clarify.** Which key, belonging to which principal? What does it grant? Is it still active? Is the repository still public? Has there been any use of it from unexpected sources? Is this the only credential in that repository?

**Isolate.** Public plus nine days means **assume compromise** (Q126). Public repositories are scraped continuously and cloud keys are typically exercised within minutes. The question is not whether it was found but what was done with it, and the shape of that answer depends entirely on what the key could do.

**Decide.** Revoke first, investigate second. Revocation is the only action that reduces risk; everything else is analysis that can happen afterwards. If revocation would break production, issue a replacement and cut over, but do not delay past that.

**Execute.**

1. **Deactivate the key immediately** (not delete - deactivate, so CloudTrail attribution remains clean and it can be re-examined). If it is in use by a production system, create a replacement first, deploy it, then deactivate - but with a hard time limit measured in tens of minutes, not days.
2. **Declare a security incident** and follow the process; do not handle this quietly.
3. **Scope the permissions.** What could the principal do? This determines whether this is an embarrassment or a breach.
4. **Hunt.** CloudTrail for every use of that access key ID over the full nine days: source IPs, user agents, API calls, regions. Look specifically for reconnaissance patterns (`GetCallerIdentity`, `ListBuckets`, `DescribeInstances`), persistence (`CreateUser`, `CreateAccessKey`, `AttachUserPolicy`), and exfiltration (`GetObject` at volume, snapshot copies, `CreateImage`).
5. **If there is any evidence of use**: escalate, engage security and legal, and work the containment path - revoke sessions, rotate everything the principal could reach, review for persistence mechanisms.
6. **Get the repository content removed** and the history purged, understanding that this is cleanup and not remediation.
7. **Scan every repository, public and private, and the CI logs and images**, because this is never a single instance.

**Reflect.** The prevention is Q233: **push protection server-side** so this cannot be committed; **pre-commit scanning** for the developer's own flow; **historical scanning** of everything. But the more important structural fix is that **this key should not have existed** - an IAM user with a long-lived access key in a config file is the pattern to eliminate. OIDC federation for CI (Q234) and workload identity for runtime (Q128) remove the credential entirely, which is the only durable answer. I would also check whether GitHub's automatic revocation partnership was enabled for the account, because it would have quarantined this within minutes.

> *Hook: a credential leak you handled, and how quickly you were able to revoke.*

---

### S10. The cluster upgrade drain will not finish

> A production node group upgrade started 90 minutes ago. Four of twelve nodes are done. The fifth has been draining for 50 minutes with no progress. The change window closes in 40 minutes and the cluster is now running two Kubernetes versions.

**Clarify.** Which pods remain on the draining node? What does `kubectl drain` report - PDB violations, unschedulable pods, or something else? Is there capacity for the pods to move to? Are any of them StatefulSet members with volumes? Is the mixed-version state causing any problem right now?

**Isolate.** A drain that stalls is almost always the eviction API refusing (Q116). In order of likelihood:

1. **An unsatisfiable PodDisruptionBudget** - `minAvailable: 1` on a single-replica Deployment, or `minAvailable` equal to `replicas`. The API refuses forever because evicting would breach it, and it can never not breach it.
2. **The replacement pod cannot schedule** - insufficient capacity, a node affinity that only matches nodes being drained, or a topology spread constraint that cannot be satisfied while a zone is short.
3. **A StatefulSet pod** whose volume cannot detach and reattach (Q111), which takes minutes and can stall entirely.
4. **A pod with no controller** - a bare pod, which drain refuses to evict.
5. **A long termination grace period** or a container ignoring `SIGTERM`, so each pod takes its full grace period.

**Decide.** The mixed-version state is safe (kubelet may lag the control plane) and is not itself an emergency, so **I do not rush**. I would rather stop cleanly at eight nodes and resume tomorrow than force-delete pods against a PDB and cause an availability incident to meet a window. The decision to state out loud is that the window is a preference and availability is a requirement.

**Execute.**

1. Read the drain output and `kubectl get pdb -A` for the affected namespaces. This names the cause in seconds.
2. If it is an unsatisfiable PDB on a single-replica service: **scale that Deployment to 2** (if it can run two replicas) or temporarily relax the PDB. Both are legitimate, reviewable changes; the second is a deliberate acceptance of brief unavailability for that service.
3. If it is capacity: add nodes to the new group first, then resume the drain. `maxUnavailable: 0` semantics need somewhere for pods to go.
4. If it is a StatefulSet volume: wait, or use the non-graceful shutdown path if the node is genuinely dead. Do not force-delete a StatefulSet pod casually - two pods with the same identity and volume is a data risk.
5. **Stop the upgrade cleanly** if the window closes: cordon nothing further, leave the cluster in the mixed state (which is supported), and resume with a fresh window.
6. Communicate the state clearly, including that a mixed-version cluster is a supported and safe steady state.

**Reflect.** The preventable causes are all policy-level: a **policy check that rejects a PDB that can never be satisfied** (Q239), **surge capacity provisioned before the upgrade begins**, and a **pre-upgrade readiness check** that simulates evictions and reports which workloads will block. I would also rehearse the upgrade in a production-shaped staging cluster (Q257) - this failure would have appeared there for free. And I would question the change-window framing, because a time-boxed window on a zero-downtime operation creates pressure to take exactly the shortcut that causes the outage.

> *Hook: a drain that hung, and what was blocking it.*

---

## Part B - Design exercises

These are the category 17 questions worked in full. Give yourself twenty minutes each, out loud, before reading.

### S11. Design a CI/CD platform for 200 engineers and 60 services (Q261)

> You have joined a 200-engineer organization with 60 Java services. Pipelines are inconsistent, deployment is a mix of Jenkins jobs and manual steps, and there is no standard for artifacts or rollback. Design the platform.

**Shape of a strong answer.** Clarify the constraints first (regulatory posture, current state, team maturity, appetite for change), then design **the contract before the implementation** - what every pipeline must produce and guarantee - and only then the paved road that satisfies it. Cover build and artifact identity, promotion, deployment mechanism, rollback, observability and the platform team's operating model. The failure mode is designing a pipeline rather than a platform, and forgetting that at 200 engineers the hard problems are adoption, migration and ownership rather than YAML.

**Clarify.** What is the regulatory posture - does anything need change approval or evidence? What is the current deployment frequency and lead time? What is the cloud and runtime target, and is it fixed? How many teams, and how autonomous are they? Is there an existing platform team, and how large? What is the appetite for disruption - is this a mandate or a persuasion exercise? What is broken enough that people want change?

**Isolate.** At 200 engineers the hard problems are not technical. Any competent engineer can design a pipeline; the difficulty is **adoption, migration and ownership across 60 services and ~20 teams**. So the design must be a *platform* with an interface and a support model, not a pipeline template.

The core insight to lead with: **standardize the contract, not the implementation** (Q16). Define what every pipeline must produce and guarantee, enforce that at the boundary, and provide a paved road that makes satisfying it the easiest option.

**Decide.** The contract every service's delivery must satisfy:

1. A **single immutable artifact per commit**, addressed by digest, built once (Q4).
2. **Signed, with provenance and an SBOM** attached to that digest (Q58-60).
3. **Promoted, not rebuilt**, through environments (Q9).
4. **Deployed declaratively from git**, so what is running is a reviewable commit (Q149).
5. **Progressively, with automated analysis and abort** (Q137).
6. **Emitting a deployment event** with the SHA, digest, environment and actor (Q14).
7. **Rollback available and tested**, with a stated rollback-safety property per release (Q143).

**Execute - the architecture.**

*Source and CI.* GitHub with branch protection as in Q26, and **reusable workflows** as the paved road (Q44): one `java-service.yml` covering build, test, scan, SBOM, sign and publish, versioned with moving major tags. Self-hosted **ephemeral** runners on Kubernetes via Actions Runner Controller for builds needing VPC access, hosted runners otherwise (Q32-34). Remote build caching so a warm build is minutes not tens of minutes (Q35-37).

*Artifacts.* One registry, immutable tags, digest references everywhere, retention policy with a never-delete rule for anything deployed to production (Q7, Q10). A proxying artifact repository with exclusive routing for internal namespaces (Q50).

*Deployment.* **Argo CD, per-cluster instances for production** (Q161), reading environment manifest repositories. Kustomize bases plus thin overlays, generated into Applications by an ApplicationSet so adding a service is adding a directory (Q157). Promotion is an automatically-opened pull request changing one image digest, and the merge is the authorization event (Q162). **Argo Rollouts** for progressive delivery, with a shared AnalysisTemplate library so a team gets canary analysis by adopting a template rather than by designing one (Q137).

*Security.* OIDC federation from CI to cloud, per service per environment, with `sub` pinned to the environment (Q234, Q236). Admission control verifying signature and provenance, plus Pod Security `restricted` and default-deny NetworkPolicy generated per namespace (Q239).

*Observability of delivery itself.* DORA metrics derived from the deployment events and git history (Q14), pipeline duration and queue-time SLOs (Q46), and a per-service dashboard showing lead time, deployment frequency, change failure rate and time since last deploy.

**Execute - the rollout, which is the real plan.**

1. **Months 0-2**: build the paved road and prove it on **two willing teams and four services**. Do not announce a standard yet. The output is a working reference and a migration guide written from real experience.
2. **Months 2-4**: publish the contract and the paved road. Migrate teams that opt in, in cohorts, with the platform team pairing on the first service per team. Publish the two pilot teams' before-and-after lead time and change failure rate - that is the recruitment material.
3. **Months 4-8**: enforce the contract *at the boundary only* - admission control requiring signed images from the registry, and a required deployment event. Teams that have not migrated must satisfy it somehow, which is a much easier conversation than "adopt our pipeline".
4. **Months 8-12**: decommission Jenkins per service as its last job migrates, and remove manual deployment access.

**The operating model.** The platform team owns the paved road as a **product**: versioned, documented, with a support channel, an SLO on its own availability, and a published roadmap. It does not own other teams' pipelines and does not become a deployment ticket queue - that is the failure mode that kills platform teams (Q16). Escape hatches are explicit: a team may deviate if it satisfies the contract, and the deviation is recorded so the platform can learn from it.

**Reflect.** What I would watch: paved-road adoption rate; time-to-first-deploy for a brand-new service (the sharpest measure of whether the platform works); the platform team's ticket volume (rising means the road is not paved); and the DORA metrics per team, which is what tells you whether any of it mattered. The biggest risk is building a beautiful platform nobody adopts, and the mitigation is that the first four services are real, willing and public.

> *Hook: a platform you built or inherited, and what adoption actually looked like.*

---

### S12. Design the migration of 25 services from EC2/Jenkins to EKS/GitOps (Q262)

> 25 Java services run on EC2 behind ALBs, deployed by Jenkins jobs invoking Ansible. There is a shared PostgreSQL, a Redis cluster, and a Kafka cluster. The business will not accept a big-bang cutover or a delivery freeze. Design the migration.

**Shape of a strong answer.** No big-bang cutover, so the design is a **sequence with a working system at every step** - strangler routing at the edge, one pilot service chosen for its low risk and high learning value, the platform capabilities built just ahead of demand, and a defined rollback at each stage. Name what runs in both places simultaneously and how state, configuration and traffic are handled during the overlap.

**Clarify.** What is driving this - cost, scaling, developer experience, or a mandate? What is the current deployment frequency and failure rate, so we can tell whether we made it worse? Which services are stateful or have local disk dependencies? What is the network topology - can EKS pods reach the existing databases? Are there services with sticky sessions, long-lived connections, or scheduled jobs? What is the timeline expectation, and who owns each service?

**Isolate.** The requirement is **a working system at every step**, so the design is a *sequence*, not an end state. Three things have to be true throughout: traffic can be split between EC2 and EKS for the same service; both platforms can reach the same data; and a service can be moved back if it goes badly.

The other framing that matters: this is really **three migrations happening at once** - runtime (EC2 → Kubernetes), deployment mechanism (Jenkins push → GitOps pull), and packaging (Ansible-deployed JARs → containers). Doing all three simultaneously for the first service is how you learn nothing from the failure. I would separate them where possible.

**Decide.** A **strangler migration at the load balancer**, service by service, with target-group weighting as the traffic control. Containerize and move the deployment mechanism *before* moving the runtime, so each change is independently reversible.

**Execute.**

*Phase 0 - foundations (weeks 1-6), no service moves.*

1. **Build the EKS cluster with Terraform** (Q178), in the same VPC, with security group and routing access to PostgreSQL, Redis and Kafka. Reusing the data layer is what makes incremental migration possible; moving data is a separate, later project.
2. **Install the platform**: Argo CD, ingress, cert-manager, external-secrets, the observability stack, admission policy - all GitOps-managed from day one so the cluster is rebuildable (Q226).
3. **Establish the shared deployment pattern**: base Kustomize manifests, the reusable CI workflow, the container build, the promotion flow.
4. **Prove observability parity.** Metrics, logs and traces from EKS must land in the same place, with the same names, as from EC2 - otherwise you cannot compare the two during a cutover, which is the entire safety mechanism.

*Phase 1 - the pilot (weeks 6-10), one service.*

5. **Choose the pilot for learning value, not for ease**: a real, production, stateless HTTP service with moderate traffic, owned by a willing team, that is not on the critical revenue path. Too trivial and you learn nothing; too critical and the first surprise is an incident.
6. **Containerize it and deploy to EKS with zero traffic.** Run it against production dependencies, exercised by synthetic traffic and mirrored production traffic (`03-microservices` Q133).
7. **Shift traffic by ALB target-group weight**: 1 percent, 5, 25, 50, 100, comparing error rate and latency against the EC2 target group at each step. The EC2 fleet stays running and warm the whole time - that is the rollback.
8. **Hold at 100 percent for two weeks** with EC2 still available before decommissioning.
9. **Write down everything that surprised you.** This is the phase's actual output.

*Phase 2 - cohorts (months 3-9).*

10. Migrate in cohorts of three or four services, grouped by team so a team migrates once rather than repeatedly.
11. Handle the special cases deliberately as they arise: **scheduled jobs** become CronJobs with concurrency policy set (Q96); **sticky sessions** need either session externalization or a routing decision; **long-lived connections** need a drain plan; **services with local disk** need the state moved out first.
12. **Secrets migrate to External Secrets** with the same store serving both platforms during the overlap (Q131).
13. Decommission each service's Jenkins job as it moves; do not leave two paths live.

*Phase 3 - completion (months 9-12).*

14. Last services, including the awkward ones, with the accumulated platform capability behind them.
15. Decommission Jenkins and the EC2 fleet.
16. Only then consider moving the data layer, if that was ever a goal.

**The rollback at each stage** is explicit: traffic weight back to the EC2 target group, which is a seconds-long change requiring no deployment. That property is what makes the whole plan acceptable to the business, and it is worth saying so directly.

**Reflect.** What I would monitor throughout: **delivery metrics per migrated service before and after** - if lead time or change failure rate gets worse, the migration is not succeeding regardless of how the architecture looks. Also cost per service, because "EKS will be cheaper" is frequently untrue at first. The biggest risks are the shared data layer becoming a contention point when connection patterns change (Q235 in `06-database` territory), and the platform team becoming the bottleneck for 25 migrations - which is why cohorts are by team and why the team does the work with the platform team pairing, not the other way round.

> *Hook: a migration you sequenced, and the service you chose to go first.*

---

### S13. Design the observability and SLO platform for that estate (Q263)

> The same 60-service estate. Each team has its own dashboards, alert rules and log formats. Nobody can answer "is the checkout journey healthy" without asking four teams. Observability spend is growing 15 percent a quarter. Design the platform, and drive adoption without a mandate.

**Shape of a strong answer.** Separate **what is standardized** (instrumentation library, semantic conventions, the pipeline, the SLO framework and burn-rate alerting) from **what is per-team** (which SLIs, what thresholds, which dashboards, which alerts page). Then adoption without a mandate - make the paved road the path of least resistance, seed it with the teams who want it, and use the on-call load reduction as the argument.

**Clarify.** What is the current tooling and contractual position - are we locked into a vendor? What is the spend and its trajectory? What is the on-call load, and is it the pain that motivates people? Do teams currently have SLOs at all? Who owns the checkout journey end to end - is there an owner, or is that the actual problem? What is the platform team's size?

**Isolate.** Three distinct problems that need separating:

1. **Inconsistency** - different formats, names and conventions, so cross-service questions are unanswerable. This is a *standards* problem.
2. **No service-level view** - nobody can state whether a user journey is healthy, because health is expressed per component. This is an *SLO* problem.
3. **Cost growth** - unbounded because nobody owns it and nothing constrains cardinality or volume. This is an *ownership and pipeline* problem.

They have different solutions, and conflating them produces a project that does none of them.

**Decide.** Standardize the **substrate** and the **framework**; leave the **content** to teams.

| Standardized (platform owns) | Per-team (service owner owns) |
| --- | --- |
| Instrumentation library and OpenTelemetry semantic conventions | Which SLIs matter for this service |
| The telemetry pipeline: Collector agent + gateway tiers | SLO targets and windows |
| Metric naming, mandatory labels, cardinality limits | Which dashboards beyond the generated ones |
| Log schema and mandatory fields | Which alerts page versus ticket |
| Trace propagation and sampling policy | Runbooks |
| The SLO framework, burn-rate alert generation, error budget reporting | Domain and business metrics |
| Generated RED dashboards per service | |
| Retention tiers and cost attribution | |

**Execute - the platform.**

1. **A shared instrumentation library** (a Spring Boot starter) that a service adds as one dependency and gets: OpenTelemetry configured, resource attributes populated from the environment, RED metrics on every endpoint with `http.route` templated, structured logging with the mandatory field set and trace correlation, and sane histogram buckets (Q186, Q191). **The paved road must be one dependency and zero configuration**, or adoption fails.
2. **An OTel Collector tier**: DaemonSet agents for local receipt and enrichment, forwarding to gateway Collectors doing tail sampling, filtering, redaction and cardinality control before egress (Q194, Q196). This tier is where cost is controlled, and putting it in place early is what stops the 15 percent quarterly growth.
3. **Metrics into Mimir (or the vendor equivalent) with per-tenant limits** (Q188), so one team's cardinality incident cannot take down everyone's alerting (Q184). Per-tenant limits are the single most important operational property here.
4. **SLOs as code.** A team declares an SLO in a small YAML file in their repository:

```yaml
slo:
  name: checkout-availability
  sli: request_based
  target: 99.9
  window: 28d
  good: sum(rate(http_requests_total{service="checkout",code!~"5.."}[5m]))
  total: sum(rate(http_requests_total{service="checkout"}[5m]))
```

and the platform **generates** the recording rules, the multi-window burn-rate alerts (Q204), the error budget dashboard and the routing. This is the highest-leverage thing on the list: it turns "write correct burn-rate alerting" - which almost nobody does correctly by hand - into four lines.

5. **Journey-level SLOs.** The checkout journey gets its own SLO measured at the edge, owned by a named person, composed from but not identical to the component SLOs (Q217). This directly answers the question in the brief.
6. **Cost attribution per team**, published (Q250, Q259).

**Execute - adoption without a mandate.**

1. **Lead with the pain that people already feel.** Nobody wants "better observability"; they want fewer 3 am pages and faster incident resolution. Frame the whole programme as on-call load reduction (Q215), because that is a thing engineers will actively pull.
2. **Make the paved road strictly better and strictly easier.** One dependency, and you get dashboards and correct alerting for free. If adopting the standard is more work than not adopting it, no amount of advocacy helps.
3. **Seed with two or three teams with the worst on-call load.** Their before-and-after page count is the argument, and it is far more persuasive than an architecture diagram.
4. **Publish comparative data.** A leaderboard of page volume, alert actionability and cost per service, without shaming - teams optimize what is visible.
5. **Turn up during incidents.** The platform team joining incidents and demonstrating that the new tooling answers questions faster is the most effective adoption mechanism there is.
6. **Use the cost lever last but do use it.** When a team's observability bill is visible and the platform pipeline cuts it by 40 percent, the conversation changes on its own.
7. **Then, and only then, add a light enforcement ratchet**: new services must use the library; existing services must have at least one SLO by a date. Enforcement lands easily once the thing being enforced is already popular.

**Reflect.** Measures of success: the fraction of services on the shared library; the fraction with a declared SLO; **pages per on-call shift** and alert actionability (Q206); mean time to identify during incidents; and cost per service trending down while coverage goes up. The failure mode to watch for is a platform team that builds a beautiful standard nobody adopts, and the mitigation is that everything is driven by teams who volunteered because they were in pain.

> *Hook: an observability standard you drove, and the team whose on-call load proved it worked.*

---

### S14. Design multi-region active-active and its release process (Q264)

> The business wants the platform live in two regions, both serving traffic, to survive a regional failure. You currently run one region with a single-writer PostgreSQL, Kafka, and 60 services on EKS. Design it - and specifically, say what breaks about your release process.

**Shape of a strong answer.** The interesting half is not the architecture but **what breaks about the pipeline** when there are two live regions - a canary in one region while the other serves the old version, schema changes that must be compatible across regions and across versions simultaneously, config and flag consistency, and the fact that "rollback" now has a region dimension. Cover the data layer honestly (Q228).

**Clarify.** What is the actual requirement - regional resilience, latency for a second geography, or a regulatory data-residency constraint? These lead to very different designs. What RTO and RPO (Q224)? Is active-active required, or would warm standby meet it at a fraction of the cost (Q227)? Which data must be strongly consistent, and which can tolerate eventual consistency? Are there regulatory constraints on where data may live? What is the budget, and does the business understand it is more than 2×?

**Isolate.** The hard problem is **state**, not compute. Sixty stateless services in a second region is a Terraform module and a week. The design is entirely determined by three decisions:

1. **Where writes happen** - single-writer with cross-region reads, partitioned writes by tenant or geography, or true multi-writer with conflict resolution.
2. **What consistency each workflow needs**, per workflow rather than globally.
3. **How traffic is routed**, and whether a user's requests must be consistent with each other.

**Decide.** For a system with a single-writer relational database and no existing consistency design, I would propose **active-active for the stateless and read paths, with a single write region and automated write-region failover** - sometimes called active/read-active. This gives regional resilience for the majority of traffic, survives a region loss with a bounded RPO, and does not require redesigning every write path around conflict resolution. True multi-writer is a multi-year architectural programme and should be entered deliberately, not as a side effect of a resilience requirement.

**Execute - the architecture.**

- **Traffic**: a global load balancer or anycast entry point (Global Accelerator, CloudFront, Cloudflare) rather than DNS failover, so shifting traffic does not wait on resolver caches (Q228). Health-check-driven, with the ability to shift weight manually.
- **Compute**: identical EKS clusters per region, created by the same Terraform, deployed by per-region Argo CD instances from the same manifest repository with a region overlay (Q161). Each sized to carry **100 percent of traffic alone**, which is the cost the business must understand.
- **Relational data**: PostgreSQL with cross-region asynchronous replication. Writes route to the primary region; reads are served locally where the workflow tolerates replica lag, and route cross-region where it does not. **Replication lag is exported as a metric and is the RPO**, so it is alerted on continuously, not discovered during failover.
- **Write-region failover**: automated detection, **human-triggered promotion** with a pre-agreed decision procedure (Q228), fencing of the old primary, and a documented, rehearsed fail-back path.
- **Kafka**: MirrorMaker 2 or cluster linking, with topic naming that makes it explicit which topics are regional and which are replicated. Consumer offsets do not translate cleanly across regions, so plan for reprocessing and require idempotent consumers.
- **Object storage**: cross-region replication, understanding its lag.
- **Caches**: regional and independent; never replicated. A cross-region cache is a consistency problem pretending to be a performance optimization.
- **Coordination**: anything quorum-based needs a third failure domain or must be regional (Q228). Two regions cannot form a quorum that survives losing one.

**Execute - what breaks about the release process, which is the point of the question.**

1. **A canary is now regional.** Deploying the canary in region A means region B is serving the old version for the whole analysis period. So **every release is, for a period, a cross-version deployment across regions** - and the two versions share a database and a Kafka topic. This makes contract and schema compatibility (Q144) not a nice-to-have but a hard, permanent constraint on every change.
2. **Rollout order matters and must be deliberate.** My default: canary in the **non-write region** first (smaller blast radius on writes), promote there fully, soak, then the write region. That is slower and it is the right trade.
3. **Schema migrations become genuinely hard.** A migration applied in the write region is immediately visible to the read region's older code. Expand-contract is now mandatory with a longer contract delay, and migrations must be compatible with *two* application versions across *two* regions simultaneously.
4. **Rollback gains a region dimension.** "Roll back" now means "roll back where", and a partial rollback leaves you in a version-skew state you must have already decided is safe.
5. **Configuration and flags must be consistent across regions**, or a user whose requests land in different regions gets different behaviour. Flag state has to be replicated, and the flag SDK's cold-start default (Q130) must be identical in both.
6. **Deployment is no longer atomic**, so there is a window - potentially hours - where the estate is heterogeneous. Every release must be designed for that.
7. **The pipeline itself must be regional.** If CI, the registry, the secret store or the GitOps controller lives only in region A, losing region A means you cannot deploy a fix to region B during exactly the incident you built this for (Q229).
8. **Testing must cover version skew** - a contract test matrix of old-versus-new across regions, not just old-versus-new in one place.

**Reflect.** What I would measure: replication lag as the live RPO; a **regular, real failover** - running production from the secondary for a week each quarter - because a failover path that is only exercised in drills will fail (Q229); and per-region SLOs, so a degraded region is visible before it becomes a failover decision. The honest caveat to give the business: active-active is not primarily an infrastructure cost, it is a permanent constraint on how every feature is built, and that ongoing tax is larger than the bill.

> *Hook: a multi-region design you worked on, and the constraint that surprised the product team.*

---

### S15. Design an internal developer platform (Q265)

> Leadership wants an internal developer platform. Teams currently spend weeks standing up a new service, copy-paste manifests between repositories, and file tickets with the infrastructure team for anything unusual. Design it: the paved road, the escape hatch, and how you know it is working.

**Shape of a strong answer.** Define the **paved road** (the supported, opinionated path that covers 80 percent of cases), the **escape hatch** (how a team does something different without leaving the platform entirely, and what they give up), and the **measures** that tell you the platform is working - adoption rate, time to first deploy for a new service, lead time, and the platform team's own ticket queue as an anti-metric. The failure mode is building a platform nobody adopts because it removes autonomy without removing toil.

**Clarify.** What is the actual pain - onboarding time, cognitive load, inconsistency, or the infrastructure team being a bottleneck? Who is asking, and what do they think a platform is? How many teams and services, and what is the growth trajectory? Is there an existing platform team, and is it staffed as a product team or as a ticket queue? What is the appetite for standardization versus autonomy? What already exists that works?

**Isolate.** The failure mode of internal platforms is well known: they **remove autonomy without removing toil**. A platform that constrains teams to a narrow path, and then requires a ticket whenever the path does not fit, is worse than no platform - it has added a queue and taken away the ability to route around it.

So the design constraint is: **the platform must reduce the amount teams have to know, without reducing what they are allowed to do.** The ticket queue to the infrastructure team is the symptom to eliminate, and it will not be eliminated by adding a portal in front of the same queue.

**Decide.** Three components, in this order of importance: a **paved road** that covers the common case end to end, a **real escape hatch** with defined trade-offs, and **self-service** so nothing in the common case requires a human.

**Execute - the paved road.**

The measure is: *how long from "we want a new service" to "it is serving production traffic"?* The target is **a day**, not weeks.

1. **Service scaffolding**: a templated repository (Backstage software templates, or a CLI) producing a working Spring Boot service with the CI workflow, Dockerfile, base manifests, the observability library (S13), default SLOs, an on-call routing entry, and a README - all wired and deployable on first commit.
2. **Infrastructure by declaration.** A service declares what it needs in a small manifest in its own repository:

```yaml
apiVersion: platform/v1
kind: ServiceInfrastructure
spec:
  database: { engine: postgres, size: small }
  queues: [orders-events]
  cache: { engine: redis, size: small }
```

and the platform provisions it - via Crossplane, or via a Terraform module generated from the declaration (Q177, Q178). The team gets the connection details as an ExternalSecret automatically. **No ticket.** This is the component that actually removes the bottleneck, and it is the hardest to build.
3. **Delivery**: the reusable CI workflow and GitOps promotion flow from S11, already wired by the template.
4. **Observability and SLOs**: from S13, on by default.
5. **Guardrails, not gates**: admission policy, cost budgets and security controls applied by the platform, so a team on the paved road is compliant by construction rather than by review.
6. **A catalogue** (Backstage or equivalent) answering: what services exist, who owns them, what they depend on, what their SLOs are, when they last deployed. This is what makes a 60-service estate navigable and it is often the most-used part of the platform.

**Execute - the escape hatch.**

The escape hatch is what distinguishes a platform from a cage, and it must be designed rather than tolerated.

- **The paved road is composed of layers, and each layer is usable independently.** A team that needs a different CI pipeline can still use the deployment layer; a team needing a bespoke manifest can still use the observability library. Monolithic platforms have no escape hatch because everything is one thing.
- **The interface is the contract, not the tooling** (S11). A team may build their own path if it satisfies the contract - signed artifact, deployment event, policy compliance. That is what is enforced at the boundary.
- **Raw access remains available.** A team can write their own Terraform and their own manifests. What they give up is explicit and stated: they own the upgrades, they do not get the generated dashboards and alerts, they must satisfy the policy checks themselves, and platform support is best-effort.
- **Deviations are recorded and reviewed.** Each one is a signal about a gap in the paved road, and the platform roadmap should be substantially driven by them. Three teams escaping for the same reason is a feature request with evidence.
- **Never make the escape hatch require permission.** Requiring approval to deviate recreates the ticket queue.

**Execute - how you know it is working.**

| Metric | What it tells you |
| --- | --- |
| **Time to first production deploy for a new service** | The sharpest single measure of the paved road |
| **Paved road adoption**, as a share of services and of new services | Whether the road is actually paved |
| **DORA metrics per team** (Q14) | Whether it improved delivery, which is the point |
| **Platform team ticket volume and queue time** | **The anti-metric.** Rising volume means self-service is not working. This is the number that tells the truth. |
| **Developer satisfaction survey**, specifically "how much time do you spend on things unrelated to your product?" | The cognitive-load measure, and the one leadership responds to |
| **Escape hatch usage, by reason** | The roadmap |
| **Cost per service and per team** (Q250) | Whether the platform is efficient as well as pleasant |
| **Time to apply an estate-wide change** - a base image bump, a policy change | The leverage the platform provides, and the strongest justification for its existence |

**Reflect.** The things I would insist on: the platform team is staffed and run as a **product team** with a roadmap, users, a support SLO and a published changelog - not as an infrastructure ticket queue with a new name. Adoption is voluntary and earned (S13). And the platform's own reliability is a tier-1 concern, because a platform outage now blocks 20 teams.

The risk I would name explicitly to leadership: **platforms fail from over-scoping**. The temptation is to build everything at once; the correct approach is to pick the single biggest source of toil - here, the infrastructure ticket queue - solve it completely for a few teams, and expand from demonstrated value.

> *Hook: a platform capability you built, and how you decided what not to build.*

---

## Part C - Leadership situations

These have no single right answer. They assess judgement, honesty and whether you have actually held the responsibility. Use **STAR-L** and quantify.

### S16. The team that will not adopt the standard

> Eleven of twelve teams have adopted the shared deployment pipeline. The twelfth - a senior, high-performing team owning the most critical service - refuses. Their tech lead says the standard is slower and less capable than what they have. Leadership asks you to make them comply.

**Clarify (of yourself, before acting).** Are they right? What specifically is slower or less capable? Is their service genuinely different, or is this preference? What is the actual cost of their non-compliance - is it a real risk, or is it tidiness? What is the relationship history here?

**Isolate.** Two very different situations, and getting this wrong is expensive.

- **They are right.** A high-performing team with a critical service has often solved problems the standard has not. Forcing compliance makes the most important service worse and destroys the credibility of the standard with everyone else.
- **They are protecting autonomy**, and the technical arguments are post-hoc. This is a legitimate concern with an illegitimate expression.

Usually it is some of both.

**Decide.** I do not lead with compliance. I lead with **finding out whether they are right**, and I separate the *contract* (what must be true) from the *implementation* (how). If their pipeline satisfies the contract, there is no problem to solve, and I would tell leadership so.

**Execute.**

1. **Go and look.** Spend a day with their pipeline. Understand what it does that the standard does not.
2. **Separate the requirements from the mechanism** (Q16). Enumerate what the organization actually needs: signed artifacts, provenance, deployment events, rollback, policy compliance. Check their pipeline against it, honestly.
3. **If they satisfy the contract**: they are compliant. Document the exception, feed their innovations back into the standard, and tell leadership that the goal was the outcome, not the tool. This usually improves the standard.
4. **If they do not**: name the specific gaps and the specific risk each creates, and ask them to close those gaps in whatever way they prefer. That is a much smaller and more reasonable ask than "adopt our pipeline".
5. **If the standard is genuinely worse**: fix the standard. Their objection is a bug report from your most demanding user.
6. **Manage upward honestly.** Tell leadership what I found, including if it is that the standard needs work. Do not deliver a compliance win that damages the critical service.

**Reflect.** What I would take away: a standard that a good team rejects is usually a standard that was designed without enough input from good teams. The durable fix is to build the paved road *with* the strongest teams rather than presenting it to them. And the mandate is the last tool, not the first - a standard adopted under duress is maintained badly and abandoned quietly.

---

### S17. You are asked to cut the release process during an outage-heavy quarter

> Change failure rate has risen. Leadership's response is to add a mandatory architecture review board and a weekly release window. You believe both will make things worse. You have one meeting to respond.

**Clarify.** What is the actual data - has change failure rate risen, or has visibility of it risen? What kinds of failure? Is it concentrated in a few services or estate-wide? What is leadership's underlying fear - customer impact, a specific incident, a board-level question?

**Isolate.** The proposal is a **prediction control** applied to a problem that needs **containment controls** (Q145). A review board and a weekly window will make batches larger, bisection harder and rollback slower, which raises the cost of each failure while reducing the frequency of releases - and change failure rate is measured per release, so the metric will improve while the outcome gets worse. That is the argument to make, and it must be made with data rather than principle.

**Decide.** Do not oppose the goal; oppose the mechanism, and bring an alternative that addresses the same fear faster. Also concede something real, because a response that offers nothing reads as defensiveness.

**Execute.**

1. **Agree the goal explicitly and first**: fewer customer-impacting incidents from changes. Make it clear I am not defending the status quo.
2. **Bring the incident data.** Classify the last quarter's change-caused incidents by mechanism: was it a code defect, a config change, a migration, a dependency, a capacity issue? Then show what a review board would have caught. In my experience it is close to none, because these failures are not predictable from a design document.
3. **Show the cost of the proposal.** A weekly window means batches of a week, so each release has more changes, each incident has more candidate causes, and MTTR rises - and the hotfix path is gated by the same window, which is the part that hurts most.
4. **Offer the alternative that addresses the same fear with faster feedback**: progressive rollout with automated analysis and abort (Q137), so a bad change reaches 5 percent of traffic rather than 100; tested, fast rollback; expand-contract discipline for anything with a data component (Q142); and risk-based approval - human review where the change touches money, data or auth, automation elsewhere.
5. **Concede something.** A change freeze during the peak week; a heightened-care period with smaller changes and mandatory canary; a design review for changes above a defined risk threshold. Giving a real control back is what makes the counter-proposal credible.
6. **Propose a measurable trial.** Run the alternative for one quarter with agreed metrics - change failure rate, MTTR, incident count, lead time - and commit to adopting their proposal if it does not improve. That reframes the disagreement as an experiment rather than a conflict, and it is very hard to refuse.

**Reflect.** The lesson I would carry: when leadership proposes a control I disagree with, the failure is usually mine - the delivery metrics were not visible enough for them to see what was happening, so they reached for the control they know. The durable fix is to make DORA metrics and incident classification visible continuously, so the conversation happens with shared data before someone proposes a board.

---

### S18. The engineer who deleted the production namespace

> A senior engineer runs a command against the wrong kubeconfig context and deletes a production namespace. Recovery takes 40 minutes. They are visibly distraught. In the postmortem, a director asks what the consequences will be for the individual.

**Clarify (in the room, carefully).** What was the actual customer impact? What made the recovery take 40 minutes rather than four? What was the engineer trying to do, and why was that the reasonable action given what they knew?

**Isolate.** Two things are being tested here and they are not the same. **The technical question** is why a single mistyped command could destroy production and why recovery took 40 minutes. **The cultural question** is whether this organization will have blameless postmortems in future, and that is decided entirely by how the director's question is answered, in public, in that room.

If the individual is punished, every subsequent incident will be reported late, described vaguely and investigated badly. That cost is much larger than this incident.

**Decide.** Answer the director directly and without hedging: the consequence is that we fix the system that permitted it. And then immediately redirect to the substantive findings, because the best defence of blamelessness is a genuinely rigorous analysis.

**Execute.**

1. **In the room**: "The consequence is that we now know a single command from one person's laptop can delete a production namespace, and that our recovery takes 40 minutes. Both are our failures, not theirs. If we punish this, the next person hides it, and we lose the ability to find these." Say it calmly and move on.
2. **Support the engineer privately.** They are already the person most affected. Make sure they are not the one presenting the postmortem if they do not want to be, and check on them a week later.
3. **Do the technical work properly**, and this is what makes the argument stick:
   - **Why did they have delete permission on a production namespace at all?** Standing write access to production is the finding (Q247).
   - **Why did the context switch silently?** Separate credentials per environment, separate accounts, a shell prompt showing the context, and `kubectl` confirmation for destructive verbs in production.
   - **Why 40 minutes?** If everything is in git and reconciled, a deleted namespace should be restored in minutes (Q149). Forty minutes means something was not in git, or the recovery was manual, or PersistentVolumes were lost. That is the most valuable finding in the whole incident.
   - **Was anything unrecoverable?** If a PVC's reclaim policy was `Delete`, data is gone, and that is a separate and serious finding.
4. **Actions with owners and dates**: remove standing production write access in favour of time-bounded, audited break-glass; separate accounts per environment; verify every production resource is reconstructible from git; test namespace recovery as a drill.
5. **Publish the postmortem widely**, with the engineer's agreement, as a demonstration of how these are handled.

**Reflect.** If the organization insists on individual consequences, that is a decision I would push back on firmly and, if it stood, would treat as a serious signal about whether the reliability programme is viable. Blamelessness is not kindness; it is the only way to get accurate information about failures, and an organization that punishes error gets fewer reports rather than fewer errors.

---

### S19. Two teams blocked on each other's release

> The payments team cannot ship until the accounts team deploys a new API field. The accounts team cannot ship until payments stops using a deprecated endpoint. Both have deadlines. Both have escalated to you. Neither reports to you.

**Clarify.** What is the actual dependency in each direction - is it a genuine ordering constraint or an assumption? What are the deadlines driven by, and are they real? Can either change be made backward compatible? Has anyone drawn the sequence out?

**Isolate.** This is a **deployment ordering problem presented as an organizational conflict**, and in almost every case it is solvable technically without either team compromising. The deadlock exists because each change was designed to be atomic rather than incremental (Q144).

The standard resolution: **accounts adds the new field additively and ships it** - a new optional field breaks nothing, so it does not depend on payments at all. **Payments migrates off the deprecated endpoint** at its own pace. **Accounts removes the deprecated endpoint later**, once payments has migrated. Expand-contract across a service boundary. The deadlock evaporates.

**Decide.** Facilitate rather than adjudicate. My job is to get both teams and a whiteboard into a room and draw the sequence, not to decide who wins. If I rule, I create a losing team and I have to keep ruling.

**Execute.**

1. **Get both leads in one room, today.** Escalations that ping-pong through managers take days; the conversation takes forty minutes.
2. **Draw the actual sequence on a board.** Almost always the "circular" dependency is not circular once you separate "add the new thing" from "remove the old thing".
3. **Establish the expand-contract sequence** with named steps and owners, and confirm each step is independently deployable and revertible.
4. **If it is genuinely circular** - which is rare and usually means a shared data format changing in both directions - then it needs a coordinated release with a rehearsed sequence and a rollback plan, and I would help design that. Feature flags on both sides usually convert it back into an ordered sequence.
5. **Write down the agreement**, including dates, so neither team is relying on memory.
6. **Check in two days later.** Facilitated agreements decay.

**Reflect.** The systemic issue is that **the organization has services that are not independently deployable** (`03-microservices` Q180), and this will recur. The durable fixes: a published compatibility policy - additive changes only, deprecation with a stated support window, never remove and add in one release; **contract tests** so a breaking change fails a build rather than a conversation; and consumer-driven contracts so the accounts team knows who uses the deprecated endpoint without asking. I would raise this as a pattern with both teams' leadership rather than as a one-off - the second occurrence is what justifies the systemic fix.

---

### S20. You inherit a platform team that everyone resents

> You take over a six-person platform team. Product teams describe them as a bottleneck, ticket queue times are two weeks, and two platform engineers are actively looking to leave. Leadership's brief is "make them faster".

**Clarify.** What is in the ticket queue, actually - categorized? What proportion is repeat work? Why does each ticket require the platform team? What does the team think the problem is? What are the two who are leaving actually unhappy about? What did the team's remit used to be, and how did it become a queue?

**Isolate.** "Make them faster" is the wrong objective, and accepting it is the first mistake. A six-person team serving 20 product teams through a ticket queue cannot be made fast enough - the queue is the problem, not the throughput. Every improvement in speed increases demand.

Categorizing the queue usually shows that 70-80 percent is a handful of repeated requests: provision a database, add a DNS record, grant access, create an environment, bump a limit. Each of those is a **self-service capability that does not exist**. The remaining 20 percent is genuinely bespoke and is where the team's expertise should go.

The morale problem has the same root: engineers hired to build platforms are doing repetitive interrupt-driven work with no visible progress, and being blamed for the queue they did not create.

**Decide.** Reframe the objective with leadership from "faster tickets" to **"eliminate the categories of ticket"**, and buy the team the space to do it by triaging ruthlessly in the short term. Then run the team as a product team (S15).

**Execute.**

*Weeks 1-2 - understand and stabilize.*

1. **Talk to all six individually.** Understand what they want to be doing and what is grinding them down. Do this before any plan.
2. **Categorize the entire queue** by request type and count. This is the artefact that changes the conversation with leadership.
3. **Talk to four or five product teams.** Understand the pain from the other side, and specifically what they would do if the platform team did not exist.
4. **Immediate triage**: close or defer everything that is not genuinely needed, publish a clear intake process with expectations, and set a WIP limit so the team is not interrupt-driven all day. A rota where one person handles interrupts and the rest are protected is the standard mechanism and it helps within a week.

*Weeks 2-8 - remove the top categories.*

5. **Pick the single biggest ticket category and automate it into self-service.** Not all of them - one, completely, end to end. A visible win in six weeks changes both morale and reputation.
6. **Publish the queue data and the plan**, including to the product teams, so the bottleneck stops being mysterious.
7. **Reset the remit with leadership**: the platform team builds capabilities; it does not perform operations on behalf of teams. Get that stated explicitly and publicly, because it is the thing that lets the team say no.

*Months 2-6 - become a product team.*

8. Work down the categories in order of volume, with a roadmap that product teams can see and influence.
9. **Give the team ownership of outcomes, not tickets** - "time to provision a database" as a metric they own, rather than "tickets closed".
10. **Fix the relationship deliberately**: embed a platform engineer with a product team for a sprint, join incidents, and run a regular forum where product teams shape the roadmap. Resentment is largely an information problem.
11. **Track the anti-metric** (S15): ticket volume and queue time going *down* is the measure of success, not throughput going up.

**Reflect.** On the two engineers leaving: I would be honest with them about the plan and the timeline and ask them to give it a quarter, without pressure. Some will leave anyway and that is a reasonable outcome. What I would not do is promise change I cannot deliver, because the second broken promise costs more than the first departure.

The lesson I would state: a platform team becomes a ticket queue when it is measured on responsiveness rather than on leverage, and the fix is a change of objective agreed with leadership - not a change of effort demanded of the team.

---

## How to use Part C

For each situation, prepare a *real* version from your own experience before the interview. The model answers above are structures, not scripts - an interviewer can tell within thirty seconds whether you are describing something you did or something you read.

For each of your stories, be ready with: the constraint you were under, the option you rejected and why, what it cost, what you would do differently, and a number.
