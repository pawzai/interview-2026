# Loop 01 - Java and Spring platform principal

**The role.** A principal engineer on a platform team at a company running roughly sixty Spring Boot services on AWS. The team owns the service template, the shared libraries, the deployment path and the standards. The job description says "hands-on" three times.

**Total time.** 4 hours: 30 + 60 + 60 + 45 + 45, with 10-minute breaks. Take the breaks (Q204).

**What this loop is optimizing for.** Depth in Java and Spring, judgement about shared code, and whether you can improve other people's work without being unpleasant. The coding and review rounds carry more weight here than in any other loop.

---

## Round 1 - Hiring manager (30 minutes)

**Persona.** Engineering manager for the platform team. Pragmatic, slightly worried that a 19-year candidate will not want to write code. Has read your resume once.

| Minutes | Segment |
| --- | --- |
| 0-3 | Introduction |
| 3-12 | Resume and scope |
| 12-22 | Hands-on probing |
| 22-27 | The team's actual problem |
| 27-30 | Your questions |

### Opening prompt

> "Thanks for making the time. Give me the two-minute version of you, and then tell me what you are looking for."

**Model answer outline.** Q15's now-arc-proof-aim structure, ending on scope rather than history. Then Q17's pull-not-push framing for what you are looking for. Two numbers, no chronology.

### Follow-up ladder

1. *"You have been at Sonata since 2022 - why are you looking?"* (Q17)
2. *"You have nineteen years and no management title. Was that deliberate?"* (Q19)
3. *"Be honest - how much code did you write last month?"* (Q23)

**Level 3 is the round.** The answer must be specific and recent, and an honest calibration ("I write code most weeks, I am not the fastest on the team, what I am is the person who can read the whole system") scores better than a claim that collapses in round 3.

### Curveball - inject at minute 22

> "Our last principal wrote a shared library that half the teams hate and cannot get off. If you joined and inherited that, what would you do in the first month?"

**What is being scored.** Whether you go straight to a rewrite (wrong), whether you ask who the users are and what specifically they hate (right), and whether you understand that the migration path is the whole problem, not the API (Q43). The strong answer is: talk to the three angriest teams, find out whether the complaint is the API or the release cadence or a bug, and do nothing structural in month one (Q22).

### Rubric focus

Communication and production judgement carry this round. Depth is barely tested; do not try to demonstrate it here.

---

## Round 2 - Java and Spring deep dive (60 minutes)

**Persona.** The most senior engineer on the team. Direct, low-affect, will ask "why?" until you stop. Enjoys being disagreed with, precisely.

| Minutes | Segment |
| --- | --- |
| 0-2 | Warm-up |
| 2-20 | Spring internals |
| 20-38 | Concurrency and the JVM |
| 38-52 | Code reading |
| 52-60 | Your questions |

### Opening prompt

> "Let us start somewhere concrete. Someone on your team says their `@Transactional` method is not rolling back. Walk me through how you would work out why."

**Model answer outline.** Not a list of causes - a **diagnostic order**: is the method being called through the proxy at all (self-invocation, `private`, `final`), is the exception checked (default rollback is unchecked only), is there a `try/catch` swallowing it, is the propagation what they think, is a second transaction manager in play, and is the datasource actually transactional. Then the mechanism underneath: the AOP proxy, `TransactionSynchronizationManager` and thread binding (Q30).

### Follow-up ladder

1. *"Why does self-invocation bypass it? What is actually happening at the call site?"*
2. *"So why did Spring choose proxies rather than weaving? What did that buy and what did it cost?"*
3. *"You have `@Transactional` on a method that also does an HTTP call to a payment provider. What is wrong with that, and what would you do instead?"*

**Level 3 is the one that separates.** The answer is that the transaction now spans a network call of unbounded duration, holding a connection and possibly row locks, and a timeout leaves you unsure whether the remote effect happened. The fix is to move the external call outside the transaction and reconcile - an outbox or a two-phase record (`../03-microservices` Q48-style reasoning applied inside one service).

### Second thread - minute 20

> "Your service is running out of database connections under load. The pool is 20 and there are 200 threads. What is happening?"

