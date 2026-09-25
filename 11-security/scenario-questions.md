# Scenario Questions

Security incidents, architecture exercises and leadership situations.

Every scenario uses **CIDER**, defined in [../01-java/README.md](../01-java/README.md):

- **Clarify** - what you ask before answering. Never diagnose or design in silence.
- **Isolate** - narrow the failure domain or the core requirement.
- **Decide** - commit to an approach and name the trade-off.
- **Execute** - the concrete steps.
- **Reflect** - what you monitor, prevent, or would do differently.

Security incidents add one thing an availability incident does not have: an **adversary who reacts to what you do**. That changes the ordering of almost every step - evidence before remediation, and a decision about whether the attacker should know they have been seen (S1, S10, `answers.md` Q274). Read the scenario, answer out loud for five minutes, then compare. The model responses are longer than you should speak - use them as the map, not the script.

---

## Part A - Security incidents

### S1. A live AWS key is in a public GitHub repository

> At 11:20 an automated notification says an AWS access key belonging to your production account has been detected in a public repository. The repository belongs to a contractor. GitHub found it four minutes after the push; the commit is 40 minutes old.

**Clarify.** Which key - which IAM principal, and what can it do? Is it a user's long-lived key or a role's temporary credential? Has it been used, and from where? What else is in that repository - other secrets, internal hostnames, a `.env`, a database dump? How long has the repository been public, and does the key appear in earlier commits or only this one? Is there a KMS key or an S3 bucket policy that also references this principal?

**Isolate.** Two questions decide everything else, and they are answered in the first five minutes:

1. **What is the blast radius?** Read the principal's effective permissions - identity policy, groups, boundary, and any resource policies that name it (Q213, Q214). "It is only a read-only key" is a claim to verify, not accept: read-only becomes far worse than read-only through `iam:PassRole`, `lambda:UpdateFunctionCode`, `s3:GetObject` on a bucket holding deploy artefacts, or `secretsmanager:GetSecretValue` (Q232).
2. **Has it been used?** CloudTrail filtered on `userIdentity.accessKeyId` for the whole window, looking at source IP, user agent and the shape of the calls. Enumeration calls (`GetCallerIdentity`, `ListBuckets`, `DescribeInstances`, `ListSecrets`) from an unfamiliar ASN are the signature of an automated harvester, and those run within minutes of a public push - the working assumption is that the key is compromised, not that it might be.

**Decide.** **Revoke first, investigate second.** This is the opposite of the usual "preserve evidence before you change anything" instinct, and the reason is that the evidence here (CloudTrail) is written elsewhere and cannot be destroyed by revocation, while every minute of validity is an active exposure. Deactivate rather than delete, so the key ID remains resolvable in the audit trail.

**Execute.**

1. **Deactivate the key** (`aws iam update-access-key --status Inactive`). Deactivate, not delete - a deleted key ID makes the log analysis harder. If it is a role, attach a deny-all inline policy and add an `aws:TokenIssueTime` deny condition so already-issued session tokens die too; deactivating a user key does not kill an STS session minted from it, and that is the step people miss.
2. **Scope the usage** from CloudTrail. Every call made with that key, its source, and whether any of them created persistence: a new IAM user or key, a new role trust, a Lambda, an EC2 instance, a modified bucket policy, a new KMS grant, a support case. Persistence is the thing that makes revocation insufficient.
3. **Treat everything the key could read as disclosed** until proven otherwise. If it had `GetSecretValue`, every secret in reach rotates - which is where the incident becomes a day of work rather than an hour (Q159).
4. **Then** deal with the repository: rotate before you sanitise, because asking the contractor to force-push first creates a window where the key is still live and you have lost the ability to see it. Rewriting history does not remove the blob from GitHub's forks, caches or the Events API, and it never removes it from whoever cloned it (Q160). The commit is public; the only real remediation is rotation.
5. **Notify** on the internal path: security lead, the account owner, and - if any data access appears in the trail - the privacy function, because the 72-hour clock starts at *awareness*, not at conclusion (Q271).
6. **Write the timeline as you go.** Push time, detection time, deactivation time, first attacker call, last attacker call.

**Reflect.** The systemic questions are all upstream of the leak. *Why did a long-lived key exist at all?* A contractor's workstation should be using federated short-lived credentials, and CI should be using OIDC federation with no stored key whatsoever (Q190, Q220). *Why was there no pre-commit gate?* Secret scanning belongs in three places - pre-commit hooks, the push protection setting on the organisation, and a scan of history - because each catches what the others miss. *Why did detection come from GitHub rather than from us?* GuardDuty's credential-exfiltration finding and a CloudTrail rule on unfamiliar-ASN API calls would have alerted independently (Q228). The metric I would report afterwards is not "the key was rotated" but **time from push to deactivation**, and the count of remaining long-lived keys in the organisation - because the durable fix is that the next leaked key is a credential that expires in an hour and is bound to a workload.

> *Hook: a leaked-credential incident, your time to containment, and the control you added so the class disappeared.*

---

### S2. A critical CVE in a transitive dependency with no fixed version

> A CVSS 9.8 remote-code-execution CVE is published for a library your platform pulls in transitively in 60 of 140 services. The maintainer has not released a fix and the last commit was 14 months ago. Your policy says critical findings are remediated in 72 hours. Leadership is asking for a status.

**Clarify.** Is the vulnerable **code path reachable** from our inputs? What is the vulnerable function, and do we call it - directly, or through the intermediate library? What preconditions does the exploit need (a specific configuration, a feature flag, a deserialization entry point, a particular parser mode)? Is there a public exploit, and what does EPSS say? Is the component in an internet-facing service or an internal batch job? Which intermediate dependency pulls it in, and does *that* library have a release that drops or replaces it?

**Isolate.** A CVSS 9.8 is a statement about the vulnerability in the abstract, not about our risk (Q9). The decomposition that turns 60 services into a workable list:

- **Reachability.** Most transitive CVEs are unreachable in a given application. Call-graph reachability analysis, or in its absence a grep for the vulnerable API plus a review of how the intermediate library uses it, will typically cut 60 services to a handful. This is the single highest-value analysis available and it takes an afternoon.
- **Exposure.** Internet-facing and processing untrusted input is a different incident from an internal job processing our own data.
- **Exploitability now.** EPSS and KEV answer "is anyone actually doing this" (Q10). A 9.8 with a 0.2 percent EPSS and no public PoC is a different tempo from a 9.8 in CISA's KEV list.

The honest framing for leadership: the 72-hour clock is about *risk reduction*, not about a version bump, and I will meet it with a compensating control if the upgrade does not exist.

**Decide.** Five options, in the order I would take them (Q194):

1. **Upgrade the intermediate dependency** to a version that has already moved off or patched the transitive one. Cheapest and most common resolution; check the intermediate's changelog first.
2. **Force the transitive version** via `dependencyManagement` / a version catalog constraint, if a patched release of the vulnerable library exists on a branch. Then test hard, because a forced transitive upgrade breaks at runtime, not at build time (Q177).
3. **Remove the dependency** - is the intermediate library there for one function that we could implement or replace? A surprising number of these are resolved by deleting something.
4. **Patch it ourselves**: fork, apply the upstream fix or write it, publish to the internal repository with a clear internal version marker, and open the upstream PR. This is legitimate engineering and the fear of it is usually overstated - but it creates a maintenance obligation that must be recorded and owned.
5. **Compensating controls plus a documented, time-boxed risk acceptance** (Q18): a WAF rule or input validation that blocks the exploit precondition, removal of the reachable entry point, egress restrictions that neutralise the payload's second stage, and a detection rule for exploitation attempts. Accepted by a named business owner with a review date - never by security on the business's behalf.

Doing nothing quietly is not on the list.

**Execute.**

1. Produce the **actual affected list** from the SBOM inventory rather than from a scanner report per repository - one query, one answer, and the same query proves remediation later (Q181).
2. Publish an internal advisory the same day: what it is, which services, our assessment of reachability, what we are doing, and by when. Ambiguity is what generates the executive escalation.
3. Fix the reachable and exposed services first; batch the rest into the normal cycle with a tracked deadline.
4. Add a **detection** for the exploit pattern before the fix lands, not after - it is the only control that works during the window.
5. Verify by rebuild-and-rescan, and keep the artefact digest of what was deployed so the evidence is a fact rather than a ticket status.

**Reflect.** Three durable outcomes. **Inventory**: the ability to answer "where is library X" in minutes is the difference between this being a day and a fortnight, and it comes from centrally collected SBOMs, not from asking teams. **Reachability tooling**: adopting a scanner that does call-graph analysis changes the noise floor of every future CVE (Q193). **Dependency policy**: this incident is an argument for counting dependencies as a liability - maintainer activity, transitive depth and whether an abandoned library is on the critical path are review criteria, not trivia (Q184). And I would revisit the 72-hour policy itself: a policy that is impossible to meet gets ignored, so it should be "72 hours to *decide and mitigate*, with remediation SLAs by exposure tier".

> *Hook: a CVE with no upstream fix, which of the five options you took, and how you handled the deadline.*

---

### S3. An agent exfiltrated data through a tool call

> Your internal support agent reads customer tickets, queries the customer database and can send email. A customer submitted a ticket containing text that instructed the agent to look up the last 50 customers and email a summary to an external address. It did. You find out from the email gateway's outbound volume alert.

**Clarify.** What did it actually send, to how many addresses, and how many records? Which tools were invoked, in what order, and under whose identity - the agent's service account or the requesting user's? Is the injected text still in the ticket corpus, and is it in the vector index? Were other tickets affected - is this one attacker or a pattern? Does the email tool have an allowlist of recipients? Is the conversation and tool-call history logged with enough fidelity to reconstruct the sequence?

