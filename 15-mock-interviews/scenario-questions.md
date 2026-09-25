# Scenario Questions

Twenty scenarios: eight things that go wrong **inside** an interview loop, six full design rounds, and six story rounds with no scripted answer.

Work them **out loud** before reading the answer. The written answers are longer than you should speak; they are written so the reasoning is visible, and your job is to compress each to the length the round allows.

**Part A** uses **CIDER** - Clarify, Isolate, Decide, Execute, Reflect - applied to the interview itself rather than to a production system. The Clarify step is the one candidates skip in both settings, and it is the one that saves the round.

**Part B** maps to Q72-Q77 in [questions.md](questions.md). Each is a complete 45-minute design round with a clock, the interviewer's likely interjections, and the arithmetic. Run them timed and recorded; reading them is worth a fraction of speaking them.

**Part C** has no scripted answer. Those are your stories, and Part C tells you how to build and rehearse them.

---

## Part A - When the round goes wrong

### S1. The interviewer rejects your core decision at minute 20

> You are twenty minutes into a design round. You have built the whole design on an event-driven write path with an outbox. The interviewer says, flatly: "I would not do it that way. Why not just write to both systems in the request?"

**Clarify.** Two questions, fast, before you defend anything. "Are you pushing on the complexity, or is there a constraint I have missed - is there a reason the event path is not available here?" And: "Would you like me to defend this one or design the alternative? I am happy to do either."

That second question is doing serious work. It converts a confrontation into a choice, and about half the time the honest answer is "I want to see you defend it", which tells you the round is a stress test rather than a redirection.

**Isolate.** Work out which of three things is actually happening, because the correct response differs:

1. **A genuine constraint you did not know about** - no broker, no operational capacity, a compliance rule. Then they are right and you should say so quickly.
2. **A test of conviction.** They want to see whether you fold, or whether you can articulate the reason you chose it.
3. **A real technical disagreement** where they favour simplicity and you favour correctness.

The discriminator is the follow-up question you ask. If you ask "what would the dual write do when the second write fails?" and they engage with the mechanism, it is (3). If they say "assume it works", it is (2). If they say "we do not run Kafka here", it is (1).

**Decide.** Defend on the **failure case**, not on the pattern name, and give them a cheaper version of your position so they are not forced to fully concede:

> "The reason I did not dual-write is the partial failure: if the database commits and the publish fails, we have a state change nobody downstream knows about, and it is silent - there is no error, and we find it in a reconciliation weeks later. The outbox costs me a table and a relay, and it buys me the guarantee that those two facts cannot diverge. If the broker is not available here, the cheaper version of the same property is a transactional status column and a poller - same guarantee, no new infrastructure. What I would not do is the dual write without either, unless a divergence is genuinely acceptable, in which case I would rather make that explicit than accidental."

**Execute.** Then **give them the round back**. "Shall I keep going with this, or would you rather I sketch the dual-write version and we compare?" If they choose the alternative, design it properly and without sulking - and name where it breaks as you go, factually. That is Q184's disagree-and-commit inside forty-five minutes.

**Reflect.** What is being scored is almost entirely the temperature and the specificity. Instant capitulation says you had no reason for your own design; a four-minute argument says you will be expensive to work with. The pass condition is: one clear mechanism-level reason, one cheaper alternative that preserves the property, and a visible willingness to go their way.

Related: Q194, Q155, Q166.

---

### S2. Asked in depth about something on your resume you did not personally build

> "You have Kubernetes and Kafka on your resume. Walk me through how you sized the partitions and what you changed about the consumer group configuration." You were the architect; another team built and tuned it.

**Clarify.** Nothing to ask. This one is decided in the first sentence you say, and the only question is whether you draw the boundary yourself or let them find it.

**Isolate.** The risk is not the gap. It is that a vague answer reads as a **claim you cannot support**, and once that suspicion exists it retroactively discounts everything else in the loop (Q192). The gap costs you one question; a detected overstatement costs you the round.

**Decide.** Draw the line explicitly, immediately, and then be genuinely useful on your side of it.

> "Let me be precise about my role there, because I do not want to overclaim. I owned the design and the decision to use a log rather than a queue, and I set the ordering and retention requirements. The partition sizing and the consumer tuning were done by the platform team - I reviewed it and I can tell you the reasoning we agreed on, but I did not run the load tests myself. Would you like the design reasoning, or would you rather move to something I did operate hands-on?"

Then deliver the design reasoning properly: partition count driven by the ordering requirement and the consumer parallelism rather than by throughput, the fact that increasing it later breaks key-to-partition affinity, and what you specified about retention relative to recovery time (Q54).

**Execute.** Offer the substitute in the same breath. "The system where I did do that hands-on is *[X]* - I can talk about the consumer lag incident there if that is more useful." You are trading a question you would score three on for one you would score five on, and interviewers almost always take it.

**Reflect.** The durable fix is upstream: **your resume should distinguish what you architected from what you operated**, because this question is generated by the resume. Go through it before the loop and mark each line "built", "operated", "designed and reviewed", or "adjacent". Then this is never a surprise.

Related: Q23, Q31, Q195.

---

### S3. The environment breaks in the coding round

> Ten minutes into a 45-minute coding round, the shared editor stops syncing. The interviewer cannot see your changes. Fixing it will take five to ten minutes of the round.

**Clarify.** "Can you see the last version I typed? Would you rather we spend a couple of minutes fixing this, or should I switch to my own editor and share my screen?" Offer options rather than waiting - the interviewer is often more flustered than you are, and taking the logistics off their hands is itself a positive signal.

**Isolate.** Two separate problems, and conflating them is the mistake: the **tooling problem**, which is nobody's fault and should be resolved in the cheapest way available, and the **time problem**, which is now a scoping decision you should make explicitly.

**Decide.** Take the fastest path that restores a shared view - your editor with a screen share, a plain file, or in the worst case a document and no execution. Then **re-scope out loud**:

> "We have lost about eight minutes. I would rather deliver one thing well than two half-finished, so I am going to do the core function and one test, and describe the edge-case handling rather than writing it. Does that work, or would you rather I prioritize something else?"

**Execute.** Keep the same discipline you would have had - state the approach, write the working version, one test, narrate the decisions (Q149). If you end up with no execution environment, say what you would expect each test to produce and walk one input through the code by hand; that recovers most of the signal.

**Reflect.** What is actually being scored here is **composure and how you handle a constraint that is not your fault**. Candidates who become flustered, apologize repeatedly, or silently rush produce a much worse impression than the lost time warrants. Interviewers routinely discount the output of a broken round and score the behaviour - which means the round is now almost entirely about the behaviour.

Practical preparation: have a local editor with a language runtime ready and a screen-share path tested, before the loop. This costs ten minutes once.

Related: Q148, Q153, Q197.

---

### S4. Two interviewers describe the role completely differently

