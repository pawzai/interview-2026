# Scenario Questions

Twenty scenarios: ten production incidents, six design walkthroughs, four leadership situations. These are what a principal-level GenAI interview actually spends its time on - the questions in [questions.md](questions.md) establish that you know the mechanism, and these establish that you have used it.

Work them **out loud** for five to ten minutes before reading the answer. The answers here are longer than you should speak; they are written so you can see the reasoning and the numbers, and you should compress each to a two or three minute spoken version.

**Part A** uses **CIDER**: Clarify, Isolate, Decide, Execute, Reflect. Say the clarifying questions out loud even when you then answer them yourself - an interviewer is testing whether you jump to a cause.

**Part B** uses the same spine for design: clarify the requirements and constraints, isolate the hard parts, decide the architecture with the arithmetic, execute in a sequence you can defend, reflect on what you would revisit. Part B maps to Q267-Q272.

**Part C** has no scripted answer. Prepare them with real detail using STAR-L, defined in [../01-java/README.md](../01-java/README.md).

---

## Part A - Production incidents

### S1. A prompt change halved quality with no code change

> Support answer quality dropped from a 4.2 average judged score to 2.9 over a weekend. No deployment went out. The only change in the audit log is a prompt template edit made on Friday afternoon by a product owner with edit access to the prompt configuration.

**Clarify.** When exactly did the score start dropping - is it a step change at the edit time or a gradual slide? Is the drop uniform or concentrated in a segment (language, tenant, question type)? What exactly changed in the diff? Was the prompt version canaried at all, or applied to 100 percent? Do we still have the previous version? Is anything else in the release descriptor different - model fingerprint, index rebuild, retrieval config (Q252)? And is the judged score itself trustworthy, or did the judge model change?

**Isolate.** The step change aligning to the edit timestamp is strong evidence, but it is not proof, so I confirm before acting: pull 30 responses from before and 30 from after and read them - the failure mode should be visible immediately, and its *shape* tells me the mechanism. The typical findings, in order of likelihood:

1. The edit moved or displaced the output contract, so the answer format changed and the judge (rightly) marks it down.
2. The edit added a constraint that conflicts with an existing instruction, and the model is resolving the contradiction inconsistently.
3. The edit added text at the *top* of the prompt, invalidating the prefix cache (Q115) and, more importantly, pushing the critical instructions further from generation (Q67).
4. The edit removed a sentence that looked redundant and was load-bearing - the classic (Q75).
5. The edit is fine and something else changed concurrently, and the timestamp correlation is a coincidence.

I would also check cost per request and token distributions for the same window (Q259) - a cache-hit-rate collapse or an output-length jump confirms a prompt-shape cause and distinguishes it from a provider change.

**Decide.** Roll back the prompt version immediately - it is a one-flag change and there is no reason to keep a 1.3-point quality regression in production while we diagnose (Q248). Confirm recovery within an hour, then diagnose against the rolled-back baseline. Then fix the *process*, because the incident's root cause is not the sentence.

**Execute.**
1. Revert the release descriptor to the previous prompt version; verify the judged score and the token distributions recover.
2. Reproduce the regression in the eval harness with the bad version - this must reproduce, and if it does not, my diagnosis is wrong and the cause is elsewhere.
3. Add the failing cases to the golden set (Q143) - the eval set demonstrably did not cover whatever this was.
4. Fix the prompt properly with an eval run attached, canary at 5 percent, then ramp (Q253).
5. Close the process gap: prompt changes go through a PR with a required eval run and per-segment blocking (Q68, Q152); direct production prompt edits are removed as a capability; the eval gate is made fast enough that the product owner can run it themselves (Q153).
6. Add the alert that would have caught this in an hour rather than over a weekend: canary eval score with control limits, and output-token distribution shift (Q260).

**Reflect.** Two lessons. The first is technical: a prompt edit has a bigger blast radius than most schema migrations and no compiler (Q255) - so the surprise is not that this happened but that it *could* happen without a gate. The second is about access: giving a product owner prompt-edit access was a good instinct badly implemented. The right version is that they can edit the prompt in a branch, see the eval result in minutes, and merge with a review - which is faster for them than filing a ticket and safe for us. I would frame the remediation that way rather than as taking a capability away, because the alternative is that prompt changes route around engineering entirely.

> Hook: a configuration change with a larger blast radius than the code changes around it, and the gate you added.

### S2. A provider deprecates a model with 30 days notice

> Your primary chat model is being retired in 30 days. It serves four production features, one of which is a fine-tuned variant of that base. A large enterprise client has a contractual quality commitment on one of the features.

**Clarify.** Is there a named successor, and what does the provider say changes - pricing, context, tokenizer, defaults, verbosity, reasoning mode? Is there a paid extension option, and what does it cost? Which of our features use it, and at what volume - the telemetry query, not the registry alone (Q256). Is the fine-tune's base transferable, or does it need retraining? What does the client contract actually commit to - a metric, an SLA, or a change-notification clause? And is there a second provider already in our approved set with an evaluated equivalent?

**Isolate.** Thirty days is tight but workable; the critical path is the **fine-tune**, because retraining plus regression and safety evaluation plus promotion is two to three weeks on its own and cannot be parallelized past the data preparation. The second constraint is the client feature: if the contract has a change-notification obligation, the notice period may be longer than 30 days, which means the honest answer might be to buy the provider's extension while we migrate.

I would produce the inventory table in the first day: feature, volume, model use, fine-tune dependency, contractual exposure, and estimated migration effort.

**Decide.** Run three tracks in parallel:

1. **Evaluate the successor and one alternative provider** on the existing harness, unchanged prompts then adapted, per segment with cost and latency (Q47).
2. **Retrain the fine-tune** on the successor base as soon as the successor is confirmed viable, with the general regression and safety suites as gates (Q127, Q138).
3. **Buy the extension if it exists and is cheap** relative to the risk. Thirty days with a contractual client is not the place for heroism, and paying for six weeks of certainty is good engineering.

For the client feature, notify proactively with a plan rather than waiting to be asked - a provider deprecation is not our fault but managing it visibly is our job.

**Execute.**
- Days 1-3: inventory, notice analysis, extension decision, client notification, kick off the eval runs.
- Days 4-12: evaluation results per feature; prompt adaptation for the successor; triage regressions. Start fine-tune data preparation on day 4 regardless, because it is the long pole.
- Days 10-18: retrain and evaluate the fine-tune; shadow the successor on production traffic for the three prompted features and review the disagreement sets (Q254).
- Days 18-25: canary and ramp, lowest-risk feature first, client feature last with its own extended observation window.
- Days 25-30: buffer. Keep the old model available until it is switched off by the provider, not by us.

**Reflect.** The retrospective action is to make the next one boring: keep a validated second-choice model permanently in the eval harness so a migration is a re-run rather than a project (Q256); pin dated versions everywhere so we are never surprised by the softer version of this, a silent update (Q159); make deprecation policy and notice period an explicit selection criterion (Q43); and reconsider whether a *provider* fine-tune is the right form, since an open-weights LoRA we host ourselves would not have been affected at all (Q126, Q133) - that is the design lesson worth carrying.

> Hook: a forced dependency migration you ran to a deadline you did not choose.

### S3. Cost tripled overnight

> Yesterday's model spend was 1,100 dollars. Today's is on track for 3,400. Traffic is flat, no deployment went out, and the feature team says nothing changed.

**Clarify.** Tripled in total, or tripled per request? Which feature, which tenant, which model - or all of them? Is it input tokens, output tokens, or call count? When exactly did the curve change - a step or a ramp? Did the cache hit rate move? Is our accounting or the provider's the source of the number (Q226)? And "nothing changed" means no *deploy* - what about a flag, a config value, a prompt version, an index rebuild, or a provider-side change?

**Isolate.** Go straight to the token distribution panel by feature (Q259). The decomposition answers it almost immediately:

