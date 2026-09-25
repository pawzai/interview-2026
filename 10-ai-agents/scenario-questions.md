# Scenario Questions

Twenty scenarios: ten production incidents, six design walkthroughs, four leadership situations. These are what a principal-level agent interview actually spends its time on - the questions in [questions.md](questions.md) establish that you know the mechanism, and these establish that you have run one.

Work them **out loud** for five to ten minutes before reading the answer. The answers here are longer than you should speak; they are written so you can see the reasoning and the numbers, and you should compress each to a two or three minute spoken version.

**Part A** uses **CIDER**: Clarify, Isolate, Decide, Execute, Reflect. Say the clarifying questions out loud even when you then answer them yourself - an interviewer is testing whether you jump to a cause.

**Part B** maps to Q261-Q266 in [questions.md](questions.md).

**Part C** has no scripted answer. Prepare them with real detail using STAR-L.

---

## Part A - Production incidents

### S1. One request cost 400 dollars

> Finance flags a single support conversation that consumed 380 dollars of model spend in eleven minutes. The agent eventually returned an answer. Nobody noticed until the monthly reconciliation. Median run cost is 4 cents.

**Clarify.** Was the run successful? Is it one run or a pattern - how many runs exceeded 10× the median in the last month? Which agent and which tenant? What is the step cap and the cost budget (I expect the answer to be "there isn't one")? Did anything deploy that week?

**Isolate.** I pull the trace and look at four things in order:

1. **Step count.** If it ran 200 steps, this is a loop or a no-termination problem (Q18, Q162). If it ran 25 steps and still cost 380 dollars, the cost is per-step, which is a very different problem.
2. **Tokens per step.** A 25-step run costing 380 dollars means roughly 150k+ input tokens per call. That points at a huge tool result sitting in the context and being re-sent every step (Q41), or at the quadratic growth having gone unmanaged (Q227).
3. **Cache hit rate.** If it is near zero on a long run, something in the prefix is varying and every call paid full price (Q229).
4. **Sub-agent fan-out.** If the supervisor spawned sub-agents that spawned sub-agents, the multiplication is there and no shared budget stopped it (Q101).

In the trace I find: a document-fetch tool returned a 180,000-token contract because the caller had no `limit`, the agent then re-read sections by re-calling the tool with slightly different arguments 40 times (duplicate calls that were never detected), and the context sat at 200k tokens from step 6 onward. Cache was fine; the problem was that 200k tokens of *cached* input at 40 steps is still real money, and the output tokens on a reasoning model at each step were not cached at all.

**Decide.** Two classes of fix, and I want both but in a specific order:

- **Immediate, today: bound the damage.** A per-run cost budget checked before every model call (Q233), a step cap, and a hard token cap on tool results (Q41). None of these require understanding the root cause, and they cap every future instance of every variant of this bug. **This is the point I would make loudest** - I do not need to know the cause to stop the bleeding.
- **This week: fix the cause.** Bound the document tool's output with pagination and a `total` field; add duplicate-call detection returning a synthetic observation (Q23); add a `fetch_document_section` tool so the agent can drill in without pulling the whole thing.

**Execute.**

1. Ship the per-run budget (0.80 dollars for this agent, ~20× median) and step cap (12) behind a flag, on today. Terminate with `budget_exceeded` and a partial answer, not an error (Q30).
2. Add the platform-level tool output cap - 2,000 tokens with head/tail truncation and an explicit truncation marker.
3. Add duplicate detection.
4. Add real-time per-run cost telemetry with an alert at 10× p99, so the next one pages someone in two minutes rather than surfacing in a monthly report (Q222).
5. Re-run the affected conversation type through the eval set to confirm the caps do not hurt success rate (Q236).
6. Query the last 90 days for other runs over 10× median and classify them - I expect to find a handful of the same pattern and possibly a second, different one.

**Reflect.** The lesson I would state: **cost is a safety property in an agent system** and needs the same treatment as a permission - enforced in code, defaulted conservatively, monitored in real time (Q163). The organizational failure is that a single request could consume unbounded resources and nobody would know for thirty days. I would add cost-per-run p99 and cost-per-successful-task to the release gate (Q209), so a future change that reintroduces this is caught before production.

---

### S2. The agent reported success and did nothing

> An internal ops agent has been closing tickets for three weeks with a 96 percent "success" rate. A team lead notices that a configuration change the agent reported as applied was never applied. On inspection, roughly one in eight "successful" runs performed no side effect at all.

**Clarify.** How is success currently determined - is it the model's own statement? Which tool should have been called? Do the traces show the tool being called and failing, or never being called? Is there a side-effect ledger at all? How many runs are affected and over what period - is this since a deploy?

**Isolate.** The critical question is whether the tool was called. Three distinct scenarios, distinguishable from the trace in minutes:

1. **The tool was never called.** The model produced a completion message describing the work. This happens when the prompt emphasizes helpful summaries, or when the task looks like a writing task (Q168).
2. **The tool was called and failed, and the error was swallowed or too vague**, so the model summarized optimistically (Q37).
3. **The tool was called and succeeded as a no-op** - the update matched existing values, or the filter matched nothing, and the tool returned `{"status": "ok"}` regardless (Q168).

I find a mix of (1) and (3): the tool returns `ok` for a zero-row update, and separately the agent sometimes skips the call entirely on requests where the desired state description is long.

**Decide.** The root cause is architectural, not a prompt bug: **the model is the reporter of its own effects**, and nothing verifies. So:

- **Contradiction check in code**: a run may not terminate with `completed` if it claims an action that does not appear as a succeeded entry in the side-effect ledger. Deterministic, cheap, total (Q168).
- **Post-condition verification**: after a mutating run, re-read the entity and assert the expected state (Q65). This is the control that catches all three scenarios.
- **No-op detection at the tool layer**: return `"no rows updated - values already matched"` rather than `ok`, so the agent and the ledger both see reality.
- **User-facing reporting rendered from the ledger**, not from the model's narrative (Q142).

**Execute.**

1. Add the side-effect ledger if it does not exist - intent before dispatch, outcome after (Q148). This is the prerequisite for everything else.
2. Ship the no-op detection in the tools (a day of work across four tools).
3. Ship the contradiction check as a hard gate on run completion; runs failing it terminate as `verification_failed` and escalate to a human.
4. Add post-condition assertions for the three highest-value mutating tools.
5. **Backfill**: query the last three weeks for runs marked successful with no corresponding side effect, and produce the list for the ops team to re-run. This is the part the business cares about most.
6. Change the success metric on the dashboard from "run completed" to "run completed **and** verified", and expect the number to drop from 96 percent to something honest.

