# Security Interview Preparation Pack

Application and cloud security depth for **Principal Engineer / Technical Lead / Solution Architect** interviews: threat modeling and the secure SDLC, authentication and credential handling, OAuth 2.1 and OIDC token engineering, authorization and access control models, browser and session security, injection and deserialization, API and microservice security, applied cryptography and TLS, secrets and key management, Java and Spring Security in practice, supply chain and CI/CD security, container and Kubernetes security, AWS cloud security, AI and LLM security, detection and incident response, compliance and governance, and security architecture design.

The protocol material is anchored on the **current** specifications - OAuth 2.1, OpenID Connect Core, TLS 1.3, and the JWT best-current-practice in RFC 8725 - with the older behaviour you will still meet in production named alongside it. The cloud material is anchored on **AWS**. That is deliberate: security interviews reward the candidate who can say "the spec says X, most estates still do Y, and here is the migration", because that is what the job actually is.

---

## Read [01-java](../01-java/README.md), [02-spring](../02-spring/README.md), [03-microservices](../03-microservices/README.md) and [07-devops](../07-devops/README.md) first

This pack is **not** an introduction to security. It starts where the security material in the earlier packs stopped, and nothing there is restated.

| Assumed known | Where this pack takes it |
| --- | --- |
| `01-java` Q132-134 filter chain, authentication components | Category 10 - filter ordering failures, `SecurityContextHolder` propagation, the four reasons `@PreAuthorize` silently does nothing |
| `01-java` Q135-136 JWT revocation, refresh tokens | Category 3 - the arithmetic between token lifetime and your revocation SLA, rotation with reuse detection, the two-tab race |
| `01-java` Q137-139 grant types, OIDC, PKCE | Category 3 - why implicit and ROPC were removed, and which of `state`, `nonce` and PKCE stops which attack |
| `01-java` Q141-142 CSRF, CORS | Category 5 - what `SameSite=Lax` did *not* fix, and why reflecting `Origin` with credentials is a vulnerability |
| `01-java` Q145 password storage | Category 2 - Argon2id parameters, pepper placement, bcrypt's 72-byte truncation, in-place work-factor upgrades |
| `01-java` Q146-147 OWASP Top 10, injection in JPA | Categories 6 and 7 - what cannot be parameterised, second-order injection, and the three API risks a web scanner cannot find |
| `02-spring` Q143-166 Spring Security architecture | Category 10 - starting at the failure modes, not the configuration |
| `02-spring` Q167-182 resource server, JWKS, token relay | Category 3 - algorithm confusion, `kid` injection, audience confusion, sender-constrained tokens |
| `02-spring` Q237-246 Spring AI, tool calling | Category 14 - the lethal trifecta, tool authorization outside the model, and what to refuse |
| `03-microservices` Q155-170 cross-boundary security | Category 7 - SPIFFE attestation, three-layer authorization, and the paved road that gets 300 services onto it |
| `03-microservices` Q166 tenant isolation | Category 4 - enforcement below the application layer, and every derived store teams forget |
| `04-system-design` Q225-234 security in a design | Categories 3, 4, 9 and 17 - the same decisions at mechanism level, plus the compliance evidence |
| `06-database` Q267-278 least privilege, encryption, PII, erasure | Category 9 and 16 - what each layer of encryption at rest actually stops, crypto-shredding, and why tokenization reduces scope where encryption does not |
| `07-devops` Q48-63 SBOM, SLSA, signing, scanning | Category 11 - the attacker's view: dependency confusion, `pull_request_target`, the OIDC subject-claim mistake |
| `07-devops` Q118-131 secrets and workload identity | Category 9 - eliminating secrets rather than storing them, envelope encryption, what KMS rotation does not do |
| `07-devops` Q239-243 admission control, pod security | Category 12 - the four escape paths, the RBAC verbs that are cluster admin, and why CIS-clean is not safe |

Where a question here overlaps, it starts one level deeper.

