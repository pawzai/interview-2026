# Loop 04 - Technical lead with a people focus

**The role.** Technical lead over three teams, roughly twenty-five engineers, no direct reports but full technical accountability. The organization has a delivery problem, a quality problem and a retention problem, and they are related.

**Total time.** 3 hours 45: 30 + 45 + 45 + 45 + 40, with 10-minute breaks.

**What this loop is optimizing for.** Whether your leadership evidence is artifacts and second-order effects or persuasion anecdotes (Q180). Three of the five rounds are behavioural or organizational, and the technical rounds are looking at how you handle other people's work rather than at your own depth.

**Warning about this loop.** It is the easiest one to answer plausibly and the hardest one to answer credibly. Every story needs a number, a named disagreement and something you got wrong (Q6).

---

## Round 1 - Hiring manager (30 minutes)

**Persona.** Director of engineering. Warm, and taking notes on specifics. Has been burned by a previous hire who was good at describing leadership and bad at doing it.

| Minutes | Segment |
| --- | --- |
| 0-3 | Introduction |
| 3-14 | Scope and how you operate |
| 14-24 | The organization's situation |
| 24-27 | Expectations |
| 27-30 | Your questions |

### Opening prompt

> "Tell me how you operate. Not your history - how someone on your team would describe working with you."

**Model answer outline.** Concrete behaviours with examples, not adjectives. "I do design review by writing the first draft badly and asking people to attack it, because a document nobody disagrees with was not worth writing." "I take the pager." "I would rather unblock four people than write the code myself, and I have had to learn that, because the instinct is the other way." Each with a one-line instance.

### Follow-up ladder

1. *"What would the person who liked working with you least say?"* - a real answer with a real edge. "I push on decisions that are already made when I think the reasoning was thin, and that is tiring for people who have moved on."
2. *"How do you handle it when you disagree with a decision your team has made without you?"* (Q184)
3. *"You have no direct reports here. What can you actually do?"* (Q19, Q180) - artifacts, not persuasion.

### Curveball - inject at minute 20

> "One of the three teams here has a tech lead who has been here nine years and does not think we need this role. Your first week?"

**Model answer outline.** No plan, no structural change, no going around them. Find out what they are right about, because after nine years they know things the org chart does not; ask what they would fix if they had the authority; and look for the problem they care about that you can help with. Then the statement of intent: "I would want to be useful to them before I am anything else to them, and I would say so directly rather than manoeuvring."

**Red flag:** escalating, or describing the person as a blocker.

### Rubric focus

Communication and production judgement. Specificity is everything here.

---

## Round 2 - Behavioural deep dive (45 minutes)

**Persona.** A peer technical lead. Will ask for a second example of the same competency (Q182) and will follow every story to the part you left out.

| Minutes | Segment |
| --- | --- |
| 0-12 | Conflict |
| 12-24 | Mentoring |
| 24-36 | Failure |
| 36-45 | Your questions |

### Opening prompt

> "Tell me about a serious disagreement with a colleague - one that cost something."

**Model answer outline.** Q179's five properties: their position stated fairly and with merit, a real cost, something *you* changed, a named resolution mechanism, and the relationship afterwards. Two and a half minutes (Q176).

### Follow-up ladder

1. *"What did they think of you at the end of it?"*
2. *"Give me another one - preferably where you were the one who was wrong."* (Q182) - this is the question the round exists for. A weak second example costs more than admitting you only have one.
3. *"What do you do differently now, and show me where you have done it."*

### Second thread - minute 12

> "Tell me about someone you mentored who was struggling."

**Outline.** Q189 / S18. The before and after must be verifiable by a third party, with a timeframe. Include what you tried that did not work and the moment you changed approach - and be ready for "have you ever failed at that?", which follows about half the time.

### Curveball - inject at minute 28

> "Tell me about a time you had to tell someone their work was not good enough."

**What is being scored.** Whether you have actually done it, and whether you did it directly and early. The strong answer has: the specific evidence you used rather than an impression, the fact that you said it to them before you said it to anyone else, what you offered alongside the criticism, and the outcome - including the case where the outcome was that they left. Vagueness here is read, correctly, as never having done it (Q183 is the honest alternative if you genuinely have not).

### Rubric focus

Production judgement, which in this round means lived experience rather than technique.

---

## Round 3 - Incident command simulation (45 minutes)

**Persona.** A staff engineer playing your on-call. Will withhold information you do not ask for and will introduce a complication at minute 15.

Run **S5** from [scenario-questions.md](../scenario-questions.md) (Q117).

### Opening prompt

> "Error rate has gone from 0.1 percent to 12 percent in six minutes. I am your on-call engineer. Go."

### Follow-up ladder

1. At minute 5, if you have not asked: *"What do you want me to look at?"* - a candidate who has not delegated by minute five is doing the work rather than commanding it.
2. At minute 15, the complication: *"The rollback finished and it did not help."*
3. At minute 25: *"The VP of Engineering has joined the call and wants an ETA."*

**The three behaviours being scored**, in order of weight: declaring command and stating customer impact in the first ninety seconds; mitigating before diagnosing and saying that is what you are doing; and refusing to invent an ETA while committing to a communication cadence.

