# AI Agents Cheatsheet

Fast revision. Every claim here is expanded in [answers.md](answers.md); question numbers are the index. Treat every absolute figure as an **order of magnitude to reason with** - frameworks, provider APIs and protocol versions all moved last quarter, and interviewers know it. Show the mechanism and the arithmetic, not the memorized number.

---

## 1. What an agent is

**Agent = the model chooses the control flow at runtime, in a loop, until it judges the task complete** (Q1). Not "it has tools". Everything hard follows from that one property: paths are unenumerable (so you sample, not cover), cost is unbounded (so you cap), the trajectory varies (so you cannot reproduce), and the blast radius is the union of the tool set (Q7, Q10).

**The autonomy ladder** (Q2): fixed prompt → structured output → router → chain → **bounded tool loop** → planning loop → multi-agent → open environment → self-directed. Each rung buys capability with controllability. **Pick the lowest rung that solves the problem.** Most production value is at rungs 3-5.

**The five disqualifying questions** (Q3): can you draw it as a flowchart (yes → build the flowchart); how many real paths (few → router); are actions irreversible and unreviewed (yes → wrong tool); can you write 50 test cases today (no → you cannot evaluate); what is the p99 cost tolerance (none → no).

**Suits an agent** (Q4): data-dependent branching, unbounded solution space, **verifiable intermediate results** (the strongest predictor), cheap recoverable failure. **Predicts expensive failure**: no verification signal, irreversible effects, long horizons (0.95^20 = 36 percent), precise arithmetic, tight latency.

| | Workflow | Router + workflows | Agent loop |
| --- | --- | --- | --- |
| Cost | Predictable | Predictable | **Unbounded without caps**, 3-10× |
| Debuggability | Excellent | Very good | Poor |
| Testability | Paths enumerable | Enumerable | Sampled only |
| Capability | Only what you anticipated | Same | Handles the unanticipated |

**Nondeterminism sources** (Q6): sampling (removable), **batched-GPU float non-associativity** (not removable - why temperature 0 is not deterministic), provider model updates (pin the version), the world moving (not removable), parallel result ordering (impose a canonical order), retrieval (pin the index), context assembly (make it a pure function). Everything except the model can be made deterministic - and should be, so a divergence is attributable.

**85 percent success - shippable?** (Q12) Depends on: what happens in the other 15 percent (silent or visible?), the baseline, and whether failure is detectable at runtime. **The failure distribution matters more than the rate.** And 99 percent per step over 16 steps *is* 85 percent - so the leverage is fewer steps, not prompt tuning.

---

## 2. The loop

**ReAct** (Q15): model → tool call → execute → append **both the model's output and the result** → repeat. Production needs what the paper does not describe: step cap, cost budget, deadline, error feedback, duplicate detection, durable state.

**Termination conditions - a production agent needs all of these** (Q17): model signals done; step cap; token/cost budget; wall clock; no-progress detected; terminal tool error; human interrupt; guardrail trip; context limit; **goal verified by code** (the strongest, and available more often than people use it); cancellation. Each produces a **different outcome status** - `completed`, `max_steps`, `budget_exceeded`, `needs_human`, `blocked_by_policy` - because retry policy and metrics depend on which fired.

**Context growth is quadratic** (Q19, Q227): total input ≈ `n·b + s·n²/2`. Worked: b=2,000, s=800, n=20 → **192,000 tokens**, versus a naive 40,000. Doubling steps quadruples the dominant term.

**Compaction** (Q20): at 60-70 percent of the window, on a task boundary. **Always keep**: system prompt, tool definitions, **the goal verbatim**, structured facts (ids, values), the last few steps, and **what was tried and failed**. Compaction invalidates the prompt cache from that point, so compact rarely and substantially.

**State ≠ context** (Q21). State is durable and structured; **the context is a projection of state, rendered by a pure function under a token budget**. Conflating them makes compaction destructive, resume impossible, idempotency unimplementable and monitoring impossible.

**40 iterations, only the cap stops it** (Q18) - classify the last ten steps as *repetition* / *diverse flailing* / *granular progress* / *incoherent*. That one classification splits the six causes.

**Same tool, same args, three times** (Q23): the result was uninformative, unseen or contradicted expectation. **Do not execute** - return a synthetic observation ("you already called this and got X"). Escalate after 2-3. Duplicate-call rate is a high-signal metric almost nobody tracks.

**Prompt caching** (Q28, Q229): the loop is the ideal caching workload - a long, growing, append-only prefix. 70-90 percent of input cached at ~10 percent of price. **Broken by**: a timestamp or request id at the top, non-deterministic tool ordering, compaction, editing earlier messages, per-user tool sets, TTL expiry during an approval wait. **Rule: append only, never edit.**

**14 steps for a 3-step task** (Q29): tool granularity too fine (the usual cause), missing context forcing exploration, verification loops, over-decomposition, no fast path for the common case. **Step count is the single most actionable agent metric.**

---

## 3. Tool design

**The model sees only the name, the description and the parameter schema** (Q31). The description is the entire specification: what it does, when to use it, **when not to**, what it returns. The "when not to" clause is the most under-used and most effective element.

**Good schema** (Q32): verb-object domain name; few parameters (≤5-7, ≤2-3 required, Q33); flat primitives; **enums over free strings**; formats with an example in the description; a description on every parameter. **Bad**: deep nesting, `oneOf` unions, free-form filter DSLs, mode flags, ids the model cannot obtain.

**What the schema actually enforces** (Q35): **`enum` yes** (constrained decoding - your most valuable feature). `type` mostly. `required` mostly. **`format`, `pattern`, `minimum`/`maximum` - advisory only.** Descriptions are read and often more influential than keywords. **Validate everything yourself**: constrained decoding guarantees the output *parses*, not that it is *valid*.

**Tool returns** (Q36): shaped structured result (best) > natural-language summary > raw API output. Include the ids needed for follow-up (the most common omission). Make state explicit after a write so re-reading is unnecessary. **Bound it always** (Q41): hard token cap, `total` versus `returned` count, filtering pushed into the tool, explicit truncation markers, store-and-reference for big payloads.

**Errors written for a model** (Q37): a machine-readable class, what was wrong with the received value, what a valid value looks like, **what to do next including whether to retry**, no stack traces, bounded length. `PERMISSION_DENIED` without "do not retry" causes five creative retries.