> The hiring manager described a hands-on principal role owning the platform. Two rounds later, a director describes the same role as "helping the teams deliver the migration" with no mention of architecture ownership.

**Clarify.** Do not point out the contradiction to either of them in the moment - it reads as auditing them, and one of them is probably describing a hope rather than a fact. Instead, ask the **same concrete question of both** and compare the answers: "what would this person decide alone in the first six months?" (Q209).

**Isolate.** Three explanations, and they lead to very different decisions:

1. **Normal organizational fuzziness.** A new role often means different things to the manager who wants it and the director who approved the headcount. Common and survivable.
2. **An unresolved disagreement** about what the role is. This is the dangerous one: you would be hired into a job two stakeholders define differently, and you would discover it in month three when you make a decision one of them did not think was yours.
3. **The manager is selling.** The scope described is what the manager wants to grow into and the director's version is the funded reality.

The discriminator is whether they can each point at a **past event** rather than a description (Q209). If the director says "the last person at this level chose our deployment platform", the scope is real regardless of how they framed it.

**Decide.** Surface it, once, late in the loop, to the hiring manager, framed as your own confusion rather than their inconsistency:

> "Can I check something I want to get right - I have heard the role described a couple of ways, and I want to make sure I am solving for the same thing you are. Is this primarily an architecture-ownership role, or primarily an execution role on the migration? I would take either, but I would prepare differently."

The clause "I would take either" is what makes it safe to answer honestly.

**Execute.** Whatever answer you get, get the **first six months in writing** in the offer conversation (Q215). Not a contract - an email that says what the first project is and what decisions sit with the role. Managers who mean it are happy to write it down; the reluctance is the signal.

**Reflect.** This is the single most common cause of a senior hire failing in the first year, and it is entirely detectable during the loop. The cost of asking is a slightly awkward two minutes; the cost of not asking is eighteen months.

Related: Q25, Q26, Q209, Q212.

---

### S5. The live incident simulation

> "Your service's error rate has gone from 0.1 percent to 12 percent in the last six minutes. I am your on-call engineer. Go." The interviewer will answer questions in character, will withhold information you do not ask for, and will introduce a complication at about the fifteen-minute mark.

This is Q117 run as a round. The interviewer is scoring behaviour, not the eventual root cause - and in most versions of this exercise, the cause is deliberately not discoverable in the time available.

**Clarify - the first ninety seconds, and they matter more than anything after.**

> "I am taking incident command. Three things first: what is the customer impact - are requests failing, or are they slow, and is it all of them or a subset? Second, when exactly did it start, and does that correlate with anything we did - a deploy, a config change, a feature flag, a scheduled job? Third, is anything else in the estate affected, or is it just us? While you answer, please get *[the dashboard]* up and start a timeline document."

The three things - impact, change correlation, blast radius - are the whole opening. Saying "I am taking command" out loud is worth a surprising amount; interviewers listen for it specifically.

**Isolate - mitigate before you diagnose, and say that you are doing it.**

> "Before we understand this: was there a deploy in the last hour? … Yes, forty minutes ago. Then I want to roll back now and diagnose afterwards. I am not confident the deploy is the cause, but rollback is cheap, reversible, and if it works we have stopped the customer impact and we can investigate calmly."

If there was no deploy, the equivalent moves are shedding load, failing over, disabling the newest feature flag, or scaling out - and the same sentence applies: cheap and reversible first.

Then run hypotheses **as falsifiable pairs**: "if this is a downstream dependency, we would see our error rate track theirs and our latency rise before the errors - can you check *[their]* dashboard? If it is a resource exhaustion, we would see it climb with traffic and be worse on the oldest pods - what does the pod age distribution look like?" Naming the discriminating evidence before looking is the behaviour being scored.

**Decide - the complication.** At about minute fifteen the interviewer will introduce something like: the rollback did not help, or a second service has started failing, or someone senior joins the call and wants an ETA. Handle each explicitly:

- **Rollback did not help** - that is information, not a setback. Say so: "good, that rules out the deploy as a sufficient cause. It might still be a trigger, so let me ask what the deploy touched." Then re-open the dependency and state hypotheses.
- **A second service failing** - re-scope the incident upward, and look for the shared dependency rather than treating it as two incidents.
- **A senior stakeholder wanting an ETA** - "I do not have an ETA. Here is what I do know: *[impact]*, *[what we have ruled out]*, *[what we are doing next]*, and I will update you in fifteen minutes whether or not we know more." Refusing to invent an ETA while committing to a cadence is the correct answer and interviewers are explicitly listening for it.

**Execute.** Keep a running verbal timeline, delegate explicitly ("you take the database, I will take the dependency, we sync in five"), and state a decision point in advance: "if the dependency theory is not confirmed in ten minutes, we shed fifty percent of traffic and buy ourselves room."

**Reflect.** Close the round yourself rather than waiting for the clock:

> "To summarize where I would be: impact mitigated by *[X]*, cause narrowed to *[Y]*, and the next step is *[Z]*. Afterwards I would want a blameless review, and the two things I would be looking for are why detection took six minutes and why the rollback path was not automatic on this SLI. The action item I would push hardest for is the second one, because it removes the need for a human to be right at 2am."

**The behaviours that fail this round:** going quiet, diagnosing before mitigating, pursuing one theory without saying what would disprove it, forgetting communications entirely, and never declaring command.

Related: Q106, Q107, Q117.

---

### S6. The bar raiser keeps pushing past the edge of what you know

> Every answer you give is met with another "why?". Four levels in, you are past what you actually know, and they are still going.

**Clarify.** Nothing to ask. Recognize what is happening: **this is the design of the round**, not a failure of your preparation (Q192). Interviewers do this deliberately to find the edge, because the location of the edge is the calibration data, and everyone has one.

**Isolate.** The failure mode is not reaching the edge - it is **not noticing that you have**. Candidates who keep producing confident-sounding material past the boundary of their knowledge trigger the worst possible note: "could not tell what he knew from what he was guessing".

The internal signal to watch for is the moment your sentences start getting longer and less specific. That is the boundary, and you will feel it a sentence before the interviewer sees it.

**Decide.** Mark the boundary out loud, then keep being useful on the other side of it by switching from recall to reasoning:

> "That is about the edge of what I know from experience - past this point I am reasoning rather than recalling, so treat it as a hypothesis. Given how *[the layer below]* works, I would expect *[X]*, and the way I would check is *[the specific test]*. Do you know the answer? I would genuinely like to."

**Execute.** Then let it be. Do not backfill, do not apologize twice, and do not try to redirect to a topic you are stronger on immediately - that reads as evasion. If they keep going in the same direction, keep reasoning explicitly labelled as reasoning; it is a perfectly good use of the remaining minutes and it shows how you think when you do not know, which is arguably more useful to them than another correct recall.