- **Input tokens per request up, cache hit rate down** → someone put volatile content in the prompt prefix, or reordered the sections (Q115). This is the most common cause of an exact tripling, because the input price goes from the cached rate to the full rate.
- **Input tokens up, cache unchanged** → retrieval is returning more or bigger chunks (a `topK` change, a chunk-size change, an index rebuild), or conversation history is no longer being compacted, or attachments got bigger.
- **Output tokens up** → a prompt edit, a model change, or a thinking mode enabled by default (Q12).
- **Call count up per user session** → a retry or repair loop firing (Q80), a cascade whose escalation rate jumped (Q222), or a client bug re-requesting.
- **Everything flat but cost up** → a price change, a tier change, a routing change sending traffic to a more expensive model, or a new caller sharing the account (Q226).

**Decide.** Contain first, diagnose second. Cost is not a correctness incident, but a 3x rate is a budget incident, so I would apply the degradation ladder if we are heading for a budget breach today (Q227) and roll back the most likely candidate change if there is one. If the cause is a cache-hit collapse, the fix is a prompt-ordering revert and it takes minutes.

**Execute.**
1. Identify the affected feature and tenant from the dashboard; check the cache hit rate and the token distributions in the same view.
2. Diff everything that is not code: flags, prompt versions, retrieval config, routing table, provider fingerprint, in the window (Q252).
3. Roll back the identified change; verify the cost per request returns to baseline within an hour.
4. If no change is identifiable on our side, check the provider fingerprint and open a provider ticket, and meanwhile clamp the cost with a `max_tokens` reduction and a routing change.
5. Add the alert that should have caught this at 20 percent rather than 300: cost per request day-over-day and cache hit rate floor (Q260).
6. Add the eval-and-cost gate to whatever change type caused it - if a retrieval config change can triple the bill with no review, that is the gap (Q152).

**Reflect.** The finding I would put in the retrospective is not the specific cause; it is that **the detection took a day and the diagnosis took an hour**, and both numbers should be the other way round. A cost-per-request alert with an hour-of-week baseline plus a cache-hit-rate floor turns this into a 20-minute non-event. I would also note that "nothing changed" is never a valid statement in a system whose behavior is determined by configuration and by a third party, and that the response to it should be a diff, not a debate.

> Hook: a cost incident where the detection lag was the real problem.

### S4. p99 latency from a long-tail generation

> The chat feature's p50 latency is 1.4 seconds and p99 is 11 seconds. The SLO is p99 under 5 seconds. The team has already ruled out the network and the retrieval layer.

**Clarify.** Is this total latency or time to first token? Is the feature streamed - and if so, which number does the user actually experience? What is the output token distribution, and what does latency look like plotted against output tokens? What is p99 at low concurrency versus peak? What is `max_tokens`? Are there retries, repairs or cascade escalations in the tail? Is a reasoning mode involved (Q12)? And is the SLO the right one - does a user waiting for the last token of a long answer care?

**Isolate.** The single most useful artifact is a scatter plot of total latency against output token count (Q210). Almost always it shows the tail is *legitimate*: p99 responses are five to ten times longer than p50, and latency is proportional to output tokens (Q1). If so, this is not a latency defect, it is an output-length distribution, and the fix is on the token side.

The other tail causes to check, in order: **cascade escalation** paying two models serially (Q222), **repair retries** (Q80), **prefill on long inputs** with a cache miss (Q21), and **queueing under peak concurrency** (Q200) - distinguishable because it correlates with load rather than with output length.

**Decide.** In this order, because the cheapest fixes are also the best product changes:

1. **If the feature is not streamed, stream it.** The perceived latency becomes TTFT (~600 ms), the SLO becomes achievable, and the cost is near zero (Q203, Q238). This is the single biggest lever and it is often the whole answer.
2. **Shorten the output** - ban preamble, specify shape, cap `max_tokens` with a properly handled truncation branch (Q23, Q223). This cuts the tail directly and reduces cost.
3. **Split the SLO** - TTFT p99 under 1.5 seconds and a separate completion target, because one aggregate number for a streaming feature measures the wrong thing.
4. **Bound the tail causes** - one retry not three (Q236), escalate the cascade in parallel rather than serially where the budget allows, cap input size, and check the prefix cache is being hit on long-context requests.
5. **Headroom for queueing** if the tail correlates with peak, plus admission control so the tail degrades predictably (Q211).

**Execute.** Instrument the latency decomposition first (queue, prefill, decode, guardrails, post-processing) so each change is attributable (Q229). Then stream, then the output-length work with an eval run to prove quality held, then the SLO redefinition with product, then the tail-cause fixes. Measure after each.

**Reflect.** The lesson to state is that **a single latency SLO is the wrong instrument for a generative feature**, because the quantity that varies most is the amount of work requested, not the speed of the system. The right SLO is TTFT plus a token-rate floor, with output length managed as a product decision. I would also flag that we spent effort ruling out the network and the retrieval layer before looking at the output token distribution, which is the domain-specific instinct worth building in the team.

> Hook: a latency SLO you redefined because it was measuring the wrong thing.

### S5. A jailbreak reaches production

> A user posts a screenshot on social media showing your customer-facing assistant producing prohibited content. The technique is a role-play framing wrapped in a low-resource language. It works reliably.

**Clarify.** What exactly was produced - disallowed content, our system prompt, another user's data, or an unauthorized action? The severity ordering matters enormously and determines everything that follows. How many users have done this - is it one researcher or is it spreading? Is the assistant's output attributable to us publicly? What did the input guardrail and output guardrail do (nothing, presumably - why)? Can we reproduce it? Does the same technique work on other flows, including ones with tool access?

**Isolate.** Reproduce it in a controlled environment immediately, then establish the *class*: this is jailbreaking (Q177), and the mechanism is that safety alignment generalizes across languages far worse than capability does (Q186), plus role-play framing exploiting the trained helpfulness of a creative collaborator. Then check the blast radius: does the technique also bypass the output guardrail (which likely runs only in English - the real finding in most versions of this incident), and does it work on any flow with tool access or private data, which would escalate this from a content incident to a security one (Q182).

**Decide.** Contain in hours, fix in days, harden in weeks.

- **Contain**: block the specific attack pattern at the input layer, add the language to the output guardrail's coverage, and if the affected flow has any privileged capability, restrict that capability immediately.
- **Fix**: the output guardrail must cover every language we serve - this is a genuine coverage gap and the correct primary remediation, because output filtering is the layer that does not depend on the model's cooperation (Q184).
- **Harden**: add the technique and its family to the permanent adversarial suite (Q157), and run a red-team pass over the other flows with the same lens (Q187).

I would not pretend a prompt fix solves it. Adding "do not role-play" to the system prompt is worth doing and is not a control (Q180).

**Execute.**
1. Reproduce, classify severity, and open an incident with a comms owner. If the output was prohibited content only, this is a sev-2; if it reached data or actions, it is a sev-1 with a security and privacy escalation path.
2. Deploy the input pattern block and the multilingual output guardrail. Verify with the reproduction.
3. Sample production traffic for other instances of the same technique and assess whether anyone was harmed.
4. Add cases to the adversarial suite, in all served languages, and make multilingual coverage a standing requirement for guardrail selection (Q57).
5. Red-team the remaining flows, prioritized by capability rather than by traffic.
6. Publish an internal note - the technique, why it worked, and the layer that should have caught it - because this is the most useful kind of shared learning and it usually gets skipped.

**Reflect.** Three things I would say. First, expect this: jailbreaks are not preventable at the model layer, so the design question is always "what is the layer that holds when the model is fully compromised" (Q178, Q181). Second, the real defect here was **guardrail language coverage**, which is a boring, discoverable gap that a coverage matrix would have caught - and I would add "every guardrail, every served language" to the launch checklist. Third, the severity ordering: the content was embarrassing, but if the same technique had reached a tool with write access it would have been a breach, and that is the argument for least-privilege tool design that this incident should be used to fund.

> Hook: a security finding whose real root cause was a coverage gap rather than a clever attack.

### S6. The eval suite passes while users complain

> The nightly eval suite has been green at 93 percent for six weeks. Support tickets about the AI feature have tripled in the same period, and the account team is escalating on behalf of two enterprise customers.