**Reflect.** Two lessons. First, **never let the model report its own effects** - the action log is the truth (Q168). Second, and more uncomfortable: the 96 percent metric was measuring the wrong thing for three weeks, and nobody questioned it because it was reassuring. I would add "what does this metric actually assert?" to the review checklist for any agent metric, and make verified-success the only success metric that appears on a dashboard.

---

### S3. Quality degraded overnight with no deploy

> Task success on a customer-facing agent drops from 88 percent to 71 percent over about six hours. No deploy went out. The team's first theory is a model provider incident, but the provider status page is green.

**Clarify.** Is the drop uniform or concentrated - by task type, tenant, region, time of day? What do the leading indicators show: steps per run, tool error rate, duplicate rate, cache hit rate, termination mix (Q207)? Did anything change that is *not* our deploy - a tool provider, an index rebuild, a config change, a feature flag, a data migration?

**Isolate.** "No deploy" is rarely true in an agent system, because so many things change behavior without a deploy of *your* service (Q156). I would check, in order of likelihood:

1. **A tool provider changed.** A dependency team shipped a schema change, a new field, a changed description, or a subtly different result format (Q43, Q110). This is the most common cause and it produces exactly this signature.
2. **The model changed under a stable alias.** Providers update models behind aliases; the status page will not mention it. Check whether `gen_ai.response.model` in the traces changed (Q253) - which is why you record it.
3. **A retrieval index rebuilt** with a different configuration, so the agent's knowledge tool returns different results (`09-rag`).
4. **Traffic mix shifted** - a marketing campaign brought a different population of questions, and the agent is not worse, it is being asked harder things (Q205).
5. **A downstream dependency degraded rather than failed** - slower, partial results, silently truncated responses (Q165).
6. **Prompt cache hit rate collapsed**, which would indicate something changed in the prefix.

In the traces, steps per run rose from 5.2 to 8.9 and tool error rate on one tool rose from 0.4 percent to 6 percent, with a new error class. That is a dependency change, not a model change.

**Decide.** Confirm with the owning team, then decide between: roll their change back (fastest if they can), adapt our tool adapter to the new shape (a day), or degrade gracefully by removing the tool from the set until fixed (immediate, with a quality cost).

**Execute.**

1. Contact the tool owner with the evidence - the error class, the timestamp, the rate. Evidence makes this a five-minute conversation instead of an argument (Q99).
2. In parallel, ship a tolerant adapter or remove the tool, whichever is faster, so users stop suffering while ownership is sorted.
3. Add the failing case to the eval set (Q199).
4. **Add a schema-drift check**: snapshot the tool schema at release and fail closed when the live schema differs (Q110). This converts a silent quality regression into a loud, immediate alert.
5. Add contract tests owned by the provider and run continuously (Q247), and register us as a consumer so their pipeline tells them who they break.

**Reflect.** The systemic issue is that **an agent's behavior depends on things outside its own release**, and the organization had no mechanism to notice them (Q253). The fixes are: version-pin everything into a release descriptor (Q248), snapshot and diff schemas, run contract tests continuously, and maintain a consumer registry. I would also note that the leading indicators - steps and tool error rate - moved *before* success rate did, and if they had been alerted on, this would have been a 40-minute incident instead of a 6-hour one (Q217).

---

### S4. The agent leaked one customer's data to another

> A support agent responding to customer A included details of customer B's order in its answer. One confirmed case, reported by the customer. The team's initial view is "a model hallucination".

**Clarify.** Do we have the full trace including tool arguments and results? Was customer B's data in the context at all? What is the tenancy/permission model for the tools - do they filter by principal? Is there any caching in the path? Is memory enabled? How many other runs might be affected - and this is the question I would ask first, because scoping the exposure is the priority over understanding it.

**Isolate.** "The model hallucinated another customer's order id" is almost never the answer - models invent plausible ids, not real ones belonging to a real other customer. So the data was **in the context**, and the question is how it got there. Candidates:

1. **A tool returned unfiltered results** - the search did not apply the principal's tenant/customer predicate, so it returned matches across customers (Q242).
2. **A cache without a tenant in the key** - a semantic cache, a tool-result cache, or a retrieval cache serving customer A a result computed for customer B. **The most commonly missed isolation gap** (Q188).
3. **Memory leakage** - a fact learned in B's session surfaced in A's, because memory scoping was per-agent rather than per-user (Q87).
4. **Session or context bleed** - a conversation state store keyed incorrectly, or a shared mutable object in a concurrency bug.
5. **The confused deputy** - the agent using a broad service credential, and the tool authorizing the *service* rather than the user (Q178).

I check the trace: the tool result contains B's order, so the tool returned it. Then I check whether the tool filters by principal - and find that it filters by an `customer_id` **parameter supplied by the model**, which the model populated from a partially-matching search result.

**Decide.** This is a serious authorization defect, not a model defect. The immediate actions are containment and scoping; the fix is architectural.

**Execute.**

1. **Contain**: disable the affected tool or the agent, immediately, pending the fix. Cost of downtime is far lower than another leak.
2. **Scope the exposure**: query all runs where a tool result contained an entity not belonging to the requesting principal. This is only possible with full tool-result logging (Q191) - if we do not have it, that is finding number one. Report the count to security and legal within the disclosure window.
3. **Fix**: the customer scope comes from the **authenticated principal in the security context**, never from a model-supplied argument (Q242). Remove the parameter entirely; the tool derives it. Enforce in the dispatcher, and again at the system of record (Q109).
4. **Audit every other tool** for the same pattern - I would expect to find more, because this is a design habit rather than a one-off.
5. Add a **cross-tenant leakage test** to the regression suite: a run for user A asserting that no result contains an entity belonging to B (Q188).
6. Audit all caches for tenant in the key, structurally (a typed key object, so it cannot be forgotten).

