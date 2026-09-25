# AWS Interview Questions

Questions are numbered continuously (`Q1`, `Q2`, ...) so that [answers.md](answers.md) can reference them directly.

Difficulty legend:

- `[C]` Core - you must answer this instantly and correctly.
- `[D]` Deep - expected of a senior engineer, requires mechanism-level detail.
- `[T]` Tricky - designed to catch you out; the obvious answer is usually wrong.
- `[A]` Architect - no single right answer, judged on trade-off reasoning.

Each category opens with an **Assumed known** line pointing at the earlier-pack questions this material builds on. If those are shaky, go back before continuing.

The material is anchored **serverless-first** - Lambda, API Gateway, EventBridge, Step Functions, DynamoDB and S3 - with ECS Fargate, EKS and Aurora as the boundary cases. Name the service you are describing, and name its limit; interviewers notice both.

---

## 1. Accounts, Organizations, landing zones and the responsibility line

> Assumed known: `01-java` Q197 (Well-Architected pillars) and `11-security` Q231 (multi-account strategy as a security boundary).

1. `[C]` What does the shared responsibility model actually divide, and how does the line move between EC2, ECS Fargate, Lambda and DynamoDB?
2. `[D]` Why is the AWS account the primary isolation boundary rather than the VPC or the IAM policy? Give three properties an account gives you that a policy cannot.
3. `[D]` Design an account structure for a 60-service, 200-engineer organization. Name each account, its purpose, and who can deploy into it.
4. `[T]` A team proposes one account per service - 60 accounts. What breaks first, and what would you propose instead?
5. `[D]` Organizational units and Service Control Policies: what belongs in an SCP versus a permission boundary versus a pipeline check?
6. `[D]` What does AWS Control Tower actually give you over a hand-rolled Organizations setup, and what does it take away?
7. `[D]` Account Factory / Landing Zone Accelerator: what should a new account have on day zero, before anyone deploys anything?
8. `[D]` Consolidated billing: how do Reserved Instances, Savings Plans and volume discounts behave across a member account boundary?
9. `[T]` Two teams share an account "because it is simpler". Six months later nobody can safely delete anything. Explain the mechanism behind that outcome.
10. `[D]` Regions, Availability Zones and Local Zones: what is actually independent, and what is shared across AZs in the same region?
11. `[T]` Your AZ identifier `us-east-1a` and a partner's `us-east-1a` are not the same physical location. Why, and where does that matter?
12. `[D]` How do you choose a region? List the factors in the order you actually apply them.
13. `[D]` Which AWS services are global, which are regional, and which are zonal? Name a design bug caused by getting one of them wrong.
14. `[D]` Tagging strategy: what tags are mandatory, how do you enforce them, and what do you do about resources that cannot be tagged?
15. `[A]` You inherit a single AWS account containing production, staging and three experiments, with no OUs and no tagging. Give your remediation sequence for the first week, first month and first quarter.

---

## 2. Workload identity and cross-account access as architecture

> Assumed known: `01-java` Q189-190 (roles versus users, identity versus resource policies) and `11-security` Q213-221 (policy evaluation order, IRSA, confused deputy). This category is about *architecture*, not the security control plane.

16. `[C]` How does each of these obtain credentials at runtime: an EC2 instance, an ECS task, an EKS pod, a Lambda function, a CodeBuild job? Name the mechanism in each case.
17. `[D]` Walk through the credential lifecycle inside a Lambda execution environment. Where do the keys come from, how long do they last, and what happens on expiry mid-invocation?
18. `[D]` The AWS SDK credential provider chain: what order does it try, and how does that order cause a "works locally, fails deployed" bug?
19. `[D]` Execution role versus resource policy for Lambda. Which one does API Gateway need, which one does EventBridge need, and why is the answer different?
20. `[T]` You grant a Lambda `s3:GetObject` on the bucket and the call still fails with `AccessDenied`. Give five distinct causes.
21. `[D]` Cross-account access patterns: assume-role, resource policy, RAM sharing, PrivateLink. Rank them for a service consumed by twelve internal teams.
22. `[D]` Design cross-account access from an application in account A to a DynamoDB table in account B. What are the failure modes of the naive approach?
23. `[D]` `sts:AssumeRole` chaining: what are the limits, and how does session duration behave across a chain?
24. `[D]` Service-linked roles versus service roles versus pass-role. Explain `iam:PassRole` and the privilege escalation it exists to prevent.
25. `[T]` A developer can create a Lambda function but not an admin role. Explain how they can still reach admin, and the control that stops it.
26. `[D]` Attribute-based access control with tags on AWS: build a working example where one policy serves 30 teams.
27. `[D]` How do you give a third-party SaaS vendor access to your account without long-lived keys? Name the exact mechanism and the parameter that makes it safe.
28. `[D]` IAM Identity Center (SSO) versus federated roles versus IAM users for human access. What does the permission-set model change about how you design accounts?
29. `[T]` Your CI pipeline uses OIDC federation into a deploy role. Name the trust-policy mistake almost everyone makes, and what an attacker does with it.
30. `[D]` Least privilege for a serverless application is 40 statements across 12 functions. How do you generate, review and maintain that without it becoming `*`?
31. `[A]` Your platform team owns the IAM baseline; product teams own their functions. Where do you draw the line so teams can move fast without you approving every policy?

