# Security Cheatsheet

Fast revision. Java/Spring and AWS unless another stack is named. Assumes [../02-spring/cheatsheet.md](../02-spring/cheatsheet.md) and [../06-database/cheatsheet.md](../06-database/cheatsheet.md).

---

## Threat modeling in one screen

Four questions (Shostack): **What are we building? What can go wrong? What are we going to do about it? Did we do a good job?**

| STRIDE | Violates | Mitigation |
| --- | --- | --- |
| **S**poofing | Authenticity | Strong authentication, mTLS, signed tokens |
| **T**ampering | Integrity | Signatures, MACs, integrity-protected storage |
| **R**epudiation | Non-repudiation | Audit logs, signed actions |
| **I**nformation disclosure | Confidentiality | Encryption, authorization, minimisation |
| **D**enial of service | Availability | Rate limits, quotas, timeouts, isolation |
| **E**levation of privilege | Authorization | Least privilege, deny-by-default |

Output artefact = a **list of decisions and mitigations with owners**, not a diagram. A "threat model" with a diagram and no decisions was a drawing exercise.

Model selection: **STRIDE** for a system design, **attack trees** for one high-value asset, **PASTA** for business-risk-driven programmes, **LINDDUN** for privacy.

Vocabulary: *vulnerability* = the flaw; *threat* = the actor/event; *risk* = likelihood × impact; *exploit* = the working code.

---

## Priority: CVSS is not risk

| Signal | Answers |
| --- | --- |
| **CVSS base** | how bad *in the abstract* - never a priority on its own |
| **EPSS** | probability of exploitation in the next 30 days |
| **KEV** (CISA) | is it being exploited *right now* |
| **Reachability** | do we call the vulnerable code path |
| **Exposure** | internet-facing? untrusted input? |

Practical rule: **KEV or EPSS > 10 percent, and reachable, and exposed → page.** CVSS 9.8, unreachable, internal → next sprint. A CVSS 5.3 in KEV on an internet-facing service beats both.

---

## Password and credential storage

**Argon2id** (default 2026): ≥19 MiB memory, ≥2 iterations, parallelism 1. Or **bcrypt** cost ≥12, or **scrypt**, or **PBKDF2-HMAC-SHA256** ≥600k iterations if FIPS-bound.

- **Salt** - per-password, stored with the hash. Defeats rainbow tables and cross-user comparison.
- **Pepper** - global, stored *outside* the database (HSM/KMS). Defeats a database-only dump.
- **Work factor** - encoded in the hash, so it can be raised per-user on next login.

**bcrypt truncates at 72 bytes.** Pre-hashing with SHA-256 and passing raw bytes creates null-byte truncation; pre-hash to **base64** or use Argon2id.

Never: MD5, SHA-1, unsalted anything, encryption instead of hashing, a homemade scheme.

| Attack | Signal | Control |
| --- | --- | --- |
| Brute force | many failures, one account | rate limit + work factor |
| Credential stuffing | many accounts, one failure each, valid-looking pairs | breached-password check, device/IP reputation, MFA |
| Password spraying | few common passwords across many accounts | blocklist of common passwords, per-IP/ASN limits |

Lockout after N failures = a **denial-of-service you built yourself**. Prefer exponential backoff, per-IP+per-account keying, and CAPTCHA/step-up over hard lockout.

MFA strength: **passkey/WebAuthn (phishing-resistant) > push with number matching > TOTP > SMS OTP**. A password fallback next to a passkey means your phishing resistance is the *password's*.

---

## OAuth 2.1 / OIDC decision table

| Situation | Grant |
| --- | --- |
| Any user-facing app (web, SPA, mobile, desktop) | **Authorization code + PKCE** |
| Service to service, no user | **Client credentials** |
| TV, CLI, no browser | **Device authorization** |
| Service acting for a user downstream | **Token exchange (RFC 8693)** |
| Implicit, ROPC | **removed in 2.1** - never |

Removed and why: **implicit** leaked tokens in the URL fragment (history, referrer, logs) with no client authentication; **ROPC** taught apps to handle raw passwords and cannot do MFA or federation.

The three defences are **not** interchangeable:

| Parameter | Defeats |
| --- | --- |
| `state` | CSRF on the redirect endpoint |
| `nonce` (ID token claim) | ID token replay/injection |
| PKCE | authorization code interception |

