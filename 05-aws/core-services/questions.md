# AWS Core Services Questions

Questions are numbered continuously (`Q1`, `Q2`, ...) so that [answers.md](answers.md) can reference them directly. **Numbering is local to this pack** - a bare `Q68` here means this file, and references to the serverless pack are written as "serverless pack Q68".

Difficulty legend:

- `[C]` Core - you must answer this instantly and correctly.
- `[D]` Deep - expected of a senior engineer, requires mechanism-level detail.
- `[T]` Tricky - designed to catch you out; the obvious answer is usually wrong.
- `[A]` Architect - no single right answer, judged on trade-off reasoning.

Each category opens with an **Assumed known** line. This pack is the **breadth** pass over the estate; [../questions.md](../questions.md) is the depth pass over serverless. Where both cover a topic, start here and go there for the mechanism.

Two habits that separate a good breadth answer from a recited one: **name the deciding number**, and **say when you would not use the service**.

---

## 1. EC2: instances, purchasing and placement

> Assumed known: `01-java` Q182 (compute selection at one line per option) and `05-aws` Category 6 (the serverless boundary from the other direction).

1. `[C]` Read `m6i.2xlarge` out loud and explain every part of it. What would `m6g`, `m6a` and `m6in` change?
2. `[C]` Name the instance families - general purpose, compute optimized, memory optimized, storage optimized, accelerated - and pick one for each of: a Spring Boot API, an in-memory cache, a video transcoder, a Kafka broker.
3. `[D]` What did the Nitro system actually change, and why does it matter to you as an architect rather than to AWS?
4. `[D]` Explain the T-family credit model: baseline, accrual, spending, and what `unlimited` mode does to your bill.
5. `[T]` A `t3.medium` runs an API that is fine for three weeks and then permanently slow. CPU sits at exactly 20 percent. Explain precisely what happened and the two fixes.
6. `[C]` List the EC2 purchasing options and the workload shape each one fits.
7. `[D]` Reserved Instances versus Savings Plans: what does each actually commit you to, and which would you buy today for a mixed fleet?
8. `[D]` Standard versus Convertible RIs, regional versus zonal scope, and On-Demand Capacity Reservations. Which of those gives you a capacity guarantee?
9. `[D]` How does Spot actually work - the interruption notice, the allocation strategies, and capacity rebalancing?
10. `[T]` A team puts the stateless web tier on 100 percent Spot to save money. Name three ways this bites them and the configuration that prevents each.
11. `[D]` Cluster, spread and partition placement groups: what does each guarantee, and name a workload for each.
12. `[D]` Default tenancy versus Dedicated Instances versus Dedicated Hosts. Which one do you need for a BYOL Oracle or Windows licence, and why?
13. `[D]` Golden AMIs versus user data versus configuration management at boot. What are the trade-offs, and what does a mature pipeline look like?
14. `[D]` User data, cloud-init and Systems Manager. Where does each run, and how do you debug a user-data script that silently did nothing?
15. `[D]` The instance metadata service: what is it for architecturally, and what changes when you enforce IMDSv2?
16. `[D]` You are asked to move a Java fleet to Graviton. What is the actual work, what breaks, and what saving do you promise?
17. `[D]` Stop, hibernate and terminate: what happens to the root volume, the instance store, the private IP and the public IP in each case?
18. `[A]` You inherit 200 EC2 instances with no right-sizing history. Describe how you get to a defensible fleet in one month without breaking anything.

---

## 2. EBS, instance store and block storage economics

> Assumed known: Q1-18 above, and `06-database` Category 6 (storage engines and I/O patterns).

