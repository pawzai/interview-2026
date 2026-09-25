# Security Interview Questions

Questions are numbered continuously (`Q1`, `Q2`, ...) so that [answers.md](answers.md) can reference them directly.

Difficulty legend:

- `[C]` Core - you must answer this instantly and correctly.
- `[D]` Deep - expected of a senior engineer, requires mechanism-level detail.
- `[T]` Tricky - designed to catch you out; the obvious answer is usually wrong.
- `[A]` Architect - no single right answer, judged on trade-off reasoning.

Each category opens with an **Assumed known** line pointing at the `01-java`, `02-spring`, `03-microservices`, `04-system-design`, `06-database` and `07-devops` questions this material builds on. If those are shaky, go back before continuing.

Protocol statements refer to the current specifications: OAuth 2.1 (draft-consolidated behaviour), OpenID Connect Core, TLS 1.3, JOSE/JWT (RFC 7519 and the BCP in RFC 8725). Where an older RFC behaviour is still what you will meet in production, both are named.

---

## 1. Security foundations, threat modeling and the secure SDLC

> Assumed known: `01-java` Q108-109 (DDD, hexagonal architecture) and `03-microservices` Q1-8 (service boundaries). This category is about how you decide what to defend before you decide how.

1. `[C]` Define confidentiality, integrity and availability, and give a production decision where two of them were in direct conflict.
2. `[C]` Authentication, authorization, accounting and non-repudiation. Which of the four do most systems implement badly, and what is the usual symptom?
3. `[D]` Define the trust boundary. Walk through a request from a browser to a database and name every boundary it crosses and the control at each.
4. `[D]` What is a threat model, and what are the four questions the Shostack framework asks? What is the output artefact?
5. `[D]` STRIDE: name each category, the property it violates, and one concrete mitigation each.
6. `[T]` A team says "we did a threat model, here is the diagram". What is missing, and how would you tell within two minutes whether it was a real exercise?
7. `[D]` Attack trees versus STRIDE versus PASTA versus LINDDUN. When do you reach for each?
8. `[D]` Explain the difference between a vulnerability, a threat, a risk and an exploit, using a single example carried through all four.
9. `[D]` CVSS base, temporal and environmental scores. Why is a CVSS 9.8 sometimes ignorable and a CVSS 5.3 sometimes a page?
10. `[D]` EPSS and KEV: what do they add over CVSS, and how would you build a patch-priority rule from all three?
11. `[D]` Defense in depth versus defense in breadth. Give an example where adding a control measurably reduced security.
12. `[D]` The principle of least privilege sounds obvious. Why does it almost always fail in practice, and what mechanism makes it stick?
13. `[D]` Fail-open versus fail-closed. Give one system where you deliberately chose fail-open and defend it.
14. `[T]` "Security through obscurity is worthless." Argue against that statement, then state where the original point is still correct.
15. `[D]` What is the secure SDLC, and what security activity belongs in each phase from design to decommission?
16. `[A]` Shift-left security: what actually works, what turns into noise, and how do you measure the difference?
17. `[A]` You join a 200-engineer organisation with no security function. What are your first three initiatives, in order, and why that order?
18. `[A]` How do you decide when a risk is acceptable? Describe the mechanism you use, who signs it, and what happens when they refuse.

---

## 2. Authentication and credential handling

> Assumed known: `02-spring` Q143-152 (filter chain, authentication components, context propagation) and `01-java` Q145 (password storage). This category is about the protocol and storage decisions underneath.

19. `[C]` How do you store a password? Name the algorithm, the parameters and why each parameter exists.
20. `[D]` bcrypt, scrypt, PBKDF2 and Argon2id compared: what resource does each make expensive, and which do you pick in 2026 for a JVM service?
21. `[T]` bcrypt silently truncates input. At how many bytes, what is the consequence when combined with a pre-hash, and what is the correct fix?
22. `[D]` Salt, pepper and work factor. Where does each live, what attack does each defeat, and what breaks when you rotate them?
23. `[D]` How do you upgrade a password hash's work factor, or migrate from one algorithm to another, without asking every user to reset?
24. `[D]` Credential stuffing versus brute force versus password spraying. The detection signal and the effective control differ for each - give all three.
25. `[T]` You add account lockout after five failed attempts. Describe the denial-of-service you just built and what you should have done instead.
26. `[D]` Username enumeration: list five places it leaks that are not the login form, and how you close each.
27. `[D]` Design a password reset flow. Token generation, storage, lifetime, single use, and the three mistakes that make it an account takeover.
28. `[C]` MFA factor categories, and why SMS OTP is still deployed despite being the weakest common second factor.
29. `[D]` TOTP: what is actually shared, how does drift tolerance work, and what replay protection must the server implement?
30. `[D]` WebAuthn and passkeys: explain attestation versus assertion, the role of the origin and the RP ID, and why phishing stops working.
31. `[T]` A user has a passkey and a password. Explain precisely how much phishing resistance you actually have, and what to do about it.
32. `[D]` Push-based MFA and MFA fatigue attacks. What is number matching, and what else do you need alongside it?
33. `[D]` Account recovery is the weakest link in every strong authentication system. Design one that does not undo your passkey rollout.
34. `[D]` Machine-to-machine authentication: shared secret, mTLS, signed JWT assertion, or workload identity federation. Compare and give your default.
35. `[A]` Build versus buy for identity: your own auth service, Keycloak, or Cognito/Auth0/Okta. Give the decision criteria and the migration cost you would warn about.

