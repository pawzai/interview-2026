# Behavioural Scenarios

Nineteen scenarios in three parts.

**Part A** - eight situations that happen at work, not in the interview. Each is worked with **CIDER** (Clarify, Isolate, Decide, Execute, Reflect) from [../01-java/README.md](../01-java/README.md), because the behavioural version of a scenario question is graded exactly like the technical one: diagnose before you prescribe. Interviewers ask these as "what would you do if..." and they are also the raw material for stories you may already have.

**Part B** - five fully worked stories, each at **two minutes and six minutes**, showing what compression actually removes. The numbers are placeholders in the form *[p99 before]*; fill them with your own and the skeleton becomes yours.

**Part C** - the method for building the bank, and the six stories in [questions.md](questions.md) Q43-Q48 that have no scripted answer anywhere in this pack.

Work all of them **out loud**. The written versions are longer than you should speak.

---

## Part A - Situations at work

### S1. Your design was approved and a peer is quietly building the alternative (Q97)

> Three weeks after the decision, you find a branch with a working implementation of the option that was rejected. The author is a respected senior engineer who was against your design and said so once, in the review.

**Clarify.** Before anything else, find out what it is. A spike to prove a point, a genuine attempt to replace your design, or an engineer working out their disagreement in code because that is how they think. Ask them, neutrally and in private: *"I saw the branch - is that a spike, or are you proposing we switch?"* The answer determines everything, and getting it wrong in either direction is expensive.

**Isolate.** The problem is not the branch. Prototyping an alternative is legitimate and often valuable. The problem is one of three things: **the decision did not actually close** (in which case that is a process failure and partly yours); **they do not believe the decision was made on the merits**; or **they are building a constituency rather than an argument**, which is the only version that is genuinely a conduct issue.

**Decide.** Treat the first two as your problem to fix, not theirs. If the decision did not close, close it properly: what was decided, on what grounds, and what would reopen it (Q100). If they think it was decided politically, ask what evidence would change their mind and take the question seriously - a respected senior engineer who thinks a decision was unprincipled is a signal about your process, not just about them.

**Execute.** The move that resolves most of these: **give the alternative a real, bounded test**. *"Let us do this properly rather than in a branch. What would we have to measure for your version to be clearly better? If you can show that in two weeks, I will take it to the group myself."* You have converted a political situation into an experiment, and you have committed to advocating for their position if it wins - which is what makes it credible.

If it continues after that, it stops being technical: a direct conversation about the effect on the team (Q93), and then their manager, framed as a working-relationship issue rather than an accusation.

**Reflect.** The thing being tested is whether you can distinguish dissent from disloyalty. Dissent from strong engineers is an asset and the instinct to suppress it is the failure. What you must not do is escalate first, or announce the decision again more loudly.

Related: Q87, Q98, Q100.

### S2. You are asked to commit to a date on someone else's estimate (Q158)

> A programme manager sends the plan for review. Your team's work is on it, with a date you did not produce, and it is about 40 percent short. The plan goes to the steering committee tomorrow.

**Clarify.** Two questions: where did the number come from, and what is the date actually anchored to? Estimates in a plan usually come from somewhere - a previous similar project, a conversation someone half-remembers, or working backwards from a commitment. And if the date is anchored to something external and immovable (a contract, a regulator, a datacentre exit), then this is a scope conversation, not an estimate conversation.

**Isolate.** The failure mode is silence now and a slip in four months. The second failure mode is refusing the date without providing anything, which makes you the obstacle and gets the number in the plan anyway.

**Decide.** Do not negotiate the estimate. Provide a **range with the driver named and options attached** (Q158, Q126). Silence is a commitment - if it goes to the committee unchallenged, it is your number.

**Execute.** Reply today, before the meeting, in writing, to the programme manager and copy your own manager:

> "I cannot stand behind *[date]* for the full scope - my range is *[X]* to *[Y]*, and what determines where it lands is *[the named unknown]*. Three options: full scope at *[Y]*; *[the reduced set]* at *[date]*, with *[what is missing]*; or *[date]* with *[the explicit debt]* and a plan to pay it. I recommend the second. If it helps I will come to the committee and present the trade-off myself."

Offering to attend is what turns you from a blocker into a contributor, and it usually is not taken up.