19. `[C]` Name the EBS volume types and the workload each is designed for.
20. `[D]` gp2 versus gp3: what changed in the performance model, and why is gp3 almost always the right migration?
21. `[D]` gp3, io2 and io2 Block Express: give the deciding numbers - IOPS, throughput, durability - at which you move up each tier.
22. `[D]` st1 and sc1: what are they good at, and what will destroy their performance?
23. `[T]` An application is slow. EBS shows IOPS well below the provisioned limit but queue depth is consistently above 30. What is happening?
24. `[D]` Explain the gp2 burst-bucket model and the `BurstBalance` metric. What is the equivalent trap on gp3?
25. `[D]` Instance store versus EBS: durability, performance, cost and the operational consequence of choosing instance store.
26. `[D]` What does "EBS-optimized" mean now, and how do you find the ceiling that is actually limiting you - the volume, the instance's EBS bandwidth, or the network?
27. `[D]` How do EBS snapshots work? Explain incremental storage, deletion behaviour, and what a cross-region copy costs you.
28. `[D]` Fast Snapshot Restore: what problem does it solve, how is it priced, and when is it worth it?
29. `[T]` A volume restored from a snapshot performs badly for the first hour and then is fine. Explain the mechanism and the three ways to avoid it.
30. `[D]` EBS encryption: default encryption, KMS key selection, and what happens when you copy an encrypted snapshot to another account.
31. `[D]` io2 Multi-Attach: what it enables, and why it is not a shared filesystem.
32. `[D]` Modifying a volume online - size, type, IOPS. What are the constraints, and what must the operating system still do?
33. `[A]` A 20 TB self-managed PostgreSQL on EC2 needs better I/O. Walk through your storage decision, including what you would measure first.

---

## 3. File and hybrid storage: EFS, FSx, Storage Gateway, Backup

> Assumed known: `01-java` Q193 (S3 storage classes) and `05-aws` Category 11 (S3 as an architectural tier).

34. `[C]` EFS, EBS and S3: give the three-way decision rule in one sentence each.
35. `[D]` EFS throughput modes - Elastic, Provisioned, Bursting - and performance modes. Which do you pick by default and why?
36. `[T]` An application on EFS is far slower than the same code on EBS, and the workload is many small files. Explain why, and what you would change.
37. `[D]` EFS storage classes, lifecycle management and One Zone. What is the failure mode of One Zone that people forget?
38. `[D]` EFS access points, POSIX permissions and mount targets. How many mount targets do you need, and what does cross-AZ access cost?
39. `[D]` The FSx family - Windows File Server, Lustre, NetApp ONTAP, OpenZFS. Name the workload each one exists for.
40. `[D]` FSx for Lustre linked to an S3 bucket: what does the linkage actually do, and what is the HPC pattern it enables?
41. `[D]` Storage Gateway modes - S3 File Gateway, FSx File Gateway, Volume Gateway, Tape Gateway. Give a real use for three of them.
42. `[D]` Storage Gateway versus DataSync: they both move data to AWS. What is the actual distinction, and when do you use both?
43. `[D]` AWS Backup: what does it centralize that per-service backups do not, and what are backup plans, vaults and selections?
44. `[D]` Backup Vault Lock, cross-account and cross-region copy. What threat model does each address?
45. `[T]` A team says "we have snapshots, so we have backups". Name four things that claim is missing.
46. `[D]` How do you derive an RTO and RPO from a backup design, and how do you prove the numbers rather than assert them?
47. `[D]` A containerized application needs a shared filesystem across tasks. Walk through EFS with ECS and EKS, including the two things that commonly go wrong.
48. `[A]` Design storage for a media company: 4K ingest, collaborative editing, and a 10-year archive with occasional retrieval.

---

## 4. Load balancing: ALB, NLB, GWLB

> Assumed known: `05-aws` Category 4 (API Gateway, CloudFront and the serverless entry path) and `03-microservices` Q5 (service-to-service communication).

