# Mock Interviews Cheatsheet

Fast revision. Everything here is expanded in [answers.md](answers.md); question numbers are the index. This is the sheet to read the night before and thirty minutes before the call.

The other packs' cheatsheets carry the technical content. **This one carries the behaviour** - the sentences, the structures and the timings that decide a round when the content is already known.

---

## 1. What is being scored, in every round

**Four things, always** (Q7): depth on demand (three levels of "why"), trade-off literacy (every answer carries a cost, an alternative, a condition), production judgement (operated it, not just built it), communication (easy to follow, pleasant to work with).

**The loop is not deciding whether you can do the job** (Q1). It is deciding whether a group of people will defend hiring you **at a level**, in a room, using **written evidence**. Whatever the interviewer cannot write down did not happen.

**A usable note looks like this** (Q6): context with a number → decision with an alternative rejected → outcome with a number → what changed afterwards. Hand them one at the end of every substantial answer.

**Senior versus principal** (Q5) - the difference is always the second sentence:

| Senior note | Principal note |
| --- | --- |
| Solved a hard problem | Redefined the problem so it did not need solving |
| Knows the mechanism | Knows the mechanism and its cost at our size |
| Led a project | Changed how three teams work, and it stuck after he left |
| Handled the incident | Changed the class of incident |

**Three ways to answer everything correctly and still fail** (Q8): level mismatch (all senior-depth), assertions with no trade-offs, and unpleasant to work with. The third is invisible and nobody will tell you.

---

## 2. The frameworks

**Four-layer technical answer:** direct answer → mechanism → trade-off → experience hook. The fourth layer is the one that disappears under time pressure and the one that becomes the interviewer's note.

**CIDER for scenarios:** Clarify, Isolate, Decide, Execute, Reflect. Say the clarifying questions out loud even when you answer them yourself.

**STAR-L for behavioural**, with the time budget (Q176): Situation 20s, Task 15s, **Action 80s**, Result 25s, Learning 15s. **The letter everyone overruns is Situation.** Practise the two-sentence version.

Full definitions in [../01-java/README.md](../01-java/README.md).

---

## 3. Round timings

**45-minute technical round** (Q9): 3 min framing → 30-32 min substance → 5 min their must-asks → 5 min your questions. **The common failure is front-loading** - 15 minutes on the first sub-topic because you know it well.

**Design round** (Q60, Q71):

| Min | What happens |
| --- | --- |
| 0-4 | Restate, scope, constrain, plan. **No boxes yet** |
| 4-10 | Arithmetic. The one number that determines the architecture |
| 10-25 | API, data model, architecture, narrated end to end |
| 25-38 | The deep dive **they** choose, failure modes attached to each box |
| 38-42 | Scale, cost, what breaks first at 10x |
| 42-45 | Summary, **name your own weakest part**, one question |

**Coding round** (Q148-153): 3 min clarify and plan → working version → one test early → edge cases → say what you skipped and why.

**Rapid fire** (Q201): lead with the answer, one clause of justification, **stop**. Six questions covered out of twenty is a fail.

---

## 4. Sentences to have ready

**Opening a design round:** *"I will do the API and data model, then the architecture, then go deep wherever you find it most interesting, then failure modes and cost. Does that order work?"*

**Checkpointing** (the single highest-value habit): *"That is the write path - does that hold up, or would you rather push on it before I move to reads?"*

**Offering the fork** (Q65): *"The three hard parts are X, Y and Z. Which would you like me to go into?"*

**Closing a design round** (Q71): *"The part I am least happy with is X - it works, but it couples A to B, and with more time I would look at C."*

**Bounding a gap** (Q31, Q195): *"I have not run that in production, so let me separate what I know from what I would verify. The mechanism is X. What I would want to know before adopting it is Y, and I would find that out by Z."*

**Marking the edge** (S6): *"Past this point I am reasoning rather than recalling, so treat it as a hypothesis."*

**Disagreeing with the interviewer** (Q34, Q194): *"That may be a difference in how we are using the term - my understanding is X, because [mechanism]. Is there a case where it holds?"*

**Correcting yourself** (Q193): *"Before we go on - I want to correct something I said earlier. I told you X; it is actually Y."*

**Skipping deliberately** (Q51, Q153): *"In production I would validate here and throw a typed exception; I am skipping it for time and assuming valid input."*