**Reflect.** Two preparation implications. First, **know where your edges are** in the three or four topics most central to the role, so the boundary is a planned statement rather than an improvisation. Second, one clean "here is my edge" per round is a positive signal; four is a level problem, and the fix is depth in the pack, not technique here (Q195).

Related: Q192, Q195, Q31.

---

### S7. At minute 30 you realize your design approach is wrong

> You have spent half the round building a design around precomputed fan-out. You have just worked out, while answering a question about a celebrity user with fifty million followers, that this cannot work for the top of the distribution.

**Clarify.** Ask yourself one question first: **is it wrong, or is it wrong for a case?** Almost always it is the second, and the distinction determines whether you patch or restart.

- Wrong for a case: the design holds for the bulk of the distribution and fails at the tail. Patch it, and the patch is the interesting part.
- Genuinely wrong: it violates a stated requirement across the board. Rare, and usually caused by missing something in the first four minutes (Q60).

**Isolate.** In this example it is the first. Precomputed fan-out is correct for the ninety-nine percent and catastrophic for the celebrity, which is the well-known hybrid case.

**Decide.** **Say it out loud, immediately, and make the discovery part of the design.** This is one of the highest-scoring moments available in a design round, and candidates waste it by quietly hoping the interviewer did not notice.

> "I have just realized this breaks for the top of the distribution, and I want to fix it rather than talk past it. Writing fifty million rows on one post is not viable - at *[a plausible write rate]* that is *[the arithmetic]*, and it makes the write path latency a function of follower count, which is unacceptable. So the design has to be hybrid: fan-out on write for normal accounts, and for accounts above a threshold - say a hundred thousand followers - fan-out on read, where the timeline query merges the precomputed feed with a small number of pulled celebrity feeds. The threshold is a tuning parameter and I would set it from the actual distribution."

**Execute.** Then **name the cost of the fix**, because a patch with no acknowledged cost looks like a save rather than a design: reads become more expensive and more complex for everyone; you now have two code paths and the boundary between them needs testing; and an account crossing the threshold needs a migration of its fan-out state.

**Reflect.** The recovery is worth more than never having had the problem, provided three things are true: you found it rather than the interviewer; the arithmetic is what found it; and the fix has a stated cost. That combination is very close to a complete demonstration of the round's rubric.

The prevention is Q66: **do the arithmetic in the first ten minutes**, because sizing is precisely what surfaces this class of error early enough to be cheap.

Related: Q66, Q68, Q71, Q73.

---

### S8. Two interviewers disagree with each other in front of you

> A panel round. You propose keeping the data in one store; one interviewer agrees strongly, the other says it will not scale. They start debating each other. Ninety seconds pass and both look at you.

**Clarify.** Do not pick a side, and do not attempt to referee. Reframe the disagreement as **a question about a fact neither of them has stated**, which is almost always the truth of it.

> "It sounds like the disagreement is about the write volume rather than about the design - if it is *[X]* per second, one store is fine for years; if it is *[10X]*, it is not. Do you have a number for that, or is that itself contested?"

**Isolate.** Three possibilities: they genuinely disagree and you have just wandered into a live organizational argument (common, and useful information about the job); one of them is testing whether you can be pushed around by the more senior person in the room; or they are performing a disagreement deliberately to see how you handle it.

You do not need to know which. The same response works for all three.

**Decide.** Take a position, but make it **conditional and falsifiable**, so that neither of them has to be wrong:

> "My default would be one store, because the cost of splitting is permanent and the cost of being wrong about the volume is a migration I can do later with a known playbook. What would change my mind is if the growth is compounding fast enough that the migration lands in the middle of the peak season, or if the two workloads have genuinely different availability requirements. So the number I would go and get before deciding is *[the specific one]*."

That answer is decisive, and it hands both of them a version of their position that survives.

**Execute.** Then **move the round on** rather than letting them resume the debate. "I will keep going with the single store and flag where the split point would be if the numbers go the other way - stop me if you would rather see the split version." Reclaiming the clock is itself a positive signal in a panel round.

**Reflect.** What is scored: that you did not flatter the more senior interviewer, that you did not sit out the question, and that you converted an argument into a decision criterion. That is exactly the behaviour they want in a design review after you join, which is why the situation gets engineered.

Related: Q166, Q194, Q59.

---

## Part B - Full design rounds

Each of these is 45 minutes. Run them timed. The clock is given in the same shape every time, which is deliberate - the structure from Q60 and Q71 should become automatic.

| Minutes | What is happening |
| --- | --- |
| 0-4 | Restate, scope, constrain, plan (Q60) |
| 4-10 | Arithmetic, and the one number that determines the architecture (Q62) |
| 10-25 | API, data model, high-level architecture, narrated end to end (Q64) |
| 25-38 | The deep dive they choose, plus failure modes as you go (Q65, Q69) |
| 38-42 | Scale, cost, and the first thing that breaks at 10x |
| 42-45 | Close: summary, the weakest part named by you, one question (Q71) |

### S9. Multi-tenant document processing platform (Q72)

> "Design a platform that ingests documents from business customers, extracts structured data from them, and makes the results available through an API. Assume you are building it for our company."

**Minutes 0-4 - scope and constrain.** The questions that change the architecture, and the answers to assume if they will not give them:

- **What kinds of documents, and who controls them?** Assume mixed PDFs including scans, 1-50 pages, uploaded by customers. This matters because scanned documents mean OCR, which changes the cost and latency model by an order of magnitude.
- **What does "extract" mean - fixed fields or open-ended?** Assume a per-tenant schema of 10-40 fields. Fixed schemas allow validation and evaluation; open-ended extraction does not.
- **Latency expectation?** Assume this is asynchronous - minutes, not seconds - and say why you are assuming it: "extraction on a 50-page scan cannot be synchronous, so I will design an async submit-and-poll or webhook API. Tell me if there is a synchronous requirement, because that would change everything."
- **Volume?** Assume 200,000 documents a day, spiky, with tenant concentration.
- **Accuracy and review?** Assume there is a confidence threshold below which a human reviews - this is the single most important requirement to surface, because a system with no human path is a very different product.
- **Tenancy model?** Shared infrastructure, hard data isolation.

**Minutes 4-10 - the arithmetic.** Do it out loud (Q62).

200,000 documents a day is a bit over 2 per second average, and with a 5x business-hours peak, maybe 10-15 per second. That is a small number, and saying so is the point: **the throughput is not the problem**. Average 10 pages at, say, 2 KB of text per page is 20 KB of text per document, so 4 GB of text per day, plus the originals - say 500 KB each, so 100 GB a day of blobs, 36 TB a year. **Storage growth and lifecycle are a real problem; request throughput is not.**

If extraction uses a model at roughly 8,000 input tokens for a long document plus a 1,000-token response, that is order-of-magnitude cents per document at current prices, so **200,000 a day is a five-figure monthly model bill** - which makes cost a first-class design constraint and justifies routing cheap documents to a cheap path (Q122).