**Reflect.** Get the date challenged **before** it is socialized. After the committee has seen it, you are asking people to retract in public, which costs ten times as much. And the reason plans arrive like this is usually that nobody asked you in time - so the durable fix is being in the room a step earlier.

Related: Q111, Q128, Q153.

### S3. Your team missed a commitment and the stakeholder found out from someone else (Q153)

> A director asks you in a channel, in front of others: "I hear the integration slipped to next month. When were you going to tell me?"

**Clarify.** Nothing to ask. This is answered in the first sentence and the only question is whether you take it cleanly.

**Isolate.** Two separate failures, and conflating them makes both worse. The **slip** is ordinary and forgivable. The **communication failure** is the actual problem, it is entirely yours, and it is the one that damages trust. Any answer that defends the slip is answering the wrong question.

**Decide.** Take the second one immediately and completely, in public because that is where it was asked, and move the detail to a private conversation.

**Execute.**

> "That is on me and I am sorry - you should have heard it from me last week when we knew. It has moved to *[date]* because *[the one-line reason]*. Let me send you the detail and the options in the next hour, and I will get you a standing update so this cannot happen again."

Then actually do it, within the hour. In the private follow-up: what happened, what you are doing, what you need, and the mechanism that prevents the recurrence - a fixed written update on a fixed day (Q163).

**Reflect.** No excuses, no "we were about to tell you", no explanation of how busy the week was. And the systemic fix is the interesting part: this almost always happens because status is communicated by exception, and the exception is exactly what people delay. A scheduled update with a mandatory state field removes the decision about whether to say something.

Related: Q113, Q111, Q166.

### S4. An engineer on your team is being carried, and everyone knows (Q141)

> A mid-level engineer has been on the team eighteen months. Their work is consistently reworked by two others who have stopped complaining and started routing around them. You are the tech lead, not their manager.

**Clarify.** Get past the team's consensus to what is actually observable. What specifically is wrong: correctness, scope, speed, communication, or judgement about when to ask? And critically: **has anyone told them?** In most versions of this situation, the honest answer is no - the reworking has been done silently, and the person believes they are doing fine.

**Isolate.** Three possibilities with different remedies: they are in the wrong role and could be excellent in another; they have a fixable gap and have never been told; or they are not going to make it here. You cannot tell which without an intervention, and eighteen months of silent compensation has made everything harder including the eventual conversation.

**Decide.** You own the technical feedback; their manager owns the performance process. Do your part first, properly, and tell the manager you are doing it (Q141).

**Execute.**

1. **Tell them.** Specific, recent, behavioural: *"the last two changes came back with the same class of comment - *[the specific one]*. I want to work out with you what is going on, because I do not think you have been getting straight feedback."*
2. **Agree one concrete goal** with a check-in - a component to own, a design to take through review, whatever the gap actually is.
3. **Stop the silent rework.** Tell the two engineers to review rather than rewrite, and to make the comments explicit. The compensation is what has hidden the problem.
4. **Tell their manager** what you have observed and what you are doing, factually, without a verdict.
5. **Give it a real period** - a quarter - and be honest at the end of it, including with yourself.

**Reflect.** The two failures here are letting it run because the conversation is unpleasant, and jumping to a verdict without having ever given clear feedback. The second is the one that gets defended in interviews and it is unfair to the person. Also note what it cost the two engineers who were quietly absorbing it - that is the part leaders usually miss.

Related: Q93, Q136, Q142.

### S5. A director asks you to ship past a security finding (Q223)

> Penetration test finds an authorization flaw: any authenticated user can read another tenant's *[resource]* by guessing an identifier. The launch is in four days, the customer event is booked, and the director says "can we log it and fix it in the first patch?"

**Clarify.** Establish the facts before taking a position, because the position depends on them. Is it exploitable in production as configured, or theoretical? Does it cross a tenant boundary - which it does here, and that is decisive. Is there contractual or regulatory exposure? Is there a partial mitigation that costs hours rather than days? Would we be able to tell if it were exploited?

**Isolate.** This is a **cross-tenant data exposure**, which puts it in a different class from most launch trade-offs. It is not a quality decision the delivery organization is entitled to make on its own: it is other people's data, and the exposure is silent - nobody would know it had happened.

