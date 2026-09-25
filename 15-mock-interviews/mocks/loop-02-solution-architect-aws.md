# Loop 02 - Solution architect, AWS-heavy

**The role.** Solution architect at a company running a mixed estate - some on-premise Java, a growing AWS footprint, and a datacentre exit in progress. The role is customer-facing internally: you present designs to engineering leadership and to finance.

**Total time.** 4 hours 15: 30 + 60 + 45 + 45 + 45, with 10-minute breaks.

**What this loop is optimizing for.** Whether you can hold an architecture together across cost, risk and delivery, and whether you can present it to someone who does not care about availability zones. Two of the five rounds have a non-engineering audience.

---

## Round 1 - Hiring manager (30 minutes)

**Persona.** Head of architecture. Political, well-informed, and evaluating whether you will be credible in front of their stakeholders.

| Minutes | Segment |
| --- | --- |
| 0-3 | Introduction |
| 3-12 | Scope and positioning |
| 12-22 | The estate and its problems |
| 22-27 | How you work with stakeholders |
| 27-30 | Your questions |

### Opening prompt

> "Tell me about the largest architecture decision you have personally owned - not the project, the decision."

**Model answer outline.** One decision, the constraint that forced it, the alternative you rejected with the reason, the outcome with a number, and the second-order effect (Q5, Q186). Resist telling the project story; the question is deliberately narrower and answering the narrow version is the signal.

### Follow-up ladder

1. *"Who disagreed, and what did you do about it?"* (Q179)
2. *"What did that decision cost you that you did not anticipate?"*
3. *"If you had to make it again today, with what you know now?"* (Q206)

### Curveball - inject at minute 20

> "We are eleven months from a datacentre exit and about forty percent migrated. What would you want to know in your first week?"

**Model answer outline.** This previews round 3, so keep it to questions rather than a plan: what is left and why is it last (the hard things are always last), which integrations are owned by teams outside your control, has the cutover been rehearsed at production data volume, and what is the go/no-go criterion and who signs it. Then the one statement worth making: "the thing that worries me at forty percent with eleven months is not the remaining sixty percent, it is whether the buffer is real" (S14).

### Rubric focus

Communication and trade-offs. Do not go deep on AWS here; that is round 2.

---

## Round 2 - AWS and cloud architecture (60 minutes)

**Persona.** A principal cloud engineer. Has strong opinions, has been burned by serverless cost, and will ask about a service you have not used.

| Minutes | Segment |
| --- | --- |
| 0-3 | Warm-up |
| 3-22 | Architecture walkthrough |
| 22-40 | Compute, cost and quotas |
| 40-52 | Identity and networking |
| 52-60 | Questions |

### Opening prompt

> "Pick a system you have built on AWS and walk me through a request end to end. I will stop you where I am interested."

**Model answer outline.** Q78's narrated path with a justification per hop, eight to ten hops, and at least three embedded invitations to a follow-up ("the health check deliberately does not check downstream dependencies"). Have a scale number ready for the system before you start.

### Follow-up ladder

1. *"Why Fargate and not Lambda for that service?"* - Q79's decision tree said out loud, ending on the specific reason for this workload.
2. *"Someone runs the numbers and says Lambda is a third of the cost. Now what?"* - Q80. Name the range, ask for the assumptions in their model (memory setting, duration, whether they included API Gateway and NAT), and offer to do the arithmetic rather than defend a position.
3. *"You migrate and the bill is forty percent higher than the model. Where do you look first?"* - attribution before optimization (Q85), then the three usual suspects: data transfer including cross-AZ and NAT processing, storage that grows forever with no lifecycle policy, and non-production environments running at production size.

### Second thread - minute 40

> "Walk me through how a request from the internet reaches a private service, and where the identity comes from."

**Outline.** The VPC picture from Q82 without hesitation - subnets, route tables as the actual definition of public, NAT, security groups versus NACLs - plus VPC endpoints and the reason (cost and keeping traffic off NAT). Then identity: roles not users, the trust policy as the real control, and the data-plane versus control-plane distinction that catches people (Q81).

### Curveball - inject at minute 33

> "How would you use *[a service you have not used]* here?"

**What is being scored.** Q84. Bound it honestly, reason from the category, and name the questions you would ask - limits, failure mode at the limit, cost at your volume, regional or global. Then the line that turns it into a positive: "managed services fail at quotas rather than gracefully, so I would not put it on a critical path without a load test against those limits" (Q89).

### Rubric focus

Depth and trade-offs. The cost arithmetic in this round is what a solution architect is hired for.

---

## Round 3 - System design (45 minutes)

**Persona.** A senior engineer. Will inject a requirement at minute 35 and will push on cost.

Run **S13, the global API platform with data residency** (Q76), using the clock in Part B of [scenario-questions.md](../scenario-questions.md).

### Opening prompt

> "Design a public API used by customers worldwide. Some jurisdictions require that their residents' data never leaves the region."

### Follow-up ladder

1. *"Do logs count as data?"* - yes, and this is the question that separates people who have done it. Regional log storage, regional retention, aggregate metrics only crossing the boundary, and traces as the hard case.
2. *"What is your disaster recovery story in a strict region?"* - multi-AZ and in-region backups, no cross-region failover, and therefore an availability ceiling that the business must sign off on. Saying that tension out loud is the point.
3. *"A customer wants to move from one region to another. What happens?"* - export, import, cutover with a read-only window, verified deletion at the source, and honesty about backups and retention windows.

