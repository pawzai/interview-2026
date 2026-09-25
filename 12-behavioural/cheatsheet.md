# Behavioural Cheatsheet

Fast revision. Everything here is expanded in [answers.md](answers.md); question numbers are the index. Read it the night before, and read only the last two sections thirty minutes before.

The technical packs carry the content. This one carries the **evidence** - what a story must contain, which competency each question is buying, and the sentences that convert an anecdote into something an interviewer can write down.

---

## 1. The seven things every story must contain

1. A **number in the Situation**.
2. A **number in the Result**, of the same kind.
3. A **decision you made**, with the alternative rejected.
4. A **named person** who disagreed, resisted or changed their mind.
5. A **second-order effect** - what changed beyond the thing itself.
6. Something you **got wrong**, volunteered.
7. A **Learning that is a rule**, plus a case of applying it since.

The two most often missing: the Situation number and the second-order effect (Q17).

**Self-score with five yes/no questions** (Q33): number in the first thirty seconds; can I name the decision and the rejection; was there a person who wanted something different; did anything go wrong; can I say in one sentence what was different afterwards.

---

## 2. The nine competencies and their evidence bar

| Competency | Evidence that satisfies it |
| --- | --- |
| Ownership | Took something unassigned, and it stayed fixed after you left |
| Influence | Named minds changed, plus a mechanism that made the right way the easy way |
| Judgement | A decision you deliberately did not make, or delayed, and why |
| Conflict | Disagreement with the relationship intact |
| Accountability | A failure you name before being asked, with a systemic fix |
| Delivery under pressure | What you cut, who you told, and when |
| Growing people | Someone now doing work you used to do |
| Communication upward | Bad news early, with options and a recommendation |
| Learning | A rule you now apply, and a case of applying it since |

If you cannot tell which one is being probed, **ask**: *"are you more interested in how the decision got made, or how I got people to go along with it?"* (Q2).

---

## 3. Senior versus principal - the second sentence

The story is the same; the level is in what you say next.

| Senior | Principal |
| --- | --- |
| I fixed the leak | Three services had it from the same library, so I changed the library |
| I led the migration | It took nine months instead of eighteen because I refused the decomposition, twice |
| We reduced latency | The batch reconciliation became unnecessary, which removed a class of overnight incident |
| I solved a hard problem | I redefined the problem so it did not need solving |

Scope of **influence**, not scope of work, is what is being levelled (Q9). The test: how many teams behave differently, and would they still if you left?

---

## 4. Structure and timing

**STAR-L**, two to three minutes: Situation 20s, Task 15s, **Action 80s**, Result 25s, Learning 15s. Situation is the letter everyone overruns - **two sentences** (Q18). Full budget in [../15-mock-interviews/cheatsheet.md](../15-mock-interviews/cheatsheet.md).

**Task is the one people skip** (Q19): what you were on the hook for and what you were not. One sentence.

**"I" for decisions, "we" for execution** (Q20). A story with no "we" is a failure of leverage; a story with no "I" is unscoreable.

**Spine, not script** (Q26): stakes with a number, the decision, the outcome with a number, the learning. Memorize four sentences and improvise the rest.

**Compression is cutting, not summarizing** (Q27). Cut in this order: background, chronology, secondary characters, intermediate steps, mechanism. Keep both numbers, the decision, one person, the learning.

---

## 5. Sentences to have ready

**Handing them the note:** *"So: a *[N]*-service estate, we standardized retry and timeout at the gateway, cut incident volume by *[percentage]*, and the standard is still in the template three years later."*

**The counterfactual** (Q6): *"It would have shipped, but as *[the design on the table]*, because nobody in the room had operated one. What I do not claim is the timeline - that was *[name]*."*

**Creating a hook when there are no follow-ups** (Q11): *"The part I would do differently is that I standardized too early."*

**Offering depth without spending the clock** (Q30): *"The reason was the partial-failure case, if that is interesting."*

**Pivoting a reused story** (Q37): *"Same programme, different part - I will skip the background."*

**No example** (Q40): *"I do not have a clean example of that. The closest I have is..."*

**Saying no** (Q154): *"We can do that. It means *[the named project]* stops for six weeks. My recommendation is not to, and it is your call."*