**Clarify.** What are the tickets actually saying - wrong answers, refusals, slowness, tone, formatting, or something not about quality at all? Which customers, which segments, which languages, which flows? Has anything changed in six weeks - traffic mix, a new customer onboarded, a corpus change, a model fingerprint? What does the eval set contain, how was it built, and when was it last refreshed? What are the implicit signals doing - regeneration, edit distance, escalation, repeat contacts (Q155)?

**Isolate.** The suite is green and users are unhappy, so **the suite is wrong**, and the diagnosis is a coverage analysis rather than a model investigation (Q144). I would take 50 real complaints, label the failures, and build the taxonomy (Q151). Then check each category against the eval set. The findings are usually some combination of:

1. **Segment absence** - the two escalating customers are in a segment (a language, a document type, an industry vocabulary) with no cases in the set, and the aggregate hides them (Q72).
2. **Distribution drift** - a customer onboarded eight weeks ago brought inputs unlike anything in the set, and the set was built from older traffic.
3. **The metric measures the wrong dimension** - correctness is fine and the complaints are about verbosity, tone, refusals or latency, none of which the suite scores (Q129).
4. **Single-turn coverage only** - the failures happen at turn six, from context rot or memory loss (Q111), and every eval case is one turn.
5. **Overfitting** - six weeks of tuning against the same 200 cases means 93 percent partly measures memorization (Q143).

**Decide.** Fix the measurement before touching the model. Concretely: rebuild the eval set from *current* production traffic with per-segment floors, add the complaint-derived cases, extend the metrics to the dimensions users are actually reacting to, add multi-turn cases, and hold out a portion for gates. Then re-score - and expect the honest number to be materially below 93 percent, which is the useful outcome.

**Execute.**
1. Complaint sampling and failure taxonomy - two days, and it produces the work list.
2. Re-baseline: re-sample the eval set from the last 30 days of traffic, stratified, with a floor per segment including the two escalating customers, plus the complaint cases. Score the current production configuration honestly and publish the real number with per-segment breakdown.
3. Add the missing metric dimensions and the multi-turn cases; validate any judge changes against human labels (Q149).
4. Fix the top failure categories by mechanism - retrieval misses go to retrieval, format issues to the schema, refusals to the guardrail thresholds - rather than by prompt-tweaking everything.
5. Institute the standing rules that prevent recurrence: every production complaint becomes an eval case, per-segment reporting with regression blocking, quarterly re-sampling with an owner, and a continuous judged production sample so the offline and online numbers can be compared (Q158, Q160).
6. Go back to the two customers with the measured per-segment numbers and a dated plan. That conversation goes very differently when you can show their segment's score.

**Reflect.** The lesson is that **an eval score is a claim about a distribution, and it is only as good as the sample**. A green suite with rising complaints is not a mystery, it is a sampling failure, and the tell that a team has internalized this is that they re-sample on a schedule and report per segment by default. I would also note the second-order failure: nobody had connected the ticket stream to the eval set, so the two systems that should have contradicted each other never met. Wiring complaints into the golden set is a one-week job that pays permanently.

> Hook: a metric that stayed green while the thing it measured got worse.

### S7. A fine-tune regressed on everything else

> A fine-tune improved invoice-field extraction from 88 to 96 percent and shipped two weeks ago. Since then: the assistant answers non-invoice questions in invoice JSON, it has stopped saying "I do not know", and one customer reports it produced content that it used to refuse.

**Clarify.** Which model exactly is serving which flows - is the fine-tune being used for anything beyond extraction? What was the training set, and did it contain any abstention, refusal or off-task examples? What learning rate, epochs, rank, and was it LoRA or full? Was a general regression suite run before promotion? Was a safety suite run? Is the base model still available and warm for rollback? And how many customers are affected by the refusal regression, because that determines the severity.

**Isolate.** This is textbook catastrophic forgetting (Q127), and the three symptoms name their causes precisely:

- **Answering everything in invoice JSON** - the training set contained only one output format, so the model learned the format as unconditional. Off-task inputs were never represented.
- **No longer abstaining** - the training set contained no abstention examples, so "always produce a value" was the learned behavior (Q81). This also means the extraction 96 percent is suspect: some of that gain may be confident guessing that the metric scored as correct because abstention was not scored properly.
- **Weakened refusals** - the fine-tune partially overwrote the base model's alignment training, which is itself a fine-tune (Q137). This is the serious one, because it is a safety regression rather than a quality one.

The process failure is singular and clear: **the promotion gate scored only the target task.**

**Decide.** Roll back the safety-relevant exposure immediately, keep the extraction gain if it can be isolated, and re-do the fine-tune properly.

- If the fine-tune serves *any* conversational or customer-facing flow, route those flows back to the base model now. This is a config change (Q133) and the refusal regression justifies it without further analysis.
- Keep the fine-tune for the extraction path only, behind a validation layer, while we assess whether the 96 percent survives correct abstention scoring.
- Re-train with the mitigations, gated on a general regression suite and a safety suite.

**Execute.**
1. Restrict the fine-tuned model to the extraction endpoint; verify no other route reaches it. Confirm the refusal behavior recovers on the conversational flows.
2. Re-score extraction with abstention counted correctly - a null where the field is genuinely absent is a success, an invented value is a worse failure than a miss (Q81). Publish the honest number; it may be below 96.
3. Build the general regression suite that should have existed: instruction-following, refusal behavior, format compliance on other formats, other languages, off-task inputs, basic reasoning - a few hundred cases, run against every candidate (Q127).
4. Re-train: LoRA at a modest rank, lower learning rate, fewer epochs with validation-loss monitoring, and **mix in 10-20 percent general instruction data plus explicit abstention and refusal examples**. This is the actual fix.
5. Promote only on: target metric held, general regression suite within tolerance, safety suite with zero regression, and evaluated on the *served* artifact rather than the checkpoint (Q133).
6. Make the general regression suite and the safety suite mandatory gates for every fine-tune, centrally provided so no team has to build them (Q160).

**Reflect.** The lesson to state clearly: **a fine-tune is a change to a general-purpose model, so it must be evaluated as one** - and a promotion gate that measures only the thing you were trying to improve will always let this through. I would also make the sharper point that the 88-to-96 improvement was partly an artifact of an evaluation that rewarded guessing, which is a measurement design error (Q81) and the kind of thing worth teaching, because it makes a fine-tune look better than it is at exactly the moment when someone is motivated to believe it.

> Hook: a change that improved its target metric and broke something nobody was measuring.

### S8. Non-deterministic output breaks a downstream parser

> A nightly batch job feeds model-extracted JSON into a billing pipeline. It has run cleanly for months. Last night 4 percent of records failed to parse, and 30 of them were partially written before the job aborted.

**Clarify.** What exactly failed - malformed JSON, valid JSON with a schema violation, or valid-and-schema-correct with a semantically impossible value? What is the failure distribution - random or concentrated on a document type? Is the pipeline using JSON mode, constrained decoding, or prompt-and-parse (Q77)? What changed - our prompt or config, or the provider's model fingerprint (Q159)? Is `finish_reason` being checked (Q23)? And critically: **what is the state of the 30 partially-written records**, because that is the bigger problem.

**Isolate.** Two separate defects here, and conflating them is the trap.

The **immediate cause** is likely one of: a provider model update changing output behavior; truncation at `max_tokens` on longer documents producing valid-prefix-invalid-JSON, which the parser reports as malformed (this is the most common and the most under-diagnosed); a new document type or a longer document entering the corpus; or, if it is prompt-and-parse, ordinary variance that finally exceeded the parser's tolerance - in which case the surprise is that it worked for months.

The **structural defect** is that a batch job writing to a billing pipeline has no transactional boundary, no idempotency and no per-record isolation: one bad record aborted the job and left partial state. That is the finding I would lead with in the retrospective, because the parse failures are inevitable and the partial write is a choice.

**Decide.** Fix the data integrity problem first, then remove the class of parse failure structurally.