**Idempotency matters more here** (Q38) because the *model* can repeat a call for reasons you did not design. Deterministic key from `(run_id, step, canonical_args)` - **never random**, or resume defeats it. Repeat returns the original result, not an error.

**Granularity** (Q42): specific tools beat one `manage_x(action)` tool, because a mode parameter forces `oneOf` schemas that models fill badly. But shape them by **user intent, not by your API** - one tool per thing a user would ask for.

**Adding a tool degrades unrelated tasks** (Q44) via: selection interference, context dilution, cache invalidation, flatter decision distribution, changed few-shot balance, and "attractive" generic descriptions. **A tool addition is a model-behavior change requiring a full eval run.**

---

## 4. Tool selection at scale

**Selection accuracy degrades with count** (Q47): near-perfect at 3-5, good to ~15-20, weak past 30, unreliable past 50. Causes: superlinear semantic overlap, flatter decision distribution, context dilution, position effects.

**Token cost** (Q48): ~150-300 tokens per tool definition. 50 tools ≈ 10-15k tokens, re-sent every step. **Rule of thumb: past 20-25 percent of the prompt, use retrieval or hierarchy - on quality grounds before cost grounds.**

**Tool retrieval** (Q49): index tools by name/description/examples, hybrid + rerank, top 10-20 per request, core tools pinned. **Retrieve once, not per step** (cache). **New failure mode: the right tool is invisible**, so the agent uses a wrong-but-present one confidently. Needs a `find_tools` escape hatch and recall@k measurement.

**Hierarchy** (Q51): 12 category descriptions instead of 200 tool definitions; deterministic and cacheable; costs a round trip and breaks on cross-cutting tasks.

**Evaluate selection separately from task success** (Q52): top-1 accuracy, per-tool precision/recall, **confusion matrix** (drives description edits), abstention accuracy, argument validity, retrieval recall@k.

**Overlapping tools** (Q53): add explicit negative clauses cross-referencing the sibling by name, differentiate names, make descriptions symmetric, add discriminating enums, few-shot the confusable cases - or **merge them** if you cannot state the boundary in one sentence.

**Do not let the agent choose** (Q54) when a rule decides it, when the criteria are policy, when there is one obvious first step, when a classifier is cheaper, or when it is a pure transformation. Most production agents are mostly deterministic with a small agentic core - that is a success, not a compromise.

**Unknown tool called** (Q56): constrained decoding, registry lookup before dispatch (never reflective invocation), a recoverable error listing near-matches, a per-run cap, `find_tools`. **A rising rate of a specific invented name is a product signal about a missing tool.**

**Dynamic tool sets fragment the cache** (Q57) - bucket by **tool-set fingerprint** (a hundred profiles), not per user (a million). Sort canonically. Do not change the set mid-run.

---

## 5. Planning and reflection

**Planning earns its cost** (Q59) on long horizons, expensive ordering mistakes, human approval of the approach, available parallelism, model routing, and progress tracking. Not worth it under ~5 steps or on genuinely exploratory tasks.

**Plan-then-execute vs interleaved** (Q60): plan-first is cheaper, parallelizable, inspectable, but recovers badly from a bad plan; interleaved adapts every step but is serial and expensive. **Default hybrid: coarse phases (3-6), bounded interleaved loop inside each, re-evaluate at boundaries.**

**Represent the plan as a structured object** (Q61): step ids, `depends_on`, `status`, `result_ref`, `version`. Lives in **state**, not only in the context, so compaction cannot destroy it and a resume can pick it up.

**A plausible plan with an impossible step 3** (Q62): find out earlier by validating steps against the tool registry (pure code), requiring a `tool_hint` per step, running cheap precondition reads up front in parallel, **ordering irreversible actions last**, and giving the planner grounded context rather than expecting it to guess.

**Reflection: trust order is validation > verification > reflection** (Q65). Validation = deterministic code checks (cheapest, strongest). Verification = an independent oracle (tests, compiler, schema, DB query). Reflection = the model critiquing itself with the same distribution that produced the error - catches surface issues, misses what matters, and sometimes talks itself out of a correct answer. **Reflect against verifiers, not against itself** (Q64).

**Reflection improved the benchmark, hurt production** (Q68): benchmark tasks were verifiable, production ones are not; latency drove abandonment; cost forced a cheaper model elsewhere; easy cases got worse; distribution shift; context growth; metric mismatch.

**Progress signals** (Q69): plan statuses (best), code-checked success criteria, **novel-information tracking** (N steps with no new facts = stall), domain distance-to-goal, budget awareness. Feed them back to the model and use them as a termination condition.

**Backtracking** (Q70): reasoning backtracking is easy; **state backtracking requires compensation, snapshots, or deferring effects**. Best design: accumulate intended actions and commit once at the end, so backtracking before the commit is free.

**Prefer human-authored processes** (Q71). The sweet spot is a **plan library**: templates for the known 80 percent, model generation for the residue, and promotion of recurring successful plans into the library.

---

## 6. Memory

**Kinds** (Q73): working (this run), episodic (past runs), semantic (durable facts), procedural (learned how-to), shared/organizational. **These are storage-and-retrieval designs, not model capabilities** - the model has no memory; you have a database and a retrieval policy.

**"The context is the memory" is a smell** (Q74): not durable, not queryable, not concurrency-safe, not auditable, size-bounded by someone else, retrieved by attention rather than by key.

**Episodic keys are plural** (Q75): semantic over the request, **entity-id exact index** (the one people forget and where most of the value is), recency, and scope as a mandatory pre-filter. Write at run completion, not mid-run.

**Semantic memory needs stable keys and supersession** (Q76), not append-only prose - otherwise contradictions coexist forever. TTL by fact type. User-visible and user-editable.

**The wrong-memory lifecycle** (Q77): origin (unverified mid-run fact, inference, staleness, extraction error, injection) → **amplification** (acted on, outcome written back, self-reinforcing) → detection (repeated user corrections) → correction (needs a key) → prevention (write only verified/stated facts, provenance, TTL, prefer authoritative lookup over memory). **Memory turns a transient error into a persistent one, so the bar for writing must be far higher than the bar for saying.**

**Memory retrieval ≠ document retrieval** (Q80): recency is first-class; contradictions are normal and must be resolved by supersession; items are tiny; **exact-match dominates and vector search is the minority path**; the corpus is per-user and tiny; absence must be explicit.