**Isolate.** This is textbook **indirect prompt injection** completing the **lethal trifecta** (Q236, Q239): the agent had access to private data, was exposed to untrusted content, and had a channel to communicate externally. All three were present, so the outcome was available to anyone who could file a ticket. The specific failures, in order of importance:

1. **The email tool had unconstrained recipients.** That is the exfiltration channel and it is the one that turned a prompt-injection curiosity into a data breach (Q243).
2. **The database tool ran with the agent's own broad privileges**, not the requesting user's, so it could read 50 customers when the human in the conversation was entitled to one (Q242).
3. **The model was the policy decision point.** Nothing outside the model checked whether "read 50 customers" and "email an external address" were permissible (Q241).

What is *not* the cause: an insufficiently firm system prompt. Instruction-level defences are a mitigation with a bypass rate, never a control (Q237) - and treating this as "we need better prompt wording" is how it recurs next month.

**Decide.** Contain by cutting the channel, not by tuning the prompt. Then re-architect so the agent's authority is bounded by something deterministic.

**Execute.**

*Containment, within the hour:*

1. Disable the email tool for the agent (feature-flagged kill switch - if there is no kill switch, that is the first finding, Q256).
2. Preserve evidence: the full conversation and tool-call log, the offending ticket, the mail gateway's records of what left. Snapshot before anything is deleted from the ticket queue.
3. Establish the exact records disclosed - from the database tool's query log, not from the model's summary - and hand that to the privacy function immediately. This is likely a notifiable personal-data breach and the clock is running from now (Q271).
4. Search for other instances of the same pattern across the corpus and across the tool-call history, keyed on external recipients and on unusually large result sets.

*Remediation, this week:*

5. **Recipient allowlist** on the email tool: the ticket's verified customer address, or an internal domain. A tool that can send to arbitrary addresses cannot be given to a model that reads untrusted text.
6. **User identity on every tool call.** The database tool authorises against the *requesting user's* permissions, enforced in the tool, so the agent can never exceed the human's authority (Q242). This is the structural fix; everything else is depth.
7. **Authorization outside the model** for consequential actions, with typed, narrow tool signatures (`get_customer(ticket_id)`, not `run_query(sql)`) (Q240, Q241).
8. **Egress control**: the agent's runtime reaches the mail relay and the database, and nothing else. That closes the whole family of exfiltration channels including markdown-image and URL tricks (Q243).
9. **Provenance in the context**: retrieved and user-supplied content is delimited and marked untrusted, and tool results are treated as data. Weak on its own; useful in combination.
10. **Detections**: outbound recipient not in allowlist, result-set size above a threshold, a tool sequence that reads bulk data then transmits, and a rate limit per conversation (Q251, Q266).

**Reflect.** The post-incident review's real finding is a **process** one: this feature shipped without a threat model that asked "what happens when the content the agent reads is written by the attacker" (Q4). I would make a lethal-trifecta review a mandatory gate for any agent with tools - three questions on one page - and add adversarial cases derived from this incident to the evaluation suite so a prompt or model change cannot silently reintroduce it (Q255, Q256). The uncomfortable thing to say out loud to leadership, and the thing that makes the review credible, is that **prompt injection has no fix**; we are choosing which leg of the trifecta to remove, and for this agent the answer is unconstrained external communication.

> *Hook: an injection or agent-misuse incident, which leg of the trifecta you cut, and what it cost the feature.*

---

### S4. A customer found an IDOR

> A customer emails support: "I changed the invoice ID in the URL and I can see another company's invoice." The endpoint is `GET /api/invoices/{id}`. It has been live for two years. You have 40,000 tenants.

**Clarify.** Which endpoints share the flaw - is it this one handler, this controller, or the pattern across the service? What does the authorization check actually do (probably: authenticated, therefore permitted)? Are IDs sequential or opaque? Is the endpoint reachable by any authenticated user, or only within a tenant? What do the access logs retain, and for how long? Has the customer told anyone else, and are they asking for a bounty or a fix?

**Isolate.** Broken Object Level Authorization (Q65): authentication passed, and nothing checked that *this* principal may see *that* object. It is the most common serious API flaw and scanners miss it because a scanner has no idea which objects a session should be able to reach - it needs two accounts and a notion of ownership to see anything at all.

Two things must be separated, because they have different tempos:

- **The vulnerability** - one missing check, fixable in an hour.
- **The exposure** - has anyone else done this over two years? That is a log-analysis question and it is the one that determines whether this is a bug fix or a breach notification.

**Decide.** Fix the endpoint immediately, then determine exposure from logs, then fix the *class* at a layer that does not depend on a developer remembering. And regardless of the log outcome, assume the reporter is not the only person who ever tried it.

**Execute.**

1. **Patch the handler**: the query becomes `WHERE id = ? AND tenant_id = ?` with the tenant taken from the verified principal, never from the request (Q69). A 404, not a 403 - a 403 confirms the object exists and leaks the existence of other tenants' data.
2. **Sweep the codebase for the pattern** the same day: every handler taking an identifier and every repository method that fetches by primary key without a tenant predicate. Expect to find more; two years of the same idiom rarely produces one instance.
3. **Analyse the logs.** Successful `200` responses where the requested invoice's tenant differs from the session's tenant. If the logs do not carry both facts, that is itself a finding and the answer becomes "we cannot rule it out", which for a regulator is materially worse than a confirmed small number.
4. **Handle the reporter well**: thank them, confirm the fix, tell them what you found, and do not send a legal threat. How this email is answered determines whether the next finding arrives by email or on Twitter.
5. **Privacy assessment** with the exposure numbers, and notification if the threshold is met (Q271).
6. **Class-level fix**, which is the actual work: tenant context established once at authentication and applied as a session variable at transaction start; **row-level security** on every tenant-scoped table with a non-owner application role, so a forgotten predicate returns zero rows instead of another tenant's data (Q69); and a repository layer that cannot express an unscoped query.
7. **Tests that find missing checks rather than confirming present ones** (Q73): generate, from the route table, a cross-tenant probe for every endpoint using two fixture tenants, and fail the build on any response that is not 404. This is the control that would have caught it in month one and catches the next one for free.

**Reflect.** Note what does *not* help, and say so if the interviewer offers it: switching to UUIDs makes enumeration impractical but leaves every leaked, logged or shared identifier fully exploitable - it is a mitigation of discovery, not of authorization (Q67). The deeper reflection is about detection: for two years the only detector was a customer. Cross-tenant access is a **high-signal, low-volume** detection that almost nobody implements (Q266), and an assertion in the data layer that a returned row's tenant matches the session's tenant turns a silent breach into an alert. I would also raise the bug-bounty question - if a customer found this in five minutes, a programme would have found it two years ago for less than the cost of this incident (Q284).

> *Hook: an authorization flaw in your system, how you determined exposure, and the mechanism you added so it could not recur.*

---

### S5. A token still works after logout

> A user reports that after logging out on a shared machine, pressing back and refreshing showed their account page with live data. Your SPA holds a 30-minute access token and a refresh token; logout clears local storage and calls `/logout`.

**Clarify.** Is the data live or from the browser cache? What does `/logout` actually do server-side - end the IdP session, revoke the refresh token, both, neither? Where are the tokens stored? Does the resource server validate anything stateful, or is it pure JWT signature-plus-claims? How long is the access token's remaining life at logout? Was there a `Cache-Control` header on the account page? Are there other clients holding tokens from the same session (mobile, a second tab, a BFF)?

**Isolate.** Almost always two independent defects wearing one costume:

1. **Browser cache.** A page returned without `Cache-Control: no-store` is re-rendered from the back-forward cache with its original content. This looks exactly like a session failure and is not one - and it is the first thing to eliminate, because if it is only this, the fix is a header.
2. **The real issue: logout is a client-side event.** Clearing local storage removes the client's copy; it does nothing to the token's validity. A stateless JWT is valid until `exp` regardless of what the client does (Q47), so anyone who captured it - a browser extension, an XSS payload, a shared machine's history, a proxy log - has up to 30 minutes of authenticated access. And if `/logout` did not revoke the refresh token, they have as long as the refresh chain lives, which is the serious version of this bug.

The third thing to check: did logout end the **IdP session**? If not, re-initiating the authorization code flow silently reissues tokens without a credential prompt, and the user on the shared machine simply clicks "sign in" and lands in the previous user's account. That is the finding that matters on a shared machine.

**Decide.** Accept a bounded window for the access token, and make it small and monitored; make the refresh token and the IdP session **genuinely revoked**, synchronously, at logout. Do not attempt to make the access token instantly revocable everywhere - that is a redesign, and it is the wrong lever if the window is already short.

**Execute.**

1. `Cache-Control: no-store` on every authenticated response, and `Clear-Site-Data` on the logout response.
2. Server-side logout that **revokes the refresh token family** (and, with rotation and reuse detection, invalidates the whole chain so a captured earlier token is dead too - Q50), ends the session at the IdP via RP-initiated logout, and returns only after both have happened.
3. Shorten the access token to five to ten minutes, and state the arithmetic: the token lifetime *is* the revocation SLA for a stateless design (Q49). If the business needs a tighter SLA than that, the options are a short-lived token with silent refresh, or opaque tokens with introspection and a cache - and each has a named cost.
4. For the truly sensitive operations, add a stateful check: a `sid` claim looked up against a revoked-session set, checked only on the endpoints that justify the latency (Q48). Sub-second propagation for the endpoints that matter, no per-request lookup for the rest.
5. Rotate the session identifier at every privilege change - login, step-up, impersonation exit - so fixation is not the next report (Q89).
6. Get the token out of local storage: memory plus an httpOnly, `SameSite`, `__Host-`-prefixed refresh cookie, or a BFF holding tokens server-side (Q51, Q52). Local storage means any XSS is a full account takeover with a stolen refresh token, and this incident is a good moment to spend that budget.