49. `[C]` ALB, NLB, GWLB and the Classic Load Balancer: one line each on what it is for.
50. `[D]` Give the real differences between ALB and NLB - layer, latency, client IP, protocols, addressing - and say which of them actually drives the decision most often.
51. `[T]` A team has chosen ALB. The requirements then add mutual TLS to the backend, a static IP for a partner allowlist, and one million requests per second. What do you do?
52. `[D]` Target groups and target types - instance, IP, Lambda, ALB-as-target. What does each enable that the others do not?
53. `[D]` Health checks on ALB versus NLB: what is different about the semantics, the defaults and the failure behaviour?
54. `[T]` All targets are healthy and clients are getting 502s. Give five distinct causes.
55. `[D]` Cross-zone load balancing: what is the default for each load balancer type, what does it cost, and when does turning it off hurt you?
56. `[D]` Sticky sessions: how do ALB cookies and NLB flow hashing differ, and what does stickiness break?
57. `[D]` ALB routing rules - host, path, header, query string, source IP - and weighted target groups. What can you build with these that people usually build in code?
58. `[D]` TLS on a load balancer: termination, SNI with multiple certificates, ACM integration, and end-to-end encryption to the target. What are the trade-offs of re-encrypting?
59. `[D]` Deregistration delay and slow start. What are they for, and what breaks when the deregistration delay is shorter than your longest request?
60. `[D]` NLB and client IP preservation, and where proxy protocol v2 comes in. What is the surprising interaction with security groups?
61. `[D]` Gateway Load Balancer: what problem does it solve that the other two cannot, and what is GENEVE doing?
62. `[D]` Which load balancer metrics do you alarm on, and what does a rising `TargetResponseTime` with flat `RequestCount` tell you?
63. `[T]` Someone asks you to raise a support ticket to pre-warm the load balancer before a launch. What is your answer in 2026?
64. `[D]` Idle timeout on the load balancer versus keep-alive on the backend. Which should be larger, and what happens when they are the wrong way round?
65. `[A]` For internal service-to-service traffic across 40 services, would you use an internal ALB per service, a shared NLB, Cloud Map, or a service mesh? Defend the choice.

---

## 5. Auto Scaling and capacity management

> Assumed known: `01-java` Q194 (target tracking versus step scaling) and Q66-81 build on Category 1 above.

66. `[C]` What are the components of an Auto Scaling group, and what do min, max and desired actually control?
67. `[D]` Launch templates versus launch configurations, and why template versioning matters operationally.
68. `[D]` Target tracking, step, simple and scheduled scaling. Give the case where each is the right choice and the case where it is dangerous.
69. `[D]` Predictive scaling: what does it need to work, and when does it beat reactive scaling?
70. `[T]` An ASG is oscillating - scaling out and back in every few minutes. Name the four settings you would look at and what each does.
71. `[D]` Cooldown, instance warm-up and instance refresh. Which applies to which scaling type, and what is the modern replacement for cooldowns?
72. `[D]` Lifecycle hooks on launch and on terminate: what would you actually use each for, and what happens if the heartbeat expires?
73. `[D]` Termination policies: which instance does an ASG kill by default, and how do you protect the one you care about?
74. `[D]` Warm pools: what problem do they solve, what do they cost, and what is the alternative you should try first?
75. `[D]` EC2 versus ELB versus custom health checks on an ASG. What does the wrong choice let you run for weeks without noticing?
76. `[D]` Instance refresh versus a blue/green ASG swap for rolling out a new AMI. What does each give you on rollback?
77. `[D]` Mixed instances policy: on-demand base capacity, Spot percentage, and the allocation strategies. How do you configure this so a Spot capacity event is survivable?
78. `[T]` Scale-out works perfectly. Every scale-in event drops in-flight requests. Explain the chain and the fix.
79. `[D]` Scaling on a queue: why is "queue depth" the wrong target metric, and what is the right one?
80. `[D]` EC2 Auto Scaling versus Application Auto Scaling. What does the latter scale, and where does that matter in a serverless estate?
81. `[A]` A retail EC2 fleet faces a 20x seasonal peak for four days. Give your capacity plan, including what you buy, what you pre-scale and what you test.

---

## 6. Route 53 and DNS architecture

> Assumed known: `04-system-design` Category 11 (geo-distribution) and `05-aws` Category 14 (multi-region topology).