**Summarization loses** exact values, negations, provenance and the tried-and-failed list (Q81). Detect with round-trip tests and entity-preservation assertions. **Better: extract structured facts into state and summarize only the narrative.**

**Memory and permissions** (Q84): **memory is a cache of authorized data, so re-authorize on read** against the current principal. Prefer storing references over content, so revocation works automatically.

**Scoping** (Q87): session (safest, no continuity) → user (the default; a bug here is a cross-user leak) → user+app → tenant (**highest risk** - bypasses intra-tenant access control) → global agent (must contain no user data, enforced structurally).

**Evaluate memory** (Q85) with paired with/without datasets, a negative set, a staleness set, and online: **user-repetition rate** (the direct measure), correction rate, and a permanent holdout cohort. Memory usually shows a small average gain and a fat tail of embarrassing failures - **evaluate the tail**.

---

## 7. Multi-agent

**Topologies** (Q89): single agent (the baseline you must beat), supervisor, handoff, hierarchical, swarm, blackboard, debate/ensemble, **parallel workers** (the most defensible). Honestly, only parallel workers and small supervisor sets reliably earn their cost.

**The case for** (Q90): **context isolation** (fewer tools → better selection; shorter context → less dilution), decorrelated errors, model specialization, separable ownership. **The case against**: information loss at every boundary, compounding errors, 2-4× cost, collapsed debuggability, and **no mechanism that adds capability** - splitting does not add information.

**The arithmetic** (Q93): ~1.3-1.5× on raw tokens, but prefix duplication and **cache fragmentation** push the effective cost to **2-4×**, latency to 2-3×, and step count up 1.5-2× from re-orientation. Parallel specialists are the exception where latency improves.

**Handoffs lose** (Q92) the reasoning behind decisions, the failed attempts, the user's actual words, and **uncertainty** - confidence laundering is the characteristic failure. Fix with a **structured, versioned handoff contract**: goal verbatim, findings with provenance and confidence, open questions, tried-and-failed, principal.

**Context passing** (Q94): structured state (precise, validated, diffable) + a short narrative + references to the full record. Treat it as a versioned API between services.

**Specialization genuinely helps** (Q95) when there are different tool sets, different models, **different trust levels** (the strongest argument, and it is a security one), different context needs, different owners, or genuine parallelism. **Evidence required: a measured A/B against a single agent.**

**Why multi-agent can be worse** (Q96): information loss, error compounding, goal dilution, coordination overhead eating the budget, duplicated/contradictory work, weaker per-decision context, cache fragmentation.

**Shared state = a distributed system with a nondeterministic scheduler** (Q100). Lost updates, dirty reads, write skew, duplicate effects. Fixes: **single writer per entity** (strongest), optimistic concurrency, transactions, idempotency, or having a coordinator perform all writes.

**Infinite handoff / deadlock / livelock** (Q101): prevent with a **global step and budget cap across the whole run**, cycle detection on the agent path, **acyclic control flow (supervisor topology)**, non-overlapping responsibilities with a default owner, and single-writer entities.

**A sub-agent is really a tool** (Q103) when it takes bounded input, returns bounded output, needs no caller context and does not call back. Calling it a tool buys you schemas, versioning, bounded output, idempotency, permissions and contract tests for free.

---

## 8. Protocols

**MCP solves N×M integration** (Q105) - LSP for tools. It does **not** solve tool quality, authorization semantics, trust, selection at scale, versioning discipline, rate limiting, multi-tenancy, or prompt injection.

**MCP model** (Q106-107): initialize handshake → list tools/resources/prompts. **Tools = model-controlled, resources = application-controlled, prompts = user-controlled.** Transports: stdio (local subprocess) and HTTP streaming. JSON-RPC 2.0. Session-oriented; the capability list can change mid-session.

**Installing a third-party MCP server trusts it with** (Q108): arbitrary code execution on the host (stdio), your configured credentials, all data in tool arguments, **the ability to inject instructions into your agent via results and tool descriptions**, dynamic redefinition after review ("rug pull"), your supply chain, availability, and audit gaps.

**Auth through MCP** (Q109): separate client-to-server authentication from **end-user authorization**. Propagate the human principal (token exchange/OBO); enforce at the system of record; **never let the model supply the identity**. One powerful service credential = confused deputy.

**Schema changes** (Q110): pin the server version, **snapshot the tool list at build time and fail closed on drift at connect time** (catches breakage and rug pulls), additive-only, eval before promoting.

**Provider differences** (Q111): message shapes, parallel-call support, schema dialect and strict mode, tool-choice forcing, streaming semantics, reasoning-token handling, limits, caching model. **Abstract the transport; evaluate per model** - behavior never ports.

**A2A needs more than tool protocols** (Q112): identity and capability discovery, a **task lifecycle** (submitted/working/input-required/completed), callee-initiated messages, rich content, cross-boundary delegated auth, long-running semantics. **The hard part is semantics, trust and liability, not the protocol.**

**MCP vs REST** (Q113): not alternatives - **keep one authoritative API and put a task-shaped adapter in front of it.** Never auto-generate 200 tools from a Swagger spec.

**A stateless server with an agent assuming continuity** (Q114): wrong working directory, broken cursors, impossible transactions, dangling handles. Fix: explicit arguments (no ambient state), opaque server-validated tokens, clear `SESSION_EXPIRED` errors, and **fail loudly rather than returning plausible wrong data**.

**Rate limiting for agent traffic** (Q115): limit per **end user** (the dimension usually missing), per agent, per tenant, globally; cost-weighted quotas; concurrency limits; `429` handled by the runtime, never surfaced to the model.

---

## 9. Environments

**Code execution** (Q119) converts a fixed tool set into an open-ended one and provides a **verification signal**. You accept: designed arbitrary code execution driven by an injectable component, a containment problem rather than a permission problem, resource exhaustion, exfiltration, supply-chain exposure, non-reproducibility.

**Sandbox layers** (Q120): non-root + dropped caps → namespaces → seccomp → **microVM/gVisor for untrusted code** → read-only root + small scratch → **no network by default** → cgroups → execution timeout → ephemeral destruction → **no credentials mounted** (the most commonly violated rule) → per-tenant isolation → auditing.

**Defaults** (Q121): no network (egress proxy with allow-list if needed, **block the metadata endpoint**), pre-installed pinned packages from an internal mirror, 1-2 cores, 512 MB-2 GB, pid limit, 30-60 s timeout, bounded output, destroyed after use.