**Decide.** Do not make it a confrontation, and do not make it your decision alone. Make it **explicit, owned, and informed** (Q223): find the cheapest mitigation, escalate to the accountable owner rather than arguing with the requester, and be clear about which line this crosses.

**Execute.**

> "Four days is not the problem - four hours might be enough. The check is missing in one place; I can put the tenant scope in the query layer and add a test, and I would want *[security]* to look at it tomorrow. What I am not willing to do is launch with a cross-tenant read open, because we could not detect it and it is not our data. If we genuinely cannot fix it, the options are launching with *[the feature disabled]* or launching to *[the single pilot tenant]* - both keep the event. If someone wants to launch open anyway, that decision needs to be *[the CISO / the accountable executive]*'s, in writing."

Then: fix it, and add the detection either way.

**Reflect.** Three things make this work rather than making you the person who blocks launches: you brought a fix rather than an objection; you offered two ways to keep the date; and you routed the decision to the person who owns the risk instead of trying to win an argument. The narrow line - other people's data, silent exposure - is what keeps your veto credible for the next time.

Related: Q157, Q170, Q225.

### S6. Two teams have been blocked on each other for six weeks (Q168)

> Team A says they are waiting for Team B's API. Team B says the requirements have never been clear. Both have escalated to you separately. Neither has written anything down.

**Clarify.** Talk to each separately first, and ask a specific question rather than "what is going on": *"what exactly do you need, in what shape, by when, and what would you do if the other team said no?"* That last part is the one that reveals whether the dependency is real.

**Isolate.** Six weeks of mutual blocking with nothing written is almost never a technical dispute. It is one of: a genuine requirements gap that nobody has been forced to write down; a priority conflict where B is being asked for something their manager has not funded; or a relationship failure where the two leads have stopped talking and are communicating through escalation.

**Decide.** Force the contract into writing and put a clock on it. The instrument is not a meeting - it is an interface definition with a date.

**Execute.**

1. **Get A to write the contract they need** - endpoints, fields, semantics, error behaviour, volume - on one page, today.
2. **Get B to respond in writing** with what they can do, by when, and what they cannot.
3. **One thirty-minute call** with both leads to close the gap, with the page on the screen. No status, only the delta.
4. **If it is a priority conflict**, stop mediating and escalate it as a resource decision to whoever owns both (Q92) - jointly, with both positions.
5. **Unblock A in the meantime**: a stub against the agreed contract so they can build against it. This step alone often reveals that the dependency was only ever about starting, not finishing.
6. **A named owner and a date** on the interface, in one place both teams can see.

**Reflect.** The thing that fixed it was making the contract explicit, and it should have taken a day in week one. The general rule worth carrying: **any cross-team dependency that has not been written down does not exist**, and the second escalation - not the first - is the signal to stop facilitating and start deciding.

Related: Q79, Q91, Q160.

### S7. The AI feature you shipped is confidently wrong in front of a customer (Q124)

> A sales engineer demos the assistant to a prospect. It states, fluently and incorrectly, that the product supports *[a capability it does not have]*. The prospect quotes it back in an email. Your CTO forwards it to you with one line: "how is this possible?"

**Clarify.** Three questions, fast, and they determine which failure you have: was the information in the retrieval corpus and wrong, absent from the corpus and hallucinated, or present and correct but retrieved poorly? Do you have the trace - the query, the retrieved context, the output? And is this a single instance or a class you have simply never measured?

**Isolate.** The failure is almost certainly not the model. It is that **the system had no abstention path**: asked something outside its grounding, it answered anyway, because nothing in the design distinguished "I retrieved good evidence" from "I retrieved nothing relevant". The second failure is that you had no evaluation covering out-of-scope questions, so this was undetectable before a customer found it.

**Decide.** Contain in hours, fix the class in weeks, and be honest with the CTO about which of these was a known gap. Do not promise that a model will stop being wrong; promise that the system will stop presenting ungrounded answers as facts.

**Execute.**

