# Behavioural Pack

The **evidence** pack for a Principal Engineer / Technical Lead / Solution Architect move: what the leadership competencies actually mean at this level, how a story is constructed so that an interviewer can write down a fact rather than an impression, and the story bank built from nineteen years at Nittany Technologies (2007-2010), Verizon India (2010-2022) and Sonata Software (2022-present).

Packs `01` to `11` prove you know the material. This one proves you have **used** it on other people, on money, on deadlines and on your own mistakes.

---

## What this pack owns, and what it does not

There are two behavioural packs in this repository and they are deliberately split.

| | Owned here (`12-behavioural`) | Owned by [../15-mock-interviews](../15-mock-interviews/README.md) |
| --- | --- | --- |
| Competency model | What "ownership" and "influence" mean at principal level, and what evidence satisfies each | - |
| Story content | Building, quantifying and refreshing the bank | - |
| Delivery mechanics | - | Timing, the follow-up ladder, recovery, what the interviewer writes down (Q176-Q206 there) |
| Rehearsal | Drills in [scenario-questions.md](scenario-questions.md) Part C | Full timed loops in [../15-mock-interviews/mocks](../15-mock-interviews/mocks/README.md) |

**The frameworks are not redefined here.** The four-layer technical answer, CIDER for scenarios and **STAR-L** for behavioural questions are defined once in [../01-java/README.md](../01-java/README.md). The ten-story seed list in that same file is what [scenario-questions.md](scenario-questions.md) Part C expands into a full bank.

---

## Files in this pack

| File | Purpose | When to use |
| --- | --- | --- |
| [README.md](README.md) | The competency matrix, what interviewers probe, the roadmap | Read first |
| [questions.md](questions.md) | 250 questions across 15 categories | Daily drilling |
| [answers.md](answers.md) | Hybrid: coaching keys for technique, drafted STAR-L skeletons for stories | After attempting yourself |
| [scenario-questions.md](scenario-questions.md) | Eight situational-judgement scenarios, five fully worked stories at two and six minutes, and the bank-building method | Weekly, out loud |
| [cheatsheet.md](cheatsheet.md) | Sentences, structures, numbers to have ready | Night before, and 30 minutes before |
| [quiz.html](quiz.html) | Interactive flashcard version | Active recall |

### About the drafted answers

Story answers are written **in the first person, as skeletons**, anchored to the real career, with the numbers left as placeholders like *[p99 before]* or *[team size]*. They are a scaffold, not a script: fill in your figures, then say it in your own words. An interviewer at this level detects a memorized paragraph within two sentences.

**Q43-Q48 have no scripted answer on purpose.** Those are the six stories that must be entirely yours; [scenario-questions.md](scenario-questions.md) Part C says how to build them.

### quiz.html

Open it directly in a browser - no server, no internet connection. Search covers question and answer text, filter by category, difficulty or progress, mark each question Known or Review with progress saved in the browser. Press `/` to focus search.

Generated from the markdown, so the markdown stays the source of truth:

```bash
python tools/build-quiz.py 12-behavioural
```

---

## The competency matrix

Every behavioural question in a principal loop is a probe into one of nine competencies. The interviewer is not scoring the story; they are scoring whether the story contains the evidence for the competency they were assigned.

| Competency | The question behind the question | Evidence that satisfies it |
| --- | --- | --- |
| **Ownership** | What happens when it is nobody's job? | You took something unassigned, and it stayed fixed after you left it |
| **Influence** | Can you change what you cannot mandate? | Named people who changed their minds, and a mechanism that made the right way the easy way |
| **Judgement** | Do you know which decisions are expensive? | A decision you deliberately did not make, or delayed, and why |
| **Conflict** | Are you expensive to work with? | Disagreement with the relationship intact and the reasoning preserved |
| **Accountability** | What do you do when you are wrong? | A failure you name before being asked, with the systemic fix |
| **Delivery under pressure** | What survives contact with a deadline? | What you cut, who you told, and when |
| **Growing people** | Do you scale through others? | Someone who is now doing work you used to do |
| **Communication upward** | Can you be trusted in front of an executive? | Bad news delivered early, with options and a recommendation |
| **Learning** | Have nineteen years produced nineteen years of experience? | A rule you now apply, and a case of applying it since |