Then the sentence that reframes the round: "so the design problems here are cost per document, tenant isolation, the human review loop, and reprocessing - not scale."

**Minutes 10-25 - the design.**

*API.* `POST /documents` returning `202` with a document id; `GET /documents/{id}` returning status and results; a webhook per tenant for completion; `POST /documents/{id}/reprocess`. Idempotency key on submit, because customers retry (Q50).

*Pipeline.* Upload goes straight to object storage via a presigned URL - never through your API, which keeps large payloads off your compute. A message per document drives a **state machine**, not a chain: `received → classified → text-extracted → fields-extracted → validated → (needs-review) → complete`. Say why a state machine: every stage is separately retriable, the state is queryable for support, and a partial failure resumes rather than restarting the expensive stages.

*Stages.* Classify first, cheaply, to decide the route: a native-text PDF skips OCR entirely, which is the largest cost saving available. Text extraction with a parser, OCR only where needed. Field extraction with a model, structured output constrained to the tenant's schema. **Validation in code** - types, formats, checksums, cross-field arithmetic - because deterministic validation catches a large share of extraction errors for free and produces the confidence signal.

*Storage.* Originals in object storage with a per-tenant prefix and lifecycle rules to colder tiers. Extracted results in a relational store, partitioned by tenant. **Every result carries the model version, prompt version and pipeline version**, which is the thing that makes reprocessing and debugging possible eighteen months later.

*Tenancy.* Isolation enforced at the query layer with a tenant id required by the repository (Q141), separate object storage prefixes with IAM conditions, and per-tenant quotas and rate limits so one customer's Monday backlog does not starve everyone else. Say explicitly: "the isolation test suite is a deliverable, not a nice-to-have."

**Minutes 25-38 - the deep dives they are likely to pick.**

- **The human review loop.** A confidence score per field, not per document, so review is field-level and takes seconds rather than minutes. A review queue with prioritization by tenant SLA and document age. **The corrections are the most valuable data you produce** - they are the eval set (Q125) and the fine-tuning corpus, so capture the before and after, not just the final value.
- **Quality and evaluation.** A labelled set per document type built from review corrections; field-level accuracy as the metric; run in CI on every prompt, model or pipeline change; a per-tenant dashboard so a regression on one customer's document type is visible even when the aggregate is flat. That last point is the multi-tenant-specific insight.
- **Cost control.** Route by document class; cache by content hash so redelivery of the same document is free; cap tokens per document and truncate with a page-level relevance filter for very long documents; batch where latency allows. State the target as **cost per successfully extracted document**, which is the only metric that connects quality and cost.
- **Reprocessing.** When the model improves, you want to re-run 30 million historical documents. That is a separate, throttled, low-priority path with its own queue and budget, writing new result versions rather than overwriting - which is why results are versioned.

**Minutes 38-42 - failure and scale.** A poison document that crashes the parser must dead-letter with the tenant notified, not retry forever. A model provider outage should degrade to queueing rather than failing submissions, with the customer-visible SLA expressed in hours. At 10x, the first thing to break is the model provider quota and your monthly bill; the second is the review queue, because human capacity does not scale with a slider - which is the argument for spending on accuracy rather than on reviewers.

**Minutes 42-45 - close.** "The design is an async, versioned state machine over object storage with cost-driven routing and a field-level human review loop. The two decisions that define it are classify-first routing, which is where the cost control lives, and versioning every result, which is what makes reprocessing and audit possible. **The part I am least happy with** is the review queue - it is a human bottleneck I have designed around rather than solved, and if the accuracy is worse than assumed, it becomes the whole system's capacity limit. At 10x I would expect the model spend and the review headcount to be the binding constraints, not the infrastructure."

**Depth:** `../09-rag` Categories 2-3; `../08-genai` Categories 10 and 13; `../05-aws` Category 8.

---

### S10. Real-time notification and fanout for twenty million users (Q73)

> "Twenty million users. When something happens that a user cares about, they should see it within a couple of seconds, on web and mobile."

**Minutes 0-4 - scope and constrain.** Nail these before drawing anything:

- **What generates a notification, and what is the fan-out distribution?** This is the question. Assume a mix: direct events (one recipient), group events (tens), and broadcast or follow-style events with a long tail up to millions. **The tail is the design.**
- **Delivery semantics?** Assume at-least-once with client-side deduplication, and say why exactly-once is not on offer (Q46).
- **Must an offline user get it later?** Assume yes - so there is durable per-user state, not just a live push.
- **Ordering?** Assume per-user ordering is desirable but not strict; the notification carries a timestamp and the client sorts.
- **Read state, and does it sync across devices?** Assume yes, which means read state is server-side and is itself a write.

**Minutes 4-10 - the arithmetic.** Twenty million users, say 10 percent concurrent at peak - **two million live connections**. That number alone determines the architecture: at maybe 50,000-100,000 concurrent connections per node with tuned settings, that is 20-40 gateway nodes, and the gateway must be a separate tier from anything else because its scaling driver is connections, not requests.

If each user gets 20 notifications a day, that is 400 million writes a day, about 5,000 per second average and maybe 20,000 at peak. At ~200 bytes each, roughly 80 GB a day of notification rows - so retention is a design decision, not an afterthought; assume 30 days hot and archive beyond.

Now the tail: one broadcast to 5 million recipients at 20,000 writes per second of capacity is over four minutes if you materialize it. **That is the number that forces the hybrid.**

**Minutes 10-25 - the design.**

*Tiers.* Producers publish an event to a durable log. A **fan-out service** consumes it, resolves recipients, and writes per-user notification rows. A **delivery service** pushes to connected clients via the gateway and to APNs/FCM for the rest. A **connection gateway** holds WebSocket connections and knows nothing about business logic. Separating the gateway from the fan-out is the single most important structural decision, because they fail and scale independently.

*The hybrid fan-out, which is the core of the round.* Below a threshold - say 10,000 recipients - **fan-out on write**: materialize a row per recipient, which makes reads trivial. Above it, **fan-out on read**: write one row to a broadcast feed, record the recipient set by reference (a topic), and have each user's timeline query merge their personal notifications with the small number of broadcast topics they subscribe to. State the threshold as a tuned parameter and say what you would tune it on: the write amplification budget versus the read latency budget.

*Routing to a connection.* A user's connection lives on a specific gateway node, so you need a registry - user id to node id, in Redis with a TTL and heartbeat - or you publish to a per-node channel and let nodes filter. Say the trade-off: a registry is precise but is a hot dependency in the delivery path; broadcast-and-filter is simpler and wastes bandwidth linearly in node count. At 40 nodes, broadcast-and-filter is defensible; at 400 it is not.