1. **Reconcile the 30 records** - identify, quarantine, and either complete or reverse them. Billing data means this is a correctness incident, not a job failure.
2. **Make the job resumable and per-record isolated**: idempotency keys per source record (Q237), per-record commit, failures to a dead-letter queue rather than aborting, and a completeness reconciliation against the expected count.
3. **Eliminate malformed output structurally**: schema-constrained decoding so syntactic invalidity is impossible (Q36), plus explicit `finish_reason` handling so truncation is a distinct, handled outcome rather than a parse error (Q23), plus a repair loop with the error fed back for the remainder (Q80).
4. **Add semantic validation** at the boundary - enum membership against live data, arithmetic consistency, referential checks - so a schema-valid wrong value cannot reach billing (Q79).

**Execute.** Reconcile the records with finance's involvement; ship the per-record isolation and dead-letter handling (this is the urgent change); pin the model version if it was floating (Q51); switch to constrained decoding and re-run the eval set to confirm no accuracy loss (Q89); add the truncation branch; add the semantic validators; add a canary eval on the extraction path so a provider change is detected within an hour rather than at the next batch (Q159); and add a monitor on the parse-failure and repair rates with an alert (Q260).

**Reflect.** The lesson is the one worth generalizing: **model output is untrusted input, and a pipeline that assumed it was a stable API was always going to fail** - the question was only when. The three defenses are structural validity (constrained decoding), a validation boundary before the domain (Q233), and per-record isolation so a bad record is a dead-letter entry rather than an incident. I would also note that "it has worked for months" is the most dangerous sentence in this domain, because the model is a third-party dependency that changes without a deployment on your side.

> Hook: a pipeline that treated a probabilistic output as a stable contract, and what it cost.

### S9. PII leaks into a provider log

> During an incident review you discover that a debugging change made three weeks ago logs full prompts - including customer personal data - to the shared observability platform, which has organization-wide read access and 400-day retention. Separately, the provider account for one tenant is on a tier without a no-training agreement.

**Clarify.** What data exactly, for how many individuals, which tenants, and which categories (names and addresses, or special-category data)? Who has actually accessed the logs - is there an access audit? What does each affected tenant's contract say about data handling and about notification? What does the provider's tier actually permit - retention period, training use, sub-processors (Q188)? Is this reportable, and to whom, and on what clock? And who owns the decision - this is a privacy incident, so the privacy officer leads and I support.

**Isolate.** Two distinct exposures with different severities and different remedies:

1. **Internal over-collection and over-retention.** Personal data in a general-purpose log store with wide access and a long retention - a policy violation and a genuine risk (Q117, Q245). Contained within our boundary, which makes it serious but tractable.
2. **Third-party processing without an adequate basis.** Data sent to a provider on a tier that permits training use is a *transfer* problem, and it is the harder one because we cannot unsend it or delete it from their systems. It may also breach a customer contract directly.

**Decide.** Stop the flow, scope the exposure, remediate, and let the privacy and legal owners run the notification decision with our evidence.

**Execute.**
1. **Stop it now**: revert the logging change, or if that is not immediate, apply a redaction filter at ingest and restrict access to the affected indices. Migrate the tenant to the correct provider tier with a no-training agreement today.
2. **Scope it**: which records, which individuals, which tenants, over what window; who accessed the logs (the access audit is the material fact for the severity assessment); what the provider retained and for how long.
3. **Purge**: delete the affected log records, confirm deletion in replicas and backups or document the backup expiry window; submit a deletion request to the provider and record their response and its limits.
4. **Notify**: hand the scope to privacy and legal for the reportability decision (regulator clocks are short, so this happens in parallel with the technical work, not after it), and prepare the customer notification with facts rather than reassurance.
5. **Prevent recurrence, structurally rather than procedurally**:
   - Content never goes to the general observability platform. Payload logging goes only to the restricted store with encryption, short retention, access audit and per-tenant opt-out - enforced in the logging library so the easy path is the compliant one (Q245).
   - A redaction filter in the shared platform's ingest as a backstop.
   - Provider tier and data-handling terms recorded per tenant in the registry and **enforced at the gateway**, so a tenant's traffic cannot reach a non-compliant provider configuration (Q266).
   - A detection control: scan log ingest for PII patterns and alert, because the next version of this will also be accidental.
   - Add the data-flow question to the review checklist, and note that a *debugging* change bypassed the review entirely - which is the process gap (Q196).

**Reflect.** The honest reflection is that both failures were **defaults**, not decisions: the default log destination was the shared platform, and the default provider tier was the one you get without asking. That is what makes it a design problem rather than an individual's mistake, and it is why the remediation has to change the defaults rather than add a rule. I would also say plainly that the debugging change was made for a good reason - someone could not diagnose an AI failure without seeing the prompt - and that if we do not provide a sanctioned way to do that, it will happen again (Q117).

> Hook: a data-handling incident whose root cause was a default rather than a decision.

### S10. GPU saturation on a self-hosted model

> You self-host a 13B model for a privacy-constrained feature on two A100s. This morning p95 time to first token went from 700 ms to 9 seconds, request timeouts are at 6 percent, and GPU utilization reads 97 percent - as it has for weeks.

**Clarify.** What is the request rate versus last week, and what is the *shape* - input length distribution, output length, concurrency? What does queue depth and queue wait look like (Q209)? What is KV cache utilization and batch occupancy? Has anything changed - a new tenant, a longer prompt, a bigger `topK`, an index rebuild producing larger chunks, a `max_tokens` increase? Did a replica die? And is 97 percent utilization meaningful here - it has been 97 percent for weeks, so it is not the signal.

**Isolate.** GPU utilization is not a capacity metric for this workload (Q202, Q209), so I go to queue wait and KV cache utilization. The likely findings:

1. **KV cache exhaustion.** Something increased context length per request - a longer system prompt, more retrieved chunks, longer conversations - and the cache is now the binding constraint, so the scheduler is admitting far fewer concurrent sequences and everything queues (Q198-199). A 2x context increase halves your concurrency, and nothing about "utilization" reveals it.
2. **A prefill storm.** A tenant started sending very long inputs, and prefill is preempting decode for everyone, which shows up exactly as a TTFT collapse (Q210).
3. **Genuine demand growth** past the knee of the throughput curve, where a small load increase produces a large latency increase.
4. **A lost replica**, halving capacity.

**Decide.** Restore service with the fastest safe lever, then fix capacity properly.

- **Immediate**: enable admission control with deadline-aware rejection so we shed rather than time out - a fast 503 with `Retry-After` is much better than a 9-second wait followed by a timeout, for both users and cost (Q211). Cap per-tenant concurrency to stop one tenant monopolizing the cache. Reduce `max_tokens` and retrieved chunk count as a degradation step (Q227).
- **Hours**: reduce context per request (fewer chunks, trim the prompt), and quantize the weights to FP8 if not already - on a 13B model that frees roughly 13 GB per GPU, which buys a substantial increase in concurrent sequences and is usually the cheapest capacity lever available (Q204, Q207).
- **Days**: add capacity with a warm floor and predictive scaling rather than reactive, because cold starts are minutes (Q208); and configure a burst-to-API overflow path if the data constraint permits it for a subset of traffic, or accept queueing honestly if it does not.

**Execute.** Ship admission control and per-tenant concurrency caps first. Then the context reduction and the quantization, with an eval run to confirm quality held on the quantized artifact - including long-context and rare-entity cases, because that is where quantization damage concentrates (Q205). Then re-derive the capacity model from the KV cache arithmetic (Q207) and size the fleet against p95 context length rather than the average. Then fix the monitoring: scale and alert on **queue wait and KV cache utilization**, not GPU utilization, and add a panel for context length per request.

**Reflect.** Two lessons. The operational one: **for inference, the capacity metric is memory and queue wait, not utilization** - and a team monitoring utilization will always be surprised by this, because the signal they are watching is saturated long before the problem starts. The design one: the incident's trigger was almost certainly a change elsewhere (more retrieved context, longer prompts) that nobody connected to GPU capacity, which is an argument for treating context length as a governed budget with an owner (Q108) rather than as a parameter any team can raise.

> Hook: a capacity incident where the metric everyone was watching could not have shown the problem.