**Landing an overrun** (Q203): *"I am going long - let me land it in two sentences."*

**Getting a number out of a vague interviewer** (Q63): *"I need one number or every choice becomes arbitrary. Can I assume X and revise?"*

---

## 5. Arithmetic you must do out loud

**System sizing** (Q62):

| Quantity | Carry this |
| --- | --- |
| Seconds/day | ~100,000 |
| 1M writes/day | ~12/s average, 30-60/s at peak |
| Peak:average | 2-5x consumer |
| Small row | ~1 KB → 1M rows/day ≈ 1 GB/day ≈ 365 GB/year |
| One Postgres | low thousands of transactions/s |
| Latency | memory ns · SSD ~100 µs · same-region ~0.5 ms · cross-region 50-150 ms · disk seek ~10 ms |

**Tokens and cost** (Q122): ~1.3 tokens per word; a page ≈ 500-800 tokens; **output costs several times input**; attention is quadratic in sequence length; cached input ≈ a tenth of the price; an agent loop's input ≈ `n·b + s·n²/2`.

**Reliability:** 0.95 per step over 20 steps = 36 percent. 99 percent per step over 16 steps = 85 percent. **Fewer steps, not better prompts.**

**Availability:** 99.9 percent = ~43 min/month. 99.95 = ~22 min. Single-AZ RDS does not fit either.

**The purpose of estimation is to eliminate a concern.** Say which one you just eliminated.

---

## 6. The trap questions

| Prompt | The trap | The move |
| --- | --- | --- |
| "Would you use Kafka here?" (Q70) | Answering the product question | State the property you need, then the component |
| "Assume infinite scale" (Q63) | Accepting it | Convert to a bounded number |
| "Lambda is cheaper" (Q80) | Agreeing or disagreeing | Name the range and offer the arithmetic |
| "Do you version your APIs?" (Q55) | Saying yes | The real question is retirement - usage telemetry, agreed deadline, **brownout** |
| "We use 2PC across services" (Q47) | Lecturing them | Ask first; then blocking coordinator and availability coupling |
| "Do you store JWTs in localStorage?" (Q137) | Yes/no | Name the threat (XSS), give the default, relocate to lifetime and revocation |
| "How big can Postgres get?" (Q101) | Guessing a number | Reframe to what breaks first: write throughput, hot set, vacuum, restore time |
| "What model do you use?" (Q128) | A model name | The selection process and the swap cost |
| "Isn't this just prompt engineering?" (Q121) | Defensiveness | Concede the true part, relocate the work |
| "We deploy once a quarter" (Q116) | Challenging the frequency | Ask about hotfixes and release duration |
| Their design has a single-AZ RDS (Q88) | Silence, or a verdict | A question, with the specific consequence |
| Interviewer states something wrong (Q34) | Winning | Mechanism, not conclusion; drop it in 60 seconds |
| "I do not think that is right" (Q194) | Capitulating or arguing | Assume you might be wrong, state the mechanism, offer them a world where they are right |
| A CVE you have not heard of (Q140) | Recognizing it | The response process: SBOM, reachability, our-context severity |
| Asked about an unused service (Q31, Q84) | Bluffing | Bound it, reason from the category, name what you would test |
| "Second example of the same thing" (Q182) | A weak second | Genuinely different, or say you have one and go deeper |
| "Tell me about a failure" (Q178) | Too little | Defensible-then-wrong, real cost, owned, rule applied since |
| "Why should we hire you over pure Java?" (Q200) | Defensiveness | Reframe onto the role's scarce skill, end with a question |

---

## 7. Diagnostic openers

Interviewers use "here is a symptom, what do you do" constantly. **Evidence before hypothesis, every time.**

**Slow query** (Q94): always or sometimes → the plan, estimated versus actual rows → examined versus returned → what changed and when → **is it slow or is it waiting** (locks, pool queueing).

**Memory leak** (Q32): is heap after full GC trending up, and did anything deploy → histogram before dump → dump on a canary → dominator tree → off-heap is a separate hunt.

**Bad RAG answers** (Q124): was the right chunk in the context → what is the eval set and where did the cases come from → what does it do when it does not know.

**Incident** (Q106, S5): impact → change correlation → blast radius → **mitigate before diagnose** → falsifiable hypotheses → communication cadence.

