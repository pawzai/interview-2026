# AWS Interview Preparation Pack

Cloud architecture depth for **Principal Engineer / Technical Lead / Solution Architect** interviews: account and organization structure, workload identity, VPC and connectivity, edge and API entry, the Lambda execution model, compute selection, the event-driven backbone, event source mapping mechanics, orchestration with Step Functions, data services, S3 as an architectural tier, observability, quotas and failure modes, multi-region topology, infrastructure and delivery, cost engineering, and Well-Architected review practice.

The material is anchored **serverless-first** - **Lambda, API Gateway, EventBridge, Step Functions, DynamoDB and S3** - with ECS Fargate, EKS and Aurora treated as the boundary cases you must know when to reach for, and Azure or GCP named only where the mechanism genuinely differs. That is deliberate. Serverless is where AWS knowledge is hardest to fake: the execution model, the concurrency accounting, the retry topology and the pricing arithmetic are all specific, all measurable, and all things a candidate who has only run containers on AWS will get wrong within two follow-up questions.

---

## Read [01-java](../01-java/README.md), [04-system-design](../04-system-design/README.md) and [11-security](../11-security/README.md) first

This pack is **not** an introduction to AWS. It starts where the cloud material in the earlier packs stopped, and nothing there is restated.

| Assumed known | Where this pack takes it |
| --- | --- |
| `01-java` Q182 ECS Fargate versus EKS versus Lambda versus EC2 | Category 6 - the boundary conditions in both directions, and the cases where the framework gives the wrong answer |
| `01-java` Q183 Lambda cold starts in Java | Category 5 - the init and invoke phases, SnapStart's restore semantics, and what provisioned concurrency does not fix |
| `01-java` Q184-186 SQS, SNS, EventBridge, Kinesis, FIFO, DLQs | Categories 7 and 8 - delivery semantics per service, event source mapping internals, partial batch failure, replay |
| `01-java` Q187-188 RDS versus Aurora versus DynamoDB, partition keys, GSI versus LSI | Category 10 - single-table access-pattern design, adaptive capacity, Aurora Serverless v2 scaling, connection storms |
| `01-java` Q189-190 IAM roles, identity versus resource policies | Category 2 - how each compute model actually obtains credentials, and cross-account patterns as architecture |
| `01-java` Q191 VPC subnets, NAT cost, endpoints, security groups | Category 3 - address planning, Hyperplane ENIs, PrivateLink, and whether the function belongs in a VPC at all |
| `01-java` Q192 Secrets Manager versus Parameter Store | Category 15 - retrieval cost inside a function, caching layers, and rotation without a redeploy |
| `01-java` Q193 S3 storage classes and lifecycle | Category 11 - request-rate scaling, transition economics, Intelligent-Tiering's break-even, event notification semantics |
| `01-java` Q194 target tracking versus step scaling | Categories 6 and 13 - what "scaling" means when there is no instance to scale, and where the real limit lives |
| `01-java` Q195 multi-region active-active | Category 14 - global tables conflict resolution, failover asymmetry, and the three problems that stay hard |
| `01-java` Q196-197 the 40 percent bill, Well-Architected pillars | Categories 16 and 17 - attribution mechanics, unit cost, and running a review that produces decisions |
| `11-security` Q213-233 IAM evaluation, KMS, CloudTrail, GuardDuty, IMDSv2 | Category 2 here uses identity as an *architecture* tool and does not re-teach the control plane |
| `04-system-design` Categories 5, 7, 11 caching tiers, queues, geo-distribution | Categories 4, 7 and 14 - the same decisions expressed in specific AWS services with their specific limits |
| `06-database` Category 11 document and wide-column stores | Category 10 - DynamoDB specifics rather than the model in general |
| `07-devops` Categories 11 and 16 Terraform, FinOps | Categories 15 and 16 - CDK and SAM against Terraform, and cost attribution for serverless where there is no instance to tag |

Where a question here overlaps, it starts one level deeper.