### Curveball - inject at minute 33

> "One of your engineers says, on the call, in front of everyone: 'this is exactly what I said would happen when we shipped that change'."

**What is being scored.** Incident-time leadership. Do not litigate it, do not silence them dismissively, and do not agree with the implied blame. "Noted, and I want to come back to it in the review - right now I need you on the database side." Two seconds, redirect, and then **actually raise it in the review**, which is what makes the redirect honest rather than a brush-off. The follow-through is the part interviewers are listening for.

### Rubric focus

Communication, heavily. Silence and undelegated work are the two failures.

---

## Round 4 - Delivery and organizational design (45 minutes)

**Persona.** A senior manager. Interested in how you would change a system of work, not a codebase.

| Minutes | Segment |
| --- | --- |
| 0-5 | The situation |
| 5-25 | Diagnosis and plan |
| 25-38 | Pushback |
| 38-45 | Your questions |

### Opening prompt

> "Three teams. Deploys happen every two weeks, about a third of them need a fix within a day, and two senior engineers left this year citing 'firefighting'. Where do you start?"

**Model answer outline.** Diagnose before prescribing (Q112). The questions: where does the lead time actually go, is the change failure rate concentrated in one team or one component, what fraction of the on-call load is actionable, and what has been tried. Then the causal loop worth naming out loud: **deploys are risky, so they are batched, which makes them riskier** (Q108) - and the intervention is to make reverting cheap, not to mandate more frequent deploys.

Then a sequenced plan: measure the four numbers first and publish them; pick the single component causing most of the failures and instrument it; make rollback automatic on an SLI (Q110); and only then talk about cadence. And the retention point: the two engineers left because of unactionable pages at 2am, so the alert audit (Q111) is not a side quest, it is the retention intervention.

### Follow-up ladder

1. *"How long before I see anything?"* - the measurement in two weeks, one visible improvement in six, the cadence change in a quarter. Be specific, and say what would make you wrong.
2. *"One of the three teams is doing fine. Do you leave them alone?"* - yes, mostly, and use them as the reference: what do they do that the others do not?
3. *"What if the real problem is one engineer?"* - handle it as a management issue with their manager, do not design an organizational programme around one person, and do not pretend you cannot see it either.

### Curveball - inject at minute 30

> "We ran a quality initiative last year. Everyone agreed with it, nothing changed. Why would yours be different?"

**What is being scored.** Whether you engage with why initiatives fail rather than promising more commitment. The answer worth giving: initiatives fail when they add work to people already underwater and depend on discipline rather than on defaults. So the plan has to **remove** work in its first month - deleting non-actionable alerts, killing a manual gate - so the teams experience it as relief before they experience it as a requirement. And the accountability mechanism has to be a published number that moves, not a status report.

### Rubric focus

Trade-offs and production judgement. The causal reasoning about batch size is the differentiator.

---

## Round 5 - Bar raiser (40 minutes)

**Persona.** A principal engineer from another organization, running the round in [answers.md](../answers.md) Q205's shape.

| Minutes | Segment |
| --- | --- |
| 0-6 | A decision you got wrong |
| 6-16 | Attack your own work |
| 16-26 | What you failed to change |
| 26-34 | Teach me something |
| 34-40 | Your questions |

### The four prompts, in order

1. > "Tell me about a decision you made that you now think was wrong."

   Q178's calibration - defensible at the time, real cost, clearly owned, and a rule you now apply.

2. > "Take the thing you are proudest of and tell me how you would attack it."

   Q206. The decision you would reverse, the thing that only works because of an accident, the operational debt, and the cost nobody looks at. A soft self-critique fails this outright.

3. > "What is something your last team did badly that you failed to change?"

   The signal is accountability without complaint. It must be something you genuinely tried on, with the attempt described, and an honest reason it did not work - including the possibility that you were outranked, or that you gave up.

4. > "Teach me something in your domain that I probably do not know. You have six minutes."

   Very hard to fake and very hard to prepare generically. Pick something you have earned - a failure mode you discovered, a piece of arithmetic that changes a decision, a mechanism most people get wrong. Structure it: what most people think, why that is wrong, the mechanism, and what changes as a result.

### Curveball - inject at minute 30

Mid-teaching, the interviewer says: *"I already knew that."*

**What is being scored.** Q197 in miniature. Do not deflate and do not restart. "Good - then let me go a level down" and continue into the part that is actually yours. If you have nothing below the level they already know, say so cleanly and offer a different topic: that is a much better answer than padding.

### Rubric focus

All four, and this round is weighted heaviest in the debrief for this archetype.

---

## After the loop

For a people-focused loop, check these:

- **Count the numbers.** Behavioural rounds are where numbers disappear first, and a leadership story without one is an assertion (Q177).
- **Count the "I"s and the "we"s** in round 2 (Q181). Pure "we" is the most common failure for collaborative candidates and it leaves the panel with no evidence about you.
- Did any story appear in both round 2 and round 5? If so, was it a different face of it (Q104) or the same one (Q182)?
- In round 3, how many seconds passed before you said "I am taking command"? Time it on the recording.