82. `[C]` Which DNS record types do you actually use on AWS, and what does TTL control operationally?
83. `[D]` Alias records versus CNAME: give the three concrete differences and the one that decides it at the zone apex.
84. `[C]` Name all seven Route 53 routing policies and give one production use for each.
85. `[D]` How does latency-based routing decide? What does it measure, and importantly, what does it not measure?
86. `[D]` Geolocation versus geoproximity routing, and what the bias parameter is for.
87. `[D]` Failover routing with health checks. Walk through what happens from the moment the primary starts failing.
88. `[T]` Failover was configured and tested, yet real traffic took 20 minutes to move during an incident. Give the three contributing mechanisms.
89. `[D]` Endpoint health checks, calculated health checks and CloudWatch alarm health checks. When do you need the second and third kinds?
90. `[D]` Weighted routing for a canary or a migration: what is it good at, and what are its two real limitations compared with a load balancer?
91. `[D]` Multivalue answer routing versus a simple record with multiple values. What does the former add?
92. `[D]` Private hosted zones and split-horizon DNS. How do you serve the same name differently inside and outside the VPC?
93. `[D]` Route 53 Resolver with inbound and outbound endpoints: draw the hybrid DNS flow in both directions.
94. `[D]` DNSSEC on Route 53: what does it protect against, and what is the operational risk you are taking on?
95. `[D]` Domain registration, delegation and NS records. Describe the most common way a delegation gets silently broken.
96. `[T]` You are cutting over a service next Tuesday. Describe your TTL strategy for the two weeks around it.
97. `[A]` Design the DNS layer for a two-region active-active service that also has on-premises consumers and a partner integration.

---

## 7. CloudFront and the global edge

> Assumed known: `05-aws` Category 4 (edge and entry for serverless) and `04-system-design` Category 5 (caching tiers).

98. `[C]` What does CloudFront give you beyond caching? Name four things.
99. `[D]` Origins, origin groups and origin failover. What triggers a failover, and what does it not cover?
100. `[D]` Origin Access Control versus the older Origin Access Identity, and what the S3 bucket policy needs to look like.
101. `[D]` Cache policy, origin request policy and response headers policy: what does each control, and why were they split apart?
102. `[D]` Cache key design: what should and should not be in it, and what is the single most common mistake?
103. `[T]` Cache hit ratio is 20 percent on a mostly static site. Give a diagnostic sequence.
104. `[D]` Invalidations versus versioned object names. Which is the correct default, and what do invalidations cost?
105. `[D]` Signed URLs versus signed cookies, and how key groups work. Which do you use for a video library?
106. `[D]` CloudFront Functions versus Lambda@Edge: give the four differences, and one use case that only each can do.
107. `[D]` Where does WAF attach, and what is the actual line between Shield Standard and Shield Advanced?
108. `[D]` Using CloudFront for dynamic and API traffic with caching disabled. What are you buying, and is it worth it?
109. `[D]` Global Accelerator versus CloudFront: what is the real distinction, and when do you need Global Accelerator specifically?
110. `[T]` A team puts CloudFront in front of their API and latency gets worse for their main market. Explain how that happens.
111. `[D]` Price classes, regional edge caches and Origin Shield. What does each one change about cost or origin load?
112. `[D]` Standard logs versus real-time logs. Which do you enable by default, and what does the other cost?
113. `[A]` Design the edge tier for a global SaaS serving a static console, a JSON API and video playback, with customers in the EU, India and the US.

---

## 8. VPC at scale: peering, Transit Gateway, hybrid connectivity

> Assumed known: `05-aws` Category 3 (VPC fundamentals, endpoints, NAT economics) and `11-security` Q225 (endpoint policies).

114. `[C]` Security groups versus network ACLs: give the four differences, and name a case where the NACL is the right tool.
115. `[D]` VPC peering: what are the limits, why is it non-transitive, and what does a CIDR overlap do to your options?
116. `[D]` Transit Gateway: what did it replace, and how do attachments and TGW route tables actually work?
117. `[D]` How is Transit Gateway priced, and what design decision does that pricing push you toward?
118. `[D]` Use TGW route tables to isolate production from non-production while sharing egress. Describe the route table layout.
119. `[D]` Site-to-Site VPN: tunnels, BGP versus static, and the throughput ceiling per tunnel. How do you exceed it?
120. `[D]` Direct Connect: hosted versus dedicated, the lead time, and what a private, public and transit VIF each reach.
121. `[D]` Design a resilient hybrid connection. What does AWS's own resiliency model recommend, and where does VPN fit as a backup?
122. `[T]` A company installs a second Direct Connect for redundancy and still has a single point of failure. Where is it, usually?
123. `[D]` Gateway endpoints versus interface endpoints, endpoint policies, and how PrivateLink reaches a service in another VPC.
124. `[D]` PrivateLink as a service-provider pattern versus VPC peering. Why does a SaaS vendor prefer PrivateLink?
125. `[D]` VPC Flow Logs: what fields matter, and name two questions flow logs categorically cannot answer.
126. `[D]` AWS Network Firewall versus NACLs versus security groups versus a third-party appliance behind a GWLB. Where does each belong?
127. `[D]` IPv6 in a VPC: what changes about subnets, routing and egress, and what is an egress-only internet gateway for?
128. `[D]` DNS inside a VPC: `enableDnsSupport`, `enableDnsHostnames`, the `.2` resolver, and how private hosted zones resolve across accounts.
129. `[T]` Two merged companies both use `10.0.0.0/16` and need connectivity next quarter. What are your options, honestly ranked?
130. `[D]` Centralized egress and inspection VPC patterns. What do they buy, and what do they cost in latency and money?
131. `[A]` Design the network for 40 accounts across 4 regions with on-premises connectivity and a shared services account.