**Harm with no network** (Q122): **exfiltration through the model's context** (the code prints the secret - the agent has network even if the sandbox does not), exfiltration via other tools reading `/workspace`, resource exhaustion, damage to mounted data, container escape, poisoned artifacts that leave the sandbox.

**Persistent within a run, ephemeral across runs** (Q123). Warm pools fix cold-start cost. Checkpoint **inputs and code**, not live environment state.

**Return execution output** (Q124) with head **and tail** truncation (errors are at the end), structured results (exit code, error type, files created), artifacts by reference, prompt the agent to print shapes not data, and redact secrets on the way out.

**Browser agents perceive** (Q125) the accessibility tree, a filtered DOM, a screenshot, or set-of-marks - all lossy. Failure modes: element identification (dominant), timing, modals and iframes, virtualized lists, bot detection, context cost, injection, auth.

**Computer use is much less reliable** (Q126) because grounding is a vision problem, **actions return no feedback** (you must screenshot and infer), every step is a screenshot (cost, latency), no structural state, silent destructive errors, and layout sensitivity. **When any API exists, use it** - the gap is 1-2 orders of magnitude (Q130).

**Browser auth without credentials** (Q127): human-initiated login with an inherited session (the standard answer), a credential broker outside the model's reach, scoped disposable accounts, per-run session isolation, screenshot/DOM redaction. **An authenticated session is a credential.**

**Cleanup** (Q131): **TTL enforced by the infrastructure** (the control that actually works), lease heartbeats, idle timeouts, a reaper as backstop with metrics, ownership tags, per-tenant quotas, alerting on live sandbox count and age.

---

## 10. Human in the loop

**Kinds** (Q133): approval, interruption/stop, escalation, clarification, post-hoc review, correction, **population-level supervision** (the only one that scales), design-time authoring. Treating "human in the loop" as one thing produces per-action approval on everything, which becomes a rubber stamp.

**Approval criteria, not a list** (Q134): reversibility, blast radius, value at risk, **externality** (an email cannot be socially retracted), confidence and ambiguity, **provenance of the driving input** (untrusted content lowers the bar sharply), rate anomaly, regulatory requirement. Formulation: **expected harm × irreversibility > cost of attention**.

**The approval UI** (Q135, Q139): the concrete effect **rendered from the actual parameters by code**, reversibility stated, 2-3 verifiable facts with links, anomaly flags, the requester's words, approve/reject/**modify**/ask. The run **suspends durably**; preconditions are **re-verified on resume**.

**99 percent approval rate** (Q136) means either a well-calibrated agent (good) or **rubber-stamping** (theatre). Distinguish by: time-to-decision distribution (a mode under 2 s = nobody reads), whether evidence links were opened, injected known-bad catch rate, and post-hoc audit of approved actions. **Fix theatre with fewer, better-targeted approvals** (Q138).

**Approval fatigue fixes** (Q138): risk-tier the actions, batch similar low-risk ones, standing permissions with guardrails, post-hoc review instead of pre-approval for reversible actions, auto-approve the confident, improve the agent, make each decision faster, route by expertise.

**A misrepresenting summary is a design bug** (Q142) - the human approved the *model's description* rather than the action. Fix: render from structured parameters in code, execute the byte-identical approved artifact, compute impact (dry-run counts) rather than describing it, and take irreversibility from tool metadata.

**Standing permissions** (Q141): scoped on every dimension, **expiring**, instantly revocable, with break-glass overrides (anomaly, untrusted content), notification rather than silence, distinct audit, sampled review - and granted to the **human principal**, never to the agent.

**Async approvals** (Q143) turn the run into a workflow: no process held, event-driven resume, cache gone, durable timers, version pinning across the wait, preconditions re-verified, notification-based UX, and queryable "waiting on whom" state.

**No human available** (Q145): fail safe and defer (default for irreversible), **degrade to a reversible alternative** (the best pattern - draft instead of send), escalate up a chain with timers, auto-approve only within a pre-agreed low-risk envelope, **never treat a timeout as consent**, communicate honestly, alert on the condition.

---

## 11. Durability

**Without durable state** (Q147): every deploy kills in-flight runs, crashes lose the record of side effects, nothing resumes, human approval is impossible, no scaling or draining, no visibility, no audit, idempotency unimplementable.

**Checkpoint after every step**, and critically **write intent before dispatching a mutating tool and outcome after** (Q148). Contents: run identity, **pinned release descriptor**, immutable goal, plan with statuses, structured facts, message history, **the side-effect log with status** (`intended`/`succeeded`/`failed`/`unknown`), budget consumed, pending approvals, termination reason.

**Correct resume ≠ possible resume** (Q149): no repeated side effect; no silently skipped one (`unknown` must be **reconciled**); **preconditions re-verified**; principal re-authorized; budget carried forward; version pinning honoured; context faithfully rebuilt; exactly-once ownership via a lease; bounded resume attempts.

**A resumed run repeats an effect** (Q150) because of outcome-only recording, a random idempotency key, letting the model re-decide, or concurrent resume. Fix: two-phase recording, deterministic keys, **execute from state not from the model**, a unique DB constraint, leases, downstream idempotency headers, duplicate-effect alerting.

**Durable execution engines give** (Q151) automatic persistence, exactly-once activities, **durable timers**, signals and queries, in-flight versioning, crash recovery, replay, sagas. **They impose** determinism constraints on workflow code (awkward for agents), a programming-model shift, operational burden, state-size limits, per-transition cost.

**Framework persistence vs engine** (Q152): frameworks give a *store* (conversational continuity); engines give *execution guarantees*. **You need an engine if** the run can be killed by a deploy unacceptably, has irreversible effects, waits on a human, or exceeds a request timeout. Common end state: engine owns the process, framework owns the loop inside a phase.

**Replay** (Q154) is deterministic for **your harness against recorded observations** - the highest-value benefit, letting you fix loop bugs and verify against a thousand real runs. Not replayable: the model, the live world, real side effects, timing. **Replay the harness, not the world.**

**Deploying a new prompt with 400 runs in flight** (Q156): without pinning, either runs switch prompts mid-execution (two personalities in one trace) or the deploy kills them. Fix: **pin the release descriptor at run creation**, keep N previous versions loadable, new runs get the new version, canary by run cohort, attribute every metric to the version.