### Curveball - inject at minute 35

> "Finance has just told us we can only afford three regions, not five. Two of your strict jurisdictions do not have one."

**What is being scored.** Q68 - absorb, locate, cost, decide. The blast radius is the routing tier and the directory, not the application. The options: serve those jurisdictions from the nearest permitted region and accept the compliance exposure (usually not acceptable - say so), do not sell into them until region four is funded (the honest commercial answer), or find a partner or a co-location arrangement. The strong move is to convert it into a revenue-versus-cost question and hand it back: "this is a commercial decision - here is the cost per region and here is the revenue at risk; I can tell you what is architecturally possible, but I should not be the one choosing which jurisdictions we abandon."

### Rubric focus

Trade-offs and communication. The residency-versus-DR tension and the cost-per-region arithmetic are the two things that must be said out loud.

---

## Round 4 - Migration and delivery (45 minutes)

**Persona.** A delivery lead who has been through two failed migrations and is sceptical of architects.

| Minutes | Segment |
| --- | --- |
| 0-5 | The situation |
| 5-30 | Your plan |
| 30-40 | Pushback |
| 40-45 | Questions |

### Opening prompt

> "Ten-year-old Java monolith, on-premise, four hundred tables. The datacentre contract ends in fourteen months and the budget is fixed. What do you do?"

This is S14 (Q77). Run it against that clock.

### Follow-up ladder

1. *"Our CTO wants microservices out of this. How do you tell him no?"* - not "no". The sequencing argument: rehost by month twelve with a buffer, then strangle the two components with the strongest case, with the first extraction demonstrably done before the contract ends. Frame it as delivering the decomposition *later and for real* rather than *concurrently and partially* (Q59, Q127's tone).
2. *"What is the thing most likely to blow this up?"* - the hidden dependencies and the integrations owned by other teams; both are discovered in month one or they are discovered in month ten.
3. *"How would you know in month six whether you are on track?"* - a rehearsed cutover at production data volume, not a percentage-complete number. Say why percentage-complete is a lying metric on migrations.

### Curveball - inject at minute 30

> "We tried a parallel run last time and the reconciliation never converged. The business lost confidence and we cancelled. Why would yours be different?"

**What is being scored.** Whether you engage with a real failure or retreat into method. The answer worth giving: a reconciliation that never converges usually means the discrepancies were counted rather than **classified**, so nobody could tell a rounding difference from a missing record class. The fix is to bucket every discrepancy by cause, drive each bucket to zero or to an explicit accepted explanation, and report classes rather than a percentage - and to set the convergence criterion before starting, so "close enough" is a decision made calmly (S11, Phase 0).

### Rubric focus

Production judgement. This round is entirely about whether you have actually done one.

---

## Round 5 - Executive and finance stakeholder (45 minutes)

**Persona.** A finance director, sitting in on the loop at the CTO's request. Numerate, not technical, and will ask what things cost.

| Minutes | Segment |
| --- | --- |
| 0-10 | The business case |
| 10-25 | Challenge |
| 25-38 | A security investment |
| 38-45 | Your questions |

### Opening prompt

> "Explain to me, without using any acronyms, why moving to AWS is worth the money."

**Model answer outline.** Q91. Run-rate comparison including the costs they already pay but do not see; honesty that lift-and-shift is usually not cheaper on day one; risk removed, quantified in their terms; a staged commitment with a decision point rather than a program; and - the credibility move - naming what would make it a mistake.

### Follow-up ladder

1. *"You said it will not be cheaper immediately. When will it be, and how confident are you?"* - give a range with the assumption that dominates the error, and say what you would measure to know (Q198's habit applied to a business number).
2. *"Last time an architect told me a number, it was out by double. Why should I believe you?"* - do not get defensive. Offer the mechanism instead: a spend cap on the first tranche, a monthly attribution report, and a defined point at which we stop if the number is not tracking.
3. *"What is the cheapest version of this that still gets us out of the datacentre?"* - a real answer, and be willing to give it. Rehost, minimal modernization, right-sized from a load test, reserved capacity after sizing is proven.

### Curveball - inject at minute 25

> "Your security colleague wants two hundred thousand for tooling and a dedicated engineer. Convince me, or tell me it can wait."

**What is being scored.** Q147, and specifically whether you will say "it can wait" for part of it. The strong answer separates the velocity items (automated scanning, shared auth components - these make delivery faster and should be funded) from the pure insurance items (which need an expected-value argument with an honest range), asks for a slice rather than the program, and states in writing what is being accepted if it is declined. A candidate who argues for all of it with fear as the mechanism fails this round.

### Rubric focus

Communication, heavily. Any acronym you use without explaining costs a point. So does any answer that does not contain a number.

---

## After the loop

Check these three specifically:

- Did any number you gave in round 5 contradict a number you gave in round 2? Finance stakeholders compare notes with engineers.
- Did you use jargon in round 5? Listen to the recording with a non-technical ear.
- In rounds 3 and 4, did you name the weakest part of your own answer before being asked (Q71)? For an architect role, volunteering the flaw is the highest-yield habit in the loop.