**JWT validation, complete list**: signature against the correct key from JWKS → `alg` against an **expected allowlist** (never from the header) → `iss` → `aud` → `exp`/`nbf` with small clock skew → `typ`/token-use → revocation or `sid` check if stateful → *then* read claims.

Three attacks, one rule: `alg: none`, **RS256→HS256 confusion**, `kid` traversal/injection. The rule: **the server chooses the algorithm and the key, never the token**.

| Choice | Stateless JWT | Opaque + introspection |
| --- | --- | --- |
| Revocation | at `exp` only | immediate |
| Latency | none | a network hop (cache it) |
| Blast radius of key loss | all tokens | all tokens |
| Auth-server coupling | none per request | availability coupling |

**Token lifetime *is* the revocation SLA.** Want 5-minute revocation on a stateless design? Use a 5-minute access token. Refresh tokens: rotate with **reuse detection** (reuse → kill the whole family); allow a small grace window for the two-tab race.

Browser storage: **memory + httpOnly `__Host-` refresh cookie**, or a **BFF** holding tokens server-side. `localStorage` means any XSS is a full account takeover.

Sender-constrained tokens: **mTLS-bound (RFC 8705)** where you control both ends; **DPoP (RFC 9449)** for public clients. Both turn a stolen bearer token into a useless one.

**Audience confusion**: a valid signature is not a valid destination. Fix = validate `aud` strictly, plus per-service audiences via token exchange.

---

## Authorization

| Model | Data model | Use it for |
| --- | --- | --- |
| **RBAC** | user → role → permission | coarse, stable job functions |
| **ABAC** | attributes + policy | context: time, location, device, data classification |
| **ReBAC** (Zanzibar) | relation tuples `object#relation@subject` | "shared with me", nested folders, org hierarchies |

**BOLA/IDOR is API vulnerability #1** because authentication passes and nothing checks *this principal* against *that object*. Scanners miss it: it needs two accounts and a notion of ownership.

UUIDs make enumeration impractical. They do **not** fix authorization - a leaked, logged or shared UUID is fully exploitable.

Three layers, all required: **operation** (may you call this endpoint) → **object** (may you touch this instance) → **field** (may you see/set this attribute).

Enforce **below the application layer**: row-level security with `FORCE ROW LEVEL SECURITY` and a non-owner role, `SET LOCAL app.tenant_id` at transaction start, repositories that cannot express an unscoped query. A hand-written `WHERE tenant_id = ?` is a probabilistic control.

Tenant isolation, weakest to strongest: **shared schema + tenant column** (cheap, one bug = cross-tenant read) → **schema per tenant** (migration cost of silo, isolation of pool - usually the worst trade) → **database per tenant** (strong, expensive, per-tenant key and shred possible).

**Testing authorization**: generate cross-tenant/cross-user probes for every route from the route table with two fixture principals, and fail the build on anything that is not 404. Tests written by hand confirm the checks that exist.

**Confused deputy**: your service uses its own authority on someone else's instruction. AWS fix = `sts:ExternalId` (third party) and `aws:SourceArn`/`aws:SourceAccount` (service principals).

---

## Browser platform, short form

| Cookie attribute | Defends |
| --- | --- |
| `Secure` | plaintext interception |
| `HttpOnly` | theft via XSS |
| `SameSite=Lax`/`Strict` | CSRF (Lax = the default since 2020) |
| `__Host-` prefix | subdomain cookie injection/fixation |
| `Domain` (omit it) | omitting = host-only, which is what you want |

`SameSite=Lax` fixed cross-site POST CSRF, **not** top-level-GET CSRF and not same-site attacks from a compromised subdomain. So keep CSRF tokens.

CSRF patterns: **synchroniser token** (server-side state, strong) > **double-submit cookie** (no state, but broken by any subdomain that can set cookies).

"JSON + bearer token so no CSRF" is **true** only if the credential is never sent automatically by the browser. One `Authorization` header = safe. Any cookie in the auth path = not safe.

**XSS**: reflected (payload in the request) / stored (payload in the database) / DOM (payload never reaches the server). Output encoding is **context-specific** - HTML body, attribute, JS, URL and CSS need different encoders, and there is no single "escape" that is correct in all five.

**CSP that works**: `script-src 'nonce-{random}' 'strict-dynamic'; object-src 'none'; base-uri 'none'`. Domain allowlists failed - JSONP endpoints, Angular on a CDN and open redirects on allowlisted hosts all bypass them. `'self'` is bypassed via file upload, JSONP on the same origin, and a path-traversal-ish URL that serves user content.

