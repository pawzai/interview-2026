# DevOps Interview Preparation Pack

Delivery and operations depth for **Principal Engineer / Technical Lead / Solution Architect** interviews: pipeline design and artifact promotion, source control strategy, CI mechanics, the software supply chain, container and image engineering, Kubernetes internals and cluster operations, configuration and secrets, release and progressive delivery, GitOps, infrastructure as code, observability and SLOs, alerting and incident response, reliability and disaster recovery, pipeline and runtime security, cost and FinOps, and platform engineering.

The material is anchored on **Kubernetes/EKS, GitHub Actions, Argo CD, Terraform and Prometheus/OpenTelemetry**, with Jenkins, GitLab CI, Helm, Datadog and ECS contrasts called out wherever the mechanism genuinely differs. That is deliberate: an interviewer can tell within two questions whether you learned "DevOps" or learned one platform's tutorial, and the way to prove the former is to describe a mechanism and then say how another tool does it differently.

---

## Read [01-java](../01-java/README.md), [02-spring](../02-spring/README.md) and [03-microservices](../03-microservices/README.md) first

This pack is **not** an introduction to CI/CD or Kubernetes. It starts where the operational material in the earlier packs stopped, and nothing there is restated.

| Assumed known | Where this pack takes it |
| --- | --- |
| `01-java` Q198 ideal CI/CD pipeline, stage by stage | Category 1 - build-once-deploy-many, artifact promotion, why a green 55-minute pipeline is a defect |
| `01-java` Q201 trunk-based versus GitFlow | Category 2 - the preconditions that make trunk-based safe, and the monorepo build graph |
| `01-java` Q202-203 image optimization, container memory | Category 5 - layer digests, layered JARs, `MaxRAMPercentage`, CFS throttling, native images |
| `01-java` Q204-205 probes, requests versus limits | Category 6 - the reconciliation loop, QoS and eviction order, the graceful-shutdown race |
| `01-java` Q206 Terraform versus CloudFormation, drift | Category 11 - state internals, `count` versus `for_each`, module refactors, policy as code |
| `01-java` Q207-210 observability, SLOs, alerts, postmortems | Categories 12 and 13 - cardinality cost, histogram error, burn-rate windows, incident command |
| `01-java` Q196 the AWS bill that jumped 40 percent | Category 16 - attribution, requests-versus-usage, spot, and what you refuse to cut |
| `02-spring` Q27-42 `ConfigData`, `spring.config.import`, secrets and `/actuator/env` | Category 8 - where the secret lives at rest and in the pod, and rotation without downtime |
| `03-microservices` Q116-118 health checks, graceful shutdown | Category 6 - the exact `DELETE` to exit sequence and why endpoint removal races `SIGTERM` |
| `03-microservices` Q121-136 discovery, gateway, mesh | Category 7 - kube-proxy, EndpointSlice, Gateway API, mesh cost and mTLS rotation |
| `03-microservices` Q137-154 tracing, sampling, cardinality | Category 12 - Prometheus internals, the Collector, exemplars, and observability spend |
| `03-microservices` Q169 SBOM, signed images, CVE response | Category 4 - SLSA levels, provenance, VEX, and the gap between a signed image and a running container |
| `03-microservices` Q171-186 deployment versus release, canary, expand-contract | Categories 9 and 10 - the controller state machine, canary statistics, and GitOps reconciliation |
| `03-microservices` Q101-120 resilience, chaos, error budgets | Category 14 - capacity arithmetic, load-test lies, DR patterns, and failover asymmetry |

Where a question here overlaps, it starts one level deeper.

**The answer frameworks are not repeated either.** The four-layer technical answer, CIDER for scenarios and STAR-L for behavioral questions are defined once in [../01-java/README.md](../01-java/README.md). Re-read that section before your first mock.

### Scope boundary

Cloud service selection, VPC design, IAM policy structure and the Well-Architected pillars belong to `05-aws`; only the pipeline's own identity (OIDC federation from the runner) is here. Application-level resilience patterns - circuit breakers, bulkheads, retry budgets - belong to `03-microservices`; this pack owns what the platform does around them. Database migration mechanics at the SQL and lock level belong to `06-database`; Category 9 here owns the deployment sequencing around them. Whole-system rehearsals belong to `04-system-design`; Category 17 here is the delivery-platform subset.

---

## Files in this pack

| File | Purpose | When to use |
| --- | --- | --- |
| [README.md](README.md) | Prerequisite map, roadmap, what interviewers probe | Read first |
| [questions.md](questions.md) | 270 questions across 17 categories | Daily drilling |
| [answers.md](answers.md) | Mechanism-level model answers | After attempting yourself |
| [scenario-questions.md](scenario-questions.md) | Delivery and production incidents, design exercises, leadership situations | Mock practice |
| [cheatsheet.md](cheatsheet.md) | Fast revision reference | Night before, and 30 minutes before |
| [quiz.html](quiz.html) | Interactive flashcard version | Active recall |

### quiz.html

Open it directly in a browser - no server, no internet connection needed. Search covers question and answer text, filter by category, difficulty or your own progress, and mark each question Known or Review with progress saved in the browser. Press `/` to focus search.