**Reflect.** The lesson to state plainly: **anything the model supplies is an untrusted proposal, and identity is never a model output** (Q8, Q242). The organizational lesson is that a security review of the tool contracts would have caught this before launch, and I would add "which parameters carry authorization meaning?" as a mandatory review question for every tool (Q46). I would also push for the full-fidelity logging of tool results as a security requirement, because without it, scoping this incident would have been impossible (Q191).

---

### S5. A web page took over the agent

> A research agent that browses and summarizes public pages started creating tickets containing internal document contents. Investigation shows a page it visited contains hidden text instructing it to do so.

**Clarify.** What tools does this agent have, and which of them can write or communicate externally? Does it have access to internal documents *and* browse untrusted pages *and* create tickets - i.e. all three legs of the trifecta (Q183)? Where do those tickets go, and who can read them? How many runs visited that page or similar ones? Is there any content sanitization today?

**Isolate.** This is textbook **indirect prompt injection** (Q128), and the mechanism needs no investigation - the model cannot distinguish instructions from data, and the page's text entered the context as data and was followed as instruction (Q177). What *does* need investigation:

1. **The capability set that made it damaging.** The agent has private-data read, untrusted-content exposure, and external communication in one context. That is the design defect (Q183).
2. **The exfiltration path** - where the tickets land and who can read them. That determines whether this is an internal embarrassment or a disclosure.
3. **The scope** - how many runs, which pages, what data. Requires full tool-result logging (Q191).
4. Whether the page was targeted at us (a real attack) or generic injection bait, which changes the security response.

**Decide.** The critical framing for the interviewer: **you do not fix this by detecting the injection** (Q190). Detection is evadable and this will recur in a form the classifier does not catch. You fix it by making a successful injection useless - a topology change.

**Execute.**

1. **Immediate containment**: disable ticket creation for this agent, or restrict tickets to a private project no external party can read. Minutes, not days.
2. **Scope and report**: enumerate affected runs and the data involved; engage security and follow the disclosure process.
3. **Split the agent** (Q185, Q95): an unprivileged **reader** with browse-only tools, no internal document access, no write tools, whose output is a **validated structured extraction** - not raw page text. A separate **privileged agent** that receives only the structured object and never sees page content.
4. **Egress allow-listing**: tickets only in private projects, no external watchers, no rendered external images or links in outputs (Q184, Q189).
5. **Taint tracking**: any run that has ingested untrusted content drops to read-only for the remainder, or requires approval for consequential actions (Q185).
6. **Add a red-team injection suite** to the release gate, with our own injected pages, and measure the pass rate as a published metric (Q189).
7. Add injection **detection** as a monitoring signal - not a gate - so we know when we are being probed (Q190).

**Reflect.** The sentence I would want on record: *you cannot prevent injection; you make it useless* (Q128). The architecture where untrusted content and privileged capability share one context is the defect, and the fix is structural separation. I would also raise that this agent passed a design review, and add "does any single context hold all three legs of the trifecta?" as a mandatory question in the agent review checklist (Q189).

---

### S6. Every run is hitting the step cap

> After a change to the tool set, the fraction of runs terminating on the step cap goes from 3 percent to 34 percent. Success rate falls 9 points. The change added three tools and edited two descriptions.

**Clarify.** Which tools were added and which descriptions edited? Did the selection eval run before this shipped (Q52)? What does the *trajectory* look like on capped runs - repetition, diverse flailing, granular progress, or incoherence (Q18)? Is the increase uniform across task types or concentrated?

**Isolate.** The four-way classification of the last ten steps in capped runs is the fastest diagnostic (Q18):

- **Repetition** → duplicate calls, uninformative results.
- **Diverse flailing** → the agent cannot find a route; possibly the wrong tools are being selected.
- **Granular progress** → over-decomposition; the new tools are too fine-grained (Q66).
- **Incoherent** → context degradation over length.

I find diverse flailing plus repetition, and a specific pattern: the agent alternates between the new `lookup_record` tool and the existing `search_orders`, because the new tool's description ("look up information about a record") is generic enough to attract nearly every query (Q53). It returns nothing useful for order queries, the agent retries with `search_orders`, gets a result, then tries `lookup_record` again for the next field.

**Decide.** This is a tool-selection interference problem (Q44), and there are three levers: fix the descriptions, remove the tool, or route deterministically. I would fix the descriptions first because it is reversible and fast, but I would also restore the step-cap behavior immediately.

**Execute.**

1. **Roll back the tool-set change** to restore service, since we have a clean rollback via version pinning (Q248). Ten minutes.
2. Build a **selection eval** if one does not exist - 200 cases with labelled correct tools, plus a confusion matrix (Q52). This should have been the gate.
3. Rewrite the descriptions with explicit boundaries and cross-references: `lookup_record` gains "Do NOT use for orders - use search_orders" and a specific scope; `search_orders` gains the symmetric clause.
4. Re-run the selection eval, look at the confusion matrix specifically for the `lookup_record`/`search_orders` pair, and only ship when it is clean.
5. Add **duplicate-call detection** with a synthetic nudge, which would have converted this loop into a recovery (Q23).
6. Add **step-cap rate and selection accuracy to the release gate**, so a tool change cannot ship without them (Q209).

**Reflect.** The lesson: **adding a tool is a model-behavior change, not an additive deployment** (Q44). It needs the same evaluation as a prompt change, and specifically it needs measurement of selection accuracy on the tasks that use the *other* tools. I would also note that the step-cap rate moved before success rate did and would have caught this within minutes if alerted (Q217).

---

### S7. A resumed run refunded twice

> A worker crashed mid-run. The run resumed on another worker and issued a second refund for the same order. A customer received 98 pounds instead of 49.

**Clarify.** Is there a side-effect ledger, and what did it show for that step? Are idempotency keys used, and are they deterministic or random? Was the refund API called with an idempotency header? Did the resume re-prompt the model, or execute from state? Could two workers have resumed the same run concurrently?

**Isolate.** Four candidate mechanisms, and they are distinguishable from the ledger (Q150):

1. **No pre-write.** The ledger recorded the effect only *after* success, so a crash between dispatch and write left the step looking pending. On resume it re-executed.
2. **Random idempotency key.** The retry generated a new key, so the downstream service treated it as a new refund.
3. **Model re-decision.** The resume rebuilt the context and let the model choose again; it re-emitted the refund call, and nothing in code recognized it as already done.
4. **Concurrent resume.** Two workers both picked up the run, with no lease.