---

## 3. OAuth 2.1, OIDC and token engineering

> Assumed known: `02-spring` Q167-182 (resource server, JWT validation, Authorization Server) and `01-java` Q135-140 (JWT revocation, refresh tokens, grants, OIDC, PKCE). This category is the protocol beneath that configuration.

36. `[C]` Name the four OAuth roles and walk the authorization code flow end to end, stating what travels on the front channel and what on the back channel.
37. `[C]` OAuth 2.0 is authorization, OIDC is authentication. What exactly does OIDC add, and what breaks when a team uses a plain access token as proof of login?
38. `[D]` PKCE: what problem does it solve, what are `code_verifier`, `code_challenge` and the method, and why is it now required for confidential clients too?
39. `[T]` Why were the implicit flow and the resource owner password credentials grant removed in OAuth 2.1? Give the concrete attack behind each.
40. `[D]` The `state` parameter, the `nonce` claim and PKCE all defend something. Map each to its specific attack - they are not interchangeable.
41. `[D]` Client credentials grant: when is it correct, what does "the subject is the client" mean for auditing, and what do you do about per-tenant scoping?
42. `[D]` Device authorization grant: draw the flow, and name the two rate-limit controls it requires.
43. `[D]` JWT structure: header, payload, signature. Which claims are registered, and which of them do you validate on every request?
44. `[C]` List the complete validation a resource server must perform on a JWT before trusting a single claim.
45. `[T]` `alg: none`, algorithm confusion (RS256 to HS256), and `kid` path traversal. Explain each attack and the one library-level rule that prevents all three.
46. `[T]` JWKS: how does key discovery work, how do you handle rotation, and what is the caching failure that takes production down during a rotation?
47. `[D]` Stateless JWT versus opaque token plus introspection. Compare revocation, latency, blast radius and operational cost.
48. `[T]` "We use JWTs so we can't revoke." Give three ways to revoke that are actually deployed, and the cost of each.
49. `[D]` Access token lifetime: how do you choose the number, and what is the arithmetic between it and your revocation SLA?
50. `[D]` Refresh token rotation with reuse detection. Describe the algorithm, the storage, and what happens on a legitimate race between two tabs.
51. `[D]` Where do you store tokens in a browser: localStorage, sessionStorage, memory, or an httpOnly cookie? Give the threat model for each and your answer for an SPA.
52. `[D]` The Backend-For-Frontend pattern for browser OAuth. What does it change, and what new problem does it introduce?
53. `[D]` Sender-constrained tokens: mTLS-bound tokens (RFC 8705) versus DPoP (RFC 9449). How does each bind, and when do you need one?
54. `[T]` Audience confusion: a token issued for service A is replayed against service B. Explain how this happens even with correct signature validation, and the two fixes.
55. `[D]` Token exchange (RFC 8693) and delegation. When a service calls another on a user's behalf, what are the options and which preserves the audit trail?
56. `[A]` Scopes versus roles versus fine-grained permissions in a token. Where do you draw the line, and what do you do when the token gets too big?
57. `[A]` Design single sign-on and single logout across eight applications, two of them legacy SAML. What breaks, and what do you tell the business about logout?

---

## 4. Authorization and access control models

> Assumed known: `02-spring` Q154-157 (method security, `@PreAuthorize`, domain object security) and `03-microservices` Q161, Q166 (distributed authorization, tenant isolation).

58. `[C]` RBAC, ABAC and ReBAC. Give the data model of each and one requirement that only the third can express cleanly.
59. `[D]` Role explosion: how does it happen, how do you detect it, and what do you replace roles with?
60. `[D]` The PEP/PDP/PIP/PAP model. Map each onto a concrete component in a Spring microservice architecture.
61. `[D]` Centralised authorization service versus embedded policy. Compare latency, availability coupling, consistency and auditability.
62. `[D]` Policy as code: Open Policy Agent/Rego, AWS Cedar, and Zanzibar-style systems. What problem is each actually built for?
63. `[D]` Google Zanzibar: explain relation tuples, userset rewrites, and the consistency mechanism (zookies). Why is it not just "a graph database"?
64. `[T]` An authorization check that runs before a database query and one that runs inside the query give different answers. Explain when, and which is correct.
65. `[C]` Insecure Direct Object Reference / Broken Object Level Authorization. Why is it the number one API vulnerability, and why do scanners miss it?
66. `[D]` Object-level, field-level and operation-level authorization. Give an example of a system that gets the first right and the second wrong.
67. `[T]` Replacing sequential IDs with UUIDs "fixes" IDOR. Explain exactly what it fixes and what it does not.
68. `[D]` Multi-tenant isolation: shared schema with a tenant column, schema per tenant, database per tenant. Rank by isolation strength and name the failure mode of each.
69. `[D]` How do you make tenant isolation enforceable rather than remembered? Describe at least two mechanisms below the application layer.
70. `[D]` Horizontal versus vertical privilege escalation, with an example of each that passed code review.
71. `[D]` Confused deputy: define it, give the classic AWS example, and explain how `ExternalId` and `aws:SourceArn` solve it.
72. `[D]` Delegation, impersonation and "act as" support tooling. How do you build a support-login feature without creating a backdoor?
73. `[D]` How do you test authorization? Describe an approach that finds missing checks rather than confirming present ones.
74. `[A]` Deny-by-default in a system with 4,000 endpoints and an existing permissive default. Sequence the migration.
75. `[A]` Break-glass access to production: design it. Who approves, how long does it last, what is recorded, and how do you stop it becoming routine?