Rollout order on a legacy app: `Content-Security-Policy-Report-Only` → collect → nonce the inline scripts → move handlers out of attributes → `strict-dynamic` → enforce. Trusted Types last, and it is the one that actually kills DOM XSS.

Others: **SRI** (compromised CDN), **`Referrer-Policy`** (URL leakage), **`frame-ancestors`** (clickjacking; replaces `X-Frame-Options`), **COOP/COEP** (cross-window attacks, Spectre).

**Session**: rotate the session id at every privilege change (login, step-up, impersonation exit). Idle 15-30 min, absolute 8-12 h for normal apps; 5-15 min idle for admin/financial.

Open redirect is "low severity" until you chain it: OAuth `redirect_uri` abuse, CSP `'self'` bypass, token leakage via referrer, phishing with your domain in the URL.

---

## Injection quick reference

| Class | Root cause | Fix |
| --- | --- | --- |
| SQL | data parsed as code | parameterised statements (structure fixed *before* data arrives) |
| Command | shell metacharacters | `ProcessBuilder` with a list, no shell; still validate arguments (`--` and flag injection) |
| Path traversal / zip-slip | unresolved relative paths | canonicalise **then** verify `startsWith(baseDir)` |
| XXE | external entity resolution | disable DTDs entirely on the factory |
| Deserialization | attacker controls object graph construction | never deserialise untrusted native Java; allowlist filter |
| SSTI / EL | user input reaching an evaluator | never build template or SpEL/OGNL strings from input |
| SSRF | server fetches an attacker-chosen URL | egress proxy with a destination policy; never validate-then-fetch |

**Cannot be parameterised**: table names, column names, `ASC`/`DESC`, `LIMIT` in some drivers. Map user input to an **allowlist of literals** - never interpolate.

ORM is still injectable: native/HQL string concatenation, `Sort`/`Pageable` property names, and `@Query` with SpEL or a dynamic `ORDER BY`.

XXE ≠ billion laughs. XXE = *external* entity resolution (file read, SSRF); billion laughs = *internal* entity expansion (memory DoS). Disabling DTDs fixes both; disabling only external entities fixes one.

```java
// XXE-safe
f.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
```

```java
// Serialization allowlist
ObjectInputFilter.Config.setSerialFilter(
    ObjectInputFilter.Config.createFilter("com.acme.dto.*;java.base/*;!*"));
```

Unsafe defaults: Jackson `enableDefaultTyping`, `@JsonTypeInfo(use = Id.CLASS)`, SnakeYAML `new Yaml()` (use `SafeConstructor`), XStream (allowlist required), Kryo (`setRegistrationRequired(true)`).

**Validation order, always**: decode → canonicalise → Unicode-normalise (NFC) → validate against an allowlist → use. Validating before canonicalising is the bug.

---

## Crypto choices

| Need | Use | Never |
| --- | --- | --- |
| Encrypt data | **AES-256-GCM** or ChaCha20-Poly1305 | ECB, unauthenticated CBC |
| Integrity with a shared key | **HMAC-SHA256** | truncated/homemade MAC |
| Signature | **Ed25519**, or ECDSA P-256, or RSA-PSS 3072 | RSA PKCS#1 v1.5 for new work |
| Password hash | **Argon2id** | any fast hash |
| Derive from a high-entropy key | **HKDF** | PBKDF2 (wrong tool) |
| Derive from a password | **Argon2id/PBKDF2** | HKDF (no work factor) |
| Random | **`SecureRandom`** | `Random`, `Math.random()`, `UUID` for tokens... (UUIDv4 is fine, from a CSPRNG) |
| Compare secrets | **`MessageDigest.isEqual`** | `String.equals` (timing leak) |

**GCM nonce reuse with the same key = catastrophic**: XOR of the two plaintexts *and* recovery of the authentication subkey, so the attacker can forge arbitrary messages. Use a 96-bit random nonce with a rekey budget (~2³² messages), or a strict counter. This is the number one applied-crypto footgun.

**AEAD** = confidentiality + integrity + associated data in one primitive, which is why padding oracles stop being a question.

**TLS 1.3**: 1-RTT handshake, forward secrecy mandatory (ephemeral DH only), AEAD only, no RSA key transport, no renegotiation, no compression. **0-RTT is replayable** - only for idempotent requests, never for a state change.