**Reflect.** The honest sentence for the review is that **we shipped a logout that was a UI affordance rather than a security control**, and nobody tested it as a control. The test I would add asserts that a captured access token and a captured refresh token both fail after logout - which is a five-line integration test that no team writes because logout "obviously works". Then I would look for the same assumption elsewhere: password change, account lockout, permission revocation and offboarding all have the identical failure mode of changing state without invalidating tokens, and they are all worth checking in the same sitting. Finally I would tell the business the true logout semantics in plain terms, because "logged out" on a shared computer is a promise the current architecture does not keep and users behave as though it does.

> *Hook: a session or token invalidation bug, the window you were exposed for, and how you changed the revocation design.*

---

### S6. SSRF reached the instance metadata service

> GuardDuty fires `UnauthorizedAccess:EC2/MetaDataDNSRebind` and, minutes later, an `InstanceCredentialExfiltration` finding for a role attached to an EC2 instance running your image-processing service. The service fetches user-supplied image URLs.

**Clarify.** Is IMDSv2 enforced on that instance, or is v1 still permitted? What role is attached and what can it do? Does CloudTrail show the role's credentials used from an IP outside your VPC - which is exactly what the exfiltration finding means? What is the URL-fetch code doing: does it validate, follow redirects, resolve DNS itself? Which URLs were submitted in the window? Is the instance in a public subnet and does it have unrestricted egress?

**Isolate.** SSRF into the metadata endpoint, and the second finding says the credentials **left the VPC** (Q109, Q222). That is not a potential exposure; it is credential theft, and the containment tempo is S1's.

The mechanics worth being able to explain: the service validated the URL and resolved the hostname to check the IP, then handed the *URL* to the HTTP client, which resolved again - and the second resolution returned `169.254.169.254`. That is the classic **DNS rebinding / TOCTOU** bypass, and its sibling is a validated URL that 302-redirects to the metadata address (Q110). Both defeat allowlist-plus-resolve, which is why that pattern is not the architecture.

**Decide.** Two tracks in parallel: kill the stolen credentials and hunt for what they did (the incident), and remove the capability rather than patch the validator (the fix). Any design whose safety depends on parsing a URL correctly will fail again.

**Execute.**

*Containment:*

1. **Invalidate the role's sessions**: revoke older sessions via an `aws:TokenIssueTime` deny condition on the role, and reduce the role's permissions to nothing while you work. Instance credentials rotate, so a deny on issue time is what actually kills the token in the attacker's hands.
2. **CloudTrail hunt** on the role: every call, source IP, and any persistence created (new users, keys, roles, trust changes, Lambdas, snapshots shared out, KMS grants) (Q232).
3. **Isolate the instance** rather than terminating it - remove it from the load balancer, replace its security group with a no-egress group, keep it running, and take a memory capture and a volume snapshot before anything else. Terminating destroys the only evidence of what ran (Q269).
4. Recover the submitted URLs and the request logs to identify the entry point and the attacker.

*Fix, in order of durability:*

5. **Enforce IMDSv2** (`HttpTokens: required`) everywhere via an SCP or Config remediation, and set `HttpPutResponseHopLimit: 1` so a container cannot reach the host's metadata. The `PUT`-then-`GET` session requirement means a blind SSRF cannot retrieve credentials, and the hop limit stops the containerised variant (Q222).
6. **Re-architect the fetch**: outbound fetching moves to a dedicated egress proxy in a subnet with no instance profile and no route to link-local, with the proxy enforcing the destination policy. The application never resolves or connects itself. That makes SSRF a proxy-policy question rather than a validation question (Q110).
7. **Least privilege on the role**, sized to what the service does - the incident's severity was set by the role's permissions, not by the SSRF (Q12).
8. **Egress restriction and VPC endpoint policies** so that even a successful credential theft cannot reach an attacker-controlled S3 bucket (Q225).
9. Client-level hardening as depth, not as the control: disable redirects, pin the connection to the validated IP, block link-local and RFC1918 ranges at the socket level, and set aggressive timeouts.

**Reflect.** What makes this incident instructive is that the code contained a validator someone had thought carefully about, and the vulnerability lived in the gap between validation and connection. That is the argument for architectural controls over careful code: IMDSv2 and an egress proxy protect the next engineer who writes a URL fetch, and there will be one. The detections I would add are outbound requests to link-local from application subnets, any use of a role's credentials from outside our IP space (the highest-signal cloud detection there is), and IMDSv1 usage as a leading indicator that an instance is unhardened. And I would use the incident to answer the question it raises about every other service: how many instance roles could survive this, and how many of them need to?

> *Hook: an SSRF or credential-theft incident, and the architectural control you introduced instead of a validator.*

---

### S7. A runtime alert says a container escaped

> Falco alerts at 02:40: `Detect release_agent File Container Escapes` on a pod in the shared production cluster, followed by a `Read sensitive file untrusted` alert on the same node. The pod belongs to a team's batch job. 200 other pods run on that node.

**Clarify.** Is the alert genuine or a known noisy rule for this workload - has it fired before, and was it ever triaged? What is the pod's security context: privileged, added capabilities, a hostPath mount, a mounted Docker/containerd socket, host PID or network namespace? What node is it on and what else runs there? What is the node's instance role, and what service account tokens are projected into pods on that node? Did the image change recently, and what is its provenance?

**Isolate.** A `release_agent` escape needs `CAP_SYS_ADMIN` or a privileged container, so the first question answers itself from the pod spec: if the pod is privileged, the escape is trivially plausible and the alert should be believed. If the pod is `restricted`-compliant, the rule is far more likely to be noise from a legitimate cgroup operation - and *that* determination takes one `kubectl get pod -o yaml`, so it is where triage starts (Q197, Q205).

If the escape is real, the blast radius is the **node**, not the pod: the container runtime socket, every other pod's filesystem and memory, every projected service account token on that node, and the node's own IAM role - which on EKS may be the path to the whole account (Q221). The escape is the beginning of the incident, not the end.

**Decide.** Contain the node as a unit, preserve evidence before remediation, and treat every credential that was resident on that node as compromised. Do not delete the pod first - it is the single most destructive triage action available here and the most tempting one at 02:40.

**Execute.**

1. **Cordon the node** so nothing new schedules onto it. Do not drain yet - draining relocates the attacker's workload and destroys state.
2. **Isolate it at the network layer**: a NetworkPolicy or security group that permits only the forensic path. This stops exfiltration and command-and-control while keeping the evidence live.
3. **Capture**: the pod spec, the image digest, container and node logs, the process tree, a memory capture if tooling allows, and a snapshot of the node volume (Q269).
4. **Revoke what was on the node**: rotate the node's IAM role credentials and the service account tokens for pods on that node, and check CloudTrail for use of the node role from unexpected sources. Bound service account tokens limit but do not eliminate the value of a stolen one (Q204).
5. **Reschedule the innocent workloads** onto healthy nodes, then drain and terminate the node - replaced, never repaired.
6. **Determine the entry**: was the container compromised through the application, or was the image itself malicious (which makes this S9)? The image digest and its provenance answer that (Q186, Q187).
7. **Root-cause the pod spec**: why did a batch job have the capability to escape? That is an admission-control failure, and it is the finding that goes in the report.

**Reflect.** The prevention is entirely at admission: Pod Security Admission `restricted` on every namespace that does not have a documented, expiring exemption, plus Gatekeeper or Kyverno policies denying privileged mode, host mounts, host namespaces and socket mounts (Q205, Q206). Enforcement should have made this pod unschedulable. I would also fix the **triage** gap - if this rule has fired before and nobody looked, the detection was decorative, and a runtime rule with no owner and no runbook is worse than none because it creates the appearance of coverage (Q210, Q265). Two systemic points for the review: the node is the security boundary, not the pod, so workloads with different trust levels should not share nodes (Q209); and a batch job running with `CAP_SYS_ADMIN` is a request nobody challenged, which is a paved-road problem rather than a team problem (Q212).

> *Hook: a container or node compromise you handled, and the admission control that would have prevented it.*

---

### S8. A certificate expired at 02:00

> Internal service-to-service calls start failing at 02:00 with PKIX path validation errors. A client certificate used by four services for mTLS to a payment provider expired. The renewal reminder went to an engineer who left in March. Someone suggests disabling certificate validation to restore service.

**Clarify.** Which certificate - the client cert we present, the provider's server cert, or an intermediate in our trust store? Is a renewed certificate already available from the provider's portal, and who has access? What is the deployment path for a new certificate - a rebuild, a secret update plus restart, or a hot reload? Is the failure total or partial? What is the business impact per hour, and is there a queue that will drain when service returns or is traffic being lost? Are other certificates about to expire - what does the inventory say?

**Isolate.** The technical failure is trivial and the interesting content is entirely in the response. Two decisions define whether this is a 40-minute outage or a Monday morning with a security incident on top of it:

1. **Do we disable validation?** No. `TrustManager` implementations that trust everything are how permanent vulnerabilities are created - they are added at 02:00 "temporarily" and found by a pentest two years later, and this is a **payment** integration, so the failure mode is credential and card-data interception (Q144). The correct emergency lever, if one is needed, is a narrower one: pin the provider's specific expected certificate or trust a specific temporary chain, with an expiring flag and a ticket that blocks the next release until it is removed. Never blanket trust.
2. **Where is the renewal actually blocked?** Usually not on the certificate - on access. The portal credential, the CSR process, the approver. That is the critical path and it is what to attack first.

**Decide.** Restore service by renewing, not by weakening; run the renewal and a parallel "who has access" thread simultaneously; and if the outage must be shortened by a compensating measure, choose one that is specific, expiring and recorded.

**Execute.**

1. Confirm the diagnosis precisely - `openssl s_client` against the endpoint, read `notAfter`, check the whole chain rather than the leaf, and check clock skew before believing anything.
2. Renew: break-glass access to the provider portal (Q75), generate a new key and CSR, obtain the certificate, deploy through the secret store, restart or hot-reload.
3. Communicate on a cadence: impact, ETA, and whether transactions are lost or queued. If payments are failing, the business needs to decide about customer messaging, and that decision is theirs.
4. Once service is restored, **inventory every certificate** in the estate with its expiry, owner and renewal mechanism - that report is the actual deliverable of the night.
5. Automate: ACME where the CA supports it, AWS Certificate Manager for public endpoints, and cert-manager or the mesh's own rotation for internal mTLS. The mesh case is the important one - a service mesh issues short-lived certificates and rotates them automatically, which is a strong argument for moving these four services onto it (Q118).
6. Alert on expiry at 30, 14 and 7 days to a **team**, never a person, and add a synthetic check that fails on the *upcoming* expiry rather than on the outage.

**Reflect.** Every expiry incident has the same root cause and it is not the certificate: a manual process with a single human owner and no monitoring. So the fix is structural - short-lived certificates rotated automatically, so the expiry window is hours and the machinery is exercised continuously rather than annually. That is the general lesson worth stating: **a control that runs once a year will be broken when you need it**, whether it is certificate renewal, a restore drill, or an on-call rotation handover. I would also add the offboarding gap to the review - the leaver's checklist did not include reassigning integration ownership, and that is guaranteed to have produced more than this one instance.

> *Hook: an expiry outage, the shortcut you refused, and the automation that replaced the process.*

---

### S9. A build image was compromised

> A vendor announces that a widely used CI action - which your pipelines use in 90 of 140 repositories - was compromised for a 30-hour window, and that it was dumping runner memory into build logs. Your builds ran 400 times in that window. Some of those pipelines have deploy credentials.

**Clarify.** What exactly did the malicious version do, and what does the vendor say it exfiltrated - environment variables, memory, the whole runner filesystem? Which versions or digests are affected? Are our references pinned to a digest, a tag, or a moving major version? Which of our 400 builds ran inside the window, and which of those had privileged credentials in the environment? Are our build logs public or private, and who could read them? What identities can those pipelines assume, and are they long-lived secrets or OIDC-federated short-lived roles?

**Isolate.** The correct assumption is that **every secret present in every affected build is disclosed**, and the work is enumerating that set, not debating likelihood (Q189). Three tiers, and the tiering is what makes it tractable:

1. **Deploy and cloud credentials** - the ability to change production. Highest priority by a wide margin.
2. **Registry, package-publishing and signing credentials** - because these turn our compromise into our customers' compromise, and that is the outcome that ends careers.
3. **Third-party API keys and tokens** in the build environment.

The second tier raises the question that must be asked before anything else: **did anything get published or deployed during the window?** If an artefact was signed or a release was pushed while an attacker had the signing credential, the incident includes downstream consumers and the disclosure obligations change entirely.

**Decide.** Rotate the whole affected credential set - do not triage by "was probably not stolen". Simultaneously verify the integrity of every artefact built or published in the window. Then remove the class of exposure by ending the practice of having long-lived secrets in build environments at all.

**Execute.**

1. **Freeze** the affected action: pin every reference to a known-good digest, or disable the workflows, so the exposure stops before analysis begins.
2. **Enumerate** affected builds from CI audit logs, and for each, the secrets available to it. If secret-to-pipeline mapping is not queryable, that is a finding in itself.
3. **Rotate** tier by tier: cloud roles and deploy credentials first, then publishing and signing keys, then third-party keys. For signing keys, rotation includes publishing the new key and, if a compromised-window signature exists, revoking trust in the old one.
4. **Verify artefacts**: for every artefact built in the window, rebuild from source and compare - which is exactly what provenance attestation and reproducibility are for (Q186, Q188). Compare deployed image digests against the expected build outputs, and check the transparency log for signatures we did not make (Q187).
5. **Hunt** in CloudTrail and the registry audit log for use of the exposed credentials, especially persistence.
6. **Check the logs themselves**: if the malicious action wrote memory into build logs, the logs are now a secret store, and their access history and retention need handling.
7. **Notify** downstream consumers if any published artefact is in doubt. Early and specific beats late and complete.

**Reflect.** The structural fixes are the whole value of this incident. **Digest-pin every third-party action and image** - a tag is a mutable pointer under someone else's control, and this compromise is exactly what that means in practice (Q185). **Eliminate long-lived secrets from CI** via OIDC federation to short-lived, tightly scoped roles, with the trust policy's subject claim constrained to the specific repository *and* branch (Q190) - had that been in place, the attacker would have obtained credentials that expired in an hour and were scoped to one repository, and this would be a memo rather than an incident. **Split the pipeline**: untrusted steps (build, test on a pull request) run with no credentials at all, and only a separate, approval-gated job holds deploy identity. **Require provenance verification at deploy time**, so an artefact without a valid attestation from our own pipeline cannot reach production (Q186). And I would say the uncomfortable part clearly: we chose convenience over pinning 90 times, and the cost was one vendor's bad 30 hours.

> *Hook: a supply-chain incident, how you scoped the credential exposure, and what you pinned or federated afterwards.*

---

### S10. Suspicious egress from a pod

> A network monitoring alert shows a pod in the production cluster making periodic outbound HTTPS connections to an IP with no reputation, every 300 seconds, 2 KB each time, since 06:00 four days ago. The pod is a Java service you own. It looks like beaconing.

**Clarify.** What is the destination - a resolvable domain, a CDN, a cloud provider range? Does the pattern have jitter or is it exactly periodic (exact periodicity is more likely a health check or a telemetry SDK than an attacker)? Did anything deploy at 06:00 four days ago, and if so what changed - a dependency, a base image, an agent, a feature flag? Is this pod's behaviour different from its replicas? What does the JVM process tree look like, and are there unexpected threads, class loaders or agents? Is the traffic leaving the mesh sidecar or bypassing it?

**Isolate.** The differential is short and mostly benign:

1. **Legitimate telemetry** nobody remembers adding - an APM agent, a licence check, a library phoning home, a new SDK in a transitive upgrade. This is the most common answer by a wide margin, and the deploy timeline usually confirms it in minutes.
2. **A misconfigured internal endpoint** now resolving to something external.
3. **Genuine command-and-control**, in which case the entry vector matters more than the beacon.

The evidence that discriminates: the **deploy correlation** (a change at 06:00 four days ago is the strongest single signal), whether all replicas behave identically (attackers rarely compromise all replicas in lockstep; a dependency change affects all of them), and TLS metadata - SNI and certificate details are visible even without decryption and usually name the vendor immediately.

**Decide.** Investigate before containing, because the probability mass is on "benign and boring", and isolating a production pod for a licence check is a self-inflicted outage. But set an explicit threshold in advance: if the destination is unattributable *or* any host-level indicator appears, it converts to a compromise response immediately - and that decision belongs to a named person, not to a group discussion.

**Execute.**

1. Attribute the destination: reverse DNS, WHOIS, TLS SNI and certificate subject, threat-intel lookup. Ninety percent of these end here.
2. Correlate with the deployment and dependency timeline, and diff the image digest and dependency tree against the previous version. A new transitive dependency with a telemetry callback is the single most likely answer.
3. Compare replicas. Uniform behaviour points to code; a single divergent pod points to compromise.
4. Inspect the runtime: process list, `jcmd VM.system_properties` and thread dump, loaded agents, open sockets, and whether the traffic goes through the sidecar.
5. If it is benign: decide whether the callback is acceptable, and if not, block it and configure it off. Record the finding - "our services phone home to vendor X" is worth knowing for the next data-protection review, since a telemetry payload can carry data that should not leave.
6. If it is not benign: containment as in S7 - network isolation before termination, capture the JVM's memory and the container filesystem, revoke the pod's service account token and any credentials it held, hunt for the entry vector and for lateral movement, and preserve everything before replacing the workload.

**Reflect.** The finding that matters regardless of the outcome is that **the cluster has no default-deny egress**, which is why this was a four-day-old alert rather than a blocked connection at 06:00 on day one (Q207). Default-deny egress with an explicit allowlist per namespace is the control that turns this entire class of question - beaconing, exfiltration, credential theft to an attacker's endpoint - into a build-time conversation rather than a 3 a.m. one. It is rarely deployed because the initial allowlist is genuinely painful to assemble; the way through is to run the policy in audit mode for a fortnight, generate the allowlist from observed traffic, then enforce (Q74). I would also add DNS and TLS-SNI logging with alerting on newly-seen destinations - the highest-value network detection available for a containerised estate (Q266) - and a supply-chain check for network callbacks in new dependencies, since the benign version of this incident is a preview of the malicious one.

> *Hook: an egress investigation you ran, what it turned out to be, and the network policy that came out of it.*

---

## Part B - Design exercises