**The answer frameworks are not repeated either.** The four-layer technical answer, CIDER for scenarios and STAR-L for behavioral questions are defined once in [../01-java/README.md](../01-java/README.md). Re-read that section before your first mock.

### Scope boundary

The security control plane - IAM policy evaluation order, SCPs and permission boundaries, KMS key policies, CloudTrail forensics, GuardDuty and Security Hub - belongs to [11-security](../11-security/questions.md) Category 13. This pack uses identity as an architectural tool: how a workload gets credentials, and how cross-account boundaries shape a design. Kubernetes operations, Terraform state internals and pipeline mechanics belong to [07-devops](../07-devops/README.md); this pack owns what is AWS-specific about deploying a serverless application. Whole-system design rehearsals belong to [04-system-design](../04-system-design/README.md); Category 17 here is the cloud-architecture subset. Relational and document internals belong to [06-database](../06-database/README.md). Bedrock model behaviour, prompting and evaluation belong to [08-genai](../08-genai/README.md); only the integration and cost shape appear here.

### Companion pack: core services

This pack is serverless-first by design, which leaves a breadth gap that Solution Architect interviews walk straight into: EC2 instance families and purchasing models, EBS volume types, EFS and FSx, the load balancer family, Auto Scaling groups, Route 53 routing policies, Transit Gateway and Direct Connect, RDS operational mechanics, container platform selection, the migration service family, and the governance and cost tooling.

That material lives in **[core-services/](core-services/README.md)** - 220 questions across 14 categories. Treat it as the breadth pass and this pack as the depth pass: if a topic appears in both, core-services tells you when to reach for the service and this pack tells you how it behaves under load. Numbering restarts at Q1 inside the companion, so a bare `Q68` there means the companion; cross-references to this pack are written out as "serverless pack Q68".

---

## Files in this pack

| File | Purpose | When to use |
| --- | --- | --- |
| [README.md](README.md) | Prerequisite map, roadmap, what interviewers probe | Read first |
| [questions.md](questions.md) | 270 questions across 17 categories | Daily drilling |
| [answers.md](answers.md) | Mechanism-level model answers | After attempting yourself |
| [scenario-questions.md](scenario-questions.md) | Cloud incidents, architecture exercises, leadership situations | Mock practice |
| [cheatsheet.md](cheatsheet.md) | Limits, pricing arithmetic and decision tables | Night before, and 30 minutes before |
| [quiz.html](quiz.html) | Interactive flashcard version | Active recall |
| [core-services/](core-services/README.md) | Companion breadth pack: 220 questions on EC2, storage, networking, RDS, containers and migration | Alongside this pack, for Solution Architect breadth |

### quiz.html

Open it directly in a browser - no server, no internet connection needed. Search covers question and answer text, filter by category, difficulty or your own progress, and mark each question Known or Review with progress saved in the browser. Press `/` to focus search.

Generated from the markdown, so the markdown stays the source of truth. After editing any of the three source files:

```bash
python tools/build-quiz.py 05-aws
```

---

## What interviewers actually probe at this level

AWS questions for a principal role are rarely "what is S3". They are testing whether you have built, operated and paid for a cloud estate.

Six recurring themes:

1. **Do you know the execution model, or the console?** The most reliable separator in serverless. A candidate who says "Lambda scales automatically" is mid-level; one who explains that concurrency is `invocations per second x average duration` and that the burst limit is separate from the account limit is senior; one who can say what happens to an in-flight `SIGTERM`, a frozen background thread and a reused `/tmp` between invocations is principal.
2. **Where does the managed service stop managing?** Retries you did not configure, an at-least-once delivery you treated as exactly-once, a stream shard that stalls on one bad record, a Synced-looking stack in front of a broken API. Every one of these is a real incident and a real question.
3. **Every limit is an architectural constraint.** Concurrency, burst rate, payload size, ENI attachment time, shard throughput, partition throughput, API Gateway's 29-second timeout. Interviewers probe whether you design against the quota table or discover it in production.
4. **Cost is a design property, not a cleanup task.** NAT gateway data processing, cross-AZ transfer, CloudWatch log ingestion, DynamoDB on-demand versus provisioned, a Lambda oversized to 3 GB "for safety". You should be able to do the arithmetic out loud and name the unit cost of a request.
5. **Correct answers are constraint-shaped.** Traffic shape, spikiness, latency target, compliance regime, team size and operational maturity. A candidate who recommends multi-region active-active or EKS before asking for those is guessing.
6. **Well-Architected is a conversation, not a checklist.** The pillars are only useful when you can name the trade-off you accepted, the risk you left open, and the business reason. "We are not buying 99.99 for this workload" is a principal-level sentence.