**Outline.** Threads block waiting for a connection, the request queue backs up, latency rises, upstream retries amplify it (Q52). Then: why enlarging the pool is usually wrong (the database has a concurrency limit too, and the pool is protecting it), what the correct pool size is derived from (the database's capacity, not the thread count), and how virtual threads change the shape of this problem - they remove the thread limit and therefore remove the accidental backpressure, so you now need an explicit semaphore (Q35).

### Curveball - inject at minute 34

The interviewer states, confidently and incorrectly: *"`volatile` would fix that counter - it makes the increment atomic."*

**What is being scored.** Q34 exactly. The correct behaviour is to disagree via the mechanism, not the conclusion, offer them a world in which they are right, and drop it within a minute if they hold.

### Code reading - minute 38

The interviewer shows a 30-line Spring `@Service` with: an injected `RestTemplate`, a `HashMap` field used as a cache with no synchronization, a `@Transactional` method that catches `Exception` and logs it, and a stream that mutates an external list inside `forEach`.

**Outline.** Use Q39's reading order out loud - intent, lifecycle and shared state, mutable state, error paths, then style. The singleton-bean-with-a-mutable-`HashMap` is the headline defect and the one to lead with; the swallowed exception is second because it silently breaks the rollback you just discussed; the `forEach` mutation is third and is a style-plus-correctness point (Q159).

### Rubric focus

Depth and trade-offs. This round is where a level call is usually made.

---

## Round 3 - Coding and pairing (60 minutes)

**Persona.** A senior engineer who will pair genuinely. Will offer hints if you surface being stuck, and will suggest one wrong approach on purpose.

| Minutes | Segment |
| --- | --- |
| 0-5 | Problem and clarification |
| 5-45 | Implementation |
| 45-55 | Extension and discussion |
| 55-60 | Questions |

### Opening prompt

> "Build a small in-process cache with a maximum size and per-entry expiry. Java, whatever tools you like, and I would like it to be something you would be comfortable putting in a shared library."

**Model answer outline.**

- **Minutes 0-5 (Q150).** Clarify: eviction policy - LRU or plain size cap? Is expiry from write or from last access? Thread safety required - single-threaded or concurrent? Do we need to know the hit rate? Is loading the value the cache's job or the caller's? Then state the plan and what you will skip.
- **Minutes 5-25.** The straightforward version: a `LinkedHashMap` in access order with `removeEldestEntry` for LRU, entries wrapping value plus expiry timestamp, expiry checked lazily on read rather than with a background thread - and say why lazily (no thread to manage, no lock contention, at the cost of expired entries occupying space until touched).
- **Minutes 25-35.** Thread safety, and this is where the round differentiates. `synchronized` around the map is correct and simple; a `ConcurrentHashMap` with an eviction structure is faster and much harder to get right. **Say the trade-off and choose the simple one for a shared library**, then name the condition under which you would change it. Mention that you would reach for Caffeine in production and that you are writing it because you were asked - that sentence is worth saying.
- **Minutes 35-45.** Tests: hit, miss, expiry, eviction at capacity, and one concurrent test using a latch rather than a sleep (Q152).

### Follow-up ladder

1. *"What happens if two threads miss on the same key at the same time?"* - the cache stampede. `computeIfAbsent` on a `ConcurrentHashMap` serializes per key, with the caveat that a long computation inside it blocks that bin.
2. *"This is going in a library used by sixty services. What changes?"* - a bound that cannot be misconfigured to unbounded, metrics exposed (hit rate, size, eviction count), no logging framework assumptions, no static state, and a documented thread-safety guarantee (Q43).
3. *"One team is using it to cache 200 MB of data per instance and their pods are being OOM-killed. Whose problem is that?"* - both. The library should have made the memory cost visible and the default safe; the team should have measured. The durable fix is a size-in-bytes bound or a documented per-entry estimate, plus the metric that would have shown it.

### Curveball - inject at minute 28

> "Rather than the timestamp per entry, why not just have a background thread sweep the map every second? Simpler, no?"

**What is being scored.** Q155. Test it out loud rather than complying or arguing: a sweeper adds a thread per cache instance, needs to lock or iterate a concurrent view, and does not actually remove the need for a read-time check unless you accept serving a stale entry for up to a second. Then offer to do it their way and note where it breaks.

### Rubric focus

Production judgement and communication. The problem is easy on purpose (Q148); the signal is in the clarification, the library framing and the narration.

---

## Round 4 - Architecture and code review (45 minutes)

**Persona.** A staff engineer from another team, presenting a design their team built. Slightly proud of it. Present in the room while you critique it (Q166).

| Minutes | Segment |
| --- | --- |
| 0-5 | They present |
| 5-35 | You review |
| 35-42 | Their pushback |
| 42-45 | Questions |

### The design presented

A service that accepts order updates over HTTP, writes them to Postgres, and publishes an `OrderUpdated` event to Kafka after the commit. Three consumers: a search indexer, an email sender and an analytics loader. The email sender is idempotent "because we check a sent flag first". Deployment is blue-green. Retries are three attempts with a fixed delay at every layer.

### Opening prompt

> "That is the design. What do you think?"

**Model answer outline.** Q163's opening - two context questions first (what is this optimizing for, what constraint am I not seeing), then a stated order (Q164), then trace one request.

The findings, in the order they should be raised:

- **Blocking:** the publish is after the commit, so a crash between the two loses the event silently. This is the dual-write problem and the fix is an outbox (Q48). Raise it as a question: "what happens if the process dies between the commit and the publish?"
- **Blocking:** "check the sent flag first" is check-then-act - two concurrent deliveries both read false and both send. The fix is a unique constraint on the dedup key, written in the same transaction as the send record (Q50).
- **Worth understanding:** what is the partition key? If it is not the order id, the three consumers can see updates out of order (Q174 / S-level reasoning).
- **Worth understanding:** fixed-delay retries at every layer is 27x amplification into a struggling downstream, with no jitter and no budget (Q52).
- **Preference, non-blocking:** the analytics consumer probably does not need to be on the same topic.

### Follow-up ladder

1. *"We have never lost an event. Is this actually a problem?"* - the honest answer: absence of evidence, and the failure is silent by construction, so you would not know. Ask whether there is a reconciliation that would detect it.
2. *"The outbox means another table and a relay. Is that worth it for an email?"* - genuinely engage: for email alone, possibly not; for the search index being permanently wrong, yes. Rank the consumers by the cost of a missing event and let that decide.
3. *"How would you sequence this if I only have one sprint?"* - the idempotency fix first (cheapest, fixes a live duplicate-email bug), then retry jitter and a budget, then the outbox. Sequencing by cost-to-fix over blast-radius is the answer.

### Curveball - inject at minute 33

> "Honestly, we considered the outbox and decided it was over-engineering. Our CTO agreed."

**What is being scored.** Whether you fold, escalate, or hold the position gracefully (S1, Q194). The right move: acknowledge that it is a legitimate trade-off at low volume, state precisely what is being accepted ("then we are accepting silent divergence at a rate we cannot currently measure"), and offer the cheap detection - a reconciliation job - as the version that costs almost nothing and makes the trade-off visible.

### Rubric focus

Communication above all. The findings here are not hard; the tone is the round.

---

## Round 5 - Behavioural and bar raiser (45 minutes)

**Persona.** A principal engineer from an unrelated part of the organization. Friendly, unhurried, and will not fill silences.

| Minutes | Segment |
| --- | --- |
| 0-12 | Influence and standards |
| 12-24 | Failure and conflict |
| 24-36 | Cross-topic probing |
| 36-45 | Your questions |

### Opening prompt

> "Tell me about a standard or a practice you got adopted by teams that did not report to you."

**Model answer outline.** Q191 and Q180. The evidence must be an artifact that made the right way easier, a named person who resisted and what changed their mind, an adoption number, and - the closing line - that it outlived your involvement.

### Follow-up ladder

1. *"Who did not adopt it, and why?"* - a real name-shaped answer with a legitimate reason on their side.
2. *"What did you have to give up to get the rest of it accepted?"*
3. *"If you joined here and found sixty services with sixty different ways of doing this, where would you start?"* - not with a standard. With the two teams in most pain, and a template that makes their next service easier (Q118, Q134).

### Second thread - minute 12

> "Tell me about a decision you made that you now think was wrong."

**Outline.** Q178's calibration and Q206's sharpness. A defensible-at-the-time decision, the cost stated plainly, what you owned, and the rule you now apply - with an instance of applying it since.

### Curveball - inject at minute 28

Silence. The interviewer says nothing for fifteen seconds after your answer, then: *"...and?"*

**What is being scored.** Q196. Do not backfill nervously with weaker material. The correct response is to add the one thing that genuinely was missing - usually the second-order effect or the learning - or to check in: "I can go deeper on the technical side or on how it landed with the team; which is more useful?"

### Closing prompt - minute 36

> "What questions do you have for me?"

**Model answer outline.** Two or three, aimed at this persona specifically (Q207, Q208). For a principal from another org: "what is the decision this organization keeps re-making?" and "where does the architecture disagree with itself today?" Never process questions here.

### Rubric focus

All four, weighted to production judgement and communication. This is the round the panel will argue over.

---

## After the loop

Fill in the loop summary in [scoring-sheet.md](scoring-sheet.md). For this archetype, check three things specifically:

- Did the code you wrote in round 3 match the standards you advocated in rounds 4 and 5? Panels notice.
- Did you use the same anecdote in round 2 and round 5? (Q104 says use different faces of one story; Q182 says a repeated face reads as a script.)
- Was your claim about being hands-on in round 1 supported by round 3?