**No date available** (Q158): *"Not before *[X]*, and I would be surprised after *[Y]*. What determines it is *[the unknown]*. I will have a date I stand behind by *[date]*."*

**Bad news** (Q153): *"Here is what I know, here is what I do not, here is what I am doing to find out, and I will update you Friday whether or not I know more."*

**Owning a reversal** (Q206): *"This was my recommendation, the assumption it rested on was *[X]*, and *[the evidence]* says *[X]* is false."*

**Blocking review comment** (S8): *"One thing I would want to resolve before this is built, and then a few smaller points."*

---

## 6. The traps, by question type

| Question | The trap | The move |
| --- | --- | --- |
| Tell me about a failure | The disguised strength, the blameless failure, the trivial one (Q102) | Real cost, systemic fix, second instance |
| Conflict | Ending on being right (Q86) | End on what it took to bring them with you |
| Disagree and commit | Only the disagreement (Q87) | Five parts: argued once, stopped, visible commitment, instrumentation, what happened |
| Influence | The well-received presentation (Q66) | Named person, mechanism, adoption number, outlived you |
| Ownership | Heroics (Q50) | It stayed fixed without you |
| Incident | Debugging instead of command (Q118) | Real clock times, mitigate before diagnose, class fix |
| Mentoring | No course correction (Q135) | What failed first, and the role they now hold |
| Deadline | Explaining the slip (Q111) | When you knew, when you said, what you offered |
| Ambiguity | Answering hypothetically (Q14) | Past tense, or the honest near-miss |
| Weakness | Disguised strength (Q239) | Real one, where it bites, the accommodation, the evidence |
| Overqualified | Protesting (Q242) | Name the real concern, then ask what the role owns after a year |
| Why leaving | Any criticism (Q238) | What you got, what you want, what this role has |

---

## 7. Numbers that land

Money, then time, then relative performance, then absolute scale (Q22). A Result number is meaningless without a Situation number of the same kind.

**When you cannot share** (Q21): percentages, orders of magnitude, or a structural change - "weekly manual reconciliation became automated" is a frequency that went to zero. Say the constraint once, then give the substitute. Never stop at "I cannot share numbers".

**Operational maturity in one number** (Q132): percentage of incidents detected by monitoring rather than by customers.

**Cost ownership** (Q58): cost per request, tenant or query - and whether the curve is sub-linear, which is the architecture claim.

---

## 8. The mechanics worth memorizing

**Adoption of a standard** (Q67, Q80): two teams in pain → mechanism before policy → migrate the first ones yourself → reference customer tells the story → default in scaffolding → deprecate the alternative → hand over to a named owner.

**Incident command** (Q119): say "I am taking incident command" → scribe, comms owner, one person changing things → mitigate before diagnose unless mitigation is a one-way door → fixed cadence updates even with no news → hand over at three hours.

**Deprecation** (Q201): instrument usage → ready migration path → announce four times → migrate the biggest yourself → brownout → blackout → delete the code.

**Escalation** (Q92): joint, written, one level, both positions stated fairly, a recommendation, a deadline. Escalate when the cost of the delay exceeds the cost of the escalation.

**Written disagreement** (Q95): state their position first → label the comment blocking / non-blocking / question / preference → never reply to the third message.

**Prioritization** (Q173): cost of delay over effort, with three named failure modes and a protected fraction for enabling work.

**Technical debt** (Q171): pay what charges interest, what is in the path of the next change, and anything that blocks detection. Most of the rest should never be paid.

---

## 9. Thirty minutes before

Read only this section and your one-page sheet (Q42).

- **The positioning sentence** (Q249) - depth with a number, then what is unusual about the combination.
- **The number strip** - every figure in the bank, in one line. Numbers are the first thing to go under fatigue.
- **The three admissions**: the failure you will volunteer, the weakest part of your best design, the thing you do not know.
- **Round assignment** - which story is primary for which interviewer, so no face repeats (Q38).
- **Two names per story**, so nothing comes out in the passive voice.

**The four habits that carry the round:** a number in the first thirty seconds; the second-order sentence at the end of every substantial answer; one volunteered mistake per round; and never a negative word about a named employer, manager or colleague.

**If you only remember one thing:** they are not scoring the story, they are scoring whether they can write down a fact. Give them the fact.