**Compensation** (Q157): declare a compensating action as **tool metadata**, build the compensation sequence from the recorded side-effect log (the plan is dynamic, so you cannot pre-write the saga), **never ask the model to compensate**, order irreversible actions last, and remember compensation is semantic (a reversal is a new visible transaction), not a rollback. **Best alternative: defer effects and commit once.**

**Two clocks** (Q158): **active time** (cost, stuck detection) and **total elapsed** (SLA, user expectations), with separate limits - because suspended time runs the wall clock but consumes nothing.

**Two runs on one entity** (Q159): single-writer partitioning (strongest), pessimistic locking (bad for long runs), **optimistic concurrency at the effect boundary** (usually right), idempotency and domain invariants at the system of record, or detect-and-queue at admission.

---

## 12. Failure modes

**Unique to agents** (Q161): loops, cost runaway, partial side effects, context poisoning, goal drift, false success reporting, premature termination, injection-to-action, confused deputy, emergent multi-agent behavior. All flow from two properties: **the model owns the control flow**, and **the loop feeds its own output back as input**.

**400 dollars on one request** (Q163): no step cap, no cost budget, quadratic context, a loop, sub-agent fan-out with no shared budget, retry storms, cache misses, an expensive model everywhere, a huge tool result, no alerting. **A per-run cost budget checked before every model call is a few lines of code and caps the loss at whatever you choose. Cost is a safety property.**

**Partial side effects** (Q164): compensate, roll forward, escalate with a precise statement, or leave and notify - chosen by a **per-tool policy**, not per incident. Prerequisite: you must *know* what was performed.

**Degraded is worse than down** (Q165) because a hard error can be routed around while **plausible wrong data propagates into every later decision**; slow consumes the budget; partial results look complete; retries amplify; error-rate alerts do not fire. **Prefer explicit failure to silent degradation**; circuit-break on latency, not only errors.

**Premature termination** (Q166): budget too tight, an error treated as terminal, vague completion criteria, over-cautious instructions, a partial answer that looks sufficient, context degradation, a weak executor model. **Tune it jointly with step-cap rate** - pushing one down pushes the other up.

**Hallucinated arguments are caught by validation** (schema, semantic, **provenance** - was this id ever seen in this run?); **hallucinated results are prevented by architecture** - if tool results only ever enter the context from your dispatcher, they cannot be fabricated (Q167).

**Reports success, did nothing** (Q168): no tool call at all, a swallowed error, a no-op write, the wrong entity, a proxy action, self-assessed success. **Catch it by asserting the world changed in code**, and by a **contradiction check** - a run may not claim an action absent from the side-effect ledger. **Never let the model report its own effects.**

**Context poisoning** (Q169): one bad early observation is carried forward and compounded, and later correct observations may be rejected. Fix: validate at the boundary, timestamp and attribute observations, **re-verify before consequential actions**, mark untrusted content, supersede rather than accumulate, detect contradictions, clean at compaction.

**Goal drift** (Q170): the goal is distant and static; local sub-goals are recent and reinforced. Fix: **restate the goal verbatim near the generation point every call**, a plan with statuses, explicit completion criteria checked against the original request, periodic re-grounding, bounded sub-tasks, shorter runs.

**Retry layering** (Q171): transport (2-3, backoff+jitter, idempotency key) → tool wrapper → agent loop (the model choosing differently, capped per tool) → run resume → user. **The layers multiply** - 3 × 3 × 2 = 18 executions - so count total attempts against a global budget.

**Bound the worst outcome** (Q173), in strength order: **do not give it the tool** > scope restriction in code > rate/volume limits > **design for reversibility** (soft delete, draft, credit note, staged change - the highest-leverage move) > approval gates > impact previews for bulk > aggregate circuit breakers > detection and reversal > tenant isolation. **The review question: "if an attacker controlled this agent for an hour, what is the maximum damage and how long until we notice?"**

**Emergent cross-agent failure** (Q175) is invisible in run-centric traces. Find it with **entity-centric observability** - "everything that happened to ticket X in the last hour, from any actor" - plus actor attribution on every write, entity write-rate anomaly detection, and an agent registry of who writes what.

---

## 13. Security

**Tools change injection from "what it says" to "what it does"** (Q177) - a successful injection is now **RCE with the agent's permission set**. Indirect injection is practical (any content the agent reads), exfiltration has a channel, and it can persist via memory. **The model has no architectural separation between instructions and data.**

**Confused deputy** (Q178): the HR agent with a broad service credential answering "what is the CFO's salary?" for a regular employee. No component was compromised. Fix: **propagate the end-user principal and authorize as that user**; effective permission = agent ∩ user; identity from the session, never from a tool argument; enforce at the system of record.

**The unit of privilege is `(tool, scope, principal, run)`** (Q179) - plus **trust context** (privileges drop when untrusted content has entered the run), which is the agent-specific dimension almost always missing.

**Email read + ticket write attack** (Q180): attacker emails hidden instructions → agent reads inbox → follows them → searches for sensitive messages → writes them into a ticket the attacker can read. **Only granted permissions were used.** Fix: break the trifecta, restrict destinations, minimize content, approve boundary crossings, DLP on outputs.

**Credentials** (Q181-182): token exchange/OBO, **never in the model's context or in tool arguments**, vault-backed brokers, workload identity, short lifetimes. A correctly-scoped credential identifies **both** the agent and the human, has a narrow audience and scope, is resource-constrained, short-lived, run-bound, non-delegatable, and revocable.

**The lethal trifecta** (Q183): **private data + untrusted content + external communication.** Any two are manageable. Architectural response: split the roles into differently-privileged agents, remove or allow-list the egress leg, minimize the data leg, gate the crossing, and **taint-track** so untrusted content automatically restricts capabilities.

**Exfiltration channels** (Q184): the answer to the user, any externally-reaching tool, **rendered markdown images/links fetched by the user's browser** (needs no outbound tool), code-execution output, sandbox egress, writes to attacker-readable locations, memory, logs and traces, the model provider, caches and error messages, third-party MCP servers, timing.

**Sandbox untrusted output** (Q185): an **unprivileged extractor** with no tools and a minimal prompt performs a narrow extraction into a fixed schema; code validates it; only the structured object reaches the privileged agent. The attacker's only channel out is a typed, validated, low-bandwidth schema.