I find (1) and (3) together: outcome-only recording, and a resume path that re-runs the loop from the reconstructed context rather than from the plan's step statuses.

**Decide.** All four fixes are cheap and I would ship all of them, because they are defence in depth on a class of bug that causes real financial harm.

**Execute.**

1. **Two-phase recording**: write `intended` with a deterministic idempotency key before dispatch, update to `succeeded`/`failed` after (Q148). Any step left `intended` after a crash is **reconciled**, not repeated - query the refund service by key before deciding (Q39).
2. **Deterministic keys** derived from `(run_id, step_index, canonical_args)`, stored with the intent, and **passed through to the payment provider's idempotency header** so the downstream service also dedupes (Q38).
3. **Execute from state on resume**: completed steps are skipped by the runtime; the model is never given the opportunity to re-propose a completed action (Q150).
4. **A unique constraint on the idempotency key** in the database, so the store enforces it even if the code is wrong (Q243).
5. **A lease** (`SELECT ... FOR UPDATE SKIP LOCKED` or a `locked_until` column) for exactly-once ownership (Q159).
6. **Reconciliation and alerting**: a daily job comparing refunds issued to the ledger, alerting on duplicates - so the next one is caught in hours, not by a customer (Q146).
7. Refund the customer's overpayment and check for other affected runs.

**Reflect.** The framing: **an agent run is a distributed, resumable, side-effecting process**, and everything we know about exactly-once from `03-microservices` applies (Q10). The specific lesson is that **outcome-only recording is not enough** - you must record intent before acting, or "did it happen?" is unanswerable. I would add "what happens if the process dies immediately after this line?" as a review question for every mutating tool call.

---

### S8. Approvals are a rubber stamp

> An agent proposes financial actions and a human approves each one. The approval rate is 99.4 percent. An audit finds that 2 percent of approved actions were incorrect and should have been caught.

**Clarify.** What does the approver see - the model's summary or the rendered action (Q142)? What is the time-to-decision distribution? How many approvals does each person handle per day? Were the incorrect ones distinguishable from the correct ones at approval time - i.e. was the information present and ignored, or absent?

**Isolate.** Two distinct failures, and the audit tells us which:

1. **The gate is theatre.** The approval rate is so high that approvers have learned the prior is "fine" and stopped reading. The time-to-decision distribution will show a mode under two seconds (Q136).
2. **The artifact is wrong.** Approvers were shown the model's prose description rather than the computed action, so even careful reading could not catch the error (Q142).

Checking the data: median decision time 1.8 seconds, and the approval UI renders a model-written summary. **Both** failures are present, and the second is the more serious because it means diligence would not have helped.

**Decide.** The counter-intuitive fix is **fewer approvals, not more diligence** (Q138). Volume is inversely related to attention, so reducing the count restores it - and simultaneously the artifact must be corrected.

**Execute.**

1. **Render the approval from the structured action parameters, in code** - the exact amount, the exact entity, the reversibility, and a computed impact for bulk actions (Q139). Never model prose. This is the primary fix.
2. **Risk-tier the actions** (Q134): auto-execute the low-value reversible ones with post-hoc sampled review; hard-approve the high-value or irreversible; use anomaly triggers for the middle. Expect approval volume to fall by 80-90 percent and the base rate of genuinely-uncertain cases to rise correspondingly.
3. **Instrument the gate**: time-to-decision, whether evidence links were opened, rejection reasons categorized (Q206).
4. **Measure the catch rate directly** by injecting known-bad proposals with the team's knowledge and consent - the only real measurement of whether the gate works.
5. **Post-hoc sampled review** of auto-executed actions, producing a measured error rate with confidence intervals.
6. **Reconciliation and a reversal path**, so errors that get through are detected and corrected within a day (Q146).

**Reflect.** The lesson: **a control that is never triggered is not a control** (Q136). Automation complacency is the default outcome of a high-approval-rate gate, and the design must account for human factors rather than assuming vigilance. I would also make the point that blaming the approvers would be both unfair and useless - they were shown a false artifact and given more decisions than attention allows, which is a design failure on both counts (Q142).

---

### S9. Two agents fighting over a ticket

> Customers receive dozens of duplicate notification emails. Investigation shows a ticket being updated 40 times in ten minutes. Two different agents, built by two different teams, are each reacting to the other's writes.

**Clarify.** Which agents touched the entity, and in what order? Do we have actor attribution on writes (Q192)? Is there a shared correlation id? How many entities are affected? Do either team's tests cover the other's agent?

**Isolate.** This is an **emergent multi-agent failure through shared state** (Q175), and the reason nobody found it earlier is that neither team's traces show anything wrong - each run is individually correct.

The finding mechanism is the important part of the answer: **entity-centric observability**. Indexing actions by the entity they touched rather than by the run makes the ping-pong immediately visible: agent A writes a triage note, agent B reads the note and writes an escalation flag, agent A reads the flag and re-triages. Neither agent filters out changes made by another agent, and each write triggers a customer notification.

In a run-centric view this is invisible - which is exactly why the entity view is the answer, and why I would build it if it does not exist.

**Decide.** Immediate containment, then a structural fix, then a governance fix - because this will recur with a different pair of agents otherwise.

**Execute.**

1. **Contain**: disable one of the two agents' write path immediately (the less critical one), and suppress duplicate notifications at the notification layer. Minutes.
2. **Actor-aware filtering**: each agent ignores changes whose actor is another agent, or at minimum does not re-trigger on them. Fixes this instance.
3. **Rate limit writes per entity** - a hard cap of N writes per entity per hour by agents, enforced at the platform, which bounds every future variant of this (Q173).
4. **Single writer per entity type** where the domain allows it: one agent owns ticket status, the other proposes rather than writes (Q100). The strongest structural fix.
5. **Actor attribution on every write** - agent, version, run, principal (Q192) - which is the prerequisite for the entity view and for any future investigation.
6. **An agent registry recording which agents write which entity types** (Q117), with overlaps flagged at design time and a review required.
7. **Entity write-rate anomaly alerting** as a standing detective control.

**Reflect.** The lesson is that **agent systems have emergent behavior across runs and across teams, and run-centric observability cannot see it** (Q175). The organizational point is sharper: neither team did anything wrong by their own specification, so the failure belongs to the platform, which allowed two agents to write the same entity type without anyone knowing (Q99). I would take the registry and the entity-centric view as platform deliverables, not team ones.