These are the worked answers to Q287-292 in [questions.md](questions.md). Design out loud for five to ten minutes before reading. In an interview, spend the first two minutes on Clarify - a candidate who starts naming products before asking about the trust boundaries has already lost most of the marks.

### S11. Zero-trust service-to-service identity for 300 services (Q287)

> Design service-to-service identity and authorization for 300 services across three Kubernetes clusters and two cloud providers. Today services trust each other because they are inside the VPC. There is no mesh. You have four quarters.

**Clarify.** What runs outside Kubernetes - VMs, Lambda, managed services, third-party SaaS calling in? Are there services that cannot be modified (vendor appliances, a legacy monolith)? Is there a mesh anywhere, or an existing PKI? What is the latency budget per hop, and how many hops does a user request make? Is there a regulatory requirement driving this, or is it risk reduction - because that changes what "done" means and how much political capital exists? Who owns the platform, and do teams deploy through a shared pipeline or their own?

**Isolate.** "Zero trust" is three separable problems that get conflated, and separating them is most of the answer:

1. **Workload identity** - a service can prove *what it is* cryptographically, without a secret it had to be given (Q150).
2. **Authenticated, encrypted transport** - both ends know who the other is, and this must be automatic or it will not be adopted.
3. **Authorization** - what a given caller may do, which is a policy question and the one that actually reduces risk. Encrypted traffic between two services that may call anything is theatre.

The constraint that shapes the plan: 300 services means **no flag day and no per-team migration effort**. Anything requiring each team to change code is a two-year project that stalls at 60 percent, and the residual 40 percent is where the incident happens.

**Decide.** **A mesh-issued SPIFFE identity per workload, mTLS by default at the sidecar, user identity carried separately in a signed token, and authorization at three layers.** Sidecar rather than library, precisely because it does not require 300 teams to change code.

- **Workload identity**: SPIFFE IDs (`spiffe://prod/ns/payments/sa/payments-api`) derived from platform attestation - the Kubernetes service account, the node's identity, or the cloud instance identity document. The trust root is the platform, so there is no secret zero.
- **Certificates**: short-lived (hours), rotated automatically by the mesh. This removes the certificate-expiry class of incident (S8) rather than managing it.
- **Cross-cluster and cross-cloud**: federate trust domains, one per cluster, with explicit federation relationships. Not one flat trust domain - a compromise in the least critical cluster must not mint identities in the most critical.
- **Non-Kubernetes workloads**: a SPIRE agent on VMs; for Lambda and managed services, a bridge that exchanges cloud IAM identity for a mesh identity at the boundary. Naming how the exceptions work is the difference between a design and a slide.
- **User identity is not workload identity** (Q119). The mesh answers "which service is calling"; the user's identity travels as a separate signed, audience-restricted token, exchanged at each hop via RFC 8693 so the audit trail records both the acting service and the human on whose behalf it acted (Q55).
- **Authorization in three layers**: the gateway (coarse - is this route allowed for this token), the mesh (which services may call which, deny-by-default, generated from the actual call graph), and the service (object-level - the layer no infrastructure can do for you, Q65).

**Execute.** The sequence matters more than the target state:

1. **Quarter one - observe.** Deploy the mesh in permissive mode: sidecars injected, mTLS where both ends support it, plaintext still allowed. Build the real call graph from telemetry. This is also the first time anyone knows what actually calls what, and it will contradict the architecture diagram.
2. **Quarter two - encrypt.** Move to strict mTLS namespace by namespace, starting with the least connected. Permissive-to-strict per namespace is reversible in one config change, which is what makes it safe to do 40 times.
3. **Quarter three - authorize.** Generate deny-by-default service-to-service policy from the observed graph, run it in audit mode, review the would-be denials with each team (which surfaces both mistakes and undocumented dependencies), then enforce. Same shadow-then-enforce pattern as Q74.
4. **Quarter four - propagate user identity.** Token exchange at the gateway and at each hop, with the trust-the-header pattern removed (Q116). This is the part that needs code changes, which is why it is last and why it goes through the shared framework library rather than 300 pull requests.
5. Throughout: the mesh is part of the paved road, so a new service gets identity, mTLS and a default policy from the service template with no decision required (Q131).

**Reflect.** What I would monitor: percentage of traffic on mTLS (the adoption metric), policy denials in audit versus enforce mode, certificate issuance and rotation failures, and sidecar-induced p99 latency - because the mesh's cost is real and hiding it destroys trust with the teams paying it. The trade I would state plainly: a sidecar mesh adds a hop, roughly 1-3 ms per call, memory per pod, and a substantial new operational surface with a control plane that can take down everything at once. That is a large bill, and it is justified at 300 services and not at 15. The failure mode I would guard against hardest is stopping after step two - mTLS everywhere is highly visible, easy to report to an auditor, and reduces very little risk on its own, so it is exactly where these programmes die. And the decision I would revisit is sidecar versus ambient mode, which changes the cost profile enough to be worth re-evaluating at the start of each quarter.

> *Hook: a zero-trust or mesh rollout you led, how far you actually got, and where it stalled.*

---

### S12. End-to-end tenant isolation for 5,000 customers (Q288)

> A B2B SaaS platform with 5,000 tenants across 12 services, one shared PostgreSQL cluster, Redis, Elasticsearch, an S3 bucket and a vector store for an AI feature. Enterprise customers demand contractual isolation and evidence. Design the isolation and the evidence.

**Clarify.** What do the contracts actually require - separate database, separate encryption key, separate region, or an attestation? What is the tenant size distribution? Is there any legitimate cross-tenant access (internal support tooling, benchmarking features, aggregate analytics)? What happens today when a tenant asks for their data to be deleted or exported? Is there an existing multi-tenant model in code, or is `tenant_id` applied by convention? How many engineers, and what is the deployment model - because isolation that depends on 60 engineers remembering something will fail.

**Isolate.** The core insight is that **isolation is only as strong as the weakest store**, and teams reliably secure the primary database and forget everything downstream. The complete surface here is twelve places, not one: PostgreSQL, Redis keys, Elasticsearch indices, S3 prefixes, the vector store, Kafka topics and message keys, the analytics warehouse, logs and traces, caches inside each service, feature-flag targeting, exported reports, and backups. Every one needs a tenant answer.

The second insight is that the mechanism must be **below the application layer**. A `WHERE tenant_id = ?` written by hand in 12 services is a probabilistic control - it fails the first time someone writes a new query in a hurry, which is precisely S4 (Q70).

The third is that the requirement is not only isolation but **provable** isolation. "We have RLS" is not evidence; a passing generated test suite plus a production invariant plus an audit trail is.

**Decide.** **Tenant context established once from the verified principal, enforced by the datastore rather than the query, partitioned in every derived store, with a placement tier for tenants who pay for physical separation.**

1. **Tenant identity comes from the token**, resolved at authentication, never from a header or parameter (Q116). It is propagated as a request-scoped value and asserted at every boundary.
2. **PostgreSQL**: `tenant_id` on every table, **row-level security** with `FORCE ROW LEVEL SECURITY` and a non-owner application role, driven by `SET LOCAL app.tenant_id` at transaction start (Q69). A forgotten predicate returns zero rows instead of another tenant's data. This is the single highest-value control in the design.
3. **Redis**: tenant prefix on every key, enforced by a wrapper client that cannot construct an unprefixed key - a convention that a library makes impossible to violate.
4. **Elasticsearch**: index or alias per tenant for large tenants, a routed shared index with a mandatory tenant filter applied by a proxy for the long tail. Never a filter the caller supplies.
5. **S3**: tenant prefix plus IAM session policies scoped to that prefix, so credentials issued for a request cannot address another tenant's objects - authorization in the credential rather than in the code.
6. **Vector store**: tenant as a namespace or collection, not as filterable metadata. Metadata post-filtering leaks through ranking, through similarity scores and through anything that returns before filtering, and it is the newest and most commonly botched instance of this whole problem (Q244).
7. **Kafka**: tenant in the key and in the envelope, with consumers asserting the tenant of every message against their processing context.
8. **Logs, traces and metrics**: tenant as a structured field, with access control on the observability platform. It is a real store of customer data and it is almost never treated as one (Q261).
9. **Enterprise tier**: a dedicated database and a dedicated KMS key per tenant, same schema and same code path, selected by a routing directory so placement is data rather than configuration. Crypto-shredding per tenant then becomes possible, which is a strong contractual answer for deletion (Q161).
10. **Support access**: a separate, audited impersonation path with explicit reason capture and time limits - never a "see all tenants" role, which is how the isolation gets bypassed by the people who built it (Q72, Q75).

**Execute.** Add RLS behind a flag and run in `SELECT`-only enforcement first to find breakage. Ship the key-wrapper and index-proxy libraries before asking anyone to migrate. Generate cross-tenant probes from the route table for every endpoint, using two fixture tenants, and fail the build on anything that is not a 404 (Q73). Add a production invariant that samples returned rows and alerts if a row's tenant does not match the request's - the detection that turns S4 into an alert. Then produce the evidence pack: architecture, control descriptions, test results, the audit trail, and a per-tenant deletion and export capability that has actually been run.

**Reflect.** What I would monitor: cross-tenant assertion failures (should be zero, and an alert on the first one), RLS policy coverage as a CI check that fails when a new table appears without a policy, per-tenant data volume and query cost, and the age of the enterprise tier's key rotations. The trade: this design costs a routing layer, four wrapper libraries and a real migration, and it buys the ability to sign an enterprise contract without re-architecting - plus a much lower probability of the incident that ends the company. The thing I would push back on during design is the phrase "contractual isolation": pinned down, it is usually satisfied by a dedicated encryption key and an attestation rather than a dedicated database, and establishing that saves a year of work. And the honest limitation to state is the support path - it is the residual risk in every multi-tenant system, because someone must be able to see across tenants, and the control there is auditing and consent rather than prevention.