*Storage.* Per-user notification list keyed by `(user_id, created_at)` in a partitioned store - this is a textbook wide-partition access pattern, so DynamoDB or Cassandra with the user as the partition key, or a partitioned relational table if the operational simplicity is worth more. Read state on the same row. Unread count is the trap: computing it per read is expensive, so maintain a counter and accept that it can drift, with a periodic reconciliation.

*Mobile push* is a different path with different failure modes - a third-party dependency with its own rate limits, tokens that expire, and no delivery guarantee. Treat it as a separate consumer of the same event, not as part of the same code path.

**Minutes 25-38 - the deep dives.**

- **Connection management.** Authentication at connect, not per message. Heartbeats to detect half-open connections. **The reconnect storm is the failure mode that matters**: when a gateway node dies, its connections all reconnect at once, so clients need jittered exponential backoff and the gateway needs connection rate limiting - otherwise a single node failure cascades. On reconnect, the client sends the last notification id it saw and gets the delta, which is also how you handle missed messages without a durable per-connection queue.
- **Backpressure.** A slow client cannot be allowed to consume memory in the gateway - bound the per-connection buffer and drop the connection when it fills, because the client will reconnect and resync from the last id. Say this explicitly; it is a detail that only comes from having run one.
- **Deduplication and idempotency.** Each notification has a stable id derived from the event; clients dedupe on it. The fan-out consumer must be idempotent because the log will redeliver (Q50).
- **The celebrity re-check.** Even with the hybrid, a user following 500 broadcast topics makes the read expensive. Cap the merge set, or promote very high-traffic topics back to materialization for active users only.

**Minutes 38-42 - failure and scale.** If the fan-out service falls behind, notifications are late but not lost - and the SLO should be stated as a percentile of end-to-end delay, with lag as the alert. If Redis (the connection registry) is down, fall back to broadcast-and-filter rather than dropping delivery. If the log is down, producers must not block: notification is not worth failing the originating transaction over, so the producer writes to its outbox and the notification is delayed (Q48). At 10x, the first constraint is connection count and therefore gateway cost, and the second is the write amplification on the fan-out tier.

**Minutes 42-45 - close.** "A separate connection tier, a durable log, and a hybrid fan-out with a threshold - materialize for the many, reference for the few. The two defining decisions are the hybrid threshold and the resync-on-reconnect protocol, which is what lets me treat the gateway as disposable. **The weakest part** is unread count consistency; I have chosen a counter that can drift with periodic reconciliation, and if the product requires it to be exact, that is a materially harder design. At 10x, connections dominate cost before anything else does."

**Depth:** `../04-system-design` Category 10; `../03-microservices` Category 3.

---

### S11. Telecom-scale nightly batch to streaming (Q74)

> "You have a nightly batch that processes call detail records - eight hours, 400 million records, producing usage aggregates and billing inputs. The business wants near-real-time. Design the migration."

This one is as much about **migration strategy** as architecture, and candidates who design only the target system miss half the round.

**Minutes 0-4 - scope and constrain.**

- **Why real-time?** Push on this, politely. Real-time fraud detection is a different requirement from a customer-facing usage dashboard, which is different again from "the batch window no longer fits". Assume: customer-visible usage within a minute, and the batch window is genuinely at risk.
- **Does billing have to move?** Assume **no**, and say why loudly: billing is the correctness-critical, audited, reconciled path, and moving it to streaming is a much larger risk than the value justifies in phase one. This is the highest-scoring judgement call in the round.
- **Late and duplicate records?** Assume yes to both - network elements deliver late and re-deliver. This is the defining property of the domain.
- **Correction records?** Assume yes - a later record can amend an earlier one, which means aggregates must be revisable.

**Minutes 4-10 - the arithmetic.** 400 million records in 8 hours is about 14,000 per second sustained *if* the batch were spread evenly - and the streaming system must handle the real arrival distribution, which is peaky, so design for 30,000-50,000 per second. At ~500 bytes a record that is 200 GB a day, 70 TB a year raw.

**The point to make from the arithmetic:** the streaming ingest rate is comparable to what the batch already processes; the hard part is not throughput, it is **correctness under late arrival and the coexistence of two systems** during the migration.

**Minutes 10-25 - the design.**

*Ingest.* Records land on a partitioned log, partitioned by subscriber id so that all records for one subscriber are ordered and one consumer owns their state (Q174). Retention long enough to reprocess - at minimum longer than your worst recovery time, and ideally long enough to rebuild a day.

*Processing.* Stateful stream processing with **event-time windows and watermarks**, not processing time. Explain the distinction, because it is the heart of the round: a record for 23:58 that arrives at 00:04 must land in yesterday's window, and a system keyed on arrival time silently gets this wrong forever. Allowed lateness bounded (say two hours), and records later than that go to a **late-arrival path** that emits a correction rather than being dropped.

*Deduplication.* A record id with a keyed state store and a TTL matching the maximum expected delay window. Say the cost: this state is per-key and it is the thing that determines your memory footprint and your recovery time.

*Aggregates.* Emit **revisable** aggregates - each output carries a version and a watermark, and consumers must handle a restatement. This is the architectural consequence of late data and it must be in the contract, not bolted on.

*Serving.* Aggregates written to a store optimized for the read pattern - per-subscriber current usage as a key-value lookup, and a columnar or time-series store for analytics.

**Minutes 25-38 - the migration, which is the real content.**

- **Phase 0: run in parallel, compare, change nothing.** The streaming pipeline runs alongside the batch and writes to a shadow output. A reconciliation job compares the two nightly and reports discrepancies by class. **You do not cut over until the discrepancy rate is understood, not just small** - a 0.01 percent difference that you cannot explain is a blocker, because the explanation is usually a whole class of records.
- **Phase 1: new consumers on streaming.** The customer-facing usage dashboard reads from the streaming aggregates. Nothing that exists today changes. This delivers the business value that motivated the project, at almost no risk, and it is the phase most candidates skip.
- **Phase 2: retire the batch for non-billing outputs**, one output at a time, each with its own reconciliation period.
- **Phase 3: billing, if ever** - and only with a full parallel run over a complete billing cycle, sign-off from finance and audit, and a rollback that is "keep running the batch" rather than a data migration.

Say the sequencing principle out loud: **the batch is the reference implementation until it is provably redundant**, and every phase keeps it running.

**Minutes 38-42 - failure and operations.** Consumer lag is the primary SLI, with alerting on the derivative as well as the value. A bad deploy in a stateful streaming job is worse than in a stateless service because state is expensive to rebuild - so you need savepoints and a tested restore, and you must know your rebuild time. Reprocessing a day requires either a long enough log retention or a replay from cold storage, and you should know which. And the operational cost is real: a 24/7 pipeline needs on-call, and the batch effectively did not.