---

## 5. Browser, session and web platform security

> Assumed known: `02-spring` Q158-161 (security headers, CSRF for a SPA, `StrictHttpFirewall`) and `01-java` Q141-142 (CSRF, CORS).

76. `[C]` The same-origin policy: define origin precisely, and list what it does and does not block.
77. `[D]` CORS: walk a preflight request and response, name every header, and explain what CORS is actually protecting.
78. `[T]` `Access-Control-Allow-Origin: *` with `Access-Control-Allow-Credentials: true`. What happens, and why is reflecting the `Origin` header a vulnerability?
79. `[C]` Cookie attributes: `Secure`, `HttpOnly`, `SameSite`, `Domain`, `Path`, `Max-Age`, and the `__Host-` prefix. What does each defend?
80. `[D]` `SameSite=Lax` versus `Strict` versus `None`. What did Lax-by-default fix, what did it not fix, and what broke?
81. `[D]` CSRF: the mechanism, the synchroniser token pattern, the double-submit cookie pattern, and why the second is weaker.
82. `[T]` "We use JSON APIs and bearer tokens, so we do not need CSRF protection." When is that true and when is it dangerously false?
83. `[C]` Reflected, stored and DOM-based XSS. What differs in where the payload lives and how you find each.
84. `[D]` Contextual output encoding: HTML body, attribute, JavaScript, URL and CSS contexts. Show why one encoder is not enough.
85. `[D]` Content Security Policy: explain `nonce`, `hash`, `strict-dynamic`, and why allowlists based on domains failed.
86. `[T]` A CSP with `script-src 'self'` is bypassed. Name three ways, without any inline script.
87. `[D]` Trusted Types and the DOM sink problem. What does it actually enforce and what is the rollout path on a legacy app?
88. `[D]` Clickjacking: `X-Frame-Options` versus `frame-ancestors`, and the UI redress variants that neither stops.
89. `[D]` Session fixation, session hijacking and session puzzling. What must happen at the moment of privilege change?
90. `[D]` Session lifetime design: idle timeout, absolute timeout, sliding renewal, and concurrent session policy. Give numbers you would defend.
91. `[D]` Subresource Integrity, `Referrer-Policy`, `Permissions-Policy`, COOP/COEP/CORP. What attack does each close?
92. `[T]` Open redirect is usually rated low severity. Chain it into something that is not.
93. `[A]` A ten-year-old application with inline scripts everywhere needs a CSP. Give the sequence that gets you to a strict policy without an outage.

---

## 6. Injection, deserialization and input handling

> Assumed known: `06-database` Q2-41 (SQL and parameterisation) and `01-java` Q146-147 (OWASP Top 10, SQL injection in a JPA application).

94. `[C]` SQL injection: the mechanism, and why parameterised queries stop it at a level string escaping cannot.
95. `[D]` What cannot be parameterised, and how do you safely build a query with a dynamic table name, column name or sort direction?
96. `[T]` A Hibernate/JPA application is still SQL injectable. Name three ways this happens despite using an ORM.
97. `[D]` Blind, boolean-based, time-based and out-of-band SQL injection. How does an attacker exfiltrate data with no visible output?
98. `[T]` Second-order injection: define it, and explain why input validation at the edge does not stop it.
99. `[D]` NoSQL injection in MongoDB and Elasticsearch, and injection into a Redis command stream. What replaces the quote character as the danger?
100. `[D]` OS command injection: why is `Runtime.exec` with a string different from `ProcessBuilder` with a list, and what still goes wrong with the latter?
101. `[D]` Path traversal and the zip-slip variant. Give the canonicalisation-based check you would actually write in Java.
102. `[D]` XXE: what feature of XML causes it, the three impacts, and the exact parser settings that disable it in Java.
103. `[T]` A parser is patched against XXE but still vulnerable to a billion-laughs denial of service. Explain the difference.
104. `[C]` Insecure deserialization: why is Java native deserialization dangerous even when the class you expect is the class you get?
105. `[D]` Gadget chains: explain conceptually how one is built, why `commons-collections` became famous, and what a look-ahead deserialization filter does.
106. `[D]` JEP 290 serialization filters and `ObjectInputFilter`. Write the policy you would apply and state its limits.
107. `[T]` Jackson polymorphic deserialization: what makes `enableDefaultTyping` dangerous, what did `@JsonTypeInfo` with `Id.CLASS` inherit, and what is the safe pattern?
108. `[D]` SnakeYAML, XStream and Kryo: what is the unsafe default in each, and what is the one-line hardening?
109. `[C]` SSRF: the mechanism, why it is now a top-ten risk in its own right, and what makes cloud environments especially exposed.
110. `[T]` You validate the URL against an allowlist and resolve DNS to check the IP. Explain the DNS rebinding and redirect bypasses, and the correct architecture.
111. `[D]` Server-side template injection and expression-language injection (SpEL, OGNL, Thymeleaf). Where does user input reach an evaluator in a typical Spring app?
112. `[D]` Allowlist versus denylist validation, canonicalisation order, and Unicode normalisation attacks. State the rule about the order of operations.
113. `[A]` Mass assignment and over-posting. Compare DTO separation, explicit field allowlists and framework binder configuration, and give your standard.