---

## 3. VPC, connectivity and the network boundary

> Assumed known: `01-java` Q191 (subnets, NAT cost, endpoints, security groups versus NACLs) and `11-security` Q225 (endpoint policies, exfiltration control).

32. `[C]` Design a VPC for a three-tier workload across three AZs. Name every subnet, route table and gateway, and say what each one is for.
33. `[D]` Plan the CIDR allocation for an organization that will end up with four regions and forty accounts. What do you reserve, and what mistake is unrecoverable?
34. `[T]` A team allocates `10.0.0.0/24` per VPC "to be efficient". What breaks, and when do they find out?
35. `[D]` How does a NAT gateway actually price, and what are the three ways to reduce that bill without losing internet egress?
36. `[D]` VPC gateway endpoints versus interface endpoints (PrivateLink): what is the difference in mechanism, cost and routing, and which services support which?
37. `[T]` You add an S3 gateway endpoint and a subset of requests still traverse the NAT gateway. Give three reasons.
38. `[D]` Security groups versus NACLs: statefulness, evaluation, and the case where you genuinely need a NACL.
39. `[D]` Security group referencing - a group as a source rather than a CIDR. What does that buy you, and what is the limit that eventually bites?
40. `[D]` Does a Lambda function need to be in a VPC? Give the decision rule, and say what you lose by putting it in one.
41. `[D]` How does Lambda VPC networking work now, and what did the Hyperplane ENI change compared with the old per-function ENI model?
42. `[T]` A VPC-attached Lambda scales to 800 concurrent executions and starts failing. Name two distinct limits that could be the cause.
43. `[D]` A Lambda in a private subnet cannot reach the internet. Walk through the diagnosis in order, and give the cheapest correct fix for an AWS-only destination.
44. `[D]` VPC peering versus Transit Gateway versus PrivateLink versus VPC Lattice. Choose one for each of: two VPCs in one account, forty VPCs across accounts, a service exposed to another company.
45. `[D]` Transit Gateway route tables and appliance mode: what problem does appliance mode solve, and what does it cost?
46. `[D]` Route 53 record types you actually use: alias versus CNAME, weighted, latency, failover, geolocation. Give the case for each.
47. `[D]` Private hosted zones, `.internal` names and resolver endpoints: how does an on-premises host resolve an AWS private name, and vice versa?
48. `[A]` Hybrid connectivity for a bank moving progressively to AWS: Direct Connect, Site-to-Site VPN, or both? Justify the topology, the failure mode you accept and the cost.

---

## 4. Edge and entry - CloudFront, API Gateway, ALB, AppSync

> Assumed known: `04-system-design` Category 5 (caching as an architectural tier) and Category 6 (load balancing, gateways, routing).

49. `[C]` Trace an HTTPS request from a browser to a Lambda handler through CloudFront and API Gateway, naming every hop and what each one can reject.
50. `[D]` API Gateway REST API versus HTTP API versus WebSocket API. Compare features, latency and price, and give the default you would pick in 2026.
51. `[T]` A team picks REST API for the request validation and WAF integration, then complains about the bill. What did they actually pay for, and what would you have done?
52. `[D]` Lambda function URLs versus API Gateway versus an ALB in front of Lambda. When is each correct?
53. `[D]` API Gateway integration types: Lambda proxy, Lambda non-proxy, HTTP, AWS service, mock. Where does a service integration remove a function entirely?
54. `[D]` Authorizers: IAM, Cognito, JWT authorizer, Lambda authorizer. Compare latency, caching and the failure mode of each.
55. `[T]` A Lambda authorizer adds 120 ms to every request. Explain the caching mechanism, its cache key trap, and what happens on a permission revocation.
56. `[D]` API Gateway usage plans, API keys and throttling: what does throttling protect, and where does it sit relative to Lambda concurrency?
57. `[D]` The 29-second API Gateway integration timeout: what do you do for a genuinely long operation? Give two patterns.
58. `[D]` CloudFront cache key design: what is in it by default, what do you add, and what does adding a header cost you?
59. `[T]` A cache hit ratio of 60 percent on static assets. Give five causes, in the order you would check them.
60. `[D]` CloudFront Functions versus Lambda@Edge: where each runs, what each can do, and their latency and price difference.
61. `[D]` Origin Access Control for a private S3 origin, plus signed URLs and signed cookies. Design access for paid content downloads.
62. `[D]` CloudFront in front of an API: what do you actually gain when almost nothing is cacheable?
63. `[D]` AppSync and GraphQL on AWS: resolvers, subscriptions, caching and authorization. When is AppSync the right entry point over API Gateway?
64. `[A]` Design the edge and entry tier for a global consumer application: static assets, a public API, WebSocket notifications, file uploads and a third-party webhook. Justify each choice and its cost.