**Minutes 42-45 - close.** "Partitioned log by subscriber, event-time windowing with bounded lateness and a correction path, revisable aggregates, and a migration that runs in parallel and moves consumers rather than moving the pipeline. The two decisions that define it are event time over processing time, and keeping billing on the batch until it is proven redundant. **The part I would push back on** is the requirement itself - if the driver is only the batch window, a faster batch or a micro-batch every fifteen minutes gets most of the value for a fraction of the risk, and I would want to see the business case for seconds before committing to a stateful streaming platform and the on-call burden that comes with it."

**Depth:** `../04-system-design` Categories 8 and 12; `../06-database` Category 11; `../03-microservices` Category 3.

---

### S12. An AI assistant inside an existing enterprise SaaS product (Q75)

> "We have a mature B2B SaaS product with 3,000 customer organizations. Leadership wants an AI assistant in it. Design it."

The trap is designing a chatbot. The round rewards designing the **surrounding system**: permissions, evaluation, cost, and the failure behaviour.

**Minutes 0-4 - scope and constrain.** Push hard here, because the requirement as given is not a requirement.

- **What job does it do?** Offer three and make them choose: answer questions about the customer's own data; answer questions about the product (help and documentation); or take actions in the product. Say why it matters: "these are three different systems with different risk profiles, and the third one is an order of magnitude harder because it needs an authorization architecture" (Q127).
- Assume: **primarily question-answering over the customer's own data, plus product help**, with actions deferred.
- **Who sees what?** Assume the product already has a permission model with roles and record-level access. **The assistant must not become a permission bypass** - that is the requirement that shapes everything.
- **Latency and volume?** Assume first token in under two seconds, and maybe 50,000 queries a day across all tenants.
- **Data handling?** Assume enterprise contracts prohibit training on customer data and some tenants require regional residency.

**Minutes 4-10 - the arithmetic.** 50,000 queries a day is well under one per second - **throughput is irrelevant**, which is worth saying explicitly because it stops the round drifting into scaling. At maybe 4,000 input and 500 output tokens per query, the cost is a per-query figure in the low cents, so tens of thousands of dollars a year at this volume - material but not decisive. **What matters is per-tenant cost attribution**, because with 3,000 tenants and no per-tenant limit, a single automated integration hammering the assistant is both an outage and a bill.

Retrieval sizing: if a typical tenant has 100,000 documents and records, the index is per-tenant-filtered rather than per-tenant-physical - 3,000 separate indexes is an operational problem, one index with a mandatory tenant filter is not.

**Minutes 10-25 - the design.**

*Shape.* A retrieval-grounded assistant, not a fine-tuned model. Say why in one sentence: the data changes constantly and is tenant-specific, which is exactly the case retrieval serves and fine-tuning does not (`../09-rag` Category 1).

*Ingestion.* The product's existing data changes continuously, so indexing is **event-driven off the existing change stream**, not a nightly crawl - and the permission metadata must be indexed alongside the content, because it changes too. State the hard part: **when a user's access is revoked, the index must reflect it immediately**, which means permissions are evaluated at query time against the current source of truth, not baked into the index alone.

*Permission-aware retrieval.* Filter **inside** the vector search with a mandatory tenant predicate and the user's accessible-resource set, not after. Post-filtering silently destroys recall and, worse, leaks through result counts and citations. If the accessible set is too large to pass as a filter, invert it - retrieve then check against the authoritative service, and over-fetch to compensate. Say which you would choose and why (`../09-rag` Category 10).

*Retrieval.* Hybrid lexical plus dense, because product data is full of identifiers, customer names and codes that embeddings handle badly. A reranker over a wide candidate set. Query routing: a question about the product goes to the documentation index, a question about the customer's data goes to the tenant index, and an ambiguous one goes to both.

*Generation.* Grounded answers with **citations to records the user can click**, which is both a trust feature and your cheapest hallucination control - a claim with no citation is visibly unsupported. Explicit abstention when retrieval returns nothing above threshold (Q126).

*Placement in the product.* Behind the existing API gateway, using the existing session and permission context - not a separate service with its own auth, which is how the permission bypass gets built by accident.

**Minutes 25-38 - the deep dives.**

- **Evaluation.** A per-tenant-shaped golden set built from real queries, with retrieval recall and answer groundedness scored separately (Q125). Run in CI on every prompt, model or index change. The multi-tenant twist: **the aggregate score hides per-tenant regressions**, so you need slices by tenant size and data type, and a canary set of tenants who opted in.
- **Rollout.** Off by default, on per tenant, with an admin toggle. Start with internal use, then five design-partner tenants, then general availability. A per-tenant kill switch that an account manager can pull without a deploy. This is the answer to "how do you ship AI into an enterprise product safely" and it is mostly product mechanics rather than model work.
- **Cost and abuse.** Per-tenant quotas and rate limits, cost attribution tagged to the tenant, a per-query token cap, and caching - both exact-match and semantic - with the honest note that cache hit rates on free-text queries are usually disappointing.
- **Data handling.** Zero-retention terms with the provider or a self-hosted model for the tenants that require it; regional routing for residency; and a clear statement of what is logged, because your request logs now contain customer data and that changes their classification.
- **Security.** The tenant's own documents are untrusted content. If you later add actions, that is the lethal trifecta and it needs the authorization architecture from Q144 - say this now, briefly, as the reason actions are phase two (Q129).

**Minutes 38-42 - failure and scale.** Provider outage: fail to a clear "assistant unavailable" rather than a degraded wrong answer, and never block the rest of the product. Bad answers: a feedback control on every response, routed to the eval set. Index lag: show the freshness boundary rather than silently answering from stale data. At 10x tenants, the operational issue is not compute - it is the long tail of tenants with unusual data shapes on which quality is quietly poor, which is an argument for the per-tenant metrics being built first.

**Minutes 42-45 - close.** "Retrieval-grounded, inside the existing permission context, event-driven indexing, per-tenant everything - quotas, metrics, rollout, kill switch. The two defining decisions are filtering inside retrieval rather than after it, and deferring actions to a second phase with a real authorization design. **The weakest part** is index freshness against permission changes; I have made permissions authoritative at query time to cover it, which costs latency, and if that budget is too tight the design gets harder. The thing I would want to measure before general availability is per-tenant quality, because the aggregate will look fine while a tenant with unusual data is having a bad experience."

**Depth:** `../09-rag` Categories 10-11; `../08-genai` Category 10; `../11-security` Category 12.

---

### S13. Global API platform with data residency (Q76)

> "A public API used by customers worldwide. Some jurisdictions require that their residents' data never leaves the region. Design it."

The trap is treating residency as a deployment detail. It is a **data-model and routing** problem, and saying that early is most of the round.

**Minutes 0-4 - scope and constrain.**