---

## Part B - Design walkthroughs

### S11. Document extraction at 200,000 invoices a day (Q267)

**Clarify.** What accuracy target, per field or per document, and what is the business cost of a wrong field versus a rejected document? What is the document population - languages, formats, born-digital versus scanned, how many distinct supplier templates? What is the schema, and how often does it change? What is the latency requirement - is this batch overnight or interactive at upload? What is the human review capacity available, and what does a reviewer cost per document? What are the audit requirements - who will ask to see why a value was extracted? And what does the current process cost, because that is the benchmark.

Assume: 200,000/day, 95 percent born-digital PDFs, 12 languages, overnight batch with a 4-hour window plus an interactive path for priority documents, 25-field schema, target 99 percent field accuracy on accepted documents, and an auditable trail.

**Isolate the hard parts.**
1. **Accuracy at scale with a long tail of templates** - the model will be excellent on common layouts and weak on the unusual ones, and the unusual ones are where the money errors live.
2. **Knowing which documents to trust**, since 99 percent on *accepted* documents implies a calibrated confidence and a review path, not a better model.
3. **Auditability** - provenance per field, not just a value.
4. **Cost at volume** - 200,000 documents a day is 6 million a month, so per-document cost dominates every other consideration.
5. **Schema and taxonomy evolution** without re-validating everything.

**Decide - the architecture.**

```
Upload / batch drop
   → Document intake: type detection, dedup by content hash, page split
   → Text layer: native PDF text extraction; OCR only for scanned pages
   → Classification: document type + template family (small fine-tuned model)
   → Extraction: fine-tuned small model, schema-constrained decoding
        - fields with nullable/sentinel abstention
        - source_text verbatim quote + page/bbox per field
   → Validation layer (deterministic):
        - source_text verified present in the document
        - arithmetic: line items sum to subtotal, tax, total
        - referential: supplier, currency, GL code exist in master data
        - format: dates, VAT numbers, IBAN checksums
   → Confidence composition + threshold
        ├─ pass  → auto-accept → ERP
        └─ fail  → escalate:
              → frontier model retry with the specific failures fed back
              → still failing → human review queue (document + highlights)
   → Random 2 percent of auto-accepted → review (measurement, not correction)
   → Audit store: document hash, request/response, versions, decisions
```

**The model decision and its arithmetic.** This is the classic fine-tuning win (Q136):

```
Frontier prompted: ~2,500 input (schema + examples + doc) + 400 output
  6M/month x (2,500 x $3 + 400 x $15)/1e6  = 6M x $0.0135  ≈ $81,000/month
Fine-tuned small model: ~1,200 input (doc only) + 400 output, ~1/20 price
                                            ≈ $4,000/month
Escalation at 12 percent to the frontier model  ≈ $10,000/month
Total                                           ≈ $14,000/month
```

So roughly a 6x saving, plus a latency improvement, for a fine-tune plus a cascade. Training data comes from the frontier model labelling real documents with human verification of a sample - distillation, with the licence question answered first (Q130). I would still **start** on the frontier model prompted, ship it, collect labelled data from the review queue, and fine-tune once the schema is stable - because fine-tuning first means fine-tuning on a task definition that is still moving (Q121).

**Confidence and the review threshold.** Self-reported confidence is not usable (Q167). The composite is: source-text verification passed, all deterministic validations passed, agreement between two samples on the disputed fields, and OCR confidence for scanned pages. Then calibrate the composite against the reviewed sample so the threshold corresponds to a **measured** field error rate, and present the curve to the business: at a 92 percent auto-accept rate the field error rate is x and review cost is y. That choice is theirs, not mine (Q90).

**Throughput and the batch window.** 200,000 documents in 4 hours is ~14 per second, which is trivially parallel - the pipeline is embarrassingly parallel per document, so it is a worker-pool-and-queue problem. Use the provider's batch API for the overnight run at roughly half price (Q221), with the interactive path on the synchronous endpoint. Size the worker pool against the provider concurrency quota, not against CPU (Q228).

**Execute - sequence.**
1. Schema, validation rules and the audit store. The validation layer is the highest-value component and it is model-independent, so it comes first.
2. Frontier-model extraction with constrained decoding, provenance and abstention. Ship to one document type and one language, with 100 percent human review, to build the labelled set and measure honestly.
3. Calibrate the confidence composite; introduce auto-accept above the threshold; ramp the threshold as the data justifies it.
4. Add languages and document types one at a time, each with its own eval slice and its own per-segment score (Q72).
5. Fine-tune the small model on the accumulated data; introduce the cascade; measure the escalation rate and the cost curve.
6. Add the random-sample review of accepted documents - without it there is no measurement of the accepted population, which is the number the business actually cares about (Q175).

**Reflect.** What I would revisit: whether the classification step earns its place or whether one extraction model handles all templates; whether the fine-tune still beats the prompted frontier model in a year, since the frontier moves and the fine-tune does not (Q138); and the threshold, quarterly, against the realized error rate. The risk I would flag up front is **schema churn** - every field added is a re-labelling and re-training cost - so I would push hard on getting the schema right and on making additions rare and batched.

### S12. An evaluation and release platform for 30 teams (Q268)

**Clarify.** How many of the 30 teams actually ship AI features today, and what does their current process look like? What is the failure that motivates this - quality incidents, slow delivery, duplicated effort, or an audit finding? Is this funded as a platform team with a mandate, or as a shared-tooling side project? What does the current release path look like end to end, and how long does it take? What model providers and frameworks are in play? And what is the appetite for mandating anything, because a platform nobody must use has to be better rather than merely available.

**Isolate the hard parts.**
1. **Adoption, which is the whole problem.** A platform that is slower than a team's current ad-hoc process will be bypassed, and a mandated one will be complied with minimally.
2. **Cost of evaluation** - a suite expensive enough to skip is not a gate (Q153).
3. **Heterogeneity** - 30 teams, different tasks, different metrics, different frameworks. A rigid schema fails; no schema means no comparability.
4. **Judge quality and comparability** - every team building its own judge is both wasteful and unreliable (Q147-149).
5. **Safety consistency** - this is the one thing that genuinely must be uniform.

**Decide - the architecture.**

```
Team's repository
  eval/
    cases/*.jsonl            (their data, their domain, versioned)
    rubric.yaml              (criteria, from a template)
    config.yaml              (segments, thresholds, model + prompt refs)
                │
                ▼
   eval-harness library (platform-owned)
     - runner: n samples, parallelism, provider abstraction
     - response cache keyed on (prompt hash, model version, params, input)
     - deterministic assertion library (schema, grounding, bounds, banned)
     - reference metrics + programmatic verifiers
     - validated judge service (central, versioned, kappa published)
     - central safety suite (consumed as a dependency, versioned)
     - per-segment scoring, confidence intervals, paired comparison
                │
     ┌──────────┴───────────┐
     ▼                      ▼
  CI action            Results store
  - PR: subset,        - every run, immutable
    posts comment      - dashboards: score trend, cost,
    with per-segment     coverage, per-team portfolio
    deltas, blocks on  - release descriptors + attached
    segment regression   eval evidence
  - nightly: full
```

**The design decisions that determine whether it works:**

1. **Teams own cases and rubrics; the platform owns everything else.** Domain knowledge cannot be centralized and ownership is the point (Q160). The platform provides templates and a starter set generated from the team's own traffic, so a team's first eval set takes a day.
2. **Response caching is not an optimization, it is the adoption mechanism.** With caching, a PR only pays for what it changed, so the gate is 2-4 minutes and a couple of dollars. That single feature is the difference between a gate that runs and one that gets disabled.
3. **The judge is a central service** with a published validation number against human labels, a pinned version, and positional and length-bias controls built in. Teams supply the rubric; they do not implement the judge.
4. **The safety suite is a versioned dependency**, centrally maintained, with zero-tolerance regression blocking. This is the one mandate.
5. **Per-segment blocking is the default rule** - a segment regression blocks even when the aggregate improves (Q72). It is the single most valuable rule in the platform.
6. **The release descriptor** (Q252) is produced by the platform and carries the eval evidence, so promotion, canary, rollback and audit all reference one artifact.
7. **Statistics done properly, once**: paired comparison, confidence intervals, and a refusal to block on differences inside the noise (Q150) - because a gate that blocks on noise loses credibility permanently.