- **Same day:** pull the trace, reproduce it, and quantify - run *[N]* similar out-of-scope questions and get the actual rate. A number turns a panic into a defect.
- **Same day:** the honest reply. *"It is possible because we did not build an abstention path - asked something we have no source for, it answers from the model's prior instead of declining. That is a design gap, not a one-off. Here is the containment today and the fix in two weeks."*
- **This week:** containment - a grounding threshold below which it declines and offers to route to a human, citations shown with every factual claim, and capability questions routed to a maintained source of truth rather than free generation.
- **Two weeks:** the evaluation set that should have existed, including an out-of-scope suite, run in CI, with a published quality number and a threshold that blocks release.
- **And the non-technical part:** tell the sales team what the assistant is for and what it is not, and give them the correction to send.

**Reflect.** The story-worthy version of this is not the fix - it is that you had shipped a probabilistic component without an evaluation harness or a fallback, and that the lesson generalizes: **the design question for any AI feature is what it does when it does not know**. Mechanisms: [../09-rag](../09-rag/questions.md) Categories 10 and 11, [../08-genai](../08-genai/questions.md) Category 11.

Related: Q125, Q222, Q235.

### S8. You are asked to review an architecture with the author in the room (Q93)

> You have been asked to review a design by a senior engineer from another team. It has a real flaw - the write path can lose data under a partition - plus a lot of things that are merely not how you would do them. Their director is in the meeting.

**Clarify.** Before the meeting, one question to the person who invited you: *"what would be most useful - a risk review, or a second opinion on the approach?"* They are very different meetings, and reviewers who deliver the second when asked for the first are the reason people dread reviews.

**Isolate.** Separate the categories ruthlessly, because the single biggest failure in architecture review is a correctness issue lost in a list of preferences:

- **Blocking:** the data loss. One item.
- **Non-blocking but should change:** things that will cost them later, with a reason.
- **Questions:** things you do not understand, which are frequently your gap rather than theirs.
- **Preferences:** how you would have done it. These do not get said out loud, or they get said once, labelled as such.

**Decide.** Lead with the one blocking item, in mechanism terms, and give them the room to own the fix. The director being present makes tone decisive: the author must not be made to look incompetent, or you will have won a technical point and lost the relationship and, usually, the fix.

**Execute.**

> "One thing I would want to resolve before this is built, and then a few smaller points. On the write path - if the broker is unavailable after the commit, the state change exists in the database and nowhere else, and nothing downstream ever finds out. Is there something handling that that I have missed? *[Pause, genuinely.]* If not, the two options I know are an outbox with a relay or a transactional status column and a poller - the second is cheaper if you do not want new infrastructure. Everything else on my list is non-blocking and I am happy to send it in writing rather than spend the meeting on it."

**Reflect.** Three moves did the work: one blocking item, framed as a question so the author can discover it rather than be corrected; a cheaper alternative offered so they are not forced into a large concession; and the rest deferred to writing, which respects both their time and their standing. If they push back with a mechanism you had not considered, concede immediately and visibly - that is what makes the next review easy.

Related: Q95, Q85, [../15-mock-interviews](../15-mock-interviews/questions.md) Q166.

---

## Part B - Worked stories at two minutes and six

Five stories, each in two lengths. The two-minute version is what you say by default; the six-minute version is what you say when asked to go deeper, and it is **not the same content delivered slowly** - it adds the constraint, the alternative, the disagreement and the part that was wrong.

Every number is a placeholder. Replace them all before you rehearse; a story delivered with vague quantities is worse than one delivered with none.

### S9. The platform standard nobody asked for (Q47, Q67)

**Two minutes.**

> "At Verizon we had *[N]* services built over *[N]* years, and each one implemented its own retry and timeout behaviour. It caused a specific class of incident: a slow dependency would cause retry storms that took down healthy services. We had *[N]* of those in *[period]*, and each one was investigated locally as if it were new.
>
> I was not asked to fix this - I owned two of the affected services. What I did first was prove it was one problem: I pulled the incident records and showed *[N]* of *[M]* incidents had the same shape. That number is what made it someone's problem rather than mine.
>
> Then, rather than propose a standard, I built the client - retry with backoff and jitter, a circuit breaker, and timeouts derived from the callee's published budget - and migrated two teams myself, including the one that had been most resistant. It went into the service template about six months later, so new services got it without deciding.
>
> Adoption went from two teams to *[N]* of *[M]* services in *[period]*, and that class of incident went from *[N]* a quarter to *[N]*. The standard is still in the template *[N]* years later, and I have not worked on it since *[year]*."