- **What exactly must stay in region - all data, personal data, or backups and logs too?** This is the question that separates people who have done it. Assume: personal data at rest and in backups, and **logs and telemetry count as data** - which is the requirement that catches teams out.
- **Can data be processed transiently outside the region?** Assume no for the strict jurisdictions.
- **Is there global data?** Assume yes - a product catalogue, configuration, and the tenant directory - and that it is non-personal.
- **Cross-region access by the customer's own staff?** Assume a user travelling should still work, which means the *access path* is global even though the *data* is not.
- **Availability target?** Assume 99.95 percent, which forces multi-AZ within a region and raises the awkward question of what a regional outage means when you cannot fail over.

**Minutes 4-10 - the arithmetic and the shape.** The key derivation is not volume, it is **the number of regions and what that multiplies**. Say it: "every region multiplies my deployment surface, my on-call complexity, my per-environment cost floor and my release coordination. So the design goal is the smallest number of regions that satisfies the requirement, and a single deployment artifact that is configured per region rather than a per-region codebase."

If the base cost of a region - load balancing, NAT, a minimum database footprint, observability - is on the order of a few thousand dollars a month before any traffic, then five regions costs a five-figure monthly floor. That number changes the conversation with the business about which jurisdictions to support, and raising it unprompted is a strong signal.

**Minutes 10-25 - the design.**

*The core decision: shard by residency.* Each tenant (or user) has a **home region** recorded in a global, non-personal **directory**. The directory maps identity to region and contains nothing that residency covers - an id and a region code. This is the linchpin: it is the only globally replicated store, and keeping it free of personal data is what makes the whole design compliant.

*Routing.* A global anycast edge terminates TLS and looks up the home region from the directory (cached), then proxies to that region. Say the failure mode: if the request lands at the wrong edge and the payload contains personal data, has data left the region? Handle it by routing on identity **before** the body is processed or logged, and by treating the edge as a transit layer with no logging of bodies. If the jurisdiction forbids even transit, the answer is a region-specific hostname and DNS-level routing, and the customer's client must use it.

*Per-region stack.* Identical infrastructure deployed by the same pipeline with a region parameter. Data stores are regional with **no cross-region replication of personal data** - which means your disaster recovery story within a strict region is multi-AZ plus in-region backups, not a warm standby elsewhere. Say that trade-off explicitly: **residency and cross-region DR are in direct tension**, and the customer has to choose.

*Global versus regional data.* Draw the line on the board: directory, catalogue, feature flags and configuration are global and replicated; everything user-generated is regional. Any new field is a residency decision, so the data model needs a classification annotation and a test that fails when an unclassified field is added to a regional entity.

*Logs and telemetry.* Regional log storage with regional retention. Aggregate metrics - counts, latencies, error rates with no user identifiers - can be global. Traces are the problem, because they carry identifiers and cross services; either strip them at the regional boundary or keep traces regional and correlate on a hashed id.

**Minutes 25-38 - the deep dives.**

- **Cross-region operations that are unavoidable.** Billing aggregation, global search, and a support engineer looking at a customer's data. Handle the first two by exporting **aggregates or pseudonymized data only**. Handle the third with in-region support tooling and access controls - and say that this is usually where the real compliance failure happens, not in the architecture.
- **Tenant migration between regions.** It will be asked for. It is an export, an import, a cutover with a read-only window, and a verified deletion at the source - and the verified deletion is the hard part, especially in backups. Be honest: "deletion from backups usually means waiting for the retention window to expire, and that has to be in the contract."
- **Release engineering.** One artifact, N regions, staged rollout region by region with the smallest first. Schema migrations run per region and must be backwards compatible, because the regions will not be at the same version simultaneously (Q99, Q110).
- **The API contract.** Regional endpoints with a documented discovery mechanism, and consistent behaviour across regions - a customer must not be able to detect which region they are in through behaviour differences, or you will get support tickets about it forever.

**Minutes 38-42 - failure and scale.** A regional outage in a strict jurisdiction means downtime for that jurisdiction, full stop - so say it out loud and make sure the business has agreed to it, because it is the consequence they least expect. A directory outage takes down routing globally, which makes it the single most critical component and the argument for it being tiny, heavily cached and independently deployable. At 10x tenants, the constraint is operational: the number of regions and the release coordination burden, not the request volume.

**Minutes 42-45 - close.** "Residency handled by sharding on a home region, with a tiny global directory that deliberately contains no personal data, identical per-region stacks from one pipeline, and a hard line between global and regional data enforced in the data model. The two defining decisions are the directory and the classification annotation with a failing test. **The weakest part** is disaster recovery in a strict region - I have traded cross-region failover for compliance and that is a real availability ceiling, so it needs to be an explicit, signed-off business decision rather than an architectural assumption."

**Depth:** `../05-aws` Categories 1 and 15; `../04-system-design` Category 9; `../11-security` Category 16.

---

### S14. Rebuild an on-premise Java monolith on AWS, fixed budget, hard date (Q77)

> "A ten-year-old Java monolith, on-premise, 400 tables, 1.2 million lines. The datacentre contract ends in fourteen months. You have a fixed budget. Go."

The constraints are the question. A candidate who designs a target architecture and ignores the date has failed. **The date is not negotiable and the scope is.**

**Minutes 0-4 - scope and constrain.** The questions to ask, and what the answers do:

- **Is the date genuinely immovable, and what happens if we miss it?** Assume immovable with a punitive extension cost. This makes it a **risk-management** exercise.
- **What is the current deployment frequency and test coverage?** Assume quarterly releases and thin coverage. This is the real constraint on how fast anything can move.
- **How many integrations does it have, and who owns them?** Assume 30, half owned by other teams. Integration coordination, not code, is usually the critical path.
- **Does the business need new features during this period?** Assume yes, some. A feature freeze is the thing everyone wants and nobody gets, so plan for parallel change.
- **What is the data volume and the acceptable cutover downtime?** Assume 4 TB and a four-hour weekend window.

**Minutes 4-10 - the strategy, said before any architecture.** This is the highest-scoring two minutes in the round:

> "With fourteen months and a hard date, I would not rewrite and I would not decompose. The plan is **rehost first, then improve** - get it running on AWS as close to as-is as possible, prove it, cut over with time to spare, and use the remaining months for the highest-value modernization. A rewrite or a decomposition in this window is how you end up asking for the datacentre extension in month twelve, and I have seen that go badly. The counterargument is that lift-and-shift does not deliver the cloud benefits - true, and I would rather deliver the deadline and a roadmap than a partial architecture and a missed date. If we finish the migration in month nine, we have five months to strangle out the two components that would benefit most."

Then set the budget frame: rehosting on right-sized instances with reserved capacity is predictable; the cost risk is in data transfer and in over-provisioning "just in case", so the plan includes a load test that sets the sizing rather than guessing.

**Minutes 10-25 - the plan.**