---

## 7. API and microservice security

> Assumed known: `03-microservices` Q121-136 (discovery, gateways, service mesh) and Q155-170 (security across service boundaries).

114. `[C]` Walk the OWASP API Security Top 10 and name the three that a traditional web application scanner will never find.
115. `[D]` Where does authentication belong: the gateway, a sidecar, or the service? Give your answer and the failure mode of the other two.
116. `[T]` The gateway authenticates, so the services trust the `X-User-Id` header. Explain the attack and the three ways to close it.
117. `[D]` Service-to-service identity: mTLS with SPIFFE/SPIRE, signed JWT assertions, or network trust. Compare rotation, revocation and audit.
118. `[D]` How does a service mesh implement mTLS, and what exactly does "zero trust networking" give you that a VPC does not?
119. `[D]` Propagating user identity through a call chain of six services. Compare token forwarding, token exchange and a signed identity header, and pick one.
120. `[D]` Rate limiting for security rather than capacity: what dimensions do you key on, and why is per-IP alone useless?
121. `[D]` Algorithms: token bucket, leaky bucket, fixed window, sliding window log, sliding window counter. Which do you deploy at the edge and why?
122. `[T]` An attacker is rate-limited per API key, so they rotate keys. What do you key on instead, and what does that cost you?
123. `[D]` Idempotency keys and replay protection. Design a request-signing scheme with a timestamp and nonce, and state the clock-skew window.
124. `[D]` Webhook security: signature scheme, replay window, secret rotation, and how a receiver avoids SSRF when it calls you back.
125. `[D]` GraphQL: introspection, query depth and complexity, batching attacks, and why field-level authorization is mandatory rather than optional.
126. `[D]` gRPC security: channel credentials versus call credentials, interceptors, and reflection in production.
127. `[D]` API keys: what are they good for, what are they not, and how do you scope, rotate and revoke them at scale?
128. `[D]` Server-side request forgery from inside a microservice mesh - the internal-network variant. Why is the blast radius bigger here?
129. `[T]` Excessive data exposure and the "filter it in the frontend" anti-pattern. How do you catch it automatically?
130. `[T]` A dependency-free microservice with no known CVEs is compromised through its own API. Name the most likely class of flaw and how you would have found it.
131. `[A]` You own an API platform with 300 services and no consistent authorization. Design the paved road, including how you get teams onto it.

---

## 8. Applied cryptography and TLS

> Assumed known: nothing - no earlier pack covers cryptography, so this category is self-contained. It is about choosing and operating primitives, not implementing them; you will not be asked to write AES.

132. `[C]` Symmetric versus asymmetric cryptography: what each is for, and the hybrid scheme every real protocol actually uses.
133. `[C]` Hash, MAC, signature and encryption. State what property each provides, and which two are routinely confused.
134. `[D]` AES modes: ECB, CBC, CTR, GCM. What is wrong with the first two in 2026, and what does AEAD add?
135. `[T]` You encrypt with AES-GCM and reuse a nonce once. Explain precisely what an attacker recovers, and how you prevent reuse at scale.
136. `[D]` Padding oracle attacks: the mechanism against CBC, why "encrypt-then-MAC" fixes it, and why AEAD makes the question disappear.
137. `[D]` Key derivation: HKDF versus PBKDF2 versus Argon2. Which do you use for a password, which for deriving from a master key, and why never the wrong way round.
138. `[D]` `SecureRandom` in Java: blocking versus non-blocking sources, seeding in a container, and how to detect a bad-entropy incident.
139. `[T]` Constant-time comparison: why does `String.equals` on a MAC matter, and what does Java give you instead?
140. `[D]` Digital signatures: RSA-PSS versus ECDSA versus Ed25519. Compare size, speed, failure modes and library support.
141. `[T]` ECDSA nonce reuse broke the PlayStation 3. Explain the mathematics at a level an interviewer will accept, and what deterministic ECDSA changes.
142. `[D]` TLS 1.3 handshake: what happens in one round trip, what was removed from 1.2, and what does 0-RTT cost you.
143. `[D]` Forward secrecy: what it means, which key exchanges provide it, and what an adversary with a stolen private key can and cannot do.
144. `[D]` Certificate validation: the chain, the trust store, hostname verification, expiry, revocation. Which step do custom Java `TrustManager` implementations usually break?
145. `[D]` CRL, OCSP, OCSP stapling and short-lived certificates. Why did revocation effectively fail on the public web?
146. `[D]` Certificate pinning: static versus dynamic, the outage risk, and what replaced it for browsers (HSTS preload, CAA, Certificate Transparency).
147. `[A]` Post-quantum cryptography: what is actually at risk, what "harvest now, decrypt later" means for your data, and what would you do this year.