**Six minutes** adds:

*The constraint.* No mandate, no platform team, and *[N]* teams with their own roadmaps. Any solution requiring other people to prioritize work for my benefit was going to fail, which is why the first version had to be something they could adopt in an afternoon.

*The alternative I rejected.* The obvious route was the architecture review board - get a standard ratified and require compliance. I had watched two previous standards go that way and neither had reached half the estate, because a ratified standard with no implementation is an unfunded mandate. The trade is that the library route is slower to start and much harder to reverse once adopted.

*The disagreement.* *[Named engineer]* on the *[X]* team was against it, and his objection was good: a shared client is a shared failure mode, and a bug in my retry logic becomes everyone's outage. I conceded that and it changed the design - every behaviour is configurable per call site with the standard as the default, we versioned it so nobody is forced onto a new release, and I added *[the specific test approach]*. He ended up being the reviewer for the first three releases.

*What I got wrong.* I set the default timeout from the p99 of the callers rather than from the callees' actual budgets, which was backwards, and it caused *[the specific problem]* for *[the team]* in the first month. It cost them *[the cost]* and it was avoidable. It also taught me the thing I now say in every review of this kind: a default in shared infrastructure is a decision made on behalf of people who are not in the room, so it needs more evidence than a decision you make for yourself.

*The second-order effect.* The unplanned one was that having a single place where retry policy lived made it possible to answer questions we could not answer before - like what our actual amplification factor was under a dependency failure. That number then drove *[the capacity decision]*.

### S10. The incident I ran badly (Q44, Q124)

**Two minutes.**

> "*[Year]*, *[the system]*, *[the scale]*. We started getting *[the symptom]* at *[time]* on a *[day]*. I took incident command.
>
> The timeline: paged at *[02:14]*; confirmed blast radius at *[02:20]* - about *[N]* percent of *[traffic]*; declared *[severity]* and posted the first update at *[02:22]*. We mitigated at *[02:31]* by *[the action]*, before knowing the cause, and customer impact ended at *[02:40]*. Root cause the next morning was *[the mechanism]*.
>
> Where I ran it badly: I stayed in command for *[five]* hours. At about hour four I made *[the decision]*, which was wrong and cost us *[N]* extra minutes of degraded service, and I made it because I was tired and had stopped writing things down. Nobody was going to tell me to hand over, because I was the commander.
>
> The fixes were both structural: the class fix for the incident itself was *[the mechanism]*, and *[the class]* has happened *[N]* times since, down from *[N]* a quarter. And we put a hard three-hour handover rule into the incident process, with a written handover checklist. I have handed over twice since and both times I was worse than I thought I was."

**Six minutes** adds:

*What made mitigation the right call.* We had two hypotheses at *[02:28]*. Failing over would fix one and be neutral for the other; the reversal cost was about *[N]* minutes. I said the reasoning out loud in the channel, gave *[name]* thirty seconds to object, and did it. The general rule I follow is to mitigate first unless mitigating is itself a one-way door - here it was not, and it bought us twenty minutes of thinking time with the customer impact already over.

*Communication.* I made *[name]* comms owner immediately so I was not writing customer updates while making changes. We updated every twenty minutes whether or not anything had changed, which sounds trivial and is the single thing that most reduces the interrupt load on the people fixing it. The update that starts "no change, still investigating, next update at *[time]*" prevents about ten individual questions.

*The bad decision in detail.* At *[06:10]* I decided to *[the action]* on the basis of *[the reasoning]*, which I would not have accepted from anyone else at *[02:00]*. Two people had reservations and did not push, because by then the shape of the room was that I was the one who had been there all night. That is the real finding: **the command role makes you harder to contradict exactly as you become less reliable.**

*What the postmortem produced, and what it did not.* Eleven actions. Nine were instance fixes and I let them all in, which I now think was wrong - the two that mattered were the class fix and the handover rule, and the other nine diluted the follow-up so much that four were never completed. I now insist on no more than three actions with named owners and dates, and the rest go on the backlog honestly rather than pretending.