**Execute - sequence.**
1. The harness library plus the assertion library plus caching, proven on **two** friendly teams end to end. Do not build for 30 before it works for two.
2. The CI action with the PR comment and per-segment blocking. This is where adoption starts, because the report is immediately useful to the engineer making the change.
3. The judge service with published validation.
4. The safety suite as a dependency, and the mandate that comes with it.
5. The results store and the portfolio dashboard - coverage, score trend, cost and owner per feature. Visibility does more for adoption than policy.
6. Release descriptors, canary integration and rollback.
7. Starter-set generation and the labelling UI, which is what unblocks the teams who have no eval set at all - and that is most of them.

**Reflect.** The metrics I would hold myself to are **adoption and cycle time**, not features shipped: percentage of AI features with an eval gate, median time from PR to production, cost per eval run, and incidents from features that passed the gate. What I would refuse: writing teams' eval cases, approving their releases, and owning their quality (Q266). And the thing I would expect to get wrong first is the rubric templates - they will be too generic to be useful, and the fix is to harvest good rubrics from the teams that write them well rather than to author them centrally.

### S13. Self-hosted inference for a bank (Q269)

**Clarify.** What exactly cannot leave - all customer data, or specific categories? Is this a regulatory requirement, a contractual one, or a policy the bank could revisit (Q190 - worth asking, because sometimes it is a proxy control)? On-premise, or a private cloud tenancy in-region - the difference is enormous for cost and operations? What are the use cases and their volumes and latency requirements? What capability is genuinely needed - is this extraction and summarization, or open-ended reasoning? What is the existing GPU and MLOps capability, and who will be on call? What is the model-risk-governance process (SR 11-7 style validation) and what does it demand of us? And what is the budget shape - capex or opex?

Assume: private cloud in-region, no data to third-party providers, four use cases (document summarization, internal knowledge assistant, extraction, a code assistant), aggregate 30 million input and 6 million output tokens a day, p95 TTFT under 1.5 s for interactive use, and a model-validation regime.

**Isolate the hard parts.**
1. **Capability versus what you can host.** No self-hosted open model matches the frontier on the hardest reasoning, so use cases must be chosen to fit - this is a scoping conversation, not an engineering one.
2. **Capacity arithmetic and utilization.** GPUs are paid for whether busy or not, so the economics live or die on duty cycle.
3. **Operations** - cold starts, upgrades, on-call, and a serving stack the bank must own.
4. **Model risk governance** - validation, documentation, reproducibility, and change control that a regulator will inspect.
5. **Multi-tenancy and access control** inside the bank, which is usually stricter than between external customers.

**Decide - the architecture and the numbers.**

Model choice: a 70B-class open-weights model for the assistant and summarization, quantized to FP8; a fine-tuned small model for extraction; a code-specialized model for the code assistant; plus self-hosted embedding, reranking and guardrail models (Q57). Pinned weights, stored internally, never auto-updated - which is also exactly what model governance wants.

Capacity, using the Q199 arithmetic for a 70B model at FP8:

```
Weights FP8: 70e9 x 1                              = 70 GB
On 2 x H100 (160 GB), tensor-parallel within node
Overhead + activations                             ≈ 15 GB
KV cache available                                 ≈ 75 GB
Per-token KV (80 layers, 8 kv heads, 128 dim, FP8) ≈ 164 KB
At 8k context per sequence                         ≈ 1.3 GB
Concurrent sequences                               ≈ 55
At ~35 tokens/s per sequence, 500-token answers:
  each slot occupied ~14 s → ~4 requests/s per 2-GPU unit
Daily interactive demand: assume 150k requests/day, peak 5x average
  → peak ~9 requests/s → 3 units (6 GPUs), plus 1 for redundancy
```

So roughly **8 H100s** for the generation tier, plus 2 GPUs for embedding, reranking, guardrails and the extraction model (Q215), plus a small non-production environment. At reserved pricing that is on the order of 25,000-35,000 dollars a month all-in for hardware, plus roughly 1.5 FTE of platform engineering - which is the line that must be in the business case, because it is the one that gets omitted (Q216).

Serving: vLLM for continuous batching, PagedAttention, prefix caching and multi-LoRA (Q201, Q212), behind an internal gateway that does routing, quotas, metering, guardrails and audit logging (Q266). Warm floor with no scale-to-zero for interactive tiers; batch work on a separate queue that soaks the spare capacity overnight (Q208).

Governance: every model artifact in a registry with its weights hash, licence, evaluation results, quantization configuration and approval record (Q262); release descriptors pinning the whole tuple (Q252); full request/response audit logging with retention set by the bank's policy; documented human oversight per use case; and the eval suite as the validation evidence, which is the artefact that makes the model-risk process tractable rather than adversarial.

**Execute - sequence.**
1. One use case, one model, one GPU pair, non-production, with the eval suite and the governance artefacts from day one - because the governance path is the long pole and proving it on a small case is what de-risks the programme.
2. The gateway, metering and audit logging. Nothing goes direct to a serving endpoint, ever.
3. Production for the first use case behind a warm floor, with capacity measured against the model rather than assumed.
4. Add the small self-hosted models (embedding, rerank, guardrails), which are cheap and unlock the rest.
5. Add use cases one at a time, each with its own eval suite and validation package.
6. Batch tier on the same fleet for overnight work, which is what lifts utilization from embarrassing to defensible.

**Reflect.** What I would revisit: whether a **private-tenancy managed endpoint** from a major provider satisfies the bank's constraint, because if it does, it is dramatically cheaper and simpler than owning the fleet, and that question should be re-asked every six months as the offerings change. Also whether the capability gap on the hardest use cases makes one of them not worth doing at all - which is a better answer than shipping a weak version. And I would flag the risk that gets underestimated: this is not a project, it is a **permanent operational capability** with on-call, upgrades and a hardware refresh cycle, and the bank should decide to own that explicitly rather than discover it.

### S14. A customer-facing support assistant for 2 million users (Q270)

**Clarify.** What is the deflection target and what is a human contact worth - that number funds everything. What is the cost ceiling per conversation? What does "never state a wrong policy" mean operationally - never contradict the approved policy corpus (enforceable), or never be wrong (not)? What channels - web, app, voice? Which languages? What is the escalation path and its capacity? What is the knowledge corpus, who owns its accuracy, and how often does it change? What can the assistant *do* besides answer - look up an order, issue a refund? And what is the regulatory context, because a wrong statement about a financial or insurance policy has consequences beyond a bad review.

Assume: web and app, 8 languages, 400,000 conversations a month, a cost ceiling of 15 cents per conversation, read-only account lookups plus order status, human escalation available, and an approved policy corpus owned by the operations team.

**Isolate the hard parts.**
1. **"Never state a wrong policy"** - this is the defining constraint, and it converts the design from generative Q&A into **grounded, verified, citation-backed answering with enforced abstention** (Q164, Q176).
2. **Cost per conversation, not per message.** A conversation is 6-10 turns, so the budget is ~2 cents per turn including retrieval, guardrails and verification (Q218).
3. **Eight languages** across retrieval, generation, guardrails and evaluation - the coverage matrix is where these projects fail (Q70, S5).
4. **Escalation quality** - the handoff must carry context, and the escalation rate is the business metric.
5. **Abuse and injection**, since it is public-facing (Q177).

**Decide - the architecture.**

```
Web / app  → session service (state, not transcript - Q113)
   → input guardrail (abuse, injection, PII) - parallel with retrieval
   → intent routing (cheap model): account query | policy question |
     small talk | escalate
   → account queries → tools, authorized from the session (Q84),
     answer rendered from the tool result, not composed freely
   → policy questions → retrieval over the approved corpus (hybrid,
     language-aware, reranked) → grounded answer with mandatory
     per-claim citation and verbatim quoted span
   → verification (deterministic + entailment):
        quote present in cited chunk? numbers present in context?
        every claim cited?  → fail → regenerate once → fail → abstain
   → output guardrail (all 8 languages) → stream to user
   → escalation: structured summary + transcript + resolved state
```

