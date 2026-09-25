# Answers

Model answers for [questions.md](questions.md). Numbers match the question numbers exactly.

Answers follow the four-layer structure defined in [../01-java/README.md](../01-java/README.md): direct answer, mechanism, trade-off, experience hook. Hooks are written as *italic placeholders* - replace them with real detail from Verizon India and Sonata Software.

Unqualified statements refer to **Lambda, API Gateway, EventBridge, Step Functions, DynamoDB and S3**; other services are named explicitly. Numbers for quotas and prices are the defaults at the time of writing - always say "the default is X, and it is adjustable" rather than quoting a figure as immutable. Q261-265 are worked as full design exercises in [scenario-questions.md](scenario-questions.md). Q266-270 are story questions with no scripted answer.

---

## 1. Accounts, Organizations, landing zones and the responsibility line

### Q1. The shared responsibility line, and how it moves

AWS is responsible for security **of** the cloud - the hardware, the hypervisor, the physical facility, the managed service's own software. You are responsible for security **in** the cloud - your data, your identity configuration, your network rules, your code.

The interesting part is how the line moves as you go up the abstraction stack:

| Model | You own | AWS owns |
| --- | --- | --- |
| EC2 | Guest OS patching, runtime, application, firewall rules, encryption choices | Hypervisor, hardware, network fabric |
| ECS on EC2 | Container image, task definition, *and still* the instance OS | The orchestrator control plane |
| ECS Fargate | Container image and task configuration | The host OS and the runtime substrate |
| Lambda | Function code, dependencies, IAM, configuration | Runtime patching, scaling, the execution environment |
| DynamoDB / S3 | Data model, access control, encryption keys if you bring them | Everything operational: replication, durability, patching |

Two things stay yours at every level, which is the point most candidates miss: **identity and access configuration**, and **your data and its classification**. Fargate does not patch your base image's application libraries, and Lambda does not stop you from granting `s3:*` on `*`.

*Hook: a workload where moving up this stack removed a class of operational work you were carrying, and the control you had to add instead.*

### Q2. Why the account is the primary isolation boundary

An IAM policy is a *grant* inside a blast radius; an account *is* the blast radius.

Three properties an account gives you that a policy cannot:

1. **Quota and limit isolation.** Lambda concurrency, API rate limits and service quotas are per-account-per-region. A runaway batch job in a shared account starves production; in a separate account it cannot.
2. **A hard default-deny.** Cross-account access requires an explicit grant on *both* sides - identity policy and resource policy or trust policy. Inside one account, a single over-broad identity policy is sufficient to reach anything. The account makes the safe case the default.
3. **Blast radius for mistakes and for credentials.** A leaked credential, a `terraform destroy` in the wrong directory, or an IAM misconfiguration is bounded by the account. Billing, CloudTrail and Config are also naturally partitioned, which makes attribution and forensics tractable.

The trade-off is real: more accounts means more baseline to manage, more cross-account plumbing, more places to look during an incident. That cost is why the answer is "an account per environment per workload domain", not "an account per resource".

*Hook: an incident whose blast radius was set by an account boundary - in either direction.*

### Q3. An account structure for 60 services and 200 engineers

I would organize by **environment first, domain second**, with shared-service accounts pulled out.

```
Root (management account - billing and Organizations only, no workloads)
├── Security OU
│   ├── log-archive        (CloudTrail, Config, VPC flow logs - write-only from others)
│   ├── security-tooling   (GuardDuty/Security Hub delegated admin, IR tooling)
├── Infrastructure OU
│   ├── network            (Transit Gateway, Direct Connect, central egress, private zones)
│   ├── shared-services    (ECR, artifact store, internal PyPI/Maven, shared CI)
├── Workloads OU
│   ├── Prod OU:    prod-payments, prod-orders, prod-platform     (one per domain, ~4-6)
│   ├── NonProd OU: dev-payments, staging-payments, ...
├── Sandbox OU     (per-engineer or per-team, low SCP, hard budget, auto-nuke)
└── Suspended OU   (SCP denying everything, for decommissioning)
```

Who deploys where: **nobody has standing human write access to a prod account.** Deployment happens through a pipeline role assumed via OIDC from CI, scoped to that account. Humans get read-only plus a break-glass role that is time-boxed, requires MFA, and pages when assumed. Non-prod accounts get developer roles with real permissions so people can work.

The grouping is by domain rather than by service because 60 accounts per environment is unmanageable (Q4), and because deployment isolation is what matters - two services owned by the same team with the same on-call rotation do not need an account between them.

*Hook: the account structure you inherited, what you changed first, and why that was the highest-value change.*

### Q4. One account per service `[T]`

What breaks, roughly in order:

1. **Networking.** 60 VPCs need connectivity. You now need Transit Gateway attachments, route propagation and IP address planning for 60 CIDRs per region, and TGW attachment hours plus data processing become a visible line item.
2. **Quotas on the meta-layer.** Accounts per organization, VPCs, TGW attachments, IAM roles for the baseline, and the number of CloudFormation StackSets targets all grow linearly. Each new account also needs the full day-zero baseline (Q7), so the baseline itself becomes a distributed deployment problem.
3. **Human cognition during an incident.** "Which account is the order-status service in" becomes a question you ask at 3 a.m.
4. **Cost.** Not the accounts themselves - those are free - but the per-account fixed costs: NAT gateways, interface endpoints (per-AZ hourly), Config recorders, GuardDuty detectors. Six interface endpoints across three AZs in 60 accounts is a serious number for zero traffic.

What I would propose instead: **account per environment per bounded context**, sized so that each account maps to one team's on-call scope. Then use IAM, tags and separate CloudFormation stacks for per-service isolation inside it. If a specific service has a genuinely different risk profile - it holds cardholder data, it is subject to a different regulator, it has a wildly different quota profile - it earns its own account on that argument, not by default.

*Hook: a proliferation you either created or unwound, and the specific pain that forced the change.*

### Q5. SCP versus permission boundary versus pipeline check

All three restrict, but they answer different questions.

| Control | Question it answers | Applies to | Who owns it |
| --- | --- | --- | --- |
| SCP | "Is this action *possible* in this account?" | Every principal in the account, including the root user | Security / platform, centrally |
| Permission boundary | "Can this principal ever exceed this ceiling, even if someone grants it more?" | A specific IAM principal | Platform, on delegated roles |
| Pipeline check (`cfn-guard`, OPA, Checkov) | "Is this *configuration* acceptable?" | The resource definition, before it exists | The delivery platform |

What belongs in an SCP: things that must never happen anywhere in the account. Deny leaving the organization, deny disabling CloudTrail/GuardDuty/Config, deny regions you do not operate in, deny deleting log-archive resources, deny creating IAM users with access keys. These are **coarse, stable and few** - an SCP that changes weekly is in the wrong place.

What belongs in a permission boundary: the ceiling for delegated administration. You let a team create roles for their Lambdas, but attach a boundary so the roles they create cannot exceed the team's own permissions - this is the mechanism that makes "teams manage their own IAM" survivable (Q30).

What belongs in a pipeline check: everything shaped like "S3 buckets must have encryption and Block Public Access", "no security group with `0.0.0.0/0` on 22", "every resource must carry `owner` and `cost-center` tags". These are numerous, change often, and need a helpful error message - all of which SCPs are bad at.

The failure mode is putting configuration policy into SCPs: you end up with a 4-KB SCP nobody can reason about, and an interactive debugging session every time a deploy fails with `AccessDenied` and no explanation.

*Hook: a guardrail you moved from one of these layers to another, and what improved.*

### Q6. Control Tower versus hand-rolled Organizations

Control Tower gives you an opinionated, AWS-maintained landing zone: the Organizations structure, the log-archive and audit accounts, CloudTrail and Config aggregation, a set of preventive (SCP) and detective (Config rule) controls it calls guardrails, Account Factory for provisioning, and drift detection against all of it.

What it genuinely buys: **you do not maintain the baseline.** New controls arrive, the account provisioning flow is supported, and there is a defensible answer for an auditor asking who verifies the structure. For an organization without a dedicated cloud platform team, that is worth a lot.

What it takes away:

- **Control over the shape.** Control Tower has opinions about OU layout and account naming, and fighting them is unpleasant.
- **IaC purity.** The landing zone is managed by Control Tower, not by your Terraform. You end up with a two-tool world - Control Tower for the frame, your IaC for the workloads - and drift between them is a real operational category. AFT (Account Factory for Terraform) exists precisely because this hurt.
- **Speed of change.** Landing zone updates are a versioned, sequential operation across all accounts, which is exactly what you want for safety and exactly what you resent when you need one change.

My rule: if you have fewer than roughly five people who will ever own the organization layer, use Control Tower. If you have a platform team that already runs Terraform at scale and needs unusual structure - multiple partitions, an odd regulatory split - hand-roll Organizations with StackSets and own it properly. What I would not do is start hand-rolled with the intention of "adding Control Tower later"; enrolling an existing messy organization is far harder than starting inside it.

*Hook: a landing-zone decision you made, and whether the maintenance burden landed where you expected.*

### Q7. Day zero for a new account

Before a single workload resource exists, the account should already have:

1. **CloudTrail** (organization trail, all regions, management plus selected data events) delivering to the central log archive, which the account itself cannot delete from.
2. **Config** recorder plus the conformance pack for your baseline, aggregating to the audit account.
3. **GuardDuty** enabled in every region you allow, with findings to the security account.
4. **IAM Access Analyzer** at the organization zone of trust.
5. **SCPs from the parent OU** applied - region deny, guardrail denies, root-user deny.
6. **No IAM users.** Human access is IAM Identity Center permission sets only; machine access is roles with OIDC or service-linked trust.
7. **A deploy role** trusted by your CI's OIDC provider, scoped with a permission boundary.
8. **Default EBS encryption on, S3 Block Public Access at the account level, IMDSv2 required** by default.
9. **Budget and cost anomaly detection** with an owner email that is a real distribution list, plus mandatory cost-allocation tags activated.
10. **The default VPC deleted**, and either no VPC or the standard VPC from your network module with flow logs enabled.
11. **Alternate contacts** (security, billing, operations) set to team addresses rather than one person's mailbox.

The reason this list matters at interview: everything on it is far cheaper to have from minute zero than to retrofit. Retrofitting CloudTrail means you have no history for the period you most want to investigate; retrofitting "no IAM users" means a migration.

*Hook: something missing from an account baseline that you discovered during an incident or an audit.*

### Q8. Consolidated billing across member accounts

All member accounts roll into the management account's single bill, and three mechanisms operate across the boundary:

- **Volume tiering** aggregates usage. S3 and data-transfer tiers are computed on the organization's combined usage, so 40 accounts each with modest S3 usage reach better tiers together than separately. This is automatic and always beneficial.
- **Reserved Instances and Savings Plans share by default.** An unused RI or Savings Plan commitment in account A is applied to matching usage in account B, within the same billing family. This is why you buy commitments centrally and why "each team buys its own" is usually wrong.
- **Credits and discounts** apply organization-wide.

Two operational consequences people trip on. First, **sharing can be disabled** per account (RI/SP discount sharing), and you sometimes want to - a team that bought a commitment for a specific workload will be unhappy when it silently subsidizes another team's dev environment. Second, **sharing makes showback confusing**: the account that consumed the discount gets the cheap rate, not the account that paid for the commitment. Cost Categories and amortized-cost views exist to fix the reporting, and you have to set them up deliberately (Q255).

*Hook: a commitment purchase decision, who owned it, and how you handled the internal accounting.*

### Q9. Two teams sharing an account `[T]`

The mechanism is that **a shared account has no reliable way to answer "who owns this resource, and what depends on it"**, and every month makes it worse:

- Resources are created by roles, not people, and CloudTrail retention is finite. After 90 days, the creation event is gone.
- Tags were advisory, so a meaningful fraction of resources have none - and the ones created by console clicks during an incident definitely have none.
- IAM policies accumulate to the union of both teams' needs, because it was faster than scoping. Nobody can now tell which permissions are load-bearing.
- Shared quotas mean each team's scaling behaviour is coupled to the other's, so "can I raise concurrency" becomes a cross-team negotiation.
- Security groups reference each other, and a subnet holds workloads from both teams, so the network cannot be untangled without downtime.

The result is the observed one: **deletion becomes unsafe**, so nothing gets deleted, so cost grows and the estate becomes archaeologically layered. That is a specific, predictable outcome, not bad luck.

The fixes, in order of leverage: mandatory tagging enforced by SCP or pipeline check from day one (Q14), separate accounts at the point where on-call ownership diverges, and IaC as the only creation path so that "who owns this" is answered by a repository rather than by memory.

*Hook: an untangling you led, how you established ownership, and what you did with the genuinely unattributable resources.*

### Q10. What is independent across regions, AZs and Local Zones

**Regions** are the strong boundary. Separate control planes, separate data planes, no automatic data replication, and independent service quotas. They are connected by the AWS backbone but fail largely independently - "largely" because a handful of global services are homed in a region (Q13, Q228), which is the caveat that matters.

**Availability Zones** within a region are separate physical facilities with independent power, cooling and physical security, connected by dedicated, high-bandwidth, low-latency links (single-digit-millisecond, usually sub-millisecond). What is *shared* across AZs in a region:

- The **regional control plane** - the EC2, Lambda and DynamoDB APIs. An AZ failure is survivable; a regional control-plane impairment is felt everywhere in the region (Q213).
- **Regional services' data planes** - S3, DynamoDB, SQS and Lambda are regional and already multi-AZ. You do not architect AZ redundancy for them; you consume it.
- Some **networking components** are regional: a NAT gateway is *zonal* (a common surprise), an ALB is regional with zonal nodes, a Transit Gateway is regional.

**Local Zones** are extensions of a region placed in a metro for single-digit-millisecond latency to that city, offering a subset of services, with the parent region's control plane. So a Local Zone gives you latency, not independence - it depends on its parent region. Same for Outposts, which additionally depends on your own facility.

The design bug this prevents: treating a NAT gateway or a zonal endpoint as regional, so a single AZ event takes out egress for the whole VPC.

*Hook: an AZ-level event you observed and which components handled it silently.*

### Q11. `us-east-1a` is not the same place for two accounts `[T]`

AZ *names* (`us-east-1a`) are mapped independently per account, so that AWS can spread customers evenly across physical zones rather than having everyone pile into "a". The stable identifier is the **AZ ID** (`use1-az4`), which is consistent across accounts.

Where it matters:

- **Cross-account VPC peering or shared subnets.** If you and a partner account both place resources in "us-east-1a" assuming co-location, you may be paying cross-AZ data transfer and adding a network hop for every request. With VPC sharing via RAM, subnets are shared by AZ ID precisely to avoid this.
- **Correlating a capacity event or an AZ impairment** with someone else's report, or with a status page.
- **Capacity and Spot placement** discussions across accounts.
- **Deliberate co-location** for latency-sensitive tiers spanning accounts.

So: use `describe-availability-zones` and read `ZoneId`, not `ZoneName`, whenever the conversation crosses an account boundary. Inside a single account, the names are stable and fine.

*Hook: a cross-AZ cost or latency surprise you diagnosed.*

### Q12. Choosing a region

The order I actually apply:

1. **Legal and data residency.** If customer data must stay in the EU, or a regulator requires in-country storage, this decides it and nothing else matters. (Q226.)
2. **Latency to the users** who will feel it, measured rather than assumed - and remember that a CDN fixes read latency for static content but not write latency to your API.
3. **Service availability.** Not every service or feature is in every region, and this is a real blocker for newer services (Bedrock models, specific instance families, specific database engine versions). Check the ones your design depends on before committing.
4. **Existing footprint.** Being in the same region as your data, your team's tooling and your partners avoids cross-region transfer cost and complexity. Gravity is a legitimate argument.
5. **Cost.** Prices differ measurably between regions - `us-east-1` is usually cheapest, Sao Paulo and some APAC regions notably more expensive. This matters at scale but should never override 1-3.
6. **Capacity and maturity.** Older, larger regions have deeper capacity pools (matters for Spot and for large instance types) and more AZs. `us-east-1` is the exception that proves both rules: it has everything first and it also has the most notable incident history.

For a second region, add: **blast-radius independence** (do not pick two regions with a shared dependency you care about) and **which global services are homed where** (Q13).

*Hook: a region selection you made and the factor that turned out to dominate.*

### Q13. Global, regional and zonal services

**Global** (one namespace, control plane usually homed in `us-east-1`): IAM, Organizations and SCPs, Route 53, CloudFront, WAF for CloudFront distributions, Shield, Certificate Manager *for CloudFront* (must be in `us-east-1`), S3 bucket namespace (though buckets are regional).

**Regional** (independent per region, multi-AZ internally): S3, DynamoDB, SQS, SNS, EventBridge, Lambda, ECS/EKS control planes, API Gateway, Step Functions, KMS keys, Secrets Manager, Aurora clusters, ElastiCache clusters.

**Zonal** (live in one AZ, you are responsible for spreading): EC2 instances, EBS volumes, subnets, **NAT gateways**, RDS instances (a single instance; Multi-AZ adds a standby in another AZ), ElastiCache nodes, and interface VPC endpoints (one ENI per subnet you enable).

Design bugs from getting these wrong:

- A **single NAT gateway** for a three-AZ VPC: an AZ event kills egress for all three AZs, and you pay cross-AZ transfer for the two remote AZs continuously. The fix is one NAT per AZ with per-AZ route tables (Q35).
- An **ACM certificate in the workload region** attached to a CloudFront distribution, which silently fails validation because CloudFront requires `us-east-1`.
- **Route 53 and IAM being global** means changes there apply everywhere at once - there is no per-region canary for a bad DNS or policy change, which is worth knowing before you make one during an incident.
- A **KMS key referenced cross-region** in a replication or restore path, which fails because keys are regional unless you use multi-region keys.

*Hook: a global-versus-regional assumption that broke something, and the control you added.*

### Q14. Tagging strategy and enforcement

My mandatory set is small, because a long list is not enforced:

| Tag | Why it must exist |
| --- | --- |
| `owner` | A team identifier that maps to an on-call rotation, not a person |
| `cost-center` | For chargeback; must match the finance system's values exactly |
| `environment` | `prod` / `staging` / `dev` - drives policy, not just reporting |
| `service` | The logical service, so cost and incidents can be attributed |
| `data-classification` | Drives encryption, retention and access review requirements |

Enforcement, layered:

1. **In IaC**, as the primary path - default tags at the provider or CDK app level so every resource inherits them without the author thinking about it. This gets you the large majority for free.
2. **In the pipeline**, as the gate - a policy check that fails the plan if a taggable resource lacks the mandatory set. Fast feedback, good error messages.
3. **In IAM/SCP**, as the backstop - `aws:RequestTag` conditions denying creation without tags for the highest-value resource types. Powerful but blunt: it produces cryptic `AccessDenied` errors, so I use it selectively rather than universally.
4. **Detectively**, with AWS Config rules and Resource Groups Tag Editor reporting non-compliance to owners weekly, plus **tag policies** in Organizations to constrain allowed *values* (which is what stops `prod`, `Prod` and `production` becoming three cost centres).

For resources that **cannot be tagged** - and there are many: individual S3 objects, CloudWatch log data, data transfer, some serverless per-request charges - tagging is not the attribution mechanism. You use **account and resource boundaries** instead: a separate account, bucket, table or log group per team or service, and then **Cost Categories** to build the reporting hierarchy from account plus tag plus service rules (Q255). Designing the boundary so it is attributable is the actual technique; tags only finish the job.

*Hook: a tagging rollout you drove, the compliance percentage you reached, and how you handled the untaggable remainder.*

### Q15. Remediating one account with everything in it `[A]`

**Clarify first**: is there any customer data at risk right now, what is the compliance deadline if any, how many engineers touch this, and is there an existing IaC repository or is the estate console-built? The answers change the sequencing far more than the technology does.

**Week one - stop the bleeding and gain visibility.** Nothing structural, because structural changes without visibility cause outages.

1. Enable CloudTrail (all regions) to a bucket with Object Lock, plus Config, GuardDuty and Access Analyzer. You cannot investigate a past you did not record.
2. Inventory: Resource Explorer or Config aggregator plus Cost Explorer grouped by service, and identify the top ten cost items and the resources with public exposure.
3. Immediate risk closure: account-level S3 Block Public Access (after checking for intentional public buckets), rotate or delete long-lived access keys, require MFA for humans, delete unused IAM users.
4. Set a budget with anomaly detection, so the finance conversation stops being a surprise.
5. Write the ownership map: which of these resources belongs to production, and who is on call for it. This is interview-relevant because it is the part that requires talking to people rather than running commands.

**First month - build the destination and move the cheap things.**

1. Create the organization: management account, log-archive, security-tooling, and new `prod-*` and `nonprod-*` accounts with a real baseline (Q7).
2. Stand up the CI OIDC deploy role and get *new* work landing in the new accounts by default. Stopping the growth of the mess matters more than shrinking it.
3. Move the genuinely stateless and low-risk workloads first - experiments, internal tools, dev environments - to build the migration muscle and the runbook.
4. Introduce mandatory tagging in IaC and in the pipeline (Q14), and start importing existing production resources into IaC (`terraform import` / CDK import) rather than recreating them.

**First quarter - move production, then close the door.**

1. Migrate production workload by workload, each with its own cutover plan: replicate data (DMS, S3 replication, DynamoDB export/import or global tables as a migration tool), run in parallel where you can, cut over DNS, keep the rollback path for a defined window.
2. Apply SCPs progressively, in audit-then-enforce order: deny unused regions, deny disabling the logging stack, deny root usage.
3. Once nothing production-critical remains in the original account, demote it to the Sandbox OU with a hard budget, or empty and close it.
4. Then, and only then, do the cost work - rightsizing, commitments, lifecycle policies - because now every resource has an owner who can approve the change.

**What I would say explicitly in the interview**: I would not attempt a big-bang re-account. The sequencing principle is *visibility, then containment, then structure, then migration, then optimization*, and the biggest risk in the whole programme is not technical - it is that an unowned production resource gets moved or deleted by someone who did not know what depended on it.

*Hook: an estate you inherited in this condition, what you did in the first week, and what took longer than you promised.*

---

## 2. Workload identity and cross-account access as architecture

### Q16. How each compute model gets credentials

| Workload | Mechanism |
| --- | --- |
| EC2 instance | Instance profile; the SDK reads temporary credentials from IMDS at `169.254.169.254` (IMDSv2 requires a PUT-obtained token) |
| ECS task | Task role; the SDK reads from the **task metadata endpoint** at `169.254.170.2` via the `AWS_CONTAINER_CREDENTIALS_RELATIVE_URI` variable injected by the agent |
| EKS pod | IRSA (a projected OIDC service-account token exchanged with STS via `AssumeRoleWithWebIdentity`) or EKS Pod Identity (an agent-served endpoint, closer to the ECS model) |
| Lambda function | The execution role; credentials arrive as `AWS_ACCESS_KEY_ID` / `SECRET` / `SESSION_TOKEN` environment variables, refreshed by the runtime |
| CodeBuild job | The project's service role, delivered like a container credential |
| GitHub Actions | No AWS-resident identity at all - OIDC web identity federation into a role (Q29) |

The unifying idea worth saying out loud: **in every case the workload receives short-lived STS credentials, and in no case should there be a stored access key.** The differences are only in the transport - metadata endpoint, injected environment, or token exchange - and the transport is what determines the attack surface. IMDS is reachable by anything on the instance, which is why SSRF plus IMDSv1 was such a productive attack (`11-security` Q222); the ECS and Pod Identity endpoints are link-local but scoped per task; Lambda's environment variables are readable by any code in the function, including a compromised dependency.

*Hook: a credential-delivery mechanism you changed - keys to roles, or IRSA adoption - and what it took to find every consumer.*

### Q17. Credential lifecycle inside a Lambda execution environment

When the execution environment is created, the Lambda service assumes the function's execution role and injects the resulting temporary credentials into the environment as `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and `AWS_SESSION_TOKEN`. The runtime refreshes them periodically over the life of the environment, so a long-lived warm environment does not accumulate expired credentials.

The mechanism detail that matters: **the SDK caches whatever it read when the client was constructed, unless the credential provider is one that re-reads.** The AWS SDKs' default environment provider re-reads the environment variables and honours the expiry, so a client created in `INIT` and reused for hours is fine. Code that reads the variables *itself* into a static field - or a third-party library that does - will hold an expired secret and start failing with `ExpiredTokenException` after a few hours of warm reuse. That is the classic "works in test, fails once a day in production" serverless bug.

If credentials expire mid-invocation, the call fails with `ExpiredToken` and the SDK's retry does not fix it because the cached credential is still stale; a fresh client, or a provider that refreshes, does. So: **construct SDK clients once in `INIT`, and never copy credentials out of the environment yourself.**

*Hook: an `ExpiredToken` error you traced to a caching layer rather than to IAM.*

### Q18. The SDK credential provider chain

Order, roughly consistent across SDKs: explicit credentials passed in code, then Java system properties, then **environment variables**, then the web-identity token file, then the shared `~/.aws/credentials` and `~/.aws/config` profile (including `role_arn` with `source_profile`, and SSO), then the container credentials endpoint, then IMDS.

The "works locally, fails deployed" bug comes from **which entry wins in each place**. Locally, a developer's profile with wide personal permissions is found in `~/.aws`, so everything works. Deployed, the environment variables or container endpoint supply the *function's* role, which has been scoped narrowly - and now a call the developer never tested against the real role fails with `AccessDenied`. The code is identical; the identity is not.

The inverse bug is worse: a stale `AWS_PROFILE` or leftover environment variable on a build machine causes the deploy to run as the wrong identity, sometimes into the wrong account. And in containers, setting `AWS_ACCESS_KEY_ID` for one purpose silently shadows the task role for everything.

Practices: never rely on ambient local credentials for anything you intend to test - assume the actual role locally (`aws sts assume-role`, or `--profile` pointing at a role with the same policy) so your laptop has the same permissions as production; log the caller identity (`sts:GetCallerIdentity`) at startup in non-prod so "who am I" is answerable; and generate the least-privilege policy from real traces (Q30) rather than from imagination.

*Hook: a permission bug that only appeared after deployment, and the practice you introduced so it did not recur.*

### Q19. Execution role versus resource policy for Lambda

The **execution role** is what the function *uses*: its permissions to call DynamoDB, S3, other services. The **resource policy** (`AddPermission` / `Lambda::Permission`) is what other principals are allowed to do *to* the function - principally `lambda:InvokeFunction`.

- **API Gateway** invokes your function using the *API Gateway service principal*, so it needs a **resource policy** on the function granting `lambda:InvokeFunction` to `apigateway.amazonaws.com`, conditioned on the API's ARN. (Unless you configure API Gateway with an explicit IAM role for the integration, which is the less common pattern.) This is why the console's "Add trigger" silently creates a permission statement, and why hand-written CloudFormation forgets it and gets a 500 with `Invalid permissions on Lambda function`.
- **EventBridge** likewise pushes to the function, so it also needs a **resource policy** for `events.amazonaws.com` with a `SourceArn` condition on the rule.
- **SQS, Kinesis and DynamoDB Streams** are the other direction: the Lambda service *polls* them on your behalf via an event source mapping, using **your execution role**. So the permissions (`sqs:ReceiveMessage`, `sqs:DeleteMessage`, `kinesis:GetRecords`, ...) belong in the **execution role**, and there is no resource policy on the function at all.

That is the whole rule, and it is the cleanest way to say it in an interview: **push-based sources need a resource policy; poll-based sources need execution-role permissions.** Getting this backwards is the single most common serverless IAM confusion.

*Hook: a trigger that failed to invoke and how you identified which side of the policy was missing.*

### Q20. `s3:GetObject` granted and still `AccessDenied` `[T]`

Five distinct causes, and I would check them in this order:

1. **The KMS key.** The object is encrypted with a customer-managed key and the role lacks `kms:Decrypt`, or the key policy does not allow the role. S3 returns `AccessDenied`, not a key error, which is why this is the most-missed cause.
2. **Resource ARN shape.** The policy grants `arn:aws:s3:::bucket` but not `arn:aws:s3:::bucket/*`. Bucket-level and object-level actions need different ARNs, and `ListBucket` versus `GetObject` need the two different forms.
3. **A bucket policy or Block Public Access denying it** - especially cross-account, where you need the grant on *both* sides, or a bucket policy with an explicit `Deny` (perhaps `aws:SecureTransport` or a `aws:PrincipalOrgID` condition the caller does not satisfy).
4. **An SCP or permission boundary** cutting above the identity policy. The identity policy allows it, the ceiling does not. `11-security` Q213 has the full evaluation order; the practical tell is that the same policy works in a different account.
5. **VPC endpoint policy or a network cause.** An S3 gateway endpoint with a restrictive endpoint policy denies the request; or the function is in a VPC with no route to S3 at all, which produces a timeout rather than `AccessDenied` - worth distinguishing.

Honourable mentions: requester-pays buckets without `x-amz-request-payer`, object ownership / ACL edge cases in older buckets, and the object simply not existing (S3 returns `AccessDenied` rather than `NoSuchKey` when the caller lacks `ListBucket`, which sends people hunting a permissions ghost). That last one is a genuinely good thing to name.

*Hook: an `AccessDenied` that took too long to diagnose, and the tooling (`IAM policy simulator`, CloudTrail, Access Analyzer) you now reach for first.*

### Q21. Cross-account access patterns for a service consumed by twelve teams

| Pattern | Shape | Best for |
| --- | --- | --- |
| **Assume-role** | Consumer's principal assumes a role in the provider account | Control-plane operations, batch access, tooling |
| **Resource policy** | Provider grants the consumer's principal directly on the resource | Single-resource sharing: a bucket, a queue, a KMS key |
| **RAM sharing** | Provider shares the *resource itself* into the consumer's account | Subnets, Transit Gateway, Route 53 rules, Aurora clusters |
| **PrivateLink / VPC Lattice** | Network-level service exposure with its own auth | An API consumed as a service, especially at scale or across trust boundaries |

For a service consumed by twelve internal teams, my ranking is:

1. **Expose it as an API behind PrivateLink or Lattice** (or simply a public API Gateway with IAM/JWT auth if the data classification allows). This is the only option that keeps the *interface* as the contract rather than the *implementation*. Consumers never touch your table or your queue, so you can change them.
2. **Resource policy on a specific resource**, if the integration is genuinely data-level - a shared bucket for file drop, an SNS topic for events. Narrow, explicit, easy to audit, easy to revoke.
3. **Assume-role**, for operational and analytical access where consumers run their own queries. Fine, but it leaks your schema into twelve codebases.
4. **RAM**, only for infrastructure primitives; it is not an application integration mechanism.

The architectural point: the moment twelve teams hold IAM permissions on your DynamoDB table, that table is a public API you can never migrate. I would rather pay the latency of an API hop.

*Hook: an internal integration you moved from direct data access to an API, and what it unblocked.*

### Q22. Account A application to account B DynamoDB table

The design: a role in account B (`OrdersTableReader`) whose trust policy allows the specific role in account A - not the account root, the specific role ARN - and whose permission policy grants exactly the needed table actions on the specific table and index ARNs. The application in A calls `sts:AssumeRole` and uses the returned credentials for its DynamoDB client. If the table is encrypted with a CMK, the key policy in B must also allow the assumed role.

Failure modes of the naive approach:

- **Trusting the account root** (`"Principal": {"AWS": "arn:aws:iam::A:root"}`) without also constraining which principal in A may assume it. That delegates to *all* of account A, including anyone who can create a role there.
- **Assuming per request.** `AssumeRole` is a network call with its own throttle; doing it per invocation adds latency and eventually hits STS rate limits. Cache the credentials and refresh before expiry - the SDKs' `STSAssumeRoleCredentialsProvider` does this if you let it.
- **Session duration versus Lambda timeout.** A 15-minute session in a 15-minute function will expire mid-run.
- **Forgetting the KMS key policy**, producing the `AccessDenied` of Q20.
- **Cross-account CloudTrail confusion**: the actions appear in B's trail under the assumed role's session name. If you do not set a meaningful `RoleSessionName`, you lose the ability to attribute activity to the calling service.
- **Coupling.** As Q21 argues, the deeper problem is that account A now depends on B's data model. I would ask whether an API belongs here.

*Hook: a cross-account data dependency you either built well or later regretted.*

### Q23. Assume-role chaining limits

Role chaining is assuming a role using credentials that themselves came from an assumed role. Two hard rules:

1. **Session duration is capped at one hour when chaining**, regardless of the role's `MaxSessionDuration`. A request for longer fails. This surprises people who set `MaxSessionDuration` to 12 hours and still get one hour.
2. **The chain does not accumulate permissions.** Each hop is a fresh session with the new role's permissions, intersected with any session policy you pass. You cannot chain your way to more access than the final role has - but nor do you keep the previous role's access.

Practically: chaining is fine for a hop or two (CI role to deploy role to workload role) and becomes an operational problem beyond that, because credential refresh has to be handled at every hop and the one-hour ceiling makes long-running jobs fail mid-flight. For long jobs, get credentials from a non-chained source - the workload's own instance/task/IRSA identity assuming the target role directly.

Also worth naming: `aws:PrincipalArn` in a trust policy sees the *immediately previous* identity, and CloudTrail shows the chain in `sharedEventID` / `userIdentity.sessionContext`, so audit is possible but requires effort.

*Hook: a chained-role setup that broke a long-running job, and how you restructured it.*

### Q24. Service-linked roles, service roles, and `iam:PassRole`

- A **service role** is a role you create for an AWS service to act on your behalf - a Lambda execution role, a CodeBuild service role. You own its policies.
- A **service-linked role** is a role predefined and managed by the service (`AWSServiceRoleForECS`), created on first use, with a policy AWS maintains and you cannot broadly edit. It exists so the service can do its own internal plumbing without you having to model it.
- **`iam:PassRole`** is the permission to *hand a role to a service*. Creating a Lambda function with an execution role, launching an EC2 instance with an instance profile, or creating an ECS task definition with a task role are all "passing" a role.

`PassRole` exists to prevent privilege escalation: without it, anyone who can create a Lambda function could attach the account's admin role and invoke it, gaining admin without ever having been granted admin. So the correct pattern is to grant `iam:PassRole` **narrowly**, scoped by resource ARN (or by a path/tag convention such as `arn:aws:iam::*:role/app/*`) and by `iam:PassedToService` condition:

```json
{
  "Effect": "Allow",
  "Action": "iam:PassRole",
  "Resource": "arn:aws:iam::123456789012:role/app/*",
  "Condition": {"StringEquals": {"iam:PassedToService": "lambda.amazonaws.com"}}
}
```

`iam:PassRole` with `Resource: "*"` in a developer policy is effectively account admin, and it is one of the first things I look for in a policy review.

*Hook: a policy review where you found an escalation path, and how you closed it without blocking the team.*

### Q25. Lambda create plus no role create still reaches admin `[T]`

If a developer can create or update a Lambda function and can `PassRole` an existing privileged role - or can *modify* an existing function that already has one - they can run arbitrary code as that role. They never create a role; they borrow one. Variants of the same trick: updating an existing function's code (`lambda:UpdateFunctionCode`) whose role is privileged, adding a layer, changing the handler, or attaching an event source. The same applies to `glue:CreateJob`, `ec2:RunInstances` with an instance profile, `codebuild:StartBuild`, `cloudformation:CreateStack` with a passed role, `datapipeline`, `sagemaker` notebooks - the whole family of "service that runs your code with a role".

Controls that stop it, in order of strength:

1. **Scope `iam:PassRole`** by resource path and `iam:PassedToService` (Q24) so only roles inside the team's own namespace can be passed.
2. **Permission boundaries** on the roles the team is allowed to create or pass, capping the ceiling regardless of what is attached (Q5).
3. **Deny `lambda:UpdateFunctionCode` and `UpdateFunctionConfiguration` on production functions** to humans entirely - production changes come from the pipeline, and the pipeline role is not a human role.
4. **Separate accounts** so the privileged roles simply do not exist next to the developer's permissions.
5. **Detection**: Access Analyzer's unused-access and CloudTrail alerting on `PassRole` of sensitive roles.

*Hook: an escalation path you found in your own estate, and which of these controls you chose.*

### Q26. ABAC with tags: one policy for 30 teams

The idea is to write the policy in terms of *matching attributes* rather than enumerating resources. The principal carries a tag (from the IAM role, or from a SAML/OIDC session tag), the resource carries the same tag, and the policy requires equality:

```json
{
  "Effect": "Allow",
  "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:Query"],
  "Resource": "arn:aws:dynamodb:*:*:table/*",
  "Condition": {
    "StringEquals": {"aws:ResourceTag/team": "${aws:PrincipalTag/team}"}
  }
}
```

One policy, thirty teams, no edits when team thirty-one arrives. For creation you pair it with `aws:RequestTag` and `aws:TagKeys` conditions so a principal can only create resources tagged with its own team, and you deny `tag:UntagResource` on the governing tag key - otherwise a principal removes the tag and the boundary evaporates.

The honest limits, which are what an interviewer probes:

- **Not every service supports resource tags in authorization**, and support varies by *action* within a service. This is the biggest practical constraint; you must check per action, and you always end up with a hybrid RBAC/ABAC policy.
- **Tags on existing resources** must be complete and correct, so ABAC depends entirely on the tagging discipline of Q14.
- **Session tags** need to be plumbed from your IdP, and `sts:TagSession` permissions configured.
- **Debuggability** is worse: an `AccessDenied` now depends on data, so the answer to "why was I denied" is "look at the tag on the resource", which is less obvious than reading a policy.

I use ABAC for the broad, repetitive, per-team grants and keep explicit RBAC for the small number of high-value, low-churn resources.

*Hook: an ABAC rollout, the services that did not support it, and the hybrid you settled on.*

### Q27. Third-party SaaS access without long-lived keys

The mechanism is a **cross-account role with a trust policy naming the vendor's AWS account as principal, and an `sts:ExternalId` condition**:

```json
{
  "Effect": "Allow",
  "Principal": {"AWS": "arn:aws:iam::VENDOR_ACCOUNT:root"},
  "Action": "sts:AssumeRole",
  "Condition": {"StringEquals": {"sts:ExternalId": "unique-value-the-vendor-gave-you"}}
}
```

The parameter that makes it safe is the **`ExternalId`**, and it is worth explaining *why* rather than just naming it. Without it, the vendor - who legitimately has role ARNs for hundreds of customers - can be tricked into using its own credentials against *your* role on behalf of a different customer, because your trust policy accepts anything from the vendor account. That is the **confused deputy** problem. The `ExternalId` is a value the vendor generates per customer and passes on every `AssumeRole`, so an attacker who knows your role ARN but not your `ExternalId` cannot get the deputy to act.

The rest of the design: grant the role the minimum the integration genuinely needs (read-only cost data, a specific bucket prefix), use `aws:SourceIp` or additional conditions where the vendor publishes stable egress, set a short `MaxSessionDuration`, log and alert on assumptions of the role, and review it on a schedule - vendor integrations are the classic thing nobody removes after the trial ends.

*Hook: a vendor integration you onboarded or offboarded, and what the access review found.*

### Q28. Identity Center versus federated roles versus IAM users

**IAM users are for nothing.** At this point the only defensible remaining uses are a handful of service accounts for systems that genuinely cannot federate, and even those should be on a path to removal. Long-lived access keys are the single most common cause of cloud credential compromise (`11-security` Q220).

**Federated roles via your own SAML/OIDC integration** was the standard answer for years: one identity provider, roles per account, users assume them. It works, and it is still what you build if you have unusual requirements, but you are maintaining the role-and-trust plumbing in every account yourself.

**IAM Identity Center** is the default now. What the **permission-set** model changes architecturally:

- A permission set is defined *once* centrally and *provisioned* as a role into each assigned account, so "read-only for the payments team in all six payments accounts" is one object, not six.
- Assignment is `(group, permission set, account)`, which means access is expressed in the vocabulary your IdP already has - groups from Entra ID or Okta - so joiner/mover/leaver is handled by the existing HR-driven process rather than by IAM.
- Every human session is short-lived and audited with the user's identity in CloudTrail, so attribution works.
- The CLI experience (`aws sso login`, credential process) removes the incentive to create keys, which is what actually reduces key sprawl.

The consequence for account design: because assignment is cheap and centrally visible, you can afford **more accounts** (Q3) - the human-access cost of an extra account drops to one assignment. Identity Center's own regional homing and its dependency for break-glass are the things to plan for: keep one emergency IAM role or root credential path, in a safe, documented, alarmed form, for the day Identity Center is the thing that is broken.

*Hook: an SSO migration you ran, and how you handled break-glass access.*

### Q29. The OIDC trust-policy mistake `[T]`

The mistake is an under-constrained `sub` condition. People write the trust policy with the audience checked and the subject wildcarded, or scoped only to the organization:

```json
"Condition": {
  "StringLike": {"token.actions.githubusercontent.com:sub": "repo:my-org/*"}
}
```

or worse, they omit the `sub` condition entirely and only check `aud`. Since GitHub's OIDC provider issues tokens for **every repository in the world** (the provider is shared), a condition that does not pin the repository means *any* GitHub Actions workflow anywhere can assume your deploy role. Pinning only `my-org/*` means any repo in your org - including a fork, or a repository a contractor can create - can deploy to production.

What an attacker does with it: opens a pull request or creates a repository, runs a workflow that assumes your role, and now has your deploy permissions in your account. There is no credential to steal and no anomaly in your repository's history.

The correct trust policy pins the repository **and the ref or environment**:

```json
"Condition": {
  "StringEquals": {
    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
    "token.actions.githubusercontent.com:sub": "repo:my-org/my-repo:environment:production"
  }
}
```

Using `environment:production` rather than `ref:refs/heads/main` is stronger, because GitHub environments carry their own approval rules and cannot be created by a fork. Add: a separate role per repository, `MaxSessionDuration` at the minimum the deploy needs, and alerting on assumptions from unexpected subjects. The generalization worth stating: **with a shared OIDC provider, the audience proves the provider, not the caller - the subject is the identity, so an unconstrained subject is an unauthenticated role.**

*Hook: an OIDC trust policy you reviewed or tightened, and how you verified nothing broke.*

### Q30. Maintaining 40 statements across 12 functions

The technique is to make least privilege a *generated and verified* artifact rather than a hand-written one.

1. **Generate from the framework.** SAM and CDK generate scoped policies from the constructs (`table.grantReadData(fn)` produces exactly the table and index ARNs). This is the biggest single win: the policy is derived from the code's actual dependencies, so it cannot drift from them.
2. **Generate from observed behaviour** for the parts the framework cannot infer: IAM Access Analyzer **policy generation** from CloudTrail produces a policy from what the role actually called over a window. Run the workload in staging with a deliberately broad policy, generate, then apply the narrow one.
3. **Verify in the pipeline.** Access Analyzer's `ValidatePolicy` and custom policy checks (`CheckNoNewAccess`, `CheckAccessNotGranted`) can fail a build when a change *widens* access - a diff-based gate rather than an absolute one, which is what makes it usable.
4. **Prune continuously.** Access Analyzer **unused access** findings tell you which permissions and which roles have not been used in N days. Review monthly and remove.
5. **Cap with boundaries** so the worst case is bounded even when a statement is too broad (Q5).
6. **Keep it readable**: one role per function (never a shared "app role" across twelve functions - that is how you get the union of all permissions), managed policies for genuinely shared concerns, and a naming convention that makes the role's purpose obvious in CloudTrail.

The trade-off I would name: least privilege has a real maintenance cost, and a policy nobody can read is not safer than a slightly broader one that everybody understands. I optimize for **narrow on the high-value actions** (`iam:*`, `kms:Decrypt`, `s3:DeleteObject`, anything on production data) and accept service-level breadth on low-risk read paths.

*Hook: a policy-generation practice you introduced and the reduction in wildcard statements you achieved.*

### Q31. Where the platform/product IAM line goes `[A]`

**Clarify**: how many teams, what is the regulatory posture, is there an existing pipeline every team uses, and how mature is the teams' IaC practice? A single-team startup and a 30-team regulated estate get different answers.

My default line: **the platform owns the ceiling and the identity plumbing; product teams own the grants inside it.** Concretely:

Platform owns:

- SCPs at the OU level, and the account baseline (Q7).
- **Permission boundaries** that any team-created role must carry, enforced by an IAM condition on `iam:CreateRole` requiring the boundary.
- The `iam:PassRole` constraint - teams may pass only roles under their own path (Q24).
- The CI OIDC trust policies, because these are the escalation-sensitive part (Q29) and because a mistake there is not local.
- The policy-check gate in the shared pipeline, plus the Access Analyzer findings pipeline and the monthly unused-access review.
- Managed policies for cross-cutting concerns: observability, KMS use, VPC access.

Product teams own:

- The execution role and its policies for each of their functions, written in their own IaC, reviewed by their own team, deployed by their own pipeline **without platform approval** - that is the whole point.
- The resource policies on their own resources, within the bounds of the SCP.

The mechanism that makes this safe rather than optimistic is that **teams cannot exceed the boundary even by mistake**, so the review is a quality conversation rather than a security gate. The platform's job is to make the safe path the fast path: if writing a correct scoped policy takes ten minutes with a construct and two days with a ticket, teams will write correct policies.

Where I would deviate: for a small number of **high-blast-radius permissions** - `iam:*`, `organizations:*`, KMS key policy changes, anything touching the log archive - I keep central approval, and I say so explicitly, because the boundary mechanism cannot protect against a legitimate-looking change to the boundary itself.

*Hook: the IAM delegation model you built, one thing you kept central longer than teams wanted, and whether that turned out to be right.*

---

## 3. VPC, connectivity and the network boundary

### Q32. A three-tier VPC across three AZs

```
VPC 10.20.0.0/16  (one region, three AZs)

Per AZ:
  public subnet   /24   -> route table: 0.0.0.0/0 via Internet Gateway
                           holds: ALB/NLB node, NAT gateway
  private-app     /22   -> route table: 0.0.0.0/0 via that AZ's NAT gateway
                           holds: ECS tasks / EKS nodes / Lambda ENIs
  private-data    /24   -> route table: no default route (or NAT for patching only)
                           holds: RDS/Aurora, ElastiCache
Shared:
  Internet Gateway (one per VPC)
  Gateway endpoints for S3 and DynamoDB (route table entries, free)
  Interface endpoints for the AWS APIs you actually call, one ENI per AZ
```

What each is for: the **public subnet** exists only for things that need a public IP - the load balancer's nodes and the NAT gateways; nothing of yours runs there. The **app subnet** is where compute lives, with egress but no ingress from the internet. The **data subnet** has no default route at all, which is the cheapest possible exfiltration control and also stops a compromised database from calling out. **Route tables are per AZ**, not per VPC, because NAT gateways are zonal (Q13) and you do not want AZ A's traffic crossing to AZ B's NAT.

Sizing: the app subnet is the biggest because it holds the elastic things - a scaling EKS node group plus Lambda ENIs consume addresses faster than people expect (Q42). I use a `/22` per AZ as the default and regret it less often than a `/24`.

*Hook: a VPC layout you designed or corrected, and the sizing decision you would change.*

### Q33. CIDR planning for four regions and forty accounts

Plan top-down from one large private block and delegate by region, then account:

```
10.0.0.0/8 for AWS overall
  10.0.0.0/12    region 1  (us-east-1)     -> 16 x /16 VPCs
  10.16.0.0/12   region 2  (eu-west-1)
  10.32.0.0/12   region 3
  10.48.0.0/12   region 4
  10.64.0.0/12   reserved for growth / acquisitions
  10.128.0.0/9   reserved for on-premises and partners
```

Then assign one `/16` per VPC (per account per region), and inside it a predictable per-AZ, per-tier layout so that any engineer can read an IP and know where it is. Manage this in **AWS IPAM** rather than a spreadsheet, so allocation is enforced at creation time and utilization is visible.

What you reserve: space for the regions you have not built yet, space for on-premises and for acquired companies (whose RFC1918 ranges will collide with yours if you have used all of `10/8`), and a block for services that need their own space - EKS pod CIDRs if you use a secondary CIDR, Transit Gateway connect, client VPN pools.

**The unrecoverable mistake is overlap.** Two VPCs with overlapping CIDRs cannot be peered or attached to the same Transit Gateway route table, and the fix is re-addressing a live workload - which means recreating subnets, and therefore every ENI, database and load balancer in them. You can add secondary CIDRs to a VPC, so *too small* is recoverable and ugly; *overlapping* is a migration. The second-order version is overlapping with your own on-premises range, which you discover on the day the Direct Connect is provisioned.

*Hook: an addressing collision you dealt with, and what it cost to resolve.*

### Q34. A `/24` per VPC `[T]`

A `/24` is 256 addresses; split across three AZs, that is roughly 80 per subnet, and AWS reserves five per subnet - so about 75 usable per AZ.

What breaks: **anything elastic**. An EKS node group with the VPC CNI assigns pod IPs from the subnet, so a handful of nodes exhausts it. A VPC-attached Lambda scaling out consumes Hyperplane ENI capacity and addresses. An ALB wants at least eight free addresses per subnet and takes more as it scales. Blue/green deployments briefly double the address requirement, which is the specific moment this bites.

When they find out: **not at build time and not under normal load** - at the first significant scale-up or the first blue/green deploy, as `InsufficientFreeAddressesInSubnet` or as pods stuck in `ContainerCreating`. Which is to say, during a traffic peak or a release, both of which are the worst possible times.

The remediation is to add a secondary CIDR to the VPC and create new, larger subnets, then migrate workloads into them - a rolling change, doable but disruptive, and for a database it means a maintenance window. The lesson to state: **address space is free, so allocate generously**; a `/16` per VPC costs nothing and removes an entire class of incident. The only reason to be frugal is if you have genuinely run out of RFC1918 space, which is the planning failure of Q33.

*Hook: an address exhaustion event and how you remediated it without downtime.*

### Q35. NAT gateway pricing and three ways to reduce it

A NAT gateway costs an **hourly charge per gateway** plus a **per-GB data processing charge on everything through it**, and the data charge is the one that surprises people because it applies to traffic that stays inside AWS. Three NAT gateways for AZ redundancy is three hourly charges, and a chatty workload pulling container images or writing to S3 through NAT can make the data processing charge exceed the compute cost.

Three ways to reduce it:

1. **VPC endpoints for the destinations that matter.** S3 and DynamoDB **gateway** endpoints are free and remove that traffic from NAT entirely - this is usually the single biggest win, because S3 and ECR image pulls dominate. Interface endpoints for other services cost hourly per AZ plus a lower per-GB rate, so they pay off above a modest volume threshold.
2. **Do not put the workload in a VPC if it does not need to be** - a Lambda talking only to AWS APIs needs no VPC at all (Q40), and therefore no NAT.
3. **Reduce the traffic**: cache container images (ECR pull-through cache with an endpoint), avoid cross-AZ NAT (per-AZ route tables, else you pay NAT *and* cross-AZ transfer), batch and compress telemetry rather than streaming raw logs to a third-party collector, and check for anything accidentally egressing at volume - a sidecar shipping full request bodies is a classic.

Alternatives worth naming: a **NAT instance** is cheaper at low volume and an operational liability; **egress-only internet gateways** are free but IPv6-only; a **centralized egress VPC** consolidates gateways (fewer hourly charges, better inspection) at the price of adding Transit Gateway data processing charges - so run the arithmetic rather than assuming centralization is cheaper.

*Hook: a NAT bill you reduced, the mechanism, and the number.*

### Q36. Gateway endpoints versus interface endpoints

| | Gateway endpoint | Interface endpoint (PrivateLink) |
| --- | --- | --- |
| Mechanism | A **route table entry** sending a prefix list to the endpoint | An **ENI with a private IP** in each subnet you enable, plus private DNS |
| Services | S3 and DynamoDB only | Most AWS services, plus Marketplace and your own services |
| Cost | Free | Hourly per endpoint per AZ, plus per-GB data processing |
| Reachability | Only from within the VPC's route tables | From the VPC, and via peering/TGW/VPN/Direct Connect from elsewhere |
| DNS | No DNS change; the public name resolves and the route sends it privately | Private DNS overrides the service name to the ENI's private IP |
| Policy | Endpoint policy | Endpoint policy, plus security groups on the ENI |

The mechanism difference drives the design differences. Because a gateway endpoint is a *route*, it only affects traffic originating in a route table you attach it to - so on-premises traffic arriving via Direct Connect cannot use it, which is the standard reason to use an S3 *interface* endpoint despite the cost. Because an interface endpoint is an *ENI*, it consumes subnet addresses, has a security group (so you can restrict who reaches it), and is billed per AZ - which means enabling six endpoints across three AZs has a non-trivial fixed cost before a single byte moves.

My rule: gateway endpoints for S3 and DynamoDB always, in every VPC, because they are free and remove the largest traffic categories from NAT. Interface endpoints selectively, for the APIs the workload actually calls at volume or must reach without internet egress - typically Secrets Manager, KMS, ECR (api and dkr), CloudWatch Logs, STS, SQS - and I check the NAT data-processing bill to decide, since the endpoint hours are only worth it above the crossover volume.

*Hook: an endpoint rollout, which endpoints you chose, and the before-and-after on the NAT bill.*

### Q37. S3 gateway endpoint added and traffic still goes via NAT `[T]`

Three reasons, in the order I would check:

1. **The wrong route table.** A gateway endpoint is attached to *specific* route tables. If the workload's subnet uses a route table that was not associated with the endpoint - often a newly created subnet, or a per-AZ table where only one was updated - that traffic still follows the default route to NAT. This is the most common cause and it explains "a subset".
2. **Cross-region requests.** The endpoint's prefix list covers S3 in *that region only*. Any request to a bucket in another region - a cross-region replication read, an artifact bucket that lives in `us-east-1`, or an SDK call with a hardcoded region - goes out through NAT. Same for requests using a **global or legacy endpoint name** that resolves outside the prefix list.
3. **Not actually S3.** Traffic to services that *look* like S3 in the trace but are not: an ECR image pull is partly S3 (covered) and partly the ECR API (not, unless you add interface endpoints); CloudFront-fronted S3 URLs go to CloudFront's public IPs, not to S3's prefix list; a third-party S3-compatible endpoint obviously is not S3.

Two more worth mentioning: **IPv6** traffic to S3 does not use the IPv4 prefix list route, and an **endpoint policy that denies** the request causes a failure the application may retry against a different path. The diagnostic is VPC flow logs - look for whether the destination is the S3 prefix list or the NAT ENI, per source subnet, and the pattern usually names the cause immediately.

*Hook: an endpoint that did not eliminate the NAT charge you expected, and what you found in the flow logs.*

### Q38. Security groups versus NACLs

**Security groups are stateful**, attached to ENIs, allow-only, and evaluated as a union of all groups on the ENI. Return traffic for an allowed outbound connection is automatically permitted. **NACLs are stateless**, attached to subnets, support both allow and deny, are evaluated in rule-number order with first-match-wins, and require explicit rules in *both* directions - including the ephemeral port range for return traffic, which is the thing everyone gets wrong.

Practically, security groups are the tool for almost everything, because they express intent ("the app tier may reach the database tier") rather than plumbing, and because referencing groups (Q39) makes the rules survive scaling.

The cases where you genuinely need a NACL:

- **You must deny a specific source.** Security groups cannot express deny, so blocking a single abusive IP range at the network layer needs a NACL (though WAF or the ALB is usually the better place).
- **A subnet-wide guarantee independent of what instances are launched.** A NACL enforcing "nothing in the data subnet may initiate outbound to the internet" holds even if someone attaches a permissive security group. This is a defence-in-depth argument, and it is the strongest one.
- **Coarse blast-radius containment during an incident** - isolating a subnet quickly without touching every ENI.

The trade-off: NACLs have a low rule limit, are order-sensitive, and produce failures that are hard to attribute because there is no per-rule counter. I keep them simple - usually the default allow-all plus one or two deliberate denies - and put the real policy in security groups.

*Hook: a NACL you added deliberately, and what it caught.*

### Q39. Security group referencing

Instead of `source: 10.20.0.0/22`, you write `source: sg-app`. The rule then means "any ENI carrying the app security group", regardless of its IP.

What it buys: rules that survive scaling, replacement and re-addressing. A new task, a replaced instance, a blue/green fleet in a new subnet - all inherit access by carrying the group, so the database's rule never changes. It also makes the rule *readable as intent*, which matters for review, and it removes the temptation to widen a CIDR "because the new subnet is not covered".

The limit that eventually bites: **rules per security group and groups per ENI are quotas** (defaults are modest - on the order of 60 rules per group and 5 groups per ENI, both adjustable within a total-rules-per-ENI budget), and crucially, **a referenced group counts toward the referencing group's rule budget in ways that are hard to predict**. In a large mesh where dozens of services reference each other, you hit the ceiling; the symptom is a failed `AuthorizeSecurityGroupIngress` during a deploy. There is also a hard limit on *how many* security groups can reference a single group, which large shared-database patterns reach.

Mitigations: group services into tiers rather than referencing per service, use prefix lists for stable CIDR sets, and at genuine scale move to a different model - VPC Lattice or a service mesh with mTLS, where identity rather than network position is the authorization primitive. The rule limits are the practical signal that network-layer authorization has stopped scaling for you.

*Hook: a security group sprawl you refactored, and the model you moved to.*

### Q40. Does a Lambda need a VPC?

**Decision rule: put a Lambda in a VPC only if it must reach a resource that has no public endpoint** - an RDS or Aurora instance in private subnets, an ElastiCache cluster, an on-premises system over Direct Connect, or an internal service behind an internal load balancer. Everything else - DynamoDB, S3, SQS, SNS, EventBridge, Step Functions, Secrets Manager, third-party HTTPS APIs - is reachable from the default, VPC-less Lambda networking, over TLS with IAM authentication.

The thing to say clearly, because it is the most common misconception: **a Lambda outside a VPC is not "on the internet".** It runs in AWS-managed network space with no inbound reachability at all; its calls to AWS services are authenticated by IAM and encrypted. Putting it in a VPC does not make it more authenticated - the IAM policy does that. The security value of a VPC for a function is specifically about *egress control* (route tables, endpoint policies, no default route) and about reaching private resources, and those are real but narrower than people assume.

What you lose by putting it in one:

- **Address consumption and ENI capacity** as it scales (Q42).
- **No internet access by default**, so any third-party HTTPS call now needs a NAT gateway - hourly plus per-GB (Q35) - or an interface endpoint per AWS service you call, which is a new fixed cost and a new set of things to configure.
- **More failure modes**: subnet exhaustion, a broken NAT, a missing endpoint, a security group change. Each is an outage cause that did not exist before.
- Historically, a large cold-start penalty; that is largely gone (Q41), and quoting it as a current reason is a tell that a candidate stopped reading in 2018.

*Hook: a function you moved into or out of a VPC, and the reason that decided it.*

### Q41. Lambda VPC networking and the Hyperplane change

**The old model (pre-2019):** when a VPC-attached function scaled, Lambda created an **ENI per function per subnet per concurrency group** at cold start. ENI attachment takes on the order of ten seconds, so cold starts for VPC functions were routinely 8-10 seconds, and heavy scaling could exhaust ENI quotas and subnet addresses.

**The current model:** Lambda uses **VPC-to-VPC NAT over AWS Hyperplane**. A small number of shared Hyperplane ENIs are created per *unique combination of subnet plus security group*, once, and every execution environment for every function using that combination is mapped through them. The ENI creation happens when the function is created or its network config changes, not per cold start. So the per-invocation VPC penalty is now negligible - single-digit milliseconds of extra network path - and cold start for a VPC function is essentially the same as for a non-VPC function.

Consequences that still matter:

- **The unit of ENI creation is (subnet, security group).** Ten functions sharing one subnet-and-security-group pair share ENIs; ten functions with ten different security groups create ten sets. So standardizing the network configuration across functions is a real optimization.
- **Changing a function's subnets or security groups** triggers new ENI provisioning, which takes minutes and can fail - it is a deploy-time risk, not a runtime one.
- **Subnet addresses are still consumed**, and cross-AZ behaviour still matters: give the function all three AZs' subnets so it survives an AZ event.
- The **NAT requirement for internet egress is unchanged** (Q40), which is now the main cost of VPC attachment.

*Hook: a VPC-attached function whose cold start you measured before and after, or a network-config change that caused a deploy failure.*

### Q42. VPC-attached Lambda failing at 800 concurrent `[T]`

Two distinct limits:

1. **Subnet IP exhaustion.** Hyperplane ENIs are shared, but each concurrent execution still consumes an address from the subnets you attached, and other things in those subnets (EKS pods, tasks, load balancer nodes) are competing for the same space. With `/24` subnets (Q34) you run out well before 800. The symptom is invocation failures with an ENI/address error and, in the Lambda metrics, errors that are not application errors.
2. **Downstream connection limits.** At 800 concurrency the function is holding up to 800 database connections; Aurora's `max_connections` for a small instance class is in the hundreds, so you get `too many connections` (Q161) - which appears as a Lambda error but is actually a downstream capacity limit. Same shape for an ElastiCache node, a self-hosted service behind an internal ALB, or an on-premises system over a Direct Connect with limited capacity.

Two more candidates worth naming as the alternates: the **account concurrency limit** (if 800 is close to a reduced ceiling) and **ENI/network-interface quotas** in unusual configurations with many distinct subnet-plus-security-group combinations.

The diagnostic order: check the error type in the Lambda metrics (invocation error versus function error), then subnet free addresses, then the downstream's connection metrics. The fixes differ completely - larger subnets versus RDS Proxy and reserved concurrency (Q129, Q162) - so identifying which limit you hit is the whole task.

*Hook: a scaling failure whose real limit was downstream rather than in Lambda.*

### Q43. A Lambda in a private subnet cannot reach the internet

Diagnosis in order:

1. **Is it actually a network failure?** A timeout at the socket level, not a 403 or an SDK credential error. Turn on the SDK's timeouts so you get a fast, unambiguous failure rather than a 15-minute function timeout.
2. **Which subnets is the function attached to?** If any of them is a *public* subnet (route to IGW), the function has **no** internet access from those - a Lambda ENI has no public IP, so a route to an internet gateway does nothing. This is a very common misconfiguration and worth naming first because it is counter-intuitive.
3. **Route table for the private subnets**: is there a `0.0.0.0/0` route, and does it point at a NAT gateway that is in a *public* subnet and in `available` state? Per-AZ route tables mean you must check all of them.
4. **Security group egress** - allowing outbound 443 (people lock egress down and forget).
5. **NACLs** on both the private and the public subnet, including the ephemeral return range (Q38).
6. **DNS**: `enableDnsSupport` on the VPC, and whether the destination resolves at all.

**Cheapest correct fix for an AWS-only destination: do not use NAT at all.** Add a **gateway endpoint** for S3 and DynamoDB (free) and **interface endpoints** for the specific AWS APIs the function calls. That removes the internet dependency entirely, and it is cheaper than a NAT gateway once you are past trivial volumes - and more importantly it removes an availability dependency. If the destination is genuinely third-party, you need NAT (one per AZ) or an egress proxy.

And the question above the question: if the only reason this function is in a VPC is habit, take it out (Q40).

*Hook: a private-subnet connectivity failure and which of these steps found it.*

### Q44. Peering versus Transit Gateway versus PrivateLink versus Lattice

| Need | Choice | Why |
| --- | --- | --- |
| Two VPCs in one account | **VPC peering** | Free (no hourly, no processing charge beyond cross-AZ), lowest latency, trivial to reason about. Non-transitive, which does not matter at two |
| Forty VPCs across accounts | **Transit Gateway** | Peering is O(n²) - 780 connections and 780 route table entries. TGW is a hub with per-attachment route tables, supports transitive routing, and integrates Direct Connect and VPN. You pay per attachment-hour plus per-GB |
| A service exposed to another company | **PrivateLink** | Exposes a single service endpoint, not a network. No CIDR coordination, no transitive reachability, unidirectional by construction - the consumer can reach your NLB and nothing else |

**VPC Lattice** is the newer, fourth answer, and worth raising deliberately: it is service-to-service connectivity with identity-based authorization (IAM auth policies), built-in load balancing and retries, working across VPCs and accounts *without* requiring non-overlapping CIDRs. For a large internal service estate it is the option that stops network topology from being the authorization model - closer to a managed mesh than to a router. The trade-off is that it is another abstraction with its own cost model and its own limits, and it does not replace TGW for general routing (databases, on-premises, non-HTTP protocols).

The framing I would give: **peering and TGW connect networks; PrivateLink and Lattice connect services.** If the requirement is "these two applications should talk", the service-level options are usually the better architecture, because they do not require your two organizations to agree on IP addresses forever.

*Hook: a connectivity topology you chose, and what you would choose now.*

### Q45. Transit Gateway route tables and appliance mode

A TGW has **attachments** (VPC, VPN, Direct Connect gateway, peering) and **route tables** you associate attachments with, plus route propagation. That indirection is the point: you can build segmentation - production attachments in one route table that cannot see the sandbox route table - which is how you get "connected but isolated" without per-VPC rules.

**Appliance mode** solves a specific problem: TGW normally selects an AZ-local path for a flow, and for a multi-AZ inspection appliance (a firewall fleet, an IDS, a NAT/proxy layer) that means the forward and return path of the same TCP flow can land on **different appliance instances in different AZs**. A stateful appliance drops the return packet because it never saw the handshake, and the symptom is asymmetric, intermittent connection failures that look like packet loss. Appliance mode makes TGW keep a flow pinned to the same AZ for both directions, so state is consistent.

What it costs: **cross-AZ data transfer and latency**, because keeping the flow symmetric can mean routing to a non-local AZ, and you pay for that per GB. It also constrains your appliance scaling design, since AZ affinity is now part of the correctness model rather than just an optimization.

The general lesson worth stating: **stateful middleboxes and multi-path networks are in tension**, and appliance mode is AWS buying symmetry at the price of locality.

*Hook: an inspection or egress architecture you built, and whether you enabled appliance mode.*

### Q46. Route 53 record types worth knowing

- **Alias** versus **CNAME**: an alias is a Route 53-specific record pointing at an AWS resource (ALB, CloudFront, S3 website, another Route 53 record). It works at the **zone apex** (`example.com`), which a CNAME cannot, resolves to A/AAAA records so clients see addresses directly, and is **free to query**. A CNAME is the DNS-standard indirection, works for subdomains, is chargeable per query, and adds a resolution hop. Use alias for every AWS target; CNAME only for non-AWS targets.
- **Weighted**: split traffic by proportion. The case: a canary at the DNS layer, or a gradual migration between two stacks. The caveat is DNS caching - weights are approximate and shift slowly (Q219).
- **Latency-based**: route each client to the region with the lowest measured latency *from their resolver*. The case: a genuinely multi-region active-active read path.
- **Failover**: primary plus secondary with a health check. The case: active-passive DR, where you accept TTL-bounded downtime.
- **Geolocation** (and **geoproximity**): route by the client's continent/country. The case: **data residency and legal requirements**, and content localization - not latency, which is what latency-based routing is for. Geoproximity with a bias is the one to use when you want to shift load between regions deliberately.
- Worth adding: **multivalue answer** for simple client-side load spreading with health checks, and the fact that **health checks are what turn any of these into a failover mechanism**.

The trade-off that unifies them: DNS is a *coarse, cached, client-controlled* traffic control. It is excellent for region selection and terrible for anything requiring fast, precise shifts - use a load balancer, CloudFront or Global Accelerator for that (Q221).

*Hook: a DNS-based traffic shift you performed, and how closely the actual distribution matched the configured one.*

### Q47. Private hosted zones and hybrid DNS resolution

A **private hosted zone** is associated with one or more VPCs; names in it resolve only for queries originating in those VPCs, via the VPC's `.2` resolver (Route 53 Resolver). Split-horizon works: the same name can exist in a public and a private zone with different answers.

**On-premises resolving an AWS private name:** create a Route 53 Resolver **inbound endpoint** - ENIs in your VPC with private IPs - and configure your on-premises DNS servers to forward the relevant zone (`aws.internal`) to those IPs over Direct Connect or VPN. The endpoint resolves against the private hosted zones associated with its VPC.

**AWS resolving an on-premises name:** create a Resolver **outbound endpoint** plus **forwarding rules** ("`corp.example.com` forwards to 10.200.1.5"). The VPC resolver then forwards matching queries out to your on-premises DNS.

Two things worth adding, because they are what makes this work at scale:

- **Rules are shareable via RAM**, so you build the forwarding configuration once in the network account and share it to every VPC, rather than configuring forty VPCs. The same applies to associating a private hosted zone with VPCs in other accounts (which requires an authorization step).
- **Resolver DNS Firewall** sits at the same layer and is the natural place to block known-bad domains and DNS-tunnelling exfiltration.

Failure modes to name: the resolver's per-ENI query rate limit (a chatty workload can exhaust it, producing intermittent resolution failures that look like application bugs), and conditional forwarding loops when both sides forward the same zone to each other.

*Hook: a hybrid DNS setup you built, and a resolution failure you debugged in it.*

### Q48. Hybrid connectivity for a bank `[A]`

**Clarify first**: what bandwidth do the migrating workloads actually need, what is the latency requirement, what does the regulator require about the transport, what is the acceptable outage for the link, and how long will the hybrid period last? A three-year hybrid estate and a nine-month migration deserve different investments.

**My recommendation: both, in a specific configuration.** Two Direct Connect connections at **different Direct Connect locations**, terminating on **different customer routers**, with a **Site-to-Site VPN as the backup path**, all attached to a Transit Gateway via a Direct Connect gateway.

Reasoning:

- **Direct Connect** gives you consistent latency, predictable bandwidth, and lower per-GB data transfer out - which for a bank moving significant volume is a genuine cost argument as well as a performance one. It also gives a private path that does not traverse the internet, which is usually what the regulatory conversation is really about.
- **A single Direct Connect is not highly available.** One connection at one location with one router is a single point of failure at three levels; AWS's own resilience guidance is explicit about this. Two connections at two locations is the maximum-resilience posture.
- **The VPN backup** costs almost nothing and covers the case where both Direct Connect paths are affected - and, importantly, it is the thing you can provision in hours if a Direct Connect order takes weeks. BGP with appropriate AS-path prepending makes the failover automatic, and the accepted failure mode is degraded bandwidth on the VPN rather than an outage.

**The failure mode I accept**: during a dual-Direct-Connect failure, throughput drops to VPN capacity (about 1.25 Gbps per tunnel, ECMP across tunnels if needed), so batch replication will lag while interactive traffic continues. I would state that explicitly to the business and agree which workloads are shed.

**Cost**: port hours for two connections, cross-connect fees from the colocation provider, per-GB data transfer out at the lower Direct Connect rate, TGW attachment hours and data processing, plus a small VPN cost. The honest note is that for a *short* migration with modest volume, VPN-only is the right answer and Direct Connect is over-engineering - the deciding factors are duration, volume and whether the latency consistency is genuinely required.

**What I would also insist on**: encryption in transit regardless of the private path (MACsec on Direct Connect, or IPsec over it) because "private circuit" is not "encrypted"; a tested failover, not an assumed one; and monitoring on BGP session state and per-path utilization so a silent failover to the backup path does not go unnoticed until the second failure.

*Hook: a hybrid connectivity design you delivered, and the failover you actually tested.*

---

## 4. Edge and entry - CloudFront, API Gateway, ALB, AppSync

### Q49. Client to Lambda handler, hop by hop

1. **DNS** - the client resolves your name; Route 53 returns the CloudFront distribution's addresses (alias record). *Can reject*: nothing, but geolocation/latency routing decides where you go.
2. **CloudFront edge (POP)** - TLS terminates here. *Can reject*: WAF rules attached to the distribution, geo-restrictions, signed-URL/cookie validation, and CloudFront Functions or Lambda@Edge on viewer request. *Can serve*: a cache hit, ending the story.
3. **Regional edge cache** (for cacheable content) then the **origin request** over the AWS backbone, with an origin-request Lambda@Edge and OAC signing if configured.
4. **API Gateway** - the regional or edge-optimized endpoint. *Can reject*: resource policy, mTLS, throttling and usage-plan limits, request validation against the model, the authorizer (IAM, Cognito, JWT or Lambda), and WAF if attached to the stage.
5. **Integration** - API Gateway invokes Lambda via the AWS API using its own service principal, permitted by the function's **resource policy** (Q19). *Can reject*: missing permission, integration timeout (29 s default), mapping-template failure for non-proxy integrations.
6. **Lambda service** - concurrency accounting happens here. *Can reject*: throttle (429/`TooManyRequestsException`) if concurrency is exhausted or reserved concurrency is hit.
7. **Execution environment** - reused if warm; created if not (`INIT`, Q65). Then the **runtime** invokes your handler with the event.

Two things worth saying at the end: **every hop has its own timeout and its own retry** (Q199, Q201), and **there are two authorization systems in the path** - one deciding whether the *caller* may use the API, and one deciding whether *API Gateway* may invoke the function. Candidates who conflate those two are easy to spot.

*Hook: a request-path failure you diagnosed by identifying which hop rejected it.*

### Q50. REST API versus HTTP API versus WebSocket API

| | REST API | HTTP API | WebSocket API |
| --- | --- | --- | --- |
| Price | Highest (roughly 3-4x HTTP API per million) | Lowest | Per message plus connection-minutes |
| Latency overhead | Higher | Lower | n/a |
| Auth | IAM, Cognito user pools, Lambda authorizer (request or token) | IAM, **JWT authorizer**, Lambda authorizer | IAM, Lambda authorizer on `$connect` |
| Features | Request/response validation and models, mapping templates, caching, usage plans and API keys, WAF, private endpoints, canary deployments, SDK generation | Proxy-first, CORS config, JWT, simpler; no built-in caching, no usage plans, fewer service integrations | Bidirectional, route selection, `@connections` management API |
| Integrations | Very broad AWS service integrations | Lambda, HTTP, some service integrations, private ALB/NLB/Cloud Map | Lambda and service integrations |

**My default in 2026: HTTP API.** For a modern service the pattern is a proxy integration to Lambda with a JWT authorizer against Cognito or an external IdP, and the features REST API adds are ones I would rather implement elsewhere - validation in the function or via a schema library, caching in CloudFront, WAF at the CloudFront layer, rate limiting per tenant in the application where the limit is a business concept rather than an API-key concept.

I would choose **REST API** deliberately when I need: usage plans and API keys as a *product* feature (a public developer API with tiers), a direct AWS service integration that removes a function entirely (Q53), private API endpoints inside a VPC, or the built-in request validation as a compliance control. And **WebSocket API** when I need server push and cannot use AppSync subscriptions or a managed alternative (Q95).

*Hook: an API type choice you made, and the feature or cost line that decided it.*

### Q51. REST chosen for validation and WAF, then the bill `[T]`

They paid a per-request premium of roughly 3-4x for two things they could have had almost free:

- **Request validation** is a JSON Schema check. Doing it in the function costs a few milliseconds of CPU on an invocation you are already paying for; doing it in REST API costs a higher rate on every request forever. The genuine value of gateway-level validation is *rejecting bad requests before they reach compute*, which matters if you are being hammered by garbage - but for well-behaved clients the validated fraction is ~100 percent, so you are paying to reject nothing.
- **WAF** attaches to CloudFront as well as to API Gateway stages. If there is a CloudFront distribution in front - and for a public API there usually should be - the WAF belongs there, where it also protects static content and where the rules are evaluated before the request enters the region.

What I would have done: **HTTP API behind CloudFront, WAF on the distribution, validation in the handler** (or in a thin shared library, so it is uniform across services). Then, if the traffic profile later shows a large fraction of malformed or unauthenticated requests, add the cheap rejection at the edge - a CloudFront Function for header/shape checks, or WAF rules - rather than moving the whole API to a more expensive tier.

The general principle worth stating: **pick the tier for the traffic you have, and put cross-cutting controls at the outermost layer that can enforce them.** Paying a per-request premium for a feature you use on a small fraction of requests is a pattern, not an accident - it shows up again with provisioned concurrency (Q69) and with DAX (Q159).

*Hook: an entry-tier cost you reduced by moving a control to a different layer.*

### Q52. Function URLs versus API Gateway versus ALB in front of Lambda

**Lambda function URL** - a dedicated HTTPS endpoint on the function itself, with `AWS_IAM` or `NONE` auth. Free (you pay only for invocations), lowest latency, supports response streaming and up to 15-minute execution (no 29-second cap). Use it for: internal service-to-service calls with IAM auth, webhook receivers, an origin behind CloudFront, and anything needing streamed responses or long duration. What it lacks: no throttling of its own beyond concurrency, no authorizers, no request validation, no path-based routing to multiple functions, no usage plans.

**API Gateway** - use it when you need an *API* rather than an endpoint: multiple routes across multiple functions, authorizers, throttling, staged deployments, custom domains with base-path mapping across services, and the developer-facing features of Q50.

**ALB in front of Lambda** - use it when Lambda is one target type among several. The genuine cases: a migration where some paths go to Lambda and others to ECS tasks or EC2 instances behind the same hostname and rules; an existing ALB-centric estate where adding a Lambda target is less work than introducing a gateway; and workloads where the ALB's hourly-plus-LCU pricing is cheaper than per-request API Gateway pricing at high volume. What you lose: the API-management features, and note the ALB's own idle timeout and payload limits (1 MB request/response for Lambda targets) apply.

The decision rule I would give: **function URL for an endpoint, API Gateway for an API, ALB when Lambda is a target in a mixed fleet.** And at very high volume, price all three - the entry tier can dominate (Q248).

*Hook: a case where you chose a function URL behind CloudFront instead of API Gateway, and what it saved.*

### Q53. API Gateway integration types

- **Lambda proxy (`AWS_PROXY`)** - the whole request is passed as an event and the function returns the whole response. The default and right answer almost always: no mapping templates, no gateway-side coupling to your payload shape.
- **Lambda non-proxy (`AWS`)** - you write VTL mapping templates to transform request and response. Powerful, unmaintainable, untestable. I use it only to adapt a legacy contract I cannot change.
- **HTTP / HTTP proxy** - forward to any HTTP endpoint (including a private ALB/NLB via a VPC link). Use it as a facade in front of an existing service during migration.
- **AWS service integration** - call an AWS API directly from the gateway with no compute in between. This is the one worth talking about.
- **Mock** - return a canned response. Useful for CORS preflight and for contract-first stubs.

**Where a service integration removes a function entirely:** any handler whose body is "validate, then make one AWS API call". Concretely - putting an event on **EventBridge** or a message on **SQS** from an ingest endpoint; a `PutItem` or `Query` on **DynamoDB** for a simple CRUD resource; starting a **Step Functions** execution; publishing to **SNS**; `PutRecord` to **Kinesis**. Removing the function removes cold starts, removes a runtime to patch, removes an error path, and removes the per-invocation cost - for a high-volume ingest endpoint this is a genuinely large saving.

The trade-off, and it is not small: the transformation logic moves into **VTL mapping templates or the newer request-parameter mappings**, which are hard to unit-test, hard to review and hard to debug (you get a `500` and a CloudWatch log line, not a stack trace). My rule is to use service integrations for **stable, simple, high-volume** paths - the ingest endpoint, the enqueue - and keep a function wherever the logic will change or needs real error handling. Step Functions Express with a direct integration is often the better middle ground when there is any orchestration at all (Q133).

*Hook: a function you deleted by using a direct service integration, and the volume at which that mattered.*

### Q54. Authorizers compared

| | IAM (SigV4) | Cognito user pool | JWT authorizer (HTTP API) | Lambda authorizer |
| --- | --- | --- | --- | --- |
| Who it is for | AWS principals: services, signed SDK clients | End users in a Cognito pool | End users with any OIDC-compliant IdP | Anything: custom tokens, opaque tokens, per-request policy |
| Latency | None added (gateway-side check) | Small, gateway-side | Small, gateway-side; JWKS cached | **A full Lambda invocation** unless cached |
| Caching | n/a | n/a | JWKS cached; token validated per request | TTL cache keyed by identity source, default 300 s |
| Failure mode | 403; nothing to break | Depends on Cognito availability | Depends on JWKS endpoint reachability at cache-miss | Your function's errors become 500s; a cold start is on the critical path of the *first* request |

The point to make: **prefer the gateway-native options.** IAM auth for service-to-service (it composes with everything else in this pack, and there is no token to leak). JWT authorizer for user-facing APIs, because validation happens in the gateway with no compute of yours in the path, and it works with any IdP - which makes it the modern default. A **Lambda authorizer** is for when you genuinely need custom logic: an opaque token to introspect, a per-request authorization decision that needs a database lookup, multi-tenant policy resolution, or a legacy header scheme.

The Lambda authorizer's hidden cost is that it is a second function on every request path: another cold start source, another thing to scale, another 429 opportunity, and another set of logs. Which leads directly to Q55.

*Hook: an authorizer choice you changed, and the latency or cost effect.*

### Q55. The 120 ms Lambda authorizer `[T]`

**The caching mechanism:** API Gateway caches the authorizer's *output policy* for `authorizerResultTtlInSeconds` (default 300, max 3600), keyed by the **identity source** you declared - typically the `Authorization` header. On a cache hit, your function is not invoked at all, so the 120 ms disappears for the TTL window.

**The cache-key trap**, which is what the question is really testing:

- If the identity source is the whole `Authorization` header (a JWT), the key is per token, so the cache is effective per user but useless for a first request per user - and for a large user base with short-lived tokens, the hit rate can be poor.
- If you use a **REQUEST**-type authorizer with multiple identity sources (header plus path plus query string), the cache key includes all of them, so the same user hitting a different path is a cache miss. People add `$context.path` for per-resource authorization and unintentionally destroy their hit rate.
- Conversely, if you return a **broad policy** (`Resource: */*`) and cache it, one cached decision authorizes every route - so a coarse policy plus caching can *over-grant*. If you return a narrow policy scoped to the requested method ARN and the cache key is only the token, the cached narrow policy will **deny** the same user's next request to a different route. This is the classic 403-after-caching bug, and the fix is to return a policy covering the routes the user is entitled to, not just the one requested.

**On permission revocation:** the cached decision stands for up to the TTL. A revoked token, a deleted user or a changed role continues to be authorized until the cache expires. There is no invalidation API. So the TTL is a direct trade between latency/cost and revocation lag, and you must pick it consciously: 300 seconds of stale authorization is fine for most applications and unacceptable for some (privileged admin routes, anything with a compliance requirement on immediate revocation). For those, use a short TTL or no cache on that route, or check a revocation list inside the handler where the decision is cheap.

*Hook: an authorizer cache setting you tuned, and the revocation requirement that constrained it.*

### Q56. Usage plans, API keys and throttling

API Gateway throttling exists at three levels: **account-level** per-region limits (requests per second plus burst), **stage and method-level** limits you set, and **usage-plan** limits tied to an API key (rate, burst and a daily/weekly/monthly quota). It is a token-bucket, so `burst` is the bucket size and `rate` the refill; exceeding it returns `429` with `Too Many Requests`.

What it protects: **your backend and your bill.** It is the outermost place to bound concurrency, which matters because Lambda concurrency is an account-level shared resource (Q68) and because a downstream database has a hard connection ceiling. It also protects *tenants from each other*, if the key is per tenant.

Where it sits relative to Lambda concurrency: **before it.** Requests rejected by API Gateway throttling never become invocations, so they cost you a fraction of a cent and no concurrency. That ordering is the reason to set gateway throttling below the point at which your Lambda concurrency or your database would fail: you want the cheap, well-behaved 429 rather than the expensive one, and you want the rejection to be *selective* (per key) rather than the indiscriminate rejection Lambda throttling gives you.

Important honesty: **API keys are not authentication.** They are for identifying and metering a *client*, not for authorizing a *user* - they travel in a header, get committed to repositories, and cannot be scoped. Say that out loud, because interviewers use usage plans to see whether a candidate conflates metering with security. Combine: JWT/IAM for auth, API key for the plan, WAF rate-based rules for abuse, and application-level quotas for anything that is a business concept.

*Hook: a throttling limit you set deliberately, and the downstream constraint that set the number.*

### Q57. Beyond the 29-second integration timeout

API Gateway's integration timeout maxes out at 29 seconds (it became configurable upward on REST APIs in some regions, but design as if 29 is the number). Two patterns:

**1. Asynchronous request-reply with a job resource.** `POST /reports` validates, writes a job record with status `PENDING`, starts the work (Step Functions execution, SQS message, or an async Lambda invoke) and returns **202 Accepted** with a `Location: /reports/{id}`. The client polls that resource, or - better - you push completion: WebSocket API, AppSync subscription, SNS to the client's webhook, or an emailed link. This is the correct answer for genuinely long work, and it also gives you retryability, visibility and idempotency for free, because the job is now a durable resource.

**2. Response streaming, bypassing API Gateway.** A **Lambda function URL** (or an ALB target) with `RESPONSE_STREAM` invoke mode has no 29-second ceiling and can start emitting bytes immediately - up to the function's 15-minute limit. Put CloudFront in front for TLS, WAF and caching. This is the right answer when the work is long but the client wants a single streamed response: an LLM token stream, a large CSV export, a server-sent-events feed.

Two things to name as *not* solutions: raising the Lambda timeout (does not help, the gateway gives up first) and retrying at the client (turns one 29-second failure into several, plus duplicate work if the function is not idempotent).

*Hook: a long-running operation you converted to a job resource, and what the client integration cost.*

### Q58. CloudFront cache key design

By default the cache key is **the distribution, the request path and the query string** according to your cache policy - and with the managed policies, `CachingOptimized` includes the URL path and *no* headers, no cookies, and no query strings unless you say so. Everything you add - a header, a cookie, a query parameter - **multiplies the number of cache entries**, so the cost of an addition is a lower hit ratio and more origin load.

What you legitimately add:

- `Accept-Encoding` (handled specially by CloudFront's compression support) so you cache gzip and brotli variants.
- A **device or variant header** if you truly serve different content - but prefer responsive content over device-specific caching.
- `Accept-Language` **only if** you actually serve translated content at that URL, and normalize it first (a Function can collapse `en-GB,en;q=0.9` to `en`) or you will cache per-browser-configuration.
- **Version or tenant in the path**, not in a header - path-based keys are easier to reason about and easier to invalidate.
- `CloudFront-Viewer-Country` for geo-variant content.

What you must **not** add: `Authorization`, `Cookie` (whole), `User-Agent` (raw), or any per-user identifier - each of these makes the key effectively per user, so the hit ratio approaches zero and you have paid for a CDN that is now a proxy. If the response is per user, mark it uncacheable and use the CDN for TLS termination, connection reuse and the backbone (Q62) instead.

The related mechanism to mention: **origin request policy is separate from cache policy.** You can *forward* a header to the origin without including it in the cache key, which is exactly what you want for things like a correlation ID or a signed token that the origin needs but that does not vary the response.

*Hook: a cache key you simplified, and the change in hit ratio and origin load.*

### Q59. 60 percent hit ratio on static assets `[T]`

In the order I would check:

1. **Cache-control headers from the origin.** No `Cache-Control`/`Expires`, or a short `max-age`, and CloudFront honours it. Also `Cache-Control: private`, `no-store`, or a `Vary: *` - any of which suppress caching entirely. This is the most common cause by a wide margin.
2. **Cache key over-specification** (Q58) - forwarding cookies, `User-Agent`, or a query string containing a cache-buster or analytics parameter (`?utm_source=...`) that varies per visitor. Query-string cache-busting on *versioned* filenames is the classic self-inflicted version.
3. **Traffic spread across many POPs with low per-object popularity.** Each POP has its own cache, so a long-tail catalogue served globally naturally has a lower first-hit ratio. **Origin Shield** exists for exactly this: it adds a regional caching layer so misses at many POPs collapse into one origin fetch.
4. **Object churn and TTL versus deploy frequency.** If you deploy hourly and invalidate everything each time, you throw away the cache you just warmed. Fingerprinted filenames plus long TTLs plus *no* invalidation is the correct pattern.
5. **Range requests, `Vary`, and compression mismatches** splitting entries; plus genuinely uncacheable responses (`4xx`/`5xx` with default short TTLs, or `Set-Cookie` on a static asset - a framework doing session handling on every response will do this).

How to actually diagnose rather than guess: the **cache statistics report** and the **`x-cache` header** (`Hit from cloudfront`, `Miss`, `RefreshHit`) on real requests, plus **CloudFront access logs** aggregated by `x-edge-result-type` and grouped by URI - that immediately shows whether misses are concentrated on a few paths (a header/TTL problem) or spread evenly (a popularity/Origin Shield problem).

*Hook: a hit ratio you improved, what the cause turned out to be, and the origin cost saved.*

### Q60. CloudFront Functions versus Lambda@Edge

| | CloudFront Functions | Lambda@Edge |
| --- | --- | --- |
| Runs at | The 400+ edge locations | Regional edge caches (13 regional locations) |
| Triggers | Viewer request, viewer response | Viewer request/response **and** origin request/response |
| Runtime | Purpose-built JavaScript, sub-millisecond, ~1-2 MB memory | Node.js or Python, full Lambda environment |
| Duration | Under 1 ms, no network calls, no filesystem | Up to 5 s (viewer) / 30 s (origin), can call other services |
| Price | Roughly 1/6th per request, no duration charge | Per request plus per GB-second |

**CloudFront Functions** are for cheap, synchronous, per-request manipulation with no I/O: header rewriting, URL normalization and rewriting, adding security headers, simple redirects, cache-key normalization (Q58), and lightweight token validation where the key is embedded. They run on every request, including cache hits, so they are the right place for anything that must always apply.

**Lambda@Edge** is for anything needing a network call or real logic: fetching from DynamoDB or Secrets Manager, calling an auth service, doing per-user A/B assignment with server-side state, generating a response, or manipulating the **origin** request - which is the capability Functions simply do not have. Note that origin-facing triggers only run on cache misses, which makes them much cheaper than viewer triggers at the same traffic level.

The decision rule: **start with a CloudFront Function; escalate to Lambda@Edge only when you need I/O or an origin-side trigger.** And name the third option, because it is often the right one: do it in the origin, or at the CloudFront configuration level (response headers policies, function-free redirects, OAC) where there is no code at all.

*Hook: an edge function you wrote, and whether you later moved it to a different layer.*

### Q61. OAC, signed URLs and signed cookies for paid downloads

**Origin Access Control** solves origin protection: the S3 bucket is private (no public access, no website endpoint), the bucket policy allows only the CloudFront distribution's service principal with a `AWS:SourceArn` condition on the distribution, and CloudFront signs its origin requests with SigV4. This means nobody can bypass CloudFront - and therefore nobody can bypass your WAF, your logging and your signed-URL checks. OAC replaces the older OAI and additionally supports SSE-KMS and non-GET methods.

**Then, viewer authorization:**

- **Signed URLs** - one URL per object, with an expiry (and optionally an IP restriction). Use when: a single file download, a URL you want to hand out in an email or an API response, or a case where each object needs different terms.
- **Signed cookies** - one authorization covering a *path pattern*, set as cookies on your own domain. Use when: the user is entitled to many objects (a video's HLS segments, a documentation site, a whole album), because signing every segment URL is impractical.

**The design for paid content downloads:**

1. The user authenticates to your API; your API checks the entitlement in the database.
2. Your API generates a **signed URL** (short expiry - minutes, not hours) using a **key stored in Secrets Manager or KMS**, with the key group configured on the distribution. Do not put private keys in the function's environment.
3. The client fetches the URL through CloudFront; OAC lets CloudFront read the private S3 object.
4. Log the entitlement decision on your side and correlate with CloudFront access logs for abuse detection.

Trade-offs to name: **a signed URL is a bearer token** - anyone who obtains it within the expiry can use it (Q174 in `11-security` terms), so keep expiries short, consider IP restriction where the client is stable, and accept that you cannot revoke it (rotating the key group revokes *all* of them, which is the blunt instrument). For high-value content, add per-user watermarking or DRM, because URL signing is access control, not copy control.

*Hook: a content-protection design you built, and how you handled abuse or link sharing.*

### Q62. CloudFront in front of an API when nothing is cacheable

Even with a zero percent hit ratio you get:

1. **TLS termination and TCP/QUIC handshakes at the edge**, close to the user. On a mobile network the handshake is a large fraction of first-byte latency, and terminating it 20 ms away instead of 150 ms away is a real improvement. HTTP/3 support comes for free here.
2. **Connection reuse over the AWS backbone.** The edge-to-origin connection is warm and travels AWS's network rather than the public internet, which improves latency *and* reduces variance - the p99 effect is bigger than the p50 effect.
3. **A single, stable front door**: one certificate, one WAF, one place for security headers, one place for geo-restriction, one hostname across multiple origins (`/api` to API Gateway, `/static` to S3, `/legacy` to an ALB) - which is a real architectural simplification.
4. **DDoS absorption** - Shield Standard at the edge, plus WAF rate-based rules applied before traffic reaches your region.
5. **Cheaper data transfer out.** CloudFront's egress rates are lower than regional egress, and traffic from origin to CloudFront is free. For a response-heavy API this alone can pay for it.
6. **Optional caching where you did not expect it** - `GET`s with short TTLs on reference data, and **stale-while-revalidate** style behaviour with origin failover to serve stale content during an origin outage.
7. **Origin failover** to a second region's endpoint on 5xx, which is a cheap piece of multi-region reliability (Q219).

What to be honest about: it adds a hop, a configuration surface and a cache to invalidate; for a purely internal, in-region API it is usually the wrong answer. And you must configure it correctly for dynamic content - forward the headers/cookies the origin needs via an **origin request policy** while keeping them out of the **cache policy** (Q58), and disable caching for methods that mutate.

*Hook: a dynamic API you fronted with CloudFront, and what the p99 and the egress bill did.*

### Q63. AppSync and GraphQL on AWS

AppSync is a managed GraphQL service: you define a schema, attach **resolvers** to fields, and each resolver maps to a data source - DynamoDB, Aurora via the Data API, Lambda, OpenSearch, an HTTP endpoint, or EventBridge. Resolvers are written in VTL or, now, in JavaScript, and **pipeline resolvers** chain several steps. **Subscriptions** are the differentiator: declare `@aws_subscribe` on a mutation and AppSync manages the WebSocket connections, the fanout and the filtering - you never operate a connection registry. **Caching** is a managed per-resolver or per-request cache. **Authorization** composes multiple modes on one API (API key, IAM, Cognito, OIDC, Lambda) and can be applied per field, which is unusually fine-grained.

When AppSync is the right entry point over API Gateway:

- **The client is a mobile or single-page app with variable data needs**, and the alternative is either over-fetching or a proliferation of bespoke endpoints. GraphQL's field selection is a genuine win here, and Amplify's client-side caching and offline support make it more than a protocol choice.
- **You need real-time push** and do not want to build the connection management that a raw WebSocket API requires (Q95). This is the single strongest reason.
- **You want to compose several backends** into one client-facing graph without writing a BFF service - **direct resolvers to DynamoDB mean no compute at all**, which is the same "delete the function" argument as Q53.

When not to: heavy, complex business logic per operation (you end up with Lambda resolvers everywhere, and you have paid for GraphQL to get REST with extra steps); public APIs consumed by third parties who expect REST/OpenAPI; teams with no GraphQL experience, because the failure modes - N+1 resolvers, unbounded query depth and cost, cache invalidation across a graph - are unfamiliar and sharp. GraphQL also makes rate limiting and cost attribution harder, because one request is not one unit of work.

*Hook: an AppSync or GraphQL decision you made, and whether the resolver model held up as logic grew.*

### Q64. The edge and entry tier for a global consumer application `[A]`

**Clarify first**: where are the users, what is the latency target for the API versus the assets, what is the upload size distribution, is the webhook sender able to retry, what is the compliance posture on where TLS terminates, and what is the traffic shape (steady, diurnal, spiky)?

**The design, per workload:**

| Workload | Choice | Why |
| --- | --- | --- |
| Static assets | S3 + CloudFront with OAC, fingerprinted filenames, long TTLs, Origin Shield, Brotli | Cache hit ratio near 100 percent, no invalidation needed, lowest egress rate |
| Public API | CloudFront -> **HTTP API** -> Lambda, WAF on the distribution, JWT authorizer | Cheapest gateway tier, edge TLS and backbone for latency (Q62), one WAF for everything |
| WebSocket notifications | **AppSync subscriptions** if the clients are already GraphQL; otherwise API Gateway WebSocket API with a DynamoDB connection table | Managed fanout beats operating a connection registry (Q63, Q95) |
| File uploads | **Presigned S3 URLs (multipart for large files)** issued by the API; S3 event to EventBridge for processing | Bytes never traverse the API or Lambda, so no payload limits, no gateway cost, no compute time paid for I/O (Q172, Q173) |
| Third-party webhooks | A **separate** endpoint: CloudFront -> HTTP API -> direct **SQS or EventBridge** service integration, verify signature in a CloudFront Function or in the consumer | Isolate untrusted, bursty, retry-happy traffic from user traffic; accept-and-enqueue means a slow consumer never causes the sender to retry (Q53) |

**Cross-cutting decisions I would state:**

- **One hostname, path-based origins** on a single distribution, so there is one certificate, one WAF and one log stream - and so a client sees one origin (no CORS preflight cost on the main path).
- **WAF placement at CloudFront**, with managed rule sets plus rate-based rules per IP and a stricter rate on the auth and webhook paths.
- **Separate the write path's throttling from the read path's**, because a spike in writes should not reject reads.
- **Route 53 latency-based routing** only if there is genuinely more than one origin region; otherwise a single region behind CloudFront is the right starting point and I would say so rather than over-building (Q229).

**Cost shape**: assets are dominated by CloudFront egress (so compression and cache ratio are the levers); the API is dominated by request count at the gateway plus Lambda GB-seconds (so HTTP API and right-sized memory matter, Q248-249); uploads are nearly free at the entry tier by construction; WebSockets are billed on connection-minutes, which for a consumer app with millions of idle connections is the line item to model *before* choosing (Q95).

**What I would deliberately not do**: put a Lambda authorizer on the hot read path, terminate uploads through API Gateway, or run a self-managed WebSocket fleet.

*Hook: an edge tier you designed, and the workload whose entry-tier cost surprised you.*

---

## 5. The Lambda execution model in depth

### Q65. The execution environment lifecycle

An **execution environment** is a MicroVM (Firecracker) that hosts one concurrent execution at a time and is reused across invocations.

**`INIT`** - runs once per environment, in three sub-phases: the *extension init* (any external extensions start), the *runtime init* (the language runtime boots - JVM start, class loading), and the *function init* (your static initializers, constructor and code outside the handler). Init has a 10-second budget for the managed runtimes' optimized path, and importantly **init CPU is not throttled the way you might assume** - you get full vCPU burst here, which is why heavy initialization is often cheaper than it looks. Init is **not billed** for the standard path (it is billed for provisioned concurrency and for SnapStart restore).

**`INVOKE`** - the runtime receives an event from the Runtime API and calls your handler. Repeats for the life of the environment. Between invocations the environment is **frozen**: no CPU is allocated, so background threads, timers and async I/O stop mid-flight (Q80).

**`SHUTDOWN`** - when Lambda decides to reclaim the environment (idle, or a deploy, or scaling down), registered extensions receive a shutdown event with a short grace period (up to 2 seconds for internal, 2 seconds signalled for external). Your handler code gets **no reliable hook** - `Runtime.getRuntime().addShutdownHook` may run but you cannot depend on it, and this is why "flush my buffered metrics on shutdown" must be an extension, not a `finally` block.

**What persists between invocations in the same environment**: everything in the process - static fields, connection pools, SDK clients, in-memory caches - plus the `/tmp` directory's contents. **What does not persist**: anything across *different* environments, and anything you assumed about wall-clock continuity.

*Hook: a bug that came from assuming either freshness or persistence of the execution environment.*

### Q66. Cold start, decomposed

A **cold start** is the additional latency incurred when an invocation must be served by a *new* execution environment rather than a warm one. Precisely: it is the `INIT` phase plus the environment creation, added to the invocation's duration as observed by the caller.

The components:

| Component | Typical scale | Can you influence it? |
| --- | --- | --- |
| Environment provisioning (MicroVM, network setup) | tens of ms | No (this is AWS's part) |
| Code/image download and unpack | ms to hundreds of ms | **Yes** - package size, layer count, container image size and layer caching |
| Runtime bootstrap | Node/Python ~50-100 ms; JVM ~300-600 ms | **Yes** - by choosing the runtime, or SnapStart/native image |
| Function init: class loading, DI container, SDK clients, config fetch | **The dominant term for Java**: 500 ms to several seconds | **Yes** - this is where almost all the winnable time is |
| First-invocation effects: JIT still interpreting, cold connection pools, empty caches, first TLS handshakes | hundreds of ms, decaying | **Partly** - priming, SnapStart with priming, connection pre-warm |

The two things that separate a good answer: first, **the biggest term for a Java function is usually your own initialization, not AWS's** - a Spring context is the cost, not Firecracker. Second, **the first *warm* invocation is also slow** because of JIT and cold pools, so "cold start" as a metric understates the problem; you should look at the latency distribution of the first N invocations of a new environment, not just at `InitDuration`.

Measure it properly: `InitDuration` in the CloudWatch `REPORT` line, the percentage of invocations with an init (that is your cold-start *rate*, which matters more than the duration), and p99 end-to-end from the caller's perspective.

*Hook: a cold-start reduction you measured, the component you attacked, and the before-and-after numbers.*

### Q67. What concurrency is, and the arithmetic

**Concurrency is the number of invocations executing simultaneously.** It is not a rate. By Little's Law:

```
concurrency = invocations per second x average duration in seconds
```

So 500 requests/second at 200 ms average needs 500 x 0.2 = **100 concurrent executions**. Halving the duration halves the required concurrency, which is why latency optimization is also a capacity and cost optimization.

Two refinements that matter in practice:

- **Use a high percentile, not the mean**, for the duration if the distribution has a tail: sizing on the mean leaves you throttling during the periods when durations are long, which is exactly when traffic is high.
- **Concurrency is per function per region, but the *limit* is account-wide** (default 1000, adjustable, shared across all functions in the region unless you carve it up with reserved concurrency). So your function's headroom depends on your neighbours.

For **event-driven, non-request** workloads the same arithmetic applies but the rate is set by the poller: an SQS event source mapping with batch size 10 processing 1000 messages/second at 200 ms per batch needs 100 x 0.2 = 20 concurrent executions.

*Hook: a capacity calculation you did before a launch, and how close the observed concurrency was.*

### Q68. 500 rps, 200 ms, 1000 concurrency `[T]`

The arithmetic: 500 x 0.2 = **100 concurrent executions** steady state. Against a 1000 limit, that is 10 percent utilization, so the naive answer is "comfortably enough". Which is the trap.

What can still throttle you:

1. **Burst.** The steady-state number says nothing about arrival shape. A traffic spike to 3000 rps for a few seconds needs 600 concurrency *immediately*, and Lambda only scales beyond the current level at a bounded rate (Q71). If the spike outpaces the scaling rate, you throttle even though your ceiling is 1000.
2. **Duration tail.** If p99 is 3 seconds - a slow downstream, a cold start, a GC pause - then during a downstream slowdown your concurrency requirement multiplies. A downstream at 2 seconds instead of 200 ms means 500 x 2 = **1000 concurrency**, exactly at the ceiling. This is the failure mode that actually happens: the throttle is a *symptom* of a downstream latency problem (Q200).
3. **Other functions.** The 1000 is shared across the region. A batch job in the same account can consume it.
4. **Reserved concurrency elsewhere** reduces the unreserved pool that this function draws from, so a colleague reserving 800 for their function leaves you 200.
5. **Per-source limits**, not Lambda's: API Gateway account-level throttling, the SQS event source mapping's own scaling ceiling, or a downstream connection limit (Q42, Q161) hit long before 1000.
6. **Provisioned concurrency misconfiguration**: if you have provisioned 50, invocations above that spill to on-demand normally, but a *reserved* concurrency of 50 on the same function is a hard cap that will throttle at 50.

So the correct answer is: "100 steady state, which fits, but I would size for the arrival burst and the p99 duration, and I would alarm on `Throttles` and on concurrency utilization rather than assume the ceiling."

*Hook: a throttling incident where the root cause was duration, not request rate.*

### Q69. Reserved versus provisioned concurrency

**Reserved concurrency** partitions the account limit. Setting reserved = 100 on a function does two things: it *guarantees* that function 100 concurrent executions (nobody else can take them), and it *caps* that function at 100. It is free. It is a **quota management** tool.

**Provisioned concurrency** pre-initializes N execution environments and keeps them warm: `INIT` has already run, so invocations up to N have no cold start. You pay an hourly rate per unit of provisioned concurrency *plus* a (lower) per-request/duration rate. It is a **latency** tool.

The case for using both on one function: a latency-sensitive, business-critical API where you want (a) no cold starts for the normal traffic band, and (b) a hard ceiling so a traffic anomaly cannot consume the whole account limit and starve other functions. So: provisioned concurrency at the p50-to-p90 traffic level, and reserved concurrency at a ceiling comfortably above the expected peak. Note the constraint: **provisioned concurrency must be less than or equal to reserved concurrency** when both are set, and it applies to a *version or alias*, never to `$LATEST` - which has real deployment consequences (Q238).

Two practical additions: use **Application Auto Scaling on provisioned concurrency** with a schedule or a utilization target, because paying for peak provisioned concurrency 24 hours a day is how this becomes expensive; and remember that **provisioned concurrency does not eliminate the first-warm-invocation JIT effect** unless you also prime (Q73, Q249).

*Hook: a function where you introduced provisioned concurrency, the latency improvement, and the monthly cost you accepted.*

### Q70. Reserved concurrency of 100 to protect a database `[T]`

It does protect the database. Two ways it makes the overall system worse:

1. **It converts a latency problem into a data-loss or error problem, at the wrong layer.** Once 100 is reached, further invocations are **throttled**. What happens then depends entirely on the invocation type, and none of the outcomes are good by default: a *synchronous* caller gets a 429 (so the user sees an error, and a naive client retries, amplifying load - Q200); an *asynchronous* invoke is retried by Lambda for up to six hours and then **dropped** unless you configured a DLQ or destination; an *SQS* mapping keeps the message and retries until `maxReceiveCount` sends it to the DLQ - so a sustained throttle silently fills your DLQ (Q130). You have moved the failure from "the database is slow" to "requests are being discarded", and the second is harder to see.
2. **It starves the function's own critical path while doing nothing about the real contention.** The cap is per function, but the database is shared: five functions each capped at 100 still present 500 connections. Meanwhile the cap applies uniformly, so a low-volume but critical operation (a payment write) is throttled equally with a bulk backfill running through the same function. And because the cap removes concurrency from the *unreserved pool*, you have also reduced headroom for every other function in the account.

What I would do instead, in order: **RDS Proxy** so connection count decouples from concurrency (Q162); **SQS in front** so the queue absorbs the burst and the event source mapping's `maximumConcurrency` shapes the drain rate with backpressure instead of rejection (Q129); **separate functions** for the critical and bulk paths so they can be throttled differently; and only then reserved concurrency, as a blast-radius ceiling rather than as flow control - with an alarm on `Throttles` so I find out when it engages.

*Hook: a protective limit you set that caused a second-order failure, and how you replaced it.*

### Q71. Burst concurrency and the scaling rate

Two separate mechanisms:

- **Burst concurrency**: when a function needs new environments, Lambda can create an initial burst immediately. Historically this was a region-dependent pool (500-3000) shared across the account; the current model gives each function its own burst allowance.
- **Sustained scaling rate**: beyond the burst, Lambda adds capacity in increments - the modern behaviour is **up to 1000 additional concurrent executions every 10 seconds, per function** (rather than the older account-wide 500-per-minute model). Requests beyond the currently available concurrency are throttled while it scales up.

How to design a spiky workload around this:

1. **Put a buffer in front.** SQS, Kinesis or EventBridge converts a spike in *arrival* into a queue with latency instead of a spike in *concurrency* with throttles. This is the single most effective answer and it should be the first thing you say.
2. **Provisioned concurrency with scheduled scaling** for *predictable* spikes - a marketing send, a market open, a batch window. Pre-warm before the event rather than discovering the scaling rate during it.
3. **Reduce duration**, which reduces required concurrency for the same rate (Q67) and therefore how far up the scaling curve you need to climb.
4. **Shard across functions** if you genuinely need more burst than one function gets - separate functions have separate burst allowances, though they share the account limit.
5. **Make the client behave**: exponential backoff with jitter and a retry budget, so a throttle does not become a retry storm (Q200).
6. **Raise the account limit in advance** - it is a support-ticket quota increase, not something you want to be requesting mid-incident.

*Hook: a spiky launch you prepared for, what you pre-warmed, and whether the scaling rate was ever the binding constraint.*

### Q72. What happens on a throttle, per invocation type

| Invocation type | Behaviour on throttle |
| --- | --- |
| **Synchronous** (API Gateway, ALB, function URL, SDK `Invoke`) | Immediate `429 TooManyRequestsException` with `Reason: ConcurrencyLimitExceeded`. Lambda does **not** retry. The caller must, or the user sees an error. API Gateway surfaces it as a 500 or 429 depending on configuration |
| **Asynchronous** (`InvokeAsync`, S3 events, SNS, EventBridge) | Lambda's internal queue holds the event and **retries for up to six hours** with backoff, in addition to the two retries on function error. If it never succeeds, the event goes to the configured **DLQ or `OnFailure` destination**, and is **silently discarded** if neither is configured |
| **SQS event source mapping** | The poller backs off; messages stay in the queue and become visible again after the visibility timeout. Retries continue until `maxReceiveCount` is exceeded, then the message goes to the queue's DLQ. Sustained throttling therefore *fills the DLQ* with messages that were never actually bad (Q130) |
| **Kinesis / DynamoDB Streams** | The poller retries the same batch, and **the shard does not advance** - so throttling one function stalls that shard for every downstream consumer of the same iterator, and `IteratorAge` climbs (Q121) |
| **Step Functions task** | Depends on your `Retry` block. `Lambda.TooManyRequestsException` is retryable and Step Functions retries it if you configured it - which you should, with backoff and jitter (Q139) |

The pattern worth articulating: **the further the invocation is from a human waiting, the more the platform retries for you, and the more likely the failure is silent.** Synchronous throttles are loud and lose the request; asynchronous throttles are quiet and lose the *event*, hours later, in a place you are not watching. That asymmetry is why `Throttles` deserves an alarm on every function and why DLQ depth deserves one too (Q124).

*Hook: a throttle whose consequence you only discovered later - in a DLQ, a rising iterator age, or a customer report.*

### Q73. SnapStart for Java

SnapStart takes a **Firecracker microVM snapshot of the initialized execution environment** after `INIT` completes, encrypts and caches it, and then *restores* from that snapshot instead of re-running `INIT` on a cold start. For a Spring Boot function it commonly cuts cold start from several seconds to a few hundred milliseconds.

**What is snapshotted**: the entire memory state after your static initializers, DI container construction, class loading and any warm-up you did in `INIT` - plus the JVM's state, which is why it helps so much for Java. **What is restored**: that same memory image, many times, for many concurrent environments, potentially days later.

**What must not be in the snapshot**, and this is the whole risk surface:

- **Anything unique per environment.** Random seeds, generated UUIDs, cached "instance IDs" - because every restored environment gets the *same* value (Q74).
- **Anything time-bound.** Credentials, tokens, signed URLs, cached secrets and TLS sessions captured at snapshot time will be stale on restore.
- **Open network connections.** Sockets, database connections and HTTP keep-alive connections do not survive; they must be re-established. A connection pool restored from a snapshot holds dead sockets.
- **Ephemeral filesystem assumptions**, since `/tmp` contents are part of the environment.

The mechanism to handle all of it is the **runtime hooks**: `Core.getGlobalContext().register(Resource)` with `beforeCheckpoint` (flush and close what must not be captured) and `afterRestore` (re-seed randomness, re-fetch credentials, re-open pools). AWS's `CRaC` integration is the standard way, and Spring Cloud Function / Spring Boot 3 support it.

Constraints to name: SnapStart applies to **published versions**, not `$LATEST`; there is a first-restore cost and a per-GB snapshot cache consideration; and the invocation must tolerate `afterRestore` latency. Alternatives worth comparing: **GraalVM native image** (faster still, but a build-time and compatibility cost) and **provisioned concurrency** (no cold start at all, but you pay hourly).

*Hook: a Java function where you enabled SnapStart, the p99 change, and the hook you had to write.*

### Q74. Duplicate identifiers and stale credentials after SnapStart `[T]`

Both bugs come from the same cause - **state captured once and restored many times** - but they need different fixes.

**Duplicate identifiers.** A `Random` or `SecureRandom` instance (or a UUID generator, or a Snowflake-style ID generator seeded with a "unique" node ID) initialized during `INIT` has its internal seed baked into the snapshot. Every restored environment starts from the identical seed and therefore produces the *identical sequence*. If you generate request IDs, idempotency keys or database primary keys from it, you get collisions across concurrent environments - and they look random and unreproducible, which is why this is a nasty bug.

*Fix*: re-seed after restore. Register a CRaC resource whose `afterRestore` re-initializes the RNG (`SecureRandom.getInstanceStrong()` fresh, or `setSeed` from a genuinely fresh entropy source). The general rule: **derive uniqueness at invocation time**, not at init time - use the Lambda request ID, or generate the UUID inside the handler with a freshly seeded generator.

**Stale credentials.** Anything fetched in `INIT` and cached - a Secrets Manager secret, an assumed-role session, an OAuth token, a signed connection string - was captured at snapshot time and may be hours or days old on restore. It will fail with an expired-token or authentication error, intermittently, on the functions that happened to restore from an older snapshot.

*Fix*: do not cache time-bound material across the checkpoint. Either fetch it in the handler with a short-lived in-memory cache keyed on expiry, or refresh it in `afterRestore`. Note the related trap: the AWS SDK's own credential provider is fine because it re-reads and refreshes (Q17), but a *client you constructed with explicitly resolved static credentials* is not.

The generalizable statement, which is what an interviewer wants: **SnapStart changes the identity of the `INIT` phase from "once per environment" to "once per snapshot", so every assumption of freshness or uniqueness in `INIT` becomes a correctness bug.**

*Hook: a SnapStart or native-image rollout where you found one of these, and how you caught it before customers did.*

### Q75. Memory and CPU coupling

Lambda gives you one dial - memory, from 128 MB to 10,240 MB - and **CPU scales proportionally with it**. Roughly, one full vCPU arrives around 1769 MB; below that you get a fraction of a core, and above it you get additional vCPUs (up to about six at 10 GB). Network and I/O bandwidth also scale with the setting.

This has a counter-intuitive consequence for cost. Billing is **GB-seconds**: `memory (GB) x duration (s)`. If doubling memory more than halves the duration - which happens whenever the function is CPU-bound, and *always* happens for JVM startup and for anything single-threaded that was previously getting a fraction of a core - then doubling memory **reduces total cost**. If the function is I/O-bound (waiting on DynamoDB, an HTTP call), duration does not improve and doubling memory doubles cost.

So the tuning method is: **profile duration against memory across the range and pick the minimum of (memory x duration), not the minimum memory.** AWS Lambda Power Tuning (a Step Functions state machine) does exactly this, running the function at each setting with a real payload and plotting cost and duration so you can choose the cost-optimal point or the latency-optimal point (Q249).

Two Java-specific notes: below ~1 vCPU the JVM's own startup and JIT are badly penalized, so very low memory settings are usually false economy; and the JVM reads the container's memory limit, so `-XX:MaxRAMPercentage` matters here as it does in containers (`07-devops` Category 5).

*Hook: a function whose memory you tuned, and whether cost or latency drove the final setting.*

### Q76. 3008 MB configured, 180 MB used `[T]`

It can be **cheaper** because of the coupling in Q75: at 3008 MB the function has ~1.7 vCPUs, so a CPU-bound workload finishes much faster. If a 512 MB configuration takes 2000 ms and 3008 MB takes 300 ms, the GB-second arithmetic is `0.5 x 2.0 = 1.0` versus `2.94 x 0.3 = 0.88` - the larger setting wins, and it also gives a much better p99. Java functions with real initialization frequently land here.

It can be **more expensive** because you pay for allocated memory whether you use it or not. If the function is I/O-bound - it calls DynamoDB, waits 200 ms, returns - the duration is identical at 512 MB and 3008 MB, and you are paying ~6x for nothing. That is the common case for thin CRUD handlers, and it is why "set it high for safety" is a real, widespread waste.

**How I decide**: measure, do not reason. Run Power Tuning across 512/1024/1769/3008 with a representative payload, and look at the cost-versus-duration curve. Then choose using the workload's role:

- **Latency-critical, user-facing** - pick the knee of the latency curve even if it is slightly past the cost minimum.
- **Asynchronous, batch, queue-drained** - pick the cost minimum.
- **Either way, check the memory *headroom*** from `Max Memory Used` in the `REPORT` line, and leave enough that a large payload or a GC spike does not OOM. An OOM-killed Lambda is billed for the full duration and produces no result, so being too tight is expensive too.

The organizational version of the answer: put the tuning in the pipeline (a periodic Power Tuning run on the top-N functions by cost) rather than relying on developers to revisit a value they set once.

*Hook: a memory setting you changed and the effect on both bill and p99.*

### Q77. Runtimes: managed, custom, container image

- **Managed runtime** (Java 21, Node, Python, .NET): AWS provides and patches the runtime, you ship a ZIP of your code plus dependencies (up to 50 MB zipped / 250 MB unzipped). Fastest cold starts, least operational work.
- **Custom runtime** (`provided.al2023`): you implement the **Runtime API** loop - poll `/next`, invoke, POST the response - so any language works, including a GraalVM native binary or Rust. You own the runtime's patching.
- **Container image**: package as an OCI image up to **10 GB**, pushed to ECR. Lambda does not run Docker; it extracts and caches the image layers into its own optimized format, then runs it in the same Firecracker environment.

**What the container option actually changes**, since this is the substance of the question:

1. **Size**: 10 GB instead of 250 MB. This is the real reason people choose it - large ML dependencies, native libraries, fonts, browser binaries.
2. **The build and supply chain**: you now use the same Dockerfile, registry, scanning, signing and SBOM tooling as the rest of your estate (`07-devops` Category 4). For an organization standardized on containers, this consistency is worth a lot, and it is the strongest non-size argument.
3. **What it does *not* change**: the execution model is identical - same lifecycle, same freeze/thaw, same concurrency, same 15-minute limit, same handler contract. It is not "running a container"; there is no port to listen on unless you use the Web Adapter, no `docker run` semantics, no sidecars.
4. **Cold start**: with layer caching, comparable to ZIP for reasonably sized images; noticeably worse for very large ones, because the first pull of an uncached image is real work. You do *not* pay for the image download in billed duration, but the caller waits.
5. **Deployment mechanics**: the artifact is an ECR image digest, so cross-region deployment needs the image replicated to an ECR repository in each region - a genuine friction point people forget.

My default is the managed runtime for typical services, container images when the dependency set is large or when consistency with the container pipeline is the deciding organizational factor.

*Hook: a function you packaged as a container image, and what drove the choice.*

### Q78. Layers and extensions

A **layer** is a ZIP overlaid onto `/opt` in the execution environment at `INIT`. Up to five layers, counting toward the 250 MB unzipped limit. Used for shared dependencies, native binaries and the Powertools/extension distributions. The honest assessment: layers are a *packaging* convenience with real downsides - they are versioned artifacts you must publish per region, they are not resolved by your build tool so they bypass dependency management, and they make "what is actually deployed" harder to answer. I use them for genuinely shared binaries and vendor extensions, and I prefer bundling application dependencies in the artifact.

An **extension** is a process that runs *alongside* your function in the same environment, registered with the **Extensions API**. Two kinds: **internal** (in-process, e.g. a JVM agent via `JAVA_TOOL_OPTIONS`) and **external** (a separate process from a layer, started before the runtime, which can be in any language).

What an extension does that your handler cannot:

- **Run during `INIT` before your code**, and continue running **between invocations** while your function is frozen - so it can pre-fetch configuration and secrets and serve them locally (the Parameter Store / Secrets Manager extension and AppConfig extension are exactly this, and are the correct answer to Q241).
- **Receive the `SHUTDOWN` event** with a grace period, which is the only reliable hook for flushing buffered telemetry. This is why every observability vendor ships an extension: batching metrics/traces in-process and flushing at shutdown removes per-invocation network calls from your billed duration.
- **Subscribe to the Telemetry API** to receive platform and function logs and traces directly, without going through CloudWatch - which is how you get logs to a third party without paying CloudWatch ingestion (Q188).

The cost: an external extension consumes memory and some CPU in your environment (so it is on your bill and can affect duration), adds to cold start, and is code running with your function's permissions - which is a supply-chain consideration worth naming.

*Hook: an extension you adopted or wrote, and what it removed from the invocation path.*

### Q79. What is safe in `INIT`, and what is a trap

**Safe and recommended** - do these once rather than per invocation:

- Construct **SDK clients** (they are thread-safe and expensive to build), with explicit region and, ideally, HTTP client and timeout configuration.
- Build the **DI container / Spring context**, load configuration, compile regular expressions, parse schemas, build immutable lookup tables.
- **Fetch configuration and secrets** - with the important caveats below.
- Establish **connection pools**, sized to *one* concurrent execution (see the trap).

**Traps:**

1. **Secrets fetched in `INIT` and cached forever.** Rotation will not be picked up, and with SnapStart they are stale on restore (Q74). Fetch with a TTL cache, or use the Parameter Store/Secrets Manager extension (Q241).
2. **Connection pools sized like a server's.** Each environment serves *one* invocation at a time, so a pool of 20 gives you 20 connections per environment times the concurrency - which is how you get Q161. Size the pool at 1-2.
3. **Background threads, schedulers and async clients.** The environment freezes between invocations, so anything not driven by the handler stops mid-operation and resumes later or never (Q80). A `ScheduledExecutorService` refreshing a cache every minute will not fire on schedule.
4. **Work whose failure is invisible.** An exception in `INIT` fails the invocation with an opaque `Runtime.ExitError` or init error, and if it is intermittent (a network call to a config service) you get correlated failures across all cold starts. Keep `INIT` deterministic and offline where possible, and fail fast with a clear message.
5. **Assuming `INIT` is billed or unbilled consistently** - it is unbilled for standard invocations but billed for provisioned concurrency and SnapStart restore, so "do everything in init, it's free" is not a safe general rule.
6. **Very heavy init that exceeds the init budget**, producing a timeout on the first invocation only - a genuinely confusing failure mode.

*Hook: something you moved into or out of `INIT`, and the effect on cold start or on correctness.*

### Q80. A background thread that stalls and resumes `[T]`

The mechanism is the **freeze/thaw cycle**. When your handler returns, Lambda **freezes the entire execution environment**: all threads are suspended and no CPU is allocated. Wall-clock time continues, but your process does not execute. When the next invocation arrives - which may be milliseconds or many minutes later, and may be on a different request - the environment is **thawed** and every thread resumes exactly where it was.

So a thread that was mid-HTTP-request when the handler returned resumes minutes later, discovers its socket has been closed by the peer (or by NAT idle timeout), and fails. A thread that was sleeping for 60 seconds sleeps for "60 seconds of thawed time", which may be an hour of wall clock. And a fire-and-forget task started at the end of an invocation may complete during a *later, unrelated* invocation - which is why you see log lines attributed to the wrong request ID, one of the more confusing symptoms in serverless.

The correctness consequences: **never fire-and-forget in Lambda.** Anything that must complete has to complete before the handler returns - `join()` the thread, `await` the future, flush the buffer. Anything periodic must be driven externally (EventBridge Scheduler) rather than by an in-process timer. And anything that batches for efficiency across invocations must be an **extension** (Q78), because extensions get a shutdown hook and are designed for exactly this.

The related detail worth adding: this is also why an async SDK call whose future you do not await may or may not have happened, which produces the classic "the metric is sometimes missing" and "the log line is in the wrong invocation" bugs.

*Hook: a fire-and-forget or async pattern that produced misattributed or lost work, and how you found it.*

### Q81. `/tmp`, ephemeral storage and cross-invocation state

`/tmp` is writable, sized from 512 MB up to **10,240 MB** (configurable, billed per GB-second above the free 512 MB), and **persists for the life of the execution environment** - so a later invocation in the same environment sees files an earlier one wrote. It is not shared between environments and it is not durable.

**What you can safely cache in the environment** (memory or `/tmp`):

- Immutable reference data: a lookup table, a machine-learning model, a compiled template set, a large static configuration file downloaded from S3 once.
- Idempotent, expensive-to-derive artifacts keyed by content hash.
- Anything with a **TTL and a size bound** where a stale or missing entry is merely a performance issue: a JWKS key set, a feature-flag snapshot, a secret with a short TTL.

**What you must never cache**:

- **Anything per request or per user.** The environment is shared across *sequential* invocations from different callers, so caching "the current user" in a static field is a cross-tenant data leak - the most serious mistake in this category, and it happens (a request-scoped field made static "for performance").
- **State you rely on for correctness**: a counter, a dedupe set, a "have I already processed this" marker. The environment can vanish at any time and there may be a thousand of them; correctness state belongs in DynamoDB (Q126).
- **Anything with a security lifetime you cannot bound** - long-lived credentials, decrypted PII written to `/tmp` and never cleaned. Treat `/tmp` as a disk that a *later, possibly different* invocation can read.
- **Large per-invocation temp files without cleanup**, which accumulate and cause `No space left on device` after N invocations - a classic warm-environment-only bug.

*Hook: a cache you added at the environment level, how you bounded it, and a leak or staleness issue you had to handle.*

### Q82. "Run our Spring Boot service on Lambda unchanged" `[A]`

**Clarify first**: what is the traffic shape and volume, what is the p99 latency requirement, is it a request-response API or does it have background schedulers and message listeners, does it hold long-lived state or connections, and what is driving the request - cost, operations, or a mandate?

**What I would tell them.** It is technically possible: the AWS Serverless Java Container or Spring Cloud Function's adapter will run a Boot application behind a Lambda handler, and the Lambda Web Adapter will run it *as an HTTP server* with almost no code change. So the question is not feasibility, it is whether the result is good. Four things determine that:

1. **Cold start.** A Boot context with JPA, security and a dozen starters is 3-8 seconds of `INIT`. With SnapStart (Q73) and priming that typically comes to a few hundred milliseconds; with provisioned concurrency it disappears at an hourly cost. So the honest statement is: *this is solvable, but only by adopting SnapStart or provisioned concurrency, and SnapStart brings its own correctness work (Q74).*
2. **What in the application assumes a server.** `@Scheduled` jobs will not fire reliably (Q80); `@KafkaListener`/JMS listeners have no thread to run on between invocations; in-memory caches and HTTP sessions are per environment and therefore wrong; a connection pool of 20 becomes 20-per-environment (Q79, Q161); a graceful-shutdown hook does not exist. Each of these needs a redesign, not a configuration change - the scheduler becomes EventBridge Scheduler, the listener becomes an event source mapping, the session becomes a token or DynamoDB.
3. **The 29-second and 6-MB boundaries** if it sits behind API Gateway, and 15 minutes / 6 MB response overall. Any long request or large payload needs the patterns of Q57 and Q172.
4. **Cost at their volume.** Above roughly the level where a Lambda runs continuously, always-on Fargate is cheaper (Q94). I would run the arithmetic with their actual request count and duration before agreeing to anything.

**What I would measure**, in a spike over a few days: `InitDuration` with and without SnapStart, p50/p99 end-to-end under realistic concurrency, memory-versus-duration curve (Q75), cost per million requests versus the equivalent Fargate task, and a list of every `@Scheduled`, listener, static cache and connection pool in the codebase.

**Conditions under which I agree**: traffic is spiky or low-duty-cycle (so we are paying for idle today); the application is genuinely request-response with no background work; the p99 budget can absorb SnapStart's restore or we accept provisioned concurrency's cost; and the team is willing to own the operational differences. **Conditions under which I refuse and recommend Fargate instead**: steady high traffic (cost), hard sub-100 ms p99 (any cold start is a violation), long-running or streaming work, or significant background/stateful behaviour. In that case I would still get most of the benefit they are asking for - no servers, autoscaling, per-second billing - with a fraction of the change.

**And the alternative I would raise**: if the goal is serverless economics rather than Lambda specifically, containerize as-is on Fargate first, then extract the genuinely event-driven parts into functions incrementally. That gets a result in weeks and does not require rewriting the application's assumptions in one step.

*Hook: a Boot-on-Lambda decision you made in either direction, the numbers you based it on, and how it aged.*

---

## 6. Compute selection and the serverless boundary

### Q83. The compute decision framework

**The first question is: what is the shape of the work?** Not "which is cheapest" and not "which is most modern" - shape, meaning duration, arrival pattern, statefulness and duty cycle. Everything else follows.

```
Is it event-driven, short (<15 min), stateless, and spiky or low duty cycle?
  -> Lambda
Is it a long-running server, or does it need >15 min, persistent connections,
   local state, sidecars, or a specific runtime environment?
  -> Containers. Then:
       Do you need Kubernetes' ecosystem/APIs, or multi-cluster/multi-cloud portability,
       and do you have the people to run it?
         yes -> EKS (Fargate or managed nodes or Karpenth)
         no  -> ECS on Fargate (default), ECS on EC2 (if you need instance control,
                GPUs, very high density, or per-instance cost optimization)
Is it a batch/HPC job with a queue and a completion, possibly hours long?
  -> AWS Batch (Fargate or EC2, spot-friendly)
Is it a legacy application, license-bound, or needing full OS control?
  -> EC2, and be honest that you own patching and scaling
Is it a simple web service and the team wants no infrastructure at all?
  -> App Runner (with the caveats of Q92)
```

The three secondary questions that break ties: **duty cycle** (below roughly 20-30 percent continuous utilization, per-request billing wins - Q94), **operational capacity** (does this team have anyone who can debug a cluster at 3 a.m.), and **the existing estate** (adding a thirteenth Fargate service to a working platform beats introducing a second paradigm for one service).

What I would say explicitly: the *default* for new work in a serverless-first estate is Lambda for event handlers and Fargate for long-lived services, and the burden of proof is on anything else.

*Hook: a compute decision where the "obvious" answer was wrong, and the characteristic that changed it.*

### Q84. Five characteristics that make Lambda wrong

1. **Steady, high, continuous load.** Per-request billing is a premium for elasticity; at high duty cycle you are paying it on every request forever. Above the crossover (Q94) always-on containers are cheaper, often several-fold.
2. **Long or unbounded duration.** The 15-minute ceiling is hard. A batch that grows with the data, a video transcode, a large migration, a job that occasionally takes 40 minutes - each needs either decomposition (Step Functions distributed map) or different compute. Fighting the limit with checkpointing is sometimes right and often a smell.
3. **Persistent connections and server-push.** WebSockets, gRPC streaming, long-polling, MQTT sessions, database connections held open for transaction spans. Lambda's freeze/thaw model (Q80) is fundamentally incompatible with holding a connection, so you need a connection-management tier anyway - at which point that tier is the server.
4. **Hard, low p99 latency.** Anything with a sub-50-100 ms p99 requirement across *all* requests cannot tolerate cold starts, and provisioned concurrency at sufficient scale to guarantee it approaches the cost and operational shape of always-on compute - so you have bought the worst of both.
5. **Heavy local state or resources**: a large in-memory cache or model that must be warm, GPU requirements, high-throughput local disk, or a process that legitimately needs many cores for a sustained period. The environment is single-concurrency, so per-environment caches are duplicated N times and cache hit rates collapse.

Two honourable mentions: **workloads with a hard downstream connection ceiling** (Q161) where concurrency is the enemy, and **anything requiring a specific OS, kernel module or license-bound runtime**.

*Hook: a workload you moved off Lambda, which of these it was, and the improvement.*

### Q85. Three container workloads that should be Lambda

1. **Scheduled jobs and cron containers.** A task that runs for 90 seconds every hour, on a service running 24/7 (or on a Fargate scheduled task with a minute of startup overhead). Lambda plus EventBridge Scheduler is cheaper by orders of magnitude and removes the "is the scheduler running" failure mode.
2. **Queue consumers with bursty backlogs.** A worker deployment sized for peak, idling most of the day. An SQS event source mapping scales from zero to hundreds and back, with no HPA to tune and no minimum replica count. The usual blocker is a shared codebase where the consumer is a mode of the main application rather than a separate artifact.
3. **Glue and reaction code**: S3-triggered processing, webhook receivers, event transformers, notification senders, index updaters, image thumbnailers. This is where a lot of "microservices" that are really three endpoints and a listener live, each costing a minimum of two always-on tasks for availability.

**What usually blocks the move**, and this is the more interesting half of the answer:

- **A shared monolithic artifact** - the code cannot be deployed as a function without extracting it, and nobody is funded to extract it.
- **Startup cost in a framework** that makes cold start unacceptable, which is really the SnapStart/native-image conversation (Q73) rather than a fundamental blocker.
- **Local development and testing habits** built around `docker compose`, so the team's whole workflow assumes a server.
- **Connection-pooled relational access** with no RDS Proxy, so concurrency breaks the database (Q161) and the team concludes "Lambda does not work with our database".
- **Organizational**: the platform team supports Kubernetes and does not support Lambda, so choosing Lambda means owning your own paved road.

*Hook: a container-to-Lambda migration you made, the saving, and which blocker you had to remove first.*

### Q86. ECS on Fargate versus ECS on EC2

| | Fargate | EC2 |
| --- | --- | --- |
| Unit you pay for | vCPU-seconds and GB-seconds per **task** | Instance-hours, whatever the task packing |
| Patching | AWS patches the substrate | You patch the AMI and drain nodes |
| Placement | AWS places the task; you choose subnets and AZ spread | **Placement strategies and constraints**: spread, binpack, affinity, instance attributes |
| Density | One task's resources are its own; no bin packing across tasks | High density possible - many small tasks per instance |
| Capacity | No capacity planning; task-level scaling | Capacity providers with managed scaling, plus warm pools |
| Spot | Fargate Spot (interruption with 2-minute notice) | EC2 Spot with full diversification control |
| Not available | GPUs, privileged mode, custom kernel parameters, host networking, daemon-type tasks, EBS-heavy I/O patterns (though EBS attach now exists), very large instance-local disks | - |

**Capacity providers** are the bridge concept: on EC2 they run an Auto Scaling group with **managed scaling** targeting a capacity-provider reservation percentage, plus **managed termination protection** so scale-in does not kill running tasks. That machinery is what you inherit responsibility for by choosing EC2.

**What you lose without an instance**: bin packing (so many small tasks are more expensive on Fargate), the ability to run daemons and agents per host, GPU and specialized hardware, per-instance cost optimization via Reserved Instances/Savings Plans on specific families, and host-level debugging - though ECS Exec covers most of the practical need for the last one.

My default is **Fargate**, and I move to EC2 for a specific reason: GPUs, a genuine density/cost argument at scale (hundreds of small tasks), a daemon requirement, or an instance-type need Fargate does not offer. "We might need to SSH in" is not a reason.

*Hook: a Fargate-versus-EC2 decision, and whether the density argument turned out to be real.*

### Q87. Lambda to Fargate to avoid cold starts, worse at peak `[T]`

Because they replaced a **per-request scaling model with a per-task scaling model, and the scaling loop is far slower than the traffic**.

On Lambda, a spike is absorbed by creating environments in seconds (Q71); the cost is a cold start on some requests. On Fargate behind an ALB, a spike is absorbed only by tasks that already exist. New capacity requires: CloudWatch metric publication (up to a minute of aggregation), the target-tracking alarm to breach (typically 1-3 datapoints), the service to launch tasks (image pull plus application start - for a JVM service, 30-90 seconds), the ALB health check to pass N consecutive times, and only then does the task receive traffic. **Two to four minutes from spike to added capacity is normal.** During that window, the existing tasks absorb everything: queues build, thread pools saturate, latency rises, and if a health check times out under load the ALB removes a task and makes it worse - the metastable collapse of `07-devops` Q88.

So the trade they actually made: they removed a few hundred milliseconds of cold start on a small fraction of requests and introduced **multi-minute under-provisioning on every spike**, plus a new class of failure (the saturation feedback loop).

What I would have done instead: keep Lambda and address the cold start directly - SnapStart or provisioned concurrency with scheduled scaling (Q69, Q73) - which is cheaper than a Fargate fleet sized for peak. Or, if Fargate is right for other reasons, size for peak rather than autoscale into it, use **predictive or scheduled scaling** for known patterns, keep a warm buffer (target tracking at 40-50 percent utilization, not 80), put an SQS buffer in front of anything that can be asynchronous, and load-shed at the ALB/gateway rather than letting saturation cascade.

The general principle: **cold start is a latency tax on some requests; slow scaling is a capacity failure for all requests during the window.** People optimize the visible one.

*Hook: a scaling-model change that traded one latency problem for a worse one.*

### Q88. EKS versus ECS in 2026

**What genuinely justifies EKS:**

- **You need the Kubernetes ecosystem**, specifically: operators that manage stateful software (databases, Kafka, Spark, ML platforms), a service mesh with rich policy, Argo CD/Workflows, KEDA-style event-driven autoscaling, or CRDs your platform is built on. This is the strongest and most common legitimate reason.
- **Portability as a genuine requirement**, not an aspiration: a regulator or customer contract requiring the workload to run on-premises or in another cloud, or a real multi-cloud strategy with the staffing to match.
- **Existing Kubernetes skills and platform investment.** If your team already runs Kubernetes well, EKS is the lower-risk choice, and "use what you operate well" is a legitimate architectural argument.
- **A large, heterogeneous estate** where the abstraction pays for itself across hundreds of workloads, and where you want workload-level primitives (namespaces, quotas, network policies, RBAC) that ECS expresses more coarsely.

**What it costs you in people** - the part candidates skip: cluster version upgrades on AWS's support cadence (roughly annual, non-optional, with add-on and API-deprecation work each time); the add-on stack (CNI, CoreDNS, kube-proxy, CSI drivers, autoscaler, ingress controller, cert-manager, external-dns, metrics-server) each with its own version matrix; capacity and scheduling tuning; RBAC and multi-tenancy design; and the on-call skill to debug a control-plane or CNI issue. Realistically that is **one to two dedicated platform engineers minimum**, and more at scale.

**ECS** gives you 80 percent of the outcome with a fraction of that: no control-plane version treadmill, IAM instead of RBAC, native integration with ALB/Service Connect/CloudWatch, and Fargate as the default. For a Java estate of a few dozen services with no exotic requirements, ECS on Fargate is the answer I would defend, and I would say the burden of proof is on Kubernetes.

*Hook: an ECS-versus-EKS decision you made, and whether the operational cost matched your estimate.*

### Q89. EKS on Fargate versus managed node groups versus Karpenter

- **EKS on Fargate**: one pod per microVM, no nodes to manage. Fits: small clusters, isolated tenants, jobs, and control-plane-adjacent workloads. Limits that decide against it: no DaemonSets (so node-level agents must become sidecars), no GPUs, no privileged pods, limited storage options, coarse CPU/memory sizing (rounded up, so cost is higher per unit), and slower pod start than a warm node.
- **Managed node groups**: EC2 instances in an ASG that EKS manages, with Cluster Autoscaler. Fits: predictable workloads and teams who want conventional nodes. Cost: you choose instance types up front, so you are bin-packing into shapes you guessed.
- **Karpenter**: watches *unschedulable pods* and provisions right-sized nodes directly from EC2, choosing instance type, size and AZ per need, consolidating workloads onto fewer nodes over time, and terminating underused nodes.

**What Karpenter does that Cluster Autoscaler did not:**

1. **It is not bound to node groups.** Cluster Autoscaler scales pre-defined ASGs, so it can only add more of a shape you already chose; Karpenter picks from the whole instance catalogue per provisioning decision. That is the fundamental difference.
2. **Consolidation** - it actively repacks and removes nodes as workloads change, rather than only scaling in when a node is empty. This is where most of the cost saving comes from.
3. **Speed** - it talks to the EC2 fleet API directly instead of waiting for ASG reconciliation, so node provisioning is typically well under a minute.
4. **Native spot handling** with diversification and interruption awareness, and expiry/drift-based node recycling that helps with AMI patching.

The trade-off: Karpenter is another controller with real power (it can launch instances) and its own configuration model (NodePools, disruption budgets); misconfigured consolidation can churn nodes and disrupt workloads that lack PodDisruptionBudgets. For a serious EKS estate it is now the default choice, and I would say so.

*Hook: a Karpenter or autoscaler migration, and the cost or provisioning-time change you measured.*

### Q90. Spot for containers and Batch

**Mechanism**: Spot is spare capacity at a large discount (commonly 60-90 percent), reclaimed with a **two-minute notice** (EC2 Spot interruption notice, or Fargate Spot's task termination signal). Interruption is per instance/task and correlated by instance type and AZ.

**Interruption handling**, the part that determines whether spot is safe:

- Handle the notice: for containers, `SIGTERM` with a real graceful shutdown - stop accepting work, finish or requeue the in-flight item, deregister from the target group, exit within the window. This is the same discipline as `07-devops` Category 6, and if a service does not have it, spot will expose that.
- **Checkpoint long work** so a job restarts from progress rather than from zero.
- **Requeue, do not lose**: for queue consumers, an interrupted task's message returns to the queue after the visibility timeout - which is why SQS-driven workers are the ideal spot workload.
- On EKS, run the **Node Termination Handler** or Karpenter's interruption handling, plus PodDisruptionBudgets.

**Diversification** is the availability lever: request many instance types across many AZs (Karpenter or an ASG with a mixed-instances policy and `capacity-optimized` allocation), so the loss of one capacity pool is a partial event. A single instance type in a single AZ is how people conclude "spot is unreliable".

**Where spot is irresponsible**: the stateful primary of anything (a database, a leader, a stateful set with slow recovery); a workload whose interruption causes customer-visible errors and which has no graceful shutdown; a job with a hard deadline and no slack (batch capacity can be unavailable, not just interrupted); anything where the operational cost of the interruption exceeds the saving. And a nuance worth naming: **spot for a service that must maintain a minimum capacity is fine only as the *marginal* capacity** - baseline on on-demand or Savings-Plan-covered capacity, burst on spot.

*Hook: a spot adoption you drove, the saving, and an interruption that taught you something.*

### Q91. AWS Batch and array jobs

Batch manages a **job queue**, **compute environments** (Fargate, EC2 on-demand, EC2 spot) and a **scheduler** that provisions capacity to match the queue, with job dependencies, retries, priorities and **array jobs** (one submission, N indexed children, ideal for embarrassingly parallel work over a partitioned dataset).

**When Batch is right over the alternatives:**

- The work is **long** (beyond Lambda's 15 minutes) and **resource-hungry** (many vCPUs, large memory, GPUs) - genomics, simulation, rendering, large ETL, model training.
- You want **queue-based, priority-ordered scheduling with fair share** across teams, and dependency graphs between jobs.
- You want **aggressive spot usage with automatic retry**, which Batch's model is built for.
- The job count is large and variable, and you do not want to manage the capacity yourself.

**When Step Functions distributed map is better**: the per-item work is short (seconds), the items are numerous (millions), the unit of work is a Lambda invocation, and you want per-item error handling, result aggregation and a visible execution history. Distributed map handles up to 10,000 concurrent child executions and reads directly from S3 - so "process every object in this prefix with a function" is its case, not Batch's.

**When a Fargate fleet with SQS is better**: the work is continuous rather than a job with a completion, the container is long-lived, and you want a simple scaling story on queue depth. Batch's value is job *lifecycle* management; if there is no lifecycle, you do not need it.

*Hook: a batch workload you placed on one of these three, and the characteristic that decided it.*

### Q92. App Runner and similar abstractions

App Runner takes a container image or a source repository and gives you a public HTTPS service with autoscaling (including scale-to-zero-ish behaviour via provisioned instances), TLS, deployments and observability, with no load balancer, cluster, task definition or network configuration to write. Similar in spirit: Elastic Beanstalk (the previous generation), Amplify Hosting for front ends, Lightsail containers.

**The problem it solves**: the distance between "I have a container" and "it is serving traffic on HTTPS with autoscaling" is, on ECS, roughly a hundred lines of infrastructure - a cluster, a task definition, a service, a target group, a load balancer, listeners, security groups, log configuration, IAM roles. App Runner collapses that to a handful of settings. For a prototype, an internal tool, a small team's first service, or a demo, it is unambiguously the right choice and it saves real days.

**Why serious teams leave**: the abstraction removes the controls you eventually need. No fine-grained networking (VPC connectors exist but are limited), no sidecars, no per-request scaling control, limited concurrency and instance sizing options, fewer deployment strategies (no real canary), coarse observability, weaker integration with the rest of the estate's tooling, and a cost model that stops being competitive with Fargate as utilization rises. Add the structural reason: **a platform team standardizes on one substrate**, and an App Runner service is an exception to every module, pipeline and dashboard they have built.

So my framing: App Runner is a good *on-ramp*, and it is fine as a permanent home for genuinely peripheral services. It is a poor foundation for a platform, and the migration off it is a real project - which is worth knowing before you start rather than after.

*Hook: a service you put on App Runner or Beanstalk, and what eventually pushed it off.*

### Q93. Graviton

Graviton is AWS's ARM64 processor family. The current generation is typically quoted at **up to 40 percent better price-performance** than comparable x86 instances - part list price (roughly 10-20 percent cheaper per hour for the equivalent size) and part throughput. Lambda on `arm64` is similarly cheaper per GB-second and often faster for the same work. Real-world results vary by workload: memory-bandwidth- and integer-heavy work does well, some vectorized and legacy-native workloads do less well, so the honest answer is "measure it, expect 15-30 percent on a typical Java service".

**Migration risk for Java is low but not zero**, and knowing where the risk actually lives is the point:

- **Pure JVM bytecode is portable**, and modern OpenJDK builds (Corretto 17/21) are well optimized for ARM64. This covers most of a typical Spring service.
- **The risk is in native code**: JNI libraries, `netty-tcnative`, Snappy/LZ4/zstd bindings, image and crypto libraries, Lombok-style build tooling is fine but native agents are not, plus anything with a platform-classified artifact. The failure mode is `UnsatisfiedLinkError` at runtime, sometimes only on a code path you did not test.
- **Base images and layers** must be multi-arch; a `Dockerfile` pinned to an amd64 digest will silently emulate or fail.
- **Build pipelines** need ARM64 builders (or `buildx` with QEMU, which is slow) and multi-arch manifests, and your ECR scanning must cover both.
- **Third-party agents** - APM, security, log shippers - need ARM64 builds; this is a common blocker and worth checking first because it is out of your control.

Migration approach: build multi-arch images from the start, move a low-risk service, load test it (not just smoke test - JIT and GC behaviour differ), then roll out by tier. On Lambda it is a one-line architecture change and easy to A/B with an alias.

*Hook: a Graviton migration you ran, the measured saving, and the dependency that blocked or delayed it.*

### Q94. 40 million invocations and it costs more than two containers `[T]`

**When it became true**: at the point where the function's aggregate *busy time* approached continuous occupancy of the equivalent container capacity. 40 million invocations a month at, say, 300 ms is 12 million seconds of compute - about 4.6 seconds of compute per wall-clock second, so roughly **five continuously busy execution environments**. At 512 MB each, that is about 2.3 GB continuously - genuinely comparable to a pair of small always-on tasks, and Lambda charges a premium per GB-second precisely because it will scale to a thousand instantly and to zero afterwards.

**How you would have predicted it** - do the arithmetic at design time, not after the bill:

1. Compute **duty cycle**: `invocations x duration / seconds in the period`. Here `40e6 x 0.3 / 2.6e6 ≈ 4.6` continuously busy environments. Multiply by memory to get GB continuously consumed.
2. Compare with the cost of that much always-on capacity (Fargate vCPU/GB-hours, or EC2 with a Savings Plan), **plus** the always-on overheads Lambda does not charge you for: the load balancer's hourly and LCU cost, a minimum of two tasks per service for availability, NAT if applicable, and the engineering time.
3. The rule of thumb that falls out: **below roughly 20-30 percent duty cycle, Lambda wins; above it, containers win**, and the crossover moves in Lambda's favour if the traffic is spiky, if the alternative needs a load balancer, or if you would have to over-provision for peak.
4. Then add the request-charge term (per-million invocations), which for very short functions can dominate GB-seconds entirely - a 20 ms function is mostly paying request charges, and that is a different optimization (batch more per invocation).

**What I would actually do before migrating**, because "move to containers" is not the only lever: check the memory setting against the duration curve (Q76 - a wrong setting can be a 2-6x error), check whether invocations can be **batched** (an SQS batch of 10 is a tenth of the request charges and amortizes init), check for idle wait inside the duration (paying GB-seconds to wait on a slow downstream is pure waste - fix the downstream or move the wait to Step Functions), and check whether the traffic is actually flat or has a peak the container fleet would have to be sized for.

*Hook: a workload whose Lambda cost you modelled against containers, and which way the decision went.*

### Q95. Long-running and stateful workloads

| Workload | Right AWS home | Why |
| --- | --- | --- |
| **WebSocket server** | **API Gateway WebSocket API** (or AppSync subscriptions) with Lambda handlers and a DynamoDB connection registry; ECS/Fargate only if you need protocol control | The managed option holds the connections so your compute stays stateless. Fargate means you own connection state, sticky routing and fanout - and scaling a fleet with millions of open sockets is a specialist job |
| **gRPC streaming** | **ECS/Fargate or EKS behind an ALB (HTTP/2) or NLB** | Lambda cannot hold a stream; API Gateway does not speak gRPC. Long-lived bidirectional streams need a server |
| **Background scheduler** | **EventBridge Scheduler** (or a Scheduler rule) invoking Lambda / starting a Step Functions execution / running an ECS task | Never an in-process scheduler in a serverless component (Q80). EventBridge Scheduler gives you at-least-once delivery, retries, a DLQ and one-time schedules |
| **Long polling / SSE stream to clients** | **Lambda function URL with response streaming** behind CloudFront, up to 15 minutes; beyond that, Fargate | Streaming responses are supported now; duration is the boundary (Q57) |
| **Stateful leader / coordinator** | **Step Functions** for workflow state; DynamoDB with conditional writes for locks and leases; ECS with a single task only if you truly need a process | Externalize the state rather than keeping a special instance |
| **Long ETL / transcode** | **AWS Batch** or **Fargate task** started by Step Functions (`.sync`), with checkpointing | Duration and resource shape exceed Lambda; Step Functions supplies the lifecycle (Q91) |
| **Kafka consumer** | **Lambda with an MSK/self-managed-Kafka event source mapping** for moderate throughput; **Fargate/EKS** for high throughput, complex stateful stream processing, or Kafka Streams | The mapping handles offsets and scaling; stateful stream topologies need a running process |

The unifying principle to state: **push the statefulness into a managed service and keep your compute stateless**, and only run a long-lived process when the protocol or the state genuinely cannot be externalized.

*Hook: a stateful workload you re-homed, and what you externalized to make it possible.*

### Q96. A decision table driven by a p99 target

| p99 latency target | Viable compute | Notes |
| --- | --- | --- |
| **< 10 ms** | Not a network round trip to your own compute at all - CloudFront/edge cache, DAX, ElastiCache, or a CloudFront Function | If the requirement is real, the answer is caching architecture, not compute choice |
| **10-50 ms** | Always-warm containers (Fargate/EKS) with pre-warmed pools, or Lambda with **provisioned concurrency** sized above peak concurrency | Any cold start violates the budget; also check the *downstream* p99, which usually dominates |
| **50-200 ms** | Lambda with **SnapStart** (Java) or a fast runtime, provisioned concurrency for the baseline band, containers equally fine | The common band for user-facing APIs. Cold starts must be rare, not absent |
| **200 ms - 1 s** | Plain Lambda, any runtime, no special measures | Occasional cold starts fit inside the budget |
| **Asynchronous / no user waiting** | Lambda, Batch, Fargate - choose on cost and duration | Optimize for cost per unit of work, not latency |

How to use it in an interview: state the target, then state **what fraction of requests may exceed it** - because "p99 under 100 ms" with a 2 percent cold-start rate is arithmetically impossible without provisioned concurrency, and being able to say that out loud is the point of the table. Then check three things: the cold-start rate (`InitDuration` occurrences over invocations), the *warm* p99 (which may already exceed the target, making cold start irrelevant), and the downstream contribution. Most "we need always-warm compute" conclusions turn out to be a slow query.

*Hook: a latency target you were given, and whether the compute choice or the data path turned out to be the constraint.*

### Q97. A 25-service EC2 estate on Jenkins `[A]`

**Clarify first**: what are the deploy frequency and current pain (cost, reliability, velocity)? Which services are stateful? What is the team's operational skill set and appetite? Is there a compliance constraint on where code runs? And crucially - is there a business driver with a date, or is this an engineering initiative? The answer changes the sequencing entirely.

**How I would classify the 25**, using the shape test of Q83:

- **To Lambda (expect 6-10 services)**: scheduled jobs, queue consumers, webhook receivers, event transformers, notification senders, small internal APIs with low or spiky traffic. Criteria: stateless, short, no persistent connections, no hard sub-100 ms p99, and a duty cycle low enough that per-request billing wins (Q94).
- **To Fargate (expect 12-15 services)**: the main request-serving Spring Boot services. Criteria: steady traffic, long-lived, need a warm process, may hold pooled database connections. This is the bulk, and it is the *low-risk, high-value* move because it is a lift-and-shift of a JVM into a container.
- **Leave on EC2 (expect 2-4)**: anything license-bound, anything with a large local data set or unusual OS dependency, and the one legacy service nobody understands. Say this explicitly - a migration plan that claims 25 of 25 is not credible.

**The order, and the reasoning for it:**

1. **Fix the pipeline first, not the compute.** Build once into an immutable artifact (image plus digest), deploy from a pipeline with OIDC into per-environment accounts. Doing this on the *existing* EC2 deployment target proves the pipeline independently of the platform change, so a rollback is a rollback of one variable. This is the single most important sequencing decision.
2. **One pilot service to Fargate** - a medium-importance, well-understood, stateless service. Containerize, get the ALB/target group/service module right, get logging and metrics equivalent to today, run in parallel with weighted DNS or ALB weighted target groups, cut over, keep the EC2 stack for a rollback window. The output is a reusable IaC module and a runbook.
3. **Two or three Lambda pilots** - the scheduled jobs and one queue consumer, because they are asynchronous and therefore the safest possible place to learn cold starts, IAM, observability and the SnapStart question (Q73). Cost saving here is immediate and visible, which helps fund the rest politically.
4. **Roll the Fargate cohort in waves**, grouped by team so each wave transfers ownership, with the module improving each wave. Databases stay where they are throughout - do not combine a compute migration with a data migration.
5. **Extract the Lambda candidates from the monolithic artifacts** where needed - this is the slowest part, so it comes after the easy wins and only where the arithmetic justifies it.
6. **Decommission**: only after each service has run on the new platform through a full peak cycle, then delete the EC2 ASG, the AMI pipeline and the Jenkins job. Undecommissioned old paths are how you end up running both forever.
7. **Finally, the platform work**: standard modules, per-service dashboards and SLOs, cost attribution, and the Jenkins-to-pipeline retirement.

**What I would explicitly refuse**: a big-bang cutover; combining this with an EKS adoption (two paradigm changes at once); and moving the databases in the same programme. **What I would measure to prove it worked**: deploy lead time, change failure rate, cost per service per month, and p99 per service before and after - with the honest expectation that cost improves most for the Lambda cohort and *velocity* improves most for the Fargate cohort.

*Hook: a platform migration you sequenced, what you piloted first, and what you deliberately left alone.*

---

## 7. The event-driven backbone

### Q98. One-sentence identity of each service

- **SQS** - a durable *work queue* for point-to-point task distribution, where one consumer group processes each message and messages are deleted when done. *Selecting question*: "is this a unit of work for exactly one consumer?"
- **SNS** - a *push fanout* topic delivering each message to every subscriber (SQS, Lambda, HTTP, email, SMS, Firehose), with filtering. *Selecting question*: "do several independent things need this notification, right now?"
- **EventBridge** - a *routing and integration bus* with content-based rules, schema registry, archive and replay, cross-account and cross-region delivery, and SaaS/AWS-service event sources. *Selecting question*: "is this a domain event whose consumers I do not want to know about?"
- **Kinesis Data Streams** - an *ordered, replayable log* partitioned into shards, retaining records for hours to a year, where multiple consumers read at their own position. *Selecting question*: "do I need ordering, replay, or high-throughput stream processing?"
- **MSK** - managed *Apache Kafka*, when you need Kafka's ecosystem (Connect, Streams, ksqlDB), its semantics, or portability. *Selecting question*: "do I need Kafka specifically, and can I fund operating it?"

The question that selects between the whole set, in one line: **queue (work) versus topic (notify) versus bus (route) versus log (order and replay)**. If a candidate can say that sentence and then defend a choice against a specific requirement, that is the level.

*Hook: a messaging choice you revisited, and the requirement that changed it.*

### Q99. Delivery semantics per service

| Service | Guarantee | The detail that matters |
| --- | --- | --- |
| **SQS standard** | At-least-once, best-effort ordering | Duplicates are normal, not exceptional; also possible from redelivery after visibility timeout (Q101) |
| **SQS FIFO** | Exactly-once *processing* within the 5-minute dedupe window, strict ordering per message group | "Exactly-once" is scoped to deduplication by `MessageDeduplicationId` within 5 minutes - it is not a general guarantee, and your consumer still needs idempotency for anything beyond that window |
| **SNS** | At-least-once per subscriber, no ordering | A failed HTTP subscriber gets a retry policy; a failed Lambda gets Lambda's async retries; delivery to different subscribers is independent, so partial delivery is a normal state |
| **SNS FIFO** | Ordered and deduplicated, to SQS FIFO subscribers only | Narrow but useful |
| **EventBridge** | At-least-once, no ordering guarantee | Retries for up to 24 hours by default with a configurable retry policy and DLQ per target; duplicates possible |
| **Kinesis** | At-least-once, **ordered per shard** | A consumer that re-reads after a checkpoint failure reprocesses; ordering is only within a shard, so the partition key defines your ordering domain |
| **DynamoDB Streams** | At-least-once, ordered per **item** (per partition key) | Strictly ordered for changes to the same item, which is the useful guarantee; 24-hour retention |

The sentence to say out loud: **on AWS, everything is at-least-once, so idempotency is not optional** (Q126). Anywhere "exactly-once" appears it is either scoped to a deduplication window (SQS FIFO), or it refers to a specific framework's internal checkpointing, not to your side effects. And **ordering, where it exists, is always per partition** - shard, message group or item - never global (Q114).

*Hook: a place where you relied on a delivery guarantee that turned out to be weaker than you thought.*

### Q100. SQS visibility timeout

When a consumer receives a message, SQS makes it **invisible** to other consumers for the visibility timeout rather than deleting it. If the consumer deletes it within that window, it is gone; if the consumer crashes or takes too long, the message becomes visible again and is redelivered.

What it protects: **against losing work when a consumer dies.** It is the mechanism that makes SQS at-least-once rather than at-most-once. It is *not* a lock in any strong sense - it is a lease with a timer.

How to set it: **greater than the maximum time your consumer needs to process the message**, with margin. For Lambda, AWS's guidance is at least **six times the function timeout** when using an event source mapping, because a batch may be retried and the poller needs room. Concretely: function timeout 30 s means visibility timeout of at least 180 s.

The two failure directions:

- **Too short**: the message becomes visible while you are still working on it, another consumer picks it up, and you get *concurrent duplicate processing* (Q101). This is the common and dangerous one.
- **Too long**: a genuinely failed message waits a long time before retry, so recovery is slow and a poison message takes much longer to reach the DLQ.

For variable processing times, use `ChangeMessageVisibility` to **extend the lease as you work** (a heartbeat pattern) rather than setting a very long default. And note that the queue-level setting is a default - the receive call can override it per message.

*Hook: a visibility timeout you tuned, and the symptom that told you it was wrong.*

### Q101. Messages processed twice under load, no errors `[T]`

The most likely mechanism is **visibility timeout expiry under increased processing latency**. Under load, per-message processing time rises (contention, slower downstream, GC, throttled dependency). Once it exceeds the visibility timeout, SQS makes the message visible again while the first consumer is *still working on it* - so a second consumer starts processing the same message concurrently. Both eventually succeed and both delete (the second delete is a no-op or an expired-receipt-handle error you may not log). No errors, correct-looking logs, duplicate side effects. The tell is that it correlates with load rather than with failures.

The near neighbours worth naming, since a good answer offers the differential:

- **Batch partial failure without `ReportBatchItemFailures`**: one message in a batch of ten fails, so the whole batch is retried and the other nine are processed a second time (Q118). This is extremely common and also produces no visible error for the nine.
- **A retry at a layer above** - the producer retrying because it did not see the `SendMessage` response, so there are genuinely two messages with different message IDs.
- **SQS standard's inherent duplication**, which is rare but real and by design.
- **Lambda's own at-least-once invocation** for asynchronous paths.

How to distinguish: log the SQS `MessageId` *and* `ApproximateReceiveCount` on every processing attempt. Receive count > 1 means redelivery (visibility or batch failure); two distinct message IDs with the same business payload means producer-side duplication.

The fix is two-layered and both layers are needed: **tune the visibility timeout and implement `ReportBatchItemFailures`** to reduce redelivery, and **make the consumer idempotent** (Q126) so that redelivery is harmless. Only the second is a guarantee.

*Hook: a duplicate-processing incident, how you identified the mechanism, and the idempotency control you added.*

### Q102. FIFO message group ID and deduplication ID

**`MessageGroupId`** is the ordering and concurrency unit. Messages within a group are delivered in order, one in-flight batch at a time; different groups are processed **in parallel**. So the group key *is* your parallelism setting.

**`MessageDeduplicationId`** (or content-based dedupe hashing the body) causes SQS to discard a duplicate with the same ID within a **5-minute** window. This is what "exactly-once processing" means for FIFO, and its scope is exactly those five minutes.

**The throughput consequence of a coarse group key** is the crux. FIFO throughput is per group: with high throughput mode you get a large aggregate (thousands of messages/second per queue) but a **single message group is limited to a low per-group rate** (on the order of a few hundred messages/second, and effectively to one consumer at a time). So:

- Group key = `orderId` → thousands of independent groups → high parallelism, ordering guaranteed where it matters (per order).
- Group key = `"all"` or `tenantId` for a large tenant → one or a few groups → throughput collapses to a single consumer's rate, and one slow message blocks everything behind it (Q103).

The design rule: **choose the finest-grained group key that still satisfies your ordering requirement.** Ask "what actually must be ordered relative to what?" - almost always it is per aggregate (order, account, device), not globally. And pair it with a dedupe ID derived from a business key (not a timestamp or a random value, which defeats the purpose).

*Hook: a FIFO group key you chose, and whether you had to change it for throughput.*

### Q103. One FIFO group for global ordering `[T]`

**Mechanism**: with a single message group, SQS FIFO guarantees strict order by delivering messages for that group **serially** - a batch is in flight, and the next batch is not delivered until the previous one is deleted or its visibility expires. So the effective concurrency is one consumer, and throughput becomes `1 / per-message-processing-time`. A 50 ms handler gives you ~20 messages/second regardless of how many consumers you run, how much Lambda concurrency you have, or what the queue's quota says. Worse, **head-of-line blocking**: one slow or failing message stalls every message behind it for the visibility timeout, repeatedly, until it reaches the DLQ.

**What I would propose instead**, in order of preference:

1. **Interrogate the requirement.** "Global ordering" is almost never the actual need. The real need is usually per-entity ordering (per order, per account, per device) or *causal* consistency. Partition by that entity and you get ordering where it matters plus parallelism everywhere else (Q102).
2. **Make the consumer order-independent.** If events carry a monotonic version or timestamp, the consumer can apply them idempotently and reject stale updates with a conditional write (`version > current_version`) - DynamoDB conditional expressions do this in one call (Q156). This is the strongest answer because it removes the ordering dependency from the transport entirely.
3. **Use a log rather than a queue** if the semantics are genuinely stream-like: Kinesis with a partition key gives per-partition ordering with replay, and lets multiple consumers read independently (Q111).
4. **If global ordering truly is required** - a ledger with a single sequence, say - then accept the single-writer throughput and design around it: make the handler as fast as possible (batch, no synchronous I/O), keep the ordered path minimal (assign a sequence number and enqueue the real work to a parallel path), and be explicit with stakeholders about the ceiling.

The sentence worth saying: **strict global ordering is a single-writer design, and single-writer designs have a throughput number - so say the number out loud before agreeing to the requirement.**

*Hook: an ordering requirement you narrowed, and the throughput you recovered.*

### Q104. Long polling, short polling and empty receives

**Short polling** (`WaitTimeSeconds=0`) samples a subset of SQS's distributed servers and returns immediately, possibly with zero messages even when messages exist. **Long polling** (up to 20 seconds) holds the connection open until a message arrives or the timer expires, and queries all servers.

Costs:

- **Short polling costs money and CPU for nothing.** Every empty receive is a billable SQS request. A consumer looping with short polling issues requests continuously - at 10 polls/second that is 26 million requests a month per consumer, all of them likely empty on a quiet queue.
- **Short polling also adds latency and duplicates**: because it samples, a message can sit for several polls before being returned, and you may need more consumers to achieve the same drain rate.
- **Long polling reduces the request count by orders of magnitude** - one request per 20 seconds when idle - and *lowers* delivery latency, because the response returns the instant a message arrives rather than at the next poll tick. That is the counter-intuitive part worth stating: long polling is both cheaper and faster.

So it changes the bill by removing empty receives, which on an idle-heavy queue are the majority of your SQS charges. Set `ReceiveMessageWaitTimeSeconds` to 20 on the queue (so it applies by default) rather than relying on every client to pass it.

One nuance: with **Lambda event source mappings you do not control this** - the Lambda poller manages its own polling and you are not billed for its empty receives in the same way; the setting matters for self-managed consumers (ECS/EC2 workers, the SDK, Spring Cloud AWS listeners). Mentioning that distinction is a good signal.

*Hook: an SQS request-charge line you reduced, and by how much.*

### Q105. SNS fanout with SQS subscribers versus SNS to Lambda

**The pattern**: SNS topic → one SQS queue per consumer → each consumer's Lambda or worker reads its own queue. Versus SNS → Lambda directly, one subscription per consumer.

Why the queue per consumer is better:

1. **Independent failure and retry.** With a queue, a consumer being down or throttled means messages accumulate *in its own queue*; nothing is lost and nothing affects the other consumers. With direct SNS-to-Lambda, delivery relies on Lambda's asynchronous retry policy (a few attempts over some hours) and then the message is gone unless a DLQ is attached - and the retry behaviour is not yours to tune.
2. **Buffering and backpressure.** The queue absorbs a spike so the consumer drains at its own rate, with `maximumConcurrency` to protect a downstream (Q129). Direct SNS-to-Lambda converts a publish spike into a concurrency spike immediately, which is how one consumer's fanout exhausts the account's Lambda concurrency and takes out unrelated functions.
3. **Replay and inspection.** A queue is inspectable; you can pause a consumer, redrive from its DLQ, and see depth and age. A direct subscription has no such surface.
4. **Batching.** An event source mapping delivers batches, so you pay fewer invocations and can amortize per-invocation costs; SNS-to-Lambda is one invocation per message.
5. **Per-consumer configuration**: different visibility timeouts, different DLQ policies, different filter policies, different retention.

The cost is one extra hop and the SQS request charges, which is small. I would use direct SNS-to-Lambda only for genuinely low-volume, non-critical notifications where losing one is acceptable.

*Hook: a fanout you converted to queue-per-consumer, and the failure it prevented afterwards.*

### Q106. SNS filtering versus EventBridge pattern matching

**SNS filter policies** are attribute-based (and, with payload-based filtering, can inspect the message body): a JSON policy of attribute names to accepted values, with operators for prefix, anything-but, numeric ranges and existence. The filter is evaluated **in SNS, before delivery**, so a non-matching subscriber costs you nothing.

**EventBridge event patterns** match against the whole event JSON, including nested fields, with a richer operator set (prefix, suffix, numeric, `anything-but`, `exists`, wildcards, and `$or`), and content filtering on arrays. The filter is evaluated **in EventBridge, before the target is invoked**.

Comparison:

| | SNS | EventBridge |
| --- | --- | --- |
| Expressiveness | Good on attributes; body filtering is newer and more limited | Richer, arbitrary nesting, more operators |
| Where the filter runs | In SNS | In EventBridge |
| Targets | SQS, Lambda, HTTP, email, SMS, Firehose | 20+ AWS targets, API destinations, cross-account and cross-region buses |
| Cost model | Per publish plus per delivery; filtered-out deliveries are free | Per event published (custom bus); matching and delivery included; **AWS-service events on the default bus are free to ingest** |
| Extras | Message ordering (FIFO topics), high fanout throughput, mobile/SMS/email endpoints | Schema registry and discovery, **archive and replay**, input transformers, scheduler, Pipes |
| Latency | Lower, and higher raw throughput | Slightly higher, generally tens of milliseconds |

Where each wins: **SNS for high-throughput, low-latency fanout to a known set of subscribers** - especially the queue-per-consumer pattern of Q105, and anything needing SMS/email/mobile push. **EventBridge for domain-event routing where producers should not know consumers**, where you want the schema registry as a contract mechanism, where you need replay after an incident (Q110), or where the source is an AWS service or a SaaS partner.

In practice a mature estate uses both: EventBridge as the domain bus, and SNS where fanout volume or latency makes it the better transport.

*Hook: a routing layer you built, and whether you standardized on one or used both.*

### Q107. EventBridge routing for eight producers and twenty consumers

**Design:**

1. **One custom bus per bounded context**, not one bus for everything and not one per service. So `orders-bus`, `payments-bus`, `inventory-bus` - roughly matching the eight producers' domains, likely 3-4 buses. Rationale: a bus is a unit of access control, quota, archive policy and blast radius, and a single shared bus makes every rule a global concern; one bus per producer service is over-fragmented and makes cross-domain consumption awkward.
2. **A published event contract per event type**, registered in the **schema registry**, versioned in the event itself (`detail-type: "OrderPlaced"`, `detail.version: "1"`). Producers own the schema; consumers code against generated bindings.
3. **A rule per consumer per event set**, owned by the *consumer* team in their own IaC, targeting **their own SQS queue** (the queue-per-consumer principle of Q105 applies here too) - so a consumer's failure, retry policy and backlog are theirs, and adding consumer twenty-one requires no change to any producer.
4. **A DLQ on every rule target**, plus an alarm on `FailedInvocations` and on DLQ depth (Q124).
5. **Archive enabled on each bus** with a retention appropriate to the domain (30-90 days), so replay is possible (Q110).
6. **Cross-account**: if consumers live in other accounts, either grant `events:PutEvents` on the bus and let consumers create rules in their own account with a bus-to-bus target, or use a central bus with resource-policy-scoped access. I prefer bus-to-bus forwarding so each account's rules are local to the team that owns them.

**What I would explicitly design in**: an `input transformer` so consumers receive a shape they need rather than the raw envelope; **additive-only schema evolution** with a contract test in the producer's pipeline (Q108); and a naming convention (`source: com.acme.orders`, `detail-type: OrderPlaced`) enforced by a check, because inconsistent naming is what makes patterns fragile.

*Hook: an event bus topology you designed, and how you handled schema ownership across teams.*

### Q108. A rule silently stops matching after a producer adds a field `[T]`

**How it happens.** EventBridge patterns match on the fields you specify and ignore the rest, so *adding* a field is normally harmless. The rule stops matching when the producer's change interacts with a pattern that is more brittle than it looks:

- The pattern used **`"$or"` or an exact-match on a container** where the new field changed the structure (a scalar became an object, or a field moved into a nested object).
- The pattern matched on a field the producer **renamed or moved** while "adding" the new one - a refactor that looks additive in the producer's mind and is breaking in the contract.
- The `detail-type` or `source` was changed as part of the same release (versioning by changing `detail-type` is a common and legitimate practice, and it silently orphans old rules).
- The producer started sending the event to a **different bus**, or through a Pipe with a transform.
- Content filtering on an **array** where the new field changed array shape, or a numeric matcher where a value became a string (`"5"` versus `5` - EventBridge is type-sensitive, and this is a genuinely common cause).

The reason it is *silent* is the important part: **a non-matching rule is not an error.** EventBridge has no metric for "an event nobody matched" by default - `TriggeredRules` simply drops to zero, and if you did not alarm on that, the failure is invisible until a customer notices missing downstream data.

**The contract practice that prevents it:**

1. **Schema registry plus generated bindings**, so a consumer's build breaks when the schema it depends on changes incompatibly.
2. **Consumer-driven contract tests in the producer's pipeline** - each consumer publishes the pattern it relies on, and the producer's CI asserts that a sample of its outgoing events still matches every registered consumer pattern. This is the concrete answer and it is the same idea as Pact in `03-microservices`.
3. **Additive-only evolution with an explicit version field**, and a new `detail-type` for a breaking change so old consumers keep working until they migrate.
4. **Alarm on `TriggeredRules` dropping to zero** per rule, and add a catch-all rule to a "unmatched events" log or queue so you can see events nobody consumed.

*Hook: a schema change that broke a consumer silently, and the contract mechanism you introduced.*

### Q109. EventBridge Pipes and Scheduler

**Pipes** replaced the "polling glue Lambda". Before Pipes, connecting a source (SQS, Kinesis, DynamoDB Streams, MSK, Kafka, Amazon MQ) to a target (any of ~15 AWS targets) with filtering, transformation and optional enrichment meant writing a Lambda that read from one, transformed, and wrote to the other. Pipes does source → **filter** → optional **enrichment** (Lambda, Step Functions, API destination) → **transform** → target, as configuration. The legitimately deleted code: DynamoDB-Streams-to-EventBridge forwarders, SQS-to-Step-Functions starters, Kinesis-to-EventBridge bridges, and the transform-and-forward functions that exist purely as plumbing.

**Scheduler** replaced both cron-in-a-container and the pattern of EventBridge scheduled *rules*. Compared with a scheduled rule it gives you: a much higher quota (millions of schedules rather than a few hundred rules per bus), **one-time schedules** (which is the big one - "do this at 14:32 next Tuesday" for a specific entity, so you no longer need a DynamoDB table of pending timers polled by a minute-cron), time zones and daylight-saving handling, flexible time windows to spread load, retry policy and a DLQ per schedule, and direct targets across the AWS API surface. The deleted code: the "pending actions" table plus its sweeper Lambda, per-tenant cron logic, and in-process schedulers (Q80, Q95).

The caution worth adding: both move logic from code you can unit-test into configuration you cannot. I use them for genuine plumbing and keep a function wherever there is business logic, error semantics or anything a test should assert. And for Pipes specifically, observability is thinner than a function's - you get metrics and a DLQ, not a stack trace.

*Hook: glue code you deleted with Pipes or Scheduler, and what you had to give up.*

### Q110. EventBridge archive and replay

**Archive** captures events matching a pattern on a bus, with a retention period, at a storage cost. **Replay** re-publishes a time range of archived events onto the bus, optionally to a *subset of rules*.

**What replay actually guarantees**: that the archived events will be delivered again to the selected rules, at a bounded rate, with **new event IDs and a `replay-name` in the event**. It does **not** guarantee ordering (there was none to begin with), does not compress or dedupe, and does not know anything about your consumers' state.

**What it breaks in a non-idempotent consumer** - and this is why the question is asked:

- **Duplicate side effects**: emails resent, payments re-attempted, inventory decremented twice, webhooks re-delivered to a customer.
- **Time-dependent logic** goes wrong: an event replayed today carries its original `time` field, but the consumer's `now()` is different, so anything computing "how long ago" or applying "current" pricing behaves differently from the original processing.
- **Out-of-order application**: if the consumer has since processed *newer* events, replaying older ones can overwrite newer state - the classic "replay reverted our data" incident. This is worse than duplication because it is silent corruption.
- **Downstream fanout amplification**: the replayed events cause the consumer to emit its own events, which are consumed by others, so a targeted replay becomes an estate-wide re-run.

**Practices**: replay to a **specific rule** rather than the whole bus; point the rule at a **dedicated replay target** where possible so you control blast radius; require consumers to be idempotent by version or by event ID (Q126) *before* you rely on replay as a recovery mechanism; use the `replay-name` field so consumers can distinguish and, where appropriate, refuse; and rehearse a replay in a non-production environment so the runbook is real. A replay is a production write operation and should be treated like one - announced, bounded and observed.

*Hook: a replay you performed or refused, and how you bounded the blast radius.*

### Q111. Sizing a Kinesis stream

**Mechanics.** A stream is divided into **shards**; each shard supports **1 MB/s or 1000 records/s ingress** and **2 MB/s egress shared across all standard consumers** (or 2 MB/s *per consumer* with **enhanced fan-out**, which uses a push model over HTTP/2 and gives each consumer its own throughput plus lower latency). The **partition key** is hashed to select a shard, so it determines distribution and defines the ordering domain. **`IteratorAge`** (`GetRecords.IteratorAgeMilliseconds`) is the lag between now and the timestamp of the last record processed - the single most important health metric.

**Sizing method:**

1. Compute required ingress in both dimensions: `peak MB/s` and `peak records/s`. Divide each by the per-shard limit and take the **larger** result. Small records make you record-rate-bound; large records make you bandwidth-bound.
2. Compute egress: number of consumers x their read throughput. With N standard consumers sharing 2 MB/s per shard, you may need more shards for reads than for writes - or enhanced fan-out, which is usually cheaper than over-sharding for more than two or three consumers.
3. Add headroom: 30-50 percent above peak, because a hot key (Q112) means one shard runs hotter than average and because resharding is not instant.
4. Choose the **capacity mode**: **provisioned** (you manage shard count) or **on-demand** (scales automatically up to a limit, roughly doubling capacity as demand grows, at a higher per-GB price). On-demand is the right default for unpredictable traffic and the wrong one for steady high volume, where provisioned plus a resharding runbook is materially cheaper.
5. Choose **retention** deliberately (24 hours default, up to 365 days) - retention is your replay window and your buffer for a broken consumer, and it is billed.

Then verify with the consumer side: `IteratorAge` near zero at peak, `WriteProvisionedThroughputExceeded` and `ReadProvisionedThroughputExceeded` at zero, and no single shard carrying disproportionate traffic.

*Hook: a stream you sized or resharded, and which of the two limits bound you.*

### Q112. Rising iterator age on one shard only `[T]`

One shard behind while the others are healthy means the problem is **specific to that shard's data or its consumer instance**, not to the stream's capacity. The candidates:

1. **A hot partition key.** The key distribution is skewed - one tenant, one device, one `null`/default value - so that shard receives far more records than the others. It is throughput-bound while the rest are idle. Check the per-shard `IncomingRecords`/`IncomingBytes` metrics; if one is much larger, this is it. Fix: change the partition key to something higher-cardinality, or add a salt/suffix for the hot key and reassemble downstream if ordering permits.
2. **A poison record stalling the shard.** Kinesis delivers in order and does not advance past a failing batch, so one record that always throws blocks the shard indefinitely (Q121). The tell is that `IncomingRecords` for the shard is normal but the consumer logs repeated identical errors. Fix: `BisectBatchOnFunctionError`, `MaximumRetryAttempts`, `MaximumRecordAgeInSeconds` and an `OnFailure` destination.
3. **A slow record class.** Not an error - some records take much longer to process (a large payload, a record that triggers an expensive downstream call, a retry loop with backoff inside the handler). The shard's throughput drops below its arrival rate and the lag grows monotonically. Fix: move the slow work out of the stream handler (enqueue it), or bound it with a timeout.
4. **Consumer-side capacity for that shard**: with the Kinesis Client Library, one worker leases the shard - if that worker's host is unhealthy, throttled or GC-thrashing, only its shards lag. With Lambda, one concurrent execution per shard (times `ParallelizationFactor`) means a single slow invocation path affects only that shard, and a Lambda throttle attributable to reserved concurrency shows exactly this shape.
5. **A recent resharding**: after a split or merge, parent shards must be drained before children are read, so lag on a specific shard during that window is expected.

Diagnostic order: per-shard incoming metrics (distinguishes 1 from the rest), then consumer error logs for that shard (distinguishes 2), then per-invocation duration distribution (distinguishes 3), then the consumer host/lease state (4).

*Hook: an iterator-age incident, which of these it was, and how you found it.*

### Q113. Kinesis versus MSK versus SQS at 200,000 events/second

**On operational cost, which is what the question asks:**

- **SQS** has essentially zero operational cost - no shards, no partitions, no brokers, no scaling decisions, unlimited throughput on standard queues. But at 200k events/second the question is whether SQS's *semantics* fit: no ordering, no replay, one logical consumer group per queue (so N consumers means N queues fed by SNS/EventBridge fanout, multiplying request charges). If the workload is "distribute work to consumers", SQS is the cheapest answer operationally and often the right one - and the request charges at 200k/s are the thing to price carefully, because per-request billing at that volume is substantial.
- **Kinesis** has moderate operational cost: you own shard count (or pay the on-demand premium), you watch `IteratorAge` and hot keys, you occasionally reshard, and you design partition keys. At 200k records/second and, say, 1 KB records, that is 200 MB/s - **200 shards** provisioned. That is a real but manageable operational surface, and everything else (durability, replication, patching, scaling of the service itself) is AWS's problem. Multiple consumers are native; replay is native.
- **MSK** has the highest operational cost even in managed form: broker sizing and count, partition count and rebalancing, topic configuration, retention and disk sizing, consumer-group lag monitoring, Kafka version upgrades, and ZooKeeper/KRaft considerations. MSK Serverless removes some of it at a price premium and with limits. You need at least one person who genuinely understands Kafka. In exchange you get Kafka's semantics, its ecosystem (Connect, Streams, ksqlDB, Debezium), compacted topics, and portability.

**My argument**: at 200k/s, the choice should be **Kinesis unless there is a Kafka-specific requirement**. The operational surface is a fraction of MSK's for a very similar capability, and the AWS-native integrations (Firehose to S3, Lambda event source mappings, Data Analytics/Flink) remove a lot of code. I would choose **MSK** if the organization already runs Kafka, needs Connect's connector ecosystem, needs log compaction or exactly-once transactional semantics, or has a portability requirement. I would choose **SQS** if the workload is genuinely task distribution with no ordering or replay need - and I would say that this is more often the case than teams assume, because "we need a stream" is frequently "we need a queue with a fanout".

*Hook: a high-throughput pipeline you chose a transport for, and the operational cost you underestimated.*

### Q114. Ordering across a distributed system

**What per-partition ordering gives the consumer**: within a partition (Kinesis shard, SQS FIFO message group, DynamoDB Streams per item, Kafka partition), records are delivered in the order they were accepted. Across partitions there is **no relationship at all**. So the guarantee is only useful if your partition key aligns with the entity whose ordering matters - and if it does, the guarantee is strong and sufficient: all changes to order 123 arrive in order, which is usually the whole requirement.

What it does *not* give you: global ordering, cross-entity causality (order-created before payment-received for a different key), or protection against reprocessing an older record after a newer one during a retry or replay.

**How to handle out-of-order arrival** - and the point is that you should design for it even when you have ordering, because retries, replays and multi-region (Q225) break it:

1. **Version or sequence numbers on the event**, with a conditional write: apply only if `event.version > stored.version`. DynamoDB's condition expressions do this atomically in one call, so it costs nothing extra (Q156). This is the primary technique.
2. **Idempotency by event ID** so a duplicate is a no-op (Q126).
3. **Last-writer-wins with a reliable timestamp**, only where the field is genuinely independent and loss is acceptable - and be aware that clock skew makes producer timestamps untrustworthy across hosts.
4. **Convergent (CRDT-style) state**: counters as increments rather than absolute values, sets as add/remove operations, so order does not matter. Very effective where it applies.
5. **Buffer and reorder** with a small window, keyed by sequence number, holding a record until its predecessor arrives - the "resequencer" pattern. Correct but stateful and latency-adding; use it only when the consumer genuinely cannot be made order-independent.
6. **Reject and re-drive**: if a prerequisite has not arrived, fail the record so it is retried after a delay. Simple, works, and needs care to avoid infinite loops (bound with `MaximumRecordAge`/`maxReceiveCount`).

The sentence I would end on: **prefer making the consumer order-independent over making the transport ordered** - it is cheaper, it scales, and it survives replay.

*Hook: an out-of-order bug you fixed, and whether you fixed the transport or the consumer.*

### Q115. The event backbone for order processing `[A]`

**Clarify first**: peak orders per second and the spike ratio; is payment authorization synchronous to the customer; what is the SLA between order placed and shipment created; what are the compensation rules (can we cancel a shipment, can we refund automatically); and who consumes these events besides fulfilment - analytics, customer notifications, partner integrations?

**Services, per link:**

| Link | Choice | Reasoning |
| --- | --- | --- |
| Order intake (API) | API Gateway → **direct SQS integration** (or Lambda) with the order written to DynamoDB, then an event emitted via **DynamoDB Streams → Pipes → EventBridge** | Accept-and-persist first; never lose an order because a downstream is unavailable. The stream-to-bus path gives the transactional-outbox guarantee without a two-phase write (Q128) |
| Domain events (`OrderPlaced`, `PaymentAuthorized`, `InventoryReserved`, `ShipmentCreated`) | **EventBridge** `orders-bus`, one rule per consumer, each targeting the consumer's own SQS queue | Producers do not know consumers; archive/replay available; adding the analytics or partner consumer later requires no producer change (Q107) |
| The business process itself | **Step Functions Standard**, one execution per order, orchestrating payment → inventory → shipment with compensation | This process has a lifecycle, a timeout, a manual-review branch and compensation - which is exactly what a state machine is for, and it makes "where is order 123" answerable (Q140) |
| Payment call | Step Functions task → Lambda → provider, with **idempotency key = order ID**, retries with backoff and jitter | The external call is the least reliable hop and the most dangerous to duplicate (Q141) |
| Inventory reservation | Step Functions task → Lambda → **DynamoDB conditional write** | Conditional write is the atomic reservation; no distributed lock needed (Q156) |
| High-volume side effects (analytics, search index, recommendations) | **Kinesis** via an EventBridge rule, or Firehose to S3 | Ordered, replayable, cheap at volume, and lets analytics reprocess history without touching the transactional path |
| Customer notifications | SNS (email/SMS/push) subscribed from an EventBridge rule | Fanout to channel endpoints is SNS's job |

**Contracts**: every event carries `eventId` (for idempotency), `eventVersion`, `occurredAt`, the aggregate ID, and only the data a consumer needs - not the whole entity. Schemas in the registry, additive-only evolution, consumer-driven contract tests in the producer's pipeline (Q108).

**Where duplicates are tolerated, stated explicitly** - this is the part interviewers are looking for:

- **Tolerated and handled by idempotency**: order intake (dedupe on client-supplied request ID), inventory reservation (conditional write on order ID), search-index and analytics updates (idempotent upserts), notifications (accepting that a rare duplicate email is better than a missing one).
- **Not tolerated - must be exactly-once in effect**: the **payment capture**. Protected by an idempotency key passed to the provider, an idempotency table with a conditional put before the call, and a state machine that never retries a call whose outcome is unknown without first *querying* the provider (Q131, Q141).
- **Tolerated but must not reorder**: shipment status updates, guarded by a version check (Q114).

**What I would name as the hard parts**: the unknown-outcome payment call; the compensation path when inventory is reserved and payment later fails (release the reservation, and what if the release fails); and the fact that `OrderPlaced` will be consumed by teams you have not met yet, so the event schema is a public API from day one.

*Hook: an order or transaction pipeline you built, where you allowed duplicates, and the one place you did not.*

---

## 8. Event source mappings, retries and idempotency

### Q116. What an event source mapping is

An **event source mapping** is a Lambda-service-managed resource that **polls** a source (SQS, Kinesis, DynamoDB Streams, MSK, self-managed Kafka, Amazon MQ, DocumentDB) and invokes your function with batches of records. An **invocation** is a single call to your function; the mapping is the machinery that decides when and with what to invoke.

**Who does the polling: the Lambda service, not your function.** This is the key mechanism and it has several consequences worth stating:

- **You are not billed for the polling** - no invocations for empty polls, no cost for the pollers themselves (with the exception of provisioned pollers where offered). Contrast with a container-based consumer, where you pay for the process whether messages exist or not.
- **The permissions live in your execution role**, not in a resource policy, because it is the Lambda service using your role to read the source (Q19).
- **Scaling is the mapping's decision**, driven by backlog and by the source's shape (Q117), not by your code and not by an HPA.
- **Failure semantics are the mapping's**, which is why the whole of this category exists: whether a failed record is retried, how often, what blocks behind it, and where it eventually goes are all *mapping configuration*, not application code.
- **The mapping is a separate resource with its own state**: it can be disabled, its `LastProcessingResult` is a diagnostic, and its configuration changes take effect without redeploying the function.

For **push** sources (API Gateway, S3, SNS, EventBridge) there is no mapping - the source invokes Lambda directly, and the retry semantics belong to the *source* (Q122).

*Hook: a time when disabling or reconfiguring an event source mapping was the right operational lever during an incident.*

### Q117. The SQS-to-Lambda mapping: batching and scaling

**Batching**: the poller collects up to `BatchSize` messages (up to 10,000 for standard queues, though the payload limit of 6 MB per invocation usually binds first) and waits up to `MaximumBatchingWindowInSeconds` (0-300) to fill the batch. Setting a batching window trades latency for fewer invocations - which is a direct cost lever (Q94) and worth doing for high-volume, latency-tolerant queues.

**Scaling**: the mapping starts with a small number of concurrent pollers (five long-poll pollers initially) and, while messages remain, **increases concurrency by up to 60 invocations per minute** for standard queues (300 per minute for FIFO, per message group constraint), up to the function's available concurrency or the mapping's `MaximumConcurrency` if set. It scales *down* when the queue drains, based on the ratio of successful empty receives.

Two things this implies that people get wrong:

1. **The ramp is not instantaneous.** A sudden backlog of a million messages does not immediately consume all your concurrency; it climbs at 60/minute. For a burst you must either pre-warm the expectation (accept the drain time) or shorten per-message duration. Conversely, this ramp is a *feature*: it protects downstreams from a thundering herd.
2. **The mapping will happily consume all available account concurrency** unless bounded, which is why `MaximumConcurrency` on the mapping (Q129) exists and is the correct control - rather than reserved concurrency, which throttles instead of slowing the poller.

Monitoring: `ApproximateNumberOfMessagesVisible` (backlog), `ApproximateAgeOfOldestMessage` (**the real SLO metric** - it captures "are we falling behind" in a way depth does not), plus the function's `Throttles` and the mapping's own concurrency.

*Hook: a queue whose batching window or maximum concurrency you tuned, and the effect on cost or on the downstream.*

### Q118. One failure in a batch of ten `[T]`

**By default, the entire batch fails.** Lambda reports the invocation as failed, so the mapping does not delete *any* of the ten messages. All ten become visible again after the visibility timeout, and all ten are redelivered - so **the nine successful messages are processed a second time**, and their `ApproximateReceiveCount` increments. Repeat until the poison message exhausts `maxReceiveCount` and goes to the DLQ, by which point the nine (and their side effects) have been repeated several times each.

Consequences worth naming:

- **Duplicate side effects at scale** - this is one of the most common causes of "we processed it twice" (Q101), and it is entirely a configuration issue.
- **Throughput loss**: with a batch size of 10 and a 10 percent poison rate, a large fraction of your work is redundant reprocessing.
- **The nine good messages may reach the DLQ too**, if the retry cycle exhausts `maxReceiveCount` for them as well - so you end up with valid messages in the DLQ, which is confusing during triage.

**The fixes, in order:**

1. **Enable `ReportBatchItemFailures`** on the mapping and return the failed message IDs (Q119). Then only the failures are retried.
2. **Make the handler idempotent** (Q126), because redelivery is always possible.
3. **Consider `BatchSize: 1`** for low-volume, high-value work where the simplicity is worth the extra invocations - a legitimate choice, not a cop-out.
4. **Catch and route unrecoverable errors inside the handler** - if a message is malformed and will never succeed, sending it to a DLQ yourself and returning success is often better than letting it churn.

*Hook: a batch-failure configuration you changed, and the reduction in duplicate processing.*

### Q119. Implementing `ReportBatchItemFailures` correctly

**Enable** `FunctionResponseTypes: [ReportBatchItemFailures]` on the event source mapping, then have the handler return:

```json
{ "batchItemFailures": [ { "itemIdentifier": "message-id-1" }, { "itemIdentifier": "message-id-7" } ] }
```

The mapping deletes the messages you did **not** list and makes the listed ones visible again. Return an empty `batchItemFailures` array for full success.

Implementation rules:

- **Catch per message**, not per batch. Loop, try/catch each record, collect the failed `messageId`s, and return them. A single try/catch around the loop defeats the mechanism.
- **Use the SQS `messageId`**, not your own business key.
- For **Kinesis and DynamoDB Streams**, the semantics differ: you return the **sequence number of the first failed record**, and the mapping retries **from that point onward** (because order matters), so everything after it is reprocessed regardless.

**The trap when the response is malformed** - and this is the substance of the question. If the returned object is not what the mapping expects, **the mapping treats the whole batch as a failure**. Specifically:

- Returning an unexpected shape, a misspelled key (`batchItemFailure`, `itemIdentifiers`), or a non-empty list containing a `null` or empty `itemIdentifier` → the entire batch is retried, silently, exactly as if the feature were off.
- Returning message IDs that were **not in the batch** → the whole batch is retried.
- Returning `null` or throwing after partially collecting failures → whole batch.

So you can enable the feature, believe it is working, and still be reprocessing everything - with no error anywhere. The defences: a **unit test asserting the exact response shape**, using the AWS-provided response types (`SQSBatchResponse` in the Java events library) rather than hand-built maps, and an operational check that `ApproximateReceiveCount` distributions look sane. Also remember to **enable it on the mapping** - implementing it in code without the `FunctionResponseTypes` setting does nothing at all, which is the other half of the same trap.

*Hook: a partial-batch implementation you debugged, and how you verified it was actually working.*

### Q120. Kinesis and DynamoDB Streams error handling settings

Because these sources are **ordered and non-advancing**, a failure blocks the shard. Four settings bound that:

| Setting | What it does | What it prevents |
| --- | --- | --- |
| **`BisectBatchOnFunctionError`** | On failure, splits the batch in two and retries each half, recursively | A single bad record failing a large batch. Isolates the poison record down to a batch of one, so the good records around it succeed |
| **`MaximumRetryAttempts`** | Caps retries of a failing batch (0 to 10,000; -1 = infinite, the default) | **Infinite blocking of the shard** by a permanently failing record |
| **`MaximumRecordAgeInSeconds`** | Discards records older than this (60 s to 7 days) | A backlog of stale records being processed long after they are useful, and a shard that can never catch up |
| **`DestinationConfig` / `OnFailure`** | Sends metadata about the discarded batch (shard, sequence-number range, cause) to an SQS queue or SNS topic | **Silent data loss** when a batch is finally discarded. Note it sends the *pointer*, not the records - you re-read the stream by sequence number |

Two more that belong in the same conversation: **`ParallelizationFactor`** (up to 10 concurrent invocations per shard, ordered *within* each partition key, which raises throughput without resharding) and **`TumblingWindowInSeconds`** for stateful aggregation across batches.

The configuration I would set as a default: `BisectBatchOnFunctionError: true`, `MaximumRetryAttempts` at a small number (3-5), `MaximumRecordAgeInSeconds` set from the business tolerance, and an `OnFailure` destination with an alarm on it. Without all four, "one bad record" is an outage (Q121).

*Hook: a stream consumer whose error configuration you hardened, and the incident that prompted it.*

### Q121. One bad record stalls a shard for six hours `[T]`

**Mechanism.** Kinesis (and DynamoDB Streams) guarantee ordered delivery per shard, so the Lambda poller will not advance the iterator past a batch that failed. With the default `MaximumRetryAttempts: -1` (infinite), the poller retries the same batch forever, with backoff. Every record behind the poison record - possibly millions - waits. `IteratorAge` climbs linearly (Q112), every downstream consumer of that shard's data is stale, and because the *other* shards are fine, aggregate dashboards look mostly healthy. Six hours is simply how long it took someone to notice.

Worse variants: if the failure is a **timeout** rather than an exception, each retry costs the full function duration, so you are also paying for it; and if the batch is large, the retry cost is multiplied by the batch's processing time.

**The three settings that would have bounded it** (Q120):

1. **`MaximumRetryAttempts`** - after N attempts, discard the batch and move on. This alone converts an outage into a data-loss event you can then repair.
2. **`MaximumRecordAgeInSeconds`** - independently caps how old a record can be, so the shard cannot be blocked beyond that horizon even if the failure mode is unusual.
3. **`BisectBatchOnFunctionError`** - narrows the damage to the single bad record instead of discarding a whole batch of good ones alongside it.

Plus the fourth thing that is not a setting: **`DestinationConfig` with an alarm**, so the discard is visible and repairable, and **an alarm on `IteratorAge`** so you find out in minutes rather than hours. `IteratorAge` is the single most important alarm on any stream consumer, and I would say so.

**And the application-side fix**: the handler should distinguish *retryable* from *unrecoverable* errors. A malformed record, a schema violation or a business-rule rejection should be routed to a DLQ by the handler and reported as success - never retried. Only transient failures (a throttled downstream, a timeout) should be allowed to fail the batch. Getting that classification right in code is what stops poison records from existing at all.

*Hook: an iterator-age incident, how long it took to detect, and the alarm you added.*

### Q122. Asynchronous invocation retry behaviour

For **asynchronous** invocations (`InvocationType: Event`, S3 events, SNS, EventBridge, CloudWatch Events), Lambda places the event in an **internal queue** and returns 202 to the caller immediately. Then:

- **On function error**: Lambda retries **twice** by default (configurable 0-2 via `MaximumRetryAttempts` on the event invoke config), with delays - roughly one minute before the first retry and two minutes before the second.
- **On throttle or service error**: Lambda retries for up to **six hours** with exponential backoff, independent of the function-error retry count.
- **Event age**: `MaximumEventAgeInSeconds` (60 s to 6 hours, default 6 hours) discards events older than the limit.
- **After exhaustion**: the event goes to the **`OnFailure` destination** (SQS, SNS, EventBridge, or another Lambda) or to the legacy **DLQ** if configured. **If neither is configured, the event is discarded silently** - no error, no log, nothing. This is the most important sentence in the answer.

Two subtleties worth adding: retries may be delivered to a **different execution environment**, so anything you cached in-process from the first attempt is gone; and Lambda may occasionally deliver an asynchronous event **more than once** even on success, so async invocation is at-least-once and the handler must be idempotent (Q126).

Note also that the source's own retry policy stacks on top for some sources - EventBridge retries for up to 24 hours with its own DLQ, and SNS has its own delivery retry policy - so an event can be retried by *two* independent layers, which is a retry-amplification consideration (Q200).

*Hook: an async invocation path where events were being lost, and how you discovered the missing destination.*

### Q123. Lambda destinations versus a DLQ

The **DLQ** (`DeadLetterConfig`) is the older mechanism: on exhaustion of retries for an *asynchronous* invocation, the **event payload** is sent to an SQS queue or SNS topic. That is all it does.

**Destinations** (`EventInvokeConfig` with `OnFailure` and `OnSuccess`) give you more:

1. **Success as well as failure.** `OnSuccess` lets you chain: process, then publish the result to EventBridge or a queue, with no code in the function to do it. That is a capability the DLQ has no equivalent for.
2. **Richer targets**: SQS, SNS, EventBridge and Lambda, rather than SQS/SNS only.
3. **Much richer payload**: the destination record includes the **original event, the response or error payload, the request ID, the invocation timestamp, and the number of retries** - so you can triage without correlating against logs. The DLQ gives you only the input event, which means "why did this fail" requires a log search by request ID that you may not have.
4. **It works for stream sources too** (via `DestinationConfig` on the mapping), where the DLQ concept does not apply.

So destinations supersede the DLQ for asynchronous invocations and I would use them by default. The remaining reasons to see a DLQ in the wild are age and the fact that some teams want the raw event only. What I would say in an interview: **use `OnFailure` destinations, keep the DLQ pattern for the *queue* (SQS's own `RedrivePolicy`), and never leave both unset** (Q122).

*Hook: a failure-triage improvement you got from destinations' extra metadata.*

### Q124. A dead letter strategy for a serverless application

**Where DLQs live** - one per failure domain, not one shared:

- **Per SQS queue**: a `RedrivePolicy` with `maxReceiveCount` (3-5 is typical) pointing at a dedicated DLQ. Retention on the DLQ set to the maximum (14 days) so you have time to triage.
- **Per Lambda asynchronous function**: an `OnFailure` destination (Q123).
- **Per event source mapping** on a stream: a `DestinationConfig` for discarded batches (Q120).
- **Per EventBridge rule target**: a target DLQ, because a target failure is otherwise invisible.
- **Per Step Functions**: a `Catch` to a failure-handling state, plus a DLQ on the state machine's triggering mechanism.

The principle: **every asynchronous boundary needs a place for the un-processable to land**, and a shared "everything" DLQ makes triage and redrive dangerous because you cannot redrive selectively.

**What alarms**, and this is where most teams fall short:

- `ApproximateNumberOfMessagesVisible > 0` on **every** DLQ, with a low threshold (1) and a real notification. A DLQ with one message and no alarm is silent data loss.
- `ApproximateAgeOfOldestMessage` on the DLQ, so a slow trickle is caught.
- The **rate** of arrivals, so a mass failure is distinguishable from a single poison message - these need different responses.

**How a replay works safely:**

1. **Triage before redriving.** Sample messages, classify: transient (downstream was down), poison (malformed, will never succeed), or systemic (a bug that is now fixed). Only the first and third are candidates for redrive.
2. **Fix the cause first.** Redriving into a still-broken consumer just re-fills the DLQ and generates load.
3. **Verify idempotency** for the messages in question, because redrive is by definition reprocessing (Q126).
4. **Use SQS's built-in DLQ redrive** (`StartMessageMoveTask`) with a **rate limit**, or drain in controlled batches. Never move a million messages back at full speed - that is Q125.
5. **Redrive to a separate "replay" queue** for the systemic case, so you can process with a modified consumer (extra logging, relaxed validation, a lower concurrency) without touching the live path.
6. **Track completion**: record how many were redriven, how many succeeded, and what remains - and delete or archive the genuinely unprocessable with a decision recorded, rather than leaving them forever.

*Hook: a DLQ triage you ran, what the split between transient and poison turned out to be, and how you redrove.*

### Q125. A DLQ replay causes a second outage `[T]`

Three mechanisms:

1. **Thundering herd on the downstream.** A DLQ accumulated over hours is a compressed backlog. Redriving it at full speed presents the consumer with, say, 200,000 messages at once; the event source mapping scales up, concurrency climbs, and the database or third-party API behind it - which was probably the original cause of the failures - is hit far harder than it was during normal traffic. You have replayed the outage.
2. **Duplicate side effects at scale.** The messages in the DLQ may have *partially* succeeded on their original attempts - the payment went through but the confirmation write failed, so the message was retried and eventually dead-lettered. Redriving without idempotency reissues those partial effects thousands of times: duplicate emails, duplicate charges, double-decremented inventory (Q101, Q126).
3. **Stale data applied over newer state.** Hours-old messages are replayed after newer messages for the same entities have already been processed, so the old state overwrites the new - the same corruption mode as an EventBridge replay (Q110). The tell is that this outage is *silent*: nothing errors, the data is just wrong.

Two more worth naming: **concurrency starvation** - the redrive consumes the account's Lambda concurrency and throttles unrelated functions (Q68); and **re-dead-lettering into a loop** if the redrive fails again and someone has wired the DLQ's DLQ back to the source.

**How to redrive safely**: fix the cause first; rate-limit the redrive (SQS's move task supports a velocity setting; otherwise drain in batches with a low `MaximumConcurrency`); assert idempotency and version guards; redrive to a separate queue with its own consumer configuration; do it during low traffic; and watch the downstream's saturation metrics, not just the queue depth, with a plan to stop. And say out loud that **a redrive is a production change** deserving the same care as a deploy.

*Hook: a redrive that went badly, or one you deliberately throttled, and what you monitored during it.*

### Q126. Implementing idempotency on AWS

**The design:**

```
Table: idempotency
  PK: idempotency_key      (S)  e.g. "orders#place#<client-request-id>"
  status                   (S)  IN_PROGRESS | COMPLETED
  expiry                   (N)  epoch seconds, TTL attribute
  response                 (S)  the serialized result, for replaying the answer
  lock_expiry              (N)  when an IN_PROGRESS record may be reclaimed
```

**The key** must come from the *client's* intent, not from the transport: a client-supplied request ID, or a deterministic hash of the meaningful business fields. Using the SQS `messageId` is wrong for producer-side duplicates (two different messages carrying the same order), and using a hash of the whole payload is fragile if the payload carries timestamps. State this explicitly - key choice is where most idempotency implementations fail.

**The TTL** is the window over which you promise deduplication. Set it from the business requirement and the maximum retry horizon of every layer that can retry: Lambda async is 6 hours, EventBridge is 24, an SQS message can live 14 days, and a human redrive can be later still. A 24-hour TTL is a common default; a payment might want 7 days. Under-setting the TTL is a silent correctness hole.

**The concurrent-request race**, which is the crux:

1. **Conditional put** with `attribute_not_exists(idempotency_key) OR expiry < :now`, writing `status = IN_PROGRESS` and a `lock_expiry`. This is atomic, so exactly one concurrent caller wins.
2. If the condition fails, read the record: if `COMPLETED`, **return the stored response** (do not re-execute, and do not error - returning the original answer is what makes retries transparent). If `IN_PROGRESS` and `lock_expiry` is in the future, return a 409 or let the caller retry; if `lock_expiry` has passed, the previous holder died, so attempt to reclaim it with another conditional write.
3. Do the work.
4. **Update to `COMPLETED`** with the response and the final TTL.

**The residual risk to name honestly**: the work and the state update are not in one transaction, so a crash between step 3 and step 4 leaves `IN_PROGRESS` with the side effect done. The mitigations are (a) make the side effect itself idempotent where possible - a conditional write on the *business* item, or a provider-side idempotency key - which is strictly better than any table; (b) use `TransactWriteItems` to write the business item and the idempotency record atomically when both are in DynamoDB (Q155); and (c) keep the lock window short enough to bound the ambiguity.

*Hook: an idempotency implementation you built, the key you chose, and the race you had to close.*

### Q127. Powertools idempotency utility

**What it does**: wraps a handler (or any function) with `@Idempotent`, computing a hash of a configurable subset of the event (`EventKeyJMESPath`, so you can key on `body.requestId` and ignore timestamps) and persisting it to a **DynamoDB persistence store**. It implements exactly the protocol of Q126: a conditional put for `INPROGRESS`, `COMPLETED` records that **return the saved response** on a repeat, a configurable expiry, an in-progress lock with expiry to handle crashed executions, optional payload validation (to detect the same key with a *different* payload, which is a bug worth surfacing), and a **local in-memory cache** to short-circuit repeats within a warm environment.

It also handles the operational details well: `raiseOnNoIdempotencyKey`, so a missing key is a loud failure rather than a silent bypass; and it works for any function, not only the handler, so you can scope idempotency to the operation that actually needs it.

**Where it still lets a duplicate through:**

- **Between the side effect and the `COMPLETED` write.** Same fundamental gap as Q126: if the function crashes after the external call and before the store is updated, the retry sees `INPROGRESS` (or a reclaimable lock) and may execute again. Powertools narrows the window; it cannot close it, because it cannot make a third-party call transactional.
- **After the expiry window.** A retry or redrive later than the configured expiry is a fresh key. A 14-day-old SQS message redriven against a 1-hour expiry will be reprocessed.
- **If the key is wrong.** Keying on the whole payload when the payload contains a timestamp, or on the message ID when the duplicate came from the producer, defeats it entirely - and it will look like it is working.
- **Partial batch processing** without `ReportBatchItemFailures`: the batch is retried, keys already `COMPLETED` are short-circuited (good), but combining batch semantics and idempotency needs care about which unit the key represents.
- **It does not make your side effects idempotent** - only the *invocation*. If the handler writes to three systems and fails on the third, the utility replays nothing; you still need compensation or a saga (Q140).

So: use it, because it is a correct and well-tested implementation of a protocol people get wrong. But describe it as **narrowing the window, not eliminating duplicates**, and pair it with an idempotency key passed to the external provider wherever one exists.

*Hook: where you used the utility, and a case where you needed provider-side idempotency in addition.*

### Q128. The transactional outbox on AWS

The problem: you must update your database **and** publish an event, atomically. A two-phase write (write the row, then publish) fails in the gap - the row exists and no event was sent, or the event was sent and the transaction rolled back.

**Option A - DynamoDB Streams as the outbox.** Write only to DynamoDB; the stream is the change log. An EventBridge Pipe (or a Lambda mapping) reads the stream and publishes the domain event. Because the stream is a *property* of the committed write, there is no gap: if the write committed, the event will be published; if it did not, nothing is published.

**Option B - a relational outbox table plus CDC.** Insert the event row in the *same transaction* as the business change, then have DMS or Debezium (on MSK Connect) tail the transaction log and publish. Same guarantee, more moving parts.

**Option C - a two-phase write.** No guarantee. Occasionally acceptable with compensation and reconciliation, never the design I would recommend.

**My recommendation: Option A when the data lives in DynamoDB, Option B when it lives in a relational database, and never Option C.** The reasoning to give: A is the least machinery for the strongest guarantee, and it also gives you ordering per item and a 24-hour replay window for free. The trade-offs to state honestly:

- The stream record is the *item's* change, not a domain event, so the Pipe/Lambda must **translate** - and that translation is where the schema contract lives (Q107). Some teams write an explicit `outbox` item into the same table via `TransactWriteItems` precisely so the stream carries a proper event rather than a diff.
- **At-least-once**, so consumers must be idempotent (Q126) - the outbox solves *loss*, not duplication.
- **24-hour stream retention** bounds your recovery window; Kinesis Data Streams for DynamoDB extends it (Q157) at a cost.
- Ordering is per item, so cross-aggregate ordering does not exist (Q114).

*Hook: an outbox you implemented, which variant, and the failure it prevented.*

### Q129. Mapping `maximumConcurrency` versus reserved concurrency

Both bound how many concurrent executions a queue's messages can consume, but they do it at different layers and with opposite failure behaviour.

- **Reserved concurrency** is a **function-level ceiling**. When it is reached, further invocations are **throttled** - the mapping's invocation attempt fails, so the messages return to the queue and their `ApproximateReceiveCount` increments. Enough sustained throttling drives them to the DLQ (Q130).
- **`MaximumConcurrency` on the event source mapping** tells the **poller** not to scale beyond N concurrent invocations. The poller simply reads more slowly; messages stay in the queue, receive counts do not increment, nothing is throttled and nothing is dead-lettered.

**To protect a downstream, set `MaximumConcurrency` on the mapping.** It is backpressure rather than rejection: the queue absorbs the backlog, the drain rate is bounded to what the database can take, and message age (not error count) tells you you are behind. That is the correct shape for a protective limit.

Reserved concurrency remains useful for a different job: **partitioning the account limit** so this function cannot starve others, and guaranteeing it a floor (Q69). I set it as a blast-radius ceiling well above the mapping's `MaximumConcurrency`, not as the flow-control mechanism.

The clean framing: **`MaximumConcurrency` shapes the flow; reserved concurrency caps the blast radius.** Use both, for their own purposes, and alarm on `Throttles` so that if reserved concurrency ever engages you know something is wrong.

*Hook: a downstream you protected, which control you used, and how you sized it.*

### Q130. `maximumConcurrency: 5` causing DLQ arrivals `[T]`

This looks like a contradiction of Q129, and the resolution is the interaction between the poller's rate and the **message's own lifecycle timers**.

With `MaximumConcurrency: 5`, the poller drains slowly. If the arrival rate exceeds `5 / average_duration` messages per second, the backlog grows without bound. Then two things kill messages independently of any throttling:

1. **`maxReceiveCount` combined with visibility-timeout expiry.** Messages that *are* picked up but whose processing outlives the visibility timeout (more likely under load, and Q100) get redelivered, incrementing the receive count each time. With a low `maxReceiveCount` (say 3) and a slow, contended consumer, messages can exhaust their receives without ever having failed for a business reason - and land in the DLQ.
2. **Message retention expiry.** If the backlog takes longer to drain than `MessageRetentionPeriod` (default 4 days), messages are **deleted by SQS**, not dead-lettered - which is worse, because they vanish.

There is also a genuine edge: `MaximumConcurrency` has a minimum of 2, and if it is set very low relative to the batch size and duration, the poller's own behaviour under a large backlog can produce receives without successful processing, again incrementing counts.

**Diagnosis**: look at `ApproximateReceiveCount` on the DLQ messages. If they are all exactly at `maxReceiveCount` but the payloads are valid and the consumer logs no errors for them, this is a throughput/lifecycle problem, not a poison-message problem. Compare `ApproximateAgeOfOldestMessage` against the retention period.

**Fixes**: size `MaximumConcurrency` to the *sustained arrival rate*, not to an arbitrary safety number - the limit must be above `arrival_rate x duration` or the queue is a leak; raise the visibility timeout to at least 6x the function timeout; raise `maxReceiveCount` so genuine transient contention does not dead-letter; extend retention; and alarm on **message age** rather than depth, because age is what tells you the drain rate is insufficient. And if the downstream genuinely cannot go faster, then the honest conclusion is that you must shed or defer load deliberately rather than let SQS decide which messages die.

*Hook: a protective concurrency limit that caused message loss, and how you resized it.*

### Q131. End-to-end guarantees for a payment event `[A]`

**Clarify first**: is the payment authorization synchronous to the user? Does the provider support idempotency keys, and does it offer a query-by-idempotency-key API? What is the acceptable time to settlement? What is the reconciliation process today, and who owns it? The answer to the third question - "can the provider tell me whether my earlier request succeeded" - changes the design fundamentally.

**The path and its controls, hop by hop:**

| Hop | Failure point | Control |
| --- | --- | --- |
| Client → API | Client retries after a timeout, unsure if the request landed | **Client-supplied idempotency key** (`Idempotency-Key` header), required and validated |
| API Gateway → Lambda | Gateway retry, or a 429 | No gateway-level retry on writes; idempotency key covers it. Throttle rather than queue at this layer so the client learns immediately |
| Lambda → durable store | Crash after accepting, before persisting | **Conditional `PutItem`** on the idempotency key *and* the payment record in one **`TransactWriteItems`**, so acceptance is atomic. Return 202 only after the commit |
| Store → event | The write committed but no event published | **DynamoDB Streams as the outbox** (Q128) - the event is a consequence of the commit, not a second write |
| Event → orchestrator | Duplicate or lost delivery | Step Functions execution **named deterministically from the payment ID**, so a duplicate start is rejected by `ExecutionAlreadyExists` - a genuinely useful exactly-once trick |
| Orchestrator → provider | **The dangerous hop**: request sent, response lost. Did the charge happen? | Pass the **provider's idempotency key**; on an unknown outcome, **never blind-retry - query the provider by that key** and branch on the answer. If the provider has no query API, move to a "pending verification" state and reconcile from their settlement file |
| Provider → our state | We charged and failed to record it | Record the attempt **before** the call (`status: SUBMITTED`, with the key), then update after. So an unknown outcome is always discoverable from our own data |
| Orchestrator → downstream (ledger, notification) | Partial completion | Compensation states for the reversible parts; for the ledger, an idempotent append keyed by payment ID |
| Everything | Permanent failure | `Catch` to a failure state that writes to a **manual-intervention queue with an alarm** - never a silent discard |

**The design principles I would state:**

1. **Never lose**: accept only after a durable, atomic commit, and emit events from the commit (outbox) rather than alongside it. Every asynchronous boundary has a DLQ with an alarm (Q124).
2. **Never apply twice**: idempotency at *three* levels - the client's key at the edge, our own idempotency table with a conditional write (Q126), and the provider's idempotency key at the external boundary. The third is the only one that protects against *our* duplicate call, so it is the non-negotiable one.
3. **Make ambiguity resolvable**: write the intent before the side effect, so "unknown" is always a state we can query our way out of. This is the single most valuable rule for payments.
4. **Reconcile independently**: a daily job comparing our ledger against the provider's settlement report, with an alarm on any discrepancy. Assume the online controls will occasionally fail, and make the offline check the backstop that finds it.
5. **Bound retries**, with backoff and jitter, and treat exhaustion as a business event requiring a human - not as a discard.

**What I would say about the residual risk**: there is no way to make a call to a third party and a write to our database atomic. The best available design converts "did it happen?" into a question we can always answer, and makes the answer eventually reconciled. Anyone claiming exactly-once across that boundary is describing idempotency plus reconciliation, and it is worth saying so plainly.

*Hook: a payment or financial flow you designed, the ambiguity case, and how reconciliation caught something the online path missed.*

---

## 9. Orchestration with Step Functions

### Q132. What Step Functions gives you that chained Lambdas do not

**Answered in terms of state: it makes the position in the process a durable, queryable, externally-managed fact rather than an implicit consequence of which messages exist.**

With chained Lambdas (or a queue between each step), the state of a business process is *distributed across the transport*: a message in flight, a partially written record, a retry counter buried in a receive count. Nobody can answer "where is order 123 and why has it not progressed" without reconstructing it from logs. With a state machine, that state is a durable execution: you can list executions, see the current state, see the input and output of every step, and see the whole history for 90 days.

That single property produces most of the other benefits:

- **Retries, backoff, jitter and error classification are declarative** and per-step, instead of being reimplemented in every function.
- **Compensation is expressible** - a `Catch` that routes to an undo path (Q140) - so sagas stop being ad-hoc.
- **Timeouts, waits and long delays are free**: `Wait` for an hour costs one state transition, whereas a Lambda waiting an hour costs an hour of GB-seconds and cannot exceed 15 minutes.
- **Human-in-the-loop and external callbacks** become a state (`waitForTaskToken`, Q138) instead of a bespoke table plus poller.
- **Steps can be non-Lambda**: a direct SDK call removes an entire function (Q136), so the orchestration also *reduces* the amount of code.
- **Observability by default** - the execution history is the audit log, which for a regulated process is a deliverable rather than a nicety.

What it costs: state-transition charges (Q143), the payload limit (Q142), ASL as a second language in the codebase, and a testing story that is weaker than plain code. I would not orchestrate a two-step process; I would orchestrate anything with compensation, waiting, branching or an SLA.

*Hook: a process you moved from chained functions to a state machine, and the operational question it finally let you answer.*

### Q133. Standard versus Express

| | Standard | Express |
| --- | --- | --- |
| Durability | **Exactly-once state transitions**, full durable history | **At-least-once** execution, no durable per-state history |
| Duration limit | 1 year | **5 minutes** |
| Pricing | Per **state transition** | Per **request plus duration and memory** (like Lambda) |
| Observability | Full execution history in the console and API, 90 days | Logs to CloudWatch Logs only, if enabled (and that logging is a real cost) |
| Throughput | Thousands of executions/second, lower per-execution rate | Very high - 100,000+ executions/second |
| Invocation | Async (`StartExecution`) or `.sync` from a parent | Async, or **`StartSyncExecution`** which returns the result inline |

**For a synchronous API-backed workflow: Express, with `StartSyncExecution`.** Reasoning: the workflow must complete inside the caller's timeout (and inside API Gateway's 29 seconds, Q57), so it is short by construction; the request-plus-duration pricing is far cheaper than per-transition pricing at API volumes; and `StartSyncExecution` returns the output directly, so API Gateway can integrate with it without a polling loop.

The trade-offs I would state as part of the same answer: Express is **at-least-once**, so every step must be idempotent - and for an API-backed flow that means the write steps need idempotency keys (Q126). And because there is no durable execution history, debugging depends entirely on having enabled CloudWatch logging at an appropriate level, which is a cost you should model (Q188) rather than discover.

I would use **Standard** for anything with a human step, a long wait, compensation semantics that must be auditable, or a regulatory requirement to show what happened.

*Hook: a workflow where you chose Express, and how you handled its at-least-once semantics.*

### Q134. Express for a 20-minute batch job `[T]`

**What happens**: the execution is terminated at the 5-minute limit with `States.Timeout`. Since Express does not keep a durable history, the failure detail is only in CloudWatch Logs - and if logging was set to `ERROR` only or not enabled, the team sees executions "completing" in the metrics with failures they cannot inspect. Worse, because Express is **at-least-once**, the orchestration may have *restarted* the execution, so a job that partially completed before the timeout can have applied its early side effects two or three times. The symptom set is: jobs that never finish, duplicate partial output, and no history to explain either.

**What the pricing model hid**: Express bills per request plus GB-second-style duration, so it *looks* like the cheap option in a spreadsheet comparison against Standard's per-transition charge - and for short, high-volume workflows it genuinely is. What that comparison hides is that the duration-based model is only cheap because Express workflows are supposed to be short: at 5 minutes the duration charge is already substantial, and a 20-minute workflow is not merely more expensive, it is *impossible*. They optimized the price of a design that cannot work.

The second hidden cost is **observability**: to debug an Express workflow you must enable `ALL`-level logging, and the CloudWatch Logs ingestion for a high-volume workflow can exceed the Step Functions charge itself. So the "cheap" option's true cost includes the logging you need to operate it.

**What I would do**: Standard workflow for the batch (per-transition pricing is trivial for a job with a handful of steps, and you get the durable history), with the long-running work in **Fargate via `.sync`** or **AWS Batch** rather than in Lambda (Q91, Q136), and a **distributed map** if the 20 minutes is really "10,000 items x 100 ms" (Q137) - in which case the right answer is a Standard workflow with a distributed map over Express child workflows, which is the pattern that gets you both scale and durability.

*Hook: a workflow type you had to change, and what the wrong choice cost before you found it.*

### Q135. ASL states and which removes the most Lambda code

The states: **`Task`** (do work), **`Choice`** (branch), **`Map`** (iterate over an array), **`Parallel`** (concurrent branches), **`Wait`** (delay until a time or for a duration), **`Pass`** (transform or inject), **`Succeed`**/**`Fail`**, plus per-`Task` **`Retry`** and **`Catch`** blocks.

**In practice the biggest code removers are `Retry`/`Catch` and `Choice`**, and I would defend that specifically:

- **`Retry`** deletes the retry loop, the backoff calculation, the jitter, the attempt counter and the error classification from *every* function. That code is written badly and inconsistently in most codebases, and it is the single most duplicated logic in a distributed system. Declaring `{"ErrorEquals": ["States.TaskFailed"], "IntervalSeconds": 2, "MaxAttempts": 5, "BackoffRate": 2, "JitterStrategy": "FULL"}` removes it, correctly, everywhere.
- **`Choice`** deletes the dispatcher function - the "read the result and decide what to call next" Lambda that otherwise exists purely to route, and which is where a surprising amount of untested branching logic accumulates.
- **`Wait`** deletes an entire pattern: the timer table plus sweeper (or a sleeping Lambda, which is billed and capped at 15 minutes).
- **`Map` / distributed `Map`** deletes the batching, chunking, concurrency-limiting and result-aggregation code around bulk work - and with it the reason people write a "coordinator" Lambda that is always the buggiest component.
- **`Parallel`** deletes `CompletableFuture` fan-out plus the partial-failure handling.

And the honourable mention that removes the most code of all, though it is not strictly a state: **direct SDK integrations on a `Task`** (Q136), which delete whole functions rather than parts of them.

*Hook: retry or branching logic you deleted from application code by moving it into a state machine.*

### Q136. Optimized integrations, SDK integrations and `.sync`

- **Optimized integrations** are hand-built integrations for common services with extra semantics: `lambda:invoke`, `sns:publish`, `sqs:sendMessage`, `dynamodb:putItem`, `ecs:runTask`, `batch:submitJob`, `states:startExecution`, `glue:startJobRun`, `sagemaker:*`, and the callback and `.sync` variants. They pre-date the SDK integrations and support the `.sync` and `.waitForTaskToken` patterns.
- **AWS SDK integrations** expose **most of the AWS API surface** (`arn:aws:states:::aws-sdk:s3:getObject`) as a task. This is what lets you build a workflow that touches twenty services without a single Lambda.
- **`.sync`** (e.g. `ecs:runTask.sync`, `batch:submitJob.sync`, `states:startExecution.sync`) means "start this and do not proceed until it finishes".

**What `.sync` does under the hood** - the substance of the question. Step Functions does not hold an open connection. It starts the job, then **monitors for completion**, and it does this in one of two ways depending on the service: for services that emit **EventBridge events** on state change (ECS task state change, Batch job state change), it consumes those events; where events are unavailable or insufficient, it **polls the service's describe API** on a backoff schedule. That is why:

- `.sync` requires **additional IAM permissions** beyond the start call - `ecs:DescribeTasks`, `events:PutRule` and `events:PutTargets` on the managed rule, `batch:DescribeJobs`. Missing these is the classic "my `.sync` task hangs or fails with AccessDenied" bug.
- There can be a **detection delay** of seconds between actual completion and the workflow advancing, because it is event- or poll-driven.
- If the workflow execution is **stopped**, Step Functions attempts to cancel the underlying job - and for some integrations that is best-effort, so you can end up with an orphaned task.

The practical guidance: prefer optimized integrations where they exist (better semantics, `.sync`, callbacks), fall back to SDK integrations to eliminate glue functions, and remember that `.sync` is orchestration polling in disguise - which is fine, but it means the IAM policy and the completion latency are part of your design.

*Hook: a `.sync` integration you used, and an IAM or timing surprise it produced.*

### Q137. Distributed Map versus inline Map

**Inline `Map`** iterates over an array **in the state machine's own payload**, with a maximum concurrency of about 40, and every iteration's input and output counts toward the execution's 256 KB payload and its history limit (25,000 events for Standard). So it is for tens of items, not thousands.

**Distributed `Map`** runs each iteration (or batch of iterations) as a **separate child workflow execution**, with:

- **Up to 10,000 concurrent** child executions.
- **An `ItemReader` that reads directly from S3**: a JSON array in an object, a JSON Lines file, a CSV file (with header handling), or the **object *listing* of a prefix or an S3 inventory manifest**. So the item set is not in the payload at all, and can be millions of items.
- **`ItemBatcher`** to group N items per child execution, which is how you avoid paying per-item orchestration overhead for cheap work.
- **`ResultWriter`** to write results to S3 rather than aggregating them into the parent's payload.
- **`ToleratedFailurePercentage` / `ToleratedFailureCount`**, so a small number of bad items does not fail the whole job - a genuinely important operational feature.
- Child executions can be **Express** (cheap, high throughput) or **Standard** (durable, inspectable per item).

**What it unlocks for a large S3 dataset**: "process every one of the 40 million objects under this prefix" becomes a single state, with no coordinator Lambda, no pagination code, no chunking logic, no concurrency management, no result-collection table, and per-item failure isolation with a bounded tolerance. It also sidesteps the payload limit entirely (Q142), because both input and output are S3-resident.

The trade-offs to name: child executions cost (state transitions for Standard children, requests plus duration for Express); the parent's visibility into individual items is limited unless you use Standard children; and a 10,000-way concurrent fan-out will happily destroy a downstream, so `MaxConcurrency` is a required design decision, not a default.

*Hook: a bulk job you converted to a distributed map, the item count, and the concurrency you had to cap it at.*

### Q138. The callback pattern for human approval

**Mechanism**: a `Task` with the `.waitForTaskToken` suffix. Step Functions generates a **task token**, passes it in the payload to whatever you invoke (a Lambda that sends an email, an SQS message to a review service, an SNS notification), and then **pauses the execution** - not polling, not billed for waiting - until someone calls `SendTaskSuccess`, `SendTaskFailure` or `SendTaskHeartbeat` with that token.

**The design:**

```
"WaitForApproval": {
  "Type": "Task",
  "Resource": "arn:aws:states:::lambda:invoke.waitForTaskToken",
  "Parameters": {
    "FunctionName": "notify-reviewer",
    "Payload": { "taskToken.$": "$$.Task.Token", "order.$": "$.order" }
  },
  "TimeoutSeconds": 259200,
  "HeartbeatSeconds": 3600,
  "Catch": [
    { "ErrorEquals": ["States.Timeout"], "Next": "EscalateOrAutoReject" },
    { "ErrorEquals": ["States.ALL"],     "Next": "ApprovalFailed" }
  ],
  "Next": "ApplyDecision"
}
```

1. `notify-reviewer` **persists the task token** alongside the review record (DynamoDB) and sends the notification with a link into your review UI. Persisting it is essential - the token is the only way back into the execution, and it exists nowhere else.
2. The reviewer acts in your UI; your API validates their authority and calls `SendTaskSuccess` with the token and the decision payload (or `SendTaskFailure` for a rejection you want to model as an error).
3. `ApplyDecision` branches on the payload.

**The timeout and the failure path** are the parts people omit:

- **`TimeoutSeconds`** must be set explicitly - without it a forgotten approval leaves the execution open for up to a year, silently. Set it to the business SLA (72 hours here) and `Catch` `States.Timeout` to an escalation or a default decision. Deciding *which* - escalate to a manager, auto-approve, or auto-reject - is a business rule, and asking for it is the right instinct.
- **`HeartbeatSeconds`** with periodic `SendTaskHeartbeat` detects a *dead reviewer process* faster than the overall timeout, which matters when the "human" is actually an external system.
- **Token loss**: if the notifying Lambda crashes after Step Functions issued the token but before persisting it, the execution waits for a token nobody holds until the timeout. Persist the token *first*, then notify.
- **Duplicate submission**: `SendTaskSuccess` on an already-completed token returns `TaskTimedOut`/`TaskDoesNotExist`; handle it as an idempotent no-op in your API rather than a 500.

*Hook: a human-approval workflow you built, and how you handled the abandoned-approval case.*

### Q139. Error handling in a state machine

**`Retry`** is per-`Task`, evaluated first, and matches on error names - service errors (`Lambda.TooManyRequestsException`, `DynamoDB.ProvisionedThroughputExceededException`), Step Functions' own (`States.Timeout`, `States.TaskFailed`), or your custom error names thrown from the function. Parameters: `IntervalSeconds`, `MaxAttempts`, `BackoffRate`, `MaxDelaySeconds` and **`JitterStrategy: FULL`** - use the last one, because without jitter a fan-out of failed tasks retries in lockstep and hammers the recovering downstream (Q200).

**`Catch`** runs after retries are exhausted, matching error names in order, routing to a state with the error in `$.error` (via `ResultPath`). This is where you put escalation, compensation entry and failure recording.

The discipline that separates a good answer:

1. **Classify errors in the function** and throw distinct, named errors. `ValidationError` must **not** be retried (retrying a malformed input is pure waste and delays the failure); `DownstreamUnavailable` must be. A single generic exception forces the state machine to treat everything the same, which is why error classification is application work that enables orchestration configuration.
2. **Retry the retryable, with jitter; catch the rest immediately.** Two `Retry` blocks on one task is normal: aggressive on throttles, conservative or absent on business errors.
3. **Set `TimeoutSeconds` on every task.** Without it a hung integration blocks the execution indefinitely, and `.sync` tasks are especially prone to this (Q136).

**Where compensation logic belongs**: not inside the failing task, and not inside a generic catch-all. It belongs in **explicit compensation states** that the `Catch` routes to, one per forward step, arranged so that the catch of step N enters the compensation chain at step N-1 (Q140). The reasons: compensation must be visible in the execution history (it is the part auditors and incident responders care about), it needs its own retries because *compensation itself can fail*, and putting it in the function couples the undo to the do and hides it from the diagram.

*Hook: an error-classification change you made that turned a retry storm into a clean failure.*

### Q140. A saga in Step Functions

**Forward path**: `AuthorizePayment` → `ReserveInventory` → `CreateShipment` → `Succeed`.

**Compensation**, entered by `Catch` at the appropriate depth:

```
AuthorizePayment   --Catch--> FailOrder                     (nothing to undo)
ReserveInventory   --Catch--> RefundPayment  -> FailOrder
CreateShipment     --Catch--> ReleaseInventory -> RefundPayment -> FailOrder
```

Each compensation state is a `Task` with its **own `Retry` block** (compensation runs when things are already unhealthy, so it needs more patience than the forward path) and its own `Catch`.

Key design points I would state:

- **Compensations must be idempotent and, ideally, semantic rather than literal.** You cannot "un-charge" a card - you issue a refund, which is a new business event with its own identifier. Model it that way rather than pretending the state can be rewound.
- **Each compensation needs the data to perform it**, so the forward steps must place their identifiers (payment ID, reservation ID) into the execution state. `ResultPath` matters here - if the forward step's output overwrites the state, the compensation has nothing to work with.
- **Order matters**: compensate in reverse.
- **A compensation for a step whose outcome is unknown** must first *query* before acting (Q131) - refunding a payment that never succeeded is its own incident.

**If compensation itself fails** - the question everyone skips:

1. **Retry it hard**: many attempts, long backoff with jitter, a long overall `TimeoutSeconds`. Most compensation failures are transient.
2. **Then stop trying to be clever.** Route to a terminal `CompensationFailed` state that (a) records the exact partial state - what succeeded, what was undone, what was not - in a durable store, (b) writes to a **manual-intervention queue with a page**, and (c) `Fail`s the execution with a distinctive error so the metric is separable.
3. **Never silently swallow it**, and never loop forever - an execution retrying a refund for a year is worse than a human being told about it in five minutes.
4. **Reconcile out of band**: the daily reconciliation job (Q131) is the backstop that catches the cases where both the action and the compensation ended ambiguous.

The sentence worth saying: **a saga's correctness rests on compensations being idempotent and on there being a defined human path when they fail** - the state machine gives you the structure, not the guarantee.

*Hook: a saga you implemented, a compensation that failed in production, and what the manual path looked like.*

### Q141. Idempotent workflow, two payments from a retry `[T]`

The state machine allowed it because **the retry is at the wrong layer relative to where the ambiguity is**. Specific mechanisms, any of which produces it:

1. **A `Retry` on the payment task with an error class that includes timeouts.** A `States.Timeout` or a socket timeout means *we do not know the outcome*. Retrying on unknown is retrying a possibly-successful charge. The workflow was idempotent in the sense that each step was written to be safely repeatable *given the same idempotency key* - but if the key is generated **inside** the task (a fresh UUID per attempt), each retry is a new logical payment to the provider. **This is the most common cause**: the key must be derived from the execution/order, not from the attempt.
2. **The provider was not given an idempotency key at all.** Our side deduplicates, the provider does not, so two HTTP requests are two charges. Our idempotency table protects against a duplicate *invocation of our handler*, not against a duplicate *outbound call* within one invocation's retry loop.
3. **An SDK-level retry inside the function** (the AWS SDK or an HTTP client retrying a POST) stacked under the state machine's retry, so one "attempt" was several requests (Q200).
4. **Express workflow's at-least-once execution** (Q133): the whole execution ran twice, and if `StartExecution` was not name-deterministic, both proceeded.
5. **An idempotency record written *after* the call** with a crash in between, so the second attempt saw no record (Q126's residual gap).

**The fixes, in order of importance**: derive the provider idempotency key deterministically from the business entity (`payment#<orderId>#<attemptGroup>`, stable across retries); write `SUBMITTED` with that key **before** the call; on any unknown outcome, do **not** retry the call - transition to a `VerifyPaymentStatus` state that queries the provider by the key and branches; remove client-side retries on non-idempotent POSTs; and use a deterministic execution name so a duplicate start is rejected.

The general principle: **retries are only safe when the operation carries an identity the callee honours.** A `Retry` block on a task without an idempotency key is a duplicate generator, and the state machine's declarative retry makes it easy to add one without thinking about that.

*Hook: a duplicate side effect caused by a retry, and where you had to move the idempotency key to fix it.*

### Q142. Payload limits and payload-by-reference

The limits: **256 KB** for the state input/output payload (and for the execution input), plus a history-event limit (25,000 events) and a per-state data size that the same 256 KB governs. Exceeding it fails the execution with `States.DataLimitExceeded`.

**Payload by reference**: instead of passing the data, pass a pointer. The task writes its output to S3 (or DynamoDB) and returns `{"bucket": "...", "key": "..."}`; the next task reads it. Variants: a single "workspace" prefix per execution (`s3://bucket/executions/{executionId}/step-3-output.json`), keyed so cleanup is a lifecycle rule (Q170).

**When the limit forces a redesign** - the cases where by-reference alone is not enough:

- **Iterating over a large collection.** An inline `Map` over 50,000 items cannot hold the array in the payload. This is not a "pass a pointer" fix; it is a **distributed `Map` with an S3 `ItemReader`** (Q137), which is the architecturally correct answer.
- **Accumulating results across many steps.** A workflow that appends to an array at each step grows until it fails, non-deterministically, in production, after weeks of working. The fix is `ResultWriter`/S3 accumulation, or `ResultPath: null` to discard outputs you do not need - and that second one is the cheap fix people forget.
- **Passing large documents through many states.** Each state's history event records input and output, so a 200 KB payload through 50 states also strains the history limit and makes the console unusable. By-reference is the fix, and it also makes the execution history readable.

Practices: use `ResultSelector` and `ResultPath` aggressively to keep only what the next state needs; never pass a whole entity when an ID suffices; and treat the execution payload as a **control plane**, not a data plane - a sentence that makes the design rule obvious.

*Hook: a workflow that hit the payload limit, and whether you moved to by-reference or to a distributed map.*

### Q143. Step Functions cost and the crossover

**Standard** bills **per state transition** (a Task, Choice, Wait, Map iteration, Parallel branch entry - each is a transition), with a small monthly free tier. **Express** bills **per request** plus **duration x memory** in GB-second-like units, and the memory tier is derived from the workflow's usage.

Worked arithmetic, using round order-of-magnitude figures (about $25 per million state transitions for Standard; for Express roughly $1 per million requests plus about $0.00001667 per GB-second):

- **Workflow A: 6 states, 1 million executions/month, 2 seconds duration, 64 MB.**
  - Standard: 6 million transitions ≈ **$150/month**.
  - Express: 1 million requests ≈ $1, plus duration `1e6 x 2 s x 0.0625 GB = 125,000 GB-s` ≈ $2.08 → **≈ $3/month**.
  - Express wins by ~50x. This is the API-backed case (Q133).
- **Workflow B: 6 states, 1 million executions/month, but 4 minutes duration** (mostly waiting on a downstream).
  - Standard: still **$150**.
  - Express: $1 + `1e6 x 240 s x 0.0625 GB = 15e6 GB-s` ≈ **$250**.
  - Standard now wins - and note that if the workflow *waits*, Standard's `Wait` state is free while Express is billing the whole time.

**The crossover** is therefore governed by duration, not by step count: with a handful of states, Express is cheaper below roughly **2-3 minutes** of duration and Standard is cheaper above it. And the more states you have, the earlier Standard becomes expensive - a 50-state workflow at a million executions is 50 million transitions, over $1,000/month, which is the point at which you ask whether some of those states should be one Lambda.

Two cost lessons that matter more than the crossover: **`Wait` states are nearly free in Standard and expensive in Express**, so long-running human or delay-based workflows must be Standard; and **Express's real cost is often the CloudWatch logging** you need for observability (Q134, Q188), which can exceed the workflow charge itself.

*Hook: a workflow whose Step Functions or logging bill you had to reduce, and what you changed.*

### Q144. Observability for state machines

**Execution history** is the primary tool and it is genuinely good: every state entry and exit with input and output, the error and cause for failures, and timings - retained and queryable via `GetExecutionHistory` for **90 days** for Standard workflows. The console's graph view with per-state input/output is usually enough to diagnose a failure in minutes.

**CloudWatch metrics**: `ExecutionsStarted`, `ExecutionsSucceeded`, `ExecutionsFailed`, `ExecutionsTimedOut`, `ExecutionsAborted`, `ExecutionThrottled`, `ExecutionTime`, and per-state `StateEntered`/`StateExited` plus `ActivityScheduleTime`/`LambdaFunctionRunTime`. The alarms I set: `ExecutionsFailed`, `ExecutionsTimedOut`, `ExecutionThrottled` (which catches quota problems), and `ExecutionTime` p99 against the business SLA.

**X-Ray** gives an end-to-end trace across the state machine and its Lambda tasks, which is how you attribute latency to a specific downstream rather than to "the workflow".

**Logging**: Standard workflows can log execution events to CloudWatch Logs; Express workflows *must*, because there is no durable history (Q133). Log level and `includeExecutionData` are cost decisions (Q188).

**Debugging a workflow that failed three days ago:**

1. **Find it**: `ListExecutions` filtered by status and time range, or - much better - the execution **name**, which is why deterministic naming from a business ID (`order-123`) is such a valuable practice. "Where is order 123" becomes `DescribeExecution` on `order-123`.
2. **Read the history**: the failed state, its input, and the `error`/`cause` fields. For a Lambda task the `cause` contains the stack trace.
3. **Correlate**: pull the Lambda's logs for that request ID (the history includes it), and the X-Ray trace if sampled.
4. **If it was Express and older than the log retention** - you cannot. This is the argument for setting retention deliberately and for emitting your own business-event log entries at key steps, which survive independently.
5. **Redrive**: Standard workflows support **redrive** of a failed execution from the point of failure (within 14 days), which is materially better than re-running from scratch because it does not repeat completed side effects.

The practice I would name as the highest-value one: **deterministic execution names plus an emitted business event at each significant step**, so a support question is answerable without console archaeology.

*Hook: a workflow failure you diagnosed days later, and what made it possible (or what was missing).*

### Q145. Step Functions versus EventBridge choreography versus a saga in code

For an **eight-step business process**, ranked:

1. **Step Functions (orchestration).** The process has a name, a lifecycle, an SLA and probably compensation - so somebody must own "where is it and why is it stuck", and a state machine answers that by construction (Q132). Eight steps is exactly the size where choreography's implicitness becomes expensive and orchestration's overhead is still trivial. This is my default recommendation.
2. **A saga implemented in application code.** Defensible when the steps are tightly coupled to one bounded context, all inside one service, and the team wants full testability in their own language. You get real unit tests and no ASL - but you now own retries, backoff, timeouts, persistence of the process state, resumption after a crash, and the operational query. Teams consistently underestimate the last three. Choose this when the process is *internal* to a service rather than across services.
3. **EventBridge choreography.** Each step reacts to the previous step's event with no central coordinator. Excellent for *extensibility* (add consumer nine without touching anyone) and for loose coupling, and it is the right shape for **notification-style** fanout (Q107). It is the worst of the three for an eight-step *process* because: there is no single place that knows the process state; compensation is distributed across eight services, each of which must know what to undo; a stuck process is diagnosed by tracing eight event hops; and the ordering and completeness of the whole flow is an emergent property nobody tests.

The framing I would offer rather than a flat ranking: **choreograph between bounded contexts, orchestrate within a business process.** A useful hybrid is exactly that - a Step Functions execution owns the order-fulfilment process, and it *emits* domain events onto EventBridge for anyone who wants to observe, so you get central control of the process and open extensibility around it. That hybrid is what I would actually build (Q115).

*Hook: a process you moved from choreography to orchestration or vice versa, and what triggered the change.*

### Q146. Deploying a new state machine with 4000 executions in flight `[T]`

**What happens to them: they keep running against the definition they started with.** Step Functions binds an execution to the state machine *revision* in effect when it started, so updating the definition does not rewrite running executions. That is the good news, and it is the first thing to say.

The nuances that follow, which are where the real answers live:

- **The update is eventually consistent.** For a short window after `UpdateStateMachine`, new executions may still start on the previous definition. So "deploy then immediately assert new behaviour" is flaky.
- **In-flight executions call the *current* version of their targets.** The state machine definition is pinned; the Lambda function it invokes is not, unless the definition names a **version or alias**. So an in-flight execution at step 3 will call the *new* code at step 4. That is the real hazard: the workflow is stable while the tasks underneath it change, and a payload contract change between steps 3 and 4 breaks 4000 executions mid-flight. **The fix is to invoke aliases, and to make task contracts backward compatible for at least the lifetime of the longest-running execution** - the same expand-contract discipline as a schema migration.
- **Removing a state is dangerous.** If an in-flight execution has not yet reached a state you deleted, it will still transition to it under its own pinned definition and that is fine - but a *human* looking at the console sees a graph that no longer matches. The genuinely breaking version is removing a **Lambda function or resource** a pinned definition still references.
- **Versions and aliases** exist for state machines too: publish a version, point an alias at it, and shift traffic with a **routing configuration** (weighted between two versions) - which gives you canary deployment for workflows, and lets you keep the old version alive until its executions drain.

**So the safe procedure**: publish a new version rather than mutating; use an alias with weighted routing for new executions; keep task Lambdas backward compatible across one release; call aliases from the definition; monitor the old version's execution count to zero before retiring it; and for genuinely incompatible changes, use a **new state machine** and route new work to it, letting the old one drain - the same strategy as an incompatible API version.

*Hook: a state machine change that affected in-flight executions, and the versioning practice you adopted afterwards.*

### Q147. An order fulfilment workflow with manual review and an SLA `[A]`

**Clarify first**: what is the end-to-end SLA and is it per-order or a percentile? What fraction of orders go to manual review, and what is the reviewers' response-time distribution? What are the third-party APIs' p99 and their timeout/retry behaviour, and do they support idempotency keys and status queries? Is the review synchronous to the customer (do they wait) or is the order accepted and reviewed after? What must be auditable?

**Workflow type: Standard**, and I would justify it firmly - a manual-review branch means an execution can be open for hours or days, which is impossible in Express, and an SLA-bound business process with compensation needs the durable history for both debugging and audit (Q133).

**Shape:**

```
StartExecution (name = order-{orderId}, deterministic -> duplicate-safe)
  ValidateOrder            (Lambda; ValidationError -> Catch -> RejectOrder)
  Choice: RiskScore
    high -> WaitForManualReview   (.waitForTaskToken, TimeoutSeconds = SLA slack,
                                   Catch States.Timeout -> EscalateOrAutoDecide)
    low  -> continue
  Parallel
    AuthorizePayment       (Lambda -> provider; idempotency key = order id;
                            Retry only on classified-transient; on unknown ->
                            VerifyPaymentStatus)
    ReserveInventory       (SDK integration -> DynamoDB conditional write)
  CreateShipment           (Lambda -> carrier API; TimeoutSeconds set;
                            Retry with FULL jitter)
  EmitOrderCompleted       (SDK integration -> EventBridge; no Lambda)
  Succeed
Catch chain -> ReleaseInventory -> RefundPayment -> RecordFailure -> Fail
```

**Error strategy for the unreliable third parties** - the crux of the question:

- **Explicit `TimeoutSeconds` on every task**, set below the remaining SLA budget rather than at a default. A task with no timeout is how you blow an SLA silently.
- **Error classification in the Lambda**: `Transient` (retry with exponential backoff and `JitterStrategy: FULL`), `Business` (do not retry, go straight to `Catch`), `Unknown` (do **not** retry - go to a verification state that queries the provider, Q141).
- **A retry budget, not just per-task retries**: track elapsed time in the execution state and use a `Choice` to stop retrying when the SLA budget is spent, failing fast into the compensation path instead of exhausting attempts. This is the mechanism that converts "retry until it works" into "meet the SLA or fail deliberately", and it is the thing most candidates miss.
- **Circuit-breaker state in DynamoDB** (Q204) that a `Choice` reads, so when the carrier API is broken the workflow takes the degraded path immediately instead of every execution paying the timeout.

**Where I would break the workflow in two**, and why: at the **manual review boundary**. The pre-review workflow (`ValidateOrder` → risk decision → accept-and-persist) is short, high-volume and synchronous-ish; the post-decision workflow (payment, inventory, shipment) is the fulfilment process. Splitting them means:

- The customer-facing accept path can be **Express** and fast, returning immediately with an order ID.
- The long-lived Standard execution is started only for orders that proceed, so I am not holding hundreds of thousands of open executions for orders that were rejected at validation.
- The review queue becomes an independent, observable system with its own SLA and its own escalation, rather than an opaque paused state inside a fulfilment execution.
- Each half can be deployed and versioned independently, which matters given Q146.

The two are joined by an event (`OrderApproved` on EventBridge) rather than by a nested execution, so a reviewer's decision is a domain event that other consumers (notifications, analytics) can also react to.

**How I would prove the SLA**: `ExecutionTime` p95/p99 alarmed against the SLA; a separate metric for time-in-review (which is a *human* SLA, and mixing it with the system SLA hides both); an EMF metric per third-party call with its own latency and error rate; and an alarm on the manual-intervention queue. And I would state the honest limitation: if 20 percent of orders go to human review with a multi-hour response distribution, the end-to-end SLA is a property of the review staffing, not of the architecture - and the design should surface that rather than obscure it.

*Hook: a workflow with a human step you designed, how you kept the SLA measurable, and what you split apart.*

---

## 10. Data services for serverless workloads

### Q148. Partitions, capacity units and item size

**Physical model**: a table is split into **partitions**, each holding up to 10 GB and serving up to **3000 RCU and 1000 WCU**. An item's **partition key** is hashed to select a partition; the **sort key** orders items within it. A partition key plus its items is an *item collection*, and one item collection cannot exceed a single partition's limits.

**Capacity units**:

- **1 RCU** = one **strongly consistent** read of up to **4 KB** per second. An eventually consistent read costs **0.5 RCU** (so 2 reads per RCU); a transactional read costs **2 RCU**.
- **1 WCU** = one write of up to **1 KB** per second. A transactional write costs **2 WCU**.
- Both round **up**: a 4.5 KB item costs 2 RCU to read strongly; a 1.1 KB item costs 2 WCU to write.

**How a request maps onto throughput** - the mapping that matters:

- `GetItem` on a 3 KB item, strongly consistent = 1 RCU. Eventually consistent = 0.5 RCU.
- `Query` returning 100 items of 2 KB each = 200 KB → 50 RCU strongly consistent (the *total bytes read*, rounded up per 4 KB, not per item - so many small items in one Query are efficient).
- `Scan` reads **everything it examines**, including items filtered out afterwards, so a `FilterExpression` does not save capacity - a point worth stating because it is the most expensive misconception in DynamoDB.
- A write with **2 GSIs** costs the base write plus a write to each affected index - so up to 3x the WCU (Q151).

The consequences to draw out: **item size is a cost multiplier on every read and write**, so putting a large blob in an item (rather than in S3 with a pointer) multiplies your bill; and **the 3000 RCU / 1000 WCU per partition limit is the real ceiling** behind every hot-partition story (Q152).

*Hook: a capacity calculation you did, and an item-size or index decision that changed the number materially.*

### Q149. Single-table design with three access patterns

Take a customer-orders service with these patterns:

1. Get a customer by ID.
2. List a customer's orders, most recent first.
3. Get an order with its line items.
4. (Commonly added) find orders by status across customers.

**Key schema**: generic keys, `PK` and `SK`, with type-prefixed values, plus a GSI with inverted or overloaded keys.

| Entity | PK | SK | Attributes |
| --- | --- | --- | --- |
| Customer | `CUST#c-123` | `PROFILE` | name, email, tier |
| Order | `CUST#c-123` | `ORDER#2026-08-14#o-9001` | total, status, createdAt |
| Line item | `ORDER#o-9001` | `ITEM#001` | sku, qty, price |
| Order header (for pattern 3) | `ORDER#o-9001` | `HEADER` | customerId, total, status |

**GSI1** for pattern 4: `GSI1PK = STATUS#PENDING`, `GSI1SK = 2026-08-14T10:03Z#o-9001`.

**How each pattern resolves:**

1. `GetItem(PK=CUST#c-123, SK=PROFILE)` - one request unit.
2. `Query(PK=CUST#c-123, SK begins_with ORDER#, ScanIndexForward=false, Limit=20)` - one query, already sorted newest-first because the sort key embeds an ISO date.
3. `Query(PK=ORDER#o-9001)` - returns the `HEADER` and all `ITEM#` rows in **one** request. This is the item-collection pattern and it is the whole point of single-table design: what would be a join is a single partition read.
4. `Query(GSI1, GSI1PK=STATUS#PENDING)` - sorted by time.

Notes I would add: the sort key is designed for **`begins_with` and range queries**, so the prefix hierarchy (`ORDER#<date>#<id>`) is chosen to support the sorts you need; a **sparse GSI** (only writing `GSI1PK` on pending orders) keeps the index small and cheap, and is one of the most useful tricks in the model; and an `entityType` attribute on every item makes items self-describing for consumers and for stream processing.

The discipline to state: **you enumerate the access patterns first and design keys to serve them; you cannot add a pattern later without adding an index or a migration.** That is the trade DynamoDB makes.

*Hook: a single-table model you designed, and an access pattern that arrived later and forced a GSI or a backfill.*

### Q150. Three situations where multiple tables are better `[T]`

1. **Wildly different lifecycle or operational requirements per entity.** One entity needs point-in-time recovery, encryption with a specific CMK and a 7-year retention; another is ephemeral session data with a 1-hour TTL and high write volume. Table-level settings - PITR, TTL, backup plans, encryption keys, capacity mode, global-table membership, stream configuration - cannot be applied per item. Forcing them together means paying the strictest setting for everything (PITR on a high-churn session table is a real cost) and losing the ability to expire one entity independently.
2. **Independent scaling and blast radius, especially with provisioned capacity.** One table means one throughput pool: a batch job hammering entity A throttles entity B, and adaptive capacity only partly compensates. Separate tables give separate capacity, separate metrics (so a throttle is attributable), separate hot-partition behaviour and separate limits. Related: an entity that will grow far beyond the others makes the shared table's item-collection and index sizing awkward.
3. **Ownership boundaries between teams or services.** A single table shared across bounded contexts is a shared database - which is the anti-pattern `03-microservices` spends a category on. Separate tables give per-team IAM scoping, independent schema evolution, independent deployment, and the ability to move an entity into its own service later without a data migration. Single-table design is a *within-a-service* technique, and the strongest argument for multiple tables is that the entities belong to different services.

Two more worth mentioning briefly: **when the entities are genuinely never queried together**, single-table design buys you nothing and costs you the complexity of overloaded keys and a harder-to-read model; and **analytics and export**, where one mixed-schema table is much harder to feed into Athena/Glue than clean per-entity tables.

The balanced statement: single-table design optimizes for **fetching related entities in one request**; if no access pattern needs that, the "best practice" is just complexity.

*Hook: a case where you split a single table, or resisted merging tables, and the deciding factor.*

### Q151. GSI, LSI, projections and index throttling

**LSI**: same partition key, different sort key. Created **only at table creation**, shares the table's throughput, supports **strongly consistent reads**, and constrains the item collection to **10 GB** total (the hard limit that catches people). Max 5 per table.

**GSI**: **different** partition key and sort key, creatable and deletable any time, has **its own capacity**, and is **eventually consistent only**. Max 20 by default.

**Projections**: `KEYS_ONLY`, `INCLUDE` (named attributes), `ALL`. This is a direct cost lever - a projection determines the index's storage and, critically, its **write cost**, because writing an item writes to every index whose projected attributes changed.

**What a GSI write costs you**: a `PutItem` that touches attributes projected into 2 GSIs consumes the base table WCU **plus** WCU for each index write, sized by the *index* item's size. So three indexes with `ALL` projections on a 1 KB item is roughly 4 WCU per write instead of 1 - a 4x write-cost multiplier that appears nowhere in the code. And if the update changes the index's *key*, DynamoDB performs a **delete plus an insert** in the index: two writes.

**How an index throttles the table** - the mechanism worth knowing precisely:

- For a **GSI**, if the index's provisioned capacity is insufficient (or an index partition is hot), the index write cannot be applied. DynamoDB does not fail the table write immediately; it buffers, but **if the backlog grows the base table's writes begin to be throttled**. So an under-provisioned or hot GSI throttles writes to the *table*, and the error appears on an operation that looks unrelated to the index. This is one of the classic DynamoDB debugging surprises.
- For an **LSI**, throughput is shared with the table by definition, so index reads and writes consume table capacity directly.

The design rules: project the minimum you need (`KEYS_ONLY` plus a follow-up `GetItem` is often cheaper than `ALL` for low-read indexes); use **sparse indexes** so only relevant items are indexed; watch per-index `ConsumedWriteCapacity` and `ThrottledRequests`; and treat each GSI as a write-amplification decision, not a free query capability.

*Hook: an index whose write amplification or throttling you had to diagnose, and what you changed.*

### Q152. Throttling at 30 percent utilization `[T]`

Two most likely causes:

1. **A hot partition.** Consumed capacity is reported as a **table-level aggregate**, but the limits are enforced **per partition** (3000 RCU / 1000 WCU, Q148). If your partition key is skewed - one tenant, one popular product, a date-based key where everything writes to today, a status key like `PENDING` - then one partition is at its ceiling while the table average sits at 30 percent. This is the answer in the large majority of cases, and the diagnostic is **CloudWatch Contributor Insights for DynamoDB**, which surfaces the most-accessed keys directly.
2. **A GSI is the actual bottleneck** (Q151). The index is hot or under-provisioned, its write backlog builds, and the base table's writes get throttled as a result. Table-level graphs look fine because you are looking at the wrong resource. Check per-index consumed and throttled metrics.

Other real candidates worth listing as the differential: **auto-scaling lag** - provisioned capacity with auto scaling reacts over minutes, so a sharp spike throttles while the target tracking catches up, and the *average* over the CloudWatch period hides the spike entirely (this is also why a 1-minute average can look like 30 percent while 5-second bursts were at 100 percent); **a burst of transactional operations** costing 2x what you counted; and **an item-size increase** pushing per-request capacity up.

The generalizable lesson to state: **DynamoDB's throttling is a per-partition, per-second phenomenon and your dashboard is a per-table, per-minute average - so the graph structurally cannot show you the cause.** You need Contributor Insights, per-index metrics, and awareness of the averaging window.

*Hook: a throttling incident where the aggregate graph was misleading, and the tool that actually found it.*

### Q153. Adaptive capacity and burst capacity

**Burst capacity**: DynamoDB retains up to **5 minutes** of unused capacity per partition and lets you consume it in a spike. It smooths short, infrequent bursts and is invisible when it works.

**Adaptive capacity**: DynamoDB continuously monitors per-partition traffic and **redistributes provisioned throughput toward hot partitions**, up to the partition maximum. It is now instantaneous rather than the slow reallocation of the original implementation. It also **isolates** a persistently hot item collection by splitting the partition (split-for-heat) when the key space allows it.

**What they fix**: transient imbalance and moderately skewed workloads. A table where one tenant is 10x busier than the others usually runs fine because adaptive capacity gives that partition more of the table's throughput.

**What they cannot fix - the class of hot key that remains**: a **single partition key value** whose demand exceeds the per-partition ceiling. Because the partition limit (3000 RCU / 1000 WCU) is physical, and because all items with the same partition key must live in the same partition, no redistribution helps. Split-for-heat can split a *partition* across key values, but it cannot split one key value's item collection across partitions. So:

- One celebrity item read 20,000 times a second → throttled, permanently.
- A counter item written 5,000 times a second → throttled, permanently.
- `GSI1PK = STATUS#PENDING` for a high-volume system → one index partition takes every write.

**The fixes are key-design fixes**: **write sharding** (append a suffix `0..N` to the key and scatter writes, then read all N shards and aggregate - the standard counter pattern); **read caching** in DAX or ElastiCache for the celebrity-read case (Q159); **time-bucketing** so today's writes spread across `STATUS#PENDING#<hour>`; or removing the pattern (an atomic counter usually wants to be a stream aggregation, not a hot item).

The sentence worth saying: **adaptive capacity solves uneven load across keys; it cannot solve too much load on one key, because that is a physics problem, not a scheduling problem.**

*Hook: a hot key you designed around, and the sharding or caching approach you used.*

### Q154. On-demand versus provisioned with auto scaling

**On-demand** bills per request (read/write request units) with no capacity planning, scales instantly to double your previous peak, and can be switched once every 24 hours per table. **Provisioned** bills per hour of provisioned RCU/WCU, with Application Auto Scaling adjusting toward a utilization target.

**The arithmetic.** On-demand costs roughly **6-7x** provisioned per unit of capacity for the same throughput. So the crossover is a **utilization** question: provisioned is cheaper when your *average* consumption is above roughly **15-20 percent** of what you would have to provision for peak.

Worked: a table peaking at 1000 WCU. Provisioned at 1000 WCU costs the same regardless of use. On-demand costs per request. If the daily average is 500 WCU (50 percent utilization), on-demand is roughly 3x the provisioned cost - provisioned wins clearly. If the average is 50 WCU with a rare 1000 spike (5 percent utilization), on-demand is roughly a third of provisioning for peak - on-demand wins clearly.

**The traffic shape that decides it:**

- **Steady or predictably diurnal** → provisioned with auto scaling (and consider **reserved capacity** for the baseline, which discounts further, Q253).
- **Spiky with a high peak-to-average ratio, or unpredictable** → on-demand. Auto scaling reacts in minutes, so a sharp spike throttles (Q152); on-demand does not.
- **New workload with unknown traffic** → on-demand, then measure for a month and switch.
- **Development and low-volume tables** → on-demand, always; provisioning 5 WCU per table across 200 tables is both more expensive and more work.
- **Genuinely bimodal** (quiet all week, 50x on Friday) → on-demand, or provisioned with **scheduled scaling** if the schedule is truly known.

Two practical notes: on-demand's "double the previous peak" behaviour means a first-ever spike beyond 2x can still throttle, so pre-warm by ramping if you know a launch is coming; and mixing modes across tables in one application is normal and correct - the decision is per table, not per estate.

*Hook: a table whose capacity mode you switched, and the utilization number that justified it.*

### Q155. Transactions versus conditional writes

**`TransactWriteItems`** applies up to 100 actions (`Put`, `Update`, `Delete`, `ConditionCheck`) across one or more tables in the same region **atomically and serializably** - all succeed or none do. `TransactGetItems` gives a consistent snapshot read. Each action costs **2x** the equivalent non-transactional operation (so a transactional write of a 1 KB item is 2 WCU), because DynamoDB does a two-phase prepare/commit internally.

**Semantics to state precisely**: it is a *serializable* transaction, not a long-lived one - no interactive transactions, no "begin/commit" spanning application logic. A conflicting concurrent transaction fails with `TransactionCanceledException` and a per-item reason (`ConditionalCheckFailed`, `TransactionConflict`, `ThrottlingError`), and **you must inspect the cancellation reasons** to know which - a very common implementation gap. Also: the same item cannot appear twice in one transaction, and there is no rollback to write yourself.

**Where a conditional write is the better choice** - the more important half:

- **Single-item atomicity.** `UpdateItem` with a `ConditionExpression` is already atomic on that item and costs **half** as much. Optimistic locking, "reserve only if available", "insert if not exists", counter increments - all of these need a conditional write, not a transaction. Reaching for `TransactWriteItems` for one item is a pure 2x cost error and I see it often.
- **When you can model the invariant into one item.** Putting the order and its line items in a single item, or the reservation and its count in one item, converts a multi-item transaction into a single conditional write. **Model to avoid transactions** is the DynamoDB-idiomatic move.
- **High-contention hot paths**, where transactional conflicts multiply retries and make the throughput worse than the single-item alternative.

**Where a transaction is genuinely right**: writing a business item **and** its idempotency record together (Q126, Q131); maintaining a uniqueness constraint via a separate `EMAIL#x` sentinel item plus the user item; debit-and-credit across two accounts; and a `ConditionCheck` on one item guarding a write to another (the "only if the parent is still active" case), which has no non-transactional equivalent.

*Hook: a transaction you replaced with a conditional write, or a uniqueness constraint you implemented with a sentinel item.*

### Q156. Optimistic locking versus a lock table, and a lossless counter

**Optimistic locking** with a version attribute:

```
UpdateItem
  Key: {PK: "ORDER#o-9001"}
  UpdateExpression: "SET #s = :new, version = :nextV"
  ConditionExpression: "version = :curV"
```

If another writer got there first, the condition fails, you re-read and retry. One round trip, no lock to leak, no timeout to tune. This is the correct default, and the DynamoDB Enhanced Client's `@DynamoDbVersionAttribute` implements it for you.

**A lock table** (acquire a lease item with a TTL, do the work, release) is a *pessimistic* design. It costs at least two extra writes, introduces lease-expiry ambiguity (did the holder die, or is it just slow?), and creates a hot item if the lock is coarse. I use it only when the critical section spans **multiple resources or a non-DynamoDB side effect** and cannot be expressed as a condition - and even then I would look at Step Functions or a single-writer partition first.

**A counter that must never lose an update:**

```
UpdateItem
  Key: {PK: "COUNTER#page-views#2026-09-01"}
  UpdateExpression: "ADD views :one"
```

`ADD` is an **atomic increment applied server-side**, so concurrent writers never lose an update and no version check is needed - this is the correct answer, and the wrong answer is read-modify-write with optimistic locking (correct but slower and contended).

The caveat that completes the answer: an atomic counter on **one item** is capped by the per-partition write limit of about 1000 WCU (Q153), so at high volume you must **shard the counter** - write to `COUNTER#...#<random 0..N>` and sum the N shards on read, or aggregate asynchronously from a stream. And note that `ADD` is *not* idempotent: a retried increment double-counts, so if the caller can retry you need either an idempotency guard (Q126) or a design where the increment is derived from a deduplicated event stream.

*Hook: a concurrency control you chose, and whether contention or idempotency turned out to be the harder problem.*

### Q157. DynamoDB Streams versus Kinesis Data Streams for DynamoDB

| | DynamoDB Streams | Kinesis Data Streams for DynamoDB |
| --- | --- | --- |
| Retention | **24 hours** | 24 hours to **365 days** |
| Ordering | Strictly ordered **per item** (per partition key) | Ordered per **shard**; the item's key is the partition key, so effectively per item, but resharding can affect it |
| Duplicates | Exactly-once record delivery into the stream | **May contain duplicates** (at-least-once into the stream) |
| Consumers | Up to **2** simultaneous readers per shard recommended | Many, plus enhanced fan-out |
| Shard management | Automatic, invisible, tracks table partitions | You manage shards (or on-demand), independent of the table |
| Cost | Read requests on the stream | Kinesis pricing: shard hours plus PUT payload units |
| Ecosystem | Lambda event source mapping, Kinesis Client Library adapter | Firehose, Managed Flink, Kinesis analytics, any Kinesis consumer |

**For a CDC pipeline I would pick Kinesis Data Streams for DynamoDB**, and the reasoning is retention and consumer count. A CDC pipeline feeds a data lake, a search index, an analytics store and probably a downstream service; with DynamoDB Streams you are at the two-consumer guidance almost immediately and you have a 24-hour recovery window - so a consumer broken over a long weekend loses data permanently. With Kinesis you set retention to 7 days or more, add consumers freely with enhanced fan-out, and get Firehose delivery to S3 for free.

**When DynamoDB Streams is right**, and it usually is for application purposes: a single Lambda consumer implementing the transactional outbox (Q128), maintaining a materialized view, or triggering side effects. Simpler, cheaper, no shard management, exactly-once into the stream, and the per-item ordering guarantee is cleanly stated.

The design that gets both: **DynamoDB Streams to a Lambda for the tight application coupling, and Kinesis Data Streams for the analytics/CDC fanout** - both can be enabled on the same table.

*Hook: a CDC pipeline you built off DynamoDB, and whether the 24-hour retention ever bit you.*

### Q158. TTL semantics

You designate a **numeric attribute holding an epoch-seconds timestamp**. DynamoDB scans for expired items in the background and deletes them.

**How promptly**: typically within 48 hours of expiry, and often much sooner, but **there is no SLA**. The item remains **readable** after its expiry time until the deletion actually happens - which is the single most important operational fact. Deletion consumes **no write capacity** and costs nothing, which is why TTL is the correct way to expire data at scale rather than a scheduled delete job.

**What it emits to the stream**: a `REMOVE` record with `userIdentity.type = "Service"` and `principalId = "dynamodb.amazonaws.com"`. That marker is what lets a consumer distinguish a TTL expiry from an application delete - and it is genuinely useful: archive-on-expiry (write the `OldImage` to S3), emit a `SubscriptionExpired` domain event, or clean up related data in another table.

**What you must never rely on it for:**

- **Correctness or security.** "The token is expired because TTL deleted it" is false - the item may still be there and readable for up to two days. **Always check the expiry attribute in your query or in code**, and use a `FilterExpression`/`ConditionExpression` on it. This is the mistake that turns TTL into a security bug (a session or a one-time token that remains valid).
- **Compliance-driven deletion deadlines.** "Delete within 24 hours" cannot be satisfied by TTL alone; you need an explicit deletion process with evidence.
- **Precise business timing** - "the offer ends at midnight" must be enforced by logic, not by the absence of a row.
- **Counting or aggregates** derived from item presence, which will be wrong during the lag window.
- Also worth noting: TTL deletion still costs *read* capacity for the background scan in the sense that it competes with your traffic in extreme cases, and expired-but-not-deleted items still consume **storage** you are billed for.

*Hook: a TTL-based expiry you implemented, and the place you had to add an explicit expiry check.*

### Q159. DAX versus ElastiCache in front of DynamoDB

**DAX** is a DynamoDB-specific, in-VPC, write-through cache cluster that speaks the DynamoDB API. You point the DAX client at it and your existing `GetItem`/`Query` calls are cached; item cache and query cache have separate TTLs. Because it is **write-through**, writes go through DAX to DynamoDB and the item cache is updated, so it is *mostly* self-invalidating.

**ElastiCache (Redis)** is a general cache you populate yourself: read-through or cache-aside logic in your code, your own key design, your own TTLs, your own invalidation on write.

| | DAX | ElastiCache Redis |
| --- | --- | --- |
| Consistency | **Eventually consistent reads only** from the cache; strongly consistent reads pass through to DynamoDB (and are not cached) | Whatever you implement; typically stale until TTL or explicit invalidation |
| Invalidation | Automatic on writes **made through DAX**; TTL otherwise | Yours to implement, and the hard part |
| Code change | Almost none (swap the client) | Real work: keys, serialization, cache-aside logic |
| Data model | Only DynamoDB items and query results | Anything: computed aggregates, sessions, rate-limit counters, sorted sets |
| Cost | Cluster of nodes, hourly, multi-node for HA | Cluster of nodes, hourly |
| Lambda fit | Requires VPC attachment (Q40) | Requires VPC attachment |

**The critical DAX caveat**: writes that **bypass DAX** - another service writing directly to the table, a stream-driven updater, a batch job, a global-table replication from another region - leave DAX serving stale data until the TTL expires. So DAX is only safe when *all* writers go through it, or when staleness bounded by the TTL is acceptable.

**When neither is the right answer**, which is often:

- **When the read pattern is not actually repetitive.** A cache in front of a uniform key distribution has a poor hit rate and you have paid for a cluster to add a hop.
- **When DynamoDB is already fast enough.** Single-digit-millisecond `GetItem` satisfies most requirements; a cache is for microsecond-scale reads or for *cost* reduction on a very hot key.
- **When the real problem is a hot partition** (Q153) - a cache does fix the read side of that, and is the right answer there, so distinguish carefully.
- **When you would have to put a Lambda in a VPC just for the cache** (Q40), adding NAT, ENIs and failure modes - measure whether the latency win survives that.
- **Better alternatives to consider first**: a smaller item and a better key design; eventually consistent reads (half the RCU); a CloudFront or API Gateway cache at the edge if the response is cacheable per request rather than per item.

*Hook: a caching layer you added in front of DynamoDB, the hit rate you achieved, and whether it was latency or cost that justified it.*

### Q160. Aurora Serverless v2 ACU scaling

**Mechanism**: capacity is measured in **ACUs** (roughly 2 GiB of memory with proportional CPU and network). You set a **minimum and maximum** ACU range (from 0 or 0.5 up to 256), and Aurora scales within it **in place, in fine-grained increments, in under a second**, without a failover or a connection drop. That is the v1-to-v2 difference: v1 scaled by finding a "scaling point" and could not scale mid-transaction, so it stalled; v2 adds capacity to the running instance.

**What the minimum controls, and why it matters more than the maximum**: the minimum sets the **buffer pool size**. Scaling down evicts cache, so a database that idles at 0.5 ACU and then receives traffic must re-warm its buffer pool from storage - producing a latency spike that looks like a scaling delay but is actually a cold cache. So set the minimum from your working-set and connection needs, not from the idle bill. (Aurora Serverless v2 can now scale to **zero** after an inactivity period, which is excellent for dev and bad for anything latency-sensitive, because resume takes seconds.)

**Where it still surprises people:**

- **It does not scale *down* quickly.** Scale-up is aggressive; scale-down is deliberately gradual to avoid thrashing, so a burst can leave you at high capacity (and cost) for a while afterwards.
- **Cost.** Per-ACU-hour pricing is meaningfully higher than a provisioned instance of equivalent size. For a **steady** workload, provisioned Aurora with a Savings Plan or reserved instance is materially cheaper - Serverless v2 pays off for variable, spiky or unpredictable load, and for dev/test.
- **Connection storms are not solved by it.** More ACUs raises `max_connections`, but a Lambda fleet at 800 concurrency still opens 800 connections and the per-connection memory cost is real (Q161). You need RDS Proxy regardless.
- **Some features and versions lag** provisioned Aurora, and the reader/writer topology still matters - scaling the writer does not scale reads.
- **A long-running transaction or a lock can block scaling actions**, and DDL under load behaves the same way it does anywhere else.

*Hook: an Aurora Serverless v2 deployment, the minimum ACU you settled on, and why.*

### Q161. `too many connections` at 400 concurrent Lambdas `[T]`

**Mechanism.** Each Lambda execution environment is a separate process with its own connection pool. Nothing is shared. So concurrency N means up to `N x pool_size` connections; with the framework default pool of 10, 400 concurrent executions is up to **4000 connections**. Aurora/PostgreSQL `max_connections` scales with instance memory and is in the hundreds for small-to-medium classes, so you exhaust it long before the database is CPU-bound. Worse, each PostgreSQL connection costs several megabytes of server memory and a backend process, so even *reaching* the limit degrades the database - and connections are opened and closed constantly as environments are created and reclaimed, so you also pay TCP plus TLS plus authentication handshake latency on every cold start.

**Fix 1: RDS Proxy** (Q162). A managed connection pooler in front of the database multiplexes many client connections onto few database connections. Lambdas connect to the proxy; the proxy holds a small warm pool.
*Trade-offs*: an extra hop (roughly 1-5 ms), an hourly per-vCPU charge, it must live in the VPC (so the Lambda must too, Q40), and **pinning** can defeat the multiplexing (Q162). It also improves failover time, which is a bonus.

**Fix 2: Do not hold connections at all - use the Data API** (for Aurora Serverless and Aurora PostgreSQL/MySQL), an HTTPS, IAM-authenticated SQL endpoint with no persistent connection.
*Trade-offs*: higher per-statement latency, a different programming model (no JDBC, so ORMs and Spring Data need adaptation or do not work), result-size limits, and per-request pricing. Excellent for low-to-moderate volume and for Step Functions SDK integrations (Q136); wrong for chatty, latency-sensitive transactional code.

**The additional fixes I would apply regardless**, because they are cheap:

- **Pool size of 1-2 per environment**, not 10 (Q79). This alone is often a 5-10x reduction.
- **Cap the concurrency that reaches the database**: `MaximumConcurrency` on the event source mapping for async paths (Q129), or reserved concurrency as a ceiling.
- **Question whether the workload belongs on a relational database at all** - if the access pattern is key-value, DynamoDB has no connection model and the problem disappears.

*Hook: a connection-exhaustion incident, which fix you applied, and the pool-size change you should have made first.*

### Q162. RDS Proxy: pooling, pinning, failover and IAM

**Pooling**: the proxy maintains a warm pool of database connections and multiplexes client sessions onto them, borrowing a database connection only for the duration of a statement or transaction and returning it afterwards. That is what lets 4000 Lambda clients share 100 database connections.

**Failover**: the proxy holds the client connections open across a database failover, detects the new writer, and re-points - so the application sees a brief stall instead of a dropped connection and a DNS-cache-length outage. AWS quotes a reduction of failover time by up to ~66 percent, and in practice it is the difference between "a pause" and "every pod restarts". For many teams this is the *primary* reason to adopt it, not pooling.

**IAM authentication**: the proxy can authenticate to the database using credentials from **Secrets Manager**, while clients authenticate to the *proxy* with **IAM** - so no database password ever exists in a function's configuration, and rotation is handled centrally. This is a genuine security improvement and worth naming.

**Pinning** - the mechanism that determines whether you get any benefit. The proxy can only multiplex when a client session is stateless between statements. If the session sets something that must persist, the proxy **pins** that client to its database connection for the life of the session, and multiplexing stops for it. Common causes:

- Explicit transactions are fine (pinned for the transaction only), but **`SET` statements** on session variables, `SET SESSION CHARACTERISTICS`, temporary tables, prepared statements outside a transaction, advisory locks, `LISTEN`/`NOTIFY`, and large result sets or packets can all pin.
- Some drivers and ORMs issue session-level `SET`s on connect (timezone, search path, character set) - so a framework's default behaviour can pin every connection without a line of your code being involved.

**Why it hurts**: with all sessions pinned, the proxy degrades to a 1:1 passthrough with an extra hop and an hourly charge, and you are back to Q161's exhaustion. The diagnostic is the `DatabaseConnectionsCurrentlySessionPinned` CloudWatch metric - if it tracks total connections, you are pinned. Fixes: remove session-level `SET`s (configure them in the database's parameter group or the database/user defaults instead), avoid temporary tables and advisory locks in the hot path, keep transactions short, and check the driver's connect-time behaviour.

*Hook: a proxy deployment where pinning undermined the benefit, and what you changed to fix it.*

### Q163. Aurora replicas, endpoints and failover

**Topology**: one writer and up to 15 **Aurora replicas** sharing the same distributed storage volume, so replication is at the *storage* layer rather than by shipping and replaying logs. That is why replica lag is typically **tens of milliseconds** rather than seconds, and why adding a replica does not add write cost.

**Endpoints**:

- **Cluster endpoint** - always resolves to the **current writer**. Use it for writes.
- **Reader endpoint** - DNS round-robins across available replicas. Use it for reads, with the caveat below.
- **Custom endpoints** - a named subset of instances, which is how you route analytics or reporting traffic to dedicated, differently sized replicas without them stealing capacity from the application's read path. Underused and genuinely useful.
- **Instance endpoints** - a specific instance; needed for pinning a session, and dangerous to hardcode.

**What a failover looks like to the application:**

1. Aurora detects writer failure and **promotes a replica** (chosen by failover priority tier); typically **under 30 seconds**, often ~10-15.
2. The **cluster endpoint's DNS is updated** to the new writer.
3. **In-flight transactions are lost** - the connection is broken and the application sees a connection error or a "read-only" error if it reconnects to a demoted instance.
4. Clients that **cache DNS beyond the TTL** keep pointing at the old writer and receive read-only errors - the JVM's `networkaddress.cache.ttl` defaulting to a long value (or `-1` with a security manager) is a classic cause of "the failover completed but the application never recovered". Set the JVM DNS TTL to ~5 seconds, or use RDS Proxy (Q162) which handles this for you.
5. **The reader endpoint's round-robin is not instant either**, and during the event a replica may briefly be both promoted and in the reader pool.

The application-side requirements to state: **retry with backoff on connection errors**, treat "read-only transaction" errors as a retryable failover signal, keep transactions short so less work is lost, and use the reader endpoint only for traffic that tolerates replica lag - a read-after-write on the reader endpoint will occasionally miss, which is the most common Aurora correctness bug.

*Hook: an Aurora failover you observed, how long recovery actually took, and the client-side setting that mattered.*

### Q164. ElastiCache Redis versus MemoryDB versus DynamoDB with DAX

| | ElastiCache Redis | MemoryDB for Redis | DynamoDB + DAX |
| --- | --- | --- | --- |
| Durability | **Cache semantics** - snapshots and AOF-ish options, but data loss on failover is possible and expected | **Durable**: writes committed to a multi-AZ transactional log before acknowledgement | DynamoDB is durable and multi-AZ; DAX is a cache in front of it |
| Latency | Sub-millisecond reads and writes | Sub-millisecond reads, **single-digit-millisecond writes** (the durability cost) | Microseconds from DAX cache; single-digit ms from DynamoDB |
| Data model | Full Redis: strings, hashes, sorted sets, streams, Lua, pub/sub | Full Redis, same API | Key-value/document with query on keys and indexes |
| Scale model | Cluster mode with shards and replicas, you size nodes | Same | Fully managed partitioning, no nodes |
| Cost shape | Node-hours | Node-hours plus write charges; more expensive than ElastiCache | Request/storage based, plus DAX node-hours if used |

**The case for each:**

- **ElastiCache Redis** - when you need Redis's *data structures* as a working set that you can afford to lose and rebuild: session caches, rate limiters and token buckets, leaderboards (sorted sets), pub/sub, deduplication sets, computed aggregates, and cache-aside in front of any database. The default choice for caching.
- **MemoryDB** - when you need Redis's data structures as the **primary, durable datastore** with microsecond reads: a real-time state store where losing state means losing business data (a live trading position, an in-flight game state, a session that *must* survive), or replacing a self-managed Redis-as-database with something you can defend in a DR review. You pay for durability in write latency and money, so only choose it when "we cannot lose this" is true.
- **DynamoDB + DAX** - when the data is item-shaped and the API is already DynamoDB, and you want microsecond reads with no cache code and no invalidation logic (Q159). The case is a hot read path on DynamoDB items where all writes go through DAX.

The decision question I would state: **"if this data disappears, what happens?"** If the answer is "we rebuild it from the source of truth" → ElastiCache. If it is "we lose business state" → MemoryDB (or a real database). And if the source of truth is already DynamoDB → DAX, because it removes an entire class of invalidation bugs.

*Hook: a cache-versus-datastore decision you made, and whether durability turned out to matter.*

### Q165. The data layer for a multi-tenant SaaS `[A]`

**Clarify first**: what is the 5 ms read target measured at - the datastore, the API, or the browser? Is it p50 or p99? What does "strict per-tenant isolation" mean legally - separate encryption keys, separate storage, separate accounts, or just correct authorization? What is the largest tenant relative to the median (the noisy-neighbour risk, Q262)? What analytics - operational dashboards for tenants, or internal BI? And what is the compliance regime (residency, retention, right to erasure)?

**The design:**

| Concern | Choice | Reasoning |
| --- | --- | --- |
| Primary operational store | **DynamoDB, single table, `PK = TENANT#<id>#<entity>`** | Tenant ID as the leading component of the partition key gives natural data locality and makes IAM-level isolation expressible (`dynamodb:LeadingKeys` condition). No connection model, scales per tenant, on-demand absorbs unpredictable growth (Q154) |
| The 5 ms read target | **DAX** in front of DynamoDB for the hot read path | Microsecond cache hits; and because all writes go through the application, DAX's write-through invalidation is safe (Q159). If 5 ms is a p99 at the API, also cache the *composed response* at CloudFront or in ElastiCache |
| Session, rate limiting, per-tenant quotas | **ElastiCache Redis** | Token buckets and counters are Redis's job, and losing them is recoverable (Q164) |
| Relational needs (reporting joins, complex transactional logic, tenant-supplied SQL) | **Aurora Serverless v2** with RDS Proxy, schema-per-tenant for large tenants, shared schema with a tenant column for the long tail | Only if genuinely required. Serverless v2 for unpredictable growth (Q160); Proxy because a Lambda tier will exhaust connections otherwise (Q161) |
| Analytics | **DynamoDB → Kinesis Data Streams for DynamoDB → Firehose → S3 (Iceberg/Parquet, partitioned by tenant and date) → Athena**, with per-tenant dashboards served from pre-aggregated DynamoDB items | Keeps analytical scans entirely off the operational store - which is the single most important isolation decision here. Long retention gives replayability (Q157) |
| Search | OpenSearch Serverless, fed from the same stream, index per large tenant or a tenant filter for the long tail | Search on DynamoDB is not a thing; the stream is the natural feed |
| Per-tenant cost reporting | Tag what is taggable; for shared resources, **emit per-tenant usage metrics (EMF) and allocate** | Serverless costs are mostly not taggable per tenant, so attribution must be computed from usage, not from tags (Q255, Q257) |

**How they stay in sync**: DynamoDB is the single source of truth, and **everything else is derived from its change stream**. One stream, several consumers: search index, analytics lake, aggregate rollups, cache warming. That means (a) there is exactly one write path, so no dual-write inconsistency (Q128); (b) every derived store is rebuildable by replaying the stream, which is what makes a search-index bug a re-index rather than an incident; and (c) consumers must be idempotent and version-aware (Q114).

**Isolation, by tier** - I would present this as a spectrum rather than a binary:

- **Pool (shared table, tenant-prefixed keys)** for the long tail: cheapest, and isolation is enforced by IAM `LeadingKeys` conditions plus a tenant-scoped session, so a code bug cannot cross tenants because the *credentials* cannot.
- **Silo (dedicated table, or dedicated account)** for the largest or most regulated tenants: available as a tier, priced accordingly, using the same code path with different configuration. Design for this from day one even if no tenant needs it yet, because retrofitting it is a rewrite.
- **Per-tenant KMS keys** where a contract requires cryptographic separation, and per-tenant residency by deploying the stack in the required region (Q226).

**Noisy neighbours**: per-tenant rate limits at the edge (usage plans or a Redis token bucket), per-tenant concurrency ceilings on async paths, and the analytics path physically separated so a tenant's report cannot slow another's writes.

**What I would flag as the risks**: the 5 ms target may be unachievable end-to-end if the response requires composing several items - so I would want to know whether we can denormalize into a single read; and "strict isolation" plus "unpredictable growth" plus "cheap" is a trilemma, so the tiering above is how I would resolve it commercially rather than technically.

*Hook: a multi-tenant data design you built, the isolation model you chose, and the tenant that forced you to change it.*

---

## 11. S3 as an architectural tier

### Q166. S3 consistency today

**S3 provides strong read-after-write consistency** for `PUT`s of new objects, overwrite `PUT`s and `DELETE`s, plus strongly consistent `LIST` operations - all at no cost and with no performance penalty, since December 2020. So after a successful `PUT` returns, a subsequent `GET` from any client returns the new data, and a `LIST` immediately reflects the change.

**Workarounds that are now obsolete** and should be deleted when you find them:

- **Retry-until-found loops** after a write ("`GET` in a loop with sleeps because the object might not be there yet").
- **"Read-after-write is fine but overwrites are eventual"** branches - both are strong now.
- **DynamoDB (or the old EMRFS consistent view / S3Guard) as a metadata index** whose only purpose was to know which objects really exist. A metadata index for *querying* is still valid; one for *consistency* is dead weight.
- **Writing to a new unique key on every update to avoid overwrite eventualness**, and the garbage-collection machinery that pattern needed.
- **Artificially randomized key prefixes purely for consistency reasons** (the performance reason is also obsolete, Q167).

**What is still not guaranteed, and worth stating so the answer is not naive**:

- **Cross-Region Replication is asynchronous** - the destination bucket is eventually consistent with the source (Q177).
- **Bucket-level configuration changes** (policies, ACLs, lifecycle rules, replication config) are eventually consistent, and can take minutes.
- **Concurrent writers to the same key** get last-writer-wins with no conditional-put semantics historically; S3 now supports conditional writes (`If-None-Match` for "create only if absent", and ETag-based preconditions), which is the correct primitive for an object-level lock or a claim - and worth knowing because it is recent and removes a whole class of DynamoDB-as-a-lock patterns.
- **`LIST` is strongly consistent but still paginated and expensive** at scale; S3 Inventory remains the right tool for large enumerations.

*Hook: a consistency workaround you removed, or a place where the CRR asynchrony still bit you.*

### Q167. Request-rate scaling and key design

**The limits**: S3 scales to at least **3500 PUT/COPY/POST/DELETE and 5500 GET/HEAD requests per second per prefix**, and there is no limit to the number of prefixes. So aggregate throughput is effectively unbounded if the keys spread across prefixes.

**What a prefix is** - the part people get wrong. It is not a "folder" and it is not the whole key: it is the **leading portion of the key name**, and S3 partitions the keyspace internally at boundaries it chooses based on observed load. Practically, treat the characters up to the last `/` as the grouping unit, but understand that S3 splits partitions adaptively as traffic grows - so a hot prefix does eventually get split, taking minutes to tens of minutes. Two important corollaries: **the old advice to add a random hash to the start of the key is obsolete** (S3 no longer requires it for performance), and **adaptive splitting is not instant**, so a sudden burst on one prefix can throttle with `503 SlowDown` until it happens.

**Designing keys for a high-throughput pipeline:**

- Put a **naturally high-cardinality, well-distributed component early** in the key: a tenant ID, a device ID, a hash bucket - something the workload spreads across. `s3://bucket/tenant=abc/date=2026-09-01/hour=14/part-0001.parquet` gives both distribution and Hive-style partitioning for Athena.
- **Avoid a monotonic leading component** - a timestamp or a sequential ID at the front concentrates all current writes into one prefix (Q168).
- **Match the query pattern**: analytics wants partition columns in the path in the order you filter on them; a document store wants tenant-first so lifecycle and access policies can be prefix-scoped.
- **Design for `LIST` avoidance**: keys should be *computable* from your metadata (in DynamoDB), so you never enumerate to find an object.
- If a genuine burst on one prefix is unavoidable, **pre-shard** with a small hash bucket (`part=07/...`) and handle `503 SlowDown` with retry and backoff (the SDKs do this by default).

*Hook: a key design you changed for throughput or for query efficiency, and the effect.*

### Q168. Timestamp prefix and a throughput plateau `[T]`

**Cause**: with keys like `s3://bucket/2026/09/01/14/events-000123.json`, every write at any given moment shares the prefix `2026/09/01/14/`. That prefix is a single partition until S3 splits it, so the pipeline is capped at roughly **3500 PUT/s** no matter how many writers you add - and because the hot prefix *moves* every hour, S3's adaptive splitting never gets ahead of the load: each new hour starts on a fresh, unsplit partition. The result is a hard plateau with intermittent `503 SlowDown`, which looks like a client problem and is not.

The same mechanism applies to any monotonic leading component: a sequential ID, an incrementing batch number, or a "latest/" prefix.

**Fixes, best first:**

1. **Reorder the key so a high-cardinality field leads**: `s3://bucket/tenant=<id>/dt=2026-09-01/hour=14/...` or `s3://bucket/shard=<hash(id) % 64>/2026/09/01/...`. Writes now spread across many prefixes permanently, and analytics still gets usable partitions.
2. **Write fewer, larger objects.** Most pipelines with this problem are writing tiny objects at high rate. Buffering into larger files (via **Firehose**, which does exactly this, or an application-side batch) reduces request rate by orders of magnitude, reduces cost (Q170's request charges, and per-object overhead), and produces files that Athena can actually read efficiently. This is frequently the *real* fix, because the underlying problem is object granularity, not S3.
3. **Add a hash bucket to the prefix** if the natural key has low cardinality.
4. **Handle `503 SlowDown` properly** with exponential backoff and jitter as a safety net, and keep the retry visible in metrics so a future plateau is diagnosable.

The lesson to state: **S3's per-prefix limit means the *shape* of your key space is a throughput decision**, and time-ordered keys - the most natural thing to write - are the worst possible shape for write throughput.

*Hook: a pipeline whose key layout or object size you changed, and the throughput or cost change.*

### Q169. Storage classes end to end

| Class | First-byte latency | Minimum duration | Retrieval charge | The case |
| --- | --- | --- | --- | --- |
| **Standard** | ms | none | none | Active data, unpredictable access, anything read frequently |
| **Intelligent-Tiering** | ms (frequent/infrequent tiers); archive tiers add latency | none (but a per-object monitoring charge) | none for the instant tiers | **Unknown or changing access patterns** at scale, with large objects |
| **Standard-IA** | ms | **30 days** | per GB retrieved | Known-infrequent access, but must be instant: backups you might restore, older documents |
| **One Zone-IA** | ms | 30 days | per GB retrieved | Reproducible data only - a derived thumbnail, a re-creatable index. **One AZ**, so an AZ loss is data loss |
| **Glacier Instant Retrieval** | **ms** | 90 days | per GB retrieved (higher) | Archives that must be instantly available: medical images, compliance records users occasionally open |
| **Glacier Flexible Retrieval** | minutes to hours (expedited 1-5 min, standard 3-5 h, bulk 5-12 h) | 90 days | per request and per GB, varies by tier | True archives with a tolerance for waiting: backups, old logs |
| **Glacier Deep Archive** | **hours** (standard 12 h, bulk up to 48 h) | **180 days** | highest | Regulatory retention you expect never to read: 7-year financial records |

The three things that make this answer good rather than a recital:

1. **The minimum duration is a real cost**: deleting or transitioning an object out of Standard-IA before 30 days (or Deep Archive before 180) still bills the remainder. So short-lived data must not be tiered - and lifecycle rules that transition at 30 days then delete at 45 are paying for the storage twice over.
2. **Retrieval cost and latency are the design constraint, not storage price.** Deep Archive is roughly 1/20th of Standard to store, but a full restore is expensive and slow. The question is always "what happens when we *do* need this", and for a 7-year retention with a legal-discovery obligation, "48 hours" may be unacceptable - which pushes you to Glacier Instant despite the higher storage price.
3. **Per-object overhead**: each object in IA and Glacier classes carries a metadata overhead (32-40 KB billed per object for Glacier classes), which is why small objects must not be archived (Q171).

*Hook: a storage-class decision you made where retrieval latency or minimum duration changed the answer.*

### Q170. Does transitioning 50 TB of small objects to Standard-IA save money?

Take **50 TB in 200 million objects** (average 250 KB), currently in Standard, US East, using round figures: Standard ≈ $0.023/GB-month, Standard-IA ≈ $0.0125/GB-month, lifecycle transition ≈ **$0.01 per 1000 objects**.

**Storage saving**: 51,200 GB x ($0.023 - $0.0125) = 51,200 x $0.0105 ≈ **$538/month**.

**Transition cost**: 200,000,000 / 1000 x $0.01 = **$2,000, one time**.

**Payback**: $2,000 / $538 ≈ **3.7 months**. So it saves money *if the data stays for more than about four months*, which for archival data it does. Note the 30-day minimum duration means anything deleted within a month of transition loses money outright.

**Then the charges people forget:**

- **Retrieval**: Standard-IA charges ≈ $0.01/GB retrieved. If 5 percent of the 50 TB is read each month, that is 2560 GB x $0.01 ≈ **$26/month** - small here. But if the access pattern is wrong and 50 percent is read, retrieval alone is $260/month and eats half the saving. **The saving is entirely a bet on the access rate**, so measure it (S3 Storage Class Analysis) before transitioning.
- **Higher per-request GET cost** in IA than Standard, which matters for many small objects.
- **Small-object arithmetic**: objects under 128 KB are **not eligible** for Intelligent-Tiering's automatic transitions and are generally uneconomic to tier at all. At 250 KB average, a meaningful fraction of the 200 million may be below that.

**The conclusion I would give**: yes, marginally - about $538/month saved for a $2,000 one-off, with the caveat that the answer is dominated by the retrieval rate and the object-size distribution. And **the bigger win is probably elsewhere**: 200 million small objects is itself the problem. Compacting them into larger objects (or moving to Glacier Instant if access is genuinely rare) changes the economics far more than a one-class transition, and reduces request costs and `LIST` pain at the same time.

*Hook: a lifecycle policy where you computed the payback, and whether retrieval charges changed your decision.*

### Q171. Intelligent-Tiering on 400 million small objects `[T]`

Because Intelligent-Tiering charges a **per-object monitoring and automation fee** (on the order of $0.0025 per 1000 objects per month), and that fee is **independent of object size**.

400,000,000 / 1000 x $0.0025 = **$1,000/month in monitoring charges alone**, before any storage.

Now the other half: **objects smaller than 128 KB are never transitioned** to the Infrequent Access tier - they stay in the frequent-access tier permanently. So for a corpus of small objects you pay the monitoring fee and receive **none** of the tiering benefit. If the average object is 20 KB, 400 million objects is only 8 TB, whose Standard storage cost is about $184/month - so the monitoring fee is roughly **five times the storage bill it was supposed to reduce**.

The rule that falls out, and it is the useful takeaway: **Intelligent-Tiering pays off for large objects with unpredictable access, and is actively harmful for large numbers of small objects.** A rough break-even is around a few hundred KB per object; below 128 KB it cannot help at all.

**What to do instead** for small objects: compact them (a daily job merging into Parquet/tar/zip, or use Firehose buffering at write time so they are never small - Q168); if compaction is impossible, choose a class explicitly based on measured access (Q170) rather than paying for automation; and consider whether the objects should be *items in DynamoDB* rather than objects in S3 at all - for sub-100 KB records with key-based access, DynamoDB is often cheaper and much faster, and removes the `LIST` and request-cost problems entirely.

*Hook: a storage bill where the per-object overhead dominated, and how you found it in Cost Explorer or the Storage Lens dashboard.*

### Q172. Multipart upload, part sizing and the incomplete-upload leak

**When to use it**: required above **5 GB**; recommended above about **100 MB**. Benefits: parallel part uploads (much higher throughput), retry of an individual failed part rather than the whole object, and the ability to begin uploading before the total size is known (streaming).

**Part sizing**: 5 MB minimum (except the last part), 5 GB maximum, **10,000 parts maximum**. So the part size must be at least `object_size / 10000` - for a 5 TB object that is 512 MB. Practical guidance: **8-16 MB parts for typical uploads over a good network**, larger (64-128 MB) for very large objects to stay under the part count and reduce per-request overhead. Too-small parts mean more requests (cost) and more per-part overhead; too-large parts mean a failed part costs more to retry.

**The cost leak nobody notices**: if a multipart upload is never completed or aborted - the client crashed, the Lambda timed out, the network dropped, the deploy killed the process - **the uploaded parts remain in S3 and you are billed for them**, indefinitely. They are **invisible in `ListObjects`**; they appear only under `ListMultipartUploads`. So a bucket can hold terabytes of orphaned parts that no console view shows and no lifecycle-by-prefix rule touches. I have seen this be a five-figure annual charge with nobody able to account for the storage.

**The fix, which should be on every bucket by default:**

```
Lifecycle rule: AbortIncompleteMultipartUpload after 7 days
```

That is one rule, applies to the whole bucket, costs nothing, and permanently removes the class of problem. Add **S3 Storage Lens** (which reports incomplete multipart upload bytes) or a periodic `ListMultipartUploads` check to verify. And in application code, wrap uploads so a failure calls `AbortMultipartUpload` explicitly rather than relying on the lifecycle rule as the only defence.

*Hook: an unexplained S3 storage cost you traced, and the lifecycle rule you standardized afterwards.*

### Q173. Presigned URLs for upload and download

A **presigned URL** embeds a SigV4 signature over the request the holder is permitted to make, created by a principal who already has that permission. No AWS credentials are needed by the client.

**Expiry**: up to **7 days** for SigV4, but bounded by the **signing credentials' own lifetime** - and this is the trap in serverless: a Lambda's role session is short-lived, so a URL signed with it stops working when the session expires, regardless of the requested expiry. Sign with a longer-lived credential path or keep expiries short (minutes), which you should anyway. Downloads: 5-15 minutes is usually right. Uploads: long enough for a slow client to finish a large file.

**Size limits**: a single `PUT` is capped at **5 GB**. Above that you presign the **multipart** operations (`CreateMultipartUpload` is done server-side, then presign each `UploadPart`, then complete server-side) - which also gives you a natural checkpoint to validate before completing.

**Enforcing content type and key structure** - the substance of the question, because a naive presigned `PUT` lets the client upload anything to that key:

1. **The key is chosen by *you***, not by the client. Generate `uploads/{tenantId}/{uuid}` server-side after authorizing the request. Never sign a client-supplied key, or a client uploads over someone else's object.
2. **Sign the `Content-Type`** as part of the request, so a mismatched upload is rejected by S3's signature check. Same for `Content-Length` where the client can tell you the size, and for `x-amz-server-side-encryption` and object tags.
3. For real enforcement, use **`POST` policy** (presigned POST) rather than presigned `PUT`: a POST policy can express **conditions** - `content-length-range`, a `starts-with` constraint on the key, required metadata, allowed content types. This is the correct mechanism when you need to bound the upload, and it is the answer that distinguishes a candidate who has actually built an upload path.
4. **Never trust the declared content type.** Validate the actual bytes after upload (magic-number sniffing, virus scanning via an S3 event trigger) before promoting the object from a quarantine prefix to its final location. Two-prefix upload-then-promote is the pattern.
5. **Bucket-side backstops**: a bucket policy requiring encryption and TLS, Block Public Access, and a lifecycle rule cleaning the quarantine prefix.

*Hook: an upload path you designed, and how you bounded what a client could put in the bucket.*

### Q174. S3 event notifications: EventBridge, SNS, SQS or Lambda

| Target | Shape | Use when |
| --- | --- | --- |
| **Direct to Lambda** | S3 invokes the function asynchronously | Single consumer, simple processing. Retries follow Lambda's async policy (Q122), so you **must** configure an `OnFailure` destination |
| **SQS** | Message per event, durable, buffered | The default for anything at volume or needing backpressure: the queue absorbs bursts, gives you a DLQ, batching and replay |
| **SNS** | Fanout to several subscribers | Multiple independent consumers, usually with SQS queues behind it (Q105) |
| **EventBridge** | The full event surface on the default bus | **The modern default**: richer filtering (on prefix, suffix, size, object tags), multiple rules and targets without touching the bucket config, cross-account and cross-region delivery, archive and replay, and more event types (including object tag and ACL changes) |

**What delivery guarantee you actually get**: **at-least-once**, and AWS is explicit that notifications are "typically delivered in seconds but can sometimes take a minute or longer". Two consequences to state:

- **Duplicates happen.** The same object-created event can be delivered more than once, so the consumer must be idempotent - keyed on bucket plus key plus **`versionId`** (or the ETag), which is the natural idempotency key here (Q126).
- **Order is not guaranteed.** Two rapid writes to the same key can produce notifications in either order, so a consumer that applies "the latest" must check the version or the object's own metadata rather than trusting arrival order (Q114).
- **Events can be missed** in edge cases (historically, concurrent writes to the same key could yield a single notification; and a misconfiguration or permissions failure loses them silently). For pipelines where completeness is a requirement, the robust pattern is **notifications for latency plus a periodic reconciliation against S3 Inventory** for completeness. Saying that out loud is the senior answer.

Also worth naming: bucket notification configuration is **a single resource per bucket**, so two teams both configuring it will overwrite each other - which is a strong practical argument for EventBridge, where each consumer owns its own rule.

*Hook: an S3-event pipeline where you had to handle duplicates or a missed event, and how you reconciled.*

### Q175. An S3-triggered Lambda writing back to the same bucket `[T]`

**The failure mode is infinite recursion.** The function is triggered by `s3:ObjectCreated:*` on the bucket; it writes its output into the same bucket; that write generates another `ObjectCreated` event; the function runs again. Lambda scales to meet the events, so within minutes you have thousands of concurrent executions, a bill climbing at the rate of your concurrency limit, exhausted account concurrency starving every other function, and a bucket filling with derived objects. It is one of the most expensive mistakes available in serverless, and AWS now ships a **recursive-loop detection** feature that will stop a function after ~16 recursive invocations - which is a safety net, not a design.

**Two ways to prevent it:**

1. **Separate the write destination.** The trigger reads from `input-bucket` and writes to `output-bucket`. Different bucket, no notification, no loop. This is the strongest fix because it is structural - the loop is impossible rather than filtered - and I would make it the standard pattern.
2. **Scope the notification so the output cannot match it.** If one bucket is required, use **prefix and suffix filters**: trigger only on `incoming/` and write to `processed/`, or trigger on `.jpg` and write `.thumb.jpg` while filtering the suffix. With EventBridge you can filter more richly (on prefix, on object tags, on size). The caution: filters are configuration, so a later change to an output path silently re-creates the loop - which is why option 1 is better.

Other defences worth naming as belt-and-braces: **reserved concurrency** as a blast-radius cap so a loop costs bounded money (Q69); an **object tag or metadata marker** on generated objects that the handler checks and exits on (a code-level guard, useful when the paths cannot be separated); a **billing alarm and a concurrency alarm** so you find out in minutes; and CloudWatch's recursive-invocation metric.

*Hook: a recursive invocation you caused or inherited, how quickly it was detected, and what it cost.*

### Q176. A bucket that survives a malicious administrator

The components, and what each one actually defends against:

- **Versioning**: every overwrite and delete creates a new version; a `DELETE` writes a **delete marker** rather than removing data. Defends against: accidental and malicious overwrite/delete by anyone *without* the ability to delete versions. Does not defend against `DeleteObjectVersion` by a privileged principal.
- **MFA Delete**: requires the bucket owner's root credentials plus an MFA code to delete a version or to change the versioning state. Defends against a compromised IAM principal, because the operation cannot be performed by any IAM user or role at all - only by root with MFA. The reason it is rarely used: it can only be enabled by the **root user via the CLI**, and it makes automation and lifecycle expiration of versions awkward.
- **Object Lock in Compliance mode** (requires versioning, and must be enabled at bucket creation or via support): a retention period during which **no one - including the root user and AWS - can delete or overwrite the object version.** *Governance* mode allows override by a principal with `s3:BypassGovernanceRetention`, so it protects against accident, not against an insider. **Compliance mode is the actual answer to "survives a malicious administrator".** Legal Hold is the indefinite variant, removable only with a specific permission.

**The design I would state:**

1. Versioning on, **Object Lock in Compliance mode** with a retention period matching the business requirement, applied by default at the bucket level.
2. The bucket in a **separate AWS account** in a `Security`/`Backup` OU, with an **SCP** denying `s3:PutBucketPolicy`, `s3:DeleteBucket`, `s3:PutBucketVersioning`, `s3:PutObjectRetention` overrides and `s3:BypassGovernanceRetention` to *every* principal in that account. An account boundary plus an SCP is what stops the administrator of the *workload* account.
3. **Replication to a second account/region** with Object Lock also enabled at the destination, so a single account compromise does not reach both copies.
4. **No human write access**: only a pipeline role writes; humans get read-only. CloudTrail data events on the bucket, delivered to a *different* account.
5. **Alarm on the control-plane operations** - any attempt to change versioning, lock configuration, policy or replication - because those attempts are the signal.
6. **Restore rehearsal**: prove you can actually read and restore, on a schedule (Q211). A protected backup you have never restored is an assumption.

The framing worth saying: **you cannot defend against an administrator using permissions inside their own blast radius, so the defence is to put the data outside it** - a different account, with an SCP, and immutability that even root cannot override.

*Hook: a backup or audit bucket you hardened, and which of these controls the security review actually required.*

### Q177. Cross-Region and Same-Region Replication

**What replicates**: new objects (and, with S3 Batch Replication, existing ones), object metadata, tags, ACLs, and - if configured - delete markers. Encryption is preserved, with SSE-KMS requiring key permissions in both regions and a destination key.

**What does not replicate** - the list that matters:

- **Objects that existed before replication was enabled** (unless you run Batch Replication explicitly).
- **Objects created by SSE-C**, and objects encrypted with a KMS key the replication role cannot use.
- **`DELETE` of a specific version** - version deletes are deliberately not replicated, so a targeted delete on the source leaves the destination copy intact. Delete *markers* replicate only if you enable that option.
- **Lifecycle actions**: an object expired by a lifecycle rule on the source is not deleted on the destination. So the destination needs its own lifecycle rules, and forgetting this is a common source of unexplained cost.
- **Objects replicated *into* the source bucket from a third bucket**, unless replica modification sync / multi-destination chaining is configured.
- **Bucket configuration**: policies, notifications, lifecycle rules, CORS. Replication copies data, not configuration - so a failover to the destination bucket does not work until you have provisioned equivalent configuration there (an IaC concern, and an easy DR gap).

**RPO**: replication is **asynchronous**, and the standard SLA is "most objects within 15 minutes". So the honest RPO is **minutes, not zero**, and it is not bounded unless you pay for **S3 Replication Time Control (RTC)**, which provides a 15-minute-99.99-percent SLA plus `OperationsFailedReplication` metrics and replication event notifications. Without RTC you have no contractual bound and no per-object visibility, which for a stated RPO is the difference between a claim and a commitment.

**SRR versus CRR**: same mechanism, different destination region. SRR's cases are log aggregation across accounts, production-to-test data copies, and satisfying a data-residency requirement while still having two independent buckets. CRR's cases are DR and reducing read latency for another region.

*Hook: a replication setup you built, and whether you enabled RTC and monitored replication lag.*

### Q178. S3 Select, Athena and Iceberg / S3 Tables

- **S3 Select** (and the newer object-level filtering in the SDKs) pushes a simple `SELECT ... WHERE` into S3 for a *single object*, returning only matching rows. Cheap, low-latency, no infrastructure - but one object at a time and limited SQL. It is genuinely useful for "read one column from one large CSV/JSON/Parquet file" inside a Lambda, and useless for anything analytical.
- **Athena** is serverless Presto/Trino over a Glue Data Catalog, scanning many objects, billed **per TB scanned**. Good for ad-hoc and scheduled analytics over data lake files.
- **Iceberg tables (including S3 Tables)** add table semantics on top of object storage: schema evolution, hidden partitioning, snapshot isolation, **row-level updates and deletes**, time travel and compaction. S3 Tables is the managed variant with automatic compaction and maintenance.

**When querying in place beats loading into a database:**

- **Data volume is large and query frequency is low.** Loading 50 TB into a warehouse to run three queries a week is absurd; scanning partitioned Parquet with Athena costs a few dollars per query.
- **The data is already in S3 as a by-product** (logs, events, exports), so ETL into a database is pure added cost and latency.
- **Schema is evolving or semi-structured**, and you want to query it before committing to a model - schema-on-read is a real advantage.
- **Retention is long and access is sporadic** - S3 plus lifecycle is far cheaper than warehouse storage.
- **You want multiple engines** on the same data (Athena, EMR, Redshift Spectrum, Managed Flink, a Spark job) without copies.

**When you should load it into a database instead**: interactive latency requirements (sub-second dashboards - use a warehouse or pre-aggregates); high query concurrency (Athena has concurrency limits and per-query cost adds up fast); heavy joins across large tables; frequent row-level updates (Iceberg makes this possible but a database makes it *cheap*); and transactional consistency requirements.

**The engineering that determines whether in-place querying works at all**: columnar format (Parquet/ORC), **partitioning matched to the query predicates**, **file sizes in the 128 MB-1 GB range** (the many-small-files problem is the number-one cause of slow, expensive Athena - Q168), compression, and partition projection or a well-maintained catalog. Iceberg's compaction exists precisely because these are hard to maintain by hand.

*Hook: a query-in-place versus load decision you made, and the file-layout work that made it viable.*

### Q179. S3 data transfer and request pricing on a serving path

Enumerate the charges on a typical path - **client → CloudFront → S3 origin in the same region as nothing else**:

1. **Storage**: per GB-month by class, plus per-object overhead in IA/Glacier classes (Q169).
2. **Requests**: per 1000 `GET`s at the origin, per 1000 `PUT`s on write. Cheap individually and significant for many small objects.
3. **S3 → CloudFront data transfer**: **free**. This is the single most important line to know, and it is why fronting S3 with CloudFront is usually cheaper as well as faster.
4. **CloudFront → internet data transfer out**: charged per GB, at rates that vary by geography, **lower than S3's direct internet egress**, with volume tiers and a free tier. This is normally the dominant cost on a serving path.
5. **CloudFront requests**: per 10,000 HTTP/HTTPS requests, by region. Plus any CloudFront Functions or Lambda@Edge invocations (Q60).
6. **If clients hit S3 directly instead**: S3 **data transfer out to the internet** per GB, higher than CloudFront's, plus per-request charges - so a presigned-URL download path that bypasses CloudFront is more expensive per GB. Worth stating, because it is a real design consequence.
7. **Cross-region**: S3 → another region is charged per GB (both for replication and for a cross-region read), plus the destination's request and storage charges. Replication also charges a per-object replication request, and RTC charges extra (Q177).
8. **Cross-AZ inside a region**: S3 is a regional service, so there is no cross-AZ charge for accessing it from EC2/Lambda in the same region - and access via a **gateway endpoint is free**, whereas access via a **NAT gateway** incurs NAT data-processing charges (Q35). This is the most commonly missed line item.
9. **Management features**: Storage Lens advanced metrics, Inventory, Analytics, replication metrics, Object Lambda, and **Intelligent-Tiering monitoring per object** (Q171).
10. **Retrieval charges** for IA and Glacier classes, plus restore-request charges for Glacier tiers.

The summary sentence: **on a CloudFront-fronted path, the bill is dominated by CloudFront egress and request count, and S3 itself is mostly storage; on a direct-to-S3 path, egress moves to S3 at a higher rate.** Then the optimizations follow naturally: cache ratio and compression (Q58, Q59), object size, and a gateway endpoint for internal access.

*Hook: an S3-related bill you decomposed, and the line item that turned out to dominate.*

### Q180. Transfer Acceleration, Direct Connect and Snowball

**For 200 TB of initial migration: Snowball Edge (or Snowcone/Snowmobile at the extremes).**

The arithmetic is the argument: 200 TB over a **1 Gbps** link at a realistic 80 percent utilization is roughly `200 x 8 x 1000 / (0.8 x 1000) ≈ 2000` hours - about **83 days** - and you would be saturating the link the whole time, which your business will not accept. Over 10 Gbps it is around 8-9 days of full saturation, which is plausible but still consumes the link. A Snowball device is shipped, loaded locally at LAN speed, and returned; several devices in parallel make 200 TB a matter of a couple of weeks end to end with no impact on production connectivity. Add: encryption is built in, and the transfer cost is a flat device fee rather than per-GB egress from your data centre's ISP.

**For a daily 500 GB feed: Direct Connect** (or, if there is already a Direct Connect, simply use it; if there is not and the volume is the only driver, evaluate whether VPN or public internet with Transfer Acceleration suffices).

500 GB/day is about 46 Mbps sustained if spread over 24 hours, or ~140 Mbps if it must land in an 8-hour window - comfortably within a 1 Gbps Direct Connect and within many internet links. The reasons to prefer Direct Connect: **predictable throughput and latency** (a daily feed with an SLA cannot be at the mercy of internet congestion), **lower per-GB data transfer** rates than internet egress, and a private path that usually simplifies the compliance conversation (Q48). The reason it might be overkill: if you have no other need for it, the port hours plus cross-connect fees may exceed the value, and internet upload with retry is fine for a non-latency-sensitive feed.

**Where Transfer Acceleration fits** - and it is worth positioning it correctly because it is often misapplied: it routes uploads over the AWS edge network to the target region, which helps **long-distance, high-latency, single-stream uploads from geographically distributed clients** (mobile users uploading to a bucket on another continent). It does *not* help when the bottleneck is your own link's bandwidth, and it costs a premium per GB. So: good for a global consumer upload path, wrong for a data centre migration.

*Hook: a bulk migration you ran, the mechanism you chose, and how close the estimate was to reality.*

### Q181. Storage for a document-management product `[A]`

**Clarify first**: what is the access distribution over document age (measure it, do not assume)? What does "legal hold" mean contractually - can we ever delete, and who authorizes? Is the 200 ms expectation for the byte stream or for a rendered preview? Are there residency requirements per customer? How large is the average document, and are there many tiny ones? What is the read pattern - direct download, or search-then-open?

**The design:**

**Keys and buckets.** One bucket per region (residency), keys leading with tenant for distribution and prefix-scoped policy: `s3://docs-eu/tenant=<id>/yyyy=2026/mm=09/<docId>/<version>/original.pdf`. Tenant-first gives request-rate distribution (Q167) and lets me scope IAM, lifecycle and replication per tenant. **Metadata lives in DynamoDB**, not in S3 - document ID, tenant, tags, retention class, current version, S3 key, size, checksum, legal-hold flag - so we never `LIST` S3 to find anything, and search/filter is a DynamoDB or OpenSearch query.

**Derived artifacts** (thumbnails, extracted text, rendered previews) go in a **separate bucket** - both to avoid the recursion trap (Q175) and because they are reproducible, so they can live in **One Zone-IA** and be regenerated if lost.

**Storage classes, driven by the 200 ms requirement for recent files:**

| Age / class of document | Class | Reasoning |
| --- | --- | --- |
| 0-90 days, or any document with an active matter | **Standard** | Instant, unpredictable access, frequent reads |
| 90 days - 1 year | **Standard-IA** | Instant retrieval preserves the 200 ms path; ~45 percent cheaper; retrieval charge acceptable at low access rates |
| 1-7 years, normal retention | **Glacier Instant Retrieval** | This is the key choice: **milliseconds** first-byte, so the retrieval-latency expectation still holds for old documents, at a fraction of Standard's price. 90-day minimum is irrelevant at this age |
| 7+ years, retained only for compliance, retrieval expected never | **Glacier Deep Archive**, if and only if the legal-discovery SLA tolerates hours | Cheapest storage; I would confirm the discovery obligation before choosing it, and default to Glacier Instant if unsure |
| Derived thumbnails/previews | **One Zone-IA**, regenerable | Losing an AZ loses nothing irreplaceable |

I would **not** use Intelligent-Tiering as the primary mechanism here: with 300 million objects the monitoring fee is roughly $750/month (Q171), and I have a *known* age-based access pattern, so explicit lifecycle rules are cheaper and predictable. I would use it selectively for a subset where access truly is unpredictable and objects are large.

**Retention, legal hold and immutability:**

- **Versioning on**, so an overwrite or accidental delete is recoverable.
- **Object Lock in Compliance mode** with a 7-year default retention on the ingest path - this is what makes the retention obligation defensible, and it means even an administrator cannot delete (Q176).
- **Legal Hold** applied per object for documents under active litigation, removable only by a principal with `s3:PutObjectLegalHold`, with CloudTrail data events and an alarm on every hold change. Critically: **a legal hold must suspend the lifecycle expiration**, so the lifecycle rule expires only objects whose DynamoDB record says no hold - which means the deletion job is application-driven, not purely a bucket lifecycle rule. That interaction is the part that is usually got wrong.
- **Deletion after 7 years** is an explicit, audited, application-driven process with a report, not a silent lifecycle expiry - because "we can prove we deleted it" is usually as much of a requirement as the deletion itself.

**Cost hygiene**: `AbortIncompleteMultipartUpload` after 7 days on every bucket (Q172); a lifecycle rule expiring **non-current versions** after N days (otherwise versioning quietly doubles storage - a very common leak); Storage Lens for per-prefix visibility and per-tenant reporting; and S3 Inventory as the reconciliation source against DynamoDB (Q174).

**Durability and DR**: Standard/IA/Glacier are already multi-AZ. For DR I would add **CRR to a second region with Object Lock at the destination** for the compliance-critical corpus only - replicating 300 million objects wholesale doubles storage cost, so this is a business decision about which documents warrant it, and I would present it that way. Remember replication does not copy bucket configuration or lifecycle rules, so the destination needs its own IaC (Q177).

**The honest trade-offs I would state**: the 200 ms expectation for "recent" files is easy, and the reason I chose Glacier *Instant* over Flexible for the 1-7 year band is precisely so that an occasional old-document read does not become a four-hour ticket - that costs more in storage and buys a much better product. And with 300 million objects, **object count, not bytes, drives several costs** (request charges, monitoring fees, inventory, `LIST` behaviour), which is the non-obvious point I would want the interviewer to hear.

*Hook: a document or media store you designed, the lifecycle policy you chose, and a cost or retrieval-latency surprise you had to correct.*

---

## 12. Observability on AWS

### Q182. The CloudWatch surface and what each part costs

| Component | For | Cost shape |
| --- | --- | --- |
| **Metrics** | Numeric time series, 1-minute (or 1-second high-resolution) granularity, 15-month retention with automatic rollup | Free for AWS-service metrics; **per custom metric per month** (a metric = a unique name plus dimension combination), plus per-API-request for `PutMetricData` and for `GetMetricData` |
| **Logs** | Raw text and structured events, queryable | **Per GB ingested** (the dominant charge, by a wide margin), plus per GB-month stored, plus **per GB scanned** by Logs Insights |
| **Alarms** | Threshold, anomaly-detection and composite evaluation with actions | Per alarm per month; anomaly-detection and composite alarms cost more |
| **Dashboards** | Visualization | Per dashboard per month above a small free tier, plus the `GetMetricData` calls each load makes |
| **Logs Insights** | Ad-hoc query over log groups | **Per GB of data scanned per query** - so a broad query over a large group is genuinely expensive |
| **Container Insights / Application Signals / Lambda Insights** | Curated infrastructure and application telemetry | Effectively priced as the custom metrics and logs they generate, which is a lot - this is where surprise bills come from |

The two facts to lead with because they drive every design decision: **log ingestion is priced per GB and is usually the largest observability line item**, and **a custom metric is billed per unique dimension combination**, which makes cardinality a direct cost (Q186). Everything in this category follows from those two.

*Hook: an observability bill you decomposed, and which of these lines dominated.*

### Q183. The Lambda metrics that matter

The alarm set I configure for every production function:

1. **`Errors`** (as a *rate* against `Invocations`, via metric math, not an absolute count) - the baseline.
2. **`Throttles`** - **greater than zero should alarm.** A throttle means requests were rejected or events delayed, and it is the metric that tells you concurrency or a reserved limit is binding (Q68, Q72).
3. **`Duration`** p99 against the timeout - not the average. An alarm at, say, 80 percent of the configured timeout catches creeping latency *before* it becomes a timeout error.
4. **`ConcurrentExecutions`** against the limit, so you see headroom shrinking rather than discovering it at the throttle.
5. **`DeadLetterErrors`** / **`DestinationDeliveryFailures`** - these mean the failure-handling path *itself* failed, so events are being lost with no record. Almost nobody alarms on them.
6. **`IteratorAge`** for stream-driven functions - the single most important metric for a Kinesis or DynamoDB Streams consumer (Q121).
7. **Queue-side companions** for SQS-driven functions: `ApproximateAgeOfOldestMessage` and DLQ depth (Q124).
8. Business-level: a **success/failure count per business operation** emitted via EMF, because "the function did not error" is not "the order was placed".

**The one most teams fail to alarm on: `Throttles`** - and the reason is that it is zero for months and then non-zero exactly when it matters. A close second is **`ConcurrentExecutions` headroom**, which is the leading indicator for the same problem. And a third that deserves mention: **`AsyncEventsDropped`/`DeadLetterErrors`**, because a silent async discard (Q122) is invisible in `Errors`.

*Hook: an alarm you added after an incident, and what it caught later.*

### Q184. Normal `Duration` and `Errors`, but users report slowness `[T]`

**The metric that tells the truth is the *client-observed* latency, and inside AWS the closest proxies are `IteratorAge`/queue age for async paths and `Latency` versus `IntegrationLatency` at API Gateway for synchronous ones.** But the specific thing missing from the default Lambda dashboard is that **`Duration` measures only the billed execution of the handler** - it excludes:

- **`InitDuration`** (cold start), which is reported separately in the `REPORT` line and is *not* part of `Duration`. So a function with 300 ms `Duration` and a 4-second init on 5 percent of invocations has a p95 the dashboard never shows.
- **Time spent queued or throttled before invocation** - a throttled synchronous request waited and then failed or was retried by the client, and the successful retry's `Duration` looks fine.
- **Everything else in the path**: API Gateway overhead, an authorizer invocation (Q55), CloudFront, DNS, TLS, the client's network.

So the honest answer has two parts. **Diagnostically**: compare API Gateway's `Latency` (total, client-facing) against `IntegrationLatency` (time in the backend) - the gap is the gateway plus authorizer, and Lambda's `Duration` inside `IntegrationLatency` shows whether the function or the platform is responsible. Then look at cold-start rate (`InitDuration` occurrences over invocations) and at percentile `Duration` rather than average.

**Why it is not on the default dashboard**: CloudWatch's automatic Lambda dashboard shows **average** duration, and averages hide bimodal distributions completely - which is exactly the shape a cold-start problem has. Percentiles must be requested explicitly, `InitDuration` requires a metric filter or Lambda Insights to graph, and true client latency requires RUM or your own instrumentation. The generalizable point: **AWS's default metrics measure AWS's part of the request, and the user's experience is the sum of parts nobody's default dashboard adds up.**

*Hook: a latency complaint you diagnosed where the service metrics looked healthy, and the signal that finally showed it.*

### Q185. Embedded Metric Format

**Mechanism**: you write a specially structured JSON object to **stdout** (so, to CloudWatch Logs), containing an `_aws` block with a `CloudWatchMetrics` section naming the namespace, dimensions and metric definitions, alongside arbitrary properties. CloudWatch Logs recognizes the format and **extracts the metrics asynchronously**, so they appear as real CloudWatch metrics with alarms and dashboards - while the full log event, including the high-cardinality properties you did not turn into dimensions, remains queryable in Logs Insights.

**Why it is cheaper than `PutMetricData` per invocation:**

1. **No synchronous API call.** `PutMetricData` is a network round trip inside your billed duration - typically 20-80 ms, on every invocation. At 50 million invocations that is real GB-seconds you are paying for, plus latency added to the user's request. EMF costs a `printf`.
2. **No per-request API charge.** `PutMetricData` is billed per request (batched up to 1000 metrics, but a Lambda usually cannot batch across invocations because it has no shutdown hook - Q80). EMF's cost is the log ingestion you were largely paying for anyway.
3. **No failure mode on the critical path.** A throttled or failed `PutMetricData` either loses the metric or, worse, fails the invocation if the code does not guard it.
4. **Cardinality without cost.** You can attach `orderId`, `tenantId` and `requestId` as *properties* (queryable in logs, free of metric cardinality) while emitting only low-cardinality *dimensions* as metrics - which is precisely the separation that Q186 says you need.

The trade-off to state: metrics arrive with a short extraction delay, and you are now paying log ingestion for the metric payload, so verbose EMF at very high volume has its own cost. Use the **Lambda Powertools metrics utility**, which builds EMF correctly, flushes once per invocation, and enforces the dimension limits.

*Hook: a metrics implementation you moved to EMF, and the duration or cost change.*

### Q186. Custom metrics cost and cardinality

**A CloudWatch custom metric is a unique combination of namespace, metric name and dimension values.** Each unique combination is billed per month (with the price stepping down at volume). So cardinality is multiplicative:

`OrderLatency` with dimensions `Service` (5 values) x `Environment` (3) x `Operation` (10) = **150 metrics**. Acceptable.

Add `CustomerId` with 10,000 values and it becomes **1,500,000 metrics**. At roughly $0.30 per metric per month at the first tier, that is a **five- to six-figure monthly bill from one dimension**, and the metrics are individually useless because most have a handful of datapoints. This is the single most expensive mistake available in CloudWatch, and it is the AWS analogue of the Prometheus `user_id` label problem in `07-devops`.

Second-order effects beyond the bill: dashboards and `GetMetricData` calls get slower and are themselves billed per metric requested; alarms cannot practically be created per combination; and the metric namespace becomes unusable for humans.

**The rules I apply:**

- **Dimensions are for things you would alarm or page on**; anything else belongs in the log event as a property (Q185) or in a trace annotation.
- **Bound every dimension's cardinality explicitly** and know the number. Anything unbounded - user ID, order ID, request ID, path with IDs in it, error message text - is forbidden as a dimension.
- **Normalize before emitting**: bucket latencies, collapse status codes to classes, template URL paths (`/orders/{id}`).
- **If per-customer visibility is genuinely required** - and sometimes it is, for a top-tier tenant SLA - do it deliberately: emit metrics for an explicit allow-list of high-value tenants (tens, not thousands), and serve everything else from Logs Insights queries or an analytics pipeline over the raw events (Q197).
- **Review the metric count** as a cost control; Cost Explorer's CloudWatch line broken out by usage type shows it.

*Hook: a cardinality problem you caught, what it was going to cost, and the alternative you built for the per-entity view.*

### Q187. Structured logging and correlation

**What belongs in every log line**, as JSON, not prose:

- `timestamp`, `level`, `message`
- `service`, `version` (or the deployed SHA/image digest), `environment`
- **`requestId`** - the Lambda request ID, from the context
- **`correlationId` / `traceId`** - the identifier that spans the *whole* user request across services, propagated in from the caller
- `functionName`, `coldStart` (a boolean - so you can filter latency by cold versus warm, which is how you answer Q184)
- Business identifiers as *properties*: `tenantId`, `orderId` - deliberately not metric dimensions (Q186)
- `durationMs` for outbound calls, and the operation name
- On errors: the exception type, message and stack, as structured fields

**How correlation works across API Gateway, Lambda and DynamoDB:**

1. **API Gateway** generates a request ID and, with tracing enabled, an **X-Ray trace ID** which it passes in the `X-Amzn-Trace-Id` header. Enable access logging with a format that includes `$context.requestId`, `$context.xrayTraceId` and, if you inject one, your own correlation header.
2. **Lambda** receives the trace header in the environment (`_X_AMZN_TRACE_ID`) and the API Gateway request ID in the event's `requestContext`. Log both, plus the Lambda request ID, on the first line of every invocation. If the caller supplied its own correlation ID (a header your clients set), prefer that as the primary key and log the AWS ones alongside.
3. **Outbound calls** must propagate it: the X-Ray SDK or ADOT instrumentation adds the trace header to SDK and HTTP calls automatically; for asynchronous hops you must **carry the correlation ID in the message body or in message attributes** yourself, because SQS, SNS, EventBridge and DynamoDB Streams do not carry your headers. This is the step people miss, and it is why traces break at the queue.
4. **DynamoDB** does not log your correlation ID, so correlation on that hop is via the X-Ray subsegment (which records the table and operation) rather than via the service's own logs.

Then a single Logs Insights query filtered on `correlationId` across all the services' log groups reconstructs the request. **Lambda Powertools' logger** does most of this for you, including automatic `coldStart` and correlation-ID injection from a configurable source - and using it is the right answer rather than hand-rolling.

*Hook: a cross-service investigation that correlation made possible, or the asynchronous hop where you had to add propagation manually.*

### Q188. CloudWatch Logs pricing and three ways teams overspend

The charges: **ingestion per GB** (the big one), **storage per GB-month** (much cheaper, and compressed), and **Logs Insights per GB scanned per query**. Plus per-GB charges for delivery to S3/Firehose if you export.

**Three ways teams spend more on logs than on compute:**

1. **`DEBUG` level in production, or logging the whole request and response.** A function logging a 4 KB event plus a 4 KB response at 50 million invocations a month is 400 GB - which at typical ingestion pricing is several times the Lambda cost for a short function. Frameworks make this worse: Spring's default startup logging, SQL statement logging, and the AWS SDK's request/response logging each multiply the volume. **This is the number-one cause.**
2. **Container/Lambda Insights or an agent left on everything.** Enhanced monitoring produces a continuous stream of high-cardinality performance events per resource. Enabled by default across a large estate, it can dwarf application logs - and because it arrives as "AWS telemetry" nobody thinks of it as their logging bill.
3. **Infinite retention on every log group.** Log groups default to *never expire*, so storage grows forever, and every Logs Insights query then scans years of data (per-GB-scanned charges) making investigation slow and expensive too. A close relative: **duplicate shipping** - logs going to CloudWatch *and* to a third-party SIEM/APM, so you pay ingestion twice.

Honourable mentions worth naming: `print`-in-a-loop inside a batch handler (one log line per record x millions of records); stack traces logged at multiple layers as an exception propagates; access logs at full verbosity on a high-traffic API; and Step Functions Express `ALL`-level logging (Q134).

**What I do about it**: `INFO` in production with sampled `DEBUG` (Powertools supports a sampling rate); never log payloads, log identifiers; **set retention on every log group by policy** (an account-level default plus a Config rule, since the default is never); use **metric filters or EMF** so dashboards read metrics rather than scanning logs; ship to S3 via Firehose for long retention and query with Athena at a fraction of the per-GB cost; and put a **budget alarm on the CloudWatch cost line** specifically, because it grows silently with traffic.

*Hook: a logging bill you cut, the mechanism, and the percentage.*

### Q189. The log pipeline for a 60-function estate

**Design:**

1. **One log group per function** (the default), with a **naming convention** and an **account-level default retention** applied at creation. Retention set by class: 7 days for dev, 30 days for production application logs, 90 days for audit-relevant logs (and those go to the compliance path below).
2. **Structured JSON logs** from every function via a shared logger (Powertools), so downstream processing never parses text (Q187).
3. **Metric extraction at the source**: EMF for business and performance metrics (Q185), plus a small number of **metric filters** on log groups for things you cannot control at the source (a specific error string in a vendor library). Dashboards and alarms read metrics, not logs - this is what keeps Logs Insights costs down.
4. **A subscription filter per log group** (or, better, an **account-level subscription filter**, which is exactly the feature that makes this manageable at 60 functions) delivering to a **Kinesis Data Firehose** stream.
5. **Firehose fans out**: to **S3** in Parquet, partitioned by date and service, for long retention and Athena querying; and to the **SIEM/APM** if there is one. Firehose handles buffering, compression and retry, and its per-GB cost plus S3 storage is far below CloudWatch's storage-plus-scan cost for data you keep for a year.
6. **S3 lifecycle** on the log bucket: Standard for 30 days, Standard-IA to 1 year, Glacier Instant beyond, expire per the retention policy (Q169).
7. **Query tiering**: Logs Insights for the last 30 days (fast, interactive, per-GB-scanned but the volume is bounded); **Athena over S3** for anything older or wider. Naming and partitioning are what make the Athena path cheap.
8. **Governance**: a Config rule (or a pipeline check) asserting that every log group has a retention policy and a subscription filter, because the failure mode of this design is a new function whose log group was created implicitly by Lambda with no retention (Q188).

**What I would explicitly *not* do**: enable Lambda Insights on all 60 (enable it on the handful being investigated); log request/response payloads; or create a per-function dashboard by hand - a single dashboard driven by metric math across the estate, plus per-function drill-down, scales and 60 hand-built dashboards do not.

*Hook: a log pipeline you built, the CloudWatch-to-S3 split you chose, and what it saved.*

### Q190. X-Ray sampling, segments, and its blind spots

**Sampling rules**: a reservoir (a fixed number of traces per second sampled regardless) plus a fixed **rate** for everything above it, configurable centrally by service name, HTTP method and URL path. The default is 1 request/second plus 5 percent. Sampling decisions are made at the entry point and **propagated** in the trace header, so the whole request is either traced or not - which is what makes a trace coherent.

**Segments and subsegments**: a **segment** is the work done by one service (the API Gateway segment, the Lambda segment - actually two, one for the service and one for the function). **Subsegments** are the finer-grained units inside it: an SDK call to DynamoDB, an HTTP call to a third party, a manually instrumented block of code. Annotations (indexed, filterable) and metadata (not indexed) attach to them, and this is where correlation IDs and business keys belong.

**What X-Ray cannot see in an event-driven system** - the important part:

- **Asynchronous hops break the trace unless the context is propagated.** X-Ray propagates through SNS→SQS→Lambda and EventBridge for many paths now, but **your own message-based hops** (a payload passed through DynamoDB Streams, a custom protocol, a message written and later read by an unrelated consumer) do not carry the trace header unless you put it there. So the classic result is two disconnected traces per business transaction.
- **Time spent waiting in a queue** is not a span. The trace shows the producer and, separately, the consumer; the hours a message sat in a backlog appear nowhere. Queue age is a *metric* problem, not a trace one (Q117).
- **Un-instrumented services**: anything without the SDK/ADOT (a third-party API, a legacy service, a database's internal work) is a black hole - you see the client-side duration and nothing about where it went (Q191).
- **Sampled-out requests**, which is by definition most of them - so X-Ray is a tool for understanding *typical* and *sampled-anomalous* behaviour, not for investigating one specific customer's failed request. That is what structured logs with a correlation ID are for.
- **Cold starts** appear as init subsegments, but the *queueing* before invocation does not.

The framing to give: **traces explain structure and latency attribution; metrics explain rates and saturation; logs explain individual cases.** X-Ray is strong on the first and weak on the third, and knowing which question you are asking is what makes the toolchain usable.

*Hook: a trace-based investigation that worked, and an async gap you had to instrument manually.*

### Q191. A 900 ms gap with no subsegment `[T]`

Three explanations, and I would name what distinguishes them:

1. **Un-instrumented work.** A call made with a client the X-Ray SDK does not patch (a raw `HttpURLConnection`, a JDBC driver without the interceptor, a native library, a gRPC client), or pure CPU work in your own code with no manual subsegment. The gap is real work you cannot see. *Distinguisher*: it reproduces consistently at the same point in the code. *Fix*: add a manual subsegment or use ADOT's auto-instrumentation.
2. **A cold start or runtime-level delay that is not attributed to a subsegment** - initialization work, class loading, JIT, a connection pool warming, or a SnapStart restore. Also: time spent **before** the handler in the runtime, and time waiting for a VPC ENI or credential refresh. *Distinguisher*: it correlates with the `coldStart` flag or with the first invocations of a new environment.
3. **Blocking on a resource, not on a call**: GC pause, thread-pool starvation waiting for a worker, a lock, or CPU throttling because the memory setting gives a fraction of a vCPU (Q75). The function is *not executing* rather than waiting on I/O, so nothing emits a span. *Distinguisher*: it correlates with concurrency or with memory configuration, and shows up in GC logs or as a duration distribution that worsens under load.

Two more worth mentioning: **an asynchronous continuation** whose subsegment was closed on a different thread (so the timing is misattributed rather than missing), and a **downstream that is instrumented but whose trace is not linked** - so the work happened elsewhere and the gap is your client waiting.

The general method: reproduce with a manual subsegment bracketing the suspect region, check the `coldStart` correlation, then check whether the gap scales with concurrency (resource contention) or is constant (un-instrumented call).

*Hook: a trace gap you chased down, and which of these it turned out to be.*

### Q192. ADOT and OpenTelemetry versus native X-Ray

**ADOT** is AWS's supported distribution of the OpenTelemetry Collector and SDKs, available as a Lambda layer, an ECS/EKS sidecar or a daemon, exporting to X-Ray, CloudWatch, Prometheus, or a third-party backend.

**What you gain:**

1. **Vendor neutrality and one instrumentation API.** The same OTel instrumentation serves X-Ray, Datadog, Grafana Tempo or Honeycomb by changing an exporter - which matters because observability backends get replaced and instrumentation should not.
2. **A far richer ecosystem** of auto-instrumentation, especially for the JVM: the OTel Java agent instruments a very long list of libraries with no code change, where the X-Ray SDK covers a narrower set (Q191's blind spots shrink).
3. **Metrics and logs, not just traces** - a single pipeline for all three signals, with the Collector doing filtering, batching, tail sampling, redaction and enrichment *before* egress. Tail-based sampling in particular is something X-Ray's head-based sampling cannot do, and it is the correct way to "keep all the slow and failed traces".
4. **Consistency with a non-AWS estate**, which for a multi-cloud or hybrid organization is decisive.

**What the Collector costs you on Lambda**, and this is the honest half:

- **Cold start**: the Collector extension adds meaningful init time (historically hundreds of milliseconds to over a second, better with the reduced-footprint distributions). For a latency-sensitive function that is a real regression.
- **Memory and CPU** inside your billed environment - the extension shares the function's resources, so it can push you to a higher memory setting.
- **Duration**: if the exporter flushes synchronously at the end of the invocation, you pay that in billed duration; asynchronous flushing risks losing spans when the environment freezes (Q80), which is why the extension model matters.
- **Complexity**: a Collector configuration file per deployment, another component to version and debug, and failure modes ("why are traces missing") that are yours rather than AWS's.

**My position**: for a Lambda-heavy, AWS-only estate where X-Ray is adequate, native X-Ray with Powertools is the lower-overhead choice. Adopt ADOT when you have a non-AWS backend, a hybrid estate, JVM services where auto-instrumentation coverage matters, or a need for tail sampling - and on **containers rather than Lambda first**, because the sidecar model carries none of the cold-start cost.

*Hook: an OTel or ADOT adoption you led, and the overhead you measured on Lambda versus containers.*

### Q193. The alarm set for an API-plus-queue-plus-worker path

**Alarm types**: **static thresholds** (a number you know), **anomaly detection** (a learned band, for metrics with a strong daily/weekly shape and no meaningful absolute threshold), **composite alarms** (boolean combinations, to suppress noise and express "the service is broken" rather than "a metric moved"), and **metric math** (to build rates and ratios, which is what most good alarms actually are).

**The set:**

*Entry (API Gateway):*
- `5XXError / Count` **rate** > 1 percent for 2 of 3 datapoints - metric math, not the raw count, so it works at any traffic level.
- `4XXError` rate anomaly detection - a spike in 4xx usually means a client or auth regression, and the normal level is workload-specific.
- `Latency` p99 > SLO, and `IntegrationLatency` p99 separately, so you can tell gateway from backend (Q184).
- `Count` **dropping to near zero** via anomaly detection - the alarm that catches "everything is broken upstream", which threshold alarms structurally cannot.

*Queue (SQS):*
- **`ApproximateAgeOfOldestMessage` > SLO** - the primary alarm. Depth is a poor signal (a big backlog draining fast is fine); age is the actual "are we behind" metric.
- `ApproximateNumberOfMessagesVisible` growth rate, as a secondary.
- **DLQ `ApproximateNumberOfMessagesVisible` > 0** with a real page (Q124).

*Worker (Lambda):*
- `Errors / Invocations` rate.
- **`Throttles` > 0** (Q183).
- `Duration` p99 above 80 percent of the timeout.
- `ConcurrentExecutions` above 80 percent of the applicable limit.

*Downstream:*
- DynamoDB `ThrottledRequests` / `SystemErrors`, per table and per index (Q152).
- For a relational store: connection count and CPU.

**Then compose.** A single downstream failure otherwise fires eight alarms and pages four people. So:

- A **composite alarm** `OrdersAPI-Unhealthy = (5xx rate high) OR (p99 latency high AND traffic normal)` is what pages; the individual alarms feed dashboards and the incident channel.
- A **suppressor**: `OrdersAPI-Unhealthy` suppressed when `Dependency-Down` is in alarm, so the page names the cause rather than the symptom.
- **Ticket-not-page** for the slow-burn signals (rising DLQ trickle, cost anomaly, gradual latency creep).

The principle worth stating: **alarm on symptoms the user feels (error rate, latency, age) and on saturation that predicts them (concurrency, throttles, queue age); use composite alarms to make one failure produce one page.**

*Hook: an alarm set you rationalized, and the reduction in pages.*

### Q194. SLOs for a serverless application

**What you measure when there is no host**: the same things as anywhere else - the *service's* behaviour, not the infrastructure's. Serverless actually makes this cleaner, because there is no CPU or disk metric to be distracted by. Concretely:

- **Availability SLI** = successful requests / valid requests, where "successful" excludes 5xx and *includes* correct 4xx (a client's bad request is not your outage). Source: API Gateway metrics, or better, structured logs where you can define validity precisely.
- **Latency SLI** = the proportion of requests faster than a threshold (e.g. 95 percent under 300 ms), not "p95 latency" - a threshold-based ratio composes with error budgets arithmetically and a percentile does not.
- **Freshness / lag SLI** for asynchronous paths = the proportion of events processed within N seconds of arrival. Source: message age or `IteratorAge`, or an application-emitted `now - event.occurredAt`. This is the serverless-specific one and it is the SLI most teams are missing.
- **Correctness SLI** where it matters: reconciliation mismatches per day (Q131).

**Where the SLI boundary goes** - the substantive part of the question. Put it **at the boundary you promise to the consumer and can measure**:

- For a public API: at the **edge** (CloudFront or API Gateway), because that includes the gateway, the authorizer and the throttling - all of which the user experiences and none of which appear in Lambda's metrics. Measuring at Lambda excuses you from your own entry tier's failures.
- Ideally, add **client-side RUM** as a second, non-authoritative signal, because DNS, TLS and the last mile are real and invisible to you.
- For an internal asynchronous pipeline: at the **point where the event becomes visible to the consumer** (the materialized view is updated), not at "the function returned successfully" - which is the difference between measuring your work and measuring the outcome.
- Do **not** set separate SLOs per function. An SLO belongs to a **user journey**, and a journey spans several functions; per-function SLOs produce a wall of numbers nobody can act on.

Then the usual machinery: error budget from the target, **multi-window burn-rate alerts** rather than raw threshold alarms, and the budget as the input to the release-versus-reliability conversation (`07-devops` Category 12 has the arithmetic).

*Hook: an SLO you defined for an event-driven path, and where you chose to put the measurement boundary.*

### Q195. Synthetics, Application Signals, Service Lens

- **CloudWatch Synthetics** (canaries): scripted Puppeteer/Selenium checks running on a schedule from AWS, with screenshots, HAR files and a heartbeat metric. **Earns its place**, and it is the most underrated item here. It is the only signal that tells you the whole path works - DNS, certificate, CDN, gateway, auth, function, database - *when there is no traffic*. Every production API should have at least a heartbeat canary and one critical-journey canary, plus an **API canary on the login flow**, because an expired certificate or a broken DNS record produces zero errors in your service metrics.
- **Application Signals** auto-discovers services and gives you request rate, latency, error rate and SLO tracking with a service map, built on ADOT-style instrumentation. **Earns its place conditionally**: it is a genuinely good "you get SLOs and a service map without building them" product, and for a team without observability engineering capacity it is a big step up. The catch is cost - it produces a lot of metrics and traces - and that it is opinionated about what a service is, so a heavily event-driven estate maps onto it imperfectly. I would enable it on the customer-facing synchronous tier and not blanket-enable it.
- **Service Lens / ServiceMap** (the older X-Ray-plus-CloudWatch view) is largely superseded by Application Signals. As a stand-alone thing to invest in, no.

**What I use instead** for the gaps: **EMF-emitted business and latency metrics** (Q185) rather than an auto-discovery product, because the metrics that matter are business-specific (orders placed, events processed, reconciliation gaps); **structured logs plus correlation IDs** (Q187) for individual-request investigation, which no service map gives you; **explicit dashboards per user journey** rather than per resource; and **burn-rate alarms on SLIs I defined** (Q194) rather than on vendor-defined health.

The one-line summary: **canaries yes, always; Application Signals selectively and with a cost eye; Service Lens no; and the highest-value observability work is still defining the right SLIs and emitting business metrics cheaply.**

*Hook: a canary that caught something your service metrics could not.*

### Q196. The alarm fired 40 minutes after the outage began `[T]`

Three mechanisms inside CloudWatch, all of which compound:

1. **Metric publication delay.** AWS-service metrics are aggregated and published on a schedule - standard resolution is **1-minute periods**, and some services publish at 5-minute intervals, with additional lag before the datapoint is available to alarms (often 1-3 minutes, more for some services). So the first datapoint reflecting the outage does not exist for several minutes after it starts.
2. **Period plus evaluation periods plus datapoints-to-alarm.** An alarm configured as `period = 5 minutes, evaluationPeriods = 3, datapointsToAlarm = 3` requires **15 minutes of breach** before it transitions. Combine with (1) and you are already near 20 minutes. This is the biggest single contributor and it is pure configuration.
3. **`TreatMissingData` and low traffic.** If the outage causes *no* datapoints (requests stopped entirely, or the function is not invoked), and the alarm treats missing data as `notBreaching` or `missing` (the default is `missing`, which retains state), the alarm **never fires** until data returns. An outage that stops traffic is invisible to a threshold alarm on error *rate*, because the denominator is zero. This is the subtle one and the reason "alarm on traffic dropping" (Q193) exists.

Plus the delivery chain: alarm → SNS → pager integration adds seconds to a minute, and a notification aggregation window in the paging tool can add several more.

**How I fix it**: use **1-minute periods** with `evaluationPeriods = 2, datapointsToAlarm = 2` for fast-burn conditions (roughly a 2-3 minute detection floor); add a **multi-window burn-rate** pair so a severe burn pages in minutes while a slow burn tickets in hours; set **`TreatMissingData: breaching`** for heartbeat-style alarms and add an explicit **low-traffic anomaly alarm**; use **canaries** (Q195) so detection does not depend on customer traffic existing; and measure **time-to-detect** as a postmortem metric so the alarm configuration itself is reviewed rather than assumed.

*Hook: a detection delay you measured after an incident, and the alarm configuration change that reduced it.*

### Q197. Observability for a 60-function estate on $5,000/month `[A]`

**Clarify first**: what is the invocation volume and average payload size (that sets the log-volume floor)? What are the regulatory retention requirements for logs? Is there an existing APM contract? What are the user journeys we are actually promising something about? And what is the current spend, broken down - because the answer usually starts by removing something rather than adding.

**The budget allocation I would propose:**

| Category | Allocation | What it buys |
| --- | --- | --- |
| Logs ingestion (CloudWatch, 30-day tier) | ~$2,000 | ~4 TB/month at typical rates - the dominant line, and the one to manage hardest |
| Long-term logs (Firehose + S3 + Athena) | ~$400 | 12-month retention at a small fraction of CloudWatch storage, queryable |
| Custom metrics (EMF-derived) | ~$900 | ~2,000-3,000 bounded-cardinality metrics - enough for per-function and per-journey dashboards |
| Alarms | ~$300 | ~1,000 alarms including composites |
| X-Ray / traces | ~$500 | Sampled tracing on the synchronous tier |
| Canaries | ~$300 | ~20-30 canaries at 5-minute intervals on critical journeys |
| Dashboards + query headroom | ~$300 | A per-journey dashboard set plus Logs Insights investigation budget |
| Reserve | ~$300 | Incident-time query and trace bursts, which is a real and spiky cost |

**The design decisions that make it fit:**

1. **Structured JSON logs at `INFO`, no payloads, identifiers only**, with sampled `DEBUG` at 1-5 percent (Powertools). This alone is usually a 5-10x reduction from the naive baseline (Q188).
2. **EMF for all metrics** (Q185) - no `PutMetricData`, no metric per customer. Dimensions are `service`, `operation`, `environment`, `outcome`; everything high-cardinality is a log property.
3. **Retention policy enforced at creation**: 30 days in CloudWatch, everything shipped to S3 via an **account-level subscription filter** for the year (Q189). Investigation older than 30 days happens in Athena.
4. **SLOs on ~8 user journeys**, not 60 functions (Q194), with burn-rate alarms; per-function alarms limited to the mechanical set of Q183 (errors, throttles, duration, DLQ, iterator age).
5. **Tracing sampled at 5 percent on the synchronous tier only**, with 100 percent on error paths where the SDK supports it. No tracing on the highest-volume asynchronous functions.
6. **Canaries on the journeys, not on every endpoint.**

**What I deliberately do not collect**, and I would say this explicitly because it is the point of the question:

- **Request and response payloads.** The single biggest cost, and identifiers plus a targeted DEBUG sample recover most of the value.
- **Per-customer or per-tenant metrics** (Q186). Per-tenant views come from Athena over the S3 logs, on demand, or from an allow-list of the top 20 tenants.
- **Lambda Insights / Container Insights across the estate.** Enabled temporarily, per function, during an investigation.
- **100 percent tracing.** Sampling is sufficient for latency attribution; individual-request forensics comes from logs plus correlation IDs.
- **Debug logging in production by default**, and verbose SDK/SQL logging anywhere.
- **Infinite CloudWatch retention.**
- **A second telemetry pipeline** to a third-party APM in parallel with CloudWatch - pick one primary and export, do not double-ingest.

**How I would govern it**: a monthly review of the CloudWatch cost line broken down by usage type (ingestion, metrics, alarms, Insights); a per-service log-volume metric published as part of the estate dashboard so a team can see their own contribution; and a check in the pipeline that fails a deploy adding a metric with an unbounded dimension. **And I would state the trade-off honestly**: at this budget we have excellent aggregate visibility and good sampled forensics, and if someone asks "what exactly happened to customer X's request three months ago" the answer is an Athena query taking minutes, not a dashboard. That is the right trade at this budget, and it should be a documented decision rather than a surprise during an incident.

*Hook: an observability budget you had to fit, what you removed first, and the visibility you knowingly gave up.*

---

## 13. Reliability, quotas and failure modes

### Q198. Ten quotas that break serverless applications

| Quota | Default (typical) | Adjustable? |
| --- | --- | --- |
| **Lambda concurrent executions** (per account per region) | 1,000 | **Yes** - and the first one to raise before a launch |
| **Lambda function/layer storage** (per account per region) | 75 GB | Yes |
| **Lambda payload** - 6 MB synchronous, 256 KB asynchronous | fixed | **No** - a design constraint |
| **Lambda timeout** 15 minutes, `/tmp` 10 GB, memory 10 GB | fixed | **No** |
| **API Gateway account-level throttle** | 10,000 rps, 5,000 burst | Yes |
| **API Gateway integration timeout** | 29 seconds | Largely **no** - design around it (Q57) |
| **DynamoDB per-partition throughput** | 3,000 RCU / 1,000 WCU | **No** - physics (Q153) |
| **DynamoDB table-level throughput / on-demand peak** | high but real; on-demand scales to 2x previous peak | Yes (table limits) |
| **Kinesis shard throughput** | 1 MB/s or 1,000 rec/s in, 2 MB/s out | **No** per shard; add shards |
| **Step Functions payload** 256 KB, history 25,000 events | fixed | **No** (Q142) |
| **SQS in-flight messages** | 120,000 standard / 20,000 FIFO | **No** |
| **VPC / subnet IP addresses, ENIs** | per your CIDR | Design-time (Q34) |
| **CloudFormation resources per stack** | 500 | Effectively no - split stacks (Q234) |
| **STS / IAM**: roles per account, policy size, session duration | various | Partly |
| **SES sending quota, Cognito rates, KMS request rates** | various | Yes, with lead time |

The framing that matters more than the list: **the adjustable ones require a support request with lead time, so they must be raised *before* the launch, not during it** - and the non-adjustable ones (payload sizes, timeouts, per-partition throughput) are **architectural constraints** that must appear in the design review. I keep a per-service quota sheet with current value, current usage and the alarm on utilization, and **Service Quotas supports CloudWatch alarms on utilization**, which is the mechanism to use rather than a spreadsheet review.

*Hook: a quota that shaped a design or caused an incident, and how you found out.*

### Q199. Every retry in a CloudFront → API Gateway → Lambda → DynamoDB path

| Hop | Retry behaviour | Keep or remove |
| --- | --- | --- |
| **Client → CloudFront** | The client's own retry (browser, mobile SDK, or a service's HTTP client). Often 3 attempts with no jitter | **Bound it.** Retry only idempotent methods, with jitter and a budget |
| **CloudFront → origin** | CloudFront retries an origin connection failure and, with an **origin group**, fails over on configured status codes | Keep - it is a connection-level retry and cheap. Be aware failover retries the request |
| **API Gateway → integration** | REST APIs historically retried a failed Lambda integration once; treat any gateway-level retry as a duplicate risk. No configurable retry on HTTP APIs | Cannot control - design for idempotency |
| **Lambda service (async only)** | 2 retries on function error, plus up to 6 hours on throttles (Q122) | Keep, but configure `MaximumRetryAttempts` and an `OnFailure` destination |
| **Event source mapping (if async)** | Retries until success, `maxReceiveCount`, or the stream settings (Q120) | Keep, bounded |
| **AWS SDK inside the function → DynamoDB** | **The big one**: standard retry mode is 3 attempts (adaptive can be more) with exponential backoff and jitter, on throttles and 5xx | Keep, but **cap `maxAttempts` and set aggressive timeouts** |
| **DynamoDB internal** | Transparent | n/a |
| **Any HTTP client to a third party inside the function** | Whatever the library defaults to - often silent retries on POST | **Remove or restrict**, then reintroduce deliberately |
| **Step Functions (if orchestrated)** | `Retry` blocks per task (Q139) | Keep, with jitter and classification |

**What I would turn off, specifically**: the client's blind retry on non-idempotent writes; any HTTP-library retry the team did not consciously configure; and the SDK's retries *layered under* a Step Functions retry (choose one place to retry per hop). **What I keep**: connection-level retries at the edge, SDK retries against AWS services with a low `maxAttempts`, and exactly one application-level retry policy per logical hop.

The multiplication is the point: 3 (client) x 2 (gateway) x 3 (SDK) is **18 attempts** for one user action - which is Q200.

*Hook: a retry layer you removed, and the reduction in downstream load during a subsequent incident.*

### Q200. 30x amplification from a downstream slowdown `[T]`

**The mechanism, multiplicatively:** a downstream slows down (not fails - slows). Then:

1. The **SDK inside the function** retries 3 times with backoff. But because the downstream is *slow* rather than erroring, each attempt also consumes the full timeout, so the function's duration multiplies too.
2. The function eventually times out or errors, so the **caller** - API Gateway to a client, or Lambda's async retry - retries. Say 2-3 attempts.
3. The **client** (browser, mobile app, or an upstream service) sees a slow or failed request and retries 3 times.

3 x 3 x 3 = **27**, and each attempt arrives while the previous ones are still in flight because nobody cancelled anything. So the struggling downstream now receives roughly 30x its normal request rate at exactly the moment it has least capacity - and the extra load ensures it never recovers. This is a **metastable failure**: the retries, not the original cause, are now sustaining the outage, so removing the original trigger does not fix it.

Two aggravating factors worth naming: **duration amplification** - Lambda concurrency requirement is `rate x duration` (Q67), so a 10x slower downstream needs 10x the concurrency, which exhausts the limit and starts throttling *unrelated* functions in the account; and **synchronized retries** - without jitter, all retries land in the same instant, producing a pulsed load pattern that is worse than a steady one.

**The two controls that stop it:**

1. **A retry budget with a circuit breaker.** Retry only while the aggregate failure rate is low - a token-bucket retry budget (the AWS SDK's **adaptive retry mode** implements client-side rate limiting for exactly this), plus a circuit breaker that stops calling the downstream entirely after a failure threshold and fails fast instead (Q204). The essential property is that **the total retry load is bounded as a fraction of the primary load**, rather than being a per-request multiplier.
2. **Retry at exactly one layer, with exponential backoff and full jitter.** Pick the layer closest to the failure that can make a correct decision (usually the SDK/service client), and make every other layer fail fast without retrying. Combined with **timeout budgets** (Q201) so an inner attempt cannot outlive the outer deadline, this collapses 27 attempts into 3.

Supporting measures: **load shedding** at the entry tier so the queue of doomed requests does not build; **`maximumConcurrency`** on async paths so the drain rate is bounded (Q129); and **`Retry-After`** semantics honoured by clients.

*Hook: a retry-amplification incident you diagnosed, and which control you added first.*

### Q201. Timeout budgets across the same path

Set from the outside in, so that each layer's timeout is **shorter than its caller's remaining budget**. With a 3-second user-facing SLO:

| Hop | Timeout | Justification |
| --- | --- | --- |
| Client → CloudFront | **5 s** total including its own retries | The user's patience budget; anything longer should show a failure, not a spinner |
| CloudFront origin read | **10 s** (configurable up to 60+) but effectively capped by the gateway | CloudFront must not be the binding constraint |
| API Gateway integration | **3 s**, explicitly - not the 29 s default | The gateway should return the failure while the client still cares. Leaving it at 29 s means a broken backend holds connections and the user waits half a minute |
| Lambda function timeout | **2.5 s** | Below the gateway's, so the function's own error handling and logging run rather than being cut off by the gateway. Set from the p99 plus margin, **never** left at a large default |
| SDK call to DynamoDB | **200 ms** connect, **500 ms** request, `maxAttempts = 3` | 3 x 500 ms = 1.5 s worst case, leaving room inside the function's 2.5 s for the rest of the work |
| Third-party HTTP call | **800 ms**, 1 retry | Bounded so it cannot consume the whole budget; if it does not answer in 800 ms, degrade (Q205) |

**The rules that make this a budget rather than a list of numbers:**

1. **Every timeout must be strictly less than its caller's remaining budget.** Sum the inner retries: `attempts x (timeout + backoff)` must fit.
2. **Propagate the deadline**, not just the timeout - pass the absolute deadline in the event or header and have each layer compute its own remaining budget. Lambda's `context.getRemainingTimeInMillis()` is exactly this and is badly underused: a handler should check it before starting a long call and fail fast rather than being killed mid-flight.
3. **Set every timeout explicitly.** The defaults are wrong: the AWS SDK's older defaults were tens of seconds, Lambda's console default is 3 seconds (too short for some, and often raised to 900 "temporarily"), and the gateway's 29 seconds is a ceiling, not a target.
4. **A timeout must be longer than the p99 of the healthy path**, or you are turning slow into broken; and shorter than the point at which the user has given up, or you are burning capacity on requests nobody wants.

*Hook: a timeout you set explicitly that turned a cascading failure into a clean degradation.*

### Q202. SDK retry modes

- **`legacy`** - the old defaults, longer and less consistent; avoid.
- **`standard`** - a consistent policy across SDKs: **3 total attempts** by default, exponential backoff with jitter, a defined set of retryable errors (throttling, transient 5xx, connection errors), and a **client-side retry quota** so a client that keeps failing stops retrying as aggressively (retries consume tokens from a bucket that refills on success).
- **`adaptive`** - standard, plus a **client-side rate limiter** that measures throttling responses and *slows the request rate itself* (not just retries), backing off proactively to find the service's sustainable rate.

**`maxAttempts`** is total attempts including the first, so `maxAttempts = 3` is one call plus two retries.

**Adaptive mode's client-side throttling**, and its trade-off: it maintains a token bucket sized by observed capacity; when throttling responses arrive it reduces the allowed send rate, and it increases it slowly on success. The benefit is that a fleet using adaptive mode collectively stops hammering a throttled resource - it is the SDK-level version of the retry budget in Q200. The **caveat AWS itself gives**: adaptive mode assumes the client is talking to a resource whose capacity it can infer, and it can *reduce throughput unnecessarily* when the throttling is caused by a different, unrelated caller sharing the resource, or when the workload is bursty by design. It also makes latency less predictable, because the SDK may delay a request before sending it.

**My practice**: `standard` mode with an explicit low `maxAttempts` (2-3) and explicit connect/request timeouts as the default; `adaptive` for **batch and background workloads** hitting a shared, throttle-prone resource (a bulk DynamoDB loader, a large S3 crawl), where finding the sustainable rate is exactly what you want; and **never** rely on SDK retries alone for a user-facing path - pair them with a circuit breaker and a deadline (Q201, Q204).

*Hook: a retry-mode change you made for a batch workload, and its effect on throttling.*

### Q203. What a 429 means from each service

| Service | Meaning | Correct client response |
| --- | --- | --- |
| **API Gateway** (`429 Too Many Requests`) | You exceeded a **stage, method or usage-plan throttle** (or the account-level rps/burst). The request never reached your backend | **Honour it.** Exponential backoff with jitter, and surface it to the user as "slow down" rather than "error". If it is legitimate traffic growth, raise the throttle or the account quota. Never retry immediately - the token bucket needs time to refill |
| **Lambda** (`429`, `TooManyRequestsException`, `Reason: ConcurrencyLimitExceeded`) | **No concurrency available** - account limit, reserved concurrency, or the burst/scaling rate (Q71, Q72) | Backoff and retry for synchronous callers; for async and event sources, let the platform handle it but **alarm** (Q183). The fix is capacity (raise the limit), duration (reduce it), or buffering (queue in front) - not more retries |
| **DynamoDB** (`ProvisionedThroughputExceededException`, `ThrottlingException`, or `RequestLimitExceeded`) | A **partition** or table exceeded its capacity, or an index did (Q151, Q152). Often a hot key rather than a global capacity problem | The SDK already retries with backoff - let it, with a low `maxAttempts`. Then **diagnose the key distribution** rather than raising capacity blindly. For bulk writes, use adaptive retry mode and a rate limiter |
| **Kinesis** (`ProvisionedThroughputExceededException`) | A **shard's** write or read limit was exceeded - so almost always a partition-key distribution problem or under-sharding (Q111) | Retry with backoff for the write; then reshard or fix the partition key. On the read side, use enhanced fan-out rather than adding consumers to a shared 2 MB/s |

**The unifying answer**: a 429 always means "the *resource* is at a limit", and the correct response is always **backoff with jitter plus a bounded number of attempts** - never a tight retry, never an unbounded one. But the *fix* differs by layer: for API Gateway it is a quota or a business decision about who gets capacity; for Lambda it is concurrency or duration; for DynamoDB and Kinesis it is almost always **key distribution**, and treating it as a capacity problem is how you end up paying for 5x the throughput you need while one partition is still hot.

*Hook: a 429 you diagnosed, and whether the fix was capacity or key design.*

### Q204. Circuit breakers when every invocation is stateless

The problem: a circuit breaker needs to remember recent failures, and a Lambda execution environment is neither shared nor durable. In-process state gives you *per-environment* breakers - which is not useless (a warm environment handling many requests will trip its own breaker) but is unreliable, because at high concurrency each new environment starts with a closed breaker and sends fresh traffic at the broken downstream.

**Where the state goes, in order of practicality:**

1. **DynamoDB**, single item per downstream: `{ pk: "cb#payments-api", state: "OPEN", openedAt, failureCount, successCount }`. Update with `ADD` for counters (atomic, Q156) and a conditional write to flip state. Read it at the start of the invocation (an eventually consistent read is 0.5 RCU, sub-millisecond with DAX if needed) and cache it in the execution environment for a few seconds so you are not reading per invocation. **This is the standard answer**: durable, shared, cheap, and the read cost is negligible with a short local TTL.
2. **ElastiCache/Redis** if the function is already in a VPC with a cluster - lower latency, native atomic counters and TTLs, and the natural home if you are also doing rate limiting there. The cost is the VPC attachment (Q40).
3. **Hybrid, and what I would actually build**: a per-environment in-memory breaker for immediate local protection (it costs nothing and reacts instantly), backed by a shared DynamoDB state read on a 5-10 second cache so that a *newly created* environment inherits the fleet's knowledge instead of probing a dead downstream. This gets the latency of local state and the correctness of shared state.
4. **Step Functions as the breaker**: a `Choice` state reading a DynamoDB flag before the risky task, so the workflow takes the degraded path without invoking anything (Q147). Clean when the call is already orchestrated.
5. **Move the breaker out of the function entirely**: put the unreliable dependency behind a **queue** so failures become backlog rather than errors, or behind an **API Gateway/proxy tier** where throttling and caching absorb it. Often the best answer, because it removes the need for distributed breaker state.

Two things I would add: **half-open probing needs a single prober**, so use a conditional write to elect one invocation to test the downstream rather than letting a thousand environments probe simultaneously; and **AWS App Config or a feature flag** is the manual version of the same thing - an operator-tripped breaker, which during an incident is often faster and more trustworthy than an automatic one.

*Hook: a circuit breaker you implemented in a serverless system, and where you stored the state.*

### Q205. Three levels of degradation for a product page

Product page backed by: catalog (name, price, images), inventory (in stock), reviews, recommendations, personalization (the user's cart and pricing tier).

**Level 1 - Full.** All five services respond. Live stock count, personalized price, recommendations, reviews with current ratings.

**Level 2 - Degraded, invisible to most users.** Non-essential services fail or are slow, and we substitute:

- **Recommendations** fail → show a cached/static "popular in this category" list, or omit the section entirely. Nobody notices.
- **Reviews** fail → show the cached aggregate rating (from the last successful fetch, stored in DynamoDB or the CDN) and hide the review list with no error message.
- **Personalization** fails → show list price and a generic experience; the cart badge falls back to a client-side count.
- **Inventory** slow → show "in stock" from a cached value with a short TTL, and re-validate at add-to-cart.

The mechanism: **per-dependency timeouts well below the page budget** (Q201), a **circuit breaker** per dependency (Q204), and a **fallback value for every non-critical call** - which is a design rule, not an exception handler: every call site must have a defined answer for "what do we render if this fails".

**Level 3 - Minimal, honest.** Catalog itself is impaired:

- Serve the **CDN-cached page** (stale-while-revalidate, or CloudFront's origin-failover to a static S3 copy) - a stale product page is vastly better than an error page, and for a catalog it is usually acceptable for minutes.
- If there is no cached copy: a static page with the product name and "we are having trouble loading details, please try again", **still with a working navigation and search**, and critically **still allowing add-to-cart if inventory can be validated later** - because the business would rather take the order and reconcile than lose it.
- **Read-only mode**: disable write paths that depend on the broken system rather than letting them fail after the user has typed.

**The cross-cutting rules I would state:**

- **Classify every dependency as critical or non-critical up front**, and enforce that non-critical ones can never fail the page. This is the single most valuable piece of the design.
- **Fail fast, do not fail slow**: a dependency at its timeout is worse than one that errors immediately, so timeouts must be tight.
- **Shed load rather than queue it** at the entry tier when saturated, so degraded service is served to everyone rather than perfect service to a few and timeouts to the rest.
- **Make the level observable**: emit a metric per degradation event so "we served 12 percent of pages without recommendations for 20 minutes" is a known fact, not a mystery.
- **Test the fallbacks** - a fallback path that has never run is a hypothesis (Q212).

*Hook: a degradation design you built, and a real incident where a fallback path saved the page.*

### Q206. A single AZ degrades rather than fails `[T]`

This is harder than a clean failure, because health checks pass intermittently and automation hesitates.

| Component | Behaviour under AZ degradation |
| --- | --- |
| **ALB** | Handles it **reasonably**: zonal target health checks remove failing targets, and **zonal shift** (via ARC) or cross-zone load balancing routes around it. But: if targets are *slow* rather than failing, health checks may pass and the ALB keeps sending traffic. And the ALB's own node in that AZ is reachable via DNS, so clients that resolved to it get degraded service until DNS and health checks converge |
| **Lambda** | Handles it **well and automatically** - the service places execution environments across AZs and shifts away from an impaired one. This is a genuine benefit of serverless and worth stating. Exception: a **VPC-attached** function whose subnets include the bad AZ can see ENI/networking problems there, and Hyperplane capacity in that AZ (Q41) |
| **DynamoDB / S3 / SQS / EventBridge** | Handle it **transparently** - regional services with internal multi-AZ replication. You will not notice |
| **Aurora** | **Mostly**: storage is 6-way across 3 AZs, so data is safe. But if the **writer instance** is in the degraded AZ, you see elevated latency without a failover trigger - the instance is alive, just slow. This is the classic "gray failure" and it often requires a **manual failover** decision. Readers in that AZ serve slow reads via the reader endpoint, which round-robins blindly |
| **ElastiCache** | **Gets worse**: a degraded primary node produces slow responses rather than a failover; Multi-AZ with automatic failover only triggers on failure detection. Clients with a node list may keep hitting the bad node, and a Redis cluster's slot ownership makes partial degradation particularly visible |
| **NAT gateway** | **Gets worse** if you have one per AZ and *that* AZ's is degraded: traffic in that AZ's route table degrades with no automatic failover (a NAT gateway is zonal, Q13). If you have a *single* NAT in the bad AZ, all egress degrades |
| **EC2/ECS on EC2** | Instances in the AZ are slow; the ASG will not replace them because they are not unhealthy. `EBS` latency in a degraded AZ is a common form of this |
| **Kinesis, MSK** | Kinesis is transparent; MSK brokers in the AZ produce partition leadership problems and elevated produce latency |

**The general lesson**: **fully managed regional services absorb AZ degradation; anything zonal that you placed yourself does not.** So the design responses are: prefer regional managed services; place zonal resources in all AZs with independent per-AZ paths; and, critically, **have a mechanism to remove an AZ deliberately** - Route 53 ARC **zonal shift**/zonal autoshift for ALB and other supported resources, plus a runbook for manually draining an AZ (deregistering targets, failing over Aurora, removing subnets from a Lambda's configuration). Gray failure is where automation is weakest, so the human lever must exist and must have been rehearsed.

*Hook: a gray AZ failure you experienced, what did not self-heal, and the manual action that fixed it.*

### Q207. An Aurora failover, second by second

Assume a Multi-AZ Aurora cluster with one writer and one reader, and a writer failure:

- **t = 0** - the writer instance fails (host failure, or a manual failover, or a patch).
- **t ≈ 0-5 s** - Aurora's monitoring detects the failure. Application connections to the writer are **already broken**; in-flight transactions are lost and clients see connection resets or hangs.
- **t ≈ 5-15 s** - Aurora **promotes** the highest-priority reader. Because storage is shared and distributed, there is **no data copy and no log replay of the volume** - promotion is a metadata operation, which is why Aurora failover is much faster than RDS Multi-AZ. The promoted instance does recover any in-flight redo and may briefly be unavailable.
- **t ≈ 10-30 s** - the **cluster endpoint's DNS record is updated** to the new writer. The record has a short TTL (~5 s).
- **t ≈ 30-60 s** - clients that respect DNS TTL reconnect and resume. Clients that **cache DNS** (the JVM's default `networkaddress.cache.ttl` being the classic offender) keep resolving the old address; they either connect to a demoted instance and receive **"cannot execute INSERT in a read-only transaction"** errors, or fail to connect at all - and this state persists until the cache expires, which can be indefinite.
- **Afterwards** - the old writer is repaired or replaced and rejoins as a reader. The buffer pool of the new writer is cold-ish, so latency is elevated for a period; a survivable-cache-warming feature mitigates but does not eliminate this.

**What the application sees**, summarized: a 10-40 second window of connection errors and read-only errors, lost in-flight transactions, and then elevated latency. **Not** a transparent event.

**What the application must therefore do**: retry on connection and read-only errors with backoff; keep transactions short; set the JVM DNS TTL to a few seconds; use **RDS Proxy** (Q162), which holds client connections and re-points them, cutting perceived downtime substantially; use the **reader endpoint** for reads so read traffic is less affected; and monitor `FailoverEvents` plus post-failover latency. If the application cannot tolerate 30 seconds of write errors, the answer is a queue in front of the write path, not a faster database.

*Hook: an Aurora failover you observed, the measured recovery time, and the client-side setting that mattered most.*

### Q208. Backup and restore: RPO and realistic RTO

| Mechanism | RPO | Realistic RTO | Notes |
| --- | --- | --- | --- |
| **DynamoDB PITR** | ~**5 minutes** (continuous, 35-day window) | **Hours** for a large table - restore creates a **new table**, then you must repoint the application or copy data back | The RTO surprise: you cannot restore in place, and restore time scales with table size. Also restores **without** indexes' warm state and with default settings |
| **DynamoDB on-demand backup** | Point of backup | Hours, same new-table mechanic | Good for pre-migration snapshots and long retention (beyond PITR's 35 days) |
| **RDS/Aurora automated backups + transaction logs** | ~**5 minutes** (PITR to any second in the retention window) | **Tens of minutes to hours** - a new cluster is provisioned, then DNS/config change, then cache is cold | Aurora's backtrack (MySQL-compatible) rewinds *in place* in minutes for a limited window - much better RTO for a logical corruption |
| **RDS/Aurora snapshots** | Point of snapshot | Similar to above | Cross-region snapshot copy adds transfer time to a DR restore |
| **S3 versioning** | **Zero** for overwrite/delete of versioned objects | **Minutes** for a few objects; **hours to days** for millions (requires listing versions and copying - S3 Batch Operations helps) | The RTO is dominated by object count, not bytes |
| **S3 replication (CRR/SRR)** | **Minutes**, 15-minute SLA only with RTC (Q177) | Near-zero if you can repoint reads; but bucket configuration does not replicate | It is a *copy*, not a backup - a delete can propagate |
| **AWS Backup** | Per plan (as good as the underlying service) | Per service, plus orchestration | Its real value is **central policy, cross-account/cross-region copies, and a vault with immutability (Vault Lock)** - which is the protection against Q176's malicious administrator |

**The three things I would insist on saying:**

1. **RPO is a configuration; RTO is a measurement.** Everyone knows their RPO because it is a setting. Almost nobody knows their RTO, because it requires actually restoring - and the answer is usually several times the estimate.
2. **A restore that produces a new resource is not a recovery** until the application points at it, which means the RTO includes a config change, a deploy, DNS propagation, cache warming, and the decision-making time before any of that starts. Include the human latency in the number.
3. **Replication is not backup.** CRR, global tables and read replicas all faithfully replicate a corruption or a delete. You need a point-in-time capability *and* an immutable copy in a separate account.

*Hook: a restore you actually performed, the measured RTO, and how it compared to the documented target.*

### Q209. PITR enabled and 2 percent of items corrupted over four hours `[T]`

**Walk through the recovery:**

1. **Stop the bleeding**: disable the bad code path (feature flag or roll back the deploy) and, if writes are still corrupting, consider throttling or disabling the writer. Establish the exact corruption window from the deploy time and the logs.
2. **Determine the blast radius**: which items, which attributes, and is the corruption identifiable? Query or scan for the signature (a null where a value should be, a wrong tenant ID, a mis-scaled number). If the corruption is *not* identifiable from the data, this becomes much harder and the stream/logs are your only source of truth.
3. **Restore PITR to a new table** at a timestamp just before the deploy. This gives you a clean copy of *everything* as of that moment, in a new table - which takes hours for a large table.
4. **Reconcile, do not swap.** This is the crux.

**Why PITR alone is not enough:**

- **The restore is a full-table snapshot at one instant, but the corruption was interleaved with four hours of *legitimate* writes.** Swapping to the restored table would discard every valid change made in those four hours - orders placed, payments recorded, profiles updated. So you cannot simply repoint the application; you must **merge**: take the corrupted 2 percent of items from the restored table and write them over the live table, leaving the other 98 percent (and all valid changes) alone. That requires being able to *identify* the affected items, which the restore does not tell you.
- **Later valid writes to a corrupted item are lost either way.** If an item was corrupted at 10:00 and legitimately updated at 12:00, restoring it to its 09:59 state discards the 12:00 update. Resolving that needs the **change stream** (DynamoDB Streams within 24 hours, or Kinesis with longer retention - Q157), replayed with the corrupting transformation excluded. If you did not retain a stream, that information does not exist.
- **PITR restores to a new table with default settings** - no auto scaling configuration, indexes rebuilt, TTL and stream settings to reapply, tags missing - so the operational RTO is longer than the restore time, and a naive swap loses configuration too (Q208).
- **Referential consequences**: derived stores (search index, analytics, a downstream service's cache) consumed the corrupt data and must also be repaired, which the table restore does nothing about.

**What makes this recoverable in practice**, and what I would put in place afterwards: a **long-retention change stream to S3** (so any window can be reconstructed and replayed), **application-level validation on write** so impossible values are rejected at the boundary, **an immutable daily export to S3** for a coarse but reliable second copy, and **a rehearsed partial-restore runbook with the merge script written in advance** - because writing a reconciliation script during the incident is where the hours actually go.

*Hook: a data-corruption incident you recovered from, and what you needed that PITR did not give you.*

### Q210. DR patterns with RTO, RPO and cost

| Pattern | RTO | RPO | Cost band (relative to primary) | What it is |
| --- | --- | --- | --- | --- |
| **Backup and restore** | Hours to days | Hours (last backup) | **~5-10 percent** - storage only | Backups copied cross-region; infrastructure created on demand from IaC |
| **Pilot light** | Tens of minutes to hours | Minutes (continuous replication) | **~15-25 percent** | Data replicated and always live (global tables, Aurora Global Database, S3 CRR); compute defined but scaled to zero or minimal |
| **Warm standby** | Minutes | Seconds to minutes | **~30-60 percent** | A scaled-down but *running* full stack in the second region, taking no traffic (or a trickle); scale up on failover |
| **Active-active (multi-site)** | Near zero | Near zero to seconds | **>100 percent** (plus complexity) | Both regions serving; failover is traffic shifting (Q222) |

**What I actually recommend most often: pilot light for serverless workloads, warm standby for anything with long start-up or stateful tiers.**

The reasoning, and this is the part worth defending: **serverless changes the economics of DR dramatically**. Lambda, API Gateway, DynamoDB, S3, EventBridge and Step Functions all cost approximately nothing when idle, so "deploying the whole stack to a second region" is a pilot light that costs little more than the data replication - the compute layer is free until invoked. That means the *pilot light* for a serverless application has close to warm-standby RTO, because there is no fleet to scale up: you replicate data with global tables and CRR, deploy the identical stack via the same pipeline, and failover is a Route 53 change plus whatever cache warming matters. That is a genuinely better cost/RTO point than containers get, and it is one of the strongest practical arguments for serverless.

Where I move up to **warm standby**: a relational database (Aurora Global Database's secondary is a running cluster you pay for), containers or EKS (a cluster and node baseline must exist, and cold-starting a cluster during a disaster is not credible), anything with long warm-up (caches, search indexes, JIT-sensitive services), and anything whose failover has never been tested - because an untested pilot light is really backup-and-restore with optimistic paperwork.

Where I push back on **active-active**: unless there is a write-consistency story you can defend (Q216, Q222) and a business case for the cost and complexity, active-active often *reduces* availability by adding failure modes - split brain, replication conflicts, doubled deployment risk (Q227). I would rather have a well-rehearsed warm standby than an active-active nobody understands (Q229).

*Hook: a DR posture you chose, the cost you justified, and the RTO you actually measured in a drill.*

### Q211. Testing DR without a maintenance window

**The design principle: make failover a routine, reversible, partial operation rather than a big-bang exercise.** Then testing it does not need a window because it is not disruptive.

**The drill ladder**, each rung testable in production:

1. **Restore verification, continuously.** An automated job restores the latest backup into a scratch environment, runs schema and row-count checks plus a handful of business-invariant queries, publishes a metric, and tears down. This proves the backup is *restorable*, which is the assumption that fails most often. Zero production impact.
2. **Read-path failover.** Shift a small percentage of *read* traffic to the standby region via Route 53 weights or a feature flag, verify correctness and latency, shift back. Non-destructive, and it exercises the standby's data freshness, its IAM, its endpoints and its scaling - the things that are actually broken.
3. **Component-level failover in production.** Aurora failover (a supported, single-command operation), a zonal shift to remove one AZ, a Lambda alias shift, a NAT/route failover. Each is small, reversible and rehearses a real runbook step. AZ-level shifts are now a supported product feature precisely so this is routine.
4. **Dependency injection with FIS** (Q212): inject latency or errors into a dependency and verify degradation (Q205) rather than collapse.
5. **Full regional failover, on a schedule.** Shift 100 percent of traffic to the standby region during a low-traffic window and **run there for a period - ideally days**. This is the only test that finds the asymmetries of Q223, and the ambitious version is to alternate the primary region every quarter so both are always proven.
6. **Game day** with the runbook, an unfamiliar operator and a stopwatch.

**What I measure**, because "the drill succeeded" is not a result:

- **Time to detect**, time to decide, time to execute, time to verify - separately. The decision time is usually the largest and the least discussed.
- **Measured RTO** against the target, and **measured RPO** (how much data was actually behind at the moment of shift - check the replication lag metric, do not assume).
- **The number of manual steps** and how many were undocumented or wrong.
- **What did not come back** - a scheduled job, a queue consumer, a third-party webhook registration, a certificate.
- **Error budget consumed** during the drill, so the cost is explicit.

And the organizational point: **schedule it, staff it, and publish the results including the failures.** A DR capability that is not exercised on a calendar decays silently, and the decay is invisible until the day it matters.

*Hook: a DR drill you ran, the measured RTO versus the target, and the thing that did not come back.*

### Q212. Five FIS experiments for a serverless estate

**AWS Fault Injection Service** runs controlled experiments with a stop condition (a CloudWatch alarm that aborts the experiment automatically), which is what makes this safe enough to run in production.

1. **Lambda function errors and added latency** (via the FIS Lambda actions / an injected extension): make a percentage of invocations of a *non-critical* dependency fail or take 5 extra seconds. **Verifies**: that the caller's timeout is tight (Q201), that the circuit breaker trips (Q204), and that the page degrades rather than fails (Q205). This is the highest-value experiment for a serverless system.
2. **Throttle a downstream API** - inject `ThrottlingException` on DynamoDB or API calls via the FIS API-error action. **Verifies**: retry configuration and jitter, that retries do not amplify (Q200), that the SDK's `maxAttempts` is bounded, and that throttle alarms fire and are attributable.
3. **Squeeze Lambda concurrency** - set reserved concurrency low, or use FIS's Lambda invocation-error injection, to force throttling. **Verifies**: what actually happens on a throttle for each invocation type (Q72) - that async events land in a destination rather than being discarded, that SQS messages are retained rather than dead-lettered, and that the `Throttles` alarm pages.
4. **Remove an Availability Zone** - a zonal shift / network-disruption action against subnets. **Verifies**: that no zonal single point of failure exists (a single NAT gateway, a single-AZ ElastiCache, an Aurora writer with no failover target), and that VPC-attached functions still have addresses and Hyperplane capacity in the remaining AZs (Q41, Q206).
5. **Stall a stream or queue consumer** - disable an event source mapping, or inject failures so a Kinesis shard blocks. **Verifies**: that `IteratorAge`/message-age alarms fire quickly (Q121), that the error-handling settings bound the damage (Q120), and that the downstream degradation is visible rather than silent.

Two more I would add given the chance: **expire a secret or credential** to verify rotation handling and that a stale cached secret does not persist (Q74, Q241); and **break the third-party dependency entirely** (block egress, or point at a black-hole endpoint) to verify the manual breaker and the business fallback.

The discipline that makes any of this worthwhile: **state a hypothesis first** ("if the recommendations service returns errors for 10 percent of requests, page latency p99 rises by less than 50 ms and no user-visible error occurs"), define the **stop condition** as an alarm, run it in **pre-production then production**, and record the result. An experiment without a hypothesis is just an outage you scheduled.

*Hook: a chaos experiment you ran on a production system, the hypothesis, and what it disproved.*

### Q213. A regional control-plane outage with a healthy data plane `[T]`

**What breaks**: anything that requires an API call to change or create state.

- **You cannot deploy.** CloudFormation, CodePipeline, `UpdateFunctionCode`, ECS service updates, `kubectl apply` against the EKS control plane - all are control-plane operations.
- **You cannot scale (some things).** Launching EC2 instances, ECS tasks or EKS nodes requires the control plane. Lambda's data plane scaling is more resilient than most, but creating *new* execution environments has historically been affected in severe events.
- **You cannot fail over, in the ways that need an API call**: promoting an Aurora replica, changing Route 53 records (Route 53's control plane is homed in `us-east-1`), updating an ALB's targets, changing a security group, rotating a secret.
- **You cannot mitigate**: no quota increase, possibly no console or IAM changes, and the AWS support system itself may be degraded.
- **Autoscaling stops adapting**, so a traffic change during the event cannot be absorbed.
- Meanwhile **existing traffic keeps flowing** - EC2 instances keep serving, Lambda keeps invoking warm environments, DynamoDB keeps reading and writing, S3 keeps serving objects. Which is why this is so disorienting: the dashboards are green and you are paralyzed.

**What you prepare in advance:**

1. **Static stability.** Design so that the normal operating state requires no control-plane calls: pre-provision capacity for the peak you might need rather than relying on scaling during an event; run N+1 across AZs so losing one needs no action; keep the standby region's stack **already deployed** (Q210) rather than deployed on demand.
2. **Data-plane failover mechanisms.** Prefer failover that uses the *data* plane: Route 53 **health-check-based** failover evaluates continuously and does not need you to make an API call (and Route 53's data plane is designed to survive control-plane impairment); **Route 53 ARC routing controls** exist specifically as a highly available, data-plane-based failover switch with a separate control plane in five regions. Global Accelerator's traffic dials are similar.
3. **Cross-region deployment capability**: a pipeline that can run from a different region, artifacts (images, Lambda packages) already replicated to the standby region's ECR/S3 - because you cannot copy them during the event.
4. **Break-glass credentials and runbooks stored outside the affected region** (and outside the affected account), including printed or offline copies of the failover procedure.
5. **A rehearsed decision framework**: who declares a regional failover, on what evidence, and what the rollback is. Under control-plane failure, human decision latency dominates the RTO.
6. **Know your `us-east-1` dependencies**: IAM, Route 53, CloudFront, ACM for CloudFront, and Organizations/SCP evaluation are homed there, so a `us-east-1` event affects you even if your workload is in Frankfurt (Q228).

*Hook: a control-plane event you lived through, what you could not do, and the static-stability change you made afterwards.*

### Q214. Setting and designing to an availability target for a payments API `[A]`

**Clarify first**: what does "unavailable" mean for this API - any 5xx, or a failed *payment*? What is the cost of a minute of downtime, in revenue and in contractual penalties? Is there a regulatory availability requirement? What availability do the *dependencies* offer - the card acquirer, the fraud service, the bank rails? And is the requirement about availability or about **not losing a payment**, because those have different designs.

**Setting the target.** I would propose **99.95 percent** for the payment *acceptance* path and be explicit about what that means:

| Target | Downtime/month | Downtime/year |
| --- | --- | --- |
| 99.9 | 43.2 min | 8.77 h |
| **99.95** | **21.9 min** | **4.38 h** |
| 99.99 | 4.4 min | 52.6 min |
| 99.999 | 26 s | 5.3 min |

The reasoning for 99.95 rather than 99.99: **the target must be lower than the composed availability of your dependencies**, or it is fiction. A serial path through CloudFront, API Gateway, Lambda and DynamoDB has a theoretical composed availability of roughly the product of their SLAs (API Gateway 99.95, Lambda 99.95, DynamoDB 99.99 for standard tables) - which is already about **99.89 percent** before your own code, your deploys or your dependencies' behaviour. Adding a third-party payment provider at 99.9 makes the *end-to-end authorization* path worse still.

**So the design must decouple availability from the slowest dependency**, and that is the actual answer:

1. **Accept-and-persist, then authorize asynchronously.** The API's job is to durably record the payment intent (one conditional write to DynamoDB, Q131) and return 202. That path depends on API Gateway + Lambda + DynamoDB only. Authorization happens in a Step Functions execution against the provider, with retries and a verification state. Now provider downtime is a *latency* event, not an availability event - which is what buys you an availability number the composed SLA said you could not have.
2. **Multi-AZ is inherent** for those three services; no work needed.
3. **Static stability** on the accept path: no synchronous dependency on anything that can be slow (no fraud check inline, no relational database, no third-party call), a tight timeout, and provisioned concurrency so a cold start never contributes.
4. **Idempotency everywhere** so client retries are free (Q126).
5. **Regional resilience**: DynamoDB global tables plus the stack deployed in a second region as a pilot light (Q210), with Route 53 health-check failover. Because the write is a single idempotent conditional put keyed by the client's idempotency key, cross-region duplicate acceptance is safely resolvable - which is unusually favourable for active-active and worth noting.

**Is one region enough? The arithmetic:**

- Single region, well-designed: dominated by the composed service SLA (~99.9-99.95) and by *your own* change failures - which in practice are the larger term. Empirically most outages are deploys and configuration, not AWS regions.
- Two regions active-active: the theoretical availability of two independent 99.95 paths is `1 - 0.0005² ≈ 99.999975 percent`, which is obviously nonsense in practice because the failure modes are **correlated**: the same bad deploy goes to both, the same schema change breaks both, `us-east-1`-homed global services affect both (Q228), and the failover mechanism itself can fail. Realistically two regions buys you roughly **99.99**, and only if the failover is tested (Q211).
- **So: one region is enough for 99.95, and the money is better spent on reducing change failure rate, on the async decoupling above, and on rehearsed recovery.** Two regions become necessary at 99.99 or when a regulator or contract requires geographic redundancy - and I would say that out loud, with the arithmetic, rather than accepting a target by acclamation (Q229).

**What I would commit to and monitor**: an SLI defined at the edge on the *acceptance* path (Q194), a separate SLI for authorization completion within N minutes, error-budget-based release policy, and a monthly report on budget consumption. And I would insist on a distinct, non-negotiable metric alongside availability: **payments lost or double-applied = zero**, with reconciliation as the proof (Q131) - because for a payments API correctness is the requirement that availability is merely in service of.

*Hook: an availability target you negotiated, the arithmetic you used, and the design change that made it achievable.*

---

## 14. Multi-region and global architecture

### Q215. The three hard problems, and the underestimated one

1. **Write conflicts and data consistency.** Two regions accepting writes to the same entity produces conflicts that the database resolves by policy (last-writer-wins in DynamoDB global tables, Q216), not by business logic. Every "eventual consistency is fine" assumption becomes a data-correctness question.
2. **Failover and its testing.** The mechanism (DNS, health checks, routing controls), the decision (who declares it, on what evidence), the asymmetry (Q223), and the fact that an untested failover is a hypothesis.
3. **Operational and cognitive cost.** Two of everything: deploys (Q227), quotas, dashboards, alarms, secrets, certificates, IaC state. Every incident starts with "which region, or both?" Every change doubles its risk surface.

**The one teams underestimate: the first - and specifically the *business* consequences of conflict resolution rather than the mechanism.** Everyone reads about last-writer-wins and nods. What they underestimate is that it means **silent data loss** with no error, no log and no metric: a customer updates their address in Europe while a support agent updates it in the US, and one change simply ceases to exist. Nothing alerts. The bug surfaces weeks later as a support ticket nobody can reproduce.

The related underestimation is **read-after-write across regions**: a user writes in region A, is routed to region B by a latency-based DNS change or a mobile network switch, and does not see their own change. This is not a theoretical concern - it is the single most common multi-region bug report, and it is caused by the design being correct at the database layer and wrong at the session layer.

So the sentence I would give: **active-active is not hard to build, it is hard to be correct in, and the incorrectness is silent.**

*Hook: a multi-region correctness issue you found, and how long it existed before you noticed.*

### Q216. DynamoDB global tables and last-writer-wins

**Mechanism**: each replica is a full read-write table; writes are replicated asynchronously to the other regions, typically within **a second or two**. Replication uses the table's stream internally and is measured by the **`ReplicationLatency`** metric (which you must alarm on). There is no leader.

**Conflict resolution: last-writer-wins on the *item*, decided by the item's write timestamp.** Two properties to state precisely:

- Resolution is **per item, not per attribute** - so a conflicting write does not merge fields; the losing write is discarded entirely, including attributes the other writer never touched.
- The timestamp is assigned by the service, so **clock skew is not your problem**, but "last" is by arrival at the replication layer, which does not necessarily match the order the users perceived.

**What last-writer-wins actually does to your data:**

- **Silent loss of the losing write.** No error to either writer; both got a 200. The lost update is unrecoverable unless you can reconstruct it from a stream or from application logs.
- **Conditional writes are only conditional locally.** `attribute_not_exists(pk)` in two regions simultaneously both succeed - so uniqueness constraints and optimistic locking **do not work across regions**. This is the most important consequence and the one candidates miss: your carefully designed conditional write (Q156) provides no cross-region guarantee at all.
- **Transactions are region-scoped.** `TransactWriteItems` is atomic within a region and replicated as individual item writes, so the other region can observe a partial transaction transiently, and can conflict with individual items of it.
- **Counters break.** `ADD` increments applied in two regions do not sum; one wins. So a global counter must be per-region-sharded and summed on read, or derived from a stream.

**How I design around it:**

- **Partition write ownership by key**, so a given entity is only ever written in one region (route by tenant, user home region or hash). This converts active-active into "active-active for the fleet, single-writer per entity" and removes conflicts by construction. **This is the technique to lead with.**
- **Model as append-only events** rather than mutable state where possible: distinct sort keys per event (`ORDER#123#EVENT#<uuid>`) never conflict, and the current state is a projection. Conflict-free by design.
- **Attribute-level or CRDT-style modelling** for genuinely concurrent fields: separate items per field, or increments as separate items.
- **Alarm on `ReplicationLatency`** and on the `PendingReplicationCount`, and treat a growing lag as a correctness risk, not just a performance one.

*Hook: a global-tables design where you partitioned write ownership, and the conflict you avoided by doing so.*

### Q217. Two regions write the same item within 200 ms `[T]`

**What you end up with**: exactly one of the two versions, whole. The item is not merged; the losing write's attributes are gone even if the winner never referenced them. Both callers received success. The replication settles within a second or two, after which both regions agree - so if you read immediately after writing in the losing region you may briefly see your own write, and then it will *change under you* to the other region's value. That transient - **read your write, then have it silently reverted** - is the most confusing symptom, and it is the one support tickets describe as "the system lost my change".

There is a second-order case worth naming: if the two writes are `UpdateItem` calls modifying *different* attributes of the same item, you might expect both to survive. They do not, reliably - resolution is at item granularity, so one whole item version wins.

**How I design so it does not matter** - four techniques, roughly in order of preference:

1. **Single-writer-per-entity routing.** Give every entity a home region (stored on the entity, or derived from a hash of its key, or from the customer's residency) and route writes there. Reads can be local everywhere. Conflicts become impossible rather than resolved. The cost is a cross-region write hop for a user who is not near their entity's home region - which is usually acceptable and always simpler than reasoning about conflicts.
2. **Append-only modelling.** Never update in place: write an immutable event item with a unique sort key (`#EVENT#<ulid>`), and compute state by reading the collection or by maintaining a projection. Two regions writing simultaneously produce two events, both preserved, and the projection applies a deterministic ordering rule. This is conflict-free and also gives you an audit trail.
3. **Decompose the item.** If two actors legitimately update different fields concurrently, make those fields separate items so their writes never collide.
4. **Make the operation commutative.** Increments as separate rows summed on read; set membership as add/remove items; state machines where transitions are idempotent and monotonic (a `version` guard, applied per region, with a reconciliation pass).

And the operational complement: **detect it**. Emit the writing region and a client-side timestamp on every write, and run a periodic job that looks for entities written in two regions within the replication window - so "how often does this actually happen" is a number rather than a worry.

*Hook: a case where you chose single-writer routing over conflict resolution, and how you handled the cross-region write latency.*

### Q218. Aurora Global Database

**Mechanism**: one **primary** cluster with read-write, and up to five **secondary** regions with read-only clusters. Replication is at the **storage layer**, performed by the Aurora storage fleet rather than by log shipping through the database engine - which is why it is fast and why it does not consume primary CPU.

**Replication lag**: typically **under a second** (AWS quotes ~1 s), measured by `AuroraGlobalDBReplicationLag`. It degrades under heavy write load and with distant regions, and you must alarm on it because it is your RPO.

**The headless secondary**: a secondary cluster with **no DB instances** - just the replicated storage volume. It costs storage and replication but no instance hours, and you create instances at failover time. This is the pilot-light option: much cheaper, at the price of adding instance provisioning (minutes) to your RTO. Worth naming because it is the cost/RTO dial most people do not know exists.

**Managed planned failover** versus **unplanned promotion**:

- **Managed planned failover** is the graceful path: Aurora stops writes on the primary, waits for the secondary to catch up fully, then switches roles - so **RPO is zero** and the global cluster topology is preserved (the old primary becomes a secondary). It requires a healthy primary, so it is for planned events, region migrations and drills. Takes minutes.
- **Unplanned promotion (detach and promote)** is what you do when the primary region is gone: you promote a secondary to be a standalone cluster. **The global cluster structure is broken** - you must reconfigure replication afterwards, and re-adding the old region is a rebuild. RPO is whatever the replication lag was at the moment of failure, and **you cannot know it precisely** because the primary is unreachable.

**The RPO you can honestly claim**: **zero only for a managed planned failover.** For an unplanned regional loss, it is "typically under one second of writes, unbounded in the pathological case, and unverifiable at the time" - which is the honest sentence. If the business requires a provable RPO of zero across a region loss, Aurora Global Database does not give it; you need synchronous replication (which costs cross-region latency on every commit) or an application-level design where the write is durable in two regions before acknowledgement - typically a queue or a multi-region-durable store in front of the database.

*Hook: an Aurora Global Database deployment, whether you used a headless secondary, and the replication lag you observed under load.*

### Q219. Route 53 health checks, failover, and the DNS TTL arithmetic

**Mechanism**: a health check polls an endpoint (or evaluates a CloudWatch alarm, or aggregates other health checks) from **multiple AWS locations**; the endpoint is unhealthy when more than a configured proportion of checkers fail. Default checking interval is 30 s (10 s for fast health checks), and the failure threshold defaults to 3 - so detection alone is `interval x threshold`.

**The arithmetic of a real failover:**

| Stage | Time |
| --- | --- |
| Health check detection | 30 s x 3 = **90 s** (or 10 s x 3 = 30 s with fast checks) |
| Route 53 propagates the record change to its edge | seconds to ~1 minute |
| **Resolver caches expire** | up to the record's **TTL** (60 s if you set it to 60) |
| **Client caches expire** | **the real problem**: browsers, mobile OSes, JVMs and connection pools cache independently and frequently ignore TTL |
| Client reconnects and warms | seconds |

So with a 60-second TTL and default health checks, **the honest failover time is 3-5 minutes for most clients and longer for the worst-behaved ones**. The specific offenders: the JVM's `networkaddress.cache.ttl` (which historically defaulted to caching forever with a security manager, and 30 s otherwise), some HTTP clients pinning a resolved address for the life of a connection pool, and mobile carriers' resolvers ignoring low TTLs.

**Practical consequences:**

- **Set TTLs to 60 s (or lower) on records you intend to fail over** - but understand you cannot get below client behaviour, so do not promise a 60-second RTO on DNS alone.
- **Use fast health checks plus a failure threshold of 2-3** for anything you care about, and health-check an endpoint that exercises the real dependency path, not a static 200.
- **Prefer non-DNS failover for fast requirements**: **CloudFront origin groups** fail over on the first request that gets a 5xx, in milliseconds, with no DNS involvement (Q62). **Global Accelerator** shifts traffic at the network layer using anycast, so clients keep the same IP - failover in seconds, no DNS caching (Q221). **ALB target groups** handle in-region failure without touching DNS.
- **Use Route 53 ARC routing controls** rather than only health checks when you want a deliberate, operator-controlled switch that does not depend on a health check's opinion (Q220).

The framing: **DNS is a coarse, cached, client-controlled mechanism - excellent for the "which region" decision, unsuitable as your only fast failover primitive.**

*Hook: a DNS failover you measured, and how long the long-tail clients actually took.*

### Q220. Route 53 Application Recovery Controller and readiness checks

ARC has two distinct capabilities, and knowing which solves which problem is the answer:

**Routing controls** are on/off switches (safety-net style) with a **highly available data plane spread across five regions**, backed by **safety rules** (assertion rules such as "at least one cell must be on", and gating rules). A routing control drives a Route 53 health check, so flipping it shifts traffic. What it solves that a health check does not:

- **A deliberate, operator-controlled decision.** A health check has an opinion based on probing an endpoint; during a gray failure (Q206) that opinion is unreliable and may flap. A routing control is a human (or automated) *decision*, and it does not change its mind.
- **Availability of the failover mechanism itself.** The routing-control data plane is designed to remain operable when a region - including the region hosting your control plane - is impaired (Q213). A failover mechanism that depends on the failing region is not a failover mechanism.
- **Guardrails against making it worse.** Safety rules prevent the classic incident of turning off both cells, or turning on a standby that is not ready.

**Readiness checks** are the other half, and they answer a question health checks structurally cannot: **"is the standby actually able to take the traffic, right now, before I send it?"** ARC continuously audits the recovery cell's resources against the primary's - capacity (ASG sizes, Lambda concurrency quotas, DynamoDB capacity), configuration (route tables, security groups, target groups), quotas and limits - and reports readiness. This detects the **configuration and quota drift** that is the single most common cause of a failed failover: the standby was correct six months ago, and since then the primary got a quota increase, a new subnet, a larger table and three new secrets that were never replicated.

So: a health check tells you the primary is broken; a **readiness check tells you the standby will work**, which is the more useful and much rarer piece of information. The cost is that ARC is not cheap (per-cluster pricing) and configuring readiness checks is real work - so I would use routing controls and readiness checks for a small number of genuinely critical, multi-region workloads and rely on health checks plus rehearsed drills (Q211) elsewhere.

*Hook: a standby that had drifted from the primary, how you discovered it, and whether readiness checking would have caught it.*

### Q221. Global Accelerator versus CloudFront versus latency-based routing

| | Global Accelerator | CloudFront | Route 53 latency-based routing |
| --- | --- | --- | --- |
| Layer | **Network (TCP/UDP)**, anycast static IPs | **HTTP/HTTPS** CDN with caching | **DNS** |
| Failover speed | **Seconds**, at the edge, no DNS or client cache involved | Milliseconds via origin groups, per request | **Minutes** (TTL plus client caching, Q219) |
| Caching | None | Yes - the primary purpose | n/a |
| Client-visible IP | **Two static anycast IPs** - useful for IP allow-listing and for clients that cannot handle DNS changes | CloudFront's IPs, resolved via DNS | Your endpoints' addresses |
| Protocols | Any TCP/UDP | HTTP/HTTPS (plus WebSocket) | Any |
| Traffic control | Traffic dials per endpoint group, weights per endpoint | Origin groups, behaviours | Weights, latency, geo |

**TCP game backend: Global Accelerator.** Reasoning: it is UDP/TCP rather than HTTP so a CDN is irrelevant; game clients are extremely latency-sensitive and Global Accelerator gets traffic onto the AWS backbone at the nearest edge (which typically improves both latency and jitter meaningfully over the public internet); the **static anycast IPs** mean the client does not re-resolve DNS and a regional failover is invisible to it, which matters enormously for long-lived connections; and failover happens in seconds via health checks at the edge rather than waiting for TTLs. The traffic dials also let you drain a region gradually.

**HTTP API: CloudFront.** Reasoning: even with nothing cacheable you get edge TLS termination, backbone transit, HTTP/3, WAF, Shield, lower egress rates and per-request origin failover (Q62) - and if anything *is* cacheable you get that for free. Global Accelerator can front an HTTP API too, and the two are complementary rather than competing (CloudFront in front of Global Accelerator is a valid pattern for a global HTTP service with a non-HTTP component), but for pure HTTP, CloudFront is the richer answer.

**Where latency-based routing still fits**: as the *coarse* region-selection mechanism when you do not want an accelerator or CDN in the path (an internal service, a regionally partitioned data plane), or in combination with the others for the initial region choice. But never as your fast failover primitive.

*Hook: a global traffic design where you chose one of these, and what the alternative would have cost you.*

### Q222. Active-passive versus active-active for write-heavy work

**For a write-heavy workload, my default is active-passive for writes, with active-active reads** - and I would defend that position rather than treating active-active as the aspiration.

**Where writes get pinned:**

- **Global single-writer**: all writes go to one region; the other serves reads locally and forwards writes cross-region (adding, say, 80-100 ms for a transatlantic hop). Simple, correct, and the write latency is the cost. Failover is a promotion.
- **Partitioned single-writer (my preferred design)**: each entity has a **home region**, derived from the customer's residency, a hash of the key, or an explicit assignment. Writes for that entity always go to its home; reads are local everywhere. This gets you *fleet-level* active-active with *entity-level* single-writer, so conflicts are impossible (Q216, Q217) and write latency is local for most users. The complexity is the routing layer and the entity-to-region mapping (a lookup at the edge, in a CloudFront Function or via the URL/host).
- **True multi-writer**: only with conflict-free modelling (append-only events, CRDTs) or with a database offering strong multi-region consistency at a latency cost.

**Read-after-write across regions** - the practical problem (Q215). Techniques, and I would name several because interviewers probe this:

1. **Sticky routing for a session.** After a write, pin that user to the region that accepted it for a period - a cookie, a header, or a session token carrying the home region, honoured at CloudFront. Simple and effective; the failure mode is a region loss, which is an acceptable exception.
2. **Read-your-writes from the write region** for the specific request that follows the write: return the written entity in the write response so the client does not need to re-read at all. Cheapest technique and it removes most of the problem.
3. **Version tokens.** The write returns a version/sequence; subsequent reads carry it, and a replica that has not caught up either waits briefly or forwards to the home region. Correct and more work.
4. **Client-side echo**: the UI shows the value the user just submitted rather than re-fetching. Trivial, and covers the majority of user-visible cases.
5. **Local read from the same region as the write**, i.e. do not move the user mid-session (which is really technique 1 stated as a rule).

And the sentence I would end on: **write-heavy plus multi-region means you are choosing between write latency and write conflicts, and there is no third option** - so pick deliberately, per entity, and make the choice visible in the data model.

*Hook: a multi-region write design you built, how you routed writes, and how you handled read-after-write.*

### Q223. The runbook works from the standby side `[T]`

Four asymmetries:

1. **Data replication direction.** Replication is configured primary → standby. After failover, the standby is serving but **nothing is replicating back**, so (a) you are running without a replica - a second failure is now unprotected - and (b) failing *back* requires establishing reverse replication and reconciling divergence, which for Aurora Global Database means detach-and-rebuild (Q218) and for DynamoDB global tables means the tables have diverged in ways last-writer-wins will resolve arbitrarily. Testing "failover works" says nothing about "we can get back", and the return trip is where the second incident happens.
2. **Capacity and quotas.** The standby has never taken production traffic, so its **service quotas** are at defaults: Lambda concurrency 1,000, API Gateway throttles, SES sending limits, DynamoDB table limits, EC2 instance limits, KMS request rates. The primary's limits were raised over years, one support ticket at a time, and none of that was replicated. The drill (which used test traffic) never approached them. **This is the most common real failure** and it is exactly what ARC readiness checks exist to detect (Q220).
3. **Out-of-band and external registrations.** Things that point at the primary by name and are not in your IaC: third-party webhook URLs, partner IP allow-lists (your standby's NAT/EIP addresses are different), OAuth redirect URIs, SFTP endpoints registered with a bank, DNS records for MX and SPF, certificate pinning, monitoring integrations, and **scheduled jobs** (EventBridge Scheduler rules that exist only in the primary, or that exist in both and would double-run). A read-only drill exercises none of these.
4. **Warm state and dependency direction.** The standby's caches, connection pools, JIT, search indexes and materialized views are cold, so its performance under full load is unknown - and a drill at 5 percent traffic proves nothing about 100 percent. Meanwhile in-region dependencies may still point at the *primary* region's resources (a Secrets Manager secret, a KMS key, an S3 bucket, a parameter, a cross-region VPC endpoint), so the standby is only "independent" until you check every ARN in the configuration - and cross-region KMS key references are a classic hard failure.

Two more worth adding: **IAM and identity** (a role or trust policy that exists only in the primary account/region, or an OIDC provider), and **the humans** - the runbook was written by someone who knew the primary and tested by someone who knew the plan, not by whoever is on call at 3 a.m.

**What fixes it**: full failover drills at 100 percent traffic for days (Q211), with the return trip included; automated readiness/quota comparison; every ARN and endpoint in IaC with region as a parameter; and a written inventory of external registrations with an owner.

*Hook: a failover asymmetry you discovered - ideally in a drill rather than an incident - and how you closed it.*

### Q224. RPO of each cross-region replication mechanism

| Mechanism | RPO | The caveat |
| --- | --- | --- |
| **S3 Cross-Region Replication** | **Minutes**; bounded only with **RTC** (15 min, 99.99 percent SLA) | Asynchronous, no bound without RTC; does not replicate pre-existing objects, version deletes, or bucket configuration (Q177) |
| **DynamoDB global tables** | **~1 second**, typically sub-second | Asynchronous, unbounded under load; conflicts resolved by last-writer-wins, so RPO understates the correctness risk (Q216). Alarm on `ReplicationLatency` |
| **Aurora Global Database** | **~1 second** typical; **zero** only for managed planned failover | Storage-layer replication; unverifiable at the moment of an unplanned regional loss (Q218) |
| **Kinesis** | **No native cross-region replication** - you build it (a consumer that re-publishes, or EventBridge/Firehose to the second region). RPO = your pipeline's lag, typically seconds | The replicator is itself a component that can fail, and it needs its own monitoring and its own idempotency |
| **EventBridge cross-region rules** | **Seconds** | At-least-once, no ordering; a rule targeting a bus in another region is the supported mechanism, and failures need a DLQ per target (Q107) |
| **RDS (non-Aurora) cross-region read replica** | **Seconds to minutes**, depending on write volume and network | Logical replication, so lag grows with load and with long transactions |
| **ElastiCache global datastore** | **Seconds** | Cache data; treat as convenience, not durability |
| **AWS Backup cross-region copy** | **Hours** (per backup schedule) | The immutability/isolation story is its value, not the RPO (Q208) |
| **EBS snapshot copy** | Hours | Point-in-time per snapshot |

**The three things I would say beyond the table:**

1. **Every one of these is asynchronous**, so **every** multi-region design has a non-zero RPO unless you make the *application* write durably to two regions before acknowledging - which costs cross-region latency on the write path and is the only way to claim zero.
2. **The RPO of the system is the worst RPO among the stores that must be mutually consistent.** If DynamoDB replicates in a second and S3 in fifteen minutes, and an item references an object, then after a failover you have items pointing at objects that do not exist yet. **Cross-store consistency after failover is the failure mode nobody models**, and the mitigations are ordering (write the object first, then the item) and tolerance (the reader handles a missing object gracefully).
3. **Measure it, do not quote it.** Alarm on each mechanism's lag metric, and record the actual lag at the moment of every drill, because "typically one second" is not a commitment you can make to a business.

*Hook: a multi-region design where two stores' replication lags differed, and how you handled the inconsistency window.*

### Q225. Idempotency and identifier generation across regions

**Identifier generation.** Do not use anything centrally coordinated, and do not use anything sequential:

- **UUIDv4** - fine for uniqueness, terrible as a database or S3 key at scale because it is random (no locality, and for DynamoDB it is actually good for distribution but useless for sorting).
- **ULID / UUIDv7 / KSUID** - **the right default**: time-ordered prefix plus randomness, so they sort chronologically, distribute reasonably, and collide with negligible probability across regions with no coordination. Time-ordered IDs also make sort keys and S3 prefixes work naturally.
- **Region-embedded IDs** (`use1-01H8...`) - my preferred variant when multi-region, because the ID itself tells you where it was created, which is invaluable for debugging, for routing (Q222's home-region lookup can read the ID), and for conflict analysis.
- **Snowflake-style with a node ID** - works, but requires assigning unique node IDs per region and per instance, which is coordination you did not want. And with SnapStart or cloned environments, a duplicated node ID silently produces duplicate IDs (Q74).
- **Never**: DynamoDB atomic counters or database sequences for cross-region IDs - they conflict or serialize.

**Ordering assumptions to avoid:**

- **Do not infer order from IDs across regions.** A time-ordered ID gives you approximate ordering only, bounded by clock skew between regions (tens to hundreds of milliseconds, occasionally worse). Two events "in order" by ID may not be causally ordered.
- **Do not rely on arrival order** in a replicated store - replication lag differs per item and per store (Q224).
- **Use logical versioning for correctness**: a per-entity monotonic version applied with a conditional write, or a vector/lamport-style counter if concurrent writers are genuinely possible. Then "newer" is a fact rather than a clock comparison. Note the caveat: conditional writes are **region-local** in global tables (Q216), so the version guard prevents *in-region* lost updates and does not prevent cross-region conflicts - which is why single-writer-per-entity routing remains the primary defence.

**Idempotency across regions**: the idempotency table is itself replicated with lag, so two simultaneous requests in two regions can both find "no record" and both proceed. Therefore: **route by idempotency key** (hash the key to a home region) if the operation must be globally exactly-once, or accept in-region idempotency plus **downstream deduplication** (the payment provider's own idempotency key, Q131) as the real guarantee. Say this plainly - it is the honest answer, and it is the point at which people realize idempotency and multi-region interact.

*Hook: an ID scheme you chose for a multi-region system, and an ordering assumption you had to remove.*

### Q226. EU data residency with a global control plane

**Clarify what "must never leave the EU" covers**: the data itself, backups, logs, telemetry, support access, and derived data such as search indexes and analytics aggregates. Also *who* is allowed to access it (personnel location can be part of the requirement), and whether the constraint is contractual, GDPR-based or a sector regulator's.

**The design:**

1. **Data plane per jurisdiction, fully self-contained.** A complete stack in `eu-central-1` (or `eu-west-1`) holding all EU customer data: DynamoDB tables, S3 buckets, Aurora clusters, queues, and - critically - **KMS keys created in-region**, logs, backups and telemetry. The same stack is deployed in `us-east-1` for US customers from the identical IaC with a region parameter. **No global tables spanning jurisdictions.**
2. **Routing at the edge, by identity not by geography.** A user's jurisdiction is a property of their *account*, not of their current location - a German customer travelling to the US must still be served from the EU. So: a **CloudFront Function or Lambda@Edge** that reads the tenant/user from the host, path or a token claim, looks up their home region in a small **replicated routing table** (a KV store at the edge - CloudFront KeyValueStore, or a token claim that already carries it), and routes to the correct regional origin. Geolocation routing (Q46) is the *wrong* mechanism here and saying so is the point.
3. **The global control plane holds only non-personal data**: tenant IDs, region assignment, entitlements, feature flags, service catalogue, billing aggregates - explicitly no personal data. Homed in one region with read replicas or a global table, and **its schema is reviewed as a compliance artifact**, because control-plane scope creep ("we'll just cache the user's email here") is exactly how residency is violated.
4. **Identity**: either a per-jurisdiction user directory, or a global IdP that stores only identifiers with personal attributes resolved regionally. If a single Cognito/IdP tenant must be global, verify what it stores and where - this is a common gap.
5. **Observability and support**: logs, traces and metrics stay in-region, with a **global dashboard that queries regionally** rather than aggregating raw data centrally. Aggregate, anonymized metrics may cross; raw logs may not. Support tooling must enforce the same boundary, including break-glass access, and **access must be logged per jurisdiction** (CloudTrail in-region, to an in-region archive).
6. **AWS-level controls to enforce it, not just document it**: separate **accounts per jurisdiction** in their own OU, with an **SCP restricting the allowed regions** (`aws:RequestedRegion`) so a well-intentioned engineer physically cannot create a resource outside the EU; `aws:ResourceOrgID`/`aws:PrincipalOrgID` conditions on bucket policies; S3 Block Public Access; and a Config rule set asserting no cross-region replication is configured. **The SCP is the strongest single control** and I would lead with it.
7. **Data-subject rights** (erasure, portability) implemented per region, with the control plane recording only that a request was fulfilled.

**The honest trade-offs**: this costs you a duplicated stack per jurisdiction (mitigated by serverless, where idle cost is near zero - Q210), a genuinely harder deployment and observability story (Q227), the inability to run global joins for analytics without an anonymization step, and a routing layer that is now on the critical path of every request. The alternative - one global stack with row-level jurisdiction tagging - is cheaper and I would refuse it, because it makes compliance a property of application code rather than of infrastructure boundaries, and code changes weekly.

*Hook: a residency requirement you implemented, the control that actually enforced it, and something you found leaking across the boundary.*

### Q227. Deploying to two live regions

**What breaks about a normal pipeline:**

1. **"Deploy" is no longer atomic.** There is a window - minutes to hours - where the two regions run different versions. Every cross-region-visible contract must therefore be **backward and forward compatible** for the duration: the data schema in a global table, the event schema on a replicated bus, and any shared S3 layout. This is expand-contract discipline applied to replication, and it is the biggest conceptual change.
2. **Region-scoped artifacts.** Lambda deployment packages, container images in ECR, layer versions and KMS keys are all regional. So the pipeline must **replicate artifacts to every region before deploying** (ECR replication rules, S3 CRR for packages), and the deployment must reference the *regional* ARN. A pipeline that hardcodes one region's ECR is the most common breakage.
3. **Rollout must be sequential, not parallel** - which is the opposite of what teams want. Deploy region A, verify against real traffic (canary, SLO burn), then region B. Parallel deployment means a bad release takes out both regions simultaneously, which removes the entire benefit of having two. This turns a 10-minute deploy into a 40-minute one, and that is the price of the architecture.
4. **Canary analysis has to be region-aware.** A canary in region A while region B serves the old version means your aggregate metrics blend two versions. Metrics, dashboards and burn-rate alarms all need a region dimension, and the automated rollback decision must be per region.
5. **Data migrations become genuinely hard.** A schema change must be applied in a way that both versions tolerate, in a store that is replicating bidirectionally. Any migration that rewrites items generates replication traffic in both directions and can conflict with live writes. So: additive-only changes, backfills that are idempotent and re-runnable, and a strong preference for **new attribute / new item type** over in-place transformation.
6. **Region-specific state and jobs**: scheduled tasks must run in exactly one region (or be idempotent), and the pipeline must know which. Leaving an EventBridge Scheduler rule enabled in both regions is a classic double-processing bug.
7. **Rollback is doubled** and may need to be partial - and you must be able to roll back region A while region B is still on the new version, which again requires the compatibility discipline of point 1.

**How I would sequence a release:**

1. Build once, sign, replicate artifacts to all regions.
2. Deploy to a **non-production region** and run the full suite.
3. Deploy to **production region B** (the one with less traffic), canary at 5-10 percent of that region's traffic, watch SLO burn for a defined bake period.
4. Promote to 100 percent in B, bake again.
5. Deploy to **region A** with the same canary.
6. Automated rollback per region on burn-rate breach; a documented decision on whether to also roll back the other region.
7. Then, and only then, run the contract phase of any migration.

**And the operational insistence**: a **regional shift** capability (routing controls, Q220) so that if a deploy degrades one region you can drain it in seconds rather than debugging under load - which is the single most valuable thing multi-region gives you for deployments, and the one people forget to use.

*Hook: a multi-region release process you built, and a version-skew bug it caught or caused.*

### Q228. A regional degradation takes down the global control plane `[T]`

**The dependency**: several AWS "global" services have their **control plane homed in `us-east-1`** - IAM (writes), Organizations and SCP management, Route 53 (record changes and health-check configuration), CloudFront (distribution configuration), ACM certificates for CloudFront, and the AWS billing and support consoles. In addition, *your own* global control plane probably has a home region: the DynamoDB table holding tenant-to-region routing, the Cognito user pool, the parameter store holding configuration, the CI/CD pipeline, the secrets, the KMS key, or the S3 bucket serving the config.

So when that region degrades: both data-plane regions keep serving traffic (they are independent), but **you cannot change anything** - cannot update DNS, cannot rotate a secret, cannot deploy, cannot fail over if failover requires a control-plane write - and if your own routing table or auth service lives there, **new requests fail even though both data planes are healthy**. That last case is the one that turns "a control-plane problem" into a customer-facing outage, and it is entirely self-inflicted.

**The fixes:**

1. **Identify and document every global-service and home-region dependency**, explicitly, as a design artifact. Most teams have never listed them.
2. **Make your own control plane's *data plane* independent.** Replicate the routing/config/entitlement data to every region (global tables, or push it to each region's local store and to the CloudFront KeyValueStore), and have each region read **locally** at request time. The control plane may then be unwritable during an event - which is acceptable - while remaining readable everywhere, which is essential. **Static stability again** (Q213): the request path must not require a call to another region.
3. **Cache aggressively with long-lived fallbacks**: authorization decisions, JWKS, feature flags and configuration cached locally with a "serve last known good indefinitely if the source is unreachable" policy rather than failing closed.
4. **Use failover mechanisms with distributed data planes**: Route 53 health-check-based failover and **ARC routing controls** (five-region data plane, Q220), Global Accelerator, CloudFront origin groups - all of which act without a control-plane write from you.
5. **Pre-stage everything you would need to change**: alternate DNS records already created (weighted at zero), certificates already issued, artifacts already replicated, the standby's quotas already raised. If failover requires creating something, it will fail.
6. **Keep a break-glass path** documented and stored outside the region, and rehearse operating with the console unavailable.
7. **Do not run your primary in `us-east-1`** if you can avoid it, and if you must depend on `us-east-1`-homed services, treat their unavailability as a *known* scenario with a written response rather than a surprise.

*Hook: a global-service or home-region dependency you found in your own architecture, and what you did to remove it from the request path.*

### Q229. "We need active-active because we need 99.99" `[A]`

**The conversation, in the order I would have it.**

**First, agree on what the number means.** 99.99 percent is **4.4 minutes per month, 52 minutes per year** of unavailability. I would put that on the table immediately, because most stakeholders have not converted the number and some will revise it when they see it. Then: measured how, at which boundary, over what window, and counting what as an outage? Is a 30-second degraded window during a deploy an outage? Is partial functionality? A target without a measurement definition is not a target (Q194).

**Second, ask what the requirement actually is.** Three very different needs get expressed as "99.99":

- "We cannot lose data" → that is an **RPO/durability** requirement, and active-active does not improve it (it often makes it worse, Q216).
- "A customer must never see an error" → that is a **retry and degradation** requirement, better served by idempotency, queues and graceful degradation (Q205).
- "We must survive losing a region" → that is genuinely multi-region, but it may be satisfied by warm standby with a 15-minute RTO, not by active-active.
- Sometimes it is "a contract says 99.99", in which case the question becomes what the contract's *definition* and penalty are, and whether the penalty is cheaper than the architecture.

**Third, the arithmetic** (Q214). A serial path through API Gateway (99.95 SLA), Lambda (99.95) and DynamoDB (99.99) composes to roughly **99.89 percent** before your own code - so **99.99 in a single region is not achievable no matter how well you build**, and I would say that clearly because it is the strongest argument in the conversation. But then the harder truth: two regions give a *theoretical* 99.999975 percent and a *realistic* ~99.99 at best, because failures are correlated - the same deploy, the same schema change, the same `us-east-1`-homed dependency (Q228), and the failover mechanism itself. And empirically, **the dominant cause of outages is change, not infrastructure**: a second region does nothing about a bad deploy, and doubles the surface for one (Q227).

**Fourth, the cost**, stated concretely: roughly double the infrastructure for a container-based stack (much less for serverless, Q210); a materially slower and riskier release process; conflict-resolution correctness work in the data layer; doubled operational surface; and a quarterly failover drill programme that must be staffed. That is a team's worth of ongoing effort, not a project.

**The alternative I would propose:**

1. **Decouple availability from the slow and unreliable parts**: accept-and-persist synchronously, do the rest asynchronously (Q214). This is usually worth more availability than a second region, and it is cheaper.
2. **Attack change failure rate**: canaries with automated rollback, progressive delivery, feature flags, and the ability to roll back in under five minutes. Most of the missing availability lives here.
3. **Multi-AZ done properly plus a warm standby in a second region**, with rehearsed failover and ARC readiness checks (Q220) - giving a defensible 99.95-99.97 with a 10-20 minute RTO for a regional event.
4. **Graceful degradation** so partial failures are not counted as outages (and make sure the SLI definition reflects that honestly).
5. **Measure for a quarter.** Publish the actual SLI. Then have the conversation again with data - very often the current architecture is at 99.9 and the gap is deploys and one flaky dependency, not geography.
6. **If active-active is still required**, do it for a *subset*: the read path and the accept path go active-active (both are conflict-free if writes are idempotent and single-writer-per-entity, Q217); the complex mutable core stays single-writer. Buy most of the benefit for a fraction of the risk.

**How I would close it**: "I can commit to 99.95 with a two-week programme and to 99.99 with a two-quarter programme and a permanent increase in operating cost and release friction. Here is what each buys in minutes, and here is what I think the actual failure history says we should fix first. Which do you want to pay for?" Putting the choice back with the numbers attached is the principal-level move - and being willing to say "we should not buy 99.99 for this workload" out loud is the point of the question.

*Hook: an availability conversation you led with a business stakeholder, the number you talked them out of or into, and what you built instead.*

---

## 15. Infrastructure as code and delivery for serverless

### Q230. CloudFormation, SAM, CDK, Terraform, Serverless Framework

- **CloudFormation** - AWS's native declarative engine and state manager. Everything else on this list except Terraform ultimately produces CloudFormation. You rarely write raw templates by choice any more, but you must understand it because **it is what fails** (Q233, Q236).
- **SAM** - a CloudFormation *transform* adding serverless-specific shorthand (`AWS::Serverless::Function`, `Api`, `StateMachine`) plus a CLI for local invoke, build and guided deploy. Small, declarative, no programming language. Excellent for a handful of functions; verbose and repetitive at scale.
- **CDK** - imperative code (TypeScript, Python, Java) that **synthesizes** CloudFormation, with high-level constructs that encode best practice (`grantReadData`, sensible defaults, log-group creation) and the ability to build your own reusable constructs. Real abstraction, real testing, real refactoring - and real footguns (Q232).
- **Terraform** - provider-based, own state file, multi-cloud, huge module ecosystem, plan/apply with an explicit diff. The strongest choice when AWS is not the only target or when the organization already runs Terraform for everything else.
- **Serverless Framework** - a third-party, YAML-first, plugin-rich tool that was the standard for years. Still capable, but the licensing change and the general convergence on CDK/SAM/Terraform means I would not start a new estate on it.

**My default for a new serverless estate: CDK**, with these reasons: shared constructs are how you make 60 services consistent without copy-paste; `grant*` methods generate least-privilege policies from actual dependencies (Q30), which is the single biggest security win available; the abstraction lets a platform team publish a `StandardHttpService` construct that bakes in logging, alarms, tracing, tagging and DLQs; and it is AWS-native so new services are supported immediately.

**When I would choose otherwise**: **Terraform** if the organization is already Terraform-standardized or genuinely multi-cloud - consistency with what the team operates beats theoretical fit. **SAM** for a small, single-team, few-function project where CDK's toolchain is overhead. And I would say plainly that the worst outcome is *both* CDK and Terraform managing overlapping resources, which produces drift nobody owns.

*Hook: an IaC choice you made or migrated, and whether the consistency argument or the capability argument dominated.*

### Q231. How CDK actually works

1. **You write an app** in a supported language. Constructs are objects in a tree rooted at `App` → `Stack` → constructs.
2. **`cdk synth` runs your program.** This is the key mental model: **CDK is a code generator, not a runtime.** Your loops, conditionals and functions all execute at synth time on your machine or in CI; none of it exists at deploy time.
3. **The output is a "cloud assembly"** - a directory (`cdk.out`) containing: one **CloudFormation template per stack**, a **manifest** describing stacks, their dependencies and environments, **asset definitions** (file and Docker image assets with their content hashes), and the parameters/context used.
4. **Assets**: any local file, Lambda bundle or Docker build referenced by the app is hashed and recorded. On `cdk deploy`, the CLI **publishes assets first** - files to the CDK bootstrap S3 bucket, images to the bootstrap ECR repository - and rewrites the template to reference the published locations by key/digest. This is why `cdk bootstrap` exists and why a missing bootstrap stack is the classic first-deploy failure.
5. **Deployment** is then a CloudFormation `CreateChangeSet`/`ExecuteChangeSet` per stack, in dependency order, assuming the bootstrap deploy/publish roles.

Three consequences worth stating because they explain most CDK confusion:

- **Logical IDs are derived from the construct path**, hashed. So renaming a construct or moving it between parents changes the logical ID, which CloudFormation reads as *delete the old resource and create a new one* (Q232).
- **Tokens**: values not known at synth time (an ARN, a generated name) are represented as opaque tokens (`${Token[TOKEN.123]}`) that resolve to CloudFormation intrinsics. You cannot `if` on them or string-parse them in your code - a common source of "why is my condition not working".
- **Context and environment lookups** (`fromLookup`) run at synth time against a live account and are cached in `cdk.context.json`, which makes synth non-hermetic unless that file is committed. Committing it is the right practice.

*Hook: a CDK behaviour that surprised you, and the synth-time-versus-deploy-time distinction that explained it.*

### Q232. A construct rename destroys a production table `[T]`

**Mechanism**: the logical ID is a hash of the **construct path**. Renaming `new Table(this, 'Orders', ...)` to `'OrdersTable'`, or moving it from the stack into a nested construct, changes the path and therefore the logical ID. CloudFormation sees the old logical ID absent from the new template and the new one present, so it performs a **create-then-delete replacement** - a brand-new empty table, and the old one deleted. The same applies to renaming the *construct id of a parent*, which changes every descendant's logical ID at once, and that is how a cosmetic refactor deletes several stateful resources in one deploy.

Note the two aggravating factors: with `RemovalPolicy.DESTROY` (the CDK default for some resources) the old table is actually deleted rather than orphaned; and because the new resource is created *first*, the deploy appears to succeed.

**Two ways to prevent it:**

1. **`RemovalPolicy.RETAIN` (plus deletion protection) on every stateful resource** - tables, buckets, databases, KMS keys. Then a logical-ID change orphans the old resource instead of deleting it: you lose the reference and keep the data, which is a recoverable mistake rather than a career-defining one. Combine with `deletionProtection: true` on DynamoDB/RDS so even a direct delete fails. **This is the essential safety net**, and I would enforce it with a CDK Aspect or a `cdk-nag`/`cfn-guard` rule that fails the build if a stateful construct lacks it.
2. **Review the change set / diff, and gate on replacement.** `cdk diff` marks replacements explicitly, and CloudFormation change sets show `Replacement: True`. A pipeline stage that **fails automatically if any change set contains a replacement of a stateful resource type** - or requires an explicit human approval with an acknowledgement - turns this from an accident into a decision. This is the control that catches it before deployment rather than after.

Supporting practices: **`overrideLogicalId`** to pin a logical ID when you genuinely must rename a construct; keeping **stateful resources in their own stack** with a slower change cadence (Q234), so application refactors cannot touch them; and never running `cdk deploy` from a laptop against production.

*Hook: a replacement you caught in a diff, or one you did not, and the guardrail you added afterwards.*

### Q233. Change sets, stack policies, `DeletionPolicy`, drift

- **Change sets** - a computed diff between the current stack and a proposed template, showing each resource's action and, critically, **`Replacement: True/False`**. Creating and reviewing a change set before executing is the difference between deploying and hoping.
- **Stack policies** - a JSON policy attached to a stack that **denies update actions on specified resources** (`Update:Replace`, `Update:Delete` on a `LogicalResourceId` or resource type). It is enforced by CloudFormation itself, so it protects even against a correct-looking template. Underused, and the right tool for "this database must never be replaced by a deploy".
- **`DeletionPolicy` / `UpdateReplacePolicy`** - `Retain`, `Snapshot` or `Delete`. Both matter: `DeletionPolicy` covers stack deletion, and **`UpdateReplacePolicy` covers the replacement case of Q232**, which people forget. Set both to `Retain` (or `Snapshot` for RDS) on stateful resources.
- **Drift detection** - compares live resource configuration against the template and reports differences caused by out-of-band changes. It is detective, not preventive, and it does not cover every property or every resource type.

**What I configure on every production stack:**

1. `DeletionPolicy: Retain` **and** `UpdateReplacePolicy: Retain` on all stateful resources, plus service-level deletion protection.
2. **Termination protection** on the stack.
3. A **stack policy** denying replace/delete on the stateful resources.
4. **Change-set-based deployment only**: the pipeline creates a change set, publishes the diff into the PR or the approval step, and executes it - never `deploy --require-approval never` into production with a direct update.
5. **A pipeline gate on replacements** of stateful types (Q232).
6. **`--role-arn`** so CloudFormation acts with an explicit, scoped service role rather than the deployer's identity - which means a compromised pipeline credential cannot exceed what CloudFormation is permitted to do.
7. **Drift detection on a schedule**, with findings raised as tickets, plus an SCP/permission model that makes out-of-band change rare in the first place (no human write access to production, Q3).
8. **Rollback configuration with CloudWatch alarms** (`RollbackConfiguration`), so a deploy that breaches an alarm during its monitoring period rolls back automatically.

*Hook: a stack policy or retain policy that saved you, or the absence of one that cost you.*

### Q234. Stack boundaries

**The rule I use: a stack is a unit of deployment lifecycle and blast radius.** Things that change together, at the same cadence, with the same rollback semantics, and owned by the same team, belong in one stack. Everything else does not.

That produces a consistent layering:

| Layer | Cadence | Examples | Why separate |
| --- | --- | --- | --- |
| **Foundation** | Rarely (months) | VPC, subnets, TGW attachments, hosted zones | A change here is high-risk and unrelated to application releases; and everything depends on it |
| **Stateful / data** | Rarely, carefully | DynamoDB tables, S3 buckets, RDS clusters, KMS keys | Must survive application redeploys and refactors (Q232). Separate stack means an application rollback cannot touch the data |
| **Shared platform** | Occasionally | Shared ECR repositories, log destinations, cross-account roles, EventBridge buses | Multiple teams consume these |
| **Application** | Continuously (per commit) | Functions, APIs, state machines, queues, alarms | Fast, frequent, independently rollbackable |
| **Edge / global** | Occasionally | CloudFront, WAF, certificates in `us-east-1` | Different region, slow updates (a CloudFront change takes minutes) - mixing it with application deploys makes every deploy slow |

**What should never share a stack:**

- **Stateful and stateless resources** - the most important rule, for the reason above.
- **Resources with very different update times.** A CloudFront distribution or an RDS instance modification takes many minutes; putting one in your application stack makes every deploy and every rollback take that long, which directly damages MTTR.
- **Resources owned by different teams**, because a stack is a single serialized update - one team's failed deploy blocks the other's (and a stack in `UPDATE_ROLLBACK_FAILED` blocks everyone, Q236).
- **Anything approaching the 500-resource limit** (Q198), which for a large serverless application arrives faster than expected because each function brings a role, a log group, an alarm and permissions.

And the counter-rule, because over-splitting is also a failure mode: **do not split so finely that a single logical change requires an ordered multi-stack deployment**, because you have then invented a distributed transaction with no coordinator. Cross-stack references are what make this painful (Q235), so the split should follow the boundaries where references are few and stable.

*Hook: a stack split (or merge) you performed, and the deploy-time or blast-radius problem that motivated it.*

### Q235. Cross-stack references

Three mechanisms:

1. **CloudFormation exports/imports** (`Fn::ImportValue`). Stack A exports a value; stack B imports it.
2. **SSM Parameter Store**. Stack A writes a parameter; stack B reads it (at deploy time via a dynamic reference, or at runtime).
3. **Construct-level reference in CDK** - pass the construct object between stacks in the same app; CDK generates an export/import pair automatically.

**The one that makes a stack impossible to delete: CloudFormation exports.** The mechanism is that **an export cannot be deleted or modified while another stack imports it.** So:

- You cannot delete stack A while stack B imports its export - CloudFormation refuses with `Export ... cannot be deleted as it is in use`.
- Worse, you cannot **change** the exported value's producing resource in a way that would update the export, because the update also fails. So a single import creates a **hard, ordered coupling**: to change A you must first remove the reference from B, deploy B, then deploy A, then re-add. That two-phase dance is the tax, and teams discover it during an urgent change.
- CDK's automatic behaviour makes this easy to create accidentally - passing a bucket from one stack to another silently creates an export/import - which is why a CDK app with several stacks can become undeployable in an order nobody chose.

**SSM parameters avoid the coupling**: the consumer reads a value, and the producer can change or delete it without CloudFormation blocking. The trade-off is that you lose the safety - if the parameter is deleted or wrong, the failure happens at deploy time (or worse, at runtime) rather than being prevented. That is usually the right trade for **loosely coupled, cross-team, cross-lifecycle** references, and I use it as the default across team boundaries.

My practice: **construct references within one app/team where the lifecycle is genuinely shared; SSM parameters (or a well-known naming convention resolved at runtime) across team and lifecycle boundaries; and avoid raw exports for anything on a foundation stack** that many others depend on. CDK's `Fn::ImportValue` avoidance patterns - `SSM StringParameter.valueForStringParameter`, or simply passing the *name* and resolving at runtime - are the practical implementation.

*Hook: a stack you could not delete or update because of an export, and how you untangled it.*

### Q236. A nested stack stuck in `UPDATE_ROLLBACK_FAILED`

**What you do, in order:**

1. **Read the failure reason** on the nested stack's events. `UPDATE_ROLLBACK_FAILED` means the *rollback* itself could not complete - typically because a resource cannot be returned to its previous state: a resource was deleted or modified out of band, an S3 bucket is not empty, an ENI is still attached, a security group is still referenced, a custom resource's Lambda failed or timed out, or an IAM permission was removed mid-flight.
2. **Fix the underlying obstruction manually.** Empty the bucket, detach the ENI, restore the deleted resource, fix the permission, make the custom resource's function respond correctly.
3. **`ContinueUpdateRollback`** on the **parent** stack, not the nested one - nested stacks are managed by the parent, so operations go through it. If a specific resource still cannot roll back, use `ContinueUpdateRollback --resources-to-skip <LogicalId>` to skip it; the stack then reaches `UPDATE_ROLLBACK_COMPLETE` and **that resource is now drifted** - CloudFormation's record of it no longer matches reality, and you must reconcile it deliberately (import, or a subsequent corrective deploy).
4. If it still cannot proceed, the remaining options are ugly: **delete the stack** (with retain policies protecting the data, Q233), or **import** resources into a fresh stack. That is why the retain policies matter so much.
5. **Afterwards**, reconcile drift and verify the stack deploys cleanly with a no-op change set before shipping anything else.

**What it tells me about the stack design:**

- **The stack is too big and too coupled.** A stack containing 200 resources across stateful and stateless layers means one bad resource freezes everything - including the rollback path (Q234).
- **Something changed out of band**, which means human or script access to production resources exists and should not (Q3).
- **Custom resources are a liability**: a Lambda-backed custom resource that does not respond correctly on the rollback path is one of the most common causes here, and it indicates the custom resource lacks proper failure handling and idempotency.
- **Stateful resources are in an application-cadence stack**, so a routine deploy can wedge the database's stack.
- More broadly: **the rollback path was never tested.** If a deploy can fail, the rollback is part of the deployment and deserves the same rehearsal.

The design changes I would make: split stateful out; keep application stacks small; replace custom resources with native support or move the logic into a pipeline step where it can be retried and debugged; enforce no out-of-band change; and use **`RollbackConfiguration` with alarms** so failures are caught early, when rollback is still simple.

*Hook: a wedged stack you recovered, what the obstruction turned out to be, and the structural change you made afterwards.*

### Q237. Terraform versus CDK for AWS specifically

| | Terraform | CDK |
| --- | --- | --- |
| **State** | An explicit **state file** (S3 plus DynamoDB locking, or Terraform Cloud) that you own, back up and occasionally repair. `state mv`, `import`, `taint` give you surgical control - and the ability to corrupt it | CloudFormation owns state, invisibly and reliably. No state file to lose, and no surgical tool either - refactoring means logical IDs (Q232) |
| **Drift** | `terraform plan` shows drift on every run, as part of the normal workflow. This is a genuine advantage | Drift detection is a separate, partial, on-demand operation. Everyday workflow does not surface it |
| **Multi-account / multi-region** | Providers with aliases; one plan can span accounts and regions - powerful and occasionally dangerous | One stack is one account-region; multi-account is multiple stacks in an app (or StackSets). Cleaner boundaries, more stacks |
| **Review experience** | `plan` is a precise, readable, resource-level diff, and it is the artifact people review. Best-in-class | `cdk diff` is good but the *program* is the source, so review means reading imperative code plus a diff. Abstraction can hide a large change behind a one-line edit |
| **Escape hatch** | `null_resource`/`local-exec`, and writing a provider. Raw AWS API access is awkward | **`addPropertyOverride` / `addOverride` / L1 `Cfn*` constructs** - direct access to any CloudFormation property, which means you are never blocked by a missing high-level construct. Very strong |
| **Abstraction and reuse** | Modules: declarative, versioned, well-understood, huge public registry | Constructs: real code, real types, real unit tests, real inheritance. Far more expressive, and far easier to over-engineer |
| **New AWS services** | Waits for the provider | CloudFormation support (and `AwsCustomResource` as a stopgap) |

**My position**: for a **serverless-heavy, AWS-only estate with a platform team**, CDK - because the `grant*` least-privilege generation, shared constructs and testability compound across dozens of services. For a **mixed or multi-cloud estate, or an organization already fluent in Terraform**, Terraform - because tool consistency and the quality of `plan` as a review artifact outweigh CDK's abstraction benefits, and because "the team can debug it at 3 a.m." is a real criterion.

The two things I would say beyond the comparison: **CDK's greatest risk is that abstraction hides blast radius** (a construct rename replacing a table, Q232), so the diff gate matters more than with Terraform; and **Terraform's greatest risk is the state file**, so remote state with locking, versioning and a tested restore is non-negotiable. And whichever you pick, **pick one per resource** - overlapping ownership is worse than either tool's weaknesses.

*Hook: a CDK-versus-Terraform decision you made, and whether the reasoning held up a year later.*

### Q238. Lambda versions, aliases and weighted canaries

**Versions** are immutable snapshots of code plus configuration, numbered on publish. **`$LATEST`** is the mutable working copy. **Aliases** are named pointers to a version (`prod` → 42), and an alias can carry a **routing configuration** that sends a percentage of invocations to a *second* version.

**How the canary works**: the alias `prod` points at version 42 with `additionalVersionWeights: {43: 0.05}`. Invocations of the alias ARN are routed 95/5 between versions 42 and 43, **per invocation, randomly**. CodeDeploy automates the shift (Q239): 5 percent, bake, alarm check, then 10, 25, 50, 100 - rolling back by resetting the weight if a CloudWatch alarm fires. Because the routing is on the alias, everything pointing at the alias ARN - API Gateway integrations, event source mappings, EventBridge targets - participates without reconfiguration.

**What a shifting alias breaks** - the substance of the question:

1. **Any state that is version-scoped.** **Provisioned concurrency** is configured per version/alias, so the new version has none unless you provision it - meaning the canary's 5 percent is served with cold starts and looks worse than it is, and a naive alarm rolls back a perfectly good release. Same for **SnapStart**, whose snapshot is per version and must be created (there is a delay after publishing before restore is fast).
2. **Environment-variable and configuration changes are part of the version**, so the two versions can have different config - which is a feature, but it means a config-only change also needs a publish, and a shared external configuration read at runtime (AppConfig, Parameter Store) is *not* versioned, so both versions see the new value. That asymmetry causes "the canary passed and the full rollout failed" when the config change is the actual problem.
3. **Anything assuming a single code version at a time**: an in-flight schema migration, a state machine passing payloads between steps where step 3 is old and step 4 is new (Q146), a queue where one version's messages are consumed by the other. Both versions must be **mutually compatible** for the duration - expand-contract again.
4. **Stateful assumptions in the execution environment**: caches keyed differently between versions, or a `/tmp` layout change (Q81).
5. **Event source mappings and `$LATEST`**: a mapping pointing at the *unqualified* function ARN follows `$LATEST` and therefore bypasses the alias entirely - so your canary does not apply to the async path. Mappings must target the **alias ARN**. This is a very common gap.
6. **Observability**: metrics are emitted per version (via the `ExecutedVersion` dimension), so dashboards and alarms must be version-aware or the canary's failures are averaged away.

*Hook: a canary deployment of a function, and the version-scoped setting that tripped you up.*

### Q239. CodeDeploy for Lambda and ECS

**For Lambda**, CodeDeploy manipulates the alias routing of Q238 with a named strategy: `AllAtOnce`, `Linear10PercentEvery1Minute` (and variants), `Canary10Percent5Minutes` (and variants). Around it:

- **`BeforeAllowTraffic` hook** - a Lambda you write, run *before* any traffic shifts. Use it for smoke tests against the new version's *qualified* ARN, schema checks, or verifying a dependency. It must report success or failure to CodeDeploy.
- **`AfterAllowTraffic` hook** - runs after the shift completes; use it for integration verification and for cleanup.
- **Automatic rollback on CloudWatch alarms** - CodeDeploy monitors the alarms you attach and resets the alias weight if one fires during the deployment.

**For ECS**, CodeDeploy does blue/green with two target groups behind the ALB: it launches the new task set (green), runs `BeforeAllowTestTraffic`/`AfterAllowTestTraffic` against a **test listener**, shifts the production listener (all at once, linear or canary), then keeps blue running for a **termination wait time** during which rollback is instant (just shift the listener back). Hooks: `BeforeInstall`, `AfterInstall`, `AfterAllowTestTraffic`, `BeforeAllowTraffic`, `AfterAllowTraffic`.

**What the rollback does not undo** - the important part:

- **Database and schema migrations.** If the release ran a migration, shifting traffic back points old code at a new schema. This is why migrations must be **backward compatible and decoupled from the deploy** (expand-contract), and why "we have automatic rollback" is not a substitute for that discipline.
- **Any side effect the new version already produced**: messages published in a new format, events emitted with a new schema, rows written with new semantics, files written to S3, notifications sent, third-party calls made. Downstream consumers have already seen them.
- **Consumed messages.** If the canary version processed and deleted SQS messages incorrectly, they are gone. Rollback does not un-consume.
- **Configuration and external state**: an AppConfig flag flipped, a Parameter Store value updated, a feature toggled - none of these are in the deployment artifact, so rollback leaves them changed.
- **Cache and derived state**: a poisoned cache entry, a corrupted materialized view, a search index updated with the new format.
- **The in-flight requests** that already failed - rollback restores service, it does not retroactively satisfy those users, which matters for the error-budget accounting.

So the honest framing: **rollback restores the code path, not the world.** The design implication is that every release must be reversible *in effect*, which is a data-modelling and contract discipline, and automated rollback is the fast path for the subset of failures where code is the whole problem.

*Hook: a rollback that restored the deployment and did not restore the system, and what you changed about migrations or contracts afterwards.*

### Q240. Configuration for serverless: env vars, Parameter Store, AppConfig, Secrets Manager

| | Environment variables | SSM Parameter Store | AppConfig | Secrets Manager |
| --- | --- | --- | --- | --- |
| Retrieval latency | **Zero** (already in the process) | ~10-40 ms per call, or ~0 with the extension's local cache | ~0 with the extension (local cache, background poll) | ~20-50 ms per call, or ~0 with the extension |
| Cost per invocation | Free | Standard parameters free to store; **API calls charged above the free throughput tier**, advanced parameters charged per parameter and per call | Per configuration-request and per session | **Per secret per month plus per 10,000 API calls** - the most expensive per call |
| Change without redeploy | **No** - a change is a function configuration update (and a new version) | Yes | **Yes, with a controlled rollout** | Yes |
| Rotation | No | Manual/automation | n/a | **Built-in rotation with Lambda rotators** for RDS and others |
| Encryption | KMS-encrypted at rest, but **visible in the console and in `GetFunctionConfiguration`** to anyone with that permission | SecureString with KMS | Not for secrets | Purpose-built, with resource policies |
| Best for | Non-secret, per-environment, stable values: table names, endpoints, log level | Non-secret configuration shared across functions; also good for cross-stack references (Q235) | **Feature flags and dynamic configuration with safe deployment** (Q242) | Credentials, API keys, anything requiring rotation |

**My layering**: environment variables for anything stable and non-secret (they are free and fastest, and being part of the version is a *feature* for auditability); **Parameter Store** for shared, non-secret configuration; **AppConfig** for anything an operator might change at runtime, especially flags and kill switches; **Secrets Manager** for credentials, with the **Parameters and Secrets Lambda extension** so retrieval is a local HTTP call against a cache rather than an API call per invocation (Q241).

The rule that matters most: **never put a secret in an environment variable**. Not because of encryption at rest - they are encrypted - but because any principal with `lambda:GetFunctionConfiguration` can read it, it appears in the console, it is captured in CloudFormation templates and CI logs, and it cannot be rotated without a deployment. That is a hard line worth stating.

*Hook: a configuration model you standardized, and how you handled rotation without a redeploy.*

### Q241. A secret fetched on every invocation `[T]`

**The arithmetic at 50 million invocations/month:**

- **Secrets Manager API cost**: charged per 10,000 API calls (about $0.05). 50,000,000 / 10,000 x $0.05 = **$250/month** in API charges alone, for one secret, for one function.
- **Latency and compute cost**: a `GetSecretValue` call is ~20-50 ms including TLS and KMS decrypt. At 30 ms and 512 MB, that is `50e6 x 0.03 s x 0.5 GB = 750,000 GB-s` ≈ **$12.50/month** of pure waiting - small, but it is also **30 ms added to every user's p50**, which is the real cost.
- **KMS**: each decrypt is a KMS request (charged per 10,000), adding roughly another **$150/month** unless it is cached.
- **Throttling risk**: Secrets Manager and KMS both have request-rate quotas. At 50 million/month (~20/second average, far more at peak) a spike can hit them, producing intermittent failures that look like application bugs (Q198).

Total: roughly **$400/month and 30 ms of latency per request** for information that changes every 30 days.

**The correct caching design**, in order of preference:

1. **The AWS Parameters and Secrets Lambda Extension.** Add the layer; the extension runs alongside your function, fetches the secret, caches it locally with a configurable TTL, and serves it over `http://localhost:2773/...`. Retrieval becomes a localhost call (~1 ms), API calls drop to roughly one per TTL per execution environment, and **rotation is picked up automatically when the TTL expires** - which is the property that makes this better than hand-rolled caching. This is the answer.
2. **In-process cache with a TTL** (Powertools' parameters utility, or the AWS Secrets Manager Java caching client): fetch in `INIT`, cache in a static field with an expiry, refresh on expiry **and** on an authentication failure (so a rotation mid-TTL self-heals rather than failing until the TTL expires). The failure-triggered refresh is the part people omit, and it is what makes rotation safe.
3. **Do not use a secret at all.** The best version of this answer: **IAM authentication** removes the secret entirely - RDS IAM auth or RDS Proxy with IAM (Q162), and IAM/SigV4 for AWS services. If there is no credential, there is nothing to fetch, cache, rotate or leak.

And the caveats to state: with **SnapStart** a secret cached in `INIT` is captured in the snapshot and will be stale on restore, so the refresh must be in `afterRestore` (Q74); and the TTL is a direct trade between cost/latency and rotation lag, so pick it from the rotation schedule (a 5-15 minute TTL against a 30-day rotation is comfortable).

*Hook: a per-invocation secret or parameter fetch you eliminated, and the cost and latency you recovered.*

### Q242. AppConfig feature flags and deployment strategies

**What AppConfig is**: a configuration service with a **validation and controlled-rollout pipeline** in front of the data. You define an application, environments, and configuration profiles (freeform JSON/YAML, or the **feature-flag** profile type with a schema for flags and attributes). Then a **deployment** rolls a new configuration version out over a chosen **deployment strategy**.

**Deployment strategies**: growth type (linear or exponential), growth rate, deployment duration, **bake time**, and **CloudWatch alarm monitors**. So "roll this flag out to 10 percent of hosts/sessions over 20 minutes, bake for 10, and **automatically roll back** if this alarm fires" is a configuration, not a script.

**What it gives you over a Parameter Store value:**

1. **Validators.** A JSON Schema and/or a **Lambda validator** run *before* the configuration is allowed to deploy. So a syntactically or semantically invalid configuration cannot reach production - which is a whole class of outage removed, because bad configuration is one of the most common causes of them.
2. **Gradual rollout with automatic rollback on alarms.** A Parameter Store value changes for everyone, instantly, with no monitoring and no undo. That is the single biggest difference: **configuration becomes a progressive deployment with the same safety properties as a code deploy.**
3. **First-class feature flags**: typed flags with attributes and constraints, per-environment values, and the option of variants - rather than a JSON blob you parse and validate yourself.
4. **The extension/agent** handles polling, caching and session management, so the client does not implement it (and the retrieval is a localhost call, Q241).
5. **Deployment history and audit** per environment, so "what changed, when, by whom" is answerable - which for configuration is usually much harder than for code.

**What it costs**: per-configuration-request and per-session pricing (so a high-volume function needs the extension's caching, and you should model it), another concept for the team, and the fact that flags accumulate - so I would insist on an owner and an expiry date per flag, and a periodic cleanup, because a hundred stale flags is its own reliability problem.

**Where I use it**: kill switches for dependencies (the manual circuit breaker of Q204), progressive feature enablement decoupled from deploys, per-tenant rollout, and operational tuning values (timeouts, batch sizes, concurrency limits) that you want to change during an incident without a deploy. **Where I do not**: secrets, and anything that should be immutable per version for auditability.

*Hook: a flag or dynamic configuration change you rolled out progressively, and a validator or alarm rollback that caught something.*

### Q243. Testing serverless

**The layers, and where I draw the line:**

1. **Unit tests** - the handler's logic with the AWS boundary abstracted behind an interface. Fast, numerous, and they should cover business rules, error classification and edge cases. What they must **not** do is assert on mocked AWS behaviour, because that only tests your mock.
2. **Local emulation** - `sam local invoke`/`start-api`, LocalStack, DynamoDB Local, Testcontainers with LocalStack. Genuinely useful for **fast inner-loop iteration** (does the handler parse this event, does the query return what I expect) and for CI where cloud resources are impractical. The limits are real and must be stated: emulators do not reproduce **IAM** (the number-one source of deploy-time failures), event source mapping behaviour and batching, throttling and concurrency, service quotas, eventual consistency, cold starts, VPC networking, or the exact event payloads of every trigger. So a green local suite tells you the logic works, not that the system works.
3. **Integration tests against real cloud resources** - an ephemeral, per-branch deployed stack (Q244) exercised by tests that call the real API Gateway, the real DynamoDB table and the real queues. **This is the tier that catches what matters in serverless**: IAM policies, resource policies, trigger wiring, payload shapes, timeouts, and the actual behaviour of managed services.
4. **Contract tests** for event schemas between producers and consumers (Q108), run in the producer's pipeline.
5. **End-to-end / synthetic** in a staging and then production environment, plus canaries in production (Q195).

**Where the line goes**: unit tests for logic; **integration tests against real AWS for anything involving a service boundary**; local emulation only as a developer convenience, never as the gate. The strong version of this position - and the one I would defend - is that **in a serverless architecture most of your system *is* the managed-service configuration**, so a test strategy that mocks all of it is testing the small part you wrote and none of the part that breaks.

**What I refuse to mock:**

- **IAM.** Never. It is the most common cause of failure and it is untestable by mocking.
- **Event source mapping semantics** - batching, partial batch failure, retry, ordering (Q118-121). These behaviours are the actual contract and mocks encode your misunderstanding of them.
- **The service that owns correctness**: DynamoDB conditional writes and transactions, SQS visibility/dedup semantics, Step Functions retry behaviour. Use the real thing (or DynamoDB Local for pure query logic, with a real-cloud test for the conditional/transactional paths).
- **The third-party API's failure modes** - those I mock deliberately in unit tests *and* verify against a sandbox, because that is where the interesting behaviour is.

*Hook: a bug that only a real-cloud test would have caught, and how you changed your test strategy.*

### Q244. Ephemeral per-branch environments

**Why they are cheap for serverless**: almost every component costs nothing when idle. A branch stack with 40 Lambda functions, an HTTP API, five DynamoDB tables in on-demand mode, some queues and a state machine costs **cents per day** if nobody calls it - there is no cluster, no load balancer hour, no instance, no minimum node count. That is transformational compared with a container stack, where each environment implies an ALB (hourly), a minimum of two tasks per service, and possibly a cluster. It means "one environment per pull request" goes from a platform luxury to a default.

**What makes it work in practice**: everything named with the branch/PR identifier (CDK stack name, table names, queue names, function names), a single command in CI to deploy and to destroy, and a teardown triggered on PR close **plus a scheduled reaper** for the ones that leak (they always leak).

**What makes it impossible for some resources:**

- **Genuinely global or account-unique names**: an S3 bucket name (globally unique), a CloudFront distribution's CNAME/certificate, a custom domain name, a Cognito domain prefix. Workable with a suffix, but not for anything with an externally registered name.
- **Slow-to-create resources**: a CloudFront distribution (minutes), an RDS/Aurora cluster (minutes to tens of minutes), an OpenSearch domain, an EKS cluster. These blow the create-and-destroy model, so the pattern becomes **share a long-lived instance across ephemeral environments** (one Aurora cluster with a schema or database per branch, one OpenSearch domain with an index per branch).
- **Quota-bound resources**: VPCs, NAT gateways, interface endpoints, ENIs, Elastic IPs, KMS keys (which have a mandatory 7-30 day deletion window, so churning them accumulates pending deletions), and per-account limits on many services. Fifty branch environments each with a VPC and NAT gateways is both expensive and quota-blocked - which is a strong argument for keeping branch stacks **out of a VPC** (Q40).
- **Data**: an environment is only useful with data. Seeding a realistic (and anonymized) dataset per branch is the real work, and for large datasets it is the reason ephemeral environments fail to be adopted.
- **Externally registered integrations**: a third-party webhook, an OAuth redirect URI, a partner IP allow-list - each needs a per-environment registration that usually cannot be automated (the same asymmetry as Q223).
- **Stateful resources with retain policies**, which by design survive the teardown and accumulate.

**So the practical design**: a per-branch stack containing all the *stateless and cheap-stateful* resources, sharing a small number of long-lived, slow, or quota-bound resources (a VPC if truly needed, a database cluster, a search domain, a certificate) provisioned once per environment tier, with strict naming, automatic teardown and a cost tag so the total is visible.

*Hook: an ephemeral-environment setup you built, what you had to share rather than duplicate, and how you handled seed data.*

### Q245. The delivery platform for 60 serverless services across four accounts `[A]`

**Clarify first**: how many teams, and does each own its services end to end? What is the current deploy frequency and the current pain? What is the regulatory posture (does a human approval need to exist)? Is there an existing CI tool the organization is committed to? And are the 60 services genuinely independent, or do they share libraries and events?

**Accounts**: `shared-services` (artifacts, shared ECR, pipeline roles), `dev`, `staging`, `prod` - matching the four given. Deploys reach each account by assuming a scoped role from CI via **OIDC** (Q29), and **no human has standing write access to `prod`** (Q3).

**Repository layout: one repository per service** (polyrepo), plus a small number of shared repositories - a **constructs library** (the paved road), a **shared workflows** repository, and an **events/schemas** repository. Reasoning: 60 services with independent lifecycles and independent teams get independent CI, independent versioning and independent blast radius; the coordination cost that a monorepo solves (atomic cross-service change) is better solved here by contract tests and additive event evolution (Q108). I would revisit this if the services turned out to be tightly coupled - and I would say that condition out loud rather than asserting polyrepo as doctrine.

**IaC: CDK** (Q230), with a **published constructs library** as the core platform asset. `StandardHttpService`, `StandardEventConsumer` and `StandardScheduledJob` constructs that bake in: log group with retention and a subscription filter (Q189), Powertools layer and structured logging, X-Ray tracing, the mechanical alarm set (Q183), DLQ and `OnFailure` destination on every async path (Q124), mandatory tags (Q14), `RemovalPolicy.RETAIN` on stateful resources (Q232), and `grant*`-generated least-privilege roles (Q30). **This is where the leverage is**: consistency comes from a library teams *want* to use, not from a document.

**Stack layout per service** (Q234): `foundation` (rare), `data` (stateful, retained, deletion-protected), `app` (per-commit), and shared `edge` in `us-east-1`.

**Pipeline shape** (per service, from the shared reusable workflow):

```
PR:      lint, unit tests, cdk synth, cdk diff posted to the PR,
         policy checks (cfn-guard / cdk-nag), SCA + secret scan,
         deploy to an ephemeral PR stack in dev + integration tests (Q243, Q244)
merge:   build once -> versioned artifact + SBOM + signature, published to shared-services
         deploy dev -> integration tests
         deploy staging -> integration + contract tests + smoke
         (automatic promotion; a gate here only if regulation requires it)
prod:    change set created, replacement gate on stateful types (Q232),
         CodeDeploy canary on the Lambda alias (10% / 5 min) with alarm rollback (Q239),
         bake, then 100%
```

**Promotion**: the **same artifact and the same synthesized template**, parameterized per environment - build once, deploy many. Configuration differences come from Parameter Store/AppConfig per environment, never from a rebuild (Q240).

**Rollback**: automatic via CodeDeploy alarm rollback within the deployment window; manual by re-pointing the alias to the previous version (seconds) or redeploying the previous artifact. Documented rollback-safety per release, because rollback does not undo migrations or emitted events (Q239) - so the platform provides an **expand-contract migration checklist** and refuses to make schema changes part of an application deploy.

**Paved road versus escape hatch:**

- **Paved road**: the shared workflow, the constructs library, CDK, the four-account model, the standard observability and alarm set, the promotion path, per-branch ephemeral environments, and the event-schema registry. A team using it gets a production-ready service in a day and never writes an IAM policy or an alarm by hand.
- **Escape hatch**: teams may use CDK L1 constructs or raw CloudFormation for anything the library does not cover (this is CDK's genuine strength, Q237); they may add their own pipeline stages; they may opt out of a specific alarm with a recorded reason. What they may **not** opt out of: OIDC-based deployment, the policy checks, tagging, log retention and shipping, the stateful-replacement gate, and DLQs on async paths. The distinction I would state: **the escape hatch is for capability, not for compliance.**

**How I would know it works**: deploy frequency and lead time per service, change failure rate, adoption of the constructs library (the honest metric - if teams route around the paved road, the road is bad), the number of services meeting the standard observability baseline, and time-to-first-deploy for a new service. Plus one qualitative check: can a team deploy to production on a Friday afternoon without asking anyone?

**What I would sequence first**: OIDC and the account model, then the shared workflow, then the constructs library with two willing pilot teams, then migration service by service - and explicitly **not** a big-bang standardization mandate, because a platform adopted under duress is maintained under duress.

*Hook: a delivery platform you built for a serverless estate, the adoption rate of the paved road, and what you had to change to get teams onto it.*

---

## 16. Cost engineering

### Q246. Price a Lambda function

**50 million invocations/month, 300 ms average, 512 MB**, `x86`, `us-east-1`, ignoring the free tier:

```
Requests:  50,000,000 / 1,000,000 x $0.20            = $10.00
Compute:   50,000,000 x 0.300 s x 0.5 GB = 7,500,000 GB-s
           7,500,000 x $0.0000166667                 = $125.00
                                              Total  ≈ $135/month
```

(Rounded rates: $0.20 per million requests, $0.0000166667 per GB-second.)

**What is missing from that arithmetic**, and this is the actual content of the answer:

1. **CloudWatch Logs ingestion.** If each invocation writes 1 KB of logs, that is 50 GB/month at roughly $0.50/GB ≈ **$25** - and at 4 KB of logs it exceeds the compute cost (Q188). This is the most commonly omitted line.
2. **The entry tier.** API Gateway HTTP API at ~$1.00 per million is **$50**; REST API at ~$3.50 per million is **$175** - more than the function itself (Q248).
3. **Downstream calls.** 50 million DynamoDB reads and writes, S3 requests, KMS decrypts, Secrets Manager calls (Q241). Usually a larger number than the Lambda charge.
4. **Provisioned concurrency**, if used - an hourly charge per unit, 24x7, whether invoked or not.
5. **Data transfer**: NAT gateway data processing if the function is in a VPC (Q35), cross-AZ, and egress.
6. **Tracing and metrics**: X-Ray per trace, custom metrics per unique dimension combination (Q186).
7. **Duration rounding**: billed per **1 ms**, so short functions are not over-billed - but the *request* charge dominates for very short functions, which is a different optimization (batch more per invocation).
8. **`arm64`** would cut the compute term by about 20 percent (Q93), and **ephemeral storage above 512 MB** adds a GB-second charge.

The point to make: **the function is rarely the expensive part.** A realistic all-in figure for this workload is $300-500/month, and the Lambda line is a quarter of it - so optimizing the memory setting while ignoring logs and the gateway is optimizing the wrong term.

*Hook: a serverless cost estimate you produced, and the line item that turned out to dominate.*

### Q247. Unit cost of a request through the stack

Per **million requests**, `us-east-1`, using round published rates and assuming a 300 ms / 512 MB function, one 4 KB DynamoDB read and one 1 KB write, a 20 KB response, and 1 KB of logs:

| Component | Rate | Cost per million requests |
| --- | --- | --- |
| CloudFront requests | ~$0.0075-0.01 per 10,000 HTTPS | **~$1.00** |
| CloudFront data out | ~$0.085/GB (first tier, NA/EU) x 20 GB | **~$1.70** |
| API Gateway HTTP API | $1.00 per million | **$1.00** |
| *(REST API instead)* | $3.50 per million | *($3.50)* |
| Lambda requests | $0.20 per million | **$0.20** |
| Lambda compute | 300 ms x 0.5 GB x 1e6 = 150,000 GB-s | **$2.50** |
| DynamoDB on-demand read (1 eventually consistent 4 KB read = 0.5 RRU) | ~$0.125 per million RRU | **~$0.06** |
| DynamoDB on-demand write (1 WRU) | ~$0.625 per million WRU | **~$0.63** |
| CloudWatch Logs ingestion (1 GB) | ~$0.50/GB | **~$0.50** |
| **Total** | | **≈ $7.60 per million ≈ $0.0000076 per request** |

**What the table teaches, which is the point of building it:**

- **Compute is the largest single line** at this duration, so duration and memory tuning (Q249) matter most - but only just.
- **The entry tier is second**, and switching REST → HTTP API saves more than any DynamoDB optimization (Q248).
- **Egress is comparable to compute** for a response-heavy API, so payload size and compression are a first-class cost lever that nobody thinks of as one.
- **DynamoDB on-demand is remarkably cheap** at this access pattern - which is why "move off DynamoDB to save money" is usually wrong, and why *write amplification through GSIs* (Q151) is the thing to watch instead.
- **Logs are not negligible**, and they scale with verbosity rather than with value.

Then the unit-economics move: at 100 million requests/month this path is ~$760, so **cost per request is a metric you can put on a dashboard** and track against feature changes (Q257).

*Hook: a per-request cost model you built, and a decision it changed.*

### Q248. When the entry tier dominates `[T]`

**The arithmetic.** Lambda compute per million requests is `duration x memory x $0.0000166667 x 1e6`. API Gateway REST is $3.50 per million; HTTP API is $1.00.

- A **100 ms / 512 MB** function costs `0.1 x 0.5 x 16.67 = $0.83` per million in compute, plus $0.20 in requests = **$1.03**. REST API at $3.50 is **3.4x the function**. HTTP API at $1.00 is about equal.
- A **300 ms / 512 MB** function is $2.50 + $0.20 = **$2.70**. REST is still larger.
- A **1 s / 1024 MB** function is $16.67 + $0.20 = **$16.87**. Now the gateway is a rounding error.

So the crossover is about **function cost per million**, not about volume: **the entry tier dominates whenever the function is short and small** - which describes most well-written API handlers. Volume only determines whether the absolute number is worth your attention: at 10 million requests/month the difference between REST and HTTP API is $25 and nobody cares; at **1 billion requests/month it is $2,500,000 a year**, and that is a headcount.

**What I change**, in order:

1. **HTTP API instead of REST** unless a REST-only feature is genuinely required (Q50, Q51) - the single largest lever, a configuration change, roughly 70 percent off the entry tier.
2. **CloudFront in front with caching** where any response is cacheable - a cache hit costs CloudFront request pricing only and bypasses the gateway and the function entirely. For read-heavy APIs with even a 30 percent hit ratio this is a large saving *and* a latency improvement.
3. **A Lambda function URL behind CloudFront** for internal or simple services, which removes the gateway charge completely (Q52).
4. **An ALB instead of API Gateway** at very high volume: ALB is hourly plus LCU rather than per-request, and above roughly a few hundred million requests a month it can be significantly cheaper - at the cost of losing the API-management features.
5. **Direct service integrations** so some requests never invoke a function at all (Q53).
6. **Batch or coalesce chatty clients** - a mobile app making six calls per screen is paying the entry tier six times; one composite endpoint (or GraphQL, Q63) is one.

*Hook: an entry-tier cost you reduced, the mechanism, and the annual saving.*

### Q249. Lambda power tuning

**The method**: run the function at a range of memory settings (128, 512, 1024, 1769, 3008, ...) against a **representative payload**, many invocations each, and record duration and computed cost. The **AWS Lambda Power Tuning** state machine does exactly this - you give it a function ARN, a payload and a list of memory values, and it returns a chart of average duration and cost per setting, with a recommended optimum for a chosen strategy (`cost`, `speed`, or `balanced`).

**Why higher memory can lower total cost** (Q75): memory and vCPU are coupled - roughly one full vCPU at 1769 MB, more above. Billing is `memory x duration`. So if doubling memory more than halves duration, cost falls. Concretely:

| Memory | Duration | GB-seconds per invocation | Relative cost |
| --- | --- | --- | --- |
| 512 MB | 2000 ms | 1.000 | 1.00 |
| 1024 MB | 950 ms | 0.950 | 0.95 |
| 1769 MB | 520 ms | 0.898 | 0.90 |
| 3008 MB | 480 ms | 1.410 | 1.41 |

Here 1769 MB is both **4x faster and 10 percent cheaper** than 512 MB, and 3008 MB is faster still but more expensive - because past one vCPU the workload stops parallelizing and you are paying for memory you cannot use. That shape - improvement up to the vCPU boundary, then flattening - is typical for single-threaded CPU-bound code, and it is why the naive "use the smallest memory" instinct is wrong.

**Caveats to state:**

- **I/O-bound functions do not improve**, so more memory is pure cost. Check whether duration is dominated by waiting on a downstream before tuning at all.
- **Tune with a real payload**; a trivial event gives a misleading curve.
- **Watch the *cold start*** separately - a higher memory setting also speeds up `INIT` (more CPU for class loading and JIT), which sometimes justifies a setting the warm-path curve does not.
- **Re-tune after significant changes**, and automate it: a scheduled Power Tuning run against the top-N functions by cost, reporting the delta, is better than a one-off exercise nobody repeats.
- **`arm64`** is a separate 20-percent lever that composes with this (Q93).

*Hook: a power-tuning exercise you ran, the setting you changed, and the effect on cost and p99.*

### Q250. The line items people forget

| Line item | The mechanism |
| --- | --- |
| **NAT gateway data processing** | Charged **per GB through the gateway**, in addition to hourly, and it applies to traffic that never leaves AWS - S3 reads, ECR pulls, DynamoDB, telemetry. Three AZs means three hourly charges. A chatty workload can spend more on NAT than on compute (Q35) |
| **Cross-AZ data transfer** | Charged **per GB in both directions** for traffic between AZs. Hit by: an ALB with cross-zone load balancing, a replica in another AZ, a cache client hitting a non-local node, Kafka/MSK replication, and a NAT gateway in a different AZ from the workload. Silent because no single resource shows it |
| **CloudWatch Logs ingestion** | **Per GB ingested**, and it scales with log verbosity rather than with value. Enhanced monitoring products (Container/Lambda Insights) generate large volumes without anyone deciding to (Q188) |
| **KMS requests** | Charged **per 10,000 requests**. Every Secrets Manager fetch, every SSE-KMS S3 `GET`/`PUT` (unless bucket keys are enabled), every envelope-encrypted DynamoDB access pattern. At high volume with per-invocation secret fetches this is hundreds of dollars (Q241). **S3 Bucket Keys** reduce S3's KMS calls by orders of magnitude and are the standard fix |
| **VPC endpoint hours** | Interface endpoints are billed **per endpoint per AZ per hour** plus per GB. Six endpoints x three AZs is 18 hourly charges *per VPC*, before any traffic - which across 40 accounts is a substantial fixed cost for idle infrastructure (Q36) |
| **EBS snapshots** | Incremental but **cumulative**: automated daily snapshots with no lifecycle policy grow forever, and deleting a volume does not delete its snapshots. Also AMIs (which are backed by snapshots) accumulate per build |

Honourable mentions I would add: **idle provisioned concurrency**, **incomplete multipart uploads** (Q172), **non-current S3 object versions** (versioning without an expiry rule quietly doubles storage), **unattached EBS volumes and unassociated Elastic IPs**, **CloudWatch custom metric cardinality** (Q186), **empty-receive SQS polling** (Q104), **Intelligent-Tiering monitoring fees on small objects** (Q171), and **dev/test environments left running**.

The unifying property: **every one of these is a charge with no obvious owner** - it does not belong to a resource anyone considers theirs, so nobody looks at it. Which is why cost attribution (Q255) and a monthly review of the *usage-type* breakdown, not just the service breakdown, is the actual control.

*Hook: a forgotten line item you discovered, how you found it, and its size.*

### Q251. Data transfer pricing rules

**Free:**

- **Data in** from the internet, always.
- **Within the same AZ** using private IPv4 addresses.
- **To and from S3, and from S3 to CloudFront** (origin fetches).
- **Through a gateway VPC endpoint** (S3 and DynamoDB) - no per-GB charge and no hourly charge.
- **To CloudFront from any AWS origin.**
- Traffic to most AWS services within the same region over private addressing (with the NAT caveat below).

**Charged:**

- **Out to the internet** - per GB, tiered, region-dependent. This is the headline rate people quote.
- **Cross-AZ**, in **both** directions, per GB. Cheap per GB and large in aggregate.
- **Cross-region**, per GB, at a higher rate than cross-AZ, charged on egress from the source region.
- **Via a NAT gateway** - the data-processing charge applies to *everything* through it, including traffic to AWS services in the same region (Q250).
- **Via a Transit Gateway** - per-GB data processing per attachment, so a VPC-to-VPC flow through TGW is charged, potentially twice.
- **Via an interface VPC endpoint / PrivateLink** - per GB, plus hourly per AZ.
- **Out via CloudFront** - per GB, but at lower rates than direct regional egress, with a large free tier.
- **Between an ALB/NLB and targets in another AZ** when cross-zone load balancing is enabled (free for ALB now, charged for NLB - a real gotcha).

**The three practical consequences worth stating:**

1. **Same-AZ private traffic is free, so AZ placement is a cost decision**, not only a resilience one - and this creates a genuine tension with multi-AZ resilience that you should name rather than pretend away.
2. **A gateway endpoint is free and a NAT gateway is not**, so the single highest-leverage network cost action in most accounts is adding S3/DynamoDB gateway endpoints (Q36).
3. **CloudFront egress is cheaper than S3 or EC2 egress**, and origin fetches are free - so putting a CDN in front of anything serving bytes to the internet is a cost reduction as well as a latency one (Q62).

*Hook: a data transfer charge you tracked down, and the endpoint or placement change that removed it.*

### Q252. Savings Plans, Reserved Instances and Spot

- **Compute Savings Plan** - commit to a **dollars-per-hour** spend for 1 or 3 years and receive a discount (up to ~66 percent for 3-year, all-upfront) applied automatically to **EC2 (any instance family, size, OS, tenancy, region), Fargate, and Lambda** (including provisioned concurrency). Maximum flexibility, slightly lower discount than the alternatives.
- **EC2 Instance Savings Plan** - commit to spend within a specific **instance family in a specific region**; higher discount (up to ~72 percent), less flexibility (you may change size, OS and AZ within the family).
- **Reserved Instances** - still relevant for services Savings Plans do not cover: **RDS/Aurora, ElastiCache, OpenSearch, Redshift, DynamoDB reserved capacity**. Standard RIs give the biggest discount and the least flexibility; Convertible RIs trade discount for exchangeability.
- **Spot** - up to ~90 percent off, interruptible with a 2-minute notice (Q90). Not a commitment; a capacity strategy.

**What a Compute Savings Plan covers** is the key fact: because it covers Fargate *and* Lambda, a serverless-first estate can commit against its baseline compute regardless of how the workload is packaged - which removes the traditional objection that commitments lock you into an architecture. It does **not** cover: DynamoDB, S3, data transfer, RDS, ElastiCache, or the request-count portion of Lambda (only the duration/GB-second component).

**How to size a commitment safely:**

1. **Measure a stable baseline** over at least 3 months from Cost Explorer, looking at the **hourly** on-demand spend for eligible services. Find the *floor* - the level you are above essentially every hour.
2. **Commit to 60-80 percent of that floor**, not to the average and never to the peak. Unused commitment is pure waste, and the discount curve is such that under-committing costs you far less than over-committing.
3. **Prefer 1-year, no-upfront** for a first commitment: a smaller discount for materially less risk while you learn your own patterns. Move to 3-year for the portion of the baseline you are confident about, laddering purchases quarterly so they do not all expire together.
4. **Account for planned change**: a migration off EC2, a Graviton move (which changes the rate but not Savings Plan eligibility), a service being decommissioned, or expected growth. A commitment made the month before a big architectural change is the classic mistake.
5. **Buy centrally in the management account** so the discount shares across the organization (Q8), and decide deliberately whether to enable sharing.
6. **Monitor utilization and coverage** monthly - Cost Explorer reports both - and treat sustained utilization below ~95 percent as an error to correct at the next renewal.

*Hook: a commitment purchase you sized, the utilization you achieved, and whether you over- or under-committed.*

### Q253. DynamoDB cost control

The levers, roughly in order of impact:

1. **Capacity mode.** On-demand is ~6-7x provisioned per unit; provisioned wins above roughly 15-20 percent utilization (Q154). Getting this wrong on a steady high-volume table is usually the single largest DynamoDB cost error.
2. **Reserved capacity** on top of provisioned, for the stable baseline - a further substantial discount for a 1- or 3-year commitment. Underused because it requires knowing your floor.
3. **Item size.** Capacity is metered in 4 KB read / 1 KB write units, rounded **up** (Q148). So an item that grows from 900 bytes to 1.1 KB **doubles** its write cost. Actions: keep large blobs in S3 with a pointer; use short attribute names (they count toward item size, and at scale this is a real percentage); avoid storing derived data you can compute.
4. **Projections and index count.** Every GSI with `ALL` multiplies write cost (Q151). `KEYS_ONLY` or a narrow `INCLUDE` plus an occasional follow-up `GetItem` is frequently cheaper. **Sparse indexes** cut both storage and writes.
5. **Consistency.** Eventually consistent reads are **half** the cost of strongly consistent ones, and the default in most SDK query builders is eventually consistent - but a lot of code sets `ConsistentRead: true` defensively without needing it. Auditing that is a free 50 percent on the read line.
6. **Transactions** cost 2x (Q155) - use conditional writes for single-item atomicity.
7. **TTL** to delete expired data at **no capacity cost** (Q158), rather than a scheduled delete job that consumes WCUs.
8. **Storage class**: the **Standard-Infrequent Access table class** cuts storage cost substantially at higher throughput prices - correct for large, rarely-read tables (audit logs, historical records).
9. **Avoid `Scan`.** A `FilterExpression` does not reduce consumed capacity; you pay for everything examined (Q148).

**The read pattern that quietly doubles cost**: **`ConsistentRead: true` set globally** (half the reads' cost wasted), and its close relative - a **`Query` with a `FilterExpression`** that reads a large item collection and discards most of it. The second is the more insidious one: it looks like an efficient query, it returns three items, and it consumed capacity for three hundred. The fix is a key or index design that makes the filter unnecessary (Q149).

*Hook: a DynamoDB bill you reduced, the lever you used, and the percentage.*

### Q254. Bill up 40 percent with no traffic change and no deploys `[T]`

Six candidates, in the order I would check them:

1. **Something enabled that generates telemetry.** Container/Lambda Insights, X-Ray at 100 percent, verbose logging turned on during an investigation and never turned off, a new custom-metric dimension (Q186), or Config recording all resource types. **Check first**, because it is common, and because it changes the bill without changing traffic. The CloudWatch and Config lines will show it immediately.
2. **Storage growth**: S3 non-current versions accumulating without an expiry rule, incomplete multipart uploads (Q172), CloudWatch Logs with no retention, EBS snapshots and AMIs, DynamoDB tables with no TTL. Storage grows monotonically and the bill grows with it even at flat traffic - so a 40 percent jump can be the month a threshold was crossed.
3. **A commitment expired.** A Savings Plan or Reserved Instance term ended, and the same usage is now billed at on-demand rates - which is exactly the shape of "no change, higher bill". Check the coverage report; this is the single cleanest explanation for a step change.
4. **Data transfer or NAT**: a new VPC endpoint removed (or never added), a workload moved to a different AZ, an S3 bucket accessed cross-region, a partner integration now pulling more data, or replication enabled somewhere. The usage-type breakdown (`DataTransfer-Regional-Bytes`, `NatGateway-Bytes`) tells you fast.
5. **A dev/test or one-off resource left running**: an oversized Aurora cluster from a migration test, an OpenSearch domain, a Fargate service scaled up for a load test, provisioned concurrency set during an incident. Cost Explorer grouped by account and by tag surfaces this.
6. **A change that was not a "deploy"**: a Parameter Store or AppConfig value, a feature flag enabling an expensive code path, a manual console change, a capacity-mode switch on a DynamoDB table, an auto-scaling policy adjustment, or a third-party integration's new sync schedule. Configuration changes are deploys in every sense except the one the team counted.

Two more worth naming: **retries and errors** - a failing downstream causing retry amplification generates real invocations, requests and log volume without any *successful* traffic increase (so "traffic" looked flat); and **AWS price or free-tier changes**, plus the simple case of a month with more days or a currency/tax change.

**The method**: Cost Explorer at **daily granularity** grouped by service to find the *date* of the step, then by **usage type** and by linked account/tag to find the *what*, then CloudTrail around that date for the *who*. The date is the most valuable single piece of information and people skip straight to the service breakdown without it.

*Hook: a cost jump you investigated, what it turned out to be, and how long it took to find.*

### Q255. Cost attribution for serverless

The core difficulty: **most serverless cost is not attributable by resource tags.** Lambda invocations can be tagged by function, but a shared API Gateway, a shared DynamoDB table, a shared EventBridge bus, CloudWatch Logs data, KMS requests and data transfer either cannot carry per-consumer tags or carry only the *owner's* tag, not the *consumer's*.

**The layered approach:**

1. **Accounts as the primary boundary.** Cost is attributable to an account with no tagging effort at all, which is the strongest argument for the account-per-domain-per-environment model of Q3. If a team's workload is in its own account, attribution is solved.
2. **Mandatory tags** on everything taggable, enforced in IaC and the pipeline (Q14), and **activated as cost allocation tags** in the billing console - a step people forget, and until you do it the tags do not appear in Cost Explorer.
3. **Cost Categories** to build the reporting hierarchy: rules combining account, tag, service and charge type into named buckets (`Team-Payments`, `Platform-Shared`, `Untagged`). This is the mechanism that turns messy reality into a chargeback model, and it can also **split** a shared cost across categories by a fixed proportion or by proportional allocation - which is the built-in answer to the shared-resource problem.
4. **Usage-based allocation for shared resources**, which is the serverless-specific technique: emit a **per-consumer usage metric** (EMF, Q185 - requests per tenant, events per team, GB written per service), then allocate the shared bill in proportion to measured usage. For a shared API Gateway across ten teams: total gateway cost x (team's request count / total requests). This is computed monthly by a small job, published to a dashboard, and it is defensible because the underlying counter is real.
5. **Split Cost Allocation Data** for ECS/EKS, which does the equivalent for container CPU/memory.
6. **A named owner for genuinely shared cost.** Some of it - the log-archive bucket, the NAT gateways, the VPC endpoints, the observability platform - is a platform cost, and pretending to allocate it precisely produces arguments rather than decisions. Assign it to the platform team's budget and report it as such.

**The reporting practice**: monthly per-team cost, per-team **unit cost** (Q257), and the "unallocated" bucket as a *tracked metric* that must trend down. If unallocated is 30 percent, the attribution model is not working, and saying so is more useful than a beautiful chart of the 70 percent.

*Hook: a chargeback or showback model you built, how you handled shared resources, and what percentage remained unallocated.*

### Q256. Making cost visible to engineers

**The mechanisms, and what each is for:**

- **AWS Budgets** with actual *and* **forecasted** alerts, per account and per team Cost Category, at 50/80/100 percent of plan. Forecast alerts are the useful ones because they fire while there is still time to act. Add **budget actions** (apply a restrictive policy, stop resources) for sandbox accounts, where a hard stop is appropriate.
- **Cost Anomaly Detection** - ML-based, per service and per Cost Category monitor, which catches step changes and gradual drifts that a fixed budget does not. Tune the threshold so it does not become noise, and route it to the owning team, not to a central mailbox.
- **Cost Explorer / CUR into Athena or QuickSight** for the analysis layer, with daily granularity and usage-type detail (Q254).

**The pattern that actually makes cost visible to engineers who do not read the bill** - because notifications alone do not work:

1. **Put it where they already look.** A weekly automated message into each team's Slack channel: this week's cost, the change versus last week, the top three contributors, and the **unit cost** (cost per thousand requests, per order, per tenant). Not an email to a manager - a message to the team channel, naming their own services.
2. **Report unit cost, not absolute cost** (Q257). Absolute cost rises with success, so engineers correctly learn to ignore it; unit cost falling is unambiguously good engineering, and it makes cost a craft metric rather than a scolding.
3. **Show it in the pull request.** A pipeline step that estimates the cost delta of an infrastructure change (Infracost-style, or a simple rule set: "this adds a NAT gateway: +$35/month", "this adds provisioned concurrency: +$X/month") puts the number at the moment of the decision, which is the only moment it can change anything.
4. **Make the top-N list visible and shared.** A single dashboard of the estate's ten most expensive resources or functions, refreshed weekly, with an owner column. Ownership plus visibility produces action; either alone does not.
5. **Tie it to a review ritual**: a 30-minute monthly cost review per team with two required outputs - one action taken and one question raised. Not a report to be read.
6. **Give engineers read access to Cost Explorer.** A surprising number of organizations lock the billing console to finance, which guarantees that nobody who can fix the cost can see it.

The principle: **cost is a design property, and design happens in pull requests and architecture discussions - so the number must appear there**, not in a monthly finance review three weeks after the decision.

*Hook: a cost-visibility practice you introduced, and a decision an engineer changed because of it.*

### Q257. Unit cost as the target

**Define it as cost per unit of business value**: cost per order, per active tenant, per thousand API requests, per document processed, per million events, per inference. Pick the unit the business already counts, so the number is comparable to revenue.

**Instrumentation:**

1. **Numerator**: the allocated cost for the service or capability, monthly (or daily) - from Cost Categories plus usage-based allocation for shared resources (Q255).
2. **Denominator**: a **business counter you already emit** - orders completed, events processed, tenants active - published as a CloudWatch metric via EMF (Q185) so it lives in the same place as the cost data.
3. **The metric itself**: computed daily by a small job (Athena over the Cost and Usage Report joined to the business counter), published as a custom metric, graphed on the team's dashboard next to latency and error rate, and included in the weekly team message (Q256).
4. **Alarm on it**, not just on absolute cost: a rising unit cost is a regression, in exactly the way a rising p99 is.

**Why it beats total spend as a target:**

- **Total spend rises with success.** A business growing 40 percent with a bill growing 30 percent is *improving*, and a "reduce the bill by 10 percent" target in that context asks engineers to slow the business down. Unit cost separates growth from waste, which is the distinction every cost conversation actually needs (Q260).
- **It makes efficiency work visible and rewardable.** Halving the cost per order is an unambiguous engineering achievement; it survives a traffic doubling, and it does not evaporate the next time marketing runs a campaign.
- **It is comparable across teams and over time**, so it supports goals ("reduce cost per order by 20 percent this half") that are not gamed by deferring work or shutting down environments.
- **It connects to margin**, which is the language the business uses - and it lets you say "this feature costs $0.004 per request, and we charge $0.02" which is a product conversation rather than an infrastructure one.
- **It changes behaviour at design time**: a new architecture's cost per request can be estimated (Q247) and compared against the current one before it is built.

The caveat to state: unit cost can hide an absolute problem (cost per order improving while total spend doubles is still a cash-flow event), so **report both** - unit cost as the engineering target, absolute spend as the budget constraint.

*Hook: a unit cost metric you defined, the number, and how it changed a decision.*

### Q258. Reducing a $40,000/month workload

**Sequence, cheapest-and-safest actions first:**

1. **Measure and attribute (week 1, no changes).** Daily-granularity breakdown by service, usage type, account and tag; identify the top ten line items, which typically account for 80 percent. Compute the current **unit cost** (Q257) so every subsequent change is measured against it. **Do not optimize anything before this** - the intuition about where the money goes is wrong more often than not.
2. **Delete waste (days, zero risk).** Unattached volumes, orphaned snapshots and AMIs, unassociated Elastic IPs, incomplete multipart uploads, non-current S3 versions, idle load balancers, dev environments running at night, forgotten OpenSearch/Aurora clusters, provisioned concurrency nobody needs, log groups with infinite retention. This is usually 5-15 percent and it costs nothing but attention (Q250).
3. **Fix configuration errors (days-weeks, low risk).** S3 lifecycle policies and log retention; DynamoDB capacity mode against measured utilization (Q154); Lambda memory settings via power tuning (Q249); `arm64` where the dependency check passes (Q93); API Gateway REST → HTTP API (Q248); S3/DynamoDB **gateway endpoints** to remove NAT data processing (Q35); S3 Bucket Keys to collapse KMS calls (Q250); turn off telemetry nobody reads and reduce log verbosity (Q188).
4. **Commit to the baseline (one action, immediate effect).** A Compute Savings Plan sized to 60-80 percent of the measured floor, plus reserved capacity for DynamoDB and RIs for RDS/ElastiCache (Q252). This is often the largest single-step reduction and it requires no engineering change - so it should not wait for step 5.
5. **Architectural change (weeks-months, real risk).** Caching to remove downstream calls; a CDN in front of anything serving bytes; batching to reduce per-request charges; moving a steady high-duty-cycle Lambda to Fargate or vice versa (Q94); consolidating chatty client calls; compacting small objects (Q171); spot for interruptible batch (Q90). Each of these needs a design review and a rollback plan.
6. **Renegotiate and re-tier (parallel track).** Enterprise agreement discussions, third-party SaaS tiers, and asking whether a component should exist at all - the cheapest architecture is the one with fewer parts.

**What I would refuse to cut, and say so explicitly:**

- **Multi-AZ redundancy and the standby DR capability.** Collapsing to a single AZ or deleting the standby saves real money and converts a survivable event into an outage. If the business wants to buy that risk, it must be an explicit, documented decision at the executive level, not a line in a cost programme.
- **Backups, PITR and the immutable archive** (Q176). Non-negotiable.
- **The observability needed to operate**: the alarm set, the SLI pipeline, DLQs and their alarms. I would reduce *volume* (retention, verbosity, sampling, cardinality - Q197) but never remove the signals that make an incident diagnosable. Cutting observability to save money is how you pay for it in MTTR.
- **Security controls**: CloudTrail, GuardDuty, Config in production, KMS where required. These are compliance-load-bearing.
- **Staging environments used for pre-production verification**, and per-branch environments if they are why the change failure rate is low. Cutting the safety net to save money is a cost transfer to incidents.
- **Provisioned concurrency on a genuinely latency-critical path**, if the SLO depends on it.

*Hook: a large cost reduction you led, the sequence you used, and the one thing you refused to cut.*

### Q259. Cost reduction followed by degraded reliability `[T]`

Three optimizations that produce exactly this pattern, with a two-month lag:

1. **Removing redundancy that only matters during a failure.** Collapsing to a single NAT gateway, a single-AZ ElastiCache or RDS instance, dropping an Aurora replica, reducing a service from three tasks to one, or deleting the standby region. Nothing changes for weeks because nothing fails - and then an AZ event or an instance replacement (which happens on AWS's schedule, not yours) becomes an outage. The lag is exactly the interval until the first infrastructure failure, which is why the causal link is missed.
2. **Tightening capacity to the observed average.** Rightsizing instances or ACUs to p50 utilization, lowering provisioned throughput or auto-scaling maximums, removing provisioned concurrency, reducing a Savings-Plan-covered baseline. Fine at normal load; then a seasonal peak, a marketing campaign or a retry storm arrives and there is no headroom - and because scaling takes minutes (Q87) or hits a quota (Q198), the result is a saturation collapse rather than a graceful slowdown.
3. **Cutting observability and safety infrastructure.** Reducing log retention and verbosity, dropping X-Ray sampling to near zero, deleting "noisy" alarms, removing staging or per-branch environments, reducing test coverage in CI to shorten builds. Reliability does not fall immediately - **detection and diagnosis** do. Two months later an incident that would have been a 10-minute fix is a 3-hour investigation, and the change failure rate has quietly risen because pre-production verification is weaker.

Two more worth naming: **removing DLQs or shortening message retention** (data loss surfaces only during the next downstream outage), and **aggressive spot adoption on the baseline rather than the margin** (Q90).

**The generalizable insight**: all of these cut **capacity that exists for the failure case**, and its value is zero on every normal day - so a purely cost-driven review will always find it and a purely metrics-driven review will never object. That is a structural bias in cost optimization, and naming it is the point.

**What I do about it**: require every cost change to state **which failure mode it makes worse**, and route anything touching redundancy, headroom, backups or observability through the same review as an architecture change; keep a **reliability regression check** in the cost programme's own reporting (change failure rate, MTTR, SLO attainment before and after); use **unit cost** as the target so cutting capacity is not the only visible lever (Q257); and re-run the DR drill (Q211) after any cost programme, because that is what actually proves the redundancy you kept still works.

*Hook: a cost optimization that came back later as a reliability problem, and the review step you added afterwards.*

### Q260. Cut 25 percent in a quarter on an estate you do not understand `[A]`

**First, negotiate the metric.** Is this 25 percent of absolute spend, or 25 percent per unit of business (Q257)? If the business is growing 20 percent, a flat absolute bill already represents a large efficiency gain, and holding both targets simultaneously may be arithmetically impossible. I would insist on agreeing this in the first meeting and on writing it down, because every subsequent decision depends on it. I would also ask what happens if I find that 25 percent requires reducing resilience - and get agreement on the escalation path *before* I need it.

**Then the plan, by phase:**

**Weeks 1-2: visibility, no changes.**

- Enable/verify the Cost and Usage Report into Athena, and build the breakdown by service, **usage type**, account, tag and day. Daily granularity, because the date of a step change is the most valuable clue (Q254).
- Identify the top 20 line items - usually 80-85 percent of the bill - and the "unallocated" percentage.
- Find the owners. This is the actual work on an estate you do not understand: for each of the top 20, name a team. Where there is no owner, that is a finding in itself.
- Check for the free wins that need no understanding: expired commitments, unattached resources, infinite log retention, missing lifecycle rules, telemetry nobody consumes.

**Weeks 3-4: harvest waste and buy the discount.**

- Delete the unambiguous waste (Q258 step 2). No design review needed; these have no consumers by definition.
- **Purchase a Compute Savings Plan** at 60-80 percent of the measured floor, plus DynamoDB reserved capacity and RIs for stable RDS/ElastiCache (Q252). This is often 8-15 percent of the whole bill from a single action, with zero engineering risk, and it is the fastest path to a visible number - which matters politically because it buys credibility for the slower work.
- Set retention and lifecycle policies everywhere.

**Weeks 5-9: configuration optimizations, per owner.**

- Work the top-20 list with each owning team: capacity mode, memory settings, `arm64`, entry-tier choice, gateway endpoints, log verbosity, index projections, storage classes (Q258 step 3). Each change is small, reversible and measured.
- **Non-production is where I would push hardest**: schedules to shut down overnight and at weekends, smaller instance classes, on-demand DynamoDB, shorter retention. Typically 20-30 percent of an estate's spend and the lowest risk of any category.

**Weeks 10-13: measure, report, and set up the architectural pipeline.**

- Publish the achieved reduction with the breakdown, and the **unit cost** trend.
- Identify the architectural changes that would deliver the next tranche (caching, CDN, batching, compute re-platforming), scoped as projects for the *following* quarter with estimates - because these cannot be done safely in a quarter on an estate you have just met, and promising them is how cost programmes cause outages.

**How I protect reliability throughout** - and I would present this as part of the plan, not as a caveat:

1. **A hard exclusion list stated up front**: multi-AZ redundancy, backups and PITR, the immutable archive, DR capability, security controls, and the observability needed to run an incident. Anything on this list requires an explicit business decision with the risk written down (Q258).
2. **Every change must name the failure mode it affects** (Q259). If the answer is "none", it is a configuration fix; if there is an answer, it goes through architecture review.
3. **Track reliability metrics alongside cost** in the programme's own reporting - SLO attainment, change failure rate, MTTR - so a regression is attributable to the programme rather than discovered a quarter later.
4. **Re-run the DR drill** at the end (Q211).
5. **Change in small, reversible increments with an owner**, never as a central sweep. The fastest way to cause an outage is for a cost team to modify a resource whose purpose they do not know - and on an estate I do not understand, that risk is the dominant one.

**What I would say honestly at the outset**: I expect to find 12-18 percent from waste, commitments and configuration with low risk, and the remaining 7-13 percent will come either from non-production discipline and architectural change (slower than one quarter) or from reducing resilience (a business decision, not mine). Rather than quietly delivering 25 percent by cutting the standby region, I would put both paths in front of the sponsor with numbers. That framing - **here is the safe number, here is what the rest costs in risk, you choose** - is the honest answer and the one I would give.

*Hook: a cost mandate you were given, what you actually delivered against it, and the conversation you had about the gap.*

---

## 17. Well-Architected reviews, design exercises and leadership

> Q261-265 are worked as full design exercises in [scenario-questions.md](scenario-questions.md), Part B. Read the question, spend twenty minutes designing out loud, then compare. Q266-270 are story questions with no scripted answer - use STAR-L and your own material.

### Q266-270. Story questions

No model answer is scripted for these, on purpose - they must be your own. Use **STAR-L** (Situation, Task, Action, Result, **Learning**), keep each to two or three minutes, and always quantify the Result.

Use the cloud story bank in [README.md](README.md) to prepare them, and make sure that across the five you cover: a decision you would make differently (Q266), a cost reduction with a number and something you refused to cut (Q267), an incident you led with a permanent fix (Q268), a standard you drove without authority (Q269), and a build-versus-buy decision in **both** directions (Q270). The most common failure at this level is answering all five from the same project - spread them across Verizon India and Sonata Software, and have the numbers ready.