---

## 9. RDS and Aurora operations

> Assumed known: `01-java` Q187 (RDS versus Aurora versus DynamoDB), `06-database` Categories 5-7 (transactions, replication, sharding). This category is about *operating* the managed service, not relational internals.

132. `[C]` RDS, Aurora and self-managed on EC2: what do you give up and gain at each step?
133. `[D]` What is an RDS Multi-AZ instance deployment actually doing, and what is the failover mechanism?
134. `[D]` Multi-AZ DB cluster (three instances) versus Multi-AZ instance deployment. What does the cluster form change?
135. `[T]` A team says Multi-AZ gives them read scaling and zero-downtime failover. Correct both halves precisely.
136. `[D]` Read replicas: replication mechanism, lag behaviour, cross-region replicas, and what promotion does.
137. `[D]` Aurora's storage architecture - six copies across three AZs, the log-structured layer. What does that buy you over RDS?
138. `[D]` Aurora replicas versus RDS read replicas, and how failover tiers decide the new writer.
139. `[D]` Aurora endpoints: cluster, reader, custom and instance. Which one does your application use, and what breaks if you pick wrong?
140. `[D]` Aurora Serverless v2: how does it scale, what is the minimum ACU trade-off, and when is it the wrong choice?
141. `[D]` Aurora Global Database: replication mechanism, RPO and RTO, and what a headless secondary is for.
142. `[D]` Automated backups versus manual snapshots, point-in-time recovery, retention and cross-region copies. What is deleted when you delete the instance?
143. `[T]` Someone deleted a production RDS instance and unchecked "create final snapshot". Walk through what you can and cannot recover.
144. `[D]` RDS Blue/Green Deployments: what does it automate, what does it not, and what is the switchover actually doing?
145. `[D]` Parameter groups and option groups: static versus dynamic parameters, and why a change appeared to do nothing.
146. `[D]` RDS Proxy outside the serverless case: what does it do for failover time and for connection storms from a container fleet?
147. `[D]` Enhanced Monitoring versus Performance Insights versus CloudWatch metrics. Which one answers "why is the database slow right now"?
148. `[D]` Maintenance windows, minor and major version upgrades, and what happens when a version reaches end of standard support.
149. `[A]` Migrate a 5 TB Oracle database to AWS with a four-hour maximum outage. Lay out the options and the decision criteria.

---

## 10. Caching, analytics and purpose-built data services

> Assumed known: `06-database` Categories 10-11 (caching, Redis, NoSQL models) and `04-system-design` Category 5.