Model tier: a mid-tier model for the grounded answer, a cheap model for routing and intent, a small self-hosted model for guardrails and entailment, and no frontier model in the default path (Q53). Prefix caching on the static prompt (Q114).

**Cost arithmetic per conversation** (8 turns):

```
Per turn: 3,500 input (2,200 cached) + 250 output
  input  1,300 x $3 + 2,200 x $0.30 = $0.0046
  output   250 x $15                = $0.0038
  embedding + rerank + guardrails + entailment (small/self-hosted)
                                    ≈ $0.0015
  routing call (cheap model)         ≈ $0.0003
  per turn ≈ $0.010  →  8 turns ≈ $0.082 per conversation
```

So ~8 cents against a 15-cent ceiling, with headroom for the escalation tail and for verification retries. Prefix caching is doing a lot of that work, which is why it is in the design rather than a later optimization.

**The "never wrong policy" mechanism**, stated as a set of enforced properties rather than an aspiration: retrieval restricted to the approved, versioned corpus; every policy claim must carry a citation with a verbatim span, verified character-for-character in code; unverifiable claims are stripped or the answer is replaced with an abstention plus an escalation offer; no model-generated numbers, dates or identifiers - all copied and verified or taken from tool results (Q172); and templated responses for the highest-risk policy categories where the model selects and fills rather than composes (Q176). The corpus's *accuracy* is explicitly the operations team's responsibility, with a freshness and review process - that division has to be agreed in writing, or we inherit an unbounded obligation.

**Execute - sequence.**
1. One language, one policy domain, grounded answering with verification and abstention, internal-only, measured against a golden set built with the operations team. This is where the quality bar is established.
2. Add the escalation path and the account tools (read-only), with authorization from the session.
3. Public launch to a small traffic slice with a human review of a sample of every conversation - expensive and non-negotiable for the first weeks.
4. Add languages one at a time, each with its own retrieval evaluation, its own golden set slice, and its own guardrail coverage check. Do not launch a language whose guardrails are untested.
5. Add the remaining policy domains, gated on corpus readiness.
6. Then optimize cost and latency (Q232), because the quality bar comes first and the budget has headroom.

**Reflect.** What I would revisit: the abstention rate, because the design deliberately trades answer coverage for correctness and the right balance is a business decision that should be reviewed monthly against escalation cost; whether the templated path for high-risk categories should be *wider* than initially scoped; and the escalation summary quality, which is invisible in eval suites and is what determines whether human agents trust the assistant. The risk I would name up front is **corpus rot** - a grounded assistant is only as correct as its corpus, so the highest-value thing the operations team can do is own document freshness, and if they will not, the assistant will confidently state last year's policy with a citation.

### S15. Code assistance inside an internal developer platform (Q271)

**Clarify.** What is the actual goal - throughput, onboarding speed, consistency with internal standards, or reducing time in code review? Which of those is measurable, and does anyone currently measure it? How many developers, in which languages and repositories? What are the IP constraints - can code leave the network, and what does the client contract say about client-owned code (in a services business this is the binding constraint)? What is the latency requirement, since inline completion and chat are different products? Is the ask completion, chat, review, test generation, or migration? And what is the appetite for measuring impact honestly, including the possibility that it does not help?

Assume: 900 developers, mixed Java/TypeScript/Python, a services business with client-owned code under NDA, an existing internal developer platform, and a mandate to improve delivery consistency rather than raw speed.

**Isolate the hard parts.**
1. **IP handling.** Client code under NDA cannot be sent to a third-party provider without permission, and permission differs per client. This is the constraint that shapes the whole design.
2. **Latency for inline completion** - useful completion needs sub-300 ms, which rules out most hosted frontier models and forces a small fast model close to the developer (Q203).
3. **Proving it helps.** Developer productivity measurement is notoriously bad, and shipping this without a measurement plan means we will never know.
4. **Internal-standards awareness**, which is the actual differentiator over a public tool - and it is a retrieval problem, not a fine-tuning one (Q123).
5. **Licence and provenance risk** on generated code (Q193).

**Decide - the architecture.**

```
IDE plugin / platform integration
  ├─ inline completion  → small fast code model, self-hosted, regional,
  │                       repo-local context (open files, imports, symbols)
  │                       target p95 < 300 ms
  └─ chat / refactor / review
        → context assembly: retrieval over the repo + internal standards
          corpus + ADRs + platform docs (per-client scoped index)
        → mid-tier code model; provider chosen by the repo's data class
        → output: diff-oriented, with the standards it applied cited
        → post-checks: licence/similarity scan, secret scan, compile/test
          where the platform can run it
Gateway: per-repo data classification → allowed provider set,
         enforced (Q266); full audit of what code went where
```

**The IP design, which is the core of the answer.** Every repository carries a **data classification** (internal / client-permitted-provider / client-restricted), set at onboarding and enforced at the gateway, not by developer discretion. Internal and permitted repositories route to the approved hosted provider under a no-training, zero-retention agreement (Q188); restricted repositories route only to the self-hosted model. Per-client evidence of permission is recorded, and the audit log answers "did any of client X's code go to a third party" precisely - which is the question that will eventually be asked. Inline completion runs on the self-hosted model for everyone, which conveniently satisfies both the latency and the IP requirement.

**Measuring whether it helps** - and I would insist on this before launch, because it is the difference between a capability and a fashion:

- **Primary: acceptance and survival.** Suggestion acceptance rate, and crucially the **edit distance and survival rate** of accepted code at 24 hours and at merge (Q155). Accepted-then-deleted is not value.
- **Secondary**: time from first commit to merge, review-comment counts on standards violations (the goal we actually stated), and onboarding time for new joiners on a platform repo.
- **Guardrails**: defect rate and incident rate on code with high AI contribution - measured, not assumed, because the honest risk is faster production of code nobody understands.
- **Self-reported**, as a supporting signal only: a short quarterly survey.
- **Design**: a staged rollout by team as a natural experiment with a comparison group, rather than a big-bang launch that makes attribution impossible.

**Execute - sequence.**
1. Data classification of every repository, and the gateway enforcement. Nothing ships before this - it is the constraint that cannot be retrofitted.
2. Self-hosted inline completion for internal repositories, with the latency target measured from the IDE, not from the server.
3. The measurement pipeline, live, before broad rollout.
4. Chat and refactor with retrieval over the internal standards corpus - this is where the differentiated value is, and it needs the standards corpus to actually exist and be curated, which is often a prerequisite project.
5. Licence and secret scanning on generated output, plus the compile-and-test loop where the platform can run it.
6. Staged rollout by team with the comparison group, and a published result at 90 days - including the possibility that the result is "no measurable effect on the stated goal", which we should be willing to say.

**Reflect.** What I would revisit: whether the differentiator should shift from completion to **standards-aware review**, since the stated goal is consistency and review is where consistency is enforced; whether the self-hosted completion model is worth its operational cost once providers offer regional, contractually-restricted endpoints; and the measurement itself, because the first version of any developer-productivity metric is wrong. The risk I would name is the seductive one: adoption metrics will look great and tell us nothing about the goal, so the discipline is to keep reporting survival rate and standards-violation counts even when acceptance rate is the number everyone wants to hear.

### S16. A cost and quality control plane at 4 million dollars a year (Q272)

**Clarify.** How is the 4 million distributed - a few large features or a long tail? How much is attributable today to a team, a feature and a tenant (usually: not much)? How much is self-hosted versus provider spend? Is the mandate to reduce cost, to control growth, to improve quality at the same cost, or to be able to answer an audit? Who owns the budget today, and is there chargeback? What already exists - a gateway, metering, evals? And what is the growth rate, because a 4 million spend growing at 15 percent a quarter is a different problem from a flat one.