> *Hook: a tenant-isolation design or remediation you led, the store everyone forgot, and the evidence you produced.*

---

### S13. Secret and key management for 200 services (Q289)

> 200 services, three environments, two clouds, one regulated workload with an HSM requirement. Today: secrets in environment variables from a CI variable store, some in a shared password manager, at least one in a config file in Git. Design the target state and the migration.

**Clarify.** What kinds of secret exist - cloud credentials, database passwords, third-party API keys, signing keys, encryption keys, certificates? Which are ours to rotate and which require a third party's cooperation? What does the regulated workload's requirement actually say: FIPS 140-2 Level 3, key non-extractability, a specific audit format? Who currently has access to production secrets and how would we know if that changed? Is there a service mesh or workload identity anywhere already? How many secrets are there - hundreds or tens of thousands? What is the rotation record: has anything ever been rotated?

**Isolate.** The reframing that makes this tractable: **most secrets should not exist**. The target is not a better vault, it is a much shorter list of things that must be stored at all (Q150). Four categories, in descending order of desirability:

1. **Eliminated** - replaced by workload identity. Cloud access, database access via IAM authentication, service-to-service auth via mesh mTLS. No secret to store, rotate, leak or scan for. This should absorb the majority of the current list and it is where the effort goes.
2. **Dynamic** - generated on demand with a short lease: database credentials from Vault's database engine, STS credentials. Nothing to rotate, because everything is already short-lived.
3. **Stored and rotated** - genuine third-party secrets with no federation option. Managed centrally, rotated automatically where the vendor's API allows, and rotated on a schedule where it does not.
4. **Keys, not secrets** - encryption and signing keys, which never leave the KMS or HSM. The operation goes to the key; the key does not come to the application (Q151).

The second observation: the failure mode of every secret-management programme is that the vault becomes a nicer place to keep the same long-lived secrets. Adoption of a store is not the outcome; **elimination and short lifetimes** are.

**Decide.** **Workload identity as the default, dynamic credentials for the remainder, a central store for genuine third-party secrets, KMS/CloudHSM for keys, and delivery by mounted volume rather than environment variable.**

- **Workload identity**: IRSA or EKS Pod Identity in Kubernetes, instance profiles on VMs, OIDC federation for CI (Q190, Q220, Q221). For cross-cloud, federate the second cloud's workload identity to the first's roles rather than storing a credential in either.
- **Dynamic database credentials**: per-service, per-environment leases with a short TTL, so a leaked credential expires before an attacker finishes enumerating.
- **Central store**: one system, three environment-separated instances with separate trust roots - a compromise of the development store must grant nothing in production. This is the boundary teams collapse for convenience, and it is the one that matters most.
- **Keys**: KMS customer-managed keys with key policies as the authorization boundary, envelope encryption for data (Q151, Q152). CloudHSM only for the regulated workload, because the operational cost is significant and it should be scoped to where the requirement actually applies.
- **Delivery**: the Secrets Store CSI driver mounting into a tmpfs volume, or an SDK fetching at startup. Not environment variables - they appear in `/proc`, in crash dumps, in `env` output, in Actuator's `/env`, in child processes and in logs (Q148, Q170). The regulated workload never receives key material at all; it calls KMS.
- **Access**: per-service, per-environment paths with least-privilege policies generated from the service definition rather than hand-written, and human read access to production secrets only through break-glass with approval and audit (Q75).

**Execute.**

1. **Inventory and stop the bleeding first.** Scan every repository's full history, every CI variable store and the password manager. The Git-committed secret is remediated as S1 - rotate before sanitising - and push protection plus pre-commit scanning goes in before anything else, because otherwise the inventory grows while you work.
2. **Migrate by category, not by team.** Cloud credentials first (highest value, cleanest elimination path, one platform change for many services), then database credentials, then third-party secrets. Sequencing by category means one migration mechanism serves many services.
3. **Ship the platform capability before the mandate**: the CSI driver, the policy generator and the templates land first, so migration is a small config change rather than a project. Then migrate the top 20 services yourself to prove the path and produce the migration guide.
4. **Enforce at the boundary**: admission control rejects pods with secret-shaped environment variables, and CI fails on a detected plaintext secret. Enforcement after the paved road exists, never before (Q212).
5. **Prove rotation works** by rotating something important on a schedule from the beginning. A rotation capability that has never run in production does not exist.
6. **Regulated workload** last, as a separate, deliberately over-engineered track with its own evidence pack.

**Reflect.** What I would measure: count of long-lived credentials remaining (the number that should trend to near zero, and the only metric leadership needs), percentage of services on workload identity, median credential age, mean time to rotate, and secret-scanning findings per month. The trade: dynamic credentials add a dependency in the startup path and a new outage mode - the vault being down means services cannot start - so it needs caching, graceful degradation and genuine HA, and I would state that cost explicitly rather than let it be discovered. The judgement I would flag is that this programme is 20 percent tooling and 80 percent migration, so the plan must be sequenced to deliver risk reduction quarterly rather than at the end - the leaked-credential remediation and the elimination of cloud keys are most of the risk and they are available in the first quarter, which is what buys the political capital for the rest.

> *Hook: a secrets programme you ran, how many long-lived credentials you eliminated, and what you could not.*

---

### S14. An LLM agent with production tool access (Q290)

> The business wants an agent for the operations team that can read runbooks and tickets, query production databases, restart services and open pull requests. It will read alert payloads and customer tickets. Design the security architecture, and say what you would refuse.

**Clarify.** Who are the users and are they already privileged - can they restart services by hand today? Which tools are strictly necessary for the first version, and which are aspiration? Is the model hosted or third-party, and what does the contract say about data retention and training? Does the agent act only when a human asks, or autonomously on an alert - because an autonomous agent reading attacker-controlled alert payloads is a different system entirely. What is the worst single action available through the tool set, and who would be accountable for it?

**Isolate.** This system has all three legs of the **lethal trifecta** by design: private data access (databases, runbooks), exposure to untrusted content (tickets, alert payloads), and external communication (pull requests, and any tool that emits text anywhere reachable) (Q239). Prompt injection is therefore not a bug to be filtered out but a **standing property** of the design (Q235, Q237), and the architecture's job is to bound the damage of a successful injection rather than to prevent one.

The three failure modes that matter, in order:

1. **Excessive agency** - the agent can do more than the human who invoked it (Q240).
2. **Exfiltration** - a channel by which injected instructions move private data outward (Q243).
3. **Unattributable action** - something happened in production and the log says "the agent did it", with no user, no reasoning trace and no way to review the decision.

**Decide.** **The agent is a user-interface convenience over an authenticated API, never a privileged actor.** Four principles, and everything follows from them:

1. **The agent's authority is exactly the invoking user's authority, never more.** Every tool call carries the user's identity and is authorised against the user's own permissions in the target system, by the target system (Q242). If the user cannot restart the payments service by hand, neither can the agent on their behalf. This single decision removes most of the risk surface, and it is the one that gets negotiated away.
2. **Authorization lives outside the model.** Tools are narrow and typed - `restart_service(service_id)` against an allowlist, `query_readonly(named_query, params)` with parameterised, pre-approved queries, never `run_sql(text)` (Q241). The model chooses *which* tool; policy decides whether it may.
3. **Write actions are proposals.** Pull requests, not merges. Restarts of non-critical services with a typed confirmation showing exactly what will happen; restarts of tier-one services refused entirely in version one. Human-in-the-loop only counts if the human is shown the concrete action and its consequence rather than a summary they will click through (Q240).
4. **Egress is closed.** The agent's runtime reaches the model endpoint, the tool endpoints and nothing else - no arbitrary URL fetch, no image rendering from remote URLs in its output, no email. Markdown links and images in the output are stripped or rewritten, because that is a live exfiltration channel that looks like formatting (Q243).

**What I would refuse in version one**, and this is a large part of what an interviewer is listening for: autonomous action without a human in the conversation; write access to production data; any tool with unconstrained parameters; production database access beyond a fixed set of read-only queries; and the ability to modify its own tools, prompts or permissions. Each can be revisited with evidence from the evaluation suite.

**Execute.**

- **Identity and audit**: the user's OIDC token exchanged per tool call for a downstream, audience-restricted token (Q55). Every call logged with user, conversation, tool, parameters, the model's stated reason, and the outcome - a reviewable trace, retained as an audit log with integrity protection (Q263).
- **Context hygiene**: retrieved content and tool results delimited and marked untrusted, with provenance on every chunk. Weak as a control, useful as depth, and honestly labelled as such.
- **Retrieval permissions** enforced at query time by filtering the index to what the user may see, not by post-filtering results (Q244).
- **Budgets**: token, cost, tool-call-count and wall-clock limits per conversation, with a hard loop bound and an alert when any is hit (Q251).
- **Isolation**: the agent runs in its own namespace and account with its own minimal role, so a compromise of the agent's runtime is not a compromise of the operations platform.
- **Evaluation as a gate**: an adversarial suite - injected tickets, injected alert payloads, poisoned runbooks, tool-description poisoning if MCP servers are involved (Q252) - run on every prompt, model or tool change, with a red-team exercise before launch and a documented acceptance threshold (Q255, Q256).
- **Kill switch**: per-tool feature flags, so a suspect capability is disabled in seconds by the on-call without a deploy. Tested, not assumed.
- **Rate limits per user and per conversation**, and a detection for unusual tool sequences (bulk read followed by an outbound action) (Q266).