150. `[C]` ElastiCache for Redis versus Memcached. Give the honest list of when Memcached still wins.
151. `[D]` Redis cluster mode enabled versus disabled: what changes about sharding, scaling and client behaviour?
152. `[D]` ElastiCache Serverless versus node-based clusters. What are you paying for and giving up?
153. `[D]` Lazy loading, write-through and TTL-based caching. What are the AWS-specific costs of each pattern?
154. `[T]` A cache warms fine in testing and collapses at peak in production. Name three distinct mechanisms that produce that.
155. `[D]` MemoryDB versus ElastiCache for Redis. What is the actual difference, and what does it let you delete from your architecture?
156. `[C]` What is Redshift for, and name three cases where it is the wrong answer.
157. `[D]` Redshift architecture: leader and compute nodes, RA3 with managed storage, and what Spectrum queries.
158. `[D]` Redshift Serverless, concurrency scaling and workload management. Which one solves "our dashboards are slow at 9am"?
159. `[D]` Athena versus Redshift: when does Athena win, and how do partitioning, file format and compression change its cost by an order of magnitude?
160. `[D]` Glue crawlers, the Data Catalog and Glue ETL jobs. When would you use EMR instead?
161. `[D]` Lake Formation: what does it add over S3 bucket policies and IAM, and when is that worth the complexity?
162. `[D]` Kinesis Data Streams versus Data Firehose for analytics ingestion. What decides it?
163. `[D]` OpenSearch Service: what is it genuinely good for, and what makes it become an operational liability?
164. `[D]` Purpose-built database selection: DocumentDB, Neptune, Keyspaces, Timestream. Name the access pattern each exists for and the general-purpose alternative you would try first.
165. `[D]` Where does QuickSight fit, and what is the argument for a central data lake versus a data mesh in a 200-engineer organization?
166. `[A]` Build an analytics platform on top of a live OLTP estate without changing the transactional systems or degrading them.

---

## 11. Containers, platforms and edge compute

> Assumed known: `01-java` Q182, `05-aws` Category 6 (the serverless boundary), `07-devops` Categories 5-8 (containers and Kubernetes operations). This category stops at *selection* and the AWS-specific object model.

167. `[C]` ECS, EKS, Fargate, App Runner, Elastic Beanstalk and Lightsail: one line each on what it is and who it is for.
168. `[D]` The ECS object model: cluster, task definition, task, service. What does a service add over a task?
169. `[D]` ECS on EC2 versus ECS on Fargate. Give the real trade-offs - cost, density, daemon containers, GPUs, image pull time.
170. `[D]` ECS capacity providers and cluster auto scaling. How does the ASG know to add an instance for a pending task?
171. `[D]` Service discovery for ECS: Cloud Map, an internal ALB, or ECS Service Connect. Which and why?
172. `[T]` A Fargate task cannot pull its image and the task definition is correct. Give four causes.
173. `[D]` EKS: what does AWS manage, what do you manage, and what are managed node groups, Fargate profiles and add-ons?
174. `[D]` EKS networking with the VPC CNI: how do pods get IPs, when do you exhaust the subnet, and what are your options then?
175. `[D]` ECR: lifecycle policies, image scanning, cross-account and cross-region strategy for a multi-account estate.
176. `[D]` AWS Batch: what is it for, and how do job queues and compute environments relate to Spot?
177. `[D]` Elastic Beanstalk in 2026: when is it still the right answer, and what does it hide that eventually hurts?
178. `[D]` Lightsail: give the honest positioning, and the migration path off it.
179. `[D]` Outposts, Local Zones and Wavelength. Name the constraint that makes each one the only option.
180. `[D]` EC2 Image Builder plus Systems Manager for AMI hygiene. What does a good AMI lifecycle look like?
181. `[T]` A six-person team says they should move to Kubernetes. Give your response, and the conditions under which you would agree.
182. `[A]` Choose the platform for 25 Java services and a team of 12 with no dedicated platform engineers. Defend the team-shaped part of the answer.

---

## 12. Migration and data transfer

> Assumed known: `07-devops` Category 15 (delivery under migration) and Q149 above.

183. `[C]` Name the 7 Rs of migration with a one-line example of each.
184. `[D]` Migration Hub and Application Discovery Service: what does a real assessment phase produce, and why do teams skip it?
185. `[D]` Application Migration Service (MGN): how does lift-and-shift replication actually work, and what is the cutover sequence?
186. `[D]` DMS: full load plus CDC, homogeneous versus heterogeneous, and where the Schema Conversion Tool fits.
187. `[T]` A DMS migration reports success and the target data is wrong. Name four causes and how you would have caught each.
188. `[D]` Snowball Edge and the network alternative: do the arithmetic that tells you when to ship disks.
189. `[D]` DataSync versus the S3 CLI versus Storage Gateway versus Transfer Family. What decides between them?
190. `[D]` AWS Transfer Family: when is a managed SFTP endpoint the right answer, and what is surprising about its cost model?
191. `[D]` S3 Transfer Acceleration, CloudFront upload and multipart tuning. Which of these actually helps a slow upload from Mumbai to `us-east-1`?
192. `[D]` Cutover planning: reverse replication, the rollback point, DNS TTL and the freeze window. What must exist before you flip?
193. `[D]` Migration waves and dependency mapping. How do you sequence 300 servers, and what makes a wave fail?
194. `[T]` A TCO comparison shows AWS is more expensive than the current data centre. Name five things the comparison probably left out - on both sides.
195. `[D]` VMware Cloud on AWS and similar hybrid holding patterns. When is that a legitimate strategy rather than an expensive delay?
196. `[A]` A data centre lease expires in nine months and there are 300 VMs, a mainframe integration and no migration experience in the team. Plan it.