---

### S10. It worked in staging

> An agent evaluated at 91 percent success offline launches and measures 63 percent in production. The team wants to roll back and "fix the prompt".

**Clarify.** How was the offline set built - hand-authored or from production traffic? What environment did it run against - fixtures or real tools? How is production success measured, and is it the same definition? Is the gap uniform or concentrated? Have we sampled production inputs and run them through the offline harness?

**Isolate.** The single most useful diagnostic is to **take 50 real production inputs and run them through the offline harness** (Q205). Two outcomes:

- **They also fail offline** → the gap is **input distribution**. The eval set does not represent real traffic - the most common cause by a distance.
- **They pass offline but fail in production** → the gap is **environment**: real tools are slower, paginated, rate-limited, returning messier data, and the error paths were never exercised (Q200).

Running it, I find both: 30 percent of the failures are input distribution (real requests are ambiguous, multi-intent, and often out of scope in ways the eval set never contains), and the rest are environment (a tool that returns 200 results in production returned 5 in fixtures, so the agent's context blows up and it loses the thread).

There is also a third contributor worth naming: **success is defined differently**. Offline it is assertions passing; in production it is measured by escalation and user correction, which is a stricter bar (Q196).

**Decide.** Rolling back is right if users are being harmed, but "fix the prompt" is the wrong next step - the prompt was tuned against an eval set that does not represent reality, so tuning it further optimizes the wrong target. **Fix the evaluation first.**

**Execute.**

1. **Roll back or reduce exposure** to a small canary while working (Q252).
2. **Rebuild the eval set from sampled production traffic** - 150 cases drawn from real inputs including the out-of-scope and ambiguous ones (Q199).
3. **Rebuild fixtures from recorded production tool responses**, not hand-written ones, and add fault injection: latency, errors, empty results, large results (Q200).
4. **Align the success definition** offline and online, or at least measure both consistently so the ratio is meaningful.
5. **Hold out a portion** of cases never used for tuning, to detect overfitting (Q205).
6. **Re-baseline**, then fix the actual defects the new eval reveals - which in this case are result bounding (Q41) and handling of out-of-scope requests (an escalation path, Q140).
7. **Track the offline/online ratio over time** as a standing metric; a stable ratio is healthy, a widening one is drift.

**Reflect.** The lesson: **an eval set built from imagination measures imagination** (Q205). The fix is a pipeline from production traces to eval cases, run continuously, so the set tracks the traffic. And the cultural point: a large offline/online gap is not a failure of the agent, it is a failure of the evaluation - and treating it as the former leads to months of prompt tuning that does not help.

---

## Part B - Design walkthroughs

These map to Q261-Q266. Spend 25-35 minutes on each. Say the requirements and the constraints out loud before drawing anything; interviewers are testing whether you scope before you design.

### S11. Customer support agent for 2 million customers (Q261)

> Read account data, issue refunds up to a limit, escalate what it cannot handle. 2 million customers, roughly 40,000 conversations a day, peak 3× average. Must not exceed refund policy. Must be auditable.

**Requirements I would establish first.** What fraction of contacts do we expect to deflect (this sets the value)? What is the refund limit and who sets it? What is the acceptable latency - are we replacing a chat queue with a 30-second wait, or an email queue with a 4-hour SLA? What happens when the agent is wrong - who bears the cost? Is there a human support team to escalate to, and what is their capacity? Which regulations apply (financial services rules, GDPR, consumer protection)?

**Scope decision.** I would target **deflection with clean escalation**, not full autonomy. The product goal is "resolve the routine 60 percent completely, escalate the rest with the work already done" (Q140). This is a far better business case than a 95 percent autonomy target, and it is achievable.

**Architecture.**

1. **A deterministic front door.** Intent classification and routing before the agent: order status, refund request, account question, complaint, out-of-scope. Recognizable intents with a single obvious first step get their context prefetched unconditionally (Q30, Q54). This alone removes 2-3 steps from every run.
2. **A single agent with a small, task-shaped tool set** - about 8 tools, named for user intent rather than for our API (Q42): `get_customer_context`, `get_order`, `search_orders`, `check_refund_eligibility`, `issue_refund`, `search_knowledge` (the `09-rag` service, Q258), `escalate_to_human`, `finish`. **Not a multi-agent topology** - I would defend that explicitly (Q90), because there is no trust separation, no genuine parallelism, and no context-isolation argument at 8 tools.
3. **Retrieval as a tool**, with permission filtering inside the service and bounded, cited results (Q258).
4. **Policy in code, not in the prompt** (Q242). Refund eligibility - amount, window, prior refunds on the order, customer tier, one-refund-per-order invariant - is evaluated by a policy service from the authenticated principal and entity state. The model may *propose* a refund; the policy decides whether it is permitted. **Aggregate limits too**, because eleven £95 refunds is the split-transaction attack (Q193).
5. **Approval tiering** (Q134): auto-execute under £50 when policy-clean and non-anomalous; human approval above £200 or on any anomaly signal; between, approve only on anomaly. Expect ~5 percent of refunds to reach a human.
6. **Escalation with a full handover** - the original request, what was found with links, what was done, why it stopped, in the same conversation so the customer never repeats themselves (Q140).

**Controls and bounds.**

- Step cap 10, cost budget ~£0.15, wall-clock 45 s with a degradation ladder (Q30).
- Per-customer refund caps per day; per-agent daily total refund value cap with a circuit breaker (Q173, Q146).
- Kill switch per tool and per agent.
- Complete audit log with both identities, the evidence shown, and the policy version (Q144, Q192).

**Scale arithmetic.** 40,000 conversations/day ≈ 0.5/s average, ~1.5/s peak. At 6 steps and 45 s per run, peak concurrency is ~70 runs - trivially handled by a container tier with virtual threads (Q235, Q251). Model spend: ~6 steps × ~4k average context with caching, roughly £0.05-0.10 per conversation, so **£2,000-4,000/day**, against a support cost per contact of several pounds - the business case is comfortable, and I would present it that way (Q225).

**Durability.** Conversations are interactive and short, but refunds are irreversible - so **Tier B** (Q160): Postgres state, per-step checkpoints, intent-before-dispatch side-effect ledger, deterministic idempotency keys, unique constraint on the key (Q243). Approval waits push a conversation into a suspended state resumable across deploys (Q143).

**Evaluation.** 200 cases from production transcripts with state assertions, forbidden-action assertions (never refund above policy, never touch another customer's order), trajectory assertions, and a red-team suite (Q199). Gate on success, cost per successful task, step-cap rate, and 100 percent on safety assertions (Q209).

**Rollout.** Shadow mode (propose, humans compare) → suggest-to-agent (a human support agent sees the proposal and clicks) → auto for read-only answers → auto for refunds under £50 → widen on measured error rates (Q266).

**What I would flag as the risk:** not the model - **the policy encoding**. Refund policy in most companies is partly written and partly folklore, and the project's hard work is making it explicit enough to put in code. I would budget for that discovery explicitly.

---

### S12. Alert triage and remediation agent (Q262)

> Triage alerts, investigate using observability tools, propose remediation. Currently 400 alerts a day to a rotating on-call, most of them noise.

**Requirements.** What fraction of alerts are actionable today (usually 5-15 percent)? What is the cost of a missed real alert versus an unnecessary page? Which systems can it read, and can it *act*? What is the on-call's tolerance for an agent that is sometimes wrong? Is there a runbook corpus?

**The framing I would lead with:** the value here is **not** autonomous remediation - it is **enrichment and triage**, turning 400 pages into 40 with a completed investigation attached. That is a large, safe, measurable win, and it is achievable now; autonomous remediation is a later phase gated on measurement (Q2). I would say this explicitly because the stakeholder usually asks for the latter (Q14).

**Architecture - and this is where a topology is genuinely justified** (Q104):

1. **Deterministic pre-processing**: dedupe, correlate by service and time window, suppress known-noise patterns, group related alerts. A meaningful fraction of the 400 disappears here with no model involved (Q54).
2. **A supervisor with parallel read-only investigators** - metrics, logs/traces, recent deploys and changes, and prior similar incidents. Parallel because each takes 3-8 s and they are independent, so 20 s serial becomes 8 s (Q93). Read-only because they consume **untrusted content** - log lines, alert payloads, user-submitted text - and must not hold write tools (Q185).
3. **A severity judgement step** with a reasoning model, using the structured findings.
4. **Remediation as a *proposal*, never an action**, in phase 1: a suggested runbook step with the evidence, presented to the on-call engineer.

**Trust separation is the design's spine.** Investigators read attacker-influenceable content; the actor (which later may restart a service or scale a deployment) never sees raw log text, only validated structured findings (Q183). I would bring the red-team injection result to justify this rather than asserting it (Q104).

**Controls.** Step cap 12 per investigator, global run budget; read-only IAM roles per investigator (Q254); alert-level rate limits so an alert storm does not fan out into thousands of model calls (Q174); and a per-run cost budget, since alert storms are exactly when cost runs away.

**Evaluation.** This one has an unusually good signal: **historical alerts with known outcomes**. 300 past alerts with their eventual resolution gives a real labelled set, and the headline metric is **false-close rate** - alerts the agent dismissed that were real. That is the number the on-call team cares about and the one I would gate on, at a threshold far stricter than overall accuracy (Q196).

**Phasing toward action.** Phase 2: propose remediation with one-click human execution. Phase 3: auto-execute a small allow-list of reversible, low-blast-radius actions (restart a pod, scale a replica set) with notification and easy undo, within rate caps (Q173). **Never** auto-execute anything irreversible or data-affecting. Each phase gated on measured error rates from the previous one.

**What I would flag:** the agent will be measured by the on-call engineers' trust, which is lost far faster than it is gained. One false-close on a real incident sets the project back months. So I would optimize for **recall on real incidents at the cost of precision** early on - it is better to escalate too much than to dismiss one real page.

---

### S13. Document processing at 200,000 documents a day (Q263)

> Extract structured data from documents, with human review below a confidence threshold. 200,000 documents a day.

**Requirements.** What documents and what fields? What is the cost of an extraction error, and is it detectable downstream? What is the human review capacity? What accuracy does the current process achieve? Is there a system of record to validate against?

**The first architectural point, and the one that matters most: this is mostly not an agent problem** (Q3, Q5). 200,000 documents a day at a fixed extraction task is a **pipeline** - parse, classify, extract, validate, route - with model-powered steps. An agentic loop is justified only for the residue: documents that fail validation, unusual layouts, or cases needing cross-document reasoning. I would open with that, because designing this as 200,000 agent runs a day would be roughly an order of magnitude more expensive and less reliable.

**Architecture.**

1. **Ingestion and parsing** (`09-rag` Category 2 territory): layout-aware parsing, OCR where needed, classification into document types.
2. **Deterministic extraction where the layout is known** - templates and rules for the high-volume standard forms. Cheapest and most reliable; often covers the majority.
3. **Model extraction with constrained decoding into a typed schema** for the rest - a single call, not a loop, for the common case (Q54).
4. **Validation in code**: schema, field formats, arithmetic consistency (do the line items sum to the total?), cross-reference against the system of record (does this supplier exist?). **This is where confidence actually comes from** - not from the model's self-reported certainty, which is not trustworthy (`08-genai` Q73).
5. **An agentic path for the residue only**: documents failing validation get a bounded loop with tools to re-read specific regions, look up reference data, and reconcile discrepancies. Maybe 5-10 percent of volume.
6. **Human review queue** for what remains uncertain, prioritized by value and by uncertainty.

**Confidence and routing.** The threshold decision is a **cost-of-error versus cost-of-review** calculation, and I would present it as such: if review costs £0.40 per document and an error costs £30 downstream, the break-even error rate is about 1.3 percent, which sets the threshold. Calibrate the confidence signal against labelled outcomes rather than trusting it a priori.

**Scale arithmetic.** 200,000/day ≈ 2.3/s average. This is **batch work with no user waiting**, so: batch model APIs at ~50 percent discount, spot compute, aggressive parallelism (Q237). At maybe £0.01-0.03 per document for the model path, that is **£2,000-6,000/day**, and the deterministic-first design is what keeps it there rather than 5× higher.

**Human review economics.** If 10 percent go to review at 30 seconds each, that is 20,000 reviews/day ≈ 167 person-hours ≈ 21 people. **The review threshold is therefore a staffing decision**, and the most valuable engineering work is anything that moves documents out of review - which argues for investing in validation rules rather than in prompt tuning (Q206). I would make that trade explicit to the stakeholder.

**Feedback loop.** Every human correction is a labelled example: it feeds the eval set, identifies systematically-hard document types, and justifies new deterministic rules (Q199). Over time the review rate should fall, and that trajectory is the programme's headline metric.

**Durability and operations.** Per-document idempotency (a document processed twice must not create two records); a dead-letter queue with a triage workflow (Q256); per-document cost tracking; throughput and backlog dashboards.

---

### S14. Coding agent from issue to reviewed pull request (Q264)

> A large repository. Take an issue, produce a pull request that a human reviews.

**Requirements.** How large is the repository, and does it build and test in a reasonable time? What is the test coverage - because that determines whether the agent has a verification signal at all (Q4)? What fraction of issues are well-specified? What is the acceptance bar - does the PR need to be mergeable, or a useful starting point?

**The property that makes this work, and I would lead with it:** coding is one of the few agent domains with a **strong external verifier**. The code compiles or it does not; the tests pass or they do not. That verification signal is what lets the loop self-correct, and it is why coding agents work better than most (Q65). **Where the tests are weak, the agent will be weak**, and I would say that up front because it sets expectations and often reveals that the highest-value investment is test coverage rather than the agent.

**Architecture.**

1. **A persistent sandbox per run** with the repository checked out, dependencies pre-installed via a warm pool, no network beyond an internal package mirror, resource limits, and destruction at run end (Q123, Q132). Persistence within the run is essential - the agent builds state (a working tree, a running test process) across steps.
2. **Tools shaped like a developer's actions**, not like filesystem primitives (Q42): `search_code` (semantic plus lexical over the repo - this is a `09-rag` problem and worth doing properly), `read_file(path, range)`, `edit_file` (structured diff application, not free-form rewriting), `run_tests(selector)`, `run_build`, `git_diff`, `open_pull_request`. Bounded output on all of them - a full test log is tens of thousands of tokens, so return "48 passed, 2 failed" plus the two failures (Q124).
3. **A plan-then-execute shape** at a coarse grain (Q60): understand the issue, locate the relevant code, make the change, test, iterate, summarize. Bounded interleaved loops within each phase.
4. **Context management is the hard engineering problem.** A large repository does not fit; the agent must search and read selectively, and the context grows fast with file contents (Q227). Aggressive result bounding, externalized file contents by reference, and compaction at phase boundaries (Q20).
5. **The verification loop as the core**: edit → build → test → read failures → edit. This is where the value is, and the step budget should be spent here rather than on exploration.

**Bounds and safety.** The sandbox is the security boundary and the agent writes only inside it. **The output is a pull request, never a merge** - so the irreversible action does not exist, and human review is structural rather than a gate that can be bypassed (Q173). No production credentials in the sandbox. No package installation from the public internet (the hallucinated-package supply-chain risk is real, Q187).

**Cost and step budget.** Realistically 20-40 steps with large contexts - this is an expensive agent, perhaps £1-5 per attempt, and the right comparison is against 30-90 minutes of engineer time. I would set a step cap around 40, a cost budget, and a wall-clock deadline, with the run producing a partial PR plus a description of what it could not do rather than failing (Q30).

**Evaluation.** Historical issues with their actual merged fixes give a labelled set. Metrics: fraction of PRs that build, fraction that pass tests, fraction merged with no changes, fraction merged after edits, fraction discarded, and reviewer time per PR. **Reviewer time is the metric that determines whether this is valuable** - a PR that takes longer to review than to write is a net negative, and that is a real risk worth naming.

**Where I would start:** narrow, well-specified, mechanical issues - dependency upgrades, adding a test, small well-described bugs with a failing test attached. Success there builds trust for wider scope, and the failure mode (a bad PR) is cheap.

---

### S15. Multi-tenant agent platform for 40 internal teams (Q265)

> 40 teams build agents on shared infrastructure. You own the platform.

**Requirements and the framing.** The first thing I would establish is **what the platform owns versus what teams own**, because everything else follows and because an unclear boundary makes the platform a helpdesk (Q224). My split: the platform owns the **execution substrate and the guarantees** - the loop runtime, durability, budget and cap enforcement, the tool gateway, identity propagation, observability, evaluation harness, and the release mechanism. Teams own their **prompts, tools, task success and cost profile**.

**Core components.**

1. **An agent runtime SDK** providing the loop with all the controls built in - step caps, budgets, deadlines, duplicate detection, compaction, side-effect ledger, approval interception, tracing (Q27). Teams write tools and prompts; they do not write loops. **Uniformity here is what makes everything else possible.**
2. **A tool gateway** as the single enforcement point: authentication, per-user authorization with principal propagation, rate limiting, quotas, output bounding, schema validation, logging, cost attribution (Q118). Agents never call providers directly.
3. **A tool registry** as the control plane: ownership, schemas with versioning and fail-closed drift detection, mutating flags, permissions, data classification, contract tests, approval workflow, usage stats (Q117).
4. **Tiered durability** (Q160): short read-only runs on a light path; runs with side effects on checkpointed Postgres; long runs and human approvals on a workflow engine. Automatic tier selection with a promotion path.
5. **An evaluation platform** (Q210): per-tenant eval sets built from their own traces, a tool simulator generated from their schemas, statistical comparison built in, and platform-level evals for the shared runtime.
6. **Observability** with uniform instrumentation, per-agent and platform dashboards, cost attribution, and an on-call boundary with routed alerting (Q224).
7. **A release mechanism**: the pinned descriptor (model, prompts, tools, policy, limits) built in CI, canaried by run cohort, rolled back atomically (Q248).

**Multi-tenancy.** Namespace isolation for state, tools and traces; **tenant in every cache key, structurally** (Q188); separate execution environments per trust tier; per-team quotas on cost, concurrency and downstream calls so one team's runaway does not degrade others (Q174); and chargeback, which changes behavior more than any guidance document.

**Governance.** Guardrails that are non-negotiable and enforced by the platform: caps, approval interception for mutating tools, principal propagation, instrumentation, an owner and runbook per agent as a precondition for deployment. Plus a review gate for agents that take irreversible actions or read untrusted content (Q189).

**The adoption problem, which is the real risk.** A platform that is slower or more restrictive than doing it yourself gets routed around, and then you have 40 unmonitored agents instead of one platform. So the design principle is that **the compliant path must be the easiest path** (Q46): one SDK call to run an agent, schema generated from typed Java methods, tracing and cost attribution for free, an evaluation harness that takes an hour to adopt, and defaults that are safe *and* fast (warm sandbox pools, prompt caching configured correctly by default). I would measure adoption and time-to-first-agent as platform KPIs.

**Sequencing.** Runtime SDK plus caps plus observability first (immediate safety and visibility value); tool gateway and registry second; durability tiers third; evaluation platform fourth. **Do not build the evaluation platform first**, even though it is the most sophisticated - teams will not adopt a platform whose first offering is more work for them.

---

### S16. Safety, evaluation and rollout for irreversible actions (Q266)

> An agent that will take irreversible actions in production systems. Design the safety, evaluation and rollout process.

**The framing to open with.** The question is not "how do we make it accurate enough" - it will never be accurate enough for irreversibility to be safe on accuracy alone. The question is **"what is the maximum damage, how is it bounded, and how fast would we know"** (Q173). Everything below serves that.

**Step 1 - reduce irreversibility before anything else.** For each action, ask whether a reversible form exists: staged instead of applied, draft instead of sent, soft delete, credit note instead of refund, pull request instead of merge, feature flag instead of config edit. **Every action converted from irreversible to reversible removes a whole column of this design**, and this is where I would spend the first week. The residue is what needs the rest.

**Step 2 - safety architecture** (Q194):

- **Capability allow-list** - explicit registered actions, no generic execution tool.
- **Policy in code** from the authenticated principal and entity state, including **aggregate limits** (Q193).
- **Trust separation** - untrusted content never shares a context with write capability, with taint tracking (Q185).
- **Approval tiering** by reversibility, blast radius, value, anomaly and provenance (Q134), with the UI rendered from the computed action (Q142).
- **Bounds** - per-run, per-user, per-tenant, per-day caps; circuit breakers on aggregate volume and value; kill switches per tool and per agent.
- **Complete audit trail** with both identities and the evidence shown (Q144).

**Step 3 - evaluation before any exposure.**

- 200-300 cases with **state assertions and forbidden-outcome assertions** - the negative assertions matter most here (Q196).
- **Trajectory assertions** as hard gates: never call the write tool before verification, never exceed scope.
- **A red-team injection suite** as a hard 100 percent gate (Q189).
- **k repetitions with statistical comparison** and a stated minimum detectable effect (Q203).
- **pass^k reported**, not just pass@1, because the customer experiences a sequence (Q208).

**Step 4 - staged rollout, each stage gated on the previous stage's measured data.** This is the heart of the answer:

1. **Shadow.** The agent runs on real traffic and **proposes** actions that are recorded but never executed. Humans perform the work as normal. Compare proposals to what humans did. Gate: agreement rate above threshold, zero forbidden-action proposals, on at least 500 real cases. **This stage costs nothing in risk and produces the most valuable data you will ever get**, and teams skip it because it feels slow.
2. **Suggest.** A human sees the proposal and clicks to execute. Gate: acceptance rate, modification rate, and the error rate of executed actions measured by post-hoc audit.
3. **Approve.** The agent executes after human approval, with the approval UI rendered from the action. Gate: approval-decision accuracy from a second-reviewer audit (Q206), plus catch-rate testing.
4. **Auto within a narrow envelope.** Low value, reversible-adjacent, non-anomalous, with notification and one-click undo, under strict daily caps. Gate: measured error rate with a confidence interval, reconciliation showing no unexplained divergence.
5. **Widen the envelope incrementally**, each widening a decision with an owner and a measured basis.

At every stage: a small canary percentage first, cohort-attributed metrics, guardrail metrics with automatic rollback (Q223).

**Step 5 - operate.** Real-time population monitoring with circuit breakers (Q146); post-hoc stratified sampled review producing a measured error rate; daily reconciliation against the system of record; an automated reversal path; and a rehearsed incident runbook - contain, revoke, assess blast radius by entity, reverse, notify.

**What I would present to the approval board.** Not an accuracy figure. A **residual-risk calculation**: at the measured error rate, with these caps, the maximum daily exposure is £X, expected loss is £Y, detection time is Z hours, and reversal is automated for these classes. Compare against the cost of the manual process. **That comparison is what gets approved**, and framing it that way is the difference between a design review that ends in a decision and one that ends in another meeting (Q194).

---

## Part C - Leadership and behavioural

These map to Q267-Q272. There is no scripted answer - the whole point is that they are yours. Prepare each with **STAR-L**: Situation, Task, Action, Result, **Learning**. Two to three minutes spoken, with at least one number and one thing you would do differently.

### S17. An agent or automation you took to production (Q267)

Have ready: what the system did, **which rung of the autonomy ladder you chose and why** (Q2), what you deliberately did *not* automate, the controls you put in place before launch, the rollout stages, and the measured outcome. The strongest version of this story is one where you chose a *lower* rung than you could have and can explain the reasoning.

### S18. A time you argued against an agent (Q268)

The most valuable story in this pack, because it demonstrates judgement rather than enthusiasm. Have ready: what was proposed, the questions you asked that changed the conclusion (Q3), what you built instead, and the comparison - cost, reliability, maintenance - between what was shipped and what was proposed. Include how you kept the stakeholder's support while narrowing the scope (Q14).

### S19. An agent failure in production that you owned (Q269)

Pick a real one with a real consequence - cost, a wrong action, a data exposure, an outage. Structure it as CIDER. Be specific about **what you changed structurally afterwards**, not just what you fixed: the control, the gate, the review question, the metric. Interviewers are listening for whether the fix was systemic or a patch, and for whether you took ownership without either minimizing or over-dramatizing.

### S20. A cost or reliability problem, with numbers (Q270)

Have the before and after: cost per run or per successful task, success rate, p95 latency, step count. Explain the *ordering* of what you did and why (Q238), which item turned out to be the biggest win (it is usually not the one people expect), and what you deliberately did not do because the quality risk was not worth it. The credibility of this story lives entirely in the specificity of the numbers.

**Also prepare Q271** (building evaluation discipline in a team that shipped on demos) and **Q272** (a stakeholder who wanted more autonomy than the system could safely support). Both are about influence rather than engineering: what you measured to make the argument, how you made the risk concrete without being the person who says no, and what you conceded in order to win the important part.