---

## 9. Secrets, keys and data protection

> Assumed known: `06-database` Q271-275 (encryption at rest, key management, PII, auditing) and `07-devops` Q118-131 (configuration and secrets management).

148. `[C]` Where do secrets belong, and why is an environment variable both the standard answer and a bad one?
149. `[D]` Compare HashiCorp Vault, AWS Secrets Manager, SSM Parameter Store and Kubernetes Secrets on encryption, access control, rotation, audit and cost.
150. `[D]` The secret-zero problem. How does a workload prove who it is before it has any credential?
151. `[D]` Envelope encryption: explain data keys, key encryption keys, and why you do not send your data to the KMS.
152. `[D]` KMS key policies, grants and IAM. Explain how a cross-account decrypt is authorised and where teams get it wrong.
153. `[T]` Key rotation: what actually rotates in AWS KMS automatic rotation, what it does not re-encrypt, and what you must do for a real compromise.
154. `[D]` Encryption at rest: full-disk, database TDE, column-level and application-level. For each, name the attacker it stops and the one it does not.
155. `[T]` "The database is encrypted at rest, so the PII is safe." Dismantle that claim.
156. `[D]` Deterministic versus randomised encryption, and searchable encryption. What query capability does each preserve and what does it leak?
157. `[D]` Tokenization versus encryption versus hashing for card data and national identifiers. Which reduces compliance scope and how?
158. `[T]` Pseudonymisation, anonymisation and k-anonymity. Why is "we removed the name" almost never anonymisation?
159. `[D]` Secret scanning and leaked-credential response. Describe the full remediation for a live key committed to a public repository.
160. `[T]` A secret was removed in a follow-up commit. Explain everything still wrong and the exact order of the real fix.
161. `[D]` Crypto-shredding for the right to erasure: per-subject keys, what it makes possible, and where it fails (backups, indexes, analytics).
162. `[A]` Design secret management for 200 services across three environments and two clouds. State your defaults and the migration path from what teams do today.

---

## 10. Java and Spring Security in practice

> Assumed known: `02-spring` Q143-182 (Spring Security and OAuth2 in full) and `01-java` Q132-149. This category starts where that configuration stopped.

163. `[C]` Order matters in the Spring Security filter chain. Name the filters in sequence and say what breaks when a custom filter is added in the wrong place.
164. `[D]` `authorizeHttpRequests` versus method security versus domain object security. Where should each rule live, and what happens when they disagree?
165. `[T]` `@PreAuthorize` on a method silently does nothing. Give four distinct causes.
166. `[D]` Spring Security's CSRF token repository options, and exactly what changed for SPAs in Spring Security 6.
167. `[T]` `SecurityContextHolder` strategies, propagation across `@Async` and reactive contexts, and the classic leak in a thread pool.
168. `[D]` Spring Security as an OAuth2 resource server: how `JwtDecoder` validates, how to add a custom validator, and how to map claims to authorities.
169. `[D]` Method security in a reactive stack: what differs, and why blocking authorization calls are a production incident waiting to happen.
170. `[D]` Spring Boot Actuator exposure: what is dangerous by default, what `heapdump` and `env` leak, and how you secure the management port properly.
171. `[D]` Log4Shell (CVE-2021-44228): what was the actual mechanism, why did the first mitigation fail, and what did it teach you about transitive dependencies?
172. `[D]` Spring4Shell (CVE-2022-22965): explain the class-loader path through data binding, and the general lesson about binding to domain objects.
173. `[T]` Spring Cloud Function SpEL injection and Spring Data property-path expressions. What is the shared root cause across all three Spring CVEs?
174. `[D]` The Java `SecurityManager` is deprecated for removal. What did it actually provide, why did it fail, and what replaces it?
175. `[D]` Java module system, `--add-opens` and reflective access. What security value do strong encapsulation and integrity by default provide?
176. `[D]` `MessageDigest`, `Cipher`, `KeyStore` and the JCA provider model. How do you enforce an approved algorithm set across an organisation?
177. `[D]` Dependency hygiene in a Gradle/Maven build: `dependencyManagement`, version catalogs, lock files, and the transitive upgrade that breaks at runtime not build time.
178. `[D]` Static analysis for Java: SpotBugs/find-sec-bugs, Semgrep, CodeQL and SonarQube. What class of bug does each find, and what is your false-positive strategy?
179. `[A]` You must prove a Java service is secure to an auditor with no security background. What evidence do you produce, and what do you refuse to promise?

---

## 11. Supply chain, dependencies and CI/CD security

> Assumed known: `07-devops` Q48-63 (build and dependency supply chain) and Q232-248 (pipeline and runtime security). This category is the attacker's view of the same machinery.

