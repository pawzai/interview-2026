# Mock Interviews Pack

The rehearsal pack for **Principal Engineer / Technical Lead / Solution Architect** loops: how a round is run and scored, how a follow-up ladder is climbed, how a design round is driven, what a wrong answer costs and how it is recovered, how a story is told so an interviewer can write down evidence, and how the offer conversation is run.

Packs `01` to `11` establish that you **know** the material. This one is about the forty-five minutes in which you have to prove it to a stranger who is taking notes.

---

## Read the technical packs first

This pack does not teach Java, AWS, retrieval or anything else. Every answer here points at the pack that owns the depth.

| Round in this pack | Owned by |
| --- | --- |
| Category 3 - Java and Spring deep dive | [../01-java](../01-java/README.md), [../02-spring](../02-spring/README.md) |
| Category 4 - Distributed systems | [../03-microservices](../03-microservices/README.md) |
| Category 5 - System design | [../04-system-design](../04-system-design/README.md) |
| Category 6 - Cloud and AWS | [../05-aws](../05-aws/README.md), [../05-aws/core-services](../05-aws/core-services/README.md) |
| Category 7 - Data and database | [../06-database](../06-database/README.md) |
| Category 8 - DevOps and incident command | [../07-devops](../07-devops/README.md) |
| Category 9 - AI | [../08-genai](../08-genai/README.md), [../09-rag](../09-rag/README.md), [../10-ai-agents](../10-ai-agents/README.md) |
| Category 10 - Security | [../11-security](../11-security/README.md) |
| Category 13 - Behavioural and leadership | [../12-behavioural](../12-behavioural/README.md) |

**The answer frameworks are not repeated either.** The four-layer technical answer, CIDER for scenarios and STAR-L for behavioral questions are defined once in [../01-java/README.md](../01-java/README.md). Re-read that section before your first mock.

If a technical answer here feels thin, that is deliberate - it is a **grading key**, not a lesson. It tells you what a strong answer must contain, what the interviewer will ask next, and what will cost you the round.

---

## Files in this pack

| File | Purpose | When to use |
| --- | --- | --- |
| [README.md](README.md) | How to run a mock, the rubric, the ramp | Read first |
| [questions.md](questions.md) | 222 questions across 15 categories | Daily drilling |
| [answers.md](answers.md) | Grading keys - strong-answer checklist, follow-up ladder, red flags, cross-pack pointer | After attempting yourself |
| [scenario-questions.md](scenario-questions.md) | Eight things that go wrong inside a loop, six full design rounds, six story rounds | Mock practice |
| [cheatsheet.md](cheatsheet.md) | Sentences, timings, arithmetic, trap questions | Night before, and 30 minutes before |
| [mocks/](mocks/README.md) | Six complete timed loops with interviewer scripts and rubrics | Full rehearsal |
| [quiz.html](quiz.html) | Interactive flashcard version | Active recall |

### mocks/

Six five-round loops, each with a persona, a verbatim opening prompt, a three-level follow-up ladder, a model-answer outline, a curveball injected at a stated minute, and a rubric. [mocks/scoring-sheet.md](mocks/scoring-sheet.md) is the printable rubric.

Run them **timed, out loud and recorded**, with the breaks. Reading a loop is worth a small fraction of speaking one.

### quiz.html

Open it directly in a browser - no server, no internet connection needed. Search covers question and answer text, filter by category, difficulty or your own progress, and mark each question Known or Review with progress saved in the browser. Press `/` to focus search.

Generated from the markdown, so the markdown stays the source of truth. After editing any of the three source files:

```bash
python tools/build-quiz.py 15-mock-interviews
```

---

## How to run a mock

**Minimum viable mock** (Q10): a timer, a question you have not scripted, speaking out loud, a recording, and one page of notes afterwards. Remove any one of those and you are training the wrong skill.

**A mock is worthless when** you read questions and think "I know that"; when there is no clock; when there are no follow-ups, because the whole game at this level is the second and third "why"; and when you stop as soon as it goes badly, because the recovery is the most valuable thing to rehearse.

**With a partner who is not in your domain** (Q14): give them the follow-up ladders in writing, and have them score only the four things a non-expert can judge reliably - did you scope before answering, was the structure statable in one sentence afterwards, were trade-offs explicit, was there a number. Add one instruction: *"if you cannot restate my answer in a sentence, mark it unclear and tell me."*

**Alone** (Q11): record, then score from the recording rather than from memory, because memory is systematically generous. Track two objective metrics session over session - **time to first structured sentence** (target under 15 seconds) and **percentage of answers containing a number** (target over half).