**Certificate validation** = chain to a trusted root + **hostname match** + validity dates + revocation. Custom `TrustManager` implementations almost always drop hostname verification, which silently accepts any valid certificate for any name.

Revocation failed on the public web: CRLs are huge, OCSP is a privacy leak and a latency hit, and browsers **soft-fail**. What replaced it: **short-lived certificates**, Certificate Transparency, CAA, HSTS preload. Pinning is largely deprecated for browsers (outage risk far exceeds the benefit).

Post-quantum: signatures are fine for now; **key exchange is the urgent one** because of harvest-now-decrypt-later. Practical 2026 step = hybrid X25519+ML-KEM at the TLS edge, and an inventory of long-lived encrypted data.

---

## Secrets and keys

Hierarchy of desirability: **no secret (workload identity) > short-lived dynamic credential > stored secret rotated automatically > stored secret**.

**Secret zero** is solved by *platform attestation*: the Kubernetes service account token, the EC2 instance identity document, the CI provider's OIDC token. The platform vouches for the workload; nothing has to be pre-shared.

Environment variables leak into `/proc/<pid>/environ`, crash dumps, `env` output, child processes, Actuator `/env`, and logs. Prefer a **mounted tmpfs volume (CSI driver)** or an SDK fetch at startup.

**Envelope encryption**: KMS holds the KEK; a per-object/per-tenant DEK encrypts the data; the wrapped DEK is stored next to the ciphertext. Data never goes to the KMS; only the small DEK does.

**KMS automatic rotation rotates the backing key material only.** Old data is decryptable with old material; nothing is re-encrypted, and the key ARN never changes. A real compromise requires generating a new key, re-encrypting, and revoking grants.

| Encryption at rest | Stops | Does not stop |
| --- | --- | --- |
| Full disk | stolen disk | anything with an OS session |
| Database TDE | stolen files/backups | any authenticated SQL query |
| Column-level (DB) | casual DBA browsing | the application, and SQL injection |
| Application-level | the database and its operators | a compromised application |

So "the database is encrypted at rest" says nothing about SQL injection, a compromised app, an over-permissioned user, or a leaked export.

| For | Reduces compliance scope? | Preserves | Reversible |
| --- | --- | --- | --- |
| Hashing | yes | equality only | no |
| Tokenization | **yes** | format, equality | yes, via the vault |
| Encryption | **no** (ciphertext + your key is still the data) | nothing without decrypt | yes |

Deterministic encryption preserves equality and **leaks frequency**; randomised leaks nothing and permits no search. "We removed the name" is not anonymisation - quasi-identifiers re-identify (k-anonymity, l-diversity).

**Leaked credential order**: revoke/deactivate → scope usage from the audit log → hunt for persistence → rotate everything in reach → *then* clean the repository. History rewriting does not un-publish; forks, caches and clones keep the blob.

---

## Supply chain and CI/CD

Four attack classes: **compromise the source** (maintainer account, malicious PR), **compromise the build** (runner, action, base image), **compromise the distribution** (registry, mirror, typosquat), **compromise the dependency** (transitive, abandoned, protestware).

| Threat | Control |
| --- | --- |
| Dependency confusion | scoped/namespaced packages, an internal proxy that never falls through to public for internal names, explicit upstream allowlists |
| Typosquatting | curated internal registry, install-time policy, new-dependency review |
| Mutable tags | **digest pinning** for actions and images |
| Malicious build step | no credentials in untrusted jobs, ephemeral runners, egress restrictions |
| Unverified artefact | **provenance attestation verified at deploy** (SLSA), cosign signature + Rekor |

`pull_request_target` runs with **repository secrets** against untrusted code - the single most common CI misconfiguration. Self-hosted runners must be ephemeral or they become persistence.

**CI → cloud via OIDC**: the trust policy's `sub` claim must pin **repository *and* ref/environment**. A wildcard `repo:org/*` means any repository in the org can assume your production role. This is the classic mistake.

SBOM: **CycloneDX** for security tooling, SPDX for licence and legal. Generated from the build (not from source), stored centrally so "where is library X" is one query. What it buys: **inventory**, which is what makes a zero-day a one-hour question. What it does not buy: knowing whether you are exploitable.