180. `[C]` What is a software supply chain attack? Distinguish the four classes with a real example of each.
181. `[D]` SBOM: SPDX versus CycloneDX, what you generate it from, and the honest answer about what an SBOM actually buys you.
182. `[D]` Dependency confusion: the exact mechanism, and the three registry-side controls that prevent it.
183. `[D]` Typosquatting, starjacking and protestware. What automated control catches each before it reaches a build?
184. `[T]` The `xz-utils` backdoor was not found by any scanner. What did find it, and what does that tell you about where to spend effort?
185. `[D]` Pinning: version ranges, exact versions, lock files and digest pinning. Where does each apply and what is the maintenance cost?
186. `[D]` SLSA levels: what does each level require, what is provenance, and what does verification look like at deploy time?
187. `[D]` Artifact signing with Sigstore/cosign: keyless signing, Fulcio, Rekor. Explain what the transparency log adds.
188. `[D]` Reproducible builds: what makes a build non-reproducible in a JVM project, and why does anyone care?
189. `[D]` CI/CD as the highest-value target. List the specific attacks on a pipeline, from `pull_request_target` to a compromised self-hosted runner.
190. `[D]` OIDC federation from a CI provider to a cloud account. Explain the trust configuration and the subject-claim mistake that lets any repository assume your role.
191. `[T]` A build step runs `curl | bash` from a vendor's site. Rank the risks and give the fix that does not break the vendor relationship.
192. `[D]` Base image strategy: distroless, Alpine, UBI, or a golden image. Compare attack surface, patch velocity and debuggability.
193. `[D]` Vulnerability management at scale: 4,000 findings in the backlog. Describe the triage and SLA model you would actually run.
194. `[T]` A critical CVE in a transitive dependency has no fixed version. What are your five options, in order?
195. `[A]` Design the release gate: what blocks a deployment, what warns, who can override, and how you keep the gate from being routinely bypassed.

---

## 12. Container and Kubernetes security

> Assumed known: `07-devops` Q64-117 (containers, Kubernetes core, networking and cluster operations) and Q239-243 (admission control, pod security, runtime detection).

196. `[C]` What actually isolates a container? Name the kernel primitives and state what a container is not.
197. `[D]` Container escape: the four common paths (privileged mode, hostPath, exposed Docker socket, kernel vulnerability) and the control for each.
198. `[D]` Capabilities, seccomp and AppArmor/SELinux. What does each restrict, and what is a sane default set for a Java service?
199. `[D]` Running as non-root, read-only root filesystem, and no privilege escalation. Why does a Java image break under these and how do you fix it?
200. `[D]` Image hardening: layers, build secrets, multi-stage builds, and what `docker history` reveals.
201. `[T]` Image scanning: what Trivy/Grype actually check, why base-image CVE counts are misleading, and how you avoid the "10,000 findings" report.
202. `[C]` Kubernetes RBAC: subjects, roles, bindings, and the three permissions that are effectively cluster admin.
203. `[T]` A pod has `get secrets` in its namespace. Explain why this is worse than it sounds and what else it enables.
204. `[D]` Service accounts and token projection. What changed with bound service account tokens and why does it matter?
205. `[D]` Pod Security Admission (baseline, restricted, privileged) and what replaced PodSecurityPolicy. What does `restricted` actually enforce?
206. `[D]` Admission control with OPA Gatekeeper or Kyverno: validating versus mutating, failure policy, and the availability risk you just added.
207. `[D]` NetworkPolicy: default-deny egress, why it is rarely deployed, and what a CNI must support for it to work.
208. `[T]` Kubernetes Secrets: how are they stored, what does etcd encryption at rest give you, and why do teams reach for an external secrets operator?
209. `[D]` Multi-tenancy in Kubernetes: namespace, virtual cluster, or separate cluster. Where is the real isolation boundary?
210. `[D]` Runtime security with Falco/eBPF: what signals are worth alerting on and what generates pure noise?
211. `[T]` Your cluster passes CIS benchmark scanning and is still trivially compromised. Give the most likely reason.
212. `[A]` Design the security baseline for a platform team running 40 teams' workloads on shared clusters. What is enforced, what is advised, and how do you roll it out?

---

## 13. AWS cloud security

> Assumed known: general AWS familiarity. Service selection, cost and networking depth belong to `05-aws`; this category is the security control plane.