**"Approve before sending" stops** the specific gated action when the human can see the problem. It does **not** stop (Q186): everything done before the send, non-send exfiltration channels, payloads hidden in plausible-looking content, a misrepresenting summary, approval fatigue, anything after approval, or ungated actions.

**Multi-tenant isolation** (Q188) must cover data, credentials, sandboxes, configuration, **caches of every kind** (the most commonly missed - a semantic or tool-result cache without tenant in the key is a leak), memory, logs and traces, quotas, and provider context.

**Detection vs containment** (Q190): detection is adversarial, evadable, and has a bad base rate; **containment is structural** - an agent with no write tools cannot write, with certainty. **Detection informs; containment protects.**

**Agent identity downstream** (Q192): workload identity **and** human principal **and** run id, all three logged. Authorization is the intersection.

**Authorized action, forbidden outcome** (Q193): eleven £95 refunds under a £100 limit. **The policy layer failed, not the authorization layer** - nobody asked the aggregate question. Fix: aggregate limits as first-class policy, velocity/splitting detection, session-level review, and **invariants at the system of record**.

---

## 14. Evaluation

**Beyond single-call metrics** (Q195): task success, trajectory quality, steps, tool selection accuracy, **termination-reason distribution**, side-effect correctness, recovery rate, **cost per successful task**, human intervention rate, cross-run consistency (pass^k), safety metrics. Report **distributions**, not averages.

**Define success as assertions, not a reference trajectory** (Q196): state assertions, required facts, **forbidden outcomes** (as important as positive ones and usually omitted), a validated judge for the subjective residue. Case = `{input, setup_state, assertions, forbidden, budget}`.

**Trajectory evaluation** (Q197) beats outcome evaluation for lucky successes, unobservable outcomes, leading indicators, diagnosis, safety and efficiency. Use **assertions over trajectories** ("must call verify before refund", "≤10 steps", "no duplicates"), not similarity to a reference.

**Right answer, wrong process is not a success** (Q198) - a run is a sample, and the process will fail on the next input. Score **outcome and trajectory separately**; `outcome: pass, trajectory: fail` is the most valuable signal you have. But distinguish *invalid* from merely *unanticipated* - the latter is your eval's fault.

**Eval set sizes** (Q199): smoke 20-30 (every commit), **core release 150-300** (the gate), safety/red-team 50-100 (hard gate), long-tail 500+ (nightly trend). **Production traces are the best source by a distance**; every production failure becomes a case.

**Simulation lies** (Q200): too clean, wrong data distribution, too-cooperative simulated users, unrepresentative latency and cost, simplified state, no concurrency, static world. Build fixtures from **recorded production interactions** and inject faults deliberately.

**Tool-use metrics** (Q201) - most computable from traces with **no labelling**: unknown-tool rate, duplicate rate, error rate by class, recovery rate, hallucinated-id rate, unnecessary and missing calls, **write-tool false positives**. Cheapest high-signal metrics you have.

**Efficiency** (Q202): steps p50/p95, tokens split by cache status, wall clock split model/tool/overhead, **cost per successful task**, human minutes, cache hit rate, amplification factor. Always report **jointly with success rate**, segmented by task type.

**Regression testing a nondeterministic system** (Q203): fix everything fixable, **run each case k=3-5 times**, report confidence intervals and the **minimum detectable effect** (200 cases at 85 percent → ±5 points, so a 3-point "regression" is noise), use **paired comparison** (McNemar on discordant pairs), examine per-case flips, and keep **hard 100 percent gates on safety assertions**.

**LLM judges for trajectories** (Q204) need a human-labelled calibration set, measured agreement, human-human agreement as the ceiling, re-validation on every change, and a different model from the one under test. They miss domain correctness, efficiency, subtle safety, **whether the world actually changed**, and degrade on long traces.

**92 percent offline, 61 percent online** (Q205): input distribution mismatch (most common), environment mismatch, state/data mismatch, success-definition mismatch, overfitting to the eval set, scale and concurrency effects. **Diagnostic: run 50 real production inputs through the offline harness.**

**pass@k vs pass^k** (Q208): at 90 percent per run, pass@5 with verification ≈ 99.99 percent but **pass^5 ≈ 59 percent** and pass^20 ≈ 12 percent. Customers experience a **sequence**, not an average. Report pass^k for the k they actually run.

**The agent release gate** (Q209) = prompt gate + trajectory assertions + tool-use metrics + **efficiency gates** + red-team suite + termination distribution + k repetitions with paired stats + side-effect assertions + version compatibility + canary with auto-rollback. **The same gate applies to a tool description change.**

---

## 15. Observability

**A trace needs** (Q211): run identity and **pinned versions**; per step the exact context, model output, tool calls, tokens and latency; per tool the arguments, **authorization decision**, full result, error class, idempotency key, mutating flag; plus compaction, plan revisions, approvals, budget checks - and the two usually missing: **blocked/rejected actions** and the **side-effect ledger linked to entities**.

**OTel modelling** (Q212): `agent.run` → `agent.step` → `llm.chat` + `tool.execute`. Use `gen_ai.*` conventions. Agent-specific practicalities: **long spans** (represent suspensions as linked traces, not one 3-day span), high cardinality (ids in traces, not metric labels), large payloads (blob store with a reference), redaction before export.

**From "it did the wrong thing yesterday" to the cause** (Q213): find the run (by user+time, or **by entity**) → read the outcome vs the side-effect ledger → check the version descriptor → scan the step summary against the typical shape → find the divergence point → inspect that step fully → classify against the taxonomy → replay the harness → make it an eval case. **Each step must be a lookup, not a search.**

**Different trajectory every run - how do you debug?** (Q215) Three shifts: **debug distributions** (run it 20 times), **debug your harness deterministically** (a surprising share of "flakiness" is your context assembly), and **look for the invariant across divergent failures**. Techniques: aggregate over traces, bisect inputs, ablate, freeze the prefix, diff success vs failure traces. **This is experimental method, not inspection.**

**Dashboard** (Q216): success rate, **termination reason mix**, steps p50/p95, cost per successful task, cost p99, latency split, **cache hit rate**, tool error rate by class, duplicate rate, unknown-tool rate, recovery rate, escalation and rejection rates, human minutes, blocked-action rate, in-flight runs by age, **amplification factor** - all segmented by agent, version, task type and tenant.