*What I would do differently now.* Declare higher, earlier. We spent *[N]* minutes at *[severity minus one]* because the impact was ambiguous, and the cost of over-declaring is an apology while the cost of under-declaring is everything that happened next.

### S11. The decision I lost (Q45, Q87)

**Two minutes.**

> "We were choosing how *[the two systems]* would stay consistent. I argued for *[the event-driven approach with an outbox]*; *[named person]*, who owned the other system, argued for *[the synchronous approach]*. It mattered because *[the consequence]* and because it was expensive to reverse.
>
> My case was the partial-failure mode: if one write succeeds and the other does not, we have a divergence nobody detects, and we find it in a reconciliation weeks later. Their case - and it was a good one - was that we had no broker in production, no operational experience with one, and a *[N]*-week deadline. The decision went to *[the decider]* and they went with the synchronous version.
>
> What I did next: I said in the room that the decision was made, then built it - properly, not a half-version - and I made sure I was the one who explained it to my team. The one thing I asked for was that we agreed in advance what would make us revisit: a divergence rate above *[the threshold]*, measured by a reconciliation job I built as part of the delivery.
>
> Eighteen months later the divergence rate was *[the number]* - materially lower than I had predicted. I was wrong about the magnitude. The reconciliation job caught *[N]* real divergences in that period and each was fixed in hours rather than discovered in a quarterly audit, so the instrumentation earned its place even though my architecture did not."

**Six minutes** adds:

*Why I lost, honestly.* I brought a correctness argument to a decision that was actually about operational capacity. My probability of divergence was an assertion, not a measurement, and when I was asked how often it would happen I did not have a number. They had one for the cost of running a broker with a team that had never run one. **The person with the number wins**, and that is the most durable thing I took from it.

*What committing actually looked like.* Three concrete things: I did not maintain a branch with my version; when a junior engineer asked me six months later why we had not used events, I gave them the reasoning for the decision rather than my dissent; and when *[the first incident]* happened, I did not say "this is what I warned about", because it was not - it was unrelated, and the temptation was strong enough that I remember it.

*The concession I got, and why it mattered more than the argument.* The reconciliation job was originally my consolation prize. It turned out to be the most valuable thing in the delivery: it made the divergence rate observable, which converted a permanent architectural argument into a measured property. I now ask for that in every decision I lose - **not a compromise on the design, but instrumentation on the assumption.**

*The relationship.* *[Named person]* and I worked on *[the next thing]* afterwards, and the fact that I had built their design properly is why that went well. If I had built it grudgingly, the next three decisions would have been harder.

*What I would still argue.* I would still make the same case, and I would make it with a measured divergence rate from a two-day experiment rather than with a mechanism. The design I would have built was not wrong; it was unaffordable in that context, and I did not weight the context.

### S12. Mentoring that did not work, and then did (Q46, Q136)

**Two minutes.**

> "*[Name]* joined the team as a *[mid-level]* engineer. Technically fine, but *[N]* months in they had not shipped anything end to end - work would get to *[80]* percent and stall, and someone else would finish it. Nobody had told them, which is the part I should have caught earlier.
>
> My first approach was wrong. I diagnosed a skills gap and treated it like one - pairing, design walkthroughs, more review. It made no difference for about *[two]* months.
>
> What changed it was asking a different question. I stopped trying to help and asked what happened at the point where things stalled, and the answer was that they did not know when a thing was finished and were afraid of being told it was not good enough - so they kept polishing. It was not a skills problem at all.
>
> So we changed the mechanism: we agreed the definition of done in writing before they started, with me, and I committed to not adding to it. The first one took *[N]* weeks and it was fine. *[Timeframe]* later they owned *[the component]*, were on its on-call rotation, and were promoted to senior *[when]* - and I was not their manager, so that was other people's assessment.
>
> What I took from it: I had been treating a confidence problem as a competence problem for two months, and the reason is that I never asked what was actually happening. I now start with 'walk me through the last time this happened' rather than with a plan."

**Six minutes** adds:

*The evidence they were struggling.* Concretely: three pieces of work in *[period]* had been finished by someone else, and the team had adapted around it silently - which is the thing I should have noticed first, because a team that stops complaining has usually stopped expecting a change.