213. `[C]` IAM policy evaluation logic: walk the full order of explicit deny, SCP, resource policy, identity policy, permission boundary and session policy.
214. `[T]` Identity-based versus resource-based policies. When does a resource policy alone grant access, and when do you need both sides?
215. `[D]` `AssumeRole`, trust policies and `sts:ExternalId`. Explain the confused deputy scenario this closes.
216. `[T]` `"Principal": "*"` in an S3 bucket policy with a `aws:PrincipalOrgID` condition. Is that safe? Explain what actually determines the answer.
217. `[D]` Service Control Policies versus permission boundaries versus IAM policies. Which is a guardrail, which is a grant, and how do they interact?
218. `[D]` IAM condition keys worth knowing: `aws:SourceIp`, `aws:SourceVpce`, `aws:PrincipalOrgID`, `aws:ResourceOrgID`, `aws:RequestTag`. Give a control built from each.
219. `[D]` IAM Access Analyzer: external access findings versus unused access findings versus policy generation. How do you operationalise each?
220. `[D]` Long-lived access keys: why do they persist, what replaces them for CI, for EC2, for EKS, and for a developer laptop?
221. `[D]` IRSA and EKS Pod Identity. Explain the token flow and what a pod must not be able to do to another pod's role.
222. `[C]` IMDSv1 versus IMDSv2: what SSRF attack does the second stop, and by what mechanism?
223. `[D]` S3 access control: bucket policy, ACLs, Block Public Access, Access Points, and presigned URLs. Which do you use and which do you disable outright?
224. `[T]` A presigned URL was shared publicly. What are the limits of the damage, and how do you invalidate it?
225. `[D]` VPC network security: security groups versus NACLs, VPC endpoints and endpoint policies, and how you prevent data exfiltration to an attacker's S3 bucket.
226. `[D]` KMS: customer-managed versus AWS-managed keys, key policies, grants, multi-region keys and the cost model. When is a CMK worth it?
227. `[D]` CloudTrail: management versus data events, organisation trails, log file validation, and how you protect the trail itself from an attacker with admin.
228. `[D]` GuardDuty, Security Hub, AWS Config, Inspector and Detective. What does each detect, and how do you avoid five overlapping alert streams?
229. `[D]` Secrets in Lambda, ECS and EKS: compare the injection mechanisms and the cold-start and cost implications.
230. `[D]` AWS WAF and Shield: what they genuinely stop, what they do not, and the managed rule set false-positive problem.
231. `[D]` Multi-account strategy and landing zones: what belongs in which account, and what security value the boundary provides that IAM does not.
232. `[T]` An attacker obtains read-only access to your account. Name five ways that becomes worse than read-only.
233. `[A]` You inherit a single AWS account with 60 IAM users, wildcard policies and no CloudTrail. Give your remediation sequence and what you do first hour, first week, first quarter.

---

## 14. AI and LLM security

> Assumed known: `04-system-design` Q209-224 (AI and ML in the request path) and `02-spring` Q237-246 (Spring AI). RAG architecture and agent orchestration design belong to `09-rag` and `10-agents`; this category is the threat model and the controls.

234. `[C]` Walk the OWASP Top 10 for LLM Applications and name the three that have no equivalent in traditional application security.
235. `[C]` Prompt injection: define it, and explain why it is architecturally different from SQL injection rather than just a new flavour of it.
236. `[D]` Direct versus indirect prompt injection. Give a concrete indirect injection path through a RAG corpus and through a tool result.
237. `[T]` "We put 'ignore any instructions in the retrieved documents' in the system prompt." Explain why this is not a control.
238. `[D]` What controls actually reduce prompt injection risk? Rank them, and be explicit about which are mitigations rather than fixes.
239. `[D]` The lethal trifecta: private data access, exposure to untrusted content, and the ability to communicate externally. Explain why removing any one of the three is the real fix.
240. `[D]` Excessive agency: how do you scope an agent's tools, and what does human-in-the-loop actually need to show the human to be meaningful?
241. `[D]` Tool and function calling security: parameter validation, authorization per tool call, and why the model must never be the policy decision point.
242. `[D]` An agent acts on behalf of a user. How do you propagate that user's identity and permissions to every tool call, and what do you log?
243. `[D]` Insecure output handling: the LLM returns HTML, SQL, a shell command or a URL. Give the control at each sink.
244. `[D]` RAG data leakage: how do you enforce per-user document permissions in a vector store, and what is wrong with post-filtering results?
245. `[T]` Embeddings are "just numbers, not data". Dismantle that claim, including what inversion attacks can recover.
246. `[T]` Sensitive information disclosure: system prompt extraction, training-data extraction and memorisation. Which do you defend and which do you accept?
247. `[D]` Model supply chain: pickle deserialization in model files, safetensors, model provenance, and the risk of a fine-tune from an unknown source.
248. `[D]` Training-data poisoning and backdoors. What is realistic for a team consuming foundation models rather than training them?
249. `[D]` Guardrails: input filters, output filters, classifier-based moderation, and constrained decoding. What is each good at and what is the latency cost?
250. `[D]` PII in prompts and logs: what leaves your boundary when you call a hosted model, and what contractual and technical controls do you put in place?
251. `[D]` Denial of wallet: unbounded token consumption, recursive agent loops, and expensive tool calls. Design the budget controls.
252. `[D]` Model Context Protocol security: server trust, tool description poisoning, confused deputy across servers, and the consent model.
253. `[D]` Multi-agent systems: what new attack surface appears when agents talk to agents, and how do you contain a compromised agent?
254. `[T]` Jailbreaks versus prompt injection - they are different problems with different owners. Explain the distinction and who cares about each.
255. `[D]` How do you red-team an LLM feature? Describe the process, the automation, and how you decide a release is acceptable.
256. `[D]` Evaluation as a security control: what do you measure, how do you stop regressions, and what does a security gate for a prompt change look like?
257. `[D]` Adversarial inputs to embeddings and retrieval: poisoning the corpus for retrieval ranking. What monitoring detects it?
258. `[D]` The EU AI Act and NIST AI RMF at an engineering level: what obligations turn into code, logging or documentation?
259. `[A]` Design the security architecture for an internal agent that can read the wiki, query the database and open pull requests.
260. `[A]` The business wants a customer-facing agent that can issue refunds. What do you allow, what do you refuse, and how do you present the trade-off?