---

## 5. The Lambda execution model in depth

> Assumed known: `01-java` Q183 (Java cold starts and the four mitigations) and `02-spring` Q261-289 (Boot production engineering, startup cost).

65. `[C]` Describe the lifecycle of a Lambda execution environment: `INIT`, `INVOKE`, `SHUTDOWN`. What runs in each phase, and what persists between invocations?
66. `[D]` Define a cold start precisely. Break the latency into its components and say which ones you can influence.
67. `[D]` What exactly is Lambda concurrency, and how do you compute the concurrency a workload needs from its request rate?
68. `[T]` Your function averages 200 ms and receives 500 requests per second. You have 1000 concurrency. Is that enough? Show the arithmetic and then say what could still throttle you.
69. `[D]` Reserved concurrency versus provisioned concurrency: what each one does, what each costs, and the case for using both on one function.
70. `[T]` You set reserved concurrency to 100 to protect a database. Name two ways this makes the overall system worse.
71. `[D]` The burst concurrency limit and the scaling rate after it: what are the numbers, and how do you design a spiky workload around them?
72. `[D]` What happens on a throttle? Trace the behaviour for a synchronous invoke, an asynchronous invoke and an SQS event source mapping.
73. `[D]` Lambda SnapStart for Java: what is snapshotted, what is restored, and what code must not be in the snapshot?
74. `[T]` After enabling SnapStart, a function starts issuing duplicate identifiers and stale credentials. Explain both bugs and the fix.
75. `[D]` Memory configuration and CPU allocation are coupled in Lambda. Explain the relationship and how you tune for cost rather than for latency.
76. `[T]` A function is configured at 3008 MB "for safety" and uses 180 MB. Explain why that can be both cheaper and more expensive, and how you decide.
77. `[D]` Lambda runtimes: managed runtime, custom runtime, container image, and the Runtime API. What does the container image option actually change?
78. `[D]` Lambda layers and extensions: how does each load, and what does an extension do during `SHUTDOWN` that your handler cannot?
79. `[D]` What is safe to do in the `INIT` phase, and what is a trap? Cover SDK clients, connection pools, secrets and background threads.
80. `[T]` A background thread started in the handler stops making progress and resumes minutes later on a different request. Explain the mechanism.
81. `[D]` `/tmp`, ephemeral storage sizing and cross-invocation state. What can you cache in the execution environment, and what must you never cache?
82. `[A]` A team wants to run their existing Spring Boot service on Lambda unchanged. Walk through what you would tell them, what you would measure, and the conditions under which you would agree.

---

## 6. Compute selection and the serverless boundary

> Assumed known: `01-java` Q182 (the four-way compute decision framework) and `07-devops` Categories 6-7 (Kubernetes internals and operations).

83. `[C]` Give your compute decision framework: Lambda, ECS Fargate, ECS on EC2, EKS, App Runner, EC2, Batch. What is the first question you ask?
84. `[D]` Name five workload characteristics that make Lambda the wrong answer, with the mechanism behind each.
85. `[D]` Name three workloads people run on containers that should be Lambda, and what usually blocks the move.
86. `[D]` ECS on Fargate versus ECS on EC2: capacity providers, task placement, cost, and what you lose without an instance.
87. `[T]` A team migrates from Lambda to Fargate to "avoid cold starts" and latency gets worse at peak. Explain how.
88. `[D]` EKS versus ECS in 2026: what genuinely justifies the Kubernetes control plane, and what does it cost you in people?
89. `[D]` EKS on Fargate versus managed node groups versus Karpenter. Where does each fit, and what does Karpenter do that Cluster Autoscaler did not?
90. `[D]` Spot capacity for containers and for Batch: interruption handling, diversification, and the workloads where spot is irresponsible.
91. `[D]` AWS Batch and array jobs: when is this the right answer over a Step Functions distributed map or a Fargate fleet?
92. `[D]` App Runner and ECS Express-style abstractions: what problem do they solve, and why do serious teams still leave them?
93. `[D]` Graviton: what is the actual price-performance change, and what is the migration risk for a Java workload?
94. `[T]` A workload runs on Lambda at 40 million invocations a month and costs more than a pair of always-on containers. At what point did that become true, and how would you have predicted it?
95. `[D]` Long-running and stateful workloads: WebSocket servers, gRPC streams, background schedulers. Map each onto the right AWS compute.
96. `[D]` Cold start, warm start and always-warm: build a decision table using a p99 latency target as the input.
97. `[A]` A 25-service Java estate on EC2 with Jenkins deploys. Which services would you move to Lambda, which to Fargate, which to leave, and in what order?

---

## 7. The event-driven backbone