**Guard against the wrong kind of improvement** (Q12): a question you have answered should not reappear for two weeks; score the *process*, not the content; and put one unprepared adjacent question in every session and score only that one.

---

## The rubric

Four dimensions, every round, because these are what interviewers actually record (Q7). The full table is in [mocks/scoring-sheet.md](mocks/scoring-sheet.md).

| | Senior (2) | Principal (3) |
| --- | --- | --- |
| **Depth** | Correct mechanism when asked | Volunteered it, held up under three "why"s |
| **Trade-offs** | Named a cost when prompted | Every recommendation carried a cost, an alternative and a condition |
| **Production judgement** | One relevant anecdote | Specific operational detail - a number, a failure, a surprise |
| **Communication** | Clear but unstructured | Structure stated and kept, checkpointed, collaborative |

A round scoring 3 across the board is a hire at principal. **Two 2s with no 4s is usually a hire at the level below, which is the most common bad outcome for a 19-year candidate** (Q1, Q5).

---

## What interviewers actually probe at this level

Six recurring themes, and none of them is whether you know the material.

1. **Level, not competence.** The loop decides *at what level* to hire you, and that decision runs on second-order evidence - what changed for the organization, the cost curve or the class of failure, not what happened to the ticket (Q5). Correct answers at senior depth are the most common way a strong candidate lands a level below.
2. **Whether you scope before you answer.** Design rounds, debugging prompts, "how would you improve our process" - all of them are testing whether you diagnose before you prescribe (Q60, Q94, Q112, Q170). Interviewers use it because senior people fail it constantly.
3. **Arithmetic.** Requests per second, storage per year, tokens per call, availability minutes per month, per-step reliability compounded over a trajectory. Most candidates have never done these sums out loud, and they are what turn an opinion into a design (Q62, Q122).
4. **How you behave at the edge of what you know.** Bar raisers push until you run out, deliberately (Q192). The score is on whether you notice the edge and mark it - not on where it is (Q195, S6).
5. **How you deliver criticism and receive it.** Architecture review with the author in the room, an interviewer who is wrong, a finding you should not perform (Q166, Q169, Q194). A round can be lost entirely on tone with every technical point correct.
6. **Whether the story has a number in it.** A leadership answer without a quantified result is an assertion, and it is the first thing to evaporate under fatigue (Q177, Q204).

---

## Study roadmap

### Week 1 - Framing and the screen

Categories 1 and 2. Be able to give the 90-second introduction cold, answer "why are you looking" without criticizing anyone, and say what a debrief actually decides.

### Week 2 - The design round

Category 5, then run S9 and S10 timed and recorded. The clock in Part B should become automatic before you touch anything else.

### Week 3 - Technical rounds

Categories 3, 4, 6 and 7. Work every follow-up ladder to level 3 out loud. This is the week to find the topics where your edge is closer than you thought.

### Week 4 - AI, security, coding and review

Categories 8, 9, 10, 11 and 12. Run S12 and the review rounds. The AI round is the one most likely to be scored on numbers you do not have.

### Week 5 - Behaviour and the bar raiser

Categories 13 and 14, and build the story bank from Part C. Five or six deep stories with four or five faces each, rehearsed at two minutes and at six.

### Week 6 - Full loops

Two complete loops from [mocks/](mocks/README.md), with the breaks, plus Category 15 and a negotiation rehearsal. Then re-run your weakest single round with a different question.

The compressed ten-day version, for a loop you already have scheduled, is Q221.

---

## Self-check before the interview

- [ ] I can give a 90-second introduction that ends on their problem rather than my history.
- [ ] I can say "why are you looking" without one negative word about a current or former employer.
- [ ] I can run the first four minutes of a design round without drawing a box.
- [ ] I can do requests-per-second, storage-per-year and cost-per-call arithmetic out loud, and say which concern the number just eliminated.
- [ ] I have a three-level follow-up ladder rehearsed for the four topics most central to this role.
- [ ] I can say "I do not know" with a boundary, what I do know, and how I would find out - and then stop.
- [ ] I can disagree with a wrong statement using the mechanism, and drop it inside sixty seconds.
- [ ] I can name the weakest part of my own design before being asked.
- [ ] I can label a review comment as blocking, non-blocking, question or preference, out loud.
- [ ] I have five stories with numbers, each with a decision, a disagreement and a second-order effect.
- [ ] I have two examples for the three competencies most central to this role.
- [ ] I have three questions per interviewer type, and none of them is about process.
- [ ] I have written down my walk-away compensation number before any conversation about it.
- [ ] I have run one full loop from `mocks/`, timed, recorded, with the breaks - and read my own notes afterwards.