**Their deployment process** (Q112): do not prescribe. Lead time and where it goes → technical or waiting-for-a-person → change failure rate → what has been tried.

**Architecture review** (Q90, Q164): purpose and constraints → trace one request → find the state → single points of failure → the boring operational things → cost. **Never critique before the first step.**

---

## 8. Review and criticism

**Order** (Q164): purpose → correctness → data → failure → operations → cost → style. The order *is* your prioritization, visibly.

**Label every comment** (Q168): **Blocking** (correctness, security, data loss, broken contract - state the consequence) · **Non-blocking, worth doing** · **Question** · **Preference, ignore me** (rarely).

**With the author present** (Q166): ask, do not assert · assume a reason exists · attack the design, never "you" · give the cost, not the verdict · say what you like and mean it.

**Twenty problems, thirty minutes** (Q172): blockers first, themes instead of instances, and say out loud what you are deliberately leaving.

**Principal reviewers notice absences** (Q173): no idempotency, no bound, no timeout, no cleanup, no way to tell it failed. And they notice what is not worth saying.

---

## 9. Behavioural

**Every story needs** (Q6, Part C): a number in the Situation and one in the Result · a decision with the alternative rejected · a **second-order effect** · something you got wrong or someone who disagreed and had a point · a Learning you can show yourself applying since.

**"We" for the outcome, "I" for the decisions** (Q181). Pure "we" leaves no evidence about you; pure "I" on a team effort reads as a problem.

**Quantifying without numbers** (Q177): ratios and multiples · orders of magnitude with a hedge · time and people · the state change ("before, a release needed a two-hour window and three approvals; after, it was a button").

**Story bank** (Q185): five or six deep stories with four or five faces each, not ten shallow ones. Memorize the **spine**, not the words. Rehearse at two minutes and at six.

**Two examples** for the three competencies most central to the role (Q182), not one each for ten.

---

## 10. Your questions

**Two to four per round, different per interviewer** (Q207). Zero is disqualifying; process questions belong with the recruiter.

**The five that move your level up** (Q208):

- "What is the decision this team keeps re-making, and why does it not stay decided?"
- "Where does the architecture disagree with itself today?"
- "Which of your constraints are real, and which are old decisions nobody has revisited?"
- "If I did this job perfectly for eighteen months, what would be different that is not on anyone's roadmap?"
- "What is the strongest argument against the direction you have chosen, and who is making it?"

**To test whether the scope is real** (Q209): *"Give me an example from the last two quarters where someone at this level changed the direction of something."* Events, not descriptions.

**To an engineer, never the manager** (Q211): what shipped late and why · how many times were you woken last month · what is the codebase like on a Tuesday afternoon · how long to your first production deploy.

**Always in reserve:** *"What would you want to know if you were me, that does not come up in interviews?"*

---

## 11. Offer and negotiation

**Never volunteer your current number** (Q21). Redirect to expectation, anchored on the role.

**No signal on their range** (Q214): ask for theirs once; if refused, give a range **whose bottom you would accept**, and never a single number.

**Levers, most to least movable** (Q215): sign-on · equity · start date · remote arrangements · an accelerated review with written criteria · **scope in writing** · level (hardest, most valuable - ask early) · base (least movable).

**Write your walk-away number down before the conversation.** The classic failures are saying a number you had not pre-decided and filling a silence with a concession.

**Competing offer** (Q216): must be real, you must be willing to take it, never a threat. Transparency + genuine preference with a reason + specific ask + permission to say no.

**Ask nobody asks for** (S4, Q215): *"Can we write down what the first project is and what decisions sit with this role?"* The reluctance is the signal.

---

## 12. The day itself

**What degrades, in order** (Q204): your structure → your listening → your numbers → your warmth. The last interviewer of the day sees the warmth, and is often the bar raiser.

**Countermeasures:** eat and drink between every round · get out of the chair · same opening question each round as a reset ritual · one index card of six numbers · **do not carry the last round with you** · no cramming on the day.

**Ask for the schedule in advance**, and if you get a choice, put the round you care most about early.

**Thirty minutes before:** read sections 4, 5 and 9 of this sheet, and your number card. Nothing else.

**The follow-up note** (Q213): within a day, short. Thanks · one specific thing you have thought about since · a correction if you owe one · interest and logistics. Nothing else.