> Assumed known: `01-java` Q184-186 (SQS, SNS, EventBridge, Kinesis selection; FIFO; DLQs) and `03-microservices` Category 3 (asynchronous messaging and event-driven architecture).

98. `[C]` SQS, SNS, EventBridge, Kinesis Data Streams and MSK: give the one-sentence identity of each and the question that selects it.
99. `[D]` Delivery semantics per service: at-least-once, at-most-once, exactly-once. State the guarantee for SQS standard, SQS FIFO, SNS, EventBridge, Kinesis and DynamoDB Streams.
100. `[D]` SQS visibility timeout: what exactly does it protect, and how do you set it relative to your consumer's processing time?
101. `[T]` Messages are being processed twice under load with no code changes and no errors in the logs. Explain the most likely mechanism.
102. `[D]` SQS FIFO: message group ID, deduplication ID, and the throughput consequence of choosing a coarse group key.
103. `[T]` A team uses a single FIFO message group to guarantee global ordering and throughput collapses. Explain the mechanism and what you would propose instead.
104. `[D]` SQS long polling, short polling and empty receives: what does each cost, and why does long polling change the bill?
105. `[D]` SNS fanout with SQS subscribers: why is a queue per consumer better than direct SNS-to-Lambda subscriptions?
106. `[D]` SNS message filtering versus EventBridge pattern matching: compare expressiveness, cost, and where the filter runs.
107. `[D]` EventBridge buses, rules, targets and the schema registry. Design event routing for a domain with eight producers and twenty consumers.
108. `[T]` An EventBridge rule silently stops matching after a producer adds a field. Explain how, and the contract practice that prevents it.
109. `[D]` EventBridge Pipes and EventBridge Scheduler: what did each replace, and what glue code do they legitimately delete?
110. `[D]` EventBridge archive and replay: what does replay actually guarantee, and what does it break in a consumer that is not idempotent?
111. `[D]` Kinesis Data Streams: shards, partition keys, iterator age and enhanced fan-out. How do you size a stream?
112. `[T]` Kinesis iterator age is rising on one shard only, while the others are fine. Diagnose it.
113. `[D]` Kinesis versus MSK versus SQS for a 200,000-events-per-second pipeline. Argue the choice on operational cost, not features.
114. `[D]` Event ordering across a distributed system: what does per-partition ordering actually give the consumer, and how do you handle out-of-order arrival?
115. `[A]` Design the event backbone for an order-processing domain: order placed, payment authorized, inventory reserved, shipment created. Choose services, name the contracts, and state where duplicates are tolerated.

---

## 8. Event source mappings, retries and idempotency

> Assumed known: `01-java` Q186 (DLQs and safe reprocessing) and `03-microservices` Category 5 (sagas, outbox, idempotency).

116. `[C]` What is an event source mapping, and how does it differ from an invocation? Who is doing the polling?
117. `[D]` The SQS-to-Lambda event source mapping: batch size, batching window, and how the poller scales concurrency up and down.
118. `[T]` A batch of ten SQS messages has one failure. What happens by default, and what does that do to the other nine?
119. `[D]` `ReportBatchItemFailures`: how do you implement partial batch failure correctly, and what is the trap when the response is malformed?
120. `[D]` Kinesis and DynamoDB Streams error handling: `BisectBatchOnFunctionError`, `MaximumRetryAttempts`, `MaximumRecordAgeInSeconds`, `DestinationConfig`. Explain what each one prevents.
121. `[T]` One bad record stalls a Kinesis shard for six hours. Explain the mechanism and the three settings that would have bounded it.
122. `[D]` Retry behaviour for asynchronous Lambda invocation: how many attempts, over what window, and where does a failure go afterwards?
123. `[D]` Lambda destinations versus a dead letter queue: what does `OnFailure` give you that a DLQ does not?
124. `[D]` Design a dead letter strategy for a serverless application: where DLQs live, what alarms on them, and how a replay works safely.
125. `[T]` A DLQ replay causes a second outage. Name three mechanisms by which that happens.
126. `[D]` Implementing idempotency on AWS: design the idempotency table, the key, the TTL, and the concurrent-request race.
127. `[D]` Lambda Powertools idempotency utility: what does it actually do, and where does it still let a duplicate through?
128. `[D]` The transactional outbox on AWS: DynamoDB Streams versus a database CDC pipeline versus a two-phase write. Recommend one.
129. `[D]` SQS-to-Lambda maximum concurrency versus reserved concurrency: which one do you set to protect a downstream, and why?
130. `[T]` Adding a `maximumConcurrency` of 5 to an SQS event source mapping causes messages to reach the DLQ. Explain the interaction.
131. `[A]` Design end-to-end delivery guarantees for a payment event that must never be lost and must never be applied twice. Name every failure point and its control.

---

## 9. Orchestration with Step Functions

> Assumed known: `03-microservices` Category 5 (saga patterns, compensation) and `04-system-design` Category 7 (asynchronous processing).