Generated from the markdown, so the markdown stays the source of truth. After editing any of the three source files:

```bash
python tools/build-quiz.py 07-devops
```

---

## What interviewers actually probe at this level

DevOps questions for a principal role are rarely "what is a pod". They are testing whether you have been the person paged when the platform broke.

Six recurring themes:

1. **Do you understand the control loop, or do you memorize commands?** The single most reliable separator. A candidate who says "run `kubectl rollout restart`" is mid-level; a candidate who explains that a controller compares desired to observed state on every resync is senior; a candidate who can say what the loop does *not* observe - and therefore what Kubernetes will happily report as healthy while the service returns 500s - is principal.
2. **Where does the pipeline lie to you?** Green builds with quarantined tests, path filters that skip the test that mattered, a canary that passes at 5 percent and fails at 100, a Synced-and-Healthy Argo application in front of a broken service. Every one of these is a real incident and a real question.
3. **Everything automated is also an attack surface.** A build agent with production credentials is production. Interviewers probe whether you can reason about what an attacker gets when they compromise CI, not whether you can name three scanners.
4. **The failure was operational, not architectural.** A liveness probe restarting a service under load, a PodDisruptionBudget hanging a drain, a stuck Terraform lock, a `user_id` label taking down Prometheus, a CFS quota making p99 worse. These are the incidents that actually happen.
5. **Correct answers are constraint-shaped.** Team size, deploy frequency, regulatory posture, on-call maturity and the cost of an outage minute. A candidate who recommends a service mesh or a canary controller before asking for those is guessing.
6. **Reliability is a budget, not an aspiration.** Availability targets, error budgets, RPO and RTO with a real restore behind them, and the ability to say "we should not buy 99.99" out loud to a business stakeholder. Reversibility and the honest number are what you are being assessed on.

---

## Study roadmap

### Week 1 - Pipeline, source control and CI

Categories 1, 2 and 3. Be able to draw a pipeline stage by stage and justify the order, argue trunk-based development from its preconditions rather than its virtues, and explain how a monorepo computes its affected set.

### Week 2 - Supply chain and containers

Categories 4 and 5. Work every `[T]` twice. Be able to explain the JVM's container-aware heap sizing and where a pod's memory actually goes when the heap graph looks fine.

### Week 3 - Kubernetes

Categories 6 and 7. The densest material in the pack. Be able to narrate `kubectl apply` to running container out loud, and describe the endpoint-removal race during a graceful shutdown from memory.

### Week 4 - Config, release and GitOps

Categories 8, 9 and 10. Form a defensible position on automatic rollback and on rolling back migrations - you will be asked - and be able to name what Argo CD does and does not know about a running service.

### Week 5 - Terraform, observability and incidents

Categories 11, 12 and 13. Be able to compute an error budget and a multi-window burn-rate alert with the arithmetic rather than the folklore, and design Alertmanager routing that turns a cluster failure into one page.

### Week 6 - Reliability, security, cost and design

Categories 14, 15 and 16, then work only from [scenario-questions.md](scenario-questions.md). Category 17 is the rehearsal.

---

## Your delivery story bank

Prepare these with real detail from Verizon India and Sonata Software. Generic answers are transparent at 19 years of experience.

1. A pipeline you took from slow to fast, with the before and after numbers and what you actually removed.
2. A production incident you led end to end, including the permanent fix and what it cost to build.
3. A release process you changed - approval gates removed, canary introduced, freeze abolished - and the change failure rate before and after.
4. A migration you ran onto a new platform without a big-bang cutover, including the rollback point you kept.
5. An outage caused by the platform rather than the code - a probe, a limit, a drain, a config change - and the guardrail that came out of it.
6. An observability or alerting change that reduced pages, with the number.
7. A security control you introduced into the pipeline, and the resistance you handled.
8. A cost reduction on the delivery or runtime platform, with the number and what you refused to cut.
9. A restore or failover you actually performed, or a drill you ran, with the measured RTO.
10. A standard you drove across teams you did not own: a shared workflow, a base image, a deployment template.

---

## Self-check before the interview

- [ ] I can narrate `kubectl apply` to a running container, naming each component in order.
- [ ] I can describe the exact sequence from pod `DELETE` to container exit, and where the endpoint-removal race sits in it.
- [ ] I can explain why a CPU limit can raise p99 latency while lowering utilization.
- [ ] I can write the expand-contract deployment sequence for a column rename across two services, including the rollback point.
- [ ] I can compute the error budget for 99.9 percent and give the burn-rate windows I would alert on.
- [ ] I can explain what a `user_id` label does to Prometheus, and what I would do when per-customer visibility is genuinely required.
- [ ] I can walk through the OIDC token exchange from a GitHub Actions job to an AWS role, and name the trigger that makes it dangerous.
- [ ] I can state what an attacker gets from a compromised build agent, and which controls bound the damage.
- [ ] I know our RPO and RTO, and I have run the failover to prove them.
- [ ] I have three stories with concrete numbers attached.