**The answer frameworks are not repeated either.** The four-layer technical answer, CIDER for scenarios and STAR-L for behavioural questions are defined once in [../01-java/README.md](../01-java/README.md). Re-read that section before your first mock.

### Scope boundary

- **Owned here**: threat modeling, OWASP, identity protocols, authorization models, browser platform security, injection, applied cryptography, secrets and KMS, supply chain, container and Kubernetes security, AWS security controls, AI/LLM security, detection and IR, compliance.
- **Not here**: AWS service selection, networking depth and cost (`05-aws`); pipeline and platform engineering as a discipline (`07-devops` - this pack only attacks it); RAG architecture and retrieval quality (`09-rag`); agent orchestration design (`10-agents`); saga and consistency theory (`03-microservices`); database internals (`06-database`); whole-system rehearsals (`04-system-design` - Category 17 here is the security subset).
- Because `05-aws`, `08-genai`, `09-rag` and `10-agents` are not built yet, Categories 13 and 14 are deliberately **self-contained** on cloud and AI security rather than deferring anything.

---

## Files in this pack

| File | Purpose | When to use |
| --- | --- | --- |
| [README.md](README.md) | Prerequisite map, roadmap, what interviewers probe | Read first |
| [questions.md](questions.md) | 300 questions across 17 categories | Daily drilling |
| [answers.md](answers.md) | Mechanism-level model answers | After attempting yourself |
| [scenario-questions.md](scenario-questions.md) | Security incidents, design exercises, leadership situations | Mock practice |
| [cheatsheet.md](cheatsheet.md) | Fast revision reference | Night before, and 30 minutes before |
| [quiz.html](quiz.html) | Interactive flashcard version | Active recall |

### quiz.html

Open it directly in a browser - no server, no internet connection needed. Search covers question and answer text, filter by category, difficulty or your own progress, and mark each question Known or Review with progress saved in the browser. Press `/` to focus search.

Generated from the markdown, so the markdown stays the source of truth. After editing any of the three source files:

```bash
python tools/build-quiz.py 11-security
```

---

## What interviewers actually probe at this level

Security questions for a principal role are rarely "what is XSS". They are testing whether you have owned a control, run an incident, and said no to someone senior.

Seven recurring themes:

1. **Can you name the mechanism, or only the mitigation?** The clearest separator in this whole domain. "Use parameterised queries" is mid-level; "the statement's structure is fixed before the data arrives, so the data can never become grammar" is senior; being able to then say what *cannot* be parameterised and how you handle a dynamic `ORDER BY` is principal.
2. **Do you know which control is a fix and which is a mitigation?** Interviewers listen for candidates who overstate. Prompt injection has no fix. Revocation of a stateless JWT is bounded by its lifetime. Encryption at rest does nothing about SQL injection. Saying so plainly builds more credibility than any list of controls.
3. **Architecture over vigilance.** Every strong answer eventually says "and this is why I would not rely on the next engineer remembering". Row-level security instead of a remembered `WHERE` clause, an egress proxy instead of a URL validator, IMDSv2 instead of careful code, admission control instead of a review checklist.
4. **Blast radius, not just entry.** Given a compromise, the interesting question is what the attacker gets next. Least privilege, short credential lifetimes, segmentation, egress control and audit integrity are all answers to "how bad does this get", and that is where senior candidates spend their time.
5. **You have run an incident.** The ordering of the first ten minutes - when you preserve before remediating, when you do the opposite (a live credential), when you isolate rather than terminate, who decides to notify - cannot be faked, and it is asked in almost every loop.
6. **Security is an organisational problem with a technical surface.** Forty teams making the same twenty decisions independently is the real vulnerability. Paved roads, defaults, champions, scorecards, exemptions with expiry dates, and risk acceptance signed by the business - the mechanism matters more than the position.
7. **AI security is now a standard section.** Expect the lethal trifecta, indirect prompt injection, tool authorization and "what would you refuse to build". A candidate who treats it as prompt-wording hygiene rather than an authority-bounding problem loses the section outright.