132. `[C]` What does Step Functions give you that chaining Lambdas does not? Answer in terms of state, not features.
133. `[D]` Standard versus Express workflows: durability, duration limit, pricing model and observability. Pick one for a synchronous API-backed workflow and justify it.
134. `[T]` A team uses Express workflows for a 20-minute batch job. What happens, and what did the pricing model hide from them?
135. `[D]` The Amazon States Language: `Task`, `Choice`, `Map`, `Parallel`, `Wait`, `Retry`, `Catch`. Which of these removes the most Lambda code in practice?
136. `[D]` Optimized integrations versus AWS SDK integrations versus `.sync` patterns. What does `.sync` do under the hood, and what does it poll?
137. `[D]` Distributed Map: how does it differ from inline `Map`, and what does it unlock for a large S3 dataset?
138. `[D]` The callback pattern with `waitForTaskToken`: design a human-approval step, including the timeout and the failure path.
139. `[D]` Error handling in a state machine: retry with backoff and jitter, catchers, and where compensation logic belongs.
140. `[D]` Implement a saga in Step Functions for order, payment and inventory. Show the compensation path and what happens if compensation itself fails.
141. `[T]` A workflow is idempotent but a retry creates two payments. Explain how the state machine allowed that.
142. `[D]` State payload limits and the payload-by-reference pattern. When does the 256 KB limit force a redesign?
143. `[D]` Step Functions cost: state transitions versus Express duration billing. Give the crossover point with real arithmetic.
144. `[D]` Observability for state machines: execution history, CloudWatch, X-Ray, and how you debug a workflow that failed three days ago.
145. `[D]` Step Functions versus EventBridge choreography versus an application-level saga in code. Rank them for an eight-step business process.
146. `[T]` Version and alias handling: you deploy a new state machine while 4000 executions are in flight. What happens to them?
147. `[A]` Design an order fulfilment workflow with a manual review branch, third-party API calls with unreliable latency, and a strict end-to-end SLA. Justify workflow type, error strategy and where you break the workflow in two.

---

## 10. Data services for serverless workloads

> Assumed known: `01-java` Q187-188 (RDS versus Aurora versus DynamoDB, partition keys, GSI versus LSI) and `06-database` Category 11 (document and wide-column stores) and Category 10 (caching and Redis).

148. `[C]` DynamoDB partitions, capacity units and item size: how does a request map onto physical throughput?
149. `[D]` Single-table design: model a service with three access patterns on one table. Write out the key schema and the item collections.
150. `[T]` Single-table design is "best practice". Give three situations where multiple tables are the better engineering answer.
151. `[D]` GSI versus LSI, projections, and eventual consistency on an index. What does a GSI write cost you, and how does an index throttle a table?
152. `[T]` Writes to a table start throttling while the consumed capacity graph shows 30 percent utilization. Give the two most likely causes.
153. `[D]` Adaptive capacity and burst capacity: what do they actually fix, and what class of hot key do they not fix?
154. `[D]` On-demand versus provisioned capacity with auto scaling: give the arithmetic for the crossover and the traffic shape that decides it.
155. `[D]` DynamoDB transactions: `TransactWriteItems` semantics, cost multiplier, and where a conditional write is the better choice.
156. `[D]` Optimistic locking with conditional expressions versus a lock table. Implement a counter that must never lose an update.
157. `[D]` DynamoDB Streams versus Kinesis Data Streams for DynamoDB: shard semantics, retention and consumer count. Which do you pick for a CDC pipeline?
158. `[D]` TTL in DynamoDB: how promptly does deletion happen, what does it emit to the stream, and what must you never rely on it for?
159. `[D]` DAX versus ElastiCache in front of DynamoDB: consistency model, invalidation, and when neither is the right answer.
160. `[D]` Aurora Serverless v2: how does ACU scaling actually work, what is the minimum you set, and where does it still surprise you?
161. `[T]` A Lambda-fronted Aurora database hits `too many connections` at 400 concurrent executions. Explain the mechanism and give two fixes with their trade-offs.
162. `[D]` RDS Proxy: what it does to connection pooling, pinning, failover time and IAM authentication. What causes pinning and why does it hurt?
163. `[D]` Aurora read replicas, the cluster endpoint versus the reader endpoint, and how a failover looks to a connected application.
164. `[D]` ElastiCache Redis versus MemoryDB versus DynamoDB with DAX: durability, latency and cost. Give a case for each.
165. `[A]` Choose the data layer for a multi-tenant SaaS with a 5 ms read target, unpredictable tenant growth, strict per-tenant isolation and analytics. Justify each store and how they stay in sync.

---

## 11. S3 as an architectural tier

> Assumed known: `01-java` Q193 (storage classes, lifecycle, halving cost) and `11-security` Q223-224 (bucket policies, Block Public Access, presigned URLs).

