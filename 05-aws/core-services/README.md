# AWS Core Services

The breadth companion to [05-aws](../README.md). Where the parent pack goes deep on serverless - the Lambda execution model, event delivery semantics, concurrency accounting - this one covers the rest of the estate a Solution Architect is expected to know cold: **EC2, EBS, EFS and FSx, the load balancer family, Auto Scaling, Route 53, VPC connectivity at scale, RDS and Aurora operations, the analytics and purpose-built data services, container platforms, the migration service family, and the governance and cost tooling.**

Two different jobs, and they are worth naming:

| | [05-aws](../README.md) | This pack |
| --- | --- | --- |
| Shape | Depth on a narrow surface | Breadth across the estate |
| Question | "What happens at `INIT` when SnapStart restores?" | "gp3 or io2, and what is the deciding number?" |
| Fails you by | Not knowing a mechanism | Not knowing a service exists |

Interviews punish both. The serverless pack protects you against the follow-up question; this one protects you against the question you did not see coming, because the interviewer's estate runs on EC2 and Aurora rather than on Lambda.

---

## Where this sits

```
01-java Q182-197        the AWS first pass - service names and one-line trade-offs
   |
   v
core-services (here)    the whole estate, one level deeper than a service list
   |
   v
05-aws                  serverless mechanisms, quotas, failure modes, cost arithmetic
```

Read this pack **before** the parent if your AWS experience is mostly containers and managed databases, and **after** it if your experience is mostly serverless and you need the breadth. Either order works; they are written to be independent.

### Assumed known

| From | What |
| --- | --- |
| `01-java` Q182 | ECS Fargate versus EKS versus Lambda versus EC2 as a one-line trade-off |
| `01-java` Q187-188 | RDS versus Aurora versus DynamoDB, and what a partition key is for |
| `01-java` Q191 | VPC subnets, NAT, endpoints, security groups versus NACLs |
| `01-java` Q193-194 | S3 storage classes, target tracking versus step scaling |
| `05-aws` Categories 1-3 | Accounts and Organizations, workload identity, VPC fundamentals |

Nothing in the parent pack is restated here. Where a topic appears in both - VPC, S3, compute selection, cost - **this pack is the breadth pass and the parent is the depth pass**, and the question here starts from the service catalogue rather than from the mechanism.

### Scope boundary

- **Serverless mechanisms** - Lambda internals, event source mappings, Step Functions, DynamoDB modelling - belong to [05-aws](../questions.md). Category 11 here covers container platform *selection*, not Lambda.
- **The security control plane** - IAM policy evaluation, KMS key policies, GuardDuty, CloudTrail forensics - belongs to [11-security](../../11-security/questions.md) Category 13.
- **SQL, indexing, the optimizer and MVCC** belong to [06-database](../../06-database/questions.md). Category 9 here is about *operating* RDS and Aurora on AWS, not about relational internals.
- **Kubernetes operations, Terraform state and pipeline mechanics** belong to [07-devops](../../07-devops/questions.md). Category 11 here stops at "which platform, and why".
- **Whole-system design rehearsals** belong to [04-system-design](../../04-system-design/README.md). Category 14 here is service selection under constraints.

**The answer frameworks are not repeated.** The four-layer technical answer, CIDER for scenarios and STAR-L for behavioral questions are defined once in [../../01-java/README.md](../../01-java/README.md).

---

## Files

| File | Purpose |
| --- | --- |
| [questions.md](questions.md) | 220 questions across 14 categories |
| [answers.md](answers.md) | Model answers, every question scripted |
| [scenario-questions.md](scenario-questions.md) | Core-service incidents and service-selection exercises |
| [cheatsheet.md](cheatsheet.md) | Instance types, volume types, decision tables, limits |
| [quiz.html](quiz.html) | Interactive flashcard version |

The roadmap, the interviewer-themes section and the cloud story bank live in the [parent README](../README.md) and apply to both packs. This pack has no story questions of its own for that reason - every question here has a scripted answer.

### Numbering

Questions restart at `Q1` and are numbered `Q1`-`Q220` within this pack. A bare `Q68` in these files means *this* pack. References to the parent are written explicitly as **"serverless pack Q68"** and link to [../answers.md](../answers.md).

### quiz.html

```bash
python tools/build-quiz.py 05-aws/core-services
```

---

## What this pack is really testing

Breadth questions look easy and are not. Four things separate a good answer:

1. **Naming the deciding number.** "gp3 or io2" is not a preference, it is a threshold - 16,000 IOPS, and the durability requirement. Anyone can list volume types; the answer is the number at which you switch.
2. **Knowing what the service replaced.** Every AWS service exists because something before it was painful. If you can say what Transit Gateway replaced and why the replacement was worth it, you understand the service; if you can only recite its features, you have read the page.
3. **Refusing the service.** Elastic Beanstalk, Global Accelerator, FSx for Lustre and Outposts are all right answers occasionally and wrong answers usually. Knowing when *not* to reach for something is the harder half of breadth.
4. **The operational tail.** Not "what is an Auto Scaling group" but what happens to an in-flight request during a scale-in, and which of the four settings involved you would actually change.

---

## Self-check

- [ ] I can pick an EC2 purchasing model for a workload from its shape, and say what Spot costs me in engineering.
- [ ] I can choose between gp3, io2 and st1 with the deciding number, not a preference.
- [ ] I can state the three real differences between ALB and NLB, and one case where the obvious choice is wrong.
- [ ] I can name all seven Route 53 routing policies and one production use for each.
- [ ] I can draw a hub-and-spoke network with Transit Gateway and say what it costs per GB.
- [ ] I can explain what a Multi-AZ RDS failover actually does to open connections, and how long it takes.
- [ ] I can choose between ECS on Fargate, EKS and Beanstalk for a given team, and defend the team-shaped part of the answer.
- [ ] I can pick a migration service per workload from the 7 Rs, and say when Snowball beats the network.
- [ ] I can name the tool for each of: which instance is oversized, which resource is non-compliant, what the bill will be next month.