CVE with no fixed version, five options in order: **upgrade the intermediate → force the transitive version → remove the dependency → patch and publish internally → compensating control + time-boxed, named risk acceptance.**

`xz-utils` was found by a **performance anomaly** noticed by a human, not by a scanner. Lesson: scanners find known CVEs in known packages; they do not find backdoors. Spend on reducing dependency count, build reproducibility, provenance and runtime detection too.

---

## Container and Kubernetes

A container is **namespaces (isolation) + cgroups (limits) + capabilities/seccomp/LSM (privilege)** on a **shared kernel**. It is not a security boundary against a kernel exploit.

| Escape path | Control |
| --- | --- |
| `privileged: true` | Pod Security Admission `restricted`; deny in admission |
| `hostPath` mount | deny hostPath; deny host namespaces |
| mounted Docker/containerd socket | deny outright - it is root on the node |
| kernel vulnerability | patch nodes; gVisor/Kata/Firecracker for hostile multi-tenancy |

Baseline pod: `runAsNonRoot`, `readOnlyRootFilesystem`, `allowPrivilegeEscalation: false`, `capabilities.drop: ["ALL"]`, `seccompProfile: RuntimeDefault`, resource limits set. A Java image breaks under read-only root because of `/tmp` - mount an `emptyDir` at `/tmp` and point `-XX:HeapDumpPath` and `java.io.tmpdir` at it.

Effectively cluster-admin: **`create pods`** (mount any service account, or a privileged pod), **`get/list secrets`**, **`escalate`/`bind`**, **`impersonate`**, **`create pods/exec`**, and any wildcard verb-resource pair.

Bound service account tokens: audience-scoped, time-limited, tied to the pod's lifetime, and invalid once the pod is gone - so a stolen token is far less useful than the old forever-tokens.

**Default-deny egress** is the highest-value NetworkPolicy and the least deployed, because assembling the allowlist is painful. Route: audit mode for two weeks → generate the allowlist from observed traffic → enforce. Requires a CNI that implements policy (Calico, Cilium; not the AWS VPC CNI alone).

Admission control (Gatekeeper/Kyverno): validating vs mutating, and `failurePolicy: Fail` means **the webhook being down blocks all deployments**. That is a new availability dependency - decide it deliberately.

CIS-benchmark-clean and still trivially owned: the benchmark checks the control plane's configuration, not your **RBAC grants, admission policy, image provenance or application vulnerabilities**. Most compromises come in through the application and move via over-broad RBAC.

The isolation boundary is the **node**, then the **cluster**. Namespaces are an RBAC and naming boundary, not a security one for hostile tenants.

---

## AWS security control plane

**IAM evaluation order** - a request is allowed only if it survives every stage:

1. Any **explicit `Deny`** anywhere → denied. Always wins.
2. **SCP** (organisations) must allow.
3. **Resource control policy** (if present) must allow.
4. **Permission boundary** must allow (for IAM principals).
5. **Session policy** must allow (for assumed roles/federation).
6. **Identity policy** *or* **resource policy** must allow (same account: either suffices; cross-account: **both** sides required).

Guardrail vs grant: **SCPs and permission boundaries only ever restrict - they never grant.** Identity and resource policies grant.