166. `[C]` What consistency does S3 provide today, and what design workarounds from the pre-2020 model are now obsolete?
167. `[D]` S3 request-rate scaling: what are the per-prefix limits, what is a prefix, and how do you design keys for a high-throughput pipeline?
168. `[T]` A data pipeline writes objects with a timestamp key prefix and throughput plateaus. Explain the cause and the fix.
169. `[D]` Storage classes end to end: Standard, Intelligent-Tiering, Standard-IA, One Zone-IA, Glacier Instant, Flexible, Deep Archive. Give the retrieval time, minimum duration and the case for each.
170. `[D]` Lifecycle transitions: compute whether moving 50 TB of small objects to Standard-IA saves money, including request and transition charges.
171. `[T]` A team enables Intelligent-Tiering on 400 million small objects and the bill rises. Explain exactly why.
172. `[D]` Multipart upload: when to use it, part sizing, and the incomplete-upload cost leak nobody notices.
173. `[D]` Presigned URLs for upload and download: expiry, size limits, and how you enforce content type and object key structure.
174. `[D]` S3 event notifications: EventBridge versus SNS versus SQS versus direct Lambda. What delivery guarantee do you actually get, and what about duplicates?
175. `[T]` An S3-triggered Lambda writes back into the same bucket. What is the failure mode, and what are the two ways to prevent it?
176. `[D]` Versioning, delete markers, MFA delete and Object Lock. Design a bucket that survives a malicious administrator.
177. `[D]` Cross-Region Replication and Same-Region Replication: what replicates, what does not, and what is the RPO?
178. `[D]` S3 Select, Athena and S3 Tables / Iceberg: when does querying in place beat loading into a database?
179. `[D]` Data transfer and request pricing for S3: enumerate the charges on a typical serving path, including CloudFront and cross-region.
180. `[D]` S3 Transfer Acceleration, Direct Connect and Snowball. Choose one for 200 TB of initial migration and one for a daily 500 GB feed.
181. `[A]` Design storage for a document-management product: 300 million documents, unpredictable access, seven-year retention, legal hold, and a 200 ms retrieval expectation for recent files. Justify classes, keys and lifecycle.

---

## 12. Observability on AWS

> Assumed known: `03-microservices` Category 8 (distributed observability) and `07-devops` Category 12 (metrics, logs, traces, SLOs, cardinality cost).

182. `[C]` CloudWatch metrics, logs, alarms, dashboards, Logs Insights and Container Insights: what is each for, and what does each cost?
183. `[D]` Which Lambda metrics matter, and which one do most teams fail to alarm on? Name the alarm set you configure for every function.
184. `[T]` `Duration` and `Errors` look normal, but users report slowness. Which metric tells you the truth, and why is it not in the default dashboard?
185. `[D]` Embedded Metric Format: how does it work, and why is it cheaper than a `PutMetricData` call per invocation?
186. `[D]` Custom metrics cost and cardinality on CloudWatch: what does one high-cardinality dimension do to your bill?
187. `[D]` Structured logging in Lambda: what belongs in every log line, and how do you correlate a request across API Gateway, Lambda and DynamoDB?
188. `[D]` CloudWatch Logs pricing: ingestion, storage, and Logs Insights scanning. Name three ways teams accidentally spend more on logs than on compute.
189. `[D]` Log retention, subscription filters and export to S3: design the log pipeline for a 60-function estate.
190. `[D]` X-Ray: sampling rules, segments and subsegments, and what X-Ray cannot see in an event-driven system.
191. `[T]` A trace shows a 900 ms gap with no subsegment. Give three explanations.
192. `[D]` ADOT and OpenTelemetry on AWS versus native X-Ray. What do you gain, and what does the Collector cost you on Lambda?
193. `[D]` Alarms that matter: static thresholds, anomaly detection, composite alarms, and metric math. Build the alarm set for an API-plus-queue-plus-worker path.
194. `[D]` SLOs for a serverless application: what do you measure when there is no host, and where do you put the SLI boundary?
195. `[D]` CloudWatch Synthetics, Application Signals and Service Lens: which of these earn their place, and what do you use instead?
196. `[T]` Your alarm fired 40 minutes after the outage began. Name the three mechanisms in CloudWatch that produce that delay.
197. `[A]` Design observability for a 60-function, 12-queue serverless estate under a 5000-dollar-per-month telemetry budget. State what you deliberately do not collect.

---

## 13. Reliability, quotas and failure modes

> Assumed known: `03-microservices` Category 6 (resilience patterns) and `07-devops` Category 14 (capacity, chaos, backup and DR).