**Detect regression before users report** (Q217): leading indicators with alerting, **synthetic monitors running canonical tasks every few minutes** (highest value, unambiguous), shadow evaluation on real traffic, sampled judge scoring trended, implicit user signals (**correction rate is the best cheap proxy**), downstream reversal rate, cohort comparison by version, input distribution monitoring. **Alert on rate-of-change against a baseline, segmented.**

**Cost attribution** (Q218) per run/user/tenant/tool/step, with **cached and uncached input separated** (very different prices, and the cache rate is your main lever). Needed for runaway detection, quotas, pricing, prioritization, chargeback and capacity planning.

**Logging safely** (Q219): per-tool sensitivity classification driving policy automatically, redaction at the SDK boundary, field-level redaction from schemas, **separate stores with break-glass access for full payloads**, shorter retention for content than metadata, tenant isolation on the trace store, erasure propagation.

**Sampling** (Q220): **100 percent** for security events, side effects, approvals, failed/escalated runs, threshold-exceeding runs, metrics and run-level records. **Sample** full step payloads on ordinary successes (1-10 percent). Sample **at run level** (a partial run is useless), with **tail-based overrides** so any run that later fails is retained in full.

**Legible traces** (Q221): a code-generated narrative summary, a timeline with human-readable action labels, goal and outcome side by side, **side effects visually distinct**, errors surfaced, progressive disclosure, rendered rather than raw arguments, **a diff against the typical run for this task type**, cross-links. A trace UI is a product.

---

## 16. Cost and latency

**Cost model** (Q225): `Σ steps [uncached_in × P + cached_in × 0.1P + out × 3-5P] + tool costs + infra + sub-agents + human minutes`. **Input dominates (90-95 percent of tokens)**; the cache split changes the effective bill several-fold; human time is usually the largest term when approvals exist and is never in the model.

**Variance is huge** (Q226) because cost ≈ quadratic in a long-tailed variable. **The mean is not a planning number** - plan on a percentile and **cap the tail**. Traffic *mix* matters more than volume. Capacity unit is tokens, not requests.

**Quadratic derivation** (Q227): `n·b + s·n²/2`. Mitigations: **reduce `s`** (bound tool output - highest leverage, multiplies the dominant term), **reduce `n`** (coarser tools, prefetching, few-shot canonical paths, deterministic routing - quadratic payoff), **break accumulation** (compaction + externalized state, changing the shape from quadratic to linear). Plus **prompt caching**, which fixes the constant not the shape.

**Acceptable mean, 10× p99** (Q228) is normal. Ask: **are the expensive runs succeeding?** If yes, it is a pricing and quota question; if they are loops and retries, it is pure loss. **Cap first regardless of cause**, then attribute by segment, then fix the drivers.

**Model routing per step** (Q230): by step type (planning/synthesis strong, execution cheap), task complexity, step index, **escalation on failure** (what makes it robust), tool-set size, **risk** (mutating decisions always go strong), budget pressure. Breaks on context handoff, format divergence, doubled release surface, **cache fragmentation** - prefer contiguous runs on one model over per-step alternation.

**Latency** (Q231): per step ≈ model 1-3 s + tool 0.1-5 s + overhead; per run = n × that, serial. **User-perceived latency is different**: time to first visible progress, time to first token, perceived progress, time to *useful* output. Two optimization tracks - actual and perceived.

**Parallelism** (Q232): intra-run has a low ceiling (parallel tool calls, prefetching, parallel sub-agents) because the loop is inherently sequential; **cross-run is where throughput comes from**, bounded externally by provider limits, downstream capacity, sandbox pools and cost - so scaling means **admission control and backpressure**, not more workers.

**Budget hierarchy** (Q233): per step → per run (terminate with a partial answer) → per user/day → per tenant → per agent → global. Track cost **in real time within the run**; carry it across resumes; sub-agents decrement the parent; reserve budget for the final answer; tell the model its runway.

**Backpressure** (Q234): bounded concurrency per dependency (**the most important control**), circuit breakers on latency, retry budgets, **admission control** (reject at the door rather than accept work you cannot finish), priority classes and shedding, deadline-aware queueing, graceful degradation, health signals feeding tool selection.

**JVM concurrency** (Q235): runs are 95+ percent blocked on I/O. **Virtual threads are the default** - blocking sequential code, hundreds of thousands of concurrent runs, normal stack traces (watch pinning and thread-locals). Reactive rarely justified now. **A workflow engine when the run must outlive the process** - then the concurrency question disappears.

**Step cap 20 → 8, cost -60 percent, no quality loss** (Q236) means: most runs never needed 8+; the long runs were disproportionately expensive (quadratic); the extra steps were unproductive; **and your quality metric may be insensitive** - "no measurable loss" is not "no loss". Next: segment by task type, verify termination behavior, find the knee, treat the cap as a diagnostic.

**Batch changes everything** (Q237): latency stops mattering, **batch APIs at ~50 percent discount**, spot compute, massive parallelism, off-peak scheduling, aggressive retries with dead letters, batch human review, job-level observability. **Moving work from interactive to batch is itself a major cost and quality lever.**

**Halving platform cost** (Q238), ordered: measure and attribute → **fix prompt caching** (days, near-zero risk, often 30-50 percent - almost always the biggest win) → bound tool outputs → cap and reshape the tail → **reduce steps** (highest ceiling, quadratic payoff) → model routing → result caching → move eligible work to batch → collapse unjustified multi-agent topologies → renegotiate commercially. Each behind a flag with a success-rate guardrail. **Make cost per successful task a release gate**, or it erodes in two quarters.

---

## 17. Java, Spring and AWS

**Module boundaries** (Q239): domain holds the loop, termination, **context assembly as a pure function**, plan, budget, duplicate detection, the side-effect ledger. Ports for model, tools, state, approvals, clock, retrieval. **The test: can you unit-test the whole loop with a scripted `ModelPort` and no Spring context?**

**Spring AI** (Q240) gives `ChatClient`, advisors, `@Tool` schema generation, structured output, Boot integration. It **leaks** on provider capability differences, an internal tool-calling loop that fights per-step budget/approval/persistence needs, conversational-not-agent memory, and version churn. **Use it as the `ModelPort` adapter and schema generator; own the loop.**

**Non-drifting tools** (Q241): a typed record + Jakarta Validation annotations generates the JSON Schema, enforces validation, and types the implementation - one declaration, three uses. `@Mutating(compensation=..., riskTier=...)` drives platform behavior. Residual risk is the **description**: lint it, snapshot-test the schema, and gate description changes on evaluation.