**Reflect.** What I would monitor: injection-attempt detections, tool-call denials by policy, confirmation-rejection rate (a high rate means the model proposes bad actions and is the single most informative product metric here), cost per conversation, and any action whose audit record lacks a user. The trade to state plainly: constraining the agent to the user's authority and to read-only queries makes it markedly less impressive than the demo, and that is the correct trade for production tools - the alternative is a system where anyone who can file a ticket can restart a service. The staging I would propose is read-only for a quarter with full logging, then proposals, then a narrow set of confirmed writes, with each gate opened on evaluation evidence rather than on enthusiasm. And the thing I would put in writing for the sponsor is that **prompt injection has no fix today** (Q237), so we are managing it by bounding authority - which means the security of this feature is a function of its tool set, and every new tool is a new security review, not a backlog item.

> *Hook: an AI feature you gated or reshaped, what you refused, and how you presented the trade-off.*

---

### S15. A secure-by-default paved road for 40 teams (Q291)

> 40 product teams, 300 services, a platform team of eight. Security findings are inconsistent, every team solves authentication differently, and the last three incidents were all preventable misconfigurations. Design the paved road and the mechanism that keeps teams on it.

**Clarify.** What do the last three incidents have in common - configuration, dependencies, authorization, secrets? Is there an existing platform, a service template, a shared framework library? Do teams deploy through a common pipeline or their own? What is the platform team's mandate: recommend, or enforce? Who is accountable when a team's service is breached today - the team, the platform, or nobody? What is the tolerance for breaking existing services, and is there executive sponsorship for anything mandatory?

**Isolate.** The failure is not knowledge, it is **defaults**. Forty teams making the same twenty security decisions independently will produce forty different answers and some of them will be wrong, every time, forever. Three consequences that shape the design:

1. **Security must be the by-product of using the platform**, not an activity teams perform. If the secure path requires reading a document, adoption tracks how well the document is written, which is to say badly.
2. **The platform team of eight cannot review 300 services.** Anything requiring central review per change is a bottleneck that will be routed around, and being routed around is worse than not existing.
3. **A control not enforced by a machine is a suggestion.** But enforcement before the paved road exists is obstruction - and it burns the credibility needed for everything after.

**Decide.** **A generated service template plus platform-provided capabilities, a small set of machine-enforced non-negotiables, and adoption driven by making the road genuinely faster than the alternative.**

**The paved road** - a new service is generated with, and gets for free:

- Authentication and token validation from the framework library, with correct JWT validation (Q44) that no team writes again.
- Deny-by-default authorization scaffolding, with a route table that fails the build if an endpoint has no explicit rule (Q74).
- Workload identity and secret delivery via CSI, with no long-lived credentials available to request (Q289/S13).
- Mesh identity, mTLS and a default network policy (Q287/S11).
- Security headers, CSP, CORS and CSRF configured correctly by default.
- Structured audit logging with tenant, user and correlation fields, into the platform's log pipeline with correct retention.
- A pipeline with SCA, SAST, secret scanning, image scanning and provenance attestation already wired (Q186).
- A hardened, patched base image, rebuilt centrally and rolled forward automatically.
- Pod security context at `restricted`, with resource limits.
- A dashboard, alerts and an on-call route.

**The non-negotiables** - enforced at admission or in the pipeline, deliberately few, so they can be defended individually:

1. No long-lived cloud credentials in a workload.
2. No privileged containers, host mounts or host namespaces.
3. No plaintext secret in a repository or an environment variable.
4. No internet-facing endpoint without authentication.
5. No deploy of an artefact without provenance from our pipeline.
6. Critical CVEs in reachable, internet-facing code remediated within the SLA.

Everything else is advisory, with a scorecard.

**Execute.** The rollout sequence is the entire answer to "and the mechanism that keeps them on it":

1. **Build the road before the rules.** Nothing is enforced until the compliant path is the easy path. The first deliverable is the template, and the measure of success is that generating a service is faster than copying one.
2. **Migrate the top 20 services yourself.** The platform team does the work, which proves the path, produces the migration guide, and earns the right to ask for the rest. This is the single highest-leverage thing eight people can do.
3. **Shadow mode, then enforce.** Every control runs in audit mode first, findings are reviewed with teams, then enforcement is turned on with a date announced well in advance and time-boxed, named exemptions available on request (Q206). Fail-open in shadow, fail-closed after (Q13).
4. **Enforce at the boundary, not by inspection**: admission control and pipeline gates, so compliance is checked by machines at the point of change.
5. **Security champions** - one funded engineer per team with training and a direct line to the platform team, who does the threat modelling and the first review. This is how eight people scale to 40 teams (Q286).
6. **Scorecards published to engineering leadership**: paved-road adoption, open findings by age, expired exemptions, time to patch. Peer comparison and manager attention move behaviour where policy does not.
7. **Keep the gate fast** - if the pipeline gate adds five minutes, teams will find another way to ship (Q195). Latency of the security tooling is a security metric.

**Reflect.** What I would measure: percentage of services generated from or migrated to the template, incidents attributable to a control the paved road provides (the number that justifies the whole investment), time from a platform patch to full fleet rollout, and exemption count and age. The trade: this centralises decisions and reduces team autonomy, which is genuinely costly - some teams have legitimate reasons to differ, so the exemption path must be real, fast and non-punitive, or the whole thing becomes an adversarial game. The failure mode I would guard against is the platform becoming a gate rather than a product: the test is whether teams choose it when they could avoid it, and if adoption needs a mandate, the road is not good enough yet. I would also plan for the **long tail** explicitly - the last 15 percent of services are legacy, unowned or genuinely special, and they will consume as much effort as the first 85 percent, so they need a named strategy (decommission, wrap, or accept with compensating controls) rather than an open ticket.

> *Hook: a paved road or platform standard you built, the adoption number, and what you did about the long tail.*

---

### S16. PCI and PII scope reduction for a monolith (Q292)

> A 12-year-old monolith processes card payments. Card numbers pass through the application, are logged in places, and are stored encrypted in the main database. Customer PII is spread across 200 tables and three downstream systems. The whole environment is in PCI scope and the audit costs a fortune. Reduce the scope.

**Clarify.** What is the current PCI level and what does the last report of compliance list as in-scope systems? Do we ever need the actual card number after authorisation - for refunds, recurring billing, chargebacks, reconciliation? Which payment providers are in use and do they offer hosted fields and network tokens? Where does card data appear today - request logs, application logs, error tracking, support tooling, database backups, the warehouse, screenshots in tickets? What is the retention obligation on historical card data, and what is it actually used for? Who owns the PII inventory, and is there one?

**Isolate.** Scope is determined by one thing: **does the system store, process or transmit cardholder data** (Q279). Everything that touches it, and everything on the same flat network segment as something that touches it, is in scope. So the objective is not "secure the card data better" - it is to make the card number never exist inside our boundary.

The three moves that take a system out of scope, in order of leverage:

1. **Never receive it.** The browser sends card data directly to the provider via hosted fields or an iframe; our server sees only a token. This removes our application from the processing path almost entirely, and it is the one move that changes the audit fundamentally.
2. **Replace stored numbers with tokens.** Provider-held network tokens for recurring billing, and a token vault for everything internal. Tokenization removes scope because the token is not cardholder data; encryption does not, because the ciphertext plus our key is cardholder data (Q157). This distinction is the heart of the question and the thing most candidates get wrong.
3. **Segment what remains.** Any residual card-handling function moves into a separate account, VPC and deployment unit with a tested, minimal boundary, so scope stops at that boundary rather than covering the estate (Q231).

PII is a different problem with a different shape: it cannot be tokenised away, because the business genuinely needs it. Its levers are **classification, minimisation, and enforced handling** - which means the deliverable is knowing where it is and controlling it, not eliminating it.

**Decide.** **Sequenced descoping: stop the flow, then remove the stored data, then segment the remainder - with PII classification running in parallel because it is the slower, more organisational track.**

**Execute.**

*Phase one - stop new card data entering (one quarter, and most of the value).*

1. Hosted fields for the payment form; our servers never see a PAN on new transactions.
2. Kill the leaks: log filtering that redacts PAN-shaped data at the appender, a scan of every log sink and error tracker for existing card data, and a CI check that fails on a PAN-shaped literal or an unredacted payment payload. Card data in logs is the finding that keeps the whole logging platform in scope, and it is usually discovered late.
3. Support tooling shows the last four digits only, sourced from the token metadata.

*Phase two - remove stored card data (two quarters).*

4. Migrate recurring billing to network tokens from the provider - a per-customer migration with a fallback path, and the longest-lead item because it depends on the provider and on customer re-consent in some flows.
5. Replace stored ciphertext with tokens, in batches, verifying each batch reconciles.
6. Then **delete** the historical card data, including from backups as retention allows, and record what could not be deleted and when it expires (Q277). Deletion is the step that actually reduces scope, and it is the step that gets deferred indefinitely if it is not scheduled explicitly.

*Phase three - segment the remainder (one quarter).*

7. Whatever still handles card data - probably reconciliation and chargeback flows - moves into its own account with its own pipeline, its own network boundary and its own minimal access list, and the boundary is tested by an assessor rather than asserted.
8. Re-scope with the assessor and reissue the report of compliance against a dramatically smaller boundary.

*In parallel - PII.*