*What I tried that failed, and why.* Pairing was the wrong instrument because they could do the work with me sitting there; the problem was not visible in that mode. Extra review made it actively worse - more feedback confirmed the fear that their work would not survive scrutiny. **The intervention was reinforcing the cause**, and that took me two months to see.

*The conversation that turned it.* I asked them to walk me through the last piece of work in detail, and the tell was the word "nearly". Everything was nearly done. I asked what would happen if they put it up as it was, and the answer told me everything.

*What the mechanism actually was.* Written acceptance criteria before starting, signed by both of us, plus one rule I imposed on myself: I would not add requirements once agreed, and if something was missing that was my error, not theirs. That is a real constraint and it cost me twice.

*Withdrawal.* I stopped reviewing their work at *[N]* months, deliberately and having told them I would. Then I asked them to be the reviewer for someone else, which did more for them than anything I did directly.

*The honest caveat.* One case, and I have had one that did not work: *[the brief second example]*, where I made the same diagnosis and it was genuinely a wrong-role problem. The rule I have is to give it a quarter and be honest at the end, including with their manager.

### S13. The AI capability, and what it cost (Q48, Q235)

**Two minutes.**

> "At Sonata from 2024 we built *[the capability - a retrieval-based assistant over *[the corpus]*]* for *[the client / the internal use]*. The problem it solved was *[the concrete one]*, which was costing *[the number]*.
>
> Two decisions defined it. First, retrieval over fine-tuning: the content changed *[weekly]*, and a fine-tuned model would have been stale and unauditable, where retrieval let us cite sources and update by re-indexing. Second, a smaller model behind a good retrieval layer rather than the largest available - which took cost per query from about *[X]* to *[Y]* and made it affordable for all users rather than a subset. Quality on our evaluation set was within *[N]* points.
>
> The controls are the part I would want to talk about: an evaluation set of *[N]* real questions with graded answers, run in CI with a threshold that blocks release; citations on every factual claim; an abstention path when retrieval confidence is below *[the threshold]*; and cost per query on a dashboard with an alarm, because the failure mode of these systems is economic as much as technical.
>
> Result: *[the outcome with a number]*, at *[the cost]* per month, with *[the quality measure]*. And *[the honest cost - the six weeks we spent on X that did not work]*."

**Six minutes** adds:

*What was hard, and it was not the model.* Roughly *[80]* percent of the effort was the retrieval layer and the data: parsing *[the document types]*, chunking in a way that did not split *[the meaningful unit]*, and handling permissions so that a user could not retrieve content they could not otherwise see. The permission problem was the one that nearly sank it - filtering after retrieval gave empty results for restricted users, and we had to move to filtering in the index, which changed the design.

*The evaluation story.* We shipped a first version with no evaluation beyond eyeballing, and it was fine until it was not (see S7). Building the evaluation set was *[N]* days of unglamorous work with *[the domain experts]* and it is the single highest-return thing we did - it turned every subsequent change from an argument into a measurement.

*Cost engineering as a design constraint.* Cost per query was in the design review from the start, which is unusual and which I would insist on again. The two decisions that moved it: the model choice, and caching at the *[level]*, which took *[percentage]* of queries off the model path entirely. The number I care about is cost per resolved question rather than per call, because that is the one that compares to the human alternative.

*What did not work.* *[The abandoned approach - agentic multi-step retrieval, or the larger context window without retrieval]*. We spent *[N]* weeks on it. It failed on *[the specific reason - latency, or non-determinism that made evaluation meaningless]*, and I killed it at the point where *[the criterion]*. I had set that criterion at the start, which is the only reason it was *[N]* weeks and not a quarter.

*Where I would want to learn from someone deeper.* *[The honest gap]*. And the thing I am most sceptical about in this space is *[the honest scepticism]*, which I hold less strongly than I did *[when]* because of *[the evidence]*.

Depth for the mechanisms: [../09-rag](../09-rag/README.md), [../08-genai](../08-genai/README.md), [../10-ai-agents](../10-ai-agents/README.md).

---

## Part C - Building the bank

Q43-Q48 in [questions.md](questions.md) have no scripted answer anywhere in this pack, and they are the six that matter most. Generic answers to them are transparent at nineteen years of experience. This part is the method.

### The method