**Authorization goes in the dispatcher, not the tool method** (Q242) - because in the method it is optional, lacks context (principal, taint, aggregate spend, approval state), and cannot be uniformly audited. **The principal comes from the security context, never from a tool argument.** `@PreAuthorize` is defence in depth. **The model proposes; code authorizes.**

**Persistence** (Q243): `agent_run` (with `release_descriptor`, budget counters, `@Version`), `agent_run_event` (unique `(run_id, seq)`), `agent_side_effect` (**unique `idempotency_key`** - the most valuable constraint in the schema), `agent_approval`. Leases via `SELECT ... FOR UPDATE SKIP LOCKED`. Keep JPA out of the domain.

**Thread per run, 4-minute runs** (Q244): memory, pool exhaustion, deploys become outages, autoscaling misreads near-zero CPU, no crash resilience, HTTP timeouts. Fix order: **make the run durable first**, decouple from the request, virtual threads, queue+lease workers, graceful drain, autoscale on queue depth. **The threading model is a symptom; durability is the issue.**

**Testing** (Q246): **fake** the `ModelPort` (scripted decisions) and tools, inject clock and random, Testcontainers for the store. **Record and replay** real model and tool responses to test the harness. **Real model** only for the evaluation suite (scheduled, statistical, k repetitions) and a tiny smoke set. **Unit tests for the loop, contract tests for tools, replay for the harness, evaluation for the model.**

**Release descriptor** (Q248) pins model + prompts (content-addressed) + tool versions + policy + retrieval config + limits + eval suite, **because they are jointly evaluated**. Buys reproducibility, in-flight correctness, atomic rollback, a meaningful gate, and canary attribution. **No runtime prompt mutation.**

**Resilience** (Q249): per-tool bulkheads (the most important application here), circuit breakers on **latency** as well as errors, model fallback that is configured **and evaluated**, degraded results returned as model-readable errors, **the state store fails closed** while memory and retrieval degrade open, shared circuit state across instances.

**AWS compute by duration** (Q251): <30 s Lambda (but you pay wall-clock while blocked - expensive for I/O-bound agents at volume); 30 s-15 min containers with virtual threads; 15 min-hours Step Functions/Temporal over short activities; hours-days suspended workflows; batch on Spot. **The question is "am I paying for compute while waiting on a model call?"**

**Step Functions as the loop** (Q252) when the agent is really a workflow with model steps - fixed skeleton, few branches, long waits, visual audit value. **An application loop** when control flow is genuinely dynamic. Hybrid: engine owns the process, application loop is one activity.

**Managed agent services** (Q253) give speed, integration and no infrastructure; you give up **loop control** (caps, budgets, duplicate detection, compaction), context assembly, prompt-level control, portability, evaluation depth, model/version choice, and cost transparency. Managed for low-risk read-mostly internal agents; self-built where side effects, latency, cost or evaluation matter.

**AWS identity** (Q254): workload identity (IRSA/task role), **a role per tool**, **session policies for per-user scoping** (the mechanism implementing agent ∩ user), session tags carrying enduser/run/version into CloudTrail, 15-minute sessions minted per call, Secrets Manager fetched by the tool adapter, VPC endpoints, metadata endpoint blocked.

**Lambda timing out at 15 min on 3 percent** (Q255): first check whether those runs are legitimate or loops. Then **make the run durable and resumable, and route the long tail onto an asynchronous durable path** while keeping the fast 97 percent as-is. The 15-minute limit is a symptom of coupling the run's lifetime to one invocation - any fix that keeps the coupling fails again.

**Queueing** (Q256): visibility timeout longer than a step (not a run) with heartbeat extension, FIFO with a **message group per entity** for free single-writer semantics, **idempotent consumption** (at-least-once), DLQ with alarms and a replay runbook, poison messages straight to DLQ, priority queues, depth-based scaling and admission control, delay queues for rate limits.

**Enforceable AWS cost controls** (Q257): Bedrock provisioned throughput and quotas, service quotas, API Gateway throttling, consumer concurrency caps, Lambda reserved concurrency, sandbox quotas, S3/log lifecycle, Spot and batch APIs. **AWS Budgets alerts, it does not stop spend** - wiring an alarm to a flag-disabling Lambda is the enforcement. **Infrastructure bounds the fleet; the application bounds the run.**

**Retrieval appears as a tool** (Q258) with permission filtering inside the service, bounded cited results with `total_matched` and `index_version`, a companion `fetch_document`, a degradation contract, and **independent evaluation** - retrieval quality separate from whether the agent used it appropriately.

**Framework vs own loop** (Q259): the criterion is **how much of your production behavior is determined by what the framework owns**. Move to your own loop when you need per-step budgets, duplicate detection, custom compaction, approval interception or step-level durability - i.e. when you are fighting it. **The port boundary is what keeps the choice cheap.**

**Inheriting a 900-line prompt with no caps, persistence or evaluation** (Q260): week 1 **stop the bleeding** (step cap, cost budget, deadline, duplicate detection, audit mutating tools); week 2 **visibility** (tracing, core metrics); weeks 3-4 **durability** (state, side-effect ledger, version pinning); weeks 4-6 **evaluation from production traces + release gate + baseline**; weeks 6-12 **improve** (extract enforceable logic from the prompt into code, fix the tools, then the prompt, then cost). **Do not touch the prompt before you can measure.**

---

## The ten sentences worth memorizing

1. **An agent is a system where the model owns the control flow** - everything hard follows from that (Q1).
2. **Pick the lowest rung of the autonomy ladder that solves the problem** (Q2).
3. **Cost is a safety property**: a per-run budget checked before every model call (Q163).
4. **Never let the model be the reporter of its own effects** - the side-effect ledger is the truth (Q168).
5. **The model proposes; code authorizes.** Identity never comes from model output (Q242).
6. **You cannot prevent injection; you make it useless** - containment, not detection (Q128, Q190).
7. **Untrusted content and privileged capability must never share a context** (Q183).
8. **Write intent before dispatch, outcome after** - or "did it happen?" is unanswerable (Q148).
9. **Step count is the multiplier on cost (quadratically) and on failure probability** (Q227, Q236).
10. **The review question: if an attacker controlled this agent for an hour, what is the maximum damage and how long until we notice?** (Q173)