Categories 4 through 14 of [questions.md](questions.md) map onto these. Category 1 explains the scoring, Categories 2 and 3 build the machinery, Category 15 is the narrative that holds it together.

---

## What interviewers actually probe at this level

1. **Scope, not effort.** The most common way a nineteen-year candidate is levelled down is a bank of stories in which they were the strongest engineer on the team. Principal evidence is a **second-order effect**: what changed for other teams, for the cost curve, or for the class of failure - not how hard the problem was.
2. **The counterfactual.** "What would have happened if you had not been there?" If the honest answer is "it would have shipped two weeks later", that is a senior story. Every story needs a version of the answer that names something that only happened because of a decision you made.
3. **Specific people.** Real leadership stories have named individuals in them who did something you did not expect - resisted, changed their mind, quit, escalated. Stories populated entirely by "the team" and "stakeholders" read as constructed.
4. **Numbers in both halves.** A number in the Situation makes the stakes legible; a number in the Result makes the outcome falsifiable. One without the other is half a story, and the Situation number is the one candidates forget.
5. **Your own mistake, volunteered.** At this level the willingness to name the weakest part of your own work, unprompted, is treated as a proxy for how you will behave in a design review two years from now.
6. **Tone under disagreement.** More principal loops are lost on how criticism is given and received than on any factual gap. A story where you were right and everyone else was foolish scores below one where you were right and it took you three weeks to bring people with you.

---

## Study roadmap

### Week 1 - The machinery

Categories 1, 2 and 3. Do not attempt stories yet. Finish the week able to state the competency matrix from memory, quantify a result you no longer have data for, and compress any story to a four-sentence spine.

### Week 2 - Draft the bank

[scenario-questions.md](scenario-questions.md) Part C, plus Q43-Q48. Write the eight core stories in full, once, with real details - long form, ugly, honest. Then reduce each to a spine. This is the only week with substantial writing in it.

### Week 3 - Ownership, influence, conflict

Categories 4, 5 and 6. These three carry the most principal-level weight and the most rework. Map each of your stories onto the competencies it can serve.

### Week 4 - Failure, incidents, people

Categories 7, 8 and 9. Record the incident story with a real timeline. The mentoring story is the one most likely to be thin, so build the before-and-after evidence deliberately.

### Week 5 - Upward, prioritization, ambiguity, technical leadership

Categories 10 through 13, plus Part A of the scenarios. This is the week to rehearse the executive summary version of every story - the same content in ninety seconds with no jargon.

### Week 6 - Culture, narrative and delivery

Categories 14 and 15, then hand the pack to [../15-mock-interviews](../15-mock-interviews/README.md) and rehearse under the clock. Re-record the two stories you like least.

---

## Self-check before the interview

- [ ] I can name the nine competencies and give one story for each, and two for the three most central to this role.
- [ ] Every story has a number in the Situation and a number in the Result.
- [ ] Every story has a decision I made, an alternative I rejected, and the reason.
- [ ] Every story has a named person who disagreed, resisted or changed their mind.
- [ ] Every story has a second-order effect I can state in one sentence.
- [ ] I can tell my three strongest stories at two minutes and at six, and the six-minute version is not the two-minute one delivered slowly.
- [ ] I can answer "what would have happened without you?" for each of them.
- [ ] I have a failure story I would volunteer, in which the fix was systemic rather than personal.
- [ ] I have a story where I was wrong and someone junior was right.
- [ ] I can say what I cut to make a date, who I told, and when I told them.
- [ ] I can describe someone who now does work I used to do.
- [ ] I can explain nineteen years, three companies, .NET into Java and AI from 2024 as one line of reasoning rather than a chronology.
- [ ] None of my stories requires me to criticize a named employer, manager or colleague.
