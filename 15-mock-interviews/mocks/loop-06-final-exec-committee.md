# Loop 06 - Final loop, executive and hiring committee

**The situation.** You have passed the technical rounds. This is the final stage: a skip-level, an executive, a bar raiser, a cross-functional peer, and the offer conversation. Nothing here is about whether you can do the work - it is about **level, risk and fit**, and it is where a loop is most often lost by a candidate who has already passed the hard rounds.

**Total time.** 3 hours: 40 + 30 + 45 + 30 + 35, with 10-minute breaks.

**Run this loop before any real interview you care about**, whatever the archetype. The level defence in round 1 and the negotiation in round 5 transfer to every role.

---

## Round 1 - Skip-level, and the level defence (40 minutes)

**Persona.** The hiring manager's manager. Has read the feedback from your technical rounds, including the one reservation. Decides the level.

| Minutes | Segment |
| --- | --- |
| 0-5 | Framing |
| 5-20 | Scope and second-order impact |
| 20-32 | The reservation from the loop |
| 32-40 | Your questions |

### Opening prompt

> "The technical feedback is positive. What I need to work out today is the level. Make the case for principal rather than senior."

**Model answer outline.** Do not answer with years or with depth. Answer with **second-order impact**, using Q5's table as the shape - three pieces of evidence, each with the sentence that makes it principal rather than senior:

> "Three things. First, *[the standard or platform artifact]* - it was adopted by *[n]* teams that did not report to me, and it is still in use two years after I stopped touching it. Second, *[the incident]* - I did not just resolve it, I changed the class of failure, and here is the number showing it stopped recurring. Third, *[the decision I talked the organization out of]* - the value there was the thing we did not build, which is the hardest kind of impact to point at and the one I would most want you to weigh."

Then invite the challenge, which is a strong move: "if there is a specific thing in the feedback that made the level a question, I would rather address it directly than guess."

### Follow-up ladder

1. *"Everything you described was in your own area. Principal here means influence across the organization. What have you changed that you had no stake in?"*
2. *"Who would be worse off if you had not been there? Name a person and what changed for them."*
3. *"What is the largest number of people whose work you have changed, and how would I verify that?"*

### Curveball - inject at minute 20

> "One of the interviewers felt your answers were strong but consistently at senior depth - lots of correct mechanism, not much organizational scope. What is your response?"

**What is being scored.** Q8's most common failure mode, delivered to your face. Do not argue with the feedback and do not collapse. The strong response: accept it as a fair read of what you *said*, take responsibility for the omission rather than for the deficiency, and supply the missing evidence.

> "That is a fair read of how I answered - I default to the mechanism because that is what technical rounds usually want, and I did not give the organizational layer. Let me give it now: *[the specific cross-team evidence]*. If it would help, I can also tell you the one where I tried and failed to change something at that scale, which is probably more informative."

That last offer is the differentiator. Volunteering the failure at the moment your level is being questioned is counter-intuitive and it works, because it is what a confident senior person does.

### Rubric focus

Trade-offs and communication. The level call is usually made in this round.

---

## Round 2 - Executive (30 minutes)

**Persona.** A CTO or VP. Thirty minutes, not technical in the details, interested in judgement and in how you talk about risk. Will not have read your resume closely.

| Minutes | Segment |
| --- | --- |
| 0-5 | Introduction |
| 5-18 | A hard call you made |
| 18-25 | Their strategy, your reaction |
| 25-30 | Your questions |

### Opening prompt

> "Tell me about a decision you made where you did not have enough information and could not wait."

**Model answer outline.** Two and a half minutes, in business language. The stakes with a number, what you knew and what you did not, the decision and the reason you could not defer, what you did to bound the downside (this is the part executives listen for), and the outcome including whether you were right. If you were wrong, say so - it is a better answer.

**The register matters more than the content.** No acronyms, no framework names, no implementation detail. If you find yourself explaining what a message queue is, you have misjudged the room.

### Follow-up ladder

1. *"What was the cost of being wrong, and who would have paid it?"*
2. *"Would you make the same call today?"*
3. *"How do you decide when to escalate a decision rather than make it?"* - the answer worth having: escalate when the decision is irreversible and expensive, when it crosses a boundary you do not own, or when it needs a mandate you cannot give yourself. Not when it is merely difficult.

### Curveball - inject at minute 18

> "We have decided to *[a strategic direction that is arguably wrong - consolidating on one cloud provider, or building an in-house platform, or a large rewrite]*. What do you think?"

**What is being scored.** Whether you flatter, whether you attack, or whether you engage. The strong shape: ask what it is optimizing for before reacting (Q170), agree with the parts that are clearly right, and name the one risk you would want managed - specifically and without drama.

> "The part I would be most confident about is *[X]*. The thing I would want someone watching is *[the specific risk]*, because it is the one that is invisible for about a year and then expensive. If I were here, that is the one I would want to own."

Ending on "that is the one I would want to own" converts a critique into an offer, which is exactly the register an executive is testing for.

### Rubric focus

Communication. Every acronym is a point off; every answer without a number is a point off.

---

## Round 3 - Bar raiser (45 minutes)

**Persona.** A principal engineer from a different organization, with no stake in the hire. Running the round from Q205.

| Minutes | Segment |
| --- | --- |
| 0-7 | A decision you got wrong |
| 7-17 | Attack your own work |
| 17-27 | The design with a flaw |
| 27-34 | What you failed to change |
| 34-40 | Teach me something |
| 40-45 | Your questions |

### The prompts

Use Q205's six questions in order. The two that carry the round:

**"Take something you built and tell me how you would attack it"** (Q206). The critique must be as sharp as a hostile outsider's - the decision you would reverse with its cost, the thing that only works because of an accident, what would happen if the two people who understand it left, and the cost nobody looks at. Close on the one you still worry about and the honest reason it is not fixed.