---

## Study roadmap

### Week 1 - Foundations: accounts, identity and network

Categories 1, 2 and 3. Be able to draw a multi-account landing zone and justify each boundary, explain how a Lambda, an ECS task and an EKS pod each obtain credentials, and plan a VPC address space that can absorb a second region.

### Week 2 - Entry and execution

Categories 4 and 5. The densest material in the pack. Work every `[T]` twice. Be able to narrate an HTTP request from client to Lambda handler naming every hop, and describe the lifecycle of an execution environment from `INIT` to shutdown from memory.

### Week 3 - Compute selection and events

Categories 6, 7 and 8. Form a defensible position on when Lambda is wrong - you will be asked - and be able to explain partial batch failure and poison-record handling for both SQS and Kinesis without hedging.

### Week 4 - Orchestration and data

Categories 9, 10 and 11. Be able to design a saga in Step Functions with its compensation path, model a three-access-pattern service on a single DynamoDB table out loud, and explain the connection-storm problem and its two fixes.

### Week 5 - Operations, reliability and multi-region

Categories 12, 13 and 14. Be able to compute a concurrency requirement from a request rate, describe the retry topology of a full request path hop by hop, and state honestly what active-active costs you.

### Week 6 - Delivery, cost and design

Categories 15 and 16, then work only from [scenario-questions.md](scenario-questions.md). Category 17 is the rehearsal.

---

## Your cloud story bank

Prepare these with real detail from Verizon India and Sonata Software. Generic answers are transparent at 19 years of experience.

1. A workload you moved to or from serverless, with the reason and the measured result.
2. A cloud production incident you led end to end - throttling, a regional degradation, a runaway cost - including the permanent fix.
3. An architecture where you chose the managed service over building, and one where you refused, each with the deciding constraint.
4. A migration onto AWS you ran without a big-bang cutover, including the rollback point you kept.
5. A cost reduction with the number, the mechanism, and what you refused to cut.
6. A multi-account or landing-zone change you drove, and the resistance you handled.
7. A latency problem you traced to a specific AWS mechanism - a cold start, an ENI attachment, a cross-AZ hop, a hot partition.
8. A DR capability you actually exercised, with the measured RPO and RTO rather than the target.
9. A quota or limit that shaped an architecture, and how you found it.
10. A cloud standard you drove across teams you did not own: a shared construct library, an account baseline, a tagging policy.

---

## Self-check before the interview

- [ ] I can narrate the full lifecycle of a Lambda execution environment, naming `INIT`, `INVOKE` and `SHUTDOWN` and what persists across each.
- [ ] I can compute the concurrency a workload needs from its request rate and duration, and say what happens at the burst limit.
- [ ] I can explain partial batch failure for SQS and for Kinesis, and what a poison record does to a shard.
- [ ] I can name every retry in a CloudFront to API Gateway to Lambda to DynamoDB path and say which ones I would turn off.
- [ ] I can model three access patterns on one DynamoDB table and explain what makes a partition key hot.
- [ ] I can explain why a Lambda in a VPC used to be slow and what changed, and when a VPC is still the wrong choice.
- [ ] I can price a request path end to end within an order of magnitude, and name the line item most people forget.
- [ ] I can state when I would refuse multi-region active-active, out loud, to a business stakeholder.
- [ ] I know the RPO and RTO of the systems I own, and I have run the failover to prove them.
- [ ] I have three stories with concrete numbers attached.