**Isolate the hard parts.**
1. **Attribution is the prerequisite.** Without per-feature, per-tenant, per-team cost, nothing else in this design can be decided (Q225).
2. **Cost and quality must be governed together**, or cost control degrades the product invisibly and the savings get reversed.
3. **Enforcement without becoming a bottleneck** - the control plane must make policies real without approving individual requests (Q266).
4. **Heterogeneity** - multiple providers, self-hosted models, and non-generation models (embeddings, rerankers, guardrails) that people forget to count (Q226).
5. **Organizational**: the levers that matter most are decisions (retire a feature, change a threshold, commit to capacity), so the design has to produce decisions, not dashboards.

**Decide - the architecture.**

```
All AI traffic → AI Gateway (single path, no exceptions)
   - auth, key custody, provider routing + fallback
   - per-tenant/team/feature quotas, concurrency, budgets
   - attribution enforcement: reject unattributed calls (Q247)
   - prompt + response caching
   - guardrail invocation
   - usage event per call (tokens, versions, tags) → metering store
   - audit log

Metering store (one row per call, tokens not prices)
   → cost engine: versioned price tables applied at query time
   → joins to outcome events → cost per resolved task (Q218)

Quality plane
   - eval harness results per release descriptor (S12)
   - canary eval scores + judged production sample per feature
   - failure taxonomy counts, guardrail trips, refusal rates

Control plane
   - budgets + degradation ladders per feature (Q227)
   - routing policy per task class (Q53)
   - portfolio view: every feature x cost x quality x usage x owner
   - alerts: cost/request, cache hit rate, escalation rate, canary score
   - monthly + quarterly review packs generated automatically (Q265)
```

**The decisions this enables, which is the actual deliverable:**

| Question | Answered by |
| --- | --- |
| Which features cost the most per resolved task? | Portfolio view - and the answer is usually not the ones people assume |
| Where is the cheapest 30 percent saving? | Cache hit rates and token distributions per feature (Q232) |
| Which features should be retired? | Cost against usage against quality, quarterly |
| Should we commit to reserved capacity? | Utilization and stability of the base load (Q230) |
| Did the cost reduction hurt quality? | Cost and quality on the same review, same period, per feature |
| Which teams need help? | Eval coverage and quality trend by team |

**Expected savings, to make it concrete.** On a 4 million dollar spend, the Q232 ladder applied across the portfolio typically yields: prefix caching 15-25 percent, output-length discipline 10-20 percent, context hygiene 5-15 percent, task routing 15-30 percent on eligible traffic, and batch migration of offline work. Realistically **30-45 percent within two quarters** - 1.2 to 1.8 million dollars - with the majority from the first three, which are low-risk and fast. That is the business case for the control plane, and it pays for itself several times over.

**Execute - sequence.**
1. **Gateway and attribution first.** Route all traffic through it, enforce tags, reject unattributed calls. Nothing else is possible before this, and it typically takes a quarter to reach full coverage including the stragglers.
2. **Metering and the cost engine**, with daily reconciliation against provider invoices and an alarm on variance (Q226). Expect the first reconciliation to be embarrassing.
3. **The portfolio view** - cost, usage, owner per feature - published. Visibility alone changes behavior before any policy does.
4. **Quality plane integration** so cost and quality appear together. This is the guardrail that keeps the programme honest.
5. **Quotas, budgets and degradation ladders** per feature, with the user-visible steps designed (Q227).
6. **The optimization campaign**, feature by feature in cost order, each change eval-gated.
7. **The review cadence** with auto-generated packs and a decision log (Q265).

**Reflect.** What I would revisit: whether chargeback is the right model - it drives accountability and it also drives teams to hide work or under-invest in evaluation, so I would charge back inference and *fund evaluation centrally*, which is a deliberate asymmetry. Also the reserved-capacity commitments, quarterly, because prices fall. The risk I would name is that a cost control plane becomes a cost-*reduction* culture, where quality regressions are invisible and cheap models get chosen by default - which is why cost per **resolved task** and the quality plane are in the design from the start rather than added later, and why I would put a quality metric next to every savings claim in every review.

---

## Part C - Leadership situations

No scripted answers. Prepare each with STAR-L and real detail; an interviewer at this level is assessing judgement and how you behave when you are the most senior person in a room that has already decided something.

### S17. Pushing back on an AI feature that should not exist

> A senior stakeholder has committed publicly to an AI feature. You believe it should not be built: the problem is better solved by a rules engine and a search box, the failure mode is a confidently wrong answer in a consequential flow, and the measurement plan does not exist.

Think about: how you separate "this is technically unsound" from "this is not worth the risk", and which argument you actually lead with. What evidence you gather before the conversation - a prototype that demonstrates the failure mode is worth more than an opinion. How you offer an alternative rather than only a refusal, since a no with no path is rarely accepted. How you handle the sunk public commitment, which is the real obstacle - can the commitment be honoured by a different implementation? Who else needs to be in the room (risk, legal, the operational team who will handle the escalations). What you would accept as a condition rather than a block - a narrowed scope, a human-in-the-loop, a measured pilot with a kill criterion agreed in advance. And what you do if you lose: whether you can make it safe anyway, what you document, and where your line actually is.

The strongest version of this story is one where you changed the shape of the feature rather than killed it, and where you can name what would have changed your mind.

### S18. A team shipping prompts with no evaluation

> A team you do not manage ships prompt changes directly to production, several times a week, with no eval set and no gate. They are fast and well-liked, and they have had two quality incidents in three months that they consider acceptable.

Think about: how you open the conversation without it being a compliance visit - what they get out of this, not what the organization gets. Why "you are being reckless" fails and "you cannot tell whether your changes work" lands. How you use their own incidents as the evidence, without making it a blame exercise. The offer that makes it real: building their first eval set *with* them from their own traffic in a day, so they experience the value before they accept the process (S12). How you keep the gate fast enough that their speed is preserved, because their speed is genuinely valuable and a process that slows it will be routed around (Q255). What you do about the incident they think is acceptable - whether it actually is, and whose judgement that is. How you escalate if they decline, and what threshold justifies escalating over a team you do not own.

The best version of this story ends with the team advocating the practice to others, not complying with it.

### S19. Buy versus build on self-hosting

> Leadership is split. One camp wants to self-host open-weights models for control, cost and IP reasons. The other wants to stay on managed APIs. Both have made the decision emotional, and you are asked for a recommendation.

Think about: how you convert an identity argument ("we are a serious engineering org") into a decision with criteria - volume, duty cycle, data constraints, capability requirements, and the operational cost including on-call (Q216). The arithmetic you would bring, and how you present the break-even honestly including the FTE line that both camps tend to omit. How you handle the strongest argument on each side rather than the weakest. Why a hybrid is usually the right answer and how you avoid it being a fudge that satisfies nobody - which parts go where, and why. How you make the recommendation reversible: a trigger to revisit, a pilot that produces evidence rather than commitment. What you do with the non-cost factors that actually decide it. And how you handle being overruled - whether the losing option can be made to work, and what you would insist on either way.

The signal an interviewer is looking for is whether you can be the person who de-escalates a religious argument into an evaluable one.

### S20. Setting an org-wide AI engineering standard

> You are asked to set the AI engineering standard for 40 teams. You have no authority over them, a small platform team, and a history in the organization of standards that were announced and ignored.

Think about: why the previous standards failed, and whether you can find out honestly. What you make mandatory versus advisory, and how short the mandatory list can be - the discipline is that everything mandatory must be enforceable and cheap (Q160, Q196). How you make compliance the fast path rather than a tax: the gateway, the harness, the templates, the pattern library. Which single mandate you would fight for if you could only have one, and why (safety, or attribution, or the eval gate). How you use visibility instead of policy - a portfolio dashboard with owners does more than a mandate. How you find and fund early adopters, and how you use their results rather than your authority. The exemption path, and why a standard without one gets circumvented invisibly. How you measure the standard itself - adoption, cycle time, incidents from compliant features - and what you would do if the data said the standard was not helping. And what you refuse to own, because a platform that owns everything becomes the bottleneck and then the thing to bypass (Q266).

The strongest version of this story includes something you removed from the standard after evidence that it was not earning its cost.