9. A data classification with three or four tiers, mapped onto actual columns and topics, and a data inventory generated from the schema and the event contracts rather than maintained by hand (Q281).
10. Classification becomes enforced rather than documented: annotated fields drive masking in logs, redaction in the warehouse, encryption for the restricted tier, and access policy in the query layer - so the classification has a mechanical consequence, which is the difference between a control and a spreadsheet.
11. Minimisation: for each PII field, the lawful basis and the retention period, then delete what has neither (Q276). This is usually where the largest genuine risk reduction is, and it is also the least glamorous.
12. A tested subject-access and erasure capability across all three downstream systems (Q277).

**Reflect.** What I would measure and report: number of systems in PCI scope, count of card records stored (which should reach zero), PAN detections in logs per month, audit hours and cost, and PII-classified columns under enforced control. The trade: this is three or four quarters of engineering that delivers no customer-visible feature, so it must be justified in the business's own terms - the audit cost, the engineering time consumed by compliance, the deal cycle time, and the breach exposure - and sequenced so value lands each quarter rather than at the end. That is why hosted fields go first: it is the smallest change with the largest scope effect, and it makes the rest credible. The thing I would insist on is that **descoping is not the same as securing**: the card data becomes the provider's problem, which is correct, but the PII remains ours and is the larger long-term risk. An organisation that finishes this programme and declares victory on the PCI report while the customer database is still uncontrolled has optimised for the auditor rather than for the customer, and I would say so at the start rather than at the end.

> *Hook: a compliance or descoping programme you led, the scope reduction you achieved, and what you refused to call done.*

---

## Part C - Leadership situations

No model answer is scripted for Part C in the sense of a correct technical response - these assess judgement, influence, and how you behave when the decision is not yours to make. Use **STAR-L** and keep each to two or three minutes. The notes below are the *shape* of a strong answer, not a script.

### S17. A team wants to ship with a known critical finding

> Two days before a launch that has been announced to customers, a penetration test returns a critical authorization flaw in the new service. The team's director wants to ship and fix in the following sprint. You are the security architect. You cannot unilaterally stop the release.

**Shape of a strong answer.** Start by being **specific about the risk rather than the severity label**: what an attacker can actually do, how discoverable it is, whether it is exploitable without authentication, and what the exposure is in the first week - not "it is a critical". A director cannot weigh a CVSS score; they can weigh "any logged-in customer can read any other customer's data, and it takes about ten minutes to find".

Then offer **options rather than a veto**, because a veto you cannot enforce is a bluff and it will be called. Typically: fix it in two days (often possible for an authorization check, and worth costing honestly); ship with the vulnerable endpoint or feature disabled; ship to a limited cohort where the exposure is bounded; or ship with a compensating control and a detection, accepted formally. Bring the estimate for each - a security person who arrives with a cost breakdown is treated as an engineer, and one who arrives with a policy is treated as an obstacle.

If the decision is to ship, make the **acceptance explicit and named**: written down, accepted by someone with the authority to accept it - the business owner, not the engineering director, and never security on the business's behalf - with the compensating control, the detection, a fix date and a review date. The mechanism matters more than the outcome of this one instance, because it is what makes the fifth such decision defensible. Escalate if the risk exceeds what that person can accept, but escalate with the options and a recommendation rather than an alarm, and tell the director you are doing it before you do it.

The reflection is about *timing*: a critical authorization flaw found two days before launch is a **process** failure, not a decision problem. The pentest was too late, and the durable fix is threat modelling at design time plus automated authorization testing in CI (Q73), so the next finding arrives in week two when it is cheap. I would also be honest about the sunk-cost dynamic - the announced date is what is really driving the conversation - and name it, gently, because unnamed pressure is what makes these decisions bad.

> *Hook: a launch you delayed or let through with a known finding, how the decision was made, and how it turned out.*

---

### S18. You have to tell an executive about a breach

> Customer data has been exposed. You have partial information: roughly how, roughly how many records, not yet the full timeline. The CEO wants an update now and asks two questions: "Is it contained?" and "Do we have to tell anyone?"

**Shape of a strong answer.** The core skill is **communicating uncertainty without either false comfort or panic**. Separate three things explicitly and label them: what we know, what we believe with a stated confidence, and what we do not know yet - and give a time by which the unknowns become known. "As of 14:00: an exposed endpoint allowed access to customer records. We have confirmed 4,000 records were retrieved. The endpoint is disabled, so no further access is possible. We do not yet know whether the same actor accessed other systems; we will know by 18:00."

Answer the two questions directly, because evasion here is what destroys trust. Containment is a technical fact and can usually be stated cleanly. Notification is a **legal determination**, not an engineering one, so the honest answer is that the privacy and legal functions decide, that the GDPR clock started when we became aware, and that engineering's job is to give them accurate numbers fast enough for them to decide (Q271). Do not speculate about liability, and do not promise a number you cannot defend.

Then manage the meeting rather than being managed by it: a fixed update cadence, one named spokesperson to the business, and clear separation of the response team from the communication team so investigators are not being interrupted for status. Resist the two pressures that always appear - to give a lower number than the evidence supports (the first number becomes the headline and revising it upward is the worst possible sequence) and to conclude the investigation early because the business needs certainty. Say "I will not give you a number I cannot stand behind, and here is when I will have one."

The leadership content is holding the line on accuracy under real pressure, and being visibly the person who will not shade the truth in either direction. The reflection is usually about **detection latency** rather than the vulnerability - the interesting question in the review is how long the exposure existed before anyone noticed, and what changes that - plus whatever the incident revealed about our ability to answer "what was accessed", which is almost always weaker than assumed and is worth fixing before the next one (Q263).

> *Hook: a breach or serious incident you communicated upward, what you refused to estimate, and what the review changed.*

---

### S19. Driving a security standard across teams you do not own

> You need 40 teams to adopt a new authentication library. It removes a whole class of vulnerability. It also means a week of work per team, delivers nothing customers can see, and you have no authority over any of them.

**Shape of a strong answer.** Start from the teams' incentives, not from the risk. A week of invisible work is a genuine cost to someone with their own roadmap, and treating it as obviously worth it is why security mandates fail. So the first move is to **reduce the cost**: make the migration a small config change rather than a rewrite, write the migration tooling, do the first few migrations yourself, and produce a guide that is specific to this codebase rather than generic. "I will do it for you, you review the PR" converts more teams than any amount of advocacy, because capacity is nearly always the real objection.

Then **sequence by influence rather than by risk**: migrate two or three respected teams first and let their engineers say it was fine. Peer evidence outperforms central mandate. Publish adoption as a scorecard visible to engineering leadership, because visibility plus manager attention does the work that authority cannot - and let teams be compared without being shamed.

Use **structural mechanisms** rather than persuasion where they exist: the new service template uses the library so all new services are compliant by default and the problem stops growing; the old path emits a deprecation warning; eventually the platform stops supporting it, with a date announced far enough ahead to be reasonable. Enforcement comes last and only after the path is genuinely easy (Q212).

Get **sponsorship for the deadline** rather than for the mandate: an engineering leader who says "this is done by end of quarter" in their own words is worth more than a security policy document. And be honest with the holdouts - some will have real reasons, and the ones who do should get an exemption with a compensating control rather than a fight, because spending your credibility on the wrong 5 percent loses you the 95.

The measure of success is adoption without escalation, and the reflection is that this problem should not have needed a campaign: if security capabilities live in a platform that teams already depend on, the next one is a version bump. That is the argument for investing in the paved road rather than in a series of migrations (S15).

> *Hook: a standard you drove across teams you did not own, the adoption curve, and what actually moved it.*

---

### S20. The security team is seen as the department of no

> You join as a senior engineer or architect. Teams route around security review, the security team's findings are ignored, and two engineers tell you privately that they stopped reporting issues because "nothing happens and you just get told off".

**Shape of a strong answer.** Diagnose before acting, and take the second complaint most seriously: **engineers who have stopped reporting** is the most dangerous symptom in the description, because it means the organisation has lost its cheapest detection capability. That is the thing to fix first, and it is fixed by behaviour rather than by process - respond to every report within a day, thank people publicly, fix something small immediately and say who reported it, and make sure nobody is ever criticised for raising something. Reputation here is built one interaction at a time and destroyed in one.

Then find out **why review is routed around**. Usually: it is slow, it arrives too late to change anything, it produces a list rather than a decision, and it says no without an alternative. Each has a concrete fix - a same-day lightweight review for most changes, engagement at design time when advice is cheap, findings that come with a suggested implementation, and a standing rule that the security function never says no without offering a path to yes.

**Deliver something teams want**, early. A library that removes a whole category of work, a pipeline check that is fast and explains its findings, a template that saves a day of setup. Being useful is the only durable route out of being the department of no, and it converts the relationship from gatekeeper to supplier.

Change what is **measured**: security teams that report "number of findings raised" are incentivised to be obstructive. Report time to remediate, adoption of secure defaults, and incidents prevented - outcomes shared with engineering rather than activity performed against them. Shared metrics create shared interest.

And be willing to say publicly that some past findings were **not worth the effort** - a security function that never de-prioritises its own backlog is not making risk decisions, and admitting a few misses buys credibility for the ones that matter. Then hold an absolutely firm line on the small set of non-negotiables, which is only possible once everything else has become negotiable.

The reflection is that "department of no" is a description of a **relationship**, and relationships change through repeated small experiences rather than through a reorganisation or a new policy. The measure that matters is whether engineers bring you problems before shipping, unprompted - and it takes about two quarters to see it move.

> *Hook: a security function or relationship you turned around, what you did first, and how you knew it had changed.*