198. `[C]` Name the ten AWS quotas most likely to break a serverless application in production, and say which are adjustable.
199. `[D]` Explain the full retry topology of a CloudFront to API Gateway to Lambda to DynamoDB request. Where is every retry, and which ones would you turn off?
200. `[T]` A downstream slowdown causes a 30x amplification of requests. Explain how retries at three layers multiply, and the two controls that stop it.
201. `[D]` Timeout budgets: set the timeout at every hop of that same path and justify each number.
202. `[D]` SDK retry configuration: standard versus adaptive retry mode, `maxAttempts`, and the client-side throttling behaviour of adaptive mode.
203. `[D]` What does a 429 from each of API Gateway, Lambda, DynamoDB and Kinesis actually mean, and what is the correct client response in each case?
204. `[D]` Circuit breakers in a serverless architecture: where do you put state when every invocation is stateless?
205. `[D]` Graceful degradation: design three levels of degraded service for a product page backed by five services.
206. `[T]` A single AZ degrades - not fails. Which of your components handle it automatically, and which get worse? Be specific about ALB, Lambda, DynamoDB, Aurora and ElastiCache.
207. `[D]` What actually happens during an Aurora failover, second by second, and what does the application see?
208. `[D]` Backup and restore on AWS: AWS Backup, DynamoDB PITR, RDS snapshots, S3 versioning. State the RPO and the realistic RTO for each.
209. `[T]` You have PITR enabled on DynamoDB. A bad deploy corrupts 2 percent of items over four hours. Walk through the recovery and say why PITR alone is not enough.
210. `[D]` DR patterns: backup-and-restore, pilot light, warm standby, active-active. Give the RTO, RPO and cost band of each, and the one you actually recommend most often.
211. `[D]` How do you test DR on AWS without a maintenance window? Design the drill and what you measure.
212. `[D]` Chaos engineering with AWS Fault Injection Service: name five experiments worth running on a serverless estate.
213. `[T]` A control-plane outage in one region leaves your data plane healthy but you cannot deploy or scale. What breaks, and what do you prepare in advance?
214. `[A]` Set the availability target for a payments API, then design to it. Show the arithmetic that says whether one region is enough.

---

## 14. Multi-region and global architecture

> Assumed known: `01-java` Q195 (active-active and its three hardest problems) and `04-system-design` Category 11 (multi-region and geo-distribution).

215. `[C]` What are the three genuinely hard problems in active-active, and which one do teams underestimate?
216. `[D]` DynamoDB global tables: replication mechanism, conflict resolution, and what last-writer-wins actually does to your data.
217. `[T]` Two regions write to the same item within 200 ms. Describe exactly what your application ends up with, and how you design so it does not matter.
218. `[D]` Aurora Global Database: replication lag, the headless secondary, managed planned failover versus unplanned promotion, and the RPO you can honestly claim.
219. `[D]` Route 53 health checks, failover routing and the arithmetic of DNS TTL during an incident. What is your real failover time?
220. `[D]` Route 53 Application Recovery Controller and readiness checks: what problem does it solve that a health check does not?
221. `[D]` Global Accelerator versus CloudFront versus latency-based routing. Choose one for a TCP game backend, one for an HTTP API.
222. `[D]` Active-passive versus active-active for a write-heavy workload. Where do you pin writes, and what do you do about read-after-write across regions?
223. `[T]` Your failover runbook was tested from the standby side and works. Name four asymmetries that make the real failover fail.
224. `[D]` Cross-region data replication mechanics: S3 CRR, DynamoDB global tables, Aurora Global Database, Kinesis and EventBridge cross-region rules. What is the RPO of each?
225. `[D]` Idempotency and identifier generation across regions. How do you avoid collisions and ordering assumptions?
226. `[D]` Data residency and sovereignty: design a system where EU customer data must never leave the EU but the control plane is global.
227. `[D]` Deploying to two live regions: what breaks about your normal pipeline, and how do you sequence a release?
228. `[T]` A regional AWS service degradation takes down your global control plane even though both data-plane regions are healthy. Explain the dependency and the fix.
229. `[A]` A stakeholder asks for active-active because "we need 99.99". Walk through the conversation, the arithmetic and the alternative you would propose.

---

## 15. Infrastructure as code and delivery for serverless

> Assumed known: `01-java` Q206 (Terraform versus CloudFormation, drift) and `07-devops` Category 11 (Terraform state, `for_each`, module refactors) and Category 10 (GitOps).