*Months 1-2: discovery and the two things that always bite.* Inventory the integrations and their network requirements, and inventory the **hidden dependencies** - the scheduled jobs on someone's server, the shared file mount, the hard-coded IPs, the database links, the licence keys tied to a MAC address. Say that these are what actually delay migrations, not the application. In parallel, set up landing zone, network connectivity (Direct Connect or VPN) and the CI/CD pipeline, because everything else depends on it.

*Months 2-5: the target and the automation.* Run the application on ECS or EC2 - choose EC2 if the app has any assumption about local state or a specific JVM tuning, ECS if it is genuinely stateless, and say the criterion. The database goes to RDS or Aurora if the engine is compatible, and **the compatibility check is a month-one task**, because an incompatibility here changes everything. Externalize configuration and secrets. Build the environment from Terraform so that the test environment and production are the same artifact.

*Months 4-8: the data path.* Continuous replication from on-premise to AWS with a tool that supports ongoing change data capture, so that the cutover is a switchover rather than a copy. Practise the cutover **at least three times** in a non-production environment and once as a full dress rehearsal with the real data volume, timed. State the rollback: DNS or connection string back to on-premise, valid for as long as reverse replication runs - and that reverse replication is the part everyone forgets.

*Months 8-10: cutover.* By component if the integrations allow, big-bang if they do not. Freeze non-essential change for two weeks around it. Have the go/no-go criteria written down in advance and agreed - not decided at 2am.

*Months 10-14: the buffer, and then modernization.* Explicitly reserve two months of buffer before the contract ends, and say so: "the plan finishes in month twelve so that a two-month slip does not become a crisis." With whatever is left, take the two highest-value improvements - typically extracting the component with the different scaling profile, and moving the batch jobs to a managed scheduler.

**Minutes 25-38 - the deep dives.**

- **Cutover mechanics and the go/no-go criteria.** Replication lag under a threshold, a verified row-count and checksum comparison, the smoke suite passing, and every integration owner having confirmed readiness. Rollback rehearsed, not theoretical.
- **How you keep delivering features during the migration.** One codebase, deployed to both environments from the same pipeline as early as possible - because a long-lived migration branch is the second most common way this fails.
- **Cost control.** Right-size from a load test rather than from the on-premise specification, which is almost always over-provisioned; savings plans only after the sizing is proven; and a budget alarm from week one. Be honest that the first month on AWS will cost more than the steady state.
- **The risk register**, and name the top three: a database incompatibility discovered late, an integration owner who cannot move in time, and the hidden-dependency inventory being incomplete. Each with a mitigation and a date by which it must be resolved.

**Minutes 38-42 - what could go wrong.** Performance regression after cutover is the most likely surprise - different storage characteristics, different network latency between app and database, and a JVM sized for a machine that no longer exists. Mitigate with a load test at production volume in month five, not month eleven. The second is that the team is doing the migration and their day job; if the budget is fixed, say plainly that scope has to give somewhere and that you would rather cut modernization than cut rehearsal.

**Minutes 42-45 - close.** "Rehost first with a two-month buffer, then modernize with what is left. The defining decisions are refusing the rewrite and rehearsing the cutover three times. **The part I would be most worried about** is the integration owners I do not control, because that is the dependency I cannot fix with engineering - so I would want those conversations started in week one and a named owner per integration with a date. And I would want the go/no-go criteria agreed in month three, in writing, while everyone is calm."

**Depth:** `../05-aws/core-services` Category 12; `../06-database` Category 12; `../07-devops` Category 1.

---

## Part C - The story rounds

No scripted answers. Q186-Q191 must be **your** stories, from Nittany Technologies, Verizon India and Sonata Software, with real numbers. Generic answers are transparent at nineteen years of experience.

**How to build each one.** Write the full account once, with the real details, then reduce it to a **spine** you can say in two sentences: system and stakes, your decision, the outcome with a number, the learning. Memorize the spine, not the words (Q185). Then rehearse at two lengths, because interviewers ask for both and the six-minute version is not the two-minute one delivered slowly.

**What every story must contain**, checked against the grading key in Q6:

- A **number** in the Situation and a **number** in the Result.
- A **decision you made**, with the alternative you rejected and why.
- A **second-order effect** - what changed for the organization, the cost curve or the class of failure, not just for the ticket (Q5).
- Something you got **wrong**, or someone who **disagreed** with you and had a point.
- One sentence of **Learning** that is a rule you now apply, and that you can show yourself applying since.

### S15. The largest system you architected end to end (Q186)

Prepare both lengths deliberately, because this is the question most likely to be asked twice in a loop by two interviewers who compare notes. The two-minute version is scope, your role, the two decisions that defined it, and the outcome. The eight-minute version adds the constraint that forced the design, the alternative you rejected, the part that turned out to be wrong, and what you would build differently now (Q206).

Guard against the two failures: describing the system rather than your decisions, and being unable to say what you personally chose.

### S16. A production incident you led (Q187)

Tell it as **incident command**, not as debugging. The interviewer for this question is listening for the things in Q106: that you took command and said so, that you mitigated before diagnosing, that you communicated on a cadence, that you made a call with incomplete information, and that the follow-up changed the class of failure rather than fixing the instance.

Have the timeline with real times in it. "We were paged at 02:14, mitigated at 02:40, root-caused at 09:00 the next morning" is far more convincing than any adjective, and the gap between mitigation and root cause is itself the evidence that you did them in the right order.

### S17. A technical decision you lost (Q188)

The whole value is in the second half - see Q184. Prepare the strongest possible version of the other side's argument, because your ability to state it fairly is what is being scored. Have the mechanism by which you committed visibly, the condition you agreed for revisiting, and what actually happened.

Choose a decision that mattered. A story about losing an argument over a library choice does not demonstrate anything.

### S18. Mentoring a struggling engineer to independence (Q189)

The evidence is the hard part. "They improved" is not evidence; "they went from needing review on every change to owning the payments integration and being the person the team asks" is. Have a before and after that a third party could verify, and a timeframe.

Include what you tried that did not work, and the moment you changed approach - mentoring stories without a course correction sound like coaching theory rather than experience. And be honest about the cases where it did not work out; being asked "have you ever failed at that?" is a common follow-up (Q182).

### S19. The boring solution - right once, wrong once (Q190)

Two stories, deliberately paired, because the pair is what demonstrates judgement rather than a preference. The first shows discipline; the second shows that you know the boring choice is a heuristic and not a principle, and that you can tell when it cost you.

For the second, the key is to identify **what signal you missed** - the constraint that would have told you the conservative option was the wrong one - and to state the rule you now use to catch it.

### S20. Driving a standard across teams you did not own (Q191)

This is the principal-level story in the bank, and it must contain the evidence from Q180: what you built that made the right way easier than the wrong way, who resisted and what changed their mind, and - the strongest close available - **that it outlived your involvement**.

Have the adoption number, the team you failed to win over and why, and the part of the standard you had to give up to get the rest accepted. A story where everyone agreed is not a story about influence.