**"Teach me something I probably do not know"** (six minutes). Structure it: what most people believe, why that is wrong, the mechanism, and what changes as a result. Pick something you earned rather than read.

### Curveball - inject at minute 27

> "I am going to push on that until you run out. Why? … And why does that happen? … And under what conditions would that not hold?"

**What is being scored.** S6 exactly. The score is on **noticing the edge and marking it** - "past this point I am reasoning rather than recalling, so treat it as a hypothesis" - and then continuing usefully. Confident-sounding material past the boundary is the single worst outcome in this round.

### Rubric focus

All four, and this is the round with the most weight in the committee discussion.

---

## Round 4 - Cross-functional peer (30 minutes)

**Persona.** A senior product manager or a security lead - someone you would work with constantly and who has no ability to assess your code.

| Minutes | Segment |
| --- | --- |
| 0-10 | Working with you |
| 10-22 | A disagreement across the boundary |
| 22-27 | Their current problem |
| 27-30 | Your questions |

### Opening prompt

> "I work with engineers all day. Tell me what it is like to work with you when we disagree about a deadline."

**Model answer outline.** Concrete and honest, not diplomatic. The good version has: how you communicate a slip (early, with the reason and with options, never on the day), the distinction you draw between "this will take longer" and "this is the wrong thing to build", and an example where you were the one who was wrong about the estimate.

> "The thing I try to do is separate the two conversations that usually get merged - what it costs, which is mine to estimate, and whether it is worth it, which is yours to decide. Where I have got that wrong is presenting an engineering constraint as if it were a decision, which is not fair to you."

### Follow-up ladder

1. *"What do engineers do that frustrates you when you are on my side of the table?"* - a real answer, kindly put. "Estimates presented with false precision, and technical objections that are really about preference."
2. *"Give me an example where you told a product person no."* - and it must include how you offered a path rather than a wall (Q127's tone).
3. *"Have you ever shipped something you thought was a bad idea?"* - Q184. The disagree-and-commit answer, with the visible commitment and the agreed condition for revisiting.

### Curveball - inject at minute 22

> "Honestly? The last person in this role was brilliant and impossible to work with. What would be different?"

**What is being scored.** Whether you can answer without either dismissing the predecessor or promising to be pleasant. The credible shape: do not compare yourself favourably to someone you have never met; name the specific behaviours you hold yourself to and how they would be able to tell; and ask what specifically went wrong, because "impossible to work with" covers several different problems with different answers.

> "I would rather not speculate about them. What I can tell you is what you would be able to check: you would hear an estimate with its uncertainty attached rather than a number, you would hear me say 'that is your call' when it is, and if I disagree with a decision you will hear it once, directly, before it is made and not afterwards. What was the actual friction? It would help me answer this properly."

### Rubric focus

Communication. This round rarely wins a loop and frequently loses one.

---

## Round 5 - The offer conversation (35 minutes)

**Persona.** The recruiter, then the hiring manager. Run this as a rehearsal, out loud, with a partner playing hardball.

| Minutes | Segment |
| --- | --- |
| 0-8 | Expectation, with no signal |
| 8-18 | The offer, below your number |
| 18-26 | The competing offer |
| 26-32 | Scope in writing |
| 32-35 | Close |

### Sequence

**Minute 0** - *"Before we go to committee, what are you looking for compensation-wise?"* (Q214). Try once to get their range; if refused, give a range whose bottom you would accept, tied to the scope and not to your history, and keep it open.

**Minute 8** - *"The offer is [10-15 percent below your stated bottom]. We think it is strong for the level."* (Q217). Separate the two questions: is the gap fixable, and is the role still worth it if not. Make one prioritized ask with a reason that is not "I want more". Have your walk-away number written down **before** this rehearsal starts - that is the whole point of doing it as a drill.

**Minute 18** - *"Do you have other offers?"* (Q216). If you do, be transparent, state a genuine preference with a reason, make a specific ask, and give them permission to say no. If you do not, say so - inventing one is the mistake this drill exists to prevent.

**Minute 26** - the ask most candidates never make (Q215): scope in writing. "Can we write down what the first project is and what decisions sit with this role? Not a contract - just an email, so that you and I are solving for the same thing in month three." Watch how they respond; the reluctance is the signal (S4).

**Minute 32** - close by summarizing what you have asked for, in priority order, and giving a decision timeline you will actually keep.

### Curveball - inject at minute 14

> "The band is the band. I cannot move base, sign-on or equity. Take it or leave it."

**What is being scored.** Whether you have a third option prepared. The non-monetary levers are still open: a start date, an accelerated review at six months with **written criteria**, a level review at twelve months, remote or travel arrangements, and the scope commitment. The strong response asks for one of those explicitly rather than accepting flatly or walking. And - the honest half - if the number is genuinely below your walk-away, say so calmly and without hostility, because you may want to talk to these people again in two years (Q219).

### Rubric focus

Communication and composure. Score yourself on whether you named a number you had not decided in advance, and whether you filled a silence with a concession. Both are the classic failures and both are audible on the recording.

---

## After the loop

This loop is scored differently from the others.

- **Did the level defence in round 1 use second-order evidence, or did it list accomplishments?** Listen back specifically for the word "still" - "it is still in use", "they still do it that way". That word is the marker of durable impact.
- **Count the acronyms in round 2.** Anything above two is a finding.
- **In round 3, how far in did you mark your edge?** If you never marked it, you either were not pushed hard enough or you went past it without noticing - and the second is the one to worry about.
- **In round 5, did you say a number you had not pre-decided?** If yes, that is the highest-priority fix before the real conversation, and it is entirely fixable by writing the number down beforehand.