230. `[C]` CloudFormation, SAM, CDK, Terraform and the Serverless Framework: what is each, and what is your default for a new serverless estate?
231. `[D]` How does CDK actually work? Synthesis, constructs, the asset pipeline and what is in the cloud assembly.
232. `[T]` A CDK construct rename destroys a production DynamoDB table. Explain the mechanism and the two ways to prevent it.
233. `[D]` CloudFormation change sets, stack policies, `DeletionPolicy` and drift detection. What do you configure on every production stack?
234. `[D]` Stack boundaries: what belongs in one stack, and what should never share a stack? Give the rule you use.
235. `[D]` Cross-stack references: exports versus SSM parameters versus a construct-level reference. Which one makes a stack impossible to delete, and why?
236. `[T]` A nested stack rollback fails and the stack is stuck in `UPDATE_ROLLBACK_FAILED`. What do you do, and what does that tell you about your stack design?
237. `[D]` Terraform versus CDK for AWS specifically: state, drift, multi-account, review experience and the escape hatch each gives you.
238. `[D]` Lambda versions and aliases: how do weighted aliases implement a canary, and what state does a shifting alias break?
239. `[D]` CodeDeploy for Lambda and ECS: linear, canary and all-at-once with pre-traffic and post-traffic hooks and automatic rollback. What does the rollback not undo?
240. `[D]` Configuration for serverless: environment variables versus SSM Parameter Store versus AppConfig versus Secrets Manager. Compare retrieval latency, cost per invocation and rotation.
241. `[T]` A function fetches a secret on every invocation. Quantify what that costs at 50 million invocations a month, and give the correct caching design.
242. `[D]` AppConfig feature flags and its deployment strategies. What does AppConfig give you over a value in a Parameter Store?
243. `[D]` Testing serverless: unit, local emulation with SAM or LocalStack, and testing against real cloud resources. Where do you draw the line, and what do you refuse to mock?
244. `[D]` Ephemeral per-branch environments on AWS: what makes them cheap for serverless, and what makes them impossible for some resources?
245. `[A]` Design the delivery platform for 60 serverless services across four accounts: repository layout, IaC choice, pipeline shape, promotion and rollback. State what is paved road and what is escape hatch.

---

## 16. Cost engineering

> Assumed known: `01-java` Q196 (the 40 percent bill investigation) and `07-devops` Category 16 (FinOps, attribution, requests versus usage).

246. `[C]` Price a Lambda function: 50 million invocations a month, 300 ms average, 512 MB. Show the arithmetic, then name what is missing from it.
247. `[D]` What is the unit cost of a request through CloudFront, API Gateway, Lambda and DynamoDB? Build the per-million-requests table.
248. `[T]` API Gateway REST costs more than the Lambda it fronts. At what request volume does the entry tier dominate, and what do you change?
249. `[D]` Lambda power tuning: describe the method, and explain how a higher memory setting can lower total cost.
250. `[D]` The line items people forget: NAT gateway data processing, cross-AZ transfer, CloudWatch Logs ingestion, KMS requests, VPC endpoint hours, EBS snapshots. Give the mechanism behind each.
251. `[D]` Data transfer pricing rules on AWS: in, out, cross-AZ, cross-region, via CloudFront, via VPC endpoint. State the ones that are free.
252. `[D]` Savings Plans versus Reserved Instances versus Spot in 2026: what does a Compute Savings Plan cover, and how do you size a commitment safely?
253. `[D]` DynamoDB cost control: on-demand versus provisioned, reserved capacity, item size, projections, and the read pattern that quietly doubles cost.
254. `[T]` The bill rises 40 percent with no traffic change and no deploys. Give six candidate causes and the order you would check them.
255. `[D]` Cost attribution for serverless: tags, cost allocation, Cost Categories, and how you attribute a shared API Gateway across ten teams.
256. `[D]` Cost anomaly detection, budgets and the pattern for making cost visible to engineers who do not read the bill.
257. `[D]` Define and instrument a unit cost metric - cost per order, cost per tenant, cost per thousand requests. Why does this beat total spend as a target?
258. `[D]` A workload costs 40,000 dollars a month. Walk through your reduction sequence, and name what you would refuse to cut.
259. `[T]` A team reduces cost 30 percent and reliability degrades two months later. Name three optimizations that do that.
260. `[A]` You are asked to cut cloud spend 25 percent in one quarter across an estate you do not fully understand. Give your plan, what you do first, and how you protect reliability.

---

## 17. Well-Architected reviews, design exercises and leadership

> Assumed known: everything above, plus `01-java` Q197 (the pillars), `04-system-design` Category 16 (design walkthroughs) and `07-devops` Category 17 (platform engineering and leadership).

261. `[A]` Design a serverless order-processing platform for a retailer: 3000 orders per minute at peak, 20x Black Friday spike, payment integration, and a 99.95 target. Justify every service and state the cost.
262. `[A]` Design a multi-tenant SaaS on AWS for 500 tenants ranging from 10 to 100,000 users, with per-tenant isolation, noisy-neighbour control and per-tenant cost reporting.
263. `[A]` Design a document ingestion and search platform: 50,000 documents a day, OCR, extraction, semantic search, and a seven-year retention obligation.
264. `[A]` Design the migration of a Java monolith on-premises onto AWS with no big-bang cutover, including the data migration and the rollback point at every stage.
265. `[A]` Run a Well-Architected review of a system you are handed cold. What do you ask, in what order, and what does your output document actually contain?
266. Tell me about a cloud architecture decision you made that you would make differently today. How did you find out, and what did you do about it?
267. Describe a cloud cost reduction you drove. What was the number, the mechanism, and what did you refuse to cut?
268. Tell me about an AWS production incident you led. What was the failure, what did you do, and what changed permanently afterwards?
269. Describe a time you drove a cloud standard across teams you did not own. How did you get adoption without authority?
270. How do you decide between a managed AWS service and building it yourself? Give a real decision, both directions, and what you would do differently.