---

## Study roadmap

### Week 1 - Foundations and identity

Categories 1, 2 and 3. The densest protocol material in the pack. Be able to draw the authorization code flow with PKCE from memory, recite the complete JWT validation list, and state the one rule that kills `alg: none`, algorithm confusion and `kid` injection together.

### Week 2 - Authorization and the browser

Categories 4 and 5. Be able to explain BOLA and why scanners miss it, describe tenant isolation enforced below the application layer, and give a strict CSP plus the rollout path for a legacy app.

### Week 3 - Injection, APIs and cryptography

Categories 6, 7 and 8. Work every `[T]` twice. Be able to say what cannot be parameterised, why validate-then-fetch fails against SSRF, and what happens when an AES-GCM nonce repeats.

### Week 4 - Secrets, Java and the supply chain

Categories 9, 10 and 11. Be able to explain envelope encryption and what KMS rotation does *not* re-encrypt, walk the Log4Shell mechanism, and give the five options for a CVE with no fixed version in order.

### Week 5 - Containers, Kubernetes and AWS

Categories 12 and 13. Be able to recite the IAM policy evaluation order without hesitating, explain the IMDSv2 mechanism, and name the Kubernetes RBAC verbs that are effectively cluster admin.

### Week 6 - AI security, response and design

Categories 14, 15 and 16, then work only from [scenario-questions.md](scenario-questions.md). Category 17 is the rehearsal: the six design exercises out loud on a whiteboard, then the eight story questions with a timer.

---

## Your security story bank

Prepare these with real detail from Verizon India and Sonata Software. Generic answers are transparent at 19 years of experience, and in security they are worse than transparent - a polished answer with no cost in it reads as second-hand.

Every one of these needs a **number** in the Result and a **learning** that changed how you work.

1. A vulnerability found in your system - by you, a pentest, a customer or a researcher - and the class-level fix you made so it could not recur. (Q293)
2. A security incident you were part of: your role, the timeline, and what the post-incident review actually changed. (Q294)
3. A release you blocked or delayed on security grounds - how you made the case, and what it cost you. (Q295)
4. A risk you deliberately accepted: who signed it, the compensating control, and how it ended. (Q297)
5. A security standard or control you drove across teams you did not own, with the adoption number. (Q296)
6. A time you were wrong about a security judgement, and what changed in how you assess risk since. (Q298)
7. A control you made *default* rather than mandatory - a library, a template, a pipeline gate - and its measured effect. (Q299)
8. A security decision a senior stakeholder disagreed with, and how you handled the disagreement. (Q300)
9. A credential, secret or key management change you led, with the count of long-lived credentials you eliminated.
10. An AI or LLM feature you gated, reshaped or refused, and how you presented the trade-off to the business.

---

## Self-check before the interview

- [ ] I can recite the complete JWT validation list and the one rule that prevents `alg: none`, RS256→HS256 confusion and `kid` injection.
- [ ] I can walk the IAM policy evaluation order - explicit deny, SCP, RCP, permission boundary, session policy, identity and resource policy - without hesitating.
- [ ] I can explain why BOLA is API vulnerability number one, why scanners miss it, and how I would test for it automatically.
- [ ] I can state what each layer of encryption at rest stops, and dismantle "the database is encrypted, so the PII is safe".
- [ ] I can explain the lethal trifecta and say which leg I would cut for a specific agent, and why prompt injection has no fix.
- [ ] I can describe the first ten minutes of a leaked-credential incident, including where the ordering differs from an availability incident.
- [ ] I can explain what tokenization reduces that encryption does not, and why.
- [ ] I can name the four container escape paths and the admission control that closes each.
- [ ] I can defend a risk-acceptance mechanism: who signs, what compensating control, what expiry.
- [ ] I have three stories with concrete numbers attached, and at least one of them is about being wrong.