**Write each one long, once.** Ugly, honest, with the real names, the real numbers and the parts that did not go well. Do not write it as an answer; write it as an account. Expect an hour per story, and expect to discover that you have forgotten numbers you will have to go and find.

**Then extract the spine** (Q26): four sentences - stakes with a number, the decision, the outcome with a number, the learning. Memorize the spine, never the paragraph.

**Then score it** against the Q17 checklist and the Q33 rubric. The failures will be consistent - usually a missing Situation number and a missing second-order effect - and it is much easier to fix them on paper than in the room.

**Then find the faces** (Q35). Write the alternative Task line and the alternative Learning for each competency the story can serve, and mark them on the coverage matrix (Q39).

**Then rehearse at two lengths**, out loud, recorded. Not the words - the spine plus fifteen details. The six-minute version is a different artifact from the two-minute one (S9-S13 show what the difference contains), and if yours is the short one delivered slowly, it is not ready.

### What every one of the six must contain

- A number in the Situation and a number in the Result.
- A decision that was yours, with the alternative you rejected and why.
- A named person who disagreed, resisted, or changed their mind.
- A second-order effect - what changed beyond the thing itself.
- Something you got wrong, volunteered rather than extracted.
- A Learning that is a rule, plus a case of applying it since.

### S14. The largest system you architected end to end

This is the story most likely to be asked twice in a loop by interviewers who compare notes, so both lengths must be genuinely different tellings rather than one truncated.

Lead with **decisions, not boxes**. The two-minute version is scope, your role, the two decisions that defined the design, and the outcome; the six-minute version adds the constraint that forced it, the alternative you rejected, the part that turned out wrong, and what you would build differently now.

Guard against the two failures: describing the system instead of your contribution, and being unable to say which parts of the design were personally yours. Prepare the counterfactual (Q6) - it is the standard follow-up here.

### S15. A production incident you led

Tell it as **incident command, not debugging** (Q118). Have real clock times; they are more convincing than any adjective, and the gap between mitigation and root cause is itself the evidence that you did them in the right order.

The interviewer is listening for the specific things in Q117 to Q123: that you took command and said so, that you mitigated before diagnosing and can say why, that you communicated on a cadence, that you made a call with incomplete information, and that the follow-up changed the class of failure rather than fixing the instance. S10 is a worked version, including the harder variant where you also handled part of it badly.

### S16. A technical decision you lost

The entire value is in the second half (Q87, Q88). Prepare the **strongest possible version of the other side's argument**, because your ability to state it fairly is what is being scored, and a candidate who cannot is telling the interviewer they never really understood the objection.

Have the mechanism by which you committed visibly, the condition you agreed for revisiting, and what actually happened - including, ideally, that you were wrong. Choose a decision that mattered; losing an argument about a library choice demonstrates nothing. S11 is a worked version.

### S17. Mentoring a struggling engineer to independence

The evidence is the hard part. "They improved" is not evidence; a role they now hold is (Q134). Have a before and after that a third party could verify, and a timeframe.

Include **what you tried that did not work and the moment you changed approach** (Q135) - mentoring stories without a course correction sound like coaching theory rather than experience. Be ready for "have you ever failed at that?" and have the honest second example (Q136). S12 is a worked version.

### S18. Driving a standard across teams you did not own

This is the principal-level story in the bank, and the one most likely to carry the level call. It must contain the Q66 evidence: what you built that made the right way easier than the wrong way, who resisted and what changed their mind, and - the strongest close available - **that it outlived your involvement**.

Have the adoption number over time, the team you failed to win over and why (Q70), and the part of the standard you had to give up to get the rest accepted. A story where everyone agreed is not a story about influence. S9 is a worked version.

### S19. The AI capability you shipped since 2024

The trap here is telling it as a technology story. The interviewer at principal level is asking whether you can put a **probabilistic component into production responsibly**, so the content is the controls: evaluation before deployment, grounding and citation, the abstention path, cost per unit as a design constraint, and what happens when it is confidently wrong.

Have the numbers - cost per query, the quality measure, the volume - and have the thing that did not work with the criterion you used to kill it. Two years of depth next to nineteen of platform is a strength only if you claim the intersection and name the gap (Q236). S13 is a worked version, and S7 is the failure mode to be ready for.