---

## 15. Detection, logging and incident response

> Assumed known: `03-microservices` Q137-154 (distributed observability) and `07-devops` Q201-217 (alerting, on-call and incident response). This category is what changes when the incident has an adversary.

261. `[C]` What must a security-relevant audit log record, and what must it never contain?
262. `[D]` Application logs versus audit logs versus security telemetry. Different retention, different integrity requirements, different consumers - explain each.
263. `[T]` Log integrity: append-only storage, hash chaining, write-once buckets. How do you stop an attacker with production access from editing the evidence?
264. `[D]` Detection engineering: what makes a good detection rule, and how do you measure a detection's value rather than counting alerts?
265. `[T]` Your SIEM produces 4,000 alerts a day and nobody looks at them. Diagnose the failure and give the fix that is not "tune the rules".
266. `[D]` Name five high-signal application-level detections that most teams do not have.
267. `[D]` Canary tokens, honeypots and honey credentials. Where do they pay off in an application architecture?
268. `[C]` Walk the incident response lifecycle. What is the single decision that most often goes wrong, and why?
269. `[D]` Containment versus evidence preservation. You need to isolate a compromised host - what do you capture first and in what order?
270. `[D]` What is a security incident commander responsible for, and how does the role differ from an availability incident?
271. `[D]` Breach notification: GDPR's 72 hours, the trigger, and what "become aware" means in engineering terms.
272. `[T]` The blameless post-incident review for a security incident. What is different from an availability review, and what must not be blameless?
273. `[D]` Tabletop exercises and purple teaming. Design one for a credential-compromise scenario and state what "pass" means.
274. `[T]` You detect an attacker in your environment. Do you eject them immediately? Argue both sides and give your default.
275. `[A]` Design the detection and response capability for a 300-engineer product organisation with no SOC and no budget for one.

---

## 16. Compliance, privacy and governance

> Assumed known: `06-database` Q271-278 (encryption, PII, auditing, erasure, retention) and `07-devops` Q246 (compliance as code). This category is what an architect must convert into engineering requirements.

276. `[C]` GDPR at an engineering level: lawful basis, data subject rights, data minimisation, purpose limitation. Which one most often changes a data model?
277. `[D]` Right to erasure across a microservice architecture with event streams, backups, search indexes and a data warehouse. What is genuinely achievable?
278. `[D]` Data residency and cross-border transfer. What do the technical controls actually look like in a multi-region deployment?
279. `[D]` PCI DSS scope: what puts a service in scope, and the three architectural moves that take it back out.
280. `[D]` SOC 2 Type II versus ISO 27001 versus a customer security questionnaire. What evidence does each need from engineering, and what is the recurring cost?
281. `[D]` Data classification: define the tiers, and explain how a classification becomes an enforced control rather than a spreadsheet.
282. `[D]` Privacy by design and a DPIA. When is one required, and what does an engineer contribute to it?
283. `[T]` "We are compliant, therefore we are secure." Give the strongest counterexample and the strongest defence of compliance work.
284. `[D]` Penetration test versus vulnerability scan versus bug bounty versus red team. What does each buy, and in what order do you adopt them?
285. `[D]` Third-party and vendor risk: how do you assess a SaaS vendor you must integrate with, and what do you do when the answer is "they are bad but mandatory"?
286. `[A]` Design a security governance model that a fast-moving engineering organisation will actually follow.

---

## 17. Security architecture design exercises and leadership

> Q287-292 are worked as full exercises in [scenario-questions.md](scenario-questions.md). Q293-300 have no model answer - they are your stories, in STAR-L form.

287. `[A]` Design zero-trust service-to-service identity for 300 services across three Kubernetes clusters and two clouds.
288. `[A]` Design end-to-end tenant isolation for a multi-tenant SaaS platform serving 5,000 customers, including the compliance evidence.
289. `[A]` Design secret and key management for 200 services, three environments and a regulated workload.
290. `[A]` Design the security architecture for an LLM agent with tool access to production systems.
291. `[A]` Design a secure-by-default paved road for 40 product teams, and the mechanism that keeps them on it.
292. `[A]` Design a PCI and PII scope-reduction programme for an existing monolith that handles card data everywhere.
293. `[A]` Tell me about a vulnerability you found, or that was found in your system, and what you changed so that class of bug could not recur.
294. `[A]` Tell me about a security incident you were part of. What was your role, what was the timeline, and what did the post-incident review change?
295. `[A]` Tell me about a time you blocked or delayed a release for a security reason. How did you make the case, and what did it cost?
296. `[A]` Tell me about a security standard or control you drove across teams you did not own.
297. `[A]` Tell me about a time you accepted a security risk deliberately. Who signed it, what was the compensating control, and how did it end?
298. `[A]` Tell me about a time you were wrong about a security judgement, and what changed in how you assess risk.
299. `[A]` Tell me about how you have changed engineers' behaviour on security - not by policy, but by making the secure path the easy one.
300. `[A]` Tell me about a security decision you made that a senior stakeholder disagreed with. How did you handle it?