---

## 13. Operations, governance and cost tooling

> Assumed known: `05-aws` Categories 12 and 16 (serverless observability and cost engineering) and `07-devops` Category 16 (FinOps practice).

197. `[C]` Which Systems Manager capabilities are worth knowing by name, and what does each replace?
198. `[D]` Session Manager versus a bastion host versus SSH keys. What does Session Manager change about your network design?
199. `[D]` Patch Manager: patch baselines, patch groups and maintenance windows. How do you patch a fleet without an outage?
200. `[D]` Run Command, State Manager and Automation runbooks. Give a real use for each.
201. `[D]` Parameter Store versus Secrets Manager: the honest comparison, including cost, rotation and throughput.
202. `[D]` AWS Config: rules, conformance packs and automatic remediation. What question does Config answer that CloudTrail cannot?
203. `[T]` An organization's Config bill is larger than the cost of some of the resources it monitors. Explain how, and what you would change.
204. `[D]` CloudFormation: change sets, drift detection, nested stacks and StackSets. Which of these do you use for a 40-account baseline?
205. `[D]` CloudFormation versus CDK versus Terraform for an operations team that does not write application code. What actually decides it?
206. `[D]` Service Catalog: what pattern does it enable, and why do most implementations fail?
207. `[D]` Trusted Advisor: which checks matter, and what are its structural limits as a cost or security tool?
208. `[D]` Compute Optimizer: what data does it need, what does it recommend well, and what does it systematically miss?
209. `[D]` Cost Explorer, the Cost and Usage Report, Budgets and Cost Anomaly Detection. Which one for which question?
210. `[D]` Savings Plans and Reserved Instances at the organization level: how does sharing work, and what is your commitment strategy for a growing estate?
211. `[D]` AWS Health Dashboard and Personal Health events. How do you turn those into automated action rather than an email nobody reads?
212. `[D]` CloudWatch for an EC2 estate: the agent, custom metrics, log groups, metric filters and composite alarms. What does the agent give you that the hypervisor cannot?
213. `[D]` Automating a fleet's non-production shutdown schedule. What are the mechanisms, and what always breaks the first time?
214. `[A]` Design the governance baseline for a company going from 3 accounts to 40 in a year, with no dedicated platform team yet.

---

## 14. Service-selection exercises

> These are worked in full in [scenario-questions.md](scenario-questions.md). Attempt each out loud for fifteen minutes before reading.

215. `[A]` Five workloads, one compute decision each: a steady internal API, a nightly 6-hour batch job, a spiky public webhook receiver, a GPU inference service, and a legacy Windows application with a licence tied to physical cores. Choose and justify.
216. `[A]` Five storage decisions: a shared filesystem for 200 editing workstations, a 400 TB archive with a legal hold, a Postgres data volume needing 30,000 IOPS, container image layers, and clickstream data queried monthly.
217. `[A]` Design connectivity for an enterprise with 3 data centres, 40 AWS accounts, a partner requiring private access to one internal API, and a compliance rule that no workload traffic may traverse the public internet.
218. `[A]` Pick the data store for six access patterns in one application, and say what you would give up by forcing them all into one store instead.
219. `[A]` Reduce the cost of an EC2-and-RDS-heavy estate by 30 percent in one quarter without reducing reliability. Sequence the work.
220. `[A]` Design a disaster recovery strategy for a legacy three-tier application on EC2 with a 4-hour RTO and a 15-minute RPO, where the application cannot be modified.