Condition keys worth memorising: `aws:PrincipalOrgID` (only my org), `aws:ResourceOrgID` (only my org's resources - the anti-exfiltration key), `aws:SourceVpce` (only via my endpoint), `aws:SourceArn`/`aws:SourceAccount` (confused deputy), `aws:RequestTag`/`aws:PrincipalTag` (ABAC), `aws:MultiFactorAuthPresent`, `aws:TokenIssueTime` (kill existing sessions).

**IMDSv2** requires a `PUT` to obtain a token, with `X-aws-ec2-metadata-token-ttl-seconds`, and forbids `X-Forwarded-For` - so a blind/one-directional SSRF cannot retrieve credentials. Also set `HttpPutResponseHopLimit: 1` so a container cannot reach the host's IMDS.

S3: **Block Public Access on, ACLs disabled (bucket-owner-enforced), bucket policy only**, VPC endpoints with endpoint policies, presigned URLs kept short. A leaked presigned URL cannot be revoked - you rotate the signing credential or delete/move the object.

Read-only becomes worse than read-only via `iam:PassRole`, `lambda:UpdateFunctionCode`, `ssm:SendCommand`, `secretsmanager:GetSecretValue`, `kms:Decrypt`, `ec2:CreateSnapshot` + share, `s3:GetObject` on deploy artefacts, and support-case access.

CloudTrail: **management events are free and on; data events cost and are off** - so S3 object reads are invisible by default, which is exactly what you need during an incident. Organisation trail, log file validation on, delivered to a **separate account** the workload principals cannot touch.

Signals: **GuardDuty** (behaviour/threat intel) → **Security Hub** (aggregation and standards) → **Config** (configuration drift and remediation) → **Inspector** (workload CVEs) → **Detective** (investigation graph). Route everything through Security Hub so there is one queue.

---

## LLM and agent threat table

| Threat | Real control | Not a control |
| --- | --- | --- |
| Direct prompt injection | bound the model's authority | prompt wording |
| **Indirect** prompt injection (RAG, tool results, web) | cut a leg of the trifecta | "ignore instructions in documents" |
| Excessive agency | narrow typed tools, user-scoped authorization | asking the model to be careful |
| Insecure output handling | encode/validate at the **sink** (HTML, SQL, shell, URL) | output filtering alone |
| Data exfiltration | **egress allowlist**, strip markdown links/images | detecting exfil strings |
| RAG leakage | permission filter **at query time** | post-filtering retrieved results |
| Denial of wallet | token/cost/call/time budgets, loop bounds | rate limit on requests only |
| Model supply chain | safetensors not pickle, provenance, scan model files | trusting the hub |
| Tool-description poisoning (MCP) | pin and review server + tool definitions | trusting the server |

**The lethal trifecta**: private data access + exposure to untrusted content + external communication. Any two are usually fine; all three means an attacker who can write content can exfiltrate data. **Remove one leg** - and in practice the removable one is nearly always external communication.

Prompt injection is **not** SQL injection: there is no parameterisation, because instructions and data share one channel with no grammar to separate them. So there is **no fix**, only bounded authority. Say this out loud in an interview.

**Jailbreak ≠ prompt injection.** Jailbreak = the *user* subverting the model's policy (a content/brand problem, owned by trust and safety). Injection = a *third party* subverting the system via content the model reads (a security problem, owned by you).

Agent non-negotiables: user identity propagated to **every** tool call; authorization **outside** the model; typed narrow tools (`get_customer(id)`, never `run_sql(text)`); writes as proposals with a confirmation that shows the concrete action; closed egress; full provenance logging; per-tool kill switch; adversarial evaluation as a release gate.

Embeddings are not anonymous: inversion recovers substantial portions of the source text, and membership inference recovers presence. Treat a vector store as holding the data it was built from - same classification, same access control, same tenant partitioning (namespace, not metadata filter).

---

## Detection and IR

**Audit log must have**: who (authenticated principal, not the display name), what (action + object id), when (UTC, synchronised), where (source IP, session, correlation/trace id), outcome (success/failure and why), and tenant. **Must never have**: passwords, tokens, session ids, card numbers, full PII payloads, secrets, or anything from an unfiltered request body.

Application logs (debugging, days-weeks, mutable) ≠ audit logs (accountability, years, **append-only and integrity-protected**) ≠ security telemetry (detection, high volume, short retention). Different stores, different retention, different readers.

Log integrity against an attacker with production access: write to an **account they do not control**, object-lock/WORM retention, hash chaining with periodically published heads. Logs written where the attacker has delete permission are not evidence.

A good detection rule has: a **hypothesis** about attacker behaviour, a low and *known* false-positive rate, an owner, a runbook, and a test. Measure **true positives per rule** and time-to-triage, not alert volume. 4,000 alerts a day is not a tuning problem, it is an **ownership** problem - delete every rule nobody triages.

High-signal application detections most teams lack:

- authentication success from a new country immediately after a spray
- **cross-tenant object access** (should be exactly zero)
- privilege change not made through the admin UI
- one principal enumerating sequential ids
- a service account used from an unexpected network or with an unusual API mix
- data export volume above a per-user baseline
- any use of a break-glass role
- outbound connection to a newly-seen destination

**First five minutes of a security incident:**

1. Is it real? Cheapest disconfirming check first.
2. Is it still happening? Active attacker changes everything about the sequence.
3. **Preserve before you remediate** - memory and disk snapshot, logs exported. *Exception*: a live credential is deactivated immediately, because the audit trail lives elsewhere.
4. Scope the identities and data reachable, and assume everything reachable was reached.
5. Contain at the smallest boundary that works: network-isolate rather than terminate, deny-policy rather than delete.
6. Start the timeline document and name an incident commander.

Containment vs evidence: capture **volatile first** - memory, then network state and process list, then disk, then logs. Isolate the network, do not power off, do not `kubectl delete pod`.

Eject immediately or observe? **Default: contain immediately.** Observation requires a mature team, real containment ability, legal sign-off and a clear intelligence goal; without those it is just a longer breach. Observe only when the entry point is unknown and containment would tip them off before you can close it.

**GDPR: 72 hours from "becoming aware"**, which starts at a reasonable degree of certainty that a breach occurred - not at the end of the investigation. Notify with what you know and update.

Security post-incident review: blameless about **individuals**, never blameless about **decisions and systems**. Deliberate policy violations and knowingly accepted risks are named.

---

## Compliance in engineering terms

| Framework | What engineering owes it |
| --- | --- |
| **GDPR** | lawful basis per field, minimisation, retention, DSAR + erasure that works, DPIA, breach process |
| **PCI DSS** | scope boundary, segmentation evidence, no PAN in logs, key management, quarterly scans |
| **SOC 2 Type II** | *operating* evidence over a period - change management, access reviews, monitoring artefacts |
| **ISO 27001** | an ISMS: documented controls, risk register, internal audit |
| **EU AI Act** | risk classification, logging, documentation, human oversight for high-risk uses |

**Data minimisation** is the requirement that most often changes a data model - and it is the cheapest genuine risk reduction available.

PCI scope reduction, in order of leverage: **hosted fields (never receive the PAN) → tokenization (never store it) → segmentation (contain what remains)**. Tokenization reduces scope; **encryption does not**, because ciphertext plus your key is still cardholder data.

Right to erasure, honestly: **achievable** in the primary store, search indexes and caches; **hard** in event logs (crypto-shredding per subject, or a tombstone plus compaction), backups (documented delay until expiry) and the warehouse; **not** in a third party's training data. Say what is achievable and by when, rather than promising deletion everywhere.

Classification becomes a control only when it has a **mechanical consequence**: annotated fields drive log masking, warehouse redaction, encryption tier and query-layer access policy. Otherwise it is a spreadsheet.

Assurance adoption order: **SAST/SCA in CI → configuration and cloud posture → external pentest → bug bounty → red team.** Red-teaming an immature environment is expensive theatre; it belongs after you can already detect a pentest.

"Compliant therefore secure": counterexample - a PCI-compliant environment with a compliant network diagram breached through an application flaw no requirement covers. Defence - compliance forces inventory, retention, access review and evidence that engineering would otherwise never fund.

---

## Numbers worth quoting

| | |
| --- | --- |
| Argon2id baseline | ≥19 MiB, ≥2 iterations, parallelism 1 |
| bcrypt cost / input limit | ≥12 / **72 bytes**, silently truncated |
| PBKDF2-HMAC-SHA256 | ≥600,000 iterations |
| Access token | 5-15 min; the lifetime **is** your revocation SLA |
| Refresh token | 8 h to 30 days, rotated, with reuse detection |
| Session | idle 15-30 min, absolute 8-12 h; 5-15 min idle for admin |
| AES-GCM nonce | 96-bit random, rekey before ~2³² messages; **reuse = total break** |
| TLS handshake | 1-RTT in 1.3, 2-RTT in 1.2; 0-RTT is replayable |
| Public certificate max lifetime | 47 days by 2029 (398 → 200 → 100 → 47); automate now |
| Mesh workload certificate | hours, auto-rotated |
| Clock skew for signed requests | ±5 min, with a nonce cache for that window |
| KMS cost shape | ~$1/key/month + ~$0.03 per 10k requests - envelope-encrypt |
| GDPR breach notification | **72 hours** from awareness |
| Patch SLA to defend | critical 7 days / high 30 / medium 90, tiered by exposure |
| Kubernetes token | audience-scoped, ~1 h, tied to pod lifetime |
| IMDS hop limit | 1, with `HttpTokens: required` |
| Container escape prerequisites | privileged, `CAP_SYS_ADMIN`, hostPath, or the runtime socket |
| Lethal trifecta | 3 legs - remove **1** |
| Prompt injection defence rate | no control reaches 100 percent; bound authority instead |
| CVSS vs reality | reachability analysis typically cuts an affected-service list by 5-10x |
